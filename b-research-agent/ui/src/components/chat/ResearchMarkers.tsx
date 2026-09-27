import { useEffect, useState } from 'react';
import {
  Brain,
  CheckCircle2,
  ChevronRight,
  FileText,
  GitBranch,
  Globe,
  PenLine,
  RotateCcw,
  Search,
} from 'lucide-react';
import { Marker, MarkerContent, MarkerIcon } from '@/components/ui/marker';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/cn';
import type { RunMarker } from '@/types';

function MarkerRow({ marker }: { marker: RunMarker }) {
  if (marker.variant === 'separator') {
    return (
      <Marker variant="separator">
        <MarkerContent className="text-xs text-text-muted whitespace-nowrap px-1">
          {marker.label}
        </MarkerContent>
      </Marker>
    );
  }

  const icon = (() => {
    if (marker.active) return <Spinner />;
    switch (marker.kind) {
      case 'plan':
        return <GitBranch />;
      case 'research':
        return <Search />;
      case 'write':
        return <PenLine />;
      case 'critique':
        return <CheckCircle2 className="text-success" />;
      case 'tool':
        return marker.label.startsWith('web_search') ? <Globe /> : <Search />;
      case 'sources':
        return <FileText />;
      case 'revise':
        return <RotateCcw />;
      case 'thinking':
        return <Spinner />;
      default:
        return <Brain />;
    }
  })();

  return (
    <Marker role={marker.active ? 'status' : undefined}>
      <MarkerIcon>{icon}</MarkerIcon>
      <MarkerContent className={marker.active ? 'shimmer' : undefined}>
        {marker.label}
      </MarkerContent>
    </Marker>
  );
}

export function ResearchMarkers({ markers }: { markers: RunMarker[] }) {
  if (markers.length === 0) return null;

  return (
    <div className="w-full rounded-xl px-1 py-1 space-y-2">
      {markers.map((m) => (
        <MarkerRow key={m.id} marker={m} />
      ))}
    </div>
  );
}

/** Collapsed by default; expands while live pipeline is running. */
export function CollapsiblePipeline({
  markers,
  live = false,
}: {
  markers: RunMarker[];
  live?: boolean;
}) {
  const [open, setOpen] = useState(live);
  const hasActive = markers.some((m) => m.active);

  useEffect(() => {
    if (live) setOpen(true);
  }, [live]);

  useEffect(() => {
    if (!live && !hasActive) setOpen(false);
  }, [live, hasActive]);

  if (markers.length === 0) return null;

  const doneCount = markers.filter((m) => !m.active && m.variant !== 'separator').length;

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex items-center gap-2 text-xs font-medium text-text-muted',
          'hover:text-text-body transition-colors rounded-lg px-1 py-1 -ml-1',
        )}
      >
        <ChevronRight
          size={14}
          className={cn('transition-transform duration-200', open && 'rotate-90')}
        />
        <span>
          {live && hasActive ? 'Research in progress…' : `Research steps (${doneCount || markers.length})`}
        </span>
        {live && hasActive && <Spinner />}
      </button>
      {open && (
        <div className="mt-1 pl-1 border-l border-glass-border ml-1.5">
          <ResearchMarkers markers={markers} />
        </div>
      )}
    </div>
  );
}

export function isResearchResponse(res: {
  status: string;
  intent?: string | null;
  plan?: { intent: string };
  critique?: unknown;
  evidence?: unknown[];
  tool_calls?: unknown[];
}): boolean {
  if (res.status === 'needs_clarification') return false;
  const intent = res.intent ?? res.plan?.intent;
  if (intent === 'chitchat' || intent === 'clarify') return false;
  return Boolean(
    res.critique ||
    (res.evidence?.length ?? 0) > 0 ||
    (res.tool_calls?.length ?? 0) > 0,
  );
}

export function thinkingMarker(label = 'Thinking…'): RunMarker[] {
  return [{ id: 'thinking', kind: 'thinking', label, active: true }];
}

export function mergeStreamMarker(prev: RunMarker[], incoming: RunMarker): RunMarker[] {
  const withoutActive = prev.filter((m) => !m.active && !m.id.startsWith('active-'));
  const byId = new Map(withoutActive.map((m) => [m.id, m]));
  byId.set(incoming.id, incoming);
  return Array.from(byId.values());
}

export function markersFromResponse(res: {
  status?: string;
  intent?: string | null;
  plan?: { intent: string; sub_queries: string[] };
  tool_calls?: { tool: string; query: string; hit_count?: number }[];
  evidence?: unknown[];
  critique?: { passed: boolean };
  revisions?: number;
}): RunMarker[] {
  if (!isResearchResponse(res)) return [];

  const out: RunMarker[] = [];

  if (res.plan) {
    out.push({
      id: 'plan-done',
      kind: 'plan',
      label: `Planned · ${res.plan.intent} · ${res.plan.sub_queries.length} sub-queries`,
      active: false,
    });
  }

  for (const [i, tc] of (res.tool_calls ?? []).entries()) {
    const hits = tc.hit_count != null ? ` · ${tc.hit_count} hits` : '';
    out.push({
      id: `tool-${i}`,
      kind: 'tool',
      label: `${tc.tool}: ${tc.query}${hits}`,
      active: false,
    });
  }

  if ((res.evidence?.length ?? 0) > 0) {
    out.push({
      id: 'sources',
      kind: 'sources',
      label: `Retrieved ${res.evidence!.length} source${res.evidence!.length === 1 ? '' : 's'}`,
      active: false,
    });
  }

  out.push({
    id: 'write-done',
    kind: 'write',
    label: 'Answer drafted',
    active: false,
  });

  if (res.critique) {
    out.push({
      id: 'critique-done',
      kind: 'critique',
      label: res.critique.passed ? 'Review complete' : 'Review · revision needed',
      active: false,
    });
  }

  if ((res.revisions ?? 0) > 0) {
    out.push({
      id: 'rev-sep',
      kind: 'revise',
      label: `${res.revisions} revision${res.revisions === 1 ? '' : 's'}`,
      active: false,
      variant: 'separator',
    });
  }

  return out;
}
