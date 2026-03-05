import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
if GROUP_CHAT_ID and GROUP_CHAT_ID.lstrip('-').isdigit():
    GROUP_CHAT_ID = int(GROUP_CHAT_ID)

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL")  # Обязательная переменная

TRIGGER_PRICE_CHANGE_PERCENT = float(os.getenv("TRIGGER_PRICE_CHANGE_PERCENT", 2.0))
TRIGGER_TIMEFRAME_MINUTES = int(os.getenv("TRIGGER_TIMEFRAME_MINUTES", 30))

API_BASE_URL = "https://cryptocurrency.cv"

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = ["en", "ru"]

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", None)