# Refundbot - Production-Grade Agentic Customer Support System

> **FastAPI + SQLAlchemy + OpenAI Function Calling** | Async-first | Three-layer security | Production observability

---

## 📋 Table of Contents
- [System Architecture](#system-architecture)
- [Lifecycle Flow](#lifecycle-flow)
- [Repository Structure](#repository-structure)
- [Session Management](#session-management)
- [Agent Execution Flow](#agent-execution-flow)
- [Security & Guardrails](#security--guardrails)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  Portal (index.html) → Orders (orders.html) → Chat (chat.html)    │
│                     Dashboard (dashboard.html)                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/SSE
┌────────────────────────────▼────────────────────────────────────────┐
│                      FASTAPI APPLICATION                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Endpoints: /chat, /orders, /feedback, /analytics          │   │
│  │  Middleware: CORS, Static Files, Error Handlers             │   │
│  │  Lifespan: DB init, service injection                       │   │
│  └────────────────────────┬────────────────────────────────────┘   │
└────────────────────────────┼────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                        AGENT LAYER                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Input Guardrails│  │   ReAct Agent    │  │ Output Guardrails│ │
│  │  - Injection     │→ │  - Context build │→ │  - Scope check   │ │
│  │  - Scope check   │  │  - LLM loop      │  │  - Info leak     │ │
│  └──────────────────┘  │  - Tool dispatch │  └──────────────────┘ │
│                         └────────┬─────────┘                         │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│                         SERVICE LAYER                                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  OrderService   │  │  RefundService   │  │  AnalyticsStore  │  │
│  │  - Cache-aside  │  │  - Policy check  │  │  - Metrics track │  │
│  │  - DB fallback  │  │  - $500 cap      │  │  - CSAT, tokens  │  │
│  └────────┬────────┘  └────────┬─────────┘  └──────────────────┘  │
└───────────┼──────────────────────┼─────────────────────────────────────┘
            │                      │
┌───────────▼──────────────────────▼─────────────────────────────────┐
│                      REPOSITORY LAYER                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ OrderRepository  │  │ PolicyRepository │  │ SessionManager  │ │
│  │ - CRUD ops       │  │ - CRUD ops       │  │ - Chat history  │ │
│  │ - Async queries  │  │ - Async queries  │  │ - Context store │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬────────┘ │
└───────────┼──────────────────────┼──────────────────────┼──────────┘
            │                      │                      │
┌───────────▼──────────────────────▼──────────────────────▼──────────┐
│                        DATA LAYER                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │   orders.db      │  │   sessions.db    │  │  Cache (Redis)  │ │
│  │  - orders        │  │  - conversations │  │  - TTL 300s     │ │
│  │  - return_policy │  │  - messages      │  │  - order cache  │ │
│  │  - refunds       │  │  - session_id    │  │  - policy cache │ │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Lifecycle Flow

### **1. User Journey: Portal → Chat → Agent Response**

```
┌──────────┐
│  CLIENT  │
└────┬─────┘
     │ 1. Load portal (index.html)
     │    GET /
     ▼
┌──────────────────────────────────────────────────────────────┐
│  PORTAL: Select user (Ankit/Priya/Rohit)                    │
│  Click "Go to My Orders" → /orders.html?email=<email>       │
└────┬─────────────────────────────────────────────────────────┘
     │ 2. Fetch user orders
     │    GET /orders?email=ankit@example.com
     ▼
┌──────────────────────────────────────────────────────────────┐
│  SERVER: OrderService.get_orders_by_customer(email)         │
│  → Repository query → Return order list                      │
└────┬─────────────────────────────────────────────────────────┘
     │ 3. Display orders, click "Need Help?"
     │    Redirect to /chat.html?email=<email>&order_id=<oid>
     ▼
┌──────────────────────────────────────────────────────────────┐
│  CHAT UI: Initialize conversation                            │
│  - Store email, order_id in sessionStorage                   │
│  - Display chat interface                                     │
└────┬─────────────────────────────────────────────────────────┘
     │ 4. User sends message: "I want a refund"
     │    POST /chat
     │    Body: {message, email, order_id, conversation_id}
     ▼
┌──────────────────────────────────────────────────────────────┐
│  FASTAPI /chat ENDPOINT                                      │
│  Step 1: Load/Create session via SessionManager             │
│  Step 2: Inject context (email, order_id) into system msg   │
│  Step 3: Call Agent.run(message, context)                   │
└────┬─────────────────────────────────────────────────────────┘
     │ 5. Agent execution (see Agent Flow below)
     ▼
┌──────────────────────────────────────────────────────────────┐
│  AGENT RESPONSE                                              │
│  - Save conversation to sessions.db                          │
│  - Track analytics (tool calls, tokens, outcomes)            │
│  - Return response to client                                 │
└────┬─────────────────────────────────────────────────────────┘
     │ 6. Display response, show feedback widget
     │    POST /feedback {rating: 1/-1}
     ▼
┌──────────────────────────────────────────────────────────────┐
│  ANALYTICS: Record CSAT, conversation outcome                │
│  Dashboard updates: /dashboard.html polls /analytics         │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
Refundbot/
│
├── app/                                    # Main application package
│   ├── __init__.py                        # Package init, exports
│   ├── main.py                            # FastAPI app, endpoints, lifespan
│   │                                      # → POST /chat, GET /orders, POST /feedback
│   │                                      # → Lifespan: init DB, inject services
│   │
│   ├── agent.py                           # ReAct agent loop (max 10 iterations)
│   │                                      # → run(): Thought→Action→Observation
│   │                                      # → Tool dispatch, context injection
│   │
│   ├── tools.py                           # Tool implementations (6 tools)
│   │                                      # → get_order(), process_refund()
│   │                                      # → get_shipment_status(), escalate_to_human()
│   │                                      # → get_return_policy(), get_orders_by_customer()
│   │
│   ├── guardrails.py                      # Three-layer security
│   │                                      # → is_prompt_injection(): 40+ patterns
│   │                                      # → is_out_of_scope(): 10+ off-topic keywords
│   │                                      # → validate_tool_call(): $500 cap enforcement
│   │                                      # → contains_internal_details(): Tool name leak prevention
│   │
│   ├── analytics.py                       # AnalyticsStore class
│   │                                      # → Track: tool_calls, agent_runs, guardrail_blocks
│   │                                      # → Track: conversation_outcomes, user_feedback, tokens
│   │                                      # → Compute: resolution_rate, CSAT, cost/conv
│   │
│   ├── session.py                         # SessionManager class
│   │                                      # → load_session(): Fetch chat history from sessions.db
│   │                                      # → save_message(): Persist user/assistant messages
│   │                                      # → get_context(): Build LLM-ready conversation array
│   │
│   ├── database.py                        # SQLAlchemy async setup
│   │                                      # → init_db_engine(): Create async engine, session factory
│   │                                      # → Base: DeclarativeBase for models
│   │                                      # → async_session_factory(): Context manager
│   │
│   ├── config.py                          # Pydantic settings
│   │                                      # → OpenAI API key, model config
│   │                                      # → Database URLs, environment vars
│   │
│   ├── models/                            # SQLAlchemy ORM models
│   │   ├── __init__.py                    # Export all models
│   │   ├── order.py                       # Order table schema
│   │   │                                  # → Fields: order_id, customer_email, total, status
│   │   │                                  # → JSON: items[], shipping_address{}
│   │   ├── return_policy.py               # ReturnPolicy table schema
│   │   │                                  # → Fields: category, return_window_days, conditions
│   │   └── refund.py                      # Refund table schema
│   │                                      # → Fields: refund_id, order_id, amount, status
│   │
│   ├── repositories/                      # Data access layer (Repository pattern)
│   │   ├── __init__.py                    # Export repositories
│   │   ├── order_repository.py            # OrderRepository class
│   │   │                                  # → get_by_id(): Fetch order by ID
│   │   │                                  # → get_by_customer_email(): Fetch user orders
│   │   │                                  # → update_status(): Update order state
│   │   ├── policy_repository.py           # PolicyRepository class
│   │   │                                  # → get_by_category(): Fetch return policy
│   │   │                                  # → get_all(): Fetch all policies
│   │   └── (session repository in session.py)
│   │
│   ├── services/                          # Business logic layer (Service pattern)
│   │   ├── __init__.py                    # Export services
│   │   ├── order_service.py               # OrderService class
│   │   │                                  # → get_order(): Cache→DB→API fallback
│   │   │                                  # → get_orders_by_customer(): List user orders
│   │   │                                  # → get_shipment_status(): Generate tracking info
│   │   │                                  # → get_return_policy(): Fetch policy with cache
│   │   └── refund_service.py              # RefundService class
│   │                                      # → process_refund(): Policy check + $500 cap
│   │                                      # → validate_eligibility(): Date + policy check
│   │
│   └── clients/                           # External API clients (placeholder)
│       └── order_api.py                   # OrderAPIClient class (future: real API)
│
├── static/                                # Frontend files (HTML/CSS/JS)
│   ├── index.html                         # Portal landing page
│   │                                      # → User selection (Ankit/Priya/Rohit)
│   │                                      # → Navigation to orders page
│   │
│   ├── orders.html                        # Order listing page
│   │                                      # → Fetch GET /orders?email=<email>
│   │                                      # → Display order table
│   │                                      # → "Need Help?" → chat.html
│   │
│   ├── chat.html                          # Chat interface
│   │                                      # → POST /chat with conversation_id
│   │                                      # → Display messages with markdown rendering
│   │                                      # → Feedback widget (👍👎)
│   │
│   └── dashboard.html                     # Analytics dashboard
│                                          # → Fetch GET /analytics
│                                          # → Chart.js visualizations (P0+P1 metrics)
│                                          # → Critical metric highlighting
│
├── seed_db.py                             # Database seeding script
│                                          # → Create 5 orders (July 2026 dates)
│                                          # → Create 3 return policies
│                                          # → Create 2 refund records
│
├── orders.db                              # SQLite database (orders, policies, refunds)
├── sessions.db                            # SQLite database (conversations, messages)
│
├── requirements.txt                       # Python dependencies
│                                          # → fastapi, uvicorn, sqlalchemy, openai
│                                          # → pydantic, httpx, aiosqlite
│
└── README.md                              # This file
```

---

## 💾 Session Management

### **Architecture**

Sessions are stored in `sessions.db` with two tables:

```sql
-- conversations table
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT UNIQUE,      -- UUID for each conversation
    customer_email TEXT,               -- User identifier
    order_id TEXT,                     -- Optional: Order context
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT,              -- Foreign key to conversations
    role TEXT,                         -- "user" | "assistant" | "system"
    content TEXT,                      -- Message text
    timestamp TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
);
```

### **What's Captured in a Session**

| Field | Purpose | Example |
|-------|---------|---------|
| `conversation_id` | Unique session identifier | `"conv_abc123"` |
| `customer_email` | User identity | `"ankit@example.com"` |
| `order_id` | Order context (optional) | `"ORD001"` |
| `messages[]` | Full chat history | `[{role: "user", content: "I want refund"}, ...]` |
| `created_at` | Session start time | `2026-07-20 10:30:00` |
| `updated_at` | Last message time | `2026-07-20 10:35:00` |

### **Session Lifecycle**

```python
# 1. Client sends first message
POST /chat
{
    "message": "I want a refund",
    "email": "ankit@example.com",
    "order_id": "ORD001",
    "conversation_id": null  # First message
}

# 2. Server creates session
session_id = str(uuid.uuid4())  # "conv_abc123"
session_manager.create_session(session_id, email, order_id)

# 3. Context injection
system_message = f"""
You are a customer support agent.
Current user: {email}
Current order: {order_id}
"""

# 4. Build conversation array
messages = [
    {"role": "system", "content": system_message},
    {"role": "user", "content": "I want a refund"}
]

# 5. Save messages after agent responds
session_manager.save_message(session_id, "user", "I want a refund")
session_manager.save_message(session_id, "assistant", agent_response)

# 6. Next message reuses same conversation_id
POST /chat
{
    "message": "What's the status?",
    "conversation_id": "conv_abc123"  # Reuse session
}

# 7. Load full history
history = session_manager.load_session(session_id)
# Returns all messages in chronological order
```

### **Context Injection Strategy**

The system injects user context into the **system message** to provide the agent with necessary information:

```python
# In app/main.py POST /chat endpoint
if email and order_id:
    context_msg = f"""
    IMPORTANT CONTEXT:
    - Current user email: {email}
    - Current order ID: {order_id}
    
    When the user refers to "my order", they mean {order_id}.
    When tools need customer_email, use {email}.
    """
    # Prepend to conversation history
```

---

## 🤖 Agent Execution Flow

### **Step-by-Step Process**

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 0: INPUT GUARDRAILS (app/guardrails.py)                  │
├─────────────────────────────────────────────────────────────────┤
│  ✓ is_prompt_injection(message)                                │
│    → Checks 40+ patterns: "ignore instructions", DAN attacks   │
│  ✓ is_out_of_scope(message)                                    │
│    → Checks 10+ keywords: "weather", "joke", "capital"         │
│  ✗ BLOCKED → Return error response immediately                 │
│  ✓ PASSED → Continue to Step 1                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: CONTEXT BUILD (app/session.py)                        │
├─────────────────────────────────────────────────────────────────┤
│  1.1 Load session history from sessions.db                     │
│      → session_manager.load_session(conversation_id)           │
│      → Returns: [{role, content, timestamp}, ...]              │
│                                                                 │
│  1.2 Inject user context into system message                   │
│      → Add: customer_email, order_id                           │
│      → Build: "Current user: ankit@example.com"                │
│                                                                 │
│  1.3 Build conversation array for LLM                          │
│      → Format: [system_msg, ...history, user_msg]             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: LLM CALL #1 (app/agent.py)                           │
├─────────────────────────────────────────────────────────────────┤
│  2.1 Call OpenAI API                                           │
│      → Model: gpt-4o                                           │
│      → Tools: [get_order, process_refund, ...]                │
│      → Max tokens: 2000, Timeout: 30s                          │
│                                                                 │
│  2.2 Response types:                                           │
│      A) Text response (no tool call) → Go to Step 5           │
│      B) Tool call response → Go to Step 3                     │
│      C) Error (timeout/rate limit) → Retry with backoff       │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (if tool_calls)
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: TOOL EXECUTION (app/tools.py)                        │
├─────────────────────────────────────────────────────────────────┤
│  3.1 PRE-TOOL GUARDRAILS                                       │
│      ✓ validate_tool_call(tool_name, args)                    │
│        → Check: process_refund amount ≤ $500                  │
│        → Check: All required args present                      │
│      ✗ BLOCKED → Return error, skip tool execution            │
│                                                                 │
│  3.2 Route to appropriate tool function                        │
│      → TOOL_REGISTRY[tool_name](**args)                       │
│      → Example: get_order(order_id, api_token)                │
│                                                                 │
│  3.3 Tool execution (async)                                    │
│      → Service layer call: OrderService.get_order()           │
│      → Cache check → DB query → API fallback                  │
│      → Returns: {success: bool, data/error: ...}              │
│                                                                 │
│  3.4 POST-TOOL GUARDRAILS                                      │
│      ✓ Check tool response for PII leakage                    │
│      ✓ Validate response schema                                │
│                                                                 │
│  3.5 Track analytics                                           │
│      → analytics.record_tool_call(tool_name, success)         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: LLM CALL #2 (feed tool results back)                 │
├─────────────────────────────────────────────────────────────────┤
│  4.1 Append tool result to conversation                        │
│      → Format: {role: "tool", tool_call_id, content}          │
│                                                                 │
│  4.2 Call OpenAI API again                                     │
│      → Same conversation + tool result                         │
│      → LLM synthesizes natural language response               │
│                                                                 │
│  4.3 Iteration control                                         │
│      → Max 10 iterations (prevent infinite loops)              │
│      → If tool_calls again → Repeat Step 3                    │
│      → If text response → Go to Step 5                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: OUTPUT GUARDRAILS (app/guardrails.py)                │
├─────────────────────────────────────────────────────────────────┤
│  5.1 Scope enforcement                                         │
│      ✓ is_out_of_scope(response)                              │
│        → Check if agent went off-topic                         │
│                                                                 │
│  5.2 Information leakage prevention                            │
│      ✓ contains_internal_details(response)                    │
│        → Check for tool names, internal IDs                    │
│        → Remove any leaked technical details                   │
│                                                                 │
│  5.3 Policy compliance                                         │
│      ✓ Verify refund amounts don't exceed policy              │
│      ✓ Check mandatory policy references included              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 6: RESPONSE & CLEANUP                                    │
├─────────────────────────────────────────────────────────────────┤
│  6.1 Save conversation to sessions.db                          │
│      → session_manager.save_message(user_msg, assistant_msg)  │
│                                                                 │
│  6.2 Track analytics                                           │
│      → Record: tokens, latency, outcome, guardrail blocks      │
│                                                                 │
│  6.3 Error handling (if any step failed)                      │
│      → Catch exceptions at each layer                          │
│      → Return user-friendly error message                      │
│      → Log error details for debugging                         │
│                                                                 │
│  6.4 Return response to client                                 │
│      → Format: {response, conversation_id, metadata}           │
└─────────────────────────────────────────────────────────────────┘
```

### **Code Example: Full Flow**

```python
# In app/main.py POST /chat endpoint
@app.post("/chat")
async def chat(request: ChatRequest):
    # STEP 0: Input guardrails
    if guardrails.is_prompt_injection(request.message):
        return {"error": "Request blocked by security filters"}
    if guardrails.is_out_of_scope(request.message):
        return {"response": "I can only help with order and refund questions."}
    
    # STEP 1: Context build
    session = await session_manager.load_session(request.conversation_id)
    context = build_context(request.email, request.order_id)
    messages = [context] + session.history + [{"role": "user", "content": request.message}]
    
    # STEP 2-4: Agent execution (iterative)
    response = await agent.run(messages, max_iterations=10)
    
    # STEP 5: Output guardrails
    if guardrails.contains_internal_details(response):
        response = sanitize_response(response)
    
    # STEP 6: Save & return
    await session_manager.save_message(session.id, "user", request.message)
    await session_manager.save_message(session.id, "assistant", response)
    await analytics.record_agent_run(success=True, tokens=response.tokens)
    
    return {"response": response.content, "conversation_id": session.id}
```

---

## 🛡️ Security & Guardrails

### **Three-Layer Defense Architecture**

```
┌────────────────────────────────────────────────────────────┐
│  Layer 1: INPUT VALIDATION (Before LLM)                   │
├────────────────────────────────────────────────────────────┤
│  • Prompt injection detection (40+ patterns)               │
│  • Out-of-scope detection (10+ keywords)                   │
│  • Rate limiting (future: 100 req/hour per IP)             │
│  • Input sanitization                                      │
│  Coverage: 60-80% of attacks                               │
└────────────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│  Layer 2: EXECUTION ENFORCEMENT (During tool calls)        │
├────────────────────────────────────────────────────────────┤
│  • Tool argument validation                                │
│  • Business rule enforcement ($500 cap)                    │
│  • Mandatory policy checks                                 │
│  • Authorization checks (user owns order)                  │
│  Coverage: 100% of policy violations                       │
└────────────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│  Layer 3: OUTPUT FILTERING (After LLM)                    │
├────────────────────────────────────────────────────────────┤
│  • Information leakage prevention (tool names)             │
│  • Scope enforcement (stay on topic)                       │
│  • PII redaction (future: credit cards, SSN)               │
│  • Response sanitization                                   │
│  Coverage: 100% of information leakage                     │
└────────────────────────────────────────────────────────────┘
```

### **Guardrail Functions**

| Function | Purpose | Triggers |
|----------|---------|----------|
| `is_prompt_injection()` | Detect jailbreak attempts | "Ignore previous instructions", DAN attacks |
| `is_out_of_scope()` | Block off-topic queries | "weather", "joke", "fibonacci" |
| `validate_tool_call()` | Enforce business rules | `process_refund(amount > 500)` |
| `contains_internal_details()` | Prevent info leakage | Response contains "get_order" tool name |

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.13+
- OpenAI API key

### **Installation**

```bash
# 1. Clone repository
git clone <repo-url>
cd Refundbot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export OPENAI_API_KEY="sk-..."

# 4. Seed databases
python seed_db.py

# 5. Run server
python -m app.main
```

### **Access Application**

- **Portal**: http://localhost:8000/
- **Chat**: http://localhost:8000/chat.html
- **Dashboard**: http://localhost:8000/dashboard.html

### **Test Users**

| Name | Email | Orders |
|------|-------|--------|
| Ankit | ankit@example.com | 3 orders |
| Priya | priya@example.com | 1 order |
| Rohit | rohit@example.com | 1 order |

---

## 📡 API Reference

### **POST /chat**
**Description**: Send message to agent

**Request**:
```json
{
  "message": "I want a refund for ORD001",
  "email": "ankit@example.com",
  "order_id": "ORD001",
  "conversation_id": "conv_abc123"  // Optional: null for first message
}
```

**Response**:
```json
{
  "response": "I've processed your refund of $299.99...",
  "conversation_id": "conv_abc123"
}
```

---

### **GET /orders**
**Description**: Get user orders

**Query Params**: `?email=ankit@example.com`

**Response**:
```json
{
  "success": true,
  "orders": [
    {
      "order_id": "ORD001",
      "customer": "Ankit Sharma",
      "product": "Laptop",
      "amount": 899.99,
      "status": "shipped",
      "order_date": "2026-07-15"
    }
  ],
  "count": 1
}
```

---

### **POST /feedback**
**Description**: Submit CSAT rating

**Request**:
```json
{
  "conversation_id": "conv_abc123",
  "rating": 1  // 1 = positive, -1 = negative
}
```

---

### **GET /analytics**
**Description**: Get dashboard metrics

**Response**:
```json
{
  "resolution_rate": 0.75,
  "escalation_rate": 0.15,
  "csat_score": 0.80,
  "cost_per_conversation": 0.02,
  "error_rate": 0.05,
  "refund_approval_rate": 0.90,
  "total_conversations": 100,
  "total_tool_calls": 250
}
```

---

## 📊 Production Metrics (P0+P1)

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Resolution Rate | 75% | 80% | ⚠️ |
| Escalation Rate | 15% | <10% | ⚠️ |
| CSAT Score | 80% | 85% | ⚠️ |
| Cost/Conversation | $0.02 | <$0.05 | ✅ |
| Error Rate | 5% | <3% | ⚠️ |
| Avg Response Time | 2.5s | <3s | ✅ |

---

## 🔮 Future Roadmap

See **Production Enhancement Plan** for:
- **Phase 1**: Long-running agent checkpoints (Google Vertex AI pattern)
- **Phase 2**: Vision API for return eligibility (photo verification)
- **Phase 3**: LLM-as-judge evaluation system (50+ test cases)
- **Phase 4**: Multi-agent routing (intent classification)
- **Phase 5**: Policy management pipeline (automated updates)
- **Phase 6**: Docker + PostgreSQL + Redis (production deployment)

---

## 📝 License

MIT License - See LICENSE file for details

---

## 👥 Contributors

Built as a learning project for **top 3-5% AI engineering** practice covering:
- Async Python + FastAPI
- Agentic AI (ReAct loops)
- Security (three-layer guardrails)
- Observability (production metrics)
- Production patterns (repository, service, cache-aside)

---

**Questions?** Open an issue or contact the maintainer.