from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime, timedelta
from typing import Dict

from services.api_client import api_client
from services.twitter_client import twitter_client
from services.nlp_service import nlp
from services.trigger_detector import trigger_detector
from services.ml_trainer import ml_trainer
from services.backtest_engine import backtest_engine
from services.breaking_news import BreakingNewsDetector
from database import async_session, News, add_news_to_db, select, User
from handlers.group import publish_all_news_to_group
from config import CHANNEL_ID, GROUP_CHAT_ID, TRIGGER_TIMEFRAME_MINUTES, ADMIN_IDS
from bot import bot
from utils import escape_html
from redis_cache import redis_client
import asyncio

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Инициализация детектора breaking news
breaking_news_detector = BreakingNewsDetector(redis_client, window_minutes=10, threshold=3)

# -------------------------------------------------------------------
# Основные задачи
# -------------------------------------------------------------------

async def scheduled_news_check():
    """Периодическая проверка новостей из free-crypto-news."""
    logger.info("Running scheduled news check...")
    news_list = await api_client.get_latest_news(limit=20)
    if not news_list:
        return

    for news in news_list:
        # Дедупликация
        async with async_session() as session:
            exists = await session.execute(select(News).where(News.url == news['url']))
            if exists.scalar_one_or_none():
                continue

        # Проверка на breaking news
        is_breaking = await breaking_news_detector.add_news(news)
        if is_breaking:
            news['is_breaking'] = True

        # Сохраняем в БД
        db_news = await add_news_to_db(news)

        # Проверяем триггер
        triggered_news = await trigger_detector.check_if_triggered(news)

        if triggered_news and db_news:
            async with async_session() as session:
                db_news.triggered = True
                db_news.price_change = triggered_news['price_change']
                db_news.sentiment_score = triggered_news['sentiment'].get('score')
                # Сохраняем impact score, если есть
                if 'impact_score' in triggered_news:
                    # Можно добавить поле в модель News, но пока пропустим
                    pass
                await session.commit()

            await publish_triggered_news_to_channel(triggered_news)
            await notify_subscribers(triggered_news)

async def scheduled_twitter_check():
    """Периодическая проверка твитов."""
    logger.info("Running scheduled Twitter check...")
    queries = ["Bitcoin", "BTC", "ETF", "halving", "SEC", "Fed"]
    for query in queries:
        tweets = await twitter_client.search_tweets(query, limit=5, hours_back=6)
        for tweet in tweets:
            # Анализ тональности
            sentiment = nlp.analyze(tweet['text'])[0]

            # Проверка на breaking news (по тексту твита)
            news_stub = {'title': tweet['text'][:200], 'url': f"https://twitter.com/i/web/status/{tweet['id']}"}
            is_breaking = await breaking_news_detector.add_news(news_stub)

            # Сохраняем в БД как псевдо-новость
            async with async_session() as session:
                exists = await session.execute(
                    select(News).where(News.url == f"https://twitter.com/i/web/status/{tweet['id']}")
                )
                if exists.scalar_one_or_none():
                    continue

            news_article = {
                'title': tweet['text'][:200],
                'url': f"https://twitter.com/i/web/status/{tweet['id']}",
                'source': 'Twitter',
                'published_at': tweet['created_at'],
                'tickers': ['BTC'],
                'is_breaking': is_breaking
            }

            db_news = await add_news_to_db(news_article)

            # Проверяем триггер
            triggered = await trigger_detector.check_if_triggered(news_article)

            if triggered and db_news:
                async with async_session() as session:
                    db_news.triggered = True
                    db_news.price_change = triggered['price_change']
                    db_news.sentiment_score = triggered['sentiment'].get('score')
                    await session.commit()
                await publish_triggered_news_to_channel(triggered)
                await notify_subscribers(triggered)

# -------------------------------------------------------------------
# Уведомления подписчиков
# -------------------------------------------------------------------

async def notify_subscribers(news_data: Dict):
    """Отправляет уведомления подписанным пользователям о триггерной новости."""
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
                f"Sentiment: <b>{escape_html(news_data['sentiment']['label'])}</b>\n"
            )
            if news_data.get('impact_score'):
                text += f"Impact score: <b>{news_data['impact_score']:.2f}</b>\n"
            if news_data.get('is_breaking'):
                text += f"🚨 <b>BREAKING NEWS</b>\n"
            text += f"\n<a href='{escape_html(news_data['url'])}'>Read more</a>\n\n"
            text += f"<b>#BitcoinBastion</b>"

            await bot.send_message(user.telegram_id, text, parse_mode='HTML', disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Failed to notify user {user.telegram_id}: {e}")

async def notify_whale_subscribers(whale_data: Dict):
    """Отправляет уведомления о китовых транзакциях."""
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

# -------------------------------------------------------------------
# Публикация в канал
# -------------------------------------------------------------------

async def publish_triggered_news_to_channel(news_data):
    """Публикует триггерную новость в канал."""
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

    # Определяем префикс для breaking news
    breaking_prefix = "🚨 BREAKING: " if news_data.get('is_breaking') else ""

    text = (
        f"{direction} <b>{breaking_prefix}{title}</b>\n\n"
        f"💰 Price change: <b>{price_change:+.2f}%</b> in {TRIGGER_TIMEFRAME_MINUTES} min\n"
        f"🧠 Sentiment: <b>{sentiment}</b> ({sentiment_score:.2f})\n"
    )
    if news_data.get('impact_score'):
        text += f"⚡ Impact score: <b>{news_data['impact_score']:.2f}</b>\n"
    if news_data.get('entities'):
        entities = ', '.join(news_data['entities'][:3])
        text += f"🔍 Entities: {escape_html(entities)}\n"

    text += (
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

# -------------------------------------------------------------------
# Проверка китовых транзакций
# -------------------------------------------------------------------

async def check_whales():
    """Проверяет новые китовые транзакции и отправляет уведомления."""
    whales = await api_client.get_whale_transactions(limit=3)
    if whales:
        for whale in whales:
            await notify_whale_subscribers(whale)

# -------------------------------------------------------------------
# ML и аналитические задачи
# -------------------------------------------------------------------

async def scheduled_ml_retrain():
    """Ежедневное переобучение ML-модели."""
    logger.info("Running scheduled ML retraining...")
    await ml_trainer.retrain_if_needed()

async def scheduled_backtest_report():
    """Еженедельный отчёт по бэктестингу (отправляется админам)."""
    logger.info("Running weekly backtest...")
    results = await backtest_engine.run_backtest(days=7, use_ml=True)

    # Формируем отчёт
    report = (
        f"📊 <b>Weekly Backtest Report</b>\n\n"
        f"📅 Period: last 7 days\n"
        f"📰 Total news: {results['total']}\n"
        f"💰 With price data: {results['with_price']}\n"
        f"🎯 Accuracy (sentiment): <b>{results['accuracy']:.1f}%</b>\n"
        f"🤖 ML Accuracy: <b>{results.get('ml_accuracy', 0):.1f}%</b>\n\n"
    )

    if results.get('by_category'):
        report += "📊 <b>Top categories:</b>\n"
        for cat, count in list(results['by_category'].items())[:5]:
            report += f"  • {cat}: {count}\n"

    if results.get('by_source'):
        report += "\n📰 <b>Top sources:</b>\n"
        for src, count in list(results['by_source'].items())[:5]:
            report += f"  • {src}: {count}\n"

    report += f"\n<b>#BitcoinBastion</b>"

    # Отправляем всем админам
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, report, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to send backtest report to {admin_id}: {e}")

async def scheduled_thresholds_update():
    """Обновляет пороги категорий на основе исторических данных."""
    logger.info("Updating price thresholds...")
    await trigger_detector.update_thresholds(days=30)

# -------------------------------------------------------------------
# Очистка кэша
# -------------------------------------------------------------------

async def cleanup_old_cache():
    """Очищает старые ключи в Redis (например, старше 7 дней)."""
    logger.info("Cleaning up old cache...")
    # В реальности нужно реализовать логику удаления старых ключей
    # Например, можно использовать redis_client.scan_iter() и удалять по шаблону
    pass

# -------------------------------------------------------------------
# Настройка планировщика
# -------------------------------------------------------------------

def setup_schedulers():
    """Инициализирует все периодические задачи."""

    # Обновление порогов категорий (ежедневно в 1:00)
    scheduler.add_job(
        scheduled_thresholds_update,
        trigger=CronTrigger(hour=1, minute=0),
        id="update_thresholds",
        replace_existing=True
    )

    # Проверка новостей (каждые 15 минут)
    scheduler.add_job(
        scheduled_news_check,
        trigger=IntervalTrigger(minutes=15),
        id="check_news",
        replace_existing=True
    )

    # Проверка твитов (каждые 30 минут)
    scheduler.add_job(
        scheduled_twitter_check,
        trigger=IntervalTrigger(minutes=30),
        id="check_twitter",
        replace_existing=True
    )

    # Проверка китовых транзакций (каждые 5 минут)
    scheduler.add_job(
        check_whales,
        trigger=IntervalTrigger(minutes=5),
        id="check_whales",
        replace_existing=True
    )

    # Публикация в группу (каждый час, если настроено)
    if GROUP_CHAT_ID:
        scheduler.add_job(
            publish_all_news_to_group,
            trigger=IntervalTrigger(minutes=60),
            args=[bot],
            id="group_news_feed",
            replace_existing=True
        )

    # Ежедневное переобучение ML (в 4:00)
    scheduler.add_job(
        scheduled_ml_retrain,
        trigger=CronTrigger(hour=4, minute=0),
        id="ml_retrain",
        replace_existing=True
    )

    # Еженедельный отчёт по бэктестингу (каждый понедельник в 9:00)
    scheduler.add_job(
        scheduled_backtest_report,
        trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
        id="backtest_report",
        replace_existing=True
    )

    # Ежедневная очистка кэша (в 3:00)
    scheduler.add_job(
        cleanup_old_cache,
        trigger=CronTrigger(hour=3, minute=0),
        id="daily_cache_cleanup",
        replace_existing=True
    )

    logger.info("All scheduled jobs configured")