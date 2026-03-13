'use client';

import { useEffect, useRef, memo, useState } from 'react';
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
    // Load TradingView widget script
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
        // Clear previous widget
        container.current.innerHTML = '';

        new (window as any).TradingView.widget({
          autosize: true,
          symbol: ticker,
          interval: 'D',
          timezone: 'America/New_York',
          theme: 'dark',
          style: '1', // 1 = Candles
          locale: 'en',
          toolbar_bg: '#131722',
          enable_publishing: false,
          withdateranges: true,
          hide_side_toolbar: false,
          allow_symbol_change: false,
          save_image: true,
          container_id: 'tradingview_chart',
          // Advanced features
          studies: [
            'Volume@tv-basicstudies',
          ],
          // Theme colors matching our design
          backgroundColor: '#131722',
          gridColor: 'rgba(42, 46, 57, 0.3)',
          // Hide TradingView branding (only available with premium)
          // hide_legend: false,
          // hide_top_toolbar: false,
        });

        // Set loading to false after a brief delay to allow widget to render
        setTimeout(() => setIsLoading(false), 1500);
      }
    };

    // Check if script is already loaded
    if ((window as any).TradingView) {
      scriptLoadedRef.current = true;
      initializeWidget();
    } else {
      loadTradingViewScript();
    }

    // Cleanup on unmount
    return () => {
      if (container.current) {
        container.current.innerHTML = '';
      }
    };
  }, [ticker]);

  return (
    <div className="deco-panel bg-card">
      <div className="border-b border-primary/12 px-4 py-3 bg-muted/20">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-[0.22em]">Live Chart {ticker}</span>
          <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">
            Powered by TradingView
          </div>
        </div>
      </div>

      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#131722]" style={{ height: `${height}px` }}>
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
              <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Initializing chart...</p>
            </div>
          </div>
        )}
        <div
          ref={container}
          id="tradingview_chart"
          style={{ height: `${height}px` }}
          className="bg-[#131722]"
        />
      </div>

      <div className="border-t border-primary/12 px-4 py-3 bg-muted/20 text-xs uppercase tracking-[0.2em] text-muted-foreground">
        Indicators | Drawing tools | Multi timeframe | Volume analysis
      </div>
    </div>
  );
}

export default memo(TradingViewChart);
