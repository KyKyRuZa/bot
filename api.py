from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncpg
from typing import List
from pydantic import BaseModel
import config
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Specifically allow your React app's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Mount the media directory to serve static files
app.mount("/media", StaticFiles(directory=Path("media")), name="media")
# Database connection pool
pool = None

# Initialize the database pool
@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(**config.DB_CONFIG)

# Close the database pool
@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()

# Define a model for message responses
class Message(BaseModel):
    id: int
    message_id: int
    text: str = None
    media_type: str = None
    media_url: str = None
    timestamp: datetime  # Changed from str to datetime

    class Config:
        # This tells Pydantic to use this model for arbitrary class instances
        # which is needed for datetime objects
        orm_mode = True

@app.get("/messages", response_model=List[Message])
async def get_messages():
    global pool
    if not pool:
        pool = await asyncpg.create_pool(**config.DB_CONFIG)
        
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT id, message_id, text, media_type, media_url, timestamp
            FROM messages
            ORDER BY timestamp DESC
        ''')
        
        # Convert rows to a list of dictionaries with proper timestamp handling
        messages = []
        for row in rows:
            message = {
                "id": row["id"],
                "message_id": row["message_id"],
                "text": row["text"],
                "media_type": row["media_type"],
                "media_url": row["media_url"],
                "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else str(row["timestamp"])
            }
            messages.append(message)
            
        return messages