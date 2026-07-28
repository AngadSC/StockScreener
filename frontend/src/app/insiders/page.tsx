'use client';

import { useMemo, useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { RefreshCw, Users } from 'lucide-react';

import InsiderControls from '@/components/insiders/InsiderControls';
import InsiderTable from '@/components/insiders/InsiderTable';
import { Button } from '@/components/ui/button';
import { insidersAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { InsiderActivityFilters } from '@/types/insiders';

const DEFAULT_FILTERS: InsiderActivityFilters = {
  type: 'buys',
  min_value: 50000,
  days: 14,
  limit: 100,
};

export default function InsidersPage() {
  const [filters, setFilters] = useState<InsiderActivityFilters>(DEFAULT_FILTERS);

  const { data, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ['insider-activity', filters],
    queryFn: () => insidersAPI.getActivity(filters),
    placeholderData: keepPreviousData,
  });

  const results = data?.results ?? [];
  // Distinguish "the request failed" from "no filings match" — the table's
  // empty state reads as a real answer, which it isn't when the API is down.
  const showError = isError && !data;

  const buyCount = useMemo(
    () => results.filter((txn) => txn.type === 'buy').length,
    [results]
  );

  const heading =
    filters.type === 'buys'
      ? 'Insider Buying'
      : filters.type === 'sells'
        ? 'Insider Selling'
        : 'Insider Activity';

  return (
    <div className="container-custom py-8">
      <section className="mb-7 border-b border-t border-[var(--line)] py-7">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="live-dot">Insider desk</div>
            <h1 className="mt-3">{heading}</h1>
            <p className="mt-3 text-base leading-relaxed text-[var(--text-secondary)]">
              Open-market purchases and sales reported to the SEC on Form 4 by company
              officers, directors, and 10% owners. Free and updated every trading day.
            </p>
            <p className="mt-2 text-[13px] leading-relaxed text-[var(--text-tertiary)]">
              A Form 4 is the filing an insider must submit to the SEC within two business days
              of buying or selling their own company’s shares.
            </p>
          </div>

          <div className="flex min-w-[240px] items-center gap-4 rounded-[var(--radius-lg)] border border-[var(--line-2)] bg-[var(--surface)] px-4 py-4 shadow-[var(--shadow-1)]">
            <div className="icon-tile h-11 w-11">
              <Users className="h-5 w-5" strokeWidth={1.6} />
            </div>
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
                Filings shown
              </div>
              <div
                className={cn(
                  'mt-1 text-2xl font-semibold tabular-nums',
                  showError ? 'text-[var(--negative)]' : 'text-[var(--text-primary)]'
                )}
              >
                {showError ? '—' : (data?.count ?? 0).toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="mb-6 rounded-[16px] border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[var(--shadow-1)]">
        <InsiderControls
          filters={filters}
          onChange={setFilters}
          isFetching={isFetching && !isLoading}
        />
      </div>

      {showError ? (
        <div className="deco-panel p-8 text-center">
          <p className="text-sm text-[var(--text-secondary)]">
            Could not load insider filings. This is a connection problem, not an empty result —
            your filters are still applied.
          </p>
          <div className="mt-4 flex justify-center">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={cn('h-4 w-4', isFetching && 'animate-spin')} />
              {isFetching ? 'Retrying…' : 'Retry'}
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="mb-3 flex items-center justify-between">
            <p className="smallcap-low">
              {filters.type === 'all' && results.length > 0
                ? `${buyCount} buys · ${results.length - buyCount} sells`
                : `Newest first · min ${formatCompact(filters.min_value)} · last ${filters.days}d`}
            </p>
            <div className="live-dot">{isLoading ? 'Updating' : 'Live'}</div>
          </div>

          <InsiderTable transactions={results} isLoading={isLoading} />
        </>
      )}
    </div>
  );
}

function formatCompact(value: number): string {
  if (value >= 1e6) return `$${(value / 1e6).toFixed(0)}M`;
  if (value >= 1e3) return `$${(value / 1e3).toFixed(0)}K`;
  return `$${value}`;
}
