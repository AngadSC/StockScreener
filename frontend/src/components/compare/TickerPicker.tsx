'use client';

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Plus, Search, X } from 'lucide-react';

import { screenerAPI } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { StockSuggestion } from '@/types/stock';

import { MAX_COMPARE_TICKERS, type SeriesColorMap } from './colors';

interface TickerPickerProps {
  tickers: string[];
  colorMap: SeriesColorMap;
  onAdd: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

export default function TickerPicker({ tickers, colorMap, onAdd, onRemove }: TickerPickerProps) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const latestQueryRef = useRef(0);
  const atLimit = tickers.length >= MAX_COMPARE_TICKERS;

  useEffect(() => {
    const trimmed = query.trim();

    if (!trimmed || atLimit) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    const requestId = ++latestQueryRef.current;
    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const result = await screenerAPI.suggestStocks(trimmed, 8);
        if (requestId !== latestQueryRef.current) return;
        setSuggestions(result.results);
        setIsOpen(true);
      } catch {
        if (requestId !== latestQueryRef.current) return;
        setSuggestions([]);
      } finally {
        if (requestId === latestQueryRef.current) setIsLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query, atLimit]);

  const addTicker = (raw: string) => {
    const symbol = raw.trim().toUpperCase();
    if (!symbol || atLimit) return;
    if (tickers.includes(symbol)) {
      setQuery('');
      setIsOpen(false);
      return;
    }
    onAdd(symbol);
    setQuery('');
    setSuggestions([]);
    setIsOpen(false);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (suggestions.length > 0) {
      addTicker(suggestions[0].ticker);
    } else {
      addTicker(query);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && query.length === 0 && tickers.length > 0) {
      onRemove(tickers[tickers.length - 1]);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="relative">
        <div
          className={cn(
            'flex h-12 items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--surface)] px-4 text-sm shadow-[var(--shadow-1)] transition-[border-color,box-shadow] duration-300 ease-out focus-within:border-[var(--accent)] focus-within:shadow-[0_0_0_3px_var(--accent-subtle),var(--shadow-1)]',
            atLimit && 'opacity-60'
          )}
        >
          <Search className="h-4 w-4 shrink-0 text-[var(--text-secondary)]" aria-hidden="true" />
          <input
            aria-label="Add a ticker to compare"
            autoComplete="off"
            className="w-full border-none bg-transparent p-0 text-sm font-semibold uppercase text-[var(--text-primary)] shadow-none outline-none placeholder:font-normal placeholder:normal-case placeholder:text-[var(--text-secondary)] focus:border-none focus:shadow-none"
            disabled={atLimit}
            maxLength={12}
            onBlur={() => setTimeout(() => setIsOpen(false), 150)}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={() => {
              if (suggestions.length > 0) setIsOpen(true);
            }}
            onKeyDown={handleKeyDown}
            placeholder={atLimit ? `Limit of ${MAX_COMPARE_TICKERS} reached` : 'Add a ticker (e.g. AAPL)'}
            type="text"
            value={query}
          />
          {query.trim() ? (
            <button
              type="submit"
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--accent-subtle)] text-[var(--accent)] transition-colors hover:bg-[var(--accent-subtle-hover)]"
              aria-label="Add ticker"
            >
              <Plus className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        {isOpen ? (
          <div className="absolute left-0 right-0 top-[calc(100%+0.5rem)] z-30 overflow-hidden rounded-[16px] border border-[var(--border-default)] bg-[var(--bg-surface-1)] shadow-[var(--shadow-lg)]">
            <div className="border-b border-[var(--border-subtle)] px-4 py-2 text-xs text-[var(--text-secondary)]">
              {isLoading ? 'Searching' : 'Quick matches'}
            </div>
            <div className="deco-scroll max-h-64 overflow-auto py-1">
              {!isLoading && suggestions.length === 0 ? (
                <div className="px-4 py-3 text-sm text-[var(--text-secondary)]">No matches found.</div>
              ) : null}
              {suggestions.map((item) => {
                const alreadyAdded = tickers.includes(item.ticker.toUpperCase());
                return (
                  <div
                    key={item.ticker}
                    className={cn(
                      'flex items-center justify-between gap-3 px-4 py-3 transition-colors duration-[180ms]',
                      alreadyAdded
                        ? 'cursor-not-allowed opacity-40'
                        : 'cursor-pointer hover:bg-[var(--accent-subtle)]'
                    )}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      if (!alreadyAdded) addTicker(item.ticker);
                    }}
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-[var(--text-primary)]">{item.ticker}</div>
                      <div
                        className="truncate text-sm text-[var(--text-secondary)]"
                        title={item.name || 'Company profile'}
                      >
                        {item.name || 'Company profile'}
                      </div>
                    </div>
                    <div className="text-xs font-medium text-[var(--accent)]">
                      {alreadyAdded ? 'Added' : 'Add'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </form>

      {tickers.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2">
          {tickers.map((ticker) => {
            const color = colorMap.get(ticker) ?? 'var(--accent)';
            return (
              <span
                key={ticker}
                className="inline-flex items-center gap-2 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-2)] py-1.5 pl-3 pr-2 text-sm font-medium text-[var(--text-primary)]"
              >
                <span
                  aria-hidden="true"
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
                {ticker}
                <button
                  type="button"
                  onClick={() => onRemove(ticker)}
                  className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[var(--text-tertiary)] transition-colors hover:bg-[var(--negative-bg)] hover:text-[var(--negative)]"
                  aria-label={`Remove ${ticker}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            );
          })}
          <span className="text-xs text-[var(--text-tertiary)]">
            {tickers.length}/{MAX_COMPARE_TICKERS} tickers
          </span>
        </div>
      ) : null}
    </div>
  );
}
