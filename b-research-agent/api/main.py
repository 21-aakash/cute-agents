from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.deps import init_runner
from api.routes import chat, documents, evals, memory, workspaces
from db.session import engine, init_db
from services.logging_config import RequestLoggingMiddleware, configure_logging
from services.vectorstore import VectorStore

logger = logging.getLogger(__name__)

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health() -> dict:
    status = {"postgres": False, "qdrant": False}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        status["postgres"] = True
    except Exception:
        logger.exception("Postgres health check failed")
    try:
        status["qdrant"] = VectorStore().health_ok()
    except Exception:
        logger.exception("Qdrant health check failed")
    status["ok"] = status["postgres"] and status["qdrant"]
    return status


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    logger.info("Starting CareerOps AI API")
    init_db()
    VectorStore()  # ensure collections exist
    init_runner()
    logger.info("Startup complete")
    yield
    logger.info("Shutting down CareerOps AI API")


def create_app() -> FastAPI:
    app = FastAPI(title="CareerOps AI API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8443",
            "http://127.0.0.1:8443",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(workspaces.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(evals.router, prefix="/api/v1")
    app.include_router(memory.router, prefix="/api/v1")
    return app


app = create_app()
