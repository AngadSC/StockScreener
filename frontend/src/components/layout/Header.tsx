'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Command } from 'lucide-react';

export default function Header() {
  const pathname = usePathname();
  const [time, setTime] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Update time every second
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('en-US', { hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Check login status
  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem('access_token'));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.href = '/auth/login';
  };

  const navItems = [
    { href: '/', label: 'DASHBOARD', key: 'D' },
    { href: '/screener', label: 'SCREENER', key: 'S' },
    { href: '/watchlist', label: 'WATCHLIST', key: 'W' },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background">
      <div className="container">
        {/* Top bar - terminal title bar style */}
        <div className="flex h-12 items-center justify-between text-xs border-b border-border/50">
          {/* Left: System name */}
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 text-primary hover:text-primary/80 transition-colors">
              <span className="text-base font-bold tracking-tight">STOCK_TERMINAL</span>
              <span className="text-muted-foreground">[v2.1.0]</span>
            </Link>
          </div>

          {/* Right: Status indicators */}
          <div className="flex items-center gap-4 text-muted-foreground">
            <span>SYS_TIME: {time}</span>
            <span className="hidden sm:inline">|</span>
            <span className="hidden sm:inline">
              STATUS: <span className="text-primary">ONLINE</span>
            </span>
            <span className="hidden md:inline">|</span>
            <span className="hidden md:inline">
              USER: {isLoggedIn ? <span className="text-primary">AUTHENTICATED</span> : 'GUEST'}
            </span>
          </div>
        </div>

        {/* Bottom bar - navigation */}
        <div className="flex h-10 items-center justify-between text-xs">
          {/* Navigation links */}
          <nav className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-1 transition-colors ${
                    isActive
                      ? 'text-primary bg-primary/10 border-b-2 border-primary'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                  }`}
                >
                  [{item.key}] {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Command palette hint + auth */}
          <div className="flex items-center gap-3">
            <button
              className="flex items-center gap-2 px-2 py-1 text-muted-foreground hover:text-primary transition-colors border border-border/50 hover:border-primary/50"
              onClick={() => {
                const event = new KeyboardEvent('keydown', {
                  key: 'k',
                  metaKey: true,
                  bubbles: true,
                });
                window.dispatchEvent(event);
              }}
            >
              <Command className="h-3 w-3" />
              <span className="hidden sm:inline">COMMAND</span>
              <kbd className="hidden md:inline px-1 text-xs">⌘K</kbd>
            </button>

            {isLoggedIn ? (
              <button
                onClick={handleLogout}
                className="px-2 py-1 text-muted-foreground hover:text-destructive transition-colors"
              >
                [LOGOUT]
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/auth/login"
                  className="px-2 py-1 text-muted-foreground hover:text-primary transition-colors"
                >
                  [LOGIN]
                </Link>
                <Link
                  href="/auth/register"
                  className="px-2 py-1 text-primary hover:text-primary/80 transition-colors border border-primary/50"
                >
                  [SIGNUP]
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
