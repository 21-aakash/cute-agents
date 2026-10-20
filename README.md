# onion-agents
### Curated Collection of Autonomous AI System Paradigms

<p align="center">
  <img src="./assets/banner.jpg" alt="Family of Cute Onion AI Agents Mascot" width="100%" />
</p>

---

A curated, production-grade monorepo featuring specialized AI agent architectures, multi-agent workflows, memory sidecars, and self-optimizing pipelines demonstrating foundational AI system paradigms.

---

## 🧅 Agent Kits & System Paradigms

| Paradigm | Agent Kit | Architectural Paradigm | Core Technologies | Description |
|---|---|---|---|---|
| **01** | **[Refundbot](./Refundbot)** | **Deterministic Guardrail & Tool-Calling** | Python, FastAPI, SQLite / PostgreSQL | Customer service and refund decision engine with policy evaluation, fraud scoring, and immutable audit trails. |
| **02** | **[Research Assistant (`b-research-agent`)](./b-research-agent)** | **Multi-Agent Directed Graph (DAG)** | LangGraph, FastAPI, Qdrant Vector DB, React 18 | Autonomous multi-agent pipeline: Planner ➔ Research ➔ Writer ➔ Critic with human-in-the-loop verification, evaluation dashboard, and voice todo notes. |
| **03** | **[Agent Memory Manager](./agent-memory-manager)** | **External Memory Companion & Sidecar** | Python, Event-driven Memory Sidecar | Dedicated companion agent tracking execution errors, environmental drift, and delivering proactive memory reminders across long-horizon tasks. |
| **04** | **[Self-Evaluation Agent](./self-evaluation-agent)** | **3-Tier Automated Evaluation Pipeline** | Python, LLM-as-a-Judge, Scikit-learn | Multi-layer testing system: Layer 1 (Deterministic Checks) ➔ Layer 2 (LLM-as-a-Judge) ➔ Layer 3 (Human Review Loops) with statistical significance regression testing. |
| **05** | **[DSPy Self-Tuning Agent Studio](./dspy-self-tuning-agent)** | **Algorithmic Prompt Optimization & Multi-Agent Cascade** | DSPy 3.4.1, Groq, BootstrapFewShot, FastAPI | Dual-paradigm console: **Paradigm 5A** heals model swaps/data drift cutting costs 15x; **Paradigm 5B** jointly compiles 3-node multi-agent pipelines to eliminate cascading domino failures. |

---

## 📂 Monorepo Structure

```
onion-agents/
├── assets/
│   └── banner.jpg               # Cute onion mascot family banner
├── Refundbot/                   # Paradigm 01: Policy guardrails & transaction decision engine
│   ├── AGENTS.md                # Agent specification & tool contracts
│   └── readme.md
├── b-research-agent/            # Paradigm 02: Multi-agent LangGraph research & todo system
│   ├── AGENTS.md                # Multi-agent graph specification
│   ├── api/                     # FastAPI backend & LangGraph runner
│   ├── ui/                      # React 18 + Vite frontend
│   └── readme.md
├── agent-memory-manager/        # Paradigm 03: Memory companion & error sidecar
│   ├── AGENTS.md                # Memory companion specification
│   └── readme.md
├── self-evaluation-agent/       # Paradigm 04: 3-tier automated LLM evaluation pipeline
│   ├── readme.md                # Architecture guide & regression testing suite
│   └── evaluation/              # Deterministic & LLM-as-a-judge evaluators
├── dspy-self-tuning-agent/      # Paradigm 05: DSPy optimization & multi-agent cascade studio
│   ├── agent/                   # DSPy signatures, datasets, evaluators & multi-agent pipeline
│   ├── web/                     # Dual-mode interactive console (Vintage Beige + Navy Blue)
│   ├── server.py                # FastAPI simulation backend with live Groq inference
│   ├── DSPY_FOUNDATIONS.md      # Core DSPy theory & framework comparison
│   ├── USE_CASE_AND_ARCHITECTURE.md # Dispute engine architecture guide
│   ├── PRODUCTION_FAILURE_MODES.md  # 5 production LLM failure classes
│   ├── LINKEDIN_POST.md         # Thought leadership post on prompt lifecycle
│   └── README.md
├── AGENTS.md                    # Monorepo agent directory & standards
└── README.md                    # Main overview & deployment guide
```

---

## 🚀 Independent Deployment Guide

Each agent is decoupled and can be deployed individually from this monorepo:

### 1. Render / Railway / Fly.io / Vercel
Set the **Root Directory** (or **Base Directory**) in your service settings:
* **Refundbot API**: `Refundbot`
* **Research Assistant Backend**: `b-research-agent`
* **Research Assistant UI**: `b-research-agent/ui`
* **DSPy Studio Server**: `dspy-self-tuning-agent`

### 2. Docker Containers
Build images directly targeting each agent directory:
```bash
# Build Refundbot
docker build -t onion-agents/refundbot ./Refundbot

# Build Research Agent API
docker build -t onion-agents/research-agent ./b-research-agent

# Build DSPy Self-Tuning Studio
docker build -t onion-agents/dspy-studio ./dspy-self-tuning-agent
```

### 3. GitHub Actions CI/CD
Path-based triggers ensure deployments only execute when the targeted agent changes:
```yaml
name: Deploy DSPy Studio
on:
  push:
    paths:
      - 'dspy-self-tuning-agent/**'
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying DSPy Self-Tuning Agent Studio..."
```

---

## 📄 License
MIT
