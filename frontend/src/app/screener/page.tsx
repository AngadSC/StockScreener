'use client';

import { Suspense, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import FilterPanel from '@/components/screener/FilterPanel';
import StockTable from '@/components/screener/StockTable';
import { screenerAPI } from '@/lib/api';
import { ScreenerFilters } from '@/types/stock';
import { Loader2 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';

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

  const { data, isLoading, refetch } = useQuery({
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
    <div className="container py-6">
      {/* Terminal Header */}
      <div className="border-b border-border pb-6 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-glow mb-2">STOCK_SCREENER.EXE</h1>
            <p className="text-sm text-muted-foreground font-mono">
              DATABASE: {data?.total.toLocaleString() || '8,247'} records indexed
            </p>
          </div>
          {data && (
            <div className="text-right text-sm terminal-border bg-card px-4 py-3">
              <p className="text-muted-foreground font-mono">
                RESULTS: <span className="text-primary font-bold">{data.results.length}</span> / {data.total.toLocaleString()}
              </p>
              {data.cached && (
                <p className="text-muted-foreground mt-1.5 font-mono">
                  SOURCE: <span className="text-primary font-bold">CACHE</span>
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <FilterPanel
            onFilterChange={handleFilterChange}
            onReset={handleReset}
            search={filters.search}
          />
        </div>

        {/* Results */}
        <div className="lg:col-span-3 space-y-4">
          {/* Loading State */}
          {isLoading && (
            <div className="terminal-border bg-card p-12 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
              <p className="text-xs text-muted-foreground">EXECUTING_QUERY...</p>
            </div>
          )}

          {/* Stock Table */}
          {!isLoading && data && (
            <StockTable
              stocks={data.results}
              onSort={handleSort}
            />
          )}

          {/* Pagination */}
          {data && data.total_pages > 1 && (
            <div className="terminal-border bg-card px-4 py-3 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">
                PAGE {data.page} OF {data.total_pages}
              </span>
              <div className="flex gap-2">
                <button className="px-3 py-1 border border-border hover:border-primary hover:text-primary transition-colors">
                  PREV
                </button>
                <button className="px-3 py-1 border border-border hover:border-primary hover:text-primary transition-colors">
                  NEXT
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ScreenerPage() {
  return (
    <Suspense fallback={<div className="container py-6" />}>
      <ScreenerPageContent />
    </Suspense>
  );
}
