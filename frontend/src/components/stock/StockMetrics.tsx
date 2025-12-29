'use client';

import { Stock } from '@/types/stock';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatMarketCap, formatNumber, formatPercent } from '@/lib/utils';

interface StockMetricsProps {
  stock: Stock;
}

export default function StockMetrics({ stock }: StockMetricsProps) {
  const metrics = [
    {
      category: 'Valuation',
      items: [
        { label: 'P/E Ratio', value: stock.pe_ratio ? formatNumber(stock.pe_ratio) : 'N/A' },
        { label: 'Forward P/E', value: stock.forward_pe ? formatNumber(stock.forward_pe) : 'N/A' },
        { label: 'PEG Ratio', value: stock.peg_ratio ? formatNumber(stock.peg_ratio) : 'N/A' },
        { label: 'P/B Ratio', value: stock.pb_ratio ? formatNumber(stock.pb_ratio) : 'N/A' },
        { label: 'P/S Ratio', value: stock.ps_ratio ? formatNumber(stock.ps_ratio) : 'N/A' },
        { label: 'EV/EBITDA', value: stock.ev_to_ebitda ? formatNumber(stock.ev_to_ebitda) : 'N/A' },
      ],
    },
    {
      category: 'Profitability',
      items: [
        { label: 'EPS', value: stock.eps ? formatCurrency(stock.eps) : 'N/A' },
        { label: 'Profit Margin', value: stock.profit_margin ? formatPercent(stock.profit_margin * 100) : 'N/A' },
        { label: 'Operating Margin', value: stock.operating_margin ? formatPercent(stock.operating_margin * 100) : 'N/A' },
        { label: 'ROE', value: stock.roe ? formatPercent(stock.roe * 100) : 'N/A' },
        { label: 'ROA', value: stock.roa ? formatPercent(stock.roa * 100) : 'N/A' },
      ],
    },
    {
      category: 'Growth',
      items: [
        { label: 'Revenue Growth', value: stock.revenue_growth ? formatPercent(stock.revenue_growth * 100) : 'N/A' },
        { label: 'Earnings Growth', value: stock.earnings_growth ? formatPercent(stock.earnings_growth * 100) : 'N/A' },
      ],
    },
    {
      category: 'Financial Health',
      items: [
        { label: 'Debt/Equity', value: stock.debt_to_equity ? formatNumber(stock.debt_to_equity) : 'N/A' },
        { label: 'Current Ratio', value: stock.current_ratio ? formatNumber(stock.current_ratio) : 'N/A' },
        { label: 'Quick Ratio', value: stock.quick_ratio ? formatNumber(stock.quick_ratio) : 'N/A' },
      ],
    },
    {
      category: 'Dividends',
      items: [
        { label: 'Dividend Yield', value: stock.dividend_yield ? formatPercent(stock.dividend_yield * 100) : 'N/A' },
        { label: 'Dividend Rate', value: stock.dividend_rate ? formatCurrency(stock.dividend_rate) : 'N/A' },
        { label: 'Payout Ratio', value: stock.payout_ratio ? formatPercent(stock.payout_ratio * 100) : 'N/A' },
      ],
    },
    {
      category: 'Trading',
      items: [
        { label: 'Beta', value: stock.beta ? formatNumber(stock.beta) : 'N/A' },
        { label: 'Volume', value: stock.volume ? stock.volume.toLocaleString() : 'N/A' },
        { label: 'Avg Volume', value: stock.avg_volume ? stock.avg_volume.toLocaleString() : 'N/A' },
        { label: '52W High', value: formatCurrency(stock.fifty_two_week_high) },
        { label: '52W Low', value: formatCurrency(stock.fifty_two_week_low) },
      ],
    },
  ];

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {metrics.map((section) => (
        <Card key={section.category}>
          <CardHeader>
            <CardTitle className="text-lg">{section.category}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-2">
              {section.items.map((item) => (
                <div key={item.label} className="flex justify-between text-sm">
                  <dt className="text-muted-foreground">{item.label}</dt>
                  <dd className="font-medium">{item.value}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
