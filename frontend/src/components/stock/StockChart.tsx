'use client';

import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { StockPrice } from '@/types/stock';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatDate } from '@/lib/utils';

interface StockChartProps {
  data: StockPrice[];
  ticker: string;
}

export default function StockChart({ data, ticker }: StockChartProps) {
  const chartData = useMemo(() => {
    return data.map((item) => ({
      date: new Date(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      price: item.close,
      volume: item.volume,
    }));
  }, [data]);

  const priceChange = useMemo(() => {
    if (data.length < 2) return null;
    const first = data[0].close;
    const last = data[data.length - 1].close;
    const change = last - first;
    const changePercent = (change / first) * 100;
    return { change, changePercent };
  }, [data]);

  return (
    <div className="terminal-border bg-card">
      {/* Header */}
      <div className="border-b border-border px-4 py-2 bg-muted/20">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold">PRICE_HISTORY [{ticker}]</span>
          {data.length > 0 && (
            <div className="text-xs text-muted-foreground">
              {formatDate(data[0].date)} → {formatDate(data[data.length - 1].date)}
              {priceChange && (
                <span className={`ml-3 font-mono ${priceChange.change >= 0 ? 'text-primary' : 'text-destructive'}`}>
                  {priceChange.change >= 0 ? '▲' : '▼'}
                  {priceChange.change >= 0 ? '+' : ''}
                  {formatCurrency(priceChange.change)} ({priceChange.changePercent.toFixed(2)}%)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="p-4">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              interval="preserveStartEnd"
              stroke="hsl(var(--border))"
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickFormatter={(value) => `$${value.toFixed(0)}`}
              stroke="hsl(var(--border))"
            />
            <Tooltip
              formatter={(value: number | undefined) => {
                if (value === undefined) return ['N/A', 'PRICE'];
                return [`$${value.toFixed(2)}`, 'CLOSE'];
              }}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0',
                fontFamily: 'monospace',
                fontSize: '11px',
              }}
              labelStyle={{ color: 'hsl(var(--muted-foreground))' }}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
              name="CLOSE_PRICE"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Footer */}
      <div className="border-t border-border px-4 py-2 bg-muted/20 text-xs text-muted-foreground">
        DATA_POINTS: {data.length} | INTERVAL: DAILY
      </div>
    </div>
  );
}
