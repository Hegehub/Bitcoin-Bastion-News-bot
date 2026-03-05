import aiohttp
import asyncio
from typing import Optional, Dict, Any, List, AsyncGenerator
from config import API_BASE_URL
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class CryptoNewsAPIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Универсальный метод с повторными попытками при ошибках."""
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Запрос к API: {url}, params={params}")
        
        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Успешный ответ от {endpoint}, размер: {len(str(data))} байт")
                    return data
                else:
                    logger.error(f"API request failed: {url} - Статус: {response.status}")
                    logger.error(f"Ответ: {await response.text()}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при запросе к {url}")
            raise  # для повторной попытки
        except aiohttp.ClientError as e:
            logger.error(f"Клиентская ошибка при запросе к {url}: {e}")
            raise  # для повторной попытки
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе к {url}: {e}")
            return None

    async def get_latest_news(self, limit: int = 20, language: str = 'en') -> Optional[List[Dict]]:
        """Получение последних новостей с проверкой структуры ответа."""
        data = await self._make_request("/api/news", params={"limit": limit, "language": language})
        
        # Проверяем структуру ответа (API может возвращать в разных форматах)
        if data:
            if isinstance(data, list):
                logger.info(f"Получено {len(data)} новостей (формат список)")
                return data
            elif isinstance(data, dict) and 'articles' in data:
                logger.info(f"Получено {len(data['articles'])} новостей (формат {{articles}})")
                return data['articles']
            elif isinstance(data, dict) and 'data' in data:
                logger.info(f"Получено {len(data['data'])} новостей (формат {{data}})")
                return data['data']
            else:
                logger.warning(f"Неизвестный формат ответа: {type(data)}")
                return None
        return None

    async def get_ai_sentiment(self, asset: str = "BTC", text: Optional[str] = None) -> Optional[Dict]:
        """Получение тональности с проверкой."""
        params = {"asset": asset}
        if text:
            params["text"] = text
        data = await self._make_request("/api/ai/sentiment", params=params)
        
        if data:
            logger.info(f"Получена тональность для {asset}: {data.get('label', 'unknown')}")
            return data
        return None

    async def get_market_metrics(self) -> Dict[str, Any]:
        """Собрать все рыночные метрики с обработкой частичных ошибок."""
        result = {
            "btc_price": None,
            "fear_greed": None,
            "fear_greed_class": None,
            "btc_dominance": None,
            "eth_dominance": None,
        }
        
        # Пытаемся получить каждый показатель независимо
        try:
            fg = await self._make_request("/api/market/fear-greed")
            if fg:
                result["fear_greed"] = fg.get("value")
                result["fear_greed_class"] = fg.get("classification")
                logger.info(f"Fear & Greed: {result['fear_greed']}")
        except Exception as e:
            logger.error(f"Ошибка получения Fear & Greed: {e}")

        try:
            btc_data = await self._make_request("/api/coin/bitcoin")
            if btc_data and 'market_data' in btc_data:
                result["btc_price"] = btc_data['market_data']['current_price']['usd']
                logger.info(f"Цена BTC: ${result['btc_price']}")
        except Exception as e:
            logger.error(f"Ошибка получения цены BTC: {e}")

        try:
            dominance = await self._make_request("/api/dominance")
            if dominance:
                result["btc_dominance"] = dominance.get("btc_dominance")
                result["eth_dominance"] = dominance.get("eth_dominance")
                logger.info(f"Доминация BTC: {result['btc_dominance']}%")
        except Exception as e:
            logger.error(f"Ошибка получения доминации: {e}")

        return result

    async def get_whale_transactions(self, limit: int = 5) -> Optional[List[Dict]]:
        """Китовые транзакции с проверкой формата."""
        data = await self._make_request("/api/whales", params={"limit": limit})
        
        if data:
            if isinstance(data, list):
                logger.info(f"Получено {len(data)} китовых транзакций")
                return data
            elif isinstance(data, dict) and 'transactions' in data:
                logger.info(f"Получено {len(data['transactions'])} китовых транзакций")
                return data['transactions']
        return None

    async def test_connection(self) -> bool:
        """Тестовая функция для проверки доступности API."""
        try:
            # Пробуем получить хотя бы одну новость
            news = await self.get_latest_news(limit=1)
            if news:
                logger.info("✅ API доступен, данные получены")
                logger.info(f"Пример новости: {news[0]['title'] if news else 'нет'}")
                return True
            else:
                logger.error("❌ API вернул пустой ответ")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к API: {e}")
            return False

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

api_client = CryptoNewsAPIClient()