import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, BotCommandScopeChatAdministrators

from config import BOT_TOKEN, TELEGRAM_WEBHOOK_URL, TELEGRAM_WEBHOOK_SECRET
from handlers import private, group, admin
from middlewares import AdminCheckMiddleware
from scheduler import setup_schedulers, scheduler
from services.api_client import api_client
from services.price_history import price_history
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


async def _set_scoped_commands() -> None:
    private_commands = [
        BotCommand(command="start", description="Open BTC menu"),
        BotCommand(command="btc", description="BTC price and sentiment context"),
        BotCommand(command="latest", description="Latest BTC headlines"),
        BotCommand(command="breaking", description="Breaking BTC alerts"),
        BotCommand(command="digest", description="BTC daily digest"),
        BotCommand(command="sentiment", description="BTC AI sentiment"),
        BotCommand(command="whales", description="BTC whale transactions"),
        BotCommand(command="liquidations", description="BTC liquidations"),
        BotCommand(command="funding", description="BTC funding rates"),
        BotCommand(command="subscribe", description="Alert subscriptions"),
    ]

    group_commands = [
        BotCommand(command="latest_group", description="Post latest BTC news to this group"),
        BotCommand(command="breaking", description="Show latest BTC breaking news"),
    ]

    admin_commands = [
        BotCommand(command="admin", description="Open admin dashboard"),
    ]

    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
    await bot.set_my_commands(admin_commands, scope=BotCommandScopeChatAdministrators())


async def on_startup():
    logger.info("Starting bot...")
    await init_db()
    await redis_cache.init_redis()
    await api_client._get_session()
    await price_history._get_session()
    await _set_scoped_commands()

    if TELEGRAM_WEBHOOK_URL:
        await bot.set_webhook(url=TELEGRAM_WEBHOOK_URL, secret_token=TELEGRAM_WEBHOOK_SECRET)
        logger.info("Webhook configured: %s", TELEGRAM_WEBHOOK_URL)

    setup_schedulers(bot)
    scheduler.start()
    logger.info("Scheduler started.")


async def on_shutdown():
    logger.info("Shutting down bot...")
    scheduler.shutdown()
    if TELEGRAM_WEBHOOK_URL:
        await bot.delete_webhook(drop_pending_updates=False)
    await redis_cache.close_redis()
    await api_client.close()
    await price_history.close()
    await dp.storage.close()
    await bot.session.close()


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    # fallback polling mode always available when webhook infra is absent
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
