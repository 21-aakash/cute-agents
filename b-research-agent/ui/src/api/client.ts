import type {
  AppConfig,
  ChatResponse,
  ChatStreamEvent,
  DocumentRecord,
  SearchHit,
  WorkspaceRecord,
} from '../types';

function headers(apiKey: string): HeadersInit {
  return { 'X-API-Key': apiKey };
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail ?? body.message ?? res.statusText;
  } catch {
    return res.statusText;
  }
}

export async function health(apiBase: string): Promise<{ ok: boolean; postgres: boolean; qdrant: boolean }> {
  const res = await fetch(`${apiBase}/health`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createWorkspace(apiBase: string, name: string): Promise<WorkspaceRecord> {
  const res = await fetch(`${apiBase}/api/v1/workspaces`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function listDocuments(config: AppConfig): Promise<DocumentRecord[]> {
  const res = await fetch(`${config.apiBase}/api/v1/workspaces/${config.workspaceId}/documents`, {
    headers: headers(config.apiKey),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function uploadDocument(config: AppConfig, file: File): Promise<DocumentRecord> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetchWithTimeout(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/documents`,
    {
      method: 'POST',
      headers: headers(config.apiKey),
      body: form,
    },
    180_000,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function searchKnowledgeBase(
  config: AppConfig,
  query: string,
  topK?: number,
): Promise<SearchHit[]> {
  const res = await fetchWithTimeout(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/documents/search`,
    {
      method: 'POST',
      headers: { ...headers(config.apiKey), 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK }),
    },
    60_000,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function deleteDocument(config: AppConfig, docId: string): Promise<void> {
  const res = await fetch(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/documents/${docId}`,
    { method: 'DELETE', headers: headers(config.apiKey) },
  );
  if (!res.ok) throw new Error(await parseError(res));
}

export async function createSession(config: AppConfig): Promise<string> {
  const res = await fetch(`${config.apiBase}/api/v1/workspaces/${config.workspaceId}/sessions`, {
    method: 'POST',
    headers: headers(config.apiKey),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const body = await res.json();
  return String(body.session_id);
}

export async function fetchSessionMessages(
  config: AppConfig,
  sessionId: string,
): Promise<{ query: string; answer: string; critic_score?: number | null }[]> {
  const res = await fetch(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/sessions/${sessionId}/messages`,
    { headers: headers(config.apiKey) },
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init: RequestInit = {},
  timeoutMs = 120_000,
  externalSignal?: AbortSignal,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onExternalAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) {
      clearTimeout(timer);
      throw new DOMException('Generation stopped', 'AbortError');
    }
    externalSignal.addEventListener('abort', onExternalAbort);
  }
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (e) {
    if (externalSignal?.aborted || (e instanceof DOMException && e.name === 'AbortError' && externalSignal)) {
      throw new Error('Generation stopped');
    }
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s`);
    }
    throw e;
  } finally {
    clearTimeout(timer);
    externalSignal?.removeEventListener('abort', onExternalAbort);
  }
}

export async function deleteSession(config: AppConfig, sessionId: string): Promise<void> {
  const res = await fetch(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/sessions/${sessionId}`,
    { method: 'DELETE', headers: headers(config.apiKey) },
  );
  if (!res.ok) throw new Error(await parseError(res));
}

export async function sendChat(
  config: AppConfig,
  sessionId: string,
  query: string,
  webSearchEnabled = true,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await fetchWithTimeout(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/sessions/${sessionId}/chat`,
    {
      method: 'POST',
      headers: { ...headers(config.apiKey), 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, web_search_enabled: webSearchEnabled }),
    },
    120_000,
    signal,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function streamChat(
  config: AppConfig,
  sessionId: string,
  query: string,
  onEvent: (event: ChatStreamEvent) => void,
  webSearchEnabled = true,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await fetch(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/sessions/${sessionId}/chat/stream`,
    {
      method: 'POST',
      headers: {
        ...headers(config.apiKey),
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ query, web_search_enabled: webSearchEnabled }),
      signal,
    },
  );
  if (!res.ok) throw new Error(await parseError(res));
  if (!res.body) throw new Error('Streaming not supported');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResponse: ChatResponse | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith('data: ')) continue;
        const event = JSON.parse(line.slice(6)) as ChatStreamEvent;
        onEvent(event);
        if (event.type === 'error') {
          throw new Error(event.message);
        }
        if (event.type === 'done') {
          finalResponse = event;
        }
      }
    }
  } catch (e) {
    if (signal?.aborted) throw new Error('Generation stopped');
    throw e;
  }

  if (!finalResponse) throw new Error('Stream ended without a response');
  return finalResponse;
}

export async function resumeChat(
  config: AppConfig,
  sessionId: string,
  answer: string,
  webSearchEnabled = true,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await fetchWithTimeout(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/sessions/${sessionId}/chat/resume`,
    {
      method: 'POST',
      headers: { ...headers(config.apiKey), 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer, web_search_enabled: webSearchEnabled }),
    },
    120_000,
    signal,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function resetMemory(config: AppConfig): Promise<void> {
  const res = await fetch(`${config.apiBase}/api/v1/workspaces/${config.workspaceId}/memory`, {
    method: 'DELETE',
    headers: headers(config.apiKey),
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function listEvalRuns(config: AppConfig): Promise<import('../types').EvalRunSummary[]> {
  const res = await fetchWithTimeout(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/evals`,
    { headers: headers(config.apiKey) },
    60_000,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function getEvalRun(config: AppConfig, evalId: string): Promise<import('../types').EvalRunDetail> {
  const res = await fetchWithTimeout(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/evals/${evalId}`,
    { headers: headers(config.apiKey) },
    60_000,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function runEval(
  config: AppConfig,
  mode: 'golden' | 'recent',
  limit = 5,
): Promise<import('../types').EvalRunDetail> {
  const res = await fetchWithTimeout(
    `${config.apiBase}/api/v1/workspaces/${config.workspaceId}/evals/run`,
    {
      method: 'POST',
      headers: { ...headers(config.apiKey), 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, limit }),
    },
    600_000,
  );
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}
