"""
Order repository - Data access layer for orders.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from learning.code_manual.Refundbot.app import database
from learning.code_manual.Refundbot.app.models import Order, Refund


class OrderRepository:
    """Repository for Order CRUD operations"""
    
    @staticmethod
    async def get_by_id(order_id: str) -> Optional[Order]:
        """Fetch order by ID"""
        async with database.async_session_factory() as session:
            stmt = select(Order).where(Order.order_id == order_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_customer_email(email: str, limit: int = 10) -> List[Order]:
        """Fetch orders by customer email"""
        async with database.async_session_factory() as session:
            stmt = select(Order).where(Order.customer_email == email).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def create(order: Order) -> Order:
        """Create new order"""
        async with database.async_session_factory() as session:
            session.add(order)
            await session.commit()
            await session.refresh(order)
            return order
    
    @staticmethod
    async def update_status(order_id: str, new_status: str) -> bool:
        """Update order status"""
        async with database.async_session_factory() as session:
            stmt = (
                update(Order)
                .where(Order.order_id == order_id)
                .values(status=new_status, updated_at=datetime.utcnow())
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
    
    @staticmethod
    async def create_refund(refund: Refund) -> Refund:
        """Create refund record"""
        async with database.async_session_factory() as session:
            session.add(refund)
            await session.commit()
            await session.refresh(refund)
            return refund
