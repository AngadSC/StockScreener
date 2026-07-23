'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ArrowLeft, ChevronDown, Loader2 } from 'lucide-react';

import { EquityCurveChart, type EquityPoint } from '@/components/backtester/BacktesterChart';
import {
  AffixInput,
  EmptyResultsState,
  FieldShell,
  MetricCard,
  SortIndicator,
  StrategyInfoDrawer,
  ToggleSwitch,
  headingLgStyle,
  headingMdStyle,
  headingSmStyle,
} from '@/components/backtester/BacktesterPrimitives';
import {
  INDICATOR_STRATEGIES,
  OBJECTIVES,
  PORTFOLIO_STRATEGIES,
  STRATEGIES,
  SUMMARY_METRICS,
  TIMEFRAME_OPTIONS,
  UNIVERSE_OPTIONS,
  buildEqualWeights,
  createDefaultRequest,
  getHoldingDaysMultiplier,
  normalizeBasketTickers,
  parseNumber,
  parseOptionalNumber,
  percentInputToRatio,
  ratioToPercentInput,
  syncWeightsToTickers,
} from '@/components/backtester/config';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { stocksAPI } from '@/lib/api';
import { cn, formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/utils';
import type {
  BacktestObjective,
  BacktestRunRequest,
  BacktestRunResponse,
  BacktestStrategyFamily,
  IndicatorBacktestRunRequest,
  IndicatorBacktestRunResponse,
} from '@/types/stock';

type BacktesterMode = 'automated' | 'indicator';
type TradeSortField = 'index' | 'ticker' | 'entry_date' | 'entry_price' | 'exit_date' | 'exit_price' | 'return_pct' | 'pnl';

type TradeRow = {
  index: number;
  ticker: string;
  entryDate: string;
  entryPrice: number;
  exitDate: string;
  exitPrice: number;
  returnPct: number;
  pnl: number;
  holdingBars: number;
};

type IndicatorPreset = {
  family: BacktestStrategyFamily;
  label: string;
  indicators: IndicatorBacktestRunRequest['indicators'];
  long_threshold?: number;
  short_threshold?: number;
};

const INDICATOR_PRESETS: IndicatorPreset[] = [
  { family: 'trend_following', label: 'Trend Following', indicators: { sma_xo: { enabled: true, weight: 1, params: { fast: 50, slow: 200 } } } },
  { family: 'mean_reversion', label: 'Mean Reversion', indicators: { bbands: { enabled: true, weight: 1, params: { window: 20, n_std: 2 } } } },
  { family: 'momentum_breakout', label: 'Momentum Breakout', indicators: { roc: { enabled: true, weight: 1, params: { period: 20, buy_above: 0, sell_below: 0 } } } },
  { family: 'oversold_reversal', label: 'RSI Reversal', indicators: { rsi: { enabled: true, weight: 1, params: { period: 14, buy_below: 30, sell_above: 70 } } } },
  { family: 'macd_trend', label: 'MACD', indicators: { macd: { enabled: true, weight: 1, params: { fast: 12, slow: 26, signal: 9 } } } },
  { family: 'golden_cross', label: 'Golden Cross', indicators: { sma_xo: { enabled: true, weight: 1, params: { fast: 50, slow: 200 } } } },
  { family: 'rsi_trend_filter', label: 'RSI Trend Filter', indicators: { rsi: { enabled: true, weight: 1, params: { period: 14, buy_above: 55, sell_below: 45 } } } },
  { family: 'volume_breakout', label: 'Volume/MFI', indicators: { mfi: { enabled: true, weight: 1, params: { period: 14, buy_below: 20, sell_above: 80 } } } },
  { family: 'mean_reversion', label: 'Bollinger Bands', indicators: { bbands: { enabled: true, weight: 1, params: { window: 20, n_std: 2 } } } },
];

function buildIndicatorRequest(
  ticker: string,
  request: BacktestRunRequest,
  preset: IndicatorPreset,
): IndicatorBacktestRunRequest {
  return {
    ticker: ticker.trim().toUpperCase(),
    start_date: request.start_date,
    end_date: request.end_date,
    timeframe: request.timeframe,
    indicators: preset.indicators,
    atr_gate: null,
    long_threshold: preset.long_threshold ?? 0.5,
    short_threshold: preset.short_threshold ?? -0.5,
    exec_lag: 1,
    tc_bps: request.tc_bps,
    allow_position_hold: true,
    generate_plots: request.generate_plots,
    generate_roc: false,
  };
}

function resultMetrics(result: BacktestRunResponse | IndicatorBacktestRunResponse | undefined) {
  if (!result) return [];
  return SUMMARY_METRICS.map((metric) => {
    const raw = Number(result.stats[metric.key] ?? 0);
    const value = metric.key === 'trade_count'
      ? formatNumber(raw).replace('.00', '')
      : metric.key.endsWith('_pct')
        ? formatPercent(raw, { mode: 'percent', withSign: metric.key !== 'win_rate_pct' })
        : formatNumber(raw);
    const tone = metric.key === 'max_drawdown_pct'
      ? 'negative'
      : metric.key === 'total_return_pct' || metric.key === 'cagr_pct'
        ? (raw >= 0 ? 'positive' : 'negative')
        : 'default';
    return { ...metric, value, tone: tone as 'positive' | 'negative' | 'default' };
  });
}

export default function BacktesterWorkspace({
  initialTickers,
  returnHref,
  returnLabel = 'Back to stock',
}: {
  initialTickers?: string[];
  returnHref?: string;
  returnLabel?: string;
}) {
  const normalizedInitialTickers = useMemo(
    () => normalizeBasketTickers((initialTickers?.length ? initialTickers : []).join(', ')),
    [initialTickers],
  );
  const [mode, setMode] = useState<BacktesterMode>('automated');
  const [request, setRequest] = useState<BacktestRunRequest>(() => createDefaultRequest(normalizedInitialTickers));
  const [basketInput, setBasketInput] = useState(normalizedInitialTickers.join(', '));
  const [indicatorTicker, setIndicatorTicker] = useState(normalizedInitialTickers[0] ?? 'AAPL');
  const [indicatorFamily, setIndicatorFamily] = useState<BacktestStrategyFamily>('oversold_reversal');
  const [activeStep, setActiveStep] = useState<'universe' | 'strategy' | 'risk'>('universe');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [tradeSort, setTradeSort] = useState<{ field: TradeSortField; order: 'asc' | 'desc' }>({ field: 'index', order: 'asc' });
  const [runVersion, setRunVersion] = useState(0);

  const automatedMutation = useMutation({ mutationFn: (payload: BacktestRunRequest) => stocksAPI.runGlobalBacktest(payload) });
  const indicatorMutation = useMutation({ mutationFn: (payload: IndicatorBacktestRunRequest) => stocksAPI.runIndicatorBacktest(payload) });
  const automatedResult = automatedMutation.data;
  const indicatorResult = indicatorMutation.data;
  const activeResult = mode === 'indicator' ? indicatorResult : automatedResult;
  const activePending = mode === 'indicator' ? indicatorMutation.isPending : automatedMutation.isPending;
  const activeError = mode === 'indicator' ? indicatorMutation.error : automatedMutation.error;

  useEffect(() => {
    const nextTickers = normalizeBasketTickers((initialTickers?.length ? initialTickers : []).join(', '));
    setBasketInput(nextTickers.join(', '));
    setIndicatorTicker(nextTickers[0] ?? 'AAPL');
    setRequest(createDefaultRequest(nextTickers));
    setAdvancedOpen(false);
    setActiveStep('universe');
  }, [initialTickers]);

  useEffect(() => {
    if (!activeResult) return;
    setRunVersion((value) => value + 1);
  }, [activeResult]);

  const resolvedTickers = useMemo(() => normalizeBasketTickers(basketInput), [basketInput]);
  useEffect(() => {
    setRequest((prev) => {
      if (prev.universe !== 'custom') return { ...prev, tickers: [], allocation_weights: {} };
      return { ...prev, tickers: resolvedTickers, allocation_weights: syncWeightsToTickers(resolvedTickers, prev.allocation_weights ?? {}) };
    });
  }, [resolvedTickers, request.universe]);

  const strategy = useMemo(() => STRATEGIES.find((item) => item.family === request.strategy.family) ?? PORTFOLIO_STRATEGIES[0], [request.strategy.family]);
  const indicatorPreset = useMemo(
    () => INDICATOR_PRESETS.find((item) => item.family === indicatorFamily) ?? INDICATOR_PRESETS[0],
    [indicatorFamily],
  );
  const indicatorStrategyInfo = useMemo(
    () => INDICATOR_STRATEGIES.find((item) => item.family === indicatorFamily) ?? INDICATOR_STRATEGIES[0],
    [indicatorFamily],
  );

  const totalAllocation = resolvedTickers.reduce((sum, symbol) => sum + Number(request.allocation_weights?.[symbol] ?? 0), 0);
  const cashReservePct = Math.max(0, Number((100 - totalAllocation).toFixed(2)));
  const allocationOverweight = request.universe === 'custom' && totalAllocation > 100.0001;
  const dateRangeInvalid = Boolean(request.start_date && request.end_date && request.start_date > request.end_date);
  const canRunAutomated = request.initial_capital > 0 && !allocationOverweight && !dateRangeInvalid && (request.universe !== 'custom' || resolvedTickers.length > 0);
  const canRunIndicator = indicatorTicker.trim().length > 0 && !dateRangeInvalid;
  const canRun = mode === 'indicator' ? canRunIndicator : canRunAutomated;

  const equityData = useMemo<EquityPoint[]>(() => (activeResult?.equity_curve ?? []).map((row) => ({
    date: String(row.Date ?? ''),
    strategy: Number(row.Equity ?? 0),
    benchmark: 'BuyHoldEquity' in row && row.BuyHoldEquity != null ? Number(row.BuyHoldEquity) : null,
  })), [activeResult]);
  const tradeRows = useMemo<TradeRow[]>(() => (automatedResult?.trade_log ?? []).map((trade, index) => ({
    index: index + 1,
    ticker: String(trade.ticker ?? ''),
    entryDate: String(trade.entry_date ?? ''),
    entryPrice: Number(trade.entry_price ?? 0),
    exitDate: String(trade.exit_date ?? ''),
    exitPrice: Number(trade.exit_price ?? 0),
    returnPct: Number(trade.net_return_pct ?? 0),
    pnl: Number(trade.net_pnl ?? 0),
    holdingBars: Number(trade.holding_period_bars ?? 0),
  })), [automatedResult]);
  const sortedTradeRows = useMemo(() => {
    const rows = [...tradeRows];
    const read = (row: TradeRow, field: TradeSortField) => {
      switch (field) {
        case 'index': return row.index;
        case 'ticker': return row.ticker;
        case 'entry_date': return new Date(row.entryDate).getTime();
        case 'entry_price': return row.entryPrice;
        case 'exit_date': return new Date(row.exitDate).getTime();
        case 'exit_price': return row.exitPrice;
        case 'return_pct': return row.returnPct;
        case 'pnl': return row.pnl;
      }
    };
    rows.sort((left, right) => {
      const a = read(left, tradeSort.field);
      const b = read(right, tradeSort.field);
      if (typeof a === 'string' && typeof b === 'string') return tradeSort.order === 'asc' ? a.localeCompare(b) : b.localeCompare(a);
      return tradeSort.order === 'asc' ? Number(a) - Number(b) : Number(b) - Number(a);
    });
    return rows;
  }, [tradeRows, tradeSort]);

  const metrics = resultMetrics(activeResult);
  const tradeSummary = automatedResult ? {
    tradeCount: tradeRows.length,
    winRate: Number(automatedResult.stats.win_rate_pct ?? 0),
    avgHoldDays: (tradeRows.length ? tradeRows.reduce((sum, trade) => sum + trade.holdingBars, 0) / tradeRows.length : 0) * getHoldingDaysMultiplier(automatedResult.timeframe),
  } : null;

  const setStrategyFamily = (family: BacktestStrategyFamily) => {
    const next = PORTFOLIO_STRATEGIES.find((item) => item.family === family) ?? PORTFOLIO_STRATEGIES[0];
    setRequest((prev) => ({
      ...prev,
      universe: next.family === 'sector_rotation_momentum' ? 'sector_etfs' : prev.universe,
      strategy: { family: next.family, params: { ...next.defaults } },
      tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: {} },
    }));
  };

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canRun) return;
    if (mode === 'indicator') {
      indicatorMutation.mutate(buildIndicatorRequest(indicatorTicker, request, indicatorPreset));
      return;
    }
    const riskControls = Object.fromEntries(Object.entries(request.risk_controls ?? {}).filter(([, value]) => value !== null && value !== undefined));
    const parameterRanges = Object.fromEntries(Object.entries(request.tuning?.parameter_ranges ?? {}).filter(([, range]) => range.min != null && range.max != null && range.step != null));
    const customTickers = request.universe === 'custom' ? resolvedTickers : [];
    automatedMutation.mutate({
      ...request,
      mode: 'automated',
      tickers: customTickers,
      allocation_weights: request.universe === 'custom'
        ? Object.fromEntries(customTickers.map((symbol) => [symbol, Number((request.allocation_weights?.[symbol] ?? 0).toFixed(4))]))
        : {},
      risk_controls: riskControls,
      tuning: request.tuning ? { ...request.tuning, parameter_ranges: parameterRanges } : undefined,
    });
  };

  const resetDefaults = () => {
    setBasketInput(normalizedInitialTickers.join(', '));
    setIndicatorTicker(normalizedInitialTickers[0] ?? 'AAPL');
    setRequest(createDefaultRequest(normalizedInitialTickers));
    setIndicatorFamily('oversold_reversal');
    setAdvancedOpen(false);
  };

  const universeStep = (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Automated Portfolio Strategies</div>
        <h2 className="mt-2" style={headingLgStyle}>Universe</h2>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">S&P 500 ranks and buys constituent stocks as a basket. It does not buy SPY.</p>
      </div>
      <FieldShell label="Universe">
        <select value={request.universe ?? 'sp500'} onChange={(event) => setRequest((prev) => ({ ...prev, universe: event.target.value as NonNullable<BacktestRunRequest['universe']> }))}>
          {UNIVERSE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </FieldShell>
      <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3 text-xs leading-5 text-[var(--text-secondary)]">
        {UNIVERSE_OPTIONS.find((option) => option.value === request.universe)?.helper}
      </div>
      {request.universe === 'custom' ? (
        <>
          <FieldShell label="Basket Tickers" helper="Separate tickers with commas or spaces. Custom baskets are limited to 25 symbols.">
            <textarea value={basketInput} onChange={(event) => setBasketInput(event.target.value.toUpperCase())} placeholder="e.g. AAPL, MSFT, NVDA" className="min-h-[110px] resize-y" />
          </FieldShell>
          <div className="border-t border-[var(--border-subtle)] pt-5">
            <div className="flex items-start justify-between gap-3">
              <div><div style={headingSmStyle}>Portfolio Weights</div><p className="mt-1 text-sm text-[var(--text-secondary)]">Used for custom basket tests. Remaining capital stays in cash.</p></div>
              <Button type="button" variant="secondary" size="sm" onClick={() => setRequest((prev) => ({ ...prev, allocation_weights: buildEqualWeights(resolvedTickers) }))}>Equal Weight</Button>
            </div>
            <div className="mt-4 space-y-3">{resolvedTickers.length > 0 ? resolvedTickers.map((symbol) => (
              <div key={symbol} className="grid grid-cols-[minmax(0,1fr)_132px] items-center gap-3 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-3 py-3">
                <div className="font-medium text-[var(--text-primary)]">{symbol}</div>
                <AffixInput value={request.allocation_weights?.[symbol] ?? 0} suffix="%" min="0" step="0.1" onChange={(value) => setRequest((prev) => ({ ...prev, allocation_weights: { ...(prev.allocation_weights ?? {}), [symbol]: Math.max(0, parseNumber(value, Number(prev.allocation_weights?.[symbol] ?? 0))) } }))} />
              </div>
            )) : <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border-default)] px-4 py-6 text-sm text-[var(--text-tertiary)]">Add one or more tickers above to configure weights.</div>}</div>
            <div className="mt-4 text-sm text-[var(--text-secondary)]">Total: {totalAllocation.toFixed(2)}% allocated {'\u00B7'} {cashReservePct.toFixed(2)}% in cash</div>
            {allocationOverweight ? <div className="mt-2 text-sm text-[var(--negative)]">Allocated capital exceeds 100%.</div> : null}
          </div>
        </>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <FieldShell label="Start Date"><Input type="date" value={request.start_date} onChange={(event) => setRequest((prev) => ({ ...prev, start_date: event.target.value }))} /></FieldShell>
        <FieldShell label="End Date"><Input type="date" value={request.end_date} onChange={(event) => setRequest((prev) => ({ ...prev, end_date: event.target.value }))} /></FieldShell>
      </div>
      <FieldShell label="Timeframe">
        <div className="seg w-full">
          {TIMEFRAME_OPTIONS.map((option) => <button key={option.value} type="button" onClick={() => setRequest((prev) => ({ ...prev, timeframe: option.value }))} className={cn('seg-btn flex-1', request.timeframe === option.value && 'active')}>{option.label}</button>)}
        </div>
      </FieldShell>
    </div>
  );

  const strategyStep = (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Automated Strategy</div>
        <h2 className="mt-2" style={headingLgStyle}>Research Strategy</h2>
      </div>
      <FieldShell label="Strategy">
        <select value={request.strategy.family} onChange={(event) => setStrategyFamily(event.target.value as BacktestStrategyFamily)}>
          {PORTFOLIO_STRATEGIES.map((item) => <option key={item.family} value={item.family}>{item.label}</option>)}
        </select>
      </FieldShell>
      <StrategyInfoDrawer strategy={strategy} />
      <div key={request.strategy.family} className="parameter-section-enter">
        <div style={headingSmStyle}>{strategy.label} Parameters</div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {strategy.fields.map((field) => (
            <FieldShell key={field.key} label={field.label} helper={field.help}>
              <Input type="number" step={field.step} value={Number(request.strategy.params[field.key] ?? 0)} onChange={(event) => setRequest((prev) => ({ ...prev, strategy: { ...prev.strategy, params: { ...prev.strategy.params, [field.key]: parseNumber(event.target.value, Number(prev.strategy.params[field.key] ?? 0)) } } }))} />
            </FieldShell>
          ))}
        </div>
      </div>
    </div>
  );

  const riskStep = (
    <div className="space-y-6">
      <div><h2 style={headingLgStyle}>Capital & Risk</h2><p className="mt-2 text-sm text-[var(--text-secondary)]">Long-only exits and execution settings.</p></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <FieldShell label="Starting Capital"><AffixInput value={request.initial_capital} prefix="$" min="0" step="100" onChange={(value) => setRequest((prev) => ({ ...prev, initial_capital: parseNumber(value, prev.initial_capital) }))} /></FieldShell>
        <FieldShell label="Transaction Cost"><AffixInput value={request.tc_bps} suffix="bps" min="0" step="1" onChange={(value) => setRequest((prev) => ({ ...prev, tc_bps: parseNumber(value, prev.tc_bps) }))} /></FieldShell>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <FieldShell label="Stop Loss %" helper="Cuts a position after a set loss."><AffixInput value={ratioToPercentInput(request.risk_controls?.stop_loss_pct)} suffix="%" min="0" step="0.1" placeholder="e.g. 8" onChange={(value) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), stop_loss_pct: percentInputToRatio(value) } }))} /></FieldShell>
        <FieldShell label="Trailing Stop %" helper="Exits after a pullback from the high."><AffixInput value={ratioToPercentInput(request.risk_controls?.trailing_stop_pct)} suffix="%" min="0" step="0.1" placeholder="e.g. 8" onChange={(value) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), trailing_stop_pct: percentInputToRatio(value) } }))} /></FieldShell>
        <FieldShell label="Take Profit %" helper="Closes after a defined gain."><AffixInput value={ratioToPercentInput(request.risk_controls?.take_profit_pct)} suffix="%" min="0" step="0.1" placeholder="e.g. 8" onChange={(value) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), take_profit_pct: percentInputToRatio(value) } }))} /></FieldShell>
      </div>
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3"><div><div className="text-sm font-medium text-[var(--text-primary)]">Fractional Shares</div><p className="mt-1 text-[11px] leading-5 text-[var(--text-tertiary)]">Useful when top baskets include high-price stocks</p></div><ToggleSwitch checked={request.allow_fractional_shares} onCheckedChange={(checked) => setRequest((prev) => ({ ...prev, allow_fractional_shares: checked }))} /></div>
        <div className="flex items-start justify-between gap-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3"><div><div className="text-sm font-medium text-[var(--text-primary)]">Show Buy &amp; Hold line</div><p className="mt-1 text-[11px] leading-5 text-[var(--text-tertiary)]">Overlay a buy-and-hold basket benchmark</p></div><ToggleSwitch checked={request.include_buy_and_hold} onCheckedChange={(checked) => setRequest((prev) => ({ ...prev, include_buy_and_hold: checked }))} /></div>
      </div>
      <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-1)]">
        <button type="button" onClick={() => setAdvancedOpen((prev) => !prev)} className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left"><div><div style={headingSmStyle}>Advanced: Parameter Tuning</div><p className="mt-1 text-sm text-[var(--text-secondary)]">Sweep bounded parameter ranges.</p></div><ChevronDown className={cn('h-4 w-4 text-[var(--text-secondary)] transition-transform duration-[250ms]', advancedOpen && 'rotate-180')} /></button>
        <div className={cn('grid transition-[grid-template-rows] duration-[250ms]', advancedOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]')}>
          <div className="overflow-hidden border-t border-[var(--border-subtle)] px-4 py-4">
            <div className="flex items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3"><div><div className="text-sm font-medium text-[var(--text-primary)]">Enable optimization</div></div><ToggleSwitch checked={request.tuning?.enabled ?? false} onCheckedChange={(checked) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), enabled: checked } }))} /></div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <FieldShell label="Objective"><select value={request.tuning?.objective ?? 'sharpe_ratio'} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), objective: event.target.value as BacktestObjective } }))}>{OBJECTIVES.map((objective) => <option key={objective.value} value={objective.value}>{objective.label}</option>)}</select></FieldShell>
              <FieldShell label="Max Combinations"><Input type="number" step="1" value={request.tuning?.max_combinations ?? 100} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), max_combinations: parseNumber(event.target.value, prev.tuning?.max_combinations ?? 100) } }))} /></FieldShell>
            </div>
            <div className="mt-4 space-y-3">{strategy.fields.map((field) => { const range = request.tuning?.parameter_ranges[field.key] ?? {}; return <div key={field.key} className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] p-4"><div style={headingSmStyle}>{field.label}</div><div className="mt-3 grid gap-3 sm:grid-cols-3"><FieldShell label="Min"><Input type="number" step={field.step} value={range.min ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), min: parseOptionalNumber(event.target.value) } } } }))} /></FieldShell><FieldShell label="Max"><Input type="number" step={field.step} value={range.max ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), max: parseOptionalNumber(event.target.value) } } } }))} /></FieldShell><FieldShell label="Step"><Input type="number" step={field.step} value={range.step ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), step: parseOptionalNumber(event.target.value) } } } }))} /></FieldShell></div></div>; })}</div>
          </div>
        </div>
      </div>
    </div>
  );

  const indicatorPanel = (
    <div className="space-y-6">
      <div>
        <div className="text-xs uppercase tracking-[0.18em] text-[var(--text-tertiary)]">Indicator Strategies</div>
        <h2 className="mt-2" style={headingLgStyle}>Single-Symbol Lab</h2>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">Indicator strategies run on one ticker and use the indicator engine, separate from ranked portfolio universes.</p>
      </div>
      <FieldShell label="Ticker"><Input value={indicatorTicker} onChange={(event) => setIndicatorTicker(event.target.value.toUpperCase())} placeholder="AAPL" /></FieldShell>
      <FieldShell label="Strategy">
        <select value={indicatorFamily} onChange={(event) => setIndicatorFamily(event.target.value as BacktestStrategyFamily)}>
          {INDICATOR_PRESETS.map((preset) => <option key={`${preset.family}-${preset.label}`} value={preset.family}>{preset.label}</option>)}
        </select>
      </FieldShell>
      {indicatorStrategyInfo ? <StrategyInfoDrawer strategy={indicatorStrategyInfo} /> : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <FieldShell label="Start Date"><Input type="date" value={request.start_date} onChange={(event) => setRequest((prev) => ({ ...prev, start_date: event.target.value }))} /></FieldShell>
        <FieldShell label="End Date"><Input type="date" value={request.end_date} onChange={(event) => setRequest((prev) => ({ ...prev, end_date: event.target.value }))} /></FieldShell>
      </div>
      <FieldShell label="Timeframe">
        <div className="seg w-full">
          {TIMEFRAME_OPTIONS.map((option) => <button key={option.value} type="button" onClick={() => setRequest((prev) => ({ ...prev, timeframe: option.value }))} className={cn('seg-btn flex-1', request.timeframe === option.value && 'active')}>{option.label}</button>)}
        </div>
      </FieldShell>
      <FieldShell label="Transaction Cost"><AffixInput value={request.tc_bps} suffix="bps" min="0" step="1" onChange={(value) => setRequest((prev) => ({ ...prev, tc_bps: parseNumber(value, prev.tc_bps) }))} /></FieldShell>
    </div>
  );

  const automatedStepBody = activeStep === 'universe' ? universeStep : activeStep === 'strategy' ? strategyStep : riskStep;

  return (
    <>
      <form onSubmit={onSubmit} className="container-custom py-6 md:py-8">
        {returnHref ? <div className="mb-4"><Link href={returnHref} className="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"><ArrowLeft className="h-4 w-4" />{returnLabel}</Link></div> : null}
        <div className="grid gap-6 xl:grid-cols-[480px_minmax(0,1fr)] xl:items-start">
          <aside className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] shadow-[var(--shadow-sm)] xl:sticky xl:top-24 xl:max-h-[calc(100vh-7rem)]">
            <div className="flex min-h-[760px] flex-col">
              <div className="border-b border-[var(--border-subtle)] px-5 py-5">
                <div className="seg w-full">
                  {[
                    { id: 'automated', label: 'Automated Strategies' },
                    { id: 'indicator', label: 'Indicator Strategies' },
                  ].map((item) => (
                    <button key={item.id} type="button" onClick={() => setMode(item.id as BacktesterMode)} className={cn('seg-btn flex-1', mode === item.id && 'active')}>{item.label}</button>
                  ))}
                </div>
                {mode === 'automated' ? (
                  <div className="mt-5 grid grid-cols-3 gap-2">
                    {[
                      { id: 'universe', label: 'Universe' },
                      { id: 'strategy', label: 'Strategy' },
                      { id: 'risk', label: 'Risk' },
                    ].map((step) => (
                      <button key={step.id} type="button" onClick={() => setActiveStep(step.id as typeof activeStep)} className={cn('rounded-[var(--radius-md)] border px-3 py-2 text-xs font-medium transition-colors', activeStep === step.id ? 'border-[var(--border-strong)] bg-[var(--bg-surface-2)] text-[var(--text-primary)]' : 'border-[var(--border-default)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]')}>{step.label}</button>
                    ))}
                  </div>
                ) : null}
              </div>
              <div className="flex-1 overflow-y-auto px-5 py-5">{mode === 'indicator' ? indicatorPanel : automatedStepBody}<div className="border-t border-[var(--border-subtle)] pt-4"><button type="button" onClick={resetDefaults} className="text-sm text-[var(--text-tertiary)] underline-offset-4 transition-colors hover:text-[var(--text-primary)] hover:underline">Reset to defaults</button></div></div>
              <div className="border-t border-[var(--border-subtle)] bg-[var(--bg-base)] px-5 py-5">
                {!canRun ? <div className="mb-3 text-sm text-[var(--text-tertiary)]">{dateRangeInvalid ? 'Fix the date range before running.' : mode === 'indicator' ? 'Enter a ticker to run the indicator backtest.' : request.universe === 'custom' ? 'Add at least one ticker to run a custom basket.' : 'Complete the required inputs to run the backtest.'}</div> : null}
                <Button type="submit" className="w-full" disabled={!canRun || activePending}>{activePending ? <><Loader2 className="h-4 w-4 animate-spin" />Running...</> : 'Run Backtest'}</Button>
              </div>
            </div>
          </aside>

          <section className="space-y-6">
            {!activeResult && !activePending && !activeError ? (
              <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] shadow-[var(--shadow-sm)]"><EmptyResultsState /></div>
            ) : activeError && !activeResult ? (
              <div className="rounded-[var(--radius-xl)] border border-[var(--negative)]/40 bg-[var(--bg-surface-1)] p-8 shadow-[var(--shadow-sm)]"><div style={headingMdStyle}>Backtest failed</div><p className="mt-2 text-sm text-[var(--negative)]">{(activeError as Error).message || 'The request could not be completed.'}</p></div>
            ) : activeResult ? (
              <div className="results-enter space-y-6">
                {activeResult.warnings.length > 0 ? <div className="rounded-[var(--radius-lg)] border border-[var(--amber)]/30 bg-[var(--amber-soft)] px-4 py-3 text-sm text-[var(--text-secondary)]">{activeResult.warnings.map((warning) => <div key={warning}>{warning}</div>)}</div> : null}
                <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div><div style={headingMdStyle}>Equity Curve</div><p className="mt-1 text-sm text-[var(--text-secondary)]">{formatDate(activeResult.start_date)} to {formatDate(activeResult.end_date)} {'\u00B7'} {activeResult.timeframe}</p></div>
                    <div className="flex items-center gap-3 text-sm text-[var(--text-tertiary)]">{activePending ? <span className="inline-flex items-center gap-2 text-[var(--text-secondary)]"><Loader2 className="h-4 w-4 animate-spin" />Running new backtest</span> : null}<span>{activeResult.source}{activeResult.cached ? ' / cached' : ''}</span></div>
                  </div>
                  <div className="mt-5"><EquityCurveChart key={runVersion} points={equityData} showBenchmark={mode === 'automated' && Boolean(automatedResult?.buy_and_hold) && request.include_buy_and_hold} runVersion={runVersion} /></div>
                </div>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">{metrics.map((metric, index) => <MetricCard key={`${metric.key}-${runVersion}`} label={metric.label} value={metric.value} tone={metric.tone} delay={index * 60} />)}</div>
                {mode === 'automated' && automatedResult ? (
                  <>
                    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]">
                      <div className="flex flex-wrap items-end justify-between gap-4"><div><div style={headingMdStyle}>Selected Holdings</div><p className="mt-1 text-sm text-[var(--text-secondary)]">{automatedResult.universe === 'sp500' ? 'S&P 500 constituent basket' : automatedResult.universe === 'sector_etfs' ? 'Sector ETF basket' : 'Custom basket'} {'\u00B7'} {automatedResult.current_holdings.length} current holdings</p></div></div>
                      <div className="mt-5 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)]"><div className="max-h-[320px] overflow-auto"><table className="w-full min-w-[620px] tabular-nums"><thead className="sticky top-0 z-10 bg-[var(--bg-surface-2)]"><tr className="border-b border-[var(--border-default)] text-xs font-medium text-[var(--text-secondary)]"><th className="px-4 py-3 text-left">Ticker</th><th className="px-4 py-3 text-left">Weight</th><th className="px-4 py-3 text-left">Market Value</th><th className="px-4 py-3 text-left">Entry</th></tr></thead><tbody>{automatedResult.current_holdings.length > 0 ? automatedResult.current_holdings.map((holding) => <tr key={String(holding.ticker)} className="border-b border-[var(--border-subtle)]"><td className="px-4 py-3 font-medium text-[var(--text-primary)]">{holding.ticker}</td><td className="px-4 py-3">{formatPercent(Number(holding.weight_pct ?? 0), { mode: 'percent' })}</td><td className="px-4 py-3">{formatCurrency(Number(holding.market_value ?? 0))}</td><td className="px-4 py-3">{formatDate(String(holding.entry_date ?? ''))}</td></tr>) : <tr><td colSpan={4} className="px-4 py-10 text-center text-sm text-[var(--text-tertiary)]">No active holdings at the end of this run.</td></tr>}</tbody></table></div></div>
                    </div>
                    <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]">
                      <div className="flex flex-wrap items-end justify-between gap-4"><div><div style={headingMdStyle}>Trade Log</div>{tradeSummary ? <p className="mt-1 text-sm text-[var(--text-secondary)]">{tradeSummary.tradeCount} trades {'\u00B7'} {tradeSummary.winRate.toFixed(1)}% win rate {'\u00B7'} Avg hold: {tradeSummary.avgHoldDays.toFixed(1)} days</p> : null}</div></div>
                      <div className="mt-5 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)]"><div className="max-h-[420px] overflow-auto"><table className="w-full min-w-[860px] tabular-nums"><thead className="sticky top-0 z-10 bg-[var(--bg-surface-2)]"><tr className="border-b border-[var(--border-default)] text-xs font-medium text-[var(--text-secondary)]">{[{ field: 'index', label: '#' }, { field: 'ticker', label: 'Ticker' }, { field: 'entry_date', label: 'Entry Date' }, { field: 'entry_price', label: 'Entry Price' }, { field: 'exit_date', label: 'Exit Date' }, { field: 'exit_price', label: 'Exit Price' }, { field: 'return_pct', label: 'Return %' }, { field: 'pnl', label: 'P&L' }].map((column) => <th key={column.field} className="px-4 py-3 text-left"><button type="button" onClick={() => setTradeSort((prev) => ({ field: column.field as TradeSortField, order: prev.field === column.field && prev.order === 'asc' ? 'desc' : 'asc' }))} className="inline-flex items-center gap-2 transition-colors hover:text-[var(--text-primary)]"><span>{column.label}</span><SortIndicator active={tradeSort.field === column.field} order={tradeSort.order} /></button></th>)}</tr></thead><tbody>{sortedTradeRows.length > 0 ? sortedTradeRows.map((trade, index) => <tr key={`${trade.ticker}-${trade.entryDate}-${trade.index}`} className={cn('border-b border-[var(--border-subtle)]', index % 2 === 0 ? 'bg-[var(--bg-surface-1)]' : 'bg-[var(--bg-base)]')}><td className="px-4 py-3">{trade.index}</td><td className="px-4 py-3 font-medium text-[var(--text-primary)]">{trade.ticker}</td><td className="px-4 py-3">{formatDate(trade.entryDate)}</td><td className="px-4 py-3">{formatCurrency(trade.entryPrice)}</td><td className="px-4 py-3">{formatDate(trade.exitDate)}</td><td className="px-4 py-3">{formatCurrency(trade.exitPrice)}</td><td className={cn('px-4 py-3', trade.returnPct >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]')}>{formatPercent(trade.returnPct, { mode: 'percent' })}</td><td className={cn('px-4 py-3', trade.pnl >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]')}>{formatCurrency(trade.pnl)}</td></tr>) : <tr><td colSpan={8} className="px-4 py-10 text-center text-sm text-[var(--text-tertiary)]">No trades were generated for this configuration.</td></tr>}</tbody></table></div></div>
                    </div>
                  </>
                ) : indicatorResult ? (
                  <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]">
                    <div style={headingMdStyle}>Indicator Output</div>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">{indicatorResult.selected_indicators.join(', ') || 'No indicators'} {'\u00B7'} {indicatorResult.results.length} rows</p>
                    <div className="mt-5 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)]"><div className="max-h-[420px] overflow-auto"><table className="w-full min-w-[760px] tabular-nums"><thead className="sticky top-0 z-10 bg-[var(--bg-surface-2)]"><tr className="border-b border-[var(--border-default)] text-xs font-medium text-[var(--text-secondary)]"><th className="px-4 py-3 text-left">Date</th><th className="px-4 py-3 text-left">Equity</th><th className="px-4 py-3 text-left">Score</th><th className="px-4 py-3 text-left">Signal</th><th className="px-4 py-3 text-left">Position</th></tr></thead><tbody>{indicatorResult.equity_curve.slice(-80).map((row) => <tr key={String(row.Date)} className="border-b border-[var(--border-subtle)]"><td className="px-4 py-3">{formatDate(String(row.Date ?? ''))}</td><td className="px-4 py-3">{formatNumber(Number(row.Equity ?? 0))}</td><td className="px-4 py-3">{formatNumber(Number(row.Score ?? 0))}</td><td className="px-4 py-3">{formatNumber(Number(row.Signal ?? 0)).replace('.00', '')}</td><td className="px-4 py-3">{formatNumber(Number(row.Position ?? 0)).replace('.00', '')}</td></tr>)}</tbody></table></div></div>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        </div>
      </form>

      <style jsx>{`
        .results-enter { animation: results-fade 300ms ease; }
        .metric-card-enter { opacity: 0; transform: translateY(12px); animation: metric-enter 300ms ease forwards; }
        .parameter-section-enter { animation: parameter-enter 250ms ease; }
        @keyframes results-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes metric-enter { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes parameter-enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </>
  );
}
