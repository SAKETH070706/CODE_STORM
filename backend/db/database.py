import os
import ssl
import logging
from typing import AsyncGenerator, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine
)
from sqlalchemy import text
from config import (
    DATABASE_URL,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
    DB_POOL_RECYCLE,
    DB_SSL_MODE,
    logger
)

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def normalize_database_url(raw_url: str) -> tuple[str, dict]:
    """
    Normalizes PostgreSQL URL for asyncpg and extracts SSL arguments for Aiven PostgreSQL.
    """
    if not raw_url:
        return "sqlite+aiosqlite:///code_storm.db", {}

    # Check for placeholder strings in unconfigured .env
    cleaned = raw_url.strip()
    if ":port" in cleaned or "@host" in cleaned or "your_" in cleaned:
        return "sqlite+aiosqlite:///code_storm.db", {}

    parsed = urlparse(cleaned)
    connect_args: dict = {}

    # Replace postgresql:// or postgres:// with postgresql+asyncpg://
    scheme = parsed.scheme
    if scheme in ("postgresql", "postgres"):
        scheme = "postgresql+asyncpg"
    elif scheme == "sqlite":
        scheme = "sqlite+aiosqlite"

    # Handle SSL for Aiven or cloud PostgreSQL
    query_params = parse_qs(parsed.query)
    ssl_param = query_params.pop("ssl", None) or query_params.pop("sslmode", None)
    
    if scheme.startswith("postgresql+asyncpg"):
        # For Aiven PostgreSQL, default to requiring SSL unless explicitly disabled
        require_ssl = (
            (ssl_param and ssl_param[0] in ("require", "verify-ca", "verify-full"))
            or DB_SSL_MODE in ("require", "verify-ca", "verify-full")
            or "aivencloud.com" in parsed.netloc
        )
        if require_ssl:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_ctx

    new_query = urlencode(query_params, doseq=True)
    clean_url = urlunparse((scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    return clean_url, connect_args


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        db_url, connect_args = normalize_database_url(DATABASE_URL)
        engine_kwargs = {
            "echo": False,
            "future": True,
            "connect_args": connect_args,
        }

        # Connection pooling (only applicable to network databases, not in-memory sqlite)
        if "sqlite" not in db_url:
            engine_kwargs.update({
                "pool_size": DB_POOL_SIZE,
                "max_overflow": DB_MAX_OVERFLOW,
                "pool_timeout": DB_POOL_TIMEOUT,
                "pool_recycle": DB_POOL_RECYCLE,
                "pool_pre_ping": True,
            })

        _engine = create_async_engine(db_url, **engine_kwargs)
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        logger.info(f"Initialized async database engine for scheme: {db_url.split('://')[0]}")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        get_engine()
    return _session_factory  # type: ignore


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an isolated async database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> tuple[bool, str]:
    """Pings database to verify connectivity for /ready endpoint."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "connected"
    except Exception as e:
        logger.warning(f"Database readiness check failed: {e}")
        return False, str(e)


async def close_database():
    """Graceful shutdown of database pool."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Closed database engine connection pool.")
