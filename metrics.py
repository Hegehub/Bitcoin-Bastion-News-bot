import aiohttp
import logging
from redis_cache import get_cached_price, set_cached_price

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self):
        self.session = None

    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()

    async def get_btc_price_coindesk(self):
        session = await self.get_session()
        url = "https://api.coindesk.com/v1/bpi/currentprice.json"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data["bpi"]["USD"]["rate_float"])
        except Exception as e:
            logger.error(f"CoinDesk error: {e}")
        return None

    # Добавьте другие источники при необходимости
