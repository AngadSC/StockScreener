'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, RefreshCw } from 'lucide-react';

import ScanTable from '@/components/markets/ScanTable';
import SectorHeatmap from '@/components/markets/SectorHeatmap';
import { Button } from '@/components/ui/button';
import { marketAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import { MARKET_SCAN_TABS } from '@/types/market';
import type { MarketScanKey } from '@/types/market';

export default function MarketsPage() {
  const [activeTab, setActiveTab] = useState<MarketScanKey>('gainers');

  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['market-scans'],
    queryFn: () => marketAPI.getScans(),
    staleTime: 60_000,
  });

  const activeTabConfig = MARKET_SCAN_TABS.find((tab) => tab.key === activeTab) ?? MARKET_SCAN_TABS[0];
  const activeRows = data?.[activeTab] ?? [];
  // Only take over the page when there is nothing to show; a failed background
  // refetch should not blank out scans we already have.
  const showError = isError && !data;

  return (
    <div className="container-custom py-8">
      <section className="mb-7 border-b border-t border-[var(--line)] py-7">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="live-dot">Free scanners</div>
            <h1 className="mt-3">Market scanners</h1>
            <p className="mt-3 text-base leading-relaxed text-[var(--text-secondary)]">
              Daily-refreshed gainers, losers, 52-week breakouts, unusual volume, and gaps, plus a
              sector heatmap. Recomputed once per market close.
            </p>
          </div>

          <div className="flex min-w-[220px] items-center gap-4 rounded-[var(--radius-lg)] border border-[var(--line-2)] bg-[var(--surface)] px-4 py-4 shadow-[var(--shadow-1)]">
            <div className="icon-tile h-11 w-11">
              <Activity className="h-5 w-5" strokeWidth={1.6} />
            </div>
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
                As of
              </div>
              <div
                className={cn(
                  'mt-1 text-lg font-semibold',
                  showError ? 'text-[var(--negative)]' : 'text-[var(--text-primary)]'
                )}
              >
                {showError ? '—' : data?.as_of_date ?? (isLoading ? 'Loading…' : '—')}
              </div>
              {showError ? (
                <div className="mt-0.5 text-[11px] text-[var(--negative)]">Data unavailable</div>
              ) : null}
            </div>
          </div>
        </div>
      </section>

      {showError ? (
        <div className="deco-panel p-8 text-center">
          <p className="text-sm text-[var(--text-secondary)]">
            Could not load the market scanners. This is a connection problem, not an empty market.
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
          <section className="mb-8">
            <h2 className="heading-md mb-4 text-[var(--text-primary)]">Sector heatmap</h2>
            <SectorHeatmap sectors={data?.sectors ?? []} isLoading={isLoading} />
          </section>

          <section>
            <div className="flex flex-wrap gap-2">
              {MARKET_SCAN_TABS.map((tab) => (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => setActiveTab(tab.key)}
                  className={cn(
                    'chip transition-[background,border-color,color]',
                    activeTab === tab.key
                      ? 'border-[var(--ink)] bg-[var(--ink)] text-[var(--ivory)]'
                      : 'hover:border-[var(--forest-line)] hover:text-[var(--ink)]'
                  )}
                >
                  {tab.label}
                  {data ? ` (${data[tab.key]?.length ?? 0})` : ''}
                </button>
              ))}
            </div>

            <p className="mb-4 mt-3 text-[13px] leading-relaxed text-[var(--text-tertiary)]">
              {activeTabConfig.description}
            </p>

            <ScanTable
              rows={activeRows}
              isLoading={isLoading}
              tab={activeTabConfig}
              asOfDate={data?.as_of_date ?? null}
            />
          </section>
        </>
      )}
    </div>
  );
}
