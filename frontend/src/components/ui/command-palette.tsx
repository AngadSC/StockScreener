'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BarChart3, HelpCircle, Search, Star, TrendingUp } from 'lucide-react';

interface Command {
  id: string;
  label: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
  action: () => void;
  keywords?: string[];
}

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const router = useRouter();

  const commands: Command[] = [
    {
      id: 'screener',
      label: 'Open Screener',
      description: 'Filter and compare stocks',
      icon: Search,
      action: () => {
        router.push('/screener');
        setIsOpen(false);
      },
      keywords: ['screen', 'filter', 'search'],
    },
    {
      id: 'backtester',
      label: 'Open Backtester',
      description: 'Run a portfolio study',
      icon: BarChart3,
      action: () => {
        router.push('/backtester');
        setIsOpen(false);
      },
      keywords: ['backtest', 'portfolio', 'strategy'],
    },
    {
      id: 'watchlist',
      label: 'View Watchlist',
      description: 'Your saved names',
      icon: Star,
      action: () => {
        router.push('/watchlist');
        setIsOpen(false);
      },
      keywords: ['watch', 'saved', 'favorites'],
    },
    {
      id: 'home',
      label: 'Market Overview',
      description: 'Return to the main dashboard',
      icon: TrendingUp,
      action: () => {
        router.push('/');
        setIsOpen(false);
      },
      keywords: ['home', 'dashboard', 'market'],
    },
    {
      id: 'help',
      label: 'Keyboard Guide',
      description: 'Open the shortcut sheet',
      icon: HelpCircle,
      action: () => {
        alert('Keyboard Shortcuts:\\nCtrl/Cmd+K - Command Palette\\n? - Shortcut Guide\\nEsc - Close');
        setIsOpen(false);
      },
      keywords: ['help', 'shortcuts', 'keyboard'],
    },
  ];

  const filteredCommands = commands.filter((cmd) => {
    const searchText = query.toLowerCase();
    return (
      cmd.label.toLowerCase().includes(searchText) ||
      cmd.description?.toLowerCase().includes(searchText) ||
      cmd.keywords?.some((kw) => kw.includes(searchText))
    );
  });

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
        setQuery('');
        setSelectedIndex(0);
        return;
      }

      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
        setQuery('');
        return;
      }

      if (isOpen) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex((prev) => (prev < filteredCommands.length - 1 ? prev + 1 : 0));
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredCommands.length - 1));
        } else if (e.key === 'Enter') {
          e.preventDefault();
          if (filteredCommands[selectedIndex]) filteredCommands[selectedIndex].action();
        }
      }
    },
    [filteredCommands, isOpen, selectedIndex]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/80 pt-[16vh]">
      <div className="absolute inset-0" onClick={() => setIsOpen(false)} />
      <div className="relative w-full max-w-2xl deco-panel bg-card">
        <div className="border-b border-primary/12 px-4 py-3 flex items-center gap-2">
          <span className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Command Palette</span>
          <span className="ml-auto text-xs uppercase tracking-[0.22em] text-muted-foreground">Esc to close</span>
        </div>

        <div className="border-b border-primary/12 px-4 py-4 flex items-center gap-3">
          <Search className="h-4 w-4 text-primary" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or route"
            className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground"
            autoFocus
          />
          <kbd className="hidden sm:inline-block border border-primary/14 px-2 py-1 text-xs">Cmd/Ctrl+K</kbd>
        </div>

        <div className="max-h-[400px] overflow-y-auto">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-8 text-center text-muted-foreground">
              <p>No commands found</p>
              <p className="mt-1 text-xs">Try different keywords</p>
            </div>
          ) : (
            <div className="py-2">
              {filteredCommands.map((cmd, idx) => {
                const Icon = cmd.icon || Search;
                const isSelected = idx === selectedIndex;

                return (
                  <button
                    key={cmd.id}
                    onClick={() => cmd.action()}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`w-full px-4 py-3 flex items-center gap-3 transition-colors ${
                      isSelected
                        ? 'bg-primary/20 border-l-2 border-l-primary'
                        : 'border-l-2 border-l-transparent hover:bg-muted/50'
                    }`}
                  >
                    <Icon className="h-5 w-5 text-primary" />
                    <div className="flex-1 text-left">
                      <p className="font-medium text-foreground">{cmd.label}</p>
                      {cmd.description ? <p className="text-xs text-muted-foreground">{cmd.description}</p> : null}
                    </div>
                    {isSelected ? (
                      <kbd className="border border-primary/14 px-2 py-1 text-xs">Enter</kbd>
                    ) : null}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="border-t border-primary/12 px-4 py-3 flex items-center gap-4 text-xs uppercase tracking-[0.18em] text-muted-foreground">
          <span>Arrow keys navigate</span>
          <span>Enter select</span>
          <span>Esc close</span>
        </div>
      </div>
    </div>
  );
}
