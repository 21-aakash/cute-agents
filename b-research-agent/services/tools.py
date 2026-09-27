from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from domain.models import Evidence
from services.config import settings
from services.embedder import Embedder
from services.vectorstore import VectorStore
from services.web_search import search_web

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    tool: str
    query: str
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class KbProbeResult:
    relevant: bool
    top_score: float


class ResearchToolkit:
    def __init__(self, vectorstore: VectorStore, embedder: Embedder, workspace_id: str) -> None:
        self.vectorstore = vectorstore
        self.embedder = embedder
        self.workspace_id = workspace_id
        self.log: list[dict] = []

    def kb_probe(self, query: str) -> KbProbeResult:
        """Single-hit relevance gate — no below-threshold fallback."""
        vector = self.embedder.embed_query(query)
        hits = self.vectorstore.search_documents(self.workspace_id, vector, top_k=1)
        if not hits:
            return KbProbeResult(relevant=False, top_score=0.0)
        score = float(hits[0].score)
        return KbProbeResult(relevant=score >= settings.min_score, top_score=round(score, 3))

    def doc_search(self, query: str, top_k: int | None = None) -> ToolResult:
        top_k = top_k or settings.top_k
        vector = self.embedder.embed_query(query)
        hits = self.vectorstore.search_documents(self.workspace_id, vector, top_k)
        evidence = [_doc_hit_to_evidence(hit) for hit in hits if hit.score >= settings.min_score]
        if not evidence and hits:
            # Vague queries (e.g. "summarise the resume") may score slightly below threshold
            evidence = [_doc_hit_to_evidence(hits[0])]
        self._record("doc_search", query, len(evidence))
        return ToolResult(tool="doc_search", query=query, evidence=evidence)

    def memory_search(self, query: str, top_k: int | None = None) -> ToolResult:
        top_k = top_k or settings.memory_top_k
        vector = self.embedder.embed_query(query)
        hits = self.vectorstore.search_memory(self.workspace_id, vector, top_k)
        evidence = [_memory_hit_to_evidence(hit) for hit in hits if hit.score >= settings.min_score]
        self._record("memory_search", query, len(evidence))
        return ToolResult(tool="memory_search", query=query, evidence=evidence)

    def web_search(self, query: str, top_k: int | None = None) -> ToolResult:
        limit = top_k or settings.web_top_k
        try:
            results = search_web(query, top_k=limit)
            evidence = []
            for r in results:
                body = r.get("body") or r.get("snippet") or r.get("description") or ""
                href = r.get("href") or r.get("url") or r.get("link")
                title = r.get("title") or "web result"
                if not body and not href:
                    continue
                evidence.append(
                    Evidence(
                        text=body or title,
                        origin="web",
                        doc_title=title,
                        url=href,
                        score=0.5,
                    )
                )
        except Exception as exc:
            logger.exception("web_search failed query=%r", query[:80])
            evidence = [
                Evidence(
                    text=f"Web search unavailable: {exc}",
                    origin="web",
                    doc_title="web error",
                    score=0.0,
                )
            ]
        self._record("web_search", query, len(evidence))
        return ToolResult(tool="web_search", query=query, evidence=evidence)

    def github_search(self, query: str) -> ToolResult:
        """Fetch public GitHub repository details and README files."""
        import httpx
        evidence: list[Evidence] = []
        clean_query = query.replace("https://github.com/", "").strip("/")
        parts = clean_query.split("/")
        headers = {"User-Agent": "CareerOps-AI"}
        try:
            with httpx.Client(timeout=10.0, headers=headers) as client:
                if len(parts) == 1 and parts[0]:
                    # User profile repos
                    user = parts[0]
                    resp = client.get(f"https://api.github.com/users/{user}/repos?sort=updated&per_page=6")
                    if resp.status_code == 200:
                        repos = resp.json()
                        summary_lines = [f"GitHub Profile: https://github.com/{user}\nTop Public Repositories:"]
                        for r in repos:
                            summary_lines.append(
                                f"- {r.get('name')}: {r.get('description') or 'No description'} (Lang: {r.get('language')}, Stars: {r.get('stargazers_count', 0)})"
                            )
                        evidence.append(
                            Evidence(
                                text="\n".join(summary_lines),
                                origin="web",
                                doc_title=f"GitHub - {user}",
                                url=f"https://github.com/{user}",
                                score=0.85,
                            )
                        )
                elif len(parts) >= 2:
                    # Specific repo
                    user, repo = parts[0], parts[1]
                    resp = client.get(f"https://api.github.com/repos/{user}/{repo}")
                    if resp.status_code == 200:
                        repo_data = resp.json()
                        desc = repo_data.get("description") or "No description"
                        lang = repo_data.get("language") or "N/A"
                        stars = repo_data.get("stargazers_count", 0)
                        evidence.append(
                            Evidence(
                                text=f"GitHub Repo: {user}/{repo}\nDescription: {desc}\nPrimary Language: {lang}\nStars: {stars}",
                                origin="web",
                                doc_title=f"GitHub - {user}/{repo}",
                                url=f"https://github.com/{user}/{repo}",
                                score=0.9,
                            )
                        )
        except Exception as exc:
            logger.warning("github_search failed for query=%r: %s", query, exc)

        self._record("github_search", query, len(evidence))
        return ToolResult(tool="github_search", query=query, evidence=evidence)

    def _record(self, tool: str, query: str, count: int) -> None:
        self.log.append({"tool": tool, "query": query, "hit_count": count, "ts": time.time()})


def _doc_hit_to_evidence(hit) -> Evidence:
    p = hit.payload or {}
    return Evidence(
        text=p.get("text", ""),
        origin="documents",
        doc_id=p.get("doc_id"),
        doc_title=p.get("doc_title", "unknown"),
        section=p.get("section"),
        score=round(float(hit.score), 3),
        chunk_index=p.get("chunk_index"),
    )


def _memory_hit_to_evidence(hit) -> Evidence:
    p = hit.payload or {}
    return Evidence(
        text=p.get("finding", ""),
        origin="memory",
        doc_id=p.get("session_id"),
        doc_title=p.get("query", "earlier finding"),
        section="long-term memory",
        score=round(float(hit.score), 3),
    )


def dedupe_evidence(items: list[Evidence]) -> list[Evidence]:
    seen: dict[tuple, Evidence] = {}
    for item in items:
        key = (item.origin, item.doc_id, item.chunk_index, item.url, item.text[:80])
        if key not in seen or item.score > seen[key].score:
            seen[key] = item
    return sorted(seen.values(), key=lambda e: e.score, reverse=True)


def format_evidence(evidence: list[Evidence], max_chars: int = 4000) -> str:
    lines: list[str] = []
    used = 0
    for i, ev in enumerate(evidence, start=1):
        label = f"[{i}] {ev.citation()}"
        block = f"{label}\n{ev.text.strip()}\n"
        if used + len(block) > max_chars:
            break
        lines.append(block)
        used += len(block)
    return "\n".join(lines) if lines else "No relevant passages were found."
