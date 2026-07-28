import {
  Activity,
  BarChart3,
  BookOpen,
  CalendarDays,
  GitCompareArrows,
  Home,
  Landmark,
  Mail,
  Search,
  Sparkles,
  Star,
  Tag,
  Users,
  type LucideIcon,
} from 'lucide-react';

/**
 * Single source of truth for primary navigation destinations.
 *
 * Both the sidebar/mobile nav (`components/layout/Header.tsx`) and the command
 * palette (`components/ui/command-palette.tsx`) derive their entries from this
 * module so the two can never drift apart. Adding a route here surfaces it in
 * both places at once.
 */
export type NavItem = {
  href: string;
  /** Label used by the sidebar and mobile nav. */
  label: string;
  icon: LucideIcon;
  /** Verb-led label used by the command palette. Falls back to `label`. */
  commandLabel?: string;
  /** One-line hint rendered under the command palette entry. */
  description?: string;
  /** Extra lowercase search terms for the command palette. */
  keywords?: string[];
  /** Shows a lock hint in the nav when the visitor is signed out. */
  requiresAuth?: boolean;
  /** Shows a "Pro" pill and routes free users to pricing from the nav. */
  proBadge?: boolean;
  /**
   * Reachable from the command palette but rendered by dedicated chrome
   * elsewhere (e.g. the account block at the bottom of the sidebar) rather than
   * inside the main nav list.
   */
  sidebarHidden?: boolean;
};

export type NavGroup = {
  label?: string;
  items: NavItem[];
};

/** Rendered by Header's account controls; still searchable in the palette. */
export const EMAIL_PREFERENCES_ITEM: NavItem = {
  href: '/settings/emails',
  label: 'Email preferences',
  icon: Mail,
  description: 'Manage daily briefs and alert emails',
  keywords: ['email', 'settings', 'notifications', 'preferences', 'alerts', 'digest', 'brief'],
  requiresAuth: true,
  sidebarHidden: true,
};

export const navGroups: NavGroup[] = [
  {
    items: [
      {
        href: '/',
        label: 'Home',
        icon: Home,
        commandLabel: 'Market Overview',
        description: 'Return to the main dashboard',
        keywords: ['home', 'dashboard', 'market', 'overview', 'movers'],
      },
    ],
  },
  {
    label: 'Markets',
    items: [
      {
        href: '/markets',
        label: 'Scanners',
        icon: Activity,
        commandLabel: 'Open Market Scanners',
        description: 'Movers, breakouts, and volume scans',
        keywords: ['markets', 'scanner', 'scan', 'movers', 'gainers', 'losers', 'breakout', 'volume', 'sectors'],
      },
      {
        href: '/earnings',
        label: 'Earnings',
        icon: CalendarDays,
        commandLabel: 'Open Earnings Calendar',
        description: 'Upcoming and recent earnings reports',
        keywords: ['earnings', 'calendar', 'eps', 'reports', 'results'],
      },
      {
        href: '/insiders',
        label: 'Insiders',
        icon: Users,
        commandLabel: 'Open Insider Activity',
        description: 'Recent insider buys and sells',
        keywords: ['insiders', 'insider', 'form 4', 'buys', 'sells', 'executives', 'filings'],
      },
      {
        href: '/macro',
        label: 'Macro',
        icon: Landmark,
        commandLabel: 'Open Macro Dashboard',
        description: 'Rates, inflation, and economic series',
        keywords: ['macro', 'fred', 'rates', 'yields', 'inflation', 'cpi', 'economy'],
      },
    ],
  },
  {
    label: 'Tools',
    items: [
      {
        href: '/screener',
        label: 'Screener',
        icon: Search,
        commandLabel: 'Open Screener',
        description: 'Filter and compare stocks',
        keywords: ['screener', 'screen', 'filter', 'search', 'scan'],
      },
      {
        href: '/compare',
        label: 'Compare',
        icon: GitCompareArrows,
        commandLabel: 'Compare Stocks',
        description: 'Line up performance side by side',
        keywords: ['compare', 'versus', 'vs', 'side by side', 'relative'],
      },
      {
        href: '/backtester',
        label: 'Backtester',
        icon: BarChart3,
        commandLabel: 'Open Backtester',
        description: 'Run a portfolio study',
        keywords: ['backtester', 'backtest', 'portfolio', 'strategy', 'simulate', 'indicator'],
      },
      {
        href: '/ai-analyzer',
        label: 'AI Analyst',
        icon: Sparkles,
        commandLabel: 'Open AI Swing Analyzer',
        description: 'Generate an AI swing report',
        keywords: ['ai', 'analyst', 'analyzer', 'swing', 'report', 'thesis'],
        proBadge: true,
      },
    ],
  },
  {
    label: 'Account',
    items: [
      {
        href: '/watchlist',
        label: 'Watchlist',
        icon: Star,
        commandLabel: 'View Watchlist',
        description: 'Your saved names',
        keywords: ['watchlist', 'watch', 'saved', 'favorites', 'starred'],
        requiresAuth: true,
      },
      {
        href: '/pricing',
        label: 'Pricing',
        icon: Tag,
        commandLabel: 'View Pricing',
        description: 'Plans and subscription tiers',
        keywords: ['pricing', 'plans', 'upgrade', 'subscription', 'billing', 'pro'],
      },
      {
        href: '/blog',
        label: 'Research Log',
        icon: BookOpen,
        commandLabel: 'Open Research Log',
        description: 'Notes, methodology, and product updates',
        keywords: ['blog', 'research', 'log', 'notes', 'updates', 'articles'],
      },
      EMAIL_PREFERENCES_ITEM,
    ],
  },
];

/** Flat list of every nav destination, in sidebar order. */
export const navItems: NavItem[] = navGroups.flatMap((group) => group.items);

export function isNavItemActive(pathname: string, href: string) {
  return pathname === href || (href !== '/' && pathname.startsWith(href));
}
