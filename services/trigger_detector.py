from datetime import datetime, timedelta
from typing import Dict, Optional
from services.api_client import api_client
import logging
from config import TRIGGER_PRICE_CHANGE_PERCENT, TRIGGER_TIMEFRAME_MINUTES
import aiohttp

logger = logging.getLogger(__name__)

class TriggerDetector:
    def __init__(self):
        self.trigger_change = TRIGGER_PRICE_CHANGE_PERCENT
        self.timeframe = TRIGGER_TIMEFRAME_MINUTES
        # Используем бесплатный CoinGecko API для исторических цен
        self.coingecko_url = "https://api.coingecko.com/api/v3"

    async def check_if_triggered(self, news_article: Dict) -> Optional[Dict]:
        """Проверяет, вызвала ли новость движение цены, используя реальные данные."""
        tickers = news_article.get('tickers', ['BTC'])
        if not tickers:
            tickers = ['BTC']

        # Берем первый тикер (обычно BTC)
        asset = tickers[0]
        
        try:
            # Парсим время новости
            news_time = datetime.fromisoformat(news_article['published_at'].replace('Z', '+00:00'))
            
            # Получаем тональность через API
            sentiment_data = await api_client.get_ai_sentiment(asset=asset, text=news_article['title'])
            if not sentiment_data:
                logger.warning(f"Не удалось получить тональность для новости: {news_article['title'][:50]}...")
                return None

            # Получаем реальное изменение цены
            price_change = await self._fetch_real_price_change(asset, news_time)
            
            if price_change is None:
                logger.warning(f"Не удалось получить изменение цены для {asset}")
                return None

            logger.info(f"Новость: {news_article['title'][:50]}... Изменение цены: {price_change:.2f}%, порог: {self.trigger_change}%")
            
            if abs(price_change) >= self.trigger_change:
                sentiment_label = sentiment_data.get('label', 'neutral')
                # Проверяем совпадение направления
                if (price_change > 0 and sentiment_label == 'positive') or \
                   (price_change < 0 and sentiment_label == 'negative'):
                    logger.info(f"✅ НОВОСТЬ-ТРИГГЕР! {news_article['title'][:50]}...")
                    news_article['triggered'] = True
                    news_article['price_change'] = price_change
                    news_article['sentiment'] = sentiment_data
                    return news_article
                else:
                    logger.info(f"❌ Направление не совпало: цена {price_change:+.2f}%, тональность {sentiment_label}")
            else:
                logger.info(f"❌ Изменение цены {price_change:.2f}% меньше порога {self.trigger_change}%")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке триггера: {e}")
            
        return None

    async def _fetch_real_price_change(self, asset: str, since_time: datetime) -> Optional[float]:
        """
        Получает реальное изменение цены через CoinGecko API.
        """
        try:
            # Конвертируем тикер в id для CoinGecko
            coin_id = self._ticker_to_coingecko_id(asset)
            
            # Время начала (когда вышла новость)
            start_timestamp = int(since_time.timestamp())
            # Время через N минут после новости
            end_time = since_time + timedelta(minutes=self.timeframe)
            end_timestamp = int(end_time.timestamp())
            
            # Ограничиваем, чтобы не уходить в будущее (если новость свежая)
            now_timestamp = int(datetime.utcnow().timestamp())
            if end_timestamp > now_timestamp:
                end_timestamp = now_timestamp
                logger.info(f"Корректировка end_timestamp: сейчас {now_timestamp}, новости {end_timestamp}")
            
            # Запрос к CoinGecko для получения цены на два момента времени
            async with aiohttp.ClientSession() as session:
                # Получаем цену на момент новости
                url_start = f"{self.coingecko_url}/coins/{coin_id}/market_chart/range"
                params = {
                    'vs_currency': 'usd',
                    'from': start_timestamp,
                    'to': start_timestamp + 60  # +1 минута, чтобы точно получить точку
                }
                
                async with session.get(url_start, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"CoinGecko error: {resp.status}")
                        return None
                    data = await resp.json()
                    prices = data.get('prices', [])
                    if not prices:
                        logger.warning(f"Нет данных о цене для {coin_id} на {since_time}")
                        return None
                    # Берем первую цену (она должна быть ближе всего к времени новости)
                    start_price = prices[0][1]
                
                # Получаем цену через N минут
                url_end = f"{self.coingecko_url}/coins/{coin_id}/market_chart/range"
                params = {
                    'vs_currency': 'usd',
                    'from': end_timestamp - 60,  # чуть раньше
                    'to': end_timestamp
                }
                
                async with session.get(url_end, params=params) as resp:
                    if resp.status != 200:
                        logger.error(f"CoinGecko error: {resp.status}")
                        return None
                    data = await resp.json()
                    prices = data.get('prices', [])
                    if not prices:
                        logger.warning(f"Нет данных о цене для {coin_id} на {end_time}")
                        return None
                    # Берем последнюю цену
                    end_price = prices[-1][1]
                
                # Рассчитываем процент изменения
                if start_price and end_price:
                    change_percent = ((end_price - start_price) / start_price) * 100
                    logger.info(f"Цена {asset}: {start_price:.2f} → {end_price:.2f} (изменение: {change_percent:.2f}%)")
                    return round(change_percent, 2)
                
        except Exception as e:
            logger.error(f"Ошибка при получении цены из CoinGecko: {e}")
            
        return None

    def _ticker_to_coingecko_id(self, ticker: str) -> str:
        """Конвертирует тикер в ID CoinGecko."""
        mapping = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'DOT': 'polkadot',
            'LINK': 'chainlink',
            'MATIC': 'polygon',
            'AVAX': 'avalanche-2',
        }
        return mapping.get(ticker.upper(), 'bitcoin')  # по умолчанию bitcoin

trigger_detector = TriggerDetector()