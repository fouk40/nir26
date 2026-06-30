from typing import AsyncGenerator, Optional

import asyncpg
import redis.asyncio as aioredis

db_pool: Optional[asyncpg.Pool] = None
redis_pool: Optional[aioredis.Redis] = None


async def init_db_pool() -> None:
    global db_pool
    db_pool = await asyncpg.create_pool(
        user="user",
        password="password",
        database="database",
        host="localhost",
        port=5432,
        min_size=10,
        max_size=50,
        command_timeout=2.0
    )


async def init_redis_pool() -> None:
    global redis_pool
    redis_pool = aioredis.from_url(
        f"redis://localhost:6379",
        decode_responses=True,
        max_connections=50,
        socket_timeout = 1.0,
        socket_connect_timeout = 1.0
    )


async def close_pools() -> None:
    if db_pool:
        await db_pool.close()
    if redis_pool:
        await redis_pool.aclose()


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    if db_pool is None:
        raise RuntimeError("Пул соединений PostgreSQL не инициализирован")

    async with db_pool.acquire() as connection:
        yield connection


async def get_redis() -> aioredis.Redis:
    if redis_pool is None:
        raise RuntimeError("Пул соединений Redis не инициализирован")

    return redis_pool