import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle, BarChart3, CheckCircle2, Loader2, Play, RefreshCw,
} from 'lucide-react';
import * as api from '@/api/client';
import { useWorkspace } from '@/context/WorkspaceContext';
import type { EvalRunDetail, EvalRunSummary } from '@/types';
import {
  AGENT_METRICS,
  MetricCard,
  RAG_METRICS,
  SampleScorePills,
} from '@/components/evals/EvalMetrics';

export default function EvalDashboard() {
  const { config, connected } = useWorkspace();
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [selected, setSelected] = useState<EvalRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [mode, setMode] = useState<'golden' | 'recent'>('golden');
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    if (!connected) return;
    setLoading(true);
    setError(null);
    try {
      const list = await api.listEvalRuns(config);
      setRuns(list);
      if (list.length > 0) {
        setSelected(await api.getEvalRun(config, list[0].id));
      } else {
        setSelected(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [config, connected]);

  useEffect(() => { loadRuns(); }, [loadRuns]);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const detail = await api.runEval(config, mode);
      setSelected(detail);
      setRuns(await api.listEvalRuns(config));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const metrics = selected?.metrics_avg ?? {};

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="w-[320px] flex-shrink-0 border-r border-glass-border p-5 overflow-y-auto space-y-4">
        <div>
          <h1 className="font-semibold text-[17px] mb-0.5 flex items-center gap-2">
            <BarChart3 size={18} className="text-primary" />
            Evaluations
          </h1>
          <p className="text-xs text-text-muted leading-relaxed">
            RAGAS quality + agent health metrics on one dashboard.
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-medium text-text-muted">Eval mode</label>
          <div className="grid grid-cols-2 gap-2">
            {(['golden', 'recent'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`py-2 px-3 rounded-lg text-xs font-medium border transition-colors ${
                  mode === m
                    ? 'bg-primary/15 border-primary/30 text-primary'
                    : 'border-glass-border text-text-muted hover:bg-glass-bg'
                }`}
              >
                {m === 'golden' ? 'Golden set' : 'Recent chats'}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleRun}
          disabled={!connected || running}
          className="w-full py-2.5 rounded-lg bg-primary/20 border border-primary/30 text-primary font-semibold text-sm hover:bg-primary hover:text-white transition-all disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {running ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {running ? 'Running eval…' : 'Run evaluation'}
        </button>

        <button onClick={loadRuns} disabled={loading} className="w-full py-2 rounded-lg border border-glass-border text-text-muted text-xs hover:bg-glass-bg flex items-center justify-center gap-1.5">
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          Refresh history
        </button>

        {error && (
          <div className="text-xs text-red-400 flex items-start gap-1.5">
            <AlertTriangle size={12} className="mt-0.5 shrink-0" /> {error}
          </div>
        )}

        <div className="space-y-1">
          <div className="text-xs font-semibold text-text-muted uppercase tracking-wider px-1">History</div>
          {runs.length === 0 ? (
            <div className="text-xs text-text-muted px-1 italic">No eval runs yet.</div>
          ) : (
            runs.map((run) => (
              <button
                key={run.id}
                onClick={() => api.getEvalRun(config, run.id).then(setSelected).catch((e) => setError(String(e)))}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs border transition-colors ${
                  selected?.id === run.id ? 'bg-primary/10 border-primary/20 text-primary' : 'border-transparent hover:bg-glass-bg text-text-muted'
                }`}
              >
                <div className="font-medium capitalize">{run.mode} · {run.sample_count} samples</div>
                <div className="text-[10px] opacity-70 mt-0.5">
                  {run.created_at ? new Date(run.created_at).toLocaleString() : '—'}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {!selected ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-text-muted">
            <BarChart3 size={36} className="opacity-30" />
            <p className="text-sm">Run an evaluation to see scores.</p>
          </div>
        ) : (
          <div className="max-w-4xl space-y-6">
            <div className="flex items-center gap-2">
              {selected.status === 'completed' ? (
                <CheckCircle2 size={18} className="text-success" />
              ) : (
                <AlertTriangle size={18} className="text-red-400" />
              )}
              <h2 className="font-semibold text-[15px] capitalize">
                {selected.mode} eval · {selected.sample_count} samples
              </h2>
              {selected.duration_ms != null && (
                <span className="text-xs text-text-muted ml-auto">{(selected.duration_ms / 1000).toFixed(1)}s</span>
              )}
            </div>

            <div>
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Agent health</h3>
              <div className="grid grid-cols-3 gap-3">
                {AGENT_METRICS.map(({ key, label, hint }) => (
                  <MetricCard key={key} label={label} value={metrics[key]} hint={hint} />
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">RAG quality (RAGAS)</h3>
              <div className="grid grid-cols-3 gap-3">
                {RAG_METRICS.map(({ key, label, hint }) => (
                  <MetricCard key={key} label={label} value={metrics[key]} hint={hint} />
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-text-body">Samples</h3>
              {selected.samples.map((sample) => (
                <div key={sample.id} className="glass-panel-elevated rounded-xl p-4 space-y-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Question</div>
                    <div className="text-sm text-text-body">{sample.question}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Answer</div>
                    <div className="text-sm text-text-body whitespace-pre-wrap">{sample.answer || '—'}</div>
                  </div>
                  <SampleScorePills scores={sample.scores} />
                  <div className="text-[11px] text-text-muted">{sample.contexts.length} context chunks</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
