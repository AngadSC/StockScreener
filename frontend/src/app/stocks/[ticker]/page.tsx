'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { ChevronRight, Loader2 } from 'lucide-react';

import AIReportCard from '@/components/ai/AIReportCard';
import StockMetrics from '@/components/stock/StockMetrics';
import TradingViewChart from '@/components/stock/TradingViewChart';
import { Button } from '@/components/ui/button';
import { screenerAPI, stocksAPI } from '@/lib/api';
import { useAuth } from '@/lib/auth';
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

// The API stores the day move as a ratio (-0.013 = -1.3%), so it has to be
// scaled by 100 before it is rendered as a percentage.
function getChangePercent(stock: Stock): number | null {
  if (typeof stock.day_change_percent === 'number') {
    return normalizePercentValue(stock.day_change_percent, 'ratio');
  }
  if (typeof stock.change_percent === 'number') {
    return normalizePercentValue(stock.change_percent, 'ratio');
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
  const { userTier } = useAuth();

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
  const heroStats = [
    { label: 'Market Cap', value: formatMarketCap(stock.market_cap) },
    { label: 'Volume', value: formatVolume(stock.volume) },
    { label: 'P/E', value: stock.pe_ratio != null ? stock.pe_ratio.toFixed(1) : 'N/A' },
    { label: 'Beta', value: stock.beta != null ? stock.beta.toFixed(2) : 'N/A' },
    { label: 'Dividend', value: stock.dividend_yield != null ? formatPercent(stock.dividend_yield, { mode: 'auto' }) : 'N/A' },
    { label: '52W Range', value: get52WeekRange(stock) },
  ];
  const rangeLow = stock.fifty_two_week_low ?? null;
  const rangeHigh = stock.fifty_two_week_high ?? null;
  const rangePosition =
    rangeLow != null && rangeHigh != null && stock.current_price != null && rangeHigh > rangeLow
      ? Math.min(100, Math.max(0, ((stock.current_price - rangeLow) / (rangeHigh - rangeLow)) * 100))
      : 50;

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
          <section className="hud relative overflow-hidden rounded-[var(--radius-xl)] border border-[var(--line-2)] bg-[var(--surface)] p-6 shadow-[var(--shadow-2)] md:p-8">
            <span className="hud-c1" />
            <span className="hud-c2" />

            <div className="relative z-10 grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(360px,0.92fr)] xl:items-center">
              <div className="min-w-0">
                <div className="smallcap">
                  Markets / {stock.sector || 'Sector'} / {ticker}
                </div>
                <h1 className="mt-3 text-[clamp(44px,13vw,64px)] leading-[0.9] md:text-[clamp(64px,8vw,96px)]">{ticker}</h1>
                <div className="serif mt-3 text-2xl italic text-[var(--ink-2)]">{companyName}</div>
                <div className="smallcap-low mt-2">{stock.industry || 'Equity research profile'}</div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button asChild size="lg">
                    <Link href="/ai-analyzer">AI analysis</Link>
                  </Button>
                  <Button asChild size="lg" variant="outline">
                    <Link href={`/compare?symbols=${ticker}`}>Compare with…</Link>
                  </Button>
                  <Button asChild size="lg" variant="ghost">
                    <Link href={`/backtester?tickers=${ticker}`}>Backtest</Link>
                  </Button>
                </div>
              </div>

              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="readout text-4xl text-[var(--text-primary)] md:text-5xl">
                    {stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : 'N/A'}
                  </div>
                  {changePercent !== null ? (
                    <div
                      className={cn('chip text-sm', changePercent >= 0 ? 'chip-up' : 'chip-dn')}
                    >
                      {formatPercent(changePercent, { mode: 'percent', withSign: true })}
                    </div>
                  ) : null}
                </div>

                <div>
                  <div className="mb-2 flex justify-between smallcap-low">
                    <span>{rangeLow != null ? formatCurrency(rangeLow) : '52W low'}</span>
                    <span>{get52WeekRange(stock)}</span>
                    <span>{rangeHigh != null ? formatCurrency(rangeHigh) : '52W high'}</span>
                  </div>
                  <div className="relative h-2 rounded-full bg-[linear-gradient(90deg,var(--dn),var(--forest),var(--up))]">
                    <span
                      className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-[var(--surface)] bg-[var(--ink)] shadow-[var(--shadow-2)]"
                      style={{ left: `${rangePosition}%` }}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 overflow-hidden rounded-[var(--radius-md)] border border-[var(--line)] bg-[rgba(221,228,225,0.015)] md:grid-cols-3">
                  {heroStats.map((stat) => (
                    <div key={stat.label} className="border-b border-r border-[var(--line)] px-4 py-4 last:border-r-0">
                      <div className="smallcap-low">{stat.label}</div>
                      <div className="serif-num mt-2 text-lg text-[var(--text-primary)]">
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

        <AIReportCard key={ticker} ticker={ticker} userTier={userTier} />

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
                      className="group min-w-[250px] max-w-[250px] rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface-1)] p-4 hover:-translate-y-[2px] hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-2)]"
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
