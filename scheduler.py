from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from typing import Dict

from services.api_client import api_client
from services.trigger_detector import trigger_detector
from services.btc_service import top_btc_articles, is_btc_related
from database import async_session, News, add_news_to_db, select, User
from handlers.group import publish_all_news_to_group
from config import CHANNEL_ID, GROUP_CHAT_ID, TRIGGER_TIMEFRAME_MINUTES
from utils import escape_html

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_bot = None


def _get_bot():
    if _bot is None:
        raise RuntimeError("Scheduler bot is not initialized")
    return _bot


async def scheduled_news_check():
    logger.info("Running scheduled BTC news check...")
    news_list = await api_client.get_bitcoin_news(limit=25)
    news_list = top_btc_articles(news_list or [], limit=20)
    for news in news_list:
        async with async_session() as session:
            exists = await session.execute(select(News).where(News.url == news["url"]))
            if exists.scalar_one_or_none():
                continue

        db_news = await add_news_to_db(news)
        triggered_news = await trigger_detector.check_if_triggered(news)
        if triggered_news and db_news:
            async with async_session() as session:
                db_news.triggered = True
                db_news.price_change = triggered_news["price_change"]
                db_news.sentiment_score = triggered_news["sentiment"].get("score")
                await session.commit()
            await publish_triggered_news_to_channel(triggered_news)
            await notify_triggered_subscribers(triggered_news)


async def check_breaking_news():
    breaking = await api_client.get_breaking_news(limit=10)
    for news in top_btc_articles(breaking or [], limit=5):
        # без Redis в этом модуле: используем БД как дедуп (URL unique)
        async with async_session() as session:
            exists = await session.execute(select(News).where(News.url == news["url"]))
            if exists.scalar_one_or_none():
                continue

        await add_news_to_db(news)
        await publish_breaking_news_to_channel(news)


async def notify_triggered_subscribers(news_data: Dict):
    async with async_session() as session:
        users = await session.execute(select(User).where(User.subscribed_triggered.is_(True)))
        users = users.scalars().all()

    for user in users:
        try:
            direction = "📈" if news_data["price_change"] > 0 else "📉"
            text = (
                f"{direction} <b>Triggered BTC Alert</b>\n\n"
                f"{escape_html(news_data['title'])}\n\n"
                f"Price change: <b>{news_data['price_change']:+.2f}%</b>\n"
                f"Sentiment: <b>{escape_html(news_data['sentiment']['label'])}</b>\n\n"
                f"<a href='{escape_html(news_data['url'])}'>Read more</a>"
            )
            await _get_bot().send_message(user.telegram_id, text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error("Failed to notify user %s: %s", user.telegram_id, e)


async def check_whales():
    whales = await api_client.get_whale_transactions(limit=3)
    if whales:
        for whale in whales:
            if str(whale.get("coin", "")).upper() != "BTC":
                continue
            await notify_whale_subscribers(whale)


async def check_liquidations():
    liqs = await api_client.get_liquidations(limit=5)
    if not liqs:
        return

    async with async_session() as session:
        users = await session.execute(select(User).where(User.subscribed_liquidations.is_(True)))
        users = users.scalars().all()

    for liq in liqs[:3]:
        pair = str(liq.get("pair", ""))
        if "BTC" not in pair:
            continue
        side = str(liq.get("side", "")).upper()
        amount = liq.get("amount_usd", 0)
        text = f"💥 <b>BTC Liquidation</b>\n{side} {pair}\n${amount:,.0f}"
        for user in users:
            try:
                await _get_bot().send_message(user.telegram_id, text, parse_mode="HTML")
            except Exception as e:
                logger.error("Failed to notify liquidation for %s: %s", user.telegram_id, e)


async def notify_whale_subscribers(whale_data: Dict):
    async with async_session() as session:
        users = await session.execute(select(User).where(User.subscribed_whales.is_(True)))
        users = users.scalars().all()
    for user in users:
        try:
            text = (
                f"🐋 <b>BTC Whale Alert</b>\n\n"
                f"<code>{float(whale_data.get('amount', 0)):.2f} BTC</code> (${float(whale_data.get('value_usd', 0)):,.0f})\n"
                f"From: <code>{str(whale_data.get('from', 'n/a'))[:10]}...</code> → "
                f"To: <code>{str(whale_data.get('to', 'n/a'))[:10]}...</code>\n"
                f"<a href='{escape_html(str(whale_data.get('tx_url', 'https://mempool.space')))}'>View transaction</a>"
            )
            await _get_bot().send_message(user.telegram_id, text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as e:
            logger.error("Failed to notify user %s: %s", user.telegram_id, e)


async def publish_breaking_news_to_channel(news_data: Dict):
    if not CHANNEL_ID:
        return
    if not is_btc_related(news_data):
        return

    text = (
        f"🚨 <b>BTC BREAKING</b>\n\n"
        f"{escape_html(news_data.get('title', 'No title'))}\n\n"
        f"<a href='{escape_html(news_data.get('url', 'https://cryptocurrency.cv'))}'>Read full article</a>"
    )
    try:
        await _get_bot().send_message(CHANNEL_ID, text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error("Failed to send breaking to channel: %s", e)


async def publish_digest_to_channel():
    if not CHANNEL_ID:
        return
    digest = await api_client.summarize_daily_digest()
    if not digest:
        return

    fg = await api_client._make_request("/api/fear-greed")
    fg_line = "n/a"
    if fg:
        fg_line = f"{fg.get('classification', 'n/a')} ({fg.get('value', 'n/a')})"

    text = f"🧾 <b>BTC Digest</b>\nFear&Greed: <b>{escape_html(str(fg_line))}</b>\n\n{escape_html(digest)}"
    try:
        await _get_bot().send_message(CHANNEL_ID, text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error("Failed to send digest to channel: %s", e)


async def publish_triggered_news_to_channel(news_data: Dict):
    if not CHANNEL_ID:
        return
    title = escape_html(news_data["title"])
    summary = escape_html(news_data.get("summary", "No summary"))
    url = escape_html(news_data["url"])
    ticker = escape_html(news_data.get("ticker", "BTC"))
    price_change = news_data["price_change"]
    sentiment = escape_html(news_data["sentiment"]["label"])
    sentiment_score = news_data["sentiment"].get("score", 0)
    direction = "📈" if price_change > 0 else "📉"
    text = (
        f"{direction} <b>{title}</b>\n\n"
        f"💰 Price change: <b>{price_change:+.2f}%</b> in {TRIGGER_TIMEFRAME_MINUTES} min\n"
        f"🧠 Sentiment: <b>{sentiment}</b> ({sentiment_score:.2f})\n"
        f"📅 {escape_html(news_data['published_at'])}\n\n"
        f"<blockquote>{summary}</blockquote>\n\n"
        f"🔗 <a href='{url}'>Read full article →</a>\n\n"
        f"<code>#{ticker}</code>  <b>#BitcoinBastion</b>"
    )
    try:
        await _get_bot().send_message(CHANNEL_ID, text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        logger.error("Failed to send to channel: %s", e)


def setup_schedulers(bot):
    global _bot
    _bot = bot
    scheduler.add_job(scheduled_news_check, trigger=IntervalTrigger(minutes=15), id="check_triggers", replace_existing=True)
    scheduler.add_job(check_breaking_news, trigger=IntervalTrigger(minutes=3), id="check_breaking", replace_existing=True)
    scheduler.add_job(check_whales, trigger=IntervalTrigger(minutes=5), id="check_whales", replace_existing=True)
    scheduler.add_job(check_liquidations, trigger=IntervalTrigger(minutes=7), id="check_liquidations", replace_existing=True)

    if GROUP_CHAT_ID:
        scheduler.add_job(publish_all_news_to_group, trigger=IntervalTrigger(minutes=60), args=[_get_bot()], id="group_news_feed", replace_existing=True)

    scheduler.add_job(publish_digest_to_channel, trigger=CronTrigger(hour="9,21", minute=0), id="daily_digest", replace_existing=True)
    scheduler.add_job(cleanup_old_cache, trigger=CronTrigger(hour=3, minute=0), id="daily_cache_cleanup", replace_existing=True)


async def cleanup_old_cache():
    return
