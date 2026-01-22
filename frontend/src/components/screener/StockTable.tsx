'use client';

import Link from 'next/link';
import { Stock } from '@/types/stock';
import { ArrowUp, ArrowDown, ChevronRight } from 'lucide-react';

interface StockTableProps {
  stocks: Stock[];
  isLoading?: boolean;
  onSort?: (field: string) => void;
}

export default function StockTable({ stocks, isLoading, onSort }: StockTableProps) {
  if (isLoading) {
    return (
      <div className="terminal-border bg-card">
        <div className="border-b border-border px-4 py-2">
          <span className="text-xs text-muted-foreground">LOADING_DATA...</span>
        </div>
        <div className="p-4 space-y-2">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-8 bg-muted/20 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (stocks.length === 0) {
    return (
      <div className="terminal-border bg-card p-8 text-center">
        <p className="text-muted-foreground mb-2">ERROR: NO_RESULTS_FOUND</p>
        <p className="text-xs text-muted-foreground">
          Adjust filter parameters and retry query
        </p>
      </div>
    );
  }

  const formatMarketCap = (value: number | null | undefined) => {
    if (!value) return 'N/A';
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
  };

  return (
    <div className="terminal-border bg-card overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-4 py-2 flex items-center justify-between bg-muted/20">
        <span className="text-xs font-bold">QUERY_RESULTS</span>
        <span className="text-xs text-muted-foreground">{stocks.length} RECORDS</span>
      </div>

      {/* Column Headers */}
      <div className="border-b border-border bg-background">
        <div className="grid grid-cols-12 gap-2 px-4 py-2 text-xs font-bold">
          <div className="col-span-1 text-muted-foreground">#</div>
          <div className="col-span-1">TICK</div>
          <div className="col-span-3">COMPANY_NAME</div>
          <div className="col-span-2 text-right">
            <button
              onClick={() => onSort?.('current_price')}
              className="hover:text-primary transition-colors"
            >
              PRICE <ArrowUp className="inline h-3 w-3" />
            </button>
          </div>
          <div className="col-span-1 text-right">CHG%</div>
          <div className="col-span-2 text-right">
            <button
              onClick={() => onSort?.('market_cap')}
              className="hover:text-primary transition-colors"
            >
              MKT_CAP <ArrowUp className="inline h-3 w-3" />
            </button>
          </div>
          <div className="col-span-1 text-right">P/E</div>
          <div className="col-span-1"></div>
        </div>
      </div>

      {/* Data Rows */}
      <div className="divide-y divide-border/50">
        {stocks.map((stock, idx) => {
          const changePercent = stock.day_change_percent || stock.change_percent;
          const isPositive = changePercent !== null && changePercent !== undefined && changePercent >= 0;

          return (
            <div
              key={stock.ticker}
              className="grid grid-cols-12 gap-2 px-4 py-3 text-sm hover:bg-primary/5 transition-colors"
            >
              {/* Line Number */}
              <div className="col-span-1 text-muted-foreground text-xs font-mono">
                {String(idx + 1).padStart(3, '0')}
              </div>

              {/* Ticker */}
              <div className="col-span-1 font-bold text-primary">
                {stock.ticker}
              </div>

              {/* Company Name */}
              <div className="col-span-3 truncate">
                {stock.name || stock.company_name || 'N/A'}
              </div>

              {/* Price */}
              <div className="col-span-2 text-right font-mono">
                {stock.current_price ? `$${stock.current_price.toFixed(2)}` : 'N/A'}
              </div>

              {/* Change % */}
              <div className={`col-span-1 text-right font-mono ${
                changePercent !== null && changePercent !== undefined
                  ? isPositive ? 'text-primary' : 'text-destructive'
                  : 'text-muted-foreground'
              }`}>
                {changePercent !== null && changePercent !== undefined
                  ? `${isPositive ? '+' : ''}${changePercent.toFixed(2)}%`
                  : 'N/A'
                }
              </div>

              {/* Market Cap */}
              <div className="col-span-2 text-right font-mono text-xs">
                {formatMarketCap(stock.market_cap)}
              </div>

              {/* P/E Ratio */}
              <div className="col-span-1 text-right font-mono text-xs">
                {stock.pe_ratio ? stock.pe_ratio.toFixed(1) : '--'}
              </div>

              {/* View Link */}
              <div className="col-span-1 text-right">
                <Link
                  href={`/stocks/${stock.ticker}`}
                  className="text-primary hover:text-primary/80 transition-colors inline-flex items-center"
                >
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="border-t border-border px-4 py-2 bg-muted/20 text-xs text-muted-foreground">
        END_OF_RECORDS [{stocks.length}]
      </div>
    </div>
  );
}
