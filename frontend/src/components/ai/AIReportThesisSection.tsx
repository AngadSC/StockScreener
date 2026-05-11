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
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--accent)]" />
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

export default function AIReportThesisSection({ report }: AIReportThesisSectionProps) {
  const moveItems = toBulletItems(report.why_it_could_move);
  const failItems = toBulletItems(report.why_it_could_fail);
  const confirmationItems = toBulletItems(report.confirmation_signals);

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

      <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--accent)]/30 bg-[var(--accent-subtle)] p-5">
        <h3 className="heading-sm text-[var(--text-primary)]">Final Verdict</h3>
        <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
          {report.final_verdict}
        </p>
      </div>
    </section>
  );
}
