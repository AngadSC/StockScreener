import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, Search, BarChart3, Brain } from 'lucide-react';

export default function HomePage() {
  const features = [
    {
      icon: Search,
      title: 'Advanced Screening',
      description: 'Filter 8,000+ US stocks by fundamentals, valuation, and financial health.',
    },
    {
      icon: BarChart3,
      title: 'Backtesting',
      description: 'Test your trading strategies with historical data and technical indicators.',
    },
    {
      icon: Brain,
      title: 'ML Features',
      description: 'Get ML-ready datasets with 23+ technical indicators for price prediction.',
    },
    {
      icon: TrendingUp,
      title: 'Real-time Data',
      description: 'Daily updates with end-of-day fundamentals and price data.',
    },
  ];

  return (
    <div className="flex flex-col">
      {/* Hero Section */}
      <section className="container py-24 text-center">
        <div className="mx-auto max-w-3xl space-y-6">
          <h1 className="text-5xl font-bold tracking-tight">
            Find Your Perfect Stock
          </h1>
          <p className="text-xl text-muted-foreground">
            Advanced stock screener with backtesting and machine learning capabilities.
            Filter, analyze, and backtest stocks with professional-grade tools.
          </p>
          <div className="flex justify-center gap-4 pt-4">
            <Link href="/screener">
              <Button size="lg">
                <Search className="mr-2 h-5 w-5" />
                Start Screening
              </Button>
            </Link>
            <Link href="/auth/register">
              <Button size="lg" variant="outline">
                Sign Up Free
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container py-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          Everything You Need
        </h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <Card key={feature.title}>
                <CardHeader>
                  <Icon className="h-10 w-10 text-primary mb-2" />
                  <CardTitle>{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{feature.description}</CardDescription>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Stats Section */}
      <section className="container py-16">
        <div className="grid gap-6 md:grid-cols-3 text-center">
          <div>
            <p className="text-4xl font-bold text-primary">8,000+</p>
            <p className="text-muted-foreground mt-2">US Stocks</p>
          </div>
          <div>
            <p className="text-4xl font-bold text-primary">23+</p>
            <p className="text-muted-foreground mt-2">Technical Indicators</p>
          </div>
          <div>
            <p className="text-4xl font-bold text-primary">10 Years</p>
            <p className="text-muted-foreground mt-2">Historical Data</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container py-24 text-center">
        <div className="mx-auto max-w-2xl space-y-6">
          <h2 className="text-3xl font-bold">
            Ready to Find Your Next Investment?
          </h2>
          <p className="text-lg text-muted-foreground">
            Join thousands of investors using data-driven stock screening.
          </p>
          <Link href="/screener">
            <Button size="lg">
              Get Started Now
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
