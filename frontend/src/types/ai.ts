export interface PriceActionStructure {
  setup_label: string;
  structure_label: string;
  breakout_label: string;
  pullback_label: string;
  range_label: string;
  gap_label: string;
  labels: string[];
  near_20d_high: boolean;
  near_60d_high: boolean;
  distance_to_support_pct: number | null;
  distance_to_resistance_pct: number | null;
  range_compression: boolean;
  higher_highs_higher_lows: boolean;
  lower_highs_lower_lows: boolean;
  gap_up_recent: boolean;
  gap_down_recent: boolean;
  failed_breakout: boolean;
  breakout_attempt: boolean;
  pullback_to_sma20: boolean;
  pullback_to_sma50: boolean;
  support_level: number | null;
  resistance_level: number | null;
  prior_20d_resistance: number | null;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
}

export interface TradeTimeframeRating {
  rating: 'buy' | 'watch' | 'avoid';
  timeframe: '1-10 trading days' | '2-8 weeks';
  confidence_score: number;
  reason: string;
}

export interface LongTermTimeframeRating {
  rating: 'accumulate' | 'hold' | 'avoid' | 'unknown';
  timeframe: '6-24 months';
  confidence_score: number;
  reason: string;
}

export interface TimeframeRatings {
  short_term: TradeTimeframeRating;
  swing: TradeTimeframeRating;
  long_term: LongTermTimeframeRating;
}

export interface AIReportOutput {
  action_label: 'buy_setup' | 'watchlist' | 'neutral' | 'avoid' | 'high_risk';
  swing_bias: 'bullish' | 'bearish' | 'neutral' | 'mixed';
  timeframe_ratings: TimeframeRatings;
  price_action_structure: PriceActionStructure;
  setup_type: string;
  confidence_score: number;
  setup_quality_score: number;
  entry_timing_score: number;
  technical_score: number;
  fundamental_score: number;
  sentiment_score: number;
  valuation_score: number;
  risk_score: number;
  trade_read: string;
  main_thesis: string;
  entry_zone: string;
  confirmation_trigger: string;
  invalidation_level: string;
  target_1: string;
  target_2: string;
  risk_reward_summary: string;
  why_it_could_move: string;
  why_it_could_fail: string;
  watchlist_action: string;
  confirmation_signals: string[];
  news_summary: string;
  final_verdict: string;
}

export interface NewsArticle {
  title?: string;
  headline?: string;
  url?: string;
  source?: string;
  published_at?: string;
  summary?: string;
  sentiment?: string;
}

export interface AIReportSuccessResponse {
  ticker: string;
  created_at: string;
  cached: boolean;
  tier_used: string;
  report: AIReportOutput;
}

export interface AIReportForbiddenResponse {
  error: 'not_pro';
  status: 403;
  message: string;
  detail?: string;
}

export interface AIReportLimitExceededResponse {
  error: 'limit_exceeded';
  status: 429;
  message: string;
  detail?: string;
}

export interface AIReportGenerationErrorResponse {
  error: 'generation_failed';
  status: number;
  message: string;
  detail?: string;
}

export type AIReportErrorResponse =
  | AIReportForbiddenResponse
  | AIReportLimitExceededResponse
  | AIReportGenerationErrorResponse;

export type AIReportResponse = AIReportSuccessResponse | AIReportErrorResponse;

export type AIReportState = 'idle' | 'loading' | 'loaded' | 'error' | 'locked';
