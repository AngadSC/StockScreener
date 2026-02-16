import axios, { AxiosError } from 'axios';
import type { 
  Stock, 
  ScreenerFilters, 
  ScreenerResponse,
  PriceHistoryResponse,
  BacktestDataResponse,
  StockSuggestion
} from '@/types/stock';
import type { AuthResponse, LoginCredentials, RegisterData, User } from '@/types/user';
import type { WatchlistResponse } from '@/types/watchlist';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'access_token';

const safeStorage = {
  get(key: string): string | null {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // Ignore storage errors in restricted browser contexts.
    }
  },
  remove(key: string): void {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.removeItem(key);
    } catch {
      // Ignore storage errors in restricted browser contexts.
    }
  },
};

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = safeStorage.get(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      safeStorage.remove(TOKEN_KEY);
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
    }
    return Promise.reject(error);
  }
);

// ====================================
// AUTH API
// ====================================

export const authAPI = {
  register: async (data: RegisterData): Promise<User> => {
    const response = await api.post<User>('/auth/register', data);
    return response.data;
  },

  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    // OAuth2 requires form data
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);

    const response = await api.post<AuthResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    // Store token
    safeStorage.set(TOKEN_KEY, response.data.access_token);

    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  logout: () => {
    safeStorage.remove(TOKEN_KEY);
    if (typeof window !== 'undefined') {
      window.location.href = '/auth/login';
    }
  },
};

// ====================================
// STOCKS API
// ====================================

export const stocksAPI = {
  getStock: async (ticker: string): Promise<Stock> => {
    const response = await api.get<Stock>(`/stocks/${ticker}`);
    return response.data;
  },

  getPriceHistory: async (
    ticker: string,
    period: '1mo' | '3mo' | '6mo' | '1y' = '1y'
  ): Promise<PriceHistoryResponse> => {
    const response = await api.get<PriceHistoryResponse>(
      `/stocks/${ticker}/prices`,
      { params: { period } }
    );
    return response.data;
  },

  getBacktestData: async (
    ticker: string,
    startDate: string,
    endDate: string,
    includeIndicators: boolean = true
  ): Promise<BacktestDataResponse> => {
    const response = await api.post<BacktestDataResponse>(
      `/stocks/${ticker}/backtest-data`,
      null,
      {
        params: {
          start_date: startDate,
          end_date: endDate,
          include_indicators: includeIndicators,
        },
      }
    );
    return response.data;
  },

  getMLFeatures: async (
    ticker: string,
    startDate: string,
    endDate: string
  ): Promise<any> => {
    const response = await api.post(
      `/stocks/${ticker}/ml-features`,
      null,
      {
        params: {
          start_date: startDate,
          end_date: endDate,
        },
      }
    );
    return response.data;
  },

  getIntradayData: async (
    ticker: string,
    interval: '1m' | '5m' | '15m' | '30m' | '60m' = '5m',
    days: number = 5
  ): Promise<any> => {
    const response = await api.get(`/stocks/${ticker}/intraday`, {
      params: { interval, days },
    });
    return response.data;
  },
};

// ====================================
// SCREENER API
// ====================================

export const screenerAPI = {
  screenStocks: async (filters: ScreenerFilters): Promise<ScreenerResponse> => {
    const response = await api.get<ScreenerResponse>('/screener/screen', {
      params: filters,
    });
    return response.data;
  },

  suggestStocks: async (
    query: string,
    limit: number = 10
  ): Promise<{ query: string; results: StockSuggestion[]; count: number }> => {
    const response = await api.get('/screener/suggest', {
      params: { q: query, limit },
    });
    return response.data;
  },

  getSectors: async (): Promise<{ sectors: string[]; count: number }> => {
    const response = await api.get('/screener/sectors');
    return response.data;
  },

  getIndustries: async (): Promise<{ industries: string[]; count: number }> => {
    const response = await api.get('/screener/industries');
    return response.data;
  },
};

// ====================================
// WATCHLIST API
// ====================================

export const watchlistAPI = {
  getWatchlist: async (): Promise<WatchlistResponse> => {
    const response = await api.get<WatchlistResponse>('/watchlist');
    return response.data;
  },

  addToWatchlist: async (ticker: string): Promise<any> => {
    const response = await api.post('/watchlist', { ticker });
    return response.data;
  },

  removeFromWatchlist: async (ticker: string): Promise<any> => {
    const response = await api.delete(`/watchlist/${ticker}`);
    return response.data;
  },
};

export default api;
