"""
Google GenAI SDK Adapter for Agent Memory Manager.
Integrates the official Google GenAI SDK (`google.genai`) with the Proactive Memory Companion.
"""

from __future__ import annotations
import os
from typing import Optional, List, Dict, Any
from .engine import ProactiveMemoryCompanion
from .models import DecisionType, PolicyDecision

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False


class GoogleGenAIMemoryAgent:
    """
    An autonomous agent powered by the official Google GenAI SDK (`google.genai`),
    protected by the Proactive Memory Companion sidecar.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        companion: Optional[ProactiveMemoryCompanion] = None,
        session_id: str = "gemini_agent_session"
    ):
        if not HAS_GOOGLE_GENAI:
            raise ImportError("Please install `google-genai` to use GoogleGenAIMemoryAgent.")

        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.model_name = model_name
        self.companion = companion or ProactiveMemoryCompanion(session_id=session_id)
        self.current_turn: int = 0
        self.trajectory_history: List[Dict[str, str]] = []

    def set_user_constraints(self, constraints: List[str]) -> None:
        """Registers immutable user constraints in knowledge memory."""
        self.companion.set_user_constraints(constraints)

    def run_turn(self, user_instruction: str, planned_action: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a single turn with proactive intervention evaluation.
        """
        self.current_turn += 1

        # 1. Pre-Action Hook: Evaluate Proactive Memory Policy
        action_candidate = planned_action or user_instruction
        decision: PolicyDecision = self.companion.evaluate_intervention(
            turn=self.current_turn,
            planned_action=action_candidate
        )

        # 2. Condition prompt based on decision (SILENT vs INJECT)
        augmented_prompt = user_instruction
        if decision.decision == DecisionType.INJECT and decision.reminder:
            augmented_prompt = (
                f"[PROACTIVE MEMORY COMPANION INJECTION]\n"
                f"{decision.reminder}\n\n"
                f"[CURRENT TASK INSTRUCTION]\n"
                f"{user_instruction}"
            )

        # 3. Execute model call via Google GenAI SDK
        model_output = ""
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=augmented_prompt
                )
                model_output = response.text or ""
            except Exception as e:
                model_output = f"[Google GenAI Error]: {str(e)}"
        else:
            model_output = f"[Simulated Response with Companion]: Executed safely conditioned on memory."

        # 4. Post-Observation Hook: Ingest output into Memory Bank
        self.companion.ingest_turn(
            turn=self.current_turn,
            action=action_candidate,
            observation=model_output
        )

        return {
            "turn": self.current_turn,
            "decision": decision.model_dump(),
            "augmented_prompt": augmented_prompt,
            "response": model_output,
            "memory_bank": self.companion.memory_bank.model_dump()
        }
