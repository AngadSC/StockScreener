// ====================================
// INSIDER ACTIVITY (SEC EDGAR Form 4)
// ====================================

export type InsiderActivityType = 'buys' | 'sells' | 'all';

export interface InsiderTransaction {
  accession_no: string;
  filed_date: string;
  transaction_date: string | null;
  symbol: string;
  company: string | null;
  owner_name: string | null;
  owner_title: string | null;
  is_officer: boolean;
  is_director: boolean;
  transaction_code: string; // "P" | "S"
  type: 'buy' | 'sell';
  shares: number | null;
  price: number | null;
  value: number | null;
}

export interface InsiderActivityFilters {
  type: InsiderActivityType;
  min_value: number;
  days: number;
  limit?: number;
}

export interface InsiderActivityResponse {
  results: InsiderTransaction[];
  count: number;
  filters: {
    type: InsiderActivityType;
    min_value: number;
    days: number;
    limit: number;
  };
  cached?: boolean;
}

export interface InsiderTickerResponse {
  symbol: string;
  company: string | null;
  results: InsiderTransaction[];
  count: number;
  filters?: {
    type: InsiderActivityType;
    days: number;
    limit: number;
  };
}
