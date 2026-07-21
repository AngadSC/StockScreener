// All account tiers. `PaidTier` covers the tiers that map to a Stripe checkout.
export type Tier = 'free' | 'pro' | 'trader' | 'elite';
export type PaidTier = Exclude<Tier, 'free'>;

export interface User {
  id: number;
  email: string;
  tier: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}
