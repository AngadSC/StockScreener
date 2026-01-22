'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Search, TrendingUp, Star, HelpCircle, BarChart3 } from 'lucide-react';

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

  // Command definitions
  const commands: Command[] = [
    {
      id: 'screener',
      label: 'Open Stock Screener',
      description: 'Filter and search stocks',
      icon: Search,
      action: () => {
        router.push('/screener');
        setIsOpen(false);
      },
      keywords: ['screen', 'filter', 'search'],
    },
    {
      id: 'watchlist',
      label: 'View Watchlist',
      description: 'Your saved stocks',
      icon: Star,
      action: () => {
        router.push('/watchlist');
        setIsOpen(false);
      },
      keywords: ['watch', 'saved', 'favorites'],
    },
    {
      id: 'home',
      label: 'Market Dashboard',
      description: 'Live market overview',
      icon: TrendingUp,
      action: () => {
        router.push('/');
        setIsOpen(false);
      },
      keywords: ['home', 'dashboard', 'market'],
    },
    {
      id: 'help',
      label: 'Keyboard Shortcuts',
      description: 'View all shortcuts',
      icon: HelpCircle,
      action: () => {
        alert('Keyboard Shortcuts:\n⌘K - Command Palette\n⌘/ - Search\nESC - Close');
        setIsOpen(false);
      },
      keywords: ['help', 'shortcuts', 'keyboard'],
    },
  ];

  // Filter commands based on query
  const filteredCommands = commands.filter((cmd) => {
    const searchText = query.toLowerCase();
    return (
      cmd.label.toLowerCase().includes(searchText) ||
      cmd.description?.toLowerCase().includes(searchText) ||
      cmd.keywords?.some((kw) => kw.includes(searchText))
    );
  });

  // Keyboard handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Open palette with ⌘K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
        setQuery('');
        setSelectedIndex(0);
        return;
      }

      // Close with Escape
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
        setQuery('');
        return;
      }

      // Navigate with arrow keys
      if (isOpen) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < filteredCommands.length - 1 ? prev + 1 : 0
          );
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev > 0 ? prev - 1 : filteredCommands.length - 1
          );
        } else if (e.key === 'Enter') {
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            filteredCommands[selectedIndex].action();
          }
        }
      }
    },
    [isOpen, filteredCommands, selectedIndex]
  );

  // Register keyboard listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/80">
      {/* Backdrop */}
      <div
        className="absolute inset-0"
        onClick={() => setIsOpen(false)}
      />

      {/* Command Palette */}
      <div className="relative w-full max-w-2xl terminal-border bg-card">
        {/* Header */}
        <div className="border-b border-border px-4 py-2 flex items-center gap-2">
          <span className="text-muted-foreground text-xs">COMMAND_PALETTE v1.0</span>
          <span className="ml-auto text-muted-foreground text-xs">[ESC] to close</span>
        </div>

        {/* Search Input */}
        <div className="border-b border-border px-4 py-3 flex items-center gap-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or search..."
            className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground"
            autoFocus
          />
          <kbd className="hidden sm:inline-block px-2 py-1 text-xs border border-border rounded">
            ⌘K
          </kbd>
        </div>

        {/* Commands List */}
        <div className="max-h-[400px] overflow-y-auto">
          {filteredCommands.length === 0 ? (
            <div className="px-4 py-8 text-center text-muted-foreground">
              <p>No commands found</p>
              <p className="text-xs mt-1">Try different keywords</p>
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
                      {cmd.description && (
                        <p className="text-xs text-muted-foreground">
                          {cmd.description}
                        </p>
                      )}
                    </div>
                    {isSelected && (
                      <kbd className="px-2 py-1 text-xs border border-border rounded">
                        ENTER
                      </kbd>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-4 py-2 flex items-center gap-4 text-xs text-muted-foreground">
          <span>↑↓ navigate</span>
          <span>ENTER select</span>
          <span>ESC close</span>
        </div>
      </div>
    </div>
  );
}
