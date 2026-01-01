'use client';

import { use } from 'react';
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

export default function StockDetailPage({ params }: { params: Promise<{ ticker: string }> }) {
  const resolvedParams = use(params);
  const ticker = resolvedParams.ticker.toUpperCase();

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
      <div className="container py-8 flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!stock) {
    return (
      <div className="container py-8">
        <Card>
          <CardContent className="py-12 text-center">
            <h2 className="text-2xl font-bold mb-2">Stock Not Found</h2>
            <p className="text-muted-foreground mb-4">
              {ticker} is not in our database
            </p>
            <Link href="/screener">
              <Button>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Screener
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container py-8 space-y-8">
      {/* Header */}
      <div>
        <Link href="/screener">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Screener
          </Button>
        </Link>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-4xl font-bold mb-2">
              {stock.ticker}
            </h1>
            <p className="text-xl text-muted-foreground mb-4">
              {stock.name}
            </p>
            <div className="flex gap-2">
              {stock.sector && <Badge variant="secondary">{stock.sector}</Badge>}
              {stock.industry && <Badge variant="outline">{stock.industry}</Badge>}
            </div>
          </div>

          <div className="text-right">
            <p className="text-3xl font-bold">
              {formatCurrency(stock.current_price)}
            </p>
            {stock.day_change_percent !== null && (
              <div className={`flex items-center justify-end gap-1 mt-2 ${getChangeColor(stock.day_change_percent)}`}>
                {stock.day_change_percent >= 0 ? (
                  <TrendingUp className="h-5 w-5" />
                ) : (
                  <TrendingDown className="h-5 w-5" />
                )}
                <span className="text-lg font-semibold">
                  {stock.day_change_percent >= 0 ? '+' : ''}
                  {stock.day_change_percent.toFixed(2)}%
                </span>
              </div>
            )}
            <p className="text-sm text-muted-foreground mt-2">
              Market Cap: {formatMarketCap(stock.market_cap)}
            </p>
          </div>
        </div>
      </div>

      {/* Price Chart */}
      {priceLoading ? (
        <Card>
          <CardContent className="py-12 flex items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </CardContent>
        </Card>
      ) : priceData && priceData.data.length > 0 ? (
        <StockChart data={priceData.data} ticker={ticker} />
      ) : null}

      {/* Metrics */}
      <div>
        <h2 className="text-2xl font-bold mb-6">Fundamentals</h2>
        <StockMetrics stock={stock} />
      </div>

      {/* Backtest Section */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Analysis</CardTitle>
          <CardDescription>
            Access backtesting data and ML features for {ticker}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Coming soon: Backtest trading strategies and access ML-ready datasets
          </p>
          <div className="flex gap-4">
            <Button disabled>Backtest Strategy</Button>
            <Button variant="outline" disabled>Get ML Features</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
