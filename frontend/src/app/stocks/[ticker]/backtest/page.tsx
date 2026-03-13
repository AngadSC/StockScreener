'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Info, Loader2, RefreshCcw } from 'lucide-react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { stocksAPI } from '@/lib/api';
import { cn, formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/utils';
import type { BacktestObjective, BacktestRunRequest, BacktestStrategyFamily } from '@/types/stock';

type StrategyField = {
  key: string;
  label: string;
  step: number;
  help: string;
};

type StrategyDef = {
  family: BacktestStrategyFamily;
  label: string;
  description: string;
  bestFor: string;
  watchFor: string;
  starterValues: string;
  defaults: Record<string, number>;
  fields: StrategyField[];
};

type ExamplePreset = {
  label: string;
  description: string;
  apply: (ticker: string) => Partial<BacktestRunRequest>;
};

type MetricGuide = {
  key: string;
  label: string;
  meaning: string;
  example: string;
};

const STRATEGIES: StrategyDef[] = [
  {
    family: 'trend_following',
    label: 'Trend Following',
    description: 'Buys when a fast EMA crosses above a slow EMA and exits on the reverse cross.',
    bestFor: 'Long trends in large-cap names and index leaders.',
    watchFor: 'Can whipsaw in sideways markets.',
    starterValues: 'Fast EMA 50, Slow EMA 200 on daily bars.',
    defaults: { fast_ema: 50, slow_ema: 200 },
    fields: [
      { key: 'fast_ema', label: 'Fast EMA', step: 1, help: 'Smaller values react faster but create more signals.' },
      { key: 'slow_ema', label: 'Slow EMA', step: 1, help: 'Larger values smooth noise and define the primary trend.' },
    ],
  },
  {
    family: 'mean_reversion',
    label: 'Mean Reversion',
    description: 'Buys when price touches the lower Bollinger Band and exits near the middle band.',
    bestFor: 'Range-bound stocks, ETFs, and calmer market regimes.',
    watchFor: 'Can keep buying into real breakdowns during strong selloffs.',
    starterValues: 'Window 20, Std Dev 2.0.',
    defaults: { window: 20, std_dev: 2 },
    fields: [
      { key: 'window', label: 'Band Window', step: 1, help: 'Higher values smooth the band calculation.' },
      { key: 'std_dev', label: 'Std Dev', step: 0.1, help: 'Higher values require a larger oversold move before entry.' },
    ],
  },
  {
    family: 'momentum_breakout',
    label: 'Momentum Breakout',
    description: 'Buys when price closes above a recent high and exits on a breakdown below a recent low.',
    bestFor: 'Fast-moving leaders with clean breakouts.',
    watchFor: 'False breakouts increase when volatility is high.',
    starterValues: 'Breakout 50, Exit 20.',
    defaults: { breakout_lookback: 50, exit_lookback: 20 },
    fields: [
      { key: 'breakout_lookback', label: 'Breakout Lookback', step: 1, help: 'How far back the strategy looks for resistance.' },
      { key: 'exit_lookback', label: 'Exit Lookback', step: 1, help: 'Shorter exits lock gains faster but can cut winners early.' },
    ],
  },
  {
    family: 'oversold_reversal',
    label: 'Oversold Reversal',
    description: 'Uses RSI to buy oversold conditions and exit once momentum normalizes.',
    bestFor: 'Short swing trades after sharp pullbacks.',
    watchFor: 'Oversold can stay oversold in strong downtrends.',
    starterValues: 'RSI 14, Entry 30, Exit 50.',
    defaults: { rsi_period: 14, entry_rsi: 30, exit_rsi: 50 },
    fields: [
      { key: 'rsi_period', label: 'RSI Period', step: 1, help: 'Shorter periods make RSI more sensitive.' },
      { key: 'entry_rsi', label: 'Entry RSI', step: 0.1, help: 'Lower values wait for deeper pullbacks before entering.' },
      { key: 'exit_rsi', label: 'Exit RSI', step: 0.1, help: 'Higher values hold longer after the bounce starts.' },
    ],
  },
  {
    family: 'moving_average_pullback',
    label: 'Moving Average Pullback',
    description: 'Buys pullbacks toward a shorter moving average while price stays above a longer trend filter.',
    bestFor: 'Trending stocks that regularly pull back and resume higher.',
    watchFor: 'Weak trends can trigger entries without follow-through.',
    starterValues: 'Trend MA 200, Pullback MA 20, Buffer 0.01.',
    defaults: { trend_ma: 200, pullback_ma: 20, entry_buffer_pct: 0.01 },
    fields: [
      { key: 'trend_ma', label: 'Trend MA', step: 1, help: 'Defines whether the market is in an uptrend.' },
      { key: 'pullback_ma', label: 'Pullback MA', step: 1, help: 'Tracks the shorter-term mean you want price to revisit.' },
      { key: 'entry_buffer_pct', label: 'Entry Buffer', step: 0.001, help: 'Lets price sit slightly above the pullback average instead of touching it exactly.' },
    ],
  },
  {
    family: 'volume_breakout',
    label: 'Volume Breakout',
    description: 'Requires both a price breakout and a volume surge before entering.',
    bestFor: 'Breakouts where confirmation matters more than early entry.',
    watchFor: 'Volume spikes around news can create one-bar traps.',
    starterValues: 'Breakout 20, Exit 10, Volume Window 20, Multiplier 2.0.',
    defaults: { breakout_lookback: 20, exit_lookback: 10, volume_window: 20, volume_multiplier: 2 },
    fields: [
      { key: 'breakout_lookback', label: 'Breakout Lookback', step: 1, help: 'Number of bars used to define resistance.' },
      { key: 'exit_lookback', label: 'Exit Lookback', step: 1, help: 'Number of bars used to define the breakdown exit.' },
      { key: 'volume_window', label: 'Volume Window', step: 1, help: 'Average volume period used for confirmation.' },
      { key: 'volume_multiplier', label: 'Volume Multiplier', step: 0.1, help: 'How much volume must exceed average to confirm the move.' },
    ],
  },
  {
    family: 'golden_cross',
    label: 'Golden Cross',
    description: 'Classic SMA crossover that enters on a fast SMA cross above a slower SMA.',
    bestFor: 'Investors who want a slower, cleaner trend system.',
    watchFor: 'Signals arrive later than EMA-based systems.',
    starterValues: 'Fast SMA 50, Slow SMA 200.',
    defaults: { fast_sma: 50, slow_sma: 200 },
    fields: [
      { key: 'fast_sma', label: 'Fast SMA', step: 1, help: 'The shorter smoothing period for the crossover.' },
      { key: 'slow_sma', label: 'Slow SMA', step: 1, help: 'The longer smoothing period that defines the primary regime.' },
    ],
  },
  {
    family: 'macd_trend',
    label: 'MACD Trend',
    description: 'Uses a MACD crossover with a zero-line filter so entries favor positive momentum.',
    bestFor: 'Momentum traders who want trend confirmation without using price breakouts.',
    watchFor: 'Late exits can give back gains after sharp reversals.',
    starterValues: 'Fast EMA 12, Slow EMA 26, Signal 9.',
    defaults: { fast_ema: 12, slow_ema: 26, signal_period: 9 },
    fields: [
      { key: 'fast_ema', label: 'Fast EMA', step: 1, help: 'The faster EMA inside the MACD calculation.' },
      { key: 'slow_ema', label: 'Slow EMA', step: 1, help: 'The slower EMA inside the MACD calculation.' },
      { key: 'signal_period', label: 'Signal Period', step: 1, help: 'Smoothing period for the MACD signal line.' },
    ],
  },
  {
    family: 'rsi_trend_filter',
    label: 'RSI Trend Filter',
    description: 'Only buys RSI strength when price is already above a longer-term moving average.',
    bestFor: 'Traders who want momentum entries but with a broad trend filter.',
    watchFor: 'Can miss deep pullback entries because it demands trend confirmation.',
    starterValues: 'Trend MA 200, RSI 14, Entry 55, Exit 45.',
    defaults: { trend_ma: 200, rsi_period: 14, entry_rsi: 55, exit_rsi: 45 },
    fields: [
      { key: 'trend_ma', label: 'Trend MA', step: 1, help: 'Long-term trend filter that price must stay above for entry.' },
      { key: 'rsi_period', label: 'RSI Period', step: 1, help: 'RSI lookback used to measure momentum.' },
      { key: 'entry_rsi', label: 'Entry RSI', step: 0.1, help: 'Momentum threshold price must reclaim before entering.' },
      { key: 'exit_rsi', label: 'Exit RSI', step: 0.1, help: 'Momentum threshold that ends the trade when lost.' },
    ],
  },
];

const OBJECTIVES: Array<{ value: BacktestObjective; label: string }> = [
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'cagr_pct', label: 'CAGR' },
  { value: 'total_return_pct', label: 'Total Return' },
  { value: 'profit_factor', label: 'Profit Factor' },
  { value: 'expectancy_pct', label: 'Expectancy' },
  { value: 'win_rate_pct', label: 'Win Rate' },
  { value: 'max_drawdown_pct', label: 'Lowest Drawdown' },
];

const STAT_LABELS: Record<string, string> = {
  initial_capital: 'Initial Capital',
  final_equity: 'Final Equity',
  total_return_pct: 'Total Return',
  cagr_pct: 'CAGR',
  max_drawdown_pct: 'Max Drawdown',
  win_rate_pct: 'Win Rate',
  average_trade_return_pct: 'Avg Trade Return',
  profit_factor: 'Profit Factor',
  sharpe_ratio: 'Sharpe Ratio',
  trade_count: 'Trade Count',
  average_holding_period_bars: 'Avg Holding',
  expectancy_pct: 'Expectancy',
};

const METRIC_GUIDE: MetricGuide[] = [
  {
    key: 'total_return_pct',
    label: 'Total Return',
    meaning: 'Net percentage gain or loss from the start of the backtest to the end.',
    example: 'Example: 42% means $10,000 grew to about $14,200 before taxes.',
  },
  {
    key: 'cagr_pct',
    label: 'CAGR',
    meaning: 'Annualized growth rate that smooths the result across the full test period.',
    example: 'Example: 12% CAGR is a strong long-term result if drawdowns stay reasonable.',
  },
  {
    key: 'max_drawdown_pct',
    label: 'Max Drawdown',
    meaning: 'Largest peak-to-trough decline during the test. Lower is generally easier to live with.',
    example: 'Example: -18% is manageable for many swing systems, while -45% is severe.',
  },
  {
    key: 'sharpe_ratio',
    label: 'Sharpe Ratio',
    meaning: 'Return earned per unit of volatility. Higher means smoother risk-adjusted returns.',
    example: 'Example: 1.0 is decent, 1.5+ is strong, 2.0+ is rare.',
  },
  {
    key: 'profit_factor',
    label: 'Profit Factor',
    meaning: 'Gross profit divided by gross loss across all closed trades.',
    example: 'Example: 1.3 is usable, 1.8 is good, below 1.0 loses money.',
  },
  {
    key: 'win_rate_pct',
    label: 'Win Rate',
    meaning: 'Percentage of closed trades that finished positive.',
    example: 'Example: 40% can still work if winners are much larger than losers.',
  },
  {
    key: 'average_trade_return_pct',
    label: 'Avg Trade Return',
    meaning: 'Average percentage return per closed trade after costs.',
    example: 'Example: 1.2% average trade return is meaningful if it scales across many trades.',
  },
  {
    key: 'expectancy_pct',
    label: 'Expectancy',
    meaning: 'Expected percentage return per trade after blending win rate and average win/loss size.',
    example: 'Example: 0.4% expectancy means the setup earns about 0.4% per trade on average.',
  },
  {
    key: 'trade_count',
    label: 'Trade Count',
    meaning: 'Number of closed trades. Too few trades means the sample may not be reliable.',
    example: 'Example: 8 trades in five years is thin; 100+ trades gives more confidence.',
  },
  {
    key: 'average_holding_period_bars',
    label: 'Avg Holding',
    meaning: 'Average time a trade stays open, measured in bars of the selected timeframe.',
    example: 'Example: 18 daily bars is about three to four trading weeks.',
  },
];

const EXAMPLE_PRESETS: ExamplePreset[] = [
  {
    label: 'Beginner Trend',
    description: 'Simple long-only trend setup with a benchmark and mild trailing stop.',
    apply: (ticker) => ({
      tickers: [ticker],
      allocation_weights: { [ticker]: 100 },
      timeframe: '1d',
      initial_capital: 10000,
      tc_bps: 5,
      strategy: { family: 'trend_following', params: { fast_ema: 50, slow_ema: 200 } },
      risk_controls: { stop_loss_pct: null, trailing_stop_pct: 0.12, take_profit_pct: null },
      include_buy_and_hold: true,
    }),
  },
  {
    label: 'Swing Rebound',
    description: 'Shorter-term reversal setup for users testing oversold bounces.',
    apply: (ticker) => ({
      tickers: [ticker],
      allocation_weights: { [ticker]: 100 },
      timeframe: '1d',
      initial_capital: 10000,
      tc_bps: 5,
      strategy: { family: 'oversold_reversal', params: { rsi_period: 14, entry_rsi: 28, exit_rsi: 52 } },
      risk_controls: { stop_loss_pct: 0.08, trailing_stop_pct: null, take_profit_pct: 0.15 },
      include_buy_and_hold: true,
    }),
  },
  {
    label: 'Breakout Basket',
    description: 'Weekly basket setup for traders comparing diversified momentum names.',
    apply: (ticker) => ({
      tickers: [ticker],
      allocation_weights: { [ticker]: 100 },
      timeframe: '1wk',
      initial_capital: 25000,
      tc_bps: 10,
      strategy: { family: 'volume_breakout', params: { breakout_lookback: 20, exit_lookback: 10, volume_window: 20, volume_multiplier: 1.5 } },
      risk_controls: { stop_loss_pct: 0.1, trailing_stop_pct: 0.15, take_profit_pct: null },
      include_buy_and_hold: true,
    }),
  },
];

const toInputDate = (date: Date) => date.toISOString().slice(0, 10);

const parseNumber = (value: string, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const parseOptionalNumber = (value: string) => {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const normalizeBasketTickers = (primaryTicker: string, basketInput: string) => {
  const ordered: string[] = [];
  const seen = new Set<string>();
  for (const raw of [primaryTicker, ...basketInput.split(',')]) {
    const symbol = raw.trim().toUpperCase();
    if (!symbol || seen.has(symbol)) continue;
    seen.add(symbol);
    ordered.push(symbol);
  }
  return ordered;
};

const buildEqualWeights = (tickers: string[]) => {
  if (tickers.length === 0) return {};
  const base = Number((100 / tickers.length).toFixed(4));
  const weights: Record<string, number> = Object.fromEntries(tickers.map((symbol) => [symbol, base]));
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  weights[tickers[tickers.length - 1]] = Number((weights[tickers[tickers.length - 1]] + (100 - total)).toFixed(4));
  return weights;
};

const syncWeightsToTickers = (tickers: string[], existing: Record<string, number>) => {
  const filtered = Object.fromEntries(
    tickers
      .filter((symbol) => Number.isFinite(existing[symbol]))
      .map((symbol) => [symbol, Number(existing[symbol])])
  );

  if (Object.keys(filtered).length === 0) {
    return buildEqualWeights(tickers);
  }

  const missing = tickers.filter((symbol) => filtered[symbol] == null);
  const specifiedTotal = Object.values(filtered).reduce((sum, value) => sum + value, 0);
  const remaining = Math.max(0, Number((100 - specifiedTotal).toFixed(4)));

  if (missing.length === 0) {
    return filtered;
  }

  const fill = Number((remaining / missing.length).toFixed(4));
  const next = { ...filtered };
  for (const symbol of missing) {
    next[symbol] = fill;
  }
  const total = Object.values(next).reduce((sum, value) => sum + value, 0);
  next[missing[missing.length - 1]] = Number((next[missing[missing.length - 1]] + (100 - total)).toFixed(4));
  return next;
};

const areWeightsEqual = (left: Record<string, number>, right: Record<string, number>, tickers: string[]) =>
  tickers.every((symbol) => Math.abs((left[symbol] ?? 0) - (right[symbol] ?? 0)) < 0.0001);

function createDefaultRequest(ticker: string): BacktestRunRequest {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(end.getFullYear() - 5);
  return {
    start_date: toInputDate(start),
    end_date: toInputDate(end),
    tickers: [ticker],
    allocation_weights: { [ticker]: 100 },
    timeframe: '1d',
    initial_capital: 10000,
    tc_bps: 5,
    allow_fractional_shares: true,
    strategy: { family: 'trend_following', params: { fast_ema: 50, slow_ema: 200 } },
    risk_controls: { stop_loss_pct: null, trailing_stop_pct: null, take_profit_pct: null },
    tuning: { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} },
    include_buy_and_hold: true,
    generate_plots: true,
  };
}

function Field({ label, help, children }: { label: string; help?: string; children: ReactNode }) {
  return (
    <label className="space-y-2 text-sm">
      <div className="font-medium text-foreground">{label}</div>
      {children}
      {help ? <div className="text-xs leading-relaxed text-muted-foreground">{help}</div> : null}
    </label>
  );
}

function StatCard({ statKey, value }: { statKey: string; value: number }) {
  const label = STAT_LABELS[statKey] ?? statKey;
  let formatted = formatNumber(value);
  if (statKey === 'initial_capital' || statKey === 'final_equity') formatted = formatCurrency(value);
  if (statKey.endsWith('_pct')) formatted = formatPercent(value, { mode: 'percent', withSign: statKey !== 'max_drawdown_pct' });
  return (
    <div className="rounded border border-border bg-muted/10 p-4">
      <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</div>
      <div className="mt-2 text-xl font-semibold text-foreground">{formatted}</div>
    </div>
  );
}

function GuideCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded border border-border bg-muted/10 p-4">
      <div className="text-sm font-semibold text-foreground">{title}</div>
      <div className="mt-2 space-y-2 text-sm leading-relaxed text-muted-foreground">{children}</div>
    </div>
  );
}

interface PageProps {
  params: { ticker: string };
}

export default function StockBacktestPage({ params }: PageProps) {
  const ticker = params.ticker.toUpperCase();
  const [request, setRequest] = useState<BacktestRunRequest>(() => createDefaultRequest(ticker));
  const [basketInput, setBasketInput] = useState(ticker);

  const resolvedTickers = useMemo(() => normalizeBasketTickers(ticker, basketInput), [basketInput, ticker]);

  useEffect(() => {
    setRequest((prev) => {
      const nextWeights = syncWeightsToTickers(resolvedTickers, prev.allocation_weights ?? {});
      const sameTickers =
        prev.tickers.length === resolvedTickers.length &&
        prev.tickers.every((symbol, index) => symbol === resolvedTickers[index]);

      if (sameTickers && areWeightsEqual(prev.allocation_weights ?? {}, nextWeights, resolvedTickers)) {
        return prev;
      }

      return {
        ...prev,
        tickers: resolvedTickers,
        allocation_weights: nextWeights,
      };
    });
  }, [resolvedTickers]);

  const { data: stock } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => stocksAPI.getStock(ticker),
  });

  const strategy = useMemo(
    () => STRATEGIES.find((item) => item.family === request.strategy.family) ?? STRATEGIES[0],
    [request.strategy.family]
  );

  const mutation = useMutation({
    mutationFn: (payload: BacktestRunRequest) => stocksAPI.runBacktest(ticker, payload),
  });

  const totalAllocation = resolvedTickers.reduce((sum, symbol) => sum + Number(request.allocation_weights?.[symbol] ?? 0), 0);
  const cashReservePct = Math.max(0, Number((100 - totalAllocation).toFixed(2)));
  const allocationOverweight = totalAllocation > 100.0001;

  const result = mutation.data;
  const equityData = (result?.equity_curve ?? []).map((row) => ({
    date: String(row.Date ?? ''),
    strategy: Number(row.Equity ?? 0),
    benchmark: row.BuyHoldEquity == null ? null : Number(row.BuyHoldEquity),
  }));

  const setStrategyFamily = (family: BacktestStrategyFamily) => {
    const next = STRATEGIES.find((item) => item.family === family) ?? STRATEGIES[0];
    setRequest((prev) => ({
      ...prev,
      strategy: { family: next.family, params: { ...next.defaults } },
      tuning: {
        ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }),
        parameter_ranges: {},
      },
    }));
  };

  const setWeight = (symbol: string, value: string) => {
    setRequest((prev) => ({
      ...prev,
      allocation_weights: {
        ...(prev.allocation_weights ?? {}),
        [symbol]: Math.max(0, parseNumber(value, Number(prev.allocation_weights?.[symbol] ?? 0))),
      },
    }));
  };

  const resetDefaults = () => {
    setRequest(createDefaultRequest(ticker));
    setBasketInput(ticker);
  };

  const applyPreset = (preset: ExamplePreset) => {
    const next = preset.apply(ticker);
    const nextTickers = next.tickers ?? [ticker];
    setRequest((prev) => ({
      ...prev,
      ...next,
      tickers: nextTickers,
      allocation_weights: syncWeightsToTickers(nextTickers, next.allocation_weights ?? {}),
    }));
    setBasketInput(nextTickers.join(', '));
  };

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const riskControls = Object.fromEntries(
      Object.entries(request.risk_controls ?? {}).filter(([, value]) => value !== null && value !== undefined)
    );
    const parameterRanges = Object.fromEntries(
      Object.entries(request.tuning?.parameter_ranges ?? {}).filter(([, range]) => range.min != null && range.max != null && range.step != null)
    );
    const allocationWeights = Object.fromEntries(
      resolvedTickers.map((symbol) => [symbol, Number((request.allocation_weights?.[symbol] ?? 0).toFixed(4))])
    );

    mutation.mutate({
      ...request,
      tickers: resolvedTickers,
      allocation_weights: allocationWeights,
      risk_controls: riskControls,
      tuning: request.tuning ? { ...request.tuning, parameter_ranges: parameterRanges } : undefined,
    });
  };

  return (
    <div className="container space-y-6 py-6">
      <div className="flex items-center justify-between gap-4">
        <Link href={`/stocks/${ticker}`} className="inline-flex items-center gap-2 text-xs text-muted-foreground transition-colors hover:text-primary">
          <ArrowLeft className="h-3.5 w-3.5" />
          BACK_TO_STOCK
        </Link>
        <Button variant="outline" onClick={resetDefaults}>
          <RefreshCcw className="h-4 w-4" />
          RESET_DEFAULTS
        </Button>
      </div>

      <section className="terminal-border bg-card p-8">
        <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Portfolio Backtester</div>
        <h1 className="mt-3 text-4xl font-bold text-glow">{ticker}</h1>
        <p className="mt-2 max-w-4xl text-muted-foreground">
          {stock?.name ?? 'Test one stock or a full basket with strategy rules, position sizing, risk controls, tuning, and buy-and-hold comparison.'}
        </p>
        <div className="mt-5 grid gap-3 lg:grid-cols-3">
          {EXAMPLE_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => applyPreset(preset)}
              className="rounded border border-border bg-muted/10 p-4 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
            >
              <div className="text-sm font-semibold text-foreground">{preset.label}</div>
              <div className="mt-2 text-sm text-muted-foreground">{preset.description}</div>
            </button>
          ))}
        </div>
      </section>

      <form className="grid gap-6 xl:grid-cols-[1.06fr_0.94fr]" onSubmit={onSubmit}>
        <div className="space-y-6">
          <section className="terminal-border space-y-5 bg-card p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold">Run Config</h2>
                <p className="text-sm text-muted-foreground">Choose the basket, date range, capital, timeframe, and whether to compare against buy-and-hold.</p>
              </div>
              <Button type="submit" disabled={mutation.isPending || allocationOverweight}>
                {mutation.isPending ? <><Loader2 className="h-4 w-4 animate-spin" />RUNNING</> : 'RUN BACKTEST'}
              </Button>
            </div>

            <Field
              label="Basket Tickers"
              help="Comma-separated symbols. The stock page ticker stays in the basket automatically so you always test the current name."
            >
              <textarea
                value={basketInput}
                onChange={(event) => setBasketInput(event.target.value.toUpperCase())}
                className="min-h-[88px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </Field>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <Field label="Start Date" help="Beginners can start with 3 to 5 years for daily systems.">
                <Input type="date" value={request.start_date} onChange={(event) => setRequest((prev) => ({ ...prev, start_date: event.target.value }))} />
              </Field>
              <Field label="End Date" help="Usually leave this at the latest available date.">
                <Input type="date" value={request.end_date} onChange={(event) => setRequest((prev) => ({ ...prev, end_date: event.target.value }))} />
              </Field>
              <Field label="Timeframe" help="Daily is best for learning. Weekly is useful for slower swing or position systems.">
                <select
                  value={request.timeframe}
                  onChange={(event) => setRequest((prev) => ({ ...prev, timeframe: event.target.value as BacktestRunRequest['timeframe'] }))}
                  className="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value="1d">Daily</option>
                  <option value="1wk">Weekly</option>
                  <option value="1mo">Monthly</option>
                </select>
              </Field>
              <Field label="Starting Capital" help="Example: start with 10000 for a small test account or 25000 for a multi-stock basket.">
                <Input type="number" step="100" value={request.initial_capital} onChange={(event) => setRequest((prev) => ({ ...prev, initial_capital: parseNumber(event.target.value, prev.initial_capital) }))} />
              </Field>
              <Field label="Transaction Cost (bps)" help="5 bps means 0.05% per trade. Use 5 to 15 for a realistic starter test.">
                <Input type="number" step="1" value={request.tc_bps} onChange={(event) => setRequest((prev) => ({ ...prev, tc_bps: parseNumber(event.target.value, prev.tc_bps) }))} />
              </Field>
              <label className="flex items-center justify-between rounded border border-border bg-muted/10 px-3 py-3 text-sm">
                <div>
                  <div className="font-medium text-foreground">Fractional Shares</div>
                  <div className="mt-1 text-xs text-muted-foreground">Leave on for realistic ETF and high-price stock sizing.</div>
                </div>
                <input type="checkbox" checked={request.allow_fractional_shares} onChange={(event) => setRequest((prev) => ({ ...prev, allow_fractional_shares: event.target.checked }))} className="h-4 w-4 accent-primary" />
              </label>
              <label className="flex items-center justify-between rounded border border-border bg-muted/10 px-3 py-3 text-sm">
                <div>
                  <div className="font-medium text-foreground">Buy &amp; Hold Line</div>
                  <div className="mt-1 text-xs text-muted-foreground">Shows what the same basket would do if you bought it and held for the full test.</div>
                </div>
                <input type="checkbox" checked={request.include_buy_and_hold} onChange={(event) => setRequest((prev) => ({ ...prev, include_buy_and_hold: event.target.checked }))} className="h-4 w-4 accent-primary" />
              </label>
            </div>
          </section>

          <section className="terminal-border space-y-5 bg-card p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold">Portfolio Weights</h2>
                <p className="text-sm text-muted-foreground">Set the target percentage for each ticker. If the total is below 100%, the unused amount stays in cash.</p>
              </div>
              <Button type="button" variant="outline" onClick={() => setRequest((prev) => ({ ...prev, allocation_weights: buildEqualWeights(resolvedTickers) }))}>
                EQUAL_WEIGHT
              </Button>
            </div>

            <div className="rounded border border-border bg-muted/10 p-4">
              <div className="mb-3 flex flex-wrap gap-2">
                {resolvedTickers.map((symbol) => (
                  <span key={symbol} className="rounded border border-primary/30 bg-primary/10 px-2 py-1 text-xs text-primary">
                    {symbol}
                  </span>
                ))}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {resolvedTickers.map((symbol) => (
                  <Field key={symbol} label={`${symbol} Weight %`} help={`Example: ${resolvedTickers.length === 1 ? '100' : resolvedTickers.length === 2 ? '50' : '20 to 40'} depending on conviction.`}>
                    <Input
                      type="number"
                      min="0"
                      step="0.1"
                      value={request.allocation_weights?.[symbol] ?? 0}
                      onChange={(event) => setWeight(symbol, event.target.value)}
                    />
                  </Field>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-3 text-sm">
                <div className={cn('rounded border px-3 py-2', allocationOverweight ? 'border-destructive/40 bg-destructive/10 text-destructive' : 'border-border bg-background text-foreground')}>
                  Total Allocation: {formatPercent(totalAllocation, { mode: 'percent' })}
                </div>
                <div className="rounded border border-border bg-background px-3 py-2 text-foreground">
                  Cash Reserve: {formatPercent(cashReservePct, { mode: 'percent' })}
                </div>
              </div>
              {allocationOverweight ? (
                <div className="mt-3 text-sm text-destructive">Total allocation cannot exceed 100%. Lower one or more ticker weights before running.</div>
              ) : null}
            </div>
          </section>

          <section className="terminal-border space-y-5 bg-card p-6">
            <div>
              <h2 className="text-lg font-bold">Strategy Family</h2>
              <p className="text-sm text-muted-foreground">Each card includes what the strategy does, when it tends to work best, and a solid starting configuration.</p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              {STRATEGIES.map((item) => (
                <button
                  key={item.family}
                  type="button"
                  onClick={() => setStrategyFamily(item.family)}
                  className={cn(
                    'rounded border p-4 text-left transition-colors',
                    item.family === request.strategy.family
                      ? 'border-primary/40 bg-primary/10'
                      : 'border-border bg-muted/5 hover:border-primary/20 hover:bg-muted/10'
                  )}
                >
                  <div className="font-semibold text-foreground">{item.label}</div>
                  <div className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.description}</div>
                  <div className="mt-3 text-xs leading-relaxed text-muted-foreground">
                    Best for: {item.bestFor}
                  </div>
                  <div className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    Watch for: {item.watchFor}
                  </div>
                  <div className="mt-3 rounded border border-border/70 bg-background/70 px-3 py-2 text-xs text-foreground">
                    Starter values: {item.starterValues}
                  </div>
                </button>
              ))}
            </div>

            <div className="rounded border border-border bg-muted/10 p-4">
              <div className="text-sm font-semibold text-foreground">{strategy.label} Parameters</div>
              <div className="mt-2 text-sm text-muted-foreground">{strategy.starterValues}</div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {strategy.fields.map((field) => (
                  <Field key={field.key} label={field.label} help={field.help}>
                    <Input
                      type="number"
                      step={field.step}
                      value={Number(request.strategy.params[field.key] ?? 0)}
                      onChange={(event) =>
                        setRequest((prev) => ({
                          ...prev,
                          strategy: {
                            ...prev.strategy,
                            params: {
                              ...prev.strategy.params,
                              [field.key]: parseNumber(event.target.value, Number(prev.strategy.params[field.key] ?? 0)),
                            },
                          },
                        }))
                      }
                    />
                  </Field>
                ))}
              </div>
            </div>
          </section>

          <section className="terminal-border space-y-5 bg-card p-6">
            <div>
              <h2 className="text-lg font-bold">Risk Controls</h2>
              <p className="text-sm text-muted-foreground">Optional exits layered on top of the strategy. A beginner-friendly starting point is a 8% stop or a 12% trailing stop, not both unless you know why.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Stop Loss %" help="Example: 0.08 means sell if the trade falls 8% from entry.">
                <Input type="number" step="0.001" value={request.risk_controls?.stop_loss_pct ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), stop_loss_pct: parseOptionalNumber(event.target.value) } }))} />
              </Field>
              <Field label="Trailing Stop %" help="Example: 0.12 means lock in gains if price drops 12% from the best level reached.">
                <Input type="number" step="0.001" value={request.risk_controls?.trailing_stop_pct ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), trailing_stop_pct: parseOptionalNumber(event.target.value) } }))} />
              </Field>
              <Field label="Take Profit %" help="Example: 0.15 means exit after a 15% gain from entry.">
                <Input type="number" step="0.001" value={request.risk_controls?.take_profit_pct ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), take_profit_pct: parseOptionalNumber(event.target.value) } }))} />
              </Field>
            </div>
          </section>

          <section className="terminal-border space-y-5 bg-card p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold">Parameter Tuning</h2>
                <p className="text-sm text-muted-foreground">Advanced grid search for users who want to sweep a strategy across multiple parameter combinations.</p>
              </div>
              <label className="flex items-center gap-3 text-sm">
                <span>Enable</span>
                <input type="checkbox" checked={request.tuning?.enabled ?? false} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), enabled: event.target.checked } }))} className="h-4 w-4 accent-primary" />
              </label>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Objective" help="Sharpe Ratio is the safest default when you want better risk-adjusted results instead of raw return only.">
                <select value={request.tuning?.objective ?? 'sharpe_ratio'} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), objective: event.target.value as BacktestObjective } }))} className="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  {OBJECTIVES.map((objective) => <option key={objective.value} value={objective.value}>{objective.label}</option>)}
                </select>
              </Field>
              <Field label="Max Combinations" help="Keep this under 100 unless you already know the parameter space is small and clean.">
                <Input type="number" step="1" value={request.tuning?.max_combinations ?? 100} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), max_combinations: parseNumber(event.target.value, prev.tuning?.max_combinations ?? 100) } }))} />
              </Field>
            </div>
            <div className="space-y-3">
              {strategy.fields.map((field) => {
                const range = request.tuning?.parameter_ranges[field.key] ?? {};
                return (
                  <div key={field.key} className="rounded border border-border bg-muted/10 p-4">
                    <div className="mb-1 text-sm font-semibold text-foreground">{field.label}</div>
                    <div className="mb-3 text-xs text-muted-foreground">{field.help}</div>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <Field label="Min"><Input type="number" step={field.step} value={range.min ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), min: parseOptionalNumber(event.target.value) } } } }))} /></Field>
                      <Field label="Max"><Input type="number" step={field.step} value={range.max ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), max: parseOptionalNumber(event.target.value) } } } }))} /></Field>
                      <Field label="Step"><Input type="number" step={field.step} value={range.step ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), step: parseOptionalNumber(event.target.value) } } } }))} /></Field>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="terminal-border min-h-[220px] bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-bold">Results</h2>
              {result ? <div className="text-xs text-muted-foreground">{result.source.toUpperCase()}{result.cached ? ' | CACHE_HIT' : ''}</div> : null}
            </div>
            {mutation.isPending ? (
              <div className="flex min-h-[150px] items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>
            ) : mutation.error ? (
              <div className="mt-5 rounded border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">{(mutation.error as Error).message || 'Backtest failed.'}</div>
            ) : result ? (
              <div className="mt-5 space-y-5">
                {result.warnings.length > 0 ? <div className="rounded border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">{result.warnings.map((warning) => <div key={warning}>{warning}</div>)}</div> : null}
                <div className="flex flex-wrap gap-2">
                  {result.tickers.map((symbol) => <span key={symbol} className="rounded border border-primary/30 bg-primary/10 px-2 py-1 text-xs text-primary">{symbol} | {formatPercent(Number(result.allocation_weights?.[symbol] ?? 0), { mode: 'percent' })} | {result.data_sources[symbol]}</span>)}
                  {result.cash_reserve_pct > 0 ? <span className="rounded border border-border px-2 py-1 text-xs text-muted-foreground">CASH | {formatPercent(Number(result.cash_reserve_pct ?? 0), { mode: 'percent' })}</span> : null}
                </div>
                <div className="grid gap-3 sm:grid-cols-2">{Object.entries(result.stats).filter(([key]) => STAT_LABELS[key]).map(([key, value]) => <StatCard key={key} statKey={key} value={Number(value)} />)}</div>
                {result.buy_and_hold ? (
                  <div className="rounded border border-sky-500/30 bg-sky-500/10 p-4">
                    <div className="text-sm font-semibold text-foreground">Buy &amp; Hold Comparison</div>
                    <div className="mt-3 grid gap-3 sm:grid-cols-3">
                      <StatCard statKey="total_return_pct" value={Number(result.buy_and_hold.stats.total_return_pct ?? 0)} />
                      <StatCard statKey="cagr_pct" value={Number(result.buy_and_hold.stats.cagr_pct ?? 0)} />
                      <StatCard statKey="max_drawdown_pct" value={Number(result.buy_and_hold.stats.max_drawdown_pct ?? 0)} />
                    </div>
                  </div>
                ) : null}
                {result.tuning_summary?.enabled ? <div className="rounded border border-border bg-muted/10 p-4 text-sm text-muted-foreground">Tuned on {result.tuning_summary.objective}. Evaluated {result.tuning_summary.evaluated_combinations} combinations.</div> : null}
              </div>
            ) : (
              <div className="flex min-h-[150px] items-center justify-center text-center text-sm text-muted-foreground">Run a configuration to populate stats, charts, the benchmark line, and the trade log.</div>
            )}
          </section>

          <section className="terminal-border bg-card p-6">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="text-lg font-bold">Metric Guide</h2>
              <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                <Info className="h-3.5 w-3.5" />
                What the numbers mean
              </div>
            </div>
            <div className="space-y-3">
              {METRIC_GUIDE.map((metric) => (
                <GuideCard key={metric.key} title={metric.label}>
                  <div>{metric.meaning}</div>
                  <div>{metric.example}</div>
                </GuideCard>
              ))}
            </div>
          </section>

          {result ? (
            <>
              <section className="terminal-border bg-card p-6">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-lg font-bold">Equity Curve</h2>
                  <div className="text-xs text-muted-foreground">{formatDate(result.start_date)} - {formatDate(result.end_date)} | {result.timeframe.toUpperCase()}</div>
                </div>
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={equityData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                      <XAxis dataKey="date" minTickGap={36} stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(148, 163, 184, 0.25)', borderRadius: '0.5rem' }}
                        formatter={(value: number | string | undefined, name?: string) => [formatCurrency(typeof value === 'number' ? value : Number(value ?? 0)), name === 'strategy' ? 'Strategy' : 'Buy & Hold']}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="strategy" name="Strategy" stroke="#22c55e" strokeWidth={2} dot={false} />
                      {result.buy_and_hold ? <Line type="monotone" dataKey="benchmark" name="Buy & Hold" stroke="#38bdf8" strokeWidth={2} dot={false} strokeDasharray="6 4" connectNulls /> : null}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </section>

              <section className="terminal-border bg-card p-4">
                <div className="mb-3 text-sm font-semibold">Generated Equity Plot</div>
                {result.equity_curve_image ? <img src={result.equity_curve_image} alt="Equity curve plot" className="w-full rounded border border-border" /> : <div className="rounded border border-dashed border-border p-6 text-sm text-muted-foreground">Equity image generation disabled.</div>}
              </section>

              <section className="terminal-border bg-card p-6">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-lg font-bold">Trade Log</h2>
                  <div className="text-xs text-muted-foreground">{result.trade_log.length} trades</div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[1040px] text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                        <th className="pb-3 pr-4">Ticker</th><th className="pb-3 pr-4">Entry</th><th className="pb-3 pr-4">Exit</th><th className="pb-3 pr-4">Entry Px</th><th className="pb-3 pr-4">Exit Px</th><th className="pb-3 pr-4">Shares</th><th className="pb-3 pr-4">Net PnL</th><th className="pb-3 pr-4">Return</th><th className="pb-3 pr-4">Bars</th><th className="pb-3 pr-4">Exit Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trade_log.length > 0 ? result.trade_log.map((trade, index) => (
                        <tr key={`${trade.ticker}-${trade.entry_date}-${index}`} className="border-b border-border/60">
                          <td className="py-3 pr-4 font-medium">{String(trade.ticker ?? '')}</td>
                          <td className="py-3 pr-4 font-mono text-xs">{String(trade.entry_date ?? '')}</td>
                          <td className="py-3 pr-4 font-mono text-xs">{String(trade.exit_date ?? '')}</td>
                          <td className="py-3 pr-4">{formatCurrency(Number(trade.entry_price ?? 0))}</td>
                          <td className="py-3 pr-4">{formatCurrency(Number(trade.exit_price ?? 0))}</td>
                          <td className="py-3 pr-4">{formatNumber(Number(trade.shares ?? 0))}</td>
                          <td className="py-3 pr-4">{formatCurrency(Number(trade.net_pnl ?? 0))}</td>
                          <td className="py-3 pr-4">{formatPercent(Number(trade.net_return_pct ?? 0), { mode: 'percent' })}</td>
                          <td className="py-3 pr-4">{formatNumber(Number(trade.holding_period_bars ?? 0))}</td>
                          <td className="py-3 pr-4">{String(trade.exit_reason ?? '')}</td>
                        </tr>
                      )) : <tr><td colSpan={10} className="py-8 text-center text-sm text-muted-foreground">No trades were generated for this configuration.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          ) : null}
        </div>
      </form>
    </div>
  );
}
