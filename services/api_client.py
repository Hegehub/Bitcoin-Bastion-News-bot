import aiohttp
from typing import Optional, Dict, Any, List, AsyncGenerator
from config import API_BASE_URL
import logging

logger = logging.getLogger(__name__)

class CryptoNewsAPIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {url} - {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception during API request to {url}: {e}")
            return None

    async def get_latest_news(self, limit: int = 20, language: str = 'en') -> Optional[List[Dict]]:
        data = await self._make_request("/api/news", params={"limit": limit, "language": language})
        return data.get("articles") if data else None

    async def get_news_by_ticker(self, ticker: str = "BTC", limit: int = 50) -> Optional[List[Dict]]:
        data = await self._make_request("/api/archive", params={"ticker": ticker, "limit": limit})
        return data.get("articles") if data else None

    async def get_ai_sentiment(self, asset: str = "BTC", text: Optional[str] = None) -> Optional[Dict]:
        params = {"asset": asset}
        if text:
            params["text"] = text
        return await self._make_request("/api/ai/sentiment", params=params)

    async def get_market_metrics(self) -> Dict[str, Any]:
        fg = await self._make_request("/api/market/fear-greed")
        btc_data = await self._make_request("/api/coin/bitcoin")
        dominance = await self._make_request("/api/dominance")
        btc_price = None
        if btc_data and 'market_data' in btc_data:
            btc_price = btc_data['market_data']['current_price']['usd']
        return {
            "btc_price": btc_price,
            "fear_greed": fg.get("value") if fg else None,
            "fear_greed_class": fg.get("classification") if fg else None,
            "btc_dominance": dominance.get("btc_dominance") if dominance else None,
            "eth_dominance": dominance.get("eth_dominance") if dominance else None,
        }

    async def get_historical_archive(self, date: str = None, ticker: str = None,
                                     query: str = None, limit: int = 100) -> Optional[List[Dict]]:
        params = {"limit": limit}
        if date:
            params["date"] = date
        if ticker:
            params["ticker"] = ticker
        if query:
            params["q"] = query
        data = await self._make_request("/api/archive", params=params)
        return data.get("articles") if data else None

    async def get_international_news(self, language: str = 'ko', translate: bool = True,
                                     limit: int = 10) -> Optional[List[Dict]]:
        params = {"language": language, "translate": str(translate).lower(), "limit": limit}
        data = await self._make_request("/api/news/international", params=params)
        return data.get("articles") if data else None

    async def ask_ai(self, question: str) -> Optional[str]:
        data = await self._make_request("/api/ask", params={"q": question})
        return data.get("response") if data else None

    async def fact_check(self, text: str) -> Optional[Dict]:
        return await self._make_request("/api/factcheck", params={"text": text})

    async def summarize_news(self, url: str, style: str = 'bullet') -> Optional[str]:
        data = await self._make_request("/api/summarize", params={"url": url, "style": style})
        return data.get("summary") if data else None

    async def extract_entities(self, text: str) -> Optional[Dict]:
        return await self._make_request("/api/entities", params={"text": text})

    async def get_whale_transactions(self, limit: int = 5) -> Optional[List[Dict]]:
        data = await self._make_request("/api/whales", params={"limit": limit})
        return data.get("transactions") if data else None

    async def get_liquidations(self, limit: int = 5) -> Optional[List[Dict]]:
        data = await self._make_request("/api/liquidations", params={"limit": limit})
        return data.get("liquidations") if data else None

    async def get_funding_rates(self) -> Optional[List[Dict]]:
        data = await self._make_request("/api/funding")
        return data.get("rates") if data else None

    async def get_market_movers(self, type: str = 'gainers', limit: int = 10) -> Optional[List[Dict]]:
        data = await self._make_request(f"/api/movers/{type}", params={"limit": limit})
        return data.get("movers") if data else None

    async def get_coin_details(self, coin_id: str) -> Optional[Dict]:
        return await self._make_request(f"/api/coin/{coin_id}")

    async def get_market_heatmap(self) -> Optional[Dict]:
        return await self._make_request("/api/heatmap")

    async def get_options_data(self) -> Optional[Dict]:
        return await self._make_request("/api/options")

    async def get_orderbook(self, pair: str = 'BTC/USD') -> Optional[Dict]:
        return await self._make_request("/api/orderbook", params={"pair": pair})

    async def stream_news(self) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/api/stream"
        try:
            session = await self._get_session()
            async with session.get(url, headers={'Accept': 'text/event-stream'}) as response:
                async for line in response.content:
                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data:'):
                            yield line[5:].strip()
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            return

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

api_client = CryptoNewsAPIClient()