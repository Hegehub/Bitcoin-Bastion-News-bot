import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, update
from database import get_db, News, User
from bibabot_client import BibabotAPIClient
from metrics import MetricsCollector
from redis_cache import get_cached_price, set_cached_price
import pytz

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self, bot):
        self.bot = bot
        self.client = BibabotAPIClient()
        self.metrics = MetricsCollector()
        self._stream_task: Optional[asyncio.Task] = None

    async def start_streaming(self):
        """Запускает получение новостей в реальном времени."""
        self._stream_task = asyncio.create_task(self._stream_worker())

    async def _stream_worker(self):
        """Воркер для стрима с автоматическим переподключением."""
        while True:
            try:
                logger.info("Connecting to news stream...")
                await self.client.stream_news(self.process_news)
            except Exception as e:
                logger.error(f"Stream error: {e}. Reconnecting in 10s...")
                await asyncio.sleep(10)

    async def process_news(self, news_data: dict):
        """Обрабатывает полученную новость."""
        # Проверяем, что новость о Bitcoin
        tickers = news_data.get("tickers", [])
        if "BTC" not in tickers:
            return

        url = news_data.get("url")
        if not url:
            return

        # Проверяем, есть ли уже в БД
        async for session in get_db():
            existing = await session.execute(select(News).where(News.url == url))
            if existing.scalar_one_or_none():
                return

        # Получаем тональность
        sentiment = await self.client.get_sentiment(url)
        if not sentiment:
            return

        # Получаем текущую цену BTC (из кэша или напрямую)
        price = await get_cached_price()
        if not price:
            # fallback
            price = await self.metrics.get_btc_price_coindesk()
            if price:
                await set_cached_price(price)

        # Сохраняем в БД
        news_item = News(
            title=news_data.get("title"),
            url=url,
            source=news_data.get("source"),
            published_at=datetime.fromisoformat(news_data["published_at"].replace("Z", "+00:00")),
            sentiment_label=sentiment.get("label"),
            sentiment_score=sentiment.get("score"),
            btc_price_at_publish=price
        )
        session.add(news_item)
        await session.commit()
        logger.info(f"Saved news: {news_data.get('title')}")

        # Запускаем таймеры для обновления цены через 1, 6, 24 часа
        asyncio.create_task(self._update_price_later(news_item.id, hours=1))
        asyncio.create_task(self._update_price_later(news_item.id, hours=6))
        asyncio.create_task(self._update_price_later(news_item.id, hours=24))

    async def _update_price_later(self, news_id: int, hours: int):
        """Обновляет цену через заданное количество часов."""
        await asyncio.sleep(hours * 3600)
        async for session in get_db():
            news = await session.get(News, news_id)
            if not news:
                return

            current_price = await self.metrics.get_btc_price_coindesk()
            if current_price:
                if hours == 1:
                    news.btc_price_1h_later = current_price
                    # Вычисляем изменение
                    if news.btc_price_at_publish:
                        change = (current_price - news.btc_price_at_publish) / news.btc_price_at_publish * 100
                        news.price_change_1h = change
                        # Определяем тренд
                        if change > 0.5:
                            news.market_trend = "positive"
                        elif change < -0.5:
                            news.market_trend = "negative"
                        else:
                            news.market_trend = "neutral"
                        # Проверяем совпадение
                        if news.market_trend != "neutral" and news.sentiment_label == news.market_trend:
                            news.matched = True
                            # Уведомляем подписчиков
                            await self.notify_subscribers_about_match(news)
                elif hours == 6:
                    news.btc_price_6h_later = current_price
                    if news.btc_price_at_publish:
                        change = (current_price - news.btc_price_at_publish) / news.btc_price_at_publish * 100
                        news.price_change_6h = change
                elif hours == 24:
                    news.btc_price_24h_later = current_price
                    if news.btc_price_at_publish:
                        change = (current_price - news.btc_price_at_publish) / news.btc_price_at_publish * 100
                        news.price_change_24h = change
                await session.commit()

    async def notify_subscribers_about_match(self, news: News):
        """Отправляет уведомление подписанным пользователям о совпавшей новости."""
        async for session in get_db():
            users = await session.execute(
                select(User).where(User.subscribed_high_sentiment == True)
            )
            for user in users.scalars():
                try:
                    text = (
                        f"📰 <b>Новость совпала с движением рынка!</b>\n\n"
                        f"{news.title}\n"
                        f"Тональность: {news.sentiment_label} ({news.sentiment_score:.2f})\n"
                        f"Изменение цены за 1ч: {news.price_change_1h:.2f}%\n"
                        f"<a href='{news.url}'>Читать</a>"
                    )
                    await self.bot.send_message(user.telegram_id, text)
                except Exception as e:
                    logger.error(f"Failed to notify user {user.telegram_id}: {e}")

    async def close(self):
        await self.client.close()
        await self.metrics.close()
        if self._stream_task:
            self._stream_task.cancel()
