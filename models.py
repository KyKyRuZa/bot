# models.py
import logging
import asyncpg
logger = logging.getLogger(__name__)


async def save_message_to_db(pool, message_id: int, text: str, media_type=None, file_id=None, file_unique_id=None):
    """Сохраняет сообщение в БД"""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO channel_messages (message_id, text, media_type, file_id, file_unique_id)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (message_id) DO NOTHING
                """,
                message_id, text, media_type, file_id, file_unique_id
            )
            logger.info(f"💾 Сообщение ID {message_id} сохранено в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении сообщения в БД: {e}")