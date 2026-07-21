'use client';

import { cn } from '@/lib/utils';
import type { InsiderActivityFilters, InsiderActivityType } from '@/types/insiders';

interface InsiderControlsProps {
  filters: InsiderActivityFilters;
  onChange: (filters: InsiderActivityFilters) => void;
  isFetching?: boolean;
}

const TYPE_OPTIONS: { value: InsiderActivityType; label: string }[] = [
  { value: 'buys', label: 'Insider buying' },
  { value: 'sells', label: 'Insider selling' },
  { value: 'all', label: 'All activity' },
];

const MIN_VALUE_OPTIONS: { value: number; label: string }[] = [
  { value: 10000, label: '$10K+' },
  { value: 50000, label: '$50K+' },
  { value: 100000, label: '$100K+' },
  { value: 250000, label: '$250K+' },
  { value: 1000000, label: '$1M+' },
];

const DAYS_OPTIONS: { value: number; label: string }[] = [
  { value: 7, label: '7D' },
  { value: 14, label: '14D' },
  { value: 30, label: '30D' },
  { value: 90, label: '90D' },
];

function ChipGroup<T extends string | number>({
  label,
  options,
  selected,
  onSelect,
}: {
  label: string;
  options: { value: T; label: string }[];
  selected: T;
  onSelect: (value: T) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
        {label}
      </span>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={String(option.value)}
            type="button"
            onClick={() => onSelect(option.value)}
            className={cn(
              'chip transition-[background,border-color,color]',
              option.value === selected
                ? 'border-[var(--ink)] bg-[var(--ink)] text-[var(--ivory)]'
                : 'hover:border-[var(--forest-line)] hover:text-[var(--ink)]'
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function InsiderControls({
  filters,
  onChange,
  isFetching,
}: InsiderControlsProps) {
  return (
    <div className="flex flex-col gap-5">
      <ChipGroup
        label="View"
        options={TYPE_OPTIONS}
        selected={filters.type}
        onSelect={(type) => onChange({ ...filters, type })}
      />
      <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_auto]">
        <ChipGroup
          label="Minimum value"
          options={MIN_VALUE_OPTIONS}
          selected={filters.min_value}
          onSelect={(min_value) => onChange({ ...filters, min_value })}
        />
        <ChipGroup
          label="Window"
          options={DAYS_OPTIONS}
          selected={filters.days}
          onSelect={(days) => onChange({ ...filters, days })}
        />
      </div>
      {isFetching ? (
        <span className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
          Updating…
        </span>
      ) : null}
    </div>
  );
}
