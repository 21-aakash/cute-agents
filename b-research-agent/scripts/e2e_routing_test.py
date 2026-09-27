#!/usr/bin/env python3
"""E2E routing test — planner sources respected, KB probe skips irrelevant docs.

Requires running infra + backend:
  podman compose up -d
  uv run uvicorn api.main:app --reload --port 8000

Usage:
  uv run python scripts/e2e_routing_test.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "scripts" / "fixtures" / "e2e-kb-doc.md"
SECRET = "SILVERFOX-42"

BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8000").rstrip("/")
CHAT_TIMEOUT = int(os.environ.get("E2E_CHAT_TIMEOUT", "180"))
UPLOAD_TIMEOUT = int(os.environ.get("E2E_UPLOAD_TIMEOUT", "180"))


def req(method: str, path: str, *, body: dict | None = None, api_key: str | None = None, timeout: int = 60):
    headers: dict[str, str] = {}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if api_key:
        headers["X-API-Key"] = api_key
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def upload_file(path: Path, *, ws_id: str, api_key: str) -> dict:
    content = path.read_bytes()
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(
        f"{BASE}/api/v1/workspaces/{ws_id}/documents",
        data=body,
        headers={"X-API-Key": api_key, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=UPLOAD_TIMEOUT) as resp:
        return json.loads(resp.read())


def tool_names(tool_calls: list[dict]) -> set[str]:
    return {tc.get("tool", "") for tc in tool_calls}


def chat(ws_id: str, session_id: str, api_key: str, query: str, *, web: bool) -> dict:
    return req(
        "POST",
        f"/api/v1/workspaces/{ws_id}/sessions/{session_id}/chat",
        body={"query": query, "web_search_enabled": web},
        api_key=api_key,
        timeout=CHAT_TIMEOUT,
    )


def main() -> int:
    print(f"E2E routing test → {BASE}\n")
    failures: list[str] = []

    health = req("GET", "/health")
    if not health.get("ok"):
        print("Backend not healthy")
        return 1

    ws = req("POST", "/api/v1/workspaces", body={"name": "E2E Routing Test"})
    ws_id, api_key = ws["id"], ws["api_key"]

    doc = upload_file(FIXTURE, ws_id=ws_id, api_key=api_key)
    if doc.get("status") != "indexed":
        print(f"Upload failed: {doc}")
        return 1
    print(f"Indexed fixture: {doc.get('chunk_count')} chunks")

    # 1. Pure RAG — docs only, no web
    sess = req("POST", f"/api/v1/workspaces/{ws_id}/sessions", api_key=api_key)
    rag = chat(
        ws_id,
        str(sess["session_id"]),
        api_key,
        "What is the codename for Project Aurora?",
        web=False,
    )
    rag_tools = tool_names(rag.get("tool_calls") or [])
    if "doc_search" not in rag_tools:
        failures.append(f"rag: expected doc_search, got {rag_tools}")
    if "web_search" in rag_tools:
        failures.append(f"rag: web_search should not run when disabled, got {rag_tools}")
    evidence = " ".join(e.get("text", "") for e in (rag.get("evidence") or [])).upper()
    if SECRET not in evidence and SECRET not in (rag.get("answer") or "").upper():
        failures.append("rag: answer/evidence missing SILVERFOX-42")
    print(f"[{'PASS' if not failures else 'FAIL'}] pure RAG tools={sorted(rag_tools)}")

    # 2. Pure web — current events, KB probe should skip docs
    sess2 = req("POST", f"/api/v1/workspaces/{ws_id}/sessions", api_key=api_key)
    web = chat(
        ws_id,
        str(sess2["session_id"]),
        api_key,
        "What are the latest breaking news headlines today?",
        web=True,
    )
    web_tools = tool_names(web.get("tool_calls") or [])
    if "web_search" not in web_tools:
        failures.append(f"web: expected web_search, got {web_tools}")
    if "doc_search" in web_tools:
        failures.append(f"web: doc_search should be skipped for news query, got {web_tools}")
    print(f"[{'PASS' if 'doc_search' not in web_tools and 'web_search' in web_tools else 'FAIL'}] pure web tools={sorted(web_tools)}")

    # 3. Second turn — switch back to RAG in same session as web query
    follow = chat(
        ws_id,
        str(sess2["session_id"]),
        api_key,
        "What is the codename for Project Aurora in our knowledge base?",
        web=True,
    )
    follow_tools = tool_names(follow.get("tool_calls") or [])
    if "doc_search" not in follow_tools:
        failures.append(f"followup: expected doc_search, got {follow_tools}")
    print(f"[{'PASS' if 'doc_search' in follow_tools else 'FAIL'}] follow-up RAG tools={sorted(follow_tools)}")

    print("\nSummary:")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  All routing checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
