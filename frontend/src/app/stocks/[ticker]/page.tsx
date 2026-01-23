'use client';

import { useQuery } from '@tanstack/react-query';
import { stocksAPI } from '@/lib/api';
import StockChart from '@/components/stock/StockChart';
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

  // Fetch price history
  const { data: priceData, isLoading: priceLoading } = useQuery({
    queryKey: ['prices', ticker],
    queryFn: () => stocksAPI.getPriceHistory(ticker, '1y'),
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
      <div className="terminal-border bg-card p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-baseline gap-4 mb-2">
              <h1 className="text-4xl font-bold text-glow">{stock.ticker}</h1>
              <span className="text-xs text-muted-foreground">EQUITY_DATA</span>
            </div>
            <p className="text-lg text-muted-foreground mb-4">
              {stock.name}
            </p>
            <div className="flex gap-3 text-xs">
              {stock.sector && (
                <div className="px-2 py-1 border border-primary/50 text-primary">
                  SECTOR: {stock.sector}
                </div>
              )}
              {stock.industry && (
                <div className="px-2 py-1 border border-border text-muted-foreground">
                  INDUSTRY: {stock.industry}
                </div>
              )}
            </div>
          </div>

          <div className="text-right border-l border-border pl-6">
            <div className="text-xs text-muted-foreground mb-2">CURRENT_PRICE</div>
            <p className="text-4xl font-bold font-mono">
              ${stock.current_price?.toFixed(2) || 'N/A'}
            </p>
            {changePercent !== null && changePercent !== undefined && (
              <div className={`flex items-center justify-end gap-2 mt-3 font-mono ${
                isPositive ? 'text-primary' : 'text-destructive'
              }`}>
                {isPositive ? '▲' : '▼'}
                <span className="text-lg font-bold">
                  {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
                </span>
              </div>
            )}
            <div className="text-xs text-muted-foreground mt-3 space-y-1">
              <p>MKT_CAP: {formatMarketCap(stock.market_cap)}</p>
              <p>VOLUME: {stock.volume ? (stock.volume / 1000000).toFixed(2) + 'M' : 'N/A'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Price Chart */}
      {priceLoading ? (
        <div className="terminal-border bg-card p-12 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-xs text-muted-foreground">LOADING_PRICE_HISTORY...</p>
        </div>
      ) : priceData && priceData.data.length > 0 ? (
        <StockChart data={priceData.data} ticker={ticker} />
      ) : (
        <div className="terminal-border bg-card p-8 text-center">
          <p className="text-xs text-muted-foreground">NO_PRICE_DATA_AVAILABLE</p>
        </div>
      )}

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