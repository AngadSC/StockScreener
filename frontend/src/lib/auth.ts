'use client';

import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { usePathname } from 'next/navigation';

import { authAPI } from '@/lib/api';
import type { User } from '@/types/user';

type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';

interface AuthContextValue {
  user: User | null;
  userTier: string;
  isLoggedIn: boolean;
  isLoading: boolean;
  refreshUser: () => Promise<User | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const PRO_TIERS = new Set(['pro', 'trader', 'elite']);

export function isProTier(userTier: string) {
  return PRO_TIERS.has(userTier.trim().toLowerCase());
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  const refreshUser = useCallback(async () => {
    setStatus('loading');
    try {
      const currentUser = await authAPI.getCurrentUser();
      setUser(currentUser);
      setStatus('authenticated');
      return currentUser;
    } catch {
      setUser(null);
      setStatus('unauthenticated');
      return null;
    }
  }, []);

  useEffect(() => {
    void refreshUser();
  }, [pathname, refreshUser]);

  const logout = useCallback(async () => {
    setUser(null);
    setStatus('unauthenticated');
    await authAPI.logout();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      userTier: user?.tier ?? 'free',
      isLoggedIn: status === 'authenticated',
      isLoading: status === 'loading',
      refreshUser,
      logout,
    }),
    [logout, refreshUser, status, user]
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
}
