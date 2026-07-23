import type { AIReportOutput } from '@/types/ai';

interface AIReportThesisSectionProps {
  report: AIReportOutput;
}

function toBulletItems(value: string | string[]) {
  if (Array.isArray(value)) {
    return value.map((item) => item.trim()).filter(Boolean);
  }

  return value
    .split(/\n|;|\r/)
    .map((item) => item.replace(/^(?:[-*\u2022]\s*|\d+[.)]\s*)/, '').trim())
    .filter(Boolean);
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="mt-3 space-y-2">
      {items.map((item, i) => (
        <li key={`${i}-${item}`} className="flex gap-3 text-sm leading-6 text-[var(--text-secondary)]">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--text-tertiary)]" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function ActionItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
      <div className="text-xs uppercase tracking-[0.1em] text-[var(--text-tertiary)]">{label}</div>
      <div className="mt-2 text-sm font-medium leading-6 text-[var(--text-primary)]">{value}</div>
    </div>
  );
}

const STRUCTURE_LABEL_OVERRIDES: Record<string, string> = {
  insufficient_data: 'Insufficient Data',
  no_clear_setup: 'No Clear Setup',
  legacy_cached_report: 'Not Available',
  confirmed_breakout: 'Confirmed Breakout',
  failed_breakout: 'Failed Breakout',
  breakout_attempt: 'Breakout Attempt',
  compression_breakout_attempt: 'Compression Breakout Attempt',
  trend_pullback: 'Trend Pullback',
  base_compression: 'Base Compression',
  extended_above_sma20: 'Extended Above SMA 20',
  below_key_sma: 'Below Key SMA',
  pullback_to_sma20: 'Pullback to SMA 20',
  pullback_to_sma50: 'Pullback to SMA 50',
  near_20d_high: 'Near 20-Day High',
  near_60d_high: 'Near 60-Day High',
  higher_highs_higher_lows: 'Higher Highs / Higher Lows',
  lower_highs_lower_lows: 'Lower Highs / Lower Lows',
  range_compression: 'Range Compression',
  gap_up_recent: 'Recent Gap Up',
  gap_down_recent: 'Recent Gap Down',
  mean_reversion_bounce: 'Mean Reversion Bounce',
  momentum_continuation: 'Momentum Continuation',
  breakdown_risk: 'Breakdown Risk',
  breakout_retest: 'Breakout Retest',
  pullback_entry: 'Pullback Entry',
};

function formatStructureLabel(value: string) {
  const normalized = value.trim().toLowerCase().replace(/[_-]+/g, '_');
  if (normalized in STRUCTURE_LABEL_OVERRIDES) {
    return STRUCTURE_LABEL_OVERRIDES[normalized];
  }
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\bsma(\d+)\b/gi, 'SMA $1')
    .replace(/\bobv\b/gi, 'OBV')
    .replace(/\brsi\b/gi, 'RSI')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatPercent(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return 'N/A';
  }

  return `${value.toFixed(1)}%`;
}

function formatPrice(value: number | null) {
  if (value === null || Number.isNaN(value)) {
    return 'N/A';
  }

  return `$${value.toFixed(2)}`;
}

function StructureMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
      <div className="text-xs uppercase tracking-[0.1em] text-[var(--text-tertiary)]">{label}</div>
      <div className="mt-2 text-sm font-semibold text-[var(--text-primary)]">{value}</div>
    </div>
  );
}

export default function AIReportThesisSection({ report }: AIReportThesisSectionProps) {
  const moveItems = toBulletItems(report.why_it_could_move);
  const failItems = toBulletItems(report.why_it_could_fail);
  const confirmationItems = toBulletItems(report.confirmation_signals);
  const structure = report.price_action_structure;

  return (
    <section className="deco-panel p-6 md:p-7">
      <div className="eyebrow">Thesis</div>
      <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Trade Read</h2>

      <p className="mt-5 max-w-[80ch] text-sm leading-7 text-[var(--text-secondary)]">
        {report.trade_read}
      </p>
      <p className="mt-3 max-w-[80ch] text-sm leading-7 text-[var(--text-secondary)]">
        {report.main_thesis}
      </p>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <ActionItem label="Entry Zone" value={report.entry_zone} />
        <ActionItem label="Confirmation Trigger" value={report.confirmation_trigger} />
        <ActionItem label="Invalidation Level" value={report.invalidation_level} />
        <ActionItem label="Target 1" value={report.target_1} />
        <ActionItem label="Target 2" value={report.target_2} />
        <ActionItem label="Watchlist Action" value={report.watchlist_action} />
      </div>

      <div className="mt-6 border-t border-[var(--border-subtle)] pt-5">
        <h3 className="heading-sm text-[var(--text-primary)]">Price Structure</h3>
        <div className="mt-4 flex flex-wrap gap-2">
          {structure.labels.map((label) => (
            <span
              key={label}
              className="rounded-full border border-[var(--border-strong)] bg-[rgba(152,152,176,0.08)] px-3 py-1 text-xs font-medium text-[var(--text-secondary)]"
            >
              {formatStructureLabel(label)}
            </span>
          ))}
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <StructureMetric label="Setup" value={formatStructureLabel(structure.setup_label)} />
          <StructureMetric label="Breakout" value={formatStructureLabel(structure.breakout_label)} />
          <StructureMetric label="Support" value={formatPrice(structure.support_level)} />
          <StructureMetric label="Resistance" value={formatPrice(structure.resistance_level)} />
          <StructureMetric label="To Support" value={formatPercent(structure.distance_to_support_pct)} />
          <StructureMetric label="To Resistance" value={formatPercent(structure.distance_to_resistance_pct)} />
          <StructureMetric label="Pullback" value={formatStructureLabel(structure.pullback_label)} />
          <StructureMetric label="Range" value={formatStructureLabel(structure.range_label)} />
        </div>
      </div>

      <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-5">
        <h3 className="heading-sm text-[var(--text-primary)]">Risk Reward</h3>
        <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
          {report.risk_reward_summary}
        </p>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-5">
          <h3 className="heading-sm text-[var(--text-primary)]">Why It Could Move</h3>
          <BulletList items={moveItems} />
        </div>

        <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-5">
          <h3 className="heading-sm text-[var(--text-primary)]">Why It Could Fail</h3>
          <BulletList items={failItems} />
        </div>
      </div>

      <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-5">
        <h3 className="heading-sm text-[var(--text-primary)]">Confirmation Signals</h3>
        <BulletList items={confirmationItems} />
      </div>

      <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--bg-surface-2)] p-5">
        <h3 className="heading-sm text-[var(--text-primary)]">Final Verdict</h3>
        <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
          {report.final_verdict}
        </p>
      </div>
    </section>
  );
}
