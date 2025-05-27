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
            media_type TEXT,  -- Изменено на TEXT для хранения JSON
            media_url TEXT,   -- Изменено на TEXT для хранения JSON
            media_group_id VARCHAR(100),  -- Добавлено поле для группировки
            timestamp TIMESTAMP DEFAULT NOW()
        );
        ''')
