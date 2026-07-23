'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import {
  Activity,
  ArrowRight,
  BarChart3,
  CalendarDays,
  ChevronRight,
  GitCompareArrows,
  Landmark,
  Mail,
  Search,
  Sparkles,
  Star,
  Users,
  type LucideIcon,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { screenerAPI, stocksAPI } from '@/lib/api';
import {
  cn,
  formatPercent,
  normalizePercentValue,
} from '@/lib/utils';
import type { Stock, StockPrice } from '@/types/stock';

function getChangePercent(stock: Stock): number | null {
  if (typeof stock.day_change_percent === 'number') {
    return normalizePercentValue(stock.day_change_percent, 'percent');
  }
  if (typeof stock.change_percent === 'number') {
    return normalizePercentValue(stock.change_percent, 'percent');
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

type Tool = {
  href: string;
  icon: LucideIcon;
  name: string;
  descriptor: string;
};

const FREE_TOOLS: Tool[] = [
  { href: '/screener', icon: Search, name: 'Screener', descriptor: '35+ fundamental and technical filters' },
  { href: '/markets', icon: Activity, name: 'Scanners', descriptor: 'Gainers, losers, breakouts, unusual volume' },
  { href: '/earnings', icon: CalendarDays, name: 'Earnings', descriptor: 'Reporting calendar for the next 14 days' },
  { href: '/insiders', icon: Users, name: 'Insiders', descriptor: 'Form 4 buys and sells from SEC filings' },
  { href: '/macro', icon: Landmark, name: 'Macro', descriptor: 'Rates, inflation, jobs, and volatility (FRED)' },
  { href: '/compare', icon: GitCompareArrows, name: 'Compare', descriptor: 'Line up to four tickers side by side' },
  { href: '/backtester', icon: BarChart3, name: 'Backtester', descriptor: 'Test a strategy against price history' },
  { href: '/watchlist', icon: Star, name: 'Watchlist', descriptor: 'Track the names you revisit most' },
];

function ToolTile({ tool }: { tool: Tool }) {
  const Icon = tool.icon;
  return (
    <Link
      href={tool.href}
      className="group row-hover flex items-center gap-3.5 rounded-[12px] border border-[var(--border-subtle)] bg-[var(--bg-surface-1)] px-4 py-3.5"
    >
      <span className="icon-tile h-9 w-9 transition-colors duration-[180ms] group-hover:text-[var(--text-primary)]">
        <Icon className="h-4 w-4" strokeWidth={1.6} aria-hidden="true" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-medium text-[var(--text-primary)]">{tool.name}</span>
        <span className="block truncate text-[12px] leading-5 text-[var(--text-tertiary)]">
          {tool.descriptor}
        </span>
      </span>
      <ChevronRight className="row-arrow h-4 w-4 shrink-0" aria-hidden="true" />
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
              className="group row-hover flex items-center justify-between gap-4 rounded-[10px] px-3 py-[10px]"
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
                  className="row-arrow h-4 w-4 shrink-0"
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

function SpotlightPanel({
  spotlight,
  changePercent,
  accent,
  series,
}: {
  spotlight: Stock;
  changePercent: number | null;
  accent: ReturnType<typeof getChangeAccent>;
  series: number[];
}) {
  return (
    <Card className="hud scan-host flex flex-col justify-between gap-5 p-5 md:p-6">
      <span className="hud-c1" />
      <span className="hud-c2" />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="eyebrow">Spotlight</div>
          <div className="serif-tight mt-2 text-4xl leading-none text-[var(--text-primary)]">
            {spotlight.ticker}
          </div>
          <div
            className="mt-1.5 max-w-[14rem] overflow-hidden text-ellipsis whitespace-nowrap text-sm text-[var(--text-secondary)]"
            title={getCompanyName(spotlight)}
          >
            {getCompanyName(spotlight)}
          </div>
        </div>
        <div className="text-right tabular-nums">
          <div className="readout text-2xl text-[var(--text-primary)]">
            {spotlight.current_price != null ? `$${spotlight.current_price.toFixed(2)}` : 'N/A'}
          </div>
          <div
            className={cn(
              'mt-2 inline-flex rounded-[var(--radius-sm)] px-2 py-[2px] text-sm font-medium',
              accent.pillClass
            )}
          >
            {formatPercent(changePercent, { mode: 'percent', withSign: true })}
          </div>
        </div>
      </div>

      <div className="flex h-[92px] items-center justify-center rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[rgba(8,8,14,0.36)]">
        <Sparkline color={accent.stroke} height={48} strokeWidth={2.2} values={series} width={200} />
      </div>

      <Link
        href={`/stocks/${spotlight.ticker}`}
        className="inline-flex items-center gap-2 text-sm font-medium text-[var(--accent)] transition-colors duration-[180ms] hover:text-[var(--accent-hover)]"
      >
        Open detail page
        <ArrowRight className="h-4 w-4" />
      </Link>
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
        <div className="grid gap-10 md:gap-14">
          {/* Hero + live spotlight */}
          <section className="border-b border-t border-[var(--line)] py-8 md:py-10">
            <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px] lg:items-center">
              <div>
                <div className="live-dot">Live market desk</div>
                <h1 className="mt-4 max-w-[18ch]">Screen, scan, and analyze US equities</h1>
                <p className="mt-4 max-w-[60ch] text-base leading-7 text-[var(--text-secondary)]">
                  Free screeners, market scanners, earnings, insider filings, and macro data. Pro
                  adds AI swing reports; Trader and Elite add daily research emails.
                </p>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Button asChild>
                    <Link href="/screener">
                      <Search className="h-4 w-4" />
                      Open screener
                    </Link>
                  </Button>
                  <Button asChild variant="outline">
                    <Link href="/markets">
                      <Activity className="h-4 w-4" />
                      Browse scanners
                    </Link>
                  </Button>
                  <Button asChild variant="ghost">
                    <Link href="/pricing">
                      See plans
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </div>
              </div>

              {spotlight ? (
                <SpotlightPanel
                  spotlight={spotlight}
                  changePercent={spotlightChange}
                  accent={spotlightAccent}
                  series={getSparklineSeries(spotlight, historyByTicker.get(spotlight.ticker))}
                />
              ) : null}
            </div>
          </section>

          {/* Live movers */}
          <section>
            <div className="mb-5 flex items-end justify-between gap-4">
              <div>
                <div className="eyebrow">Today</div>
                <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Market movers</h2>
              </div>
              <Link
                href="/markets"
                className="inline-flex items-center gap-2 text-sm font-medium text-[var(--accent)] transition-colors duration-[180ms] hover:text-[var(--accent-hover)]"
              >
                All scanners
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="grid gap-6 xl:grid-cols-3">
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
            </div>
          </section>

          {/* Free tools */}
          <section>
            <div className="mb-5">
              <div className="eyebrow">Free · no account required</div>
              <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Market tools</h2>
              <p className="mt-2 max-w-[64ch] text-sm leading-6 text-[var(--text-secondary)]">
                The full research toolkit is free. Sign in only to save a watchlist.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {FREE_TOOLS.map((tool) => (
                <ToolTile key={tool.href} tool={tool} />
              ))}
            </div>
          </section>

          {/* Paid ladder */}
          <section className="grid gap-6 lg:grid-cols-2">
            <Card className="flex flex-col p-6 md:p-7">
              <div className="flex items-center gap-2">
                <span className="status">Pro</span>
                <span className="text-[12px] text-[var(--text-tertiary)]">$19.99 / mo</span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <span className="icon-tile h-10 w-10">
                  <Sparkles className="h-5 w-5" strokeWidth={1.6} />
                </span>
                <h3 className="heading-md text-[var(--text-primary)]">AI Swing Analyzer</h3>
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                Structured swing-trade reports for any US ticker: the setup, key levels, recent
                catalysts, and a plain-English thesis. 150 reports a month.
              </p>
              <div className="mt-auto flex flex-wrap gap-3 pt-6">
                <Button asChild>
                  <Link href="/ai-analyzer">
                    <Sparkles className="h-4 w-4" />
                    Open AI Analyst
                  </Link>
                </Button>
                <Button asChild variant="ghost">
                  <Link href="/pricing">Pro details</Link>
                </Button>
              </div>
            </Card>

            <Card className="flex flex-col p-6 md:p-7">
              <div className="flex items-center gap-2">
                <span className="status">Trader &amp; Elite</span>
                <span className="text-[12px] text-[var(--text-tertiary)]">$39.99 / $79.99 / mo</span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <span className="icon-tile h-10 w-10">
                  <Mail className="h-5 w-5" strokeWidth={1.6} />
                </span>
                <h3 className="heading-md text-[var(--text-primary)]">Daily research, emailed</h3>
              </div>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-[var(--text-secondary)]">
                <li>
                  <span className="font-medium text-[var(--text-primary)]">Daily Market Brief</span>{' '}
                  <span className="text-[var(--text-tertiary)]">(Trader)</span> — an AI market
                  summary sent before the open.
                </li>
                <li>
                  <span className="font-medium text-[var(--text-primary)]">Watchlist AI Digest</span>{' '}
                  <span className="text-[var(--text-tertiary)]">(Elite)</span> — pre-market AI
                  analysis of your watchlist, ranked and delivered daily.
                </li>
              </ul>
              <div className="mt-auto flex flex-wrap gap-3 pt-6">
                <Button asChild variant="outline">
                  <Link href="/pricing">Compare plans</Link>
                </Button>
                <Button asChild variant="ghost">
                  <Link href="/settings/emails">
                    <Mail className="h-4 w-4" />
                    Email settings
                  </Link>
                </Button>
              </div>
            </Card>
          </section>
        </div>
      </div>
    </div>
  );
}
