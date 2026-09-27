from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_runner, get_workspace
from db.models import ChatRun, EvalRun, EvalSample, Workspace
from db.session import get_db
from services.agentic_eval import public_sample_scores
from services.ragas_eval import run_golden_eval, run_recent_eval
from services.workspace_docs import list_indexed_documents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workspaces/{workspace_id}/evals", tags=["evals"])


class EvalRunRequest(BaseModel):
    mode: str = Field(default="golden", pattern="^(golden|recent)$")
    limit: int = Field(default=5, ge=1, le=20)


class EvalSampleOut(BaseModel):
    id: str
    question: str
    answer: str
    ground_truth: str
    contexts: list[str]
    scores: dict[str, float | None]
    chat_run_id: str | None = None


class EvalRunSummary(BaseModel):
    id: str
    mode: str
    status: str
    sample_count: int
    metrics_avg: dict[str, float | None]
    duration_ms: int | None
    created_at: datetime | None
    error_message: str | None = None


class EvalRunDetail(EvalRunSummary):
    samples: list[EvalSampleOut] = Field(default_factory=list)


def _summary(row: EvalRun) -> EvalRunSummary:
    return EvalRunSummary(
        id=str(row.id),
        mode=row.mode,
        status=row.status,
        sample_count=row.sample_count,
        metrics_avg=row.metrics_avg or {},
        duration_ms=row.duration_ms,
        created_at=row.created_at,
        error_message=row.error_message,
    )


def _detail(row: EvalRun) -> EvalRunDetail:
    base = _summary(row)
    samples = [
        EvalSampleOut(
            id=str(s.id),
            question=s.question,
            answer=s.answer,
            ground_truth=s.ground_truth,
            contexts=s.contexts or [],
            scores=public_sample_scores(s.scores or {}),
            chat_run_id=str(s.chat_run_id) if s.chat_run_id else None,
        )
        for s in row.samples
    ]
    return EvalRunDetail(**base.model_dump(), samples=samples)


def _persist_eval(db: Session, workspace_id: uuid.UUID, mode: str, result, *, status: str = "completed", error: str | None = None) -> EvalRun:
    run = EvalRun(
        workspace_id=workspace_id,
        mode=mode,
        status=status,
        sample_count=len(result.samples),
        metrics_avg=result.metrics_avg,
        duration_ms=result.duration_ms,
        error_message=error,
    )
    db.add(run)
    db.flush()
    for sample in result.samples:
        db.add(
            EvalSample(
                eval_run_id=run.id,
                question=sample.question,
                answer=sample.answer,
                ground_truth=sample.ground_truth,
                contexts=sample.contexts,
                scores=sample.scores,
                chat_run_id=uuid.UUID(sample.chat_run_id) if sample.chat_run_id else None,
            )
        )
    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[EvalRunSummary])
def list_eval_runs(
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> list[EvalRunSummary]:
    rows = (
        db.query(EvalRun)
        .filter(EvalRun.workspace_id == workspace.id)
        .order_by(EvalRun.created_at.desc())
        .limit(20)
        .all()
    )
    return [_summary(r) for r in rows]


@router.get("/{eval_id}", response_model=EvalRunDetail)
def get_eval_run(
    eval_id: uuid.UUID,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> EvalRunDetail:
    row = db.get(EvalRun, eval_id)
    if row is None or row.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Eval run not found")
    return _detail(row)


@router.post("/run", response_model=EvalRunDetail)
def run_eval(
    body: EvalRunRequest,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> EvalRunDetail:
    logger.info("eval.run start workspace=%s mode=%s limit=%d", workspace.id, body.mode, body.limit)
    try:
        if body.mode == "golden":
            indexed = list_indexed_documents(db, workspace.id)
            if not indexed:
                raise HTTPException(status_code=400, detail="Upload and index documents before running golden evals.")
            result = run_golden_eval(
                runner=get_runner(),
                workspace_id=str(workspace.id),
                indexed_documents=indexed,
            )
        else:
            runs = (
                db.query(ChatRun)
                .filter(ChatRun.workspace_id == workspace.id)
                .order_by(ChatRun.created_at.desc())
                .limit(body.limit)
                .all()
            )
            if not runs:
                raise HTTPException(status_code=400, detail="No chat runs to evaluate yet.")
            payload = [
                {
                    "id": str(r.id),
                    "query": r.query,
                    "answer": r.answer or "",
                    "evidence": r.evidence or [],
                    "tool_calls": r.tool_calls or [],
                    "critique": r.critique or {},
                }
                for r in runs
            ]
            result = run_recent_eval(chat_runs=payload)

        row = _persist_eval(db, workspace.id, body.mode, result)
        logger.info(
            "eval.run ok workspace=%s eval=%s samples=%d duration_ms=%s",
            workspace.id,
            row.id,
            row.sample_count,
            row.duration_ms,
        )
        return _detail(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("eval.run failed workspace=%s", workspace.id)
        failed = EvalRun(
            workspace_id=workspace.id,
            mode=body.mode,
            status="failed",
            sample_count=0,
            metrics_avg={},
            error_message=str(exc)[:500],
        )
        db.add(failed)
        db.commit()
        db.refresh(failed)
        raise HTTPException(status_code=500, detail=str(exc)[:200]) from exc
