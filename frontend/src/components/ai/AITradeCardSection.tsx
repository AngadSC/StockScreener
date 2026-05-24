'use client';

import { cn } from '@/lib/utils';
import type {
  AITradeCard,
  TradeCardDecision,
  TradeCardBestAction,
  TradeCardConfidence,
  TradeLevels,
} from '@/types/ai';

// ── Constants ────────────────────────────────────────────────────────────────

const BEST_ACTION_LABELS: Record<TradeCardBestAction, string> = {
  buy_now: 'Buy Now',
  wait_for_breakout: 'Wait for Breakout',
  wait_for_pullback: 'Wait for Pullback',
  hold_if_in: 'Hold If In',
  avoid: 'Avoid',
  short_now: 'Short Now',
  wait_for_breakdown: 'Wait for Breakdown',
};

const CONFIDENCE_LABELS: Record<TradeCardConfidence, string> = {
  low: 'Low',
  moderate: 'Moderate',
  strong: 'Strong',
  very_strong: 'Very Strong',
};

// ── Decision badge styling ────────────────────────────────────────────────────

interface DecisionStyle {
  badge: string;
  dot: string;
}

function getDecisionStyle(decision: TradeCardDecision): DecisionStyle {
  switch (decision) {
    case 'Long Setup Active':
      return {
        badge:
          'border-[var(--positive)]/40 bg-[var(--positive-bg)] text-[var(--positive)] font-semibold',
        dot: 'bg-[var(--positive)]',
      };
    case 'Conditional Long':
      return {
        badge:
          'border-[var(--positive)]/25 bg-[rgba(34,197,94,0.07)] text-[var(--positive)] font-medium',
        dot: 'bg-[var(--positive)]',
      };
    case 'Bullish Watch':
      return {
        badge:
          'border-amber-400/40 bg-amber-400/10 text-amber-400 font-medium',
        dot: 'bg-amber-400',
      };
    case 'No Trade':
      return {
        badge:
          'border-[var(--border-default)] bg-[rgba(152,152,176,0.08)] text-[var(--text-secondary)] font-medium',
        dot: 'bg-[var(--text-tertiary)]',
      };
    case 'Conditional Short':
      return {
        badge:
          'border-orange-400/40 bg-orange-400/10 text-orange-400 font-medium',
        dot: 'bg-orange-400',
      };
    case 'Short Setup Active':
      return {
        badge:
          'border-[var(--negative)]/40 bg-[var(--negative-bg)] text-[var(--negative)] font-semibold',
        dot: 'bg-[var(--negative)]',
      };
    case 'Avoid':
      return {
        badge:
          'border-[var(--negative)]/40 bg-[var(--negative-bg)] text-[var(--negative)] font-semibold',
        dot: 'bg-[var(--negative)]',
      };
    case 'High Risk':
      return {
        badge:
          'border-orange-500/40 bg-orange-500/10 text-orange-400 font-semibold',
        dot: 'bg-orange-400',
      };
    default:
      return {
        badge:
          'border-[var(--border-default)] bg-[rgba(152,152,176,0.08)] text-[var(--text-secondary)] font-medium',
        dot: 'bg-[var(--text-tertiary)]',
      };
  }
}

function getLeanColor(lean: 'bullish' | 'bearish' | 'neutral') {
  if (lean === 'bullish') return 'text-[var(--positive)]';
  if (lean === 'bearish') return 'text-[var(--negative)]';
  return 'text-[var(--text-tertiary)]';
}

function getConfidenceColor(label: TradeCardConfidence) {
  switch (label) {
    case 'very_strong':
      return 'text-[var(--positive)]';
    case 'strong':
      return 'text-[var(--positive)]';
    case 'moderate':
      return 'text-amber-400';
    case 'low':
      return 'text-[var(--text-tertiary)]';
    default:
      return 'text-[var(--text-tertiary)]';
  }
}

// ── Price formatting ──────────────────────────────────────────────────────────

function fmtPrice(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return '—'; // em dash
  return `$${value.toFixed(2)}`;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
        {label}
      </span>
      <div className="h-px flex-1 bg-[var(--border-subtle)]" />
    </div>
  );
}

function LevelCell({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      className={cn(
        'rounded-[var(--radius-md)] border p-3.5',
        accent
          ? 'border-[var(--accent)]/30 bg-[var(--accent-subtle)]'
          : 'border-[var(--border-subtle)] bg-[var(--bg-surface-2)]'
      )}
    >
      <div className="text-[11px] font-medium uppercase tracking-[0.1em] text-[var(--text-tertiary)]">
        {label}
      </div>
      <div
        className={cn(
          'mt-1.5 tabular-nums text-sm font-semibold',
          accent ? 'text-[var(--accent)]' : 'text-[var(--text-primary)]'
        )}
      >
        {value}
      </div>
    </div>
  );
}

function TradeLevelsGrid({ levels }: { levels: TradeLevels }) {
  const noSetup =
    levels.method === 'no_setup' ||
    (levels.preferred_entry === null &&
      levels.aggressive_entry_min === null &&
      levels.aggressive_entry_max === null &&
      levels.confirmation_trigger === null &&
      levels.add_level === null &&
      levels.invalidation_level === null &&
      levels.target_1 === null &&
      levels.target_2 === null);

  if (noSetup) {
    return (
      <p className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] px-4 py-3 text-sm text-[var(--text-secondary)]">
        No specific trade levels available for this setup.
      </p>
    );
  }

  // Build "Aggressive Zone" display
  const aggMin = levels.aggressive_entry_min;
  const aggMax = levels.aggressive_entry_max;
  let aggressiveZone = '—';
  if (aggMin !== null && aggMax !== null) {
    aggressiveZone = `${fmtPrice(aggMin)} – ${fmtPrice(aggMax)}`;
  } else if (aggMin !== null) {
    aggressiveZone = fmtPrice(aggMin);
  } else if (aggMax !== null) {
    aggressiveZone = fmtPrice(aggMax);
  }

  return (
    <div className="space-y-2.5">
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        <LevelCell label="Preferred Entry" value={fmtPrice(levels.preferred_entry)} accent />
        <LevelCell label="Aggressive Zone" value={aggressiveZone} />
        <LevelCell label="Add At" value={fmtPrice(levels.add_level)} />
        <LevelCell label="Target 1" value={fmtPrice(levels.target_1)} />
        <LevelCell label="Exit / Stop" value={fmtPrice(levels.invalidation_level)} />
        <LevelCell label="Target 2" value={fmtPrice(levels.target_2)} />
      </div>

      {levels.chase_above !== null ? (
        <p className="text-xs text-[var(--text-tertiary)]">
          <span className="font-medium text-amber-400">Note:</span> Don&rsquo;t chase above{' '}
          <span className="font-semibold tabular-nums text-[var(--text-secondary)]">
            {fmtPrice(levels.chase_above)}
          </span>
          .
        </p>
      ) : null}

      {levels.warnings.length > 0 ? (
        <ul className="mt-1 space-y-1">
          {levels.warnings.map((w, i) => (
            <li
              key={`warning-${i}`}
              className="text-[11px] leading-5 text-[var(--text-tertiary)]"
            >
              <span className="mr-1 text-amber-400">&#9888;</span>
              {w}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function IfThenRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-1 gap-1 sm:grid-cols-[max-content_1fr] sm:gap-x-4">
      <dt className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--text-tertiary)] sm:w-44 sm:shrink-0">
        {label}
      </dt>
      <dd className="text-sm leading-6 text-[var(--text-secondary)]">{value}</dd>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

interface AITradeCardSectionProps {
  ticker: string;
  card: AITradeCard | null | undefined;
}

export default function AITradeCardSection({ ticker, card }: AITradeCardSectionProps) {
  if (!card) return null;

  const decisionStyle = getDecisionStyle(card.decision);
  const bestActionLabel = BEST_ACTION_LABELS[card.best_action_now] ?? card.best_action_now;
  const confidenceLabel = CONFIDENCE_LABELS[card.confidence_label] ?? card.confidence_label;
  const leanLabel =
    card.ai_lean.charAt(0).toUpperCase() + card.ai_lean.slice(1);

  return (
    <section className="deco-panel p-6 md:p-7">
      {/* Header row */}
      <div className="eyebrow">AI Trade Card</div>

      <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        {/* Left: Decision badge + metadata */}
        <div className="space-y-3">
          {/* Decision badge */}
          <div
            className={cn(
              'inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm',
              decisionStyle.badge
            )}
          >
            <span
              className={cn('h-2 w-2 shrink-0 rounded-full', decisionStyle.dot)}
            />
            {card.decision}
          </div>

          {/* Lean + Confidence inline row */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm">
            <span className="text-[var(--text-tertiary)]">
              AI Lean:{' '}
              <span className={cn('font-semibold', getLeanColor(card.ai_lean))}>
                {leanLabel}
              </span>
            </span>
            <span className="text-[var(--text-tertiary)]">
              Setup:{' '}
              <span
                className={cn('font-semibold', getConfidenceColor(card.confidence_label))}
              >
                {confidenceLabel}
              </span>
            </span>
            <span className="text-[var(--text-tertiary)]">
              Score:{' '}
              <span className="font-semibold tabular-nums text-[var(--text-primary)]">
                {card.setup_score}
              </span>
            </span>
          </div>

          {/* Best action */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-[var(--text-tertiary)]">Best Action:</span>
            <span className="font-semibold text-[var(--text-primary)]">{bestActionLabel}</span>
          </div>
        </div>

        {/* Right: ticker callout */}
        <div className="hidden flex-col items-end sm:flex">
          <span className="text-xs uppercase tracking-widest text-[var(--text-tertiary)]">
            {ticker}
          </span>
          <span className="mt-1 text-xs text-[var(--text-tertiary)]">{card.setup_type}</span>
        </div>
      </div>

      {/* Verdict */}
      <p className="mt-5 max-w-[72ch] text-base font-medium leading-7 text-[var(--text-primary)]">
        {card.verdict}
      </p>

      {/* ── Trade Levels ─────────────────────────────────────────────────────── */}
      <div className="mt-7 space-y-3.5">
        <SectionDivider label="Trade Levels" />
        <TradeLevelsGrid levels={card.trade_levels} />
      </div>

      {/* ── Main Reason ──────────────────────────────────────────────────────── */}
      {card.main_reason ? (
        <div className="mt-7 space-y-3.5">
          <SectionDivider label="Why It Could Work" />
          <div className="space-y-2.5">
            <p className="text-sm leading-7 text-[var(--text-secondary)]">{card.main_reason}</p>
            {card.bull_case.length > 0 ? (
              <ul className="mt-2 space-y-2">
                {card.bull_case.map((item, i) => (
                  <li
                    key={`bull-${i}`}
                    className="flex gap-3 text-sm leading-6 text-[var(--text-secondary)]"
                  >
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--positive)]" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* ── Main Risk ────────────────────────────────────────────────────────── */}
      {card.main_risk ? (
        <div className="mt-7 space-y-3.5">
          <SectionDivider label="Main Risk" />
          <div className="space-y-2.5">
            <p className="text-sm leading-7 text-[var(--text-secondary)]">{card.main_risk}</p>
            {card.bear_case.length > 0 ? (
              <ul className="mt-2 space-y-2">
                {card.bear_case.map((item, i) => (
                  <li
                    key={`bear-${i}`}
                    className="flex gap-3 text-sm leading-6 text-[var(--text-secondary)]"
                  >
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--negative)]" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* ── If/Then Plan ─────────────────────────────────────────────────────── */}
      <div className="mt-7 space-y-3.5">
        <SectionDivider label="If / Then Plan" />
        <dl className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-5 space-y-3.5">
          <IfThenRow label="If trigger hits" value={card.if_then_plan.if_trigger_hits} />
          <IfThenRow label="If rejects" value={card.if_then_plan.if_rejects} />
          <IfThenRow
            label="If breaks invalidation"
            value={card.if_then_plan.if_breaks_invalidation}
          />
          <IfThenRow label="If already holding" value={card.if_then_plan.if_already_holding} />
          <IfThenRow label="If missed entry" value={card.if_then_plan.if_missed_entry} />
        </dl>
      </div>
    </section>
  );
}
