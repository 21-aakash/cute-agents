from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from db.models import Document


def list_indexed_documents(db: Session, workspace_id: uuid.UUID) -> list[dict]:
    docs = (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id, Document.status == "indexed")
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        {
            "title": d.title,
            "filename": d.filename,
            "source_type": d.source_type,
            "chunk_count": d.chunk_count,
        }
        for d in docs
    ]


def format_doc_catalog(docs: list[dict]) -> str:
    if not docs:
        return "Indexed documents: none (workspace knowledge base is empty)."
    lines = [
        f"- {d['title']} (file: {d['filename']}, {d['chunk_count']} chunks)"
        for d in docs
    ]
    return "Indexed documents in workspace knowledge base:\n" + "\n".join(lines)
