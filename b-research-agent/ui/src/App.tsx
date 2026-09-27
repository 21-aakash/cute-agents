import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageSquare, Settings, Library, Search, FileText,
  ChevronRight, Brain, Clock, Plus, Zap, AlertTriangle, Play, CheckCircle2,
  Upload, X, ToggleLeft, ToggleRight, Loader2, BookOpen, FilePdf,
  FileSpreadsheet, FileCode, File, Trash2, ChevronDown, Database, Eye, EyeOff, Square,
  BarChart3,
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import * as api from './api/client';
import { useWorkspace } from './context/WorkspaceContext';
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

type View = 'chat' | 'library' | 'evals';

type DocType = 'pdf' | 'docx' | 'txt' | 'csv' | 'json' | 'md' | 'other';
type IndexStatus = 'idle' | 'indexing' | 'indexed' | 'error';

interface KBDocument {
  id: string;
  name: string;
  type: DocType;
  description: string;
  file: File | null;
  fileName: string;
  fileSize: number;
  status: IndexStatus;
  enabled: boolean;
  chunks?: number;
  uploadedAt: Date;
}

const DOC_TYPE_OPTIONS: { value: DocType; label: string }[] = [
  { value: 'pdf', label: 'PDF' },
  { value: 'docx', label: 'Word Document' },
  { value: 'txt', label: 'Plain Text' },
  { value: 'csv', label: 'CSV / Spreadsheet' },
  { value: 'json', label: 'JSON' },
  { value: 'md', label: 'Markdown' },
  { value: 'other', label: 'Other' },
];

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

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function DocTypeIcon({ type, className }: { type: DocType; className?: string }) {
  const cls = cn("shrink-0", className);
  if (type === 'pdf') return <FileText size={16} className={cn(cls, "text-red-400")} />;
  if (type === 'csv') return <FileSpreadsheet size={16} className={cn(cls, "text-green-400")} />;
  if (type === 'json' || type === 'md') return <FileCode size={16} className={cn(cls, "text-blue-400")} />;
  if (type === 'docx') return <FileText size={16} className={cn(cls, "text-indigo-400")} />;
  return <File size={16} className={cn(cls, "text-text-muted")} />;
}

const SUPPORTED_EXT = ['.pdf', '.txt', '.md'];

function mapDocRecord(d: DocumentRecord): KBDocument {
  const status: IndexStatus =
    d.status === 'indexed' ? 'indexed' :
    d.status === 'failed' ? 'error' :
    d.status === 'pending' ? 'indexing' : 'idle';
  return {
    id: d.id,
    name: d.title,
    type: (d.source_type as DocType) || 'other',
    description: d.filename,
    file: null,
    fileName: d.filename,
    fileSize: 0,
    status,
    enabled: true,
    chunks: d.chunk_count,
    uploadedAt: new Date(),
  };
}

const IconButton = ({ icon: Icon, onClick, active, className, title }: any) => (
  <button
    onClick={onClick}
    title={title}
    className={cn(
      "p-2 rounded-lg transition-colors duration-200",
      active ? "bg-glass-bg-elevated text-primary" : "text-text-muted hover:bg-glass-bg hover:text-text-body",
      className
    )}
  >
    <Icon size={20} />
  </button>
);

// ── Upload Form ──────────────────────────────────────────────────────────────

function UploadForm({ onUpload, uploading }: { onUpload: (file: File) => Promise<void>; uploading: boolean }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    const ext = '.' + (f.name.split('.').pop()?.toLowerCase() ?? '');
    if (!SUPPORTED_EXT.includes(ext)) {
      setError('Only PDF, TXT, and Markdown files are supported.');
      return;
    }
    setError(null);
    setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setError(null);
    try {
      await onUpload(file);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const canSubmit = !!file && !uploading;

  return (
    <form onSubmit={handleSubmit} className="glass-panel-elevated rounded-2xl p-5 space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <Upload size={16} className="text-primary" />
        <h2 className="font-semibold text-[15px]">Add Document</h2>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-xl p-6 flex flex-col items-center gap-2 cursor-pointer transition-all duration-200 select-none",
          dragging ? "border-primary/60 bg-primary/5" : "border-glass-border hover:border-primary/40 hover:bg-glass-bg"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".pdf,.txt,.md"
          onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }}
        />
        {file ? (
          <>
            <DocTypeIcon type={fileTypeFromFile(file)} className="w-8 h-8" />
            <span className="font-medium text-text-body text-sm">{file.name}</span>
            <span className="text-xs text-text-muted">{formatBytes(file.size)}</span>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              className="text-xs text-text-muted hover:text-red-400 transition-colors flex items-center gap-1 mt-1"
            >
              <X size={12} /> Remove
            </button>
          </>
        ) : (
          <>
            <Upload size={24} className="text-text-muted" />
            <span className="text-sm text-text-muted">Drop a file here or <span className="text-primary font-medium">browse</span></span>
            <span className="text-xs text-text-muted">PDF · TXT · Markdown</span>
          </>
        )}
      </div>

      {error && (
        <div className="text-xs text-red-400 flex items-center gap-1.5">
          <AlertTriangle size={12} /> {error}
        </div>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="w-full py-2.5 rounded-lg bg-primary/20 border border-primary/30 text-primary font-semibold text-sm hover:bg-primary hover:text-white transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {uploading ? <Loader2 size={15} className="animate-spin" /> : <Database size={15} />}
        {uploading ? 'Indexing…' : 'Index Document'}
      </button>
    </form>
  );
}

// ── Document Row ─────────────────────────────────────────────────────────────

function DocRow({
  doc,
  onToggle,
  onDelete,
  onIndex,
}: {
  doc: KBDocument;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
  onIndex: (id: string) => void;
}) {
  return (
    <div className={cn(
      "glass-panel-elevated rounded-xl p-4 transition-all duration-200",
      !doc.enabled && "opacity-60"
    )}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 w-8 h-8 rounded-lg bg-glass-bg border border-glass-border flex items-center justify-center shrink-0">
          <DocTypeIcon type={doc.type} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-semibold text-sm text-text-body truncate">{doc.name}</span>
            {doc.status === 'indexing' && (
              <span className="text-[10px] font-medium text-primary bg-primary/10 border border-primary/20 px-1.5 py-0.5 rounded-full flex items-center gap-1 shrink-0">
                <Loader2 size={10} className="animate-spin" /> Indexing
              </span>
            )}
            {doc.status === 'indexed' && (
              <span className="text-[10px] font-medium text-success bg-success/10 border border-success/20 px-1.5 py-0.5 rounded-full shrink-0">
                Indexed
              </span>
            )}
            {doc.status === 'idle' && (
              <span className="text-[10px] font-medium text-text-muted bg-glass-bg border border-glass-border px-1.5 py-0.5 rounded-full shrink-0">
                Pending
              </span>
            )}
            {doc.status === 'error' && (
              <span className="text-[10px] font-medium text-red-400 bg-red-400/10 border border-red-400/20 px-1.5 py-0.5 rounded-full shrink-0">
                Error
              </span>
            )}
          </div>

          <div className="text-xs text-text-muted mb-2 leading-relaxed line-clamp-2">
            {doc.description || <span className="italic">No description</span>}
          </div>

          <div className="flex items-center gap-3 text-[11px] text-text-muted">
            <span className="uppercase font-medium">{doc.type}</span>
            <span>·</span>
            <span>{formatBytes(doc.fileSize)}</span>
            {doc.chunks !== undefined && (
              <>
                <span>·</span>
                <span>{doc.chunks} chunks</span>
              </>
            )}
            <span>·</span>
            <span>{doc.uploadedAt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0 ml-1">
          {doc.status === 'idle' && (
            <button
              onClick={() => onIndex(doc.id)}
              className="p-1.5 rounded-lg text-primary hover:bg-primary/10 transition-colors"
              title="Index now"
            >
              <Database size={15} />
            </button>
          )}
          <button
            onClick={() => onToggle(doc.id)}
            title={doc.enabled ? "Disable for agent context" : "Enable for agent context"}
            className={cn("p-1.5 rounded-lg transition-colors", doc.enabled ? "text-primary hover:bg-primary/10" : "text-text-muted hover:bg-glass-bg")}
          >
            {doc.enabled ? <Eye size={15} /> : <EyeOff size={15} />}
          </button>
          <button
            onClick={() => onDelete(doc.id)}
            className="p-1.5 rounded-lg text-text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors"
            title="Delete"
          >
            <Trash2 size={15} />
          </button>
        </div>
      </div>

      {/* Indexing progress bar */}
      {doc.status === 'indexing' && (
        <div className="mt-3 h-1 bg-glass-bg rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full animate-[indexing_2s_ease-in-out_infinite]" style={{ width: '60%' }} />
        </div>
      )}
    </div>
  );
}

// ── Library Page ─────────────────────────────────────────────────────────────

function LibraryPage() {
  const { config, connected } = useWorkspace();
  const [docs, setDocs] = useState<KBDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDocs = useCallback(async () => {
    if (!connected) return;
    setLoading(true);
    setError(null);
    try {
      const records = await api.listDocuments(config);
      setDocs(records.map(mapDocRecord));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [config, connected]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const record = await api.uploadDocument(config, file);
      setDocs(prev => [mapDocRecord(record), ...prev]);
    } finally {
      setUploading(false);
    }
  };

  const handleToggle = (id: string) => {
    setDocs(prev => prev.map(d => d.id === id ? { ...d, enabled: !d.enabled } : d));
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDocument(config, id);
      setDocs(prev => prev.filter(d => d.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const enabledCount = docs.filter(d => d.enabled && d.status === 'indexed').length;
  const totalChunks = docs.filter(d => d.enabled && d.status === 'indexed').reduce((s, d) => s + (d.chunks ?? 0), 0);

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: Upload form */}
      <div className="w-[380px] flex-shrink-0 border-r border-glass-border p-6 overflow-y-auto space-y-5">
        <div>
          <h1 className="font-semibold text-[17px] mb-0.5">Knowledge Base</h1>
          <p className="text-xs text-text-muted leading-relaxed">
            Upload documents to index them in the vector store. Enable or disable each one to control what the agent can retrieve.
          </p>
        </div>

        <UploadForm onUpload={handleUpload} uploading={uploading} />

        {error && (
          <div className="text-xs text-red-400 flex items-center gap-1.5">
            <AlertTriangle size={12} /> {error}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="glass-panel rounded-xl p-3">
            <div className="text-[22px] font-bold tabular-nums text-text-body">{enabledCount}</div>
            <div className="text-xs text-text-muted mt-0.5">Active documents</div>
          </div>
          <div className="glass-panel rounded-xl p-3">
            <div className="text-[22px] font-bold tabular-nums text-text-body">{totalChunks}</div>
            <div className="text-xs text-text-muted mt-0.5">Indexed chunks</div>
          </div>
        </div>
      </div>

      {/* Right: Document list */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-sm text-text-body flex items-center gap-2">
            <BookOpen size={15} className="text-primary" />
            Documents
            <span className="text-xs font-normal text-text-muted bg-glass-bg px-2 py-0.5 rounded-full">{docs.length}</span>
          </h2>
          <span className="text-xs text-text-muted">{enabledCount} in agent context</span>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3 text-text-muted">
            <Loader2 size={24} className="animate-spin text-primary" />
            <span className="text-sm">Loading documents…</span>
          </div>
        ) : docs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3 text-text-muted">
            <Database size={32} className="opacity-30" />
            <span className="text-sm">No documents yet — upload one to get started.</span>
          </div>
        ) : (
          <div className="space-y-3 max-w-3xl">
            {docs.map(doc => (
              <DocRow
                key={doc.id}
                doc={doc}
                onToggle={handleToggle}
                onDelete={(id) => { handleDelete(id).catch(e => setError(String(e))); }}
                onIndex={() => {}}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Chat Page ────────────────────────────────────────────────────────────────

function ChatPage() {
  const { config, connected, activeSessionId, newSession, renameSession, registerAbortGeneration } = useWorkspace();
  const [inputText, setInputText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [isResearching, setIsResearching] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(true);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [pendingClarify, setPendingClarify] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [liveMarkers, setLiveMarkers] = useState<RunMarker[]>([]);
  const toolsRef = useRef<HTMLDivElement>(null);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string | null>(activeSessionId);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    sessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  useEffect(() => {
    registerAbortGeneration(() => abortRef.current?.abort());
    return () => registerAbortGeneration(null);
  }, [registerAbortGeneration]);

  const persistMessages = useCallback(
    (sessionId: string, next: ChatMessage[]) => {
      if (config.workspaceId) {
        saveStoredMessages(config.workspaceId, sessionId, next);
      }
    },
    [config.workspaceId],
  );

  const updateMessages = useCallback(
    (updater: (prev: ChatMessage[]) => ChatMessage[], sessionId?: string | null) => {
      setMessages((prev) => {
        const next = updater(prev);
        const sid = sessionId ?? sessionIdRef.current;
        if (sid) persistMessages(sid, next);
        return next;
      });
    },
    [persistMessages],
  );

  // Load chat history when session or workspace changes
  useEffect(() => {
    if (!activeSessionId || !config.workspaceId) {
      setMessages([WELCOME_MESSAGE]);
      return;
    }

    const cached = loadStoredMessages(config.workspaceId, activeSessionId);
    if (cached.length > 1) {
      setMessages(cached);
      return;
    }

    if (!connected) {
      setMessages([WELCOME_MESSAGE]);
      return;
    }

    let cancelled = false;
    setLoadingHistory(true);
    api.fetchSessionMessages(config, activeSessionId)
      .then((turns) => {
        if (cancelled) return;
        if (turns.length === 0) {
          setMessages([WELCOME_MESSAGE]);
          return;
        }
        const restored = [WELCOME_MESSAGE, ...turnsToMessages(turns)];
        setMessages(restored);
        persistMessages(activeSessionId, restored);
      })
      .catch(() => {
        if (!cancelled) setMessages([WELCOME_MESSAGE]);
      })
      .finally(() => {
        if (!cancelled) setLoadingHistory(false);
      });

    return () => { cancelled = true; };
  }, [activeSessionId, config.workspaceId, connected, persistMessages]);

  useEffect(() => {
    if (!isResearching) return;
    setLiveMarkers(thinkingMarker('Starting research…'));
  }, [isResearching]);

  useEffect(() => {
    if (!toolsOpen) return;
    const handler = (e: MouseEvent) => {
      if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) {
        setToolsOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [toolsOpen]);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isResearching, liveMarkers]);

  const ensureSession = async (): Promise<string> => {
    if (activeSessionId) return activeSessionId;
    return newSession();
  };

  const handleResponse = (res: ChatResponse, sessionId: string, queryForTitle?: string) => {
    if (res.status === 'needs_clarification') {
      setPendingClarify(true);
      updateMessages(prev => [...prev, {
        role: 'clarify',
        content: 'I need a bit more context before researching.',
        questions: res.questions ?? [],
      }], sessionId);
      setLiveMarkers([]);
      return;
    }
    setPendingClarify(false);
    const markers = markersFromResponse(res);
    setLiveMarkers([]);
    updateMessages(prev => [...prev, {
      role: 'assistant',
      content: res.answer ?? '',
      markers,
      revisions: res.revisions ?? 0,
    }], sessionId);
    if (queryForTitle) {
      renameSession(sessionId, queryForTitle.slice(0, 48));
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setLiveMarkers([]);
  };

  const handleSend = async () => {
    if (!inputText.trim() || !connected) return;
    const text = inputText.trim();
    setInputText("");
    setIsResearching(true);
    setChatError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const sessionId = await ensureSession();
      updateMessages(
        prev => [
          ...prev,
          { role: 'user', content: text },
          { role: 'assistant', content: '', streaming: true, markers: [] },
        ],
        sessionId,
      );

      if (pendingClarify) {
        const res = await api.resumeChat(config, sessionId, text, webSearchEnabled, controller.signal);
        updateMessages(prev => {
          const next = prev.slice(0, -1);
          return next;
        }, sessionId);
        handleResponse(res, sessionId);
        return;
      }

      let gotToken = false;
      const res = await api.streamChat(
        config,
        sessionId,
        text,
        (event) => {
          if (event.type === 'status') {
            setLiveMarkers(thinkingMarker(event.message));
          }
          if (event.type === 'marker') {
            setLiveMarkers((prev) => mergeStreamMarker(prev, event.marker));
            updateMessages(prev => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === 'assistant') {
                next[next.length - 1] = {
                  ...last,
                  markers: mergeStreamMarker(last.markers ?? [], event.marker),
                };
              }
              return next;
            }, sessionId);
          }
          if (event.type === 'token') {
            if (!gotToken) {
              gotToken = true;
            }
            updateMessages(prev => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === 'assistant') {
                next[next.length - 1] = {
                  ...last,
                  content: last.content + event.content,
                  streaming: true,
                };
              }
              return next;
            }, sessionId);
          }
        },
        webSearchEnabled,
        controller.signal,
      );

      if (res.status === 'needs_clarification') {
        updateMessages(prev => prev.slice(0, -1), sessionId);
        handleResponse(res, sessionId);
        return;
      }

      setLiveMarkers([]);
      updateMessages(prev => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === 'assistant') {
          const finalMarkers = markersFromResponse(res);
          next[next.length - 1] = {
            role: 'assistant',
            content: res.answer ?? last.content,
            markers: finalMarkers.length > 0 ? finalMarkers : last.markers,
            revisions: res.revisions ?? 0,
            streaming: false,
          };
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
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === 'assistant' && last.streaming) {
              next[next.length - 1] = {
                ...last,
                content: last.content || 'Generation stopped.',
                streaming: false,
              };
            } else {
              next.push({ role: 'assistant', content: 'Generation stopped.' });
            }
            return next;
          }, sid);
        } else {
          setChatError(msg);
          updateMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === 'assistant' && last.streaming && !last.content) {
              next.pop();
            }
            next.push({ role: 'assistant', content: `Sorry, something went wrong: ${msg}` });
            return next;
          }, sid);
          setLiveMarkers([]);
        }
      }
    } finally {
      abortRef.current = null;
      setIsResearching(false);
    }
  };

  return (
    <main className="flex-1 flex flex-col relative overflow-hidden">
        {chatError && (
          <div className="mx-auto w-full max-w-3xl px-4 mt-3">
            <div className="text-xs text-red-400 flex items-center gap-1.5 glass-panel px-3 py-2 rounded-lg">
              <AlertTriangle size={12} /> {chatError}
            </div>
          </div>
        )}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-3xl px-4 py-6 space-y-6">
          {loadingHistory && (
            <div className="text-xs text-text-muted flex items-center gap-2">
              <Loader2 size={12} className="animate-spin" /> Loading conversation…
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={cn("flex w-full", msg.role === 'user' ? "justify-end" : "justify-start")}>
              <div className={cn(
                "rounded-2xl p-4 leading-[1.6] text-[15px]",
                msg.role === 'user'
                  ? "glass-panel-elevated max-w-[85%]"
                  : "bg-transparent w-full",
              )}>
                {msg.role !== 'user' && (
                  <div className="flex items-center gap-2 mb-2 text-text-muted font-medium text-xs uppercase tracking-wider">
                    <Zap size={14} className="text-primary" />
                    {msg.role === 'clarify' ? 'Clarification needed' : 'Research Assistant'}
                  </div>
                )}
                {msg.markers && msg.markers.length > 0 && (
                  <CollapsiblePipeline
                    markers={msg.markers}
                    live={Boolean(msg.streaming && isResearching)}
                  />
                )}
                <PlainOrFormatted text={msg.content} />
                {msg.streaming && (
                  <span className="inline-block w-0.5 h-4 ml-0.5 bg-primary animate-pulse align-middle" />
                )}
                {msg.role === 'clarify' && msg.questions && msg.questions.length > 0 && (
                  <ul className="mt-3 space-y-1.5 text-sm text-text-muted list-disc pl-4">
                    {msg.questions.map((q, j) => <li key={j}>{q}</li>)}
                  </ul>
                )}
              </div>
            </div>
          ))}
          <div ref={endOfMessagesRef} />
          </div>
        </div>

        <div className="pb-4 pt-2 mx-auto w-full max-w-3xl px-4 relative z-20">
          <div className="glass-panel-elevated rounded-2xl p-2 flex flex-col">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={pendingClarify ? "Answer the clarification question…" : "Ask a research question..."}
              className="w-full bg-transparent border-none focus:outline-none resize-none p-3 h-14 text-[15px] placeholder:text-text-muted"
            />
            <div className="flex justify-between items-center px-2 pb-1">
              <div className="flex items-center gap-2">
                {/* Plus → tools popover */}
                <div className="relative" ref={toolsRef}>
                  <button
                    onClick={() => setToolsOpen(v => !v)}
                    className={cn(
                      "p-2 rounded-lg transition-colors duration-150",
                      toolsOpen
                        ? "bg-primary/10 text-primary"
                        : "text-text-muted hover:bg-glass-bg hover:text-text-body"
                    )}
                  >
                    <Plus size={18} className={cn("transition-transform duration-200", toolsOpen && "rotate-45")} />
                  </button>

                  {toolsOpen && (
                    <div className="absolute bottom-full left-0 mb-2 w-[220px] glass-panel-elevated rounded-xl border border-glass-border shadow-lg overflow-hidden z-50">
                      <div className="px-3 pt-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                        Agent Tools
                      </div>

                      {/* Web search row */}
                      <button
                        onClick={() => setWebSearchEnabled(v => !v)}
                        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-glass-bg transition-colors text-left"
                      >
                        <div className={cn(
                          "w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors",
                          webSearchEnabled ? "bg-primary/15 text-primary" : "bg-glass-bg text-text-muted"
                        )}>
                          <Search size={14} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-text-body leading-none mb-0.5">Web Search</div>
                          <div className="text-[11px] text-text-muted">Live web results</div>
                        </div>
                        <span className={cn(
                          "w-8 h-4 rounded-full relative transition-colors duration-200 shrink-0",
                          webSearchEnabled ? "bg-primary" : "bg-glass-border"
                        )}>
                          <span className={cn(
                            "absolute top-0.5 w-3 h-3 rounded-full bg-white shadow-sm transition-transform duration-200",
                            webSearchEnabled ? "translate-x-4" : "translate-x-0.5"
                          )} />
                        </span>
                      </button>

                      <div className="h-px bg-glass-border mx-3" />

                      <div className="w-full flex items-center gap-3 px-3 py-2.5 opacity-60 cursor-default">
                        <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 bg-primary/15 text-primary">
                          <BookOpen size={14} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-text-body leading-none mb-0.5">Document Retrieval</div>
                          <div className="text-[11px] text-text-muted">Always active</div>
                        </div>
                        <span className="w-8 h-4 rounded-full relative bg-primary shrink-0">
                          <span className="absolute top-0.5 right-0.5 w-3 h-3 rounded-full bg-white shadow-sm" />
                        </span>
                      </div>

                      <div className="px-3 pb-2.5 pt-1">
                        <div className={cn(
                          "text-[11px] px-2 py-1.5 rounded-lg text-center font-medium transition-colors",
                          webSearchEnabled ? "bg-primary/10 text-primary" : "bg-glass-bg text-text-muted"
                        )}>
                          {webSearchEnabled ? "Web + Library retrieval active" : "Library-only mode"}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {webSearchEnabled && (
                  <button
                    onClick={() => setWebSearchEnabled(false)}
                    className="flex items-center gap-1 px-2 py-1 rounded-md bg-primary/10 border border-primary/20 text-primary text-xs font-medium hover:bg-primary/20 transition-colors group"
                  >
                    <Search size={11} />
                    Web
                    <X size={10} className="opacity-50 group-hover:opacity-100 ml-0.5" />
                  </button>
                )}
              </div>

              {isResearching ? (
                <button
                  onClick={handleStop}
                  className="bg-red-500/15 text-red-400 border border-red-400/30 hover:bg-red-500/25 px-4 py-1.5 rounded-lg font-medium transition-all duration-200 flex items-center gap-1.5"
                >
                  <Square size={14} fill="currentColor" />
                  Stop
                </button>
              ) : (
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim() || !connected}
                  className="bg-primary/20 text-primary border border-primary/30 hover:bg-primary hover:text-white px-4 py-1.5 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Send
                </button>
              )}
            </div>
          </div>
          <div className="text-center text-xs text-text-muted mt-2">
            {!connected
              ? "Connecting to backend…"
              : webSearchEnabled
                ? "Searches the web and your library · AI can make mistakes."
                : "Library-only mode · web search is off · AI can make mistakes."}
          </div>
        </div>
      </main>
  );
}

// ── Settings Modal ───────────────────────────────────────────────────────────

function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { config, updateConfig, connect, connecting, connected, error } = useWorkspace();
  const [apiBase, setApiBase] = useState(config.apiBase);
  const [workspaceId, setWorkspaceId] = useState(config.workspaceId);
  const [apiKey, setApiKey] = useState(config.apiKey);

  useEffect(() => {
    if (open) {
      setApiBase(config.apiBase);
      setWorkspaceId(config.workspaceId);
      setApiKey(config.apiKey);
    }
  }, [open, config]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={onClose}>
      <div className="glass-panel-elevated rounded-2xl p-6 w-full max-w-md space-y-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-[15px]">Settings</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-glass-bg text-text-muted"><X size={18} /></button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">API Base URL</label>
            <input
              value={apiBase}
              onChange={e => setApiBase(e.target.value)}
              placeholder="(empty = same origin via proxy)"
              className="w-full bg-glass-bg border border-glass-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/50"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">Workspace ID</label>
            <input
              value={workspaceId}
              onChange={e => setWorkspaceId(e.target.value)}
              className="w-full bg-glass-bg border border-glass-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/50 font-mono text-xs"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-text-muted mb-1">API Key</label>
            <input
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              type="password"
              className="w-full bg-glass-bg border border-glass-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/50 font-mono text-xs"
            />
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs">
          {connecting && <><Loader2 size={12} className="animate-spin text-primary" /> Connecting…</>}
          {connected && !connecting && <><CheckCircle2 size={12} className="text-success" /> Connected</>}
          {error && !connecting && <span className="text-red-400">{error}</span>}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => {
              updateConfig({ apiBase, workspaceId, apiKey });
              connect();
            }}
            className="flex-1 py-2 rounded-lg bg-primary/20 border border-primary/30 text-primary font-medium text-sm hover:bg-primary hover:text-white transition-colors"
          >
            Save & Connect
          </button>
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-glass-border text-text-muted hover:bg-glass-bg text-sm">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [view, setView] = useState<View>('chat');
  const [collapsed, setCollapsed] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const {
    connected, connecting, error, sessions, activeSessionId,
    setActiveSessionId, newSession, deleteSession,
  } = useWorkspace();

  const handleNewChat = async () => {
    await newSession();
    setView('chat');
  };

  const handleDeleteSession = async (id: string) => {
    await deleteSession(id);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden text-sm flex-col">
      {(connecting || error) && (
        <div className={cn(
          "shrink-0 px-4 py-1.5 text-xs flex items-center gap-2 border-b",
          error ? "bg-red-400/10 border-red-400/20 text-red-400" : "bg-primary/5 border-primary/20 text-primary"
        )}>
          {connecting ? <Loader2 size={12} className="animate-spin" /> : <AlertTriangle size={12} />}
          {connecting ? 'Connecting to backend…' : error}
          {!connecting && (
            <button onClick={() => setSettingsOpen(true)} className="underline ml-auto">Settings</button>
          )}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
      {/* Left Sidebar */}
      <aside
        className={cn(
          "flex-shrink-0 flex flex-col border-r border-glass-border glass-panel transition-all duration-300 ease-in-out",
          collapsed ? "w-[60px]" : "w-[240px]"
        )}
      >
        {/* Header */}
        <div className={cn(
          "h-14 flex items-center border-b border-glass-border shrink-0 transition-all duration-300",
          collapsed ? "justify-center px-0" : "gap-3 px-4"
        )}>
          <div className="w-8 h-8 rounded-md bg-primary/20 flex items-center justify-center text-primary border border-primary/30 shrink-0">
            <Zap size={18} />
          </div>
          {!collapsed && (
            <span className="font-semibold text-[15px] whitespace-nowrap overflow-hidden flex items-center gap-2">
              CareerOps AI
              {connected && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" title="Connected" />}
            </span>
          )}
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {collapsed ? (
            /* Collapsed: icons centered vertically */
            <div className="flex-1 flex flex-col items-center justify-center gap-1">
              <IconButton icon={MessageSquare} active={view === 'chat'} onClick={() => setView('chat')} title="Chat" />
              <IconButton icon={Library} active={view === 'library'} onClick={() => setView('library')} title="Knowledge Base" />
              <IconButton icon={BarChart3} active={view === 'evals'} onClick={() => setView('evals')} title="Evaluations" />
            </div>
          ) : view === 'chat' ? (
            <>
              <div className="p-3">
                <button
                  onClick={handleNewChat}
                  disabled={!connected}
                  className="w-full glass-panel-elevated py-2.5 px-3 rounded-lg flex items-center justify-center gap-2 hover:bg-black/5 transition-colors text-primary font-medium disabled:opacity-50"
                >
                  <Plus size={16} />
                  <span>New chat</span>
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-1">
                <div className="text-xs font-semibold text-text-muted mb-2 px-2 uppercase tracking-wider">Sessions</div>
                {sessions.length === 0 ? (
                  <div className="text-xs text-text-muted px-2 italic">No sessions yet</div>
                ) : (
                  sessions.map(s => (
                    <div
                      key={s.id}
                      className={cn(
                        "group flex items-center gap-0.5 rounded-md transition-colors",
                        activeSessionId === s.id
                          ? "bg-primary/10 border border-primary/20"
                          : "hover:bg-glass-bg border border-transparent",
                      )}
                    >
                      <button
                        onClick={() => setActiveSessionId(s.id)}
                        className={cn(
                          "flex-1 min-w-0 text-left px-3 py-2 truncate transition-colors",
                          activeSessionId === s.id ? "text-primary" : "text-text-muted",
                        )}
                      >
                        {s.title}
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteSession(s.id).catch(() => {});
                        }}
                        title="Delete chat"
                        className="shrink-0 p-1.5 mr-1 rounded-md text-text-muted opacity-40 group-hover:opacity-100 hover:text-red-400 hover:bg-red-400/10 transition-all"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-2 text-text-muted p-6">
              <Database size={28} className="opacity-30" />
              <span className="text-xs text-center leading-relaxed opacity-60">Manage your indexed documents from the panel on the right.</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className={cn(
          "p-3 border-t border-glass-border flex items-center shrink-0",
          collapsed ? "flex-col gap-1 justify-center" : "justify-between"
        )}>
          {!collapsed && (
            <>
              <IconButton icon={MessageSquare} active={view === 'chat'} onClick={() => setView('chat')} title="Chat" />
              <IconButton icon={Library} active={view === 'library'} onClick={() => setView('library')} title="Knowledge Base" />
              <IconButton icon={BarChart3} active={view === 'evals'} onClick={() => setView('evals')} title="Evaluations" />
              <IconButton icon={Settings} title="Settings" onClick={() => setSettingsOpen(true)} />
            </>
          )}
          {collapsed && <IconButton icon={Settings} title="Settings" onClick={() => setSettingsOpen(true)} />}
          <IconButton
            icon={collapsed ? ChevronRight : ChevronRight}
            onClick={() => setCollapsed(v => !v)}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className={cn("transition-transform duration-300", !collapsed && "rotate-180")}
          />
        </div>
      </aside>

      {view === 'chat' ? <ChatPage /> : view === 'library' ? <LibraryPage /> : <EvalDashboard />}
      </div>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
