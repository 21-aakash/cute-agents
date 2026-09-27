"""
Shared HTTP client for external API calls.
"""
import httpx
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Shared HTTP client with connection pooling
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """
    Get shared HTTP client with connection pooling.
    Reuses connections for better performance.
    """
    global _http_client
    
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            headers={
                "User-Agent": "RefundBot/1.0",
                "X-Service-Name": "customer-support-agent"
            }
        )
        logger.info("HTTP client initialized with connection pooling")
    
    return _http_client


async def close_http_client() -> None:
    """Close HTTP client and cleanup connections"""
    global _http_client
    
    if _http_client:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client closed")


def generate_request_id() -> str:
    """Generate unique request ID for tracing"""
    return str(uuid.uuid4())
