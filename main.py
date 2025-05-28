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
import aiofiles
from pathlib import Path
from collections import defaultdict

# === Импорты проекта ===
from config import API_TOKEN, CHANNEL_ID
from db import init_db
from models import save_message_to_db, save_media_group_to_db
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

# === Константы для медиа файлов ===
MEDIA_ROOT = Path("/var/www/uploads")
IMAGE_DIR = MEDIA_ROOT / "img"
VIDEO_DIR = MEDIA_ROOT / "video"
AUDIO_DIR = MEDIA_ROOT / "audio"
DOCUMENT_DIR = MEDIA_ROOT / "documents"

# Создаем директории, если они не существуют
for directory in [MEDIA_ROOT, IMAGE_DIR, VIDEO_DIR, AUDIO_DIR, DOCUMENT_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# === Хранилище для группировки медиа ===
media_groups = defaultdict(list)
media_group_timers = {}

# === Функция для скачивания и сохранения медиа файлов ===
async def download_and_save_media(file_id, media_type, message_id):
    try:
        # Определяем директорию и расширение файла в зависимости от типа медиа
        if media_type == "photo":
            directory = IMAGE_DIR
            extension = "jpg"
        elif media_type == "video":
            directory = VIDEO_DIR
            extension = "mp4"
        elif media_type == "audio":
            directory = AUDIO_DIR
            extension = "mp3"
        elif media_type == "voice":
            directory = AUDIO_DIR
            extension = "mp3"
        elif media_type == "document":
            directory = DOCUMENT_DIR
            extension = "file"  # Будет заменено на реальное расширение
        elif media_type == "animation":
            directory = VIDEO_DIR
            extension = "mp4"
        else:
            return None


        # Формируем имя файла, используя message_id вместо file_unique_id
        filename = f"{message_id}_{media_type}.{extension}"
        filepath = directory / filename
        
        # Скачиваем файл
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        
        if file_info.file_size and file_info.file_size > 20 * 1024 * 1024:
                logger.warning(f"Файл слишком большой ({file_info.file_size} bytes) для скачивания через Bot API: {file_id}")
                return None

        # Если это документ, можем получить оригинальное расширение
        if media_type == "document" and "." in file_path:
            extension = file_path.split(".")[-1]
            filename = f"{message_id}_{media_type}.{extension}"
            filepath = directory / filename
        
        # Скачиваем файл
        file_content = await bot.download_file(file_path)
        
        # Сохраняем файл
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(file_content.read())
        
        # Формируем URL для доступа к файлу
        relative_path = f"uploads/{directory.name}/{filename}"
        url = f"http://anotsenimzhizn.ru/{relative_path}"
        
        logger.info(f"Сохранен файл: {filepath}, URL: {url}")
        return url
    
    except Exception as e:
            logger.error(f"Ошибка при скачивании файла {file_id}: {e}")
            # Возвращаем None вместо краша бота
            return None

# === Функция для обработки группы медиа ===
async def process_media_group(media_group_id):
    if media_group_id not in media_groups:
        return
    
    messages = media_groups[media_group_id]
    if not messages:
        return
    
    # Берем первое сообщение как основное
    main_message = messages[0]
    
    # Собираем все медиа URLs
    media_urls = []
    media_types = []
    
    for msg_data in messages:
        if msg_data['media_url']:
            media_urls.append(msg_data['media_url'])
            media_types.append(msg_data['media_type'])
    
    # Сохраняем как одно сообщение с несколькими медиа
    await save_media_group_to_db(
        dp.pool,
        message_id=main_message['message_id'],
        text=main_message['text'],
        media_types=media_types,
        media_urls=media_urls,
        media_group_id=media_group_id
    )
    
    # Очищаем группу
    del media_groups[media_group_id]
    if media_group_id in media_group_timers:
        media_group_timers[media_group_id].cancel()
        del media_group_timers[media_group_id]
    
    logger.info(f"Обработана группа медиа {media_group_id} с {len(messages)} элементами")

# === Обработчик сообщений из канала ===
@dp.channel_post(F.chat.id == CHANNEL_ID)
async def log_channel_message(message: Message):
    logger.info(f"📩 Получено сообщение из канала {CHANNEL_ID} (ID: {message.message_id})")

    # Получаем текст сообщения
    content = message.text or message.caption or ""

    # Определяем тип медиа и получаем file_id
    media_type = None
    file_id = None
    media_url = None

    if message.photo:
        media_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        file_id = message.video.file_id
    elif message.document:
        media_type = "document"
        file_id = message.document.file_id
    elif message.audio:
        media_type = "audio"
        file_id = message.audio.file_id
    elif message.voice:
        media_type = "voice"
        file_id = message.voice.file_id
    elif message.animation:
        media_type = "animation"
        file_id = message.animation.file_id

    # Если есть медиа, скачиваем и сохраняем его
    if media_type and file_id:
        media_url = await download_and_save_media(file_id, media_type, message.message_id)

    # Проверяем, является ли сообщение частью группы медиа
    if message.media_group_id:
        # Добавляем в группу
        media_groups[message.media_group_id].append({
            'message_id': message.message_id,
            'text': content,
            'media_type': media_type,
            'media_url': media_url
        })
        
        # Отменяем предыдущий таймер если есть
        if message.media_group_id in media_group_timers:
            media_group_timers[message.media_group_id].cancel()
        
        # Устанавливаем таймер на обработку группы (ждем 2 секунды)
        media_group_timers[message.media_group_id] = asyncio.create_task(
            asyncio.sleep(2)
        )
        
        try:
            await media_group_timers[message.media_group_id]
            await process_media_group(message.media_group_id)
        except asyncio.CancelledError:
            pass
    else:
        # Обычное сообщение, сохраняем как есть
        await save_message_to_db(
            dp.pool,
            message_id=message.message_id,
            text=content,
            media_type=media_type,
            media_url=media_url
        )

# === Функция запуска бота ===
async def run_bot():
    logger.info("🤖 Бот запускается...")

    try:
        await bot.delete_webhook()
    except Exception as e:
        logger.warning(f"Ошибка при удалении вебхука: {e}")

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
