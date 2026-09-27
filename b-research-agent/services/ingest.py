from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from services.config import settings

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150


def load_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return path.stem, "\n\n".join(pages)
    if suffix in {".doc", ".docx"}:
        try:
            import docx
            doc = docx.Document(str(path))
            text = "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return path.stem, text
        except Exception as e:
            raise ValueError(f"Could not read DOCX file {path.name}: {e}") from e
    if suffix in {".txt", ".md", ".json", ".csv"}:
        return path.stem, path.read_text(encoding="utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(text: str, doc_title: str, source_type: str) -> list[dict]:
    sections = _split_sections(text)
    chunks: list[dict] = []
    idx = 0
    for section_name, section_text in sections:
        for piece in _window_chunks(section_text):
            chunks.append(
                {
                    "text": piece,
                    "doc_title": doc_title,
                    "source_type": source_type,
                    "section": section_name,
                    "chunk_index": idx,
                }
            )
            idx += 1
    return chunks


def _split_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    sections: list[tuple[str, str]] = []
    current_name = "body"
    current_lines: list[str] = []
    heading = re.compile(r"^#{1,3}\s+(.+)$")

    for line in lines:
        match = heading.match(line.strip())
        if match:
            if current_lines:
                sections.append((current_name, "\n".join(current_lines).strip()))
            current_name = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_name, "\n".join(current_lines).strip()))

    if not sections:
        sections.append(("body", text.strip()))
    return sections


def _window_chunks(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + CHUNK_SIZE)
        chunk = text[start:end]
        if end < len(text):
            boundary = chunk.rfind(". ")
            if boundary > CHUNK_SIZE // 2:
                end = start + boundary + 1
                chunk = text[start:end]
        chunks.append(chunk.strip())
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return [c for c in chunks if c]
