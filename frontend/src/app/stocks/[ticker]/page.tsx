'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';

import StockMetrics from '@/components/stock/StockMetrics';
import TradingViewChart from '@/components/stock/TradingViewChart';
import { Button } from '@/components/ui/button';
import { stocksAPI } from '@/lib/api';
import { formatMarketCap, formatPercent, formatVolume, normalizePercentValue } from '@/lib/utils';

interface PageProps {
  params: { ticker: string };
}

export default function StockDetailPage({ params }: PageProps) {
  const ticker = params.ticker.toUpperCase();

  const { data: stock, isLoading: stockLoading } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => stocksAPI.getStock(ticker),
  });

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
          <Link href="/screener">
            <Button variant="outline">Return to Screener</Button>
          </Link>
        </div>
      </div>
    );
  }

  const rawChangePercent = stock.day_change_percent ?? stock.change_percent;
  const changePercent = normalizePercentValue(rawChangePercent, 'auto');
  const isPositive = changePercent !== null && changePercent >= 0;

  return (
    <div className="container-custom space-y-6 py-8">
      <Link
        href="/screener"
        className="inline-flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to Screener
      </Link>

      <section className="deco-panel p-8">
        <div className="grid gap-8 xl:grid-cols-[1.15fr_0.85fr]">
          <div>
            <div className="deco-kicker">Stock profile</div>
            <div className="mt-3 flex flex-wrap items-end gap-4">
              <h1>{stock.ticker}</h1>
              <div className="text-sm font-medium text-primary">{stock.sector || 'Equity'}</div>
            </div>
            <p className="mt-3 text-xl text-foreground/90">{stock.name}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {stock.sector ? <span className="deco-chip">{stock.sector}</span> : null}
              {stock.industry ? <span className="deco-chip">{stock.industry}</span> : null}
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href={`/backtester?tickers=${ticker}`}>
                <Button>Launch Backtester</Button>
              </Link>
              <Link href={`/backtester?tickers=${ticker}`}>
                <Button variant="outline">
                  Compare
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <div className="deco-panel p-6">
              <div className="text-xs font-medium text-muted-foreground">Current Price</div>
              <div className="mt-3 text-5xl font-semibold text-foreground tabular-nums">
                {stock.current_price != null ? `$${stock.current_price.toFixed(2)}` : 'N/A'}
              </div>
              {changePercent !== null ? (
                <div className={isPositive ? 'mt-3 text-sm text-positive' : 'mt-3 text-sm text-negative'}>
                  {formatPercent(changePercent, { mode: 'percent', withSign: true })}
                </div>
              ) : null}
            </div>
            <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-3">
              <div className="rounded-lg border border-border/70 bg-muted/20 p-4">
                <div className="text-xs font-medium text-muted-foreground">Market Cap</div>
                <div className="mt-2 text-lg font-semibold text-foreground">
                  {formatMarketCap(stock.market_cap)}
                </div>
              </div>
              <div className="rounded-lg border border-border/70 bg-muted/20 p-4">
                <div className="text-xs font-medium text-muted-foreground">Volume</div>
                <div className="mt-2 text-lg font-semibold text-foreground">
                  {formatVolume(stock.volume)}
                </div>
              </div>
              <div className="rounded-lg border border-border/70 bg-muted/20 p-4">
                <div className="text-xs font-medium text-muted-foreground">Beta</div>
                <div className="mt-2 text-lg font-semibold text-foreground tabular-nums">
                  {stock.beta != null ? stock.beta.toFixed(2) : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <TradingViewChart ticker={ticker} />

      <section className="deco-panel p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="deco-kicker">Fundamentals</div>
            <h2 className="mt-2">Core Metrics</h2>
          </div>
          <Link href={`/backtester?tickers=${ticker}`} className="deco-link text-sm font-medium">
            Backtest This Stock
          </Link>
        </div>
        <div className="deco-divider" />
        <StockMetrics stock={stock} />
      </section>
    </div>
  );
}
