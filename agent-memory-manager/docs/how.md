Here is the exact clarification of the original concept, addressing how filtering works, how injection works, what type of memory is stored, and why the main agent **never needs to ask for memory**.

---

### 1. Does the Main Agent Ask for Memory? (The Core Breakthrough)

**No! The Main Agent never asks for memory.**

* **Why standard agents fail (The "Pull" / Reactive Flaw)**:
  In traditional RAG or vector search, the main agent has to decide to query its own memory. But if the agent is suffering from amnesia or is about to make a mistake, **it doesn't know that it doesn't know**. It won't call `search_memory()`.
* **The Paper's Solution (Proactive "Push")**:
  The Memory Companion runs **outside** the main agent. It passively watches the stream of actions and observations. When it detects a mistake or risk, it **proactively pushes** a reminder directly into the main agent's incoming prompt before the main agent takes its next action.

---

### 2. What Types of Memory Are Stored?

The paper categorizes memory into **3 distinct, structured buckets** (not a giant raw text dump):

| Memory Type | What is Stored | Concrete Example |
| :--- | :--- | :--- |
| **1. Status Memory** *(Working State)* | • Active sub-goals<br>• Completed milestones<br>• Current blockers | `"Subgoal": "Configure PostgreSQL port", "Completed": ["Cloned repo", "Installed packages"], "Blocker": "Port 5432 refused"` |
| **2. Knowledge Memory** *(Facts & Constraints)* | • Environment parameters (paths, ports, IPs)<br>• Immutable user constraints & rules | `"Environment": {"db_port": 5433}, "Constraints": ["Do NOT touch /migrations/legacy", "Timeout < 30s"]` |
| **3. Procedural Memory** *(Failures & Solutions)* | • Failed command signatures<br>• Error root causes<br>• Verified working patterns | `"FailedAttempt": "psql -p 5432 -> Connection refused", "RootCause": "Runs on 5433", "Countermeasure": "Use -p 5433"` |

---

### 3. How Does Filtering & Decision Work? (`SILENT` vs. `INJECT`)

This is the most important finding in the DeepLearning.AI / Meta AI paper:
> **"Reminding an agent constantly actually reduced accuracy compared to targeted timing."**

If the memory agent injects information on every turn, it causes **attention dilution** (the main agent gets confused by too much text). 

The companion uses a **Proactive Filter Policy**:

```
           Companion Analyzes: (Planned Action + Current Memory Bank)
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
     [IS THERE A RISK?]                                    [IS IT ROUTINE?]
     • About to repeat a failed command?                   • Normal tool execution?
     • About to violate a user constraint?                 • Progressing on subgoal?
     • Drifting from the active subgoal?                   • No past error match?
             │                                                     │
             ▼                                                     ▼
     🎯 ACTION: INJECT                                     🤫 ACTION: SILENT
     Inject concise 1-2 sentence nudge                     Do NOT inject anything
     ("Turn 3 failed with 5432, use 5433")                 (Keep context 100% clean)
```

---

### 4. How Does Injection Actually Happen in Code?

The injection is completely transparent to the Main Agent. It happens in the **pre-action message wrapper**:

1. **When `SILENT`**:
   The prompt sent to LLM is just the standard prompt:
   ```json
   {"role": "user", "content": "Proceed with step 4."}
   ```

2. **When `INJECT`**:
   The Memory Companion injects a high-priority system/companion reminder at the very end of the prompt:
   ```json
   {
     "role": "user", 
     "content": "Proceed with step 4.\n\n[Memory Companion Alert]: In turn 3, PostgreSQL connection on port 5432 failed with 'Connection Refused'. The correct port is 5433. Do not modify files in /migrations/."
   }
   ```

---

### Summary Checklist of the Architecture

1. **Who manages memory?** $\to$ A dedicated, lightweight secondary agent (Memory Companion).
2. **Does the main agent ask for it?** $\to$ No, it is pushed proactively by the companion.
3. **What is stored?** $\to$ 3 buckets: `Status` (goals), `Knowledge` (constraints & environment), and `Procedural` (failed command signatures & fixes).
4. **When is it sent?** $\to$ Only when a risk trigger matches (`INJECT`), otherwise the companion stays completely `SILENT`.

Does this exact mental model match your vision? If yes, we can start writing the clean Python implementation!