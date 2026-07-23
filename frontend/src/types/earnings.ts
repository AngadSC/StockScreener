export type EarningsTimeHint = 'bmo' | 'amc' | 'unknown';

export interface EarningsEventItem {
  ticker: string | null;
  name: string | null;
  market_cap: number | null;
  earnings_date: string;
  time_hint: EarningsTimeHint;
  eps_estimate: number | null;
  is_watchlisted: boolean;
}

export interface EarningsCalendarResponse {
  days: number;
  from_date: string;
  to_date: string;
  authenticated: boolean;
  events: EarningsEventItem[];
}
