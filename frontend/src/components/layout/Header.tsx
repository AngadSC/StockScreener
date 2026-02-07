'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { TrendingUp, Search, Star, LogIn, LogOut } from 'lucide-react';
import { screenerAPI } from '@/lib/api';
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
    setIsLoggedIn(!!localStorage.getItem('access_token'));
  }, []);

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
        const result = await screenerAPI.suggestStocks(trimmed, 8);
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
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.href = '/auth/login';
  };

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = searchQuery.trim();
    if (trimmed) {
      setSuggestOpen(false);
      router.push(`/screener?search=${encodeURIComponent(trimmed)}`);
    } else {
      setSuggestOpen(false);
      router.push('/screener');
    }
  };

  const handleSuggestionSelect = (ticker: string) => {
    setSearchQuery(ticker);
    setSuggestOpen(false);
    router.push(`/screener?search=${encodeURIComponent(ticker)}`);
  };

  const navItems = [
    { href: '/', label: 'Market', icon: TrendingUp },
    { href: '/screener', label: 'Screener', icon: Search },
    { href: '/watchlist', label: 'Watchlist', icon: Star },
  ];

  return (
    <header className="border-b border-border bg-card sticky top-0 z-50 backdrop-blur-sm bg-card/95">
      <div className="container-custom">
        <div className="flex h-16 items-center justify-between gap-4">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <TrendingUp className="h-6 w-6 text-primary" />
            <span className="text-xl font-semibold">StockScreener</span>
          </Link>

          <div className="flex flex-1 items-center justify-center gap-4">
            {/* Navigation */}
            <nav className="flex items-center gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                      isActive
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Global Search */}
            <form
              onSubmit={handleSearchSubmit}
              className="hidden sm:flex items-center gap-2 border border-border rounded-md bg-muted/20 px-3 py-1.5 relative"
            >
              <Search className="h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search ticker or name..."
                className="bg-transparent outline-none text-sm w-40 md:w-56 placeholder:text-muted-foreground"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                onFocus={() => {
                  if (suggestions.length > 0) {
                    setSuggestOpen(true);
                  }
                }}
                onBlur={() => {
                  setTimeout(() => setSuggestOpen(false), 150);
                }}
                aria-label="Search stocks"
              />

              {suggestOpen && (
                <div className="absolute left-0 right-0 top-full mt-2 terminal-border bg-card z-50">
                  <div className="px-3 py-2 text-[10px] text-muted-foreground border-b border-border">
                    {isSuggestLoading ? 'SEARCHING...' : 'SUGGESTED_STOCKS'}
                  </div>
                  <div className="max-h-64 overflow-auto">
                    {!isSuggestLoading && suggestions.length === 0 && (
                      <div className="px-3 py-2 text-xs text-muted-foreground">
                        NO_MATCHES_FOUND
                      </div>
                    )}
                    {suggestions.map((item) => (
                      <div
                        key={item.ticker}
                        className="px-3 py-2 text-xs hover:bg-primary/10 cursor-pointer flex items-center justify-between"
                        onMouseDown={(event) => {
                          event.preventDefault();
                          handleSuggestionSelect(item.ticker);
                        }}
                      >
                        <span className="font-mono text-primary">{item.ticker}</span>
                        <span className="text-muted-foreground truncate ml-3">
                          {item.name || 'N/A'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </form>
          </div>

          {/* Auth */}
          <div className="flex items-center gap-2">
            {isLoggedIn ? (
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            ) : (
              <>
                <Link
                  href="/auth/login"
                  className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <LogIn className="h-4 w-4" />
                  Login
                </Link>
                <Link
                  href="/auth/register"
                  className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors font-medium"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
