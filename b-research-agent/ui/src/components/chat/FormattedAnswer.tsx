import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { extractFitScoreInfo, FitScoreGauge } from './FitScoreCard';

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|\[[0-9]+\])/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-semibold text-text-body">{part.slice(2, -2)}</strong>;
    }
    if (/^\[[0-9]+\]$/.test(part)) {
      return (
        <sup key={i} className="text-[10px] text-primary ml-0.5">
          {part}
        </sup>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function FormattedAnswer({ text }: { text: string }) {
  const fitInfo = extractFitScoreInfo(text);
  const lines = text.split('\n');
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (listItems.length === 0) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="my-2 space-y-1.5 list-disc pl-5 text-text-body">
        {listItems.map((item, i) => (
          <li key={i} className="leading-relaxed">{renderInline(item)}</li>
        ))}
      </ul>,
    );
    listItems = [];
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushList();
      continue;
    }
    if (line.startsWith('# ')) {
      flushList();
      blocks.push(
        <h2 key={`h2-${blocks.length}`} className="font-bold text-lg text-text-body mt-4 mb-2 first:mt-0">
          {line.slice(2)}
        </h2>,
      );
      continue;
    }
    if (line.startsWith('## ')) {
      flushList();
      blocks.push(
        <h3 key={`h-${blocks.length}`} className="font-semibold text-text-body mt-4 mb-2 first:mt-0 text-[15px]">
          {line.slice(3)}
        </h3>,
      );
      continue;
    }
    if (line.startsWith('### ')) {
      flushList();
      blocks.push(
        <h4 key={`h4-${blocks.length}`} className="font-medium text-text-body mt-3 mb-1.5 text-sm">
          {line.slice(4)}
        </h4>,
      );
      continue;
    }
    if (line.startsWith('- ') || line.startsWith('* ')) {
      listItems.push(line.slice(2));
      continue;
    }
    if (/^[0-9]+\.\s/.test(line)) {
      flushList();
      blocks.push(
        <div key={`num-${blocks.length}`} className="my-1.5 pl-2 border-l-2 border-primary/30 text-text-body text-sm leading-relaxed">
          {renderInline(line)}
        </div>
      );
      continue;
    }
    flushList();
    blocks.push(
      <p key={`p-${blocks.length}`} className="my-2 leading-relaxed text-text-body">
        {renderInline(line)}
      </p>,
    );
  }
  flushList();

  return (
    <div className="formatted-answer">
      {fitInfo.hasScore && (
        <FitScoreGauge
          score={fitInfo.score}
          verdict={fitInfo.verdict}
          seniority={fitInfo.seniority}
        />
      )}
      {blocks}
    </div>
  );
}

export function isLikelyMarkdown(text: string): boolean {
  return /^#{1,3}\s/m.test(text) || /^[-*]\s/m.test(text) || /[0-9]{1,3}\/100/.test(text);
}

export function PlainOrFormatted({ text }: { text: string }) {
  if (!text) return null;
  if (isLikelyMarkdown(text)) {
    return <FormattedAnswer text={text} />;
  }
  return <div className="whitespace-pre-wrap leading-relaxed text-text-body">{text}</div>;
}
