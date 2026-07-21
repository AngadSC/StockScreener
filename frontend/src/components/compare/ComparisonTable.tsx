'use client';

import { type ReactNode } from 'react';
import { X } from 'lucide-react';

import {
  cn,
  formatMarketCap,
  formatPercent,
  normalizePercentValue,
} from '@/lib/utils';
import type { Stock } from '@/types/stock';

import RangeBar from './RangeBar';
import type { SeriesColorMap } from './colors';

interface ComparisonTableProps {
  tickers: string[];
  stocksByTicker: Map<string, Stock | undefined>;
  loadingTickers: Set<string>;
  erroredTickers: Set<string>;
  colorMap: SeriesColorMap;
  onRemove: (ticker: string) => void;
}

type BestDirection = 'higher' | 'lower';

interface MetricRow {
  key: string;
  label: string;
  format: (stock: Stock) => string;
  compareValue: (stock: Stock) => number | null;
  bestDirection?: BestDirection;
}

const numberFmt = (value: number | null | undefined, digits = 1): string =>
  value == null || Number.isNaN(value) ? 'N/A' : value.toFixed(digits);

const currencyFmt = (value: number | null | undefined): string =>
  value == null || Number.isNaN(value) ? 'N/A' : `$${value.toFixed(2)}`;

const ratioPercentFmt = (value: number | null | undefined): string =>
  value == null || Number.isNaN(value) ? 'N/A' : formatPercent(value, { mode: 'ratio' });

const positiveOnly = (value: number | null): number | null => (value != null && value > 0 ? value : null);

const METRIC_ROWS: MetricRow[] = [
  {
    key: 'price',
    label: 'Price',
    format: (s) => currencyFmt(s.current_price),
    compareValue: () => null,
  },
  {
    key: 'day_change',
    label: 'Day Change',
    format: (s) => {
      const raw = s.day_change_percent ?? s.change_percent;
      return raw == null ? 'N/A' : formatPercent(raw, { mode: 'auto', withSign: true });
    },
    compareValue: (s) => normalizePercentValue(s.day_change_percent ?? s.change_percent, 'auto'),
    bestDirection: 'higher',
  },
  {
    key: 'market_cap',
    label: 'Market Cap',
    format: (s) => formatMarketCap(s.market_cap),
    compareValue: () => null,
  },
  {
    key: 'pe_ratio',
    label: 'P/E Ratio',
    format: (s) => numberFmt(s.pe_ratio),
    compareValue: (s) => positiveOnly(s.pe_ratio),
    bestDirection: 'lower',
  },
  {
    key: 'forward_pe',
    label: 'Forward P/E',
    format: (s) => numberFmt(s.forward_pe),
    compareValue: (s) => positiveOnly(s.forward_pe),
    bestDirection: 'lower',
  },
  {
    key: 'peg_ratio',
    label: 'PEG Ratio',
    format: (s) => numberFmt(s.peg_ratio, 2),
    compareValue: (s) => positiveOnly(s.peg_ratio),
    bestDirection: 'lower',
  },
  {
    key: 'pb_ratio',
    label: 'P/B Ratio',
    format: (s) => numberFmt(s.pb_ratio, 2),
    compareValue: (s) => positiveOnly(s.pb_ratio),
    bestDirection: 'lower',
  },
  {
    key: 'ps_ratio',
    label: 'P/S Ratio',
    format: (s) => numberFmt(s.ps_ratio, 2),
    compareValue: (s) => positiveOnly(s.ps_ratio),
    bestDirection: 'lower',
  },
  {
    key: 'profit_margin',
    label: 'Profit Margin',
    format: (s) => ratioPercentFmt(s.profit_margin),
    compareValue: (s) => s.profit_margin,
    bestDirection: 'higher',
  },
  {
    key: 'operating_margin',
    label: 'Operating Margin',
    format: (s) => ratioPercentFmt(s.operating_margin),
    compareValue: (s) => s.operating_margin,
    bestDirection: 'higher',
  },
  {
    key: 'roe',
    label: 'ROE',
    format: (s) => ratioPercentFmt(s.roe),
    compareValue: (s) => s.roe,
    bestDirection: 'higher',
  },
  {
    key: 'debt_to_equity',
    label: 'Debt / Equity',
    format: (s) => numberFmt(s.debt_to_equity, 2),
    compareValue: (s) => (s.debt_to_equity != null && s.debt_to_equity >= 0 ? s.debt_to_equity : null),
    bestDirection: 'lower',
  },
  {
    key: 'revenue_growth',
    label: 'Revenue Growth',
    format: (s) => ratioPercentFmt(s.revenue_growth),
    compareValue: (s) => s.revenue_growth,
    bestDirection: 'higher',
  },
  {
    key: 'earnings_growth',
    label: 'Earnings Growth',
    format: (s) => ratioPercentFmt(s.earnings_growth),
    compareValue: (s) => s.earnings_growth,
    bestDirection: 'higher',
  },
  {
    key: 'dividend_yield',
    label: 'Dividend Yield',
    format: (s) => ratioPercentFmt(s.dividend_yield),
    compareValue: (s) => (s.dividend_yield != null ? s.dividend_yield : null),
    bestDirection: 'higher',
  },
  {
    key: 'beta',
    label: 'Beta',
    format: (s) => numberFmt(s.beta, 2),
    compareValue: () => null,
  },
];

function computeBestTicker(
  row: MetricRow,
  tickers: string[],
  stocksByTicker: Map<string, Stock | undefined>
): string | null {
  if (!row.bestDirection) return null;

  const entries = tickers
    .map((ticker) => {
      const stock = stocksByTicker.get(ticker);
      const value = stock ? row.compareValue(stock) : null;
      return { ticker, value };
    })
    .filter((entry): entry is { ticker: string; value: number } => entry.value != null);

  if (entries.length < 2) return null;

  const best = entries.reduce((champion, entry) => {
    if (row.bestDirection === 'higher') {
      return entry.value > champion.value ? entry : champion;
    }
    return entry.value < champion.value ? entry : champion;
  });

  return best.ticker;
}

function HeaderCell({
  ticker,
  stock,
  isLoading,
  isErrored,
  color,
  onRemove,
}: {
  ticker: string;
  stock: Stock | undefined;
  isLoading: boolean;
  isErrored: boolean;
  color: string;
  onRemove: (ticker: string) => void;
}) {
  const companyName = stock?.name || stock?.company_name;

  return (
    <th className="min-w-[140px] whitespace-nowrap px-4 py-3 text-right align-top">
      <div className="flex items-start justify-end gap-2">
        <div className="min-w-0 text-right">
          <div className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-sm font-semibold text-[var(--text-primary)]">{ticker}</span>
          </div>
          <div className="mt-0.5 max-w-[160px] truncate text-[11px] font-normal normal-case text-[var(--text-tertiary)]" title={companyName || undefined}>
            {isLoading ? 'Loading...' : isErrored ? 'No data available' : companyName || '—'}
          </div>
        </div>
        <button
          type="button"
          onClick={() => onRemove(ticker)}
          className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[var(--text-tertiary)] transition-colors hover:bg-[var(--negative-bg)] hover:text-[var(--negative)]"
          aria-label={`Remove ${ticker} from comparison`}
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </th>
  );
}

function ValueCell({ children, isBest }: { children: ReactNode; isBest: boolean }) {
  return (
    <td
      className={cn(
        'px-4 py-3 text-right text-sm tabular-nums text-[var(--text-primary)]',
        isBest && 'bg-[var(--accent-subtle)]'
      )}
    >
      <span className="inline-flex items-center justify-end gap-1.5">
        {isBest ? <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" /> : null}
        {children}
      </span>
    </td>
  );
}

export default function ComparisonTable({
  tickers,
  stocksByTicker,
  loadingTickers,
  erroredTickers,
  colorMap,
  onRemove,
}: ComparisonTableProps) {
  return (
    <div className="deco-panel hud overflow-hidden bg-[var(--bg-surface-1)]">
      <span className="hud-c1" />
      <span className="hud-c2" />
      <div className="border-b border-[var(--line)] px-5 py-4">
        <div className="eyebrow">Fundamentals</div>
        <h2 className="heading-md mt-2 text-[var(--text-primary)]">Side-by-side comparison</h2>
      </div>

      <div className="deco-scroll overflow-x-auto">
        <table className="w-full caption-bottom text-sm">
          <thead className="bg-[var(--bg-surface-2)]">
            <tr className="border-b border-[var(--border-default)] text-xs font-medium uppercase tracking-[0.06em] text-[var(--text-secondary)]">
              <th className="sticky left-0 z-10 min-w-[160px] bg-[var(--bg-surface-2)] px-4 py-3 text-left">
                Metric
              </th>
              {tickers.map((ticker) => (
                <HeaderCell
                  key={ticker}
                  ticker={ticker}
                  stock={stocksByTicker.get(ticker)}
                  isLoading={loadingTickers.has(ticker)}
                  isErrored={erroredTickers.has(ticker)}
                  color={colorMap.get(ticker) ?? 'var(--accent)'}
                  onRemove={onRemove}
                />
              ))}
            </tr>
          </thead>
          <tbody>
            {METRIC_ROWS.map((row) => {
              const bestTicker = computeBestTicker(row, tickers, stocksByTicker);

              return (
                <tr
                  key={row.key}
                  className="border-b border-[var(--border-subtle)] last:border-b-0 hover:bg-[var(--bg-surface-2)]/40"
                >
                  <td className="sticky left-0 z-10 bg-[var(--bg-surface-1)] px-4 py-3 text-sm text-[var(--text-secondary)]">
                    {row.label}
                  </td>
                  {tickers.map((ticker) => {
                    const stock = stocksByTicker.get(ticker);
                    if (loadingTickers.has(ticker)) {
                      return (
                        <td key={ticker} className="px-4 py-3 text-right">
                          <span className="screener-skeleton ml-auto inline-block h-4 w-14 rounded-full" />
                        </td>
                      );
                    }
                    if (!stock || erroredTickers.has(ticker)) {
                      return (
                        <td key={ticker} className="px-4 py-3 text-right text-sm text-[var(--text-tertiary)]">
                          &mdash;
                        </td>
                      );
                    }
                    return (
                      <ValueCell key={ticker} isBest={bestTicker === ticker}>
                        {row.format(stock)}
                      </ValueCell>
                    );
                  })}
                </tr>
              );
            })}

            <tr className="border-b border-[var(--border-subtle)] last:border-b-0">
              <td className="sticky left-0 z-10 bg-[var(--bg-surface-1)] px-4 py-3 align-middle text-sm text-[var(--text-secondary)]">
                52W Range
              </td>
              {tickers.map((ticker) => {
                const stock = stocksByTicker.get(ticker);
                if (loadingTickers.has(ticker)) {
                  return (
                    <td key={ticker} className="px-4 py-3 text-right">
                      <span className="screener-skeleton ml-auto inline-block h-4 w-24 rounded-full" />
                    </td>
                  );
                }
                if (!stock || erroredTickers.has(ticker)) {
                  return (
                    <td key={ticker} className="px-4 py-3 text-right text-sm text-[var(--text-tertiary)]">
                      &mdash;
                    </td>
                  );
                }
                return (
                  <td key={ticker} className="px-4 py-3">
                    <div className="flex justify-end">
                      <RangeBar
                        low={stock.fifty_two_week_low}
                        high={stock.fifty_two_week_high}
                        current={stock.current_price}
                      />
                    </div>
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      <div className="border-t border-[var(--border-subtle)] px-5 py-3 text-[11px] text-[var(--text-tertiary)]">
        A tinted cell marks the strongest value in a row where a clear "better" direction exists.
      </div>
    </div>
  );
}
