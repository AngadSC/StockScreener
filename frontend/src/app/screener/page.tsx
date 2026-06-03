'use client';

import { Suspense, useDeferredValue, useEffect, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { BarChart3, Columns3 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

import FilterPanel from '@/components/screener/FilterPanel';
import StockTable from '@/components/screener/StockTable';
import { screenerAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { ScreenerFilters } from '@/types/stock';

function getDefaultFilters(search?: string): ScreenerFilters {
  return {
    limit: 50,
    sort_by: 'market_cap',
    sort_order: 'desc',
    search,
    skip: 0,
  };
}

function ScreenerPageContent() {
  const searchParams = useSearchParams();
  const searchQuery = searchParams.get('search')?.trim() || undefined;

  const [filters, setFilters] = useState<ScreenerFilters>(() => getDefaultFilters(searchQuery));
  const deferredFilters = useDeferredValue(filters);

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      search: searchQuery,
      skip: 0,
    }));
  }, [searchQuery]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['screener', deferredFilters],
    queryFn: () => screenerAPI.screenStocks(deferredFilters),
    placeholderData: keepPreviousData,
  });

  const currentPage = Math.floor((filters.skip ?? 0) / (filters.limit ?? 50)) + 1;
  const savedViews = ['Quality', 'Deep value', 'Growth', 'Dividend', 'Mega tech'];

  const handleFilterChange = (nextFilters: ScreenerFilters) => {
    setFilters(nextFilters);
  };

  const handleReset = () => {
    setFilters(getDefaultFilters(searchQuery));
  };

  const handleSort = (field: string) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: field,
      sort_order: prev.sort_by === field && prev.sort_order === 'desc' ? 'asc' : 'desc',
      skip: 0,
    }));
  };

  const handlePageChange = (page: number) => {
    const perPage = filters.limit ?? 50;
    setFilters((prev) => ({
      ...prev,
      skip: Math.max(0, (page - 1) * perPage),
    }));
  };

  return (
    <div className="container-custom py-8">
      <section className="mb-7 border-b border-t border-[var(--line)] py-7">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="live-dot">Screening desk</div>
            <h1 className="mt-3">Screener</h1>
            <p className="mt-3 text-base leading-relaxed text-[var(--text-secondary)]">
              Build a live market cut with valuation, quality, liquidity, and sector controls.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {savedViews.map((view, index) => (
                <button
                  key={view}
                  type="button"
                  className={cn(
                    'chip transition-[background,border-color,color]',
                    index === 0
                      ? 'border-[var(--ink)] bg-[var(--ink)] text-[var(--ivory)]'
                      : 'hover:border-[var(--forest-line)] hover:text-[var(--ink)]'
                  )}
                >
                  {view}
                </button>
              ))}
            </div>
          </div>

          <div className="hud flex min-w-[240px] items-center gap-4 rounded-[16px] border border-[var(--line)] bg-[var(--surface)] px-4 py-4 shadow-[var(--shadow-1)]">
            <span className="hud-c1" />
            <span className="hud-c2" />
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--accent-subtle)] text-[var(--accent)]">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
                Matches
              </div>
              <div className="mt-1 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                {data?.total.toLocaleString() ?? '0'}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-8 lg:grid-cols-[280px_minmax(0,1fr)] lg:items-start">
        <aside>
          <div className="deco-scroll hud flex flex-col overflow-hidden border border-[var(--line)] bg-[var(--surface)] shadow-[var(--shadow-1)] lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]">
            <span className="hud-c1" />
            <span className="hud-c2" />
            <FilterPanel
              filters={filters}
              isFetching={isFetching}
              onChange={handleFilterChange}
              onReset={handleReset}
            />
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="mb-3 flex justify-end">
            <button type="button" className="btn btn-quiet btn-sm inline-flex items-center">
              <Columns3 className="h-4 w-4" />
              Columns
            </button>
          </div>
          <StockTable
            stocks={data?.results ?? []}
            isLoading={isLoading || isFetching}
            sortBy={filters.sort_by}
            sortOrder={filters.sort_order}
            onSort={handleSort}
            page={data?.page ?? currentPage}
            totalPages={data?.total_pages ?? 1}
            total={data?.total ?? 0}
            perPage={data?.per_page ?? filters.limit ?? 50}
            onPageChange={handlePageChange}
            onResetFilters={handleReset}
          />
        </div>
      </div>
    </div>
  );
}

export default function ScreenerPage() {
  return (
    <Suspense fallback={<div className="container-custom py-8" />}>
      <ScreenerPageContent />
    </Suspense>
  );
}
