from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import ensure_upload_dir, get_workspace
from db.models import Document, Workspace
from db.session import get_db
from domain.models import Evidence
from services.embedder import get_embedder
from services.ingest import chunk_text, load_text
from services.tools import ResearchToolkit
from services.vectorstore import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    source_type: str
    chunk_count: int
    status: str


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class SearchHitResponse(BaseModel):
    text: str
    doc_id: str | None = None
    doc_title: str
    section: str | None = None
    score: float
    chunk_index: int | None = None


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    docs = db.query(Document).filter(Document.workspace_id == workspace.id).all()
    return [
        DocumentResponse(
            id=d.id,
            title=d.title,
            filename=d.filename,
            source_type=d.source_type,
            chunk_count=d.chunk_count,
            status=d.status,
        )
        for d in docs
    ]


@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Supported types: .pdf, .txt, .md")

    upload_dir = ensure_upload_dir() / str(workspace.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / (file.filename or "upload")
    content = await file.read()
    dest.write_bytes(content)

    doc = Document(
        workspace_id=workspace.id,
        title=dest.stem,
        filename=file.filename or dest.name,
        source_type=suffix.lstrip("."),
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        title, text = load_text(dest)
        chunks = chunk_text(text, doc_title=title, source_type=doc.source_type)
        vs = VectorStore()
        count = vs.upsert_document_chunks(
            workspace_id=str(workspace.id),
            doc_id=str(doc.id),
            chunks=chunks,
            embedder=get_embedder(),
        )
        doc.title = title
        doc.chunk_count = count
        doc.status = "indexed"
        db.commit()
    except Exception as exc:
        logger.exception("Document indexing failed for %s", doc.id)
        doc.status = "failed"
        doc.error_message = str(exc)[:500]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}") from exc

    logger.info(
        "Indexed document %s (%s) — %d chunks in workspace %s",
        doc.id,
        doc.filename,
        doc.chunk_count,
        workspace.id,
    )
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        source_type=doc.source_type,
        chunk_count=doc.chunk_count,
        status=doc.status,
    )


@router.post("/search", response_model=list[SearchHitResponse])
def search_knowledge_base(
    body: SearchRequest,
    workspace: Workspace = Depends(get_workspace),
) -> list[SearchHitResponse]:
    """Semantic search over indexed documents (no LLM). Used by UI smoke tests and E2E."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    tools = ResearchToolkit(
        VectorStore(),
        get_embedder(),
        str(workspace.id),
    )
    result = tools.doc_search(body.query.strip(), top_k=body.top_k)
    return [_evidence_to_search_hit(e) for e in result.evidence]


def _evidence_to_search_hit(evidence: Evidence) -> SearchHitResponse:
    return SearchHitResponse(
        text=evidence.text,
        doc_id=evidence.doc_id,
        doc_title=evidence.doc_title,
        section=evidence.section,
        score=evidence.score,
        chunk_index=evidence.chunk_index,
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: uuid.UUID,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> dict:
    doc = db.get(Document, doc_id)
    if doc is None or doc.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Document not found")
    VectorStore().delete_document_chunks(str(workspace.id), str(doc.id))
    db.delete(doc)
    db.commit()
    return {"deleted": str(doc_id)}
