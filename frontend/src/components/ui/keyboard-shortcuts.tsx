'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

export default function KeyboardShortcuts() {
  const [isOpen, setIsOpen] = useState(false);

  const shortcuts = [
    {
      category: 'NAVIGATION',
      items: [
        { keys: ['⌘', 'K'], description: 'Open command palette' },
        { keys: ['Ctrl', 'K'], description: 'Open command palette (Windows/Linux)' },
        { keys: ['ESC'], description: 'Close modals/dialogs' },
        { keys: ['[D]'], description: 'Go to Dashboard (from header)' },
        { keys: ['[S]'], description: 'Go to Screener (from header)' },
        { keys: ['[W]'], description: 'Go to Watchlist (from header)' },
      ],
    },
    {
      category: 'SCREENER',
      items: [
        { keys: ['↑', '↓'], description: 'Navigate results (in command palette)' },
        { keys: ['Enter'], description: 'Select item' },
      ],
    },
    {
      category: 'SYSTEM',
      items: [
        { keys: ['?'], description: 'Show this help menu' },
        { keys: ['Ctrl', '/'], description: 'Quick search' },
      ],
    },
  ];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Open shortcuts with '?' key
      if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setIsOpen(true);
      }

      // Close with Escape
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
      {/* Backdrop */}
      <div
        className="absolute inset-0"
        onClick={() => setIsOpen(false)}
      />

      {/* Modal */}
      <div className="relative w-full max-w-3xl terminal-border bg-card max-h-[80vh] overflow-y-auto">
        {/* Header */}
        <div className="border-b border-border px-4 py-3 flex items-center justify-between sticky top-0 bg-card">
          <div>
            <h2 className="text-lg font-bold text-glow">KEYBOARD_SHORTCUTS</h2>
            <p className="text-xs text-muted-foreground mt-1">Quick reference guide</p>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-muted-foreground hover:text-primary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Shortcuts List */}
        <div className="p-6 space-y-6">
          {shortcuts.map((section) => (
            <div key={section.category}>
              <h3 className="text-xs font-bold text-primary mb-3 border-b border-border pb-2">
                ──[ {section.category} ]──
              </h3>
              <div className="space-y-3">
                {section.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between py-2 text-sm hover:bg-primary/5 transition-colors px-2"
                  >
                    <span className="text-muted-foreground">{item.description}</span>
                    <div className="flex gap-1">
                      {item.keys.map((key, keyIdx) => (
                        <kbd
                          key={keyIdx}
                          className="px-2 py-1 text-xs border border-border bg-muted/20 font-mono min-w-[2rem] text-center"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-4 py-3 bg-muted/20 text-xs text-muted-foreground text-center">
          Press <kbd className="px-2 py-1 border border-border mx-1">?</kbd> anytime to open this help menu
        </div>
      </div>
    </div>
  );
}
