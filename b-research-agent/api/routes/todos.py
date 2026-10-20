from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_authenticated_user
from db.models import TodoItem, User
from db.session import get_db
from services.llm import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/todos", tags=["todos"])


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    horizon: str = Field(default="daily", description="daily | weekly | monthly | yearly")
    priority: str = Field(default="medium", description="low | medium | high")
    due_date: datetime | None = None
    tags: list[str] = Field(default_factory=list)


class TodoUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    horizon: str | None = None
    priority: str | None = None
    status: str | None = None  # pending | completed | archived
    due_date: datetime | None = None
    tags: list[str] | None = None


class TodoOut(BaseModel):
    id: str
    user_id: str
    title: str
    description: str | None = None
    horizon: str
    status: str
    priority: str
    tags: list[str] = []
    due_date: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class ParseVoiceRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw transcription or natural language ramble")


class ParseVoiceResponse(BaseModel):
    extracted_count: int
    summary: str
    todos: list[TodoOut]


def _to_out(item: TodoItem) -> TodoOut:
    return TodoOut(
        id=str(item.id),
        user_id=str(item.user_id),
        title=item.title,
        description=item.description,
        horizon=item.horizon or "daily",
        status=item.status or "pending",
        priority=item.priority or "medium",
        tags=item.tags or [],
        due_date=item.due_date,
        completed_at=item.completed_at,
        created_at=item.created_at,
    )


@router.get("", response_model=list[TodoOut])
def list_todos(
    horizon: str | None = Query(None, description="Filter by horizon: daily, weekly, monthly, yearly"),
    status_filter: str | None = Query(None, alias="status", description="pending, completed, or all"),
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    query = db.query(TodoItem).filter(TodoItem.user_id == user.id)

    if horizon and horizon != "all":
        query = query.filter(TodoItem.horizon == horizon.lower())

    if status_filter and status_filter != "all":
        query = query.filter(TodoItem.status == status_filter.lower())
    else:
        # Default: hide archived
        query = query.filter(TodoItem.status != "archived")

    # Order: pending first, then by priority, then created_at desc
    items = query.order_by(
        TodoItem.status.asc(),
        TodoItem.created_at.desc(),
    ).all()

    return [_to_out(item) for item in items]


@router.post("", response_model=TodoOut, status_code=status.HTTP_201_CREATED)
def create_todo(
    req: TodoCreate,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    horizon_clean = req.horizon.lower() if req.horizon.lower() in ("daily", "weekly", "monthly", "yearly") else "daily"
    priority_clean = req.priority.lower() if req.priority.lower() in ("low", "medium", "high") else "medium"

    item = TodoItem(
        user_id=user.id,
        title=req.title.strip(),
        description=req.description.strip() if req.description else None,
        horizon=horizon_clean,
        status="pending",
        priority=priority_clean,
        tags=req.tags,
        due_date=req.due_date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(
    todo_id: uuid.UUID,
    req: TodoUpdate,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    item = db.query(TodoItem).filter(TodoItem.id == todo_id, TodoItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="To-do item not found")

    if req.title is not None:
        item.title = req.title.strip()
    if req.description is not None:
        item.description = req.description.strip()
    if req.horizon is not None and req.horizon.lower() in ("daily", "weekly", "monthly", "yearly"):
        item.horizon = req.horizon.lower()
    if req.priority is not None and req.priority.lower() in ("low", "medium", "high"):
        item.priority = req.priority.lower()
    if req.tags is not None:
        item.tags = req.tags
    if req.due_date is not None:
        item.due_date = req.due_date

    if req.status is not None:
        new_status = req.status.lower()
        if new_status in ("pending", "completed", "archived"):
            if new_status == "completed" and item.status != "completed":
                item.completed_at = datetime.now(timezone.utc)
            elif new_status != "completed":
                item.completed_at = None
            item.status = new_status

    db.commit()
    db.refresh(item)
    return _to_out(item)


@router.delete("/{todo_id}")
def delete_todo(
    todo_id: uuid.UUID,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    item = db.query(TodoItem).filter(TodoItem.id == todo_id, TodoItem.user_id == user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="To-do item not found")

    db.delete(item)
    db.commit()
    return {"ok": True, "message": "To-do item deleted"}


@router.get("/stats")
def get_todo_stats(
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    all_items = db.query(TodoItem).filter(TodoItem.user_id == user.id).all()

    stats = {
        "total": len(all_items),
        "completed": sum(1 for i in all_items if i.status == "completed"),
        "pending": sum(1 for i in all_items if i.status == "pending"),
        "daily": {
            "total": sum(1 for i in all_items if i.horizon == "daily"),
            "completed": sum(1 for i in all_items if i.horizon == "daily" and i.status == "completed"),
        },
        "weekly": {
            "total": sum(1 for i in all_items if i.horizon == "weekly"),
            "completed": sum(1 for i in all_items if i.horizon == "weekly" and i.status == "completed"),
        },
        "monthly": {
            "total": sum(1 for i in all_items if i.horizon == "monthly"),
            "completed": sum(1 for i in all_items if i.horizon == "monthly" and i.status == "completed"),
        },
        "yearly": {
            "total": sum(1 for i in all_items if i.horizon == "yearly"),
            "completed": sum(1 for i in all_items if i.horizon == "yearly" and i.status == "completed"),
        },
    }
    return stats


@router.post("/parse-input", response_model=ParseVoiceResponse)
def parse_voice_or_text_todos(
    req: ParseVoiceRequest,
    user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    """AI Agent endpoint: transforms unstructured voice/text rambles into 4-horizon actionable to-dos."""
    raw_text = req.text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    system_prompt = (
        "You are an expert executive productivity agent. The user will provide a raw voice transcription "
        "or brain-dump of their tasks, thoughts, and plans.\n"
        "Your job is to parse and decompose this ramble into clean, actionable items across 4 temporal horizons:\n"
        "- 'daily': Tasks to do TODAY or within the next 24 hours.\n"
        "- 'weekly': Tasks, deliverables, or habits to achieve THIS WEEK.\n"
        "- 'monthly': Strategic goals or projects for THIS MONTH.\n"
        "- 'yearly': Big vision, career milestones, or high-level goals for THIS YEAR.\n\n"
        "Assign priority: 'high', 'medium', or 'low'.\n"
        "Extract tags (e.g. ['work', 'health', 'finance', 'errand', 'family']).\n"
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "summary": "Short 1-sentence friendly breakdown of what was captured",\n'
        '  "items": [\n'
        '    {\n'
        '      "title": "Clear actionable task title",\n'
        '      "description": "Optional context or null",\n'
        '      "horizon": "daily" | "weekly" | "monthly" | "yearly",\n'
        '      "priority": "high" | "medium" | "low",\n'
        '      "tags": ["tag1", "tag2"]\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    extracted_items: list[dict[str, Any]] = []
    summary = "Parsed your thoughts into actionable items."

    try:
        llm = LLMClient()
        response_text = llm.complete(system=system_prompt, user=raw_text, temperature=0.1)

        # Parse JSON from response
        clean_json = response_text.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.removeprefix("```json").removesuffix("```").strip()
        elif clean_json.startswith("```"):
            clean_json = clean_json.removeprefix("```").removesuffix("```").strip()

        data = json.loads(clean_json)
        summary = data.get("summary", summary)
        extracted_items = data.get("items", [])
    except Exception as e:
        logger.warning("LLM parsing failed or unavailable (%s). Falling back to heuristic parser.", e)
        # Heuristic fallback for offline/no-key mode
        lines = [line.strip("- *• ") for line in raw_text.split("\n") if line.strip()]
        for line in lines:
            lower = line.lower()
            horizon = "daily"
            if any(w in lower for w in ("this month", "monthly", "by next month")):
                horizon = "monthly"
            elif any(w in lower for w in ("this year", "annual", "yearly", "long term")):
                horizon = "yearly"
            elif any(w in lower for w in ("this week", "weekly", "by friday", "weekend")):
                horizon = "weekly"

            priority = "high" if any(w in lower for w in ("urgent", "asap", "important", "critical")) else "medium"
            extracted_items.append({
                "title": line,
                "description": None,
                "horizon": horizon,
                "priority": priority,
                "tags": ["quick-capture"],
            })

    created_todos: list[TodoItem] = []
    for item_data in extracted_items:
        title = item_data.get("title", "").strip()
        if not title:
            continue
        horizon = item_data.get("horizon", "daily")
        if horizon not in ("daily", "weekly", "monthly", "yearly"):
            horizon = "daily"
        priority = item_data.get("priority", "medium")
        if priority not in ("low", "medium", "high"):
            priority = "medium"

        todo = TodoItem(
            user_id=user.id,
            title=title,
            description=item_data.get("description"),
            horizon=horizon,
            status="pending",
            priority=priority,
            tags=item_data.get("tags") or [],
        )
        db.add(todo)
        created_todos.append(todo)

    db.commit()
    for todo in created_todos:
        db.refresh(todo)

    logger.info("Parsed and created %d to-dos for user %s", len(created_todos), user.email)

    return ParseVoiceResponse(
        extracted_count=len(created_todos),
        summary=summary,
        todos=[_to_out(t) for t in created_todos],
    )
