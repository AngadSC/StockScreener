'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Settings, Sparkles } from 'lucide-react';
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

const ALREADY_SUBSCRIBED_MESSAGE =
  'You already have an active subscription — use Manage billing to change plans.';

export function CheckoutButton({ tier, label, fallbackUrl }: Props) {
  const router = useRouter();
  const { isLoggedIn, isLoading } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Set when the backend rejects checkout with 409 because the account already
  // holds a live subscription. Plan changes belong in the Customer Portal, so the
  // button turns into the portal action instead of starting a second one.
  const [alreadySubscribed, setAlreadySubscribed] = useState(false);

  const usePro = tier === 'pro';
  const effectiveFallbackUrl = usePro ? fallbackUrl : undefined;

  const handleCheckout = async () => {
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
      const conflict = axios.isAxiosError(err) && err.response?.status === 409;
      const detail =
        axios.isAxiosError(err) && typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : conflict
            ? ALREADY_SUBSCRIBED_MESSAGE
            : 'Could not start checkout. Please try again.';
      setError(detail);
      setSubmitting(false);

      if (conflict) {
        // Deliberately skip the Payment Link fallback here: it would start the
        // second subscription the 409 exists to prevent.
        setAlreadySubscribed(true);
        return;
      }

      if (effectiveFallbackUrl) {
        window.location.href = effectiveFallbackUrl;
      }
    }
  };

  const handleManageBilling = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const { url } = await billingAPI.createPortalSession();
      window.location.href = url;
    } catch (err) {
      const detail =
        axios.isAxiosError(err) && typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : 'Could not open subscription management. Please try again.';
      setError(detail);
      setSubmitting(false);
    }
  };

  const disabled = submitting || isLoading;
  const busyLabel = alreadySubscribed ? 'Opening…' : 'Redirecting…';

  return (
    <div className="space-y-2">
      <Button
        onClick={alreadySubscribed ? handleManageBilling : handleCheckout}
        disabled={disabled}
        variant={alreadySubscribed ? 'outline' : 'default'}
        className="w-full rounded-full"
      >
        {alreadySubscribed ? <Settings className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
        {submitting ? busyLabel : alreadySubscribed ? 'Manage billing' : label}
      </Button>
      {error ? (
        <p className="text-xs text-[var(--negative)]">{error}</p>
      ) : null}
    </div>
  );
}
