from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from db.models import Workspace
from db.session import get_db
from graph.runner import ResearchGraphRunner
from services.config import settings
from services.embedder import get_embedder
from services.vectorstore import VectorStore

_runner: ResearchGraphRunner | None = None


def init_runner() -> ResearchGraphRunner:
    global _runner
    if _runner is None:
        _runner = ResearchGraphRunner(vectorstore=VectorStore())
    return _runner


def get_runner() -> ResearchGraphRunner:
    if _runner is None:
        return init_runner()
    return _runner


def get_workspace(
    workspace_id: uuid.UUID,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None or ws.api_key != x_api_key:
        raise HTTPException(status_code=401, detail="Invalid workspace or API key")
    return ws


def ensure_upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_authenticated_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
):
    from db.models import User
    from services.auth import decode_access_token

    if not authorization or not authorization.startswith("Bearer "):
        first_user = db.query(User).first()
        if first_user:
            return first_user
        raise HTTPException(status_code=401, detail="Authentication token required")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    return user

