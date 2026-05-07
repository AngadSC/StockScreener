import AIScoreBadge from '@/components/ai/AIScoreBadge';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { AIReportOutput } from '@/types/ai';

interface AIReportSummaryCardProps {
  report: AIReportOutput;
}

function getBiasClass(swingBias: string) {
  const normalizedBias = swingBias.trim().toLowerCase();

  if (normalizedBias === 'bullish') {
    return 'border-[var(--positive)]/35 bg-[var(--positive-bg)] text-[var(--positive)]';
  }

  if (normalizedBias === 'bearish') {
    return 'border-[var(--negative)]/35 bg-[var(--negative-bg)] text-[var(--negative)]';
  }

  return 'border-[var(--border-strong)] bg-[rgba(152,152,176,0.08)] text-[var(--neutral)]';
}

export default function AIReportSummaryCard({ report }: AIReportSummaryCardProps) {
  return (
    <section className="deco-panel p-6 md:p-7">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="eyebrow">AI Report</div>
          <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Summary</h2>
        </div>
        <Badge className={cn('capitalize', getBiasClass(report.swing_bias))}>
          {report.swing_bias}
        </Badge>
      </div>

      <div className="mt-5 rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
        <div className="text-xs uppercase tracking-[0.1em] text-[var(--text-tertiary)]">
          Setup Type
        </div>
        <div className="heading-sm mt-2 text-[var(--text-primary)]">{report.setup_type}</div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <AIScoreBadge label="Setup Quality" score={report.setup_quality_score} />
        <AIScoreBadge label="Entry Timing" score={report.entry_timing_score} />
        <AIScoreBadge label="Risk" score={report.risk_score} />
        <AIScoreBadge label="Technical" score={report.technical_score} />
      </div>
    </section>
  );
}
