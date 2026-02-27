import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import News, get_db
from metrics import MetricsCollector
from redis_cache import redis
import json

logger = logging.getLogger(__name__)

class NewsAnalyzer:
    def __init__(self):
        self.bibabot_url = "https://cryptocurrency.cv/api"
        self.session = None
        self.metrics = MetricsCollector()

    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
        await self.metrics.close()

    # Получение новостей из BiBaBot
    async def fetch_news(self, ticker="BTC", limit=20) -> List[Dict]:
        session = await self.get_session()
        url = f"{self.bibabot_url}/news"
        params = {"ticker": ticker, "limit": limit}
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("articles", [])
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
        return []

    # Получение тональности новости через BiBaBot
    async def get_sentiment(self, news_url: str) -> Optional[Dict]:
        session = await self.get_session()
        url = f"{self.bibabot_url}/ai/sentiment"
        params = {"url": news_url}
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("sentiment")
        except Exception as e:
            logger.error(f"Error getting sentiment: {e}")
        return None

    # Получение цены BTC на момент запроса
    async def get_current_btc_price(self) -> Optional[float]:
        # Сначала проверяем кэш Redis
        cached = await redis.get("btc_price")
        if cached:
            return float(cached)
        # Иначе через MetricsCollector
        price_data = await self.metrics.get_btc_price_coindesk()
        if price_data:
            price = price_data["price"]
            await redis.setex("btc_price", 300, price)  # кэш на 5 минут
            return price
        return None

    # Сохранение новости в БД
    async def save_news_to_db(self, article: Dict, sentiment: Dict, price_at_publish: float):
        async for session in get_db():
            # Проверяем, есть ли уже такая новость
            existing = await session.execute(
                select(News).where(News.url == article["url"])
            )
            if existing.scalar_one_or_none():
                return
            news_item = News(
                title=article["title"],
                url=article["url"],
                source=article.get("source"),
                published_at=datetime.fromisoformat(article["published_at"].replace("Z", "+00:00")),
                sentiment_label=sentiment.get("label"),
                sentiment_score=sentiment.get("score"),
                btc_price_at_publish=price_at_publish
            )
            session.add(news_item)
            await session.commit()
            logger.info(f"Saved news: {article['title']}")

    # Запланированная задача: проверка новых новостей и анализ
    async def check_news_and_analyze(self):
        logger.info("Checking for new news...")
        news_list = await self.fetch_news(limit=30)
        current_price = await self.get_current_btc_price()
        if not current_price:
            logger.error("Cannot get current BTC price")
            return

        for article in news_list:
            # Получаем тональность (можно с задержкой)
            sentiment = await self.get_sentiment(article["url"])
            if not sentiment:
                continue
            await self.save_news_to_db(article, sentiment, current_price)

        # Теперь для новостей, у которых нет цены через 1 час, запланируем обновление
        # Это делается в scheduler'е, вызывающем update_price_after_delay
        logger.info("News check completed.")

    # Обновление цены через 1 час после публикации
    async def update_price_after_delay(self, news_id: int, delay_hours: int = 1):
        await asyncio.sleep(delay_hours * 3600)  # ждем указанное количество часов
        async for session in get_db():
            news = await session.get(News, news_id)
            if news and news.btc_price_1h_later is None:
                current_price = await self.get_current_btc_price()
                if current_price:
                    if delay_hours == 1:
                        news.btc_price_1h_later = current_price
                    elif delay_hours == 24:
                        news.btc_price_24h_later = current_price
                    await session.commit()
                    logger.info(f"Updated price for news {news_id} after {delay_hours}h")

    # Анализ новостей на совпадение с реакцией рынка
    async def analyze_matching_news(self):
        # Выбираем новости, у которых есть цена через 1 час, но ещё не отмечены matched
        async for session in get_db():
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            news_items = await session.execute(
                select(News).where(
                    News.btc_price_1h_later.isnot(None),
                    News.matched == False,
                    News.published_at <= one_hour_ago
                )
            )
            for news in news_items.scalars():
                # Определяем тренд рынка по изменению цены за 1 час
                change_1h = (news.btc_price_1h_later - news.btc_price_at_publish) / news.btc_price_at_publish * 100
                if change_1h > 0.5:
                    market_trend = "positive"
                elif change_1h < -0.5:
                    market_trend = "negative"
                else:
                    market_trend = "neutral"

                news.market_trend = market_trend
                # Совпадение, если тональность новости и тренд совпадают (и не нейтральны)
                if market_trend != "neutral" and news.sentiment_label == market_trend:
                    news.matched = True
                    # Здесь можно отправить уведомления подписчикам
                    await self.notify_subscribers(news)
                await session.commit()

    # Уведомление подписчиков
    async def notify_subscribers(self, news: News):
        # Получаем всех подписанных пользователей из БД
        async for session in get_db():
            users = await session.execute(select(User).where(User.subscribed == True))
            for user in users.scalars():
                # Отправляем сообщение через бота (нужен доступ к боту)
                # Передадим через очередь или прямо вызовем метод bot.send_message
                # Поскольку мы в отдельной задаче, лучше использовать отдельную очередь.
                # Пока пропустим.
                pass
