'use client';

import { useState } from 'react';
import { Lock, Loader2, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';

const PRO_TIERS = new Set(['pro', 'trader', 'elite']);

interface AIReportButtonProps {
  ticker: string;
  userTier: string;
  onGenerate: (ticker: string) => void | Promise<void>;
}

function isProTier(userTier: string) {
  return PRO_TIERS.has(userTier.trim().toLowerCase());
}

export default function AIReportButton({
  ticker,
  userTier,
  onGenerate,
}: AIReportButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);
  const canGenerate = isProTier(userTier);

  const handleClick = async () => {
    if (!canGenerate || isGenerating) return;

    setIsGenerating(true);
    try {
      await onGenerate(ticker);
    } finally {
      setIsGenerating(false);
    }
  };

  if (!canGenerate) {
    return (
      <Button disabled variant="outline">
        <Lock className="h-4 w-4" />
        Upgrade to Pro
      </Button>
    );
  }

  return (
    <Button disabled={isGenerating} onClick={handleClick}>
      {isGenerating ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Generating
        </>
      ) : (
        <>
          <Sparkles className="h-4 w-4" />
          Generate AI Report
        </>
      )}
    </Button>
  );
}
