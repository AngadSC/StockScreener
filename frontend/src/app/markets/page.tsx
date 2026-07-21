'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity } from 'lucide-react';

import ScanTable from '@/components/markets/ScanTable';
import SectorHeatmap from '@/components/markets/SectorHeatmap';
import { marketAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import { MARKET_SCAN_TABS } from '@/types/market';
import type { MarketScanKey } from '@/types/market';

export default function MarketsPage() {
  const [activeTab, setActiveTab] = useState<MarketScanKey>('gainers');

  const { data, isLoading } = useQuery({
    queryKey: ['market-scans'],
    queryFn: () => marketAPI.getScans(),
    staleTime: 60_000,
  });

  const activeTabConfig = MARKET_SCAN_TABS.find((tab) => tab.key === activeTab) ?? MARKET_SCAN_TABS[0];
  const activeRows = data?.[activeTab] ?? [];

  return (
    <div className="container-custom py-8">
      <section className="mb-7 border-b border-t border-[var(--line)] py-7">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="live-dot">Free scanners</div>
            <h1 className="mt-3">Markets</h1>
            <p className="mt-3 text-base leading-relaxed text-[var(--text-secondary)]">
              Daily-refreshed gainers, losers, 52-week breakouts, unusual volume, and gaps, plus a live sector
              heatmap. Computed once per close from data already in the warehouse.
            </p>
          </div>

          <div className="hud flex min-w-[220px] items-center gap-4 rounded-[16px] border border-[var(--line)] bg-[var(--surface)] px-4 py-4 shadow-[var(--shadow-1)]">
            <span className="hud-c1" />
            <span className="hud-c2" />
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--accent-subtle)] text-[var(--accent)]">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
                As of
              </div>
              <div className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                {data?.as_of_date ?? (isLoading ? 'Loading…' : '—')}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-8">
        <h2 className="heading-md mb-4 text-[var(--text-primary)]">Sector heatmap</h2>
        <SectorHeatmap sectors={data?.sectors ?? []} isLoading={isLoading} />
      </section>

      <section>
        <div className="mb-4 flex flex-wrap gap-2">
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

        <ScanTable
          rows={activeRows}
          isLoading={isLoading}
          tab={activeTabConfig}
          asOfDate={data?.as_of_date ?? null}
        />
      </section>
    </div>
  );
}
