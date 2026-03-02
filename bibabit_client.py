import aiohttp
import asyncio
import logging
from typing import Optional, Dict, List, Any
from sse_client import EventSource  # используем aiohttp-sse-client

logger = logging.getLogger(__name__)

class BibabotAPIClient:
    def __init__(self, base_url: str = "https://cryptocurrency.cv"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"API error {resp.status} for {url}: {await resp.text()}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {url}")
            return None
        except Exception as e:
            logger.error(f"Request error for {url}: {e}")
            return None

    # --- Новости ---
    async def get_latest_news(self, limit: int = 10, ticker: str = "BTC") -> List[Dict]:
        data = await self._get("api/news", params={"limit": limit, "ticker": ticker})
        return data.get("articles", []) if data else []

    async def search_news(self, query: str, limit: int = 10) -> List[Dict]:
        data = await self._get("api/search", params={"q": query, "limit": limit})
        return data.get("articles", []) if data else []

    # --- AI анализ ---
    async def get_sentiment(self, url: str) -> Optional[Dict]:
        return await self._get("api/ai/sentiment", params={"url": url})

    async def summarize(self, url: str, style: str = "bullet") -> Optional[str]:
        data = await self._get("api/summarize", params={"url": url, "style": style})
        return data.get("summary") if data else None

    async def factcheck(self, url: str) -> Optional[Dict]:
        return await self._get("api/factcheck", params={"url": url})

    # --- Рыночные метрики ---
    async def get_fear_greed(self) -> Optional[Dict]:
        return await self._get("api/market/fear-greed")

    async def get_btc_dominance(self) -> Optional[float]:
        data = await self._get("api/dominance")
        if data and "btc_dominance" in data:
            return data["btc_dominance"]
        return None

    async def get_liquidations(self) -> Optional[List[Dict]]:
        data = await self._get("api/liquidations")
        return data.get("liquidations") if data else None

    async def get_whales(self) -> Optional[List[Dict]]:
        data = await self._get("api/whales")
        return data.get("whales") if data else None

    async def get_funding_rates(self) -> Optional[Dict]:
        return await self._get("api/funding")

    # --- Исторический архив ---
    async def get_archive(self, date: str = None, ticker: str = None, limit: int = 100) -> List[Dict]:
        params = {}
        if date:
            params["date"] = date
        if ticker:
            params["ticker"] = ticker
        if limit:
            params["limit"] = limit
        data = await self._get("api/archive", params=params)
        return data.get("articles", []) if data else []

    # --- Стриминг новостей (SSE) ---
    async def stream_news(self, callback):
        """
        Подключается к /api/stream и вызывает callback для каждого события.
        callback принимает один аргумент — данные события (dict).
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/stream"
        async with session.get(url, headers={"Accept": "text/event-stream"}) as resp:
            async for event in EventSource(resp.content):
                if event.event == "news" and event.data:
                    try:
                        data = event.json()
                        await callback(data)
                    except Exception as e:
                        logger.error(f"Error processing stream event: {e}")
