import axios, { AxiosError } from 'axios';
import type { 
  Stock, 
  ScreenerFilters, 
  ScreenerResponse,
  PriceHistoryResponse,
  BacktestDataResponse,
  IndicatorBacktestRunRequest,
  IndicatorBacktestRunResponse,
  BacktestRunRequest,
  BacktestRunResponse,
  StockSuggestion
} from '@/types/stock';
import type { AuthResponse, LoginCredentials, RegisterData, User } from '@/types/user';
import type { WatchlistResponse } from '@/types/watchlist';
import type { AIReportResponse, AIReportSuccessResponse } from '@/types/ai';
import type { EmailPreferences, EmailPreferencesUpdate } from '@/types/email';
import type { MarketScansResponse, MarketSectorsResponse } from '@/types/market';
import type {
  InsiderActivityFilters,
  InsiderActivityResponse,
  InsiderTickerResponse,
} from '@/types/insiders';
import type { EarningsCalendarResponse } from '@/types/earnings';
import type { MacroDashboardResponse } from '@/types/macro';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const requestUrl = typeof error.config?.url === 'string' ? error.config.url : '';
    const isAuthEndpoint = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register');
    const isSessionCheck = requestUrl.includes('/auth/me');
    if (error.response?.status === 401) {
      // Redirect to login on unauthorized, except during auth requests.
      if (typeof window !== 'undefined' && !isAuthEndpoint && !isSessionCheck) {
        window.location.href = '/auth/login';
      }
    }
    return Promise.reject(error);
  }
);

const getApiOrigin = () => {
  try {
    return new URL(API_BASE_URL).origin;
  } catch {
    return API_BASE_URL.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
  }
};

type FastAPIErrorDetail =
  | string
  | {
      error?: string;
      message?: string;
      ticker?: string;
      model?: string;
      last_error?: string;
    };

type FastAPIErrorResponse = {
  detail?: FastAPIErrorDetail;
};

const getErrorDetail = (error: AxiosError<FastAPIErrorResponse>) => (
  typeof error.response?.data?.detail === 'string'
    ? error.response.data.detail
    : typeof error.response?.data?.detail === 'object'
      ? [
          error.response.data.detail.message,
          error.response.data.detail.error ? `Code: ${error.response.data.detail.error}` : undefined,
          error.response.data.detail.model ? `Model: ${error.response.data.detail.model}` : undefined,
          error.response.data.detail.last_error ? `Last error: ${error.response.data.detail.last_error}` : undefined,
        ].filter(Boolean).join(' | ')
    : undefined
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

    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  logout: async () => {
    await api.post('/auth/logout');
    if (typeof window !== 'undefined') window.location.href = '/auth/login';
  },
};

// ====================================
// BILLING API
// ====================================

export const billingAPI = {
  // `tier` is optional and defaults to Pro on the backend when omitted, keeping
  // older callers working. Pass 'trader' | 'elite' to check out those plans.
  createCheckoutSession: async (
    tier?: 'pro' | 'trader' | 'elite'
  ): Promise<{ url: string; id: string }> => {
    const response = await api.post<{ url: string; id: string }>(
      '/billing/create-checkout-session',
      tier ? { tier } : {}
    );
    return response.data;
  },

  createPortalSession: async (): Promise<{ url: string }> => {
    const response = await api.post<{ url: string }>(
      '/billing/create-portal-session'
    );
    return response.data;
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

  runBacktest: async (
    ticker: string,
    config: BacktestRunRequest
  ): Promise<BacktestRunResponse> => {
    const response = await api.post<BacktestRunResponse>(
      `/stocks/${ticker}/backtest`,
      config
    );
    return response.data;
  },

  runGlobalBacktest: async (
    config: BacktestRunRequest
  ): Promise<BacktestRunResponse> => {
    const response = await api.post<BacktestRunResponse>(
      '/backtests/run',
      config
    );
    return response.data;
  },

  runIndicatorBacktest: async (
    config: IndicatorBacktestRunRequest
  ): Promise<IndicatorBacktestRunResponse> => {
    const response = await api.post<IndicatorBacktestRunResponse>(
      '/backtests/indicator/run',
      config
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
// MARKET SCANNERS API (free, public -- no auth)
// ====================================

export const marketAPI = {
  getScans: async (): Promise<MarketScansResponse> => {
    const response = await api.get<MarketScansResponse>('/market/scans');
    return response.data;
  },

  getSectors: async (): Promise<MarketSectorsResponse> => {
    const response = await api.get<MarketSectorsResponse>('/market/sectors');
    return response.data;
  },

  getEarningsCalendar: async (days: number = 14): Promise<EarningsCalendarResponse> => {
    const response = await api.get<EarningsCalendarResponse>('/market/earnings', {
      params: { days },
    });
    return response.data;
  },

  getMacroDashboard: async (): Promise<MacroDashboardResponse> => {
    const response = await api.get<MacroDashboardResponse>('/market/macro');
    return response.data;
  },
};

// ====================================
// INSIDER ACTIVITY API (SEC EDGAR Form 4 - free/public)
// ====================================

export const insidersAPI = {
  getActivity: async (
    filters: InsiderActivityFilters
  ): Promise<InsiderActivityResponse> => {
    const response = await api.get<InsiderActivityResponse>('/market/insider-activity', {
      params: filters,
    });
    return response.data;
  },

  getForTicker: async (
    ticker: string,
    days: number = 90
  ): Promise<InsiderTickerResponse> => {
    const response = await api.get<InsiderTickerResponse>(
      `/market/insider-activity/${encodeURIComponent(ticker.trim().toUpperCase())}`,
      { params: { days } }
    );
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

// ====================================
// AI REPORTS API
// ====================================

export const generateAIReport = async (ticker: string): Promise<AIReportResponse> => {
  try {
    const response = await api.post<AIReportSuccessResponse>(
      `${getApiOrigin()}/api/ai-reports/${encodeURIComponent(ticker.trim().toUpperCase())}`
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError<FastAPIErrorResponse>(error)) {
      const detail = getErrorDetail(error);

      if (error.response?.status === 403) {
        return {
          error: 'not_pro',
          status: 403,
          message: detail ?? 'AI reports require a Pro account.',
          detail,
        };
      }

      if (error.response?.status === 429) {
        return {
          error: 'limit_exceeded',
          status: 429,
          message: detail ?? 'AI report limit exceeded.',
          detail,
        };
      }

      if (error.response?.status) {
        return {
          error: 'generation_failed',
          status: error.response.status,
          message: detail ?? 'Unable to generate the AI report.',
          detail,
        };
      }
    }

    throw error;
  }
};

// ====================================
// EMAIL PREFERENCES API
// ====================================

export const emailAPI = {
  getPreferences: async (): Promise<EmailPreferences> => {
    const response = await api.get<EmailPreferences>('/email/preferences');
    return response.data;
  },

  updatePreferences: async (
    update: EmailPreferencesUpdate
  ): Promise<EmailPreferences> => {
    const response = await api.put<EmailPreferences>('/email/preferences', update);
    return response.data;
  },
};

export default api;
