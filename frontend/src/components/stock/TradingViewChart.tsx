'use client';

import { memo, useEffect, useRef, useState } from 'react';
import { Loader2 } from 'lucide-react';

interface TradingViewChartProps {
  ticker: string;
  height?: number;
}

function TradingViewChart({ ticker, height = 500 }: TradingViewChartProps) {
  const container = useRef<HTMLDivElement>(null);
  const scriptLoadedRef = useRef(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadTradingViewScript = () => {
      if (scriptLoadedRef.current) return;

      const script = document.createElement('script');
      script.src = 'https://s3.tradingview.com/tv.js';
      script.async = true;
      script.onload = () => {
        scriptLoadedRef.current = true;
        initializeWidget();
      };
      document.head.appendChild(script);
    };

    const initializeWidget = () => {
      if (container.current && (window as any).TradingView) {
        container.current.innerHTML = '';

        new (window as any).TradingView.widget({
          autosize: true,
          symbol: ticker,
          interval: 'D',
          timezone: 'America/New_York',
          theme: 'dark',
          style: '1',
          locale: 'en',
          toolbar_bg: '#0f0f1a',
          enable_publishing: false,
          withdateranges: true,
          hide_side_toolbar: false,
          allow_symbol_change: false,
          save_image: true,
          container_id: 'tradingview_chart',
          studies: ['Volume@tv-basicstudies'],
          backgroundColor: '#0f0f1a',
          gridColor: 'rgba(61, 61, 96, 0.22)',
        });

        setTimeout(() => setIsLoading(false), 1500);
      }
    };

    if ((window as any).TradingView) {
      scriptLoadedRef.current = true;
      initializeWidget();
    } else {
      loadTradingViewScript();
    }

    return () => {
      if (container.current) {
        container.current.innerHTML = '';
      }
    };
  }, [ticker]);

  return (
    <div className="deco-panel bg-card">
      <div className="border-b border-border/70 bg-muted/20 px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Live Chart {ticker}</span>
          <div className="text-xs text-muted-foreground">Powered by TradingView</div>
        </div>
      </div>

      <div className="relative">
        {isLoading && (
          <div
            className="absolute inset-0 z-10 flex items-center justify-center bg-surface-1"
            style={{ height: `${height}px` }}
          >
            <div className="text-center">
              <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-primary" />
              <p className="text-xs text-muted-foreground">Initializing chart...</p>
            </div>
          </div>
        )}
        <div ref={container} id="tradingview_chart" style={{ height: `${height}px` }} className="bg-surface-1" />
      </div>

      <div className="border-t border-border/70 bg-muted/20 px-4 py-3 text-xs text-muted-foreground">
        Indicators | Drawing tools | Multi-timeframe | Volume analysis
      </div>
    </div>
  );
}

export default memo(TradingViewChart);
