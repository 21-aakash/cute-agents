"""
FastAPI Backend for Agent Memory Manager Web Dashboard & Arena.
Serves static UI, handles real-time arena execution, and integrates with LLM providers (Groq Qwen-27B / GPT-OSS).
"""

from __future__ import annotations
import os
import sys
import json
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add use-cases/devops-arena to sys.path
ARENA_DIR = PROJECT_ROOT / "use-cases" / "devops-arena"
if str(ARENA_DIR) not in sys.path:
    sys.path.insert(0, str(ARENA_DIR))

from companion.engine import ProactiveMemoryCompanion
from companion.models import DecisionType
from scenarios import get_postgres_port_trap_scenario, get_forbidden_legacy_dir_scenario

# Load API keys from use-cases/.env
ENV_FILE = PROJECT_ROOT / "use-cases" / ".env"
API_KEYS: Dict[str, str] = {}
if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                parts = line.split(":", 1)
                key = parts[0].strip().lower().replace(" ", "_")
                val = parts[1].strip()
                if val:
                    API_KEYS[key] = val

app = FastAPI(title="Agent Memory Manager Live Arena")

# Active companion memory instances in memory
ACTIVE_COMPANIONS: Dict[str, ProactiveMemoryCompanion] = {}

# Mount static folder
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def get_or_create_companion(session_id: str, constraints: Optional[List[str]] = None) -> ProactiveMemoryCompanion:
    if session_id not in ACTIVE_COMPANIONS:
        comp = ProactiveMemoryCompanion(session_id=session_id)
        if constraints:
            comp.set_user_constraints(constraints)
        ACTIVE_COMPANIONS[session_id] = comp
    return ACTIVE_COMPANIONS[session_id]


class StepEvaluationRequest(BaseModel):
    session_id: str
    scenario_id: str
    turn: int
    command: str
    observation: str
    constraints: List[str] = []


class ResetSessionRequest(BaseModel):
    session_id: str
    constraints: List[str] = []


class LiveLLMRequest(BaseModel):
    provider: str = "groq"
    prompt: str
    model: Optional[str] = None
    use_companion: bool = True
    session_id: str = "live_llm_session"


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Agent Memory Manager UI</h1>")


@app.post("/api/reset-session")
async def reset_session(req: ResetSessionRequest):
    """Resets the in-memory and stored companion session."""
    ACTIVE_COMPANIONS.pop(req.session_id, None)
    comp = ProactiveMemoryCompanion(session_id=req.session_id)
    if req.constraints:
        comp.set_user_constraints(req.constraints)
    ACTIVE_COMPANIONS[req.session_id] = comp
    return {"status": "reset", "session_id": req.session_id}


@app.get("/api/scenarios")
async def get_scenarios():
    """Returns available arena scenarios with separate vanilla and companion trajectories."""
    s1 = get_postgres_port_trap_scenario()
    s2 = get_forbidden_legacy_dir_scenario()
    
    def serialize_step(st):
        return {
            "turn": st.turn,
            "intent": st.intent,
            "command": st.command,
            "observation": st.expected_observation,
            "is_failing": st.is_failing_command,
            "violates_constraint": st.violates_constraint,
            "is_loop_retry": getattr(st, "is_loop_retry", False)
        }

    return [
        {
            "id": s1.id,
            "name": s1.name,
            "description": s1.description,
            "prompt": s1.initial_user_prompt,
            "constraints": s1.constraints,
            "vanilla_steps": [serialize_step(st) for st in s1.vanilla_steps],
            "companion_steps": [serialize_step(st) for st in s1.companion_steps]
        },
        {
            "id": s2.id,
            "name": s2.name,
            "description": s2.description,
            "prompt": s2.initial_user_prompt,
            "constraints": s2.constraints,
            "vanilla_steps": [serialize_step(st) for st in s2.vanilla_steps],
            "companion_steps": [serialize_step(st) for st in s2.companion_steps]
        }
    ]


@app.post("/api/evaluate-step")
async def evaluate_step(req: StepEvaluationRequest):
    """
    Evaluates a single turn in the companion lifecycle:
    Pre-Action evaluation -> Ingestion update -> Returns decision + updated memory bank.
    """
    companion = get_or_create_companion(req.session_id, req.constraints)

    # 1. Pre-Action Decision
    decision = companion.evaluate_intervention(turn=req.turn, planned_action=req.command)

    # 2. Determine resulting observation (if injected and corrected, observation changes)
    resulting_observation = req.observation
    if decision.decision == DecisionType.INJECT:
        if "5432" in req.command:
            resulting_observation = "CREATE TABLE auth_users; Migration applied successfully on port 5433."
        elif "/migrations/legacy/" in req.command:
            resulting_observation = "Refactored user models in /app/models.py safely without touching legacy files."

    # 3. Post-Observation Ingestion
    companion.ingest_turn(turn=req.turn, action=req.command, observation=resulting_observation)

    return {
        "turn": req.turn,
        "decision": {
            "action": decision.decision.value,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "reminder": decision.reminder
        },
        "resulting_observation": resulting_observation,
        "memory_bank": companion.memory_bank.model_dump(),
        "telemetry": companion.store.get_telemetry_summary(req.session_id)
    }


@app.post("/api/live-llm")
async def run_live_llm(req: LiveLLMRequest):
    """
    Runs live LLM generation (using Groq Qwen-27B / GPT-OSS) with Proactive Memory Companion injection.
    """
    groq_key = API_KEYS.get("groq", "")
    companion = get_or_create_companion(req.session_id)
    
    # Pre-action intervention check
    final_prompt = req.prompt
    decision = companion.evaluate_intervention(turn=1, planned_action=req.prompt)
    if req.use_companion and decision.decision == DecisionType.INJECT and decision.reminder:
        final_prompt = f"System Reminder: {decision.reminder}\n\nUser Request: {req.prompt}"

    response_text = ""
    model_name = req.model or "qwen/qwen3.8-27b"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if groq_key:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": final_prompt}],
                        "temperature": 0.2,
                        "max_tokens": 400
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data["choices"][0]["message"]["content"]
                else:
                    response_text = f"[Groq API Error {resp.status_code}]: {resp.text}"
            else:
                response_text = "[Notice]: Please ensure Groq API key is present in use-cases/.env."

    except Exception as e:
        response_text = f"[LLM Call Error]: {str(e)}"

    # Ingest output into companion
    companion.ingest_turn(turn=1, action=req.prompt, observation=response_text)

    return {
        "final_prompt": final_prompt,
        "intervention": decision.decision.value,
        "reminder": decision.reminder,
        "llm_response": response_text,
        "memory_bank": companion.memory_bank.model_dump()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
