#!/usr/bin/env python3
"""Smoke test UI proxy + backend wiring (no secrets printed)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8443"


def req(method: str, path: str, body: dict | None = None, api_key: str | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    if body is not None:
        data = json.dumps(body).encode()
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    try:
        health = req("GET", "/health")
        checks.append(("health", health.get("ok") is True, str(health)))
    except Exception as e:
        print(f"FAIL health: {e}")
        return 1

    try:
        ws = req("POST", "/api/v1/workspaces", {"name": "Smoke Test"})
        ws_id = ws["id"]
        api_key = ws["api_key"]
        checks.append(("create_workspace", bool(ws_id and api_key), ws_id[:8] + "…"))
    except Exception as e:
        print(f"FAIL workspace: {e}")
        return 1

    try:
        docs = req("GET", f"/api/v1/workspaces/{ws_id}/documents", api_key=api_key)
        checks.append(("list_documents", isinstance(docs, list), f"{len(docs)} docs"))
    except Exception as e:
        checks.append(("list_documents", False, str(e)))

    try:
        sess = req("POST", f"/api/v1/workspaces/{ws_id}/sessions", api_key=api_key)
        checks.append(("create_session", "session_id" in sess, str(sess["session_id"])[:8] + "…"))
    except Exception as e:
        checks.append(("create_session", False, str(e)))

    print("Smoke test results:")
    ok = True
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")
        ok = ok and passed

    if not ok:
        return 1
    print("\nUpload + chat require OPENAI_API_KEY in b-research-agent/.env")
    return 0


if __name__ == "__main__":
    sys.exit(main())
