import aioredis
import json
from config import REDIS_URL

redis = aioredis.from_url(REDIS_URL, decode_responses=True)

async def get_cached_price():
    data = await redis.get("btc_price")
    return float(data) if data else None

async def set_cached_price(price: float, ttl: int = 300):
    await redis.setex("btc_price", ttl, price)

async def get_cached_fear_greed():
    data = await redis.get("fear_greed")
    return json.loads(data) if data else None

async def set_cached_fear_greed(fg: dict, ttl: int = 600):
    await redis.setex("fear_greed", ttl, json.dumps(fg))
