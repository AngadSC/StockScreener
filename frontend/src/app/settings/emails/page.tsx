'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Mail } from 'lucide-react';

import { Card } from '@/components/ui/card';
import EmailPreferenceRow, {
  type EmailPreferenceRowConfig,
} from '@/components/settings/EmailPreferenceRow';
import { emailAPI } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { EmailPreferenceKey, EmailPreferences, EmailPreferencesUpdate } from '@/types/email';

const QUERY_KEY = ['email-preferences'] as const;

const TIER_RANK: Record<string, number> = { free: 0, pro: 1, trader: 2, elite: 3 };

function meetsTier(userTier: string, required?: 'trader' | 'elite'): boolean {
  if (!required) return true;
  const rank = TIER_RANK[userTier.trim().toLowerCase()] ?? 0;
  return rank >= TIER_RANK[required];
}

const PREFERENCE_ROWS: EmailPreferenceRowConfig[] = [
  {
    key: 'daily_brief',
    title: 'Daily Market Brief',
    description: 'An AI-written morning market summary, delivered before the open.',
    badge: 'Trader+',
    requiredTier: 'trader',
  },
  {
    key: 'watchlist_digest',
    title: 'Watchlist AI Digest',
    description: 'Pre-market AI analysis of your watchlist stocks, ranked and delivered daily.',
    badge: 'Elite',
    requiredTier: 'elite',
  },
  {
    key: 'weekly_recap',
    title: 'Weekly Recap',
    description: "A Sunday review of the week's market action.",
    badge: 'Coming soon',
  },
  {
    key: 'product_updates',
    title: 'Product updates',
    description: 'Occasional news about new QuantorSignal features.',
  },
];

export default function EmailPreferencesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isLoading: authLoading, isLoggedIn, userTier } = useAuth();

  useEffect(() => {
    if (!authLoading && !isLoggedIn) {
      router.replace('/auth/login?redirect=/settings/emails');
    }
  }, [authLoading, isLoggedIn, router]);

  const { data, isLoading, isError } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: emailAPI.getPreferences,
    enabled: isLoggedIn,
  });

  const [pendingKey, setPendingKey] = useState<EmailPreferenceKey | null>(null);
  const [savedKey, setSavedKey] = useState<EmailPreferenceKey | null>(null);
  const [errorState, setErrorState] = useState<{ key: EmailPreferenceKey; message: string } | null>(
    null
  );
  const savedTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (savedTimeoutRef.current) clearTimeout(savedTimeoutRef.current);
    };
  }, []);

  const mutation = useMutation({
    mutationFn: (update: EmailPreferencesUpdate) => emailAPI.updatePreferences(update),
    onMutate: async (update) => {
      const [key] = Object.keys(update) as EmailPreferenceKey[];
      setErrorState(null);
      setPendingKey(key);

      await queryClient.cancelQueries({ queryKey: QUERY_KEY });
      const previous = queryClient.getQueryData<EmailPreferences>(QUERY_KEY);
      if (previous) {
        queryClient.setQueryData<EmailPreferences>(QUERY_KEY, { ...previous, ...update });
      }
      return { previous, key };
    },
    onError: (_err, _update, context) => {
      if (context?.previous) {
        queryClient.setQueryData(QUERY_KEY, context.previous);
      }
      if (context?.key) {
        setErrorState({ key: context.key, message: 'Could not save. Try again.' });
      }
    },
    onSuccess: (result, _update, context) => {
      queryClient.setQueryData(QUERY_KEY, result);
      if (context?.key) {
        setSavedKey(context.key);
        if (savedTimeoutRef.current) clearTimeout(savedTimeoutRef.current);
        savedTimeoutRef.current = setTimeout(() => setSavedKey(null), 2000);
      }
    },
    onSettled: () => {
      setPendingKey(null);
    },
  });

  const handleToggle = (key: EmailPreferenceKey, next: boolean) => {
    const update: EmailPreferencesUpdate = { [key]: next };
    mutation.mutate(update);
  };

  const showLoadingState = authLoading || (isLoggedIn && isLoading);

  return (
    <div className="container-custom py-8 md:py-10">
      <div className="mx-auto max-w-3xl space-y-7">
        <section className="flex flex-col gap-4 border-b border-t border-[var(--line)] py-7">
          <div className="eyebrow flex items-center gap-2">
            <Mail className="h-3.5 w-3.5" aria-hidden="true" strokeWidth={1.6} />
            Account
          </div>
          <h1 className="heading-xl text-[var(--text-primary)]">Email preferences</h1>
          <p className="max-w-[56ch] text-sm leading-6 text-[var(--text-secondary)]">
            Choose which emails QuantorSignal sends you. Preferences save automatically and take
            effect on the next scheduled send.
          </p>
        </section>

        {showLoadingState ? (
          <Card className="p-8 text-center">
            <Loader2
              className="mx-auto mb-3 h-6 w-6 animate-spin text-[var(--text-tertiary)]"
              aria-hidden="true"
            />
            <p className="text-sm text-[var(--text-secondary)]">Loading preferences...</p>
          </Card>
        ) : null}

        {!authLoading && !isLoggedIn ? (
          <Card className="p-6 md:p-7">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="eyebrow">Account required</div>
                <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Sign in to continue</h2>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  Redirecting you to sign in...
                </p>
              </div>
              <Link href="/auth/login?redirect=/settings/emails" className="deco-link text-sm font-medium">
                Go to sign in
              </Link>
            </div>
          </Card>
        ) : null}

        {isLoggedIn && !isLoading && isError ? (
          <Card className="p-6 md:p-7">
            <p className="text-sm text-[var(--text-secondary)]">
              Could not load your email preferences. Please refresh and try again.
            </p>
          </Card>
        ) : null}

        {isLoggedIn && !isLoading && !isError && data ? (
          <Card className="p-5 md:p-6">
            <div>
              {PREFERENCE_ROWS.map((row) => (
                <EmailPreferenceRow
                  key={row.key}
                  config={row}
                  checked={data[row.key]}
                  locked={!meetsTier(userTier, row.requiredTier)}
                  pending={pendingKey === row.key}
                  saved={savedKey === row.key}
                  errorMessage={errorState?.key === row.key ? errorState.message : null}
                  onToggle={(next) => handleToggle(row.key, next)}
                />
              ))}
            </div>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
