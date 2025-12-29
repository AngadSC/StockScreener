// Stock types matching backend Pydantic models

export interface Stock {
  ticker: string;
  name: string | null;
  
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
  source: 'cache' | 'yfinance';
  cached: boolean;
  start_date: string;
  end_date: string;
  data_points: number;
  indicators_included: boolean;
  columns: string[];
  data: BacktestDataPoint[];
}

export interface ScreenerFilters {
  min_pe?: number;
  max_pe?: number;
  min_market_cap?: number;
  max_market_cap?: number;
  sectors?: string[];
  industries?: string[];
  min_dividend_yield?: number;
  max_debt_to_equity?: number;
  min_price?: number;
  max_price?: number;
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
