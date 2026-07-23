'use client';

import { useMemo, useRef } from 'react';

/**
 * Categorical series palette for the compare tool (blue / orange / aqua / gold).
 *
 * Deliberately distinct from the app's semantic --positive/--negative (green/rust)
 * tokens so a ticker's line color never reads as a "price up" or "price down"
 * signal — identity only, never polarity.
 *
 * Validated with the dataviz palette checker against the app's dark surface
 * (#0d1011) on the adjacent-pair gate that applies to line charts: worst
 * adjacent CVD ΔE 8.4 (protan/deutan, target >= 8), worst adjacent
 * normal-vision ΔE 19.8 (floor >= 15), all four slots clear 3:1 contrast and
 * sit inside the dark lightness band (OKLCH L 0.48-0.67). Order matters —
 * it is the CVD-safety mechanism, so slots are assigned in this fixed order
 * and never re-cycled.
 */
export const SERIES_COLORS = ['#3987e5', '#d95926', '#199e70', '#c98500'] as const;

export const MAX_COMPARE_TICKERS = SERIES_COLORS.length;

export type SeriesColorMap = Map<string, string>;

/**
 * Assigns each ticker a stable color slot for the lifetime it stays in the
 * comparison set. Colors are keyed to the symbol (not array index/rank), so
 * removing one ticker never repaints the remaining ones.
 */
export function useSeriesColors(tickers: string[]): SeriesColorMap {
  const assignmentRef = useRef<Map<string, number>>(new Map());

  return useMemo(() => {
    const assignment = assignmentRef.current;
    const activeSymbols = new Set(tickers);

    // Free slots held by tickers that are no longer in the list.
    for (const symbol of Array.from(assignment.keys())) {
      if (!activeSymbols.has(symbol)) {
        assignment.delete(symbol);
      }
    }

    // Assign the lowest free slot to any new ticker.
    tickers.forEach((symbol) => {
      if (assignment.has(symbol)) return;
      const usedSlots = new Set(assignment.values());
      let slot = 0;
      while (usedSlots.has(slot) && slot < SERIES_COLORS.length) slot += 1;
      assignment.set(symbol, Math.min(slot, SERIES_COLORS.length - 1));
    });

    const colorMap: SeriesColorMap = new Map();
    tickers.forEach((symbol) => {
      const slot = assignment.get(symbol) ?? 0;
      colorMap.set(symbol, SERIES_COLORS[slot % SERIES_COLORS.length]);
    });

    return colorMap;
  }, [tickers]);
}
