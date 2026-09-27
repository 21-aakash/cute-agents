from __future__ import annotations

from typing import TypedDict


class ResearchGraphState(TypedDict, total=False):
    # Inputs
    query: str
    workspace_id: str
    session_id: str
    conversation_turns: list[dict]
    conversation_summary: str

    # Planner
    plan: dict

    # Research
    evidence: list[dict]
    notes: str
    tool_calls: list[dict]

    # Writer
    answer: str

    # Critic
    critique: dict

    # Loop control
    revision_note: str
    revisions: int
    clarify_count: int

    # Knowledge base context for planner
    indexed_documents: list[dict]

    # UI toggle: include live web search in research
    web_search_enabled: bool
