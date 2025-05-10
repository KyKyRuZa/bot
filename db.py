import asyncpg
from config import DB_CONFIG
import logging

logger = logging.getLogger(__name__)

async def create_db_pool():
    pool = await asyncpg.create_pool(**DB_CONFIG)
    logger.info("✅ Успешно подключились к PostgreSQL")
    return pool


async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS channel_messages (
                id SERIAL PRIMARY KEY,
                message_id INTEGER NOT NULL UNIQUE,
                text TEXT,
                media_type TEXT,
                file_id TEXT,
                file_unique_id TEXT,
                timestamp TIMESTAMP NOT NULL DEFAULT NOW()
            )
        ''')
        logger.info("✅ Таблица channel_messages готова")