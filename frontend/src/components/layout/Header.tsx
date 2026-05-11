'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import {
  BarChart3,
  BookOpen,
  Lock,
  LogIn,
  LogOut,
  Menu,
  Search,
  Sparkles,
  Star,
  TrendingUp,
  X,
  type LucideIcon,
} from 'lucide-react';

import BrandMark from '@/components/layout/BrandMark';
import { Button } from '@/components/ui/button';
import { authAPI, screenerAPI } from '@/lib/api';
import { isProTier } from '@/lib/auth';
import { cn } from '@/lib/utils';
import type { StockSuggestion } from '@/types/stock';

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  requiresAuth?: boolean;
  proBadge?: boolean;
};

const navItems: NavItem[] = [
  { href: '/', label: 'Market', icon: TrendingUp },
  { href: '/screener', label: 'Screener', icon: Search },
  { href: '/ai-analyzer', label: 'AI Analyzer', icon: Sparkles, proBadge: true },
  { href: '/backtester', label: 'Backtester', icon: BarChart3 },
  { href: '/watchlist', label: 'Watchlist', icon: Star, requiresAuth: true },
  { href: '/blog', label: 'Blog', icon: BookOpen },
];

function isNavItemActive(pathname: string, href: string) {
  return pathname === href || (href !== '/' && pathname.startsWith(href));
}

export default function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userTier, setUserTier] = useState<string | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [isSuggestLoading, setIsSuggestLoading] = useState(false);
  const latestQueryRef = useRef(0);

  useEffect(() => {
    let mounted = true;

    const loadSession = async () => {
      try {
        const user = await authAPI.getCurrentUser();
        if (mounted) {
          setIsLoggedIn(true);
          setUserTier(user.tier ?? 'free');
        }
      } catch {
        if (mounted) {
          setIsLoggedIn(false);
          setUserTier('free');
        }
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
    setIsMobileMenuOpen(false);
    setSuggestOpen(false);
  }, [pathname]);

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

  const closeSearchOverlays = () => {
    setSuggestOpen(false);
    setIsMobileMenuOpen(false);
  };

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = searchQuery.trim();
    closeSearchOverlays();
    router.push(trimmed ? `/screener?search=${encodeURIComponent(trimmed)}` : '/screener');
  };

  const handleSuggestionSelect = (ticker: string) => {
    setSearchQuery(ticker);
    closeSearchOverlays();
    router.push(`/stocks/${ticker}`);
  };

  const handleLogout = async () => {
    try {
      setIsMobileMenuOpen(false);
      await authAPI.logout();
      setIsLoggedIn(false);
      setUserTier('free');
    } catch {
      window.location.href = '/auth/login';
    }
  };

  const renderNavAffordance = (item: NavItem, mobile = false) => {
    const showLock = Boolean(item.requiresAuth && !isLoggedIn);

    return (
      <>
        <span>{item.label}</span>
        {item.proBadge ? (
          <span className="rounded-full border border-[var(--accent)]/30 bg-[var(--accent-subtle)] px-1.5 py-0.5 text-[10px] font-semibold uppercase leading-none text-[var(--accent)]">
            Pro
          </span>
        ) : null}
        {showLock ? <Lock className="h-3 w-3 shrink-0" aria-hidden="true" /> : null}
        {showLock && !mobile ? (
          <span
            role="tooltip"
            className="pointer-events-none absolute left-1/2 top-[calc(100%+0.75rem)] z-20 w-max max-w-[220px] -translate-x-1/2 translate-y-1 rounded-full border border-[var(--border-default)] bg-[rgba(8,8,14,0.96)] px-3 py-1.5 text-[11px] font-medium text-[var(--text-primary)] opacity-0 shadow-[var(--shadow-md)] transition-[opacity,transform] duration-180 group-hover/watchlist:translate-y-0 group-hover/watchlist:opacity-100"
          >
            Sign in to access your Watchlist
          </span>
        ) : null}
      </>
    );
  };

  const renderNavLink = (item: NavItem, mobile = false) => {
    const Icon = item.icon;
    const isActive = isNavItemActive(pathname, item.href);
    const showLock = Boolean(item.requiresAuth && !isLoggedIn);
    const routeToPricing = Boolean(item.proBadge && userTier && !isProTier(userTier));
    const href = routeToPricing ? `/pricing?feature=${encodeURIComponent(item.href.replace('/', ''))}` : item.href;

    return (
      <Link
        key={`${mobile ? 'mobile' : 'desktop'}-${item.href}`}
        href={href}
        data-active={mobile ? undefined : String(isActive)}
        title={showLock ? 'Sign in to access your Watchlist' : undefined}
        onClick={() => setIsMobileMenuOpen(false)}
        className={cn(
          mobile
            ? 'flex items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-sm font-medium transition-[background,border-color,color] duration-[180ms]'
            : 'qs-nav-link relative inline-flex h-full items-center gap-2 px-4 text-sm font-medium',
          mobile &&
            (isActive
              ? 'border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent)]'
              : 'border-[var(--border-default)] bg-transparent text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)]'),
          showLock && !mobile && 'group/watchlist'
        )}
      >
        <span className="inline-flex items-center gap-2">
          <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span className="relative inline-flex items-center gap-1.5">
            {renderNavAffordance(item, mobile)}
          </span>
        </span>
      </Link>
    );
  };

  const renderSearchForm = (mobile = false) => (
    <div
      className={cn(
        'relative',
        mobile
          ? 'w-full'
          : 'hidden w-[160px] shrink-0 transition-[width] duration-300 ease-out focus-within:w-[280px] lg:block'
      )}
    >
      <form
        onSubmit={handleSearchSubmit}
        className="flex h-10 items-center gap-2 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-2)] px-3.5 text-sm transition-[border-color,width] duration-300 ease-out focus-within:border-[var(--accent)]"
      >
        <Search className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" aria-hidden="true" />
        <input
          type="text"
          placeholder="Search"
          className="w-full border-none bg-transparent p-0 text-sm text-[var(--text-primary)] shadow-none outline-none placeholder:text-[var(--text-secondary)] focus:border-none focus:shadow-none"
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
      </form>

      {suggestOpen ? (
        <div className="absolute left-0 right-0 top-[calc(100%+0.75rem)] z-[110] overflow-hidden rounded-[20px] border border-[var(--border-default)] bg-[var(--bg-surface-1)] shadow-[var(--shadow-lg)]">
          <div className="border-b border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)]">
            {isSuggestLoading ? 'Searching' : 'Quick matches'}
          </div>
          <div className="deco-scroll max-h-64 overflow-auto py-1">
            {!isSuggestLoading && suggestions.length === 0 ? (
              <div className="px-4 py-3 text-sm text-[var(--text-secondary)]">No matches found.</div>
            ) : null}
            {suggestions.map((item) => (
              <div
                key={item.ticker}
                className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 transition-colors duration-[180ms] hover:bg-[var(--accent-subtle)]"
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSuggestionSelect(item.ticker);
                }}
              >
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-[var(--text-primary)]">
                    {item.ticker}
                  </div>
                  <div className="truncate text-sm text-[var(--text-secondary)]">
                    {item.name || 'Company profile'}
                  </div>
                </div>
                <div className="text-xs font-medium text-[var(--accent)]">Open</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );

  return (
    <header className="sticky top-0 z-[100] border-b border-[var(--border-subtle)] bg-[rgba(8,8,14,0.85)] backdrop-blur-[12px]">
      <div className="container-custom">
        <div className="flex min-h-[76px] items-center gap-4">
          <Link href="/" className="group flex shrink-0 items-center gap-3 py-3">
            <BrandMark className="transition-transform duration-300 group-hover:scale-[1.03]" />
            <div className="text-lg font-semibold tracking-[-0.01em] text-[var(--text-primary)] md:text-xl">
              QuantorSignal
            </div>
          </Link>

          <nav className="hidden flex-1 items-stretch justify-center lg:flex">
            {navItems.map((item) => renderNavLink(item))}
          </nav>

          <div className="ml-auto hidden items-center gap-4 border-l border-[var(--border-subtle)] pl-5 lg:flex">
            {renderSearchForm()}

            <div className="flex items-center gap-2 border-l border-[var(--border-subtle)] pl-4">
              {isLoggedIn ? (
                <Button variant="ghost" className="h-10 rounded-full px-4" onClick={handleLogout}>
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </Button>
              ) : (
                <>
                  <Button asChild variant="ghost" className="h-10 rounded-full px-4">
                    <Link href="/auth/login">
                      <LogIn className="h-4 w-4" />
                      Login
                    </Link>
                  </Button>
                  <Button asChild className="h-10 rounded-full px-4">
                    <Link href="/auth/register">Join Free</Link>
                  </Button>
                </>
              )}
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            className="ml-auto rounded-full lg:hidden"
            aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setIsMobileMenuOpen((open) => !open)}
          >
            {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>

        {isMobileMenuOpen ? (
          <div
            id="mobile-navigation"
            className="grid gap-4 border-t border-[var(--border-subtle)] py-4 lg:hidden"
          >
            {renderSearchForm(true)}

            <nav className="grid gap-2">{navItems.map((item) => renderNavLink(item, true))}</nav>

            <div className="grid gap-2 pt-1">
              {isLoggedIn ? (
                <Button variant="ghost" className="w-full justify-center rounded-full" onClick={handleLogout}>
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </Button>
              ) : (
                <>
                  <Button asChild variant="ghost" className="w-full justify-center rounded-full">
                    <Link href="/auth/login">
                      <LogIn className="h-4 w-4" />
                      Login
                    </Link>
                  </Button>
                  <Button asChild className="w-full justify-center rounded-full">
                    <Link href="/auth/register">Join Free</Link>
                  </Button>
                </>
              )}
            </div>
          </div>
        ) : null}
      </div>

      <style jsx>{`
        .qs-nav-link {
          color: var(--text-secondary);
          transition: color 180ms ease;
        }

        .qs-nav-link::after {
          content: '';
          position: absolute;
          left: 0;
          bottom: 0;
          height: 2px;
          width: 0;
          background: var(--accent);
          transition: width 200ms ease;
        }

        .qs-nav-link:hover {
          color: var(--text-primary);
        }

        .qs-nav-link:hover::after {
          width: 100%;
        }

        .qs-nav-link[data-active='true'] {
          color: var(--accent);
        }

        .qs-nav-link[data-active='true']::after {
          width: 100%;
          animation: qs-nav-sweep 300ms ease forwards;
        }

        @keyframes qs-nav-sweep {
          from {
            width: 0;
          }

          to {
            width: 100%;
          }
        }
      `}</style>
    </header>
  );
}
