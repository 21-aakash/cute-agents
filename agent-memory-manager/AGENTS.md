# 🧠 Agent Specification: Agent Memory Manager

## 🎯 Role & Objective
Agent Memory Manager is an external memory companion architecture designed to assist primary autonomous AI agents during long-horizon, multi-step tasks by managing context window hygiene, logging failed environmental commands, and providing targeted notifications.

---

## 🧩 Architectural Paradigm: External Memory Companion (Sidecar Pattern)

* **Research Foundation**: Inspired by Meta AI research on long-context task execution and memory companions.
* **Core Mechanisms**:
  * **Failed Command Tracking**: Observes tool outputs and logs error signatures to prevent agents from repeating bad commands.
  * **Targeted Reminder Dispatch**: Injects short memory notes into the primary agent's context *only* when relevant, preventing context pollution and over-prompting degradation.
  * **State Snapshotting**: Preserves environment variables, workspace paths, and active goal states across multi-turn sessions.

---

## 📊 Benchmark Highlights
* **Task Benchmark**: $\tau^2$ Bench
* **Performance Gain**: Increased success rate from **55.0%** to **61.8%** on Claude Sonnet 3.5/4.5.
* **Key Finding**: Targeted, episodic memory injection outperforms continuous memory flooding by maintaining attention focus.

---

## 🛠️ Usage & Integration
This module serves as a pluggable memory sidecar that hooks into agent event loops via middleware or MCP protocols.
