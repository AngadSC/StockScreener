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
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="container py-6 space-y-6">
      {/* Terminal Header */}
      <div className="border-b border-border pb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-glow">MARKET_TERMINAL v2.1.0</h1>
            <p className="text-xs text-muted-foreground mt-1">Real-time market data and analysis</p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <p>SESSION_START: {currentTime}</p>
            <p className="mt-1">MARKET_STATUS: <span className="text-primary">STREAMING</span></p>
          </div>
        </div>
      </div>

      {/* System Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="terminal-border bg-card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground">SYSTEM.STOCKS_DB</span>
            <Activity className="h-3 w-3 text-primary" />
          </div>
          <div className="text-3xl font-bold text-primary">8,247</div>
          <div className="text-xs text-muted-foreground mt-1">US Equities Tracked</div>
        </div>

        <div className="terminal-border bg-card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground">SYSTEM.INDICATORS</span>
            <Activity className="h-3 w-3 text-primary" />
          </div>
          <div className="text-3xl font-bold text-primary">23+</div>
          <div className="text-xs text-muted-foreground mt-1">Technical Indicators</div>
        </div>

        <div className="terminal-border bg-card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-muted-foreground">SYSTEM.HISTORY</span>
            <Activity className="h-3 w-3 text-primary" />
          </div>
          <div className="text-3xl font-bold text-primary">10Y</div>
          <div className="text-xs text-muted-foreground mt-1">Historical Data Depth</div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Gainers */}
        <div className="terminal-border bg-card">
          <div className="border-b border-border px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              <span className="text-xs font-bold">TOP_GAINERS</span>
            </div>
            <span className="text-xs text-muted-foreground">LIVE</span>
          </div>
          <div className="p-4">
            {gainers?.results.map((stock, idx) => (
              <Link
                key={stock.ticker}
                href={`/stocks/${stock.ticker}`}
                className="flex items-center justify-between py-2 border-b border-border/50 last:border-0 hover:bg-primary/5 transition-colors -mx-4 px-4"
              >
                <div>
                  <div className="text-sm font-bold">[{idx + 1}] {stock.ticker}</div>
                  <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                    {stock.name || stock.company_name || 'N/A'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm">${stock.current_price?.toFixed(2)}</div>
                  <div className="text-xs text-primary">
                    {stock.change_percent ? `+${stock.change_percent.toFixed(2)}%` : 'N/A'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Top Losers */}
        <div className="terminal-border bg-card">
          <div className="border-b border-border px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-destructive" />
              <span className="text-xs font-bold">TOP_LOSERS</span>
            </div>
            <span className="text-xs text-muted-foreground">LIVE</span>
          </div>
          <div className="p-4">
            {losers?.results.map((stock, idx) => (
              <Link
                key={stock.ticker}
                href={`/stocks/${stock.ticker}`}
                className="flex items-center justify-between py-2 border-b border-border/50 last:border-0 hover:bg-primary/5 transition-colors -mx-4 px-4"
              >
                <div>
                  <div className="text-sm font-bold">[{idx + 1}] {stock.ticker}</div>
                  <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                    {stock.name || stock.company_name || 'N/A'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm">${stock.current_price?.toFixed(2)}</div>
                  <div className="text-xs text-destructive">
                    {stock.change_percent ? `${stock.change_percent.toFixed(2)}%` : 'N/A'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Most Active */}
        <div className="terminal-border bg-card">
          <div className="border-b border-border px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              <span className="text-xs font-bold">MOST_ACTIVE</span>
            </div>
            <span className="text-xs text-muted-foreground">LIVE</span>
          </div>
          <div className="p-4">
            {active?.results.map((stock, idx) => (
              <Link
                key={stock.ticker}
                href={`/stocks/${stock.ticker}`}
                className="flex items-center justify-between py-2 border-b border-border/50 last:border-0 hover:bg-primary/5 transition-colors -mx-4 px-4"
              >
                <div>
                  <div className="text-sm font-bold">[{idx + 1}] {stock.ticker}</div>
                  <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                    {stock.name || stock.company_name || 'N/A'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm">${stock.current_price?.toFixed(2)}</div>
                  <div className="text-xs text-muted-foreground">
                    VOL: {stock.volume ? (stock.volume / 1000000).toFixed(1) + 'M' : 'N/A'}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="terminal-border bg-card p-6">
        <h2 className="text-lg font-bold mb-4 text-glow">QUICK_ACTIONS</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            href="/screener"
            className="flex items-center justify-between p-4 border border-border hover:border-primary hover:bg-primary/5 transition-all group"
          >
            <div>
              <div className="font-bold">LAUNCH_SCREENER</div>
              <div className="text-xs text-muted-foreground mt-1">
                Filter 8,000+ stocks with advanced criteria
              </div>
            </div>
            <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
          </Link>

          <Link
            href="/watchlist"
            className="flex items-center justify-between p-4 border border-border hover:border-primary hover:bg-primary/5 transition-all group"
          >
            <div>
              <div className="font-bold">VIEW_WATCHLIST</div>
              <div className="text-xs text-muted-foreground mt-1">
                Track your saved stocks and portfolios
              </div>
            </div>
            <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
          </Link>
        </div>
      </div>

      {/* Footer hint */}
      <div className="text-center text-xs text-muted-foreground py-4 border-t border-border">
        <p>Press <kbd className="px-2 py-1 border border-border">⌘K</kbd> to open command palette</p>
      </div>
    </div>
  );
}
