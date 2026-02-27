from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from news_analyzer import NewsAnalyzer
from metrics import MetricsCollector
import asyncio

scheduler = AsyncIOScheduler()

async def scheduled_news_check():
    analyzer = NewsAnalyzer()
    await analyzer.check_news_and_analyze()
    await analyzer.close()

async def scheduled_price_update():
    # Например, обновление кэша цены
    metrics = MetricsCollector()
    price = await metrics.get_btc_price_coindesk()
    if price:
        await redis.setex("btc_price", 300, price["price"])
    await metrics.close()

async def scheduled_matching_analysis():
    analyzer = NewsAnalyzer()
    await analyzer.analyze_matching_news()
    await analyzer.close()

def start_scheduler():
    scheduler.add_job(scheduled_news_check, IntervalTrigger(minutes=15), id="news_check")
    scheduler.add_job(scheduled_price_update, IntervalTrigger(minutes=5), id="price_update")
    scheduler.add_job(scheduled_matching_analysis, IntervalTrigger(minutes=30), id="matching_analysis")
    scheduler.start()
