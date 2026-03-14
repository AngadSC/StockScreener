'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, Loader2, Search } from 'lucide-react';

import HelpPopover from '@/components/ui/help-popover';
import { Input } from '@/components/ui/input';
import { screenerAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { ScreenerFilters } from '@/types/stock';

interface FilterPanelProps {
  filters: ScreenerFilters;
  isFetching?: boolean;
  onChange: (filters: ScreenerFilters) => void;
  onReset: () => void;
}

type SectionKey = 'valuation' | 'quality' | 'sectorIndustry' | 'sorting';

const DEFAULT_OPEN_SECTIONS: Record<SectionKey, boolean> = {
  valuation: true,
  quality: false,
  sectorIndustry: false,
  sorting: false,
};

const LIMIT_OPTIONS = [25, 50, 100, 250];

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

function AccordionSection({
  title,
  isOpen,
  onToggle,
  children,
}: {
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState(0);

  useEffect(() => {
    if (!contentRef.current) return;
    setContentHeight(contentRef.current.scrollHeight);
  }, [children, isOpen]);

  return (
    <section className="border-b border-[var(--border-subtle)] last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 py-4 text-left"
      >
        <span className="heading-sm text-[var(--text-primary)]">{title}</span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-[var(--text-tertiary)] transition-transform duration-[250ms] ease-[cubic-bezier(0.16,1,0.3,1)]',
            isOpen && 'rotate-180 text-[var(--accent)]'
          )}
        />
      </button>

      <div
        className="overflow-hidden transition-[max-height] duration-[250ms] ease-[cubic-bezier(0.16,1,0.3,1)]"
        style={{ maxHeight: isOpen ? `${contentHeight}px` : '0px' }}
      >
        <div ref={contentRef} className="pb-5">
          {children}
        </div>
      </div>
    </section>
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
        <span className="text-xs font-medium text-[var(--text-secondary)]">{label}</span>
        {help ? <HelpPopover title={label} description={help} suggestion={suggestion} /> : null}
      </div>
      {children}
    </label>
  );
}

export default function FilterPanel({ filters, isFetching, onChange, onReset }: FilterPanelProps) {
  const [openSections, setOpenSections] = useState(DEFAULT_OPEN_SECTIONS);

  const { data: sectors } = useQuery({
    queryKey: ['screener-sectors'],
    queryFn: () => screenerAPI.getSectors(),
  });

  const { data: industries } = useQuery({
    queryKey: ['screener-industries'],
    queryFn: () => screenerAPI.getIndustries(),
  });

  const updateFilters = (patch: Partial<ScreenerFilters>, resetPagination: boolean = true) => {
    onChange({
      ...filters,
      ...patch,
      skip: resetPagination ? 0 : patch.skip ?? filters.skip ?? 0,
    });
  };

  const toggleSection = (section: SectionKey) => {
    setOpenSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const handleMultiSelectChange = (field: 'sectors' | 'industries', values: string[]) => {
    updateFilters({
      [field]: values.length > 0 ? values : undefined,
    });
  };

  return (
    <>
      <div className="deco-scroll flex-1 overflow-y-auto p-[var(--space-5)]">
        <div className="space-y-5">
          <div>
            <div className="deco-kicker">Filters</div>
            <h2 className="mt-2 text-[24px] font-semibold leading-[1.2] text-[var(--text-primary)]">
              Screen setup
            </h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Results update automatically as you adjust the inputs.
            </p>
          </div>

          <div className="space-y-4">
            <Field
              label="Ticker or Company"
              help="Use a ticker or company fragment to narrow the universe before applying metric filters."
              suggestion="AAPL, Microsoft, regional bank"
            >
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
                <Input
                  type="text"
                  value={filters.search ?? ''}
                  onChange={(event) =>
                    updateFilters({
                      search: event.target.value.trim() ? event.target.value : undefined,
                    })
                  }
                  placeholder="Search ticker or company"
                  className="pl-9"
                />
              </div>
            </Field>

            <Field
              label="Result Limit"
              help="Choose how many rows are returned per page."
              suggestion="50 for regular scanning, 100 for broader passes"
            >
              <select
                value={filters.limit ?? 50}
                onChange={(event) => updateFilters({ limit: parseInt(event.target.value, 10) })}
              >
                {LIMIT_OPTIONS.map((limit) => (
                  <option key={limit} value={limit}>
                    {limit}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface-2)] px-4 py-2">
            <AccordionSection
              title="Valuation & Price"
              isOpen={openSections.valuation}
              onToggle={() => toggleSection('valuation')}
            >
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Min P/E">
                  <Input
                    type="number"
                    value={filters.min_pe ?? ''}
                    onChange={(event) => updateFilters({ min_pe: parseFloatInput(event.target.value) })}
                  />
                </Field>
                <Field label="Max P/E">
                  <Input
                    type="number"
                    value={filters.max_pe ?? ''}
                    onChange={(event) => updateFilters({ max_pe: parseFloatInput(event.target.value) })}
                  />
                </Field>
                <Field label="Min Price">
                  <Input
                    type="number"
                    value={filters.min_price ?? ''}
                    onChange={(event) => updateFilters({ min_price: parseFloatInput(event.target.value) })}
                  />
                </Field>
                <Field label="Max Price">
                  <Input
                    type="number"
                    value={filters.max_price ?? ''}
                    onChange={(event) => updateFilters({ max_price: parseFloatInput(event.target.value) })}
                  />
                </Field>
                <Field label="Min Market Cap">
                  <Input
                    type="text"
                    inputMode="numeric"
                    value={formatIntegerForInput(filters.min_market_cap)}
                    onChange={(event) =>
                      updateFilters({ min_market_cap: parseIntegerInput(event.target.value) })
                    }
                  />
                </Field>
                <Field label="Max Market Cap">
                  <Input
                    type="text"
                    inputMode="numeric"
                    value={formatIntegerForInput(filters.max_market_cap)}
                    onChange={(event) =>
                      updateFilters({ max_market_cap: parseIntegerInput(event.target.value) })
                    }
                  />
                </Field>
                <Field label="Min Volume">
                  <Input
                    type="text"
                    inputMode="numeric"
                    value={formatIntegerForInput(filters.min_volume)}
                    onChange={(event) =>
                      updateFilters({ min_volume: parseIntegerInput(event.target.value) })
                    }
                  />
                </Field>
                <Field label="Min Avg Volume">
                  <Input
                    type="text"
                    inputMode="numeric"
                    value={formatIntegerForInput(filters.min_avg_volume)}
                    onChange={(event) =>
                      updateFilters({ min_avg_volume: parseIntegerInput(event.target.value) })
                    }
                  />
                </Field>
              </div>
            </AccordionSection>

            <AccordionSection
              title="Quality & Risk"
              isOpen={openSections.quality}
              onToggle={() => toggleSection('quality')}
            >
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Min ROE (%)">
                  <Input
                    type="number"
                    step="0.1"
                    value={toPercentInputValue(filters.min_roe)}
                    onChange={(event) => updateFilters({ min_roe: fromPercentInput(event.target.value) })}
                  />
                </Field>
                <Field label="Min Revenue Growth (%)">
                  <Input
                    type="number"
                    step="0.1"
                    value={toPercentInputValue(filters.min_revenue_growth)}
                    onChange={(event) =>
                      updateFilters({ min_revenue_growth: fromPercentInput(event.target.value) })
                    }
                  />
                </Field>
                <Field label="Min Dividend Yield (%)">
                  <Input
                    type="number"
                    step="0.1"
                    value={toPercentInputValue(filters.min_dividend_yield)}
                    onChange={(event) =>
                      updateFilters({ min_dividend_yield: fromPercentInput(event.target.value) })
                    }
                  />
                </Field>
                <Field label="Max Debt to Equity">
                  <Input
                    type="number"
                    step="0.1"
                    value={filters.max_debt_to_equity ?? ''}
                    onChange={(event) =>
                      updateFilters({ max_debt_to_equity: parseFloatInput(event.target.value) })
                    }
                  />
                </Field>
                <Field label="Max Beta">
                  <Input
                    type="number"
                    step="0.1"
                    value={filters.max_beta ?? ''}
                    onChange={(event) => updateFilters({ max_beta: parseFloatInput(event.target.value) })}
                  />
                </Field>
              </div>
            </AccordionSection>

            <AccordionSection
              title="Sector & Industry"
              isOpen={openSections.sectorIndustry}
              onToggle={() => toggleSection('sectorIndustry')}
            >
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field
                  label="Sector"
                  help="Use Ctrl or Command to select more than one sector."
                  suggestion="Technology, Healthcare"
                >
                  <select
                    multiple
                    value={filters.sectors ?? []}
                    onChange={(event) =>
                      handleMultiSelectChange(
                        'sectors',
                        Array.from(event.target.selectedOptions, (option) => option.value)
                      )
                    }
                    className="min-h-[180px]"
                  >
                    {(sectors?.sectors ?? []).map((sector) => (
                      <option key={sector} value={sector}>
                        {sector}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field
                  label="Industry"
                  help="Use Ctrl or Command to select more than one industry."
                  suggestion="Semiconductors, Software"
                >
                  <select
                    multiple
                    value={filters.industries ?? []}
                    onChange={(event) =>
                      handleMultiSelectChange(
                        'industries',
                        Array.from(event.target.selectedOptions, (option) => option.value)
                      )
                    }
                    className="min-h-[180px]"
                  >
                    {(industries?.industries ?? []).map((industry) => (
                      <option key={industry} value={industry}>
                        {industry}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
            </AccordionSection>

            <AccordionSection
              title="Sorting"
              isOpen={openSections.sorting}
              onToggle={() => toggleSection('sorting')}
            >
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Sort By">
                  <select
                    value={filters.sort_by ?? 'market_cap'}
                    onChange={(event) => updateFilters({ sort_by: event.target.value })}
                  >
                    <option value="market_cap">Market Cap</option>
                    <option value="current_price">Price</option>
                    <option value="day_change_percent">Chg%</option>
                    <option value="volume">Volume</option>
                    <option value="avg_volume">Avg Volume</option>
                    <option value="pe_ratio">P/E</option>
                    <option value="roe">ROE</option>
                    <option value="revenue_growth">Revenue Growth</option>
                    <option value="dividend_yield">Dividend Yield</option>
                    <option value="beta">Beta</option>
                  </select>
                </Field>
                <Field label="Order">
                  <select
                    value={filters.sort_order ?? 'desc'}
                    onChange={(event) =>
                      updateFilters({ sort_order: event.target.value as 'asc' | 'desc' })
                    }
                  >
                    <option value="desc">Descending</option>
                    <option value="asc">Ascending</option>
                  </select>
                </Field>
              </div>
            </AccordionSection>
          </div>
        </div>
      </div>

      <div className="sticky bottom-0 border-t border-[var(--border-subtle)] bg-[linear-gradient(180deg,rgba(15,15,26,0.94)_0%,rgba(15,15,26,1)_30%)] px-[var(--space-5)] py-4 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
            {isFetching ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--accent)]" />
                Updating results
              </>
            ) : (
              'Auto-run enabled'
            )}
          </div>

          <button
            type="button"
            onClick={onReset}
            className="text-sm text-[var(--text-tertiary)] transition-colors hover:text-[var(--negative)]"
          >
            Reset all filters
          </button>
        </div>
      </div>
    </>
  );
}
