'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Search, Sparkles, Star } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { screenerAPI } from '@/lib/api';
import { cn, formatMarketCap, formatPercent, formatVolume, normalizePercentValue } from '@/lib/utils';
import type { Stock } from '@/types/stock';

function getChangePercent(stock: Stock): number | null {
  if (typeof stock.day_change_percent === 'number') {
    return normalizePercentValue(stock.day_change_percent, 'auto');
  }
  if (typeof stock.change_percent === 'number') {
    return normalizePercentValue(stock.change_percent, 'auto');
  }
  return null;
}

function MarketList({
  title,
  subtitle,
  stocks,
  tone,
}: {
  title: string;
  subtitle: string;
  stocks: Stock[];
  tone: 'up' | 'down' | 'neutral';
}) {
  return (
    <section className="deco-panel p-6">
      <div className="deco-kicker">{subtitle}</div>
      <h2 className="mt-2">{title}</h2>
      <div className="deco-divider" />
      <div className="space-y-3">
        {stocks.map((stock) => {
          const changePercent = getChangePercent(stock);
          const isPositive = (changePercent ?? 0) >= 0;
          const toneClass =
            tone === 'neutral'
              ? 'text-muted-foreground'
              : isPositive
                ? 'text-positive'
                : 'text-negative';

          return (
            <Link
              key={stock.ticker}
              href={`/stocks/${stock.ticker}`}
              className="interactive-card block rounded-lg border border-border/70 bg-muted/20 px-4 py-4"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-xl font-semibold text-foreground">{stock.ticker}</div>
                  <div className="truncate text-sm text-muted-foreground">
                    {stock.name || stock.company_name || 'Company profile'}
                  </div>
                </div>
                <div className="text-right tabular-nums">
                  <div className="text-lg font-semibold text-foreground">
                    {stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : 'N/A'}
                  </div>
                  <div className={`text-sm ${toneClass}`}>
                    {tone === 'neutral'
                      ? stock.volume
                        ? `${formatVolume(stock.volume)} volume`
                        : 'N/A'
                      : formatPercent(changePercent, { mode: 'percent', withSign: true })}
                  </div>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
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

  const mostActive = (active?.results ?? []).slice(0, 5);
  const spotlight = topGainers[0] ?? mostActive[0];

  return (
    <div className="min-h-screen">
      <div className="container-custom py-8">
        <section className="deco-panel p-8 md:p-10">
          <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
            <div>
              <h1 className="max-w-4xl text-glow md:text-[64px]">QuantorSignal</h1>
              <p className="mt-5 max-w-3xl text-lg leading-relaxed text-muted-foreground">
                Screen the market, inspect individual names, and test portfolio behavior inside a
                single workflow built for deliberate analysis.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/screener">
                    <Search className="h-4 w-4" />
                    Open Screener
                  </Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/backtester">
                    <Sparkles className="h-4 w-4" />
                    Launch Backtester
                  </Link>
                </Button>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Link href="/screener" className="deco-panel interactive-card p-5">
                <div className="deco-kicker">Discover</div>
                <div className="mt-2 text-2xl font-semibold">Screener</div>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  Filter by valuation, quality, sector, industry, liquidity, and growth without
                  losing table density.
                </p>
                <div className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-primary">
                  Open Screener <ArrowRight className="h-4 w-4" />
                </div>
              </Link>
              <Link href="/backtester" className="deco-panel interactive-card p-5">
                <div className="deco-kicker">Test</div>
                <div className="mt-2 text-2xl font-semibold">Backtester</div>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  Compare weighted baskets, tune strategies, and review trade logs in a compact
                  workspace.
                </p>
                <div className="mt-5 inline-flex items-center gap-2 text-sm font-medium text-primary">
                  Launch Backtester <ArrowRight className="h-4 w-4" />
                </div>
              </Link>
              <Link href="/watchlist" className="deco-panel interactive-card p-5 sm:col-span-2">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="deco-kicker">Track</div>
                    <div className="mt-2 text-2xl font-semibold">Watchlist</div>
                    <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                      Keep a focused list of the names you are actively monitoring.
                    </p>
                  </div>
                  <Star className="h-8 w-8 text-primary" />
                </div>
              </Link>
            </div>
          </div>
        </section>

        {spotlight ? (
          <section className="mt-8">
            <div className="deco-panel p-6">
              <div className="deco-kicker">Featured stock</div>
              <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
                <div>
                  <div className="text-4xl font-semibold">{spotlight.ticker}</div>
                  <p className="mt-2 text-base text-muted-foreground">
                    {spotlight.name || spotlight.company_name || 'Selected from today’s leaders'}
                  </p>
                </div>
                <div className="text-right tabular-nums">
                  <div className="text-3xl font-semibold">
                    {spotlight.current_price != null ? `$${spotlight.current_price.toFixed(2)}` : 'N/A'}
                  </div>
                  <div
                    className={cn(
                      'mt-2 text-sm',
                      (getChangePercent(spotlight) ?? 0) >= 0 ? 'text-positive' : 'text-negative'
                    )}
                  >
                    {formatPercent(getChangePercent(spotlight), {
                      mode: 'percent',
                      withSign: true,
                    })}
                  </div>
                </div>
              </div>
              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-border/70 bg-muted/20 p-4">
                  <div className="text-xs font-medium text-muted-foreground">Market Cap</div>
                  <div className="mt-2 text-xl font-semibold text-foreground">
                    {formatMarketCap(spotlight.market_cap)}
                  </div>
                </div>
                <div className="rounded-lg border border-border/70 bg-muted/20 p-4">
                  <div className="text-xs font-medium text-muted-foreground">Volume</div>
                  <div className="mt-2 text-xl font-semibold text-foreground">
                    {formatVolume(spotlight.volume)}
                  </div>
                </div>
                <div className="rounded-lg border border-border/70 bg-muted/20 p-4">
                  <div className="text-xs font-medium text-muted-foreground">Sector</div>
                  <div className="mt-2 text-xl font-semibold text-foreground">
                    {spotlight.sector || 'N/A'}
                  </div>
                </div>
              </div>
              <div className="mt-6">
                <Link
                  href={`/stocks/${spotlight.ticker}`}
                  className="deco-link inline-flex items-center gap-2 text-sm font-medium"
                >
                  Open detail page <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </section>
        ) : null}

        <div className="mt-8 grid gap-6 xl:grid-cols-3">
          <MarketList title="Top Gainers" subtitle="Momentum Up" stocks={topGainers} tone="up" />
          <MarketList title="Top Losers" subtitle="Pressure Down" stocks={topLosers} tone="down" />
          <MarketList title="Most Active" subtitle="Liquidity Flow" stocks={mostActive} tone="neutral" />
        </div>
      </div>
    </div>
  );
}
