# 🎯 Product Vision — One-Stop Tech Platform

> *Saved from product strategy session — Oct 2026*

---

## The Big Idea

A **one-stop solution for Indian tech guys** — not a generic AI wrapper, but a platform with real, finished, opinionated tools built around how developers actually live and work.

The tone: **A brilliant friend who's a FAANG senior** — brutally honest about gaps, but personally invested in your success.

---

## The Three Pillars

### 💼 1. Career Agent ← **Build this first. This is the wedge.**

**The Problem:** Job seekers spend hundreds of hours manually searching job boards, reading company blogs, assessing skill matches, customizing resumes and cover letters, and following up — all manually.

**What it does:**
- Upload Resume / CV (PDF/DOCX) + career domain preferences
- **Multi-Agent Research:** Searches real-time job listings & company engineering blogs, decomposes JD into hard vs soft skill requirements
- **Gap & Fit Analysis:** Computes Match Score (0–100), details exact technical gaps
- **High-ATS Resume Generation:** Tailored resumes using Google XYZ formula, strictly grounded in real experience — no hallucinated skills
- **Cold Outreach + Gmail Follow-ups:** 1-click personalized cold emails to hiring managers, automated follow-up sequences on Day 3, Day 7, Day 14
- **Career Pivot Research:** Transferable skills map, step-by-step learning roadmap

**UI:** Kanban pipeline (Applied → Followed Up → Interview → Offer) + chat + email draft preview

**Why Indian devs will love it:**
- LinkedIn + Naukri are clunky — this is a smart wingman
- Referral-first culture → cold outreach needs to feel personal, not spammy
- Match score gives clarity vs anxiety of "am I good enough?"

---

### 📋 2. Productivity / OPS Agent ← **Build second**

**NOT another todo app.** The hook:
> *"Paste your Jira ticket / PRD and I'll break it into your week"*

- AI-powered task decomposition from unstructured input
- Connects to real work context (tickets, PRDs, meeting notes)
- Weekly planning assistant

---

### 🔬 3. Research Agent ← **Already built, needs UI refresh**

Deep research assistant — like Perplexity but sessions persist as structured markdown docs.

- **Research Trees** showing thinking, tool use, web search steps (the killer UI feature)
- Feeds INTO Career Agent (company research before applying)
- Saves to vector store for future retrieval

---

## Architecture Decision: One Home, Three Modes

```
┌────────────────────────────────────────────┐
│          [Platform Name]                    │
│   "Your AI-powered tech career engine"      │
├───────────┬──────────────┬─────────────────┤
│  📋 OPS   │  💼 CAREER   │  🔬 RESEARCH    │
│  (Tasks)  │  (Job Agent) │  (Deep Dive)    │
└───────────┴──────────────┴─────────────────┘
           ↓ Shared bottom bar ↓
     [ Ask anything... ] → Smart Router
```

**One unified chat bar** (like Raycast command palette) that routes intent to the right agent.
Each workspace has its **own dedicated UI** — not just a chatbox.

---

## Build Sequence

| Phase | What | Why |
|---|---|---|
| **V1** | Research Agent UI refresh (white, minimalist + research trees) | Foundation; already has working backend |
| **V2** | Career Agent — Kanban + Chat + Gmail drafts | The wedge; highest pain, no good solution |
| **V3** | Unified home + routing | Only after both are real |
| **V4** | Productivity layer | For users already placed |

---

## How Real Indian Tech Guys Will Use This

| Behaviour | What we build for it |
|---|---|
| Opens LinkedIn anxiously 5x/day | Daily pipeline view in Career Agent |
| 50+ WhatsApp groups for referrals | Referral tracking + warm intro templates |
| Applies to 30 jobs, hears from 2 | Automated follow-up sequences |
| Reads blogs on weekend, forgets | Research sessions that persist |
| Doesn't pay Rs 2000/mo upfront | Free tier: 5 applications + basic research |
| Mobile-first | Mobile-responsive, WhatsApp-style chat feel |

---

## UI Philosophy

- **White, minimalist** — clean like Linear, not flashy like most AI tools
- **Research trees** showing agent thinking / tool use — signature feature
- **Unified chat** at bottom as the "always available" interface
- Each agent gets its OWN dedicated UI beyond the chat
- No noise, no dark mode clutter — light, clean, fast

---

## Current Status

- Research Agent backend (LangGraph: Plan → Research → Write → Critique → Persist) — DONE
- Qdrant vector store + PostgreSQL — DONE
- FastAPI routes — DONE
- Research tree UI (ResearchMarkers) — DONE, KEEP
- Auth + workspace context — DONE
- **Next: Rebuild UI with unified home**
- Career Agent backend — TODO
- Productivity Agent — TODO
