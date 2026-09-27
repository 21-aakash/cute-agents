from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base
from services.config import settings

logger = logging.getLogger(__name__)


def create_resilient_engine():
    db_url = settings.database_url
    if not db_url.startswith("sqlite"):
        try:
            test_engine = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 2})
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Connected to PostgreSQL database at %s", db_url.split("@")[-1] if "@" in db_url else db_url)
            return test_engine
        except Exception as e:
            logger.warning("PostgreSQL unreachable at %s (%s). Falling back to local SQLite database.", db_url, e)

    sqlite_url = "sqlite:///./careerops.db"
    eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    return eng


engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully on %s", engine.url)
    except Exception as e:
        logger.warning("Could not auto-create database tables on startup: %s", e)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
