import { redirect } from 'next/navigation';

interface PageProps {
  params: { ticker: string };
}

export default function StockBacktestRedirectPage({ params }: PageProps) {
  redirect(`/backtester?tickers=${encodeURIComponent(params.ticker.toUpperCase())}`);
}
