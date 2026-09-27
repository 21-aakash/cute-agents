from __future__ import annotations

import re
import time
from typing import Literal

from langgraph.types import Command, interrupt
from langchain_core.runnables import RunnableConfig

from domain.models import Critique, Evidence, Plan
from domain.state import ResearchGraphState
from services.config import settings
from services.tools import ResearchToolkit, dedupe_evidence, format_evidence
from services.workspace_docs import format_doc_catalog

MAX_SUBQUERIES = 4

PLANNER_SYSTEM = """You are the Router/Planner for CareerOps AI. Your job is to classify candidate queries, select retrieval sources, and plan research.

Return JSON only:
{
  "intent": "fit_evaluation" | "resume_tailor" | "cold_email" | "career_pivot" | "doc_qa" | "chitchat",
  "ready_to_research": true | false,
  "clarifying_questions": ["..."],
  "sub_queries": ["..."],
  "sources": ["docs", "web", "memory"],
  "use_memory": true | false,
  "reasoning": "one sentence"
}

Routing rules:
1. chitchat — greetings, pleasantries, or general intro questions.
2. fit_evaluation — user asks for a match score, comparison of CV vs Job Description, or skill gap audit.
3. resume_tailor — user asks to rewrite, optimize, or tailor resume bullet points for a JD.
4. cold_email — user asks for outreach emails to recruiters, hiring managers, or cover letters.
5. career_pivot — user asks how to transition into a new tech domain or what learning roadmap to follow.
6. doc_qa — factual questions about uploaded resume or candidate vault files.

Source rules:
- ["docs"] — query is about candidate experience, uploaded CV, or vault files.
- ["web"] — external job postings, company tech blogs, market trends, or GitHub profiles.
- ["docs", "web"] — comparing candidate vault with target job requirements or company tech stack.
- Provide 1–2 focused sub_queries; avoid duplicates.
- No prose outside JSON."""

RESEARCH_SYSTEM = """You are the Research agent. Synthesize bullet notes ONLY from the retrieved evidence below.
Attribute each point to its source label [1], [2], etc. Extract concrete facts (names, skills, dates, employers).
If evidence passages exist, you MUST extract content from them — never claim nothing was retrieved.
State gaps only for information genuinely absent from the evidence. Do not invent facts."""

WRITER_SYSTEM = """You are the Writer for CareerOps AI. Produce a comprehensive, cited answer using the retrieved evidence and research notes.

Rules:
- Primary source: the Retrieved evidence section. Use research notes as a supplement.
- When tailoring resumes or analyzing job fit:
  • Calculate a clear Match Fit Score (0–100) based on hard/soft skills if comparing a candidate vault with a Job Description.
  • Use the Google XYZ formula: "Accomplished [X] as measured by [Y], by doing [Z]" for bullet points.
  • Highlight transferable skills, key gaps, and actionable recommendations.
- When drafting outreach emails:
  • Draft concise, high-converting cold outreach / cover emails referencing specific company tech stacks and projects.
- NEVER ask the user to upload or paste a document when evidence passages are already present.
- Use inline citations like [1], [2] matching evidence labels.
- Format in clean Markdown with clear headings, bullet points, and bold terms.
- If evidence is empty, state clearly that nothing relevant was found in the career knowledge base."""

CRITIC_SYSTEM = """You are the Critic for CareerOps AI. Grade the answer against the evidence ONLY (not your own knowledge).

Return JSON:
{
  "correctness": 1-5,
  "completeness": 1-5,
  "clarity": 1-5,
  "grounded": true | false,
  "revision_request": "specific gap or empty string",
  "comments": "brief"
}"""

CHITCHAT_SYSTEM = """You are CareerOps AI — an autonomous career copilot and deep research assistant. Answer greetings, introduce your capabilities (resume tailoring, fit scoring, cold outreach, career pivots, deep document research), and guide the user concisely."""

_CHITCHAT_RE = re.compile(
    r"^(?:hi|hello|hey|howdy|yo|sup|thanks|thank you|thx|good morning|good afternoon|good evening|bye|goodbye)[\s!.?]*$",
    re.IGNORECASE,
)
_ANSWER_DENIES_EVIDENCE_RE = re.compile(
    r"\b("
    r"don'?t have (?:the |any )?(?:resume|document|research notes|content|information)"
    r"|do not have (?:the |any )?(?:resume|document|research notes|content|information)"
    r"|please paste"
    r"|please upload"
    r"|send (?:the |me )?resume"
    r"|no research notes"
    r"|can'?t evaluate them now"
    r")\b",
    re.IGNORECASE,
)
_CURRENT_EVENTS_RE = re.compile(
    r"\b(today|latest|breaking news|headlines|current events|right now|this week|news today)\b",
    re.IGNORECASE,
)


def _query_mentions_catalog(query: str, docs: list[dict]) -> bool:
    q = query.lower()
    for doc in docs:
        title = doc.get("title", "").lower()
        stem = doc.get("filename", "").rsplit(".", 1)[0].lower()
        if title and title in q:
            return True
        if stem and len(stem) > 3 and stem in q:
            return True
    return False


def _default_sources(query: str, indexed_docs: list[dict], web_enabled: bool) -> list[str]:
    if web_enabled and _CURRENT_EVENTS_RE.search(query) and not _query_mentions_catalog(query, indexed_docs):
        return ["web"]
    if indexed_docs:
        return ["docs"]
    if web_enabled:
        return ["web"]
    return []


def _normalize_sources(
    sources: list[str],
    *,
    query: str,
    indexed_docs: list[dict],
    web_enabled: bool,
) -> list[str]:
    allowed = {"docs", "web", "memory"}
    out: list[str] = []
    for s in sources:
        if s not in allowed or s in out:
            continue
        if s == "web" and not web_enabled:
            continue
        if s == "docs" and not indexed_docs:
            continue
        out.append(s)

    if not out:
        out = _default_sources(query, indexed_docs, web_enabled)

    # Current-events + catalog mismatch → web-only even if planner said docs
    if web_enabled and _CURRENT_EVENTS_RE.search(query) and not _query_mentions_catalog(query, indexed_docs):
        if "web" in out:
            return ["web"]

    return out


def _is_obvious_chitchat(query: str) -> bool:
    return bool(_CHITCHAT_RE.match(query.strip()))


def _deps(config: RunnableConfig) -> dict:
    return config["configurable"]["deps"]


def plan_node(
    state: ResearchGraphState, config: RunnableConfig
) -> Command[Literal["chitchat", "clarify", "research"]]:
    if _is_obvious_chitchat(state["query"]):
        plan = Plan(
            intent="chitchat",
            ready_to_research=False,
            reasoning="Greeting or social message",
        )
        return Command(update={"plan": plan.model_dump()}, goto="chitchat")

    deps = _deps(config)
    llm = deps["llm"]
    logger = deps["logger"]
    turns = state.get("conversation_turns") or []
    summary = state.get("conversation_summary") or ""
    from services.session import SessionService

    conversation = SessionService.format_context(turns, summary)
    indexed_docs = deps.get("indexed_documents") or state.get("indexed_documents") or []
    web_enabled = deps.get("web_search_enabled", state.get("web_search_enabled", True))
    doc_catalog = format_doc_catalog(indexed_docs)
    web_flag = "enabled — include web in sources for external/current topics" if web_enabled else "disabled — do NOT include web in sources"

    fallback = {
        "intent": "synthesis",
        "ready_to_research": True,
        "clarifying_questions": [],
        "sub_queries": [state["query"]],
        "sources": _default_sources(state["query"], indexed_docs, web_enabled),
        "use_memory": False,
        "reasoning": "Planner fallback",
    }
    raw = llm.complete_json(
        system=PLANNER_SYSTEM,
        user=(
            f"{doc_catalog}\nWeb search: {web_flag}\n\n"
            f"Conversation:\n{conversation}\n\nQuestion: {state['query']}"
        ),
        fallback=fallback,
        role="planner",
    )
    plan = Plan.model_validate({**fallback, **raw})
    plan.sources = _normalize_sources(
        plan.sources,
        query=state["query"],
        indexed_docs=indexed_docs,
        web_enabled=web_enabled,
    )

    clarify_count = state.get("clarify_count", 0)
    # Router rule: if KB has docs, don't clarify — send to research agent (it owns retrieval).
    if indexed_docs and not plan.ready_to_research:
        plan.ready_to_research = True
        if not plan.sub_queries:
            plan.sub_queries = [state["query"]]
        if not plan.sources:
            plan.sources = _default_sources(state["query"], indexed_docs, web_enabled)

    # Safety valve: stop clarify loops after max rounds
    if clarify_count >= settings.max_clarify_rounds:
        plan.ready_to_research = True
        if not plan.sub_queries:
            plan.sub_queries = [state["query"]]

    logger.log("plan", intent=plan.intent, ready=plan.ready_to_research, sources=plan.sources)

    if plan.intent == "chitchat":
        return Command(update={"plan": plan.model_dump()}, goto="chitchat")
    if not plan.ready_to_research:
        return Command(update={"plan": plan.model_dump()}, goto="clarify")
    return Command(update={"plan": plan.model_dump()}, goto="research")


def clarify_node(state: ResearchGraphState) -> Command[Literal["plan"]]:
    plan = Plan.model_validate(state.get("plan") or {})
    user_reply = interrupt(
        {
            "questions": plan.clarifying_questions or ["Can you provide more detail?"],
            "original_query": state["query"],
        }
    )
    answer = user_reply.get("answer", "") if isinstance(user_reply, dict) else str(user_reply)
    enriched = f"{state['query']}\n\nUser clarification: {answer}"
    return Command(
        update={
            "query": enriched,
            "clarify_count": state.get("clarify_count", 0) + 1,
        },
        goto="plan",
    )


def chitchat_node(state: ResearchGraphState, config: RunnableConfig) -> dict:
    deps = _deps(config)
    query = state["query"]
    answer = deps["llm"].complete(
        system=CHITCHAT_SYSTEM,
        user=query,
        temperature=0.4,
        role="chitchat",
    )
    deps["logger"].log("chitchat")
    return {"answer": answer or "Hello! How can I help you today?", "evidence": [], "notes": ""}


def research_node(state: ResearchGraphState, config: RunnableConfig) -> dict:
    deps = _deps(config)
    tools: ResearchToolkit = deps["tools"]
    llm = deps["llm"]
    logger = deps["logger"]
    plan = Plan.model_validate(state.get("plan") or {})
    revision_note = state.get("revision_note") or ""
    indexed_docs = deps.get("indexed_documents") or state.get("indexed_documents") or []
    web_enabled = bool(deps.get("web_search_enabled", state.get("web_search_enabled", True)))

    sub_queries = plan.sub_queries or [state["query"]]
    sources = _normalize_sources(
        plan.sources,
        query=state["query"],
        indexed_docs=indexed_docs,
        web_enabled=web_enabled,
    )

    use_docs = "docs" in sources
    if use_docs:
        probe = tools.kb_probe(state["query"])
        tools.log.append({
            "tool": "kb_probe",
            "query": state["query"],
            "hit_count": 1 if probe.relevant else 0,
            "ts": time.time(),
        })
        if not probe.relevant:
            use_docs = False
            logger.log("kb_probe", relevant=False, score=probe.top_score)
        else:
            logger.log("kb_probe", relevant=True, score=probe.top_score)

    all_evidence: list[Evidence] = []
    for sub_q in sub_queries[:MAX_SUBQUERIES]:
        if use_docs:
            all_evidence.extend(tools.doc_search(sub_q).evidence)
        if plan.use_memory and "memory" in sources:
            all_evidence.extend(tools.memory_search(sub_q).evidence)
        if web_enabled and "web" in sources:
            all_evidence.extend(tools.web_search(sub_q).evidence)
        if "github.com" in state["query"].lower() or "github" in state["query"].lower():
            all_evidence.extend(tools.github_search(state["query"]).evidence)

    evidence = dedupe_evidence(all_evidence)
    evidence_block = format_evidence(evidence)
    user = f"Question: {state['query']}\n\nEvidence:\n{evidence_block}"
    if revision_note:
        user += f"\n\nRevision request from Critic:\n{revision_note}"

    notes = llm.complete(system=RESEARCH_SYSTEM, user=user, temperature=0.2, role="worker")
    logger.log("research", evidence=len(evidence), sub_queries=len(sub_queries), sources=sources)
    return {
        "evidence": [e.model_dump() for e in evidence],
        "notes": notes,
        "tool_calls": tools.log,
    }


def write_node(state: ResearchGraphState, config: RunnableConfig) -> dict:
    deps = _deps(config)
    turns = state.get("conversation_turns") or []
    summary = state.get("conversation_summary") or ""
    from services.session import SessionService

    conversation = SessionService.format_context(turns, summary)
    revision = state.get("revision_note") or ""
    evidence = [Evidence.model_validate(e) for e in state.get("evidence") or []]
    evidence_block = format_evidence(evidence)
    notes = state.get("notes", "")

    user = (
        f"Question: {state['query']}\n\nConversation:\n{conversation}\n\n"
        f"Retrieved evidence (primary — cite these):\n{evidence_block}\n\n"
        f"Research notes:\n{notes or '(none)'}"
    )
    if revision:
        user += f"\n\nAddress this revision request:\n{revision}"

    answer = deps["llm"].complete(system=WRITER_SYSTEM, user=user, temperature=0.2, role="worker")
    deps["logger"].log("write", evidence_chunks=len(evidence))
    return {"answer": answer}


def critique_node(state: ResearchGraphState, config: RunnableConfig) -> dict:
    deps = _deps(config)
    evidence = [Evidence.model_validate(e) for e in state.get("evidence") or []]
    evidence_block = format_evidence(evidence, max_chars=3500)
    fallback = {
        "correctness": 1,
        "completeness": 1,
        "clarity": 1,
        "grounded": False,
        "revision_request": "Insufficient evidence.",
        "comments": "Critic fallback",
    }
    raw = deps["llm"].complete_json(
        system=CRITIC_SYSTEM,
        user=(
            f"Question: {state['query']}\n\nAnswer:\n{state.get('answer', '')}\n\n"
            f"Evidence:\n{evidence_block}"
        ),
        fallback=fallback,
        role="critic",
    )
    scores = [raw.get("correctness", 1), raw.get("completeness", 1), raw.get("clarity", 1)]
    average = sum(scores) / 3
    grounded = bool(raw.get("grounded", False))
    answer = state.get("answer", "") or ""

    # Fail answers that deny having content when evidence was retrieved
    if evidence and _ANSWER_DENIES_EVIDENCE_RE.search(answer):
        grounded = False
        average = min(average, 2.0)
        raw["revision_request"] = "Answer ignores retrieved evidence; rewrite using evidence passages."

    passed = average >= settings.critic_pass_threshold and grounded
    critique = Critique(
        correctness=int(scores[0]),
        completeness=int(scores[1]),
        clarity=int(scores[2]),
        average=round(average, 2),
        grounded=grounded,
        passed=passed,
        revision_request=raw.get("revision_request") or None,
        comments=str(raw.get("comments", "")),
    )
    deps["logger"].log("critique", passed=passed, average=critique.average)
    return {"critique": critique.model_dump()}


def revise_node(state: ResearchGraphState, config: RunnableConfig) -> dict:
    critique = state.get("critique") or {}
    note = critique.get("revision_request") or critique.get("comments") or ""
    _deps(config)["logger"].log("revise", attempt=state.get("revisions", 0) + 1)
    return {
        "revisions": state.get("revisions", 0) + 1,
        "revision_note": note,
    }


def persist_node(state: ResearchGraphState, config: RunnableConfig) -> dict:
    deps = _deps(config)
    critique = state.get("critique") or {}
    logger = deps["logger"]

    if not critique.get("passed"):
        logger.log("memory_write", stored=False, reason="did not pass critic")
        return {}

    evidence = state.get("evidence") or []
    doc_ids = sorted({e.get("doc_id") for e in evidence if e.get("doc_id")})

    try:
        deps["vectorstore"].store_memory(
            workspace_id=state["workspace_id"],
            query=state["query"],
            finding=state.get("answer", ""),
            session_id=state.get("session_id", ""),
            score=float(critique.get("average", 0)),
            doc_ids=[d for d in doc_ids if d],
            embedder=deps["embedder"],
        )
        logger.log("memory_write", stored=True)
    except Exception as exc:
        logger.log("memory_write", stored=False, error=str(exc)[:200])
    return {}
