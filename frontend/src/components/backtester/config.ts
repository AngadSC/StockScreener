'use client';

import type { BacktestObjective, BacktestRunRequest, BacktestStrategyFamily } from '@/types/stock';

export type WizardStepId = 'portfolio' | 'strategy' | 'risk';

export type StrategyField = {
  key: string;
  label: string;
  step: number;
  help: string;
};

export type StrategyDef = {
  family: BacktestStrategyFamily;
  label: string;
  description: string;
  bestFor: string;
  watchFor: string;
  starterValues: string;
  defaults: Record<string, number>;
  fields: StrategyField[];
};

export type ExamplePreset = {
  label: string;
  description: string;
  family: BacktestStrategyFamily;
  params: Record<string, number>;
};

export const WIZARD_STEPS: Array<{ id: WizardStepId; label: string; shortLabel: string }> = [
  { id: 'portfolio', label: 'Portfolio Setup', shortLabel: 'Portfolio' },
  { id: 'strategy', label: 'Strategy', shortLabel: 'Strategy' },
  { id: 'risk', label: 'Risk & Advanced', shortLabel: 'Risk' },
];

export const TIMEFRAME_OPTIONS: Array<{ value: BacktestRunRequest['timeframe']; label: string }> = [
  { value: '1d', label: 'Daily' },
  { value: '1wk', label: 'Weekly' },
  { value: '1mo', label: 'Monthly' },
];

export const OBJECTIVES: Array<{ value: BacktestObjective; label: string }> = [
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'cagr_pct', label: 'CAGR' },
  { value: 'total_return_pct', label: 'Total Return' },
  { value: 'profit_factor', label: 'Profit Factor' },
  { value: 'expectancy_pct', label: 'Expectancy' },
  { value: 'win_rate_pct', label: 'Win Rate' },
  { value: 'max_drawdown_pct', label: 'Lowest Drawdown' },
];

export const SUMMARY_METRICS = [
  { key: 'total_return_pct', label: 'Total Return' },
  { key: 'cagr_pct', label: 'CAGR' },
  { key: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { key: 'max_drawdown_pct', label: 'Max Drawdown' },
  { key: 'win_rate_pct', label: 'Win Rate' },
  { key: 'trade_count', label: 'Total Trades' },
] as const;

export const STRATEGIES: StrategyDef[] = [
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

export const EXAMPLE_PRESETS: ExamplePreset[] = [
  {
    label: 'Beginner Trend',
    description: 'A slower trend template built around the classic 50/200 crossover.',
    family: 'trend_following',
    params: { fast_ema: 50, slow_ema: 200 },
  },
  {
    label: 'Swing Rebound',
    description: 'A shorter RSI rebound template for oversold recoveries.',
    family: 'oversold_reversal',
    params: { rsi_period: 14, entry_rsi: 28, exit_rsi: 52 },
  },
  {
    label: 'Breakout Basket',
    description: 'A breakout template that waits for price and volume confirmation.',
    family: 'volume_breakout',
    params: { breakout_lookback: 20, exit_lookback: 10, volume_window: 20, volume_multiplier: 1.5 },
  },
];

export const toInputDate = (date: Date) => date.toISOString().slice(0, 10);
export const parseNumber = (value: string, fallback: number) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

export const parseOptionalNumber = (value: string) => {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

export const normalizeBasketTickers = (basketInput: string) => {
  const ordered: string[] = [];
  const seen = new Set<string>();
  for (const raw of basketInput.split(/[\s,]+/)) {
    const symbol = raw.trim().toUpperCase();
    if (!symbol || seen.has(symbol)) continue;
    seen.add(symbol);
    ordered.push(symbol);
  }
  return ordered;
};

export const buildEqualWeights = (tickers: string[]) => {
  if (tickers.length === 0) return {};
  const base = Number((100 / tickers.length).toFixed(4));
  const weights: Record<string, number> = Object.fromEntries(tickers.map((symbol) => [symbol, base]));
  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  weights[tickers[tickers.length - 1]] = Number((weights[tickers[tickers.length - 1]] + (100 - total)).toFixed(4));
  return weights;
};

export const syncWeightsToTickers = (tickers: string[], existing: Record<string, number>) => {
  if (tickers.length === 0) return {};
  const filtered = Object.fromEntries(
    tickers.filter((symbol) => Number.isFinite(existing[symbol])).map((symbol) => [symbol, Number(existing[symbol])]),
  );
  if (Object.keys(filtered).length === 0) return buildEqualWeights(tickers);
  const missing = tickers.filter((symbol) => filtered[symbol] == null);
  const specifiedTotal = Object.values(filtered).reduce((sum, value) => sum + value, 0);
  const remaining = Math.max(0, Number((100 - specifiedTotal).toFixed(4)));
  if (missing.length === 0) return filtered;
  const fill = Number((remaining / missing.length).toFixed(4));
  const next = { ...filtered };
  for (const symbol of missing) next[symbol] = fill;
  const total = Object.values(next).reduce((sum, value) => sum + value, 0);
  next[missing[missing.length - 1]] = Number((next[missing[missing.length - 1]] + (100 - total)).toFixed(4));
  return next;
};

export const areWeightsEqual = (left: Record<string, number>, right: Record<string, number>, tickers: string[]) =>
  tickers.every((symbol) => Math.abs((left[symbol] ?? 0) - (right[symbol] ?? 0)) < 0.0001);

export const ratioToPercentInput = (value: number | null | undefined) => {
  if (value == null || !Number.isFinite(value)) return '';
  return Number((value * 100).toFixed(2)).toString();
};

export const percentInputToRatio = (value: string) => {
  const parsed = parseOptionalNumber(value);
  return parsed == null ? null : parsed / 100;
};

export const getHoldingDaysMultiplier = (timeframe: BacktestRunRequest['timeframe']) => {
  if (timeframe === '1wk') return 7;
  if (timeframe === '1mo') return 30;
  return 1;
};

export function createDefaultRequest(tickers: string[]): BacktestRunRequest {
  const normalizedTickers = tickers.length ? tickers : ['SPY'];
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(end.getFullYear() - 5);
  return {
    start_date: toInputDate(start),
    end_date: toInputDate(end),
    tickers: normalizedTickers,
    allocation_weights: buildEqualWeights(normalizedTickers),
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
