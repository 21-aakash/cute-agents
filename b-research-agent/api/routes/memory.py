from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import get_workspace
from db.models import Workspace
from services.vectorstore import VectorStore

router = APIRouter(prefix="/workspaces/{workspace_id}/memory", tags=["memory"])


@router.delete("")
def reset_memory(workspace: Workspace = Depends(get_workspace)) -> dict:
    VectorStore().reset_memory(str(workspace.id))
    return {"reset": True}
