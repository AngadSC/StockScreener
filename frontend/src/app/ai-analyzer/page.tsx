'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { Lock, Search, Sparkles } from 'lucide-react';

import AIReportCard from '@/components/ai/AIReportCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { isProTier, useAuth } from '@/lib/auth';

export default function AiAnalyzerPage() {
  const { isLoading, isLoggedIn, userTier } = useAuth();
  const [tickerInput, setTickerInput] = useState('');
  const [submittedTicker, setSubmittedTicker] = useState('');
  const canAnalyze = isLoggedIn && isProTier(userTier);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!canAnalyze) return;

    const ticker = tickerInput.trim().toUpperCase();
    if (ticker) setSubmittedTicker(ticker);
  };

  return (
    <div className="container-custom py-8 md:py-10">
      <div className="mx-auto max-w-4xl space-y-6">
        <section className="space-y-4">
          <div className="eyebrow">Pro Research</div>
          <h1 className="heading-xl text-[var(--text-primary)]">AI Swing Analyzer</h1>
          <p className="max-w-[56ch] text-sm leading-6 text-[var(--text-secondary)]">
            Generate a setup-focused swing report for a ticker using market context, news, and
            technical structure.
          </p>
        </section>

        <section className="deco-panel p-5 md:p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-secondary)]"
                aria-hidden="true"
              />
              <Input
                aria-label="Ticker symbol"
                className="pl-10 uppercase"
                disabled={isLoading || !canAnalyze}
                maxLength={12}
                onChange={(event) => setTickerInput(event.target.value)}
                placeholder="AAPL"
                value={tickerInput}
              />
            </div>
            <Button disabled={isLoading || !canAnalyze || !tickerInput.trim()} type="submit">
              <Sparkles className="h-4 w-4" />
              Analyze
            </Button>
          </form>
        </section>

        {isLoading ? (
          <section className="deco-panel p-6 text-sm text-[var(--text-secondary)]">
            Checking account access...
          </section>
        ) : null}

        {!isLoading && !isLoggedIn ? (
          <section className="deco-panel p-6 md:p-7">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="eyebrow">Account Required</div>
                <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Sign in to analyze</h2>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  AI Swing Analyzer is available after signing in.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/auth/login">Sign In</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/auth/register">Create Account</Link>
                </Button>
              </div>
            </div>
          </section>
        ) : null}

        {!isLoading && isLoggedIn && !isProTier(userTier) ? (
          <section className="deco-panel p-6 md:p-7">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div className="flex gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[var(--accent)]/25 bg-[var(--accent-subtle)]">
                  <Lock className="h-5 w-5 text-[var(--accent)]" />
                </div>
                <div>
                  <div className="eyebrow">Pro Access</div>
                  <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Upgrade to Pro</h2>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">
                    AI reports require a Pro, Trader, or Elite account tier.
                  </p>
                </div>
              </div>
              <Button asChild>
                <Link href="/contact">Upgrade to Pro</Link>
              </Button>
            </div>
          </section>
        ) : null}

        {canAnalyze && submittedTicker ? (
          <AIReportCard key={submittedTicker} ticker={submittedTicker} userTier={userTier} />
        ) : null}
      </div>
    </div>
  );
}
