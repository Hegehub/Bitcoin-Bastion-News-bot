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
from database import init_db
import redis_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Регистрация роутеров
dp.include_router(private.router)
dp.include_router(group.router)
dp.include_router(admin.router)

# Middleware для проверки админства
dp.message.middleware(AdminCheckMiddleware())
dp.callback_query.middleware(AdminCheckMiddleware())

async def on_startup():
    logger.info("🚀 Запуск бота...")
    
    # Инициализация БД
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    # Инициализация Redis
    await redis_cache.init_redis()
    logger.info("✅ Redis подключен")
    
    # Инициализация сессии API (без теста - тест будет доступен только админам)
    await api_client._get_session()
    logger.info("✅ Сессия API создана")
    
    # Настройка планировщика
    setup_schedulers(bot)
    scheduler.start()
    logger.info("✅ Планировщик запущен")
    
    logger.info("🤖 Бот готов к работе. Для проверки API используйте команду /api_status (только для админов)")

async def on_shutdown():
    logger.info("🛑 Остановка бота...")
    scheduler.shutdown()
    await redis_cache.close_redis()
    await api_client.close()
    await dp.storage.close()
    await bot.session.close()
    logger.info("✅ Ресурсы освобождены")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logger.info("🔄 Запускаем поллинг...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())