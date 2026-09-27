"""
Shipping Service API client.
"""
import logging
from typing import Dict
from learning.code_manual.Refundbot.app.clients.api_client import get_http_client, generate_request_id
from learning.code_manual.Refundbot.app.config import settings

logger = logging.getLogger(__name__)

# API endpoints (would come from config in production)
SHIPPING_SERVICE_URL = getattr(settings, 'SHIPPING_SERVICE_URL', 'https://api.internal.company.com/shipping')


class ShippingAPIClient:
    """Client for Shipping Tracking Service"""
    
    @staticmethod
    async def get_tracking(order_id: str, api_token: str = None) -> Dict:
        """
        Fetch shipment tracking information.
        
        Args:
            order_id: Order ID to track
            api_token: API authentication token (optional)
        
        Returns:
            Dict with success status and tracking data
        """
        try:
            client = await get_http_client()
            
            headers = {
                "X-Request-ID": generate_request_id()
            }
            
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"
            
            response = await client.get(
                f"{SHIPPING_SERVICE_URL}/v1/tracking/{order_id}",
                headers=headers
            )
            
            if response.status_code == 404:
                return {
                    "success": False,
                    "error": f"No tracking information for order {order_id}"
                }
            
            if response.status_code != 200:
                logger.error(f"Shipping API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": "Shipping service unavailable"
                }
            
            data = response.json()
            
            # Transform API response to standard format
            return {
                "success": True,
                "tracking": {
                    "carrier": data.get("carrier", "Unknown"),
                    "tracking_number": data.get("tracking_number", "N/A"),
                    "status": data.get("status", "unknown"),
                    "estimated_delivery": data.get("estimated_delivery_date", ""),
                    "current_location": data.get("current_location", "In transit")
                }
            }
        
        except Exception as e:
            logger.error(f"Error calling Shipping API: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Failed to fetch tracking data"
            }
