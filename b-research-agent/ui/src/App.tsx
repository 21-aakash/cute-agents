import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageSquare, Settings, Library, Search, FileText,
  ChevronRight, Brain, Clock, Plus, Zap, AlertTriangle, CheckCircle2,
  Upload, X, Loader2, BookOpen, FilePdf,
  FileSpreadsheet, FileCode, File, Trash2, ChevronDown, Database, Eye, EyeOff, Square,
  BarChart3, LogOut, Briefcase, Cpu, FlaskConical,
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import * as api from './api/client';
import { useAuth } from './context/AuthContext';
import { useWorkspace } from './context/WorkspaceContext';
import { AuthPage } from './components/auth/AuthPage';
import type { ChatMessage, ChatResponse, DocumentRecord, RunMarker } from './types';
import {
  CollapsiblePipeline,
  markersFromResponse,
  mergeStreamMarker,
  thinkingMarker,
} from '@/components/chat/ResearchMarkers';
import { PlainOrFormatted } from '@/components/chat/FormattedAnswer';
import {
  WELCOME_MESSAGE,
  loadStoredMessages,
  saveStoredMessages,
  turnsToMessages,
} from '@/lib/chatStorage';
import EvalDashboard from '@/components/evals/EvalDashboard';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Types ─────────────────────────────────────────────────────────────────────

type AgentMode = 'research' | 'career' | 'ops';
type View = 'chat' | 'library' | 'evals';

type DocType = 'pdf' | 'docx' | 'txt' | 'csv' | 'json' | 'md' | 'other';
type IndexStatus = 'idle' | 'indexing' | 'indexed' | 'error';

interface KBDocument {
  id: string; name: string; type: DocType; description: string;
  file: File | null; fileName: string; fileSize: number;
  status: IndexStatus; enabled: boolean; chunks?: number; uploadedAt: Date;
}

const AGENT_MODES: { id: AgentMode; label: string; icon: React.ElementType; desc: string; color: string }[] = [
  {
    id: 'research',
    label: 'Research',
    icon: FlaskConical,
    desc: 'Deep multi-agent research with citation grounding',
    color: '#6366f1',
  },
  {
    id: 'career',
    label: 'Career',
    icon: Briefcase,
    desc: 'Job search, match scoring & Gmail follow-ups',
    color: '#0ea5e9',
  },
  {
    id: 'ops',
    label: 'OPS',
    icon: Cpu,
    desc: 'Task decomposition from tickets and PRDs',
    color: '#10b981',
  },
];

const COMING_SOON_MESSAGES: Record<AgentMode, { title: string; desc: string; bullets: string[] }> = {
  research: {
    title: 'Research Studio',
    desc: 'Ask anything — the agent plans, searches, writes, and critiques.',
    bullets: [],
  },
  career: {
    title: 'Career Agent',
    desc: 'Your AI-powered job search wingman.',
    bullets: [
      'Upload resume → get match scores for any JD',
      'Auto-tailored resumes using Google XYZ formula',
      'Gmail follow-ups scheduled on Day 3 / 7 / 14',
      'Application Kanban pipeline',
    ],
  },
  ops: {
    title: 'Productivity OPS',
    desc: 'Paste any unstructured input — ticket, PRD, meeting notes.',
    bullets: [
      'AI breaks it into your week automatically',
      'Priority scoring and time estimates',
      'Connects to your work context',
    ],
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileTypeFromFile(file: File): DocType {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  if (ext === 'pdf') return 'pdf';
  if (['doc', 'docx'].includes(ext)) return 'docx';
  if (ext === 'txt') return 'txt';
  if (['csv', 'xls', 'xlsx'].includes(ext)) return 'csv';
  if (ext === 'json') return 'json';
  if (['md', 'mdx'].includes(ext)) return 'md';
  return 'other';
}

function mapDocRecord(d: DocumentRecord): KBDocument {
  const status: IndexStatus =
    d.status === 'indexed' ? 'indexed' :
    d.status === 'failed' ? 'error' :
    d.status === 'pending' ? 'indexing' : 'idle';
  return {
    id: d.id, name: d.title, type: (d.source_type as DocType) || 'other',
    description: d.filename, file: null, fileName: d.filename, fileSize: 0,
    status, enabled: true, chunks: d.chunk_count, uploadedAt: new Date(),
  };
}

function DocTypeIcon({ type, className }: { type: DocType; className?: string }) {
  const cls = cn('shrink-0', className);
  if (type === 'pdf')  return <FileText size={15} className={cn(cls, 'text-red-400')} />;
  if (type === 'csv')  return <FileSpreadsheet size={15} className={cn(cls, 'text-green-500')} />;
  if (type === 'json' || type === 'md') return <FileCode size={15} className={cn(cls, 'text-blue-400')} />;
  if (type === 'docx') return <FileText size={15} className={cn(cls, 'text-indigo-400')} />;
  return <File size={15} className={cn(cls, 'text-gray-400')} />;
}

const SUPPORTED_EXT = ['.pdf', '.txt', '.md'];

// ── Agent Mode Badge ──────────────────────────────────────────────────────────

function ModeBadge({ mode }: { mode: AgentMode }) {
  const m = AGENT_MODES.find(a => a.id === mode)!;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide"
      style={{ background: m.color + '15', color: m.color, border: `1px solid ${m.color}25` }}
    >
      <m.icon size={10} />
      {m.label}
    </span>
  );
}

// ── Coming Soon Panel ─────────────────────────────────────────────────────────

function ComingSoon({ mode }: { mode: AgentMode }) {
  const info = COMING_SOON_MESSAGES[mode];
  const m = AGENT_MODES.find(a => a.id === mode)!;
  return (
    <main className="flex-1 flex flex-col items-center justify-center p-8 text-center">
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5"
        style={{ background: m.color + '12', border: `1px solid ${m.color}20` }}
      >
        <m.icon size={24} style={{ color: m.color }} />
      </div>
      <h2 className="text-[18px] font-bold text-[#111827] mb-2">{info.title}</h2>
      <p className="text-sm text-[#6b7280] max-w-sm mb-6">{info.desc}</p>
      {info.bullets.length > 0 && (
        <ul className="text-left space-y-2 max-w-xs w-full">
          {info.bullets.map(b => (
            <li key={b} className="flex items-start gap-2 text-sm text-[#374151]">
              <span style={{ color: m.color }} className="mt-0.5 text-base leading-none">·</span>
              {b}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-8 px-4 py-2 rounded-lg text-xs font-medium"
        style={{ background: m.color + '10', color: m.color, border: `1px solid ${m.color}20` }}>
        Coming soon — Research Studio is available now
      </div>
    </main>
  );
}

// ── Upload Form ───────────────────────────────────────────────────────────────

function UploadForm({ onUpload, uploading }: { onUpload: (file: File) => Promise<void>; uploading: boolean }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    const ext = '.' + (f.name.split('.').pop()?.toLowerCase() ?? '');
    if (!SUPPORTED_EXT.includes(ext)) { setError('Only PDF, TXT, and Markdown files are supported.'); return; }
    setError(null); setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0]; if (f) handleFile(f);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setError(null);
    try { await onUpload(file); setFile(null); } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-[#e5e7eb] bg-white p-5">
      <div className="flex items-center gap-2">
        <Upload size={15} className="text-[#6366f1]" />
        <span className="font-semibold text-sm text-[#111827]">Add Document</span>
      </div>
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-xl p-6 flex flex-col items-center gap-2 cursor-pointer transition-all duration-200 select-none text-center',
          dragging ? 'border-[#6366f1]/60 bg-[#6366f1]/5' : 'border-[#e5e7eb] hover:border-[#6366f1]/40 hover:bg-[#f9fafb]'
        )}
      >
        <input ref={inputRef} type="file" className="hidden" accept=".pdf,.txt,.md"
          onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} />
        {file ? (
          <>
            <DocTypeIcon type={fileTypeFromFile(file)} className="w-8 h-8" />
            <span className="font-medium text-[#111827] text-sm">{file.name}</span>
            <span className="text-xs text-[#6b7280]">{formatBytes(file.size)}</span>
            <button type="button" onClick={e => { e.stopPropagation(); setFile(null); }}
              className="text-xs text-[#6b7280] hover:text-red-400 transition-colors flex items-center gap-1">
              <X size={11} /> Remove
            </button>
          </>
        ) : (
          <>
            <Upload size={22} className="text-[#9ca3af]" />
            <span className="text-sm text-[#6b7280]">Drop a file or <span className="text-[#6366f1] font-medium">browse</span></span>
            <span className="text-xs text-[#9ca3af]">PDF · TXT · Markdown</span>
          </>
        )}
      </div>
      {error && <div className="text-xs text-red-500 flex items-center gap-1.5"><AlertTriangle size={11} /> {error}</div>}
      <button type="submit" disabled={!file || uploading}
        className="w-full py-2.5 rounded-lg bg-[#6366f1] text-white text-sm font-semibold hover:bg-[#4f46e5] transition-colors disabled:opacity-40 flex items-center justify-center gap-2">
        {uploading ? <Loader2 size={14} className="animate-spin" /> : <Database size={14} />}
        {uploading ? 'Indexing…' : 'Index Document'}
      </button>
    </form>
  );
}

// ── Doc Row ───────────────────────────────────────────────────────────────────

function DocRow({ doc, onToggle, onDelete }: {
  doc: KBDocument; onToggle: (id: string) => void; onDelete: (id: string) => void;
}) {
  return (
    <div className={cn('rounded-xl border border-[#e5e7eb] bg-white p-4 transition-opacity', !doc.enabled && 'opacity-50')}>
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#f3f4f6] border border-[#e5e7eb] flex items-center justify-center shrink-0 mt-0.5">
          <DocTypeIcon type={doc.type} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="font-semibold text-sm text-[#111827] truncate">{doc.name}</span>
            {doc.status === 'indexing' && (
              <span className="text-[10px] font-medium text-[#6366f1] bg-[#6366f1]/10 border border-[#6366f1]/20 px-1.5 py-0.5 rounded-full flex items-center gap-1 shrink-0">
                <Loader2 size={9} className="animate-spin" /> Indexing
              </span>
            )}
            {doc.status === 'indexed' && (
              <span className="text-[10px] font-medium text-[#16a34a] bg-green-50 border border-green-200 px-1.5 py-0.5 rounded-full shrink-0">Indexed</span>
            )}
            {doc.status === 'error' && (
              <span className="text-[10px] font-medium text-red-500 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded-full shrink-0">Error</span>
            )}
          </div>
          <div className="text-xs text-[#6b7280] flex items-center gap-2">
            <span className="uppercase font-medium">{doc.type}</span>
            {doc.chunks !== undefined && <><span>·</span><span>{doc.chunks} chunks</span></>}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => onToggle(doc.id)} title={doc.enabled ? 'Disable' : 'Enable'}
            className={cn('p-1.5 rounded-lg transition-colors', doc.enabled ? 'text-[#6366f1] hover:bg-[#6366f1]/10' : 'text-[#9ca3af] hover:bg-[#f3f4f6]')}>
            {doc.enabled ? <Eye size={14} /> : <EyeOff size={14} />}
          </button>
          <button onClick={() => onDelete(doc.id)} title="Delete"
            className="p-1.5 rounded-lg text-[#9ca3af] hover:text-red-400 hover:bg-red-50 transition-colors">
            <Trash2 size={14} />
          </button>
        </div>
      </div>
      {doc.status === 'indexing' && (
        <div className="mt-3 h-0.5 bg-[#f3f4f6] rounded-full overflow-hidden">
          <div className="h-full bg-[#6366f1] rounded-full animate-[indexing_2s_ease-in-out_infinite]" style={{ width: '60%' }} />
        </div>
      )}
    </div>
  );
}

// ── Library Page ──────────────────────────────────────────────────────────────

function LibraryPage() {
  const { config, connected } = useWorkspace();
  const [docs, setDocs] = useState<KBDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    if (!connected) return;
    setLoading(true); setError(null);
    try { const records = await api.listDocuments(config); setDocs(records.map(mapDocRecord)); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  }, [config, connected]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try { const record = await api.uploadDocument(config, file); setDocs(prev => [mapDocRecord(record), ...prev]); }
    finally { setUploading(false); }
  };

  const enabledCount = docs.filter(d => d.enabled && d.status === 'indexed').length;

  return (
    <div className="flex-1 flex overflow-hidden bg-[#f9fafb]">
      <div className="w-[340px] flex-shrink-0 border-r border-[#e5e7eb] p-5 overflow-y-auto space-y-5 bg-white">
        <div>
          <h1 className="font-bold text-[15px] text-[#111827] mb-1">Knowledge Base</h1>
          <p className="text-xs text-[#6b7280] leading-relaxed">Upload docs to index them. Toggle to control what the agent can retrieve.</p>
        </div>
        <UploadForm onUpload={handleUpload} uploading={uploading} />
        {error && <div className="text-xs text-red-500 flex items-center gap-1.5"><AlertTriangle size={11} /> {error}</div>}
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Active docs', value: enabledCount },
            { label: 'Total', value: docs.length },
          ].map(s => (
            <div key={s.label} className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] p-3">
              <div className="text-2xl font-bold text-[#111827] tabular-nums">{s.value}</div>
              <div className="text-xs text-[#6b7280] mt-0.5">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-sm text-[#111827] flex items-center gap-1.5">
            <BookOpen size={14} className="text-[#6366f1]" /> Documents
            <span className="text-xs text-[#6b7280] bg-[#f3f4f6] px-1.5 py-0.5 rounded-full font-normal">{docs.length}</span>
          </h2>
          <span className="text-xs text-[#6b7280]">{enabledCount} in agent context</span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48 gap-2 text-[#6b7280]">
            <Loader2 size={20} className="animate-spin text-[#6366f1]" />
            <span className="text-sm">Loading…</span>
          </div>
        ) : docs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-2 text-[#9ca3af]">
            <Database size={28} className="opacity-40" />
            <span className="text-sm">No documents yet — upload one to get started.</span>
          </div>
        ) : (
          <div className="space-y-2.5 max-w-2xl">
            {docs.map(doc => (
              <DocRow key={doc.id} doc={doc}
                onToggle={id => setDocs(prev => prev.map(d => d.id === id ? { ...d, enabled: !d.enabled } : d))}
                onDelete={id => { api.deleteDocument(config, id).then(() => setDocs(prev => prev.filter(d => d.id !== id))).catch(e => setError(String(e))); }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Chat Page ─────────────────────────────────────────────────────────────────

function ChatPage({ agentMode }: { agentMode: AgentMode }) {
  const { config, connected, activeSessionId, newSession, renameSession, registerAbortGeneration } = useWorkspace();
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isResearching, setIsResearching] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const [pendingClarify, setPendingClarify] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [liveMarkers, setLiveMarkers] = useState<RunMarker[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string | null>(activeSessionId);
  const abortRef = useRef<AbortController | null>(null);

  const m = AGENT_MODES.find(a => a.id === agentMode)!;

  useEffect(() => { sessionIdRef.current = activeSessionId; }, [activeSessionId]);
  useEffect(() => {
    registerAbortGeneration(() => abortRef.current?.abort());
    return () => registerAbortGeneration(null);
  }, [registerAbortGeneration]);

  const persistMessages = useCallback((sessionId: string, next: ChatMessage[]) => {
    if (config.workspaceId) saveStoredMessages(config.workspaceId, sessionId, next);
  }, [config.workspaceId]);

  const updateMessages = useCallback((updater: (prev: ChatMessage[]) => ChatMessage[], sessionId?: string | null) => {
    setMessages(prev => {
      const next = updater(prev);
      const sid = sessionId ?? sessionIdRef.current;
      if (sid) persistMessages(sid, next);
      return next;
    });
  }, [persistMessages]);

  useEffect(() => {
    if (!activeSessionId || !config.workspaceId) { setMessages([WELCOME_MESSAGE]); return; }
    const cached = loadStoredMessages(config.workspaceId, activeSessionId);
    if (cached.length > 1) { setMessages(cached); return; }
    if (!connected) { setMessages([WELCOME_MESSAGE]); return; }
    let cancelled = false;
    setLoadingHistory(true);
    api.fetchSessionMessages(config, activeSessionId)
      .then(turns => {
        if (cancelled) return;
        const restored = turns.length === 0 ? [WELCOME_MESSAGE] : [WELCOME_MESSAGE, ...turnsToMessages(turns)];
        setMessages(restored); persistMessages(activeSessionId, restored);
      })
      .catch(() => { if (!cancelled) setMessages([WELCOME_MESSAGE]); })
      .finally(() => { if (!cancelled) setLoadingHistory(false); });
    return () => { cancelled = true; };
  }, [activeSessionId, config.workspaceId, connected, persistMessages]);

  useEffect(() => { if (isResearching) setLiveMarkers(thinkingMarker('Starting research…')); }, [isResearching]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isResearching, liveMarkers]);

  const ensureSession = async () => activeSessionId ?? newSession();

  const handleResponse = (res: ChatResponse, sessionId: string, queryForTitle?: string) => {
    if (res.status === 'needs_clarification') {
      setPendingClarify(true);
      updateMessages(prev => [...prev, { role: 'clarify', content: 'I need a bit more context.', questions: res.questions ?? [] }], sessionId);
      setLiveMarkers([]); return;
    }
    setPendingClarify(false);
    const markers = markersFromResponse(res);
    setLiveMarkers([]);
    updateMessages(prev => [...prev, { role: 'assistant', content: res.answer ?? '', markers, revisions: res.revisions ?? 0 }], sessionId);
    if (queryForTitle) renameSession(sessionId, queryForTitle.slice(0, 48));
  };

  const handleSend = async () => {
    if (!inputText.trim() || !connected) return;
    const text = inputText.trim();
    setInputText(''); setIsResearching(true); setChatError(null);
    const controller = new AbortController(); abortRef.current = controller;
    try {
      const sessionId = await ensureSession();
      updateMessages(prev => [...prev, { role: 'user', content: text }, { role: 'assistant', content: '', streaming: true, markers: [] }], sessionId);
      if (pendingClarify) {
        const res = await api.resumeChat(config, sessionId, text, webSearchEnabled, controller.signal);
        updateMessages(prev => prev.slice(0, -1), sessionId);
        handleResponse(res, sessionId); return;
      }
      let gotToken = false;
      const res = await api.streamChat(config, sessionId, text, event => {
        if (event.type === 'status') setLiveMarkers(thinkingMarker(event.message));
        if (event.type === 'marker') {
          setLiveMarkers(prev => mergeStreamMarker(prev, event.marker));
          updateMessages(prev => {
            const next = [...prev]; const last = next[next.length - 1];
            if (last?.role === 'assistant') next[next.length - 1] = { ...last, markers: mergeStreamMarker(last.markers ?? [], event.marker) };
            return next;
          }, sessionId);
        }
        if (event.type === 'token') {
          if (!gotToken) gotToken = true;
          updateMessages(prev => {
            const next = [...prev]; const last = next[next.length - 1];
            if (last?.role === 'assistant') next[next.length - 1] = { ...last, content: last.content + event.content, streaming: true };
            return next;
          }, sessionId);
        }
      }, webSearchEnabled, controller.signal);

      if (res.status === 'needs_clarification') { updateMessages(prev => prev.slice(0, -1), sessionId); handleResponse(res, sessionId); return; }
      setLiveMarkers([]);
      updateMessages(prev => {
        const next = [...prev]; const last = next[next.length - 1];
        if (last?.role === 'assistant') {
          const finalMarkers = markersFromResponse(res);
          next[next.length - 1] = { role: 'assistant', content: res.answer ?? last.content, markers: finalMarkers.length > 0 ? finalMarkers : last.markers, revisions: res.revisions ?? 0, streaming: false };
        }
        return next;
      }, sessionId);
      renameSession(sessionId, text.slice(0, 48));
      setPendingClarify(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      const sid = sessionIdRef.current;
      if (sid) {
        if (msg === 'Generation stopped') {
          updateMessages(prev => {
            const next = [...prev]; const last = next[next.length - 1];
            if (last?.role === 'assistant' && last.streaming) next[next.length - 1] = { ...last, content: last.content || 'Generation stopped.', streaming: false };
            else next.push({ role: 'assistant', content: 'Generation stopped.' });
            return next;
          }, sid);
        } else {
          setChatError(msg);
          updateMessages(prev => {
            const next = [...prev]; const last = next[next.length - 1];
            if (last?.role === 'assistant' && last.streaming && !last.content) next.pop();
            next.push({ role: 'assistant', content: `Sorry, something went wrong: ${msg}` });
            return next;
          }, sid);
          setLiveMarkers([]);
        }
      }
    } finally { abortRef.current = null; setIsResearching(false); }
  };

  const placeholder = agentMode === 'career'
    ? 'Ask about a company, paste a JD, or describe a role you want…'
    : agentMode === 'ops'
    ? 'Paste a ticket, PRD, or meeting notes to decompose…'
    : 'Ask a research question…';

  return (
    <main className="flex-1 flex flex-col relative overflow-hidden bg-[#f9fafb]">
      {chatError && (
        <div className="mx-auto w-full max-w-2xl px-4 mt-3">
          <div className="text-xs text-red-500 flex items-center gap-1.5 bg-red-50 border border-red-100 px-3 py-2 rounded-lg">
            <AlertTriangle size={11} /> {chatError}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="mx-auto w-full max-w-2xl px-4 py-6 space-y-5">
          {loadingHistory && (
            <div className="text-xs text-[#9ca3af] flex items-center gap-2">
              <Loader2 size={11} className="animate-spin" /> Loading conversation…
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={cn('flex w-full animate-fade-in', msg.role === 'user' ? 'justify-end' : 'justify-start')}>
              {msg.role === 'user' ? (
                <div className="max-w-[82%] bg-[#111827] text-white rounded-2xl rounded-br-md px-4 py-2.5 text-[14px] leading-relaxed">
                  {msg.content}
                </div>
              ) : (
                <div className="w-full">
                  {/* Agent label */}
                  <div className="flex items-center gap-1.5 mb-2">
                    <m.icon size={12} style={{ color: m.color }} />
                    <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: m.color }}>
                      {msg.role === 'clarify' ? 'Clarification needed' : m.label + ' Agent'}
                    </span>
                  </div>

                  {msg.markers && msg.markers.length > 0 && (
                    <CollapsiblePipeline markers={msg.markers} live={Boolean(msg.streaming && isResearching)} />
                  )}
                  {/* Live markers */}
                  {msg.streaming && isResearching && liveMarkers.length > 0 && (
                    <CollapsiblePipeline markers={liveMarkers} live />
                  )}

                  <div className="text-[14px] leading-[1.7] text-[#111827]">
                    <PlainOrFormatted text={msg.content} />
                    {msg.streaming && <span className="inline-block w-0.5 h-4 ml-0.5 bg-[#111827] animate-pulse align-middle rounded-full" />}
                  </div>

                  {msg.role === 'clarify' && msg.questions && msg.questions.length > 0 && (
                    <ul className="mt-3 space-y-1.5 text-sm text-[#374151] list-none pl-0">
                      {msg.questions.map((q, j) => (
                        <li key={j} className="flex items-start gap-1.5">
                          <span className="text-[#9ca3af] mt-0.5">·</span>{q}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="px-4 pb-4 pt-2 mx-auto w-full max-w-2xl">
        <div className="rounded-2xl border border-[#e5e7eb] bg-white shadow-sm overflow-hidden">
          <textarea
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder={placeholder}
            className="w-full bg-transparent border-none focus:outline-none resize-none px-4 pt-3 pb-1 text-[14px] text-[#111827] placeholder:text-[#9ca3af] leading-relaxed"
            rows={2}
          />
          <div className="flex justify-between items-center px-3 pb-2.5">
            <div className="flex items-center gap-2">
              <ModeBadge mode={agentMode} />
              <button
                onClick={() => setWebSearchEnabled(v => !v)}
                className={cn(
                  'flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium transition-colors',
                  webSearchEnabled ? 'bg-[#eff6ff] text-[#2563eb] border border-[#bfdbfe]' : 'bg-[#f3f4f6] text-[#9ca3af] border border-[#e5e7eb]'
                )}
              >
                <Search size={10} /> Web
              </button>
            </div>

            {isResearching ? (
              <button onClick={() => abortRef.current?.abort()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 text-red-500 border border-red-100 text-xs font-medium hover:bg-red-100 transition-colors">
                <Square size={11} fill="currentColor" /> Stop
              </button>
            ) : (
              <button onClick={handleSend} disabled={!inputText.trim() || !connected}
                className="px-3 py-1.5 rounded-lg text-white text-xs font-semibold transition-all disabled:opacity-40"
                style={{ background: m.color }}>
                Send
              </button>
            )}
          </div>
        </div>
        <div className="text-center text-[11px] text-[#9ca3af] mt-1.5">
          {!connected ? 'Connecting…' : webSearchEnabled ? 'Web + library retrieval active · AI can make mistakes.' : 'Library-only mode.'}
        </div>
      </div>
    </main>
  );
}

// ── Settings Modal ────────────────────────────────────────────────────────────

function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { config, updateConfig, connect, connecting, connected, error } = useWorkspace();
  const [apiBase, setApiBase] = useState(config.apiBase);
  const [workspaceId, setWorkspaceId] = useState(config.workspaceId);
  const [apiKey, setApiKey] = useState(config.apiKey);

  useEffect(() => { if (open) { setApiBase(config.apiBase); setWorkspaceId(config.workspaceId); setApiKey(config.apiKey); } }, [open, config]);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-2xl border border-[#e5e7eb] shadow-xl p-6 w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-[#111827]">Settings</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#f3f4f6] text-[#9ca3af]"><X size={16} /></button>
        </div>
        <div className="space-y-3">
          {[
            { label: 'API Base URL', value: apiBase, set: setApiBase, placeholder: '(empty = proxy)', mono: false },
            { label: 'Workspace ID', value: workspaceId, set: setWorkspaceId, placeholder: '', mono: true },
            { label: 'API Key', value: apiKey, set: setApiKey, placeholder: '', mono: true },
          ].map(f => (
            <div key={f.label}>
              <label className="block text-xs font-medium text-[#6b7280] mb-1">{f.label}</label>
              <input value={f.value} onChange={e => f.set(e.target.value)} placeholder={f.placeholder}
                className={cn('w-full border border-[#e5e7eb] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#2563eb] bg-[#f9fafb]', f.mono && 'font-mono text-xs')} />
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 text-xs">
          {connecting && <><Loader2 size={11} className="animate-spin text-[#2563eb]" /> Connecting…</>}
          {connected && !connecting && <><CheckCircle2 size={11} className="text-[#16a34a]" /> Connected</>}
          {error && !connecting && <span className="text-red-500">{error}</span>}
        </div>
        <div className="flex gap-2">
          <button onClick={() => { updateConfig({ apiBase, workspaceId, apiKey }); connect(); }}
            className="flex-1 py-2 rounded-lg bg-[#2563eb] text-white text-sm font-medium hover:bg-[#1d4ed8] transition-colors">
            Save & Connect
          </button>
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-[#e5e7eb] text-[#6b7280] text-sm hover:bg-[#f9fafb]">Close</button>
        </div>
      </div>
    </div>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function App() {
  const { isAuthenticated, isLoading: authLoading, user, logout } = useAuth();
  const [agentMode, setAgentMode] = useState<AgentMode>('research');
  const [view, setView] = useState<View>('chat');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const { connected, connecting, error, sessions, activeSessionId, setActiveSessionId, newSession, deleteSession } = useWorkspace();

  const handleNewChat = async () => { await newSession(); setView('chat'); };

  if (authLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[#f9fafb]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-7 h-7 border-2 border-[#2563eb]/20 border-t-[#2563eb] rounded-full animate-spin" />
          <span className="text-xs text-[#9ca3af]">Loading…</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return <AuthPage />;

  const currentMode = AGENT_MODES.find(a => a.id === agentMode)!;

  return (
    <div className="flex h-screen w-full overflow-hidden text-sm bg-[#f9fafb]">
      {/* ── Connection banner ── */}
      {(connecting || error) && (
        <div className={cn(
          'fixed top-0 left-0 right-0 z-50 px-4 py-1.5 text-xs flex items-center gap-2 border-b',
          error ? 'bg-red-50 border-red-200 text-red-600' : 'bg-blue-50 border-blue-200 text-[#2563eb]'
        )}>
          {connecting ? <Loader2 size={11} className="animate-spin" /> : <AlertTriangle size={11} />}
          {connecting ? 'Connecting to backend…' : error}
          {!connecting && <button onClick={() => setSettingsOpen(true)} className="underline ml-auto">Settings</button>}
        </div>
      )}

      {/* ── Left Sidebar ── */}
      <aside className="w-[220px] flex-shrink-0 flex flex-col border-r border-[#e5e7eb] bg-white">
        {/* Logo */}
        <div className="h-12 flex items-center gap-2.5 px-4 border-b border-[#e5e7eb] shrink-0">
          <div className="w-7 h-7 rounded-lg bg-[#2563eb] flex items-center justify-center">
            <Zap size={14} className="text-white" />
          </div>
          <span className="font-bold text-[#111827] text-[15px]">Nexus</span>
          {connected && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[#16a34a]" title="Connected" />}
        </div>

        {/* Agent Mode Switcher */}
        <div className="p-3 border-b border-[#e5e7eb] shrink-0">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9ca3af] px-1 mb-2">Agents</div>
          {AGENT_MODES.map(mode => (
            <button
              key={mode.id}
              onClick={() => { setAgentMode(mode.id); setView('chat'); }}
              className={cn(
                'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-all mb-0.5',
                agentMode === mode.id
                  ? 'bg-[#f3f4f6] text-[#111827] font-medium'
                  : 'text-[#6b7280] hover:bg-[#f9fafb] hover:text-[#374151]'
              )}
            >
              <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0"
                style={{ background: agentMode === mode.id ? mode.color + '15' : 'transparent' }}>
                <mode.icon size={13} style={{ color: agentMode === mode.id ? mode.color : undefined }} />
              </div>
              <span className="text-[13px]">{mode.label}</span>
              {mode.id !== 'research' && (
                <span className="ml-auto text-[9px] font-medium text-[#9ca3af] bg-[#f3f4f6] px-1.5 py-0.5 rounded-full">Soon</span>
              )}
            </button>
          ))}
        </div>

        {/* Session list (only for Research for now) */}
        <div className="flex-1 overflow-hidden flex flex-col p-3">
          <button onClick={handleNewChat} disabled={!connected}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg border border-dashed border-[#e5e7eb] text-[#9ca3af] text-xs hover:border-[#d1d5db] hover:text-[#6b7280] transition-colors mb-3 disabled:opacity-40">
            <Plus size={13} /> New chat
          </button>

          <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9ca3af] px-1 mb-1.5">Sessions</div>
          <div className="flex-1 overflow-y-auto scrollbar-thin space-y-0.5">
            {sessions.length === 0 ? (
              <div className="text-[11px] text-[#9ca3af] px-1 italic">No sessions yet</div>
            ) : sessions.map(s => (
              <div key={s.id} className={cn(
                'group flex items-center gap-0.5 rounded-md transition-colors',
                activeSessionId === s.id ? 'bg-[#eff6ff] border border-[#bfdbfe]' : 'hover:bg-[#f3f4f6] border border-transparent'
              )}>
                <button onClick={() => { setActiveSessionId(s.id); setView('chat'); }}
                  className={cn('flex-1 min-w-0 text-left px-2.5 py-1.5 text-[12px] truncate', activeSessionId === s.id ? 'text-[#2563eb] font-medium' : 'text-[#6b7280]')}>
                  {s.title}
                </button>
                <button onClick={e => { e.stopPropagation(); deleteSession(s.id).catch(() => {}); }}
                  className="shrink-0 p-1 mr-0.5 rounded text-[#9ca3af] opacity-0 group-hover:opacity-100 hover:text-red-400 transition-all">
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom: nav + user */}
        <div className="border-t border-[#e5e7eb] p-2 shrink-0 space-y-0.5">
          {[
            { id: 'library' as View, icon: Library, label: 'Library' },
            { id: 'evals' as View, icon: BarChart3, label: 'Evals' },
          ].map(nav => (
            <button key={nav.id} onClick={() => setView(nav.id)}
              className={cn('w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs transition-colors',
                view === nav.id ? 'bg-[#f3f4f6] text-[#374151] font-medium' : 'text-[#9ca3af] hover:text-[#6b7280] hover:bg-[#f9fafb]')}>
              <nav.icon size={13} /> {nav.label}
            </button>
          ))}
          <button onClick={() => setSettingsOpen(true)}
            className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs text-[#9ca3af] hover:text-[#6b7280] hover:bg-[#f9fafb] transition-colors">
            <Settings size={13} /> Settings
          </button>

          {user && (
            <div className="flex items-center gap-2 px-2.5 py-2 mt-1 border-t border-[#f3f4f6]">
              <div className="w-6 h-6 rounded-full bg-[#2563eb] flex items-center justify-center text-white text-[10px] font-bold uppercase shrink-0">
                {(user.full_name || user.email).charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] font-medium text-[#374151] truncate">{user.full_name || user.email}</div>
              </div>
              <button onClick={logout} title="Sign out" className="p-1 rounded text-[#9ca3af] hover:text-red-400 transition-colors shrink-0">
                <LogOut size={12} />
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* ── Main content ── */}
      {view === 'chat'
        ? (agentMode === 'research' ? <ChatPage agentMode={agentMode} /> : <ComingSoon mode={agentMode} />)
        : view === 'library' ? <LibraryPage />
        : <EvalDashboard />
      }

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
