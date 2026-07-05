from contextlib import asynccontextmanager

import asyncpg
import redis
import redis.asyncio as aioredis
from fastapi import FastAPI, Depends

import app.database as db_module
from app.database import init_db_pool, init_redis_pool, close_pools, get_db, get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_pool()
    await init_redis_pool()

    async with db_module.db_pool.acquire() as conn:
        await conn.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, balance INT);")
        await conn.execute("CREATE TABLE IF NOT EXISTS outbox (id SERIAL PRIMARY KEY, user_id INT, new_balance INT);")
        await conn.execute("INSERT INTO users (id, balance) SELECT generate_series(1, 1000), 0 ON CONFLICT DO NOTHING;")

    yield None
    await close_pools()


app = FastAPI(lifespan=lifespan)


@app.post("/balance/dual-write")
async def dual_write(
        user_id: int,
        amount: int,
        db: asyncpg.Connection = Depends(get_db),
        cache: aioredis.Redis = Depends(get_redis)
):
    async with db.transaction():
        new_balance = await db.fetchval(
            "UPDATE users SET balance = balance + $1 WHERE id = $2 RETURNING balance",
            amount, user_id
        )

    try:
        await cache.set(f"user:{user_id}:balance", new_balance, ex=600)
    except redis.RedisError as e:
        print(f"Ошибка двойной записи в Redis: {e.__class__.__name__}")
        return {"status": "ok_with_redis_error"}

    return {"status": "ok"}


@app.post("/balance/tx-dual-write")
async def tx_dual_write(
        user_id: int, amount: int,
        db: asyncpg.Connection = Depends(get_db),
        cache: aioredis.Redis = Depends(get_redis)
):
    tr = db.transaction()
    await tr.start()
    try:
        new_balance = await db.fetchval(
            "UPDATE users SET balance = balance + $1 WHERE id = $2 RETURNING balance",
            amount, user_id
        )
        await cache.set(f"user:{user_id}:balance", new_balance, ex=600)
        await tr.commit()
    except redis.RedisError as e:
        await tr.rollback()
        return {"status": "error", "detail": "Транзакция отменена из-за сбоя Redis"}

    return {"status": "ok"}


@app.post("/balance/outbox-write")
async def outbox_write(
        user_id: int, amount: int,
        db: asyncpg.Connection = Depends(get_db)
):
    async with db.transaction():
        new_balance = await db.fetchval(
            "UPDATE users SET balance = balance + $1 WHERE id = $2 RETURNING balance",
            amount, user_id
        )
        await db.execute(
            "INSERT INTO outbox (user_id, new_balance) VALUES ($1, $2)",
            user_id, new_balance
        )
    return {"status": "ok"}


@app.post("/balance/cdc-write")
async def cdc_write(
        user_id: int, amount: int,
        db: asyncpg.Connection = Depends(get_db)
):
    async with db.transaction():
        await db.execute(
            "UPDATE users SET balance = balance + $1 WHERE id = $2",
            amount, user_id
        )
    return {"status": "ok"}


@app.post("/system/reset")
async def reset_system(
        db: asyncpg.Connection = Depends(get_db),
        cache: aioredis.Redis = Depends(get_redis)
):
    await db.execute("TRUNCATE TABLE users, outbox RESTART IDENTITY;")
    await db.execute("INSERT INTO users (id, balance) SELECT generate_series(1, 1000), 0 ON CONFLICT DO NOTHING;")

    await cache.flushdb()