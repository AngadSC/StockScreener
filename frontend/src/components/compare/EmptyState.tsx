'use client';

import { GitCompareArrows } from 'lucide-react';

interface EmptyStateProps {
  onSelectExample: (tickers: string[]) => void;
}

const EXAMPLES: { label: string; tickers: string[] }[] = [
  { label: 'AAPL vs MSFT vs GOOGL', tickers: ['AAPL', 'MSFT', 'GOOGL'] },
  { label: 'NVDA vs AMD', tickers: ['NVDA', 'AMD'] },
  { label: 'JPM vs BAC vs WFC', tickers: ['JPM', 'BAC', 'WFC'] },
];

export default function EmptyState({ onSelectExample }: EmptyStateProps) {
  return (
    <div className="deco-panel flex min-h-[420px] items-center justify-center bg-[var(--bg-surface-1)] p-8">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-2)] text-[var(--text-secondary)]">
          <GitCompareArrows className="h-7 w-7" />
        </div>
        <h2 className="mt-5 text-2xl font-semibold text-[var(--text-primary)]">Add tickers to compare</h2>
        <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
          Search for 2 to 4 tickers above to line up performance, valuation, and quality metrics
          side by side.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example.label}
              type="button"
              onClick={() => onSelectExample(example.tickers)}
              className="chip transition-[background,border-color,color] hover:border-[var(--forest-line)] hover:text-[var(--ink)]"
            >
              {example.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
