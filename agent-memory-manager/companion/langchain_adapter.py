"""
LangChain Adapter for Agent Memory Manager.
Provides callback handlers and runnable wrappers for LangChain & LangGraph.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from .engine import ProactiveMemoryCompanion
from .models import DecisionType, PolicyDecision


class LangChainMemoryCompanionCallback:
    """
    LangChain Callback Handler that injects targeted proactive reminders
    and ingests tool execution outputs.
    """

    def __init__(self, companion: Optional[ProactiveMemoryCompanion] = None, session_id: str = "langchain_session"):
        self.companion = companion or ProactiveMemoryCompanion(session_id=session_id)
        self.current_turn = 0

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Called before LLM generates text."""
        self.current_turn += 1

    def on_tool_end(self, output: str, name: Optional[str] = None, **kwargs: Any) -> None:
        """Called after tool finishes execution."""
        tool_action = kwargs.get("tool_input", str(name or "tool"))
        self.companion.ingest_turn(
            turn=self.current_turn,
            action=str(tool_action),
            observation=str(output)
        )

    def evaluate_action_risk(self, planned_action: str) -> Optional[str]:
        """Checks if a planned tool action should receive an injection."""
        decision = self.companion.evaluate_intervention(
            turn=self.current_turn + 1,
            planned_action=planned_action
        )
        if decision.decision == DecisionType.INJECT:
            return decision.reminder
        return None
