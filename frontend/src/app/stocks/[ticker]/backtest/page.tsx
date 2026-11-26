import { redirect } from 'next/navigation';

interface PageProps {
  params: Promise<{ ticker: string }>;
}

export default async function StockBacktestRedirectPage(props: PageProps) {
  const params = await props.params;
  redirect(`/backtester?tickers=${encodeURIComponent(params.ticker.toUpperCase())}`);
}
