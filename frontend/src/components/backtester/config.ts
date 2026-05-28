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
  {
    family: 'price_momentum',
    label: 'Price Momentum (Leaders)',
    description: 'Holds stocks with strong 12-month returns while price stays above a short-term moving average. Based on Bessembinder\'s finding that a tiny fraction of stocks drive all wealth creation.',
    bestFor: 'Large-cap leaders and index heavyweights in sustained uptrends.',
    watchFor: 'Overcrowding risk — sharp reversals when top performers unwind.',
    starterValues: 'Momentum Window 252 (12 months), Exit MA 50.',
    defaults: { momentum_window: 252, exit_ma: 50 },
    fields: [
      { key: 'momentum_window', label: 'Momentum Window', step: 1, help: 'Look-back period for measuring price momentum. 126 = 6 months, 252 = 12 months.' },
      { key: 'exit_ma', label: 'Exit MA', step: 1, help: 'Short moving average used as a trailing exit trigger.' },
    ],
  },
  {
    family: 'sector_momentum',
    label: 'Sector Rotation Momentum',
    description: 'Holds when price is near the top of its recent trading range, capturing the relative strength concept behind sector rotation strategies.',
    bestFor: 'Sector ETFs and macro leaders riding institutional capital flows.',
    watchFor: 'Sudden macro shocks snap rotations violently.',
    starterValues: 'Rotation Window 126 (6 months), RS Percentile 0.8.',
    defaults: { rotation_window: 126, rs_percentile: 0.8 },
    fields: [
      { key: 'rotation_window', label: 'Rotation Window', step: 1, help: 'Period used to measure the high-low range for relative strength scoring.' },
      { key: 'rs_percentile', label: 'RS Percentile', step: 0.05, help: 'Price must be in the top X% of its range to enter. 0.8 = top 20%.' },
    ],
  },
  {
    family: 'extreme_reversal',
    label: 'Mean Reversion After Extremes',
    description: 'Buys after a stock drops sharply from a recent peak, betting on a partial recovery. Based on De Bondt & Thaler\'s overreaction hypothesis.',
    bestFor: 'Range-bound names after news-driven selloffs in calm volatility regimes.',
    watchFor: 'Strong downtrends — oversold can stay oversold.',
    starterValues: 'Peak Lookback 20, Drop 10%, Recovery 3%.',
    defaults: { peak_lookback: 20, drop_pct: 0.10, recovery_pct: 0.03 },
    fields: [
      { key: 'peak_lookback', label: 'Peak Lookback', step: 1, help: 'Days to look back when finding the recent peak.' },
      { key: 'drop_pct', label: 'Drop %', step: 0.01, help: 'Minimum drop from peak required before entering. 0.10 = 10%.' },
      { key: 'recovery_pct', label: 'Recovery %', step: 0.01, help: 'Exit when drawdown recovers to within this % of the peak. 0.03 = 3% below peak.' },
    ],
  },
  {
    family: 'gap_fill',
    label: 'Gap Fill Reflex',
    description: 'Buys gap-down opens expecting price to partially fill back toward the prior close. Based on behavioral overreaction to overnight news shocks.',
    bestFor: 'Liquid large-caps where gaps are more likely to fill than continue.',
    watchFor: 'True fundamental news — gaps with real catalysts continue downward.',
    starterValues: 'Gap Threshold 3%, Fill Ratio 50%.',
    defaults: { gap_threshold: 0.03, fill_ratio: 0.5 },
    fields: [
      { key: 'gap_threshold', label: 'Gap Threshold', step: 0.005, help: 'Minimum gap-down size to trigger entry. 0.03 = 3% below prior close.' },
      { key: 'fill_ratio', label: 'Fill Ratio', step: 0.05, help: 'Exit when price closes X% of the gap. 0.5 = 50% fill target.' },
    ],
  },
  {
    family: 'momentum_filter',
    label: 'Losers Keep Losing',
    description: 'Holds only when the stock has positive 6-month momentum and is above a short-term moving average. Avoids weak names by filtering out negative momentum.',
    bestFor: 'Filtering out structural losers in a diversified basket.',
    watchFor: 'Short-squeeze risk in heavily shorted names — avoided here by going flat, not short.',
    starterValues: 'Momentum Window 126 (6 months), Trend Window 20.',
    defaults: { momentum_window: 126, trend_window: 20 },
    fields: [
      { key: 'momentum_window', label: 'Momentum Window', step: 1, help: 'Period to measure the medium-term return trend. 126 = 6 months.' },
      { key: 'trend_window', label: 'Trend Window', step: 1, help: 'Short MA used to confirm the stock is in a local uptrend.' },
    ],
  },
  {
    family: 'volatility_regime',
    label: 'Volatility Regimes',
    description: 'Invests only when the VIX is calm (below entry threshold) and exits when fear spikes. Based on GARCH-regime research showing drawdowns follow volatility expansions.',
    bestFor: 'Systematic de-risking during market stress.',
    watchFor: 'Can miss sharp rebounds that happen right after a VIX spike.',
    starterValues: 'VIX Entry 20, VIX Exit 25, Trend MA 50.',
    defaults: { vix_entry: 20.0, vix_exit: 25.0, trend_ma: 50 },
    fields: [
      { key: 'vix_entry', label: 'VIX Entry', step: 0.5, help: 'VIX must be below this level to allow new entries.' },
      { key: 'vix_exit', label: 'VIX Exit', step: 0.5, help: 'Exit existing positions when VIX spikes above this level.' },
      { key: 'trend_ma', label: 'Trend MA', step: 1, help: 'Price must also be above this moving average to enter.' },
    ],
  },
  {
    family: 'overnight_edge',
    label: 'Overnight vs Intraday Edge',
    description: 'Holds when rolling overnight returns (close-to-open) consistently exceed intraday returns (open-to-close). Exploits the structural edge where most equity returns occur overnight.',
    bestFor: 'Understanding which stocks have overnight vs intraday return profiles.',
    watchFor: 'Signals can be noisy — works best on liquid, actively traded names.',
    starterValues: 'Lookback 20 days.',
    defaults: { lookback: 20 },
    fields: [
      { key: 'lookback', label: 'Lookback', step: 1, help: 'Rolling window to compare overnight vs intraday average returns.' },
    ],
  },
  {
    family: 'relative_strength',
    label: 'Index Drag Filter',
    description: 'Holds only when the stock is outperforming SPY on a rolling 3-month basis. Based on Bessembinder\'s finding that most stocks underperform the index — only hold those that don\'t.',
    bestFor: 'Filtering out dead-weight stocks from a long-only portfolio.',
    watchFor: 'Becomes momentum-lite and may overlap with other momentum strategies.',
    starterValues: 'Lookback 63 (3 months), RS Threshold 0.',
    defaults: { lookback: 63, rs_threshold: 0.0 },
    fields: [
      { key: 'lookback', label: 'Lookback', step: 1, help: 'Period over which to compare stock return vs SPY return.' },
      { key: 'rs_threshold', label: 'RS Threshold', step: 0.01, help: 'Stock must outperform SPY by at least this much to enter. 0 = any outperformance.' },
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
