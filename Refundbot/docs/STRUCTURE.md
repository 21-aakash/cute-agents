# Production-Ready Project Structure

## 📁 Complete Organization

```
app/
├── __init__.py                     # Package initialization
├── config.py                       # Settings & configuration
├── database.py                     # DB engine & session factory ✅ CREATED
│
├── models/                         # SQLAlchemy ORM models
│   ├── __init__.py                 # Models package ✅ CREATED
│   └── order.py                    # Order, ReturnPolicy, Refund ✅ CREATED
│
├── repositories/                   # Data access layer (CRUD)
│   ├── __init__.py                 # ✅ CREATED
│   ├── order_repository.py         # OrderRepository class
│   └── policy_repository.py        # PolicyRepository class
│
├── services/                       # Business logic layer
│   ├── __init__.py
│   ├── order_service.py            # Order business logic
│   └── refund_service.py           # Refund workflow logic
│
├── clients/                        # External API clients
│   ├── __init__.py
│   ├── api_client.py               # Shared HTTP client
│   ├── order_api.py                # Order microservice client
│   └── shipping_api.py             # Shipping service client
│
├── cache/                          # Redis caching layer
│   ├── __init__.py
│   └── redis_client.py             # Cache get/set operations
│
├── agent.py                        # LLM agentic loop
├── guardrails.py                   # Business rules & validation
├── tools.py                        # Agent tool dispatchers
├── session.py                      # Session persistence
├── models.py                       # Pydantic API models
└── main.py                         # FastAPI application
```

---

## 🎯 Architectural Layers

### **Layer 1: Models** (`app/models/`)
**Purpose:** Database schema definitions

```python
# app/models/order.py
class Order(Base):
    """SQLAlchemy model - maps to `orders` table"""
    __tablename__ = "orders"
    order_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_name: Mapped[str]
    total: Mapped[float]
    # ...
```

**Responsibility:** Schema only - no business logic

---

### **Layer 2: Repositories** (`app/repositories/`)
**Purpose:** Data access operations (CRUD)

```python
# app/repositories/order_repository.py
class OrderRepository:
    """Pure data access - no business logic"""
    
    @staticmethod
    async def get_by_id(order_id: str) -> Optional[Order]:
        async with get_session() as session:
            stmt = select(Order).where(Order.order_id == order_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
    
    @staticmethod
    async def create(order: Order) -> Order:
        async with get_session() as session:
            session.add(order)
            await session.commit()
            return order
```

**Responsibility:** Database queries only - returns models

---

### **Layer 3: Clients** (`app/clients/`)
**Purpose:** External API communication

```python
# app/clients/order_api.py
class OrderAPIClient:
    """REST API client for Order Management Service"""
    
    @staticmethod
    async def get_order(order_id: str, api_token: str) -> Dict:
        client = get_http_client()  # Shared connection pool
        response = await client.get(
            f"{ORDER_SERVICE_URL}/v1/orders/{order_id}",
            headers={"Authorization": f"Bearer {api_token}"}
        )
        return response.json()
```

**Responsibility:** HTTP calls only - returns dicts

---

### **Layer 4: Cache** (`app/cache/`)
**Purpose:** Redis caching for hot data

```python
# app/cache/redis_client.py
async def cache_get(key: str) -> Optional[Any]:
    """Get from Redis, return None if miss"""
    client = await get_redis_client()
    value = await client.get(key)
    return json.loads(value) if value else None

async def cache_set(key: str, value: Any, ttl: int = 300):
    """Set in Redis with TTL"""
    client = await get_redis_client()
    await client.setex(key, ttl, json.dumps(value))
```

**Responsibility:** Cache operations only

---

### **Layer 5: Services** (`app/services/`)
**Purpose:** Business logic - orchestrates repositories, clients, cache

```python
# app/services/order_service.py
class OrderService:
    """
    Business logic layer - coordinates:
    - Cache checking
    - Database queries  
    - API calls
    - Data transformation
    """
    
    @staticmethod
    async def get_order(order_id: str) -> Dict:
        # 1. Check cache first (hot path)
        cached = await cache_get(f"order:{order_id}")
        if cached:
            return cached
        
        # 2. Try database (warm path)
        order_model = await OrderRepository.get_by_id(order_id)
        if order_model:
            result = {
                "success": True,
                "order": {
                    "order_id": order_model.order_id,
                    "customer": order_model.customer_name,
                    "total": order_model.total,
                    "status": order_model.status,
                    "items": order_model.items
                }
            }
            # Cache for next time
            await cache_set(f"order:{order_id}", result, ttl=300)
            return result
        
        # 3. Fall back to API (cold path)
        api_token = get_api_token()
        result = await OrderAPIClient.get_order(order_id, api_token)
        
        if result["success"]:
            await cache_set(f"order:{order_id}", result, ttl=300)
        
        return result
```

**Responsibility:** 
- ✅ Business rules
- ✅ Multi-source orchestration
- ✅ Caching strategy
- ✅ Error handling
- ✅ Data transformation

---

### **Layer 6: Tools** (`app/tools.py`)
**Purpose:** Agent tool interface - calls services

```python
# app/tools.py (SIMPLIFIED)
from app.services.order_service import OrderService

def get_order(order_id: str) -> Dict:
    """
    Agent tool - delegates to service layer.
    This is what the LLM agent calls.
    """
    return await OrderService.get_order(order_id)
```

**Responsibility:** Thin wrapper - routes to services

---

## 🔄 Data Flow Example

**User asks:** "What's the status of order ORD-12345?"

```
┌─────────────┐
│  LLM Agent  │ Decides to call get_order("ORD-12345")
└──────┬──────┘
       │
       v
┌─────────────┐
│ tools.py    │ get_order() → delegates
└──────┬──────┘
       │
       v
┌─────────────────────┐
│ services/           │ OrderService.get_order()
│ order_service.py    │ 
└──────┬─────┬────┬───┘
       │     │    │
       v     v    v
   ┌─────┐ ┌───┐ ┌─────────┐
   │Cache│ │DB │ │API Call │
   └─────┘ └───┘ └─────────┘
     Redis  PostgreSQL  Microservice
```

---

## 🧪 Testing Strategy

### **Unit Tests** (Fast - no I/O)
```python
# Test repositories with in-memory SQLite
# Test services with mocked repositories
# Test clients with httpx mock
```

### **Integration Tests** (Slow - real I/O)
```python
# Test full service → repository → database
# Test API clients against staging environment
```

---

## 📦 Dependencies by Layer

```txt
# Core
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
openai>=1.3.0

# Database
sqlalchemy>=2.0.23
aiosqlite>=0.19.0           # SQLite async driver
asyncpg>=0.29.0             # PostgreSQL async driver

# API Clients
httpx>=0.25.0

# Cache (optional)
redis>=5.0.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

---

## 🚀 Migration Path

**Step 1:** Keep mock data in `tools.py` (current state)

**Step 2:** Add service layer with environment switch:
```python
# app/tools.py
DATA_SOURCE = os.getenv("DATA_SOURCE", "mock")

async def get_order(order_id: str):
    if DATA_SOURCE == "production":
        return await OrderService.get_order(order_id)
    else:
        # Use mock data (current implementation)
        return ORDERS_DB.get(order_id, {})
```

**Step 3:** Deploy with `DATA_SOURCE=production` in .env

---

## ✅ Benefits of This Structure

1. **Separation of Concerns**
   - Each layer has one responsibility
   - Easy to test in isolation
   - Changes don't cascade

2. **Swap Data Sources Easily**
   - Dev: mock data
   - Staging: database
   - Production: hybrid (cache + DB + API)

3. **Testability**
   - Mock repositories in service tests
   - Mock HTTP in client tests
   - Test tools with mock services

4. **Scalability**
   - Add new data sources without touching agent
   - Cache layer improves performance
   - Connection pooling handles load

5. **Maintainability**
   - Find code easily (repository vs service vs client)
   - One file per class
   - Clear dependencies

---

**All foundational files created! Service layer examples in this doc. Ready to implement?** 🚀
