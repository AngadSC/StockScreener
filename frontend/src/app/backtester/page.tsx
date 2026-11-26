import BacktesterWorkspace from '@/components/backtester/BacktesterWorkspace';

interface BacktesterPageProps {
  searchParams?: Promise<{
    tickers?: string;
  }>;
}

export default async function BacktesterPage(props: BacktesterPageProps) {
  const searchParams = await props.searchParams;
  const tickers =
    searchParams?.tickers
      ?.split(',')
      .map((ticker) => ticker.trim().toUpperCase())
      .filter(Boolean) ?? [];

  return <BacktesterWorkspace initialTickers={tickers} />;
}
