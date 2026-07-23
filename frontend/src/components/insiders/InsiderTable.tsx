'use client';

import { useRouter } from 'next/navigation';
import { SearchX } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';
import type { InsiderTransaction } from '@/types/insiders';

interface InsiderTableProps {
  transactions: InsiderTransaction[];
  isLoading?: boolean;
}

function formatValue(value: number | null): string {
  if (value === null || value === undefined || isNaN(value)) return 'N/A';
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function formatShares(shares: number | null): string {
  if (shares === null || shares === undefined || isNaN(shares)) return 'N/A';
  return Math.round(shares).toLocaleString('en-US');
}

function formatPrice(price: number | null): string {
  if (price === null || price === undefined || isNaN(price)) return 'N/A';
  return `$${price.toFixed(2)}`;
}

function SkeletonRows() {
  return (
    <tbody>
      {Array.from({ length: 10 }).map((_, index) => (
        <tr key={index} className="border-b border-[var(--border-subtle)] last:border-b-0">
          {Array.from({ length: 8 }).map((__, cell) => (
            <td key={cell} className="px-4 py-3">
              <div className="screener-skeleton h-4 w-full max-w-[120px] rounded-full" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

export default function InsiderTable({ transactions, isLoading }: InsiderTableProps) {
  const router = useRouter();

  if (!isLoading && transactions.length === 0) {
    return (
      <div className="deco-panel flex min-h-[420px] items-center justify-center bg-[var(--bg-surface-1)] p-8">
        <div className="max-w-sm text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-2)] text-[var(--text-secondary)]">
            <SearchX className="h-7 w-7" />
          </div>
          <h2 className="mt-5 text-2xl font-semibold text-[var(--text-primary)]">
            No insider filings
          </h2>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            No Form 4 transactions match these filters yet. Try widening the window or
            lowering the minimum value.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="deco-panel overflow-hidden bg-[var(--bg-surface-1)]">
      <div className="overflow-x-auto">
        <table className="deco-table">
          <thead className="bg-[var(--bg-surface-2)]">
            <tr className="border-b border-[var(--border-default)]">
              <th className="px-4 py-3 text-left">Filed</th>
              <th className="px-4 py-3 text-left">Symbol</th>
              <th className="px-4 py-3 text-left">Company</th>
              <th className="px-4 py-3 text-left">Insider</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-right">Shares</th>
              <th className="px-4 py-3 text-right">Price</th>
              <th className="px-4 py-3 text-right">Value</th>
            </tr>
          </thead>

          {isLoading ? (
            <SkeletonRows />
          ) : (
            <tbody>
              {transactions.map((txn, index) => {
                const isBuy = txn.type === 'buy';
                const company = txn.company || 'N/A';

                return (
                  <tr
                    key={`${txn.accession_no}-${index}`}
                    tabIndex={0}
                    onClick={() => router.push(`/stocks/${txn.symbol}`)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        router.push(`/stocks/${txn.symbol}`);
                      }
                    }}
                    className="group row-hover cursor-pointer border-b border-[var(--border-subtle)] text-sm focus-visible:bg-[var(--bg-surface-2)] focus-visible:outline-none"
                  >
                    <td className="whitespace-nowrap px-4 py-3 tabular-nums text-[var(--text-secondary)]">
                      {formatDate(txn.filed_date)}
                    </td>
                    <td className="serif-num px-4 py-3 text-base text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
                      {txn.symbol}
                    </td>
                    <td
                      title={company}
                      className="max-w-[220px] truncate px-4 py-3 text-[var(--text-secondary)]"
                    >
                      {company}
                    </td>
                    <td className="max-w-[240px] px-4 py-3">
                      <div className="truncate text-[var(--text-primary)]" title={txn.owner_name ?? ''}>
                        {txn.owner_name || 'N/A'}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        {txn.is_officer ? (
                          <Badge variant="secondary">Officer</Badge>
                        ) : null}
                        {txn.is_director ? (
                          <Badge variant="outline">Director</Badge>
                        ) : null}
                        {txn.owner_title ? (
                          <span
                            className="truncate text-[11px] text-[var(--text-tertiary)]"
                            title={txn.owner_title}
                          >
                            {txn.owner_title}
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`chip tabular-nums ${isBuy ? 'chip-up' : 'chip-dn'}`}>
                        {isBuy ? 'Buy' : 'Sell'}
                      </span>
                    </td>
                    <td className="serif-num px-4 py-3 text-right tabular-nums text-[var(--text-secondary)]">
                      {formatShares(txn.shares)}
                    </td>
                    <td className="serif-num px-4 py-3 text-right tabular-nums text-[var(--text-secondary)]">
                      {formatPrice(txn.price)}
                    </td>
                    <td
                      className={`serif-num px-4 py-3 text-right text-[15px] tabular-nums ${
                        isBuy ? 'text-[var(--up)]' : 'text-[var(--text-primary)]'
                      }`}
                    >
                      {formatValue(txn.value)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          )}
        </table>
      </div>
    </div>
  );
}
