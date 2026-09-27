from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()


"""
================================================================================
 RAKUTEN AI — MODEL SELECTION GUIDE FOR AGENTIC APPS
 Sorted: highest intelligence → lowest  |  Costs: approx public rates ($/1M tk)
================================================================================

 TIER  | MODEL ID                        | INTEL  | TOOL CALL | COST I/O       | BEST FOR
 ------+---------------------------------+--------+-----------+----------------+-------------------------------------------
 🔴 S  | gpt-5.4, gpt-5.4-2026-03-05    | ★★★★★ | Native    | $$$$  ~$20/$80 | Top orchestrator; complex multi-step plans
 🔴 S  | gpt-5.2                         | ★★★★★ | Native    | $$$$  ~$15/$60 | Flagship agent brain; nuanced tool routing
 🔴 S  | gpt-5.1, gpt-5.1-chat-latest   | ★★★★★ | Native    | $$$   ~$12/$50 | High-precision orchestration
 🔴 S  | gpt-5, gpt-5-2025-08-07        | ★★★★½ | Native    | $$$   ~$10/$40 | General-purpose orchestrator
 🔴 S  | o4-mini                         | ★★★★★ | Native    | $$$   ~$3/$12* | Deep reasoning: planning, code, math (*+think)
 🟠 A  | o3-mini                         | ★★★★  | Native    | $$    ~$1/$4*  | Budget reasoning; structured output (*+think)
 🟠 A  | gpt-4.1                         | ★★★★  | Native    | $$    ~$2/$8   | Reliable workhorse; 1M ctx; long-doc agents
 🟠 A  | gpt-5-mini, gpt-5-mini-*        | ★★★½  | Native    | $$    ~$1.5/$6 | Fast worker agent; sub-tasks; summarisation
 🟡 B  | gpt-5.4-mini  (⚠ ID=gpt-5.4-mini, labelled "5.4 nano" in registry)
        |                                 | ★★★½  | Native    | $$    ~$1/$4   | Balanced speed/quality for pipelines
 🟡 B  | gpt-4.1-mini                    | ★★★   | Native    | $     ~$0.4/$1.6| High-volume worker nodes; RAG retrieval
 🟡 B  | gpt-4o                          | ★★★   | Native    | $$    ~$5/$15  | Multimodal (vision+tools); image agents
 🟢 C  | gpt-5-nano, gpt-5-nano-*        | ★★½   | Native    | $     ~$0.3/$1.2| Classifier; router; lightweight extraction
 🟢 C  | gpt-5.4-nano  (⚠ ID=gpt-5.4-nano, labelled "5.4 mini" in registry)
       |                                 | ★★½   | Native    | $     ~$0.3/$1 | Nano tasks: intent detect; slot filling
 🟢 C  | gpt-4.1-nano                    | ★★    | Native    | $     ~$0.1/$0.4| Cheapest reliable tool caller; triage/routing
 🟢 C  | gpt-4o-mini                     | ★★    | Native    | $     ~$0.15/$0.6| Economy worker; high-throughput pipelines
 ⚪ D  | gpt-5-chat-latest               | ★★★★  | NONE      | $$$   ~$10/$40 | Conversational UX only — no tool calling
 ⚪ D  | gpt-3.5-turbo                   | ★     | Limited   | $     ~$0.5/$1.5| Legacy fallback only — avoid in new agents

================================================================================
 AGENTIC DESIGN QUICK PICKS
================================================================================
  Orchestrator    →  gpt-5.x series or o4-mini   (intelligence + reliable tool selection)
  Worker/Tools    →  gpt-4.1 or gpt-5-mini       (fast, cheap, solid tool calling)
  Router/Triage   →  gpt-4.1-nano or gpt-4o-mini (sub-cent per call)
  Deep Reasoning  →  o4-mini > o3-mini            (planning/code; NOT for high-freq calls)
  Multimodal      →  gpt-4o                       (vision input support)
  Budget Agent    →  gpt-4.1-mini + gpt-4.1-nano  (combo for cost-sensitive pipelines)

  ⚠  gpt-5-chat-latest has NO tool/function calling — chat UX only
  ⚠  gpt-5.4-mini / gpt-5.4-nano IDs appear SWAPPED vs display names in the registry
  ℹ  Costs are approximate public rates — Rakuten API pricing may differ
================================================================================

================================================================================
 MY AGENT STACK — DECISIONS (for: large tools + large context + planning)
================================================================================

  ROLE          | MODEL          | WHY
  --------------+----------------+------------------------------------------------
  Orchestrator  | gpt-5.1        | ★★★★★ tool routing (matters at 20+ tools);
                |                | fast per step (1-3s) — NOT a thinking model,
                |                | so agent loops don't choke; 40% cheaper than
                |                | gpt-5.4 for ~same quality.
  Planner       | o4-mini        | Best raw reasoning (RLVR-trained); called ONCE
   (one-shot)   |                | upfront for deep decomposition. Worth the 30s
                |                | once; lethal inside an agent loop.
  Workers       | gpt-4.1-mini   | Fast + cheap for summarise / extract / format
   (parallel)   | gpt-5-mini     | sub-tasks. High volume, low cost.
  Router/Triage | gpt-4.1-nano   | Sub-cent per call; intent detect; slot fill.

  REJECTED FOR ORCHESTRATOR (and why):
  --------------------------------------------------------------------------------
  gpt-5.4     →  Top intelligence but cost premium ($20/$80) not justified vs 5.1
  o4-mini     →  Thinking-model latency (20-60s/step) kills 10+ step agent loops
  gpt-4.1     →  Pick ONLY if you need its 1M context window; tool routing weaker
  gpt-5-mini  →  Worker-tier; drops tool calls when inventory >20 tools

  HYBRID FLOW:
  --------------------------------------------------------------------------------
        USER REQUEST
              │
              ▼
    ┌──────────────────────┐
    │ PLANNER  (1 call)    │  o4-mini    — deep upfront plan
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │ ORCHESTRATOR (loop)  │  gpt-5.1    — fast tool routing every step
    └──────────┬───────────┘
               ▼
    ┌──────────────────────┐
    │ WORKERS  (parallel)  │  gpt-4.1-mini / gpt-5-mini
    └──────────────────────┘

  OPEN QUESTIONS TO RESOLVE BEFORE LOCKING IN:
  --------------------------------------------------------------------------------
  1. How big is "large context" routinely?  >200k → check gpt-5.1 ctx limit
     on Rakuten endpoint, else fall back to gpt-4.1 (1M ctx).
  2. Tool inventory size?  >30 tools → even gpt-5.1 degrades; need tool
     grouping / sub-agents.
  3. Average loop depth?  >20 steps → per-step latency is the dominant cost;
     never use a thinking model in the loop.
  4. Cost ceiling per task?  gpt-5.1 × 20-step loop × 8k tokens/step ≈ $2-8/task.

  DEFAULT:  OPENAI_MODEL=gpt-5.1
================================================================================
"""

api_key = os.environ.get("OPENAI_API_KEY")
model = os.environ.get("OPENAI_MODEL", "gpt-4.1")

client = OpenAI(
  api_key= api_key,
  base_url="https://api.ai.public.rakuten-it.com/openai/v1"
)

print(f"Using model: {model}")

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a short story about a magic backpack."},
    ],
)
print(response) 
