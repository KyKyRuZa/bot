# main.py
import asyncio
import uvicorn
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import asyncpg
import logging
import sys
import os

# === Импорты проекта ===
from config import API_TOKEN, CHANNEL_ID
from db import init_db
from models import save_message_to_db
from api import app  # FastAPI приложение

# === Логирование ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === Инициализация бота ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# === Обработчик сообщений из канала ===
@dp.channel_post(F.chat.id == CHANNEL_ID)
async def log_channel_message(message: Message):
    logger.info(f"📩 Получено сообщение из канала {CHANNEL_ID} (ID: {message.message_id})")

    # Получаем текст сообщения
    content = message.text or message.caption or "[Медиа или другой тип контента]"

    # Определяем тип медиа и получаем file_id
    media_type = None
    file_id = None
    file_unique_id = None

    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
        file_unique_id = message.photo[-1].file_unique_id
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
        file_unique_id = message.document.file_unique_id
    elif message.audio:
        media_type = "audio"
        file_id = message.audio.file_id
        file_unique_id = message.audio.file_unique_id
    elif message.voice:
        media_type = "voice"
        file_id = message.voice.file_id
        file_unique_id = message.voice.file_unique_id
    elif message.animation:
        media_type = "animation"
        file_id = message.animation.file_id
        file_unique_id = message.animation.file_unique_id

    # Сохраняем сообщение в БД
    await save_message_to_db(
        dp.pool,
        message_id=message.message_id,
        text=content,
        media_type=media_type,
        file_id=file_id,
        file_unique_id=file_unique_id
    )


# === Функция запуска бота ===
async def run_bot():
    logger.info("🤖 Бот запускается...")
    dp.pool = await asyncpg.create_pool(**config.DB_CONFIG)
    await init_db(dp.pool)
    me = await bot.get_me()
    logger.info(f"✅ Бот @{me.username} запущен")
    await dp.start_polling(bot, allowed_updates=["message", "channel_post"])


# === Запуск FastAPI и бота в одном цикле ===
async def main():
    # Подключаемся к БД
    dp.pool = await asyncpg.create_pool(**config.DB_CONFIG)
    await init_db(dp.pool)

    # Проверяем авторизацию бота
    me = await bot.get_me()
    logger.info(f"🤖 Бот успешно авторизован как @{me.username}")

    # Запускаем FastAPI сервер
    api_server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000))

    # Запускаем оба сервера параллельно
    await asyncio.gather(
        api_server.serve(),
        run_bot()
    )

# === Точка входа ===
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import config  # Добавляем импорт здесь, чтобы пути были правильные
    asyncio.run(main())