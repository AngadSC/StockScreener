from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
from pathlib import Path 
import os

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Stock Screener API"
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000"
    
    # ===== DATA PROVIDERS =====
    HISTORICAL_PROVIDER: str = "yfinance"
    REALTIME_PROVIDER: str = "yfinance"
    FUNDAMENTALS_PROVIDER: str = "yahooquery"
    FUNDAMENTALS_FALLBACK: str = "yfinance"
    
    # ===== YFINANCE SETTINGS =====
    YFINANCE_ENABLED: bool = True
    YFINANCE_BATCH_SIZE: int = 100
    YFINANCE_INITIAL_JITTER_MIN: int = 15  # Seconds between batches during initial load
    YFINANCE_INITIAL_JITTER_MAX: int = 25
    YFINANCE_DAILY_JITTER_MIN: int = 2     # Seconds between batches during daily update
    YFINANCE_DAILY_JITTER_MAX: int = 5
    
    # ===== YAHOOQUERY SETTINGS =====
    YAHOOQUERY_ENABLED: bool = True
    YAHOOQUERY_BATCH_SIZE: int = 50
    YAHOOQUERY_JITTER_MIN: int = 10
    YAHOOQUERY_JITTER_MAX: int = 15
    
    # ===== DATA SETTINGS =====
    STOCK_HISTORY_YEARS: int = 5
    FUNDAMENTALS_UPDATE_CYCLE_DAYS: int = 7  # Full refresh in 7 days
    
    # ===== REDIS CACHE SETTINGS =====
    STOCK_CACHE_TTL: int = 86400              # 24 hours for basic stock info
    STOCK_DETAIL_CACHE_TTL: int = 7200        # 2 hours for detailed stock views
    SCREENER_CACHE_TTL: int = 3600            # 1 hour for screener results
    PRICE_HISTORY_CACHE_TTL: int = 7200       # 2 hours for price history
    SCREENER_USE_CACHE: bool = False          # Always query PostgreSQL for screener
    
    # ===== RATE LIMITING =====
    RATE_LIMIT_ENABLED: bool = True
    
    # Environment
    ENVIRONMENT: str = "development"
    
    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors(cls, v):
        """Convert comma-separated string to list of origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        case_sensitive = True

settings = Settings()
