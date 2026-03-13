'use client';

import Link from 'next/link';
import { Stock } from '@/types/stock';
import { formatMarketCap, formatPercent } from '@/lib/utils';
import { ArrowUp, ChevronRight } from 'lucide-react';

interface StockTableProps {
  stocks: Stock[];
  isLoading?: boolean;
  onSort?: (field: string) => void;
}

export default function StockTable({ stocks, isLoading, onSort }: StockTableProps) {
  if (isLoading) {
    return (
      <div className="deco-panel bg-card">
        <div className="border-b border-primary/12 px-4 py-3">
          <span className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Loading data...</span>
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
      <div className="deco-panel bg-card p-8 text-center">
        <p className="mb-2 text-muted-foreground">No results found.</p>
        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
          Adjust filters and run again
        </p>
      </div>
    );
  }

  return (
    <div className="deco-panel overflow-hidden bg-card">
      <div className="border-b border-primary/12 bg-muted/20 px-4 py-3 flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-[0.22em]">Results</span>
        <span className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{stocks.length} records</span>
      </div>

      <div className="border-b border-primary/10 bg-background/80">
        <div className="grid grid-cols-12 gap-2 px-4 py-3 text-[11px] font-bold uppercase tracking-[0.18em]">
          <div className="col-span-1 text-muted-foreground">#</div>
          <div className="col-span-1">Ticker</div>
          <div className="col-span-3">Company</div>
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
              Mkt Cap <ArrowUp className="inline h-3 w-3" />
            </button>
          </div>
          <div className="col-span-1 text-right">P/E</div>
          <div className="col-span-1"></div>
        </div>
      </div>

      <div className="divide-y divide-primary/10">
        {stocks.map((stock, idx) => {
          const changePercent = stock.day_change_percent ?? stock.change_percent;
          const isPositive = changePercent !== null && changePercent !== undefined && changePercent >= 0;

          return (
            <div
              key={stock.ticker}
              className="grid grid-cols-12 gap-2 px-4 py-4 text-sm transition-colors hover:bg-primary/5"
            >
              <div className="col-span-1 text-xs text-muted-foreground">
                {String(idx + 1).padStart(3, '0')}
              </div>

              <div className="col-span-1 font-display text-lg uppercase tracking-[0.14em] text-primary">
                <Link
                  href={`/stocks/${stock.ticker}`}
                  className="hover:underline underline-offset-4"
                >
                  {stock.ticker}
                </Link>
              </div>

              <div className="col-span-3 truncate">
                {stock.name || stock.company_name || 'N/A'}
              </div>

              <div className="col-span-2 text-right font-semibold">
                {stock.current_price !== null && stock.current_price !== undefined
                  ? `$${stock.current_price.toFixed(2)}`
                  : 'N/A'
                }
              </div>

              <div className={`col-span-1 text-right font-mono ${
                changePercent !== null && changePercent !== undefined
                  ? isPositive ? 'text-primary' : 'text-destructive'
                  : 'text-muted-foreground'
              }`}>
                {formatPercent(changePercent, { mode: 'auto', withSign: true })}
              </div>

              <div className="col-span-2 text-right text-xs">
                {formatMarketCap(stock.market_cap)}
              </div>

              <div className="col-span-1 text-right text-xs">
                {stock.pe_ratio ? stock.pe_ratio.toFixed(1) : '--'}
              </div>

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

      <div className="border-t border-primary/12 bg-muted/20 px-4 py-3 text-xs uppercase tracking-[0.22em] text-muted-foreground">
        End of records [{stocks.length}]
      </div>
    </div>
  );
}
