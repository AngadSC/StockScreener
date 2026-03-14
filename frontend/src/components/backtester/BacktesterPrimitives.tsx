'use client';

import type { CSSProperties, ReactNode } from 'react';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';

import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import type { StrategyDef } from '@/components/backtester/config';

export const headingLgStyle: CSSProperties = { font: 'var(--heading-lg)' };
export const headingMdStyle: CSSProperties = { font: 'var(--heading-md)' };
export const headingSmStyle: CSSProperties = { font: 'var(--heading-sm)' };
export const captionStyle: CSSProperties = { font: 'var(--caption)' };

export function FieldShell({
  label,
  helper,
  children,
}: {
  label: string;
  helper?: string;
  children: ReactNode;
}) {
  return (
    <label className="space-y-2">
      <div className="text-sm font-medium text-[var(--text-primary)]">{label}</div>
      {children}
      {helper ? (
        <p className="text-[11px] leading-5 text-[var(--text-tertiary)]" style={captionStyle}>
          {helper}
        </p>
      ) : null}
    </label>
  );
}

export function AffixInput({
  value,
  onChange,
  type = 'number',
  step,
  placeholder,
  prefix,
  suffix,
  min,
}: {
  value: string | number;
  onChange: (value: string) => void;
  type?: React.ComponentProps<typeof Input>['type'];
  step?: number | string;
  placeholder?: string;
  prefix?: string;
  suffix?: string;
  min?: number | string;
}) {
  return (
    <div className="relative">
      {prefix ? (
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--text-secondary)]">
          {prefix}
        </span>
      ) : null}
      <Input
        type={type}
        value={value}
        step={step}
        min={min}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className={cn(prefix && 'pl-8', suffix && 'pr-12')}
      />
      {suffix ? (
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-[var(--text-secondary)]">
          {suffix}
        </span>
      ) : null}
    </div>
  );
}

export function ToggleSwitch({
  checked,
  onCheckedChange,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full border transition-all duration-[180ms]',
        checked
          ? 'border-[var(--accent)] bg-[var(--accent)] shadow-[0_0_0_3px_var(--accent-subtle)]'
          : 'border-[var(--border-default)] bg-[var(--bg-surface-2)]',
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 rounded-full bg-white transition-transform duration-[180ms]',
          checked ? 'translate-x-6' : 'translate-x-1',
        )}
      />
    </button>
  );
}

export function StrategyInfoDrawer({ strategy }: { strategy: StrategyDef }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] p-4 transition-all duration-[250ms]">
      <div className="text-xs uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Strategy Snapshot</div>
      <div className="mt-2" style={headingSmStyle}>
        {strategy.label}
      </div>
      <p className="mt-2 text-sm text-[var(--text-secondary)]">{strategy.description}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Best For</div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{strategy.bestFor}</p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Watch For</div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{strategy.watchFor}</p>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--text-tertiary)]">Starter Values</div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{strategy.starterValues}</p>
        </div>
      </div>
    </div>
  );
}

export function EmptyResultsState() {
  return (
    <div className="flex min-h-[720px] items-center justify-center px-6 py-10">
      <div className="max-w-md text-center">
        <svg viewBox="0 0 280 160" className="mx-auto h-40 w-full max-w-[280px]" aria-hidden="true">
          <defs>
            <linearGradient id="backtester-empty-gradient" x1="0%" x2="100%" y1="0%" y2="0%">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.12" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.38" />
            </linearGradient>
          </defs>
          <rect x="20" y="20" width="240" height="120" rx="18" fill="var(--bg-surface-2)" stroke="var(--border-default)" />
          <path d="M44 110 C78 98, 90 116, 118 88 S170 42, 236 66" fill="none" stroke="url(#backtester-empty-gradient)" strokeWidth="4" strokeLinecap="round" />
          <path d="M44 112 C78 100, 90 118, 118 90 S170 44, 236 68 L236 124 L44 124 Z" fill="var(--accent)" fillOpacity="0.08" />
          <circle cx="118" cy="88" r="5" fill="var(--accent)" fillOpacity="0.7" />
          <circle cx="178" cy="52" r="5" fill="var(--accent)" fillOpacity="0.7" />
        </svg>
        <div className="mt-6" style={headingMdStyle}>
          Configure and run your backtest
        </div>
        <p className="mt-2 text-sm text-[var(--text-tertiary)]">Results, equity curve, and trade log will appear here.</p>
      </div>
    </div>
  );
}

export function SortIndicator({ active, order }: { active: boolean; order: 'asc' | 'desc' }) {
  return (
    <span className="flex flex-col leading-none">
      <ChevronUp className={cn('h-3 w-3', active && order === 'asc' ? 'text-[var(--accent)]' : 'text-[var(--text-tertiary)]')} />
      <ChevronDown className={cn('-mt-1 h-3 w-3', active && order === 'desc' ? 'text-[var(--accent)]' : 'text-[var(--text-tertiary)]')} />
    </span>
  );
}

export function MetricCard({
  label,
  value,
  tone,
  delay,
}: {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'default';
  delay: number;
}) {
  return (
    <div className="metric-card-enter rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] p-4" style={{ animationDelay: `${delay}ms` }}>
      <div className="text-[11px] uppercase tracking-[0.14em] text-[var(--text-tertiary)]">{label}</div>
      <div
        className={cn(
          'mt-2 tabular-nums',
          tone === 'positive' && 'text-[var(--positive)]',
          tone === 'negative' && 'text-[var(--negative)]',
          tone === 'default' && 'text-[var(--text-primary)]',
        )}
        style={headingMdStyle}
      >
        {value}
      </div>
    </div>
  );
}

export function StepMarker({
  index,
  label,
  active,
  completed,
  onClick,
}: {
  index: number;
  label: string;
  active: boolean;
  completed: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" onClick={onClick} className="flex min-w-0 items-center gap-2 text-left">
      <span
        className={cn(
          'flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold transition-colors duration-[180ms]',
          active && 'border-[var(--accent)] bg-[var(--accent)] text-white',
          completed && 'border-[var(--positive)] bg-[var(--positive-bg)] text-[var(--positive)]',
          !active && !completed && 'border-[var(--border-default)] text-[var(--text-tertiary)]',
        )}
      >
        {completed ? <Check className="h-3.5 w-3.5" /> : index + 1}
      </span>
      <span
        className={cn(
          'min-w-0 truncate text-sm',
          active && 'text-[var(--text-primary)]',
          completed && 'text-[var(--text-secondary)]',
          !active && !completed && 'text-[var(--text-tertiary)]',
        )}
      >
        {label}
      </span>
    </button>
  );
}
