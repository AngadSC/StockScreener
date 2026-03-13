'use client';

import { useEffect, useRef, useState } from 'react';
import { HelpCircle, X } from 'lucide-react';

import { cn } from '@/lib/utils';

interface HelpPopoverProps {
  title: string;
  description: string;
  suggestion?: string;
  className?: string;
}

export default function HelpPopover({
  title,
  description,
  suggestion,
  className,
}: HelpPopoverProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleClick = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div ref={ref} className={cn('relative inline-flex', className)}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-primary/30 bg-primary/10 text-primary transition-colors hover:bg-primary/20"
        aria-label={`Help for ${title}`}
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </button>
      {open ? (
        <div className="deco-panel absolute right-0 top-[calc(100%+0.75rem)] z-40 w-72 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="deco-kicker">Field Guide</div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-muted-foreground transition-colors hover:text-primary"
              aria-label="Close help"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-2 font-display text-base uppercase tracking-[0.14em] text-foreground">
            {title}
          </div>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{description}</p>
          {suggestion ? (
            <div className="mt-4 border border-primary/20 bg-primary/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-primary">
              Suggested: {suggestion}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
