from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import date, datetime
import time
import random
from yahooquery import Ticker
from app.providers.base import StockDataProvider
from app.config import settings


class YahooQueryProvider(StockDataProvider):
    """
    YahooQuery provider - BEST for batch fundamentals.
    
    Advantages over yfinance:
    - TRUE batch fundamentals (single API call for 50+ tickers)
    - More reliable data modules
    - Better structured response
    
    Use for:
    - Fundamentals only (primary use case)
    - Batch operations (10x faster than yfinance for fundamentals)
    """
    
    def __init__(self):
        self._request_count = 0
    
    @property
    def name(self) -> str:
        return "yahooquery"
    
    def _apply_jitter(self):
        """Apply random sleep to avoid rate limiting (uses config settings)"""
        if not settings.RATE_LIMIT_ENABLED:
            return
        
        sleep_time = random.uniform(
            settings.YAHOOQUERY_JITTER_MIN,
            settings.YAHOOQUERY_JITTER_MAX
        )
        
        time.sleep(sleep_time)
    
    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch fundamental data for single stock.
        
        Uses yahooquery modules:
        - summaryDetail: P/E, market cap, etc.
        - defaultKeyStatistics: Beta, margins, etc.
        - financialData: ROE, debt ratios, etc.
        - price: Current price info
        """
        try:
            ticker_obj = Ticker(ticker)
            
            # Fetch all relevant modules in one call
            modules = ticker_obj.get_modules([
                'summaryDetail',
                'defaultKeyStatistics',
                'financialData',
                'price'
            ])
            
            # Check for errors
            if ticker not in modules:
                print(f"✗ No data for {ticker}")
                return None
            
            data = modules[ticker]
            
            # Check if response is an error string
            if isinstance(data, str) or 'error' in str(data).lower():
                print(f"✗ Error fetching {ticker}: {data}")
                return None
            
            # Extract modules
            summary = data.get('summaryDetail', {})
            stats = data.get('defaultKeyStatistics', {})
            financials = data.get('financialData', {})
            price_data = data.get('price', {})
            
            # Build normalized fundamentals dict
            fundamentals = {
                'ticker': ticker,
                
                # Valuation
                'pe_ratio': summary.get('trailingPE'),
                'forward_pe': summary.get('forwardPE'),
                'peg_ratio': stats.get('pegRatio'),
                'price_to_book': stats.get('priceToBook'),
                'price_to_sales': stats.get('priceToSalesTrailing12Months'),
                'ev_to_ebitda': stats.get('enterpriseToEbitda'),
                
                # Profitability
                'profit_margin': financials.get('profitMargins'),
                'operating_margin': financials.get('operatingMargins'),
                'roe': financials.get('returnOnEquity'),
                'roa': financials.get('returnOnAssets'),
                
                # Financial Health
                'debt_to_equity': financials.get('debtToEquity'),
                'current_ratio': financials.get('currentRatio'),
                'quick_ratio': financials.get('quickRatio'),
                
                # Growth
                'revenue_growth': financials.get('revenueGrowth'),
                'earnings_growth': financials.get('earningsGrowth'),
                
                # Dividends
                'dividend_yield': summary.get('dividendYield'),
                'dividend_rate': summary.get('dividendRate'),
                'payout_ratio': summary.get('payoutRatio'),
                
                # Size & Trading
                'market_cap': summary.get('marketCap') or price_data.get('marketCap'),
                'volume': summary.get('volume') or price_data.get('regularMarketVolume'),
                'avg_volume': summary.get('averageVolume') or summary.get('averageVolume10days'),
                'beta': stats.get('beta'),
                
                # Price
                'current_price': price_data.get('regularMarketPrice') or summary.get('regularMarketPrice'),
                'day_change_percent': price_data.get('regularMarketChangePercent'),
                'fifty_two_week_high': summary.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': summary.get('fiftyTwoWeekLow'),
                
                # Classification
                'sector': price_data.get('sector'),
                'industry': price_data.get('industry'),
                
                # Store raw data for anything we missed
                'additional_data': {
                    'summary': summary,
                    'stats': stats,
                    'financials': financials,
                    'price': price_data
                }
            }
            
            self._request_count += 1
            
            # Apply jitter for rate limiting
            self._apply_jitter()
            
            return fundamentals
            
        except Exception as e:
            print(f"✗ YahooQuery error for {ticker}: {e}")
            return None
    
    def get_batch_fundamentals(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch fundamentals for multiple stocks in ONE API call.
        
        This is the KEY advantage over yfinance:
        - yfinance: 50 tickers = 50 API calls
        - yahooquery: 50 tickers = 1 API call (50x faster!)
        
        Args:
            tickers: List of ticker symbols
        
        Returns:
            Dict mapping ticker -> fundamentals dict
        """
        if not tickers:
            return {}
        
        try:
            print(f"📦 Fetching batch fundamentals for {len(tickers)} tickers...")
            
            # Create Ticker object with all symbols
            ticker_obj = Ticker(tickers)
            
            # Fetch all modules in ONE API call
            modules = ticker_obj.get_modules([
                'summaryDetail',
                'defaultKeyStatistics',
                'financialData',
                'price'
            ])
            
            results = {}
            
            # Process each ticker's data
            for ticker_symbol in tickers:
                if ticker_symbol not in modules:
                    continue
                
                data = modules[ticker_symbol]
                
                # Skip errors
                if isinstance(data, str) or 'error' in str(data).lower():
                    continue
                
                # Extract modules
                summary = data.get('summaryDetail', {})
                stats = data.get('defaultKeyStatistics', {})
                financials = data.get('financialData', {})
                price_data = data.get('price', {})
                
                # Build normalized fundamentals
                fundamentals = {
                    'ticker': ticker_symbol,
                    
                    # Valuation
                    'pe_ratio': summary.get('trailingPE'),
                    'forward_pe': summary.get('forwardPE'),
                    'peg_ratio': stats.get('pegRatio'),
                    'price_to_book': stats.get('priceToBook'),
                    'price_to_sales': stats.get('priceToSalesTrailing12Months'),
                    'ev_to_ebitda': stats.get('enterpriseToEbitda'),
                    
                    # Profitability
                    'profit_margin': financials.get('profitMargins'),
                    'operating_margin': financials.get('operatingMargins'),
                    'roe': financials.get('returnOnEquity'),
                    'roa': financials.get('returnOnAssets'),
                    
                    # Financial Health
                    'debt_to_equity': financials.get('debtToEquity'),
                    'current_ratio': financials.get('currentRatio'),
                    'quick_ratio': financials.get('quickRatio'),
                    
                    # Growth
                    'revenue_growth': financials.get('revenueGrowth'),
                    'earnings_growth': financials.get('earningsGrowth'),
                    
                    # Dividends
                    'dividend_yield': summary.get('dividendYield'),
                    'dividend_rate': summary.get('dividendRate'),
                    'payout_ratio': summary.get('payoutRatio'),
                    
                    # Size & Trading
                    'market_cap': summary.get('marketCap') or price_data.get('marketCap'),
                    'volume': summary.get('volume') or price_data.get('regularMarketVolume'),
                    'avg_volume': summary.get('averageVolume') or summary.get('averageVolume10days'),
                    'beta': stats.get('beta'),
                    
                    # Price
                    'current_price': price_data.get('regularMarketPrice') or summary.get('regularMarketPrice'),
                    'day_change_percent': price_data.get('regularMarketChangePercent'),
                    'fifty_two_week_high': summary.get('fiftyTwoWeekHigh'),
                    'fifty_two_week_low': summary.get('fiftyTwoWeekLow'),
                    
                    # Classification
                    'sector': price_data.get('sector'),
                    'industry': price_data.get('industry'),
                    
                    # Store raw data
                    'additional_data': {
                        'summary': summary,
                        'stats': stats,
                        'financials': financials,
                        'price': price_data
                    }
                }
                
                results[ticker_symbol] = fundamentals
            
            self._request_count += 1
            
            # Apply jitter AFTER batch (one delay for all tickers)
            self._apply_jitter()
            
            print(f"✓ Fetched {len(results)}/{len(tickers)} fundamentals successfully")
            return results
            
        except Exception as e:
            print(f"✗ YahooQuery batch error: {e}")
            return {}
    
    def get_historical_prices(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        yahooquery CAN fetch historical prices, but yfinance is better for this.
        We use yahooquery ONLY for fundamentals.
        
        This method is included for interface compliance but should not be used.
        """
        print(f"⚠️  Warning: yahooquery provider is for fundamentals only. Use yfinance for historical prices.")
        return None
    
    def get_batch_historical_prices(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date,
        is_bulk_load: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Not implemented - use yfinance for historical prices.
        """
        print(f"⚠️  Warning: yahooquery provider is for fundamentals only. Use yfinance for historical prices.")
        return None
    
    def supports_batch(self) -> bool:
        """
        YES! yahooquery has EXCELLENT batch support for fundamentals.
        This is its main advantage over yfinance.
        """
        return True
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Return rate limit info for monitoring"""
        return {
            'provider': 'yahooquery',
            'requests_made': self._request_count,
            'rate_limit': 'Unknown (uses Yahoo Finance API)',
            'jitter_config': {
                'enabled': settings.RATE_LIMIT_ENABLED,
                'min': settings.YAHOOQUERY_JITTER_MIN,
                'max': settings.YAHOOQUERY_JITTER_MAX
            },
            'note': 'Batch requests count as 1 request regardless of ticker count'
        }
