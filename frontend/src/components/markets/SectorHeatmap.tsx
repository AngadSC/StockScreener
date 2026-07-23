'use client';

import { formatMarketCap, formatPercent } from '@/lib/utils';
import type { SectorPerformance } from '@/types/market';

// Matches --up / --dn from globals.css so heatmap tiles stay in the same
// palette as the rest of the app's up/down chips.
const POSITIVE_RGB = '94, 201, 115';
const NEGATIVE_RGB = '193, 79, 54';
const NEUTRAL_RGB = '148, 148, 148';

// % change at which a tile reaches full color saturation. Sector averages
// rarely move more than a few percent in a single session.
const MAX_INTENSITY_PCT = 4;

function intensityFor(changePercent: number | null): { rgb: string; alpha: number } {
  if (changePercent === null || changePercent === undefined || changePercent === 0) {
    return { rgb: NEUTRAL_RGB, alpha: 0.05 };
  }
  const magnitude = Math.min(Math.abs(changePercent), MAX_INTENSITY_PCT) / MAX_INTENSITY_PCT;
  const alpha = 0.08 + magnitude * 0.55;
  return { rgb: changePercent > 0 ? POSITIVE_RGB : NEGATIVE_RGB, alpha };
}

interface SectorHeatmapProps {
  sectors: SectorPerformance[];
  isLoading?: boolean;
}

function SkeletonTiles() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
      {Array.from({ length: 12 }).map((_, index) => (
        <div key={index} className="screener-skeleton h-[104px] rounded-[var(--radius-lg)]" />
      ))}
    </div>
  );
}

export default function SectorHeatmap({ sectors, isLoading }: SectorHeatmapProps) {
  if (isLoading) {
    return <SkeletonTiles />;
  }

  if (sectors.length === 0) {
    return (
      <div className="deco-panel flex min-h-[120px] items-center justify-center bg-[var(--bg-surface-1)] p-6 text-center">
        <p className="text-sm text-[var(--text-secondary)]">
          Scanner data is generated after the market close. Check back soon.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
      {sectors.map((sector) => {
        const { rgb, alpha } = intensityFor(sector.avg_change_percent);
        const isPositive = (sector.avg_change_percent ?? 0) >= 0;

        return (
          <div
            key={sector.sector}
            className="hud flex flex-col justify-between gap-2 rounded-[var(--radius-lg)] border border-[var(--border-subtle)] p-4 transition-transform duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:-translate-y-0.5"
            style={{ backgroundColor: `rgba(${rgb}, ${alpha})` }}
          >
            <span className="hud-c1" />
            <span className="hud-c2" />
            <div className="truncate text-xs font-medium uppercase tracking-[0.08em] text-[var(--text-secondary)]">
              {sector.sector}
            </div>
            <div
              className={`serif-num text-2xl ${isPositive ? 'text-[var(--up)]' : 'text-[var(--dn)]'}`}
            >
              {formatPercent(sector.avg_change_percent, { mode: 'percent', withSign: true })}
            </div>
            <div className="flex items-center justify-between text-[11px] text-[var(--text-tertiary)]">
              <span>
                {sector.advancers}↑ / {sector.decliners}↓
              </span>
              <span>{formatMarketCap(sector.total_market_cap)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
