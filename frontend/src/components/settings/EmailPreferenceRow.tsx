'use client';

import Link from 'next/link';
import { Clock, Loader2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { EmailPreferenceToggle } from './EmailPreferenceToggle';
import type { EmailPreferenceKey } from '@/types/email';

export interface EmailPreferenceRowConfig {
  key: EmailPreferenceKey;
  title: string;
  description: string;
  /** Display badge text, e.g. "Trader+", "Elite", "Coming soon". */
  badge?: string;
  /** Minimum tier that has this feature included. Omit if available to everyone. */
  requiredTier?: 'trader' | 'elite';
}

interface EmailPreferenceRowProps {
  config: EmailPreferenceRowConfig;
  checked: boolean;
  locked: boolean;
  pending: boolean;
  saved: boolean;
  errorMessage?: string | null;
  onToggle: (next: boolean) => void;
}

const TIER_LABEL: Record<'trader' | 'elite', string> = {
  trader: 'Trader',
  elite: 'Elite',
};

export default function EmailPreferenceRow({
  config,
  checked,
  locked,
  pending,
  saved,
  errorMessage,
  onToggle,
}: EmailPreferenceRowProps) {
  const isComingSoon = config.badge === 'Coming soon';

  return (
    <div className="flex flex-col gap-4 border-b border-[var(--border-subtle)] py-5 last:border-b-0 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 flex-1 pr-0 sm:pr-6">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">{config.title}</h3>
          {config.badge ? (
            isComingSoon ? (
              <Badge variant="secondary" className="gap-1.5">
                <Clock className="h-3 w-3" aria-hidden="true" />
                {config.badge}
              </Badge>
            ) : (
              <Badge>{config.badge}</Badge>
            )
          ) : null}
        </div>
        <p className="mt-1.5 text-sm leading-6 text-[var(--text-secondary)]">
          {config.description}
        </p>
        {locked && config.requiredTier ? (
          <p className="mt-2 text-xs text-[var(--text-tertiary)]">
            Included with the {TIER_LABEL[config.requiredTier]} plan.{' '}
            <Link href="/pricing" className="deco-link">
              View pricing
            </Link>
          </p>
        ) : null}
        {errorMessage ? (
          <p className="mt-2 text-xs text-[var(--negative)]">{errorMessage}</p>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-3 sm:pt-0.5">
        <span
          className={cn(
            'text-xs font-medium text-[var(--positive)] transition-opacity duration-[200ms]',
            saved ? 'opacity-100' : 'opacity-0'
          )}
          aria-live="polite"
        >
          Saved
        </span>
        {pending ? (
          <Loader2
            className="h-3.5 w-3.5 animate-spin text-[var(--text-tertiary)]"
            aria-hidden="true"
          />
        ) : null}
        <EmailPreferenceToggle
          checked={checked}
          onChange={onToggle}
          disabled={pending}
          label={config.title}
        />
      </div>
    </div>
  );
}
