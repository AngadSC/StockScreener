'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import {
  Activity,
  BarChart3,
  BookOpen,
  CalendarDays,
  GitCompareArrows,
  Home,
  Landmark,
  Lock,
  LogIn,
  LogOut,
  Mail,
  Menu,
  Search,
  Sparkles,
  Star,
  Tag,
  Users,
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

type NavGroup = {
  label?: string;
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    items: [{ href: '/', label: 'Home', icon: Home }],
  },
  {
    label: 'Markets',
    items: [
      { href: '/markets', label: 'Scanners', icon: Activity },
      { href: '/earnings', label: 'Earnings', icon: CalendarDays },
      { href: '/insiders', label: 'Insiders', icon: Users },
      { href: '/macro', label: 'Macro', icon: Landmark },
    ],
  },
  {
    label: 'Tools',
    items: [
      { href: '/screener', label: 'Screener', icon: Search },
      { href: '/compare', label: 'Compare', icon: GitCompareArrows },
      { href: '/backtester', label: 'Backtester', icon: BarChart3 },
      { href: '/ai-analyzer', label: 'AI Analyst', icon: Sparkles, proBadge: true },
    ],
  },
  {
    label: 'Account',
    items: [
      { href: '/watchlist', label: 'Watchlist', icon: Star, requiresAuth: true },
      { href: '/pricing', label: 'Pricing', icon: Tag },
      { href: '/blog', label: 'Research Log', icon: BookOpen },
    ],
  },
];

function isNavItemActive(pathname: string, href: string) {
  return pathname === href || (href !== '/' && pathname.startsWith(href));
}

function openCommandPalette() {
  window.dispatchEvent(new CustomEvent('qs-open-command-palette'));
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
    setSearchQuery(searchParams.get('search') || '');
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

  const renderSearchForm = (mobile = false) => (
    <div className={cn('relative', mobile ? 'w-full' : 'w-full')}>
      <form
        onSubmit={handleSearchSubmit}
        className="flex h-10 items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--surface)] px-3.5 text-sm shadow-[var(--shadow-1)] transition-[border-color,box-shadow] duration-300 focus-within:border-[var(--forest)] focus-within:shadow-[0_0_0_3px_var(--forest-soft),var(--shadow-1)]"
      >
        <Search className="h-4 w-4 shrink-0 text-[var(--mute)]" aria-hidden="true" />
        <input
          aria-label="Search stocks"
          className="w-full border-none bg-transparent p-0 text-sm text-[var(--ink)] shadow-none outline-none placeholder:text-[var(--whisper)] focus:border-none focus:shadow-none"
          onBlur={() => {
            setTimeout(() => setSuggestOpen(false), 150);
          }}
          onChange={(event) => setSearchQuery(event.target.value)}
          onFocus={() => {
            if (suggestions.length > 0) setSuggestOpen(true);
          }}
          placeholder="Ticker or company"
          type="text"
          value={searchQuery}
        />
      </form>

      {suggestOpen ? (
        <div className="absolute left-0 right-0 top-[calc(100%+0.75rem)] z-[120] overflow-hidden rounded-[16px] border border-[var(--line-2)] bg-[var(--surface)] shadow-[var(--shadow-3)]">
          <div className="border-b border-[var(--line)] px-4 py-2 font-mono text-[10.5px] uppercase tracking-[0.14em] text-[var(--mute)]">
            {isSuggestLoading ? 'Searching' : 'Quick matches'}
          </div>
          <div className="deco-scroll max-h-64 overflow-auto py-1">
            {!isSuggestLoading && suggestions.length === 0 ? (
              <div className="px-4 py-3 text-sm text-[var(--ink-2)]">No matches found.</div>
            ) : null}
            {suggestions.map((item) => (
              <div
                key={item.ticker}
                className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 transition-colors duration-[180ms] hover:bg-[var(--surface-2)]"
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSuggestionSelect(item.ticker);
                }}
              >
                <div className="min-w-0">
                  <div className="serif-num text-base text-[var(--ink)]">{item.ticker}</div>
                  <div className="truncate text-sm text-[var(--ink-2)]">
                    {item.name || 'Company profile'}
                  </div>
                </div>
                <div className="status">Open</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );

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
        onClick={() => setIsMobileMenuOpen(false)}
        className={cn(
          'group relative flex items-center gap-3 rounded-[10px] px-3.5 py-2 text-[13.5px] transition-[background,color] duration-200',
          isActive
            ? 'bg-[rgba(221,228,225,0.06)] font-medium text-[var(--ink)]'
            : 'text-[var(--mute)] hover:bg-[rgba(221,228,225,0.04)] hover:text-[var(--ink)]',
          !mobile && isActive && 'before:absolute before:left-[-16px] before:top-1/2 before:h-[18px] before:w-[3px] before:-translate-y-1/2 before:rounded-r-[3px] before:bg-[var(--forest)]'
        )}
        title={showLock ? 'Sign in to access your Watchlist' : undefined}
      >
        <Icon className="h-4 w-4 shrink-0" aria-hidden="true" strokeWidth={1.5} />
        <span className="min-w-0 flex-1 truncate">{item.label}</span>
        {item.proBadge ? <span className="status">Pro</span> : null}
        {showLock ? <Lock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /> : null}
      </Link>
    );
  };

  const renderNavGroups = (mobile = false) => (
    <>
      {navGroups.map((group, index) => (
        <div key={group.label ?? `group-${index}`} className={cn(index > 0 && 'mt-4')}>
          {group.label ? (
            <div className="px-3.5 pb-1.5 font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-[var(--whisper)]">
              {group.label}
            </div>
          ) : null}
          <div className="grid gap-0.5">
            {group.items.map((item) => renderNavLink(item, mobile))}
          </div>
        </div>
      ))}
    </>
  );

  const renderAccountControls = (mobile = false) => (
    <div className="grid gap-1.5">
      {isLoggedIn ? (
        <>
          <Link
            href="/settings/emails"
            onClick={() => setIsMobileMenuOpen(false)}
            className={cn(
              'flex items-center gap-3 rounded-[10px] px-3.5 py-2 text-[13.5px] transition-[background,color] duration-200',
              isNavItemActive(pathname, '/settings/emails')
                ? 'bg-[rgba(221,228,225,0.06)] font-medium text-[var(--ink)]'
                : 'text-[var(--mute)] hover:bg-[rgba(221,228,225,0.04)] hover:text-[var(--ink)]'
            )}
          >
            <Mail className="h-4 w-4 shrink-0" aria-hidden="true" strokeWidth={1.5} />
            <span className="flex-1">Email preferences</span>
          </Link>
          <Button variant="ghost" className="w-full justify-start" onClick={handleLogout}>
            <LogOut className="h-4 w-4" />
            Sign Out
          </Button>
        </>
      ) : (
        <>
          <Button asChild variant="ghost" className="w-full justify-start">
            <Link href="/auth/login">
              <LogIn className="h-4 w-4" />
              Login
            </Link>
          </Button>
          <Button asChild className="w-full">
            <Link href="/auth/register">Join Free</Link>
          </Button>
        </>
      )}
    </div>
  );

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-[90] hidden w-[248px] flex-col border-r border-[var(--line)] bg-[rgba(6,8,9,0.88)] px-4 py-5 backdrop-blur-xl lg:flex">
        <Link href="/" className="group flex shrink-0 items-center gap-3 px-1 py-1">
          <BrandMark className="transition-transform duration-300 group-hover:scale-[1.03]" />
          <div className="leading-tight">
            <div className="serif-tight text-[20px] text-[var(--ink)]">Quantor<span className="italic text-[var(--forest)]">signal</span></div>
            <div className="smallcap-low mt-0.5">Research terminal</div>
          </div>
        </Link>

        <button
          type="button"
          onClick={openCommandPalette}
          className="mt-6 flex w-full shrink-0 items-center gap-3 rounded-full border border-[var(--line)] bg-[var(--surface)] px-4 py-2.5 text-left text-sm text-[var(--ink-2)] shadow-[var(--shadow-1)] transition-[border-color,background,color] hover:border-[var(--line-2)] hover:bg-[var(--surface-2)] hover:text-[var(--ink)]"
        >
          <Search className="h-4 w-4" strokeWidth={1.5} />
          <span className="flex-1">Search</span>
          <kbd className="kbd">Ctrl K</kbd>
        </button>

        <nav className="deco-scroll mt-6 min-h-0 flex-1 overflow-y-auto pr-1">
          {renderNavGroups()}

          {userTier && !isProTier(userTier) ? (
            <div className="hud hud-blue mt-6 rounded-[14px] border border-[var(--line)] bg-[var(--ivory)] p-4 shadow-[var(--shadow-1)]">
              <span className="hud-c1" />
              <span className="hud-c2" />
              <div className="smallcap text-[var(--sapphire)]">Quantor Pro</div>
              <p className="mt-2 text-sm leading-5 text-[var(--ink-2)]">
                AI swing reports, daily briefs, and higher research limits.
              </p>
              <Button asChild size="sm" className="mt-4 w-full">
                <Link href="/pricing">View tiers</Link>
              </Button>
            </div>
          ) : null}
        </nav>

        <div className="mt-4 shrink-0 border-t border-[var(--line)] pt-4">
          <div className="mb-3 flex items-center gap-3 rounded-[12px] bg-[rgba(221,228,225,0.03)] px-3 py-2.5">
            <div className="grid h-8 w-8 place-items-center rounded-full border border-[var(--line-2)] bg-[var(--surface-2)] font-mono text-[11px] text-[var(--ink)]">
              QS
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm text-[var(--ink)]">{isLoggedIn ? 'Workspace' : 'Guest'}</div>
              <div className="smallcap-low truncate">{userTier ?? 'free'} tier</div>
            </div>
          </div>
          {renderAccountControls()}
        </div>
      </aside>

      <header className="sticky top-0 z-[100] border-b border-[var(--line)] bg-[rgba(6,8,9,0.88)] backdrop-blur-xl lg:hidden">
        <div className="container-custom">
          <div className="flex min-h-[68px] items-center gap-4">
            <Link href="/" className="flex shrink-0 items-center gap-3">
              <BrandMark size="sm" />
              <div className="serif-tight text-[19px] text-[var(--ink)]">
                Quantor<span className="italic text-[var(--forest)]">signal</span>
              </div>
            </Link>

            <Button
              variant="ghost"
              size="icon"
              className="ml-auto"
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
              className="deco-scroll grid max-h-[calc(100vh-68px)] gap-4 overflow-y-auto border-t border-[var(--line)] py-4"
            >
              {renderSearchForm(true)}
              <button
                type="button"
                onClick={openCommandPalette}
                className="flex items-center justify-between rounded-full border border-[var(--line)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--ink-2)]"
              >
                <span className="inline-flex items-center gap-2">
                  <Search className="h-4 w-4" />
                  Command palette
                </span>
                <kbd className="kbd">Ctrl K</kbd>
              </button>
              <nav>{renderNavGroups(true)}</nav>
              <div className="border-t border-[var(--line)] pt-4">{renderAccountControls(true)}</div>
            </div>
          ) : null}
        </div>
      </header>
    </>
  );
}
