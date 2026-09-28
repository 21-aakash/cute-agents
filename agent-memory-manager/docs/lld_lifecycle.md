# Low-Level Design (LLD) & Lifecycle Architecture

> **Architecture Pattern**: Proactive Memory Companion (Sidecar Pattern)  
> **Interaction Model**: Dual-Hook ReAct Agent Loop (Thought $\to$ Action $\to$ Tool Execution $\to$ Observation)

---

## 1. Class & Component Diagram (LLD)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ENVIRONMENT & TOOLS                                  │
│  ┌────────────────────┐   ┌────────────────────┐   ┌───────────────────────────────┐   │
│  │ run_bash(command)  │   │ read_file(path)    │   │ query_db(host, port, sql)     │   │
│  └────────────────────┘   └────────────────────┘   └───────────────────────────────┘   │
└──────────────────────────────────────────▲─────────────────────────────────────────────┘
                                           │ Executes Tool / Returns Observation
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MAIN REACT AGENT                                     │
│  - goal: str                                                                           │
│  - context_history: List[Message]                                                      │
│  - react_step() -> (thought, action, tool_name, tool_input)                            │
│  - step(observation) -> processes feedback                                            │
└───────────────────────▲────────────────────────────────────────┬───────────────────────┘
                        │                                        │
           (1) Injects  │ [INJECT(reminder)]                     │ (2) Observes
           Reminder     │                                        │ Action & Output
                        │                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                MEMORY COMPANION AGENT                                  │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Memory Bank:                                                                  │  │
│  │    • StatusMemory: active_subgoal, completed_milestones, pending_blockers        │  │
│  │    • KnowledgeMemory: environment_facts (ports, paths), user_constraints         │  │
│  │    • ProceduralMemory: failed_attempts (hashes, errors, countermeasures)         │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ 2. Proactive Policy Engine:                                                      │  │
│  │    • pre_action_hook(planned_action) -> SILENT (0 tokens) | INJECT(reminder)     │  │
│  │    • post_observation_hook(action, observation) -> updates Memory Bank           │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Turn-by-Turn ReAct Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant MainAgent as Main ReAct Agent
    participant Companion as Memory Companion (Sidecar)
    participant Tools as Environment / Tools

    User->>MainAgent: Task: "Run migrations on DB & execute test suite"
    User->>Companion: Register User Constraints (e.g. "Do not touch /legacy/")
    
    loop Every Turn (t = 1 .. N)
        Note over MainAgent: Agent forms Thought & Planned Action
        MainAgent->>Companion: Pre-Action Hook: (planned_action, context)
        
        alt Policy = SILENT (No risk detected)
            Companion-->>MainAgent: None (Keep context clean & unpolluted)
        else Policy = INJECT (Risk detected: repeating error or constraint violation)
            Companion-->>MainAgent: "[Companion Alert: Turn 2 failed with 5432. DB is on port 5433]"
            Note over MainAgent: Replaces failing thought with safe alternative
        end

        MainAgent->>Tools: Execute Tool (tool_name, tool_input)
        Tools-->>MainAgent: Observation (stdout, stderr, exit code)

        MainAgent->>Companion: Post-Observation Hook: (action, observation)
        Note over Companion: Updates Status, Knowledge & Procedural Memory
    end

    MainAgent-->>User: Task Complete (100% Success, 0 Error Loops)
```
