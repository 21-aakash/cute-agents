"""
Order service - Business logic for order operations.
Orchestrates repositories, API clients, and cache.
"""
import logging
from typing import Dict
from learning.code_manual.Refundbot.app.repositories import OrderRepository, PolicyRepository
from learning.code_manual.Refundbot.app.clients import OrderAPIClient
from learning.code_manual.Refundbot.app.cache import cache_get, cache_set

logger = logging.getLogger(__name__)


class OrderService:
    """
    Business logic layer for orders.
    Implements cache-aside pattern with database fallback and API fallback.
    """
    
    @staticmethod
    async def get_order(order_id: str, api_token: str = None) -> Dict:
        """
        Get order with multi-tier lookup: Cache → Database → API
        
        Args:
            order_id: Order ID to fetch
            api_token: Optional API token for external service calls
        
        Returns:
            Dict with success status and order data
        """
        cache_key = f"order:{order_id}"
        
        # 1. Try cache first (hot path - fastest)
        cached = await cache_get(cache_key)
        if cached:
            logger.debug(f"Cache hit for order {order_id}")
            return cached
        
        # 2. Try database (warm path - local data)
        order_model = await OrderRepository.get_by_id(order_id)
        if order_model:
            logger.debug(f"Database hit for order {order_id}")
            
            result = {
                "success": True,
                "order": {
                    "order_id": order_model.order_id,
                    "customer": order_model.customer_name,
                    "total": order_model.total,
                    "status": order_model.status,
                    "date": order_model.created_at.strftime("%Y-%m-%d"),
                    "items": order_model.items
                }
            }
            
            # Cache for next time (5 minute TTL)
            await cache_set(cache_key, result, ttl=300)
            return result
        
        # 3. Fallback to external API (cold path - remote call)
        logger.debug(f"API fallback for order {order_id}")
        result = await OrderAPIClient.get_order(order_id, api_token)
        
        # Cache successful API responses
        if result.get("success"):
            await cache_set(cache_key, result, ttl=300)
        
        return result
    
    @staticmethod
    async def get_return_policy(item_category: str) -> Dict:
        """
        Get return policy with cache and database lookup.
        
        Args:
            item_category: Product category (e.g., "Electronics", "Apparel")
        
        Returns:
            Dict with success status and policy data
        """
        cache_key = f"policy:{item_category}"
        
        # Check cache
        cached = await cache_get(cache_key)
        if cached:
            return cached
        
        # Query database
        policy = await PolicyRepository.get_by_category(item_category)
        
        if not policy:
            return {
                "success": False,
                "error": f"No return policy found for category: {item_category}"
            }
        
        result = {
            "success": True,
            "policy": {
                "category": policy.category,
                "return_window_days": policy.return_window_days,
                "conditions": policy.conditions,
                "restocking_fee": policy.restocking_fee,
                "refund_method": policy.refund_method
            }
        }
        
        # Cache with longer TTL (policies rarely change)
        await cache_set(cache_key, result, ttl=3600)
        return result
    
    @staticmethod
    async def get_orders_by_customer(customer_email: str) -> Dict:
        """
        Get all orders for a customer by email.
        
        Args:
            customer_email: Customer's email address
        
        Returns:
            Dict with success flag and list of orders
        """
        # Query database for all orders matching email
        orders = await OrderRepository.get_by_customer_email(customer_email)
        
        if not orders:
            return {
                "success": False,
                "error": f"No orders found for {customer_email}",
                "orders": []
            }
        
        # Convert to dict format
        order_list = [
            {
                "order_id": order.order_id,
                "customer": order.customer_name,
                "customer_email": order.customer_email,
                "product": order.items[0]["name"] if order.items else "N/A",
                "amount": order.total,
                "status": order.status,
                "order_date": order.created_at.strftime("%Y-%m-%d"),
                "items": order.items
            }
            for order in orders
        ]
        
        return {
            "success": True,
            "orders": order_list,
            "count": len(order_list)
        }
    
    @staticmethod
    async def get_shipment_status(order_id: str) -> Dict:
        """
        Get shipping status and tracking info for an order.
        
        Args:
            order_id: Order identifier
        
        Returns:
            Dict with tracking information
        """
        # Get order first
        order_model = await OrderRepository.get_by_id(order_id)
        
        if not order_model:
            return {
                "success": False,
                "error": f"Order {order_id} not found"
            }
        
        # Generate tracking info based on order status
        status_map = {
            "pending": {
                "status": "Order Received",
                "location": "Processing Center",
                "estimated_delivery": "Processing"
            },
            "shipped": {
                "status": "In Transit",
                "location": "Distribution Hub",
                "estimated_delivery": "2-3 business days"
            },
            "delivered": {
                "status": "Delivered",
                "location": "Customer Address",
                "estimated_delivery": "Completed"
            },
            "cancelled": {
                "status": "Cancelled",
                "location": "N/A",
                "estimated_delivery": "N/A"
            }
        }
        
        tracking_info = status_map.get(order_model.status, status_map["pending"])
        
        return {
            "success": True,
            "tracking": {
                "order_id": order_id,
                "status": tracking_info["status"],
                "location": tracking_info["location"],
                "estimated_delivery": tracking_info["estimated_delivery"],
                "last_updated": order_model.updated_at.strftime("%Y-%m-%d %H:%M")
            }
        }

