from typing import Dict
from app.providers.base import StockDataProvider
from app.providers.yfinance_provider import YFinanceProvider
from app.providers.yahooquery_provider import YahooQueryProvider
from app.config import settings

class ProviderFactory:
    """
    Factory for creating and caching provider instances
    """
    _providers: Dict[str, StockDataProvider] = {}
    
    @classmethod
    def get_provider(cls, provider_name: str) -> StockDataProvider:
        """Get a provider by name (cached)"""
        
        # Return cached instance if exists
        if provider_name in cls._providers:
            return cls._providers[provider_name]
        
        # Create new instance
        if provider_name == "yfinance":
            provider = YFinanceProvider()
        elif provider_name == "yahooquery":
            provider = YahooQueryProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        # Cache and return
        cls._providers[provider_name] = provider
        return provider
    
    @classmethod
    def get_historical_provider(cls) -> StockDataProvider:
        """Get the configured historical data provider"""
        return cls.get_provider(settings.HISTORICAL_PROVIDER)
    
    @classmethod
    def get_realtime_provider(cls) -> StockDataProvider:
        """Get the configured realtime data provider"""
        return cls.get_provider(settings.REALTIME_PROVIDER)
    
    @classmethod
    def get_fundamentals_provider(cls) -> StockDataProvider:
        """Get the configured fundamentals provider"""
        return cls.get_provider(settings.FUNDAMENTALS_PROVIDER)
