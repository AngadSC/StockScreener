import BacktesterWorkspace from '@/components/backtester/BacktesterWorkspace';

interface BacktesterPageProps {
  searchParams?: {
    tickers?: string;
  };
}

export default function BacktesterPage({ searchParams }: BacktesterPageProps) {
  const tickers =
    searchParams?.tickers
      ?.split(',')
      .map((ticker) => ticker.trim().toUpperCase())
      .filter(Boolean) ?? [];

  return <BacktesterWorkspace initialTickers={tickers} />;
}
