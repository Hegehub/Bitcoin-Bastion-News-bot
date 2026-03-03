import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from services.api_client import api_client
import logging
from config import TRIGGER_PRICE_CHANGE_PERCENT, TRIGGER_TIMEFRAME_MINUTES

logger = logging.getLogger(__name__)

class TriggerDetector:
    def __init__(self):
        self.trigger_change = TRIGGER_PRICE_CHANGE_PERCENT
        self.timeframe = TRIGGER_TIMEFRAME_MINUTES

    async def check_if_triggered(self, news_article: Dict) -> Optional[Dict]:
        """
        Проверяет, вызвала ли новость движение цены.
        Возвращает обогащенную новость или None.
        """
        tickers = news_article.get('tickers', ['BTC'])
        if not tickers:
            tickers = ['BTC']

        asset = tickers[0]
        news_time = datetime.fromisoformat(news_article['published_at'].replace('Z', '+00:00'))

        # Получаем тональность через API
        sentiment_data = await api_client.get_ai_sentiment(asset=asset, text=news_article['title'])
        if not sentiment_data:
            return None

        # Заглушка: здесь должен быть запрос к историческим ценам.
        # В реальности используйте CoinGecko или другой API для получения цены на момент новости и через N минут.
        # Пока имитируем случайное изменение цены (для демонстрации).
        price_change = await self._fetch_price_change(asset, news_time)

        if price_change is not None and abs(price_change) >= self.trigger_change:
            sentiment_label = sentiment_data.get('label', 'neutral')
            # Проверяем совпадение направления
            if (price_change > 0 and sentiment_label == 'positive') or \
               (price_change < 0 and sentiment_label == 'negative'):
                news_article['triggered'] = True
                news_article['price_change'] = price_change
                news_article['sentiment'] = sentiment_data
                return news_article
        return None

    async def _fetch_price_change(self, asset: str, since_time: datetime) -> Optional[float]:
        """
        Заглушка. В реальном проекте здесь запрос к историческому API цен.
        Возвращает изменение цены в процентах за self.timeframe минут.
        """
        # Эмуляция: случайное значение от -5% до +5%
        import random
        return round(random.uniform(-5.0, 5.0), 2)

# Глобальный экземпляр детектора
trigger_detector = TriggerDetector()
