'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { ScreenerFilters } from '@/types/stock';
import { Filter, X } from 'lucide-react';

interface FilterPanelProps {
  onFilterChange: (filters: ScreenerFilters) => void;
  onReset: () => void;
}

export default function FilterPanel({ onFilterChange, onReset }: FilterPanelProps) {
  const [filters, setFilters] = useState<ScreenerFilters>({
    limit: 50,
    sort_by: 'market_cap',
    sort_order: 'desc',
  });

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
    };
    setFilters(resetFilters);
    onReset();
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filters
            </CardTitle>
            <CardDescription>
              Filter stocks by fundamentals
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={handleReset}>
            <X className="h-4 w-4 mr-2" />
            Reset
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Valuation Filters */}
        <div className="space-y-4">
          <h3 className="font-semibold text-sm">Valuation</h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min_pe">Min P/E Ratio</Label>
              <Input
                id="min_pe"
                type="number"
                placeholder="0"
                value={filters.min_pe || ''}
                onChange={(e) => handleInputChange('min_pe', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="max_pe">Max P/E Ratio</Label>
              <Input
                id="max_pe"
                type="number"
                placeholder="50"
                value={filters.max_pe || ''}
                onChange={(e) => handleInputChange('max_pe', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
          </div>
        </div>

        {/* Market Cap */}
        <div className="space-y-4">
          <h3 className="font-semibold text-sm">Market Cap</h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min_market_cap">Min ($)</Label>
              <Input
                id="min_market_cap"
                type="number"
                placeholder="1000000000"
                value={filters.min_market_cap || ''}
                onChange={(e) => handleInputChange('min_market_cap', e.target.value ? parseInt(e.target.value) : undefined)}
              />
              <p className="text-xs text-muted-foreground">e.g., 1B = 1000000000</p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="max_market_cap">Max ($)</Label>
              <Input
                id="max_market_cap"
                type="number"
                placeholder="100000000000"
                value={filters.max_market_cap || ''}
                onChange={(e) => handleInputChange('max_market_cap', e.target.value ? parseInt(e.target.value) : undefined)}
              />
            </div>
          </div>
        </div>

        {/* Price Range */}
        <div className="space-y-4">
          <h3 className="font-semibold text-sm">Price Range</h3>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min_price">Min Price ($)</Label>
              <Input
                id="min_price"
                type="number"
                placeholder="0"
                value={filters.min_price || ''}
                onChange={(e) => handleInputChange('min_price', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="max_price">Max Price ($)</Label>
              <Input
                id="max_price"
                type="number"
                placeholder="1000"
                value={filters.max_price || ''}
                onChange={(e) => handleInputChange('max_price', e.target.value ? parseFloat(e.target.value) : undefined)}
              />
            </div>
          </div>
        </div>

        {/* Dividends */}
        <div className="space-y-4">
          <h3 className="font-semibold text-sm">Dividends</h3>
          
          <div className="space-y-2">
            <Label htmlFor="min_dividend_yield">Min Dividend Yield (%)</Label>
            <Input
              id="min_dividend_yield"
              type="number"
              placeholder="2.0"
              step="0.1"
              value={filters.min_dividend_yield || ''}
              onChange={(e) => handleInputChange('min_dividend_yield', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Financial Health */}
        <div className="space-y-4">
          <h3 className="font-semibold text-sm">Financial Health</h3>
          
          <div className="space-y-2">
            <Label htmlFor="max_debt_to_equity">Max Debt/Equity Ratio</Label>
            <Input
              id="max_debt_to_equity"
              type="number"
              placeholder="2.0"
              step="0.1"
              value={filters.max_debt_to_equity || ''}
              onChange={(e) => handleInputChange('max_debt_to_equity', e.target.value ? parseFloat(e.target.value) : undefined)}
            />
          </div>
        </div>

        {/* Results per page */}
        <div className="space-y-4">
          <h3 className="font-semibold text-sm">Display</h3>
          
          <div className="space-y-2">
            <Label>Results per page: {filters.limit}</Label>
            <Slider
              value={[filters.limit || 50]}
              onValueChange={(value) => handleInputChange('limit', value[0])}
              min={10}
              max={100}
              step={10}
            />
          </div>
        </div>

        {/* Apply Button */}
        <Button className="w-full" onClick={handleApplyFilters}>
          <Filter className="h-4 w-4 mr-2" />
          Apply Filters
        </Button>
      </CardContent>
    </Card>
  );
}
