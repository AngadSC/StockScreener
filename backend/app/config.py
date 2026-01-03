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
    
    # CORS - will be converted from string to list
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000"

    #API KEYS 
    FMP_API_KEY: str
    TIINGO_API_KEY:str
    
    # Stock Settings
    STOCK_UPDATE_HOUR: int = 21
    STOCK_UPDATE_BATCH_SIZE: int = 1000
    STOCK_CACHE_TTL: int = 86400
    STOCK_HISTORY_YEARS: int = 4

    # rate limiting
    YFINANCE_REQUESTS_PER_MINUTE: int = 15
    YFINANCE_MAX_RETRIES: int = 3
    YFINANCE_RETRY_DELAY: int = 5

    #FMP SETTINGS
    FMP_BASE_URL: str = "https://financialmodelingprep.com/api/v3"
    FMP_REQUESTS_PER_DAY: int = 250
    FMP_BATCH_SIZE: int = 100  
 
 
    # Tiingo Settings
    TIINGO_BASE_URL: str = "https://api.tiingo.com"
    TIINGO_REQUESTS_PER_HOUR: int = 50
    TIINGO_REQUESTS_PER_DAY: int = 1000


    #Cache TTLS
    SCREENER_CACHE_TTL: int = 3600  # 1 hour
    PRICE_HISTORY_CACHE_TTL: int = 7200  # 2 hours
    BACKTEST_CACHE_TTL: int = 7200  # 2 hours
    
    
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