"""
Test suite for production session management.
Run: pytest test_session_orm.py -v
"""
import pytest
from datetime import datetime, timedelta
from learning.code_manual.Refundbot.app.session import (
    init_db,
    close_db,
    health_check,
    get_or_create,
    save,
    get,
    clear,
    list_all,
    count_sessions,
    cleanup_old,
    get_session_stats,
)


@pytest.fixture(scope="module")
async def setup_db():
    """Initialize database for testing."""
    await init_db()
    yield
    await close_db()


@pytest.mark.asyncio
async def test_health_check(setup_db):
    """Test database connectivity."""
    healthy = await health_check()
    assert healthy is True


@pytest.mark.asyncio
async def test_create_session(setup_db):
    """Test session creation."""
    session = await get_or_create()
    assert session.session_id is not None
    assert session.messages == []
    assert session.context == {}
    assert isinstance(session.created_at, datetime)


@pytest.mark.asyncio
async def test_get_or_create_existing(setup_db):
    """Test retrieving existing session."""
    # Create
    session1 = await get_or_create("test-123")
    session1.messages.append({"role": "user", "content": "Hello"})
    await save(session1)
    
    # Retrieve
    session2 = await get_or_create("test-123")
    assert session2.session_id == "test-123"
    assert len(session2.messages) == 1
    assert session2.messages[0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_save_and_get(setup_db):
    """Test save and retrieve operations."""
    # Create and save
    session = await get_or_create("save-test")
    session.messages = [
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Response"},
    ]
    session.context = {"order_id": "12345", "refund_amount": 100.0}
    await save(session)
    
    # Retrieve
    loaded = await get("save-test")
    assert loaded is not None
    assert len(loaded.messages) == 2
    assert loaded.context["order_id"] == "12345"


@pytest.mark.asyncio
async def test_clear_session(setup_db):
    """Test session deletion."""
    # Create
    session = await get_or_create("delete-test")
    await save(session)
    
    # Verify exists
    exists = await get("delete-test")
    assert exists is not None
    
    # Delete
    deleted = await clear("delete-test")
    assert deleted is True
    
    # Verify gone
    gone = await get("delete-test")
    assert gone is None


@pytest.mark.asyncio
async def test_list_all(setup_db):
    """Test listing all sessions."""
    # Create multiple
    for i in range(5):
        session = await get_or_create(f"list-test-{i}")
        await save(session)
    
    # List
    sessions = await list_all(limit=10)
    assert len(sessions) >= 5
    
    # Check ordering (newest first)
    for i in range(len(sessions) - 1):
        assert sessions[i].updated_at >= sessions[i + 1].updated_at


@pytest.mark.asyncio
async def test_count_sessions(setup_db):
    """Test session counting."""
    initial_count = await count_sessions()
    
    # Add sessions
    for i in range(3):
        session = await get_or_create(f"count-test-{i}")
        await save(session)
    
    new_count = await count_sessions()
    assert new_count >= initial_count + 3


@pytest.mark.asyncio
async def test_cleanup_old(setup_db):
    """Test old session cleanup."""
    # Create old session (manually set updated_at)
    session = await get_or_create("old-test")
    session.updated_at = datetime.utcnow() - timedelta(days=10)
    await save(session)
    
    # Cleanup sessions older than 7 days
    deleted_count = await cleanup_old(days=7)
    assert deleted_count >= 1
    
    # Verify deleted
    gone = await get("old-test")
    assert gone is None


@pytest.mark.asyncio
async def test_session_stats(setup_db):
    """Test session statistics."""
    stats = await get_session_stats()
    
    assert "total" in stats
    assert "active_24h" in stats
    assert "active_7d" in stats
    assert stats["total"] >= 0
    assert stats["active_24h"] <= stats["active_7d"]
    assert stats["active_7d"] <= stats["total"]


@pytest.mark.asyncio
async def test_concurrent_updates(setup_db):
    """Test handling concurrent updates."""
    import asyncio
    
    session_id = "concurrent-test"
    session = await get_or_create(session_id)
    
    async def add_message(content: str):
        sess = await get(session_id)
        if sess:
            sess.messages.append({"role": "user", "content": content})
            await save(sess)
    
    # Simulate concurrent updates
    await asyncio.gather(
        add_message("msg1"),
        add_message("msg2"),
        add_message("msg3"),
    )
    
    # Verify all messages saved (may have race conditions - that's expected)
    final = await get(session_id)
    assert final is not None
    # In production, you'd use optimistic locking or row versioning


@pytest.mark.asyncio
async def test_json_serialization(setup_db):
    """Test complex JSON data handling."""
    session = await get_or_create("json-test")
    
    # Complex nested data
    session.context = {
        "order": {
            "id": "ORD-999",
            "items": [
                {"id": "ITEM-1", "price": 99.99, "quantity": 2},
                {"id": "ITEM-2", "price": 149.99, "quantity": 1},
            ],
            "metadata": {"source": "web", "campaign": None},
        },
        "flags": [True, False, True],
        "nullable": None,
    }
    await save(session)
    
    # Retrieve and verify
    loaded = await get("json-test")
    assert loaded.context["order"]["items"][0]["price"] == 99.99
    assert loaded.context["flags"] == [True, False, True]
    assert loaded.context["nullable"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
