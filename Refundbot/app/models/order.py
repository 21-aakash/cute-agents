"""
Order-related database models.
"""
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String, Float, DateTime, JSON, Integer
from learning.code_manual.Refundbot.app.database import Base


class Order(Base):
    """Order table model"""
    __tablename__ = "orders"
    
    order_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    customer_email: Mapped[str] = mapped_column(String(200), index=True)
    total: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), index=True)  # pending, shipped, delivered, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items: Mapped[dict] = mapped_column(JSON)  # JSONB in PostgreSQL
    shipping_address: Mapped[dict] = mapped_column(JSON)


class ReturnPolicy(Base):
    """Return policy table model"""
    __tablename__ = "return_policies"
    
    category: Mapped[str] = mapped_column(String(100), primary_key=True)
    return_window_days: Mapped[int] = mapped_column(Integer)
    conditions: Mapped[str] = mapped_column(String(500))
    restocking_fee: Mapped[float] = mapped_column(Float)
    refund_method: Mapped[str] = mapped_column(String(200))


class Refund(Base):
    """Refund transaction table model"""
    __tablename__ = "refunds"
    
    refund_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(50), index=True)
    item_id: Mapped[str] = mapped_column(String(50))
    amount: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50))  # pending, approved, rejected, completed
    requested_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
