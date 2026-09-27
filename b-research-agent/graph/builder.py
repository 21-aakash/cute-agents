from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from domain.state import ResearchGraphState
from graph.nodes import (
    chitchat_node,
    clarify_node,
    critique_node,
    persist_node,
    plan_node,
    research_node,
    revise_node,
    write_node,
)
from services.config import settings


def _should_revise(state: ResearchGraphState) -> str:
    critique = state.get("critique") or {}
    if critique.get("passed"):
        return "persist"
    if state.get("revisions", 0) >= settings.max_revisions:
        return "persist"
    return "revise"


def build_graph(checkpointer=None):
    workflow = StateGraph(ResearchGraphState)

    workflow.add_node("plan", plan_node)
    workflow.add_node("clarify", clarify_node)
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node(
        "research",
        research_node,
        retry_policy=RetryPolicy(max_attempts=3),
    )
    workflow.add_node("write", write_node)
    workflow.add_node("critique", critique_node)
    workflow.add_node("revise", revise_node)
    workflow.add_node("persist", persist_node)

    workflow.add_edge(START, "plan")
    workflow.add_edge("research", "write")
    workflow.add_edge("write", "critique")
    workflow.add_edge("revise", "research")
    workflow.add_edge("persist", END)
    workflow.add_edge("chitchat", END)

    workflow.add_conditional_edges(
        "critique",
        _should_revise,
        {"revise": "revise", "persist": "persist"},
    )

    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    return workflow.compile()
