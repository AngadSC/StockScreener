'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { getAIUsage } from '@/lib/api';
import { isProTier } from '@/lib/auth';
import { cn } from '@/lib/utils';

/** Shared key so a finished generation can invalidate the meter from anywhere. */
export const AI_USAGE_QUERY_KEY = ['ai-usage'] as const;

// Below this share of the allowance remaining, the meter warns rather than
// just informs — the point is to be told before the workflow stops, not after.
const LOW_REMAINING_RATIO = 0.1;

interface AIUsageMeterProps {
  userTier: string;
  className?: string;
}

function formatResetDate(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return 'next month';
  return parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function AIUsageMeter({ userTier, className }: AIUsageMeterProps) {
  const enabled = isProTier(userTier);
  const { data, isLoading, isError } = useQuery({
    queryKey: AI_USAGE_QUERY_KEY,
    queryFn: getAIUsage,
    enabled,
    staleTime: 30_000,
  });

  // Free/signed-out users have no allowance to report on, and a failed fetch
  // must stay silent: a meter that guesses is worse than no meter.
  if (!enabled || isError) return null;

  if (isLoading || !data) {
    return (
      <div
        className={cn('h-[52px] w-full animate-pulse rounded-2xl bg-[var(--bg-surface-2)]', className)}
        aria-hidden="true"
      />
    );
  }

  const { used, limit, remaining, resets_at: resetsAt } = data;
  if (limit <= 0) return null;

  const pctUsed = Math.min(100, Math.round((used / limit) * 100));
  const exhausted = remaining <= 0;
  const low = !exhausted && remaining <= Math.max(1, Math.round(limit * LOW_REMAINING_RATIO));
  const barColor = exhausted
    ? 'var(--negative)'
    : low
      ? 'var(--amber)'
      : 'var(--accent)';

  return (
    <div
      className={cn(
        'rounded-2xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3',
        className
      )}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <div className="text-sm text-[var(--text-secondary)]">
          <span className="font-semibold text-[var(--text-primary)]">
            {remaining.toLocaleString()}
          </span>{' '}
          of {limit.toLocaleString()} AI reports left this month
        </div>
        <div className="text-xs text-[var(--text-tertiary)]">
          Resets {formatResetDate(resetsAt)}
        </div>
      </div>

      <div
        className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-[var(--bg-surface-2)]"
        role="progressbar"
        aria-valuenow={used}
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-label={`${used} of ${limit} monthly AI reports used`}
      >
        <div
          className="h-full rounded-full transition-[width] duration-500 ease-out"
          style={{ width: `${pctUsed}%`, backgroundColor: barColor }}
        />
      </div>

      {exhausted ? (
        <p className="mt-2.5 text-xs leading-5 text-[var(--text-secondary)]">
          You&apos;ve used every report on this plan.{' '}
          <Link href="/pricing" className="font-medium text-[var(--accent)] hover:underline">
            Upgrade for a higher monthly limit
          </Link>{' '}
          or wait for the reset on {formatResetDate(resetsAt)}.
        </p>
      ) : null}

      {low ? (
        <p className="mt-2.5 text-xs leading-5 text-[var(--text-secondary)]">
          {remaining === 1 ? '1 report left' : `Only ${remaining} reports left`} before the reset on{' '}
          {formatResetDate(resetsAt)}.{' '}
          <Link href="/pricing" className="font-medium text-[var(--accent)] hover:underline">
            See higher tiers
          </Link>
        </p>
      ) : null}
    </div>
  );
}
