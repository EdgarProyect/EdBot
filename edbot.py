# edbot.py

import logging
import os
import asyncio
import time
from collections import defaultdict, Counter

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, ContextTypes, filters
)
from telegram.error import BadRequest
from ads import send_ads  # Nuestra función de anuncios del archivo ads.py

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID', '0'))
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

if not TOKEN or not CHAT_ID or not ADMIN_ID:
    print("❌ Faltan TOKEN, CHAT_ID o ADMIN_ID en el archivo .env")
    exit(1)

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuración de moderación
BANNED_WORDS = ["puto", "puta", "palabrota1", "palabrota2", "spam", "scam"]
GREETING_WORDS = ["hola", "buenas", "saludos", "hey"]
THANKS_WORDS = ["gracias", "thanks", "thx", "agradecido"]
SPAM_LINKS = ["bit.ly", "tinyurl", "acortador.com", "spam.com"]
WARNING_THRESHOLD = 3
BAN_THRESHOLD = 5
MUTE_DURATION = 60 * 10  # 10 minutos

# Seguimiento de usuarios
user_warnings = defaultdict(int)
user_messages = defaultdict(list)
message_counter = Counter()

# Botón para aceptar políticas
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("accept_policy_"):
        user_id = query.data.split("_")[2]
        if str(query.from_user.id) == user_id:
            await query.edit_message_text(
                f"✅ ¡Gracias {query.from_user.first_name}! Has aceptado las políticas del grupo."
            )
        else:
            await query.edit_message_text("🚫 Este botón es solo para el usuario que acaba de unirse.")

# Publicación programada de anuncios
async def schedule_ads(context: ContextTypes.DEFAULT_TYPE):
    try:
        await send_ads(CHAT_ID, context.bot)
    except Exception as e:
        logger.error(f"💥 Error enviando anuncios automáticos: {e}")

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("logo.png", "rb") as logo:
            await update.message.reply_photo(logo, caption=f"🌟 ¡Bienvenido {update.message.from_user.first_name}! 🌟")
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌍 Facebook", url="https://facebook.com/tu_pagina"),
                InlineKeyboardButton("🐦 Twitter", url="https://twitter.com/tu_perfil"),
                InlineKeyboardButton("📸 Instagram", url="https://instagram.com/tu_perfil"),
                InlineKeyboardButton("🎥 YouTube", url="https://youtube.com/tu_canal")
            ],
            [
                InlineKeyboardButton("💻 Web", url="https://edgarglienke.com.ar"),
                InlineKeyboardButton("📱 WhatsApp", url="https://wa.me/5491161051718")
            ]
        ])
        await update.message.reply_text("📲 ¡Sígueme en mis redes sociales!", reply_markup=markup)
    except Exception as e:
        logger.error(f"💥 Error en /start: {e}")

# Comando /estadisticas
async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_messages:
        await update.message.reply_text("📉 Aún no hay suficientes datos para generar estadísticas.")
        return

    ranking = sorted(user_messages.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    mensaje = "📊 *Top 10 usuarios más activos del grupo:*\n\n"
    for i, (user_id, timestamps) in enumerate(ranking, 1):
        try:
            user = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            nombre = user.user.full_name
        except:
            nombre = f"Usuario {user_id}"
        mensaje += f"{i}. *{nombre}* — {len(timestamps)} mensajes\n"

    await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

# Bienvenida a nuevos miembros
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            username = member.username or member.first_name or "Invitado"
            with open("logo.png", "rb") as logo:
                await update.message.reply_photo(
                    logo,
                    caption=(f"👋 ¡Hola {username}! Bienvenido al grupo. 🎉\n\n"
                             "Por favor acepta nuestras políticas para participar.")
                )
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Acepto políticas", callback_data=f"accept_policy_{member.id}")]
            ])
            await update.message.reply_text("Haz clic abajo para continuar:", reply_markup=markup)

# Moderación de mensajes
async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    message = update.message
    text = message.text.lower()
    user_id = message.from_user.id
    chat_id = message.chat_id

    if any(word in text for word in GREETING_WORDS):
        await message.reply_text(f"¡Hola {message.from_user.first_name}! 👋")
        return
    elif any(word in text for word in THANKS_WORDS):
        await message.reply_text(f"¡De nada {message.from_user.first_name}! 😊")
        return

    if any(word in text for word in BANNED_WORDS + SPAM_LINKS):
        await message.delete()
        warning = f"⚠️ {message.from_user.mention_markdown()}, evita lenguaje o enlaces inapropiados."
        warn_msg = await context.bot.send_message(chat_id, text=warning, parse_mode="Markdown")
        user_warnings[user_id] += 1
        await asyncio.sleep(30)
        await warn_msg.delete()
        await check_penalties(update, context, user_id)
        return

    now = time.time()
    user_messages[user_id].append(now)
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < 60]

    if len(user_messages[user_id]) > 5:
        await message.delete()
        msg = await context.bot.send_message(chat_id, text=f"⚠️ {message.from_user.mention_markdown()}, estás spameando.", parse_mode="Markdown")
        user_warnings[user_id] += 1
        await asyncio.sleep(30)
        await msg.delete()
        await check_penalties(update, context, user_id)
        return

    message_counter[text] += 1
    if message_counter[text] > 3:
        await message.delete()
        msg = await context.bot.send_message(chat_id, text=f"⚠️ {message.from_user.mention_markdown()}, no repitas el mismo mensaje.", parse_mode="Markdown")
        user_warnings[user_id] += 1
        await asyncio.sleep(30)
        await msg.delete()
        await check_penalties(update, context, user_id)
        return

# Penalización por spam y lenguaje
async def check_penalties(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    chat_id = update.message.chat_id
    if user_warnings[user_id] >= BAN_THRESHOLD:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.send_message(chat_id, text="🚫 Usuario baneado por múltiples infracciones.")
            await context.bot.send_message(ADMIN_ID, f"🚨 Usuario {user_id} baneado.")
            user_warnings[user_id] = 0
        except BadRequest as e:
            logger.error(f"❌ Error al banear: {e}")
    elif user_warnings[user_id] >= WARNING_THRESHOLD:
        try:
            until = int(time.time()) + MUTE_DURATION
            permissions = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(chat_id, user_id, permissions, until_date=until)
            await context.bot.send_message(chat_id, text="🔇 Usuario silenciado temporalmente.")
        except BadRequest as e:
            logger.error(f"❌ Error al silenciar: {e}")

# Mensaje cuando el bot es agregado a un grupo
async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    if result.new_chat_member.status in ["member", "administrator"]:
        try:
            with open("logo.png", "rb") as logo:
                await context.bot.send_photo(
                    chat_id=result.chat.id,
                    photo=logo,
                    caption=f"🤖 ¡Gracias por añadirme a *{result.chat.title}*!",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"💥 Error en bienvenida a grupo: {e}")

# Función principal
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estadisticas", estadisticas))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER))

    app.job_queue.run_repeating(schedule_ads, interval=1800, first=10)

    logger.info("🚀 Bot iniciado correctamente")
    await app.run_polling()

# Ejecución directa
if __name__ == "__main__":
    asyncio.run(main())
