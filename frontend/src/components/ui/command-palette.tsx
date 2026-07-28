'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { HelpCircle, Search, TrendingUp, type LucideIcon } from 'lucide-react';

import { screenerAPI } from '@/lib/api';
import { navItems } from '@/lib/nav';
import { cn } from '@/lib/utils';
import type { StockSuggestion } from '@/types/stock';

const SUGGEST_DEBOUNCE_MS = 200;
const SUGGEST_LIMIT = 6;
const LIST_ID = 'command-palette-results';

interface PaletteCommand {
  id: string;
  label: string;
  description?: string;
  icon: LucideIcon;
  keywords?: string[];
  proBadge?: boolean;
  run: () => void;
}

/** Flattened selection model so one index spans both groups. */
type PaletteRow =
  | { kind: 'command'; command: PaletteCommand }
  | { kind: 'stock'; suggestion: StockSuggestion };

interface PaletteOptionProps {
  icon: LucideIcon;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
  onHover: () => void;
  subtitle?: string | null;
  title: string;
  titleClassName?: string;
  trailing?: ReactNode;
}

function PaletteOption({
  icon: Icon,
  index,
  isSelected,
  onSelect,
  onHover,
  subtitle,
  title,
  titleClassName,
  trailing,
}: PaletteOptionProps) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={isSelected}
      id={`${LIST_ID}-option-${index}`}
      data-row-index={index}
      onClick={onSelect}
      onMouseEnter={onHover}
      className={cn(
        'flex w-full items-center gap-3 px-4 py-3 transition-[background,border-color,box-shadow,color,transform] duration-[180ms]',
        isSelected
          ? 'border-l-2 border-l-[var(--forest)] bg-[var(--forest-soft)]'
          : 'border-l-2 border-l-transparent hover:bg-[var(--surface-2)]'
      )}
    >
      <Icon
        className={cn('h-5 w-5 shrink-0', isSelected ? 'text-[var(--forest)]' : 'text-[var(--text-tertiary)]')}
        strokeWidth={1.5}
      />
      <div className="min-w-0 flex-1 text-left">
        <p className={cn('truncate font-medium text-[var(--ink)]', titleClassName)}>{title}</p>
        {subtitle ? <p className="truncate text-xs text-[var(--ink-2)]">{subtitle}</p> : null}
      </div>
      {trailing}
      {isSelected ? <kbd className="kbd">Enter</kbd> : null}
    </button>
  );
}

function GroupLabel({ children }: { children: ReactNode }) {
  return (
    <div className="px-4 pb-1 pt-3 font-mono text-[10.5px] uppercase tracking-[0.14em] text-[var(--mute)]">
      {children}
    </div>
  );
}

export default function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [stocks, setStocks] = useState<StockSuggestion[]>([]);
  const [isStockLoading, setIsStockLoading] = useState(false);
  const latestQueryRef = useRef(0);
  const listRef = useRef<HTMLDivElement | null>(null);
  const router = useRouter();

  const reset = useCallback(() => {
    // Bump the request id so any in-flight suggest response is discarded
    // instead of repopulating a palette that has moved on.
    latestQueryRef.current += 1;
    setQuery('');
    setSelectedIndex(0);
    setStocks([]);
    setIsStockLoading(false);
  }, []);

  const openPalette = useCallback(() => {
    reset();
    setIsOpen(true);
  }, [reset]);

  const closePalette = useCallback(() => {
    reset();
    setIsOpen(false);
  }, [reset]);

  const navigate = useCallback(
    (href: string) => {
      closePalette();
      router.push(href);
    },
    [closePalette, router]
  );

  const commands = useMemo<PaletteCommand[]>(() => {
    const navCommands = navItems.map<PaletteCommand>((item) => ({
      id: `nav:${item.href}`,
      label: item.commandLabel ?? item.label,
      description: item.description,
      icon: item.icon,
      keywords: [...(item.keywords ?? []), item.label.toLowerCase(), item.href.replace(/^\//, '')],
      proBadge: item.proBadge,
      run: () => navigate(item.href),
    }));

    return [
      ...navCommands,
      {
        id: 'action:shortcuts',
        label: 'Keyboard Guide',
        description: 'Open the shortcut sheet',
        icon: HelpCircle,
        keywords: ['help', 'shortcuts', 'keyboard', 'keys', 'guide'],
        run: () => {
          closePalette();
          window.dispatchEvent(new CustomEvent('qs-open-shortcuts'));
        },
      },
    ];
  }, [closePalette, navigate]);

  const filteredCommands = useMemo(() => {
    const searchText = query.trim().toLowerCase();
    if (!searchText) return commands;
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(searchText) ||
        cmd.description?.toLowerCase().includes(searchText) ||
        cmd.keywords?.some((keyword) => keyword.includes(searchText))
    );
  }, [commands, query]);

  const rows = useMemo<PaletteRow[]>(
    () => [
      ...filteredCommands.map((command) => ({ kind: 'command' as const, command })),
      ...stocks.map((suggestion) => ({ kind: 'stock' as const, suggestion })),
    ],
    [filteredCommands, stocks]
  );

  const runRow = useCallback(
    (row: PaletteRow) => {
      if (row.kind === 'command') {
        row.command.run();
        return;
      }
      navigate(`/stocks/${encodeURIComponent(row.suggestion.ticker)}`);
    },
    [navigate]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) closePalette();
        else openPalette();
        return;
      }

      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        closePalette();
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (rows.length === 0) return;
        setSelectedIndex((prev) => (prev + 1) % rows.length);
        return;
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (rows.length === 0) return;
        setSelectedIndex((prev) => (prev <= 0 ? rows.length - 1 : prev - 1));
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        const row = rows[selectedIndex];
        if (row) runRow(row);
      }
    },
    [closePalette, isOpen, openPalette, rows, runRow, selectedIndex]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('qs-open-command-palette', openPalette);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('qs-open-command-palette', openPalette);
    };
  }, [handleKeyDown, openPalette]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keep the highlight inside the list when results shrink (e.g. suggestions
  // are cleared while the palette stays open).
  useEffect(() => {
    setSelectedIndex((prev) => (prev >= rows.length ? 0 : prev));
  }, [rows.length]);

  useEffect(() => {
    const node = listRef.current?.querySelector<HTMLElement>(`[data-row-index="${selectedIndex}"]`);
    node?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex, rows.length]);

  // Ticker/company suggestions from the screener's relevance-ranked endpoint.
  // The list order is preserved exactly as the backend returns it.
  useEffect(() => {
    const trimmed = query.trim();
    // Invalidate before the early return so clearing the input also cancels an
    // in-flight response instead of letting it land on an empty query.
    const requestId = ++latestQueryRef.current;

    if (!isOpen || !trimmed) {
      setStocks([]);
      setIsStockLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsStockLoading(true);
      try {
        const result = await screenerAPI.suggestStocks(trimmed, SUGGEST_LIMIT);
        if (requestId !== latestQueryRef.current) return;
        setStocks(result.results);
      } catch {
        // Suggestions are an enhancement — fail silently and keep commands usable.
        if (requestId !== latestQueryRef.current) return;
        setStocks([]);
      } finally {
        if (requestId === latestQueryRef.current) setIsStockLoading(false);
      }
    }, SUGGEST_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [isOpen, query]);

  if (!isOpen) return null;

  const hasQuery = query.trim().length > 0;
  const showStockSection = hasQuery && (stocks.length > 0 || isStockLoading);
  const activeOptionId = rows[selectedIndex] ? `${LIST_ID}-option-${selectedIndex}` : undefined;

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center bg-black/65 px-4 pt-[16vh] backdrop-blur-sm">
      <div className="absolute inset-0" onClick={closePalette} />
      <div className="hud hud-blue relative w-full max-w-[640px] overflow-hidden rounded-[18px] border border-[var(--line-2)] bg-[var(--surface)] shadow-[var(--shadow-3)]">
        <span className="hud-c1" />
        <span className="hud-c2" />
        <div className="flex items-center gap-2 border-b border-[var(--line)] px-5 py-3">
          <span className="smallcap text-[var(--sapphire)]">Command palette</span>
          <span className="smallcap-low ml-auto">Esc to close</span>
        </div>

        <div className="flex items-center gap-3 border-b border-[var(--line)] px-5 py-5">
          <Search className="h-4 w-4 text-[var(--sapphire)]" strokeWidth={1.5} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search a ticker, company, or page"
            role="combobox"
            aria-controls={LIST_ID}
            aria-expanded
            aria-autocomplete="list"
            aria-activedescendant={activeOptionId}
            aria-label="Search commands and stocks"
            autoComplete="off"
            className="serif flex-1 border-none bg-transparent p-0 text-2xl text-[var(--ink)] shadow-none outline-none placeholder:text-[var(--whisper)] focus:border-none focus:shadow-none"
            autoFocus
          />
          <kbd className="kbd hidden sm:inline-block">
            Cmd/Ctrl+K
          </kbd>
        </div>

        <div
          ref={listRef}
          id={LIST_ID}
          role="listbox"
          aria-label="Command palette results"
          className="deco-scroll max-h-[400px] overflow-y-auto"
        >
          {rows.length === 0 && !isStockLoading ? (
            <div className="px-4 py-8 text-center text-[var(--ink-2)]">
              <p>No matches found</p>
              <p className="smallcap-low mt-1">Try a ticker, a company name, or a page</p>
            </div>
          ) : (
            <>
              {filteredCommands.length > 0 ? (
                <div className="pb-2">
                  <GroupLabel>Commands</GroupLabel>
                  {filteredCommands.map((cmd, idx) => (
                    <PaletteOption
                      key={cmd.id}
                      icon={cmd.icon}
                      index={idx}
                      isSelected={idx === selectedIndex}
                      onHover={() => setSelectedIndex(idx)}
                      onSelect={() => cmd.run()}
                      subtitle={cmd.description}
                      title={cmd.label}
                      trailing={cmd.proBadge ? <span className="status">Pro</span> : null}
                    />
                  ))}
                </div>
              ) : null}

              {showStockSection ? (
                <div className={cn('pb-2', filteredCommands.length > 0 && 'border-t border-[var(--line)]')}>
                  <GroupLabel>{isStockLoading && stocks.length === 0 ? 'Stocks — searching' : 'Stocks'}</GroupLabel>
                  {stocks.map((suggestion, idx) => {
                    const rowIndex = filteredCommands.length + idx;
                    return (
                      <PaletteOption
                        key={suggestion.ticker}
                        icon={TrendingUp}
                        index={rowIndex}
                        isSelected={rowIndex === selectedIndex}
                        onHover={() => setSelectedIndex(rowIndex)}
                        onSelect={() => navigate(`/stocks/${encodeURIComponent(suggestion.ticker)}`)}
                        subtitle={suggestion.name || 'Company profile'}
                        title={suggestion.ticker}
                        titleClassName="serif-num text-base"
                      />
                    );
                  })}
                  {stocks.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-[var(--ink-2)]">Looking up tickers…</div>
                  ) : null}
                </div>
              ) : null}
            </>
          )}
        </div>

        <div className="smallcap-low flex items-center gap-4 border-t border-[var(--line)] px-5 py-3">
          <span>Arrow keys navigate</span>
          <span>Enter select</span>
          <span>Esc close</span>
        </div>
      </div>
    </div>
  );
}
