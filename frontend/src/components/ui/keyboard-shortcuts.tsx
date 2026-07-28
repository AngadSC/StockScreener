'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

const shortcuts = [
  {
    category: 'Navigation',
    items: [
      { keys: ['Ctrl', 'K'], description: 'Open command palette' },
      { keys: ['Cmd', 'K'], description: 'Open command palette on macOS' },
      { keys: ['Esc'], description: 'Close modals or drawers' },
    ],
  },
  {
    category: 'Workspace',
    items: [
      { keys: ['?'], description: 'Open this shortcut guide' },
      { keys: ['Arrow'], description: 'Move through palette and search results' },
      { keys: ['Enter'], description: 'Launch selected command or open the highlighted stock' },
    ],
  },
];

/**
 * The global "?" listener must never steal keystrokes from a field the user is
 * typing in — otherwise a password or ticker containing "?" is impossible to
 * enter.
 */
function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable) return true;
  const tagName = target.tagName;
  return tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT';
}

export default function KeyboardShortcuts() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
        return;
      }

      if (e.key === '?' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        if (isEditableTarget(e.target)) return;
        e.preventDefault();
        setIsOpen(true);
      }
    };

    const openOverlay = () => setIsOpen(true);

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('qs-open-shortcuts', openOverlay);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('qs-open-shortcuts', openOverlay);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[210] flex items-center justify-center bg-black/80"
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard shortcuts"
    >
      <div className="absolute inset-0" onClick={() => setIsOpen(false)} />
      <div className="relative w-full max-w-3xl deco-panel bg-card max-h-[80vh] overflow-y-auto">
        <div className="sticky top-0 flex items-center justify-between border-b border-border/70 bg-card px-4 py-4">
          <div>
            <div className="deco-kicker">Reference</div>
            <h2 className="mt-2 text-2xl font-semibold">Keyboard Shortcuts</h2>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-muted-foreground hover:text-primary transition-colors"
            aria-label="Close keyboard shortcuts"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {shortcuts.map((section) => (
            <div key={section.category}>
              <h3 className="mb-3 text-sm font-semibold text-primary">{section.category}</h3>
              <div className="space-y-3">
                {section.items.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-4 rounded-lg border border-border/70 px-4 py-3">
                    <span className="text-sm text-muted-foreground">{item.description}</span>
                    <div className="flex gap-1">
                      {item.keys.map((key, keyIdx) => (
                        <kbd key={keyIdx} className="rounded-md border border-border/70 px-2 py-1 text-xs text-muted-foreground">
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
      </div>
    </div>
  );
}
