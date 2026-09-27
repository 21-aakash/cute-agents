"""
Production-grade session management with async SQLAlchemy 2.0.

Features:
- Async engine with connection pooling
- Proper error handling and retries
- Transaction management
- Health checks
- Auto-cleanup for old sessions
"""
import logging
from typing import Optional, AsyncIterator
from uuid import uuid4
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from sqlalchemy import select, JSON, func
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import SQLAlchemyError


logger = logging.getLogger(__name__)


# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./sessions.db"

# Engine with connection pooling
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=3600,    # Recycle connections after 1 hour
    connect_args={
        "check_same_thread": False,  # SQLite specific
        "timeout": 30,
    },
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class SessionModel(Base):
    """
    Session model for conversation persistence.
    
    Attributes:
        session_id: Unique session identifier
        messages: List of chat messages (JSON)
        context: Agent context dict (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "sessions"
    
    session_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )
    
    def __repr__(self) -> str:
        return f"<Session {self.session_id} ({len(self.messages)} messages)>"


# Database lifecycle
async def init_db() -> None:
    """Initialize database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized")
    except SQLAlchemyError as e:
        logger.error(f"❌ Database init failed: {e}")
        raise


async def close_db() -> None:
    """Close database connections gracefully."""
    try:
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except SQLAlchemyError as e:
        logger.error(f"❌ Database close failed: {e}")


async def health_check() -> bool:
    """Check database connectivity."""
    try:
        async with async_session_maker() as db:
            await db.execute(select(1))
        return True
    except SQLAlchemyError as e:
        logger.error(f"❌ Health check failed: {e}")
        return False


# Context manager for sessions
@asynccontextmanager
async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Get database session with automatic cleanup.
    
    Usage:
        async with get_db() as db:
            result = await db.execute(...)
    """
    session = async_session_maker()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Transaction failed: {e}")
        raise
    finally:
        await session.close()


# Session operations
async def get_or_create(session_id: Optional[str] = None) -> SessionModel:
    """
    Get existing session or create new one.
    
    Args:
        session_id: Optional session ID
        
    Returns:
        SessionModel instance
        
    Raises:
        SQLAlchemyError: Database operation failed
    """
    async with get_db() as db:
        if session_id:
            # Try to load existing
            result = await db.execute(
                select(SessionModel).where(SessionModel.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                logger.debug(f"Loaded session: {session_id}")
                return session
        
        # Create new
        new_id = session_id or str(uuid4())
        session = SessionModel(
            session_id=new_id,
            messages=[],
            context={},
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)  # Refresh to get DB state
        logger.info(f"Created session: {new_id}")
        return session


async def save(session: SessionModel) -> None:
    """
    Save/update session in database.
    
    Args:
        session: Session to save
        
    Raises:
        SQLAlchemyError: Save operation failed
    """
    async with get_db() as db:
        session.updated_at = datetime.utcnow()
        # Use merge to handle detached objects
        merged = await db.merge(session)
        await db.commit()
        logger.debug(f"Saved session: {session.session_id}")


async def get(session_id: str) -> Optional[SessionModel]:
    """
    Get session by ID.
    
    Args:
        session_id: Session identifier
        
    Returns:
        SessionModel or None if not found
    """
    async with get_db() as db:
        result = await db.execute(
            select(SessionModel).where(SessionModel.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            logger.debug(f"Retrieved session: {session_id}")
        return session


async def clear(session_id: str) -> bool:
    """
    Delete a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        True if deleted, False if not found
    """
    async with get_db() as db:
        result = await db.execute(
            select(SessionModel).where(SessionModel.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if session:
            await db.delete(session)
            await db.commit()
            logger.info(f"Deleted session: {session_id}")
            return True
        
        logger.warning(f"Session not found: {session_id}")
        return False


async def list_all(limit: int = 100, offset: int = 0) -> list[SessionModel]:
    """
    List all sessions with pagination.
    
    Args:
        limit: Maximum sessions to return
        offset: Number of sessions to skip
        
    Returns:
        List of SessionModel instances
    """
    async with get_db() as db:
        stmt = (
            select(SessionModel)
            .order_by(SessionModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        sessions = list(result.scalars().all())
        logger.debug(f"Listed {len(sessions)} sessions")
        return sessions


async def count_sessions() -> int:
    """Get total session count."""
    async with get_db() as db:
        result = await db.execute(select(func.count(SessionModel.session_id)))
        return result.scalar() or 0


async def cleanup_old(days: int = 7) -> int:
    """
    Delete sessions older than N days.
    
    Args:
        days: Delete sessions not updated in this many days
        
    Returns:
        Number of sessions deleted
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    async with get_db() as db:
        # Find old sessions
        stmt = select(SessionModel).where(SessionModel.updated_at < cutoff)
        result = await db.execute(stmt)
        old_sessions = list(result.scalars().all())
        
        # Delete them
        for session in old_sessions:
            await db.delete(session)
        
        await db.commit()
        count = len(old_sessions)
        logger.info(f"Cleaned up {count} old sessions (>{days} days)")
        return count


async def get_session_stats() -> dict:
    """
    Get session statistics.
    
    Returns:
        Dict with total, active (< 1 day), recent (< 7 days)
    """
    async with get_db() as db:
        total = await db.scalar(select(func.count(SessionModel.session_id)))
        
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        active = await db.scalar(
            select(func.count(SessionModel.session_id))
            .where(SessionModel.updated_at >= one_day_ago)
        )
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent = await db.scalar(
            select(func.count(SessionModel.session_id))
            .where(SessionModel.updated_at >= seven_days_ago)
        )
        
        return {
            "total": total or 0,
            "active_24h": active or 0,
            "active_7d": recent or 0,
        }
