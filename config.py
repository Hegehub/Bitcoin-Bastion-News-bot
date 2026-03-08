import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit, quote_plus

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

    parts = urlsplit(normalized)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    # Supabase commonly provides sslmode=require; asyncpg expects ssl=require.
    if "sslmode" in query and "ssl" not in query:
        sslmode_value = query.pop("sslmode")
        if sslmode_value:
            query["ssl"] = sslmode_value

    # Enforce TLS for Supabase links if not explicitly set.
    if (parts.hostname or "").endswith("supabase.co") and "ssl" not in query:
        query["ssl"] = "require"

    rebuilt_query = urlencode(query)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, rebuilt_query, parts.fragment))


def _build_database_url_from_parts() -> str | None:
    """Build URL from separate credentials if a full URL is not provided."""
    user = os.getenv("DB_USER") or os.getenv("PGUSER") or os.getenv("user")
    password = os.getenv("DB_PASSWORD") or os.getenv("PGPASSWORD") or os.getenv("password")
    host = os.getenv("DB_HOST") or os.getenv("PGHOST") or os.getenv("host")
    port = os.getenv("DB_PORT") or os.getenv("PGPORT") or os.getenv("port") or "5432"
    dbname = os.getenv("DB_NAME") or os.getenv("PGDATABASE") or os.getenv("dbname") or "postgres"

    if not (user and password and host):
        return None

    raw = (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{quote_plus(dbname)}"
        "?sslmode=require"
    )
    return _normalize_database_url(raw)


def _select_database_url() -> str | None:
    """Select the best DB URL for deployment environment.

    Priority:
    1) DATABASE_URL
    2) SUPABASE_POOLER_URL
    3) SUPABASE_DB_URL
    4) URL built from DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME
       (also supports PG* and legacy lowercase user/password/host/port/dbname)
    """
    raw = os.getenv("DATABASE_URL")
    if raw:
        return _normalize_database_url(raw)

    pooler = os.getenv("SUPABASE_POOLER_URL")
    if pooler:
        return _normalize_database_url(pooler)

    supabase_direct = os.getenv("SUPABASE_DB_URL")
    if supabase_direct:
        return _normalize_database_url(supabase_direct)

    return _build_database_url_from_parts()


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
if GROUP_CHAT_ID and GROUP_CHAT_ID.lstrip("-").isdigit():
    GROUP_CHAT_ID = int(GROUP_CHAT_ID)

ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = _select_database_url()
DATABASE_CONNECT_RETRIES = int(os.getenv("DATABASE_CONNECT_RETRIES", 3))
DATABASE_CONNECT_RETRY_DELAY = float(os.getenv("DATABASE_CONNECT_RETRY_DELAY", 2.0))
SUPABASE_POOL_MODE = (os.getenv("SUPABASE_POOL_MODE") or "").strip().lower()

TRIGGER_PRICE_CHANGE_PERCENT = float(os.getenv("TRIGGER_PRICE_CHANGE_PERCENT", 2.0))
TRIGGER_TIMEFRAME_MINUTES = int(os.getenv("TRIGGER_TIMEFRAME_MINUTES", 30))

API_BASE_URL = "https://cryptocurrency.cv"

DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = ["en", "ru"]

CRYPTORANK_API_KEY = os.getenv("CRYPTORANK_API_KEY")
CRYPTORANK_BASE_URL = "https://api.cryptorank.io/v2"

WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000/webapp")
