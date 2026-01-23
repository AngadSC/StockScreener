'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { screenerAPI } from '@/lib/api';
import { TrendingUp, TrendingDown, Activity, Search, Star } from 'lucide-react';

export default function HomePage() {
  // Fetch market movers
  const { data: gainers, isLoading: gainersLoading } = useQuery({
    queryKey: ['gainers'],
    queryFn: () => screenerAPI.screenStocks({
      limit: 10,
      sort_by: 'change_percent',
      sort_order: 'desc',
      min_price: 5,
      min_market_cap: 1000000000
    }),
  });

  const { data: losers, isLoading: losersLoading } = useQuery({
    queryKey: ['losers'],
    queryFn: () => screenerAPI.screenStocks({
      limit: 10,
      sort_by: 'change_percent',
      sort_order: 'asc',
      min_price: 5,
      min_market_cap: 1000000000
    }),
  });

  const { data: active, isLoading: activeLoading } = useQuery({
    queryKey: ['active'],
    queryFn: () => screenerAPI.screenStocks({
      limit: 10,
      sort_by: 'volume',
      sort_order: 'desc',
      min_market_cap: 1000000000
    }),
  });

  return (
    <div className="min-h-screen bg-background">
      <div className="container-custom py-8 space-y-8">
        {/* Hero Section */}
        <div className="space-y-2">
          <h1 className="text-4xl font-semibold">Market Overview</h1>
          <p className="text-muted-foreground text-lg">
            Track top movers, analyze trends, and discover opportunities
          </p>
        </div>

        {/* Market Movers Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Top Gainers */}
          <div className="card-elevated">
            <div className="p-6 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-success/10">
                  <TrendingUp className="h-5 w-5 text-success" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Top Gainers</h3>
                  <p className="text-sm text-muted-foreground">Biggest movers up today</p>
                </div>
              </div>
            </div>
            <div className="p-6">
              {gainersLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-16 bg-muted/30 rounded animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {gainers?.results.slice(0, 5).map((stock) => (
                    <Link
                      key={stock.ticker}
                      href={`/stocks/${stock.ticker}`}
                      className="block p-3 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-foreground">{stock.ticker}</div>
                          <div className="text-sm text-muted-foreground truncate">
                            {stock.name || stock.company_name || 'N/A'}
                          </div>
                        </div>
                        <div className="text-right ml-4">
                          <div className="font-semibold">
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
              )}
            </div>
          </div>

          {/* Top Losers */}
          <div className="card-elevated">
            <div className="p-6 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-destructive/10">
                  <TrendingDown className="h-5 w-5 text-destructive" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Top Losers</h3>
                  <p className="text-sm text-muted-foreground">Biggest declines today</p>
                </div>
              </div>
            </div>
            <div className="p-6">
              {losersLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-16 bg-muted/30 rounded animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {losers?.results.slice(0, 5).map((stock) => (
                    <Link
                      key={stock.ticker}
                      href={`/stocks/${stock.ticker}`}
                      className="block p-3 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-foreground">{stock.ticker}</div>
                          <div className="text-sm text-muted-foreground truncate">
                            {stock.name || stock.company_name || 'N/A'}
                          </div>
                        </div>
                        <div className="text-right ml-4">
                          <div className="font-semibold">
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
              )}
            </div>
          </div>

          {/* Most Active */}
          <div className="card-elevated">
            <div className="p-6 border-b border-border">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Activity className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">Most Active</h3>
                  <p className="text-sm text-muted-foreground">Highest volume today</p>
                </div>
              </div>
            </div>
            <div className="p-6">
              {activeLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-16 bg-muted/30 rounded animate-pulse" />
                  ))}
                </div>
              ) : (
                <div className="space-y-3">
                  {active?.results.slice(0, 5).map((stock) => (
                    <Link
                      key={stock.ticker}
                      href={`/stocks/${stock.ticker}`}
                      className="block p-3 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-foreground">{stock.ticker}</div>
                          <div className="text-sm text-muted-foreground truncate">
                            {stock.name || stock.company_name || 'N/A'}
                          </div>
                        </div>
                        <div className="text-right ml-4">
                          <div className="font-semibold">
                            ${stock.current_price?.toFixed(2)}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {stock.volume ? `${(stock.volume / 1000000).toFixed(1)}M vol` : 'N/A'}
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Quick Access Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          <Link href="/screener" className="card-elevated card-hover p-8 group">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-2xl font-semibold mb-2">Stock Screener</h3>
                <p className="text-muted-foreground">
                  Filter and analyze 8,000+ stocks with advanced screening tools
                </p>
              </div>
              <Search className="h-8 w-8 text-primary group-hover:scale-110 transition-transform" />
            </div>
          </Link>

          <Link href="/watchlist" className="card-elevated card-hover p-8 group">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-2xl font-semibold mb-2">Watchlist</h3>
                <p className="text-muted-foreground">
                  Track and monitor your favorite stocks in one place
                </p>
              </div>
              <Star className="h-8 w-8 text-primary group-hover:scale-110 transition-transform" />
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
