import os
import json
import time
import asyncio
import logging
from collections import defaultdict, Counter

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, ContextTypes, filters
)
from telegram.error import BadRequest
from ads import send_ads  # Tu archivo ads.py con la función send_ads

# === Configuración inicial ===
load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
GRUPOS_FILE = "grupos.json"

if not TOKEN or not CHAT_ID or not ADMIN_ID:
    print("❌ Faltan TOKEN, CHAT_ID o ADMIN_ID en .env")
    exit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Almacenamiento de grupos ===
grupos = {}
def cargar_grupos():
    global grupos
    try:
        with open(GRUPOS_FILE, "r", encoding="utf-8") as f:
            grupos = json.load(f)
    except FileNotFoundError:
        grupos = {}

def guardar_grupos():
    with open(GRUPOS_FILE, "w", encoding="utf-8") as f:
        json.dump(grupos, f, indent=2, ensure_ascii=False)

# === Moderación y seguimiento ===
BANNED_WORDS = ["puto", "puta", "palabrota1", "spam", "scam"]
GREETING_WORDS = ["hola", "buenas", "saludos", "hey"]
THANKS_WORDS = ["gracias", "thanks", "thx", "agradecido"]
SPAM_LINKS = ["bit.ly", "tinyurl", "spam.com"]
WARNING_THRESHOLD = 3
BAN_THRESHOLD = 5
MUTE_DURATION = 60 * 10  # 10 min

user_warnings = defaultdict(int)
user_messages = defaultdict(list)
message_counter = Counter()

# === Handlers ===
async def track_group_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    status = update.my_chat_member.new_chat_member.status
    if chat.type in ("group", "supergroup"):
        if status == "member":
            grupos[str(chat.id)] = {"title": chat.title, "type": chat.type}
            guardar_grupos()
            logger.info(f"➕ Bot agregado: {chat.title} ({chat.id})")
        elif status == "kicked" and str(chat.id) in grupos:
            del grupos[str(chat.id)]
            guardar_grupos()
            logger.info(f"➖ Bot eliminado: {chat.title} ({chat.id})")

async def listar_grupos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🔒 Comando restringido.")
    if not grupos:
        return await update.message.reply_text("❌ No estoy en ningún grupo.")
    respuesta = "📋 *Grupos activos:*\n\n"
    for gid, info in grupos.items():
        respuesta += f"• *{info['title']}*\n  ID: `{gid}`\n  Tipo: `{info['type']}`\n\n"
    await update.message.reply_text(respuesta, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("logo.png", "rb") as logo:
            await update.message.reply_photo(logo, caption=f"🌟 ¡Bienvenido {update.effective_user.first_name}!")
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

async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_messages:
        return await update.message.reply_text("📉 Sin datos aún.")
    ranking = sorted(user_messages.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    mensaje = "📊 *Top 10 usuarios activos:*\n\n"
    for i, (uid, times) in enumerate(ranking, 1):
        try:
            user = await context.bot.get_chat_member(update.effective_chat.id, uid)
            nombre = user.user.full_name
        except:
            nombre = f"Usuario {uid}"
        mensaje += f"{i}. *{nombre}* — {len(times)} mensajes\n"
    await update.message.reply_text(mensaje, parse_mode=ParseMode.MARKDOWN)

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        nombre = member.username or member.first_name
        with open("logo.png", "rb") as logo:
            await update.message.reply_photo(
                logo,
                caption=(f"👋 ¡Hola {nombre}! Bienvenido 🎉\n\n"
                         "Aceptá nuestras políticas para participar.")
            )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Acepto políticas", callback_data=f"accept_policy_{member.id}")]
        ])
        await update.message.reply_text("Haz clic abajo para continuar:", reply_markup=markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("accept_policy_"):
        uid = query.data.split("_")[2]
        if str(query.from_user.id) == uid:
            await query.edit_message_text(f"✅ ¡Gracias {query.from_user.first_name}! Políticas aceptadas.")
        else:
            await query.edit_message_text("🚫 Este botón es solo para vos.")

async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()
    uid = update.message.from_user.id
    cid = update.message.chat_id

    if any(w in text for w in GREETING_WORDS):
        return await update.message.reply_text(f"¡Hola {update.message.from_user.first_name}! 👋")
    if any(w in text for w in THANKS_WORDS):
        return await update.message.reply_text(f"¡De nada {update.message.from_user.first_name}! 😊")

    if any(w in text for w in BANNED_WORDS + SPAM_LINKS):
        await update.message.delete()
        aviso = await context.bot.send_message(cid, f"⚠️ {update.message.from_user.mention_markdown()}, lenguaje inapropiado.", parse_mode="Markdown")
        user_warnings[uid] += 1
        await asyncio.sleep(30)
        await aviso.delete()
        return await check_penalties(update, context, uid)

    now = time.time()
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if now - t < 60]

    if len(user_messages[uid]) > 5:
        await update.message.delete()
        msg = await context.bot.send_message(cid, f"⚠️ {update.message.from_user.mention_markdown()}, estás spameando.", parse_mode="Markdown")
        user_warnings[uid] += 1
        await asyncio.sleep(30)
        await msg.delete()
        return await check_penalties(update, context, uid)

    message_counter[text] += 1
    if message_counter[text] > 3:
        await update.message.delete()
        msg = await context.bot.send_message(cid, f"⚠️ {update.message.from_user.mention_markdown()}, mensaje repetido.", parse_mode="Markdown")
        user_warnings[uid] += 1
        await asyncio.sleep(30)
        await msg.delete()
        return await check_penalties(update, context, uid)

async def check_penalties(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    cid = update.message.chat_id
    if user_warnings[uid] >= BAN_THRESHOLD:
        try:
            await context.bot.ban_chat_member(cid, uid)
            await context.bot.send_message(cid, "🚫 Usuario baneado.")
            await context.bot.send_message(ADMIN_ID, f"🚨 Usuario {uid} baneado.")
            user_warnings[uid] = 0
        except BadRequest as e:
            logger.error(f"❌ Error al banear: {e}")
    elif user_warnings[uid] >= WARNING_THRESHOLD:
        try:
            until = int(time.time()) + MUTE_DURATION
            permissions = ChatPermissions(can_send_messages=False)
            await context.bot.restrict_chat_member(cid, uid, permissions, until_date=until)
            await context.bot.send_message(cid, "🔇 Usuario silenciado temporalmente.")
        except BadRequest as e:
            logger.error(f"❌ Error al silenciar: {e}")

async def schedule_ads(context: ContextTypes.DEFAULT_TYPE):
    try:
        await send_ads(CHAT_ID, context.bot)
    except Exception as e:
        logger.error(f"💥 Error en anuncios: {e}")

# === MAIN ===
async def main():
    cargar_grupos()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("estadisticas", estadisticas))
    app.add_handler(CommandHandler("grupos", listar_grupos))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_message))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(ChatMemberHandler(track_group_activity, chat_member_types=["my_chat_member"]))

    app.job_queue.run_repeating(schedule_ads, interval=1800, first=10)

    logger.info("🚀 Bot iniciado correctamente")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
