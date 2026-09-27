"""
Order Management Service API client.
"""
import logging
from typing import Dict
from learning.code_manual.Refundbot.app.clients.api_client import get_http_client, generate_request_id
from learning.code_manual.Refundbot.app.config import settings

logger = logging.getLogger(__name__)

# API endpoints (would come from config in production)
ORDER_SERVICE_URL = getattr(settings, 'ORDER_SERVICE_URL', 'https://api.internal.company.com/orders')


class OrderAPIClient:
    """Client for Order Management Service"""
    
    @staticmethod
    async def get_order(order_id: str, api_token: str = None) -> Dict:
        """
        Fetch order from Order Management Service.
        
        Args:
            order_id: Order ID to fetch
            api_token: API authentication token (optional)
        
        Returns:
            Dict with success status and order data
        """
        try:
            client = await get_http_client()
            
            headers = {
                "X-Request-ID": generate_request_id()
            }
            
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
            
            response = await client.get(
                f"{ORDER_SERVICE_URL}/v1/orders/{order_id}",
                headers=headers
            )
            
            if response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
            
            if response.status_code != 200:
                logger.error(f"Order API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": "Order service unavailable"
                }
            
            data = response.json()
            
            # Transform API response to standard format
            return {
                "success": True,
                "order": {
                    "order_id": data.get("id", order_id),
                    "customer": data.get("customer", {}).get("name", "Unknown"),
                    "total": data.get("total_amount", 0.0),
                    "status": data.get("status", "unknown"),
                    "date": data.get("created_at", ""),
                    "items": data.get("items", [])
                }
            }
        
        except Exception as e:
            logger.error(f"Error calling Order API: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Failed to fetch order data"
            }
