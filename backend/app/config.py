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
    
    # Stock Settings
    STOCK_UPDATE_HOUR: int = 21
    STOCK_UPDATE_BATCH_SIZE: int = 1000
    STOCK_CACHE_TTL: int = 86400
    
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