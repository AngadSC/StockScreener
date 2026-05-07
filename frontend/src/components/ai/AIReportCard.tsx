'use client';

import { useEffect, useState } from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';

import AIReportButton from '@/components/ai/AIReportButton';
import AIReportNewsSection from '@/components/ai/AIReportNewsSection';
import AIReportSummaryCard from '@/components/ai/AIReportSummaryCard';
import AIReportThesisSection from '@/components/ai/AIReportThesisSection';
import { Button } from '@/components/ui/button';
import { generateAIReport } from '@/lib/api';
import type { AIReportOutput, AIReportState } from '@/types/ai';

const PRO_TIERS = new Set(['pro', 'trader', 'elite']);

interface AIReportCardProps {
  ticker: string;
  userTier: string;
}

function isProTier(userTier: string) {
  return PRO_TIERS.has(userTier.trim().toLowerCase());
}

function isSuccessResponse(
  response: Awaited<ReturnType<typeof generateAIReport>>
): response is Extract<Awaited<ReturnType<typeof generateAIReport>>, { report: AIReportOutput }> {
  return 'report' in response;
}

export default function AIReportCard({ ticker, userTier }: AIReportCardProps) {
  const [state, setState] = useState<AIReportState>(() =>
    isProTier(userTier) ? 'idle' : 'locked'
  );
  const [report, setReport] = useState<AIReportOutput | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const normalizedTicker = ticker.trim().toUpperCase();
  const locked = !isProTier(userTier) || state === 'locked';

  useEffect(() => {
    if (isProTier(userTier)) {
      setState((currentState) => (currentState === 'locked' ? 'idle' : currentState));
      return;
    }

    setState('locked');
  }, [userTier]);

  const handleGenerate = async () => {
    if (!isProTier(userTier)) {
      setState('locked');
      return;
    }

    setState('loading');
    setErrorMessage(null);

    try {
      const response = await generateAIReport(normalizedTicker);

      if (isSuccessResponse(response)) {
        setReport(response.report);
        setState('loaded');
        return;
      }

      if (response.error === 'not_pro') {
        setState('locked');
      } else {
        setState('error');
      }
      setErrorMessage(response.message);
    } catch {
      setState('error');
      setErrorMessage('Unable to generate the AI report. Please try again.');
    }
  };

  if (locked) {
    return (
      <section className="deco-panel p-6 md:p-7">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="eyebrow">AI Report</div>
            <h2 className="heading-lg mt-2 text-[var(--text-primary)]">{normalizedTicker}</h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              AI reports require a Pro, Trader, or Elite account tier.
            </p>
          </div>
          <AIReportButton ticker={normalizedTicker} userTier={userTier} onGenerate={handleGenerate} />
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-5">
      <section className="deco-panel p-6 md:p-7">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="eyebrow">AI Report</div>
            <h2 className="heading-lg mt-2 text-[var(--text-primary)]">{normalizedTicker}</h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Generate a setup-focused read using the latest cached market context.
            </p>
          </div>
          <AIReportButton ticker={normalizedTicker} userTier={userTier} onGenerate={handleGenerate} />
        </div>
      </section>

      {state === 'loading' ? (
        <section className="deco-panel p-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-[var(--accent)]/25 bg-[var(--accent-subtle)]">
            <RotateCcw className="h-5 w-5 animate-spin text-[var(--accent)]" />
          </div>
          <p className="mt-4 text-sm text-[var(--text-secondary)]">Generating AI report...</p>
        </section>
      ) : null}

      {state === 'error' ? (
        <section className="deco-panel p-6 md:p-7">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[var(--negative)]/25 bg-[var(--negative-bg)]">
                <AlertCircle className="h-5 w-5 text-[var(--negative)]" />
              </div>
              <div>
                <h3 className="heading-sm text-[var(--text-primary)]">Report unavailable</h3>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  {errorMessage ?? 'Unable to generate the AI report.'}
                </p>
              </div>
            </div>
            <Button onClick={handleGenerate} variant="outline">
              Retry
            </Button>
          </div>
        </section>
      ) : null}

      {state === 'loaded' && report ? (
        <>
          <AIReportSummaryCard report={report} />
          <AIReportThesisSection report={report} />
          <AIReportNewsSection report={report} />
        </>
      ) : null}
    </div>
  );
}
