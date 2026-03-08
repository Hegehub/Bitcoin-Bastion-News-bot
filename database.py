import asyncio
import logging
from datetime import datetime
from urllib.parse import urlsplit

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import (
    DATABASE_CONNECT_RETRIES,
    DATABASE_CONNECT_RETRY_DELAY,
    DATABASE_URL,
    SUPABASE_POOL_MODE,
)

logger = logging.getLogger(__name__)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add DATABASE_URL (or SUPABASE_POOLER_URL/SUPABASE_DB_URL) to your .env file."
    )


def _database_host() -> str:
    return urlsplit(DATABASE_URL).hostname or "unknown-host"


def _is_supabase_pooler() -> bool:
    host = urlsplit(DATABASE_URL).hostname or ""
    return "pooler.supabase.com" in host


def _engine_connect_args() -> dict:
    # Disable asyncpg statement cache only for transaction mode poolers.
    # In session mode prepared statements are supported.
    if _is_supabase_pooler() and SUPABASE_POOL_MODE == "transaction":
        return {"statement_cache_size": 0}
    return {}


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=_engine_connect_args(),
)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=True)
    first_name: Mapped[str] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_whales: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_liquidations: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_historical: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_international: Mapped[bool] = mapped_column(Boolean, default=False)
    subscribed_ai_alerts: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(500), unique=True)
    source: Mapped[str] = mapped_column(String(200))
    published_at: Mapped[datetime] = mapped_column(DateTime)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    tickers: Mapped[str] = mapped_column(String, nullable=True)
    triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    price_change: Mapped[float] = mapped_column(Float, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db():
    retries = max(DATABASE_CONNECT_RETRIES, 1)
    delay = max(DATABASE_CONNECT_RETRY_DELAY, 0.1)

    for attempt in range(1, retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            return
        except OSError as exc:
            logger.error(
                "Database connection attempt %s/%s failed for host '%s': %s",
                attempt,
                retries,
                _database_host(),
                exc,
            )
            if attempt == retries:
                raise RuntimeError(
                    "Cannot connect to database. Check DATABASE_URL host/port/firewall and SSL settings. "
                    "For Supabase, use SUPABASE_POOLER_URL and set SUPABASE_POOL_MODE=session|transaction according to your pool."
                ) from exc
            await asyncio.sleep(delay * attempt)


async def add_user(
    telegram_id: int,
    username: str = None,
    first_name: str = None,
    language: str = "en",
):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                language=language,
            )
            session.add(user)
            await session.commit()
        return user


async def add_news_to_db(news_data: dict):
    async with async_session() as session:
        existing = await session.scalar(select(News).where(News.url == news_data["url"]))
        if existing:
            return existing
        news = News(
            title=news_data["title"],
            url=news_data["url"],
            source=news_data.get("source", "unknown"),
            published_at=datetime.fromisoformat(news_data["published_at"].replace("Z", "+00:00")),
            summary=news_data.get("summary"),
            tickers=",".join(news_data.get("tickers", [])) if news_data.get("tickers") else None,
        )
        session.add(news)
        await session.commit()
        return news
