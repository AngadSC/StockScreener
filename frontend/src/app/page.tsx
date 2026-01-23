'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { screenerAPI } from '@/lib/api';
import { TrendingUp, TrendingDown, Activity, ArrowRight } from 'lucide-react';

export default function HomePage() {
  const [currentTime, setCurrentTime] = useState('');

  // Fetch top gainers
  const { data: gainers } = useQuery({
    queryKey: ['gainers'],
    queryFn: () => screenerAPI.screenStocks({
      limit: 5,
      sort_by: 'change_percent',
      sort_order: 'desc',
      min_price: 5,
      min_market_cap: 1000000000
    }),
  });

  // Fetch top losers
  const { data: losers } = useQuery({
    queryKey: ['losers'],
    queryFn: () => screenerAPI.screenStocks({
      limit: 5,
      sort_by: 'change_percent',
      sort_order: 'asc',
      min_price: 5,
      min_market_cap: 1000000000
    }),
  });

  // Fetch most active (by volume)
  const { data: active } = useQuery({
    queryKey: ['active'],
    queryFn: () => screenerAPI.screenStocks({
      limit: 5,
      sort_by: 'volume',
      sort_order: 'desc',
      min_market_cap: 1000000000
    }),
  });

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container-wide py-10 space-y-10">
      {/* Header */}
      <div className="space-y-3">
        <h1 className="text-5xl font-bold">Market Dashboard</h1>
        <p className="text-muted-foreground text-xl">{currentTime} · Live Data</p>
      </div>

      {/* System Stats */}
      <div className="grid grid-cols-3 gap-6">
        <div className="terminal-border card-elevated p-6 hover:scale-105 transition-transform">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-lg bg-primary/10">
              <Activity className="h-6 w-6 text-primary" />
            </div>
            <span className="text-muted-foreground">Stocks</span>
          </div>
          <div className="text-4xl font-bold font-mono">8,247</div>
        </div>

        <div className="terminal-border card-elevated p-6 hover:scale-105 transition-transform">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-lg bg-primary/10">
              <Activity className="h-6 w-6 text-primary" />
            </div>
            <span className="text-muted-foreground">Indicators</span>
          </div>
          <div className="text-4xl font-bold font-mono">23+</div>
        </div>

        <div className="terminal-border card-elevated p-6 hover:scale-105 transition-transform">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 rounded-lg bg-primary/10">
              <Activity className="h-6 w-6 text-primary" />
            </div>
            <span className="text-muted-foreground">History</span>
          </div>
          <div className="text-4xl font-bold font-mono">10Y</div>
        </div>
      </div>

      {/* Market Movers */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Top Gainers */}
        <div className="terminal-border card-elevated">
          <div className="bg-success/5 border-b border-border px-6 py-4">
            <div className="flex items-center gap-3">
              <TrendingUp className="h-5 w-5 text-success" />
              <div>
                <h3 className="font-bold text-lg">Top Gainers</h3>
                <p className="text-xs text-muted-foreground">Biggest movers today</p>
              </div>
            </div>
          </div>
          <div className="p-6 space-y-4">
            {gainers?.results.map((stock) => (
              <Link
                key={stock.ticker}
                href={`/stocks/${stock.ticker}`}
                className="block p-4 rounded-lg border border-transparent hover:border-success hover:bg-success/5 card-hover"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono font-bold text-lg text-primary mb-1">
                      {stock.ticker}
                    </div>
                    <div className="text-sm text-muted-foreground truncate">
                      {stock.name || stock.company_name || 'N/A'}
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className="font-mono font-bold text-lg">
                      ${stock.current_price?.toFixed(2)}
                    </div>
                    <div className="text-sm font-medium text-success">
                      +{stock.change_percent?.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Top Losers */}
        <div className="terminal-border card-elevated">
          <div className="bg-destructive/5 border-b border-border px-6 py-4">
            <div className="flex items-center gap-3">
              <TrendingDown className="h-5 w-5 text-destructive" />
              <div>
                <h3 className="font-bold text-lg">Top Losers</h3>
                <p className="text-xs text-muted-foreground">Biggest declines today</p>
              </div>
            </div>
          </div>
          <div className="p-6 space-y-4">
            {losers?.results.map((stock) => (
              <Link
                key={stock.ticker}
                href={`/stocks/${stock.ticker}`}
                className="block p-4 rounded-lg border border-transparent hover:border-destructive hover:bg-destructive/5 card-hover"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono font-bold text-lg text-primary mb-1">
                      {stock.ticker}
                    </div>
                    <div className="text-sm text-muted-foreground truncate">
                      {stock.name || stock.company_name || 'N/A'}
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className="font-mono font-bold text-lg">
                      ${stock.current_price?.toFixed(2)}
                    </div>
                    <div className="text-sm font-medium text-destructive">
                      {stock.change_percent?.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Most Active */}
        <div className="terminal-border card-elevated">
          <div className="bg-primary/5 border-b border-border px-6 py-4">
            <div className="flex items-center gap-3">
              <Activity className="h-5 w-5 text-primary" />
              <div>
                <h3 className="font-bold text-lg">Most Active</h3>
                <p className="text-xs text-muted-foreground">Highest volume today</p>
              </div>
            </div>
          </div>
          <div className="p-6 space-y-4">
            {active?.results.map((stock) => (
              <Link
                key={stock.ticker}
                href={`/stocks/${stock.ticker}`}
                className="block p-4 rounded-lg border border-transparent hover:border-primary hover:bg-primary/5 card-hover"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-mono font-bold text-lg text-primary mb-1">
                      {stock.ticker}
                    </div>
                    <div className="text-sm text-muted-foreground truncate">
                      {stock.name || stock.company_name || 'N/A'}
                    </div>
                  </div>
                  <div className="text-right ml-4">
                    <div className="font-mono font-bold text-lg">
                      ${stock.current_price?.toFixed(2)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {stock.volume ? `${(stock.volume / 1000000).toFixed(1)}M vol` : 'N/A'}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link
          href="/screener"
          className="terminal-border card-elevated p-8 card-hover group"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-2xl font-bold">Stock Screener</h3>
            <ArrowRight className="h-7 w-7 text-primary group-hover:translate-x-2 transition-transform" />
          </div>
          <p className="text-muted-foreground">
            Filter through 8,000+ stocks with advanced criteria and metrics
          </p>
        </Link>

        <Link
          href="/watchlist"
          className="terminal-border card-elevated p-8 card-hover group"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-2xl font-bold">Watchlist</h3>
            <ArrowRight className="h-7 w-7 text-primary group-hover:translate-x-2 transition-transform" />
          </div>
          <p className="text-muted-foreground">
            Track your favorite stocks and monitor portfolio performance
          </p>
        </Link>
      </div>
    </div>
  );
}
