# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from config import DB_CONFIG, API_TOKEN
import logging
from aiogram import Bot

app = FastAPI()
logger = logging.getLogger(__name__)

# Инициализация бота для доступа к файлам
bot = Bot(token=API_TOKEN)

# === CORS Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Подключение к БД ===
@app.on_event("startup")
async def startup():
    app.state.pool = await asyncpg.create_pool(**DB_CONFIG)
    logger.info("🌐 API: Успешно подключились к PostgreSQL")


# === Маршрут для получения всех сообщений ===
@app.get("/messages")
async def get_messages():
    pool = app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT message_id, text, media_type, file_id, file_unique_id, timestamp 
            FROM channel_messages
            ORDER BY timestamp DESC
        ''')
        return [
            {
                "id": r['message_id'],
                "text": r['text'],
                "media_type": r['media_type'],
                "file_id": r['file_id'],
                "file_unique_id": r['file_unique_id'],
                "timestamp": r['timestamp']
            }
            for r in rows
        ]


# === Маршрут для получения URL файла по его file_id ===
@app.get("/file/{file_id}")
async def get_file_url(file_id: str):
    try:
        file_info = await bot.get_file(file_id)
        file_path = file_info.file_path
        file_url = f"https://api.telegram.org/file/bot {API_TOKEN}/{file_path}"
        return {"file_url": file_url}
    except Exception as e:
        logger.error(f"Ошибка при получении файла: {e}")
        raise HTTPException(status_code=404, detail="Файл не найден")