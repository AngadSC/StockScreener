'use client';

import Link from 'next/link';
import { Check, Clock, CreditCard } from 'lucide-react';

import { ManageSubscriptionButton } from '@/components/billing/ManageSubscriptionButton';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { isProTier, useAuth } from '@/lib/auth';
import { cn } from '@/lib/utils';
import type { PaidTier } from '@/types/user';
import { CheckoutButton } from './CheckoutButton';

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
    description: 'Structured AI swing reports for any US ticker.',
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
    price: '$39.99 USD',
    priceNote: 'Founders Edition',
    description: 'A higher-usage plan for more active research workflows.',
    features: [
      'Everything in Pro',
      '400 AI reports monthly',
      'Daily Market Brief email every market morning',
      'Watchlist earnings & signal alerts (rolling out)',
    ],
    status: 'checkout',
    cta: 'Continue to checkout',
    badge: 'Founders Edition',
  },
  {
    name: 'Elite',
    tier: 'elite',
    price: '$79.99 USD',
    priceNote: 'Founders Edition',
    description: 'The top tier reserved for the most complete QuantorSignal feature set.',
    features: [
      'Everything in Trader',
      '1,000 AI reports monthly',
      'Daily Watchlist AI Digest — pre-market AI analysis of up to 10 watchlist stocks, emailed',
      'Early access to new features',
    ],
    status: 'checkout',
    cta: 'Continue to checkout',
    badge: 'Founders Edition',
  },
];

interface PlanCtaProps {
  plan: Plan;
  isCurrent: boolean;
  isLoggedIn: boolean;
  userTier: string;
}

function PlanCta({ plan, isCurrent, isLoggedIn, userTier }: PlanCtaProps) {
  // The plan the user is already on never offers checkout again — a second
  // Checkout Session would bill them twice, so send them to the portal instead.
  if (isCurrent) {
    if (isProTier(userTier)) {
      return (
        <div className="[&_button]:w-full">
          <ManageSubscriptionButton userTier={userTier} />
        </div>
      );
    }
    return (
      <Button disabled variant="outline" className="w-full rounded-full">
        Current plan
      </Button>
    );
  }

  if (plan.status === 'available') {
    // Signed-in subscribers already have everything in the free plan.
    if (isLoggedIn) {
      return (
        <Button disabled variant="outline" className="w-full rounded-full">
          Included in your plan
        </Button>
      );
    }
    return (
      <Button asChild variant="outline" className="w-full rounded-full">
        <Link href="/auth/register">{plan.cta}</Link>
      </Button>
    );
  }

  if (plan.status === 'checkout') {
    return (
      <CheckoutButton
        tier={plan.tier as PaidTier}
        label={plan.cta}
        fallbackUrl={plan.tier === 'pro' ? proFallbackCheckoutUrl : undefined}
      />
    );
  }

  return (
    <Button disabled variant="outline" className="w-full rounded-full">
      {plan.cta}
    </Button>
  );
}

export default function PricingPage() {
  const { isLoggedIn, userTier } = useAuth();
  const normalizedTier = userTier.trim().toLowerCase();

  return (
    <div className="container-custom py-8 md:py-12">
      <div className="mx-auto max-w-6xl space-y-8">
        <section className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <div className="eyebrow">Pricing</div>
            <h1 className="heading-xl mt-3 text-[var(--text-primary)]">Choose your research tier</h1>
            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)]">
              Start free, or upgrade to Pro, Trader, or Elite for AI reports and higher
              monthly limits.
            </p>
          </div>
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-[var(--border-default)] bg-[var(--bg-surface-1)] px-4 py-2 text-sm text-[var(--text-secondary)]">
            <CreditCard className="h-4 w-4 text-[var(--text-tertiary)]" aria-hidden="true" strokeWidth={1.6} />
            Secure checkout
          </div>
        </section>

        {isLoggedIn && isProTier(normalizedTier) ? (
          <p className="text-sm leading-6 text-[var(--text-secondary)]">
            You are on the {normalizedTier.charAt(0).toUpperCase() + normalizedTier.slice(1)} plan.
            Switching plans or cancelling happens in Manage subscription — starting a second
            checkout would bill you twice.
          </p>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {plans.map((plan) => {
            const isCurrent = isLoggedIn && plan.tier === normalizedTier;

            return (
              <article
                key={plan.tier}
                className={cn(
                  'flex min-h-[430px] flex-col rounded-[var(--radius-md)] border bg-[var(--bg-surface-1)] p-5 shadow-[var(--shadow-sm)]',
                  plan.highlight || isCurrent
                    ? 'border-[var(--accent)] shadow-[var(--glow-accent)]'
                    : 'border-[var(--border-subtle)]'
                )}
              >
                <div className="flex min-h-8 items-center justify-between gap-3">
                  <h2 className="heading-md text-[var(--text-primary)]">{plan.name}</h2>
                  {isCurrent ? <Badge>Current plan</Badge> : plan.badge ? <Badge>{plan.badge}</Badge> : null}
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
                  <PlanCta
                    plan={plan}
                    isCurrent={isCurrent}
                    isLoggedIn={isLoggedIn}
                    userTier={normalizedTier}
                  />
                </div>
              </article>
            );
          })}
        </section>

        <section className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] bg-[var(--bg-surface-1)] p-5 md:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <div className="eyebrow">Secure checkout</div>
              <h2 className="heading-md mt-2 text-[var(--text-primary)]">Access is granted automatically</h2>
              <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                After payment, Stripe notifies our backend and your account is upgraded to your
                chosen tier immediately — no manual step required.
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
