'use client';

import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, StarOff } from 'lucide-react';

import { watchlistAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';

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
    <div className="container-custom space-y-6 py-8">
      <section className="deco-panel bg-grid-luxe p-8">
        <div className="deco-kicker">Curated Ledger</div>
        <h1 className="mt-3 text-5xl font-semibold text-glow">Watchlist</h1>
        <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
          Keep a compact ledger of the symbols you revisit most often.
        </p>
      </section>

      {isLoading ? (
        <div className="deco-panel p-12 text-center">
          <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading watchlist...</p>
        </div>
      ) : null}

      {isError ? (
        <div className="deco-panel p-8">
          <p className="mb-3 text-sm text-muted-foreground">
            Could not load your watchlist. Sign in and try again.
          </p>
          <Link href="/auth/login" className="deco-link text-sm uppercase tracking-[0.18em]">
            Go to login
          </Link>
        </div>
      ) : null}

      {!isLoading && !isError && data ? (
        <>
          <div className="deco-panel px-4 py-4 text-xs uppercase tracking-[0.22em] text-muted-foreground">
            Total items: {data.total}
          </div>

          {data.items.length === 0 ? (
            <div className="deco-panel p-10 text-center">
              <p className="mb-2 text-sm text-muted-foreground">No stocks in your watchlist yet.</p>
              <Link href="/screener" className="deco-link text-sm uppercase tracking-[0.18em]">
                Open screener
              </Link>
            </div>
          ) : (
            <div className="deco-panel overflow-hidden bg-card">
              <table className="deco-table">
                <thead className="bg-muted/20">
                  <tr>
                    <th>Ticker</th>
                    <th>Name</th>
                    <th>Added</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.id} className="border-b border-primary/10 last:border-b-0">
                      <td className="font-display text-lg uppercase tracking-[0.12em] text-primary">
                        <Link href={`/stocks/${item.ticker}`}>{item.ticker}</Link>
                      </td>
                      <td className="text-muted-foreground">{item.stock?.name || 'N/A'}</td>
                      <td className="text-muted-foreground">{new Date(item.added_at).toLocaleDateString()}</td>
                      <td className="text-right">
                        <Button
                          variant="ghost"
                          onClick={() => removeMutation.mutate(item.ticker)}
                          disabled={removeMutation.isPending}
                        >
                          <StarOff className="h-4 w-4" />
                          Remove
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}
