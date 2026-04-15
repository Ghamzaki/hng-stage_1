import os
import asyncpg

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                gender TEXT NOT NULL,
                gender_probability REAL NOT NULL,
                sample_size INTEGER NOT NULL,
                age INTEGER NOT NULL,
                age_group TEXT NOT NULL,
                country_id TEXT NOT NULL,
                country_probability REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)