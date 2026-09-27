# 🤖 My Cute Agents — Multi-Agent Monorepo

A curated monorepo housing autonomous AI agents, multi-agent workflows, and memory companions designed for production-grade evaluation, research, customer service, and long-horizon task execution.

---

## 📂 Repository Structure

```
my-cute-agents/
├── 🤖 Refundbot/              # Automated refund processing & dispute resolution agent
├── 🔬 b-research-agent/        # Multi-agent LangGraph research engine with FastAPI & React UI
├── 🧠 agent-memory-manager/   # Dedicated agent memory companion for long-context retention
└── 📄 README.md               # Monorepo overview & deployment guide
```

---

## 📦 Featured Agents

### 1. [Refundbot](./Refundbot)
An intelligent automated refund processing and dispute adjudication agent.
* **Stack**: Python, FastAPI, SQLite/PostgreSQL, Pytest
* **Features**: Autonomous dispute triage, policy rule matching, fraud detection, and audit trail generation.
* **Quickstart**:
  ```bash
  cd Refundbot
  pip install -r requirements.txt
  python seed_db.py
  uvicorn app.main:app --reload
  ```

### 2. [Research Assistant (`b-research-agent`)](./b-research-agent)
A multi-agent autonomous research pipeline: **Planner → Research → Writer → Critic → Persist**.
* **Stack**: LangGraph, FastAPI, Qdrant Vector DB, PostgreSQL, React 18 + Vite
* **Features**: Multi-hop web search, source verification, automated fact-checking, and interactive evaluation dashboard.
* **Quickstart**:
  ```bash
  cd b-research-agent
  docker-compose up -d  # starts Qdrant & Postgres
  uv sync
  uv run uvicorn api.main:app --reload
  ```

### 3. [Agent Memory Manager (`agent-memory-manager`)](./agent-memory-manager)
A dedicated memory companion architecture inspired by Meta AI research to help agents retain key details and track failed commands during long-horizon tasks.
* **Features**: Smart targeted reminders, environment tracking, and reduced context degradation.

---

## 🚀 Deployment Guide (Monorepo)

Each agent in this monorepo can be deployed independently to your preferred cloud provider.

### Option A: Render / Railway / Fly.io / Vercel
1. Connect this GitHub repository.
2. Under **Service Settings**, set the **Root Directory** (or **Base Directory**) to the agent folder (e.g., `Refundbot` or `b-research-agent`).
3. Set your build and start commands for that specific subfolder.

### Option B: Docker Containers
Build images directly targeting the agent directories:
```bash
# Build Refundbot
docker build -t cute-agents/refundbot ./Refundbot

# Build Research Agent API
docker build -t cute-agents/research-agent ./b-research-agent
```

### Option C: GitHub Actions CI/CD (Path Filters)
Trigger automated deployments only when a specific agent's code changes:
```yaml
name: Deploy Refundbot
on:
  push:
    paths:
      - 'Refundbot/**'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy Refundbot
        run: echo "Deploying Refundbot..."
```

---

## 📜 License
MIT
