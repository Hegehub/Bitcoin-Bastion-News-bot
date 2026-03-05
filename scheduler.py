from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from services.api_client import api_client
from services.trigger_detector import trigger_detector
from database import async_session, News, add_news_to_db, select, User
from handlers.group import publish_all_news_to_group
from config import CHANNEL_ID, GROUP_CHAT_ID
from bot import bot
import asyncio

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def scheduled_news_check():
    """Периодическая проверка новых новостей на триггерность."""
    logger.info("Запуск проверки новых новостей...")
    news_list = await api_client.get_latest_news(limit=20)
    if not news_list:
        return

    for news in news_list:
        async with async_session() as session:
            exists = await session.execute(select(News).where(News.url == news['url']))
            if exists.scalar_one_or_none():
                continue

        db_news = await add_news_to_db(news)
        triggered_news = await trigger_detector.check_if_triggered(news)
        
        if triggered_news and db_news:
            async with async_session() as session:
                db_news.triggered = True
                db_news.price_change = triggered_news['price_change']
                db_news.sentiment_score = triggered_news['sentiment'].get('score')
                await session.commit()

            await publish_triggered_news_to_channel(triggered_news)
            
            # Отправляем уведомления подписчикам
            await notify_subscribers(triggered_news)

async def notify_subscribers(news_data: Dict):
    """Отправляет уведомления подписанным пользователям о триггерной новости"""
    async with async_session() as session:
        users = await session.execute(
            select(User).where(User.subscribed_triggered == True)
        )
        users = users.scalars().all()
    
    for user in users:
        try:
            direction = "📈" if news_data['price_change'] > 0 else "📉"
            text = (
                f"{direction} **Triggered News Alert!**\n\n"
                f"{news_data['title']}\n\n"
                f"Price change: {news_data['price_change']:+.2f}%\n"
                f"Sentiment: {news_data['sentiment']['label']}\n\n"
                f"[Read more]({news_data['url']})"
            )
            await bot.send_message(user.telegram_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Failed to notify user {user.telegram_id}: {e}")

async def notify_whale_subscribers(whale_data: Dict):
    """Уведомления о китовых транзакциях"""
    async with async_session() as session:
        users = await session.execute(
            select(User).where(User.subscribed_whales == True)
        )
        users = users.scalars().all()
    
    for user in users:
        try:
            text = (
                f"🐋 **Whale Alert!**\n\n"
                f"{whale_data['amount']:.2f} {whale_data['coin']} (${whale_data['value_usd']:,.0f})\n"
                f"From: {whale_data['from'][:6]}... → To: {whale_data['to'][:6]}...\n"
                f"[View transaction]({whale_data['tx_url']})"
            )
            await bot.send_message(user.telegram_id, text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Failed to notify user {user.telegram_id}: {e}")

async def check_whales():
    """Периодическая проверка новых китовых транзакций"""
    whales = await api_client.get_whale_transactions(limit=3)
    if whales:
        # Здесь логика проверки, были ли эти транзакции уже отправлены
        # Для простоты просто отправляем уведомления
        for whale in whales:
            await notify_whale_subscribers(whale)

async def publish_triggered_news_to_channel(news_data):
    """Публикация триггерной новости в канал."""
    if not CHANNEL_ID:
        return
    price_change = news_data['price_change']
    direction = "📈" if price_change > 0 else "📉"
    sentiment = news_data['sentiment']['label']
    text = (
        f"{direction} **{news_data['title']}**\n\n"
        f"💰 Price change: **{price_change:+.2f}%**\n"
        f"🧠 Sentiment: **{sentiment}**\n"
        f"📅 {news_data['published_at']}\n\n"
        f"[Read full article]({news_data['url']})"
    )
    try:
        await bot.send_message(CHANNEL_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Failed to send to channel: {e}")

def setup_schedulers():
    scheduler.add_job(
        scheduled_news_check,
        trigger=IntervalTrigger(minutes=15),
        id="check_triggers",
        replace_existing=True
    )
    
    scheduler.add_job(
        check_whales,
        trigger=IntervalTrigger(minutes=5),
        id="check_whales",
        replace_existing=True
    )
    
    if GROUP_CHAT_ID:
        scheduler.add_job(
            publish_all_news_to_group,
            trigger=IntervalTrigger(minutes=60),
            args=[bot],
            id="group_news_feed",
            replace_existing=True
        )
    
    # Очистка старых кэшей (каждый день в 3:00)
    scheduler.add_job(
        cleanup_old_cache,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_cache_cleanup",
        replace_existing=True
    )

async def cleanup_old_cache():
    from redis_cache import redis_client
    # Можно удалить ключи старше N дней
    pass