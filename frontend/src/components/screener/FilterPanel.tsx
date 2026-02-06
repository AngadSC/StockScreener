'use client';

import { useEffect, useState } from 'react';
import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';
import { ScreenerFilters } from '@/types/stock';
import { Play, RotateCcw } from 'lucide-react';

interface FilterPanelProps {
  onFilterChange: (filters: ScreenerFilters) => void;
  onReset: () => void;
  search?: string;
}

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

  const handleInputChange = (field: keyof ScreenerFilters, value: any) => {
    const newFilters = { ...filters, [field]: value };
    setFilters(newFilters);
  };

  const handleApplyFilters = () => {
    onFilterChange(filters);
  };

  const handleReset = () => {
    const resetFilters: ScreenerFilters = {
      limit: 50,
      sort_by: 'market_cap',
      sort_order: 'desc',
      search,
    };
    setFilters(resetFilters);
    onReset();
  };

  return (
    <div className="terminal-border bg-card h-fit sticky top-20">
      {/* Header */}
      <div className="border-b border-border px-3 py-2 flex items-center justify-between">
        <span className="text-xs font-bold">FILTER_PARAMS</span>
        <button
          onClick={handleReset}
          className="text-xs text-muted-foreground hover:text-primary transition-colors flex items-center gap-1"
        >
          <RotateCcw className="h-3 w-3" />
          RESET
        </button>
      </div>

      <div className="p-3 space-y-4 text-xs">
        {/* Valuation */}
        <div className="space-y-2">
          <div className="text-muted-foreground mb-2">──[ VALUATION ]──</div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block mb-1 text-muted-foreground">MIN_PE</label>
              <Input
                type="number"
                placeholder="0"
                className="h-8 text-xs"
                value={filters.min_pe || ''}
                onChange={(e) => handleInputChange('min_pe', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
            <div>
              <label className="block mb-1 text-muted-foreground">MAX_PE</label>
              <Input
                type="number"
                placeholder="50"
                className="h-8 text-xs"
                value={filters.max_pe || ''}
                onChange={(e) => handleInputChange('max_pe', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
          </div>
        </div>

        {/* Market Cap */}
        <div className="space-y-2">
          <div className="text-muted-foreground mb-2">──[ MARKET_CAP ]──</div>
          <div>
            <label className="block mb-1 text-muted-foreground">MIN_CAP ($)</label>
            <Input
              type="number"
              placeholder="1000000000"
              className="h-8 text-xs"
              value={filters.min_market_cap || ''}
              onChange={(e) => handleInputChange('min_market_cap', e.target.value ? parseInt(e.target.value) : undefined)}
            />
            <p className="text-[10px] text-muted-foreground mt-1">1B = 1000000000</p>
          </div>
          <div>
            <label className="block mb-1 text-muted-foreground">MAX_CAP ($)</label>
            <Input
              type="number"
              placeholder="∞"
              className="h-8 text-xs"
              value={filters.max_market_cap || ''}
              onChange={(e) => handleInputChange('max_market_cap', e.target.value ? parseInt(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Price Range */}
        <div className="space-y-2">
          <div className="text-muted-foreground mb-2">──[ PRICE_RANGE ]──</div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block mb-1 text-muted-foreground">MIN ($)</label>
              <Input
                type="number"
                placeholder="0"
                className="h-8 text-xs"
                value={filters.min_price || ''}
                onChange={(e) => handleInputChange('min_price', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
            <div>
              <label className="block mb-1 text-muted-foreground">MAX ($)</label>
              <Input
                type="number"
                placeholder="∞"
                className="h-8 text-xs"
                value={filters.max_price || ''}
                onChange={(e) => handleInputChange('max_price', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
          </div>
        </div>

        {/* Dividends */}
        <div className="space-y-2">
          <div className="text-muted-foreground mb-2">──[ DIVIDENDS ]──</div>
          <div>
            <label className="block mb-1 text-muted-foreground">MIN_YIELD (%)</label>
            <Input
              type="number"
              placeholder="0.0"
              step="0.1"
              className="h-8 text-xs"
              value={filters.min_dividend_yield || ''}
              onChange={(e) => handleInputChange('min_dividend_yield', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Financial Health */}
        <div className="space-y-2">
          <div className="text-muted-foreground mb-2">──[ FIN_HEALTH ]──</div>
          <div>
            <label className="block mb-1 text-muted-foreground">MAX_DEBT_EQUITY</label>
            <Input
              type="number"
              placeholder="2.0"
              step="0.1"
              className="h-8 text-xs"
              value={filters.max_debt_to_equity || ''}
              onChange={(e) => handleInputChange('max_debt_to_equity', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Display Options */}
        <div className="space-y-2">
          <div className="text-muted-foreground mb-2">──[ DISPLAY ]──</div>
          <div>
            <label className="block mb-1 text-muted-foreground">
              LIMIT: {filters.limit}
            </label>
            <Slider
              value={[filters.limit || 50]}
              onValueChange={(value) => handleInputChange('limit', value[0])}
              min={10}
              max={100}
              step={10}
              className="mt-2"
            />
            <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
              <span>10</span>
              <span>100</span>
            </div>
          </div>
        </div>

        {/* Execute Button */}
        <button
          onClick={handleApplyFilters}
          className="w-full border border-primary bg-primary/10 hover:bg-primary/20 text-primary py-2 transition-colors flex items-center justify-center gap-2 font-bold"
        >
          <Play className="h-3 w-3" />
          EXECUTE_QUERY
        </button>
      </div>
    </div>
  );
}
