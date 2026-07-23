// Market scanners types, matching backend/app/services/market_scans.py's payload shape.

export interface MarketScanRow {
  symbol: string;
  name: string | null;
  sector: string | null;
  close: number | null;
  change_pct: number | null;
  // Scan-specific ranking value: change_pct for gainers/losers, % off the
  // 52-week high/low for high_52w/low_52w, volume ratio for unusual_volume,
  // gap % for gap_up/gap_down.
  metric: number | null;
  volume: number | null;
  market_cap: number | null;
}

export interface SectorPerformance {
  sector: string;
  avg_change_percent: number | null;
  advancers: number;
  decliners: number;
  stock_count: number;
  total_market_cap: number;
}

export interface MarketScansResponse {
  as_of_date: string | null;
  prior_date: string | null;
  gainers: MarketScanRow[];
  losers: MarketScanRow[];
  high_52w: MarketScanRow[];
  low_52w: MarketScanRow[];
  unusual_volume: MarketScanRow[];
  gap_up: MarketScanRow[];
  gap_down: MarketScanRow[];
  sectors: SectorPerformance[];
  cached?: boolean;
}

export interface MarketSectorsResponse {
  as_of_date: string | null;
  sectors: SectorPerformance[];
}

export type MarketScanKey =
  | 'gainers'
  | 'losers'
  | 'high_52w'
  | 'low_52w'
  | 'unusual_volume'
  | 'gap_up'
  | 'gap_down';

export interface MarketScanTabConfig {
  key: MarketScanKey;
  label: string;
  metricLabel: string;
  metricFormat: 'percent' | 'ratio';
  /** One plain-English line explaining what the scan surfaces. */
  description: string;
}

export const MARKET_SCAN_TABS: MarketScanTabConfig[] = [
  { key: 'gainers', label: 'Gainers', metricLabel: 'Chg%', metricFormat: 'percent', description: 'Stocks with the largest positive price change since the prior close.' },
  { key: 'losers', label: 'Losers', metricLabel: 'Chg%', metricFormat: 'percent', description: 'Stocks with the largest negative price change since the prior close.' },
  { key: 'high_52w', label: '52W Highs', metricLabel: 'Off high', metricFormat: 'percent', description: 'Names trading at or near their highest price of the past 52 weeks.' },
  { key: 'low_52w', label: '52W Lows', metricLabel: 'Off low', metricFormat: 'percent', description: 'Names trading at or near their lowest price of the past 52 weeks.' },
  { key: 'unusual_volume', label: 'Unusual Volume', metricLabel: 'Vol ratio', metricFormat: 'ratio', description: 'Today’s volume divided by average volume — a spike often precedes a move.' },
  { key: 'gap_up', label: 'Gap Ups', metricLabel: 'Gap%', metricFormat: 'percent', description: 'Opened well above the prior close, usually on overnight news or earnings.' },
  { key: 'gap_down', label: 'Gap Downs', metricLabel: 'Gap%', metricFormat: 'percent', description: 'Opened well below the prior close, usually on overnight news or earnings.' },
];
