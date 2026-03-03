import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# API
BIBABOT_API = "https://cryptocurrency.cv/api"

# База данных
DATABASE_URL = "sqlite+aiosqlite:///crypto_bot.db"

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Параметры
NEWS_CHECK_INTERVAL = 15  # минут (для планировщика, если не используем стрим)
PRICE_UPDATE_INTERVAL = 5  # минут
WHALE_CHECK_INTERVAL = 10  # минут
LIQUIDATION_CHECK_INTERVAL = 10  # минут
