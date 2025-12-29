'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { TrendingUp, Search, Star, LogIn, LogOut, User } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function Header() {
  const pathname = usePathname();
  const isLoggedIn = typeof window !== 'undefined' && localStorage.getItem('access_token');

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    window.location.href = '/auth/login';
  };

  const navItems = [
    { href: '/', label: 'Home', icon: TrendingUp },
    { href: '/screener', label: 'Screener', icon: Search },
    { href: '/watchlist', label: 'Watchlist', icon: Star },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center space-x-2">
          <TrendingUp className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">StockScreener</span>
        </Link>

        {/* Navigation */}
        <nav className="flex items-center space-x-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center space-x-2 text-sm font-medium transition-colors hover:text-primary",
                  isActive ? "text-primary" : "text-muted-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Auth buttons */}
        <div className="flex items-center space-x-4">
          {isLoggedIn ? (
            <>
              <Button variant="ghost" size="sm">
                <User className="h-4 w-4 mr-2" />
                Profile
              </Button>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4 mr-2" />
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link href="/auth/login">
                <Button variant="ghost" size="sm">
                  <LogIn className="h-4 w-4 mr-2" />
                  Login
                </Button>
              </Link>
              <Link href="/auth/register">
                <Button size="sm">
                  Sign Up
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
