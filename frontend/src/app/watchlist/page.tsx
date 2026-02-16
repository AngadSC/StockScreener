'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, StarOff } from 'lucide-react';
import { watchlistAPI } from '@/lib/api';

export default function WatchlistPage() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => watchlistAPI.getWatchlist(),
  });

  const removeMutation = useMutation({
    mutationFn: (ticker: string) => watchlistAPI.removeFromWatchlist(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
  });

  return (
    <div className="container py-6">
      <div className="border-b border-border pb-6 mb-8">
        <h1 className="text-3xl font-bold text-glow mb-2">WATCHLIST.DASHBOARD</h1>
        <p className="text-sm text-muted-foreground font-mono">
          Track and manage your saved tickers
        </p>
      </div>

      {isLoading && (
        <div className="terminal-border bg-card p-12 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-xs text-muted-foreground">LOADING_WATCHLIST...</p>
        </div>
      )}

      {isError && (
        <div className="terminal-border bg-card p-6">
          <p className="text-sm text-muted-foreground mb-3">
            Could not load watchlist. Log in and try again.
          </p>
          <Link href="/auth/login" className="text-primary hover:underline text-sm">
            Go to login
          </Link>
        </div>
      )}

      {!isLoading && !isError && data && (
        <>
          <div className="terminal-border bg-card px-4 py-3 mb-4 text-xs text-muted-foreground font-mono">
            TOTAL_ITEMS: {data.total}
          </div>

          {data.items.length === 0 ? (
            <div className="terminal-border bg-card p-8 text-center">
              <p className="text-sm text-muted-foreground mb-2">No stocks in watchlist yet.</p>
              <Link href="/screener" className="text-primary hover:underline text-sm">
                Open screener
              </Link>
            </div>
          ) : (
            <div className="terminal-border bg-card overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/30 border-b border-border">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-mono text-muted-foreground">
                      TICKER
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-muted-foreground">
                      NAME
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-mono text-muted-foreground">
                      ADDED
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-mono text-muted-foreground">
                      ACTION
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.id} className="border-b border-border/60 last:border-b-0">
                      <td className="px-4 py-3">
                        <Link href={`/stocks/${item.ticker}`} className="text-primary hover:underline">
                          {item.ticker}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {item.stock?.name || 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {new Date(item.added_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => removeMutation.mutate(item.ticker)}
                          disabled={removeMutation.isPending}
                          className="inline-flex items-center gap-2 px-3 py-1.5 border border-border hover:border-primary hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <StarOff className="h-3.5 w-3.5" />
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
