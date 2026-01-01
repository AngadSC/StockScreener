'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import FilterPanel from '@/components/screener/FilterPanel';
import StockTable from '@/components/screener/StockTable';
import { screenerAPI } from '@/lib/api';
import { ScreenerFilters } from '@/types/stock';
import { Loader2 } from 'lucide-react';

export default function ScreenerPage() {
  const [filters, setFilters] = useState<ScreenerFilters>({
    limit: 50,
    sort_by: 'market_cap',
    sort_order: 'desc',
  });

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
    <div className="container py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Stock Screener</h1>
        <p className="text-muted-foreground">
          Filter through {data?.total.toLocaleString() || '8,000+'} stocks to find your perfect investment
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <FilterPanel 
            onFilterChange={handleFilterChange}
            onReset={handleReset}
          />
        </div>

        {/* Results */}
        <div className="lg:col-span-3 space-y-4">
          {/* Results Header */}
          {data && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {data.results.length} of {data.total.toLocaleString()} stocks
                {data.cached && ' (cached)'}
              </p>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {/* Stock Table */}
          {!isLoading && data && (
            <StockTable 
              stocks={data.results}
              onSort={handleSort}
            />
          )}

          {/* Pagination (if needed) */}
          {data && data.total_pages > 1 && (
            <div className="flex justify-center gap-2 mt-6">
              <p className="text-sm text-muted-foreground">
                Page {data.page} of {data.total_pages}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
