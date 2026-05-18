'use client';

import { useState } from 'react';
import { Settings } from 'lucide-react';
import axios from 'axios';

import { Button } from '@/components/ui/button';
import { billingAPI } from '@/lib/api';
import { isProTier } from '@/lib/auth';

interface Props {
  userTier: string;
}

export function ManageSubscriptionButton({ userTier }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isProTier(userTier)) return null;

  const handleClick = async () => {
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

  return (
    <div className="space-y-2">
      <Button
        onClick={handleClick}
        disabled={submitting}
        variant="outline"
        className="rounded-full"
      >
        <Settings className="h-4 w-4" />
        {submitting ? 'Opening…' : 'Manage subscription'}
      </Button>
      {error ? (
        <p className="text-xs text-[var(--negative)]">{error}</p>
      ) : null}
    </div>
  );
}
