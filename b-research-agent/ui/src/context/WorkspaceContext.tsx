import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import * as api from '../api/client';
import { clearStoredMessages } from '../lib/chatStorage';
import type { AppConfig, SessionRecord } from '../types';

const STORAGE_KEY = 'research_assistant_config';
const SESSIONS_KEY = 'research_assistant_sessions';
const ACTIVE_SESSION_KEY = 'research_assistant_active_session';

interface WorkspaceContextValue {
  config: AppConfig;
  connected: boolean;
  connecting: boolean;
  error: string | null;
  sessions: SessionRecord[];
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  connect: () => Promise<void>;
  updateConfig: (partial: Partial<AppConfig>) => void;
  newSession: () => Promise<string>;
  renameSession: (id: string, title: string) => void;
  deleteSession: (id: string) => Promise<void>;
  registerAbortGeneration: (fn: (() => void) | null) => void;
}

const defaultConfig: AppConfig = {
  apiBase: import.meta.env.VITE_API_BASE ?? '',
  workspaceId: '',
  apiKey: '',
};

function loadConfig(): AppConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...defaultConfig, ...JSON.parse(raw) };
  } catch {
    /* ignore */
  }
  return { ...defaultConfig };
}

function loadSessions(): SessionRecord[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* ignore */
  }
  return [];
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<AppConfig>(loadConfig);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionRecord[]>(loadSessions);
  const [activeSessionId, setActiveSessionIdState] = useState<string | null>(() => {
    const saved = localStorage.getItem(ACTIVE_SESSION_KEY);
    const loaded = loadSessions();
    if (saved && loaded.some((s) => s.id === saved)) return saved;
    return loaded[0]?.id ?? null;
  });
  const abortGenerationRef = useRef<(() => void) | null>(null);

  const registerAbortGeneration = useCallback((fn: (() => void) | null) => {
    abortGenerationRef.current = fn;
  }, []);

  const setActiveSessionId = useCallback((id: string | null) => {
    setActiveSessionIdState(id);
    if (id) localStorage.setItem(ACTIVE_SESSION_KEY, id);
    else localStorage.removeItem(ACTIVE_SESSION_KEY);
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  }, [config]);

  useEffect(() => {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  }, [sessions]);

  const updateConfig = useCallback((partial: Partial<AppConfig>) => {
    setConfig((prev) => ({ ...prev, ...partial }));
    setConnected(false);
  }, []);

  const connect = useCallback(async () => {
    setConnecting(true);
    setError(null);
    try {
      let next = { ...config };
      if (!next.workspaceId || !next.apiKey) {
        const ws = await api.createWorkspace(next.apiBase, 'Research Workspace');
        next = { ...next, workspaceId: ws.id, apiKey: ws.api_key };
        setConfig(next);
      }
      const status = await api.health(next.apiBase);
      if (!status.ok) {
        throw new Error(
          `Backend unhealthy — postgres: ${status.postgres}, qdrant: ${status.qdrant}`,
        );
      }
      setConnected(true);
    } catch (e) {
      setConnected(false);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setConnecting(false);
    }
  }, [config]);

  useEffect(() => {
    connect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- initial connect only

  const newSession = useCallback(async () => {
    const id = await api.createSession(config);
    const session: SessionRecord = { id, title: 'New chat' };
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(id);
    return id;
  }, [config, setActiveSessionId]);

  const renameSession = useCallback((id: string, title: string) => {
    setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)));
  }, []);

  const deleteSession = useCallback(
    async (id: string) => {
      if (activeSessionId === id) {
        abortGenerationRef.current?.();
      }
      if (config.workspaceId) {
        clearStoredMessages(config.workspaceId, id);
      }
      if (connected && config.workspaceId && config.apiKey) {
        try {
          await api.deleteSession(config, id);
        } catch {
          /* local-only session or already gone */
        }
      }
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (activeSessionId === id) {
          const fallback = next[0]?.id ?? null;
          setActiveSessionId(fallback);
        }
        return next;
      });
    },
    [config, connected, activeSessionId, setActiveSessionId],
  );

  const value = useMemo(
    () => ({
      config,
      connected,
      connecting,
      error,
      sessions,
      activeSessionId,
      setActiveSessionId,
      connect,
      updateConfig,
      newSession,
      renameSession,
      deleteSession,
      registerAbortGeneration,
    }),
    [
      config,
      connected,
      connecting,
      error,
      sessions,
      activeSessionId,
      connect,
      updateConfig,
      newSession,
      renameSession,
      deleteSession,
      registerAbortGeneration,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error('useWorkspace must be used within WorkspaceProvider');
  return ctx;
}
