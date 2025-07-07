
import aioredis
from aioredis import Redis
import os
from fastapi import Depends, FastAPI
from fastapi_limiter import FastAPILimiter

app = FastAPI()
MAX_ATTEMPTS = 5
RATE_LIMIT_DURATION=60


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/")

async def get_redis() -> Redis:
    return await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

async def rate_limiter(redis: Redis, key: str, limit: int, duration: int) -> bool:
    current = await redis.get(key)
    if current is None:
        await redis.set(key, 1, ex=duration)
    else:
        if int(current) >= limit:
            return False
        await redis.incr(key)
    return True

@app.on_event("startup")
async def startup():
    redis = await aioredis.create_redis_pool("redis://localhost:6379")  # Ensure this points to your Redis instance
    await FastAPILimiter.init(redis)

@app.on_event("shutdown")
async def shutdown():
    await FastAPILimiter.close()