import json
import random
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Lista fija de anuncios
ADS = [
    {
        "image": "producto1.jpg",
        "caption": "🔥 Producto 1 en oferta 🔥",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto1"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar1"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir1"),
        ],
    },
    {
        "image": "producto2.jpg",
        "caption": "🎉 Producto 2 exclusivo 🎉",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto2"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar2"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir2"),
        ],
    },
    {
        "image": "producto3.jpg",
        "caption": "🚀 Producto 3 con envío gratis 🚀",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto3"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar3"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir3"),
        ],
    },
    {
        "image": "producto4.jpg",
        "caption": "📦 Producto 4: última oportunidad 📦",
        "buttons": [
            InlineKeyboardButton("💲 Precio", url="https://tuweb.com/producto4"),
            InlineKeyboardButton("🛒 Comprar", url="https://tuweb.com/comprar4"),
            InlineKeyboardButton("📤 Compartir", url="https://tuweb.com/compartir4"),
        ],
    },
    {
        "image": "producto5.jpg",
        "caption": "🌟 Contratá nuestro servicio ahora 🌟",
        "buttons": [
            InlineKeyboardButton("💲 Contratar + Info", url="https://wa.me/5491161051718"),
            InlineKeyboardButton("📤 Compartir", url="https://edgarglienke.com.ar/bot"),
        ],
    },
]

# 🔁 Pool para rotación sin repeticiones
ads_pool = []

def is_within_schedule():
    """Verifica si la hora está entre las 07:00 y las 21:00"""
    now = datetime.now().time()
    return datetime.strptime("07:00", "%H:%M").time() <= now <= datetime.strptime("21:00", "%H:%M").time()

async def send_ads(chat_id: int, bot: Bot):
    """Envía un anuncio aleatorio con imagen y botones al grupo especificado."""
    global ads_pool

    if not is_within_schedule():
        logger.info("⏰ Fuera de horario de anuncios (07:00 a 21:00)")
        return

    if not ads_pool:
        ads_pool = ADS.copy()
        random.shuffle(ads_pool)
        logger.info("🔁 Reiniciando pool de anuncios")

    ad = ads_pool.pop()
    try:
        with open(ad["image"], "rb") as img:
            markup = InlineKeyboardMarkup([ad["buttons"]])
            await bot.send_photo(
                chat_id=chat_id,
                photo=img,
                caption=ad["caption"],
                reply_markup=markup
            )
    except FileNotFoundError:
        logger.warning(f"⚠️ Imagen no encontrada: {ad['image']}")
    except Exception as e:
        logger.error(f"❌ Error al enviar anuncio a {chat_id}: {e}")

async def schedule_ads(context: ContextTypes.DEFAULT_TYPE):
    """Carga la lista de grupos y envía un anuncio a cada uno."""
    try:
        with open("grupos.json", "r", encoding="utf-8") as f:
            grupos = json.load(f)

        for gid, info in grupos.items():
            try:
                await send_ads(int(gid), context.bot)
                logger.info(f"📢 Anuncio enviado a {info['title']} ({gid})")
            except Exception as e:
                logger.error(f"💥 Error en grupo {gid}: {e}")

    except Exception as e:
        logger.error(f"💥 Error al cargar grupos.json: {e}")
