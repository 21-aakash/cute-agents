# Research Assistant — UI Spec (Figma Make)

**Purpose:** Hand this file to Figma Make to generate the frontend. Backend is FastAPI at `http://localhost:8000`. Integration phase will wire React/Vite output to these APIs + SSE stream.

**Reference feel:** Perplexity (research chat + source cards) + glassmorphism (frosted panels, soft blur, subtle borders).

---

## 1. Product summary

A research assistant where users upload a knowledge base, ask questions, and see **live agent progress** (plan → research → write → critique) with **sources, tool calls, and cited answers** — not a black-box chat bubble.

**Core jobs:**
- Upload & manage documents (Library)
- Ask research questions (Chat)
- See streaming agent steps + retrieved sources (Research panel)
- Clarify vague questions inline (Clarify flow)
- Browse long-term memory (Memory)

---

## 2. Design system — glassmorphism

### Canvas
- Background: deep gradient `#0B0F19` → `#121826` with soft radial glow (purple/teal at 8% opacity, top-right)
- Optional subtle grid or noise texture at 3% opacity

### Glass panels
| Token | Value |
|---|---|
| `glass-bg` | `rgba(255,255,255,0.06)` |
| `glass-bg-elevated` | `rgba(255,255,255,0.10)` |
| `glass-border` | `1px solid rgba(255,255,255,0.12)` |
| `glass-blur` | `backdrop-filter: blur(20px)` |
| `glass-shadow` | `0 8px 32px rgba(0,0,0,0.35)` |
| `radius-lg` | `16px` |
| `radius-md` | `12px` |
| `radius-sm` | `8px` |

### Accent
- Primary: `#7C9CFF` (links, active tab, send button)
- Success: `#4ADE80` (critic pass, grounded)
- Warning: `#FBBF24` (clarify needed, revision loop)
- Error: `#F87171` (failed ingest, critic fail)
- Muted text: `rgba(255,255,255,0.55)`
- Body text: `rgba(255,255,255,0.92)`

### Typography
- Font: **Inter** or **Geist** — UI; **Source Serif** optional for cited answer body
- H1 page title: 24px / 600
- Chat message: 15px / 400, line-height 1.6
- Source card title: 13px / 600
- Meta / timestamps: 11px / 400, muted

---

## 3. Layout (desktop ≥1280px)

Perplexity-style **3-column** with collapsible side panels:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Top bar (glass): Logo | Workspace name | Library · Memory · Settings       │
├──────────────┬──────────────────────────────────────┬─────────────────────┤
│  LEFT 240px  │           CENTER (flex)               │   RIGHT 360px       │
│  Sessions    │           Chat thread                 │   Research panel    │
│  + New chat  │           + composer                  │   (live stream)     │
│              │                                       │                     │
│  History     │  User bubble                          │  ● Planning         │
│  list        │  Assistant bubble (streaming)         │  ● Researching…     │
│              │  Clarify card (if needed)             │  Tool: doc_search   │
│              │                                       │  Sources (cards)    │
│              │                                       │  Critic scores      │
└──────────────┴──────────────────────────────────────┴─────────────────────┘
```

### Mobile (<768px)
- Single column: Chat full width
- Research panel → bottom sheet (swipe up) or tab `[Chat | Sources | Library]`
- Sessions → hamburger drawer

---

## 4. Screens

### 4.1 Onboarding / Workspace setup (first visit)
- Glass card centered
- Fields: Workspace name (optional display)
- `API Key` paste field (stored in localStorage as `research_api_key`)
- `Workspace ID` (UUID, from backend or created via API)
- CTA: **Connect** → calls `GET /api/v1/workspaces/{id}` with `X-API-Key`
- Link: Create workspace (calls `POST /api/v1/workspaces`)

### 4.2 Chat (main)
**Center column components:**

1. **Empty state**
   - Headline: "Research your documents"
   - 3 suggestion chips (glass pills): e.g. "Summarize my uploaded docs", "Compare two topics", "What are the key risks?"
   - Subtext: answers cite your library + web when needed

2. **User message bubble**
   - Right-aligned, `glass-bg-elevated`, no heavy border

3. **Assistant message bubble**
   - Left-aligned, wider max-width (~720px)
   - **Streaming text** with cursor blink while `answer` streams
   - Inline citation pills `[1]` `[2]` — click scrolls/highlights source in right panel
   - Footer meta: critic score badge, revision count, duration

4. **Clarify card** (when `status: needs_clarification`)
   - Amber glass border
   - Bot asks 1–2 questions from `questions[]`
   - Inline text input + **Submit clarification** → `POST .../chat/resume`

5. **Composer (sticky bottom)**
   - Glass bar, textarea (auto-grow, max 4 lines)
   - Attach disabled in v1 (upload via Library)
   - Send button (primary glow on hover)
   - Disabled + spinner while run in progress

### 4.3 Research panel (right — Perplexity-like)

Shows **live progress** during a run, then **frozen snapshot** when complete.

**Sections (top to bottom):**

#### A. Agent timeline (vertical stepper)
Each step is a glass row with status icon:

| Step | Label | Subtext |
|---|---|---|
| plan | Planning | intent, sub_queries count |
| research | Researching | tool count, evidence count |
| write | Writing | — |
| critique | Reviewing | scores when done |
| persist | Saving memory | only if passed |

States: `pending` (dim) | `active` (pulse + primary border) | `done` (check) | `skipped` (chitchat path)

#### B. Tool calls (expandable list)
Each row from `tool_calls[]`:
```
 doc_search     "API key rotation procedure"     6 hits    240ms
 web_search     "credential rotation best practice"  3 hits
 memory_search  "key rotation"                   1 hit
```
- Expand → show raw query + hit count
- Icon by tool type

#### C. Sources / Evidence (card grid)
Perplexity-style **source cards** from `evidence[]`:

```
┌─────────────────────────────┐
│  Security Policy          │  score 0.84
│ Section: API Key Rotation   │
│ "Revoke the old key in..."  │  [1]
└─────────────────────────────┘
┌─────────────────────────────┐
│  owasp.org                │  score 0.71
│ "Credential rotation..."    │  [2]
└─────────────────────────────┘
┌─────────────────────────────┐
│  memory                   │
│ Earlier finding: ...        │  [3]
└─────────────────────────────┘
```

- Badge by `origin`: `documents` | `web` | `memory`
- Click card → modal with full `text` + metadata
- Web cards link out via `url`

#### D. Plan detail (collapsible)
- Intent chip: `synthesis` | `comparison` | `followup` | …
- Sources chips: `docs` `web` `memory`
- Sub-queries as numbered list

#### E. Critic scores (when complete)
- 3 horizontal bars: Correctness, Completeness, Clarity (1–5)
- Badges: `Grounded` / `Not grounded`, `Passed` / `Needs revision`
- If `revisions > 0`: "Revised 2×"

### 4.4 Library (modal or full page tab)
- Drag-drop upload zone (glass dashed border)
- Accept: `.pdf`, `.md`, `.txt`
- Table: title, type, chunks, status (`pending` | `indexed` | `failed`)
- Row actions: delete
- Upload progress bar per file

### 4.5 Memory (tab)
- Count of stored findings
- Search input → `GET .../memory/search?q=` (backend TBD; show placeholder in v1 UI)
- Reset button → `DELETE .../memory` with confirm dialog

### 4.6 Settings (drawer)
- API base URL (default `http://localhost:8000`)
- Workspace ID + API key (edit)
- Theme: dark only for v1

---

## 5. Streaming UX (integration contract)

Backend v1 returns one JSON blob; **v2 will add SSE**. UI must be built **stream-ready**:

### Planned endpoint
```
GET /api/v1/workspaces/{id}/sessions/{session_id}/chat/stream
POST body same as /chat
Content-Type: text/event-stream
Header: X-API-Key
```

### SSE event types (design for these now)

| Event | Payload | UI behavior |
|---|---|---|
| `run.started` | `{ run_id }` | Clear panel, show timeline |
| `node.started` | `{ node: "plan" \| "research" \| ... }` | Activate step in timeline |
| `plan.done` | `{ plan: Plan }` | Fill plan section |
| `tool.call` | `{ tool, query, hit_count, duration_ms }` | Append tool row (animate in) |
| `evidence.chunk` | `{ evidence: Evidence, index }` | Append source card |
| `research.notes` | `{ delta: string }` | Optional debug tab |
| `answer.delta` | `{ delta: string }` | Append to assistant bubble (typewriter) |
| `critique.done` | `{ critique: Critique }` | Show score bars |
| `clarify.required` | `{ questions: string[] }` | Show clarify card, pause stream |
| `run.completed` | `{ run_id, revisions, duration_ms }` | Stop spinner |
| `run.error` | `{ message }` | Toast + error state |

**Figma Make:** Show Research panel in **mid-stream state** (plan done, research active, 2 source cards visible, answer partially typed).

---

## 6. API integration (implement today)

Base: `{API_BASE}/api/v1`  
Auth header on all requests: `X-API-Key: {api_key}`

| Action | Method | Path |
|---|---|---|
| Create workspace | POST | `/workspaces` `{ "name": "..." }` |
| List documents | GET | `/workspaces/{id}/documents` |
| Upload document | POST | `/workspaces/{id}/documents` multipart `file` |
| Delete document | DELETE | `/workspaces/{id}/documents/{doc_id}` |
| New session | POST | `/workspaces/{id}/sessions` |
| Send message | POST | `/workspaces/{id}/sessions/{session_id}/chat` `{ "query": "..." }` |
| Clarify resume | POST | `/workspaces/{id}/sessions/{session_id}/chat/resume` `{ "answer": "..." }` |
| Reset memory | DELETE | `/workspaces/{id}/memory` |
| Health | GET | `/health` |

### Chat response (`ChatResponse`)
```typescript
type ChatResponse = {
  status: "completed" | "needs_clarification";
  answer?: string;
  questions?: string[];
  plan?: Plan;
  evidence?: Evidence[];
  critique?: Critique;
  revisions?: number;
  run_id?: string;
};

type Plan = {
  intent: string;
  ready_to_research: boolean;
  sub_queries: string[];
  sources: ("docs" | "web" | "memory")[];
  reasoning: string;
};

type Evidence = {
  text: string;
  origin: "documents" | "web" | "memory";
  doc_title: string;
  section?: string;
  url?: string;
  score: number;
};

type Critique = {
  correctness: number;
  completeness: number;
  clarity: number;
  average: number;
  grounded: boolean;
  passed: boolean;
  revision_request?: string;
};
```

### Client storage (localStorage)
```typescript
{
  api_base: "http://localhost:8000",
  workspace_id: "uuid",
  api_key: "string",
  session_id: "uuid"  // current chat
}
```

---

## 7. Component inventory (for Figma Make)

| Component | Variants |
|---|---|
| `GlassPanel` | default, elevated, interactive |
| `ChatBubble` | user, assistant, streaming, error |
| `ClarifyCard` | single-question, multi-question |
| `Composer` | idle, focused, loading |
| `AgentStep` | pending, active, done, skipped |
| `ToolCallRow` | doc_search, web_search, memory_search, get_section |
| `SourceCard` | document, web, memory |
| `CitationPill` | `[1]` `[2]` … clickable |
| `ScoreBar` | 1–5 with label |
| `Badge` | intent, origin, grounded, passed |
| `UploadZone` | idle, dragover, uploading, error |
| `DocTableRow` | indexed, pending, failed |
| `SuggestionChip` | default, hover |
| `Toast` | success, error, info |

---

## 8. Key user flows

### Happy path — research question
1. User types question → Send
2. Research panel: Planning → active
3. Tool rows appear → source cards populate
4. Answer streams in center column
5. Critic scores appear → done

### Clarify path
1. User: "Tell me about security"
2. Response `needs_clarification` + questions
3. Clarify card in chat → user answers → resume
4. Normal research flow continues

### Upload path
1. Library tab → drop PDF
2. Row shows `pending` → `indexed`
3. User returns to Chat, asks question about doc

---

## 9. Figma Make prompt (copy-paste)

```
Design a dark-mode research assistant web app with glassmorphism (frosted glass panels, blur, subtle white borders on #0B0F19 gradient background).

Layout: 3 columns — left session sidebar (240px), center Perplexity-style chat, right research panel (360px) showing live agent timeline, tool calls, and source cards.

Style like Perplexity: clean research chat, numbered citation pills in answers, source cards with doc title, section, relevance score, and web/memory badges.

Include states: empty chat with suggestion chips, streaming assistant message, clarify question card, research panel mid-run (plan done, researching, 2 source cards), critic score bars.

Components: glass panels, chat bubbles, agent stepper, tool call rows, source cards, upload dropzone, document table.

Desktop 1440px primary artboard + mobile 390px with bottom sheet for sources.

Colors: primary #7C9CFF, success #4ADE80, warning #FBBF24. Font Inter.
```

---

## 10. Integration checklist (after Figma Make export)

- [ ] Place frontend in `frontend/` (Vite + React + TypeScript)
- [ ] Env: `VITE_API_BASE=http://localhost:8000`
- [ ] CORS enabled on FastAPI for dev origin
- [ ] Wire non-stream `/chat` first; mock timeline from final `ChatResponse`
- [ ] Add SSE `/chat/stream` on backend; swap client to EventSource
- [ ] Map citation pill click → scroll to `SourceCard` by index

---

## 11. Out of scope for UI v1

- User auth / multi-tenant billing
- Long-running dormancy webhooks (v2)
- Collaborative editing
- Mobile native app
