'use client';

import { formatCurrency } from '@/lib/utils';

interface RangeBarProps {
  low: number | null | undefined;
  high: number | null | undefined;
  current: number | null | undefined;
}

export default function RangeBar({ low, high, current }: RangeBarProps) {
  const hasRange = low != null && high != null && high > low;
  const position =
    hasRange && current != null ? Math.min(100, Math.max(0, ((current - low) / (high - low)) * 100)) : null;

  if (!hasRange) {
    return <span className="text-sm text-[var(--text-tertiary)]">N/A</span>;
  }

  return (
    <div className="min-w-[108px]">
      <div className="relative h-1.5 rounded-full bg-[linear-gradient(90deg,var(--dn),var(--forest),var(--up))]">
        {position != null ? (
          <span
            aria-hidden="true"
            className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--bg-surface-1)] bg-[var(--ink)] shadow-[var(--shadow-1)]"
            style={{ left: `${position}%` }}
          />
        ) : null}
      </div>
      <div className="mt-1.5 flex justify-between text-[10px] tabular-nums text-[var(--text-tertiary)]">
        <span>{formatCurrency(low)}</span>
        <span>{formatCurrency(high)}</span>
      </div>
    </div>
  );
}
