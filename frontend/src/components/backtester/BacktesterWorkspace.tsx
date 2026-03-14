'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ArrowLeft, Check, ChevronDown, Loader2 } from 'lucide-react';

import { EquityCurveChart, type EquityPoint } from '@/components/backtester/BacktesterChart';
import {
  AffixInput,
  EmptyResultsState,
  FieldShell,
  MetricCard,
  SortIndicator,
  StepMarker,
  StrategyInfoDrawer,
  ToggleSwitch,
  captionStyle,
  headingLgStyle,
  headingMdStyle,
  headingSmStyle,
} from '@/components/backtester/BacktesterPrimitives';
import {
  EXAMPLE_PRESETS,
  OBJECTIVES,
  STRATEGIES,
  SUMMARY_METRICS,
  TIMEFRAME_OPTIONS,
  WIZARD_STEPS,
  areWeightsEqual,
  buildEqualWeights,
  createDefaultRequest,
  getHoldingDaysMultiplier,
  normalizeBasketTickers,
  parseNumber,
  parseOptionalNumber,
  percentInputToRatio,
  ratioToPercentInput,
  syncWeightsToTickers,
  type WizardStepId,
} from '@/components/backtester/config';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { stocksAPI } from '@/lib/api';
import { cn, formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/utils';
import type { BacktestObjective, BacktestRunRequest, BacktestStrategyFamily } from '@/types/stock';

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
    () => normalizeBasketTickers((initialTickers?.length ? initialTickers : ['SPY']).join(', ')),
    [initialTickers],
  );
  const [request, setRequest] = useState<BacktestRunRequest>(() => createDefaultRequest(normalizedInitialTickers));
  const [basketInput, setBasketInput] = useState(normalizedInitialTickers.join(', '));
  const [activeStep, setActiveStep] = useState<WizardStepId>('portfolio');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [hoveredStrategy, setHoveredStrategy] = useState<BacktestStrategyFamily | null>(null);
  const [tradeSort, setTradeSort] = useState<{ field: TradeSortField; order: 'asc' | 'desc' }>({ field: 'index', order: 'asc' });
  const [runVersion, setRunVersion] = useState(0);
  const [runSuccessPulse, setRunSuccessPulse] = useState(false);

  useEffect(() => {
    const nextTickers = normalizeBasketTickers((initialTickers?.length ? initialTickers : ['SPY']).join(', '));
    setBasketInput(nextTickers.join(', '));
    setRequest(createDefaultRequest(nextTickers));
    setAdvancedOpen(false);
    setActiveStep('portfolio');
  }, [initialTickers]);

  const resolvedTickers = useMemo(() => normalizeBasketTickers(basketInput), [basketInput]);
  useEffect(() => {
    setRequest((prev) => {
      const nextWeights = syncWeightsToTickers(resolvedTickers, prev.allocation_weights ?? {});
      const sameTickers = prev.tickers.length === resolvedTickers.length && prev.tickers.every((symbol, index) => symbol === resolvedTickers[index]);
      if (sameTickers && areWeightsEqual(prev.allocation_weights ?? {}, nextWeights, resolvedTickers)) return prev;
      return { ...prev, tickers: resolvedTickers, allocation_weights: nextWeights };
    });
  }, [resolvedTickers]);

  const strategy = useMemo(() => STRATEGIES.find((item) => item.family === request.strategy.family) ?? STRATEGIES[0], [request.strategy.family]);
  const previewStrategy = useMemo(() => STRATEGIES.find((item) => item.family === (hoveredStrategy ?? request.strategy.family)) ?? strategy, [hoveredStrategy, request.strategy.family, strategy]);
  const mutation = useMutation({ mutationFn: (payload: BacktestRunRequest) => stocksAPI.runGlobalBacktest(payload) });
  const result = mutation.data;

  useEffect(() => {
    if (!result) return;
    setRunVersion((value) => value + 1);
    setRunSuccessPulse(true);
    const timer = window.setTimeout(() => setRunSuccessPulse(false), 500);
    return () => window.clearTimeout(timer);
  }, [result]);

  const totalAllocation = resolvedTickers.reduce((sum, symbol) => sum + Number(request.allocation_weights?.[symbol] ?? 0), 0);
  const cashReservePct = Math.max(0, Number((100 - totalAllocation).toFixed(2)));
  const allocationOverweight = totalAllocation > 100.0001;
  const dateRangeInvalid = Boolean(request.start_date && request.end_date && request.start_date > request.end_date);
  const canRun = resolvedTickers.length > 0 && !allocationOverweight && !dateRangeInvalid && request.initial_capital > 0;
  const equityData = useMemo<EquityPoint[]>(() => (result?.equity_curve ?? []).map((row) => ({ date: String(row.Date ?? ''), strategy: Number(row.Equity ?? 0), benchmark: row.BuyHoldEquity == null ? null : Number(row.BuyHoldEquity) })), [result]);
  const tradeRows = useMemo<TradeRow[]>(() => (result?.trade_log ?? []).map((trade, index) => ({ index: index + 1, ticker: String(trade.ticker ?? ''), entryDate: String(trade.entry_date ?? ''), entryPrice: Number(trade.entry_price ?? 0), exitDate: String(trade.exit_date ?? ''), exitPrice: Number(trade.exit_price ?? 0), returnPct: Number(trade.net_return_pct ?? 0), pnl: Number(trade.net_pnl ?? 0), holdingBars: Number(trade.holding_period_bars ?? 0) })), [result]);
  const tradeSummary = useMemo(() => {
    if (!result) return null;
    const tradeCount = tradeRows.length;
    const avgHoldingBars = tradeCount > 0 ? tradeRows.reduce((sum, trade) => sum + trade.holdingBars, 0) / tradeCount : 0;
    return { tradeCount, winRate: Number(result.stats.win_rate_pct ?? 0), avgHoldDays: avgHoldingBars * getHoldingDaysMultiplier(result.timeframe) };
  }, [result, tradeRows]);
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
  const completedSteps = {
    portfolio: resolvedTickers.length > 0 && request.initial_capital > 0 && !allocationOverweight && !dateRangeInvalid,
    strategy: strategy.fields.every((field) => Number.isFinite(Number(request.strategy.params[field.key] ?? NaN))),
    risk: ['stop_loss_pct', 'trailing_stop_pct', 'take_profit_pct'].every((key) => {
      const value = request.risk_controls?.[key as keyof NonNullable<BacktestRunRequest['risk_controls']>];
      return value == null || value >= 0;
    }),
  };
  const metrics = result ? SUMMARY_METRICS.map((metric) => {
    const raw = Number(result.stats[metric.key] ?? 0);
    const value = metric.key === 'trade_count' ? formatNumber(raw).replace('.00', '') : metric.key.endsWith('_pct') ? formatPercent(raw, { mode: 'percent', withSign: metric.key !== 'win_rate_pct' }) : formatNumber(raw);
    const tone = metric.key === 'max_drawdown_pct' ? 'negative' : metric.key === 'total_return_pct' || metric.key === 'cagr_pct' ? (raw >= 0 ? 'positive' : 'negative') : 'default';
    return { ...metric, value, tone: tone as 'positive' | 'negative' | 'default' };
  }) : [];

  const setStrategyFamily = (family: BacktestStrategyFamily) => {
    const next = STRATEGIES.find((item) => item.family === family) ?? STRATEGIES[0];
    setRequest((prev) => ({ ...prev, strategy: { family: next.family, params: { ...next.defaults } }, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: {} } }));
  };
  const resetDefaults = () => {
    const nextTickers = normalizeBasketTickers((initialTickers?.length ? initialTickers : ['SPY']).join(', '));
    setBasketInput(nextTickers.join(', '));
    setRequest(createDefaultRequest(nextTickers));
    setAdvancedOpen(false);
  };
  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canRun) return;
    const riskControls = Object.fromEntries(Object.entries(request.risk_controls ?? {}).filter(([, value]) => value !== null && value !== undefined));
    const parameterRanges = Object.fromEntries(Object.entries(request.tuning?.parameter_ranges ?? {}).filter(([, range]) => range.min != null && range.max != null && range.step != null));
    mutation.mutate({
      ...request,
      tickers: resolvedTickers,
      allocation_weights: Object.fromEntries(resolvedTickers.map((symbol) => [symbol, Number((request.allocation_weights?.[symbol] ?? 0).toFixed(4))])),
      risk_controls: riskControls,
      tuning: request.tuning ? { ...request.tuning, parameter_ranges: parameterRanges } : undefined,
    });
  };

  const portfolioStep = (
    <div className="space-y-6">
      <h2 style={headingLgStyle}>Portfolio Setup</h2>
      <FieldShell label="Basket Tickers" helper="Separate tickers with commas or spaces.">
        <textarea value={basketInput} onChange={(event) => setBasketInput(event.target.value.toUpperCase())} placeholder="e.g. AAPL, MSFT, NVDA" className="min-h-[110px] resize-y" />
      </FieldShell>
      <div className="grid gap-4 sm:grid-cols-2">
        <FieldShell label="Start Date"><Input type="date" value={request.start_date} onChange={(event) => setRequest((prev) => ({ ...prev, start_date: event.target.value }))} /></FieldShell>
        <FieldShell label="End Date"><Input type="date" value={request.end_date} onChange={(event) => setRequest((prev) => ({ ...prev, end_date: event.target.value }))} /></FieldShell>
      </div>
      {dateRangeInvalid ? <div className="rounded-[var(--radius-md)] border border-[var(--negative)]/40 bg-[var(--negative-bg)] px-3 py-2 text-sm text-[var(--negative)]">End date must be on or after the start date.</div> : null}
      <FieldShell label="Timeframe">
        <div className="grid grid-cols-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] p-1">
          {TIMEFRAME_OPTIONS.map((option) => <button key={option.value} type="button" onClick={() => setRequest((prev) => ({ ...prev, timeframe: option.value }))} className={cn('rounded-[var(--radius-md)] px-3 py-2 text-sm transition-colors', request.timeframe === option.value ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]')}>{option.label}</button>)}
        </div>
      </FieldShell>
      <div className="grid gap-4 sm:grid-cols-2">
        <FieldShell label="Starting Capital"><AffixInput value={request.initial_capital} prefix="$" min="0" step="100" onChange={(value) => setRequest((prev) => ({ ...prev, initial_capital: parseNumber(value, prev.initial_capital) }))} /></FieldShell>
        <FieldShell label="Transaction Cost (bps)"><AffixInput value={request.tc_bps} suffix="bps" min="0" step="1" onChange={(value) => setRequest((prev) => ({ ...prev, tc_bps: parseNumber(value, prev.tc_bps) }))} /></FieldShell>
      </div>
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3"><div><div className="text-sm font-medium text-[var(--text-primary)]">Fractional Shares</div><p className="mt-1 text-[11px] leading-5 text-[var(--text-tertiary)]">Recommended for high-price stocks</p></div><ToggleSwitch checked={request.allow_fractional_shares} onCheckedChange={(checked) => setRequest((prev) => ({ ...prev, allow_fractional_shares: checked }))} /></div>
        <div className="flex items-start justify-between gap-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3"><div><div className="text-sm font-medium text-[var(--text-primary)]">Show Buy &amp; Hold line</div><p className="mt-1 text-[11px] leading-5 text-[var(--text-tertiary)]">Overlay the benchmark on the equity curve</p></div><ToggleSwitch checked={request.include_buy_and_hold} onCheckedChange={(checked) => setRequest((prev) => ({ ...prev, include_buy_and_hold: checked }))} /></div>
      </div>
      <div className="border-t border-[var(--border-subtle)] pt-6">
        <div className="flex items-start justify-between gap-3"><div><div style={headingSmStyle}>Portfolio Weights</div><p className="mt-1 text-sm text-[var(--text-secondary)]">Set allocation per ticker. Remaining % stays in cash.</p></div><Button type="button" variant="secondary" size="sm" onClick={() => setRequest((prev) => ({ ...prev, allocation_weights: buildEqualWeights(resolvedTickers) }))}>Equal Weight</Button></div>
        <div className="mt-4 space-y-3">{resolvedTickers.length > 0 ? resolvedTickers.map((symbol) => <div key={symbol} className="grid grid-cols-[minmax(0,1fr)_132px] items-center gap-3 rounded-[var(--radius-md)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-3 py-3"><div className="font-medium text-[var(--text-primary)]">{symbol}</div><AffixInput value={request.allocation_weights?.[symbol] ?? 0} suffix="%" min="0" step="0.1" onChange={(value) => setRequest((prev) => ({ ...prev, allocation_weights: { ...(prev.allocation_weights ?? {}), [symbol]: Math.max(0, parseNumber(value, Number(prev.allocation_weights?.[symbol] ?? 0))) } }))} /></div>) : <div className="rounded-[var(--radius-lg)] border border-dashed border-[var(--border-default)] px-4 py-6 text-sm text-[var(--text-tertiary)]">Add one or more tickers above to configure weights.</div>}</div>
        <div className="mt-4 space-y-2"><div className="h-1.5 overflow-hidden rounded-full bg-[var(--bg-surface-3)]"><div className={cn('h-full rounded-full transition-all duration-[250ms]', allocationOverweight ? 'bg-[var(--negative)]' : 'bg-[var(--positive)]')} style={{ width: `${Math.min(totalAllocation, 100)}%` }} /></div><div className="text-sm text-[var(--text-secondary)]">Total: {totalAllocation.toFixed(2)}% allocated {'\u00B7'} {cashReservePct.toFixed(2)}% in cash</div>{allocationOverweight ? <div className="text-sm text-[var(--negative)]">Allocated capital exceeds 100%. Lower one or more weights before running.</div> : null}</div>
      </div>
    </div>
  );

  const strategyStep = (
    <div className="space-y-6">
      <h2 style={headingLgStyle}>Strategy</h2>
      <div className="grid gap-3 sm:grid-cols-2">{STRATEGIES.map((item) => <button key={item.family} type="button" onClick={() => setStrategyFamily(item.family)} onMouseEnter={() => setHoveredStrategy(item.family)} onMouseLeave={() => setHoveredStrategy(null)} className={cn('relative rounded-[var(--radius-lg)] border bg-[var(--bg-surface-1)] p-4 text-left transition-all', item.family === request.strategy.family ? 'border-[var(--accent)] bg-[var(--accent-subtle)]' : 'border-[var(--border-default)] hover:border-[var(--border-strong)]')}>{item.family === request.strategy.family ? <span className="absolute right-3 top-3 inline-flex h-6 w-6 items-center justify-center rounded-full bg-[var(--positive-bg)] text-[var(--positive)]"><Check className="h-3.5 w-3.5" /></span> : null}<div style={headingSmStyle}>{item.label}</div><p className="mt-2 text-[11px] leading-5 text-[var(--text-secondary)]" style={captionStyle}>{item.description}</p></button>)}</div>
      <StrategyInfoDrawer strategy={previewStrategy} />
      <div key={request.strategy.family} className="parameter-section-enter"><div style={headingSmStyle}>{strategy.label} Parameters</div><div className="mt-4 flex flex-wrap gap-2">{EXAMPLE_PRESETS.map((preset) => <button key={preset.label} type="button" title={preset.description} onClick={() => setRequest((prev) => ({ ...prev, strategy: { family: preset.family, params: { ...preset.params } }, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: {} } }))} className={cn('rounded-full border px-3 py-1.5 text-xs transition-colors', preset.family === request.strategy.family && JSON.stringify(preset.params) === JSON.stringify(request.strategy.params) ? 'border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--text-primary)]' : 'border-[var(--border-default)] bg-[var(--bg-surface-2)] text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]')}>{preset.label}</button>)}</div><div className="mt-4 grid gap-4 sm:grid-cols-2">{strategy.fields.map((field) => <FieldShell key={field.key} label={field.label} helper={field.help}><Input type="number" step={field.step} value={Number(request.strategy.params[field.key] ?? 0)} onChange={(event) => setRequest((prev) => ({ ...prev, strategy: { ...prev.strategy, params: { ...prev.strategy.params, [field.key]: parseNumber(event.target.value, Number(prev.strategy.params[field.key] ?? 0)) } } }))} /></FieldShell>)}</div></div>
    </div>
  );

  const riskStep = (
    <div className="space-y-6">
      <div><h2 style={headingLgStyle}>Risk Controls</h2><p className="mt-2 text-sm text-[var(--text-secondary)]">Optional exit rules layered on top of your strategy.</p></div>
      <div className="grid gap-4 md:grid-cols-3">
        <FieldShell label="Stop Loss %" helper="Cuts the position if price falls a set distance below entry."><AffixInput value={ratioToPercentInput(request.risk_controls?.stop_loss_pct)} suffix="%" min="0" step="0.1" placeholder="e.g. 8" onChange={(value) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), stop_loss_pct: percentInputToRatio(value) } }))} /></FieldShell>
        <FieldShell label="Trailing Stop %" helper="Follows the move higher and exits after a pullback from the peak."><AffixInput value={ratioToPercentInput(request.risk_controls?.trailing_stop_pct)} suffix="%" min="0" step="0.1" placeholder="e.g. 8" onChange={(value) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), trailing_stop_pct: percentInputToRatio(value) } }))} /></FieldShell>
        <FieldShell label="Take Profit %" helper="Closes the trade after a predefined gain target is reached."><AffixInput value={ratioToPercentInput(request.risk_controls?.take_profit_pct)} suffix="%" min="0" step="0.1" placeholder="e.g. 8" onChange={(value) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), take_profit_pct: percentInputToRatio(value) } }))} /></FieldShell>
      </div>
      <div className="overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-1)]">
        <button type="button" onClick={() => setAdvancedOpen((prev) => !prev)} className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left"><div><div style={headingSmStyle}>Advanced: Parameter Tuning</div><p className="mt-1 text-sm text-[var(--text-secondary)]">Sweep parameter ranges to search for stronger combinations.</p></div><ChevronDown className={cn('h-4 w-4 text-[var(--text-secondary)] transition-transform duration-[250ms]', advancedOpen && 'rotate-180')} /></button>
        <div className={cn('grid transition-[grid-template-rows] duration-[250ms]', advancedOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]')}>
          <div className="overflow-hidden">
            <div className="border-t border-[var(--border-subtle)] px-4 py-4">
              <div className="flex items-center justify-between gap-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3"><div><div className="text-sm font-medium text-[var(--text-primary)]">Enable optimization</div><p className="mt-1 text-[11px] leading-5 text-[var(--text-tertiary)]">Run a bounded parameter sweep on the selected strategy.</p></div><ToggleSwitch checked={request.tuning?.enabled ?? false} onCheckedChange={(checked) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), enabled: checked } }))} /></div>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <FieldShell label="Objective"><select value={request.tuning?.objective ?? 'sharpe_ratio'} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), objective: event.target.value as BacktestObjective } }))}>{OBJECTIVES.map((objective) => <option key={objective.value} value={objective.value}>{objective.label}</option>)}</select></FieldShell>
                <FieldShell label="Max Combinations"><Input type="number" step="1" value={request.tuning?.max_combinations ?? 100} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), max_combinations: parseNumber(event.target.value, prev.tuning?.max_combinations ?? 100) } }))} /></FieldShell>
              </div>
              <div className="mt-4 space-y-3">{strategy.fields.map((field) => { const range = request.tuning?.parameter_ranges[field.key] ?? {}; return <div key={field.key} className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] p-4"><div style={headingSmStyle}>{field.label}</div><div className="mt-3 grid gap-3 sm:grid-cols-3"><FieldShell label="Min"><Input type="number" step={field.step} value={range.min ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), min: parseOptionalNumber(event.target.value) } } } }))} /></FieldShell><FieldShell label="Max"><Input type="number" step={field.step} value={range.max ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), max: parseOptionalNumber(event.target.value) } } } }))} /></FieldShell><FieldShell label="Step"><Input type="number" step={field.step} value={range.step ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: { ...prev.tuning?.parameter_ranges, [field.key]: { ...(prev.tuning?.parameter_ranges[field.key] ?? {}), step: parseOptionalNumber(event.target.value) } } } }))} /></FieldShell></div></div>; })}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
  const stepBody = activeStep === 'portfolio' ? portfolioStep : activeStep === 'strategy' ? strategyStep : riskStep;

  return (
    <>
      <form onSubmit={onSubmit} className="container-custom py-6 md:py-8">
        {returnHref ? <div className="mb-4"><Link href={returnHref} className="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"><ArrowLeft className="h-4 w-4" />{returnLabel}</Link></div> : null}
        <div className="grid gap-6 xl:grid-cols-[480px_minmax(0,1fr)] xl:items-start">
          <aside className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] shadow-[var(--shadow-sm)] xl:sticky xl:top-24 xl:h-[calc(100vh-7rem)]">
            <div className="flex h-full min-h-[760px] flex-col">
              <div className="border-b border-[var(--border-subtle)] px-5 py-5"><div className="flex items-center gap-3">{WIZARD_STEPS.map((step, index) => <div key={step.id} className="flex min-w-0 flex-1 items-center gap-3"><StepMarker index={index} label={step.shortLabel} active={activeStep === step.id} completed={completedSteps[step.id] && activeStep !== step.id} onClick={() => setActiveStep(step.id)} />{index < WIZARD_STEPS.length - 1 ? <div className="hidden flex-1 sm:block"><div className="h-px bg-[var(--border-default)]"><div className={cn('h-px transition-all duration-[250ms]', completedSteps[step.id] ? 'w-full bg-[var(--accent)]' : 'w-0 bg-[var(--accent)]')} /></div></div> : null}</div>)}</div></div>
              <div className="flex-1 overflow-y-auto px-5 py-5">{stepBody}<div className="border-t border-[var(--border-subtle)] pt-4"><button type="button" onClick={resetDefaults} className="text-sm text-[var(--text-tertiary)] underline-offset-4 transition-colors hover:text-[var(--text-primary)] hover:underline">Reset to defaults</button></div></div>
              <div className={cn('border-t border-[var(--border-subtle)] bg-[var(--bg-base)] px-5 py-5 transition-colors duration-[180ms]', runSuccessPulse && 'wizard-run-success')}>
                {!canRun ? <div className="mb-3 text-sm text-[var(--text-tertiary)]">{resolvedTickers.length === 0 ? 'Add at least one ticker to run the backtest.' : allocationOverweight ? 'Allocated capital must be 100% or less.' : dateRangeInvalid ? 'Fix the date range before running.' : 'Complete the required inputs to run the backtest.'}</div> : null}
                <Button type="submit" className="w-full" disabled={!canRun || mutation.isPending}>{mutation.isPending ? <><Loader2 className="h-4 w-4 animate-spin" />Running...</> : 'Run Backtest'}</Button>
              </div>
            </div>
          </aside>

          <section className="space-y-6">
            {!result && !mutation.isPending && !mutation.error ? (
              <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] shadow-[var(--shadow-sm)]"><EmptyResultsState /></div>
            ) : mutation.error && !result ? (
              <div className="rounded-[var(--radius-xl)] border border-[var(--negative)]/40 bg-[var(--bg-surface-1)] p-8 shadow-[var(--shadow-sm)]"><div style={headingMdStyle}>Backtest failed</div><p className="mt-2 text-sm text-[var(--negative)]">{(mutation.error as Error).message || 'The request could not be completed.'}</p></div>
            ) : result ? (
              <div className="results-enter space-y-6">
                {result.warnings.length > 0 ? <div className="rounded-[var(--radius-lg)] border border-[var(--accent)]/30 bg-[var(--accent-subtle)] px-4 py-3 text-sm text-[var(--text-primary)]">{result.warnings.map((warning) => <div key={warning}>{warning}</div>)}</div> : null}
                <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]"><div className="flex flex-wrap items-start justify-between gap-4"><div><div style={headingMdStyle}>Equity Curve</div><p className="mt-1 text-sm text-[var(--text-secondary)]">{formatDate(result.start_date)} to {formatDate(result.end_date)} {'\u00B7'} {result.timeframe}</p></div><div className="flex items-center gap-3 text-sm text-[var(--text-tertiary)]">{mutation.isPending ? <span className="inline-flex items-center gap-2 text-[var(--text-secondary)]"><Loader2 className="h-4 w-4 animate-spin" />Running new backtest</span> : null}<span>{result.source}{result.cached ? ' / cached' : ''}</span></div></div><div className="mt-5"><EquityCurveChart key={runVersion} points={equityData} showBenchmark={Boolean(result.buy_and_hold) && request.include_buy_and_hold} runVersion={runVersion} /></div></div>
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">{metrics.map((metric, index) => <MetricCard key={`${metric.key}-${runVersion}`} label={metric.label} value={metric.value} tone={metric.tone} delay={index * 60} />)}</div>
                <div className="rounded-[var(--radius-xl)] border border-[var(--border-default)] bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]"><div className="flex flex-wrap items-end justify-between gap-4"><div><div style={headingMdStyle}>Trade Log</div>{tradeSummary ? <p className="mt-1 text-sm text-[var(--text-secondary)]">{tradeSummary.tradeCount} trades {'\u00B7'} {tradeSummary.winRate.toFixed(1)}% win rate {'\u00B7'} Avg hold: {tradeSummary.avgHoldDays.toFixed(1)} days</p> : null}</div><div className="flex flex-wrap gap-2 text-xs text-[var(--text-tertiary)]">{result.tickers.map((symbol) => <span key={symbol} className="rounded-full border border-[var(--border-default)] px-2.5 py-1">{symbol} {Number(result.allocation_weights?.[symbol] ?? 0).toFixed(2)}%</span>)}{result.cash_reserve_pct > 0 ? <span className="rounded-full border border-[var(--border-default)] px-2.5 py-1">Cash {Number(result.cash_reserve_pct).toFixed(2)}%</span> : null}</div></div><div className="mt-5 overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border-default)]"><div className="max-h-[420px] overflow-auto"><table className="w-full min-w-[860px] tabular-nums"><thead className="sticky top-0 z-10 bg-[var(--bg-surface-2)]"><tr className="border-b border-[var(--border-default)] text-xs font-medium text-[var(--text-secondary)]">{[{ field: 'index', label: '#' }, { field: 'ticker', label: 'Ticker' }, { field: 'entry_date', label: 'Entry Date' }, { field: 'entry_price', label: 'Entry Price' }, { field: 'exit_date', label: 'Exit Date' }, { field: 'exit_price', label: 'Exit Price' }, { field: 'return_pct', label: 'Return %' }, { field: 'pnl', label: 'P&L' }].map((column) => <th key={column.field} className="px-4 py-3 text-left"><button type="button" onClick={() => setTradeSort((prev) => ({ field: column.field as TradeSortField, order: prev.field === column.field && prev.order === 'asc' ? 'desc' : 'asc' }))} className="inline-flex items-center gap-2 transition-colors hover:text-[var(--text-primary)]"><span>{column.label}</span><SortIndicator active={tradeSort.field === column.field} order={tradeSort.order} /></button></th>)}</tr></thead><tbody>{sortedTradeRows.length > 0 ? sortedTradeRows.map((trade, index) => <tr key={`${trade.ticker}-${trade.entryDate}-${trade.index}`} className={cn('border-b border-[var(--border-subtle)]', index % 2 === 0 ? 'bg-[var(--bg-surface-1)]' : 'bg-[var(--bg-base)]')}><td className="px-4 py-3">{trade.index}</td><td className="px-4 py-3 font-medium text-[var(--text-primary)]">{trade.ticker}</td><td className="px-4 py-3">{formatDate(trade.entryDate)}</td><td className="px-4 py-3">{formatCurrency(trade.entryPrice)}</td><td className="px-4 py-3">{formatDate(trade.exitDate)}</td><td className="px-4 py-3">{formatCurrency(trade.exitPrice)}</td><td className={cn('px-4 py-3', trade.returnPct >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]')}>{formatPercent(trade.returnPct, { mode: 'percent' })}</td><td className={cn('px-4 py-3', trade.pnl >= 0 ? 'text-[var(--positive)]' : 'text-[var(--negative)]')}>{formatCurrency(trade.pnl)}</td></tr>) : <tr><td colSpan={8} className="px-4 py-10 text-center text-sm text-[var(--text-tertiary)]">No trades were generated for this configuration.</td></tr>}</tbody></table></div></div>{result.tuning_summary?.enabled ? <div className="mt-4 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-4 py-3 text-sm text-[var(--text-secondary)]">Optimization ran on {result.tuning_summary.objective} across {result.tuning_summary.evaluated_combinations} combinations.</div> : null}</div>
              </div>
            ) : null}
          </section>
        </div>
      </form>

      <style jsx>{`
        .wizard-run-success { animation: backtester-success-flash 500ms ease; }
        .results-enter { animation: results-fade 300ms ease; }
        .metric-card-enter { opacity: 0; transform: translateY(12px); animation: metric-enter 300ms ease forwards; }
        .parameter-section-enter { animation: parameter-enter 250ms ease; }
        @keyframes backtester-success-flash { 0% { box-shadow: inset 0 0 0 0 rgba(74, 222, 128, 0); } 50% { box-shadow: inset 0 0 0 1px rgba(74, 222, 128, 0.95); } 100% { box-shadow: inset 0 0 0 0 rgba(74, 222, 128, 0); } }
        @keyframes results-fade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes metric-enter { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes parameter-enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
    </>
  );
}
