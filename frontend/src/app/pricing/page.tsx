import Link from 'next/link';
import { Check, Clock, CreditCard } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ProCheckoutButton } from './ProCheckoutButton';

type Plan = {
  name: string;
  tier: string;
  price: string;
  priceNote: string;
  description: string;
  features: string[];
  status: 'available' | 'checkout' | 'soon';
  cta: string;
  highlight?: boolean;
  badge?: string;
};

const proFallbackCheckoutUrl = process.env.NEXT_PUBLIC_STRIPE_PRO_CHECKOUT_URL?.trim();

const plans: Plan[] = [
  {
    name: 'Free',
    tier: 'free',
    price: '$0',
    priceNote: 'Start with market tools',
    description: 'Core screening and research tools for getting a feel for the platform.',
    features: ['Market overview', 'Stock screener', 'Ticker profiles', 'Watchlist access'],
    status: 'available',
    cta: 'Create free account',
  },
  {
    name: 'Pro',
    tier: 'pro',
    price: '$19.99 USD',
    priceNote: 'Founders Edition',
    description: 'Unlock the AI Swing Analyzer and the active Pro workflow.',
    features: [
      'AI Swing Analyzer access',
      'Setup-focused AI reports',
      '150 AI reports monthly',
      'Founder pricing while available',
    ],
    status: 'checkout',
    cta: 'Continue to checkout',
    highlight: true,
    badge: 'Founders Edition',
  },
  {
    name: 'Trader',
    tier: 'trader',
    price: 'Coming soon',
    priceNote: 'Advanced tier',
    description: 'A higher-usage plan for more active research workflows.',
    features: ['Higher AI report limits', 'Expanded research tooling', 'Priority feature access'],
    status: 'soon',
    cta: 'Coming soon',
  },
  {
    name: 'Elite',
    tier: 'elite',
    price: 'Coming soon',
    priceNote: 'Highest tier',
    description: 'The top tier reserved for the most complete QuantorSignal feature set.',
    features: ['Highest AI limits', 'Premium workflow features', 'Early access experiments'],
    status: 'soon',
    cta: 'Coming soon',
  },
];

export default function PricingPage() {
  return (
    <div className="container-custom py-8 md:py-12">
      <div className="mx-auto max-w-6xl space-y-8">
        <section className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <div className="eyebrow">Pricing</div>
            <h1 className="heading-xl mt-3 text-[var(--text-primary)]">Choose your research tier</h1>
            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
              Start free, upgrade to Pro for AI reports, or keep an eye on the upcoming Trader and
              Elite tiers.
            </p>
          </div>
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-1)] px-4 py-2 text-sm text-[var(--text-secondary)]">
            <CreditCard className="h-4 w-4 text-[var(--accent)]" aria-hidden="true" />
            Secure checkout for Pro
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {plans.map((plan) => (
            <article
              key={plan.tier}
              className={cn(
                'flex min-h-[430px] flex-col rounded-[var(--radius-md)] border bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]',
                plan.highlight
                  ? 'border-[var(--accent)] shadow-[var(--glow-accent)]'
                  : 'border-[var(--border-subtle)]'
              )}
            >
              <div className="flex min-h-8 items-center justify-between gap-3">
                <h2 className="heading-md text-[var(--text-primary)]">{plan.name}</h2>
                {plan.badge ? <Badge>{plan.badge}</Badge> : null}
                {plan.status === 'soon' ? (
                  <Badge variant="secondary" className="gap-1.5">
                    <Clock className="h-3 w-3" aria-hidden="true" />
                    Soon
                  </Badge>
                ) : null}
              </div>

              <div className="mt-6">
                <div className="text-3xl font-semibold leading-tight text-[var(--text-primary)]">
                  {plan.price}
                </div>
                <p className="mt-1 text-xs font-medium uppercase tracking-[0.1em] text-[var(--text-tertiary)]">
                  {plan.priceNote}
                </p>
              </div>

              <p className="mt-5 min-h-[48px] text-sm leading-6 text-[var(--text-secondary)]">
                {plan.description}
              </p>

              <ul className="mt-6 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex gap-3 text-sm leading-5 text-[var(--text-secondary)]">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-[var(--positive)]" aria-hidden="true" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-auto pt-7">
                {plan.status === 'available' ? (
                  <Button asChild variant="outline" className="w-full rounded-full">
                    <Link href="/auth/register">{plan.cta}</Link>
                  </Button>
                ) : null}

                {plan.status === 'checkout' ? (
                  <ProCheckoutButton
                    label={plan.cta}
                    fallbackUrl={proFallbackCheckoutUrl}
                  />
                ) : null}

                {plan.status === 'soon' ? (
                  <Button disabled variant="outline" className="w-full rounded-full">
                    {plan.cta}
                  </Button>
                ) : null}
              </div>
            </article>
          ))}
        </section>

        <section className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-1)] p-5 md:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="eyebrow">Secure checkout</div>
              <h2 className="heading-md mt-2 text-[var(--text-primary)]">Pro access is granted automatically</h2>
              <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                After payment, Stripe notifies our backend and your account is upgraded to Pro
                immediately — no manual step required.
              </p>
            </div>
            <Button asChild variant="outline" className="rounded-full">
              <Link href="/ai-analyzer">Back to AI Analyzer</Link>
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
