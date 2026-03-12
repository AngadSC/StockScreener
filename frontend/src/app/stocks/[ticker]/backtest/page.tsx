'use client';

import Link from 'next/link';
import { useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { stocksAPI } from '@/lib/api';
import { cn, formatCurrency, formatDate, formatNumber, formatPercent } from '@/lib/utils';
import type { BacktestObjective, BacktestRunRequest, BacktestStrategyFamily } from '@/types/stock';

type StrategyField = { key: string; label: string; step: number };
type StrategyDef = {
  family: BacktestStrategyFamily;
  label: string;
  description: string;
  defaults: Record<string, number>;
  fields: StrategyField[];
};

const STRATEGIES: StrategyDef[] = [
  { family: 'trend_following', label: 'Trend Following', description: 'EMA crossover.', defaults: { fast_ema: 50, slow_ema: 200 }, fields: [{ key: 'fast_ema', label: 'Fast EMA', step: 1 }, { key: 'slow_ema', label: 'Slow EMA', step: 1 }] },
  { family: 'mean_reversion', label: 'Mean Reversion', description: 'Bollinger Band bounce.', defaults: { window: 20, std_dev: 2 }, fields: [{ key: 'window', label: 'Band Window', step: 1 }, { key: 'std_dev', label: 'Std Dev', step: 0.1 }] },
  { family: 'momentum_breakout', label: 'Momentum Breakout', description: 'Break above rolling high, exit on rolling low.', defaults: { breakout_lookback: 50, exit_lookback: 20 }, fields: [{ key: 'breakout_lookback', label: 'Breakout', step: 1 }, { key: 'exit_lookback', label: 'Exit', step: 1 }] },
  { family: 'oversold_reversal', label: 'Oversold Reversal', description: 'RSI oversold bounce.', defaults: { rsi_period: 14, entry_rsi: 30, exit_rsi: 50 }, fields: [{ key: 'rsi_period', label: 'RSI Period', step: 1 }, { key: 'entry_rsi', label: 'Entry RSI', step: 0.1 }, { key: 'exit_rsi', label: 'Exit RSI', step: 0.1 }] },
  { family: 'moving_average_pullback', label: 'Moving Average Pullback', description: 'Buy pullbacks in an uptrend.', defaults: { trend_ma: 200, pullback_ma: 20, entry_buffer_pct: 0.01 }, fields: [{ key: 'trend_ma', label: 'Trend MA', step: 1 }, { key: 'pullback_ma', label: 'Pullback MA', step: 1 }, { key: 'entry_buffer_pct', label: 'Buffer', step: 0.001 }] },
  { family: 'volume_breakout', label: 'Volume Breakout', description: 'Resistance break with volume confirmation.', defaults: { breakout_lookback: 20, exit_lookback: 10, volume_window: 20, volume_multiplier: 2 }, fields: [{ key: 'breakout_lookback', label: 'Breakout', step: 1 }, { key: 'exit_lookback', label: 'Exit', step: 1 }, { key: 'volume_window', label: 'Volume Window', step: 1 }, { key: 'volume_multiplier', label: 'Volume Mult', step: 0.1 }] },
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

function createDefaultRequest(ticker: string): BacktestRunRequest {
  const end = new Date();
  const start = new Date(end);
  start.setFullYear(end.getFullYear() - 5);
  return {
    start_date: toInputDate(start),
    end_date: toInputDate(end),
    tickers: [ticker],
    timeframe: '1d',
    initial_capital: 10000,
    tc_bps: 5,
    allow_fractional_shares: true,
    strategy: { family: 'trend_following', params: { fast_ema: 50, slow_ema: 200 } },
    risk_controls: { stop_loss_pct: null, trailing_stop_pct: null, take_profit_pct: null },
    tuning: { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} },
    generate_plots: true,
  };
}

function Field({ label, help, children }: { label: string; help?: string; children: ReactNode }) {
  return (
    <label className="space-y-2 text-sm">
      <div className="font-medium text-foreground">{label}</div>
      {children}
      {help ? <div className="text-xs text-muted-foreground">{help}</div> : null}
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

interface PageProps {
  params: { ticker: string };
}

export default function StockBacktestPage({ params }: PageProps) {
  const ticker = params.ticker.toUpperCase();
  const [request, setRequest] = useState<BacktestRunRequest>(() => createDefaultRequest(ticker));
  const [basketInput, setBasketInput] = useState(ticker);

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

  const result = mutation.data;
  const equityData = (result?.equity_curve ?? []).map((row) => ({
    date: String(row.Date ?? ''),
    equity: Number(row.Equity ?? 0),
  }));

  const setStrategyFamily = (family: BacktestStrategyFamily) => {
    const next = STRATEGIES.find((item) => item.family === family) ?? STRATEGIES[0];
    setRequest((prev) => ({
      ...prev,
      strategy: { family: next.family, params: { ...next.defaults } },
      tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), parameter_ranges: {} },
    }));
  };

  const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const tickers = basketInput.split(',').map((item) => item.trim().toUpperCase()).filter(Boolean);
    const riskControls = Object.fromEntries(Object.entries(request.risk_controls ?? {}).filter(([, value]) => value !== null && value !== undefined));
    const parameterRanges = Object.fromEntries(
      Object.entries(request.tuning?.parameter_ranges ?? {}).filter(([, range]) => range.min != null && range.max != null && range.step != null)
    );
    mutation.mutate({
      ...request,
      tickers,
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
        <Button variant="outline" onClick={() => { setRequest(createDefaultRequest(ticker)); setBasketInput(ticker); }}>
          RESET_DEFAULTS
        </Button>
      </div>

      <section className="terminal-border bg-card p-8">
        <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground">Portfolio Backtester</div>
        <h1 className="mt-3 text-4xl font-bold text-glow">{ticker}</h1>
        <p className="mt-2 max-w-3xl text-muted-foreground">
          {stock?.name ?? 'Run strategy-family backtests across one stock or a basket with capital sizing, risk controls, tuning, and a trade log.'}
        </p>
      </section>

      <form className="grid gap-6 xl:grid-cols-[1.06fr_0.94fr]" onSubmit={onSubmit}>
        <div className="space-y-6">
          <section className="terminal-border bg-card p-6 space-y-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold">Run Config</h2>
                <p className="text-sm text-muted-foreground">Basket, capital, date range, and timeframe.</p>
              </div>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? <><Loader2 className="h-4 w-4 animate-spin" />RUNNING</> : 'RUN BACKTEST'}
              </Button>
            </div>
            <Field label="Basket Tickers" help="Comma-separated symbols. The page ticker is included automatically if missing.">
              <textarea value={basketInput} onChange={(event) => setBasketInput(event.target.value.toUpperCase())} className="min-h-[88px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring" />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <Field label="Start Date"><Input type="date" value={request.start_date} onChange={(event) => setRequest((prev) => ({ ...prev, start_date: event.target.value }))} /></Field>
              <Field label="End Date"><Input type="date" value={request.end_date} onChange={(event) => setRequest((prev) => ({ ...prev, end_date: event.target.value }))} /></Field>
              <Field label="Timeframe">
                <select value={request.timeframe} onChange={(event) => setRequest((prev) => ({ ...prev, timeframe: event.target.value as BacktestRunRequest['timeframe'] }))} className="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <option value="1d">Daily</option>
                  <option value="1wk">Weekly</option>
                  <option value="1mo">Monthly</option>
                </select>
              </Field>
              <Field label="Starting Capital"><Input type="number" step="100" value={request.initial_capital} onChange={(event) => setRequest((prev) => ({ ...prev, initial_capital: parseNumber(event.target.value, prev.initial_capital) }))} /></Field>
              <Field label="Transaction Cost (bps)"><Input type="number" step="1" value={request.tc_bps} onChange={(event) => setRequest((prev) => ({ ...prev, tc_bps: parseNumber(event.target.value, prev.tc_bps) }))} /></Field>
              <label className="flex items-center justify-between rounded border border-border bg-muted/10 px-3 py-3 text-sm">
                <span>Fractional Shares</span>
                <input type="checkbox" checked={request.allow_fractional_shares} onChange={(event) => setRequest((prev) => ({ ...prev, allow_fractional_shares: event.target.checked }))} className="h-4 w-4 accent-primary" />
              </label>
            </div>
          </section>

          <section className="terminal-border bg-card p-6 space-y-5">
            <div>
              <h2 className="text-lg font-bold">Strategy Family</h2>
              <p className="text-sm text-muted-foreground">Choose one of the six supported strategy families.</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {STRATEGIES.map((item) => (
                <button key={item.family} type="button" onClick={() => setStrategyFamily(item.family)} className={cn('rounded border p-4 text-left transition-colors', item.family === request.strategy.family ? 'border-primary/40 bg-primary/10' : 'border-border bg-muted/5 hover:border-primary/20 hover:bg-muted/10')}>
                  <div className="font-semibold text-foreground">{item.label}</div>
                  <div className="mt-2 text-sm text-muted-foreground">{item.description}</div>
                </button>
              ))}
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {strategy.fields.map((field) => (
                <Field key={field.key} label={field.label}>
                  <Input type="number" step={field.step} value={Number(request.strategy.params[field.key] ?? 0)} onChange={(event) => setRequest((prev) => ({ ...prev, strategy: { ...prev.strategy, params: { ...prev.strategy.params, [field.key]: parseNumber(event.target.value, Number(prev.strategy.params[field.key] ?? 0)) } } }))} />
                </Field>
              ))}
            </div>
          </section>

          <section className="terminal-border bg-card p-6 space-y-5">
            <div>
              <h2 className="text-lg font-bold">Risk Controls</h2>
              <p className="text-sm text-muted-foreground">Optional fixed stop loss, trailing stop, and take-profit levels.</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field label="Stop Loss %"><Input type="number" step="0.001" value={request.risk_controls?.stop_loss_pct ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), stop_loss_pct: parseOptionalNumber(event.target.value) } }))} /></Field>
              <Field label="Trailing Stop %"><Input type="number" step="0.001" value={request.risk_controls?.trailing_stop_pct ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), trailing_stop_pct: parseOptionalNumber(event.target.value) } }))} /></Field>
              <Field label="Take Profit %"><Input type="number" step="0.001" value={request.risk_controls?.take_profit_pct ?? ''} onChange={(event) => setRequest((prev) => ({ ...prev, risk_controls: { ...(prev.risk_controls ?? {}), take_profit_pct: parseOptionalNumber(event.target.value) } }))} /></Field>
            </div>
          </section>

          <section className="terminal-border bg-card p-6 space-y-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold">Parameter Tuning</h2>
                <p className="text-sm text-muted-foreground">Optional grid search on the current strategy parameters.</p>
              </div>
              <label className="flex items-center gap-3 text-sm">
                <span>Enable</span>
                <input type="checkbox" checked={request.tuning?.enabled ?? false} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), enabled: event.target.checked } }))} className="h-4 w-4 accent-primary" />
              </label>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Objective">
                <select value={request.tuning?.objective ?? 'sharpe_ratio'} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), objective: event.target.value as BacktestObjective } }))} className="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  {OBJECTIVES.map((objective) => <option key={objective.value} value={objective.value}>{objective.label}</option>)}
                </select>
              </Field>
              <Field label="Max Combinations"><Input type="number" step="1" value={request.tuning?.max_combinations ?? 100} onChange={(event) => setRequest((prev) => ({ ...prev, tuning: { ...(prev.tuning ?? { enabled: false, objective: 'sharpe_ratio', max_combinations: 100, parameter_ranges: {} }), max_combinations: parseNumber(event.target.value, prev.tuning?.max_combinations ?? 100) } }))} /></Field>
            </div>
            <div className="space-y-3">
              {strategy.fields.map((field) => {
                const range = request.tuning?.parameter_ranges[field.key] ?? {};
                return (
                  <div key={field.key} className="rounded border border-border bg-muted/10 p-4">
                    <div className="mb-3 text-sm font-semibold text-foreground">{field.label}</div>
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
          <section className="terminal-border bg-card p-6 min-h-[220px]">
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
                <div className="flex flex-wrap gap-2">{result.tickers.map((symbol) => <span key={symbol} className="rounded border border-primary/30 bg-primary/10 px-2 py-1 text-xs text-primary">{symbol} · {result.data_sources[symbol]}</span>)}</div>
                <div className="grid gap-3 sm:grid-cols-2">{Object.entries(result.stats).filter(([key]) => STAT_LABELS[key]).map(([key, value]) => <StatCard key={key} statKey={key} value={Number(value)} />)}</div>
                {result.tuning_summary?.enabled ? <div className="rounded border border-border bg-muted/10 p-4 text-sm text-muted-foreground">Tuned on {result.tuning_summary.objective}. Evaluated {result.tuning_summary.evaluated_combinations} combinations.</div> : null}
              </div>
            ) : (
              <div className="flex min-h-[150px] items-center justify-center text-center text-sm text-muted-foreground">Run a configuration to populate stats, charts, and the trade log.</div>
            )}
          </section>

          {result ? (
            <>
              <section className="terminal-border bg-card p-6">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <h2 className="text-lg font-bold">Equity Curve</h2>
                  <div className="text-xs text-muted-foreground">{formatDate(result.start_date)} - {formatDate(result.end_date)} · {result.timeframe.toUpperCase()}</div>
                </div>
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={equityData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" />
                      <XAxis dataKey="date" minTickGap={36} stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" domain={['auto', 'auto']} />
                      <Tooltip contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(148, 163, 184, 0.25)', borderRadius: '0.5rem' }} formatter={(value: number | string | undefined) => [formatNumber(typeof value === 'number' ? value : Number(value ?? 0)), 'EQUITY']} />
                      <Line type="monotone" dataKey="equity" stroke="#22c55e" strokeWidth={2} dot={false} />
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
