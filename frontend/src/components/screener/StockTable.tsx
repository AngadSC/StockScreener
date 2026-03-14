'use client';

import Link from 'next/link';
import { ArrowUp, ChevronLeft, ChevronRight } from 'lucide-react';

import type { Stock } from '@/types/stock';
import { formatMarketCap, formatPercent } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface StockTableProps {
  stocks: Stock[];
  isLoading?: boolean;
  onSort?: (field: string) => void;
  page?: number;
  totalPages?: number;
  total?: number;
  perPage?: number;
  onPageChange?: (page: number) => void;
}

function buildPages(currentPage: number, totalPages: number) {
  const pages = new Set<number>([1, totalPages, currentPage - 1, currentPage, currentPage + 1]);
  return Array.from(pages).filter((page) => page >= 1 && page <= totalPages).sort((a, b) => a - b);
}

export default function StockTable({
  stocks,
  isLoading,
  onSort,
  page = 1,
  totalPages = 1,
  total = stocks.length,
  perPage = stocks.length,
  onPageChange,
}: StockTableProps) {
  if (isLoading) {
    return (
      <div className="deco-panel bg-card">
        <div className="border-b border-border/70 px-4 py-3">
          <span className="text-xs font-medium text-muted-foreground">Loading data...</span>
        </div>
        <div className="space-y-2 p-4">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-8 animate-pulse rounded-md bg-muted/30" />
          ))}
        </div>
      </div>
    );
  }

  if (stocks.length === 0) {
    return (
      <div className="deco-panel bg-card p-8 text-center">
        <p className="mb-2 text-muted-foreground">No results found.</p>
        <p className="text-xs text-muted-foreground">Adjust your filters and try again.</p>
      </div>
    );
  }

  const startIndex = total === 0 ? 0 : (page - 1) * perPage + 1;
  const endIndex = Math.min(page * perPage, total);
  const pages = buildPages(page, totalPages);

  return (
    <div className="deco-panel overflow-hidden bg-card">
      <div className="flex items-center justify-between border-b border-border/70 bg-muted/20 px-4 py-3">
        <span className="text-sm font-semibold">Results</span>
        <span className="text-xs text-muted-foreground">
          Showing {startIndex}-{endIndex} of {total.toLocaleString()}
        </span>
      </div>

      <div className="border-b border-border/70 bg-background/80">
        <div className="grid grid-cols-12 gap-2 px-4 py-3 text-xs font-medium text-muted-foreground">
          <div className="col-span-1">#</div>
          <div className="col-span-1">Ticker</div>
          <div className="col-span-3">Company</div>
          <div className="col-span-2 text-right">
            <button onClick={() => onSort?.('current_price')} className="inline-flex items-center gap-1 hover:text-primary">
              Price <ArrowUp className="h-3 w-3" />
            </button>
          </div>
          <div className="col-span-1 text-right">Chg%</div>
          <div className="col-span-2 text-right">
            <button onClick={() => onSort?.('market_cap')} className="inline-flex items-center gap-1 hover:text-primary">
              Market Cap <ArrowUp className="h-3 w-3" />
            </button>
          </div>
          <div className="col-span-1 text-right">P/E</div>
          <div className="col-span-1" />
        </div>
      </div>

      <div className="divide-y divide-border/70">
        {stocks.map((stock, idx) => {
          const changePercent = stock.day_change_percent ?? stock.change_percent;
          const isPositive =
            changePercent !== null && changePercent !== undefined && changePercent >= 0;

          return (
            <div
              key={stock.ticker}
              className="grid grid-cols-12 gap-2 px-4 py-4 text-sm transition-[background,border-color,box-shadow,color,transform] duration-[180ms] hover:bg-[var(--accent-subtle)]"
            >
              <div className="col-span-1 text-xs text-muted-foreground tabular-nums">
                {String(startIndex + idx).padStart(3, '0')}
              </div>

              <div className="col-span-1 text-lg font-semibold text-primary">
                <Link href={`/stocks/${stock.ticker}`} className="hover:underline underline-offset-4">
                  {stock.ticker}
                </Link>
              </div>

              <div className="col-span-3 truncate">{stock.name || stock.company_name || 'N/A'}</div>

              <div className="col-span-2 text-right font-semibold tabular-nums">
                {stock.current_price !== null && stock.current_price !== undefined
                  ? `$${stock.current_price.toFixed(2)}`
                  : 'N/A'}
              </div>

              <div
                className={`col-span-1 text-right tabular-nums ${
                  changePercent !== null && changePercent !== undefined
                    ? isPositive
                      ? 'text-positive'
                      : 'text-negative'
                    : 'text-muted-foreground'
                }`}
              >
                {formatPercent(changePercent, { mode: 'auto', withSign: true })}
              </div>

              <div className="col-span-2 text-right text-xs tabular-nums">
                {formatMarketCap(stock.market_cap)}
              </div>

              <div className="col-span-1 text-right text-xs tabular-nums">
                {stock.pe_ratio ? stock.pe_ratio.toFixed(1) : '--'}
              </div>

              <div className="col-span-1 text-right">
                <Link
                  href={`/stocks/${stock.ticker}`}
                  className="inline-flex items-center text-primary transition-colors hover:text-primary/80"
                >
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {totalPages > 1 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/70 bg-muted/20 px-4 py-3">
          <div className="text-xs text-muted-foreground">
            Page {page} of {totalPages}
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onPageChange?.(page - 1)}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            {pages.map((pageNumber) => (
              <Button
                key={pageNumber}
                type="button"
                variant={pageNumber === page ? 'default' : 'ghost'}
                size="sm"
                onClick={() => onPageChange?.(pageNumber)}
              >
                {pageNumber}
              </Button>
            ))}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => onPageChange?.(page + 1)}
              disabled={page >= totalPages}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
