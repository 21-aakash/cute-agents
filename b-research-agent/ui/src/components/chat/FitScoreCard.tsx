import React from 'react';
import { cn } from '@/lib/cn';

interface FitScoreCardProps {
  score: number;
  verdict?: string;
  seniority?: string;
  strengths?: string[];
  gaps?: string[];
}

export function extractFitScoreInfo(text: string): {
  hasScore: boolean;
  score: number;
  verdict: string;
  seniority: string;
} {
  const scoreMatch = text.match(/(?:Match Fit Evaluation|Match Score|Fit Score)[^0-9]*([0-9]{1,3})\s*(?:\/|\s*out of\s*)100/i) || text.match(/([0-9]{1,3})\/100/);
  const verdictMatch = text.match(/\*\*Verdict:\*\*\s*([^\n\r*]+)/i);
  const seniorityMatch = text.match(/\*\*Seniority Alignment:\*\*\s*([^\n\r*]+)/i);

  if (scoreMatch) {
    const score = Math.min(100, Math.max(0, parseInt(scoreMatch[1], 10)));
    return {
      hasScore: true,
      score,
      verdict: verdictMatch ? verdictMatch[1].trim() : (score >= 80 ? 'Strong Match' : score >= 60 ? 'Moderate Match' : 'Stretch Role'),
      seniority: seniorityMatch ? seniorityMatch[1].trim() : 'Aligned',
    };
  }
  return { hasScore: false, score: 0, verdict: '', seniority: '' };
}

export function FitScoreGauge({ score, verdict, seniority }: { score: number; verdict?: string; seniority?: string }) {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const colorClass =
    score >= 80
      ? 'text-emerald-500 stroke-emerald-500'
      : score >= 60
      ? 'text-amber-500 stroke-amber-500'
      : 'text-rose-500 stroke-rose-500';

  const bgGradient =
    score >= 80
      ? 'from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-500/20'
      : score >= 60
      ? 'from-amber-500/10 via-amber-500/5 to-transparent border-amber-500/20'
      : 'from-rose-500/10 via-rose-500/5 to-transparent border-rose-500/20';

  return (
    <div className={cn('my-4 p-4 rounded-xl border bg-gradient-to-br flex flex-wrap items-center gap-5 shadow-sm', bgGradient)}>
      {/* Circular Gauge */}
      <div className="relative w-24 h-24 flex items-center justify-center shrink-0">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 96 96">
          <circle
            cx="48"
            cy="48"
            r={radius}
            className="stroke-gray-200 dark:stroke-gray-800"
            strokeWidth="8"
            fill="transparent"
          />
          <circle
            cx="48"
            cy="48"
            r={radius}
            className={cn('transition-all duration-1000 ease-out', colorClass)}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="text-2xl font-bold tracking-tight text-gray-900 dark:text-gray-100">{score}</span>
          <span className="text-[10px] font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wider">Fit Score</span>
        </div>
      </div>

      {/* Breakdown Badges */}
      <div className="flex-1 min-w-[200px] space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-700 dark:text-gray-300">Target Match</span>
          <span
            className={cn(
              'px-2.5 py-0.5 rounded-full text-xs font-medium border',
              score >= 80
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800'
                : score >= 60
                ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800'
                : 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800'
            )}
          >
            {verdict || (score >= 80 ? 'Strong Match' : 'Moderate Match')}
          </span>
        </div>

        {seniority && (
          <div className="text-xs text-gray-600 dark:text-gray-400">
            <span className="font-medium">Seniority Alignment:</span> {seniority}
          </div>
        )}

        <div className="flex items-center gap-3 pt-1 text-[11px] text-gray-700 dark:text-gray-300">
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span> 80-100 Strong
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span> 60-79 Moderate
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span> &lt;60 Gap
          </span>
        </div>
      </div>
    </div>
  );
}
