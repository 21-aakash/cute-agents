"""
FastMCP Server for Agent Memory Manager.
Exposes tools for Claude Desktop, Cursor, and Antigravity IDEs:
- record_turn: Ingest action and observation into memory bank
- evaluate_intervention: Check if planned action is safe or needs targeted injection
- get_working_memory: Retrieve active state, constraints, and failure signatures
"""

from __future__ import annotations
import json
from typing import Dict, Any, List, Optional
from companion.engine import ProactiveMemoryCompanion
from companion.models import DecisionType

# Initialize global companion instance for MCP sessions
companion = ProactiveMemoryCompanion(session_id="mcp_session")


def record_turn(turn: int, action: str, observation: str) -> str:
    """
    Ingests an action and its resulting environment observation into the structured memory bank.
    """
    companion.ingest_turn(turn=turn, action=action, observation=observation)
    return f"Successfully ingested turn {turn} into memory bank."


def evaluate_intervention(turn: int, planned_action: str) -> str:
    """
    Evaluates whether the agent should proceed normally (SILENT) or receive a targeted injection.
    """
    decision = companion.evaluate_intervention(turn=turn, planned_action=planned_action)
    return json.dumps({
        "decision": decision.decision.value,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,
        "reminder": decision.reminder
    }, indent=2)


def get_working_memory() -> str:
    """
    Returns the current 3-category structured memory bank (Status, Knowledge, Procedural).
    """
    return companion.memory_bank.model_dump_json(indent=2)


def set_constraints(constraints: List[str]) -> str:
    """
    Sets immutable user rules and boundary constraints.
    """
    companion.set_user_constraints(constraints)
    return f"Updated user constraints: {len(constraints)} rules registered."


if __name__ == "__main__":
    print("Agent Memory Manager MCP Server initialized.")
    print("Tools exposed: record_turn, evaluate_intervention, get_working_memory, set_constraints")
