'use client';

import { useQuery } from '@tanstack/react-query';
import { stocksAPI } from '@/lib/api';
import TradingViewChart from '@/components/stock/TradingViewChart';
import StockMetrics from '@/components/stock/StockMetrics';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, TrendingUp, TrendingDown, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { formatCurrency, formatMarketCap, getChangeColor } from '@/lib/utils';

// FIX: Remove 'Promise' and 'use' - Next.js 14 passes params directly
interface PageProps {
  params: { ticker: string };
}

export default function StockDetailPage({ params }: PageProps) {
  // FIX: Access ticker directly from params (no resolvedParams needed)
  const ticker = params.ticker.toUpperCase();

  // Fetch stock data
  const { data: stock, isLoading: stockLoading } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => stocksAPI.getStock(ticker),
  });

  if (stockLoading) {
    return (
      <div className="container py-8">
        <div className="terminal-border bg-card p-12 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-xs text-muted-foreground">LOADING_STOCK_DATA...</p>
        </div>
      </div>
    );
  }

  if (!stock) {
    return (
      <div className="container py-8">
        <div className="terminal-border bg-card p-12 text-center">
          <p className="text-destructive font-bold mb-2">ERROR: STOCK_NOT_FOUND</p>
          <p className="text-xs text-muted-foreground mb-6">
            Ticker [{ticker}] not indexed in database
          </p>
          <Link href="/screener">
            <button className="px-4 py-2 border border-primary text-primary hover:bg-primary/10 transition-colors">
              &lt; RETURN_TO_SCREENER
            </button>
          </Link>
        </div>
      </div>
    );
  }

  const changePercent = stock.day_change_percent || stock.change_percent;
  const isPositive = changePercent !== null && changePercent !== undefined && changePercent >= 0;

  return (
    <div className="container py-6 space-y-6">
      {/* Back Button */}
      <Link href="/screener">
        <button className="text-xs text-muted-foreground hover:text-primary transition-colors">
          &lt; BACK_TO_SCREENER
        </button>
      </Link>

      {/* Stock Header */}
      <div className="terminal-border bg-card p-8">
        <div className="flex items-start justify-between gap-8">
          <div className="flex-1">
            <div className="flex items-baseline gap-4 mb-3">
              <h1 className="text-5xl font-bold text-glow">{stock.ticker}</h1>
              <span className="text-xs text-muted-foreground tracking-wider">EQUITY_DATA</span>
            </div>
            <p className="text-xl text-foreground/90 mb-6 font-light">
              {stock.name}
            </p>
            <div className="flex gap-3 text-xs">
              {stock.sector && (
                <div className="px-3 py-1.5 border border-primary/50 bg-primary/5 text-primary rounded-sm">
                  SECTOR: {stock.sector}
                </div>
              )}
              {stock.industry && (
                <div className="px-3 py-1.5 border border-border bg-muted/20 text-muted-foreground rounded-sm">
                  INDUSTRY: {stock.industry}
                </div>
              )}
            </div>
          </div>

          <div className="text-right border-l border-border pl-8 min-w-[240px]">
            <div className="text-xs text-muted-foreground mb-3 tracking-wider">CURRENT_PRICE</div>
            <p className="text-5xl font-bold font-mono mb-2">
              ${stock.current_price?.toFixed(2) || 'N/A'}
            </p>
            {changePercent !== null && changePercent !== undefined && (
              <div className={`flex items-center justify-end gap-2 mt-4 mb-6 font-mono ${
                isPositive ? 'text-success' : 'text-destructive'
              }`}>
                {isPositive ? '▲' : '▼'}
                <span className="text-xl font-bold">
                  {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
                </span>
              </div>
            )}
            <div className="text-xs text-muted-foreground space-y-2 border-t border-border pt-4">
              <div className="flex justify-between gap-4">
                <span>MKT_CAP:</span>
                <span className="font-mono text-foreground/80">{formatMarketCap(stock.market_cap)}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span>VOLUME:</span>
                <span className="font-mono text-foreground/80">
                  {stock.volume ? (stock.volume / 1000000).toFixed(2) + 'M' : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Price Chart with TradingView */}
      <TradingViewChart ticker={ticker} />

      {/* Metrics */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <h2 className="text-lg font-bold text-glow">FUNDAMENTAL_METRICS</h2>
          <div className="flex-1 border-b border-border"></div>
        </div>
        <StockMetrics stock={stock} />
      </div>

      {/* Advanced Analysis Section */}
      <div className="terminal-border bg-card">
        <div className="border-b border-border px-4 py-2 bg-muted/20">
          <span className="text-xs font-bold">ADVANCED_ANALYSIS</span>
          <span className="ml-3 text-xs text-muted-foreground">[COMING_SOON]</span>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-xs text-muted-foreground">
            $ ./backtest --ticker={ticker} --strategy=&lt;STRATEGY_NAME&gt;
          </p>
          <p className="text-xs text-muted-foreground">
            $ ./ml-features --ticker={ticker} --indicators=all
          </p>
          <div className="flex gap-3 mt-6">
            <button
              disabled
              className="px-4 py-2 border border-border text-muted-foreground cursor-not-allowed opacity-50"
            >
              RUN_BACKTEST
            </button>
            <button
              disabled
              className="px-4 py-2 border border-border text-muted-foreground cursor-not-allowed opacity-50"
            >
              EXPORT_ML_DATA
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}