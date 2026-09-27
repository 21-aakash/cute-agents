from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Intent = Literal[
    "fit_evaluation",
    "resume_tailor",
    "cold_email",
    "career_pivot",
    "doc_qa",
    "synthesis",
    "chitchat",
    "single_doc",
    "comparison",
    "followup",
]
Source = Literal["docs", "web", "memory"]
EvidenceOrigin = Literal["documents", "memory", "web"]
DocumentStatus = Literal["pending", "indexed", "failed"]


class Plan(BaseModel):
    intent: Intent = "fit_evaluation"
    ready_to_research: bool = True
    clarifying_questions: list[str] = Field(default_factory=list)
    sub_queries: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=lambda: ["docs"])
    use_memory: bool = False
    reasoning: str = ""


class Evidence(BaseModel):
    text: str
    origin: EvidenceOrigin
    doc_id: str | None = None
    doc_title: str = "unknown"
    section: str | None = None
    url: str | None = None
    score: float = 0.0
    chunk_index: int | None = None

    def citation(self) -> str:
        if self.origin == "memory":
            return f"[memory: {self.doc_title}]"
        if self.origin == "web" and self.url:
            return f"[web: {self.url}]"
        if self.section and self.section != "body":
            return f"[{self.doc_title} — {self.section}]"
        return f"[{self.doc_title}]"


class Critique(BaseModel):
    correctness: int = 1
    completeness: int = 1
    clarity: int = 1
    average: float = 1.0
    grounded: bool = False
    passed: bool = False
    revision_request: str | None = None
    comments: str = ""


class Turn(BaseModel):
    query: str
    answer: str
    score: float = 0.0


class DocumentMeta(BaseModel):
    id: str
    workspace_id: str
    title: str
    filename: str
    source_type: str
    chunk_count: int = 0
    status: DocumentStatus = "pending"
    created_at: datetime | None = None


class ChatResponse(BaseModel):
    status: Literal["completed", "needs_clarification"] = "completed"
    answer: str = ""
    questions: list[str] = Field(default_factory=list)
    intent: str | None = None
    critique: Critique | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    plan: Plan | None = None
    revisions: int = 0
    run_id: str | None = None
    tool_calls: list[dict] = Field(default_factory=list)
