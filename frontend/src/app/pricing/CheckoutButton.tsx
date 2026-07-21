'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import axios from 'axios';

import { Button } from '@/components/ui/button';
import { billingAPI } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import type { PaidTier } from '@/types/user';

interface Props {
  tier: PaidTier;
  label: string;
  // Fallback checkout URL used only for the Pro plan when the API call fails
  // (e.g. a signed-out visitor hitting a Stripe Payment Link).
  fallbackUrl?: string;
}

export function CheckoutButton({ tier, label, fallbackUrl }: Props) {
  const router = useRouter();
  const { isLoggedIn, isLoading } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usePro = tier === 'pro';
  const effectiveFallbackUrl = usePro ? fallbackUrl : undefined;

  const handleClick = async () => {
    setError(null);

    if (!isLoggedIn) {
      router.push('/auth/login?redirect=/pricing');
      return;
    }

    setSubmitting(true);
    try {
      const { url } = await billingAPI.createCheckoutSession(tier);
      window.location.href = url;
    } catch (err) {
      const detail =
        axios.isAxiosError(err) && typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : 'Could not start checkout. Please try again.';
      setError(detail);
      setSubmitting(false);

      if (effectiveFallbackUrl) {
        window.location.href = effectiveFallbackUrl;
      }
    }
  };

  const disabled = submitting || isLoading;

  return (
    <div className="space-y-2">
      <Button
        onClick={handleClick}
        disabled={disabled}
        className="w-full rounded-full"
      >
        <Sparkles className="h-4 w-4" />
        {submitting ? 'Redirecting…' : label}
      </Button>
      {error ? (
        <p className="text-xs text-[var(--negative)]">{error}</p>
      ) : null}
    </div>
  );
}
