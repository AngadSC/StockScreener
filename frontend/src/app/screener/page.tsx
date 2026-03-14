'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';

import FilterPanel from '@/components/screener/FilterPanel';
import StockTable from '@/components/screener/StockTable';
import { screenerAPI } from '@/lib/api';
import type { ScreenerFilters } from '@/types/stock';

function ScreenerPageContent() {
  const searchParams = useSearchParams();
  const searchQuery = searchParams.get('search')?.trim() || undefined;

  const [filters, setFilters] = useState<ScreenerFilters>(() => ({
    limit: 50,
    sort_by: 'market_cap',
    sort_order: 'desc',
    search: searchQuery,
    skip: 0,
  }));

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      search: searchQuery,
      skip: 0,
    }));
  }, [searchQuery]);

  const { data, isLoading } = useQuery({
    queryKey: ['screener', filters],
    queryFn: () => screenerAPI.screenStocks(filters),
  });

  const handleFilterChange = (newFilters: ScreenerFilters) => {
    setFilters(newFilters);
  };

  const handleReset = () => {
    setFilters({
      limit: 50,
      sort_by: 'market_cap',
      sort_order: 'desc',
      search: searchQuery,
      skip: 0,
    });
  };

  const handleSort = (field: string) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: field,
      sort_order: prev.sort_by === field && prev.sort_order === 'desc' ? 'asc' : 'desc',
      skip: 0,
    }));
  };

  const currentPage = useMemo(() => {
    const perPage = filters.limit ?? 50;
    const skip = filters.skip ?? 0;
    return Math.floor(skip / perPage) + 1;
  }, [filters.limit, filters.skip]);

  const handlePageChange = (page: number) => {
    const perPage = filters.limit ?? 50;
    setFilters((prev) => ({
      ...prev,
      skip: Math.max(0, (page - 1) * perPage),
    }));
  };

  return (
    <div className="container-custom space-y-6 py-8">
      <section className="deco-panel p-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="deco-kicker">Workspace</div>
            <h1 className="mt-3">Screener</h1>
            <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
              Search for names, shape the universe with filters, and keep the results table front
              and center.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-border/70 bg-muted/20 px-4 py-4">
              <div className="text-xs font-medium text-muted-foreground">Records</div>
              <div className="mt-2 text-2xl font-semibold text-foreground tabular-nums">
                {data?.total.toLocaleString() || '8,247'}
              </div>
            </div>
            <div className="rounded-lg border border-border/70 bg-muted/20 px-4 py-4">
              <div className="text-xs font-medium text-muted-foreground">Visible</div>
              <div className="mt-2 text-2xl font-semibold text-foreground tabular-nums">
                {data?.results.length ?? filters.limit ?? 50}
              </div>
            </div>
          </div>
        </div>
      </section>

      <FilterPanel onFilterChange={handleFilterChange} onReset={handleReset} search={filters.search} />

      {isLoading ? (
        <div className="deco-panel p-16 text-center">
          <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
          <div className="text-sm text-muted-foreground">Refreshing the market ledger...</div>
        </div>
      ) : (
        <StockTable
          stocks={data?.results ?? []}
          onSort={handleSort}
          page={data?.page ?? currentPage}
          totalPages={data?.total_pages ?? 1}
          total={data?.total ?? 0}
          perPage={data?.per_page ?? filters.limit ?? 50}
          onPageChange={handlePageChange}
        />
      )}
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
