'use client';

import { useEffect, useRef } from 'react';

import { formatCurrency, formatDate } from '@/lib/utils';

export type EquityPoint = {
  date: string;
  strategy: number;
  benchmark: number | null;
};

export function EquityCurveChart({
  points,
  showBenchmark,
  runVersion,
}: {
  points: EquityPoint[];
  showBenchmark: boolean;
  runVersion: number;
}) {
  const strategyPathRef = useRef<SVGPathElement | null>(null);
  const width = 920;
  const height = 340;
  const paddingX = 28;
  const paddingY = 22;
  const baselineValue = points[0]?.strategy ?? 0;
  const benchmarkValues = showBenchmark ? points.map((point) => point.benchmark).filter((value): value is number => value != null) : [];
  const values = [...points.map((point) => point.strategy), ...benchmarkValues];
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = Math.max(maxValue - minValue, Math.max(Math.abs(maxValue), 1) * 0.08, 1);
  const chartMin = minValue - range * 0.08;
  const chartMax = maxValue + range * 0.08;
  const plotWidth = width - paddingX * 2;
  const plotHeight = height - paddingY * 2;
  const baselineY = paddingY + (1 - (baselineValue - chartMin) / Math.max(chartMax - chartMin, 1)) * plotHeight;
  const positiveClipId = `strategy-pos-${runVersion}`;
  const negativeClipId = `strategy-neg-${runVersion}`;

  const toX = (index: number) => paddingX + (plotWidth * index) / Math.max(points.length - 1, 1);
  const toY = (value: number) => paddingY + (1 - (value - chartMin) / Math.max(chartMax - chartMin, 1)) * plotHeight;

  const strategyLine = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${toX(index)} ${toY(point.strategy)}`).join(' ');
  const benchmarkLine = points
    .filter((point) => point.benchmark != null)
    .map((point, index) => {
      const actualIndex = points.findIndex((candidate) => candidate.date === point.date);
      return `${index === 0 ? 'M' : 'L'} ${toX(actualIndex)} ${toY(point.benchmark ?? 0)}`;
    })
    .join(' ');
  const areaPath = [`M ${toX(0)} ${baselineY}`, ...points.map((point, index) => `L ${toX(index)} ${toY(point.strategy)}`), `L ${toX(points.length - 1)} ${baselineY}`, 'Z'].join(' ');

  useEffect(() => {
    const node = strategyPathRef.current;
    if (!node) return;
    const length = node.getTotalLength();
    node.style.transition = 'none';
    node.style.strokeDasharray = `${length}`;
    node.style.strokeDashoffset = `${length}`;
    const frame = requestAnimationFrame(() => {
      node.style.transition = 'stroke-dashoffset 1200ms ease-out';
      node.style.strokeDashoffset = '0';
    });
    return () => cancelAnimationFrame(frame);
  }, [runVersion, strategyLine]);

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] p-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[360px] w-full">
        <defs>
          <clipPath id={positiveClipId}>
            <rect x="0" y="0" width={width} height={baselineY} />
          </clipPath>
          <clipPath id={negativeClipId}>
            <rect x="0" y={baselineY} width={width} height={height - baselineY} />
          </clipPath>
        </defs>

        {[0.25, 0.5, 0.75].map((ratio) => {
          const y = paddingY + plotHeight * ratio;
          return <line key={ratio} x1={paddingX} x2={width - paddingX} y1={y} y2={y} stroke="rgba(61, 61, 96, 0.32)" strokeDasharray="4 8" />;
        })}

        <line x1={paddingX} x2={width - paddingX} y1={baselineY} y2={baselineY} stroke="rgba(152, 152, 176, 0.3)" />
        <path d={areaPath} fill="rgba(74, 222, 128, 0.08)" clipPath={`url(#${positiveClipId})`} />
        <path d={areaPath} fill="rgba(248, 113, 113, 0.08)" clipPath={`url(#${negativeClipId})`} />
        <path ref={strategyPathRef} d={strategyLine} fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {showBenchmark && benchmarkLine ? (
          <path d={benchmarkLine} fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeDasharray="7 7" strokeLinecap="round" strokeLinejoin="round" />
        ) : null}
      </svg>

      <div className="mt-3 flex items-center justify-between gap-3 text-xs text-[var(--text-tertiary)]">
        <span>{formatDate(points[0]?.date)}</span>
        <span className="tabular-nums">Start {formatCurrency(baselineValue)}</span>
        <span>{formatDate(points[points.length - 1]?.date)}</span>
      </div>
    </div>
  );
}
