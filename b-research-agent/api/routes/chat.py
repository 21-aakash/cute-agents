from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.deps import get_runner, get_workspace
from db.models import ChatRun, ChatSession, ChatTurn, Workspace
from db.session import get_db
from domain.models import ChatResponse, Critique, Evidence, Plan
from graph.nodes import CHITCHAT_SYSTEM, _is_obvious_chitchat
from services.session import SessionService
from services.workspace_docs import list_indexed_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/sessions", tags=["chat"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _stream_words(text: str):
    words = text.split()
    if not words:
        return
    for i, word in enumerate(words):
        chunk = word if i == len(words) - 1 else word + " "
        yield _sse({"type": "token", "content": chunk})


def _persist_chat_result(
    *,
    db: Session,
    session: ChatSession,
    workspace: Workspace,
    session_svc: SessionService,
    query: str,
    result: dict,
) -> ChatResponse:
    answer = result.get("answer", "") or "I couldn't produce an answer. Please try again."
    critique = Critique.model_validate(result["critique"]) if result.get("critique") else None
    plan = Plan.model_validate(result["plan"]) if result.get("plan") else None
    evidence = [Evidence.model_validate(e) for e in result.get("evidence", [])]

    run = ChatRun(
        session_id=session.id,
        workspace_id=workspace.id,
        query=query,
        answer=answer,
        plan=result.get("plan"),
        critique=result.get("critique"),
        revisions=result.get("revisions", 0),
        evidence=result.get("evidence"),
        tool_calls=result.get("tool_calls"),
        duration_ms=result.get("duration_ms"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    session_svc.add_turn(
        session,
        query=query,
        answer=answer,
        score=critique.average if critique else 0.0,
    )

    return ChatResponse(
        status="completed",
        answer=answer,
        intent=result.get("intent"),
        critique=critique,
        evidence=evidence,
        plan=plan,
        revisions=result.get("revisions", 0),
        run_id=str(run.id),
        tool_calls=result.get("tool_calls") or [],
    )


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID


class ChatRequest(BaseModel):
    query: str
    web_search_enabled: bool = True


class ResumeRequest(BaseModel):
    answer: str
    web_search_enabled: bool = True


@router.post("", response_model=CreateSessionResponse)
def create_session(
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> CreateSessionResponse:
    session = ChatSession(workspace_id=workspace.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("session.created workspace=%s session=%s", workspace.id, session.id)
    return CreateSessionResponse(session_id=session.id)


class TurnResponse(BaseModel):
    query: str
    answer: str
    critic_score: float | None = None


@router.get("/{session_id}/messages", response_model=list[TurnResponse])
def get_session_messages(
    session_id: uuid.UUID,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> list[TurnResponse]:
    session = db.get(ChatSession, session_id)
    if session is None or session.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Session not found")
    turns = (
        db.query(ChatTurn)
        .filter(ChatTurn.session_id == session.id)
        .order_by(ChatTurn.created_at.asc())
        .all()
    )
    logger.info("session.messages workspace=%s session=%s count=%d", workspace.id, session_id, len(turns))
    return [
        TurnResponse(query=t.query, answer=t.answer, critic_score=t.critic_score)
        for t in turns
    ]


@router.delete("/{session_id}")
def delete_session(
    session_id: uuid.UUID,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> dict:
    session = db.get(ChatSession, session_id)
    if session is None or session.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Session not found")

    db.query(ChatRun).filter(ChatRun.session_id == session.id).delete()
    db.delete(session)
    db.commit()
    logger.info("session.deleted workspace=%s session=%s", workspace.id, session_id)
    return {"deleted": str(session_id)}


@router.post("/{session_id}/chat", response_model=ChatResponse)
def chat(
    session_id: uuid.UUID,
    body: ChatRequest,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = db.get(ChatSession, session_id)
    if session is None or session.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Session not found")

    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(
        "chat.request workspace=%s session=%s query=%r",
        workspace.id,
        session_id,
        query[:200],
    )

    session_svc = SessionService(db)
    turns, summary = session_svc.conversation_context(session)
    indexed_docs = list_indexed_documents(db, workspace.id)
    try:
        result = get_runner().run(
            query=query,
            workspace_id=str(workspace.id),
            session_id=str(session_id),
            conversation_turns=turns,
            conversation_summary=summary,
            indexed_documents=indexed_docs,
            web_search_enabled=body.web_search_enabled,
        )
    except Exception as exc:
        logger.exception("chat.failed workspace=%s session=%s", workspace.id, session_id)
        raise HTTPException(status_code=502, detail=f"Research pipeline failed: {exc}") from exc

    if result["status"] == "needs_clarification":
        logger.info("chat.clarify workspace=%s session=%s", workspace.id, session_id)
        return ChatResponse(
            status="needs_clarification",
            questions=result.get("questions", []),
            intent="clarify",
        )

    answer = result.get("answer", "")
    if not answer:
        logger.warning("chat.empty_answer workspace=%s session=%s intent=%s", workspace.id, session_id, result.get("intent"))
        answer = "I couldn't produce an answer. Please try again."

    critique = Critique.model_validate(result["critique"]) if result.get("critique") else None
    plan = Plan.model_validate(result["plan"]) if result.get("plan") else None
    evidence = [Evidence.model_validate(e) for e in result.get("evidence", [])]

    run = ChatRun(
        session_id=session.id,
        workspace_id=workspace.id,
        query=query,
        answer=answer,
        plan=result.get("plan"),
        critique=result.get("critique"),
        revisions=result.get("revisions", 0),
        evidence=result.get("evidence"),
        tool_calls=result.get("tool_calls"),
        duration_ms=result.get("duration_ms"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    session_svc.add_turn(
        session,
        query=query,
        answer=answer,
        score=critique.average if critique else 0.0,
    )

    logger.info(
        "chat.completed workspace=%s session=%s run=%s intent=%s duration_ms=%s answer_len=%d",
        workspace.id,
        session_id,
        run.id,
        result.get("intent"),
        result.get("duration_ms"),
        len(answer),
    )

    return ChatResponse(
        status="completed",
        answer=answer,
        intent=result.get("intent"),
        critique=critique,
        evidence=evidence,
        plan=plan,
        revisions=result.get("revisions", 0),
        run_id=str(run.id),
        tool_calls=result.get("tool_calls") or [],
    )


@router.post("/{session_id}/chat/stream")
def chat_stream(
    session_id: uuid.UUID,
    body: ChatRequest,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
):
    session = db.get(ChatSession, session_id)
    if session is None or session.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Session not found")

    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    session_svc = SessionService(db)
    turns, summary = session_svc.conversation_context(session)
    indexed_docs = list_indexed_documents(db, workspace.id)
    runner = get_runner()
    llm = runner.llm

    def event_generator():
        try:
            if _is_obvious_chitchat(query):
                intent = "chitchat"
                yield _sse({"type": "intent", "intent": intent})
                logger.info("chat.stream chitchat workspace=%s session=%s", workspace.id, session_id)

                parts: list[str] = []
                for token in llm.stream(
                    system=CHITCHAT_SYSTEM,
                    user=query,
                    temperature=0.4,
                    role="chitchat",
                ):
                    parts.append(token)
                    yield _sse({"type": "token", "content": token})

                answer = "".join(parts) or "Hello! How can I help you today?"
                result = {
                    "status": "completed",
                    "answer": answer,
                    "intent": intent,
                    "duration_ms": 0,
                }
                response = _persist_chat_result(
                    db=db,
                    session=session,
                    workspace=workspace,
                    session_svc=session_svc,
                    query=query,
                    result=result,
                )
                yield _sse({"type": "done", **response.model_dump(mode="json")})
                return

            yield _sse({"type": "status", "message": "Thinking…"})
            logger.info("chat.stream research workspace=%s session=%s query=%r", workspace.id, session_id, query[:200])

            result = None
            for kind, payload in runner.run_streaming(
                query=query,
                workspace_id=str(workspace.id),
                session_id=str(session_id),
                conversation_turns=turns,
                conversation_summary=summary,
                indexed_documents=indexed_docs,
                web_search_enabled=body.web_search_enabled,
            ):
                if kind == "marker":
                    yield _sse({"type": "marker", "marker": payload})
                elif kind == "result":
                    result = payload

            if result is None:
                raise RuntimeError("Research pipeline produced no result")

            if result["status"] == "needs_clarification":
                yield _sse({
                    "type": "done",
                    "status": "needs_clarification",
                    "questions": result.get("questions", []),
                    "intent": "clarify",
                    "answer": "",
                })
                return

            intent = result.get("intent", "synthesis")
            yield _sse({"type": "intent", "intent": intent})

            answer = result.get("answer", "") or ""
            yield from _stream_words(answer)

            response = _persist_chat_result(
                db=db,
                session=session,
                workspace=workspace,
                session_svc=session_svc,
                query=query,
                result=result,
            )
            yield _sse({"type": "done", **response.model_dump(mode="json")})
        except Exception as exc:
            logger.exception("chat.stream.failed workspace=%s session=%s", workspace.id, session_id)
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{session_id}/chat/resume", response_model=ChatResponse)
def chat_resume(
    session_id: uuid.UUID,
    body: ResumeRequest,
    workspace: Workspace = Depends(get_workspace),
    db: Session = Depends(get_db),
) -> ChatResponse:
    session = db.get(ChatSession, session_id)
    if session is None or session.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Session not found")

    answer_text = body.answer.strip()
    if not answer_text:
        raise HTTPException(status_code=400, detail="Answer cannot be empty")

    logger.info("chat.resume workspace=%s session=%s", workspace.id, session_id)

    session_svc = SessionService(db)
    turns, summary = session_svc.conversation_context(session)
    indexed_docs = list_indexed_documents(db, workspace.id)
    try:
        result = get_runner().run(
            query="",
            workspace_id=str(workspace.id),
            session_id=str(session_id),
            conversation_turns=turns,
            conversation_summary=summary,
            indexed_documents=indexed_docs,
            web_search_enabled=body.web_search_enabled,
            resume={"answer": answer_text},
        )
    except Exception as exc:
        logger.exception("chat.resume.failed workspace=%s session=%s", workspace.id, session_id)
        raise HTTPException(status_code=502, detail=f"Research pipeline failed: {exc}") from exc

    if result["status"] == "needs_clarification":
        return ChatResponse(
            status="needs_clarification",
            questions=result.get("questions", []),
            intent="clarify",
        )

    answer = result.get("answer", "") or "I couldn't produce an answer. Please try again."
    critique = Critique.model_validate(result["critique"]) if result.get("critique") else None
    plan = Plan.model_validate(result["plan"]) if result.get("plan") else None
    evidence = [Evidence.model_validate(e) for e in result.get("evidence", [])]

    logger.info(
        "chat.resume.completed workspace=%s session=%s intent=%s answer_len=%d",
        workspace.id,
        session_id,
        result.get("intent"),
        len(answer),
    )

    return ChatResponse(
        status="completed",
        answer=answer,
        intent=result.get("intent"),
        critique=critique,
        evidence=evidence,
        plan=plan,
        revisions=result.get("revisions", 0),
        tool_calls=result.get("tool_calls") or [],
    )
