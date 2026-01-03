from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import date

class StockDataProvider(ABC):
    """
    Abstract base class for stock data providers
    All providers must implement these methods
    """
    
    @abstractmethod
    def get_historical_prices(
        self, 
        ticker: str, 
        start_date: date, 
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data for a single stock
        
        Returns:
            DataFrame with columns: ['Open', 'High', 'Low', 'Close', 'Volume']
            Index: date
        """
        pass
    
    @abstractmethod
    def get_batch_historical_prices(
        self,
        tickers: List[str],
        start_date: date,
        end_date: date
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data for multiple stocks
        
        Returns:
            DataFrame in long format with columns:
            ['date', 'ticker', 'Open', 'High', 'Low', 'Close', 'Volume']
        """
        pass
    
    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch fundamental data for a single stock
        
        Returns:
            Dict with fundamental metrics
        """
        pass
    
    @abstractmethod
    def get_batch_fundamentals(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch fundamental data for multiple stocks
        
        Returns:
            Dict mapping ticker -> fundamentals dict
        """
        pass
    
    @abstractmethod
    def supports_batch(self) -> bool:
        """Does this provider support batch requests?"""
        pass
    
    @abstractmethod
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limit information for monitoring"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass
