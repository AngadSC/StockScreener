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

export default function AIReportThesisSection({ report }: AIReportThesisSectionProps) {
  const moveItems = toBulletItems(report.why_it_could_move);
  const failItems = toBulletItems(report.why_it_could_fail);
  const confirmationItems = toBulletItems(report.confirmation_signals);

  return (
    <section className="deco-panel p-6 md:p-7">
      <div className="eyebrow">Thesis</div>
      <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Trade Read</h2>

      <p className="mt-5 max-w-[80ch] text-sm leading-7 text-[var(--text-secondary)]">
        {report.main_thesis}
      </p>

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

      <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--negative)]/30 bg-[var(--negative-bg)] p-4 text-sm leading-6 text-[var(--text-primary)]">
        <span className="font-semibold text-[var(--negative)]">Invalidation: </span>
        {report.invalidation}
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
