# Proactive Memory Agent: Research Specification & System Design

> **Reference Paper**: *Remember When It Matters: Proactive Memory Agent for Long-Horizon Agents*  
> **Authors**: Yifan Wu, Lizhu Zhang, Yuhang Zhou, Mingyi Wang, Bo Peng, Serena Li, Xiangjun Fan, Zhuokai Zhao (Meta AI Research)  
> **arXiv**: [2607.08716](https://arxiv.org/abs/2607.08716) (July 2026)  
> **Evaluation Benchmarks**: $\tau^2$-Bench (+6.8% pass@1), Terminal-Bench 2.0 (+8.3% pass@1)

---

## 1. Theoretical Framework: Behavioral State Decay

Autonomous LLMs executing complex multi-step trajectories experience **Behavioral State Decay**, an empirical phenomenon where critical information is present in earlier context history but becomes ineffective at steering future actions due to attention dilution and context length expansion.

```
Trajectory Horizon (Turns) ───►  t=1 ........................ t=15 ........................ t=30
Context Size                ───►  [Small Context]            [Medium Context]             [Degraded Attention]
Failure Modes Encountered   ───►                             • Command Failure Loops      • Lost User Constraints
                                                             • Stale Subgoal Drifting     • Repeated Syntax Errors
```

### Why Existing Paradigms Underperform
1. **Passive Retrieval (Standard RAG)**: Requires the action agent to proactively query its memory. An agent that is unaware it is making a mistake will not query its memory.
2. **Continuous Memory Broadcasting**: Prepending the entire memory bank on every turn floods the prompt, increases token costs, and dilutes model attention, reducing overall pass rate.
3. **Proactive Intervention (The Proposed Solution)**: A standalone companion monitors trajectory observations, updates a structured memory bank, and selectively executes a binary decision policy: `SILENT` vs `INJECT(reminder)`.

---

## 2. Structured Memory Bank Schema

The Memory Bank $\mathcal{M}$ is partitioned into three explicit categories:

$$\mathcal{M} = \{\mathcal{M}_{\text{status}}, \mathcal{M}_{\text{knowledge}}, \mathcal{M}_{\text{procedural}}\}$$

```json
{
  "status": {
    "current_subgoal": "Locate and configure database connection parameters",
    "completed_milestones": [
      "Cloned repository to /workspace/app",
      "Installed Python dependencies via pyproject.toml"
    ],
    "pending_blockers": [
      "PostgreSQL port 5432 is not accepting default credentials"
    ]
  },
  "knowledge": {
    "environment_facts": {
      "python_version": "3.11.8",
      "working_dir": "/workspace/app",
      "config_file": "/workspace/app/config/settings.yaml"
    },
    "user_constraints": [
      "Do not modify files in /migrations/",
      "Keep test timeout strictly under 30 seconds"
    ]
  },
  "procedural": {
    "failed_attempts": [
      {
        "turn": 4,
        "action_signature": "psql -U postgres -h localhost -d testdb",
        "error_signature": "psql: error: connection to server at \"localhost\" failed: Connection refused",
        "root_cause": "PostgreSQL daemon not started on host; Docker container 'postgres-db' runs on port 5433",
        "countermeasure": "Use psql -p 5433 or inspect docker ps"
      }
    ],
    "verified_patterns": [
      "Export DB_PORT=5433 before running pytest"
    ]
  }
}
```

---

## 3. The Dual-Step Algorithmic Cycle

At turn $t$, given the previous action $a_{t-1}$ and environment observation $o_{t-1}$:

### Step 1: Memory Bank Ingestion & Update
The companion receives $(a_{t-1}, o_{t-1})$ and updates $\mathcal{M}_t$:
* Detects execution failures (non-zero exit codes, HTTP 4xx/5xx, stack traces).
* Extracts new environment facts (IPs, paths, config keys).
* Updates subgoal progress.

### Step 2: Proactive Policy Evaluation ($\pi_{\text{mem}}$)
The companion inspects the planned context and evaluates whether intervention is warranted:

$$\pi_{\text{mem}}(H_t, \mathcal{M}_t) \to (\text{decision}, r_t)$$

* **`SILENT`**: Routine execution proceeding normally. Context is left unpolluted.
* **`INJECT`**: Companion injects a concise, high-priority grounded reminder $r_t$ into the action agent's prompt stream.

---

## 4. Prompt Specifications (Memory Agent & Decision Engine)

### Memory Ingestion & Update Prompt Template
```
You are the Proactive Memory Companion for an autonomous action agent.
Analyze the latest action and environment observation to update the Structured Memory Bank.

[CURRENT MEMORY BANK]
{current_memory_json}

[LATEST TURN]
Action: {action_str}
Observation: {observation_str}

Update the Memory Bank:
1. Status (active subgoal, milestones, blockers)
2. Knowledge (environment parameters, constraints)
3. Procedural (failed command signatures, root causes, verified patterns)

Output the updated memory bank as valid JSON.
```

### Proactive Intervention Policy Prompt Template
```
You are the Proactive Memory Policy Engine.
Your goal is to decide whether to intervene (INJECT) or remain SILENT.

Decision Rubric:
- Choose INJECT only if:
  1. The agent is about to repeat a previously failed command/action or known error signature.
  2. The agent is in danger of violating a known user constraint or environment fact.
  3. The agent has lost track of the current subgoal or is stuck in an execution loop.
- Choose SILENT if:
  1. The agent is making steady progress.
  2. The next action is safe and does not trigger known failure modes.

Output format:
{
  "decision": "SILENT" | "INJECT",
  "confidence": 0.0 to 1.0,
  "reasoning": "<brief rationale>",
  "reminder": "<concise 1-2 sentence targeted reminder if INJECT, else null>"
}
```

---

## 5. Engineering Implementation Roadmap

Based directly on the research paper's specifications, we build:
1. `companion/models.py`: Pydantic models for `MemoryBank`, `StatusMemory`, `KnowledgeMemory`, `ProceduralMemory`, and `PolicyDecision`.
2. `companion/tracker.py`: Tool & shell command error signature hasher (normalized fingerprinting).
3. `companion/engine.py`: Proactive Memory Agent executing the dual-step update and decision cycle.
4. `companion/store.py`: SQLite persistence layer for session state and trajectory logging.
5. `companion/middleware.py`: Transparent Python wrapper (`@companion.watch` / event hooks) for any LLM agent.
6. `benchmarks/`: Benchmark test suites evaluating Terminal-Bench failure loops and $\tau^2$-Bench long-horizon constraints.
