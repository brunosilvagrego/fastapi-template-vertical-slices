import asyncio
import socket
from enum import StrEnum

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


class DatabaseDriver(StrEnum):
    """Enum for supported database drivers."""

    ASYNCPG = "postgresql+asyncpg"
    PSYCOPG = "postgresql+psycopg"


def get_database_url(drivername: str = DatabaseDriver.ASYNCPG) -> URL:
    """Construct the database URL from settings."""
    return URL.create(
        drivername=drivername,
        username=settings.DB_USERNAME,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_DATABASE,
    )


url = get_database_url()

engine = create_async_engine(url)

SessionManager = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


async def db_health_check(timeout_seconds: float = 1.0) -> bool:
    """Check if the database is up. Returns True if the database is healthy,
    False otherwise."""
    try:
        async with SessionManager() as db_session:
            await asyncio.wait_for(
                db_session.execute(text("SELECT 1")),
                timeout=timeout_seconds,
            )
    except TimeoutError, socket.gaierror:
        return False

    return True
