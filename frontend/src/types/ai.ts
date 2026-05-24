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
  action_label:
    | 'actionable_long'
    | 'long_watchlist'
    | 'neutral_wait'
    | 'short_watchlist'
    | 'actionable_short'
    | 'avoid'
    | 'high_risk';
  directional_bias:
    | 'bullish'
    | 'bearish'
    | 'neutral'
    | 'mixed_bullish_lean'
    | 'mixed_bearish_lean';
  timeframe_ratings: TimeframeRatings;
  price_action_structure: PriceActionStructure;
  setup_type: string;
  confidence_score: number;
  setup_quality_score: number;
  entry_timing_score: number;
  technical_score: number;
  price_structure_score: number;
  volume_score: number;
  momentum_score: number;
  trend_score: number;
  fundamental_score: number;
  revenue_earnings_quality_score: number;
  sentiment_score: number;
  news_score: number;
  valuation_score: number;
  risk_score: number;
  risk_reward_score: number;
  short_term_score: number;
  swing_trade_score: number;
  long_term_score: number;
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
  trade_card?: AITradeCard | null;
}

export interface NewsArticle {
  title?: string;
  headline?: string;
  url?: string;
  source?: string;
  published_at?: string;
  summary?: string;
  sentiment?: string;
  event_type?: string;
  materiality?: 'low' | 'medium' | 'high' | string;
  time_horizon?: 'immediate' | 'medium_term' | 'long_term' | string;
  why_it_matters?: string;
}

// ── Trade Card Types ──────────────────────────────────────────────────────────

export interface TradeLevels {
  current_price: number | null;
  preferred_entry: number | null;
  aggressive_entry_min: number | null;
  aggressive_entry_max: number | null;
  confirmation_trigger: number | null;
  add_level: number | null;
  invalidation_level: number | null;
  target_1: number | null;
  target_2: number | null;
  chase_above: number | null;
  method: string | null; // "breakout" | "pullback" | "breakdown" | "no_setup"
  warnings: string[];
}

export interface IfThenPlan {
  if_trigger_hits: string;
  if_rejects: string;
  if_breaks_invalidation: string;
  if_already_holding: string;
  if_missed_entry: string;
}

export type TradeCardDecision =
  | 'Long Setup Active'
  | 'Conditional Long'
  | 'Bullish Watch'
  | 'No Trade'
  | 'Conditional Short'
  | 'Short Setup Active'
  | 'Avoid'
  | 'High Risk';

export type TradeCardBestAction =
  | 'buy_now'
  | 'wait_for_breakout'
  | 'wait_for_pullback'
  | 'hold_if_in'
  | 'avoid'
  | 'short_now'
  | 'wait_for_breakdown';

export type TradeCardConfidence = 'low' | 'moderate' | 'strong' | 'very_strong';

export interface AITradeCard {
  decision: TradeCardDecision;
  ai_lean: 'bullish' | 'bearish' | 'neutral';
  best_action_now: TradeCardBestAction;
  verdict: string;
  setup_type: string;
  confidence_label: TradeCardConfidence;
  setup_score: number;
  trade_levels: TradeLevels;
  main_reason: string;
  main_risk: string;
  bull_case: string[];
  bear_case: string[];
  if_then_plan: IfThenPlan;
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
