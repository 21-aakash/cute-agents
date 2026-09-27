-- Seed data for Refundbot production database
-- Run this file to populate initial data

-- ============================================================================
-- Return Policies (Product Categories)
-- ============================================================================

INSERT INTO return_policies (category, return_window_days, conditions, restocking_fee, refund_method)
VALUES 
    ('Electronics', 30, 'Item must be in original packaging with all accessories', 10.0, 'Original payment method'),
    ('Apparel', 60, 'Item must be unworn with original tags', 0.0, 'Original payment method or store credit'),
    ('Home', 90, 'Item must be unused and in original packaging', 5.0, 'Original payment method'),
    ('Books', 45, 'Item must be in resellable condition', 0.0, 'Original payment method or store credit'),
    ('Furniture', 30, 'Item must be unassembled and in original packaging', 15.0, 'Original payment method')
ON CONFLICT (category) DO NOTHING;


-- ============================================================================
-- Sample Orders
-- ============================================================================

INSERT INTO orders (
    order_id, 
    customer_name, 
    customer_email, 
    total, 
    status, 
    created_at,
    updated_at,
    items,
    shipping_address
)
VALUES 
    (
        'ORD-12345',
        'John Doe',
        'john.doe@email.com',
        1299.99,
        'delivered',
        '2024-01-15 10:30:00',
        '2024-01-15 10:30:00',
        '[
            {"item_id": "ITEM-001", "name": "Laptop", "price": 999.99, "category": "Electronics", "quantity": 1},
            {"item_id": "ITEM-002", "name": "Mouse", "price": 29.99, "category": "Electronics", "quantity": 1},
            {"item_id": "ITEM-003", "name": "Keyboard", "price": 79.99, "category": "Electronics", "quantity": 1}
        ]'::json,
        '{
            "street": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "zip": "94105",
            "country": "USA"
        }'::json
    ),
    (
        'ORD-67890',
        'Jane Smith',
        'jane.smith@email.com',
        45.99,
        'shipped',
        '2024-02-10 14:20:00',
        '2024-02-10 14:20:00',
        '[
            {"item_id": "ITEM-101", "name": "T-Shirt", "price": 25.99, "category": "Apparel", "quantity": 1},
            {"item_id": "ITEM-102", "name": "Hat", "price": 19.99, "category": "Apparel", "quantity": 1}
        ]'::json,
        '{
            "street": "456 Oak Ave",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
            "country": "USA"
        }'::json
    ),
    (
        'ORD-99999',
        'Bob Wilson',
        'bob.wilson@email.com',
        599.99,
        'cancelled',
        '2024-03-01 09:15:00',
        '2024-03-01 09:15:00',
        '[
            {"item_id": "ITEM-201", "name": "Headphones", "price": 599.99, "category": "Electronics", "quantity": 1}
        ]'::json,
        '{
            "street": "789 Pine Rd",
            "city": "Seattle",
            "state": "WA",
            "zip": "98101",
            "country": "USA"
        }'::json
    ),
    (
        'ORD-11111',
        'Alice Johnson',
        'alice.j@email.com',
        299.97,
        'delivered',
        '2024-06-15 16:45:00',
        '2024-06-15 16:45:00',
        '[
            {"item_id": "ITEM-301", "name": "Desk Lamp", "price": 89.99, "category": "Home", "quantity": 1},
            {"item_id": "ITEM-302", "name": "Office Chair", "price": 149.99, "category": "Furniture", "quantity": 1},
            {"item_id": "ITEM-303", "name": "Notebook Set", "price": 59.99, "category": "Books", "quantity": 1}
        ]'::json,
        '{
            "street": "321 Elm St",
            "city": "Portland",
            "state": "OR",
            "zip": "97201",
            "country": "USA"
        }'::json
    ),
    (
        'ORD-22222',
        'Charlie Brown',
        'charlie.b@email.com',
        899.98,
        'pending',
        '2024-07-18 11:00:00',
        '2024-07-18 11:00:00',
        '[
            {"item_id": "ITEM-401", "name": "Gaming Monitor", "price": 449.99, "category": "Electronics", "quantity": 1},
            {"item_id": "ITEM-402", "name": "Mechanical Keyboard", "price": 179.99, "category": "Electronics", "quantity": 1},
            {"item_id": "ITEM-403", "name": "Gaming Mouse", "price": 89.99, "category": "Electronics", "quantity": 1},
            {"item_id": "ITEM-404", "name": "Mouse Pad", "price": 29.99, "category": "Electronics", "quantity": 1}
        ]'::json,
        '{
            "street": "555 Maple Dr",
            "city": "Denver",
            "state": "CO",
            "zip": "80202",
            "country": "USA"
        }'::json
    )
ON CONFLICT (order_id) DO NOTHING;


-- ============================================================================
-- Sample Refunds (Optional - for testing)
-- ============================================================================

INSERT INTO refunds (
    refund_id,
    order_id,
    item_id,
    amount,
    reason,
    status,
    requested_by,
    created_at,
    processed_at
)
VALUES 
    (
        'RFD-00001',
        'ORD-12345',
        'ITEM-002',
        29.99,
        'Item not needed',
        'approved',
        'customer',
        '2024-01-20 10:00:00',
        '2024-01-20 10:05:00'
    )
ON CONFLICT (refund_id) DO NOTHING;


-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Count records
SELECT 'Return Policies' as table_name, COUNT(*) as count FROM return_policies
UNION ALL
SELECT 'Orders', COUNT(*) FROM orders
UNION ALL
SELECT 'Refunds', COUNT(*) FROM refunds;

-- Show sample data
SELECT order_id, customer_name, total, status, created_at FROM orders ORDER BY created_at DESC LIMIT 5;
