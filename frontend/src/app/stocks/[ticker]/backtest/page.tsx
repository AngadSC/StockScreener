'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2 } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { stocksAPI } from '@/lib/api';
import { formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/utils';
import type { BacktestRunRequest } from '@/types/stock';

type IndicatorKey =
  | 'rsi'
  | 'stoch'
  | 'willr'
  | 'roc'
  | 'tsi'
  | 'ao'
  | 'sma_xo'
  | 'ema_xo'
  | 'macd'
  | 'adx'
  | 'aroon'
  | 'bbands'
  | 'obv'
  | 'mfi'
  | 'cmf';

type FieldDef = {
  key: string;
  label: string;
  step?: number;
};

type IndicatorDef = {
  key: IndicatorKey;
  label: string;
  description: string;
  defaults: { enabled: boolean; weight: number; params: Record<string, number> };
  fields: FieldDef[];
};

const INDICATORS: IndicatorDef[] = [
  {
    key: 'rsi',
    label: 'RSI Threshold',
    description: 'Buy oversold, sell overbought.',
    defaults: { enabled: true, weight: 1, params: { period: 14, buy_below: 30, sell_above: 70 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_below', label: 'Buy Below', step: 0.1 },
      { key: 'sell_above', label: 'Sell Above', step: 0.1 },
    ],
  },
  {
    key: 'stoch',
    label: 'Stochastic XO',
    description: '%K/%D crossover.',
    defaults: { enabled: false, weight: 1, params: { k: 14, d: 3 } },
    fields: [
      { key: 'k', label: 'K Window', step: 1 },
      { key: 'd', label: 'D Smooth', step: 1 },
    ],
  },
  {
    key: 'willr',
    label: 'Williams %R',
    description: 'Threshold-based momentum reversal.',
    defaults: { enabled: false, weight: 1, params: { period: 14, buy_below: -80, sell_above: -20 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_below', label: 'Buy Below', step: 0.1 },
      { key: 'sell_above', label: 'Sell Above', step: 0.1 },
    ],
  },
  {
    key: 'roc',
    label: 'ROC',
    description: 'Trade the rate-of-change sign.',
    defaults: { enabled: false, weight: 1, params: { period: 12, buy_above: 0, sell_below: 0 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_above', label: 'Buy Above', step: 0.1 },
      { key: 'sell_below', label: 'Sell Below', step: 0.1 },
    ],
  },
  {
    key: 'tsi',
    label: 'TSI',
    description: 'True Strength Index sign filter.',
    defaults: { enabled: false, weight: 1, params: { slow: 25, fast: 13, buy_above: 0, sell_below: 0 } },
    fields: [
      { key: 'slow', label: 'Slow', step: 1 },
      { key: 'fast', label: 'Fast', step: 1 },
      { key: 'buy_above', label: 'Buy Above', step: 0.1 },
      { key: 'sell_below', label: 'Sell Below', step: 0.1 },
    ],
  },
  {
    key: 'ao',
    label: 'Awesome Oscillator',
    description: 'Zero-line bias.',
    defaults: { enabled: false, weight: 1, params: { fast: 5, slow: 34, buy_above: 0, sell_below: 0 } },
    fields: [
      { key: 'fast', label: 'Fast', step: 1 },
      { key: 'slow', label: 'Slow', step: 1 },
      { key: 'buy_above', label: 'Buy Above', step: 0.1 },
      { key: 'sell_below', label: 'Sell Below', step: 0.1 },
    ],
  },
  {
    key: 'sma_xo',
    label: 'SMA Crossover',
    description: 'Fast/slow SMA crossover.',
    defaults: { enabled: false, weight: 1, params: { fast: 10, slow: 50 } },
    fields: [
      { key: 'fast', label: 'Fast SMA', step: 1 },
      { key: 'slow', label: 'Slow SMA', step: 1 },
    ],
  },
  {
    key: 'ema_xo',
    label: 'EMA Crossover',
    description: 'Fast/slow EMA crossover.',
    defaults: { enabled: true, weight: 1, params: { fast: 12, slow: 26 } },
    fields: [
      { key: 'fast', label: 'Fast EMA', step: 1 },
      { key: 'slow', label: 'Slow EMA', step: 1 },
    ],
  },
  {
    key: 'macd',
    label: 'MACD',
    description: 'Line/signal crossover.',
    defaults: { enabled: true, weight: 1, params: { fast: 12, slow: 26, signal: 9 } },
    fields: [
      { key: 'fast', label: 'Fast', step: 1 },
      { key: 'slow', label: 'Slow', step: 1 },
      { key: 'signal', label: 'Signal', step: 1 },
    ],
  },
  {
    key: 'adx',
    label: 'ADX + DI',
    description: 'Directional crossover gated by ADX.',
    defaults: { enabled: false, weight: 1, params: { period: 14, adx_min: 20 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'adx_min', label: 'ADX Min', step: 0.1 },
    ],
  },
  {
    key: 'aroon',
    label: 'Aroon XO',
    description: 'Aroon up/down crossover.',
    defaults: { enabled: false, weight: 1, params: { period: 14 } },
    fields: [{ key: 'period', label: 'Period', step: 1 }],
  },
  {
    key: 'bbands',
    label: 'Bollinger Bands',
    description: 'Price vs band extremes.',
    defaults: { enabled: false, weight: 1, params: { window: 20, n_std: 2 } },
    fields: [
      { key: 'window', label: 'Window', step: 1 },
      { key: 'n_std', label: 'Std Dev', step: 0.1 },
    ],
  },
  {
    key: 'obv',
    label: 'OBV Slope',
    description: 'Direction from OBV slope.',
    defaults: { enabled: false, weight: 1, params: { window: 5 } },
    fields: [{ key: 'window', label: 'Slope Window', step: 1 }],
  },
  {
    key: 'mfi',
    label: 'MFI',
    description: 'Money flow threshold reversal.',
    defaults: { enabled: false, weight: 1, params: { period: 14, buy_below: 20, sell_above: 80 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_below', label: 'Buy Below', step: 0.1 },
      { key: 'sell_above', label: 'Sell Above', step: 0.1 },
    ],
  },
  {
    key: 'cmf',
    label: 'CMF',
    description: 'Chaikin Money Flow threshold.',
    defaults: { enabled: false, weight: 1, params: { period: 20, threshold: 0 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'threshold', label: 'Threshold', step: 0.01 },
    ],
  },
];

function toInputDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function createDefaultRequest(): BacktestRunRequest {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(end.getFullYear() - 2);

  return {
    start_date: toInputDate(start),
    end_date: toInputDate(end),
    indicators: Object.fromEntries(
      INDICATORS.map((indicator) => [
        indicator.key,
        { ...indicator.defaults, params: { ...indicator.defaults.params } },
      ])
    ),
    atr_gate: {
      enabled: false,
      params: {
        period: 14,
        close_pct: 0.02,
      },
    },
    long_threshold: 0.5,
    short_threshold: -0.5,
    exec_lag: 1,
    tc_bps: 5,
    allow_position_hold: true,
    generate_plots: true,
    generate_roc: true,
  };
}

function parseNumber(value: string, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

interface PageProps {
  params: { ticker: string };
}

export default function StockBacktestPage({ params }: PageProps) {
  const ticker = params.ticker.toUpperCase();
  const [request, setRequest] = useState<BacktestRunRequest>(() => createDefaultRequest());

  const { data: stock } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => stocksAPI.getStock(ticker),
  });

  const mutation = useMutation({
    mutationFn: (payload: BacktestRunRequest) => stocksAPI.runBacktest(ticker, payload),
  });

  const result = mutation.data;
  const equityData = (result?.equity_curve ?? []).map((point) => ({
    date: String(point.Date ?? ''),
    equity: Number(point.Equity ?? 0),
  }));
  const selectedCount = Object.values(request.indicators).filter((indicator) => indicator.enabled).length;
  const tableRows = (result?.results ?? []).slice(-25).reverse();

  return (
    <div className="container py-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <Link
          href={`/stocks/${ticker}`}
          className="inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-primary transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          BACK_TO_STOCK
        </Link>
        <Button variant="outline" onClick={() => setRequest(createDefaultRequest())}>
          RESET_DEFAULTS
        </Button>
      </div>

      <div className="terminal-border bg-card p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Indicator Backtest Lab</div>
            <h1 className="mt-3 text-4xl font-bold text-glow">{ticker}</h1>
            <p className="mt-2 text-muted-foreground">
              {stock?.name ??
                'Configure the full indicator lab, run against DB-first historical data, and inspect the resulting equity curve and plots.'}
            </p>
          </div>
          <div className="grid gap-3 text-xs text-muted-foreground sm:grid-cols-3">
            <div className="rounded border border-border bg-muted/10 px-3 py-2">
              <div>DATA FLOW</div>
              <div className="mt-1 font-mono text-foreground">DB -&gt; YFINANCE</div>
            </div>
            <div className="rounded border border-border bg-muted/10 px-3 py-2">
              <div>ENABLED</div>
              <div className="mt-1 font-mono text-foreground">{selectedCount} INDICATORS</div>
            </div>
            <div className="rounded border border-border bg-muted/10 px-3 py-2">
              <div>PLOTS</div>
              <div className="mt-1 font-mono text-foreground">EQUITY + ROC</div>
            </div>
          </div>
        </div>
      </div>

      <form
        className="space-y-6"
        onSubmit={(event) => {
          event.preventDefault();
          mutation.mutate(request);
        }}
      >
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <section className="terminal-border bg-card p-6 space-y-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold">RUN CONFIG</h2>
                  <p className="text-sm text-muted-foreground">Date range, execution settings, and score thresholds.</p>
                </div>
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      RUNNING
                    </>
                  ) : (
                    'RUN BACKTEST'
                  )}
                </Button>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <label className="space-y-2 text-sm">
                  <span className="text-muted-foreground">Start Date</span>
                  <Input
                    type="date"
                    value={request.start_date}
                    onChange={(event) => setRequest((prev) => ({ ...prev, start_date: event.target.value }))}
                  />
                </label>
                <label className="space-y-2 text-sm">
                  <span className="text-muted-foreground">End Date</span>
                  <Input
                    type="date"
                    value={request.end_date}
                    onChange={(event) => setRequest((prev) => ({ ...prev, end_date: event.target.value }))}
                  />
                </label>
                <label className="space-y-2 text-sm">
                  <span className="text-muted-foreground">Long Threshold</span>
                  <Input
                    type="number"
                    step="0.01"
                    value={request.long_threshold}
                    onChange={(event) =>
                      setRequest((prev) => ({
                        ...prev,
                        long_threshold: parseNumber(event.target.value, prev.long_threshold),
                      }))
                    }
                  />
                </label>
                <label className="space-y-2 text-sm">
                  <span className="text-muted-foreground">Short Threshold</span>
                  <Input
                    type="number"
                    step="0.01"
                    value={request.short_threshold}
                    onChange={(event) =>
                      setRequest((prev) => ({
                        ...prev,
                        short_threshold: parseNumber(event.target.value, prev.short_threshold),
                      }))
                    }
                  />
                </label>
                <label className="space-y-2 text-sm">
                  <span className="text-muted-foreground">Execution Lag</span>
                  <Input
                    type="number"
                    step="1"
                    min="0"
                    value={request.exec_lag}
                    onChange={(event) =>
                      setRequest((prev) => ({
                        ...prev,
                        exec_lag: parseNumber(event.target.value, prev.exec_lag),
                      }))
                    }
                  />
                </label>
                <label className="space-y-2 text-sm">
                  <span className="text-muted-foreground">Transaction Cost (bps)</span>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    value={request.tc_bps}
                    onChange={(event) =>
                      setRequest((prev) => ({
                        ...prev,
                        tc_bps: parseNumber(event.target.value, prev.tc_bps),
                      }))
                    }
                  />
                </label>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded border border-border bg-muted/10 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-semibold">ATR Volatility Gate</div>
                      <div className="text-xs text-muted-foreground">Only act when ATR/Close clears the threshold.</div>
                    </div>
                    <input
                      type="checkbox"
                      checked={request.atr_gate?.enabled ?? false}
                      onChange={(event) =>
                        setRequest((prev) => ({
                          ...prev,
                          atr_gate: {
                            enabled: event.target.checked,
                            params: prev.atr_gate?.params ?? { period: 14, close_pct: 0.02 },
                          },
                        }))
                      }
                      className="h-4 w-4 accent-primary"
                    />
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <label className="space-y-2 text-sm">
                      <span className="text-muted-foreground">ATR Period</span>
                      <Input
                        type="number"
                        step="1"
                        value={Number(request.atr_gate?.params.period ?? 14)}
                        onChange={(event) =>
                          setRequest((prev) => ({
                            ...prev,
                            atr_gate: {
                              enabled: prev.atr_gate?.enabled ?? false,
                              params: {
                                ...prev.atr_gate?.params,
                                period: parseNumber(event.target.value, Number(prev.atr_gate?.params.period ?? 14)),
                              },
                            },
                          }))
                        }
                      />
                    </label>
                    <label className="space-y-2 text-sm">
                      <span className="text-muted-foreground">Min ATR/Close</span>
                      <Input
                        type="number"
                        step="0.001"
                        value={Number(request.atr_gate?.params.close_pct ?? 0.02)}
                        onChange={(event) =>
                          setRequest((prev) => ({
                            ...prev,
                            atr_gate: {
                              enabled: prev.atr_gate?.enabled ?? false,
                              params: {
                                ...prev.atr_gate?.params,
                                close_pct: parseNumber(
                                  event.target.value,
                                  Number(prev.atr_gate?.params.close_pct ?? 0.02)
                                ),
                              },
                            },
                          }))
                        }
                      />
                    </label>
                  </div>
                </div>

                <div className="rounded border border-border bg-muted/10 p-4 space-y-3">
                  <div className="font-semibold">Execution Flags</div>
                  <label className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-muted-foreground">Allow position hold between signals</span>
                    <input
                      type="checkbox"
                      checked={request.allow_position_hold}
                      onChange={(event) =>
                        setRequest((prev) => ({ ...prev, allow_position_hold: event.target.checked }))
                      }
                      className="h-4 w-4 accent-primary"
                    />
                  </label>
                  <label className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-muted-foreground">Generate backend plot images</span>
                    <input
                      type="checkbox"
                      checked={request.generate_plots}
                      onChange={(event) => setRequest((prev) => ({ ...prev, generate_plots: event.target.checked }))}
                      className="h-4 w-4 accent-primary"
                    />
                  </label>
                  <label className="flex items-center justify-between gap-3 text-sm">
                    <span className="text-muted-foreground">Generate ROC curve</span>
                    <input
                      type="checkbox"
                      checked={request.generate_roc}
                      onChange={(event) => setRequest((prev) => ({ ...prev, generate_roc: event.target.checked }))}
                      className="h-4 w-4 accent-primary"
                    />
                  </label>
                </div>
              </div>
            </section>

            <section className="terminal-border bg-card p-6 space-y-5">
              <div>
                <h2 className="text-lg font-bold">INDICATOR LAB</h2>
                <p className="text-sm text-muted-foreground">
                  Toggle any subset, adjust weights, then the weighted score is converted into final signals.
                </p>
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                {INDICATORS.map((indicator) => {
                  const config = request.indicators[indicator.key];
                  return (
                    <div key={indicator.key} className="rounded border border-border bg-muted/10 p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="font-semibold">{indicator.label}</div>
                          <div className="mt-1 text-xs text-muted-foreground">{indicator.description}</div>
                        </div>
                        <input
                          type="checkbox"
                          checked={config.enabled}
                          onChange={(event) =>
                            setRequest((prev) => ({
                              ...prev,
                              indicators: {
                                ...prev.indicators,
                                [indicator.key]: {
                                  ...prev.indicators[indicator.key],
                                  enabled: event.target.checked,
                                },
                              },
                            }))
                          }
                          className="mt-1 h-4 w-4 accent-primary"
                        />
                      </div>
                      <div className="mt-4 grid gap-3">
                        <label className="space-y-2 text-sm">
                          <span className="text-muted-foreground">Weight</span>
                          <Input
                            type="number"
                            step="0.1"
                            value={config.weight}
                            onChange={(event) =>
                              setRequest((prev) => ({
                                ...prev,
                                indicators: {
                                  ...prev.indicators,
                                  [indicator.key]: {
                                    ...prev.indicators[indicator.key],
                                    weight: parseNumber(event.target.value, prev.indicators[indicator.key].weight),
                                  },
                                },
                              }))
                            }
                          />
                        </label>
                        <div className="grid gap-3 sm:grid-cols-2">
                          {indicator.fields.map((field) => (
                            <label key={field.key} className="space-y-2 text-sm">
                              <span className="text-muted-foreground">{field.label}</span>
                              <Input
                                type="number"
                                step={field.step ?? 1}
                                value={Number(config.params[field.key] ?? 0)}
                                onChange={(event) =>
                                  setRequest((prev) => ({
                                    ...prev,
                                    indicators: {
                                      ...prev.indicators,
                                      [indicator.key]: {
                                        ...prev.indicators[indicator.key],
                                        params: {
                                          ...prev.indicators[indicator.key].params,
                                          [field.key]: parseNumber(
                                            event.target.value,
                                            Number(prev.indicators[indicator.key].params[field.key] ?? 0)
                                          ),
                                        },
                                      },
                                    },
                                  }))
                                }
                              />
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <div className="space-y-6">
            <section className="terminal-border bg-card p-6 min-h-[260px]">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-bold">RESULTS</h2>
                {result && (
                  <div className="text-xs text-muted-foreground">
                    SOURCE: <span className="text-foreground font-mono">{result.source.toUpperCase()}</span>
                    {result.cached ? ' | CACHE_HIT' : ''}
                  </div>
                )}
              </div>

              {mutation.isPending ? (
                <div className="flex min-h-[180px] items-center justify-center">
                  <div className="text-center">
                    <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
                    <p className="mt-4 text-sm text-muted-foreground">Running indicator lab...</p>
                  </div>
                </div>
              ) : mutation.error ? (
                <div className="mt-6 rounded border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
                  {(mutation.error as Error).message || 'Backtest failed.'}
                </div>
              ) : result ? (
                <div className="mt-5 space-y-5">
                  {result.warnings.length > 0 && (
                    <div className="rounded border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
                      {result.warnings.map((warning) => (
                        <div key={warning}>{warning}</div>
                      ))}
                    </div>
                  )}

                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {Object.entries(result.stats).map(([key, value]) => (
                      <div key={key} className="rounded border border-border bg-muted/10 p-3">
                        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{key}</div>
                        <div className="mt-2 text-lg font-semibold text-foreground">
                          {key.includes('%')
                            ? formatPercent(value, { mode: 'percent', withSign: !key.includes('drawdown') })
                            : formatNumber(value)}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div>
                    <div className="mb-2 text-sm font-semibold">Selected Indicators</div>
                    <div className="flex flex-wrap gap-2">
                      {result.selected_indicators.map((name) => (
                        <span
                          key={name}
                          className="rounded border border-primary/30 bg-primary/10 px-2 py-1 text-xs text-primary"
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-[180px] items-center justify-center text-center text-sm text-muted-foreground">
                  Configure the indicator set, then run the backtest to populate stats, charts, and plots.
                </div>
              )}
            </section>

            {result && (
              <>
                <section className="terminal-border bg-card p-6">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <h2 className="text-lg font-bold">EQUITY CURVE</h2>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(result.start_date)} - {formatDate(result.end_date)}
                    </div>
                  </div>
                  <div className="h-[320px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={equityData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                        <XAxis dataKey="date" minTickGap={36} stroke="#94a3b8" />
                        <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: '#0f172a',
                            border: '1px solid rgba(148, 163, 184, 0.25)',
                            borderRadius: '0.5rem',
                          }}
                          formatter={(value: number | string | undefined, name: string | undefined) => [
                            formatNumber(typeof value === 'number' ? value : Number(value ?? 0)),
                            String(name ?? '').toUpperCase(),
                          ]}
                        />
                        <Line type="monotone" dataKey="equity" stroke="#22c55e" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </section>

                <section className="grid gap-6 lg:grid-cols-2">
                  <div className="terminal-border bg-card p-4">
                    <div className="mb-3 text-sm font-semibold">Generated Equity Plot</div>
                    {result.equity_curve_image ? (
                      <img
                        src={result.equity_curve_image}
                        alt="Equity curve plot"
                        className="w-full rounded border border-border"
                      />
                    ) : (
                      <div className="rounded border border-dashed border-border p-6 text-sm text-muted-foreground">
                        Equity image generation disabled.
                      </div>
                    )}
                  </div>
                  <div className="terminal-border bg-card p-4">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div className="text-sm font-semibold">Generated ROC Plot</div>
                      <div className="text-xs text-muted-foreground">
                        AUC:{' '}
                        {result.roc_auc !== null && result.roc_auc !== undefined
                          ? formatNumber(result.roc_auc)
                          : 'N/A'}
                      </div>
                    </div>
                    {result.roc_curve_image ? (
                      <img
                        src={result.roc_curve_image}
                        alt="ROC curve plot"
                        className="w-full rounded border border-border"
                      />
                    ) : (
                      <div className="rounded border border-dashed border-border p-6 text-sm text-muted-foreground">
                        ROC could not be produced for this run.
                      </div>
                    )}
                  </div>
                </section>

                <section className="terminal-border bg-card p-6">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <h2 className="text-lg font-bold">RECENT BAR OUTPUT</h2>
                    <div className="text-xs text-muted-foreground">Last 25 rows</div>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[900px] text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                          <th className="pb-3 pr-4">Date</th>
                          <th className="pb-3 pr-4">Close</th>
                          <th className="pb-3 pr-4">Score</th>
                          <th className="pb-3 pr-4">Signal</th>
                          <th className="pb-3 pr-4">Position</th>
                          <th className="pb-3 pr-4">Strat Ret</th>
                          <th className="pb-3 pr-4">Equity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tableRows.map((row) => (
                          <tr key={String(row.Date)} className="border-b border-border/60">
                            <td className="py-3 pr-4 font-mono text-xs">{String(row.Date)}</td>
                            <td className="py-3 pr-4">{formatCurrency(Number(row.Close ?? 0))}</td>
                            <td className="py-3 pr-4">{formatNumber(Number(row.Score ?? 0))}</td>
                            <td className="py-3 pr-4">{formatNumber(Number(row.Signal ?? 0))}</td>
                            <td className="py-3 pr-4">{formatNumber(Number(row.Position ?? 0))}</td>
                            <td className="py-3 pr-4">
                              {formatPercent(Number(row.StratRet ?? 0) * 100, { mode: 'percent' })}
                            </td>
                            <td className="py-3 pr-4">{formatNumber(Number(row.Equity ?? 0))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
