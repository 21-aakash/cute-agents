export type EvidenceOrigin = 'documents' | 'memory' | 'web';

export interface Plan {
  intent: string;
  ready_to_research: boolean;
  sub_queries: string[];
  sources: string[];
  use_memory: boolean;
  reasoning: string;
}

export interface Evidence {
  text: string;
  origin: EvidenceOrigin;
  doc_id?: string | null;
  doc_title: string;
  section?: string | null;
  url?: string | null;
  score: number;
  chunk_index?: number | null;
}

export interface Critique {
  correctness: number;
  completeness: number;
  clarity: number;
  average: number;
  grounded: boolean;
  passed: boolean;
  revision_request?: string | null;
  comments: string;
}

export interface ToolCall {
  tool: string;
  query: string;
  hit_count?: number;
  ts?: number;
}

export interface ChatResponse {
  status: 'completed' | 'needs_clarification';
  answer?: string;
  questions?: string[];
  intent?: string | null;
  plan?: Plan;
  evidence?: Evidence[];
  critique?: Critique;
  revisions?: number;
  run_id?: string;
  tool_calls?: ToolCall[];
}

export interface DocumentRecord {
  id: string;
  title: string;
  filename: string;
  source_type: string;
  chunk_count: number;
  status: 'pending' | 'indexed' | 'failed';
}

export interface SearchHit {
  text: string;
  doc_id?: string | null;
  doc_title: string;
  section?: string | null;
  score: number;
  chunk_index?: number | null;
}

export interface WorkspaceRecord {
  id: string;
  name: string;
  api_key: string;
}

export interface SessionRecord {
  id: string;
  title: string;
}

export interface AppConfig {
  apiBase: string;
  workspaceId: string;
  apiKey: string;
}

export interface EvalRunSummary {
  id: string;
  mode: string;
  status: string;
  sample_count: number;
  metrics_avg: Record<string, number | null>;
  duration_ms?: number | null;
  created_at?: string | null;
  error_message?: string | null;
}

export interface EvalSample {
  id: string;
  question: string;
  answer: string;
  ground_truth: string;
  contexts: string[];
  scores: Record<string, number | null>;
  chat_run_id?: string | null;
}

export interface EvalRunDetail extends EvalRunSummary {
  samples: EvalSample[];
}

export interface ResearchRun {
  plan?: Plan;
  evidence: Evidence[];
  toolCalls: ToolCall[];
  critique?: Critique;
  revisions: number;
  isLoading: boolean;
  activeStep: 'plan' | 'research' | 'write' | 'critique' | 'done';
}

export interface RunMarker {
  id: string;
  kind: 'plan' | 'research' | 'write' | 'critique' | 'tool' | 'sources' | 'revise' | 'thinking';
  label: string;
  active?: boolean;
  variant?: 'default' | 'separator';
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'clarify';
  content: string;
  critique?: Critique;
  questions?: string[];
  revisions?: number;
  markers?: RunMarker[];
  streaming?: boolean;
}

export type ChatStreamEvent =
  | { type: 'intent'; intent: string }
  | { type: 'token'; content: string }
  | { type: 'status'; message: string }
  | { type: 'marker'; marker: RunMarker }
  | { type: 'error'; message: string }
  | ({ type: 'done' } & ChatResponse);
