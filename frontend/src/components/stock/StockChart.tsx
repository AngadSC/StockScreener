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
    <Card>
      <CardHeader>
        <CardTitle>{ticker} Price History</CardTitle>
        <CardDescription>
          {data.length > 0 && (
            <span>
              {formatDate(data[0].date)} - {formatDate(data[data.length - 1].date)}
              {priceChange && (
                <span className={priceChange.change >= 0 ? 'text-green-600 ml-4' : 'text-red-600 ml-4'}>
                  {priceChange.change >= 0 ? '+' : ''}
                  {formatCurrency(priceChange.change)} ({priceChange.changePercent.toFixed(2)}%)
                </span>
              )}
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 12 }}
              interval="preserveStartEnd"
            />
            <YAxis 
              domain={['auto', 'auto']}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `$${value.toFixed(2)}`}
            />
            <Tooltip 
              formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
              labelStyle={{ color: '#000' }}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="price" 
              stroke="#2563eb" 
              strokeWidth={2}
              dot={false}
              name="Close Price"
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
