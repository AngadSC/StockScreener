'use client';

import { Suspense, useEffect, useState } from 'react';
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
    });
  };

  const handleSort = (field: string) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: field,
      sort_order: prev.sort_by === field && prev.sort_order === 'desc' ? 'asc' : 'desc',
    }));
  };

  return (
    <div className="container-custom space-y-6 py-8">
      <section className="deco-panel bg-grid-luxe p-8">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <div className="deco-kicker">Market Hall</div>
            <h1 className="mt-3 text-5xl font-semibold text-glow">Screener</h1>
            <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
              Search for names, shape the universe with collapsible filters, and keep the results table front
              and center.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="border border-primary/14 bg-background/60 px-4 py-4">
              <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Records</div>
              <div className="mt-2 text-2xl font-semibold text-foreground">
                {data?.total.toLocaleString() || '8,247'}
              </div>
            </div>
            <div className="border border-primary/14 bg-background/60 px-4 py-4">
              <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Visible</div>
              <div className="mt-2 text-2xl font-semibold text-foreground">
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
        <StockTable stocks={data?.results ?? []} onSort={handleSort} />
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
