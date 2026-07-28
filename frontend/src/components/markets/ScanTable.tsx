'use client';

import Link from 'next/link';

import { formatPercent, formatVolume } from '@/lib/utils';
import type { MarketScanRow, MarketScanTabConfig } from '@/types/market';

interface ScanTableProps {
  rows: MarketScanRow[];
  isLoading?: boolean;
  tab: MarketScanTabConfig;
  asOfDate: string | null;
}

function formatMetric(value: number | null, format: MarketScanTabConfig['metricFormat']): string {
  if (value === null || value === undefined) return 'N/A';
  if (format === 'ratio') return `${value.toFixed(2)}x`;
  return formatPercent(value, { mode: 'percent', withSign: true });
}

function SkeletonRows() {
  return (
    <tbody>
      {Array.from({ length: 8 }).map((_, index) => (
        <tr key={index} className="border-b border-[var(--border-subtle)] last:border-b-0">
          <td className="px-4 py-3">
            <div className="screener-skeleton h-4 w-5 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <div className="screener-skeleton h-4 w-14 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <div className="screener-skeleton h-4 w-36 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <div className="screener-skeleton h-4 w-24 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-4 w-16 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-6 w-16 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-4 w-16 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-4 w-16 rounded-full" />
          </td>
        </tr>
      ))}
    </tbody>
  );
}

export default function ScanTable({ rows, isLoading, tab, asOfDate }: ScanTableProps) {
  if (!isLoading && rows.length === 0) {
    return (
      <div className="deco-panel flex min-h-[320px] items-center justify-center bg-[var(--bg-surface-1)] p-8">
        <div className="max-w-sm text-center">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">
            {asOfDate ? 'No matches today' : 'Scanner data is generated after the market close'}
          </h2>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            {asOfDate
              ? `No stocks met the ${tab.label.toLowerCase()} threshold as of ${asOfDate}.`
              : 'Check back after the next close for gainers, losers, and more.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="deco-panel overflow-hidden bg-[var(--bg-surface-1)]">
      <div className="deco-scroll overflow-x-auto">
        <table className="deco-table">
          <thead className="bg-[var(--bg-surface-2)]">
            <tr className="border-b border-[var(--border-default)]">
              <th className="w-10 px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-left">Symbol</th>
              <th className="px-4 py-3 text-left">Company</th>
              <th className="px-4 py-3 text-left">Sector</th>
              <th className="px-4 py-3 text-right">Price</th>
              <th className="px-4 py-3 text-right">Chg%</th>
              <th className="px-4 py-3 text-right">Volume</th>
              <th className="px-4 py-3 text-right">{tab.metricLabel}</th>
            </tr>
          </thead>

          {isLoading ? (
            <SkeletonRows />
          ) : (
            <tbody>
              {rows.map((row, index) => {
                const hasChange = row.change_pct !== null && row.change_pct !== undefined;
                const isPositive = hasChange && (row.change_pct as number) >= 0;

                return (
                  <tr
                    key={row.symbol}
                    className="row-hover border-b border-[var(--border-subtle)] text-sm"
                  >
                    <td className="px-4 py-3 text-[var(--text-tertiary)]">{index + 1}</td>
                    <td className="serif-num px-4 py-3 text-base text-[var(--text-primary)]">
                      <Link href={`/stocks/${row.symbol}`} className="transition-colors hover:text-[var(--accent)]">
                        {row.symbol}
                      </Link>
                    </td>
                    <td
                      title={row.name ?? undefined}
                      className="max-w-[260px] truncate px-4 py-3 text-[var(--text-secondary)]"
                    >
                      {row.name || 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-[var(--text-secondary)]">{row.sector || 'N/A'}</td>
                    <td className="serif-num px-4 py-3 text-right text-[17px] text-[var(--text-primary)]">
                      {row.close !== null && row.close !== undefined ? `$${row.close.toFixed(2)}` : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {hasChange ? (
                        <span className={`chip tabular-nums ${isPositive ? 'chip-up' : 'chip-dn'}`}>
                          {formatPercent(row.change_pct, { mode: 'percent', withSign: true })}
                        </span>
                      ) : (
                        <span className="tabular-nums text-[var(--text-secondary)]">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--text-secondary)]">
                      {formatVolume(row.volume)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--text-secondary)]">
                      {formatMetric(row.metric, tab.metricFormat)}
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
