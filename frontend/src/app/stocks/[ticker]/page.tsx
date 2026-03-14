'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { ChevronRight, Loader2 } from 'lucide-react';

import StockMetrics from '@/components/stock/StockMetrics';
import TradingViewChart from '@/components/stock/TradingViewChart';
import { Button } from '@/components/ui/button';
import { screenerAPI, stocksAPI } from '@/lib/api';
import {
  cn,
  formatCurrency,
  formatMarketCap,
  formatPercent,
  formatVolume,
  normalizePercentValue,
} from '@/lib/utils';
import type { Stock, StockPrice } from '@/types/stock';

interface PageProps {
  params: { ticker: string };
}

function getCompanyName(stock: Stock): string {
  return stock.name || stock.company_name || 'Company profile';
}

function getChangePercent(stock: Stock): number | null {
  if (typeof stock.day_change_percent === 'number') {
    return normalizePercentValue(stock.day_change_percent, 'auto');
  }
  if (typeof stock.change_percent === 'number') {
    return normalizePercentValue(stock.change_percent, 'auto');
  }
  return null;
}

function getChangeAccent(changePercent: number | null) {
  if (changePercent == null) {
    return {
      pillClass: 'bg-[rgba(152,152,176,0.08)] text-[var(--neutral)]',
      stroke: 'var(--neutral)',
    };
  }

  if (changePercent >= 0) {
    return {
      pillClass: 'bg-[var(--positive-bg)] text-[var(--positive)]',
      stroke: 'var(--positive)',
    };
  }

  return {
    pillClass: 'bg-[var(--negative-bg)] text-[var(--negative)]',
    stroke: 'var(--negative)',
  };
}

function get52WeekRange(stock: Stock): string {
  if (stock.fifty_two_week_low != null && stock.fifty_two_week_high != null) {
    return `${formatCurrency(stock.fifty_two_week_low)} - ${formatCurrency(stock.fifty_two_week_high)}`;
  }
  if (stock.fifty_two_week_low != null) {
    return `Low ${formatCurrency(stock.fifty_two_week_low)}`;
  }
  if (stock.fifty_two_week_high != null) {
    return `High ${formatCurrency(stock.fifty_two_week_high)}`;
  }
  return 'N/A';
}

function getSparklineSeries(stock: Stock, history?: StockPrice[]): number[] {
  const historicalSeries =
    history
      ?.slice(-6)
      .map((point) => point.close)
      .filter((value) => Number.isFinite(value)) ?? [];

  if (historicalSeries.length >= 2) {
    return historicalSeries;
  }

  const currentPrice = stock.current_price ?? 100;
  const rawChange = getChangePercent(stock) ?? 0;
  const changeRatio = rawChange / 100;
  const anchorPrice =
    Math.abs(changeRatio + 1) < 0.001 ? currentPrice * 0.82 : currentPrice / (1 + changeRatio);
  const tickerSeed =
    stock.ticker.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0) % 9;
  const sway = Math.max(Math.abs(changeRatio) * 0.6, 0.012);
  const modulation = (tickerSeed - 4) * 0.0035;

  return [
    anchorPrice * (1 - sway * 0.45 + modulation),
    anchorPrice * (1 + sway * 0.18 - modulation),
    anchorPrice * (1 - sway * 0.12 + modulation * 0.5),
    anchorPrice * (1 + sway * 0.3 - modulation * 0.75),
    currentPrice,
  ];
}

function getChartExtents(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  return { min, range: max - min || 1 };
}

function buildPolylinePoints(
  values: number[],
  width: number,
  height: number,
  padding: number
): string {
  if (values.length === 0) {
    return '';
  }

  const { min, range } = getChartExtents(values);

  return values
    .map((value, index) => {
      const x =
        values.length === 1
          ? width / 2
          : padding + (index * (width - padding * 2)) / (values.length - 1);
      const y = height - padding - ((value - min) / range) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(' ');
}

function getLastPoint(values: number[], width: number, height: number, padding: number) {
  if (values.length === 0) {
    return null;
  }

  const { min, range } = getChartExtents(values);
  const lastIndex = values.length - 1;
  const x =
    values.length === 1
      ? width / 2
      : padding + (lastIndex * (width - padding * 2)) / (values.length - 1);
  const y = height - padding - ((values[lastIndex] - min) / range) * (height - padding * 2);

  return { x, y };
}

function Sparkline({
  values,
  color,
  width = 76,
  height = 28,
  strokeWidth = 2,
}: {
  values: number[];
  color: string;
  width?: number;
  height?: number;
  strokeWidth?: number;
}) {
  const points = buildPolylinePoints(values, width, height, 3);
  const lastPoint = getLastPoint(values, width, height, 3);

  if (!points || !lastPoint) {
    return null;
  }

  return (
    <svg
      aria-hidden="true"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="shrink-0"
    >
      <polyline
        fill="none"
        points={points}
        stroke={color}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={strokeWidth}
      />
      <circle cx={lastPoint.x} cy={lastPoint.y} fill={color} r={strokeWidth} />
    </svg>
  );
}

export default function StockDetailPage({ params }: PageProps) {
  const ticker = params.ticker.toUpperCase();

  const { data: stock, isLoading: stockLoading } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => stocksAPI.getStock(ticker),
  });

  const { data: relatedStocks = [] } = useQuery({
    queryKey: ['related-stocks', ticker, stock?.sector, stock?.industry],
    enabled: Boolean(stock && (stock.sector || stock.industry)),
    queryFn: async () => {
      const response = await screenerAPI.screenStocks({
        sectors: stock?.sector ? [stock.sector] : undefined,
        industries: stock?.sector ? undefined : stock?.industry ? [stock.industry] : undefined,
        limit: 12,
        sort_by: 'market_cap',
        sort_order: 'desc',
      });

      return response.results.filter((candidate) => candidate.ticker !== ticker).slice(0, 5);
    },
  });

  const relatedHistoryQueries = useQueries({
    queries: relatedStocks.map((candidate) => ({
      queryKey: ['stock-price-history', candidate.ticker, '1mo'],
      queryFn: () => stocksAPI.getPriceHistory(candidate.ticker, '1mo'),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const relatedHistoryByTicker = useMemo(() => {
    const map = new Map<string, StockPrice[]>();

    relatedStocks.forEach((candidate, index) => {
      map.set(candidate.ticker, relatedHistoryQueries[index]?.data?.data ?? []);
    });

    return map;
  }, [relatedHistoryQueries, relatedStocks]);

  if (stockLoading) {
    return (
      <div className="container-custom py-8">
        <div className="deco-panel p-12 text-center">
          <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading stock profile...</p>
        </div>
      </div>
    );
  }

  if (!stock) {
    return (
      <div className="container-custom py-8">
        <div className="deco-panel p-12 text-center">
          <p className="mb-2 text-lg text-negative">Stock not found.</p>
          <p className="mb-6 text-sm text-muted-foreground">
            Ticker {ticker} is not available in the current database snapshot.
          </p>
          <Button asChild variant="outline">
            <Link href="/screener">Return to Screener</Link>
          </Button>
        </div>
      </div>
    );
  }

  const companyName = getCompanyName(stock);
  const changePercent = getChangePercent(stock);
  const changeAccent = getChangeAccent(changePercent);
  const heroStats = [
    { label: 'Market Cap', value: formatMarketCap(stock.market_cap) },
    { label: 'Volume', value: formatVolume(stock.volume) },
    { label: 'Beta', value: stock.beta != null ? stock.beta.toFixed(2) : 'N/A' },
    { label: '52W Range', value: get52WeekRange(stock) },
  ];

  return (
    <div className="container-custom py-8 md:py-10">
      <div className="space-y-6">
        <nav
          aria-label="Breadcrumb"
          className="flex flex-wrap items-center gap-2 text-[var(--text-tertiary)]"
          style={{ font: 'var(--caption)' }}
        >
          <Link
            href="/screener"
            className="transition-colors duration-[180ms] hover:text-[var(--accent)]"
          >
            Screener
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-[var(--text-secondary)]">{ticker}</span>
        </nav>

        <div className="space-y-4">
          <section className="relative overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface-1)] p-6 shadow-[var(--shadow-sm)] md:p-8">
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 left-0 w-[40%]"
              style={{
                background:
                  'linear-gradient(90deg, rgb(var(--accent-rgb) / 0.08) 0%, rgb(var(--accent-rgb) / 0.03) 22%, rgb(var(--accent-rgb) / 0) 40%)',
              }}
            />

            <div className="relative z-10 grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.92fr)] xl:items-center">
              <div className="min-w-0">
                <div className="eyebrow text-[var(--text-tertiary)]">Equity</div>
                <h1 className="heading-xl mt-3 text-[var(--text-primary)]">{ticker}</h1>
                <div className="heading-sm mt-2 text-[var(--text-secondary)]">{companyName}</div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button asChild size="lg">
                    <Link href={`/backtester?tickers=${ticker}`}>Backtest This Stock</Link>
                  </Button>
                  <Button asChild size="lg" variant="ghost">
                    <Link href={`/screener?search=${ticker}`}>Compare</Link>
                  </Button>
                </div>
              </div>

              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="heading-xl tabular-nums text-[var(--text-primary)]">
                    {stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : 'N/A'}
                  </div>
                  {changePercent !== null ? (
                    <div
                      className={cn(
                        'inline-flex rounded-[var(--radius-pill)] px-3 py-1 text-sm font-medium',
                        changeAccent.pillClass
                      )}
                    >
                      {formatPercent(changePercent, { mode: 'percent', withSign: true })}
                    </div>
                  ) : null}
                </div>

                <div className="flex flex-col divide-y divide-[var(--border-subtle)] overflow-hidden rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.01)] md:flex-row md:divide-x md:divide-y-0">
                  {heroStats.map((stat) => (
                    <div key={stat.label} className="flex-1 px-4 py-4">
                      <div
                        className="uppercase tracking-[0.1em] text-[var(--text-tertiary)]"
                        style={{ font: 'var(--caption)' }}
                      >
                        {stat.label}
                      </div>
                      <div
                        className="mt-2 tabular-nums text-[var(--text-primary)]"
                        style={{ font: 'var(--heading-sm)' }}
                      >
                        {stat.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <TradingViewChart ticker={ticker} />
        </div>

        <section className="deco-panel p-6 md:p-7">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="eyebrow">Fundamentals</div>
              <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Core Metrics</h2>
            </div>
            <Button asChild>
              <Link href={`/backtester?tickers=${ticker}`}>Backtest This Stock</Link>
            </Button>
          </div>
          <div className="deco-divider" />
          <StockMetrics stock={stock} />
        </section>

        {stock.description ? (
          <section className="deco-panel p-6 md:p-7">
            <div className="eyebrow">Company Overview</div>
            <h2 className="heading-lg mt-2 text-[var(--text-primary)]">About {companyName}</h2>
            <p className="mt-4 max-w-[72ch] leading-7 text-[var(--text-secondary)]">
              {stock.description}
            </p>
          </section>
        ) : null}

        {relatedStocks.length > 0 ? (
          <section className="deco-panel p-6 md:p-7">
            <div className="eyebrow">Related Names</div>
            <h2 className="heading-lg mt-2 text-[var(--text-primary)]">You may also like</h2>
            <div className="deco-scroll mt-5 overflow-x-auto pb-2">
              <div className="flex gap-4">
                {relatedStocks.map((candidate) => {
                  const candidateChange = getChangePercent(candidate);
                  const candidateAccent = getChangeAccent(candidateChange);

                  return (
                    <Link
                      key={candidate.ticker}
                      href={`/stocks/${candidate.ticker}`}
                      className="group min-w-[250px] max-w-[250px] rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface-1)] p-4 hover:-translate-y-[2px] hover:border-[var(--accent)] hover:shadow-[0_0_0_1px_var(--accent),0_16px_32px_rgba(91,91,214,0.14)]"
                      style={{
                        transition: 'transform 200ms ease, border-color 200ms ease, box-shadow 200ms ease',
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="heading-sm text-[var(--text-primary)]">
                            {candidate.ticker}
                          </div>
                          <div
                            className="mt-1 overflow-hidden text-ellipsis whitespace-nowrap text-sm text-[var(--text-secondary)]"
                            title={getCompanyName(candidate)}
                          >
                            {getCompanyName(candidate)}
                          </div>
                        </div>
                        <div
                          className={cn(
                            'inline-flex shrink-0 rounded-[var(--radius-pill)] px-2 py-[3px] text-[12px] font-medium',
                            candidateAccent.pillClass
                          )}
                        >
                          {formatPercent(candidateChange, { mode: 'percent', withSign: true })}
                        </div>
                      </div>

                      <div className="mt-5 flex items-end justify-between gap-3">
                        <div className="tabular-nums text-xl font-semibold text-[var(--text-primary)]">
                          {candidate.current_price != null
                            ? `$${candidate.current_price.toFixed(2)}`
                            : 'N/A'}
                        </div>
                        <Sparkline
                          color={candidateAccent.stroke}
                          values={getSparklineSeries(
                            candidate,
                            relatedHistoryByTicker.get(candidate.ticker)
                          )}
                        />
                      </div>

                      <div className="mt-4 text-[11px] uppercase tracking-[0.08em] text-[var(--text-tertiary)]">
                        {candidate.sector || stock.sector || 'Market'}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
