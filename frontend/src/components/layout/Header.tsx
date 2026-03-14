'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { BarChart3, LogIn, LogOut, Search, Star, TrendingUp } from 'lucide-react';

import BrandMark from '@/components/layout/BrandMark';
import { Button } from '@/components/ui/button';
import { authAPI, screenerAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { StockSuggestion } from '@/types/stock';

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [isSuggestLoading, setIsSuggestLoading] = useState(false);
  const latestQueryRef = useRef(0);

  useEffect(() => {
    let mounted = true;

    const loadSession = async () => {
      try {
        await authAPI.getCurrentUser();
        if (mounted) setIsLoggedIn(true);
      } catch {
        if (mounted) setIsLoggedIn(false);
      }
    };

    loadSession();
    return () => {
      mounted = false;
    };
  }, [pathname]);

  useEffect(() => {
    const query = searchParams.get('search') || '';
    setSearchQuery(query);
  }, [searchParams]);

  useEffect(() => {
    const trimmed = searchQuery.trim();

    if (!trimmed) {
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
  }, [searchQuery]);

  const navItems = [
    { href: '/', label: 'Market', icon: TrendingUp },
    { href: '/screener', label: 'Screener', icon: Search },
    { href: '/backtester', label: 'Backtester', icon: BarChart3 },
    { href: '/watchlist', label: 'Watchlist', icon: Star },
  ];

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = searchQuery.trim();
    setSuggestOpen(false);
    router.push(trimmed ? `/screener?search=${encodeURIComponent(trimmed)}` : '/screener');
  };

  const handleSuggestionSelect = (ticker: string) => {
    setSearchQuery(ticker);
    setSuggestOpen(false);
    router.push(`/stocks/${ticker}`);
  };

  const handleLogout = async () => {
    try {
      await authAPI.logout();
      setIsLoggedIn(false);
    } catch {
      window.location.href = '/auth/login';
    }
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/90 backdrop-blur-xl">
      <div className="container-custom">
        <div className="flex min-h-20 items-center justify-between gap-6 py-4">
          <Link href="/" className="group flex items-center gap-4">
            <BrandMark className="transition-transform duration-300 group-hover:scale-[1.03]" />
            <div className="text-xl font-semibold text-foreground">QuantorSignal</div>
          </Link>

          <div className="hidden min-w-0 flex-1 items-center justify-center gap-6 xl:flex">
            <nav className="flex items-center gap-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      'inline-flex items-center gap-2 rounded-md border px-4 py-3 text-sm font-medium transition-[background,border-color,box-shadow,color,transform] duration-[180ms]',
                      isActive
                        ? 'border-primary/40 bg-[var(--accent-subtle)] text-primary shadow-[var(--glow-accent)]'
                        : 'border-transparent text-muted-foreground hover:border-border hover:bg-muted/40 hover:text-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <form
              onSubmit={handleSearchSubmit}
              className="relative w-full max-w-md rounded-lg border border-border/70 bg-card px-4 py-3 shadow-sm"
            >
              <div className="flex items-center gap-3">
                <Search className="h-4 w-4 text-primary" />
                <input
                  type="text"
                  placeholder="Search ticker or company"
                  className="w-full border-none bg-transparent p-0 text-sm text-foreground shadow-none outline-none placeholder:text-muted-foreground focus:border-none focus:shadow-none"
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  onFocus={() => {
                    if (suggestions.length > 0) setSuggestOpen(true);
                  }}
                  onBlur={() => {
                    setTimeout(() => setSuggestOpen(false), 150);
                  }}
                  aria-label="Search stocks"
                />
              </div>

              {suggestOpen ? (
                <div className="deco-panel absolute left-0 right-0 top-[calc(100%+0.75rem)] z-50 p-2">
                  <div className="border-b border-border/70 px-3 py-2 text-xs text-muted-foreground">
                    {isSuggestLoading ? 'Searching' : 'Quick matches'}
                  </div>
                  <div className="deco-scroll max-h-64 overflow-auto py-1">
                    {!isSuggestLoading && suggestions.length === 0 ? (
                      <div className="px-3 py-3 text-sm text-muted-foreground">No matches found.</div>
                    ) : null}
                    {suggestions.map((item) => (
                      <div
                        key={item.ticker}
                        className="flex cursor-pointer items-center justify-between rounded-md px-3 py-3 transition-[background,border-color,box-shadow,color,transform] duration-[180ms] hover:bg-[var(--accent-subtle)]"
                        onMouseDown={(event) => {
                          event.preventDefault();
                          handleSuggestionSelect(item.ticker);
                        }}
                      >
                        <div>
                          <div className="text-base font-semibold text-primary">{item.ticker}</div>
                          <div className="text-sm text-muted-foreground">
                            {item.name || 'Company profile'}
                          </div>
                        </div>
                        <div className="text-xs text-primary">Open</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </form>
          </div>

          <div className="flex items-center gap-3">
            {isLoggedIn ? (
              <Button variant="ghost" onClick={handleLogout}>
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            ) : (
              <>
                <Link href="/auth/login" className="hidden md:block">
                  <Button variant="ghost">
                    <LogIn className="h-4 w-4" />
                    Sign In
                  </Button>
                </Link>
                <Link href="/auth/register">
                  <Button>Create Account</Button>
                </Link>
              </>
            )}
          </div>
        </div>

        <div className="grid gap-3 border-t border-border/70 py-3 xl:hidden">
          <form
            onSubmit={handleSearchSubmit}
            className="flex items-center gap-3 rounded-lg border border-border/70 bg-card px-4 py-3"
          >
            <Search className="h-4 w-4 text-primary" />
            <input
              type="text"
              placeholder="Search ticker or company"
              className="w-full border-none bg-transparent p-0 text-sm text-foreground shadow-none outline-none placeholder:text-muted-foreground focus:border-none focus:shadow-none"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
            />
          </form>
          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'inline-flex items-center gap-2 rounded-md border px-3 py-2 text-xs font-medium',
                    isActive
                      ? 'border-primary/40 bg-[var(--accent-subtle)] text-primary'
                      : 'border-border/70 text-muted-foreground'
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
