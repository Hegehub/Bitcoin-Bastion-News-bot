from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging
from services.api_client import api_client
from services.price_history import price_history
from config import TRIGGER_PRICE_CHANGE_PERCENT, TRIGGER_TIMEFRAME_MINUTES
from database import async_session, News
from sqlalchemy import select

logger = logging.getLogger(__name__)

class TriggerDetector:
    def __init__(self):
        self.trigger_change = TRIGGER_PRICE_CHANGE_PERCENT
        self.timeframe = TRIGGER_TIMEFRAME_MINUTES

    async def check_if_triggered(self, news_article: Dict) -> Optional[Dict]:
        tickers = news_article.get('tickers', [])
        if not tickers:
            tickers = self._extract_tickers(news_article['title'])
        if not tickers:
            tickers = ['BTC']
        primary_ticker = tickers[0]

        try:
            news_time = datetime.fromisoformat(news_article['published_at'].replace('Z', '+00:00'))
        except (KeyError, TypeError, ValueError):
            news_time = datetime.utcnow() - timedelta(hours=1)
        check_time = news_time + timedelta(minutes=self.timeframe)

        sentiment_data = await api_client.get_ai_sentiment(asset=primary_ticker, text=news_article['title'])
        if not sentiment_data:
            logger.warning(f"Failed to get sentiment for: {news_article['title'][:50]}")
            return None

        price_change = await price_history.get_price_change_percent(primary_ticker, news_time, check_time)
        if price_change is None:
            logger.warning(f"Failed to get price change for {primary_ticker}")
            return None

        if abs(price_change) >= self.trigger_change:
            sentiment_label = sentiment_data.get('label', 'neutral').lower()
            direction_match = (
                (price_change > 0 and sentiment_label == 'positive') or
                (price_change < 0 and sentiment_label == 'negative')
            )
            if direction_match:
                news_article['triggered'] = True
                news_article['price_change'] = price_change
                news_article['sentiment'] = sentiment_data
                logger.info(f"✅ Triggered news: {news_article['title'][:50]}... change: {price_change:+.2f}%")
                return news_article
        return None

    def _extract_tickers(self, text: str) -> List[str]:
        common_tickers = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'LINK', 'MATIC', 'AVAX', 'UNI', 'ATOM', 'LTC', 'BCH', 'ALGO', 'XLM', 'VET', 'FIL', 'TRX', 'FTM', 'NEAR', 'APT', 'ARB', 'OP', 'SUI']
        words = text.upper().split()
        found = []
        for word in words:
            clean = word.strip('.,!?:;()[]{}"\'')
            if clean in common_tickers:
                found.append(clean)
        return found

    async def analyze_historical_news(self, days: int = 7) -> Dict:
        stats = {'total_analyzed': 0, 'triggered': 0, 'by_coin': {}, 'accuracy': 0}
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            result = await session.execute(
                select(News).where(News.published_at >= cutoff)
            )
            news_list = result.scalars().all()
        for news in news_list:
            stats['total_analyzed'] += 1
            if news.triggered:
                stats['triggered'] += 1
                ticker = news.tickers.split(',')[0] if news.tickers else 'BTC'
                stats['by_coin'][ticker] = stats['by_coin'].get(ticker, 0) + 1
        if stats['total_analyzed'] > 0:
            stats['accuracy'] = (stats['triggered'] / stats['total_analyzed']) * 100
        return stats

trigger_detector = TriggerDetector()