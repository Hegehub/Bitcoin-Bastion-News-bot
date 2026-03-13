import redis.asyncio as redis
from config import REDIS_URL
import json

redis_client = None

async def init_redis():
    global redis_client
    redis_client = await redis.from_url(REDIS_URL, decode_responses=True)

async def close_redis():
    if redis_client:
        await redis_client.close()

async def set_cache(key: str, value, ttl: int = 300):
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await redis_client.setex(key, ttl, value)

async def get_cache(key: str):
    val = await redis_client.get(key)
    if val:
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return val
    return None

async def delete_cache(key: str):
    await redis_client.delete(key)
