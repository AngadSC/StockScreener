import Link from 'next/link';

import BrandMark from '@/components/layout/BrandMark';

type FooterColumn = {
  heading: string;
  links: { href: string; label: string }[];
};

const footerColumns: FooterColumn[] = [
  {
    heading: 'Markets',
    links: [
      { href: '/markets', label: 'Scanners' },
      { href: '/earnings', label: 'Earnings' },
      { href: '/insiders', label: 'Insiders' },
      { href: '/macro', label: 'Macro' },
    ],
  },
  {
    heading: 'Tools',
    links: [
      { href: '/screener', label: 'Screener' },
      { href: '/compare', label: 'Compare' },
      { href: '/backtester', label: 'Backtester' },
      { href: '/ai-analyzer', label: 'AI Analyst' },
    ],
  },
  {
    heading: 'Company',
    links: [
      { href: '/pricing', label: 'Pricing' },
      { href: '/blog', label: 'Research Log' },
      { href: '/contact', label: 'Contact' },
      { href: '/settings/emails', label: 'Email preferences' },
    ],
  },
];

const legalLinks = [
  { href: '/terms', label: 'Terms' },
  { href: '/privacy', label: 'Privacy' },
];

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border-subtle)] bg-[var(--bg-base)]">
      <div className="container-custom">
        <div className="grid gap-8 py-10 md:grid-cols-[1.4fr_repeat(3,1fr)] md:gap-6">
          <div className="max-w-xs">
            <Link
              href="/"
              className="inline-flex items-center gap-3 text-[var(--text-secondary)] transition-colors duration-[180ms] hover:text-[var(--text-primary)]"
            >
              <BrandMark size="sm" />
              <span className="serif-tight text-[17px] text-[var(--text-primary)]">
                Quantor<span className="italic text-[var(--forest)]">signal</span>
              </span>
            </Link>
            <p className="mt-3 text-[13px] leading-6 text-[var(--text-tertiary)]">
              Screening, scanners, and AI research for equity investors.
            </p>
          </div>

          {footerColumns.map((column) => (
            <nav key={column.heading} aria-label={column.heading} className="text-[13px]">
              <div className="mb-3 font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-[var(--text-tertiary)]">
                {column.heading}
              </div>
              <ul className="space-y-2.5">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-[var(--text-secondary)] transition-colors duration-[180ms] hover:text-[var(--text-primary)]"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="flex flex-col gap-3 border-t border-[var(--border-subtle)] py-5 text-[12px] text-[var(--text-tertiary)] sm:flex-row sm:items-center sm:justify-between">
          <div>&copy; {new Date().getFullYear()} QuantorSignal. Data for research, not investment advice.</div>
          <nav className="flex items-center gap-4">
            {legalLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="transition-colors duration-[180ms] hover:text-[var(--text-secondary)]"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </footer>
  );
}
