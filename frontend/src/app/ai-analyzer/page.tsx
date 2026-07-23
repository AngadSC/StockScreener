'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { Lock, Search, Sparkles } from 'lucide-react';

import AIReportCard from '@/components/ai/AIReportCard';
import { ManageSubscriptionButton } from '@/components/billing/ManageSubscriptionButton';
import { Button } from '@/components/ui/button';
import { screenerAPI } from '@/lib/api';
import { isProTier, useAuth } from '@/lib/auth';
import type { StockSuggestion } from '@/types/stock';

export default function AiAnalyzerPage() {
  const { isLoading, isLoggedIn, userTier } = useAuth();
  const [tickerInput, setTickerInput] = useState('');
  const [submittedTicker, setSubmittedTicker] = useState('');
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [isSuggestLoading, setIsSuggestLoading] = useState(false);
  const latestQueryRef = useRef(0);
  const canAnalyze = isLoggedIn && isProTier(userTier);

  useEffect(() => {
    const trimmed = tickerInput.trim();

    if (!trimmed || !canAnalyze) {
      setSuggestions([]);
      setSuggestOpen(false);
      return;
    }

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

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!canAnalyze) return;

    const ticker = tickerInput.trim().toUpperCase();
    if (ticker) {
      setSuggestOpen(false);
      setSubmittedTicker(ticker);
    }
  };

  const handleSuggestionSelect = (ticker: string) => {
    const normalizedTicker = ticker.trim().toUpperCase();
    setTickerInput(normalizedTicker);
    setSuggestOpen(false);
    if (canAnalyze) {
      setSubmittedTicker(normalizedTicker);
    }
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
                  onChange={(event) => setTickerInput(event.target.value)}
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
                <div className="icon-tile h-10 w-10">
                  <Lock className="h-5 w-5" strokeWidth={1.6} />
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
