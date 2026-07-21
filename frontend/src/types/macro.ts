export interface MacroSparklinePoint {
  date: string;
  value: number | null;
}

export interface MacroSeriesData {
  id: string;
  label: string;
  unit: string;
  latest_value: number | null;
  latest_date: string | null;
  change_1m: number | null;
  sparkline: MacroSparklinePoint[];
}

export interface MacroDashboardResponse {
  configured: boolean;
  series: MacroSeriesData[];
}
