#!/usr/bin/env python3
"""Validate agentic + RAGAS eval metrics (unit + optional live API)."""
from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.agentic_eval import aggregate_agentic, score_agentic_sample  # noqa: E402

BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8000").rstrip("/")
LIVE = os.environ.get("EVAL_LIVE", "1").lower() not in {"0", "false", "no"}
FIXTURE = ROOT / "scripts" / "fixtures" / "e2e-kb-doc.md"

AGENT_AVG_KEYS = {
    "completion_rate",
    "grounded_rate",
    "critic_pass_rate",
    "evidence_rate",
    "retrieval_hit_rate",
    "tool_invocation_rate",
    "tool_error_rate",
}
RAGAS_AVG_KEYS = {"faithfulness", "answer_relevancy", "context_precision"}
SAMPLE_AGENT_KEYS = {
    "completed",
    "critic_grounded",
    "critic_passed",
    "evidence_found",
    "doc_search_hit",
    "tool_invoked",
    "tool_error",
}


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    line = f"  [{status}] {name}"
    if detail:
        line += f": {detail}"
    print(line)
    return ok


def test_agentic_unit() -> bool:
    print("\nUnit: agentic metrics")
    ok = True

    good = score_agentic_sample({
        "answer": "SILVERFOX-42 is the codename.",
        "evidence": [{"text": "codename SILVERFOX-42", "origin": "documents"}],
        "tool_calls": [{"tool": "doc_search", "hit_count": 2}],
        "critique": {"grounded": True, "passed": True},
    })
    ok &= check("completed=1", good["completed"] == 1.0)
    ok &= check("tool_invoked=1", good["tool_invoked"] == 1.0)
    ok &= check("doc_search_hit=1", good["doc_search_hit"] == 1.0)
    ok &= check("grounded=1", good["critic_grounded"] == 1.0)

    bad = score_agentic_sample({
        "answer": "",
        "evidence": [],
        "tool_calls": [{"tool": "web_search", "hit_count": 0}],
        "critique": {"grounded": False, "passed": False},
    })
    ok &= check("empty answer completed=0", bad["completed"] == 0.0)
    ok &= check("web miss counts as tool error", bad["tool_error"] == 1.0)

    agg = aggregate_agentic([good, bad])
    ok &= check("aggregate has completion_rate", "completion_rate" in agg)
    ok &= check("aggregate completion_rate=0.5", agg["completion_rate"] == 0.5)
    ok &= check("aggregate tool_error_rate", agg["tool_error_rate"] == 0.5)
    return ok


def req(method, path, *, body=None, api_key=None, timeout=60):
    headers = {}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if api_key:
        headers["X-API-Key"] = api_key
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.loads(resp.read())


def upload(path: Path, ws_id: str, api_key: str) -> dict:
    content = path.read_bytes()
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    r = urllib.request.Request(
        f"{BASE}/api/v1/workspaces/{ws_id}/documents",
        data=body,
        headers={"X-API-Key": api_key, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(r, timeout=180) as resp:
        return json.loads(resp.read())


def test_live_api() -> bool:
    if not LIVE:
        print("\nSkipping live API (EVAL_LIVE=0)")
        return True

    print(f"\nLive API: {BASE}")
    ok = True
    try:
        ws = req("POST", "/api/v1/workspaces", body={"name": "Eval All Test"})
        ws_id, api_key = ws["id"], ws["api_key"]
        upload(FIXTURE, ws_id, api_key)
        result = req(
            "POST",
            f"/api/v1/workspaces/{ws_id}/evals/run",
            body={"mode": "golden"},
            api_key=api_key,
            timeout=600,
        )
    except Exception as exc:
        return check("live golden eval", False, str(exc))

    metrics = result.get("metrics_avg") or {}
    ok &= check("status completed", result.get("status") == "completed")
    ok &= check("sample_count > 0", (result.get("sample_count") or 0) > 0)

    missing_agent = AGENT_AVG_KEYS - set(metrics.keys())
    ok &= check("agent avg keys present", not missing_agent, f"missing={missing_agent}")

    for key in ("completion_rate", "tool_invocation_rate", "retrieval_hit_rate"):
        val = metrics.get(key)
        ok &= check(f"{key} in range", val is not None and 0.0 <= val <= 1.0, str(val))

    samples = result.get("samples") or []
    if samples:
        s0 = samples[0].get("scores") or {}
        ok &= check("sample has agent keys", SAMPLE_AGENT_KEYS.intersection(s0.keys()))
        ok &= check("sample completed=1 for golden", s0.get("completed") == 1.0, str(s0.get("completed")))
        ok &= check("no internal keys in API", not any(k.startswith("_") for k in s0))

    print(f"  metrics: {json.dumps({k: metrics.get(k) for k in sorted(metrics)}, indent=2)}")
    return ok


def main() -> int:
    print("Eval all test")
    ok = test_agentic_unit() and test_live_api()
    print("\n" + ("All eval checks passed." if ok else "Some eval checks failed."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
