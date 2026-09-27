from __future__ import annotations

from typing import Any

SEARCH_TOOLS = frozenset({"doc_search", "web_search", "memory_search"})


def _is_tool_error(tool_call: dict) -> bool:
    tool = tool_call.get("tool", "")
    hit_count = tool_call.get("hit_count")
    if tool == "web_search" and hit_count == 0:
        return True
    if tool in SEARCH_TOOLS and hit_count is not None and hit_count < 0:
        return True
    return False


def score_agentic_sample(result: dict[str, Any]) -> dict[str, float]:
    """Deterministic agentic metrics for one pipeline run (0–1 unless noted)."""
    answer = (result.get("answer") or "").strip()
    tool_calls = result.get("tool_calls") or []
    critique = result.get("critique") or {}
    evidence = result.get("evidence") or []

    search_calls = [t for t in tool_calls if t.get("tool") in SEARCH_TOOLS]
    tool_errors = sum(1 for t in search_calls if _is_tool_error(t))

    doc_searches = [t for t in tool_calls if t.get("tool") == "doc_search"]
    doc_hit = any((t.get("hit_count") or 0) > 0 for t in doc_searches)

    return {
        "completed": 1.0 if answer else 0.0,
        "critic_grounded": 1.0 if critique.get("grounded") else 0.0,
        "critic_passed": 1.0 if critique.get("passed") else 0.0,
        "evidence_found": 1.0 if evidence else 0.0,
        "doc_search_hit": 1.0 if doc_hit else 0.0,
        "tool_invoked": 1.0 if search_calls else 0.0,
        "tool_error": 1.0 if tool_errors > 0 else 0.0,
        "_tool_call_count": float(len(search_calls)),
        "_tool_error_count": float(tool_errors),
    }


def aggregate_agentic(samples: list[dict[str, float]]) -> dict[str, float | None]:
    if not samples:
        return {}

    def avg(key: str) -> float | None:
        vals = [s[key] for s in samples if key in s and s[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    total_calls = sum(s.get("_tool_call_count", 0) for s in samples)
    total_errors = sum(s.get("_tool_error_count", 0) for s in samples)

    return {
        "completion_rate": avg("completed"),
        "grounded_rate": avg("critic_grounded"),
        "critic_pass_rate": avg("critic_passed"),
        "evidence_rate": avg("evidence_found"),
        "retrieval_hit_rate": avg("doc_search_hit"),
        "tool_invocation_rate": avg("tool_invoked"),
        "tool_error_rate": round(total_errors / total_calls, 4) if total_calls else 0.0,
    }


def public_sample_scores(raw: dict[str, float]) -> dict[str, float | None]:
    """Strip internal counters before API/UI."""
    return {k: v for k, v in raw.items() if not k.startswith("_")}
