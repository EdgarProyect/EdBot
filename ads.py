import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
from datetime import datetime

# Lista fija de publicidades
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

# 🔁 Lista dinámica para control sin repetición
ads_pool = []

def is_within_schedule():
    """Devuelve True si la hora actual está entre las 7 y 21hs."""
    now = datetime.now().time()
    return now >= datetime.strptime("07:00", "%H:%M").time() and now <= datetime.strptime("21:00", "%H:%M").time()

async def send_ads(chat_id, bot):
    global ads_pool

    while True:
        if not is_within_schedule():
            print("⏰ Fuera de horario de anuncios (07:00 a 21:00). Esperando 5 minutos.")
            await asyncio.sleep(300)
            continue

        if not ads_pool:
            ads_pool = ADS.copy()
            random.shuffle(ads_pool)
            print("🔁 Reiniciando pool de anuncios")

        ad = ads_pool.pop()
        try:
            with open(ad["image"], "rb") as image_file:
                markup = InlineKeyboardMarkup([ad["buttons"]])
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=image_file,
                    caption=ad["caption"],
                    reply_markup=markup
                )
        except FileNotFoundError:
            print(f"⚠️ Imagen no encontrada: {ad['image']}")
        except Exception as e:
            print(f"❌ Error al enviar anuncio: {e}")

        # Esperar un tiempo aleatorio entre publicaciones (ej. entre 15 y 45 minutos)
        wait_time = random.choice([900, 1800, 2700])  # 15, 30, 45 min
        await asyncio.sleep(wait_time)
