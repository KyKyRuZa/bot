# Assuming this is part of your db.py file
async def init_db(pool):
    """
    Инициализирует базу данных, создавая необходимые таблицы
    """
    async with pool.acquire() as conn:
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            message_id BIGINT NOT NULL,
            text TEXT,
            media_type VARCHAR(50),
            media_url TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        );
        ''')
