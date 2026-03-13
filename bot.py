import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
from handlers import private, group, admin
from middlewares import AdminCheckMiddleware
from scheduler import setup_schedulers, scheduler
from services.api_client import api_client
from services.cryptorank_client import cryptorank
from services.price_history import price_history
from services.twitter_client import twitter_client
from services.nlp_service import nlp
from database import init_db
import redis_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(private.router)
dp.include_router(group.router)
dp.include_router(admin.router)

dp.message.middleware(AdminCheckMiddleware())

async def on_startup():
    logger.info("Starting bot...")
    await init_db()
    await redis_cache.init_redis()
    await api_client._get_session()
    await cryptorank._get_session()
    # twitter_client не требует сессии
    # nlp уже инициализирован при импорте
    setup_schedulers()
    scheduler.start()
    logger.info("Scheduler started.")

async def on_shutdown():
    logger.info("Shutting down bot...")
    scheduler.shutdown()
    await redis_cache.close_redis()
    await api_client.close()
    await cryptorank.close()
    await price_history.close()
    await dp.storage.close()
    await bot.session.close()

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
