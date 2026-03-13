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
DATABASE_URL = os.getenv("DATABASE_URL")

TRIGGER_PRICE_CHANGE_PERCENT = float(os.getenv("TRIGGER_PRICE_CHANGE_PERCENT", 2.0))
TRIGGER_TIMEFRAME_MINUTES = int(os.getenv("TRIGGER_TIMEFRAME_MINUTES", 30))

API_BASE_URL = "https://cryptocurrency.cv"

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = ["en", "ru"]

CRYPTORANK_API_KEY = os.getenv("CRYPTORANK_API_KEY")
CRYPTORANK_BASE_URL = "https://api.cryptorank.io/v2"

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# LLM Provider
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

USE_LLAMA_FALLBACK = os.getenv("USE_LLAMA_FALLBACK", "true").lower() == "true"

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")