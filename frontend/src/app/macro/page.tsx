'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDown, ArrowUp, Loader2, Minus, TrendingUp } from 'lucide-react';

import MacroSparkline from '@/components/macro/MacroSparkline';
import { marketAPI } from '@/lib/api';
import { cn, formatDate } from '@/lib/utils';
import type { MacroSeriesData } from '@/types/macro';

const YIELD_CURVE_SERIES_ID = 'T10Y2Y';

function formatMacroValue(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A';
  if (unit === 'idx') return value.toFixed(2);
  return `${value.toFixed(2)}%`;
}

function ChangeIndicator({ value, unit }: { value: number | null | undefined; unit: string }) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return <span className="text-xs text-muted-foreground">No 1M change data</span>;
  }
  if (Math.abs(value) < 0.005) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
        <Minus className="h-3 w-3" />
        Flat vs 1M ago
      </span>
    );
  }
  const isUp = value > 0;
  const suffix = unit === 'idx' ? '' : 'pp';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 text-xs tabular-nums',
        isUp ? 'text-positive' : 'text-negative'
      )}
    >
      {isUp ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
      {isUp ? '+' : ''}
      {value.toFixed(2)}
      {suffix} vs 1M ago
    </span>
  );
}

function StatTile({ series }: { series: MacroSeriesData }) {
  return (
    <div className="deco-panel flex flex-col gap-3 bg-card p-5">
      <div>
        <div className="text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
          {series.label}
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-semibold tabular-nums">
            {formatMacroValue(series.latest_value, series.unit)}
          </span>
        </div>
        <div className="mt-1 flex items-center justify-between">
          <ChangeIndicator value={series.change_1m} unit={series.unit} />
          {series.latest_date ? (
            <span className="text-[11px] text-muted-foreground">{formatDate(series.latest_date)}</span>
          ) : null}
        </div>
      </div>
      <MacroSparkline data={series.sparkline} />
    </div>
  );
}

function YieldCurveCallout({ series }: { series: MacroSeriesData | undefined }) {
  if (!series || series.latest_value === null || series.latest_value === undefined) {
    return null;
  }

  const isInverted = series.latest_value < 0;

  return (
    <div className="deco-panel bg-card p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
            <TrendingUp className="h-3.5 w-3.5" />
            Yield Curve — 10Y minus 2Y
          </div>
          <div className="mt-2 flex items-baseline gap-3">
            <span
              className={cn(
                'text-3xl font-semibold tabular-nums',
                isInverted ? 'text-negative' : 'text-positive'
              )}
            >
              {series.latest_value >= 0 ? '+' : ''}
              {series.latest_value.toFixed(2)}pp
            </span>
            <span className={cn('chip', isInverted ? 'chip-dn' : 'chip-up')}>
              {isInverted ? 'Inverted' : 'Normal'}
            </span>
          </div>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
            {isInverted
              ? 'Short-term (2Y) yields are trading above long-term (10Y) yields — an inverted curve that has historically preceded recessions.'
              : 'Long-term (10Y) yields are trading above short-term (2Y) yields — a normal, upward-sloping curve.'}
          </p>
          {series.latest_date ? (
            <p className="mt-1 text-[11px] text-muted-foreground">
              As of {formatDate(series.latest_date)}
            </p>
          ) : null}
        </div>
        <div className="w-full max-w-sm flex-1">
          <MacroSparkline
            data={series.sparkline}
            color={isInverted ? 'var(--dn)' : 'var(--up)'}
            height={90}
            showZeroLine
            valueFormatter={(v) => `${v.toFixed(2)}pp`}
          />
        </div>
      </div>
    </div>
  );
}

function SetupNotice() {
  return (
    <div className="deco-panel p-10 text-center">
      <div className="deco-kicker justify-center">Setup required</div>
      <h2 className="mt-3 text-xl font-semibold">Macro dashboard isn&apos;t configured yet</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">
        This dashboard runs on free data from the Federal Reserve (FRED). Grab a free API key at{' '}
        <span className="font-medium text-foreground">fred.stlouisfed.org</span> and set{' '}
        <code className="rounded bg-muted/40 px-1.5 py-0.5 text-xs">FRED_API_KEY</code> in the
        backend environment to turn this on.
      </p>
    </div>
  );
}

export default function MacroPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['macro-dashboard'],
    queryFn: () => marketAPI.getMacroDashboard(),
  });

  const yieldCurveSeries = useMemo(
    () => data?.series.find((s) => s.id === YIELD_CURVE_SERIES_ID),
    [data]
  );
  const gridSeries = useMemo(
    () => (data?.series ?? []).filter((s) => s.id !== YIELD_CURVE_SERIES_ID),
    [data]
  );

  return (
    <div className="container-custom space-y-6 py-8">
      <section className="deco-panel p-8">
        <div className="deco-kicker">Macro desk</div>
        <h1 className="mt-3">Macro Dashboard</h1>
        <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
          Rates, inflation, employment, and volatility — the macro backdrop for every trade,
          sourced from the Federal Reserve.
        </p>
      </section>

      {isLoading ? (
        <div className="deco-panel p-12 text-center">
          <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading macro data...</p>
        </div>
      ) : null}

      {isError ? (
        <div className="deco-panel p-8 text-center">
          <p className="text-sm text-muted-foreground">
            Could not load the macro dashboard. Please try again shortly.
          </p>
        </div>
      ) : null}

      {!isLoading && !isError && data && !data.configured ? <SetupNotice /> : null}

      {!isLoading && !isError && data?.configured ? (
        <>
          <YieldCurveCallout series={yieldCurveSeries} />

          {gridSeries.length === 0 ? (
            <div className="deco-panel p-10 text-center text-sm text-muted-foreground">
              No macro observations yet. The nightly sync job populates this dashboard.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {gridSeries.map((series) => (
                <StatTile key={series.id} series={series} />
              ))}
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
