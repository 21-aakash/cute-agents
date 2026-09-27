"""
FastAPI app with production-grade lifecycle management.

Key features:
- Database initialization on startup (both session DB and order DB)
- HTTP client initialization for external APIs
- Graceful shutdown with connection cleanup
- Background task for session cleanup
- Health check endpoint
- Production mode only
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
from pathlib import Path

from learning.code_manual.Refundbot.app.session import (
    init_db,
    close_db,
    health_check,
    get_or_create,
    save,
    get,
    clear,
    list_all,
    cleanup_old,
    get_session_stats,
)
from learning.code_manual.Refundbot.app.agent import run_agent
from learning.code_manual.Refundbot.app.schemas import (
    ChatRequest,
    ChatResponse,
    SessionInfo,
    HealthResponse,
    ErrorResponse,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.
    
    Startup:
    - Initialize session database
    - Initialize production services
    - Run health checks
    
    Shutdown:
    - Close all database connections
    - Close HTTP client
    - Cleanup resources
    """
    # Startup
    logger.info("🚀 Starting up...")
    
    # Initialize session database
    await init_db()
    
    # Initialize production infrastructure
    logger.info("🔧 Initializing production services...")
    
    # Initialize order database
    from learning.code_manual.Refundbot.app.database import init_db_engine
    await init_db_engine()
    
    # HTTP client will be initialized on first use (lazy)
    logger.info("✅ Production services ready")
    
    # Health check
    healthy = await health_check()
    if not healthy:
        logger.error("❌ Health check failed on startup!")
        raise RuntimeError("Database not available")
    
    logger.info("✅ Application ready")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    
    # Close session database
    await close_db()
    
    # Close production services
    logger.info("🔧 Closing production services...")
    
    from learning.code_manual.Refundbot.app.database import close_db_engine
    await close_db_engine()
    
    from learning.code_manual.Refundbot.app.clients import close_http_client
    await close_http_client()
    
    from learning.code_manual.Refundbot.app.cache import close_redis_client
    await close_redis_client()
    
    logger.info("✅ Production services closed")
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Refund Bot API",
    description="Production-grade AI customer support agent",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    logger.info(f"📁 Static files mounted from {STATIC_DIR}")


# Serve UI at root
@app.get("/")
async def serve_ui():
    """Serve the portal landing page."""
    portal_path = STATIC_DIR / "portal.html"
    if portal_path.exists():
        return FileResponse(portal_path)
    return {"message": "RefundBot API", "docs": "/docs"}


@app.get("/orders.html")
async def serve_orders():
    """Serve the orders page."""
    orders_path = STATIC_DIR / "orders.html"
    if orders_path.exists():
        return FileResponse(orders_path)
    raise HTTPException(status_code=404, detail="Orders page not found")


@app.get("/chat.html")
async def serve_chat():
    """Serve the chat page."""
    chat_path = STATIC_DIR / "chat.html"
    if chat_path.exists():
        return FileResponse(chat_path)
    raise HTTPException(status_code=404, detail="Chat page not found")


@app.get("/dashboard.html")
async def serve_dashboard():
    """Serve the dashboard page."""
    dashboard_path = STATIC_DIR / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    raise HTTPException(status_code=404, detail="Dashboard page not found")


# Endpoints
@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
) -> ChatResponse:
    """
    Chat with the AI agent.
    
    Args:
        request: Chat message and optional session ID
        background_tasks: FastAPI background tasks
        
    Returns:
        Agent response with session ID
    """
    try:
        # Get or create session
        session = await get_or_create(request.session_id)
        
        # Add user context to session if provided
        if request.customer_email or request.order_id:
            if not session.context:
                session.context = {}
            if request.customer_email:
                session.context["customer_email"] = request.customer_email
            if request.order_id:
                session.context["order_id"] = request.order_id
            await save(session)
        
        # Run agent (now async!)
        response = await run_agent(session.session_id, request.message)
        
        # Schedule cleanup in background
        background_tasks.add_task(cleanup_old, days=7)
        
        return ChatResponse(
            session_id=session.session_id,
            response=response,
        )
    
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders")
async def get_orders_by_email(customer_email: str):
    """
    Get orders for a customer by email.
    
    Args:
        customer_email: Customer's email address
        
    Returns:
        List of orders for the customer
    """
    try:
        from learning.code_manual.Refundbot.app.tools import get_orders_by_customer
        result = get_orders_by_customer(customer_email)
        return result
    except Exception as e:
        logger.error(f"Failed to get orders: {e}")
        return {"success": False, "error": str(e), "orders": []}


# P0 Metric Endpoints
@app.post("/feedback")
async def record_feedback(session_id: str, rating: str):
    """
    Record user feedback (CSAT).
    
    Args:
        session_id: Session identifier
        rating: positive or negative
        
    Returns:
        Success confirmation
    """
    try:
        if rating not in ["positive", "negative"]:
            raise HTTPException(status_code=400, detail="Rating must be 'positive' or 'negative'")
        
        analytics.record_user_feedback(session_id, rating)
        return {"success": True, "message": "Feedback recorded"}
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/conversation-outcome")
async def record_conversation_outcome(session_id: str, outcome: str):
    """
    Record conversation outcome for resolution rate tracking.
    
    Args:
        session_id: Session identifier
        outcome: resolved, escalated, or abandoned
        
    Returns:
        Success confirmation
    """
    try:
        if outcome not in ["resolved", "escalated", "abandoned"]:
            raise HTTPException(status_code=400, detail="Invalid outcome")
        
        # Get message count from session
        session = await get_or_create(session_id)
        message_count = len(session.messages)
        
        analytics.record_conversation_outcome(session_id, outcome, message_count)
        return {"success": True, "message": "Outcome recorded"}
    except Exception as e:
        logger.error(f"Failed to record outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """
    Get session information.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Session metadata
    """
    session = await get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionInfo(
        session_id=session.session_id,
        message_count=len(session.messages),
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str) -> dict:
    """
    Delete a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success status
    """
    deleted = await clear(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted", "session_id": session_id}


@app.get("/sessions", response_model=list[SessionInfo])
async def list_sessions(limit: int = 100, offset: int = 0) -> list[SessionInfo]:
    """
    List all sessions.
    
    Args:
        limit: Maximum sessions to return
        offset: Pagination offset
        
    Returns:
        List of session information
    """
    sessions = await list_all(limit=limit, offset=offset)
    
    return [
        SessionInfo(
            session_id=s.session_id,
            message_count=len(s.messages),
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        System health status
    """
    db_healthy = await health_check()
    stats = await get_session_stats()
    
    return HealthResponse(
        status="healthy" if db_healthy else "unhealthy",
        database="connected" if db_healthy else "disconnected",
        stats=stats,
    )


@app.post("/admin/cleanup")
async def admin_cleanup(days: int = 7) -> dict:
    """
    Admin endpoint to cleanup old sessions.
    
    Args:
        days: Delete sessions older than this
        
    Returns:
        Cleanup statistics
    """
    count = await cleanup_old(days=days)
    return {
        "status": "completed",
        "deleted_count": count,
        "cutoff_days": days,
    }


@app.get("/analytics")
async def get_analytics():
    """
    Get comprehensive analytics summary.
    
    Returns:
        Agent performance metrics, tool statistics, session data
    """
    from learning.code_manual.Refundbot.app.analytics import get_analytics_summary
    return await get_analytics_summary()


@app.get("/analytics/timeseries")
async def get_timeseries(hours: int = 24):
    """
    Get time-series data for visualization.
    
    Args:
        hours: Number of hours to include (default 24)
    
    Returns:
        Hourly aggregated metrics for charts
    """
    from learning.code_manual.Refundbot.app.analytics import get_time_series_data
    return await get_time_series_data(hours=hours)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )
