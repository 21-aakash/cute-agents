"""
Universal Middleware & Decorator for Proactive Memory Companion.
Seamlessly wraps any agent execution loop (LangChain, LangGraph, LiteLLM, custom).
"""

from __future__ import annotations
from typing import Callable, Any, Dict, List, Optional, Tuple
from .engine import ProactiveMemoryCompanion
from .models import PolicyDecision, DecisionType


class MemoryCompanionMiddleware:
    """
    Middleware wrapper that injects proactive reminders before LLM calls
    and updates the memory bank after tool observations.
    """

    def __init__(self, companion: Optional[ProactiveMemoryCompanion] = None, session_id: str = "default_session"):
        self.companion = companion or ProactiveMemoryCompanion(session_id=session_id)
        self.current_turn: int = 0

    def wrap_prompt(self, user_prompt: str, planned_action: Optional[str] = None) -> Tuple[str, PolicyDecision]:
        """
        Pre-Action Hook: Evaluates policy and conditionally injects reminder into the prompt.
        """
        self.current_turn += 1
        decision = self.companion.evaluate_intervention(
            turn=self.current_turn,
            planned_action=planned_action or user_prompt
        )

        if decision.decision == DecisionType.INJECT and decision.reminder:
            augmented_prompt = f"{user_prompt}\n\n{decision.reminder}"
            return augmented_prompt, decision

        return user_prompt, decision

    def record_result(self, action: str, observation: str) -> None:
        """
        Post-Observation Hook: Feeds tool execution results back into the memory bank.
        """
        self.companion.ingest_turn(
            turn=self.current_turn,
            action=action,
            observation=observation
        )

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns session telemetry metrics."""
        return self.companion.store.get_telemetry_summary(self.companion.session_id)
