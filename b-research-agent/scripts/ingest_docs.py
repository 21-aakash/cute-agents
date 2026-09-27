#!/usr/bin/env python3
"""CLI bulk document ingest."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from db.session import SessionLocal, init_db
from db.models import Document, Workspace
from services.embedder import get_embedder
from services.ingest import chunk_text, load_text
from services.vectorstore import VectorStore


def ingest_path(workspace_id: str, path: Path) -> int:
    suffix = path.suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        print(f"Skip unsupported: {path}")
        return 0

    db = SessionLocal()
    doc = Document(
        workspace_id=uuid.UUID(workspace_id),
        title=path.stem,
        filename=path.name,
        source_type=suffix.lstrip("."),
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    title, text = load_text(path)
    chunks = chunk_text(text, doc_title=title, source_type=doc.source_type)
    vs = VectorStore()
    count = vs.upsert_document_chunks(
        workspace_id=workspace_id,
        doc_id=str(doc.id),
        chunks=chunks,
        embedder=get_embedder(),
    )
    doc.title = title
    doc.chunk_count = count
    doc.status = "indexed"
    db.commit()
    db.close()
    print(f"Ingested {path.name}: {count} chunks")
    return count


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/ingest_docs.py <workspace_id> <file_or_dir> [...]")
        sys.exit(1)

    init_db()
    workspace_id = sys.argv[1]
    paths = sys.argv[2:]
    total = 0
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file():
                    total += ingest_path(workspace_id, f)
        elif path.is_file():
            total += ingest_path(workspace_id, path)
    print(f"Done. Total chunks: {total}")


if __name__ == "__main__":
    main()
