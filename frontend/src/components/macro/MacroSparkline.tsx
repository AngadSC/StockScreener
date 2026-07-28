'use client';

import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { formatDate } from '@/lib/utils';
import type { MacroSparklinePoint } from '@/types/macro';

interface MacroSparklineProps {
  data: MacroSparklinePoint[];
  color?: string;
  height?: number;
  valueFormatter?: (value: number) => string;
  showZeroLine?: boolean;
}

/**
 * Recharts defaults a numeric axis to a zero-anchored domain, which squashes
 * tight macro series (DGS10 moving 4.15 -> 4.55) into a flat line inside a
 * 56px box. Fit the domain to the data instead — but keep zero inside the
 * window whenever the zero baseline is drawn, otherwise a fully inverted
 * yield curve (all values negative) would push the reference line offscreen
 * exactly when it matters most.
 */
function getValueDomain(values: number[], includeZero: boolean): [number, number] {
  if (values.length === 0) return [0, 1];

  let min = Math.min(...values);
  let max = Math.max(...values);

  if (includeZero) {
    min = Math.min(0, min);
    max = Math.max(0, max);
  }

  const span = max - min;
  const pad = span > 0 ? span * 0.12 : Math.max(Math.abs(max) * 0.05, 0.01);

  return [min - pad, max + pad];
}

export default function MacroSparkline({
  data,
  color = 'var(--sapphire)',
  height = 56,
  valueFormatter,
  showZeroLine = false,
}: MacroSparklineProps) {
  const chartData = data
    .filter((point) => point.value !== null && point.value !== undefined && Number.isFinite(point.value))
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

  const domain = getValueDomain(
    chartData.map((point) => point.value),
    showZeroLine
  );

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 4, right: 2, bottom: 0, left: 2 }}>
          {/* Hidden axes: the x axis binds the tooltip label to the real date
              (without it recharts labels points by array index), and the y axis
              carries the fitted domain. */}
          <XAxis dataKey="date" hide />
          <YAxis hide domain={domain} />
          {showZeroLine ? (
            <ReferenceLine y={0} stroke="var(--line-2)" strokeDasharray="2 2" ifOverflow="extendDomain" />
          ) : null}
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
