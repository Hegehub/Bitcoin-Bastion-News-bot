import aiohttp
from typing import Optional, Dict, Any, List
from config import CRYPTORANK_API_KEY, CRYPTORANK_BASE_URL
import logging
from redis_cache import get_cache, set_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CryptoRankClient:
    def __init__(self):
        self.base_url = CRYPTORANK_BASE_URL
        self.api_key = CRYPTORANK_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        headers = {"X-Api-Key": self.api_key}
        try:
            session = await self._get_session()
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"CryptoRank API error {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            logger.error(f"CryptoRank request exception: {e}")
            return None

    async def get_global_metrics(self) -> Optional[Dict[str, Any]]:
        cache_key = "cryptorank_global"
        cached = await get_cache(cache_key)
        if cached:
            return cached
        data = await self._make_request("/global")
        if data and "data" in data:
            await set_cache(cache_key, data["data"], ttl=300)
            return data["data"]
        return None

    async def get_currency_id(self, symbol: str) -> Optional[int]:
        cache_key = f"cryptorank_map_{symbol.upper()}"
        cached = await get_cache(cache_key)
        if cached:
            return cached
        data = await self._make_request("/currencies/map", params={"limit": 500})
        if data and "data" in data:
            for item in data["data"]:
                if item.get("symbol", "").upper() == symbol.upper():
                    await set_cache(cache_key, item["id"], ttl=86400)
                    return item["id"]
        return None

    async def get_sparkline(self, currency_id: int, from_time: datetime, to_time: datetime, interval: str = "5m") -> Optional[List[Dict]]:
        params = {
            "from": from_time.isoformat() + "Z",
            "to": to_time.isoformat() + "Z",
            "interval": interval,
            "limit": 500
        }
        cache_key = f"sparkline:{currency_id}:{from_time.timestamp()}:{to_time.timestamp()}:{interval}"
        cached = await get_cache(cache_key)
        if cached:
            return cached
        data = await self._make_request(f"/currencies/{currency_id}/sparkline", params)
        if data and "data" in data and "values" in data["data"]:
            points = data["data"]["values"]
            await set_cache(cache_key, points, ttl=600)
            return points
        return None

    async def get_price_at_time(self, currency_id: int, timestamp: datetime) -> Optional[float]:
        from_ts = timestamp - timedelta(hours=1)
        to_ts = timestamp + timedelta(hours=1)
        points = await self.get_sparkline(currency_id, from_ts, to_ts, "5m")
        if not points:
            return None
        target_ms = int(timestamp.timestamp() * 1000)
        closest = min(points, key=lambda p: abs(p["timestamp"] - target_ms))
        return float(closest["price"])

    async def get_price_change_percent(self, currency_id: int, from_time: datetime, to_time: datetime) -> Optional[float]:
        price_from = await self.get_price_at_time(currency_id, from_time)
        price_to = await self.get_price_at_time(currency_id, to_time)
        if price_from and price_to and price_from > 0:
            return round(((price_to - price_from) / price_from) * 100, 2)
        return None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

cryptorank = CryptoRankClient()
