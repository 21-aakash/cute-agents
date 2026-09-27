import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${Math.round(value * 100)}%`;
}

export function scoreColor(value: number | null | undefined): string {
  if (value == null) return 'text-text-muted';
  if (value >= 0.8) return 'text-success';
  if (value >= 0.6) return 'text-primary';
  return 'text-red-400';
}

export function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: number | null | undefined;
  hint: string;
}) {
  return (
    <div className="glass-panel rounded-xl p-4">
      <div className="text-xs font-medium text-text-muted uppercase tracking-wider mb-1">{label}</div>
      <div className={cn('text-[28px] font-bold tabular-nums', scoreColor(value))}>{pct(value)}</div>
      <div className="text-[11px] text-text-muted mt-1 leading-relaxed">{hint}</div>
    </div>
  );
}

export const RAG_METRICS = [
  { key: 'faithfulness', label: 'Faithfulness', hint: 'Answer supported by retrieved context (RAGAS)' },
  { key: 'answer_relevancy', label: 'Answer relevancy', hint: 'Answer addresses the question (RAGAS)' },
  { key: 'context_precision', label: 'Context precision', hint: 'Retrieved chunks match ground truth (RAGAS)' },
] as const;

export const AGENT_METRICS = [
  { key: 'completion_rate', label: 'Completion rate', hint: 'Runs that produced a non-empty answer' },
  { key: 'grounded_rate', label: 'Grounded rate', hint: 'Critic marked answer as grounded in evidence' },
  { key: 'tool_invocation_rate', label: 'Tool call rate', hint: 'Runs that invoked doc/web/memory search' },
  { key: 'tool_error_rate', label: 'Tool error rate', hint: 'Failed or empty tool calls / total calls' },
  { key: 'retrieval_hit_rate', label: 'Retrieval hit rate', hint: 'doc_search returned at least one chunk' },
  { key: 'evidence_rate', label: 'Evidence rate', hint: 'Runs with any retrieved evidence' },
] as const;

export function SampleScorePills({ scores }: { scores: Record<string, number | null | undefined> }) {
  const keys = [...RAG_METRICS, ...AGENT_METRICS];
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      {keys.map(({ key, label }) => (
        scores[key] != null ? (
          <span key={key} className={cn('font-semibold tabular-nums px-2 py-0.5 rounded-md bg-glass-bg', scoreColor(scores[key]))}>
            {label} {pct(scores[key])}
          </span>
        ) : null
      ))}
    </div>
  );
}
