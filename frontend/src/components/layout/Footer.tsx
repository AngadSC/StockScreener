import Link from 'next/link';

import BrandMark from '@/components/layout/BrandMark';

const footerLinks = [
  { href: '/blog', label: 'Blog' },
  { href: '/terms', label: 'Terms of Service' },
  { href: '/privacy', label: 'Privacy Policy' },
  { href: '/contact', label: 'Contact' },
];

export default function Footer() {
  return (
    <footer className="border-t border-[var(--border-subtle)] bg-[var(--bg-base)]">
      <div className="container-custom">
        <div className="flex flex-col gap-4 py-5 text-[13px] text-[var(--text-tertiary)] md:flex-row md:items-center md:justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-3 text-[var(--text-tertiary)] transition-colors duration-[180ms] hover:text-[var(--text-secondary)]"
          >
            <BrandMark size="sm" />
            <span>QuantorSignal</span>
          </Link>

          <nav className="flex flex-wrap items-center justify-center gap-4 md:flex-1">
            {footerLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="transition-colors duration-[180ms] hover:text-[var(--text-secondary)]"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          <div className="text-left md:text-right">
            &copy; {new Date().getFullYear()} QuantorSignal
          </div>
        </div>
      </div>
    </footer>
  );
}
