'use client';

import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';

import { formatCurrency, formatPercent } from '@/lib/utils';

export type EquityPoint = {
  date: string;
  strategy: number;
  benchmark: number | null;
};

const STRATEGY_STROKE = '#8b5cf6';
const STRATEGY_FILL = 'rgba(139, 92, 246, 0.14)';
const BENCHMARK_STROKE = '#cbd5e1';
const BENCHMARK_FILL = 'rgba(203, 213, 225, 0.1)';
const GRID_STROKE = 'rgba(255, 255, 255, 0.05)';
const AXIS_STROKE = 'rgba(255, 255, 255, 0.12)';
const LABEL_FILL = 'rgba(255, 255, 255, 0.72)';
const TOOLTIP_BG = 'rgba(13, 17, 23, 0.92)';

const axisCurrencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const monthYearFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  year: 'numeric',
});

const fullDateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function parseLocalDate(raw: string) {
  if (!raw) return new Date(NaN);
  return raw.includes('T') ? new Date(raw) : new Date(`${raw}T00:00:00`);
}

function buildTickIndices(length: number, desiredCount: number) {
  if (length <= 0) return [];
  if (length === 1) return [0];

  const count = Math.min(length, desiredCount);
  const indices = Array.from({ length: count }, (_, index) =>
    Math.round((index * (length - 1)) / Math.max(count - 1, 1)),
  );

  return [...new Set(indices)].sort((left, right) => left - right);
}

function buildYTicks(min: number, max: number, count: number) {
  if (count <= 1) return [max];
  return Array.from({ length: count }, (_, index) => max - ((max - min) * index) / (count - 1));
}

function buildLinePath(
  points: EquityPoint[],
  getValue: (point: EquityPoint) => number | null,
  toX: (index: number) => number,
  toY: (value: number) => number,
) {
  let started = false;
  const segments: string[] = [];

  points.forEach((point, index) => {
    const value = getValue(point);
    if (value == null || Number.isNaN(value)) return;
    segments.push(`${started ? 'L' : 'M'} ${toX(index)} ${toY(value)}`);
    started = true;
  });

  return segments.join(' ');
}

function buildAreaPath(
  points: EquityPoint[],
  getValue: (point: EquityPoint) => number | null,
  toX: (index: number) => number,
  toY: (value: number) => number,
  bottomY: number,
) {
  const coordinates = points
    .map((point, index) => {
      const value = getValue(point);
      if (value == null || Number.isNaN(value)) return null;
      return { x: toX(index), y: toY(value) };
    })
    .filter((value): value is { x: number; y: number } => value != null);

  if (coordinates.length === 0) return '';

  return [
    `M ${coordinates[0].x} ${bottomY}`,
    ...coordinates.map(({ x, y }) => `L ${x} ${y}`),
    `L ${coordinates[coordinates.length - 1].x} ${bottomY}`,
    'Z',
  ].join(' ');
}

export function EquityCurveChart({
  points,
  showBenchmark,
  runVersion,
}: {
  points: EquityPoint[];
  showBenchmark: boolean;
  runVersion: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const strategyPathRef = useRef<SVGPathElement | null>(null);
  const [containerWidth, setContainerWidth] = useState(920);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const updateSize = () => {
      setContainerWidth(Math.max(element.clientWidth, 320));
    };

    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const hasPoints = points.length > 0;
  const width = Math.max(containerWidth, 320);
  const height = width < 640 ? 320 : 360;
  const padding = {
    top: 18,
    right: width < 480 ? 14 : 20,
    bottom: width < 480 ? 42 : 46,
    left: width < 480 ? 58 : 76,
  };
  const plotWidth = Math.max(width - padding.left - padding.right, 1);
  const plotHeight = Math.max(height - padding.top - padding.bottom, 1);
  const plotBottomY = height - padding.bottom;
  const xTickCount = width < 480 ? 4 : width < 900 ? 5 : 6;
  const yTickCount = width < 480 ? 4 : 5;

  const benchmarkValues = showBenchmark
    ? points.map((point) => point.benchmark).filter((value): value is number => value != null)
    : [];
  const allValues = [...points.map((point) => point.strategy), ...benchmarkValues];
  const minValue = hasPoints ? Math.min(...allValues) : 0;
  const maxValue = hasPoints ? Math.max(...allValues) : 0;
  const valueSpan = Math.max(maxValue - minValue, Math.abs(maxValue || minValue || 1) * 0.1, 1);
  const valuePadding = valueSpan * 0.05;
  const chartMin = minValue - valuePadding;
  const chartMax = maxValue + valuePadding;
  const yDomain = Math.max(chartMax - chartMin, 1);

  const toX = (index: number) => padding.left + (plotWidth * index) / Math.max(points.length - 1, 1);
  const toY = (value: number) => padding.top + (1 - (value - chartMin) / yDomain) * plotHeight;

  const strategyLine = hasPoints ? buildLinePath(points, (point) => point.strategy, toX, toY) : '';
  const benchmarkLine = showBenchmark ? buildLinePath(points, (point) => point.benchmark, toX, toY) : '';
  const strategyArea = hasPoints ? buildAreaPath(points, (point) => point.strategy, toX, toY, plotBottomY) : '';
  const benchmarkArea = showBenchmark ? buildAreaPath(points, (point) => point.benchmark, toX, toY, plotBottomY) : '';
  const yTicks = buildYTicks(chartMin, chartMax, yTickCount);
  const xTickIndices = buildTickIndices(points.length, xTickCount);

  useEffect(() => {
    const node = strategyPathRef.current;
    if (!node || !strategyLine) return;
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

  useEffect(() => {
    if (!hasPoints) {
      setHoveredIndex(null);
      return;
    }
    setHoveredIndex((current) => {
      if (current == null) return null;
      return clamp(current, 0, points.length - 1);
    });
  }, [hasPoints, points.length]);

  if (!hasPoints) {
    return (
      <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] p-4 text-sm text-[var(--text-tertiary)]">
        No equity data available.
      </div>
    );
  }

  const hoverPoint = hoveredIndex != null ? points[hoveredIndex] : null;
  const hoverX = hoveredIndex != null ? toX(hoveredIndex) : null;
  const hoverStrategyY = hoverPoint ? toY(hoverPoint.strategy) : null;
  const hoverBenchmarkY =
    hoverPoint != null && hoverPoint.benchmark != null ? toY(hoverPoint.benchmark) : null;
  const tooltipDate = hoverPoint ? fullDateFormatter.format(parseLocalDate(hoverPoint.date)) : null;
  const relativeDiff =
    hoverPoint != null &&
    hoverPoint.benchmark != null &&
    hoverPoint.benchmark !== 0
      ? ((hoverPoint.strategy - hoverPoint.benchmark) / hoverPoint.benchmark) * 100
      : null;
  const tooltipWidth = width < 480 ? 176 : 220;
  const tooltipGap = 14;
  const tooltipLeft =
    hoverX == null
      ? 12
      : hoverX + tooltipGap + tooltipWidth <= width - 12
        ? hoverX + tooltipGap
        : clamp(hoverX - tooltipWidth - tooltipGap, 12, Math.max(width - tooltipWidth - 12, 12));

  const handlePointerMove = (event: ReactMouseEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const pointerX = clamp(event.clientX - rect.left, padding.left, width - padding.right);
    const ratio = (pointerX - padding.left) / plotWidth;
    const nextIndex = clamp(Math.round(ratio * Math.max(points.length - 1, 0)), 0, points.length - 1);
    setHoveredIndex(nextIndex);
  };

  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--bg-surface-2)] p-3">
      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-[var(--text-secondary)]">
        <span className="inline-flex items-center gap-2">
          <span className="h-[2px] w-6 rounded-full" style={{ backgroundColor: STRATEGY_STROKE }} />
          Strategy
        </span>
        {showBenchmark ? (
          <span className="inline-flex items-center gap-2">
            <span
              className="h-[2px] w-6 rounded-full"
              style={{
                backgroundImage: `linear-gradient(to right, ${BENCHMARK_STROKE} 0 60%, transparent 60% 100%)`,
                backgroundSize: '10px 2px',
              }}
            />
            Buy &amp; Hold
          </span>
        ) : null}
      </div>

      <div ref={containerRef} className="relative h-[360px] w-full max-sm:h-[320px]">
        {hoverPoint ? (
          <div
            className="pointer-events-none absolute top-3 z-10 rounded-xl border border-white/10 px-3 py-2 text-xs text-white shadow-lg backdrop-blur-sm"
            style={{ left: tooltipLeft, width: tooltipWidth, backgroundColor: TOOLTIP_BG }}
          >
            <div className="font-medium text-white">{tooltipDate}</div>
            <div className="mt-1 flex items-center justify-between gap-3">
              <span className="inline-flex items-center gap-2 text-white/80">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: STRATEGY_STROKE }} />
                Strategy
              </span>
              <span className="tabular-nums">{formatCurrency(hoverPoint.strategy)}</span>
            </div>
            {showBenchmark && hoverPoint.benchmark != null ? (
              <div className="mt-1 flex items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-white/80">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: BENCHMARK_STROKE }} />
                  Buy &amp; Hold
                </span>
                <span className="tabular-nums">{formatCurrency(hoverPoint.benchmark)}</span>
              </div>
            ) : null}
            {showBenchmark && relativeDiff != null ? (
              <div className="mt-1 flex items-center justify-between gap-3 text-white/75">
                <span>Difference</span>
                <span className="tabular-nums">{formatPercent(relativeDiff, { mode: 'percent' })}</span>
              </div>
            ) : null}
          </div>
        ) : null}

        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-full w-full"
          role="img"
          aria-label="Equity curve comparing the strategy and buy-and-hold benchmark"
        >
          {yTicks.map((tickValue) => {
            const y = toY(tickValue);
            return (
              <g key={tickValue}>
                <line x1={padding.left} x2={width - padding.right} y1={y} y2={y} stroke={GRID_STROKE} />
                <text
                  x={padding.left - 10}
                  y={y}
                  fill={LABEL_FILL}
                  fontSize="11"
                  textAnchor="end"
                  dominantBaseline="middle"
                >
                  {axisCurrencyFormatter.format(tickValue)}
                </text>
              </g>
            );
          })}

          <line
            x1={padding.left}
            x2={padding.left}
            y1={padding.top}
            y2={plotBottomY}
            stroke={AXIS_STROKE}
          />
          <line
            x1={padding.left}
            x2={width - padding.right}
            y1={plotBottomY}
            y2={plotBottomY}
            stroke={AXIS_STROKE}
          />

          {showBenchmark && benchmarkArea ? <path d={benchmarkArea} fill={BENCHMARK_FILL} /> : null}
          {strategyArea ? <path d={strategyArea} fill={STRATEGY_FILL} /> : null}

          {showBenchmark && benchmarkLine ? (
            <path
              d={benchmarkLine}
              fill="none"
              stroke={BENCHMARK_STROKE}
              strokeWidth="2"
              strokeDasharray="6 6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : null}
          <path
            ref={strategyPathRef}
            d={strategyLine}
            fill="none"
            stroke={STRATEGY_STROKE}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {xTickIndices.map((index) => {
            const point = points[index];
            const x = toX(index);
            const date = parseLocalDate(point.date);
            return (
              <g key={`${point.date}-${index}`}>
                <line x1={x} x2={x} y1={plotBottomY} y2={plotBottomY + 6} stroke={AXIS_STROKE} />
                <text
                  x={x}
                  y={plotBottomY + 18}
                  fill={LABEL_FILL}
                  fontSize="11"
                  textAnchor="middle"
                >
                  {monthYearFormatter.format(date)}
                </text>
              </g>
            );
          })}

          {hoverPoint && hoverX != null ? (
            <>
              <line
                x1={hoverX}
                x2={hoverX}
                y1={padding.top}
                y2={plotBottomY}
                stroke="rgba(255, 255, 255, 0.28)"
                strokeDasharray="5 5"
              />
              {hoverStrategyY != null ? (
                <>
                  <circle cx={hoverX} cy={hoverStrategyY} r="6" fill="rgba(13, 17, 23, 0.95)" />
                  <circle cx={hoverX} cy={hoverStrategyY} r="3.5" fill={STRATEGY_STROKE} />
                </>
              ) : null}
              {showBenchmark && hoverBenchmarkY != null ? (
                <>
                  <circle cx={hoverX} cy={hoverBenchmarkY} r="6" fill="rgba(13, 17, 23, 0.95)" />
                  <circle cx={hoverX} cy={hoverBenchmarkY} r="3.5" fill={BENCHMARK_STROKE} />
                </>
              ) : null}
            </>
          ) : null}

          <rect
            x={padding.left}
            y={padding.top}
            width={plotWidth}
            height={plotHeight}
            fill="transparent"
            onMouseMove={handlePointerMove}
            onMouseLeave={() => setHoveredIndex(null)}
          />
        </svg>
      </div>
    </div>
  );
}
