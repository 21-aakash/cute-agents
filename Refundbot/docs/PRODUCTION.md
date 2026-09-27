# 🚀 Production Deployment Guide

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys
```

## 🗄️ Database Migrations with Alembic

```bash
# Install Alembic
pip install alembic

# Initialize Alembic
alembic init alembic

# Edit alembic.ini - set your database URL
sqlalchemy.url = sqlite+aiosqlite:///./sessions.db

# Create first migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# In production, always run migrations before app start
alembic upgrade head && uvicorn app.main:app
```

### alembic/env.py configuration

```python
from app.session import Base
target_metadata = Base.metadata

# For async engines
from sqlalchemy.ext.asyncio import create_async_engine

async def run_async_migrations():
    connectable = create_async_engine(config.get_main_option("sqlalchemy.url"))
    
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()
```

## 🐳 Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations and start
CMD alembic upgrade head && \
    uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  refundbot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_MODEL=gpt-4o
      - DATABASE_URL=postgresql+asyncpg://user:pass@db/refundbot
    volumes:
      - ./sessions.db:/app/sessions.db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

## 📊 Monitoring & Logging

### Structured Logging

```python
# app/logging_config.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

### Prometheus Metrics

```python
# pip install prometheus-fastapi-instrumentator

from prometheus_fastapi_instrumentator import Instrumentator

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)
```

### Sentry Error Tracking

```python
# pip install sentry-sdk[fastapi]

import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
    environment="production",
)
```

## ⚡ Performance Tuning

### 1. Connection Pooling

```python
# app/session.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Base connections
    max_overflow=40,       # Overflow connections
    pool_pre_ping=True,    # Health check
    pool_recycle=3600,     # Recycle after 1h
)
```

### 2. Query Optimization

```python
# Use eager loading for relationships
stmt = select(SessionModel).options(
    selectinload(SessionModel.messages)
)

# Add indexes
class SessionModel(Base):
    session_id: Mapped[str] = mapped_column(primary_key=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(index=True)  # For cleanup queries
```

### 3. Caching Layer

```python
# pip install redis[hiredis] aioredis

from redis.asyncio import Redis

redis = Redis.from_url("redis://localhost")

async def get_cached_session(session_id: str):
    # Try cache first
    cached = await redis.get(f"session:{session_id}")
    if cached:
        return SessionModel.parse_raw(cached)
    
    # Fall back to DB
    session = await get(session_id)
    if session:
        await redis.setex(
            f"session:{session_id}",
            300,  # 5 min TTL
            session.json()
        )
    return session
```

### 4. Background Tasks

```python
# Use FastAPI BackgroundTasks for non-blocking ops

@app.post("/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    # Handle request
    response = await run_agent(...)
    
    # Cleanup old sessions in background
    background_tasks.add_task(cleanup_old, days=7)
    
    return response
```

## 🔒 Security Checklist

- [x] **Environment variables** - Never commit .env files
- [x] **SQL injection protection** - ORM handles this
- [x] **Prompt injection detection** - Implemented in guardrails.py
- [x] **Rate limiting** - Add with `slowapi` or nginx
- [x] **HTTPS** - Use reverse proxy (nginx/Caddy)
- [x] **Authentication** - Add JWT/OAuth before production
- [x] **Input validation** - Pydantic handles this
- [x] **CORS** - Configure allowed origins

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

## 📈 Scalability

### Horizontal Scaling

```bash
# Run multiple workers
uvicorn app.main:app --workers 4

# Or use Gunicorn with Uvicorn workers
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

### Database Scaling

For production, use PostgreSQL instead of SQLite:

```python
# app/session.py
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db"

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)
```

### Caching Strategy

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────┐
│   FastAPI   │
└──────┬──────┘
       │
┌──────▼──────┐     Hit? → Return
│    Redis    │
└──────┬──────┘
       │ Miss
┌──────▼──────┐
│  PostgreSQL │
└─────────────┘
```

## 🧪 Testing in Production

```bash
# Run health check
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is your refund policy?"}'

# Check metrics (if Prometheus enabled)
curl http://localhost:8000/metrics

# Load testing with hey
hey -n 1000 -c 10 http://localhost:8000/health
```

## 📋 Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Health check endpoint responding
- [ ] Logging configured (structured JSON)
- [ ] Error tracking (Sentry) enabled
- [ ] Metrics (Prometheus) exposed
- [ ] Rate limiting configured
- [ ] CORS policies set
- [ ] HTTPS/TLS configured
- [ ] Backup strategy defined
- [ ] Monitoring alerts configured
- [ ] Load testing completed
- [ ] Documentation updated

## 🚨 Troubleshooting

### Database locked errors
```python
# Increase timeout for SQLite
connect_args={"timeout": 30}

# Or migrate to PostgreSQL for production
```

### High memory usage
```python
# Limit connection pool
pool_size=10
max_overflow=20

# Add session expiry
await cleanup_old(days=1)
```

### Slow queries
```python
# Add indexes
session_id: Mapped[str] = mapped_column(index=True)
updated_at: Mapped[datetime] = mapped_column(index=True)

# Enable query logging
engine = create_async_engine(DATABASE_URL, echo=True)
```

---

**Next Steps:**
1. Set up monitoring dashboard (Grafana + Prometheus)
2. Configure auto-scaling (Kubernetes/ECS)
3. Implement blue-green deployment
4. Add chaos engineering tests
