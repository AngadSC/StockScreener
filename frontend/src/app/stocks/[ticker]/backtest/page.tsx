'use client';

import Link from 'next/link';
import { type ReactNode, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Check, ChevronDown, HelpCircle, Loader2, X } from 'lucide-react';
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
import { cn, formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/utils';
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
  help?: string;
  step?: number;
};

type IndicatorDef = {
  key: IndicatorKey;
  label: string;
  description: string;
  help: string;
  defaults: { enabled: boolean; weight: number; params: Record<string, number> };
  fields: FieldDef[];
};

const FIELD_HELP: Record<string, string> = {
  period: 'How many bars are used in the calculation. Larger values react more slowly.',
  buy_below: 'A buy signal is allowed only when the indicator falls below this level.',
  sell_above: 'A sell signal is allowed only when the indicator rises above this level.',
  buy_above: 'A buy signal is allowed only when the indicator rises above this level.',
  sell_below: 'A sell signal is allowed only when the indicator falls below this level.',
  fast: 'The shorter lookback window. It reacts faster to recent price moves.',
  slow: 'The longer lookback window. It smooths noise and defines the slower trend.',
  signal: 'The smoothing window for the signal line used to confirm crossovers.',
  k: 'Number of bars used for the fast stochastic %K calculation.',
  d: 'Smoothing window applied to %K to create the slower %D line.',
  adx_min: 'Minimum ADX strength required before crossover signals are accepted.',
  window: 'Rolling lookback window used by the indicator.',
  n_std: 'How many standard deviations define the upper and lower Bollinger Bands.',
  threshold: 'Cutoff value that flips the signal from bearish to bullish or vice versa.',
  close_pct: 'Minimum ATR as a share of closing price before trades are allowed.',
};

const RUN_SETTING_HELP = {
  long_threshold: 'When the combined weighted score rises above this value, the strategy can go long.',
  short_threshold: 'When the combined weighted score falls below this value, the strategy can go short.',
  exec_lag: 'How many bars to wait after a signal before the trade is executed. 0 means the same bar, 1 means the next bar.',
  tc_bps: 'Estimated transaction cost applied on each trade. 10 bps equals 0.10%.',
  weight: 'How much this indicator contributes to the combined score. Larger weights make it matter more.',
  allow_position_hold:
    'Keeps the current position until a new opposite signal appears instead of flattening between signals.',
  generate_plots: 'Requests rendered plot images from the backend for this backtest run.',
  generate_roc: 'Requests a ROC curve and AUC score so you can inspect signal quality.',
  atr_gate: 'Optional volatility filter. Trades only happen when ATR as a share of price is high enough.',
};

const INDICATORS: IndicatorDef[] = [
  {
    key: 'rsi',
    label: 'RSI Threshold',
    description: 'Buy oversold conditions and sell overbought conditions.',
    help: 'Relative Strength Index. It measures momentum on a 0 to 100 scale and is commonly used for reversal setups.',
    defaults: { enabled: true, weight: 1, params: { period: 14, buy_below: 30, sell_above: 70 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_below', label: 'Buy Below', step: 0.1 },
      { key: 'sell_above', label: 'Sell Above', step: 0.1 },
    ],
  },
  {
    key: 'stoch',
    label: 'Stochastic Crossover',
    description: 'Uses the %K and %D crossover for entries.',
    help: 'Stochastic Oscillator compares the close to the recent price range. It is often used to time momentum turns.',
    defaults: { enabled: false, weight: 1, params: { k: 14, d: 3 } },
    fields: [
      { key: 'k', label: 'K Window', step: 1 },
      { key: 'd', label: 'D Smooth', step: 1 },
    ],
  },
  {
    key: 'willr',
    label: 'Williams %R',
    description: 'Uses oversold and overbought thresholds for reversal trades.',
    help: 'Williams %R is a momentum oscillator similar to stochastic, but scaled from 0 to -100.',
    defaults: { enabled: false, weight: 1, params: { period: 14, buy_below: -80, sell_above: -20 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_below', label: 'Buy Below', step: 0.1 },
      { key: 'sell_above', label: 'Sell Above', step: 0.1 },
    ],
  },
  {
    key: 'roc',
    label: 'Rate of Change',
    description: 'Trades based on whether price momentum is positive or negative.',
    help: 'Rate of Change measures percentage price momentum over a chosen lookback window.',
    defaults: { enabled: false, weight: 1, params: { period: 12, buy_above: 0, sell_below: 0 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_above', label: 'Buy Above', step: 0.1 },
      { key: 'sell_below', label: 'Sell Below', step: 0.1 },
    ],
  },
  {
    key: 'tsi',
    label: 'True Strength Index',
    description: 'Uses smoothed momentum strength to filter long and short setups.',
    help: 'True Strength Index smooths price changes twice, which reduces noise versus raw momentum.',
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
    description: 'Uses the oscillator zero line as a bullish or bearish bias.',
    help: 'Awesome Oscillator compares fast and slow median-price averages to show momentum shifts.',
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
    description: 'Goes long when the fast SMA crosses above the slow SMA.',
    help: 'Simple moving average crossover. It is a classic trend-following signal with slower reactions than EMA.',
    defaults: { enabled: false, weight: 1, params: { fast: 10, slow: 50 } },
    fields: [
      { key: 'fast', label: 'Fast SMA', step: 1 },
      { key: 'slow', label: 'Slow SMA', step: 1 },
    ],
  },
  {
    key: 'ema_xo',
    label: 'EMA Crossover',
    description: 'Uses a faster-reacting moving average crossover.',
    help: 'Exponential moving average crossover. EMAs weight recent price action more heavily than SMAs.',
    defaults: { enabled: true, weight: 1, params: { fast: 12, slow: 26 } },
    fields: [
      { key: 'fast', label: 'Fast EMA', step: 1 },
      { key: 'slow', label: 'Slow EMA', step: 1 },
    ],
  },
  {
    key: 'macd',
    label: 'MACD Crossover',
    description: 'Uses the MACD line crossing its signal line.',
    help: 'Moving Average Convergence Divergence combines trend and momentum by comparing two EMAs and a signal line.',
    defaults: { enabled: true, weight: 1, params: { fast: 12, slow: 26, signal: 9 } },
    fields: [
      { key: 'fast', label: 'Fast', step: 1 },
      { key: 'slow', label: 'Slow', step: 1 },
      { key: 'signal', label: 'Signal', step: 1 },
    ],
  },
  {
    key: 'adx',
    label: 'ADX + DI Trend',
    description: 'Uses DI crossovers only when trend strength is high enough.',
    help: 'ADX measures trend strength. Combined with +DI and -DI, it filters directional moves in stronger markets.',
    defaults: { enabled: false, weight: 1, params: { period: 14, adx_min: 20 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'adx_min', label: 'ADX Min', step: 0.1 },
    ],
  },
  {
    key: 'aroon',
    label: 'Aroon Crossover',
    description: 'Tracks whether recent highs or lows are dominating.',
    help: 'Aroon measures how recently the market made new highs or lows to detect emerging trends.',
    defaults: { enabled: false, weight: 1, params: { period: 14 } },
    fields: [{ key: 'period', label: 'Period', step: 1 }],
  },
  {
    key: 'bbands',
    label: 'Bollinger Bands',
    description: 'Trades when price reaches statistically stretched band levels.',
    help: 'Bollinger Bands wrap price with a moving average and standard deviation bands to show volatility extremes.',
    defaults: { enabled: false, weight: 1, params: { window: 20, n_std: 2 } },
    fields: [
      { key: 'window', label: 'Window', step: 1 },
      { key: 'n_std', label: 'Std Dev', step: 0.1 },
    ],
  },
  {
    key: 'obv',
    label: 'OBV Slope',
    description: 'Uses the direction of volume flow rather than price alone.',
    help: 'On-Balance Volume accumulates volume based on price direction, which can highlight accumulation or distribution.',
    defaults: { enabled: false, weight: 1, params: { window: 5 } },
    fields: [{ key: 'window', label: 'Slope Window', step: 1 }],
  },
  {
    key: 'mfi',
    label: 'Money Flow Index',
    description: 'Combines price and volume to detect overbought or oversold reversals.',
    help: 'Money Flow Index is often described as a volume-weighted RSI.',
    defaults: { enabled: false, weight: 1, params: { period: 14, buy_below: 20, sell_above: 80 } },
    fields: [
      { key: 'period', label: 'Period', step: 1 },
      { key: 'buy_below', label: 'Buy Below', step: 0.1 },
      { key: 'sell_above', label: 'Sell Above', step: 0.1 },
    ],
  },
  {
    key: 'cmf',
    label: 'Chaikin Money Flow',
    description: 'Uses buying and selling pressure relative to volume.',
    help: 'Chaikin Money Flow measures whether volume is flowing into or out of the asset over time.',
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

function HelpHint({ text, className }: { text: string; className?: string }) {
  return (
    <details className={cn('group/help relative inline-block', className)}>
      <summary
        title={text}
        className="flex list-none cursor-pointer items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring [&::-webkit-details-marker]:hidden"
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </summary>
      <div className="absolute right-0 z-30 mt-2 w-64 rounded-md border border-border bg-background/95 p-3 text-xs leading-relaxed text-muted-foreground shadow-xl backdrop-blur">
        {text}
      </div>
    </details>
  );
}

function LabeledField({
  label,
  help,
  children,
}: {
  label: string;
  help?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-2 text-muted-foreground">
        <span>{label}</span>
        {help ? <HelpHint text={help} /> : null}
      </div>
      {children}
    </div>
  );
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
  const selectedIndicators = INDICATORS.filter((indicator) => request.indicators[indicator.key]?.enabled);
  const tableRows = (result?.results ?? []).slice(-25).reverse();

  const setIndicatorEnabled = (key: IndicatorKey, enabled: boolean) => {
    setRequest((prev) => ({
      ...prev,
      indicators: {
        ...prev.indicators,
        [key]: {
          ...prev.indicators[key],
          enabled,
        },
      },
    }));
  };

  const setIndicatorWeight = (key: IndicatorKey, value: string) => {
    setRequest((prev) => ({
      ...prev,
      indicators: {
        ...prev.indicators,
        [key]: {
          ...prev.indicators[key],
          weight: parseNumber(value, prev.indicators[key].weight),
        },
      },
    }));
  };

  const setIndicatorParam = (key: IndicatorKey, paramKey: string, value: string) => {
    setRequest((prev) => ({
      ...prev,
      indicators: {
        ...prev.indicators,
        [key]: {
          ...prev.indicators[key],
          params: {
            ...prev.indicators[key].params,
            [paramKey]: parseNumber(value, Number(prev.indicators[key].params[paramKey] ?? 0)),
          },
        },
      },
    }));
  };

  const setAllIndicators = (enabled: boolean) => {
    setRequest((prev) => ({
      ...prev,
      indicators: Object.fromEntries(
        INDICATORS.map((indicator) => [
          indicator.key,
          {
            ...prev.indicators[indicator.key],
            enabled,
          },
        ])
      ),
    }));
  };

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
                <LabeledField label="Start Date">
                  <Input
                    type="date"
                    value={request.start_date}
                    onChange={(event) => setRequest((prev) => ({ ...prev, start_date: event.target.value }))}
                  />
                </LabeledField>
                <LabeledField label="End Date">
                  <Input
                    type="date"
                    value={request.end_date}
                    onChange={(event) => setRequest((prev) => ({ ...prev, end_date: event.target.value }))}
                  />
                </LabeledField>
                <LabeledField label="Long Score Trigger" help={RUN_SETTING_HELP.long_threshold}>
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
                </LabeledField>
                <LabeledField label="Short Score Trigger" help={RUN_SETTING_HELP.short_threshold}>
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
                </LabeledField>
                <LabeledField label="Trade Delay (bars)" help={RUN_SETTING_HELP.exec_lag}>
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
                </LabeledField>
                <LabeledField label="Cost Per Trade (bps)" help={RUN_SETTING_HELP.tc_bps}>
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
                </LabeledField>
              </div>

              <div className="rounded border border-border bg-muted/10 p-4 text-sm text-muted-foreground">
                <div className="font-semibold text-foreground">How the score works</div>
                <p className="mt-2">
                  Enabled indicators each produce a bullish or bearish vote. Their weights are combined into one score,
                  then the strategy trades only when that score clears the long or short trigger you set above.
                </p>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded border border-border bg-muted/10 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 font-semibold">
                        <span>ATR Volatility Gate</span>
                        <HelpHint text={RUN_SETTING_HELP.atr_gate} />
                      </div>
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
                    <LabeledField label="ATR Period" help={FIELD_HELP.period}>
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
                    </LabeledField>
                    <LabeledField label="Min ATR/Close" help={FIELD_HELP.close_pct}>
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
                    </LabeledField>
                  </div>
                </div>

                <div className="rounded border border-border bg-muted/10 p-4 space-y-3">
                  <div className="font-semibold">Execution Flags</div>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <span>Allow position hold between signals</span>
                      <HelpHint text={RUN_SETTING_HELP.allow_position_hold} />
                    </div>
                    <input
                      type="checkbox"
                      checked={request.allow_position_hold}
                      onChange={(event) =>
                        setRequest((prev) => ({ ...prev, allow_position_hold: event.target.checked }))
                      }
                      className="h-4 w-4 accent-primary"
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <span>Generate backend plot images</span>
                      <HelpHint text={RUN_SETTING_HELP.generate_plots} />
                    </div>
                    <input
                      type="checkbox"
                      checked={request.generate_plots}
                      onChange={(event) => setRequest((prev) => ({ ...prev, generate_plots: event.target.checked }))}
                      className="h-4 w-4 accent-primary"
                    />
                  </div>
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <span>Generate ROC curve</span>
                      <HelpHint text={RUN_SETTING_HELP.generate_roc} />
                    </div>
                    <input
                      type="checkbox"
                      checked={request.generate_roc}
                      onChange={(event) => setRequest((prev) => ({ ...prev, generate_roc: event.target.checked }))}
                      className="h-4 w-4 accent-primary"
                    />
                  </div>
                </div>
              </div>
            </section>

            <section className="terminal-border bg-card p-6 space-y-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h2 className="text-lg font-bold">INDICATOR LAB</h2>
                  <p className="text-sm text-muted-foreground">
                    Pick one or many indicators from the menu, then tune only the ones you actually want to use.
                  </p>
                </div>
                <details className="group relative w-full max-w-xl">
                  <summary className="flex list-none cursor-pointer items-center justify-between gap-3 rounded-md border border-border bg-muted/10 px-4 py-3 text-sm transition-colors hover:border-primary/40 hover:bg-muted/20 [&::-webkit-details-marker]:hidden">
                    <div className="min-w-0">
                      <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Select Indicators</div>
                      <div className="mt-1 truncate font-medium text-foreground">
                        {selectedIndicators.length > 0
                          ? selectedIndicators.map((indicator) => indicator.label).join(', ')
                          : 'Choose one or more indicators'}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="rounded border border-border px-2 py-1 text-xs text-muted-foreground">
                        {selectedCount} selected
                      </span>
                      <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180" />
                    </div>
                  </summary>
                  <div className="absolute left-0 right-0 z-20 mt-2 rounded-md border border-border bg-background/95 p-3 shadow-2xl backdrop-blur">
                    <div className="flex items-center justify-between gap-3 border-b border-border/70 pb-3">
                      <div className="text-xs text-muted-foreground">
                        Check as many indicators as you want. The strategy will combine them into a single score.
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setAllIndicators(true)}
                          className="text-xs text-primary transition-colors hover:text-primary/80"
                        >
                          Select all
                        </button>
                        <button
                          type="button"
                          onClick={() => setAllIndicators(false)}
                          className="text-xs text-muted-foreground transition-colors hover:text-foreground"
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                    <div className="mt-3 grid max-h-80 gap-2 overflow-y-auto pr-1">
                      {INDICATORS.map((indicator) => {
                        const enabled = request.indicators[indicator.key].enabled;
                        return (
                          <label
                            key={indicator.key}
                            className={cn(
                              'flex cursor-pointer items-start justify-between gap-3 rounded-md border px-3 py-3 transition-colors',
                              enabled
                                ? 'border-primary/40 bg-primary/5'
                                : 'border-border bg-muted/5 hover:bg-muted/10'
                            )}
                          >
                            <div className="flex items-start gap-3">
                              <input
                                type="checkbox"
                                checked={enabled}
                                onChange={(event) => setIndicatorEnabled(indicator.key, event.target.checked)}
                                className="mt-1 h-4 w-4 accent-primary"
                              />
                              <div>
                                <div className="font-medium text-foreground">{indicator.label}</div>
                                <div className="mt-1 text-xs text-muted-foreground">{indicator.description}</div>
                              </div>
                            </div>
                            {enabled ? <Check className="mt-0.5 h-4 w-4 text-primary" /> : null}
                          </label>
                        );
                      })}
                    </div>
                  </div>
                </details>
              </div>

              <div className="flex flex-wrap gap-2">
                {selectedIndicators.length > 0 ? (
                  selectedIndicators.map((indicator) => (
                    <button
                      key={indicator.key}
                      type="button"
                      onClick={() => setIndicatorEnabled(indicator.key, false)}
                      className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs text-primary transition-colors hover:bg-primary/15"
                    >
                      <span>{indicator.label}</span>
                      <X className="h-3.5 w-3.5" />
                    </button>
                  ))
                ) : (
                  <div className="rounded border border-dashed border-border px-4 py-3 text-sm text-muted-foreground">
                    No indicators selected yet. Open the menu above and choose the signals you want to combine.
                  </div>
                )}
              </div>

              <p className="text-sm text-muted-foreground">
                Each selected indicator can be weighted and customized below. Hover or click the help icon beside any
                name to see what it does.
              </p>

              {selectedIndicators.length > 0 ? (
                <div className="grid gap-4 xl:grid-cols-2">
                  {selectedIndicators.map((indicator) => {
                    const config = request.indicators[indicator.key];
                    return (
                      <div key={indicator.key} className="rounded border border-border bg-muted/10 p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <div className="font-semibold">{indicator.label}</div>
                              <HelpHint text={indicator.help} />
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">{indicator.description}</div>
                          </div>
                          <button
                            type="button"
                            onClick={() => setIndicatorEnabled(indicator.key, false)}
                            className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
                          >
                            <X className="h-3.5 w-3.5" />
                            Remove
                          </button>
                        </div>
                        <div className="mt-4 grid gap-3">
                          <LabeledField label="Weight" help={RUN_SETTING_HELP.weight}>
                            <Input
                              type="number"
                              step="0.1"
                              value={config.weight}
                              onChange={(event) => setIndicatorWeight(indicator.key, event.target.value)}
                            />
                          </LabeledField>
                          <div className="grid gap-3 sm:grid-cols-2">
                            {indicator.fields.map((field) => (
                              <LabeledField
                                key={field.key}
                                label={field.label}
                                help={field.help ?? FIELD_HELP[field.key]}
                              >
                                <Input
                                  type="number"
                                  step={field.step ?? 1}
                                  value={Number(config.params[field.key] ?? 0)}
                                  onChange={(event) => setIndicatorParam(indicator.key, field.key, event.target.value)}
                                />
                              </LabeledField>
                            ))}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : null}
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
