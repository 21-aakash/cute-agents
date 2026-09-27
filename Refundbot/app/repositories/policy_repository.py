"""
Return Policy repository - Data access layer for return policies.
"""
from typing import Optional, List
from sqlalchemy import select
from learning.code_manual.Refundbot.app import database
from learning.code_manual.Refundbot.app.models import ReturnPolicy


class PolicyRepository:
    """Repository for ReturnPolicy CRUD operations"""
    
    @staticmethod
    async def get_by_category(category: str) -> Optional[ReturnPolicy]:
        """Fetch return policy by product category"""
        async with database.async_session_factory() as session:
            stmt = select(ReturnPolicy).where(ReturnPolicy.category == category)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all() -> List[ReturnPolicy]:
        """Fetch all return policies"""
        async with database.async_session_factory() as session:
            stmt = select(ReturnPolicy)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    @staticmethod
    async def create(policy: ReturnPolicy) -> ReturnPolicy:
        """Create new return policy"""
        async with database.async_session_factory() as session:
            session.add(policy)
            await session.commit()
            await session.refresh(policy)
            return policy
