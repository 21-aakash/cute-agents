#!/usr/bin/env python3
"""End-to-end test for the research agent API, knowledge base, and LangGraph pipeline.

Requires running infra + backend:
  podman compose up -d
  uv run uvicorn api.main:app --reload --port 8000

Usage:
  uv run python scripts/e2e_agent_test.py
  E2E_BASE=http://127.0.0.1:8443 uv run python scripts/e2e_agent_test.py  # via UI proxy
  E2E_SKIP_LLM=1 uv run python scripts/e2e_agent_test.py  # skip chat/RAG LLM checks
"""
from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "scripts" / "fixtures" / "e2e-kb-doc.md"
SECRET = "SILVERFOX-42"

BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = int(os.environ.get("E2E_TIMEOUT", "120"))
UPLOAD_TIMEOUT = int(os.environ.get("E2E_UPLOAD_TIMEOUT", "180"))
CHAT_TIMEOUT = int(os.environ.get("E2E_CHAT_TIMEOUT", "180"))
SKIP_LLM = os.environ.get("E2E_SKIP_LLM", "").lower() in {"1", "true", "yes"}


class Check:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append((name, passed, detail))
        if not passed:
            print(f"  [FAIL] {name}: {detail}")

    @property
    def ok(self) -> bool:
        return all(p for _, p, _ in self.results)


def req(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    api_key: str | None = None,
    timeout: int = TIMEOUT,
) -> dict | list:
    headers: dict[str, str] = {}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if api_key:
        headers["X-API-Key"] = api_key
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        raw = resp.read()
        if not raw:
            return {}
        return json.loads(raw)


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
        headers={
            "X-API-Key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=UPLOAD_TIMEOUT) as resp:
        return json.loads(resp.read())


def run() -> int:
    checks = Check()
    print(f"E2E agent test → {BASE}\n")

    if not FIXTURE.is_file():
        checks.record("fixture_exists", False, str(FIXTURE))
        _print_summary(checks)
        return 1

    # 1. Health
    try:
        health = req("GET", "/health")
        checks.record(
            "health",
            health.get("ok") is True,
            f"postgres={health.get('postgres')} qdrant={health.get('qdrant')}",
        )
    except Exception as exc:
        checks.record("health", False, str(exc))
        _print_summary(checks)
        return 1

    # 2. Workspace
    ws_id = api_key = ""
    try:
        ws = req("POST", "/api/v1/workspaces", body={"name": "E2E Agent Test"})
        ws_id = ws["id"]
        api_key = ws["api_key"]
        checks.record("create_workspace", bool(ws_id and api_key), ws_id[:8] + "…")
    except Exception as exc:
        checks.record("create_workspace", False, str(exc))
        _print_summary(checks)
        return 1

    doc_id = ""
    # 3. Upload knowledge base document
    try:
        doc = upload_file(FIXTURE, ws_id=ws_id, api_key=api_key)
        doc_id = doc["id"]
        checks.record(
            "upload_document",
            doc.get("status") == "indexed" and doc.get("chunk_count", 0) > 0,
            f"status={doc.get('status')} chunks={doc.get('chunk_count')}",
        )
    except Exception as exc:
        checks.record("upload_document", False, str(exc))

    # 4. Documents list includes upload
    try:
        docs = req("GET", f"/api/v1/workspaces/{ws_id}/documents", api_key=api_key)
        found = any(d.get("id") == doc_id and d.get("status") == "indexed" for d in docs)
        checks.record("list_documents", isinstance(docs, list) and found, f"{len(docs)} docs")
    except Exception as exc:
        checks.record("list_documents", False, str(exc))

    # 5. Vector search (Qdrant retrieval, no LLM)
    try:
        hits = req(
            "POST",
            f"/api/v1/workspaces/{ws_id}/documents/search",
            body={"query": "Project Aurora codename"},
            api_key=api_key,
        )
        texts = " ".join(h.get("text", "") for h in hits).upper()
        checks.record(
            "kb_vector_search",
            isinstance(hits, list)
            and len(hits) > 0
            and SECRET in texts,
            f"hits={len(hits)} top_score={hits[0].get('score') if hits else 'n/a'}",
        )
    except Exception as exc:
        checks.record("kb_vector_search", False, str(exc))

    # 6. Session
    session_id = ""
    try:
        sess = req("POST", f"/api/v1/workspaces/{ws_id}/sessions", api_key=api_key)
        session_id = str(sess["session_id"])
        checks.record("create_session", bool(session_id), session_id[:8] + "…")
    except Exception as exc:
        checks.record("create_session", False, str(exc))

    # 7. Chitchat
    if session_id:
        try:
            chat = req(
                "POST",
                f"/api/v1/workspaces/{ws_id}/sessions/{session_id}/chat",
                body={"query": "hi"},
                api_key=api_key,
                timeout=CHAT_TIMEOUT,
            )
            answer = chat.get("answer", "")
            checks.record(
                "chat_chitchat",
                chat.get("status") == "completed"
                and chat.get("intent") == "chitchat"
                and len(answer) > 0,
                f"intent={chat.get('intent')} answer_len={len(answer)}",
            )
        except Exception as exc:
            if SKIP_LLM:
                checks.record("chat_chitchat", True, f"skipped ({exc})")
            else:
                checks.record("chat_chitchat", False, str(exc))

    # 8. RAG query over uploaded document (requires LLM)
    rag_session_id = ""
    if not SKIP_LLM:
        try:
            sess = req("POST", f"/api/v1/workspaces/{ws_id}/sessions", api_key=api_key)
            rag_session_id = str(sess["session_id"])
            chat = req(
                "POST",
                f"/api/v1/workspaces/{ws_id}/sessions/{rag_session_id}/chat",
                body={"query": "What is the codename for Project Aurora?"},
                api_key=api_key,
                timeout=CHAT_TIMEOUT,
            )
            answer = (chat.get("answer") or "").upper()
            evidence_text = " ".join(
                e.get("text", "") for e in (chat.get("evidence") or [])
            ).upper()
            grounded = SECRET in answer or SECRET in evidence_text
            checks.record(
                "chat_rag_query",
                chat.get("status") == "completed" and grounded,
                f"intent={chat.get('intent')} evidence={len(chat.get('evidence') or [])}",
            )
        except Exception as exc:
            checks.record("chat_rag_query", False, str(exc))

    # 9. Session history
    if session_id:
        try:
            messages = req(
                "GET",
                f"/api/v1/workspaces/{ws_id}/sessions/{session_id}/messages",
                api_key=api_key,
            )
            checks.record(
                "session_messages",
                isinstance(messages, list) and len(messages) >= 1,
                f"{len(messages)} turn(s)",
            )
        except Exception as exc:
            checks.record("session_messages", False, str(exc))

    # 10. Delete uploaded document (+ verify removed from list)
    if doc_id:
        try:
            deleted = req(
                "DELETE",
                f"/api/v1/workspaces/{ws_id}/documents/{doc_id}",
                api_key=api_key,
            )
            docs_after = req("GET", f"/api/v1/workspaces/{ws_id}/documents", api_key=api_key)
            still_there = any(d.get("id") == doc_id for d in docs_after)
            checks.record(
                "delete_document",
                deleted.get("deleted") == doc_id and not still_there,
                f"remaining={len(docs_after)}",
            )
        except Exception as exc:
            checks.record("delete_document", False, str(exc))

        # 11. Search returns no SILVERFOX after delete
        try:
            hits = req(
                "POST",
                f"/api/v1/workspaces/{ws_id}/documents/search",
                body={"query": "Project Aurora codename SILVERFOX"},
                api_key=api_key,
            )
            texts = " ".join(h.get("text", "") for h in hits).upper()
            checks.record(
                "kb_search_after_delete",
                SECRET not in texts,
                f"hits={len(hits)}",
            )
        except Exception as exc:
            checks.record("kb_search_after_delete", False, str(exc))

    # 12. Delete session
    if session_id:
        try:
            deleted = req(
                "DELETE",
                f"/api/v1/workspaces/{ws_id}/sessions/{session_id}",
                api_key=api_key,
            )
            checks.record(
                "delete_session",
                deleted.get("deleted") == session_id,
                f"deleted={deleted.get('deleted', '')[:8]}…",
            )
        except Exception as exc:
            checks.record("delete_session", False, str(exc))

    if rag_session_id:
        try:
            req(
                "DELETE",
                f"/api/v1/workspaces/{ws_id}/sessions/{rag_session_id}",
                api_key=api_key,
            )
        except Exception:
            pass

    # 13. Deleted session returns 404
    if session_id:
        try:
            req(
                "GET",
                f"/api/v1/workspaces/{ws_id}/sessions/{session_id}/messages",
                api_key=api_key,
            )
            checks.record("delete_session_404", False, "expected 404, got 200")
        except urllib.error.HTTPError as exc:
            checks.record("delete_session_404", exc.code == 404, f"status={exc.code}")
        except Exception as exc:
            checks.record("delete_session_404", False, str(exc))

    _print_summary(checks)
    return 0 if checks.ok else 1


def _print_summary(checks: Check) -> None:
    print("\nE2E results:")
    for name, passed, detail in checks.results:
        status = "PASS" if passed else "FAIL"
        line = f"  [{status}] {name}"
        if detail:
            line += f": {detail}"
        print(line)
    print()
    if checks.ok:
        print("All checks passed.")
    else:
        print("Some checks failed.")


if __name__ == "__main__":
    sys.exit(run())
