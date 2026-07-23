'use client';

import { Suspense, useEffect, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { GitCompareArrows } from 'lucide-react';

import ComparisonTable from '@/components/compare/ComparisonTable';
import { MAX_COMPARE_TICKERS, useSeriesColors } from '@/components/compare/colors';
import EmptyState from '@/components/compare/EmptyState';
import PerformanceChart from '@/components/compare/PerformanceChart';
import TickerPicker from '@/components/compare/TickerPicker';
import { stocksAPI } from '@/lib/api';
import type { Stock } from '@/types/stock';

function parseSymbolsParam(raw: string | null): string[] {
  if (!raw) return [];
  const unique: string[] = [];
  const seen = new Set<string>();
  raw
    .split(',')
    .map((value) => value.trim().toUpperCase())
    .filter(Boolean)
    .forEach((symbol) => {
      if (seen.has(symbol)) return;
      seen.add(symbol);
      unique.push(symbol);
    });
  return unique.slice(0, MAX_COMPARE_TICKERS);
}

function ComparePageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const [tickers, setTickers] = useState<string[]>(() => parseSymbolsParam(searchParams.get('symbols')));

  // Keep the URL in sync so a comparison is shareable/bookmarkable.
  useEffect(() => {
    const nextValue = tickers.join(',');
    const currentValue = searchParams.get('symbols') ?? '';
    if (nextValue === currentValue) return;
    const query = nextValue ? `?symbols=${nextValue}` : '';
    router.replace(`${pathname}${query}`, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickers]);

  const colorMap = useSeriesColors(tickers);

  const stockQueries = useQueries({
    queries: tickers.map((ticker) => ({
      queryKey: ['compare-stock', ticker],
      queryFn: () => stocksAPI.getStock(ticker),
      staleTime: 60 * 1000,
      retry: 1,
    })),
  });

  const stocksByTicker = new Map<string, Stock | undefined>();
  const loadingTickers = new Set<string>();
  const erroredTickers = new Set<string>();

  tickers.forEach((ticker, index) => {
    const query = stockQueries[index];
    if (query?.data) stocksByTicker.set(ticker, query.data);
    if (query?.isLoading) loadingTickers.add(ticker);
    if (query?.isError) erroredTickers.add(ticker);
  });

  const addTicker = (ticker: string) => {
    setTickers((prev) => {
      if (prev.includes(ticker) || prev.length >= MAX_COMPARE_TICKERS) return prev;
      return [...prev, ticker];
    });
  };

  const removeTicker = (ticker: string) => {
    setTickers((prev) => prev.filter((symbol) => symbol !== ticker));
  };

  const selectExample = (example: string[]) => {
    setTickers(example.slice(0, MAX_COMPARE_TICKERS));
  };

  return (
    <div className="container-custom py-8 md:py-10">
      <div className="space-y-6">
        <section className="border-b border-t border-[var(--line)] py-7">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-2xl">
              <div className="live-dot">Compare desk</div>
              <h1 className="heading-xl mt-3 text-[var(--text-primary)]">Compare stocks</h1>
              <p className="mt-3 text-base leading-relaxed text-[var(--text-secondary)]">
                Line up performance and fundamentals for up to {MAX_COMPARE_TICKERS} tickers at once.
                Share the URL to send a comparison to someone else.
              </p>
            </div>
            <div className="flex min-w-[220px] items-center gap-4 rounded-[var(--radius-lg)] border border-[var(--line-2)] bg-[var(--surface)] px-4 py-4 shadow-[var(--shadow-1)]">
              <div className="icon-tile h-11 w-11">
                <GitCompareArrows className="h-5 w-5" strokeWidth={1.6} />
              </div>
              <div>
                <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
                  Selected
                </div>
                <div className="mt-1 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                  {tickers.length}/{MAX_COMPARE_TICKERS}
                </div>
              </div>
            </div>
          </div>
        </section>

        <TickerPicker tickers={tickers} colorMap={colorMap} onAdd={addTicker} onRemove={removeTicker} />

        {tickers.length === 0 ? (
          <EmptyState onSelectExample={selectExample} />
        ) : (
          <div className="space-y-6">
            <PerformanceChart tickers={tickers} colorMap={colorMap} />
            <ComparisonTable
              tickers={tickers}
              stocksByTicker={stocksByTicker}
              loadingTickers={loadingTickers}
              erroredTickers={erroredTickers}
              colorMap={colorMap}
              onRemove={removeTicker}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="container-custom py-8" />}>
      <ComparePageContent />
    </Suspense>
  );
}
