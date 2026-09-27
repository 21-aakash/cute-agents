from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from graph.builder import build_graph
from graph.pipeline_markers import active_marker, markers_from_state
from services.config import settings
from services.embedder import get_embedder
from services.llm import LLMClient
from services.observability import RunLogger
from services.tools import ResearchToolkit
from services.vectorstore import VectorStore

logger = logging.getLogger(__name__)


def make_checkpointer():
    """Create LangGraph checkpointer. Falls back to MemorySaver on failure."""
    backend = settings.checkpoint_backend.lower()
    if backend == "memory":
        logger.info("Using MemorySaver checkpointer")
        return MemorySaver()

    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg import Connection

        dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        dsn = dsn.replace("@localhost:", "@127.0.0.1:")
        logger.info("Connecting Postgres checkpointer (timeout=%ss)", settings.checkpoint_connect_timeout)
        conn = Connection.connect(
            dsn,
            autocommit=True,
            connect_timeout=settings.checkpoint_connect_timeout,
        )
        checkpointer = PostgresSaver(conn)
        checkpointer.setup()
        logger.info("Postgres checkpointer ready")
        return checkpointer
    except Exception:
        logger.exception("Postgres checkpointer failed; falling back to MemorySaver")
        return MemorySaver()


class ResearchGraphRunner:
    def __init__(self, vectorstore: VectorStore | None = None, checkpointer=None) -> None:
        self.vectorstore = vectorstore or VectorStore()
        self.llm = LLMClient()
        self.embedder = get_embedder()
        cp = checkpointer if checkpointer is not None else make_checkpointer()
        self.graph = build_graph(checkpointer=cp)
        logger.info("ResearchGraphRunner initialized")

    def _build_config(
        self,
        *,
        session_id: str,
        workspace_id: str,
        indexed_documents: list[dict],
        web_search_enabled: bool = True,
    ) -> tuple[dict, ResearchToolkit, RunLogger]:
        run_logger = RunLogger()
        tools = ResearchToolkit(self.vectorstore, self.embedder, workspace_id)
        deps = {
            "llm": self.llm,
            "tools": tools,
            "embedder": self.embedder,
            "vectorstore": self.vectorstore,
            "logger": run_logger,
            "indexed_documents": indexed_documents,
            "web_search_enabled": web_search_enabled,
        }
        config = {"configurable": {"thread_id": session_id, "deps": deps}}
        return config, tools, run_logger

    def run_streaming(
        self,
        *,
        query: str,
        workspace_id: str,
        session_id: str,
        conversation_turns: list[dict],
        conversation_summary: str,
        indexed_documents: list[dict] | None = None,
        web_search_enabled: bool = True,
        resume: dict | None = None,
    ) -> Iterator[tuple[str, Any]]:
        """Yield ('marker', dict) progress events, then ('result', final dict)."""
        docs = indexed_documents or []
        config, tools, run_logger = self._build_config(
            session_id=session_id,
            workspace_id=workspace_id,
            indexed_documents=docs,
            web_search_enabled=web_search_enabled,
        )
        stream_input: dict | Command
        if resume is not None:
            stream_input = Command(resume=resume)
        else:
            stream_input = {
                "query": query,
                "workspace_id": workspace_id,
                "session_id": session_id,
                "conversation_turns": conversation_turns,
                "conversation_summary": conversation_summary,
                "indexed_documents": docs,
                "web_search_enabled": web_search_enabled,
                "revisions": 0,
                "revision_note": "",
                "clarify_count": 0,
            }

        accumulated: dict[str, Any] = {}
        seen: set[str] = set()

        try:
            for chunk in self.graph.stream(stream_input, config, stream_mode="updates"):
                for node_name, update in chunk.items():
                    if node_name == "__interrupt__":
                        continue
                    yield ("marker", active_marker(node_name))
                    if isinstance(update, dict) and update:
                        accumulated.update(update)
                    if node_name == "research":
                        accumulated["tool_calls"] = tools.log
                    for marker in markers_from_state(accumulated, seen=seen):
                        yield ("marker", marker)
        except Exception:
            logger.exception("graph.run_streaming failed session=%s", session_id)
            raise

        snapshot = self.graph.get_state(config)
        state_values = snapshot.values or accumulated
        if state_values.get("tool_calls") is None:
            state_values = {**state_values, "tool_calls": tools.log}

        # Clarify interrupt — graph paused waiting for user input
        if snapshot.next:
            interrupt_payload = {}
            for task in snapshot.tasks or []:
                if task.interrupts:
                    interrupt_payload = task.interrupts[0].value or {}
                    break
            if interrupt_payload or state_values.get("plan"):
                plan = state_values.get("plan") or {}
                questions = interrupt_payload.get("questions") if isinstance(interrupt_payload, dict) else None
                if not questions and plan:
                    questions = plan.get("clarifying_questions")
                yield (
                    "result",
                    {
                        "status": "needs_clarification",
                        "questions": questions or ["Can you provide more detail?"],
                        "answer": "",
                        "intent": "clarify",
                        "duration_ms": run_logger.duration_ms,
                        "events": run_logger.events,
                    },
                )
                return

        final = state_values
        plan = final.get("plan") or {}
        yield (
            "result",
            {
                "status": "completed",
                "answer": final.get("answer", ""),
                "plan": final.get("plan"),
                "intent": plan.get("intent", "synthesis"),
                "critique": final.get("critique"),
                "evidence": final.get("evidence", []),
                "notes": final.get("notes", ""),
                "revisions": final.get("revisions", 0),
                "tool_calls": final.get("tool_calls", tools.log),
                "duration_ms": run_logger.duration_ms,
                "events": run_logger.events,
            },
        )

    def run(
        self,
        *,
        query: str,
        workspace_id: str,
        session_id: str,
        conversation_turns: list[dict],
        conversation_summary: str,
        indexed_documents: list[dict] | None = None,
        web_search_enabled: bool = True,
        resume: dict | None = None,
    ) -> dict[str, Any]:
        docs = indexed_documents or []
        logger.info(
            "graph.run session=%s workspace=%s query=%r resume=%s indexed_docs=%d web=%s",
            session_id,
            workspace_id,
            query[:120] if query else "",
            resume is not None,
            len(docs),
            web_search_enabled,
        )
        result: dict[str, Any] | None = None
        for kind, payload in self.run_streaming(
            query=query,
            workspace_id=workspace_id,
            session_id=session_id,
            conversation_turns=conversation_turns,
            conversation_summary=conversation_summary,
            indexed_documents=docs,
            web_search_enabled=web_search_enabled,
            resume=resume,
        ):
            if kind == "result":
                result = payload
        if result is None:
            raise RuntimeError("Graph produced no result")
        return result
