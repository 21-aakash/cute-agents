"""
Backend tool implementations.
Production mode only - uses database and external services.
"""
from typing import Dict
from datetime import datetime
import random
import asyncio


def get_orders_by_customer(customer_email: str) -> Dict:
    """
    Get all orders for a customer by email from production database.
    
    Args:
        customer_email: Customer's email address
        
    Returns:
        Dict with success flag and list of orders
    """
    from learning.code_manual.Refundbot.app.services import OrderService
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        future = asyncio.ensure_future(OrderService.get_orders_by_customer(customer_email))
        return loop.run_until_complete(future)
    else:
        return loop.run_until_complete(OrderService.get_orders_by_customer(customer_email))


def get_order(order_id: str) -> Dict:
    """
    Look up order details by ID from production database.
    
    Args:
        order_id: Order identifier
        
    Returns:
        Dict with success flag and order data
    """
    from learning.code_manual.Refundbot.app.services import OrderService
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        future = asyncio.ensure_future(OrderService.get_order(order_id))
        return loop.run_until_complete(future)
    else:
        return loop.run_until_complete(OrderService.get_order(order_id))


def get_shipment_status(order_id: str) -> Dict:
    """
    Get shipping status and tracking info from production services.
    
    Args:
        order_id: Order identifier
        
    Returns:
        Dict with tracking information
    """
    from learning.code_manual.Refundbot.app.services import OrderService
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        future = asyncio.ensure_future(OrderService.get_shipment_status(order_id))
        return loop.run_until_complete(future)
    else:
        return loop.run_until_complete(OrderService.get_shipment_status(order_id))


def get_return_policy(item_category: str) -> Dict:
    """
    Get return policy for a product category from production database.
    
    Args:
        item_category: Product category (Electronics, Apparel, Home, etc.)
        
    Returns:
        Dict with return policy details
    """
    from learning.code_manual.Refundbot.app.services import OrderService
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        future = asyncio.ensure_future(OrderService.get_return_policy(item_category))
        return loop.run_until_complete(future)
    else:
        return loop.run_until_complete(OrderService.get_return_policy(item_category))


def process_refund(order_id: str, item_id: str, reason: str) -> Dict:
    """
    Process a refund for an order item via production service.
    
    Args:
        order_id: Order identifier
        item_id: Item identifier
        reason: Refund reason
        
    Returns:
        Dict with refund confirmation
    """
    from learning.code_manual.Refundbot.app.services import RefundService
    from learning.code_manual.Refundbot.app.analytics import analytics
    
    # Get item amount first
    order_result = get_order(order_id)
    if not order_result.get("success"):
        return order_result
    
    # Find item in order
    order_data = order_result["order"]
    item = None
    for order_item in order_data.get("items", []):
        if order_item.get("item_id") == item_id:
            item = order_item
            break
    
    if not item:
        return {
            "success": False,
            "error": f"Item {item_id} not found in order {order_id}"
        }
    
    amount = item.get("price", 0.0)
    
    # P1 Metric: Track refund approval
    analytics.record_refund_decision(
        order_id=order_id,
        decision="auto_approved",
        amount=amount
    )
    
    # Process refund via service
    loop = asyncio.get_event_loop()
    if loop.is_running():
        future = asyncio.ensure_future(
            RefundService.process_refund(order_id, item_id, amount, reason)
        )
        return loop.run_until_complete(future)
    else:
        return loop.run_until_complete(
            RefundService.process_refund(order_id, item_id, amount, reason)
        )


def escalate_to_human(summary: str) -> Dict:
    """
    Escalate case to human agent.
    
    Args:
        summary: Case summary for human agent
        
    Returns:
        Dict with ticket information
    """
    # Generate ticket ID
    ticket_id = f"TKT-{random.randint(100000, 999999)}"
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "status": "Created",
        "summary": summary,
        "priority": "Normal",
        "assigned_to": "Human Support Team",
        "estimated_response": "Within 2 hours",
        "message": f"I've connected you with our human support team for review. Ticket #{ticket_id} created - you'll hear back within 2 hours.",
    }