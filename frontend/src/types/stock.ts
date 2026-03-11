// Stock types matching backend Pydantic models

export interface Stock {
  ticker: string;
  name: string | null;
  company_name?: string | null; // Alternative field name from API

  // Basic info
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  
  // Valuation
  pe_ratio: number | null;
  forward_pe: number | null;
  peg_ratio: number | null;
  pb_ratio: number | null;
  ps_ratio: number | null;
  ev_to_ebitda: number | null;
  
  // Profitability
  eps: number | null;
  profit_margin: number | null;
  operating_margin: number | null;
  roe: number | null;
  roa: number | null;
  
  // Growth
  revenue_growth: number | null;
  earnings_growth: number | null;
  
  // Financial health
  debt_to_equity: number | null;
  current_ratio: number | null;
  quick_ratio: number | null;
  
  // Dividends
  dividend_yield: number | null;
  dividend_rate: number | null;
  payout_ratio: number | null;
  
  // Trading
  current_price: number | null;
  day_change_percent: number | null;
  change_percent?: number | null; // Alternative field name from API
  volume: number | null;
  avg_volume: number | null;
  beta: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  
  // Metadata
  last_updated: string | null;
}

export interface StockPrice {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface PriceHistoryResponse {
  ticker: string;
  period: string;
  data_points: number;
  data: StockPrice[];
}

export interface BacktestDataPoint {
  Date: string;
  Open: number;
  High: number;
  Low: number;
  Close: number;
  Volume: number;
  Adj_Close: number;
  Returns: number;
  
  // Technical indicators (if included)
  SMA_20?: number;
  SMA_50?: number;
  SMA_200?: number;
  EMA_12?: number;
  EMA_26?: number;
  MACD?: number;
  MACD_Signal?: number;
  RSI_14?: number;
  BB_Upper?: number;
  BB_Lower?: number;
  Volume_SMA_20?: number;
}

export interface BacktestDataResponse {
  ticker: string;
  source: 'cache' | 'database' | 'yfinance';
  cached: boolean;
  start_date: string;
  end_date: string;
  data_points: number;
  indicators_included: boolean;
  columns: string[];
  data: BacktestDataPoint[];
}

export interface BacktestIndicatorConfig {
  enabled: boolean;
  weight: number;
  params: Record<string, number | boolean>;
}

export interface BacktestGateConfig {
  enabled: boolean;
  params: Record<string, number | boolean>;
}

export interface BacktestRunRequest {
  start_date: string;
  end_date: string;
  indicators: Record<string, BacktestIndicatorConfig>;
  atr_gate?: BacktestGateConfig;
  long_threshold: number;
  short_threshold: number;
  exec_lag: number;
  tc_bps: number;
  allow_position_hold: boolean;
  generate_plots: boolean;
  generate_roc: boolean;
}

export interface BacktestRunResponse {
  ticker: string;
  source: 'database' | 'yfinance';
  cached: boolean;
  start_date: string;
  end_date: string;
  warnings: string[];
  selected_indicators: string[];
  stats: Record<string, number>;
  equity_curve: Array<Record<string, string | number | null>>;
  results: Array<Record<string, string | number | null>>;
  equity_curve_image?: string | null;
  roc_auc?: number | null;
  roc_curve_image?: string | null;
}

export interface ScreenerFilters {
  search?: string;
  min_pe?: number;
  max_pe?: number;
  min_market_cap?: number;
  max_market_cap?: number;
  sectors?: string[];
  industries?: string[];
  min_dividend_yield?: number;
  max_debt_to_equity?: number;
  max_beta?: number;
  min_roe?: number;
  min_revenue_growth?: number;
  min_price?: number;
  max_price?: number;
  min_volume?: number;
  min_avg_volume?: number;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ScreenerResponse {
  results: Stock[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  cached?: boolean;
}

export interface StockSuggestion {
  ticker: string;
  name: string | null;
}
