'use client';

import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip } from 'recharts';

import { formatDate } from '@/lib/utils';
import type { MacroSparklinePoint } from '@/types/macro';

interface MacroSparklineProps {
  data: MacroSparklinePoint[];
  color?: string;
  height?: number;
  valueFormatter?: (value: number) => string;
  showZeroLine?: boolean;
}

export default function MacroSparkline({
  data,
  color = 'var(--sapphire)',
  height = 56,
  valueFormatter,
  showZeroLine = false,
}: MacroSparklineProps) {
  const chartData = data
    .filter((point) => point.value !== null && point.value !== undefined)
    .map((point) => ({ date: point.date, value: point.value as number }));

  if (chartData.length < 2) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center text-[11px] text-muted-foreground"
      >
        Not enough data yet
      </div>
    );
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 4, right: 2, bottom: 0, left: 2 }}>
          {showZeroLine ? <ReferenceLine y={0} stroke="var(--line-2)" strokeDasharray="2 2" /> : null}
          <Tooltip
            cursor={{ stroke: 'var(--line-2)', strokeWidth: 1 }}
            contentStyle={{
              background: 'var(--surface)',
              border: '1px solid var(--line)',
              borderRadius: 8,
              fontSize: 11,
              padding: '6px 8px',
            }}
            labelFormatter={(label) => formatDate(String(label))}
            formatter={(value: number | undefined) => {
              const numeric = value ?? 0;
              return [valueFormatter ? valueFormatter(numeric) : numeric.toFixed(2), ''];
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
