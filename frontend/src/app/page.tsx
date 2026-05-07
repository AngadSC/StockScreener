'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import {
  ArrowRight,
  BarChart3,
  ChevronRight,
  Search,
  Sparkles,
  Star,
  type LucideIcon,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { screenerAPI, stocksAPI } from '@/lib/api';
import {
  cn,
  formatMarketCap,
  formatPercent,
  formatVolume,
  normalizePercentValue,
} from '@/lib/utils';
import type { Stock, StockPrice } from '@/types/stock';

function getChangePercent(stock: Stock): number | null {
  if (typeof stock.day_change_percent === 'number') {
    return normalizePercentValue(stock.day_change_percent, 'auto');
  }
  if (typeof stock.change_percent === 'number') {
    return normalizePercentValue(stock.change_percent, 'auto');
  }
  return null;
}

function getCompanyName(stock: Stock): string {
  return stock.name || stock.company_name || 'Company profile';
}

function getSparklineSeries(stock: Stock, history?: StockPrice[]): number[] {
  const historicalSeries =
    history
      ?.slice(-5)
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
  width,
  height,
  strokeWidth,
}: {
  values: number[];
  color: string;
  width: number;
  height: number;
  strokeWidth: number;
}) {
  const points = buildPolylinePoints(values, width, height, 2);
  const lastPoint = getLastPoint(values, width, height, 2);

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

function FeatureCard({
  href,
  icon: Icon,
  title,
  description,
  cta,
}: {
  href: string;
  icon: LucideIcon;
  title: string;
  description: string;
  cta: string;
}) {
  return (
    <Link href={href} className="group block">
      <Card
        className="flex h-full flex-col gap-4 p-5 hover:-translate-y-[2px] hover:border-[var(--accent)] hover:shadow-[0_0_0_1px_var(--accent),0_16px_32px_rgba(91,91,214,0.14)]"
        style={{ transition: 'all 200ms ease' }}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-2)] text-[var(--accent)]">
          <Icon className="h-4 w-4" />
        </div>
        <div className="space-y-2">
          <h2 className="heading-sm text-[var(--text-primary)]">{title}</h2>
          <p
            className="text-[var(--text-secondary)]"
            style={{ fontSize: '11px', lineHeight: '1.4' }}
          >
            {description}
          </p>
        </div>
        <div className="mt-auto inline-flex items-center gap-2 text-sm font-medium text-[var(--accent)]">
          {cta}
          <ArrowRight className="h-4 w-4 transition-transform duration-[200ms] group-hover:translate-x-1" />
        </div>
      </Card>
    </Link>
  );
}

function MarketSection({
  eyebrow,
  title,
  stocks,
  historyByTicker,
}: {
  eyebrow: string;
  title: string;
  stocks: Stock[];
  historyByTicker: Map<string, StockPrice[]>;
}) {
  return (
    <Card className="p-5 md:p-6">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2 className="heading-md mt-2 text-[var(--text-primary)]">{title}</h2>
      </div>
      <div className="mt-5 space-y-2">
        {stocks.length === 0 ? (
          <div className="rounded-[10px] border border-[var(--border-subtle)] px-4 py-3 text-sm text-[var(--text-secondary)]">
            Market data is currently unavailable.
          </div>
        ) : null}

        {stocks.map((stock) => {
          const companyName = getCompanyName(stock);
          const changePercent = getChangePercent(stock);
          const accent = getChangeAccent(changePercent);

          return (
            <Link
              key={`${title}-${stock.ticker}`}
              href={`/stocks/${stock.ticker}`}
              className="group flex items-center justify-between gap-4 rounded-[10px] px-3 py-[10px] hover:bg-[var(--bg-surface-2)]"
              style={{ transition: 'background 120ms ease' }}
            >
              <div className="min-w-0">
                <div className="text-sm font-semibold tracking-[0.01em] text-[var(--text-primary)]">
                  {stock.ticker}
                </div>
                <div
                  className="max-w-[180px] overflow-hidden text-ellipsis whitespace-nowrap text-sm text-[var(--text-secondary)] md:max-w-[210px]"
                  title={companyName}
                >
                  {companyName}
                </div>
              </div>

              <div className="flex items-center gap-3 tabular-nums">
                <div className="text-sm font-medium text-[var(--text-primary)]">
                  {stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : 'N/A'}
                </div>
                <Sparkline
                  color={accent.stroke}
                  height={20}
                  strokeWidth={1.8}
                  values={getSparklineSeries(stock, historyByTicker.get(stock.ticker))}
                  width={40}
                />
                <div
                  className={cn(
                    'rounded-[var(--radius-sm)] px-2 py-[2px] text-xs font-medium',
                    accent.pillClass
                  )}
                >
                  {formatPercent(changePercent, { mode: 'percent', withSign: true })}
                </div>
                <ChevronRight
                  className="h-4 w-4 shrink-0 text-[var(--text-tertiary)] group-hover:translate-x-1"
                  style={{ transition: 'transform 150ms ease' }}
                />
              </div>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}

export default function HomePage() {
  const { data: gainers } = useQuery({
    queryKey: ['gainers'],
    queryFn: () =>
      screenerAPI.screenStocks({
        limit: 25,
        sort_by: 'day_change_percent',
        sort_order: 'desc',
        min_price: 5,
        min_market_cap: 1000000000,
      }),
  });

  const { data: losers } = useQuery({
    queryKey: ['losers'],
    queryFn: () =>
      screenerAPI.screenStocks({
        limit: 25,
        sort_by: 'day_change_percent',
        sort_order: 'asc',
        min_price: 5,
        min_market_cap: 1000000000,
      }),
  });

  const { data: active } = useQuery({
    queryKey: ['active'],
    queryFn: () =>
      screenerAPI.screenStocks({
        limit: 10,
        sort_by: 'volume',
        sort_order: 'desc',
        min_market_cap: 1000000000,
      }),
  });

  const topGainers = useMemo(() => {
    const stocks = gainers?.results ?? [];
    return [...stocks]
      .filter((stock) => (getChangePercent(stock) ?? 0) > 0)
      .sort((a, b) => (getChangePercent(b) ?? -Infinity) - (getChangePercent(a) ?? -Infinity))
      .slice(0, 5);
  }, [gainers]);

  const topLosers = useMemo(() => {
    const stocks = losers?.results ?? [];
    return [...stocks]
      .filter((stock) => (getChangePercent(stock) ?? 0) < 0)
      .sort((a, b) => (getChangePercent(a) ?? Infinity) - (getChangePercent(b) ?? Infinity))
      .slice(0, 5);
  }, [losers]);

  const mostActive = useMemo(() => (active?.results ?? []).slice(0, 5), [active]);
  const spotlight = topGainers[0] ?? mostActive[0] ?? topLosers[0];

  const trackedTickers = useMemo(
    () =>
      Array.from(
        new Set(
          [spotlight, ...topGainers, ...topLosers, ...mostActive]
            .filter((stock): stock is Stock => Boolean(stock))
            .map((stock) => stock.ticker)
        )
      ),
    [mostActive, spotlight, topGainers, topLosers]
  );

  const historyQueries = useQueries({
    queries: trackedTickers.map((ticker) => ({
      queryKey: ['stock-price-history', ticker, '1mo'],
      queryFn: () => stocksAPI.getPriceHistory(ticker, '1mo'),
      staleTime: 5 * 60 * 1000,
    })),
  });

  const historyByTicker = useMemo(() => {
    const map = new Map<string, StockPrice[]>();

    trackedTickers.forEach((ticker, index) => {
      map.set(ticker, historyQueries[index]?.data?.data ?? []);
    });

    return map;
  }, [historyQueries, trackedTickers]);

  const spotlightChange = spotlight ? getChangePercent(spotlight) : null;
  const spotlightAccent = getChangeAccent(spotlightChange);

  return (
    <div className="min-h-full">
      <div className="container-custom py-10 md:py-12">
        <div className="grid gap-8">
          <section>
            <Card className="p-6 md:p-8 lg:p-10">
              <div className="grid gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
                <div className="flex flex-col justify-center">
                  <div className="eyebrow">Market Intelligence</div>
                  <h1 className="heading-xl mt-3 text-[var(--text-primary)]">QuantorSignal</h1>
                  <p
                    className="heading-sm max-w-[480px] text-[var(--text-secondary)]"
                    style={{ marginTop: 'var(--space-3)' }}
                  >
                    Screen stocks, analyze fundamentals, and backtest strategies &mdash; in one
                    workspace.
                  </p>
                  <div
                    className="flex flex-wrap items-center"
                    style={{ marginTop: 'var(--space-5)', gap: 'var(--space-3)' }}
                  >
                    <Button asChild>
                      <Link href="/screener">
                        <Search className="h-4 w-4" />
                        Open Screener
                      </Link>
                    </Button>
                    <Button asChild variant="outline">
                      <Link href="/ai-analyzer">
                        <Sparkles className="h-4 w-4" />
                        Try AI Swing Analyzer
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button asChild variant="ghost">
                      <Link href="/backtester">
                        <BarChart3 className="h-4 w-4" />
                        Launch Backtester
                      </Link>
                    </Button>
                  </div>
                </div>

                <div className="grid gap-4">
                  <FeatureCard
                    cta="Open Screener"
                    description="Filter the market by quality, value, sector, and liquidity in seconds."
                    href="/screener"
                    icon={Search}
                    title="Screener"
                  />
                  <FeatureCard
                    cta="Launch Backtester"
                    description="Run historical strategy checks and compare portfolio behavior quickly."
                    href="/backtester"
                    icon={BarChart3}
                    title="Backtester"
                  />
                  <FeatureCard
                    cta="Open Watchlist"
                    description="Keep high-conviction names close and move from idea to review faster."
                    href="/watchlist"
                    icon={Star}
                    title="Watchlist"
                  />
                </div>
              </div>
            </Card>
          </section>

          {spotlight ? (
            <section>
              <Card className="p-6 md:p-8">
                <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_220px] lg:items-start">
                  <div className="min-w-0">
                    <div className="eyebrow">Featured Instrument</div>
                    <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="text-4xl font-semibold tracking-[-0.02em] text-[var(--text-primary)]">
                          {spotlight.ticker}
                        </div>
                        <div
                          className="mt-2 max-w-[22rem] overflow-hidden text-ellipsis whitespace-nowrap text-base text-[var(--text-secondary)]"
                          title={getCompanyName(spotlight)}
                        >
                          {getCompanyName(spotlight)}
                        </div>
                      </div>
                      <div className="text-left tabular-nums sm:text-right">
                        <div className="text-3xl font-semibold text-[var(--text-primary)]">
                          {spotlight.current_price != null
                            ? `$${spotlight.current_price.toFixed(2)}`
                            : 'N/A'}
                        </div>
                        <div
                          className={cn(
                            'mt-2 inline-flex rounded-[var(--radius-sm)] px-2 py-[2px] text-sm font-medium',
                            spotlightAccent.pillClass
                          )}
                        >
                          {formatPercent(spotlightChange, {
                            mode: 'percent',
                            withSign: true,
                          })}
                        </div>
                      </div>
                    </div>
                    <div className="mt-6 grid gap-4 sm:grid-cols-3">
                      <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
                        <div className="text-xs font-medium text-[var(--text-secondary)]">
                          Market Cap
                        </div>
                        <div className="mt-2 text-xl font-semibold text-[var(--text-primary)]">
                          {formatMarketCap(spotlight.market_cap)}
                        </div>
                      </div>
                      <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
                        <div className="text-xs font-medium text-[var(--text-secondary)]">
                          Volume
                        </div>
                        <div className="mt-2 text-xl font-semibold text-[var(--text-primary)]">
                          {formatVolume(spotlight.volume)}
                        </div>
                      </div>
                      <div className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-4">
                        <div className="text-xs font-medium text-[var(--text-secondary)]">
                          Sector
                        </div>
                        <div className="mt-2 text-xl font-semibold text-[var(--text-primary)]">
                          {spotlight.sector || 'N/A'}
                        </div>
                      </div>
                    </div>
                    <div className="mt-6">
                      <Link
                        href={`/stocks/${spotlight.ticker}`}
                        className="inline-flex items-center gap-2 text-sm font-medium text-[var(--accent)] transition-colors duration-[180ms] hover:text-[var(--accent-hover)]"
                      >
                        Open detail page
                        <ArrowRight className="h-4 w-4" />
                      </Link>
                    </div>
                  </div>

                  <div className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] p-5">
                    <div className="text-xs font-medium uppercase tracking-[0.1em] text-[var(--text-tertiary)]">
                      5 Day Trend
                    </div>
                    <div className="mt-5 flex h-[112px] items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[rgba(8,8,14,0.36)]">
                      <Sparkline
                        color={spotlightAccent.stroke}
                        height={52}
                        strokeWidth={2.4}
                        values={getSparklineSeries(spotlight, historyByTicker.get(spotlight.ticker))}
                        width={180}
                      />
                    </div>
                    <div className="mt-4 text-sm text-[var(--text-secondary)]">
                      Short-term price action for the current market spotlight.
                    </div>
                  </div>
                </div>
              </Card>
            </section>
          ) : null}

          <section className="grid gap-6 xl:grid-cols-3">
            <MarketSection
              eyebrow="Momentum"
              historyByTicker={historyByTicker}
              stocks={topGainers}
              title="Top Gainers"
            />
            <MarketSection
              eyebrow="Pressure"
              historyByTicker={historyByTicker}
              stocks={topLosers}
              title="Top Losers"
            />
            <MarketSection
              eyebrow="Activity"
              historyByTicker={historyByTicker}
              stocks={mostActive}
              title="Most Active"
            />
          </section>
        </div>
      </div>
    </div>
  );
}
