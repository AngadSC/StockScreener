'use client';

import { Suspense, useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Loader2, Lock, Search, Sparkles } from 'lucide-react';

import AIReportCard from '@/components/ai/AIReportCard';
import { ManageSubscriptionButton } from '@/components/billing/ManageSubscriptionButton';
import { Button } from '@/components/ui/button';
import { screenerAPI } from '@/lib/api';
import { isProTier, useAuth } from '@/lib/auth';
import type { StockSuggestion } from '@/types/stock';

// Stripe returns from checkout before the webhook has flipped the tier, so poll
// the session for a short window instead of leaving the buyer on the paywall.
const ACTIVATION_POLL_INTERVAL_MS = 3000;
const ACTIVATION_TIMEOUT_MS = 18000;

function AiAnalyzerPageContent() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoading, isLoggedIn, refreshUser, userTier } = useAuth();
  const [tickerInput, setTickerInput] = useState('');
  const [submittedTicker, setSubmittedTicker] = useState('');
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [isSuggestLoading, setIsSuggestLoading] = useState(false);
  const [activationPending, setActivationPending] = useState(false);
  const [activationTimedOut, setActivationTimedOut] = useState(false);
  const latestQueryRef = useRef(0);
  // Ticker the user already acted on (submit or suggestion click). Stops the
  // debounced suggest effect from firing again for that exact value.
  const committedTickerRef = useRef<string | null>(null);
  const canAnalyze = isLoggedIn && isProTier(userTier);
  const checkoutSucceeded = searchParams.get('checkout') === 'success';
  const isActivating = activationPending && !canAnalyze;

  // Latch the post-checkout redirect, then strip the query param so a reload
  // does not restart the wait.
  useEffect(() => {
    if (!checkoutSucceeded) return;
    setActivationPending(true);
    setActivationTimedOut(false);
    router.replace(pathname, { scroll: false });
  }, [checkoutSucceeded, pathname, router]);

  useEffect(() => {
    if (!activationPending) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const deadline = Date.now() + ACTIVATION_TIMEOUT_MS;

    const poll = async () => {
      const currentUser = await refreshUser();
      if (cancelled) return;

      if (currentUser && isProTier(currentUser.tier)) {
        setActivationPending(false);
        return;
      }
      if (Date.now() >= deadline) {
        setActivationPending(false);
        setActivationTimedOut(true);
        return;
      }
      timer = setTimeout(() => void poll(), ACTIVATION_POLL_INTERVAL_MS);
    };

    void poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [activationPending, refreshUser]);

  useEffect(() => {
    const trimmed = tickerInput.trim();

    if (!trimmed || !canAnalyze) {
      setSuggestions([]);
      setSuggestOpen(false);
      return;
    }

    // The value came from a suggestion click or a submit — the report is already
    // rendering, so do not fetch matches that would reopen the dropdown over it.
    if (committedTickerRef.current === trimmed.toUpperCase()) return;

    const requestId = ++latestQueryRef.current;
    const timer = setTimeout(async () => {
      setIsSuggestLoading(true);
      try {
        const result = await screenerAPI.suggestStocks(trimmed, 6);
        if (requestId !== latestQueryRef.current) return;
        setSuggestions(result.results);
        setSuggestOpen(true);
      } catch {
        if (requestId !== latestQueryRef.current) return;
        setSuggestions([]);
        setSuggestOpen(false);
      } finally {
        if (requestId === latestQueryRef.current) {
          setIsSuggestLoading(false);
        }
      }
    }, 220);

    return () => clearTimeout(timer);
  }, [canAnalyze, tickerInput]);

  const commitTicker = (ticker: string) => {
    const normalizedTicker = ticker.trim().toUpperCase();
    if (!normalizedTicker) return;

    // Invalidate the in-flight suggest request before closing the dropdown so a
    // late response cannot reopen it on top of the report.
    latestQueryRef.current += 1;
    committedTickerRef.current = normalizedTicker;
    setIsSuggestLoading(false);
    setSuggestOpen(false);
    setTickerInput(normalizedTicker);
    if (canAnalyze) {
      setSubmittedTicker(normalizedTicker);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!canAnalyze) return;

    commitTicker(tickerInput);
  };

  const handleSuggestionSelect = (ticker: string) => {
    commitTicker(ticker);
  };

  return (
    <div className="container-custom py-8 md:py-10">
      <div className="mx-auto max-w-5xl space-y-7">
        <section className="flex flex-col gap-4 border-b border-t border-[var(--line)] py-7 md:flex-row md:items-start md:justify-between">
          <div className="space-y-4">
            <div className="live-dot">AI research desk</div>
            <h1 className="heading-xl text-[var(--text-primary)]">AI Analyst</h1>
            <p className="max-w-[56ch] text-sm leading-6 text-[var(--text-secondary)]">
              Ask for a setup-focused thesis using market context, news, fundamentals, and technical
              structure.
            </p>
          </div>
          <ManageSubscriptionButton userTier={userTier} />
        </section>

        <section className="glass hud hud-blue p-5 md:p-6">
          <span className="hud-c1" />
          <span className="hud-c2" />
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <div className="flex h-12 items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--surface)] px-4 text-sm shadow-[var(--shadow-1)] transition-[border-color,box-shadow] duration-300 ease-out focus-within:border-[var(--sapphire)] focus-within:shadow-[0_0_0_3px_var(--sapphire-soft),var(--shadow-1)]">
                <Search className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" aria-hidden="true" />
                <input
                  aria-label="Ticker symbol"
                  autoComplete="off"
                  className="w-full border-none bg-transparent p-0 text-sm font-semibold uppercase text-[var(--text-primary)] shadow-none outline-none placeholder:font-normal placeholder:normal-case placeholder:text-[var(--text-secondary)] focus:border-none focus:shadow-none"
                  disabled={isLoading || !canAnalyze}
                  maxLength={12}
                  onBlur={() => {
                    setTimeout(() => setSuggestOpen(false), 150);
                  }}
                  onChange={(event) => {
                    committedTickerRef.current = null;
                    setTickerInput(event.target.value);
                  }}
                  onFocus={() => {
                    if (suggestions.length > 0) setSuggestOpen(true);
                  }}
                  placeholder="Ask for a ticker thesis or company brief"
                  type="text"
                  value={tickerInput}
                />
              </div>
              {suggestOpen ? (
                <div className="absolute left-0 right-0 top-[calc(100%+0.75rem)] z-30 overflow-hidden rounded-[20px] border border-[var(--border-default)] bg-[var(--bg-surface-1)] shadow-[var(--shadow-lg)]">
                  <div className="border-b border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)]">
                    {isSuggestLoading ? 'Searching' : 'Quick matches'}
                  </div>
                  <div className="deco-scroll max-h-64 overflow-auto py-1">
                    {!isSuggestLoading && suggestions.length === 0 ? (
                      <div className="px-4 py-3 text-sm text-[var(--text-secondary)]">
                        No matches found.
                      </div>
                    ) : null}
                    {suggestions.map((item) => (
                      <div
                        key={item.ticker}
                        className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 transition-colors duration-[180ms] hover:bg-[var(--bg-surface-2)]"
                        onMouseDown={(event) => {
                          event.preventDefault();
                          handleSuggestionSelect(item.ticker);
                        }}
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-[var(--text-primary)]">
                            {item.ticker}
                          </div>
                          <div
                            className="truncate text-sm text-[var(--text-secondary)]"
                            title={item.name || 'Company profile'}
                          >
                            {item.name || 'Company profile'}
                          </div>
                        </div>
                        <div className="text-xs font-medium text-[var(--accent)]">Analyze</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
            <Button
              className="h-12 rounded-full px-6"
              disabled={isLoading || !canAnalyze || !tickerInput.trim()}
              type="submit"
            >
              <Sparkles className="h-4 w-4" />
              Analyze
            </Button>
          </form>
          <div className="mt-4 flex flex-wrap gap-2">
            {['Find a bullish thesis', 'Compare semiconductors', 'Screen resilient dividends'].map((suggestion) => (
              <button key={suggestion} type="button" className="chip suggest-chip italic">
                {suggestion}
              </button>
            ))}
          </div>
          {!submittedTicker ? (
            <p className="mt-4 max-w-[70ch] text-xs leading-5 text-[var(--text-secondary)]">
              Each report covers the setup and trend, key support and resistance levels, recent
              catalysts, and a plain-English thesis. Uses one of your monthly reports.
            </p>
          ) : null}
        </section>

        {isActivating ? (
          <section className="deco-panel p-6 md:p-7">
            <div className="flex gap-4">
              <div className="icon-tile h-10 w-10">
                <Loader2 className="h-5 w-5 animate-spin" strokeWidth={1.6} />
              </div>
              <div>
                <div className="eyebrow">Payment received</div>
                <h2 className="heading-lg mt-2 text-[var(--text-primary)]">
                  Activating your subscription...
                </h2>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">
                  Stripe is confirming the payment with our servers. This usually takes a few
                  seconds and the AI Analyst unlocks automatically.
                </p>
              </div>
            </div>
          </section>
        ) : null}

        {!isActivating && isLoading ? (
          <section className="deco-panel p-6 text-sm text-[var(--text-secondary)]">
            Checking account access...
          </section>
        ) : null}

        {!isActivating && !isLoading && !isLoggedIn ? (
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

        {!isActivating && !isLoading && isLoggedIn && !isProTier(userTier) ? (
          <section className="deco-panel p-6 md:p-7">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div className="flex gap-4">
                <div className="icon-tile h-10 w-10">
                  <Lock className="h-5 w-5" strokeWidth={1.6} />
                </div>
                <div>
                  <div className="eyebrow">Pro Access</div>
                  <h2 className="heading-lg mt-2 text-[var(--text-primary)]">Upgrade to Pro</h2>
                  <p className="mt-2 text-sm text-[var(--text-secondary)]">
                    AI reports require a Pro, Trader, or Elite account tier.
                  </p>
                  {activationTimedOut ? (
                    <p className="mt-2 text-sm text-[var(--text-secondary)]">
                      Just paid? Your payment is still processing. Refresh this page in a moment —
                      access unlocks as soon as Stripe confirms it.
                    </p>
                  ) : null}
                </div>
              </div>
              <Button asChild>
                <Link href="/pricing?feature=ai-analyzer">Upgrade to Pro</Link>
              </Button>
            </div>
          </section>
        ) : null}

        {canAnalyze && submittedTicker ? (
          <div className="card-ivory p-1">
            <AIReportCard key={submittedTicker} ticker={submittedTicker} userTier={userTier} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function AiAnalyzerPage() {
  return (
    <Suspense fallback={<div className="container-custom py-8" />}>
      <AiAnalyzerPageContent />
    </Suspense>
  );
}
