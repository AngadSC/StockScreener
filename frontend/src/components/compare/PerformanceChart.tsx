'use client';

import { useMemo, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Loader2 } from 'lucide-react';

import { stocksAPI } from '@/lib/api';
import { cn, parseLocalDate } from '@/lib/utils';
import type { StockPrice } from '@/types/stock';

import type { SeriesColorMap } from './colors';

type Period = '1mo' | '6mo' | '1y';

const PERIOD_OPTIONS: { value: Period; label: string }[] = [
  { value: '1mo', label: '1M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
];

interface PerformanceChartProps {
  tickers: string[];
  colorMap: SeriesColorMap;
}

type ChartRow = { date: string } & Record<string, number | string | null>;

/**
 * Rebase every series to a single, shared baseline date rather than to each
 * ticker's own first close. The baseline is the latest first-available date
 * across the selection, so a ticker with a shorter history (a recent IPO, a
 * gap in coverage) can no longer sit at 0% while its peers already carry a
 * market move it was never exposed to. Rows before the baseline are dropped.
 */
function buildNormalizedSeries(tickers: string[], historyByTicker: Map<string, StockPrice[]>): ChartRow[] {
  const usableByTicker = new Map<string, StockPrice[]>();

  tickers.forEach((ticker) => {
    const points = (historyByTicker.get(ticker) ?? []).filter(
      (point) => Boolean(point.date) && Number.isFinite(point.close) && point.close > 0
    );
    if (points.length > 0) usableByTicker.set(ticker, points);
  });

  if (usableByTicker.size === 0) return [];

  // Common baseline = the latest "first available" date across the series.
  const firstDates = Array.from(usableByTicker.values()).map((points) =>
    points.reduce((earliest, point) => (point.date < earliest ? point.date : earliest), points[0].date)
  );
  const baseline = firstDates.reduce((latest, date) => (date > latest ? date : latest), firstDates[0]);

  const dateSet = new Set<string>();
  const pctByTickerDate = new Map<string, Map<string, number>>();

  usableByTicker.forEach((points, ticker) => {
    const inWindow = points.filter((point) => point.date >= baseline);
    if (inWindow.length === 0) return;

    // Close on the baseline date, or the first session after it if this ticker
    // did not trade that day.
    const baselinePoint = inWindow.reduce(
      (earliest, point) => (point.date < earliest.date ? point : earliest),
      inWindow[0]
    );
    const baselineClose = baselinePoint.close;
    if (!Number.isFinite(baselineClose) || baselineClose <= 0) return;

    const map = new Map<string, number>();
    inWindow.forEach((point) => {
      dateSet.add(point.date);
      map.set(point.date, (point.close / baselineClose - 1) * 100);
    });
    pctByTickerDate.set(ticker, map);
  });

  return Array.from(dateSet)
    .sort()
    .map((date) => {
      const row: ChartRow = { date };
      tickers.forEach((ticker) => {
        row[ticker] = pctByTickerDate.get(ticker)?.get(date) ?? null;
      });
      return row;
    });
}

function formatDateTick(value: string) {
  const parsed = parseLocalDate(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function ChartTooltip({
  active,
  payload,
  label,
  colorMap,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string | number; value: number | null }>;
  label?: string;
  colorMap: SeriesColorMap;
}) {
  if (!active || !payload || payload.length === 0) return null;

  const parsed = label ? parseLocalDate(label) : null;
  const dateLabel =
    parsed && !Number.isNaN(parsed.getTime())
      ? parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
      : label;

  const rows = [...payload]
    .filter((entry) => entry.value !== null && entry.value !== undefined)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

  if (rows.length === 0) return null;

  return (
    <div className="rounded-[12px] border border-[var(--border-default)] bg-[var(--bg-surface-1)] px-3 py-2.5 text-xs shadow-[var(--shadow-lg)]">
      <div className="mb-1.5 font-medium text-[var(--text-secondary)]">{dateLabel}</div>
      <div className="space-y-1">
        {rows.map((entry) => {
          const ticker = String(entry.dataKey);
          const value = entry.value ?? 0;
          return (
            <div key={ticker} className="flex items-center justify-between gap-4">
              <span className="inline-flex items-center gap-1.5 text-[var(--text-primary)]">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: colorMap.get(ticker) ?? 'var(--accent)' }}
                />
                {ticker}
              </span>
              <span
                className={cn(
                  'tabular-nums font-medium',
                  value >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]'
                )}
              >
                {value >= 0 ? '+' : ''}
                {value.toFixed(2)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function PerformanceChart({ tickers, colorMap }: PerformanceChartProps) {
  const [period, setPeriod] = useState<Period>('6mo');

  const historyQueries = useQueries({
    queries: tickers.map((ticker) => ({
      queryKey: ['compare-price-history', ticker, period],
      queryFn: () => stocksAPI.getPriceHistory(ticker, period),
      staleTime: 5 * 60 * 1000,
      retry: 1,
    })),
  });

  const isLoading = historyQueries.some((query) => query.isLoading);
  const hasAnyData = historyQueries.some((query) => (query.data?.data?.length ?? 0) > 0);
  const failedTickers = tickers.filter((_, index) => historyQueries[index]?.isError);

  const chartData = useMemo(() => {
    const historyByTicker = new Map<string, StockPrice[]>();
    tickers.forEach((ticker, index) => {
      historyByTicker.set(ticker, historyQueries[index]?.data?.data ?? []);
    });
    return buildNormalizedSeries(tickers, historyByTicker);
  }, [tickers, historyQueries]);

  return (
    <div className="deco-panel p-5 md:p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="eyebrow">Performance</div>
          <h2 className="heading-md mt-2 text-[var(--text-primary)]">Normalized % change</h2>
          <p className="mt-1.5 max-w-md text-[13px] leading-relaxed text-[var(--text-tertiary)]">
            Every line is rebased to 0% on the first date all selected tickers have data, so you
            compare percentage moves over the same window, not share prices.
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-full border border-[var(--line)] bg-[var(--surface)] p-1">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => setPeriod(option.value)}
              className={cn(
                'rounded-full px-3 py-1.5 text-xs font-medium transition-colors duration-[180ms]',
                period === option.value
                  ? 'bg-[var(--ink)] text-[var(--ivory)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {failedTickers.length > 0 ? (
        <div className="mb-4 rounded-[12px] border border-[var(--negative)]/20 bg-[var(--negative-bg)] px-3 py-2 text-xs text-[var(--negative)]">
          Price history unavailable for {failedTickers.join(', ')}.
        </div>
      ) : null}

      {isLoading ? (
        <div className="flex h-[340px] items-center justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-[var(--accent)]" />
        </div>
      ) : !hasAnyData ? (
        <div className="flex h-[340px] items-center justify-center text-sm text-[var(--text-secondary)]">
          No price history available for this selection.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={chartData} margin={{ top: 4, right: 12, left: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateTick}
              tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
              stroke="var(--line-2)"
              interval="preserveStartEnd"
              minTickGap={40}
            />
            <YAxis
              tickFormatter={(value: number) => `${value >= 0 ? '+' : ''}${value.toFixed(0)}%`}
              tick={{ fontSize: 11, fill: 'var(--text-tertiary)' }}
              stroke="var(--line-2)"
              width={52}
            />
            <Tooltip content={<ChartTooltip colorMap={colorMap} />} />
            <Legend
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              iconType="line"
              iconSize={14}
            />
            {tickers.map((ticker) => (
              <Line
                key={ticker}
                type="monotone"
                dataKey={ticker}
                name={ticker}
                stroke={colorMap.get(ticker) ?? 'var(--accent)'}
                strokeWidth={2}
                dot={false}
                connectNulls
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
