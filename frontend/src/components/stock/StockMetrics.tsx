'use client';

import { Stock } from '@/types/stock';
import { formatCurrency, formatNumber } from '@/lib/utils';

interface StockMetricsProps {
  stock: Stock;
}

const hasNumber = (value: number | null | undefined): value is number => {
  return value !== null && value !== undefined && !Number.isNaN(value);
};

const formatPercent = (value: number | null | undefined): string => {
  if (!hasNumber(value)) return 'N/A';
  return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`;
};

const numberItem = (label: string, value: number | null | undefined) => ({
  label,
  value: hasNumber(value) ? formatNumber(value) : 'N/A',
  hasValue: hasNumber(value),
});

const currencyItem = (label: string, value: number | null | undefined) => ({
  label,
  value: hasNumber(value) ? formatCurrency(value) : 'N/A',
  hasValue: hasNumber(value),
});

const percentItem = (label: string, value: number | null | undefined) => ({
  label,
  value: formatPercent(value),
  hasValue: hasNumber(value),
});

const integerItem = (label: string, value: number | null | undefined) => ({
  label,
  value: hasNumber(value) ? Math.trunc(value).toLocaleString() : 'N/A',
  hasValue: hasNumber(value),
});

export default function StockMetrics({ stock }: StockMetricsProps) {
  const metrics = [
    {
      category: 'Valuation',
      items: [
        numberItem('P/E Ratio', stock.pe_ratio),
        numberItem('Forward P/E', stock.forward_pe),
        numberItem('PEG Ratio', stock.peg_ratio),
        numberItem('P/B Ratio', stock.pb_ratio),
        numberItem('P/S Ratio', stock.ps_ratio),
        numberItem('EV/EBITDA', stock.ev_to_ebitda),
      ],
    },
    {
      category: 'Profitability',
      items: [
        currencyItem('EPS', stock.eps),
        percentItem('Profit Margin', stock.profit_margin),
        percentItem('Operating Margin', stock.operating_margin),
        percentItem('ROE', stock.roe),
        percentItem('ROA', stock.roa),
      ],
    },
    {
      category: 'Growth',
      items: [
        percentItem('Revenue Growth', stock.revenue_growth),
        percentItem('Earnings Growth', stock.earnings_growth),
      ],
    },
    {
      category: 'Financial Health',
      items: [
        numberItem('Debt/Equity', stock.debt_to_equity),
        numberItem('Current Ratio', stock.current_ratio),
        numberItem('Quick Ratio', stock.quick_ratio),
      ],
    },
    {
      category: 'Dividends',
      items: [
        percentItem('Dividend Yield', stock.dividend_yield),
        currencyItem('Dividend Rate', stock.dividend_rate),
        percentItem('Payout Ratio', stock.payout_ratio),
      ],
    },
    {
      category: 'Trading',
      items: [
        numberItem('Beta', stock.beta),
        integerItem('Volume', stock.volume),
        integerItem('Avg Volume', stock.avg_volume),
        currencyItem('52W High', stock.fifty_two_week_high),
        currencyItem('52W Low', stock.fifty_two_week_low),
      ],
    },
  ];

  const visibleMetrics = metrics
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => item.hasValue),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {visibleMetrics.map((section) => (
        <div key={section.category} className="deco-panel bg-card">
          <div className="border-b border-border/70 bg-muted/20 px-4 py-3">
            <span className="text-sm font-semibold">{section.category}</span>
          </div>

          <div className="space-y-2 p-4 text-sm">
            {section.items.map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between gap-4 border-b border-border/70 py-2 last:border-0"
              >
                <span className="text-muted-foreground">{item.label}</span>
                <span className="tabular-nums font-semibold text-primary">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
