'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, RotateCcw, Search, SlidersHorizontal } from 'lucide-react';

import HelpPopover from '@/components/ui/help-popover';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { screenerAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { ScreenerFilters } from '@/types/stock';

interface FilterPanelProps {
  onFilterChange: (filters: ScreenerFilters) => void;
  onReset: () => void;
  search?: string;
}

const formatIntegerForInput = (value: number | undefined): string => {
  if (value === undefined || Number.isNaN(value)) return '';
  return Math.trunc(value).toLocaleString('en-US');
};

const parseIntegerInput = (rawValue: string): number | undefined => {
  const digitsOnly = rawValue.replace(/[^0-9]/g, '');
  if (!digitsOnly) return undefined;
  return parseInt(digitsOnly, 10);
};

const parseFloatInput = (rawValue: string): number | undefined => {
  const trimmed = rawValue.trim();
  if (!trimmed) return undefined;
  const parsed = parseFloat(trimmed);
  return Number.isNaN(parsed) ? undefined : parsed;
};

const toPercentInputValue = (decimalValue: number | undefined): string => {
  if (decimalValue === undefined || Number.isNaN(decimalValue)) return '';
  return (decimalValue * 100).toString();
};

const fromPercentInput = (rawValue: string): number | undefined => {
  const parsed = parseFloatInput(rawValue);
  if (parsed === undefined) return undefined;
  return parsed / 100;
};

function Group({
  title,
  children,
  defaultOpen = false,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-lg border border-border/70 bg-muted/20">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-4 text-left"
      >
        <div className="text-sm font-medium text-foreground">{title}</div>
        <ChevronDown className={cn('h-4 w-4 text-primary transition-transform', open && 'rotate-180')} />
      </button>
      {open ? <div className="border-t border-border/70 p-4">{children}</div> : null}
    </div>
  );
}

function Field({
  label,
  help,
  suggestion,
  children,
}: {
  label: string;
  help?: string;
  suggestion?: string;
  children: ReactNode;
}) {
  return (
    <label className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
        {help ? <HelpPopover title={label} description={help} suggestion={suggestion} /> : null}
      </div>
      {children}
    </label>
  );
}

export default function FilterPanel({ onFilterChange, onReset, search }: FilterPanelProps) {
  const [filters, setFilters] = useState<ScreenerFilters>({
    limit: 50,
    sort_by: 'market_cap',
    sort_order: 'desc',
    search,
    skip: 0,
  });

  const { data: sectors } = useQuery({
    queryKey: ['screener-sectors'],
    queryFn: () => screenerAPI.getSectors(),
  });

  const { data: industries } = useQuery({
    queryKey: ['screener-industries'],
    queryFn: () => screenerAPI.getIndustries(),
  });

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      search,
    }));
  }, [search]);

  const selectedSectorSet = useMemo(() => new Set(filters.sectors ?? []), [filters.sectors]);
  const selectedIndustrySet = useMemo(() => new Set(filters.industries ?? []), [filters.industries]);

  const handleInputChange = (
    field: keyof ScreenerFilters,
    value: number | string | string[] | undefined
  ) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const toggleArrayValue = (field: 'sectors' | 'industries', value: string) => {
    setFilters((prev) => {
      const current = new Set(prev[field] ?? []);
      if (current.has(value)) current.delete(value);
      else current.add(value);
      const next = Array.from(current);
      return {
        ...prev,
        [field]: next.length > 0 ? next : undefined,
      };
    });
  };

  const handleApplyFilters = () => {
    onFilterChange({
      ...filters,
      skip: 0,
    });
  };

  const handleReset = () => {
    const resetFilters: ScreenerFilters = {
      limit: 50,
      sort_by: 'market_cap',
      sort_order: 'desc',
      search,
      skip: 0,
    };
    setFilters(resetFilters);
    onReset();
  };

  return (
    <div className="deco-panel p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="deco-kicker">Controls</div>
          <h2 className="mt-2">Screener Controls</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Tune the market universe without sacrificing table density.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button type="button" variant="ghost" onClick={handleReset}>
            <RotateCcw className="h-4 w-4" />
            Reset
          </Button>
          <Button type="button" onClick={handleApplyFilters}>
            <SlidersHorizontal className="h-4 w-4" />
            Apply Filters
          </Button>
        </div>
      </div>

      <div className="deco-divider" />

      <div className="grid gap-4">
        <Group title="Search" defaultOpen>
          <div className="grid gap-4 lg:grid-cols-2">
            <Field
              label="Ticker or Company"
              help="Use a ticker, company fragment, or both. This is the fastest way to narrow the table."
              suggestion="AAPL, NVIDIA, or bank"
            >
              <div className="flex items-center gap-3 rounded-md border border-border/70 bg-muted/20 px-4 py-3">
                <Search className="h-4 w-4 text-primary" />
                <input
                  type="text"
                  value={filters.search ?? ''}
                  onChange={(event) => handleInputChange('search', event.target.value || undefined)}
                  placeholder="Search ticker or company"
                  className="w-full border-none bg-transparent p-0 text-sm text-foreground shadow-none outline-none placeholder:text-muted-foreground focus:border-none focus:shadow-none"
                />
              </div>
            </Field>
            <Field
              label="Result Limit"
              help="Raise the limit when you want a broader table. Keep it moderate for faster comparison."
              suggestion="50 to 100"
            >
              <div className="space-y-3 pt-2">
                <div className="text-sm text-foreground tabular-nums">{filters.limit ?? 50} rows</div>
                <Slider
                  value={[filters.limit ?? 50]}
                  onValueChange={(value) => handleInputChange('limit', value[0])}
                  min={10}
                  max={150}
                  step={10}
                />
              </div>
            </Field>
          </div>
        </Group>

        <Group title="Valuation and Price" defaultOpen>
          <div className="grid gap-4 lg:grid-cols-4">
            <Field label="Min P/E" help="Useful for excluding loss-making or extreme valuation names." suggestion="5 to 10">
              <Input type="number" value={filters.min_pe ?? ''} onChange={(e) => handleInputChange('min_pe', parseFloatInput(e.target.value))} />
            </Field>
            <Field label="Max P/E" help="Cap the valuation range to avoid overpriced names." suggestion="25 to 40">
              <Input type="number" value={filters.max_pe ?? ''} onChange={(e) => handleInputChange('max_pe', parseFloatInput(e.target.value))} />
            </Field>
            <Field label="Min Price" help="Removes penny stocks and illiquid low-price names." suggestion="5">
              <Input type="number" value={filters.min_price ?? ''} onChange={(e) => handleInputChange('min_price', parseFloatInput(e.target.value))} />
            </Field>
            <Field label="Max Price" help="Useful if you want a tighter price band." suggestion="500">
              <Input type="number" value={filters.max_price ?? ''} onChange={(e) => handleInputChange('max_price', parseFloatInput(e.target.value))} />
            </Field>
            <Field label="Market Cap Min" help="Large-cap studies often start at $10B or $50B." suggestion="10,000,000,000">
              <Input type="text" inputMode="numeric" value={formatIntegerForInput(filters.min_market_cap)} onChange={(e) => handleInputChange('min_market_cap', parseIntegerInput(e.target.value))} />
            </Field>
            <Field label="Market Cap Max" help="Leave blank for no ceiling or cap for mid-cap focus." suggestion="250,000,000,000">
              <Input type="text" inputMode="numeric" value={formatIntegerForInput(filters.max_market_cap)} onChange={(e) => handleInputChange('max_market_cap', parseIntegerInput(e.target.value))} />
            </Field>
            <Field label="Min Volume" help="Reduces low-liquidity names that are harder to trade." suggestion="500,000">
              <Input type="text" inputMode="numeric" value={formatIntegerForInput(filters.min_volume)} onChange={(e) => handleInputChange('min_volume', parseIntegerInput(e.target.value))} />
            </Field>
            <Field label="Min Avg Volume" help="Average volume gives a cleaner liquidity filter than a single day." suggestion="1,000,000">
              <Input type="text" inputMode="numeric" value={formatIntegerForInput(filters.min_avg_volume)} onChange={(e) => handleInputChange('min_avg_volume', parseIntegerInput(e.target.value))} />
            </Field>
          </div>
        </Group>

        <Group title="Quality and Risk">
          <div className="grid gap-4 lg:grid-cols-4">
            <Field label="Min ROE (%)" help="Higher ROE filters for stronger profitability." suggestion="15">
              <Input type="number" step="0.1" value={toPercentInputValue(filters.min_roe)} onChange={(e) => handleInputChange('min_roe', fromPercentInput(e.target.value))} />
            </Field>
            <Field label="Min Revenue Growth (%)" help="Filters for expanding businesses." suggestion="10">
              <Input type="number" step="0.1" value={toPercentInputValue(filters.min_revenue_growth)} onChange={(e) => handleInputChange('min_revenue_growth', fromPercentInput(e.target.value))} />
            </Field>
            <Field label="Min Dividend Yield (%)" help="Useful for income-oriented screens." suggestion="1.5">
              <Input type="number" step="0.1" value={toPercentInputValue(filters.min_dividend_yield)} onChange={(e) => handleInputChange('min_dividend_yield', fromPercentInput(e.target.value))} />
            </Field>
            <Field label="Max Debt to Equity" help="Keeps leverage within a defined band." suggestion="2.0">
              <Input type="number" step="0.1" value={filters.max_debt_to_equity ?? ''} onChange={(e) => handleInputChange('max_debt_to_equity', parseFloatInput(e.target.value))} />
            </Field>
            <Field label="Max Beta" help="Useful when you want calmer names with lower volatility." suggestion="1.5">
              <Input type="number" step="0.1" value={filters.max_beta ?? ''} onChange={(e) => handleInputChange('max_beta', parseFloatInput(e.target.value))} />
            </Field>
          </div>
        </Group>

        <Group title="Sector and Industry">
          <div className="grid gap-5">
            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                Sector Focus
                <HelpPopover
                  title="Sector Focus"
                  description="Sectors let you isolate broad themes before drilling into specific industries."
                  suggestion="Technology, Financial Services, Healthcare"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                {(sectors?.sectors ?? []).map((sector) => (
                  <button
                    key={sector}
                    type="button"
                    onClick={() => toggleArrayValue('sectors', sector)}
                    className={cn(
                      'rounded-full border px-3 py-2 text-xs font-medium transition-[background,border-color,box-shadow,color,transform] duration-[180ms]',
                      selectedSectorSet.has(sector)
                        ? 'border-primary/40 bg-[var(--accent-subtle)] text-primary'
                        : 'border-border/70 text-muted-foreground hover:border-primary/30 hover:text-foreground'
                    )}
                  >
                    {sector}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-medium text-muted-foreground">
                Industry Focus
                <HelpPopover
                  title="Industry Focus"
                  description="Industries apply a tighter thematic cut after selecting sectors."
                  suggestion="Semiconductors, Banks, Software"
                />
              </div>
              <div className="flex max-h-44 flex-wrap gap-2 overflow-auto pr-1">
                {(industries?.industries ?? []).slice(0, 48).map((industry) => (
                  <button
                    key={industry}
                    type="button"
                    onClick={() => toggleArrayValue('industries', industry)}
                    className={cn(
                      'rounded-full border px-3 py-2 text-xs font-medium transition-[background,border-color,box-shadow,color,transform] duration-[180ms]',
                      selectedIndustrySet.has(industry)
                        ? 'border-primary/40 bg-[var(--accent-subtle)] text-primary'
                        : 'border-border/70 text-muted-foreground hover:border-primary/30 hover:text-foreground'
                    )}
                  >
                    {industry}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Group>

        <Group title="Sorting">
          <div className="grid gap-4 lg:grid-cols-2">
            <Field label="Sort By" help="Choose the ranking dimension for the table." suggestion="Market Cap or Daily Change %">
              <select value={filters.sort_by ?? 'market_cap'} onChange={(e) => handleInputChange('sort_by', e.target.value)}>
                <option value="market_cap">Market Cap</option>
                <option value="current_price">Price</option>
                <option value="day_change_percent">Daily Change %</option>
                <option value="volume">Volume</option>
                <option value="avg_volume">Avg Volume</option>
                <option value="pe_ratio">P/E</option>
                <option value="roe">ROE</option>
                <option value="revenue_growth">Revenue Growth</option>
                <option value="dividend_yield">Dividend Yield</option>
                <option value="beta">Beta</option>
              </select>
            </Field>
            <Field label="Order" help="Descending is usually best for leaders and largest names." suggestion="Descending">
              <select
                value={filters.sort_order ?? 'desc'}
                onChange={(e) => handleInputChange('sort_order', e.target.value as 'asc' | 'desc')}
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </Field>
          </div>
        </Group>
      </div>
    </div>
  );
}
