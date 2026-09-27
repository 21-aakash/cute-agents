from __future__ import annotations

from typing import Any


def markers_from_state(state: dict[str, Any], *, seen: set[str]) -> list[dict[str, Any]]:
    """Build UI pipeline markers from accumulated graph state."""
    out: list[dict[str, Any]] = []

    plan = state.get("plan")
    if plan and "plan-done" not in seen:
        seen.add("plan-done")
        sub_q = plan.get("sub_queries") or []
        out.append(
            {
                "id": "plan-done",
                "kind": "plan",
                "label": f"Planned · {plan.get('intent', 'research')} · {len(sub_q)} sub-queries",
                "active": False,
            }
        )

    for i, tc in enumerate(state.get("tool_calls") or []):
        mid = f"tool-{i}"
        if mid in seen:
            continue
        seen.add(mid)
        hits = tc.get("hit_count")
        hit_suffix = f" · {hits} hits" if hits is not None else ""
        out.append(
            {
                "id": mid,
                "kind": "tool",
                "label": f"{tc.get('tool', 'search')}: {tc.get('query', '')}{hit_suffix}",
                "active": False,
            }
        )

    evidence = state.get("evidence") or []
    if evidence and "sources" not in seen:
        seen.add("sources")
        n = len(evidence)
        out.append(
            {
                "id": "sources",
                "kind": "sources",
                "label": f"Retrieved {n} source{'s' if n != 1 else ''}",
                "active": False,
            }
        )

    if state.get("answer") and "write-done" not in seen:
        seen.add("write-done")
        out.append(
            {
                "id": "write-done",
                "kind": "write",
                "label": "Answer drafted",
                "active": False,
            }
        )

    if state.get("critique") and "critique-done" not in seen:
        seen.add("critique-done")
        passed = bool(state["critique"].get("passed"))
        out.append(
            {
                "id": "critique-done",
                "kind": "critique",
                "label": "Review complete" if passed else "Review · revision needed",
                "active": False,
            }
        )

    revisions = state.get("revisions") or 0
    if revisions > 0 and "rev-sep" not in seen:
        seen.add("rev-sep")
        out.append(
            {
                "id": "rev-sep",
                "kind": "revise",
                "label": f"{revisions} revision{'s' if revisions != 1 else ''}",
                "active": False,
                "variant": "separator",
            }
        )

    return out


def active_marker(node: str) -> dict[str, Any]:
    labels = {
        "plan": ("plan", "Planning…"),
        "research": ("research", "Searching knowledge base…"),
        "write": ("write", "Writing answer…"),
        "critique": ("critique", "Reviewing answer…"),
        "revise": ("revise", "Revising…"),
    }
    kind, label = labels.get(node, ("thinking", "Working…"))
    return {"id": f"active-{node}", "kind": kind, "label": label, "active": True}
