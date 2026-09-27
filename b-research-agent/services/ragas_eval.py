from __future__ import annotations

import asyncio
import json
import logging
import math
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from services.agentic_eval import aggregate_agentic, public_sample_scores, score_agentic_sample

logger = logging.getLogger(__name__)

RAGAS_KEYS = ("faithfulness", "answer_relevancy", "context_precision")

DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "scripts" / "fixtures" / "eval_dataset.json"


def _ensure_ragas_imports() -> None:
    """RAGAS pulls optional VertexAI; stub it when absent."""
    if "langchain_community.chat_models.vertexai" not in sys.modules:
        stub = ModuleType("langchain_community.chat_models.vertexai")
        stub.ChatVertexAI = type("ChatVertexAI", (), {})  # type: ignore[attr-defined]
        sys.modules["langchain_community.chat_models.vertexai"] = stub


@dataclass
class EvalSampleInput:
    question: str
    ground_truth: str = ""
    chat_run_id: str | None = None


@dataclass
class EvalSampleResult:
    question: str
    answer: str
    ground_truth: str
    contexts: list[str]
    scores: dict[str, float | None]
    chat_run_id: str | None = None


@dataclass
class EvalRunResult:
    samples: list[EvalSampleResult] = field(default_factory=list)
    metrics_avg: dict[str, float | None] = field(default_factory=dict)
    duration_ms: int = 0


def load_golden_dataset(path: Path | None = None) -> list[EvalSampleInput]:
    dataset_path = path or DEFAULT_DATASET
    raw = json.loads(dataset_path.read_text())
    return [
        EvalSampleInput(
            question=item["question"],
            ground_truth=item.get("ground_truth", ""),
        )
        for item in raw
    ]


def _contexts_from_evidence(evidence: list[dict]) -> list[str]:
    doc_contexts = [
        e.get("text", "").strip()
        for e in evidence
        if e.get("origin") == "documents" and e.get("text")
    ]
    if doc_contexts:
        return doc_contexts
    return [e.get("text", "").strip() for e in evidence if e.get("text")]


def _avg_scores(samples: list[EvalSampleResult]) -> dict[str, float | None]:
    ragas: dict[str, float | None] = {}
    for key in RAGAS_KEYS:
        vals = [s.scores[key] for s in samples if s.scores.get(key) is not None]
        ragas[key] = round(sum(vals) / len(vals), 4) if vals else None

    agentic_raw = [
        {k: v for k, v in s.scores.items() if k in {
            "completed", "critic_grounded", "critic_passed", "evidence_found",
            "doc_search_hit", "tool_invoked", "tool_error",
            "_tool_call_count", "_tool_error_count",
        }}
        for s in samples
    ]
    agentic = aggregate_agentic(agentic_raw)
    return {**ragas, **agentic}


def _merge_scores(ragas: dict[str, float | None], agentic: dict[str, float]) -> dict[str, float | None]:
    return {**agentic, **ragas}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return round(f, 4)


class RagasEvaluator:
    def __init__(self) -> None:
        _ensure_ragas_imports()
        from ragas.embeddings.base import embedding_factory
        from ragas.llms import llm_factory

        from services.config import settings
        from services.openai_client import get_openai_client

        sync_client = get_openai_client()
        from openai import AsyncOpenAI

        async_client = AsyncOpenAI(
            api_key=sync_client.api_key,
            base_url=str(sync_client.base_url),
            timeout=settings.openai_timeout,
            max_retries=2,
        )
        model = settings.model_for("eval")
        self._llm = llm_factory(model, client=async_client)
        self._embeddings = embedding_factory(
            "openai",
            model=settings.openai_embedding_model,
            client=async_client,
        )
        from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, Faithfulness

        self._faithfulness = Faithfulness(llm=self._llm)
        self._answer_relevancy = AnswerRelevancy(llm=self._llm, embeddings=self._embeddings)
        self._context_precision = ContextPrecision(llm=self._llm)

    async def _score_sample(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
    ) -> dict[str, float | None]:
        scores: dict[str, float | None] = {}
        if not answer.strip():
            return {"faithfulness": None, "answer_relevancy": None, "context_precision": None}
        real_contexts = [c for c in contexts if c and c != "No retrieved context."]
        if not real_contexts:
            return {
                "faithfulness": None,
                "answer_relevancy": _safe_float(
                    (await self._answer_relevancy.ascore(question, answer)).value
                ) if answer.strip() else None,
                "context_precision": None,
            }
        contexts = real_contexts

        try:
            scores["faithfulness"] = _safe_float(
                (await self._faithfulness.ascore(question, answer, contexts)).value
            )
        except Exception:
            logger.exception("faithfulness failed question=%r", question[:80])
            scores["faithfulness"] = None

        try:
            scores["answer_relevancy"] = _safe_float(
                (await self._answer_relevancy.ascore(question, answer)).value
            )
        except Exception:
            logger.exception("answer_relevancy failed question=%r", question[:80])
            scores["answer_relevancy"] = None

        if ground_truth.strip():
            try:
                scores["context_precision"] = _safe_float(
                    (
                        await self._context_precision.ascore(
                            question,
                            ground_truth,
                            contexts,
                        )
                    ).value
                )
            except Exception:
                logger.exception("context_precision failed question=%r", question[:80])
                scores["context_precision"] = None
        else:
            scores["context_precision"] = None

        return scores

    async def score_batch(self, rows: list[dict[str, Any]]) -> list[dict[str, float | None]]:
        tasks = [
            self._score_sample(
                question=row["question"],
                answer=row["answer"],
                contexts=row["contexts"],
                ground_truth=row.get("ground_truth", ""),
            )
            for row in rows
        ]
        return await asyncio.gather(*tasks)

    def score_batch_sync(self, rows: list[dict[str, Any]]) -> list[dict[str, float | None]]:
        return asyncio.run(self.score_batch(rows))


def run_golden_eval(
    *,
    runner,
    workspace_id: str,
    indexed_documents: list[dict],
    dataset: list[EvalSampleInput] | None = None,
) -> EvalRunResult:
    """Run pipeline on golden questions, then score with RAGAS."""
    start = time.perf_counter()
    samples_in = dataset or load_golden_dataset()
    pipeline_rows: list[dict[str, Any]] = []
    meta: list[EvalSampleResult] = []
    agentic_rows: list[dict[str, float]] = []

    for item in samples_in:
        session_id = str(uuid.uuid4())
        result = runner.run(
            query=item.question,
            workspace_id=workspace_id,
            session_id=session_id,
            conversation_turns=[],
            conversation_summary="",
            indexed_documents=indexed_documents,
            web_search_enabled=False,
        )
        result["status"] = "completed"
        answer = result.get("answer", "") or ""
        evidence = result.get("evidence") or []
        contexts = _contexts_from_evidence(evidence)
        agentic = score_agentic_sample(result)
        agentic_rows.append(agentic)
        pipeline_rows.append(
            {
                "question": item.question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": item.ground_truth,
            }
        )
        meta.append(
            EvalSampleResult(
                question=item.question,
                answer=answer,
                ground_truth=item.ground_truth,
                contexts=contexts,
                scores=agentic,
            )
        )

    evaluator = RagasEvaluator()
    score_rows = evaluator.score_batch_sync(pipeline_rows)
    for sample, ragas_scores, agentic in zip(meta, score_rows, agentic_rows, strict=True):
        sample.scores = _merge_scores(ragas_scores, agentic)

    duration_ms = int((time.perf_counter() - start) * 1000)
    return EvalRunResult(
        samples=meta,
        metrics_avg=_avg_scores(meta),
        duration_ms=duration_ms,
    )


def run_recent_eval(*, chat_runs: list[dict], ground_truth_map: dict[str, str] | None = None) -> EvalRunResult:
    """Score existing chat runs (no pipeline re-run)."""
    start = time.perf_counter()
    ground_truth_map = ground_truth_map or {}
    rows: list[dict[str, Any]] = []
    meta: list[EvalSampleResult] = []
    agentic_rows: list[dict[str, float]] = []

    for run in chat_runs:
        question = run.get("query", "")
        answer = run.get("answer", "") or ""
        evidence = run.get("evidence") or []
        contexts = _contexts_from_evidence(evidence)
        ground_truth = ground_truth_map.get(question, "")
        agentic = score_agentic_sample(run)
        agentic_rows.append(agentic)
        rows.append(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": ground_truth,
            }
        )
        meta.append(
            EvalSampleResult(
                question=question,
                answer=answer,
                ground_truth=ground_truth,
                contexts=contexts,
                scores=agentic,
                chat_run_id=run.get("id"),
            )
        )

    if not rows:
        return EvalRunResult(samples=[], metrics_avg={}, duration_ms=0)

    evaluator = RagasEvaluator()
    score_rows = evaluator.score_batch_sync(rows)
    for sample, ragas_scores, agentic in zip(meta, score_rows, agentic_rows, strict=True):
        sample.scores = _merge_scores(ragas_scores, agentic)

    duration_ms = int((time.perf_counter() - start) * 1000)
    return EvalRunResult(
        samples=meta,
        metrics_avg=_avg_scores(meta),
        duration_ms=duration_ms,
    )
