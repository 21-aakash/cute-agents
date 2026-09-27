
GraphState     = live dict moving through nodes (one run)
Checkpoint     = saved copies of that dict (for resume/replay/fork)
ChatTurn       = final user-visible Q&A
ChatRun        = full agent trace for that Q&A
ChatSession    = bucket for many turns + rolling summary


User Alice, Session abc, message "Summarize Project Aurora"
│
├─ HTTP POST /chat  (session_id=abc, X-API-Key=W1)
│
├─ Load short-term: ChatTurns + summary for session abc
│
├─ graph.stream(initial GraphState, config={
│       thread_id: "abc",
│       deps: { tools(W1), indexed_docs, web=true }  ← new per request
│   })
│
│   plan → research → write → critique → persist
│   │      │                              │
│   │      └─ doc_search / web_search     └─ store_memory → Qdrant (workspace W1)
│   │
│   └─ checkpoint save after each node → checkpoints (thread_id=abc)
│
├─ Save ChatRun (plan, evidence, tools, critique…)
├─ Save ChatTurn (query, answer)
│
└─ Return answer to UI

User Bob, Session xyz — same time, same API process
└─ Same singleton graph, different thread_id + deps → isolated



check pointer : LangGraph can save snapshots after each node , napshot includes things like: 

Checkpoint is the most granular state of the agent workflow


- current query, plan, evidence, answer
- where the graph paused (e.g. clarify waiting for user)

Nodes do not call the checkpointer. You attach it at compile time:
workflow.compile(checkpointer=cp)
LangGraph automatically after each step:


plan node runs     → merge update → checkpoint save (thread_id=session_id)
research node runs → merge update → checkpoint save
clarify interrupt  → pause       → checkpoint save (paused state)
...


ResearchGraphRunner (singleton)
  └── self.graph  (compiled with checkpointer attached)

Each request:
  stream_input = { query, session_id, ... }     ← initial state
  config = { thread_id: session_id, deps }    ← per-request deps

  graph.stream(input, config)
       │
       ├─ node reads state, returns partial update
       ├─ LangGraph merges into ResearchGraphState
       └─ checkpointer saves snapshot for thread_id  ← automatic

Postgres/Memory
  └── snapshots keyed by session_id






Three “memory” layers in your project


1. LangGraph checkpoint : Memory/Postgres , isolated by seesion id 

2. Short-term chat context : Postgres ChatTurn + ChatSession.summary , si: session id 

3. Long-term memory (findings) : Qdrant memory collection . workspace_id (not session) 


Workspace = knowledge base boundary (uploaded docs, Qdrant memory, API key)
Session = one chat thread inside that workspace
Many sessions per workspace ✓
Many workspaces per user ✓ (conceptually)



**LLD for the six prod gaps** — mapped to your `b-research-agent` layout. Snippets are illustrative; not a full implementation.

---

## 1. Postgres checkpoints (replace `memory`)

**Problem:** `MemorySaver` lives in process RAM. Restart → in-flight clarify/resume graphs are gone.

**You already have the hook** in `graph/runner.py`:

```22:47:learning/c-projects/i-agenti-projects-all/b-research-agent/graph/runner.py
def make_checkpointer():
    backend = settings.checkpoint_backend.lower()
    if backend == "memory":
        return MemorySaver()
    # ... PostgresSaver(conn).setup()
```

### LLD

```
Startup (api/main.py lifespan)
  └─ ResearchGraphRunner(checkpointer=make_checkpointer())
       thread_id = session_id  (already in config["configurable"]["thread_id"])

On chat/resume
  └─ graph.stream(..., config)  → state read/written to checkpoint tables
```



### Changes


| Piece    | Action                                                                |
| -------- | --------------------------------------------------------------------- |
| Config   | `CHECKPOINT_BACKEND=postgres` in prod `.env`                          |
| DSN      | Same Postgres as app DB (or separate DB `research_agent_checkpoints`) |
| Tables   | `PostgresSaver.setup()` creates LangGraph checkpoint tables           |
| Pool     | Use one long-lived connection or pool per worker (not per request)    |
| Fallback | Keep memory only for local dev                                        |


```python
# services/checkpointer.py  (extract from runner.py)
@lru_cache
def get_checkpointer():
    if settings.checkpoint_backend == "postgres":
        conn = Connection.connect(dsn, autocommit=True)
        saver = PostgresSaver(conn)
        saver.setup()  # idempotent
        return saver
    return MemorySaver()

# graph/runner.py — singleton at startup, not per request
class ResearchGraphRunner:
    def __init__(self, checkpointer=None):
        cp = checkpointer or get_checkpointer()
        self.graph = build_graph(checkpointer=cp)
```

**Resume flow:** User clarifies → `Command(resume=...)` with same `thread_id=session_id` → graph loads last checkpoint from Postgres.

---



## 2. Alembic migrations (replace `create_all` + ad-hoc `ALTER`)

**Problem:** `init_db()` in `db/session.py` is not versioned; prod deploys can't roll forward/back safely.

### LLD

```
db/
  models.py          ← source of truth (SQLAlchemy)
  alembic/
    env.py           ← imports Base.metadata from db.models
    versions/
      001_initial.py
      002_chat_runs_answer.py
      003_eval_tables.py
      004_langgraph_note.py  (optional: app tables only; LG creates its own)
```



### Flow

```
Deploy pipeline:
  alembic upgrade head   → then start uvicorn
Startup:
  init_db() removed or dev-only
```

```bash
# bootstrap once
uv run alembic init db/alembic
```

```python
# db/alembic/env.py (core)
from db.models import Base
target_metadata = Base.metadata

def run_migrations_online():
    connectable = create_engine(settings.database_url)
    with connectable.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
```

```python
# db/alembic/versions/002_add_chat_run_answer.py
def upgrade():
    op.add_column("chat_runs", sa.Column("answer", sa.Text(), server_default=""))

def downgrade():
    op.drop_column("chat_runs", "answer")
```

**Rule:** Every schema change = new migration file. Never `ALTER` in `init_db()` again.

---



## 3. Auth — SSO, RBAC, rate limits

**Today:** `X-API-Key` → lookup `Workspace.api_key` in `api/deps.py`.

### LLD (layered)

```
Request
  → TLS terminator (Caddy/nginx)
  → RateLimitMiddleware (Redis token bucket per workspace/IP)
  → AuthMiddleware
       ├─ API key path (machines, scripts)     → workspace_id
       └─ JWT/OIDC path (humans via SSO)       → user_id + workspace memberships
  → RBAC dependency
       require_role("member") on /chat, require_role("admin") on /evals/run
  → Route handler
```



### API key (keep for backward compat)

```python
# api/deps.py
def get_workspace(x_api_key: str = Header(...), db: Session = Depends(get_db)):
    ws = db.query(Workspace).filter_by(api_key=x_api_key).first()
    if not ws:
        raise HTTPException(401)
    return ws
```



### SSO (OIDC — e.g. Okta/Google)

```python
# api/auth/oidc.py
def verify_jwt(authorization: str = Header(...)) -> UserClaims:
    token = authorization.removeprefix("Bearer ")
    claims = jwt.decode(token, jwks_client, audience=settings.oidc_audience)
    return UserClaims(sub=claims["sub"], email=claims["email"])

# api/deps.py
def get_actor(
    db: Session = Depends(get_db),
    api_key: str | None = Header(None, alias="X-API-Key"),
    user: UserClaims | None = Depends(optional_oidc),
) -> Actor:
    if api_key:
        return Actor(kind="api_key", workspace=resolve_workspace(api_key, db))
    if user:
        return Actor(kind="user", user=user, workspaces=memberships(db, user.sub))
    raise HTTPException(401)
```



### RBAC

```python
# db/models.py
class WorkspaceMember(Base):
    workspace_id: UUID
    user_id: str          # OIDC sub
    role: str             # viewer | member | admin

def require_role(min_role: str):
    def _dep(actor: Actor = Depends(get_actor), ws_id: UUID = Path(...)):
        if not actor.can(ws_id, min_role):
            raise HTTPException(403)
        return actor
    return _dep

@router.post("/chat")
def chat(..., _: Actor = Depends(require_role("member"))):
    ...
```



### Rate limits

```python
# api/middleware/rate_limit.py  (Redis)
async def rate_limit(workspace_id: str, limit: int = 60, window: int = 60):
    key = f"rl:{workspace_id}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    if count > limit:
        raise HTTPException(429, "Rate limit exceeded")
```

**Phased rollout:** Phase 1 = rate limits + rotate API keys. Phase 2 = OIDC for UI. Phase 3 = RBAC.

---



## 4. Secrets, TLS, reverse proxy

**Problem:** `.ENV` on disk; API on plain HTTP.

### LLD

```
Internet
  → Caddy/nginx (:443 TLS, cert from Let's Encrypt)
       ├─ /api/*  → uvicorn :8000 (internal)
       └─ /*      → UI static (Vite build) or :5173 dev

Secrets:
  K8s Secret / Vault / AWS SM → env vars at container start
  Never commit .env
```

```yaml
# docker-compose.prod.yml (sketch)
services:
  caddy:
    image: caddy:2
    ports: ["443:443"]
    volumes: ["./Caddyfile:/etc/caddy/Caddyfile", "caddy_data:/data"]
  api:
    env_file: []  # inject via orchestrator
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}  # from secret store
      DATABASE_URL: ${DATABASE_URL}
    expose: ["8000"]
```

```caddyfile
# Caddyfile
research.example.com {
    reverse_proxy /api/* api:8000
    root * /srv/ui
    file_server
    header Strict-Transport-Security "max-age=31536000"
}
```

```python
# services/config.py — no secrets in repo
openai_api_key: str = ""  # required from env in prod

@model_validator
def prod_secrets(self):
    if os.getenv("ENV") == "production" and not self.openai_api_key:
        raise ValueError("OPENAI_API_KEY required")
```

---



## 5. v2 — long-running dormancy (ADK-style)

**Today:** Clarify uses `interrupt()` — graph pauses until `/chat/resume`. That is basic dormancy; v2 = hours/days + multi-step workflows.

### LLD

```
Graph node (plan/research)
  → if needs_user OR waiting_external:
       return Command(update={...}, goto=END)   # or interrupt()
       persist "pending_reason" on ChatSession

External resume (hours later)
  POST /sessions/{id}/chat/resume
  → Command(resume={"answer": ...})
  → PostgresSaver loads checkpoint by thread_id=session_id
  → continues from exact node
```

```python
# graph/nodes.py — you already have this pattern
def clarify_node(state):
    user_reply = interrupt({"questions": [...], "original_query": state["query"]})
    return Command(update={"query": enriched}, goto="plan")

# v2 extension: timed / external wake
def wait_for_approval_node(state, config):
    if not state.get("approval_received"):
        interrupt({"type": "approval", "ticket_id": state["ticket_id"]})
    return Command(goto="research")
```

**Requirements for v2:**

- `CHECKPOINT_BACKEND=postgres` (mandatory)
- `ChatSession.status`: `active | waiting_input | waiting_external | completed`
- Optional: job queue (Celery/ARQ) for scheduled wake-ups
- TTL/cleanup job for stale checkpoints

---



## 6. Auto evals on every chat (not only manual batch)

**Today:** Eval runs via `POST /evals/run`. `ChatRun` is persisted in `_persist_chat_result`.

### LLD

```
chat completed
  → _persist_chat_result() saves ChatRun
  → enqueue_eval(chat_run_id)     # non-blocking
       ├─ Tier 1 (sync, cheap): score_agentic_sample(result) → update ChatRun.agentic_scores
       └─ Tier 2 (async queue):  if doc_search used AND sample_hash in 10%:
              RagasEvaluator.score_one(...) → EvalSample row
```

```python
# api/routes/chat.py — after db.commit()
from services.agentic_eval import score_agentic_sample
from services.eval_queue import enqueue_ragas_if_sampled

def _persist_chat_result(..., result: dict):
    run = ChatRun(..., agentic_scores=score_agentic_sample(result))
    db.add(run)
    db.commit()
    enqueue_ragas_if_sampled(run.id, workspace_id)  # BackgroundTasks or Redis queue
    return ChatResponse(...)
```

```python
# services/eval_queue.py
SAMPLE_RATE = 0.10  # 10% of RAG turns get RAGAS

def enqueue_ragas_if_sampled(run_id: UUID, workspace_id: UUID):
    if random.random() > SAMPLE_RATE:
        return
    arq.enqueue("tasks.score_ragas", run_id, workspace_id)

# worker/tasks.py
async def score_ragas(ctx, run_id, workspace_id):
    run = load_chat_run(run_id)
    scores = RagasEvaluator().score_one(run.query, run.answer, run.evidence)
    upsert_eval_sample(run_id, scores)
```

**Dashboard:** Roll up `ChatRun.agentic_scores` hourly + show latest RAGAS batch samples (no need to score 100% of chats).

### DB addition

```python
# db/models.py
class ChatRun(Base):
    ...
    agentic_scores: Mapped[dict | None] = mapped_column(JSONB)  # Tier 1, every run
```

---



## Suggested implementation order


| Phase  | Items                                          | Effort    |
| ------ | ---------------------------------------------- | --------- |
| **P0** | Postgres checkpoints + Alembic                 | ~1 day    |
| **P1** | Docker + Caddy TLS + secrets via env           | ~1 day    |
| **P2** | Auto agentic eval on persist + 10% RAGAS queue | ~1 day    |
| **P3** | Rate limits + API key rotation                 | ~0.5 day  |
| **P4** | OIDC + RBAC                                    | ~2–3 days |
| **P5** | v2 dormancy (session status, external resume)  | ~2 days   |


---




ResearchGraphRunner : singkletone class for all users 


                  ┌─────────────────────────┐
User A ──────────►│  ResearchGraphRunner   │◄────────── User B
(session abc)     │  (single instance)     │           (session xyz)
                  │  • self.graph          │
                  │  • self.llm            │
                  │  • self.vectorstore    │
                  └─────────────────────────┘


ResearchGraphRunner()  ← created once in init_runner()
        │
        ├── User A, session abc  → uses same object
        ├── User B, session xyz  → uses same object
        └── User C, session 123  → uses same object



- Builds the graph once (build_graph(checkpointer=...))
- Injects per-request deps (tools, workspace docs, - web toggle) via config["configurable"]["deps"]
- Uses session_id as thread_id for checkpointing

Without it, every route would duplicate graph setup, config building, and interrupt handling

how multiple users handles : 

User A, session abc → thread_id: abc → checkpoint row for abc
User B, session xyz → thread_id: xyz → checkpoint row for xyz

- Same graph, different threads in checkpoint storage. User A never sees User B’s state.

- Shared across requests: graph, LLM client, embedder, Qdrant client.
- Not shared: session state, tool log, workspace-scoped toolkit.


singleton graph + per-session thread_id + per-request deps 

Per-request deps — how it works
Each chat call builds a new config in _build_config():


def _build_config(..., session_id, workspace_id, indexed_documents, web_search_enabled):
    run_logger = RunLogger()
    tools = ResearchToolkit(self.vectorstore, self.embedder, workspace_id)
    deps = {
        "llm": self.llm,              # shared (from runner)
        "tools": tools,               # NEW per request
        "embedder": self.embedder,    # shared
        "vectorstore": self.vectorstore,  # shared
        "logger": run_logger,         # NEW per request
        "indexed_documents": indexed_documents,  # NEW per request
        "web_search_enabled": web_search_enabled,
    }
    config = {"configurable": {"thread_id": session_id, "deps": deps}}
    return config, tools, run_logger





fetaures needed for real users : 


1. SSO- Single Sign-On
- way to login , just scope of diff users 



2. RBAC
- set role level access to fetaures : 

Viewer — read chats only
Member — chat + upload
Admin — delete workspace, run evals, manage members




3. TLS 

HTTP sends API keys and chat content in plain text on the network.
Encrypt traffic browser ↔ server
Required for production web apps, cookies, SSO
Browsers flag HTTP as insecure

4. Reverse Proxy 
Why you’d add it:

Terminate TLS (handle HTTPS certs)
Route /api → backend, / → UI static files
Rate limiting, IP blocking, request size limits
Hide internal ports (8000 not exposed directly)
5. secret management : 

Secrets not in git or Docker images
Injected at runtime (K8s secrets, Vercel env, AWS SM)

