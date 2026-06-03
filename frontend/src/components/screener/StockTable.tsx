'use client';

import { useRouter } from 'next/navigation';
import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, SearchX } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { formatMarketCap, formatPercent } from '@/lib/utils';
import type { Stock } from '@/types/stock';

interface StockTableProps {
  stocks: Stock[];
  isLoading?: boolean;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (field: string) => void;
  page?: number;
  totalPages?: number;
  total?: number;
  perPage?: number;
  onPageChange?: (page: number) => void;
  onResetFilters?: () => void;
}

interface SortableColumnProps {
  field: string;
  label: string;
  align?: 'left' | 'right';
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort?: (field: string) => void;
}

function buildPages(currentPage: number, totalPages: number) {
  if (totalPages <= 1) return [1];

  const pages = new Set<number>([1, totalPages]);
  for (let value = currentPage - 1; value <= currentPage + 1; value += 1) {
    if (value >= 1 && value <= totalPages) pages.add(value);
  }

  return Array.from(pages).sort((a, b) => a - b);
}

function SortableColumn({
  field,
  label,
  align = 'left',
  sortBy,
  sortOrder,
  onSort,
}: SortableColumnProps) {
  const isActive = sortBy === field;
  const justifyClass = align === 'right' ? 'justify-end text-right' : 'justify-start text-left';

  return (
    <th className={align === 'right' ? 'text-right' : 'text-left'}>
      <button
        type="button"
        onClick={() => onSort?.(field)}
        className={`inline-flex w-full items-center gap-2 ${justifyClass} transition-colors hover:text-[var(--text-primary)]`}
      >
        <span>{label}</span>
        <span className="flex flex-col leading-none">
          <ChevronUp
            className={`h-3 w-3 ${isActive && sortOrder === 'asc' ? 'text-[var(--accent)]' : 'text-[var(--text-tertiary)]'}`}
          />
          <ChevronDown
            className={`-mt-1 h-3 w-3 ${isActive && sortOrder === 'desc' ? 'text-[var(--accent)]' : 'text-[var(--text-tertiary)]'}`}
          />
        </span>
      </button>
    </th>
  );
}

function SkeletonRows() {
  return (
    <tbody>
      {Array.from({ length: 8 }).map((_, index) => (
        <tr key={index} className="border-b border-[var(--border-subtle)] last:border-b-0">
          <td className="px-4 py-3">
            <div className="screener-skeleton h-4 w-14 rounded-full" />
          </td>
          <td className="px-4 py-3">
            <div className="screener-skeleton h-4 w-40 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-4 w-20 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-6 w-16 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-4 w-24 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-4 w-12 rounded-full" />
          </td>
          <td className="px-4 py-3 text-right">
            <div className="screener-skeleton ml-auto h-10 w-10 rounded-full" />
          </td>
        </tr>
      ))}
    </tbody>
  );
}

function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange?: (page: number) => void;
}) {
  const pages = buildPages(page, totalPages);

  return (
    <div className="flex flex-wrap items-center justify-center gap-2 px-4 py-4 text-sm">
      <button
        type="button"
        onClick={() => onPageChange?.(page - 1)}
        disabled={page <= 1}
        className="inline-flex items-center gap-1 text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:text-[var(--text-tertiary)]"
      >
        <ChevronLeft className="h-4 w-4" />
        Previous
      </button>

      {pages.map((pageNumber, index) => {
        const previous = pages[index - 1];
        const showEllipsis = previous !== undefined && pageNumber - previous > 1;

        return (
          <div key={pageNumber} className="flex items-center gap-2">
            {showEllipsis ? <span className="text-[var(--text-tertiary)]">...</span> : null}
            <button
              type="button"
              onClick={() => onPageChange?.(pageNumber)}
              className={`min-w-[2rem] text-center transition-colors ${
                pageNumber === page
                  ? 'font-semibold text-[var(--accent)]'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              [{pageNumber}]
            </button>
          </div>
        );
      })}

      <button
        type="button"
        onClick={() => onPageChange?.(page + 1)}
        disabled={page >= totalPages}
        className="inline-flex items-center gap-1 text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:text-[var(--text-tertiary)]"
      >
        Next
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function StockTable({
  stocks,
  isLoading,
  sortBy,
  sortOrder,
  onSort,
  page = 1,
  totalPages = 1,
  total = stocks.length,
  perPage = stocks.length,
  onPageChange,
  onResetFilters,
}: StockTableProps) {
  const router = useRouter();

  const startIndex = total === 0 ? 0 : (page - 1) * perPage + 1;
  const endIndex = Math.min(page * perPage, total);

  if (!isLoading && stocks.length === 0) {
    return (
      <div className="deco-panel flex min-h-[520px] items-center justify-center bg-[var(--bg-surface-1)] p-8">
        <div className="max-w-sm text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-2)] text-[var(--text-secondary)]">
            <SearchX className="h-7 w-7" />
          </div>
          <h2 className="mt-5 text-2xl font-semibold text-[var(--text-primary)]">No results found</h2>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Try adjusting your filters or broadening your search.
          </p>
          <div className="mt-6">
            <Button type="button" variant="secondary" onClick={onResetFilters}>
              Reset filters
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="deco-panel hud overflow-hidden bg-[var(--bg-surface-1)]">
      <span className="hud-c1" />
      <span className="hud-c2" />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--line)] bg-[var(--bg-surface-1)] px-5 py-4">
        <div>
          <h2 className="heading-md text-[var(--text-primary)]">Results</h2>
          <p className="smallcap-low mt-1">
            {total > 0 ? `Showing ${startIndex}-${endIndex} of ${total.toLocaleString()}` : 'Scanning the market'}
          </p>
        </div>
        <div className="live-dot">
          {isLoading ? (
            'Updating'
          ) : (
            'Live'
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table>
          <thead className="bg-[var(--bg-surface-2)]">
            <tr className="border-b border-[var(--border-default)] text-xs font-medium text-[var(--text-secondary)]">
              <th className="px-4 py-3 text-left">Ticker</th>
              <th className="px-4 py-3 text-left">Company</th>
              <SortableColumn
                field="current_price"
                label="Price"
                align="right"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortableColumn
                field="day_change_percent"
                label="Chg%"
                align="right"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortableColumn
                field="market_cap"
                label="Market Cap"
                align="right"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <SortableColumn
                field="pe_ratio"
                label="P/E"
                align="right"
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={onSort}
              />
              <th className="w-16 px-4 py-3 text-right" />
            </tr>
          </thead>

          {isLoading ? (
            <SkeletonRows />
          ) : (
            <tbody>
              {stocks.map((stock) => {
                const changePercent = stock.day_change_percent ?? stock.change_percent;
                const isPositive =
                  changePercent !== null && changePercent !== undefined && changePercent >= 0;
                const companyName = stock.name || stock.company_name || 'N/A';

                return (
                  <tr
                    key={stock.ticker}
                    tabIndex={0}
                    onClick={() => router.push(`/stocks/${stock.ticker}`)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        router.push(`/stocks/${stock.ticker}`);
                      }
                    }}
                    className="group row-hover cursor-pointer border-b border-[var(--border-subtle)] text-sm focus-visible:bg-[var(--bg-surface-2)] focus-visible:outline-none"
                  >
                    <td className="serif-num px-4 py-3 text-base text-[var(--text-primary)]">
                      {stock.ticker}
                    </td>
                    <td
                      title={companyName}
                      className="max-w-[320px] truncate px-4 py-3 text-[var(--text-secondary)]"
                    >
                      {companyName}
                    </td>
                    <td className="serif-num px-4 py-3 text-right text-[17px] text-[var(--text-primary)]">
                      {stock.current_price !== null && stock.current_price !== undefined
                        ? `$${stock.current_price.toFixed(2)}`
                        : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {changePercent !== null && changePercent !== undefined ? (
                        <span
                          className={`chip tabular-nums ${
                            isPositive
                              ? 'chip-up'
                              : 'chip-dn'
                          }`}
                        >
                          {formatPercent(changePercent, { mode: 'auto', withSign: true })}
                        </span>
                      ) : (
                        <span className="tabular-nums text-[var(--text-secondary)]">N/A</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--text-secondary)]">
                      {formatMarketCap(stock.market_cap)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-[var(--text-secondary)]">
                      {stock.pe_ratio !== null && stock.pe_ratio !== undefined
                        ? stock.pe_ratio.toFixed(1)
                        : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-transparent bg-[var(--bg-surface-2)] text-[var(--text-secondary)] transition-transform duration-150 group-hover:translate-x-1 group-hover:text-[var(--accent)]">
                        <ChevronRight className="h-5 w-5" />
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          )}
        </table>
      </div>

      {totalPages > 1 && !isLoading ? (
        <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-surface-1)]">
          <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
        </div>
      ) : null}
    </div>
  );
}
