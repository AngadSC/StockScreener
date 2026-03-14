'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { HelpCircle, X } from 'lucide-react';

import { cn } from '@/lib/utils';

interface HelpPopoverProps {
  title: string;
  description: string;
  suggestion?: string;
  className?: string;
}

const POPOVER_GAP = 12;
const VIEWPORT_GUTTER = 12;

export default function HelpPopover({
  title,
  description,
  suggestion,
  className,
}: HelpPopoverProps) {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  const popoverId = useId();
  const wrapperRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const trigger = buttonRef.current;
    const popover = popoverRef.current;
    if (!trigger || !popover) return;

    const triggerRect = trigger.getBoundingClientRect();
    const popoverWidth = popover.offsetWidth;
    const popoverHeight = popover.offsetHeight;
    const maxLeft = Math.max(VIEWPORT_GUTTER, window.innerWidth - popoverWidth - VIEWPORT_GUTTER);
    const preferredTop = triggerRect.bottom + POPOVER_GAP;
    const fitsBelow = preferredTop + popoverHeight + VIEWPORT_GUTTER <= window.innerHeight;

    setPosition({
      left: Math.min(Math.max(triggerRect.left, VIEWPORT_GUTTER), maxLeft),
      top: fitsBelow
        ? preferredTop
        : Math.max(VIEWPORT_GUTTER, triggerRect.top - popoverHeight - POPOVER_GAP),
    });
  }, [open]);

  useEffect(() => {
    if (!open) {
      setPosition(null);
      return;
    }

    const handleClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        wrapperRef.current?.contains(target) ||
        popoverRef.current?.contains(target)
      ) {
        return;
      }

      setOpen(false);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    const handleViewportChange = () => {
      setOpen(false);
    };

    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('scroll', handleViewportChange, true);

    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleViewportChange);
      window.removeEventListener('scroll', handleViewportChange, true);
    };
  }, [open]);

  return (
    <div ref={wrapperRef} className={cn('relative inline-flex', className)}>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-primary/30 bg-[var(--accent-subtle)] text-primary transition-[background,border-color,box-shadow,color,transform] duration-[180ms] hover:bg-[var(--accent-subtle-hover)]"
        aria-label={`Help for ${title}`}
        aria-controls={open ? popoverId : undefined}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </button>
      {open && typeof document !== 'undefined'
        ? createPortal(
            <div
              ref={popoverRef}
              id={popoverId}
              role="dialog"
              aria-label={`${title} help`}
              className="deco-panel fixed z-50 w-72 max-w-[calc(100vw-1.5rem)] p-4"
              style={
                position
                  ? {
                      left: `${position.left}px`,
                      top: `${position.top}px`,
                    }
                  : {
                      left: '0px',
                      top: '0px',
                      visibility: 'hidden',
                    }
              }
            >
              <div className="flex items-start justify-between gap-3">
                <div className="deco-kicker">Field guide</div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="text-muted-foreground transition-colors hover:text-primary"
                  aria-label="Close help"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-2 text-base font-semibold text-foreground">{title}</div>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{description}</p>
              {suggestion ? (
                <div className="mt-4 rounded-md border border-primary/20 bg-[var(--accent-subtle)] px-3 py-2 text-xs text-primary">
                  Suggested: {suggestion}
                </div>
              ) : null}
            </div>,
            document.body
          )
        : null}
    </div>
  );
}
