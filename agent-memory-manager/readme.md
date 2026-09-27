# Agent Memory Manager

A specialized memory companion for autonomous AI agents based on Meta AI research.

---

## Overview

Complex, long-horizon tasks frequently cause AI agents to suffer from context degradation and repeated command mistakes. Agent Memory Manager functions as a dedicated external memory companion that monitors agent actions, logs error signatures, and provides targeted memory injections.

---

## Key Capabilities

* **Targeted Memory Injection**: Delivers concise context updates only when triggered by relevant conditions, avoiding context overload.
* **Command Failure Tracking**: Identifies and records failed commands to prevent the primary agent from entering repetitive failure loops.
* **State Preservation**: Retains active goals, workspace environmental parameters, and session history across multi-turn workflows.

---

## Research Benchmarks

* **tau2 Bench Evaluation**: Increased task success rate from 55.0% to 61.8% for modern frontier models (Claude Sonnet 3.5 / 4.5).
* **Finding**: Episodic, targeted memory reminders significantly outperform continuous memory broadcasting by minimizing attention degradation.
