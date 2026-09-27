from __future__ import annotations

import logging
import secrets
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_workspace
from db.models import Workspace
from db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    api_key: str


@router.post("", response_model=WorkspaceResponse)
def create_workspace(body: CreateWorkspaceRequest, db: Session = Depends(get_db)) -> WorkspaceResponse:
    import secrets

    ws = Workspace(name=body.name, api_key=secrets.token_urlsafe(32))
    db.add(ws)
    db.commit()
    db.refresh(ws)
    logger.info("workspace.created id=%s name=%r", ws.id, ws.name)
    return WorkspaceResponse(id=ws.id, name=ws.name, api_key=ws.api_key)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace_info(
    workspace: Workspace = Depends(get_workspace),
) -> WorkspaceResponse:
    return WorkspaceResponse(id=workspace.id, name=workspace.name, api_key=workspace.api_key)
