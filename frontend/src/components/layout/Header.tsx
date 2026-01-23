'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { TrendingUp, Search, Star, LogIn, LogOut } from 'lucide-react';

export default function Header() {
  const pathname = usePathname();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem('access_token'));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.href = '/auth/login';
  };

  const navItems = [
    { href: '/', label: 'Market', icon: TrendingUp },
    { href: '/screener', label: 'Screener', icon: Search },
    { href: '/watchlist', label: 'Watchlist', icon: Star },
  ];

  return (
    <header className="border-b border-border bg-card sticky top-0 z-50 backdrop-blur-sm bg-card/95">
      <div className="container-custom">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <TrendingUp className="h-6 w-6 text-primary" />
            <span className="text-xl font-semibold">StockScreener</span>
          </Link>

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
