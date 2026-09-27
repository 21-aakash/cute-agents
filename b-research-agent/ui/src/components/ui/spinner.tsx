import { cn } from '@/lib/cn';

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'inline-block size-3.5 rounded-full border-2 border-current border-t-transparent animate-spin',
        className,
      )}
      aria-hidden
    />
  );
}
