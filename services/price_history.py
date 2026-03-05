import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from config import COINGECKO_API_KEY
from redis_cache import get_cache, set_cache

logger = logging.getLogger(__name__)

class PriceHistoryService:
    """Сервис для получения исторических цен с CoinGecko (не Binance)"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session: Optional[aiohttp.ClientSession] = None
        self.api_key = COINGECKO_API_KEY
        
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Выполняет запрос к CoinGecko API"""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        if self.api_key:
            headers["x-cg-pro-api-key"] = self.api_key
        
        # Добавляем параметры по умолчанию для бесплатного плана
        if not params:
            params = {}
        
        try:
            session = await self._get_session()
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("Rate limit exceeded for CoinGecko")
                    return None
                else:
                    logger.error(f"CoinGecko request failed: {url} - {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception during CoinGecko request: {e}")
            return None
    
    async def get_price_at_time(self, coin_id: str, timestamp: datetime) -> Optional[float]:
        """
        Получает цену монеты на конкретный момент времени
        Использует исторические данные CoinGecko
        """
        # Пробуем получить из кэша
        cache_key = f"price:{coin_id}:{timestamp.strftime('%Y%m%d%H')}"
        cached = await get_cache(cache_key)
        if cached:
            return cached
        
        # Конвертируем timestamp в Unix
        unix_time = int(timestamp.timestamp())
        
        # Получаем цену на этот момент
        params = {
            'date': timestamp.strftime('%d-%m-%Y'),
            'localization': 'false'
        }
        
        data = await self._make_request(f"/coins/{coin_id}/history", params=params)
        if data and 'market_data' in data:
            price = data['market_data']['current_price']['usd']
            # Кэшируем на 24 часа
            await set_cache(cache_key, price, ttl=86400)
            return price
        
        return None
    
    async def get_price_change_percent(self, coin_id: str, from_time: datetime, to_time: datetime) -> Optional[float]:
        """
        Вычисляет процент изменения цены между двумя моментами времени
        """
        price_from = await self.get_price_at_time(coin_id, from_time)
        price_to = await self.get_price_at_time(coin_id, to_time)
        
        if price_from and price_to and price_from > 0:
            change = ((price_to - price_from) / price_from) * 100
            return round(change, 2)
        
        return None
    
    async def get_current_price(self, coin_id: str = 'bitcoin') -> Optional[float]:
        """Получает текущую цену монеты"""
        cache_key = f"current_price:{coin_id}"
        cached = await get_cache(cache_key)
        if cached:
            return cached
        
        data = await self._make_request(f"/simple/price", params={
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_last_updated_at': 'true'
        })
        
        if data and coin_id in data:
            price = data[coin_id]['usd']
            await set_cache(cache_key, price, ttl=60)  # Кэш на 1 минуту
            return price
        
        return None
    
    async def get_historical_range(self, coin_id: str, days: int = 7) -> Optional[List[Dict]]:
        """Получает исторические цены за последние N дней"""
        cache_key = f"history:{coin_id}:{days}"
        cached = await get_cache(cache_key)
        if cached:
            return cached
        
        data = await self._make_request(f"/coins/{coin_id}/market_chart", params={
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'
        })
        
        if data and 'prices' in data:
            # Преобразуем в удобный формат
            prices = [
                {'timestamp': item[0], 'price': item[1]} 
                for item in data['prices']
            ]
            await set_cache(cache_key, prices, ttl=3600)  # Кэш на 1 час
            return prices
        
        return None
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

# Глобальный экземпляр
price_history = PriceHistoryService()