import React from 'react';
import { cn } from '@/lib/cn';

type MarkerVariant = 'default' | 'separator';

interface MarkerProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: MarkerVariant;
}

export function Marker({ variant = 'default', className, children, ...props }: MarkerProps) {
  if (variant === 'separator') {
    return (
      <div
        className={cn('flex items-center gap-3 py-1', className)}
        {...props}
      >
        <div className="h-px flex-1 bg-glass-border" />
        {children}
        <div className="h-px flex-1 bg-glass-border" />
      </div>
    );
  }

  return (
    <div
      className={cn('flex items-center gap-2.5 text-sm text-text-muted', className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function MarkerIcon({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        'flex size-7 shrink-0 items-center justify-center rounded-lg border border-glass-border bg-glass-bg text-primary [&>svg]:size-3.5',
        className,
      )}
    >
      {children}
    </span>
  );
}

export function MarkerContent({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <span className={cn('text-[13px] leading-snug text-text-body/80', className)}>
      {children}
    </span>
  );
}
