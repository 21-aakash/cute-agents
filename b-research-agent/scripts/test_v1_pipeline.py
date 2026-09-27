from __future__ import annotations

import os
import sys

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app

def test_v1_system():
    print("Testing CareerOps AI Version 1 API and Graph Foundation...")
    client = TestClient(app)
    
    # 1. Health check
    res = client.get("/health")
    print(f"1. Health Check Endpoint: status={res.status_code}, data={res.json()}")
    assert res.status_code == 200, "Health check failed"
    
    # 2. Workspace creation
    res = client.post("/api/v1/workspaces", json={"name": "CareerOps Candidate Workspace"})
    print(f"2. Workspace Creation: status={res.status_code}")
    assert res.status_code == 200, "Workspace creation failed"
    ws = res.json()
    ws_id = ws["id"]
    api_key = ws["api_key"]
    print(f"   Created workspace id={ws_id}")
    
    # 3. List documents in candidate workspace
    headers = {"X-API-Key": api_key}
    res = client.get(f"/api/v1/workspaces/{ws_id}/documents", headers=headers)
    print(f"3. List Documents: status={res.status_code}, count={len(res.json())}")
    assert res.status_code == 200, "Document listing failed"
    
    # 4. Create chat session
    res = client.post(f"/api/v1/workspaces/{ws_id}/sessions", json={}, headers=headers)
    print(f"4. Session Creation: status={res.status_code}")
    assert res.status_code == 200, "Session creation failed"
    session_id = res.json()["session_id"]
    print(f"   Created session id={session_id}")
    
    print("\n=======================================================")
    print("SUCCESS: ALL CAREEROPS AI VERSION 1 CORE ENDPOINTS PASSED!")
    print("=======================================================")

if __name__ == "__main__":
    test_v1_system()
