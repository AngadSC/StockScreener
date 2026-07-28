'use client';

import { useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { StockPrice } from '@/types/stock';
import { formatCurrency, formatDate, parseLocalDate } from '@/lib/utils';

interface StockChartProps {
  data: StockPrice[];
  ticker: string;
}

export default function StockChart({ data, ticker }: StockChartProps) {
  const chartData = useMemo(() => {
    return data.map((item) => ({
      // parseLocalDate: bare YYYY-MM-DD parsed as UTC would label every bar a day early for US viewers.
      date: parseLocalDate(item.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
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
      <div className="border-b border-border px-4 py-3 bg-muted/20">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Price History {ticker}</span>
          {data.length > 0 && (
            <div className="text-xs text-muted-foreground">
              {formatDate(data[0].date)} to {formatDate(data[data.length - 1].date)}
              {priceChange && (
                <span
                  className={`ml-3 tabular-nums ${
                    priceChange.change >= 0 ? 'text-positive' : 'text-negative'
                  }`}
                >
                  {priceChange.change >= 0 ? '+' : ''}
                  {formatCurrency(priceChange.change)} ({priceChange.changePercent.toFixed(2)}%)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="p-4">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(61, 61, 96, 0.28)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: '#9898B0' }}
              interval="preserveStartEnd"
              stroke="#2A2A42"
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fontSize: 11, fill: '#9898B0' }}
              tickFormatter={(value) => `$${value.toFixed(0)}`}
              stroke="#2A2A42"
            />
            <Tooltip
              formatter={(value: number | undefined) => {
                if (value === undefined) return ['N/A', 'Price'];
                return [`$${value.toFixed(2)}`, 'Close'];
              }}
              contentStyle={{
                backgroundColor: '#0F0F1A',
                border: '1px solid #2A2A42',
                borderRadius: '8px',
                fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
                fontSize: '12px',
              }}
              labelStyle={{ color: '#9898B0' }}
            />
            <Legend />
            <Line type="monotone" dataKey="price" stroke="#5B5BD6" strokeWidth={2} dot={false} name="Close Price" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="border-t border-border px-4 py-3 bg-muted/20 text-xs text-muted-foreground">
        Data points: {data.length} | Interval: Daily
      </div>
    </div>
  );
}
