"""
Seed script to populate database with initial data.
Uses SQLAlchemy models for type safety and validation.

Usage:
    python seed_db.py
"""
import asyncio
import sys
from datetime import datetime

# Add app to path
sys.path.insert(0, '.')

from learning.code_manual.Refundbot.app import database
from learning.code_manual.Refundbot.app.database import init_db_engine, get_session, Base
from learning.code_manual.Refundbot.app.models import Order, ReturnPolicy, Refund


async def seed_return_policies():
    """Insert return policies for product categories"""
    policies = [
        ReturnPolicy(
            category="Electronics",
            return_window_days=30,
            conditions="Item must be in original packaging with all accessories",
            restocking_fee=10.0,
            refund_method="Original payment method"
        ),
        ReturnPolicy(
            category="Apparel",
            return_window_days=60,
            conditions="Item must be unworn with original tags",
            restocking_fee=0.0,
            refund_method="Original payment method or store credit"
        ),
        ReturnPolicy(
            category="Home",
            return_window_days=90,
            conditions="Item must be unused and in original packaging",
            restocking_fee=5.0,
            refund_method="Original payment method"
        ),
        ReturnPolicy(
            category="Books",
            return_window_days=45,
            conditions="Item must be in resellable condition",
            restocking_fee=0.0,
            refund_method="Original payment method or store credit"
        ),
        ReturnPolicy(
            category="Furniture",
            return_window_days=30,
            conditions="Item must be unassembled and in original packaging",
            restocking_fee=15.0,
            refund_method="Original payment method"
        ),
    ]
    
    async with database.async_session_factory() as session:
        for policy in policies:
            session.add(policy)
        
        try:
            await session.commit()
            print(f"✅ Inserted {len(policies)} return policies")
        except Exception as e:
            print(f"⚠️  Return policies may already exist: {e}")
            await session.rollback()


async def seed_orders():
    """Insert sample orders"""
    orders = [
        Order(
            order_id="ORD-12345",
            customer_name="John Doe",
            customer_email="john.doe@email.com",
            total=1299.99,
            status="delivered",
            created_at=datetime(2026, 7, 15, 10, 30, 0),
            updated_at=datetime(2026, 7, 15, 10, 30, 0),
            items=[
                {"item_id": "ITEM-001", "name": "Laptop", "price": 999.99, "category": "Electronics", "quantity": 1},
                {"item_id": "ITEM-002", "name": "Mouse", "price": 29.99, "category": "Electronics", "quantity": 1},
                {"item_id": "ITEM-003", "name": "Keyboard", "price": 79.99, "category": "Electronics", "quantity": 1}
            ],
            shipping_address={
                "street": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
                "country": "USA"
            }
        ),
        Order(
            order_id="ORD-67890",
            customer_name="Jane Smith",
            customer_email="jane.smith@email.com",
            total=45.99,
            status="shipped",
            created_at=datetime(2026, 7, 10, 14, 20, 0),
            updated_at=datetime(2026, 7, 10, 14, 20, 0),
            items=[
                {"item_id": "ITEM-101", "name": "T-Shirt", "price": 25.99, "category": "Apparel", "quantity": 1},
                {"item_id": "ITEM-102", "name": "Hat", "price": 19.99, "category": "Apparel", "quantity": 1}
            ],
            shipping_address={
                "street": "456 Oak Ave",
                "city": "Austin",
                "state": "TX",
                "zip": "78701",
                "country": "USA"
            }
        ),
        Order(
            order_id="ORD-99999",
            customer_name="Bob Wilson",
            customer_email="bob.wilson@email.com",
            total=599.99,
            status="cancelled",
            created_at=datetime(2026, 7, 1, 9, 15, 0),
            updated_at=datetime(2026, 7, 1, 9, 15, 0),
            items=[
                {"item_id": "ITEM-201", "name": "Headphones", "price": 599.99, "category": "Electronics", "quantity": 1}
            ],
            shipping_address={
                "street": "789 Pine Rd",
                "city": "Seattle",
                "state": "WA",
                "zip": "98101",
                "country": "USA"
            }
        ),
        Order(
            order_id="ORD-11111",
            customer_name="Alice Johnson",
            customer_email="alice.j@email.com",
            total=299.97,
            status="delivered",
            created_at=datetime(2026, 7, 5, 16, 45, 0),
            updated_at=datetime(2026, 7, 5, 16, 45, 0),
            items=[
                {"item_id": "ITEM-301", "name": "Desk Lamp", "price": 89.99, "category": "Home", "quantity": 1},
                {"item_id": "ITEM-302", "name": "Office Chair", "price": 149.99, "category": "Furniture", "quantity": 1},
                {"item_id": "ITEM-303", "name": "Notebook Set", "price": 59.99, "category": "Books", "quantity": 1}
            ],
            shipping_address={
                "street": "321 Elm St",
                "city": "Portland",
                "state": "OR",
                "zip": "97201",
                "country": "USA"
            }
        ),
        Order(
            order_id="ORD-22222",
            customer_name="Charlie Brown",
            customer_email="charlie.b@email.com",
            total=899.98,
            status="pending",
            created_at=datetime(2026, 7, 18, 11, 0, 0),
            updated_at=datetime(2026, 7, 18, 11, 0, 0),
            items=[
                {"item_id": "ITEM-401", "name": "Gaming Monitor", "price": 449.99, "category": "Electronics", "quantity": 1},
                {"item_id": "ITEM-402", "name": "Mechanical Keyboard", "price": 179.99, "category": "Electronics", "quantity": 1},
                {"item_id": "ITEM-403", "name": "Gaming Mouse", "price": 89.99, "category": "Electronics", "quantity": 1},
                {"item_id": "ITEM-404", "name": "Mouse Pad", "price": 29.99, "category": "Electronics", "quantity": 1}
            ],
            shipping_address={
                "street": "555 Maple Dr",
                "city": "Denver",
                "state": "CO",
                "zip": "80202",
                "country": "USA"
            }
        )
    ]
    
    async with database.async_session_factory() as session:
        for order in orders:
            session.add(order)
        
        try:
            await session.commit()
            print(f"✅ Inserted {len(orders)} sample orders")
        except Exception as e:
            print(f"⚠️  Orders may already exist: {e}")
            await session.rollback()


async def seed_refunds():
    """Insert sample refunds (optional)"""
    refunds = [
        Refund(
            refund_id="RFD-00001",
            order_id="ORD-12345",
            item_id="ITEM-002",
            amount=29.99,
            reason="Item not needed",
            status="approved",
            requested_by="customer",
            created_at=datetime(2024, 1, 20, 10, 0, 0),
            processed_at=datetime(2024, 1, 20, 10, 5, 0)
        )
    ]
    
    async with database.async_session_factory() as session:
        for refund in refunds:
            session.add(refund)
        
        try:
            await session.commit()
            print(f"✅ Inserted {len(refunds)} sample refunds")
        except Exception as e:
            print(f"⚠️  Refunds may already exist: {e}")
            await session.rollback()


async def create_tables():
    """Create all database tables"""
    print("📦 Creating database tables...")
    
    async with database.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Tables created")


async def verify_data():
    """Verify seeded data"""
    print("\n📊 Verification:")
    
    from sqlalchemy import select, func
    
    async with database.async_session_factory() as session:
        # Count return policies
        result = await session.execute(select(func.count()).select_from(ReturnPolicy))
        policy_count = result.scalar()
        print(f"  Return Policies: {policy_count}")
        
        # Count orders
        result = await session.execute(select(func.count()).select_from(Order))
        order_count = result.scalar()
        print(f"  Orders: {order_count}")
        
        # Count refunds
        result = await session.execute(select(func.count()).select_from(Refund))
        refund_count = result.scalar()
        print(f"  Refunds: {refund_count}")
        
        # Show sample orders
        print("\n📦 Sample Orders:")
        result = await session.execute(
            select(Order.order_id, Order.customer_name, Order.total, Order.status)
            .order_by(Order.created_at.desc())
            .limit(5)
        )
        for order in result:
            print(f"  {order.order_id} - {order.customer_name} - ${order.total:.2f} - {order.status}")


async def main():
    """Main seed function"""
    print("🌱 Seeding database...\n")
    
    # Initialize database
    await init_db_engine()
    
    # Create tables
    await create_tables()
    
    print("\n📝 Inserting data...")
    
    # Seed data
    await seed_return_policies()
    await seed_orders()
    await seed_refunds()
    
    # Verify
    await verify_data()
    
    print("\n✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
