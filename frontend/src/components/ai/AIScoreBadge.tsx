import { cn } from '@/lib/utils';

interface AIScoreBadgeProps {
  label: string;
  score: number;
}

function clampScore(score: number) {
  if (!Number.isFinite(score)) return 0;
  return Math.min(100, Math.max(0, Math.round(score)));
}

function getScoreColor(score: number) {
  if (score > 70) {
    return 'bg-[var(--positive)]';
  }

  if (score >= 40) {
    return 'bg-amber-400';
  }

  return 'bg-[var(--negative)]';
}

export default function AIScoreBadge({ label, score }: AIScoreBadgeProps) {
  const normalizedScore = clampScore(score);

  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-[var(--text-secondary)]">{label}</span>
        <span className="tabular-nums text-sm font-semibold text-[var(--text-primary)]">
          {normalizedScore}
        </span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-[var(--radius-pill)] bg-[var(--bg-surface-3)]">
        <div
          className={cn('h-full rounded-[var(--radius-pill)]', getScoreColor(normalizedScore))}
          style={{ width: `${normalizedScore}%` }}
        />
      </div>
    </div>
  );
}
