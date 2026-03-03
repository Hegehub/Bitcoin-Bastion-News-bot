import aiohttp
import asyncio
import logging
from typing import Optional, Dict, List, Any
from aiohttp_sse_client import EventSource

logger = logging.getLogger(__name__)

class BibabotAPIClient:
    """
    Асинхронный клиент для работы с Free Crypto News API (Bitcoin-Bastion).
    Поддерживает REST эндпоинты и SSE-стриминг новостей.
    """

    def __init__(self, base_url: str = "https://cryptocurrency.cv"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Создаёт или возвращает существующую сессию aiohttp."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Закрывает сессию клиента."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _get(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """
        Базовый GET-запрос к API.
        Возвращает декодированный JSON или None при ошибке.
        """
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

    # --- Новости и поиск ---

    async def get_latest_news(self, limit: int = 10, ticker: str = "BTC") -> List[Dict]:
        """
        Получает последние новости.
        GET /api/news?limit=<limit>&ticker=<ticker>
        """
        data = await self._get("api/news", params={"limit": limit, "ticker": ticker})
        return data.get("articles", []) if data else []

    async def search_news(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Полнотекстовый поиск по новостям.
        GET /api/search?q=<query>&limit=<limit>
        """
        data = await self._get("api/search", params={"q": query, "limit": limit})
        return data.get("articles", []) if data else []

    # --- AI анализ ---

    async def get_sentiment(self, url: str) -> Optional[Dict]:
        """
        Анализ тональности новости.
        GET /api/ai/sentiment?url=<url>
        """
        return await self._get("api/ai/sentiment", params={"url": url})

    async def summarize(self, url: str, style: str = "bullet") -> Optional[str]:
        """
        Суммаризация новости.
        GET /api/summarize?url=<url>&style=<style>
        style может быть "bullet" или "paragraph"
        """
        data = await self._get("api/summarize", params={"url": url, "style": style})
        return data.get("summary") if data else None

    async def factcheck(self, url: str) -> Optional[Dict]:
        """
        Проверка фактов в новости.
        GET /api/factcheck?url=<url>
        """
        return await self._get("api/factcheck", params={"url": url})

    # --- Рыночные метрики ---

    async def get_fear_greed(self) -> Optional[Dict]:
        """
        Индекс страха и жадности.
        GET /api/market/fear-greed
        """
        return await self._get("api/market/fear-greed")

    async def get_btc_dominance(self) -> Optional[float]:
        """
        Доминация Bitcoin (в процентах).
        GET /api/dominance
        Предполагаемый формат ответа: {"btc_dominance": 42.5}
        """
        data = await self._get("api/dominance")
        if data and "btc_dominance" in data:
            return data["btc_dominance"]
        return None

    async def get_liquidations(self) -> Optional[List[Dict]]:
        """
        Последние ликвидации.
        GET /api/liquidations
        """
        data = await self._get("api/liquidations")
        return data.get("liquidations") if data else None

    async def get_whales(self) -> Optional[List[Dict]]:
        """
        Китовые транзакции.
        GET /api/whales
        """
        data = await self._get("api/whales")
        return data.get("whales") if data else None

    async def get_funding_rates(self) -> Optional[Dict]:
        """
        Ставки финансирования.
        GET /api/funding
        """
        return await self._get("api/funding")

    # --- Дополнительные источники данных (не из основного API) ---

    async def get_btc_price_coindesk(self) -> Optional[float]:
        """
        Получает текущую цену Bitcoin от CoinDesk (резервный источник).
        Используется, если цена недоступна из основного API.
        GET https://api.coindesk.com/v1/bpi/currentprice.json
        """
        session = await self._get_session()
        url = "https://api.coindesk.com/v1/bpi/currentprice.json"
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data["bpi"]["USD"]["rate_float"])
                else:
                    logger.error(f"CoinDesk error {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"CoinDesk request failed: {e}")
            return None

    # --- Исторический архив ---

    async def get_archive(self, date: str = None, ticker: str = None, limit: int = 100) -> List[Dict]:
        """
        Доступ к историческому архиву новостей.
        GET /api/archive?date=<date>&ticker=<ticker>&limit=<limit>
        """
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
        callback должен быть асинхронной функцией, принимающей один аргумент (данные события).
        При обрыве соединения метод завершается, и внешний код должен перезапустить его.
        """
        session = await self._get_session()
        url = f"{self.base_url}/api/stream"
        async with session.get(url, headers={"Accept": "text/event-stream"}) as resp:
            async for event in EventSource(resp.content):
                if event.event == "news" and event.data:
                    try:
                        data = event.json()
                        # Если callback асинхронный, вызываем через await
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
                    except Exception as e:
                        logger.error(f"Error processing stream event: {e}")
