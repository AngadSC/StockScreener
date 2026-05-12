import AIScoreBadge from '@/components/ai/AIScoreBadge';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { AIReportOutput } from '@/types/ai';

interface AIReportSummaryCardProps {
  report: AIReportOutput;
}

function getBiasClass(directionalBias: string) {
  const normalizedBias = directionalBias.trim().toLowerCase();

  if (normalizedBias === 'bullish' || normalizedBias === 'mixed_bullish_lean') {
    return 'border-[var(--positive)]/35 bg-[var(--positive-bg)] text-[var(--positive)]';
  }

  if (normalizedBias === 'bearish' || normalizedBias === 'mixed_bearish_lean') {
    return 'border-[var(--negative)]/35 bg-[var(--negative-bg)] text-[var(--negative)]';
  }

  return 'border-[var(--border-strong)] bg-[rgba(152,152,176,0.08)] text-[var(--neutral)]';
}

function formatReportLabel(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getRatingClass(rating: string) {
  const normalized = rating.trim().toLowerCase();

  if (normalized === 'buy' || normalized === 'accumulate') {
    return 'border-[var(--positive)]/35 bg-[var(--positive-bg)] text-[var(--positive)]';
  }

  if (normalized === 'avoid') {
    return 'border-[var(--negative)]/35 bg-[var(--negative-bg)] text-[var(--negative)]';
  }

  return 'border-[var(--border-strong)] bg-[rgba(152,152,176,0.08)] text-[var(--neutral)]';
}

function TimeframeRatingCard({
  label,
  rating,
  timeframe,
  confidence,
  reason,
}: {
  label: string;
  rating: string;
  timeframe: string;
  confidence: number;
  reason: string;
}) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.1em] text-[var(--text-tertiary)]">
            {label}
          </div>
          <div className="mt-2 text-xs text-[var(--text-tertiary)]">{timeframe}</div>
        </div>
        <Badge className={cn('shrink-0 capitalize', getRatingClass(rating))}>
          {formatReportLabel(rating)}
        </Badge>
      </div>
      <div className="mt-3 text-sm font-semibold text-[var(--text-primary)]">
        {Math.round(confidence)}% confidence
      </div>
      <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{reason}</p>
    </div>
  );
}

export default function AIReportSummaryCard({ report }: AIReportSummaryCardProps) {
  const scoreBadges = [
    ['Confidence', report.confidence_score],
    ['Swing', report.swing_trade_score],
    ['Short Term', report.short_term_score],
    ['Long Term', report.long_term_score],
    ['Setup Quality', report.setup_quality_score],
    ['Entry Timing', report.entry_timing_score],
    ['Technical', report.technical_score],
    ['Price Structure', report.price_structure_score],
    ['Volume', report.volume_score],
    ['Momentum', report.momentum_score],
    ['Risk/Reward', report.risk_reward_score],
    ['Risk Control', report.risk_score],
    ['News', report.news_score],
    ['Fundamentals', report.fundamental_score],
    ['Revenue/Earnings', report.revenue_earnings_quality_score],
    ['Valuation', report.valuation_score],
  ] as const;

  return (
    <section className="deco-panel p-6 md:p-7">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="eyebrow">AI Report</div>
          <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Summary</h2>
        </div>
        <Badge className={cn('capitalize', getBiasClass(report.directional_bias))}>
          {formatReportLabel(report.directional_bias)}
        </Badge>
      </div>

      <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
        <div className="text-xs uppercase tracking-[0.1em] text-[var(--text-tertiary)]">
          Action
        </div>
        <div className="heading-sm mt-2 text-[var(--text-primary)]">
          {formatReportLabel(report.action_label)}
        </div>
        <div className="mt-2 text-sm text-[var(--text-secondary)]">
          {formatReportLabel(report.setup_type)}
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {scoreBadges.map(([label, score]) => (
          <AIScoreBadge key={label} label={label} score={score} />
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <TimeframeRatingCard
          label="Short Term"
          rating={report.timeframe_ratings.short_term.rating}
          timeframe={report.timeframe_ratings.short_term.timeframe}
          confidence={report.timeframe_ratings.short_term.confidence_score}
          reason={report.timeframe_ratings.short_term.reason}
        />
        <TimeframeRatingCard
          label="Swing"
          rating={report.timeframe_ratings.swing.rating}
          timeframe={report.timeframe_ratings.swing.timeframe}
          confidence={report.timeframe_ratings.swing.confidence_score}
          reason={report.timeframe_ratings.swing.reason}
        />
        <TimeframeRatingCard
          label="Long Term"
          rating={report.timeframe_ratings.long_term.rating}
          timeframe={report.timeframe_ratings.long_term.timeframe}
          confidence={report.timeframe_ratings.long_term.confidence_score}
          reason={report.timeframe_ratings.long_term.reason}
        />
      </div>
    </section>
  );
}
