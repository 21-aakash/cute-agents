"""
Refund service - Business logic for refund processing.
"""
import logging
from typing import Dict
from datetime import datetime
from learning.code_manual.Refundbot.app.repositories import OrderRepository
from learning.code_manual.Refundbot.app.models import Refund
from learning.code_manual.Refundbot.app.cache import cache_delete

logger = logging.getLogger(__name__)


class RefundService:
    """Business logic layer for refund operations"""
    
    @staticmethod
    async def process_refund(
        order_id: str,
        item_id: str,
        amount: float,
        reason: str,
        requested_by: str = "agent"
    ) -> Dict:
        """
        Process a refund with validation and database recording.
        
        Args:
            order_id: Order ID to refund
            item_id: Specific item ID to refund
            amount: Refund amount
            reason: Reason for refund
            requested_by: Who requested (agent/customer/system)
        
        Returns:
            Dict with success status and refund details
        """
        try:
            # Validate order exists
            order = await OrderRepository.get_by_id(order_id)
            if not order:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
            
            # Validate order is not cancelled
            if order.status == "cancelled":
                return {
                    "success": False,
                    "error": "Cannot refund cancelled orders"
                }
            
            # Create refund record
            refund = Refund(
                order_id=order_id,
                item_id=item_id,
                amount=amount,
                reason=reason,
                status="approved",
                requested_by=requested_by,
                created_at=datetime.utcnow(),
                processed_at=datetime.utcnow()
            )
            
            # Save to database
            saved_refund = await OrderRepository.create_refund(refund)
            
            # Invalidate order cache (data changed)
            await cache_delete(f"order:{order_id}")
            
            logger.info(f"Refund processed: {saved_refund.refund_id} for order {order_id}")
            
            return {
                "success": True,
                "refund_id": saved_refund.refund_id,
                "amount": saved_refund.amount,
                "status": saved_refund.status,
                "message": f"Refund of ${amount:.2f} approved for order {order_id}"
            }
        
        except Exception as e:
            logger.error(f"Error processing refund: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Failed to process refund"
            }
