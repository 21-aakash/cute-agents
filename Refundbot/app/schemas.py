"""
Pydantic models for API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Chat request from client."""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    session_id: Optional[str] = Field(None, description="Optional session ID for continuing conversation")
    customer_email: Optional[str] = Field(None, description="Customer email for context")
    order_id: Optional[str] = Field(None, description="Order ID for context")


class ChatResponse(BaseModel):
    """Chat response to client."""
    session_id: str = Field(..., description="Session identifier")
    response: str = Field(..., description="Agent response")


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    message_count: int
    created_at: str
    updated_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    stats: dict
    

class ErrorResponse(BaseModel):
    """Error response."""
    detail: str
    error_code: Optional[str] = None