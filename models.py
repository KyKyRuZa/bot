# Assuming this is your models.py file
async def save_message_to_db(pool, message_id, text, media_type=None, media_url=None):
    """
    Сохраняет сообщение в базу данных
    """
    query = """
    INSERT INTO messages (message_id, text, media_type, media_url, timestamp)
    VALUES ($1, $2, $3, $4, NOW())
    RETURNING id;
    """
    
    async with pool.acquire() as conn:
        message_db_id = await conn.fetchval(
            query, message_id, text, media_type, media_url
        )
        return message_db_id
