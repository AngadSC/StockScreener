'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, ChevronRight, Loader2, Star, Sunrise, Sunset } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { marketAPI } from '@/lib/api';
import { cn, formatMarketCap } from '@/lib/utils';
import type { EarningsEventItem, EarningsTimeHint } from '@/types/earnings';

const DAYS_AHEAD = 14;

const TIME_HINT_LABEL: Record<EarningsTimeHint, string> = {
  bmo: 'Before Open',
  amc: 'After Close',
  unknown: 'Time TBD',
};

function isWeekend(dateStr: string): boolean {
  const day = new Date(`${dateStr}T00:00:00`).getDay();
  return day === 0 || day === 6;
}

function formatDayLabel(dateStr: string): string {
  return new Date(`${dateStr}T00:00:00`).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  });
}

function buildWeekdayRange(fromDate: string, totalDays: number): string[] {
  const start = new Date(`${fromDate}T00:00:00`);
  const result: string[] = [];
  for (let i = 0; i < totalDays; i += 1) {
    const current = new Date(start);
    current.setDate(start.getDate() + i);
    const iso = current.toISOString().slice(0, 10);
    if (!isWeekend(iso)) result.push(iso);
  }
  return result;
}

function groupByDate(events: EarningsEventItem[]): Map<string, EarningsEventItem[]> {
  const map = new Map<string, EarningsEventItem[]>();
  for (const event of events) {
    const list = map.get(event.earnings_date) ?? [];
    list.push(event);
    map.set(event.earnings_date, list);
  }
  for (const list of map.values()) {
    list.sort((a, b) => (b.market_cap ?? 0) - (a.market_cap ?? 0));
  }
  return map;
}

function TimeHintBadge({ hint }: { hint: EarningsTimeHint }) {
  if (hint === 'bmo') {
    return (
      <Badge variant="outline" className="gap-1">
        <Sunrise className="h-3 w-3" />
        {TIME_HINT_LABEL.bmo}
      </Badge>
    );
  }
  if (hint === 'amc') {
    return (
      <Badge variant="outline" className="gap-1">
        <Sunset className="h-3 w-3" />
        {TIME_HINT_LABEL.amc}
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1">
      {TIME_HINT_LABEL.unknown}
    </Badge>
  );
}

export default function EarningsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['earnings-calendar', DAYS_AHEAD],
    queryFn: () => marketAPI.getEarningsCalendar(DAYS_AHEAD),
  });

  const grouped = useMemo(() => groupByDate(data?.events ?? []), [data]);
  const dayRange = useMemo(
    () => (data ? buildWeekdayRange(data.from_date, DAYS_AHEAD) : []),
    [data]
  );
  const totalReports = data?.events?.length ?? 0;

  return (
    <div className="container-custom py-8">
      <section className="mb-7 border-b border-t border-[var(--line)] py-7">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="live-dot">Earnings desk</div>
            <h1 className="mt-3">Earnings calendar</h1>
            <p className="mt-3 text-base leading-relaxed text-[var(--text-secondary)]">
              Upcoming reports for your watchlist and the market&apos;s largest companies, grouped by
              trading day for the next {DAYS_AHEAD} days.
            </p>
          </div>

          <div className="flex min-w-[220px] items-center gap-4 rounded-[var(--radius-lg)] border border-[var(--line-2)] bg-[var(--surface)] px-4 py-4 shadow-[var(--shadow-1)]">
            <div className="icon-tile h-11 w-11">
              <CalendarDays className="h-5 w-5" strokeWidth={1.6} />
            </div>
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.12em] text-[var(--text-tertiary)]">
                Reports ahead
              </div>
              <div className="mt-1 text-2xl font-semibold tabular-nums text-[var(--text-primary)]">
                {isLoading ? '—' : totalReports.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </section>

      {isLoading ? (
        <div className="deco-panel p-12 text-center">
          <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-[var(--accent)]" />
          <p className="text-sm text-[var(--text-secondary)]">Loading earnings calendar...</p>
        </div>
      ) : null}

      {isError ? (
        <div className="deco-panel p-8 text-center">
          <p className="text-sm text-[var(--text-secondary)]">
            Could not load the earnings calendar. Please try again shortly.
          </p>
        </div>
      ) : null}

      {!isLoading && !isError ? (
        <div className="space-y-4">
          {dayRange.map((dateStr) => {
            const events = grouped.get(dateStr) ?? [];
            return (
              <div key={dateStr} className="deco-panel overflow-hidden bg-[var(--bg-surface-1)]">
                <div className="flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface-2)] px-4 py-3">
                  <div className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-[var(--text-tertiary)]" />
                    <span className="text-sm font-semibold text-[var(--text-primary)]">
                      {formatDayLabel(dateStr)}
                    </span>
                  </div>
                  <span className="tabular-nums text-xs text-[var(--text-tertiary)]">
                    {events.length} {events.length === 1 ? 'report' : 'reports'}
                  </span>
                </div>

                {events.length === 0 ? (
                  <div className="px-4 py-6 text-center text-sm text-[var(--text-tertiary)]">
                    No earnings scheduled.
                  </div>
                ) : (
                  <div className="divide-y divide-[var(--border-subtle)]">
                    {events.map((event) => (
                      <Link
                        key={`${event.ticker}-${event.earnings_date}`}
                        href={`/stocks/${event.ticker}`}
                        className={cn(
                          'group row-hover flex flex-wrap items-center justify-between gap-3 px-4 py-3',
                          event.is_watchlisted && 'bg-[var(--accent-subtle)]'
                        )}
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          {event.is_watchlisted ? (
                            <Star className="h-3.5 w-3.5 shrink-0 fill-current text-[var(--accent)]" />
                          ) : null}
                          <span className="serif-num text-base text-[var(--text-primary)] transition-colors group-hover:text-[var(--accent)]">
                            {event.ticker}
                          </span>
                          <span className="truncate text-sm text-[var(--text-secondary)]">
                            {event.name || ''}
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <TimeHintBadge hint={event.time_hint} />
                          {event.eps_estimate !== null && event.eps_estimate !== undefined ? (
                            <span className="tabular-nums text-[var(--text-secondary)]">
                              Est. EPS {event.eps_estimate.toFixed(2)}
                            </span>
                          ) : null}
                          {event.market_cap !== null && event.market_cap !== undefined ? (
                            <span className="tabular-nums text-[var(--text-secondary)]">
                              {formatMarketCap(event.market_cap)}
                            </span>
                          ) : null}
                          <ChevronRight className="row-arrow h-4 w-4" strokeWidth={1.6} />
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
