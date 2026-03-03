from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import get_db, News, User
from bibabot_client import BibabotAPIClient
from redis_cache import redis
from sqlalchemy import select
import logging
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def publish_matched_news(bot, channel_id: str):
    """Публикует в канал новые совпавшие новости."""
    async for session in get_db():
        # Находим последние 5 совпавших, ещё не опубликованных
        news_items = await session.execute(
            select(News).where(
                News.matched == True,
                News.published_in_channel == False
            ).order_by(News.published_at.desc()).limit(5)
        )
        for news in news_items.scalars():
            text = (
                f"📈 <b>Анализ новости</b>\n\n"
                f"{news.title}\n"
                f"Источник: {news.source}\n"
                f"Тональность: {news.sentiment_label} ({news.sentiment_score:.2f})\n"
                f"Цена BTC на момент публикации: ${news.btc_price_at_publish:,.0f}\n"
                f"Изменение через 1ч: {news.price_change_1h:+.2f}%\n"
                f"<a href='{news.url}'>Читать полностью</a>"
            )
            try:
                await bot.send_message(chat_id=channel_id, text=text)
                news.published_in_channel = True
                await session.commit()
                logger.info(f"Published news {news.id} to channel")
            except Exception as e:
                logger.error(f"Failed to publish news {news.id}: {e}")

async def check_whales(bot):
    """Проверяет новые китовые транзакции и уведомляет подписчиков."""
    client = BibabotAPIClient()
    whales = await client.get_whales()
    await client.close()
    if not whales:
        return

    # Получаем последние сохранённые транзакции из Redis
    last_whales = await redis.get("last_whales")
    if last_whales:
        last_whales = json.loads(last_whales)
    else:
        last_whales = []

    # Находим новые (по tx_hash)
    new_whales = [w for w in whales if w.get("tx_hash") not in {lw.get("tx_hash") for lw in last_whales}]
    if new_whales:
        await redis.setex("last_whales", 3600, json.dumps(whales[:20]))  # храним последние 20

        # Уведомляем подписчиков
        async for session in get_db():
            users = await session.execute(select(User).where(User.subscribed_whales == True))
            for user in users.scalars():
                for w in new_whales[:3]:  # ограничим 3
                    text = (
                        f"🐋 <b>Китовая транзакция!</b>\n"
                        f"Сумма: {w.get('amount_usd', 'N/A')} USD\n"
                        f"Монета: {w.get('symbol', 'BTC')}\n"
                        f"Биржа: {w.get('exchange', 'Unknown')}\n"
                        f"<a href='{w.get('tx_url', '#')}'>Детали</a>"
                    )
                    try:
                        await bot.send_message(user.telegram_id, text)
                    except Exception as e:
                        logger.error(f"Failed to send whale alert: {e}")

async def check_liquidations(bot):
    """Проверяет новые ликвидации и уведомляет подписчиков."""
    client = BibabotAPIClient()
    liquidations = await client.get_liquidations()
    await client.close()
    if not liquidations:
        return

    last_liquidations = await redis.get("last_liquidations")
    if last_liquidations:
        last_liquidations = json.loads(last_liquidations)
    else:
        last_liquidations = []

    # Предположим, что у ликвидации есть уникальный id
    new_liqs = [l for l in liquidations if l.get("id") not in {ll.get("id") for ll in last_liquidations}]
    if new_liqs:
        await redis.setex("last_liquidations", 3600, json.dumps(liquidations[:20]))

        async for session in get_db():
            users = await session.execute(select(User).where(User.subscribed_liquidations == True))
            for user in users.scalars():
                for liq in new_liqs[:3]:
                    text = (
                        f"💥 <b>Ликвидация!</b>\n"
                        f"Сумма: {liq.get('amount_usd', 'N/A')} USD\n"
                        f"Монета: {liq.get('symbol', 'BTC')}\n"
                        f"Сторона: {liq.get('side', 'Long/Short')}\n"
                        f"Цена: ${liq.get('price', 'N/A')}"
                    )
                    try:
                        await bot.send_message(user.telegram_id, text)
                    except Exception as e:
                        logger.error(f"Failed to send liquidation alert: {e}")

def start_scheduler(bot, channel_id):
    scheduler.add_job(
        publish_matched_news,
        trigger=IntervalTrigger(minutes=30),
        args=[bot, channel_id],
        id="publish_news"
    )
    scheduler.add_job(
        check_whales,
        trigger=IntervalTrigger(minutes=10),
        args=[bot],
        id="check_whales"
    )
    scheduler.add_job(
        check_liquidations,
        trigger=IntervalTrigger(minutes=10),
        args=[bot],
        id="check_liquidations"
    )
    scheduler.start()
