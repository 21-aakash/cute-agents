"""
Proactive Memory Companion Core Engine.
Executes the dual-step cycle:
1. Ingest & Update: M_t = Update(M_{t-1}, a_{t-1}, o_{t-1})
2. Policy Evaluation: pi_mem(H_t, M_t) -> (decision, reminder)
"""

from __future__ import annotations
import re
from typing import Optional, List, Dict, Any, Callable
from .models import (
    MemoryBank,
    StatusMemory,
    KnowledgeMemory,
    ProceduralMemory,
    FailedAttempt,
    PolicyDecision,
    DecisionType,
)
from .tracker import FailureTracker
from .store import SQLiteMemoryStore


class ProactiveMemoryCompanion:
    """
    The Proactive Memory Agent (Sidecar).
    Operates alongside the primary action agent to prevent behavioral state decay.
    """

    def __init__(
        self,
        session_id: str = "default_session",
        store: Optional[SQLiteMemoryStore] = None,
        llm_policy_evaluator: Optional[Callable[[Dict[str, Any], str], PolicyDecision]] = None
    ):
        self.session_id = session_id
        self.store = store or SQLiteMemoryStore()
        self.tracker = FailureTracker()
        self.llm_policy_evaluator = llm_policy_evaluator
        
        # Load or initialize memory bank
        loaded = self.store.load_memory_bank(session_id)
        if loaded:
            self.memory_bank = loaded
        else:
            self.memory_bank = MemoryBank(session_id=session_id)

    # -------------------------------------------------------------------------
    # Step 1: Memory Ingestion & Update
    # -------------------------------------------------------------------------
    def ingest_turn(
        self,
        turn: int,
        action: str,
        observation: str,
        extracted_facts: Optional[Dict[str, Any]] = None,
        active_subgoal: Optional[str] = None
    ) -> None:
        """
        Updates the 3-category Memory Bank with new trajectory observations.
        """
        # 1. Update Procedural Memory via Failure Tracker
        failed_attempt = self.tracker.record_turn(turn, action, observation)
        if failed_attempt:
            # Check if this specific failure is already recorded
            existing = next(
                (f for f in self.memory_bank.procedural.failed_attempts 
                 if f.action_signature == failed_attempt.action_signature),
                None
            )
            if not existing:
                self.memory_bank.procedural.failed_attempts.append(failed_attempt)

        # 2. Update Knowledge Memory
        if extracted_facts:
            self.memory_bank.knowledge.environment_facts.update(extracted_facts)

        # Heuristic fact extraction (ports, paths)
        self._extract_implicit_facts(action, observation)

        # 3. Update Status Memory
        if active_subgoal:
            self.memory_bank.status.current_subgoal = active_subgoal
        if not failed_attempt and "success" in observation.lower():
            if action not in self.memory_bank.status.completed_milestones:
                self.memory_bank.status.completed_milestones.append(action)

        self.memory_bank.last_updated_turn = turn

        # Persist to SQLite store
        self.store.save_memory_bank(self.memory_bank)
        self.store.record_turn(self.session_id, turn, action, observation)

    def set_user_constraints(self, constraints: List[str]) -> None:
        """Registers immutable user constraints and rules."""
        self.memory_bank.knowledge.user_constraints = constraints
        self.store.save_memory_bank(self.memory_bank)

    def _extract_implicit_facts(self, action: str, observation: str) -> None:
        """Lightweight regex extractor for common environmental variables/ports."""
        # Detect port assignments (e.g. "port: 5433" or "-p 5433")
        port_match = re.search(r"(?:port|listening on|bound to)[\s:=]+(\d{4,5})", observation, re.IGNORECASE)
        if port_match:
            self.memory_bank.knowledge.environment_facts["active_port"] = port_match.group(1)

        # Detect working directory
        pwd_match = re.search(r"(?:in directory|working dir|cwd)[\s:=]+([\w/\\.-]+)", observation, re.IGNORECASE)
        if pwd_match:
            self.memory_bank.knowledge.environment_facts["working_dir"] = pwd_match.group(1)

    # -------------------------------------------------------------------------
    # Step 2: Proactive Policy Evaluation (SILENT vs INJECT)
    # -------------------------------------------------------------------------
    def evaluate_intervention(
        self,
        turn: int,
        planned_action: str,
        current_context: Optional[str] = None
    ) -> PolicyDecision:
        """
        Evaluates whether to remain SILENT or INJECT a targeted reminder.
        """
        # If an external LLM policy evaluator is registered, use it
        if self.llm_policy_evaluator:
            decision = self.llm_policy_evaluator(self.memory_bank.model_dump(), planned_action)
            self.store.record_intervention(self.session_id, turn, decision)
            return decision

        # Fast Deterministic / Heuristic Policy Engine
        decision = self._deterministic_policy_check(planned_action)
        self.store.record_intervention(self.session_id, turn, decision)
        return decision

    def _deterministic_policy_check(self, planned_action: str) -> PolicyDecision:
        """
        Evaluates rule-based triggers with maximum precision to avoid false injections.
        """
        if not planned_action or not planned_action.strip():
            return PolicyDecision(
                decision=DecisionType.SILENT,
                reasoning="No planned action provided."
            )

        norm_action = FailureTracker.normalize_command(planned_action)

        # Check 1: Failure Risk (Does planned action match a known failed attempt?)
        failed_risk = self.tracker.check_failure_risk(planned_action)
        if failed_risk:
            countermeasure = failed_risk.countermeasure or "Avoid repeating this failing pattern."
            reminder = (
                f"[Memory Companion Warning]: In Turn {failed_risk.turn}, running '{failed_risk.action_signature}' "
                f"failed with '{failed_risk.error_signature}'. {countermeasure}"
            )
            return PolicyDecision(
                decision=DecisionType.INJECT,
                confidence=0.95,
                reasoning=f"Planned action matches failed attempt from Turn {failed_risk.turn}.",
                reminder=reminder,
                matched_error_signature=failed_risk.error_signature
            )

        # Check 2: Constraint Violation Check
        for constraint in self.memory_bank.knowledge.user_constraints:
            # E.g. "Do not edit files in /migrations/legacy/"
            prohibited_match = re.search(r"(?:do not|never|prohibit|avoid)[\s\w]+(?:in|to|edit|modify|delete)\s+([\w/\\.-]+)", constraint, re.IGNORECASE)
            if prohibited_match:
                forbidden_target = prohibited_match.group(1).lower()
                if forbidden_target in norm_action:
                    reminder = (
                        f"[Memory Companion Alert]: Potential constraint violation. "
                        f"User constraint strictly states: '{constraint}'."
                    )
                    return PolicyDecision(
                        decision=DecisionType.INJECT,
                        confidence=0.98,
                        reasoning=f"Planned action targets forbidden resource: {forbidden_target}",
                        reminder=reminder,
                        matched_constraint=constraint
                    )

        # Check 3: Routine / Normal Operation -> STAY SILENT (Preserve Attention)
        return PolicyDecision(
            decision=DecisionType.SILENT,
            confidence=1.0,
            reasoning="Planned action does not match any known failure signatures or constraint risks.",
            reminder=None
        )
