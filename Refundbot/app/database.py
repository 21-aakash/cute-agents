"""
Database connection and session management.
Centralized database configuration for async PostgreSQL/MySQL.
"""
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from learning.code_manual.Refundbot.app.config import settings
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


# Database engine - created once at module level
engine: AsyncEngine = None
async_session_factory = None


async def init_db_engine(database_url: str = None) -> None:
    """
    Initialize database engine and session factory.
    
    Args:
        database_url: Override default from settings
    """
    global engine, async_session_factory
    
    url = database_url or getattr(settings, 'DATABASE_URL', 'sqlite+aiosqlite:///./sessions.db')
    
    engine = create_async_engine(
        url,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,      # Validate connections before use
        pool_recycle=3600,       # Recycle connections every hour
        echo=False,              # Set True for SQL logging
    )
    
    async_session_factory = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info(f"Database engine initialized: {url.split('@')[-1] if '@' in url else url}")


async def close_db_engine() -> None:
    """Close database engine and cleanup connections"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database engine closed")


async def get_session() -> AsyncSession:
    """
    Get a new database session.
    
    Usage:
        async with get_session() as session:
            result = await session.execute(...)
    """
    if not async_session_factory:
        raise RuntimeError("Database not initialized. Call init_db_engine() first.")
    
    return async_session_factory()
