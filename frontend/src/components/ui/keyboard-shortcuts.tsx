'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

export default function KeyboardShortcuts() {
  const [isOpen, setIsOpen] = useState(false);

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
        { keys: ['Arrow'], description: 'Move inside the command palette' },
        { keys: ['Enter'], description: 'Launch selected command' },
      ],
    },
  ];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setIsOpen(true);
      }

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
      <div className="absolute inset-0" onClick={() => setIsOpen(false)} />
      <div className="relative w-full max-w-3xl deco-panel bg-card max-h-[80vh] overflow-y-auto">
        <div className="border-b border-primary/12 px-4 py-4 flex items-center justify-between sticky top-0 bg-card">
          <div>
            <div className="deco-kicker">Reference</div>
            <h2 className="mt-2 text-2xl font-semibold">Keyboard Shortcuts</h2>
          </div>
          <button onClick={() => setIsOpen(false)} className="text-muted-foreground hover:text-primary transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {shortcuts.map((section) => (
            <div key={section.category}>
              <h3 className="text-xs uppercase tracking-[0.22em] text-primary mb-3">{section.category}</h3>
              <div className="space-y-3">
                {section.items.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between gap-4 border border-primary/10 px-4 py-3">
                    <span className="text-sm text-muted-foreground">{item.description}</span>
                    <div className="flex gap-1">
                      {item.keys.map((key, keyIdx) => (
                        <kbd key={keyIdx} className="border border-primary/14 px-2 py-1 text-xs uppercase tracking-[0.12em]">
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
