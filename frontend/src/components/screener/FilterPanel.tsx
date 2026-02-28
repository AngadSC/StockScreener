'use client';

import { useEffect, useState } from 'react';
import { Play, RotateCcw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { ScreenerFilters } from '@/types/stock';

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

export default function FilterPanel({ onFilterChange, onReset, search }: FilterPanelProps) {
  const [filters, setFilters] = useState<ScreenerFilters>({
    limit: 50,
    sort_by: 'market_cap',
    sort_order: 'desc',
    search,
  });

  useEffect(() => {
    setFilters((prev) => ({
      ...prev,
      search,
    }));
  }, [search]);

  const handleInputChange = (field: keyof ScreenerFilters, value: number | string | undefined) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
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
    <div className="terminal-border bg-card h-fit sticky top-20">
      <div className="border-b border-border px-4 py-3 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold tracking-wide">SCREENER FILTERS</p>
          <p className="text-[10px] text-muted-foreground mt-1">Percent fields accept whole % values, e.g. 15 for 15%</p>
        </div>
        <button
          onClick={handleReset}
          className="text-xs text-muted-foreground hover:text-primary transition-colors flex items-center gap-1.5"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          RESET
        </button>
      </div>

      <div className="p-4 space-y-5 text-xs">
        <div className="space-y-2">
          <p className="text-[11px] font-semibold text-foreground/90">Valuation</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block mb-1 text-muted-foreground">Min P/E</label>
              <Input
                type="number"
                placeholder="0"
                className="h-8 text-xs"
                value={filters.min_pe ?? ''}
                onChange={(e) => handleInputChange('min_pe', parseFloatInput(e.target.value))}
              />
            </div>
            <div>
              <label className="block mb-1 text-muted-foreground">Max P/E</label>
              <Input
                type="number"
                placeholder="50"
                className="h-8 text-xs"
                value={filters.max_pe ?? ''}
                onChange={(e) => handleInputChange('max_pe', parseFloatInput(e.target.value))}
              />
            </div>
          </div>
          <div>
            <label className="block mb-1 text-muted-foreground">Market Cap Min ($)</label>
            <Input
              type="text"
              inputMode="numeric"
              placeholder="1,000,000,000"
              className="h-8 text-xs"
              value={formatIntegerForInput(filters.min_market_cap)}
              onChange={(e) => handleInputChange('min_market_cap', parseIntegerInput(e.target.value))}
            />
          </div>
          <div>
            <label className="block mb-1 text-muted-foreground">Market Cap Max ($)</label>
            <Input
              type="text"
              inputMode="numeric"
              placeholder="10,000,000,000"
              className="h-8 text-xs"
              value={formatIntegerForInput(filters.max_market_cap)}
              onChange={(e) => handleInputChange('max_market_cap', parseIntegerInput(e.target.value))}
            />
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-semibold text-foreground/90">Price and Liquidity</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block mb-1 text-muted-foreground">Min Price ($)</label>
              <Input
                type="number"
                placeholder="0"
                className="h-8 text-xs"
                value={filters.min_price ?? ''}
                onChange={(e) => handleInputChange('min_price', parseFloatInput(e.target.value))}
              />
            </div>
            <div>
              <label className="block mb-1 text-muted-foreground">Max Price ($)</label>
              <Input
                type="number"
                placeholder="500"
                className="h-8 text-xs"
                value={filters.max_price ?? ''}
                onChange={(e) => handleInputChange('max_price', parseFloatInput(e.target.value))}
              />
            </div>
          </div>
          <div>
            <label className="block mb-1 text-muted-foreground">Min Volume</label>
            <Input
              type="text"
              inputMode="numeric"
              placeholder="500,000"
              className="h-8 text-xs"
              value={formatIntegerForInput(filters.min_volume)}
              onChange={(e) => handleInputChange('min_volume', parseIntegerInput(e.target.value))}
            />
          </div>
          <div>
            <label className="block mb-1 text-muted-foreground">Min Avg Volume</label>
            <Input
              type="text"
              inputMode="numeric"
              placeholder="1,000,000"
              className="h-8 text-xs"
              value={formatIntegerForInput(filters.min_avg_volume)}
              onChange={(e) => handleInputChange('min_avg_volume', parseIntegerInput(e.target.value))}
            />
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-semibold text-foreground/90">Quality and Risk</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block mb-1 text-muted-foreground">Min ROE (%)</label>
              <Input
                type="number"
                step="0.1"
                placeholder="15"
                className="h-8 text-xs"
                value={toPercentInputValue(filters.min_roe)}
                onChange={(e) => handleInputChange('min_roe', fromPercentInput(e.target.value))}
              />
            </div>
            <div>
              <label className="block mb-1 text-muted-foreground">Min Revenue Growth (%)</label>
              <Input
                type="number"
                step="0.1"
                placeholder="10"
                className="h-8 text-xs"
                value={toPercentInputValue(filters.min_revenue_growth)}
                onChange={(e) => handleInputChange('min_revenue_growth', fromPercentInput(e.target.value))}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block mb-1 text-muted-foreground">Min Dividend Yield (%)</label>
              <Input
                type="number"
                step="0.1"
                placeholder="1.5"
                className="h-8 text-xs"
                value={toPercentInputValue(filters.min_dividend_yield)}
                onChange={(e) => handleInputChange('min_dividend_yield', fromPercentInput(e.target.value))}
              />
            </div>
            <div>
              <label className="block mb-1 text-muted-foreground">Max Debt to Equity</label>
              <Input
                type="number"
                step="0.1"
                placeholder="2.0"
                className="h-8 text-xs"
                value={filters.max_debt_to_equity ?? ''}
                onChange={(e) => handleInputChange('max_debt_to_equity', parseFloatInput(e.target.value))}
              />
            </div>
          </div>
          <div>
            <label className="block mb-1 text-muted-foreground">Max Beta</label>
            <Input
              type="number"
              step="0.1"
              placeholder="1.5"
              className="h-8 text-xs"
              value={filters.max_beta ?? ''}
              onChange={(e) => handleInputChange('max_beta', parseFloatInput(e.target.value))}
            />
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-[11px] font-semibold text-foreground/90">Sorting and Output</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block mb-1 text-muted-foreground">Sort By</label>
              <select
                className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-xs"
                value={filters.sort_by ?? 'market_cap'}
                onChange={(e) => handleInputChange('sort_by', e.target.value)}
              >
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
            </div>
            <div>
              <label className="block mb-1 text-muted-foreground">Order</label>
              <select
                className="h-8 w-full rounded-md border border-input bg-transparent px-2 text-xs"
                value={filters.sort_order ?? 'desc'}
                onChange={(e) => handleInputChange('sort_order', e.target.value as 'asc' | 'desc')}
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block mb-1 text-muted-foreground">Result Limit: {filters.limit ?? 50}</label>
            <Slider
              value={[filters.limit ?? 50]}
              onValueChange={(value) => handleInputChange('limit', value[0])}
              min={10}
              max={150}
              step={10}
              className="mt-2"
            />
            <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
              <span>10</span>
              <span>150</span>
            </div>
          </div>
        </div>

        <button
          onClick={handleApplyFilters}
          className="w-full border border-primary bg-primary/10 hover:bg-primary/20 text-primary py-2 transition-colors flex items-center justify-center gap-2 font-bold"
        >
          <Play className="h-3.5 w-3.5" />
          APPLY FILTERS
        </button>
      </div>
    </div>
  );
}
