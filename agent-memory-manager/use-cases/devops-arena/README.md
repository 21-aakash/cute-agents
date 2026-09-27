# Use Case Specification: The Live DevOps & Bug Fixer Arena

> **Benchmark Foundation**: Terminal-Bench 2.0 & $\tau^2$-Bench  
> **Target Audience**: AI Researchers, Agent Developers, Software Engineers  
> **Interactive Modality**: Side-by-Side Live Arena (Vanilla Agent vs. Proactive Memory Agent)

---

## 1. Executive Summary

Autonomous coding agents (e.g., SWE-bench, Devin, Claude, Cursor agent loops) frequently fail when tackling multi-step terminal tasks that span 10+ turns. The primary failure mode is **Behavioral State Decay**: an agent tries a command that fails, explores other files for 4 turns, and then repeats the exact same broken command or violates an earlier user constraint.

The **Live DevOps & Bug Fixer Arena** is an end-to-end benchmark and interactive showcase demonstrating how a **Proactive Memory Companion (Sidecar)** eliminates repetitive error loops and enforces task constraints with minimal token overhead.

---

## 2. Side-by-Side Comparative Dynamics

```
+-----------------------------------------------------------------------------------------------+
|                                     AGENT MEMORY ARENA                                        |
|  Task: "Debug and fix broken auth migration & spin up backend test suite with DB port 5433"   |
+-----------------------------------------------+-----------------------------------------------+
|         [RED] VANILLA AGENT                   |       [GREEN] PROACTIVE COMPANION AGENT       |
+-----------------------------------------------+-----------------------------------------------+
| Turn 1: Cloned repo                           | Turn 1: Cloned repo                           |
| Turn 2: Ran `psql -p 5432` -> Refused [ERROR] | Turn 2: Ran `psql -p 5432` -> Refused [ERROR] |
| Turn 3: Edited settings.py                    | Turn 3: Edited settings.py [SILENT]           |
| Turn 4: Installed dependencies                | Turn 4: Installed dependencies [SILENT]       |
| Turn 5: Checked docker logs                   | Turn 5: Checked docker logs [SILENT]          |
|                                               |                                               |
| Turn 6: Lost Turn 2 context!                  | Turn 6: Agent prepares to retry port 5432...  |
|         Retries `psql -p 5432` -> LOOP [FAIL] |         TARGETED INJECTION:                   |
| Turn 7: Wasted tokens, edits legacy migration |         "[Alert]: Turn 2 proved DB is 5433."  |
| Turn 8: TASK STALLED / FAILED                 | Turn 7: Connects to 5433 & tests pass! [OK]   |
+-----------------------------------------------+-----------------------------------------------+
| Result: 15 Turns | $0.42 Cost | Failed Loop   | Result: 7 Turns | $0.14 Cost | 100% Success   |
+-----------------------------------------------+-----------------------------------------------+
```

---

## 3. The 3 Arena Scenarios

### Scenario 1: The PostgreSQL Port Trap (Command Failure Fingerprinting)
* **Goal**: Connect to database, run migration, and execute `pytest tests/test_db.py`.
* **Trap**: Default port `5432` is closed; Docker container is bound to `5433`.
* **Vanilla Failure**: Agent runs `psql -p 5432`, gets connection refused, changes some python code, and tries `psql -p 5432` again at turn 7.
* **Companion Intervention**: Procedural memory records the port 5432 failure signature. When the agent attempts a command with `5432`, the companion injects:  
  `"[Memory Companion Warning]: In Turn 2, connection to 5432 failed (Connection Refused). Use port 5433."`

### Scenario 2: The Forbidden Legacy Directory (Constraint Guardian)
* **Goal**: Refactor authentication logic in `/app/auth/`.
* **Constraint**: *"Do not edit files in `/migrations/legacy/` under any circumstances."*
* **Vanilla Failure**: By Turn 9, the initial prompt instruction has decayed from the agent's attention; it edits `/migrations/legacy/v1_auth.sql`, failing the safety evaluation.
* **Companion Intervention**: Knowledge memory tracks the immutable constraint. Companion intercepts the planned file edit and injects:  
  `"[Memory Companion Alert]: Violation risk: User constraint prohibits editing files in /migrations/legacy/."`

### Scenario 3: The Expired OAuth Token Refresh (Working State Tracking)
* **Goal**: Execute a multi-stage data sync with an external REST API requiring OAuth2 bearer tokens.
* **Trap**: Access token expires after step 3 (HTTP 401).
* **Vanilla Failure**: Repeats the same API call with the expired token 3 times before giving up.
* **Companion Intervention**: Companion tracks the 401 status in Status memory, injects the requirement to call `/auth/refresh` before continuing.

---

## 4. Telemetry Metrics & Evaluation Rubric

Every run through the Arena records quantitative metrics for community sharing:

| Metric | Definition | Target Benchmark |
| :--- | :--- | :--- |
| **Pass@1 Success Rate** | Percentage of tasks completed without unhandled errors | +15% to +25% over baseline |
| **Repeated Error Loop Count** | Number of times the exact same failure signature is repeated | Reduced to **0** |
| **Token Cost Reduction** | Total tokens spent across the trajectory | **40% - 60% savings** |
| **Silence Ratio ($\pi = \text{SILENT}$)** | Percentage of turns where companion remains quiet | **> 85%** (Prevents attention dilution) |

---

## 5. Technical Architecture & Components to Code

```
agent-memory-manager/
├── companion/                 # Core Memory Engine
│   ├── models.py              # Pydantic models (MemoryBank, PolicyDecision, etc.)
│   ├── tracker.py             # Error signature hashing & fingerprint detector
│   ├── engine.py              # Proactive Memory Agent (Ingest & Policy Evaluation)
│   ├── store.py               # SQLite session storage
│   └── middleware.py          # Universal Python wrapper & decorator
├── use-cases/
│   └── devops-arena/
│       ├── README.md          # This specification document
│       ├── scenarios.py       # Deterministic test scenarios (DB Port, Legacy Dir, OAuth)
│       └── runner.py          # Side-by-side execution engine & metrics logger
└── server/                    # FastMCP & API layer
```
