#!/usr/bin/env python3
"""Smoke test for RAGAS eval API."""
from __future__ import annotations

import json
import os
import sys
import uuid
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "scripts" / "fixtures" / "e2e-kb-doc.md"
BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = int(os.environ.get("EVAL_TIMEOUT", "600"))


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


def main() -> int:
    print(f"Eval smoke test → {BASE}")
    ws = req("POST", "/api/v1/workspaces", body={"name": "Eval Smoke"})
    ws_id, api_key = ws["id"], ws["api_key"]
    upload(FIXTURE, ws_id, api_key)
    print("Uploaded fixture, running golden eval (may take several minutes)…")
    result = req(
        "POST",
        f"/api/v1/workspaces/{ws_id}/evals/run",
        body={"mode": "golden"},
        api_key=api_key,
        timeout=TIMEOUT,
    )
    metrics = result.get("metrics_avg") or {}
    print(f"Samples: {result.get('sample_count')}  status: {result.get('status')}")
    print(f"Faithfulness: {metrics.get('faithfulness')}")
    print(f"Answer relevancy: {metrics.get('answer_relevancy')}")
    print(f"Context precision: {metrics.get('context_precision')}")
    ok = result.get("status") == "completed" and result.get("sample_count", 0) > 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
