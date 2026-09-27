"""
FastAPI Backend for Agent Memory Manager Web Dashboard & Arena.
Serves static UI, handles real-time arena execution, and integrates with LLM providers (Groq, Gemini, OpenRouter).
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

# Mount static folder
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class StepEvaluationRequest(BaseModel):
    session_id: str
    scenario_id: str
    turn: int
    command: str
    observation: str
    constraints: List[str] = []


class LiveLLMRequest(BaseModel):
    provider: str  # "groq" | "gemini" | "openrouter"
    prompt: str
    model: Optional[str] = None
    use_companion: bool = True
    session_id: str = "live_llm_session"


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Agent Memory Manager UI - Initializing Static Files</h1>")


@app.get("/api/scenarios")
async def get_scenarios():
    """Returns available arena scenarios."""
    s1 = get_postgres_port_trap_scenario()
    s2 = get_forbidden_legacy_dir_scenario()
    return [
        {
            "id": "postgres_port_trap",
            "name": s1.name,
            "description": s1.description,
            "prompt": s1.initial_user_prompt,
            "constraints": s1.constraints,
            "steps": [
                {
                    "turn": st.turn,
                    "intent": st.intent,
                    "command": st.command,
                    "observation": st.expected_observation,
                    "is_failing": st.is_failing_command,
                    "violates_constraint": st.violates_constraint
                }
                for st in s1.steps
            ]
        },
        {
            "id": "forbidden_legacy_dir",
            "name": s2.name,
            "description": s2.description,
            "prompt": s2.initial_user_prompt,
            "constraints": s2.constraints,
            "steps": [
                {
                    "turn": st.turn,
                    "intent": st.intent,
                    "command": st.command,
                    "observation": st.expected_observation,
                    "is_failing": st.is_failing_command,
                    "violates_constraint": st.violates_constraint
                }
                for st in s2.steps
            ]
        }
    ]


@app.post("/api/evaluate-step")
async def evaluate_step(req: StepEvaluationRequest):
    """
    Evaluates a single turn in the companion lifecycle:
    Pre-Action evaluation -> Ingestion update -> Returns decision + updated memory bank.
    """
    companion = ProactiveMemoryCompanion(session_id=req.session_id)
    if req.constraints:
        companion.set_user_constraints(req.constraints)

    # 1. Pre-Action Decision
    decision = companion.evaluate_intervention(turn=req.turn, planned_action=req.command)

    # 2. Post-Observation Ingestion
    companion.ingest_turn(turn=req.turn, action=req.command, observation=req.observation)

    return {
        "turn": req.turn,
        "decision": {
            "action": decision.decision.value,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "reminder": decision.reminder
        },
        "memory_bank": companion.memory_bank.model_dump(),
        "telemetry": companion.store.get_telemetry_summary(req.session_id)
    }


@app.post("/api/live-llm")
async def run_live_llm(req: LiveLLMRequest):
    """
    Runs live LLM generation with Proactive Memory Companion injection.
    """
    groq_key = API_KEYS.get("groq", "")
    openrouter_key = API_KEYS.get("opn_router", "") or API_KEYS.get("open_router", "")
    gemini_key = API_KEYS.get("gemini", "")

    companion = ProactiveMemoryCompanion(session_id=req.session_id)
    
    # Pre-action intervention check
    final_prompt = req.prompt
    decision = companion.evaluate_intervention(turn=1, planned_action=req.prompt)
    if req.use_companion and decision.decision == DecisionType.INJECT and decision.reminder:
        final_prompt = f"{req.prompt}\n\n{decision.reminder}"

    response_text = ""
    provider_used = req.provider.lower()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if provider_used == "groq" and groq_key:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": req.model or "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": final_prompt}],
                        "temperature": 0.2
                    }
                )
                data = resp.json()
                response_text = data["choices"][0]["message"]["content"]

            elif provider_used == "openrouter" and openrouter_key:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openrouter_key}"},
                    json={
                        "model": req.model or "meta-llama/llama-3.3-70b-instruct",
                        "messages": [{"role": "user", "content": final_prompt}]
                    }
                )
                data = resp.json()
                response_text = data["choices"][0]["message"]["content"]

            elif provider_used == "gemini" and gemini_key:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                resp = await client.post(
                    url,
                    json={"contents": [{"parts": [{"text": final_prompt}]}]}
                )
                data = resp.json()
                response_text = data["candidates"][0]["content"]["parts"][0]["text"]

            else:
                response_text = f"[Simulation Mode]: No active API key found for {req.provider}. Successfully processed with companion."

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
    print("Starting Agent Memory Manager Live Arena on http://localhost:8000")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
