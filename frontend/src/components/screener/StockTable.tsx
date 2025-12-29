'use client';

import Link from 'next/link';
import { Stock } from '@/types/stock';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowUpDown, TrendingUp, TrendingDown, ExternalLink } from 'lucide-react';
import { formatCurrency, formatMarketCap, formatPercent, getChangeColor } from '@/lib/utils';

interface StockTableProps {
  stocks: Stock[];
  isLoading?: boolean;
  onSort?: (field: string) => void;
}

export default function StockTable({ stocks, isLoading, onSort }: StockTableProps) {
  if (isLoading) {
    return (
      <div className="w-full space-y-4">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="h-16 bg-muted animate-pulse rounded" />
        ))}
      </div>
    );
  }

  if (stocks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <TrendingUp className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold">No stocks found</h3>
        <p className="text-sm text-muted-foreground mt-2">
          Try adjusting your filters to see more results
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">Ticker</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Sector</TableHead>
            <TableHead className="text-right">
              <Button variant="ghost" size="sm" onClick={() => onSort?.('current_price')}>
                Price
                <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            </TableHead>
            <TableHead className="text-right">Change</TableHead>
            <TableHead className="text-right">
              <Button variant="ghost" size="sm" onClick={() => onSort?.('market_cap')}>
                Market Cap
                <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            </TableHead>
            <TableHead className="text-right">
              <Button variant="ghost" size="sm" onClick={() => onSort?.('pe_ratio')}>
                P/E Ratio
                <ArrowUpDown className="ml-2 h-4 w-4" />
              </Button>
            </TableHead>
            <TableHead className="text-right">Div Yield</TableHead>
            <TableHead className="w-[100px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {stocks.map((stock) => (
            <TableRow key={stock.ticker} className="hover:bg-muted/50">
              <TableCell className="font-mono font-bold">
                {stock.ticker}
              </TableCell>
              
              <TableCell>
                <div className="max-w-[200px] truncate">
                  {stock.name || 'N/A'}
                </div>
              </TableCell>
              
              <TableCell>
                {stock.sector ? (
                  <Badge variant="outline">{stock.sector}</Badge>
                ) : (
                  <span className="text-muted-foreground">N/A</span>
                )}
              </TableCell>
              
              <TableCell className="text-right font-medium">
                {formatCurrency(stock.current_price)}
              </TableCell>
              
              <TableCell className="text-right">
                <div className={`flex items-center justify-end gap-1 ${getChangeColor(stock.day_change_percent)}`}>
                  {stock.day_change_percent !== null && stock.day_change_percent !== undefined ? (
                    <>
                      {stock.day_change_percent >= 0 ? (
                        <TrendingUp className="h-4 w-4" />
                      ) : (
                        <TrendingDown className="h-4 w-4" />
                      )}
                      <span className="font-medium">
                        {formatPercent(stock.day_change_percent)}
                      </span>
                    </>
                  ) : (
                    <span className="text-muted-foreground">N/A</span>
                  )}
                </div>
              </TableCell>
              
              <TableCell className="text-right">
                {formatMarketCap(stock.market_cap)}
              </TableCell>
              
              <TableCell className="text-right">
                {stock.pe_ratio ? stock.pe_ratio.toFixed(2) : 'N/A'}
              </TableCell>
              
              <TableCell className="text-right">
                {stock.dividend_yield 
                  ? `${(stock.dividend_yield * 100).toFixed(2)}%` 
                  : 'N/A'
                }
              </TableCell>
              
              <TableCell>
                <Link href={`/stocks/${stock.ticker}`}>
                  <Button variant="ghost" size="sm">
                    View
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
