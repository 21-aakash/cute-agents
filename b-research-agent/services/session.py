from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import ChatSession, ChatTurn
from domain.models import Turn
from services.config import settings
from services.llm import LLMClient


class SessionService:
    def __init__(self, db: Session, llm: LLMClient | None = None) -> None:
        self.db = db
        self.llm = llm or LLMClient()

    def get_session(self, session_id: str) -> ChatSession | None:
        return self.db.get(ChatSession, session_id)

    def conversation_context(self, session: ChatSession) -> tuple[list[dict], str]:
        turns = (
            self.db.query(ChatTurn)
            .filter(ChatTurn.session_id == session.id)
            .order_by(ChatTurn.created_at.asc())
            .all()
        )
        recent = turns[-settings.verbatim_turns :]
        turn_dicts = [
            {"query": t.query, "answer": t.answer, "score": t.critic_score or 0.0}
            for t in recent
        ]
        return turn_dicts, session.summary or ""

    def add_turn(self, session: ChatSession, query: str, answer: str, score: float) -> None:
        self.db.add(
            ChatTurn(
                session_id=session.id,
                query=query,
                answer=answer,
                critic_score=score,
            )
        )
        self.db.commit()
        self._maybe_compress(session)

    def _maybe_compress(self, session: ChatSession) -> None:
        turns = (
            self.db.query(ChatTurn)
            .filter(ChatTurn.session_id == session.id)
            .order_by(ChatTurn.created_at.asc())
            .all()
        )
        if len(turns) <= settings.verbatim_turns:
            return
        stale = turns[: -settings.verbatim_turns]
        transcript = "\n".join(f"Q: {t.query}\nA: {t.answer[:300]}" for t in stale)
        prior = f"Existing summary: {session.summary}\n\n" if session.summary else ""
        session.summary = self.llm.complete(
            system=(
                "Compress research conversations into 3 factual sentences covering "
                "what was asked and concluded. No preamble."
            ),
            user=f"{prior}New exchanges:\n{transcript}",
            temperature=0.2,
            max_tokens=220,
            role="worker",
        ).strip()
        self.db.commit()

    @staticmethod
    def format_context(turns: list[dict], summary: str, max_chars: int = 1500) -> str:
        parts: list[str] = []
        if summary:
            parts.append(f"Earlier in this session: {summary}")
        for turn in turns:
            answer = turn["answer"].strip().replace("\n", " ")
            if len(answer) > 300:
                answer = answer[:300].rstrip() + "..."
            parts.append(f"Q: {turn['query']}\nA: {answer}")
        context = "\n\n".join(parts)
        return context[:max_chars] if context else "This is the first question."
