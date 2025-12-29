import { Stock } from './stock';

export interface WatchlistItem {
  id: number;
  ticker: string;
  added_at: string;
  stock: Stock;
}

export interface WatchlistResponse {
  items: WatchlistItem[];
  total: number;
}

