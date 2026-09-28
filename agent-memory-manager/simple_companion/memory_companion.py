"""
Proactive Memory Companion Agent (Sidecar).
Maintains the 3-category Memory Bank and evaluates the binary intervention policy:
- SILENT: When execution is safe (keeps main agent context lean).
- INJECT: Injects a concise, high-priority grounded reminder when risks occur.
"""

from typing import Dict, List, Any, Optional
import re


class MemoryCompanion:
    """A dedicated memory companion that monitors and assists the primary ReAct agent."""

    def __init__(self, constraints: Optional[List[str]] = None):
        # 3-Category Structured Memory Bank
        self.status = {
            "active_subgoal": None,
            "completed_milestones": [],
            "pending_blockers": []
        }
        self.knowledge = {
            "environment_facts": {},
            "user_constraints": constraints or []
        }
        self.procedural = {
            "failed_attempts": [],      # List of {turn, action, error, countermeasure}
            "verified_patterns": []
        }

        # Telemetry metrics
        self.injections_count = 0
        self.silence_count = 0

    # -------------------------------------------------------------------------
    # 1. PRE-ACTION HOOK: Proactive Policy Evaluation
    # -------------------------------------------------------------------------
    def pre_action_check(self, turn: int, planned_action: str) -> Optional[str]:
        """
        Evaluates whether the companion should stay SILENT or INJECT a reminder.
        Returns:
            str: Targeted grounded reminder if INJECT.
            None: If SILENT (preserves attention hygiene).
        """
        action_clean = planned_action.strip().lower()

        # Rule 1: Check for Known Failure Loop (Repeating a previously failed command)
        for fail in self.procedural["failed_attempts"]:
            # Check matching failed port or command pattern
            if "5432" in action_clean and "5432" in fail["action"]:
                self.injections_count += 1
                return (
                    f"[COMPANION INJECTION - Turn {fail['turn']} Failure Detected]\n"
                    f"Warning: You ran '{fail['action']}' in Turn {fail['turn']} and received '{fail['error']}'.\n"
                    f"Countermeasure: The active container port is mapped to 5433 (not 5432). Use port 5433 instead."
                )

        # Rule 2: Check for User Constraint Violation (e.g. touching forbidden legacy directories)
        for constraint in self.knowledge["user_constraints"]:
            if "/migrations/legacy/" in action_clean or "legacy" in action_clean:
                self.injections_count += 1
                return (
                    f"[COMPANION INJECTION - Constraint Guardian]\n"
                    f"Alert: Planned action targets a protected file. User constraint strictly states: '{constraint}'."
                )

        # Rule 3: Safe & Routine Action -> REMAIN SILENT
        self.silence_count += 1
        return None

    # -------------------------------------------------------------------------
    # 2. POST-OBSERVATION HOOK: Memory Bank Ingestion
    # -------------------------------------------------------------------------
    def post_observation_update(self, turn: int, action: str, observation: str) -> None:
        """Updates Status, Knowledge, and Procedural memory from environment observation."""
        obs_lower = observation.lower()
        action_lower = action.lower()

        # 1. Detect and register failures in Procedural Memory
        if "connection refused" in obs_lower or "failed" in obs_lower or "error" in obs_lower:
            # Check if not already recorded
            already_recorded = any(f["action"] == action_lower for f in self.procedural["failed_attempts"])
            if not already_recorded:
                error_summary = "ConnectionRefused (Port 5432 down)" if "5432" in action else "CommandExecutionError"
                self.procedural["failed_attempts"].append({
                    "turn": turn,
                    "action": action_lower,
                    "error": error_summary,
                    "raw_observation": observation[:80]
                })
                self.status["pending_blockers"].append(f"Port 5432 connection refused in turn {turn}")

        # 2. Extract facts into Knowledge Memory
        if "5433->5432" in observation:
            self.knowledge["environment_facts"]["active_postgres_port"] = 5433
            self.status["completed_milestones"].append("Discovered active DB port 5433 via docker ps")

        # 3. Update milestones in Status Memory
        if "migration applied successfully" in obs_lower:
            self.status["completed_milestones"].append("Applied auth migrations on port 5433")
            self.procedural["verified_patterns"].append("psql -h localhost -p 5433")

        if "passed" in obs_lower:
            self.status["completed_milestones"].append("Test suite passed (100%)")

    def get_summary(self) -> Dict[str, Any]:
        """Returns statistics and snapshot of memory bank."""
        total = self.injections_count + self.silence_count
        silence_ratio = (self.silence_count / total * 100) if total > 0 else 100
        return {
            "injections": self.injections_count,
            "silence_count": self.silence_count,
            "silence_ratio": f"{silence_ratio:.1f}%",
            "failed_attempts_tracked": len(self.procedural["failed_attempts"]),
            "facts_discovered": self.knowledge["environment_facts"],
            "completed_milestones": self.status["completed_milestones"]
        }
