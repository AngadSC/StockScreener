export interface AIReportOutput {
  action_label: 'buy_setup' | 'watchlist' | 'neutral' | 'avoid' | 'high_risk';
  swing_bias: 'bullish' | 'bearish' | 'neutral' | 'mixed';
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
