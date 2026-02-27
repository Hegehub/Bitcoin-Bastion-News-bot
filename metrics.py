import aiohttp
import logging
from datetime import datetime, timedelta
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

    # CoinDesk API (пример: текущая цена BTC)
    async def get_btc_price_coindesk(self):
        # По документации CoinDesk: https://api.coindesk.com/v1/bpi/currentprice.json
        session = await self.get_session()
        url = "https://api.coindesk.com/v1/bpi/currentprice.json"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = float(data["bpi"]["USD"]["rate_float"])
                    return {"price": price, "source": "coindesk"}
        except Exception as e:
            logger.error(f"CoinDesk error: {e}")
        return None

    # DexScreener: поиск пары BTC (например, на Ethereum)
    async def get_dex_data(self, chain="ethereum", pair="0x...") -> dict:
        # Для примера: возвращаем ликвидность и объем
        session = await self.get_session()
        url = f"https://api.dexscreener.com/latest/dex/search?q=BTC"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Парсим нужные поля
                    pairs = data.get("pairs", [])
                    if pairs:
                        # Берем первую пару с наибольшей ликвидностью
                        best = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0)))
                        return {
                            "liquidity_usd": float(best.get("liquidity", {}).get("usd", 0)),
                            "volume_24h": float(best.get("volume", {}).get("h24", 0)),
                            "price_usd": float(best.get("priceUsd", 0)),
                            "pair": best.get("pairAddress")
                        }
        except Exception as e:
            logger.error(f"DexScreener error: {e}")
        return None

    # Индекс страха и жадности (можно из BiBaBot или альтернативы)
    async def get_fear_greed(self):
        session = await self.get_session()
        # Используем API alternative.me
        url = "https://api.alternative.me/fng/"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["data"][0]
        except Exception as e:
            logger.error(f"Fear & Greed error: {e}")
        return None

    # Доминация BTC (например, из CoinGecko)
    async def get_btc_dominance(self):
        session = await self.get_session()
        url = "https://api.coingecko.com/api/v3/global"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["data"]["market_cap_percentage"]["btc"]
        except Exception as e:
            logger.error(f"CoinGecko error: {e}")
        return None

    # Открытый интерес (можно из CoinGlass через парсинг или API)
    # Пока заглушка
    async def get_open_interest(self):
        # TODO: реализовать через какой-либо API
        return None

    # Универсальный метод для получения всех метрик
    async def get_all_metrics(self):
        btc_price = await self.get_btc_price_coindesk()
        fear_greed = await self.get_fear_greed()
        dominance = await self.get_btc_dominance()
        dex = await self.get_dex_data()
        return {
            "btc_price": btc_price,
            "fear_greed": fear_greed,
            "dominance": dominance,
            "dex": dex
        }
