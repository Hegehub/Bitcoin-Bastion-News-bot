import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()


def _normalize_database_url(raw_url: str | None) -> str | None:
    """Normalize DATABASE_URL so it works with SQLAlchemy asyncpg + Supabase."""
    if not raw_url:
        return None

    normalized = raw_url.strip()

    # Heroku/Supabase snippets may still use the deprecated postgres:// prefix.
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql://", 1)

    # Ensure async SQLAlchemy uses asyncpg driver.
    if normalized.startswith("postgresql://"):
        normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Supabase commonly provides sslmode=require; asyncpg expects ssl=require.
    parts = urlsplit(normalized)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    if "sslmode" in query and "ssl" not in query:
        sslmode_value = query.pop("sslmode")
        if sslmode_value:
            query["ssl"] = sslmode_value

    rebuilt_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, rebuilt_query, parts.fragment))


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
if GROUP_CHAT_ID and GROUP_CHAT_ID.lstrip("-").isdigit():
    GROUP_CHAT_ID = int(GROUP_CHAT_ID)

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"))

TRIGGER_PRICE_CHANGE_PERCENT = float(os.getenv("TRIGGER_PRICE_CHANGE_PERCENT", 2.0))
TRIGGER_TIMEFRAME_MINUTES = int(os.getenv("TRIGGER_TIMEFRAME_MINUTES", 30))

API_BASE_URL = "https://cryptocurrency.cv"

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = ["en", "ru"]

CRYPTORANK_API_KEY = os.getenv("CRYPTORANK_API_KEY")
CRYPTORANK_BASE_URL = "https://api.cryptorank.io/v2"

WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000/webapp")
