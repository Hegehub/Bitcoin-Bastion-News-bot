from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from services.api_client import api_client
from services.trigger_detector import trigger_detector
from database import async_session, News, add_news_to_db, select, User
from handlers.group import publish_all_news_to_group
from config import CHANNEL_ID, GROUP_CHAT_ID, TRIGGER_TIMEFRAME_MINUTES
from bot import bot
from utils import escape_html
import asyncio

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def scheduled_news_check():
    logger.info("Running scheduled news check...")
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
            await notify_subscribers(triggered_news)

async def notify_subscribers(news_data: Dict):
    async with async_session() as session:
        users = await session.execute(select(User).where(User.subscribed_triggered == True))
        users = users.scalars().all()
    for user in users:
        try:
            direction = "📈" if news_data['price_change'] > 0 else "📉"
            text = (
                f"{direction} <b>Triggered News Alert!</b>\n\n"
                f"{escape_html(news_data['title'])}\n\n"
                f"Price change: <b>{news_data['price_change']:+.2f}%</b>\n"
                f"Sentiment: <b>{escape_html(news_data['sentiment']['label'])}</b>\n\n"
                f"<a href='{escape_html(news_data['url'])}'>Read more</a>\n\n"
                f"<b>#BitcoinBastion</b>"
            )
            await bot.send_message(user.telegram_id, text, parse_mode='HTML', disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Failed to notify user {user.telegram_id}: {e}")

async def check_whales():
    whales = await api_client.get_whale_transactions(limit=3)
    if whales:
        for whale in whales:
            await notify_whale_subscribers(whale)

async def notify_whale_subscribers(whale_data: Dict):
    async with async_session() as session:
        users = await session.execute(select(User).where(User.subscribed_whales == True))
        users = users.scalars().all()
    for user in users:
        try:
            text = (
                f"🐋 <b>Whale Alert!</b>\n\n"
                f"<code>{whale_data['amount']:.2f} {whale_data['coin']}</code> (${whale_data['value_usd']:,.0f})\n"
                f"From: <code>{whale_data['from'][:6]}...</code> → To: <code>{whale_data['to'][:6]}...</code>\n"
                f"<a href='{escape_html(whale_data['tx_url'])}'>View transaction</a>\n\n"
                f"<b>#BitcoinBastion</b>"
            )
            await bot.send_message(user.telegram_id, text, parse_mode='HTML', disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Failed to notify user {user.telegram_id}: {e}")

async def publish_triggered_news_to_channel(news_data):
    if not CHANNEL_ID:
        return
    title = escape_html(news_data['title'])
    summary = escape_html(news_data.get('summary', 'No summary'))
    url = escape_html(news_data['url'])
    ticker = escape_html(news_data.get('ticker', 'BTC'))
    price_change = news_data['price_change']
    sentiment = escape_html(news_data['sentiment']['label'])
    sentiment_score = news_data['sentiment'].get('score', 0)
    direction = "📈" if price_change > 0 else "📉"
    text = (
        f"{direction} <b>{title}</b>\n\n"
        f"💰 Price change: <b>{price_change:+.2f}%</b> in {TRIGGER_TIMEFRAME_MINUTES} min\n"
        f"🧠 Sentiment: <b>{sentiment}</b> ({sentiment_score:.2f})\n"
        f"📅 {escape_html(news_data['published_at'])}\n\n"
        f"<blockquote>{summary}</blockquote>\n\n"
        f"🔗 <a href='{url}'>Read full article →</a>\n\n"
        f"<code>#{ticker}</code>  <b>#BitcoinBastion</b>\n"
        f"<tg-spoiler>⚡ Analysis details: 1h change: +?.?% , 6h change: +?.?%</tg-spoiler>"
    )
    try:
        await bot.send_message(CHANNEL_ID, text, parse_mode='HTML', disable_web_page_preview=True)
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
    scheduler.add_job(
        cleanup_old_cache,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_cache_cleanup",
        replace_existing=True
    )

async def cleanup_old_cache():
    # Очистка старых ключей Redis (опционально)
    pass