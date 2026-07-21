from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field, field_validator
from typing import List, Union
from pathlib import Path 
import json

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "https://quantorsignal.com",
    "https://www.quantorsignal.com",
]

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AUTH_COOKIE_NAME: str = "access_token"
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Stock Screener API"
    
    # CORS
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = DEFAULT_CORS_ORIGINS
    
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
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10
    RATE_LIMIT_REGISTER_PER_5_MINUTES: int = 20
    RATE_LIMIT_HEAVY_PER_MINUTE: int = 20
    RATE_LIMIT_SCREENER_PER_MINUTE: int = 120
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 300

    # ===== AI SETTINGS =====
    news_api_key: str = Field(default="", validation_alias=AliasChoices("NEWS_API_KEY", "news_api_key"))
    ai_provider: str = Field(default="anthropic", validation_alias=AliasChoices("AI_PROVIDER", "ai_provider"))
    ai_model: str = Field(default="claude-sonnet-4-6", validation_alias=AliasChoices("AI_MODEL", "ai_model"))
    ai_api_key: str = Field(default="", validation_alias=AliasChoices("AI_API_KEY", "ai_api_key"))
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key"),
    )
    openai_api_key: str = Field(default="", validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"))
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias=AliasChoices(
            "OPENAI_BASE_URL",
            "OPENAI_COMPATIBLE_BASE_URL",
            "AI_BASE_URL",
            "openai_base_url",
        ),
    )
    ai_monthly_report_limit_pro: int = Field(
        default=150,
        validation_alias=AliasChoices("AI_MONTHLY_REPORT_LIMIT_PRO", "ai_monthly_report_limit_pro"),
    )
    ai_monthly_report_limit_trader: int = Field(
        default=400,
        validation_alias=AliasChoices("AI_MONTHLY_REPORT_LIMIT_TRADER", "ai_monthly_report_limit_trader"),
    )
    ai_monthly_report_limit_elite: int = Field(
        default=1000,
        validation_alias=AliasChoices("AI_MONTHLY_REPORT_LIMIT_ELITE", "ai_monthly_report_limit_elite"),
    )

    # ===== STRIPE BILLING =====
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    STRIPE_TRADER_PRICE_ID: str = ""
    STRIPE_ELITE_PRICE_ID: str = ""
    STRIPE_SUCCESS_URL: str = "http://localhost:3000/ai-analyzer?checkout=success"
    STRIPE_CANCEL_URL: str = "http://localhost:3000/pricing?checkout=cancelled"
    STRIPE_PORTAL_RETURN_URL: str = "http://localhost:3000/ai-analyzer"

    # ===== SEC EDGAR (Insider Activity / Form 4) =====
    # Mandatory politeness: EDGAR requires a descriptive User-Agent on every request.
    EDGAR_USER_AGENT: str = "QuantorSignal contact@quantorsignal.com"
    # Throttle to stay under EDGAR's 10 req/sec fair-access ceiling (we target ~4.5/sec).
    EDGAR_MIN_REQUEST_INTERVAL: float = 0.22
    EDGAR_CIK_MAP_TTL: int = 86400            # Cache ticker->CIK map for a day
    EDGAR_BACKFILL_DAYS: int = 7              # Days to backfill on first/empty run
    EDGAR_ACTIVITY_CACHE_TTL: int = 300       # Public insider-activity endpoint cache

    # ===== ADMIN ACCESS =====
    ADMIN_EMAILS: Union[str, List[str]] = []
    
    # Environment
    ENVIRONMENT: str = "development"

    # ===== EMAIL (Resend) =====
    # Transactional / lifecycle email via the Resend HTTP API. The sending
    # domain in EMAIL_FROM must be verified in the Resend dashboard (SPF/DKIM)
    # before mail will deliver. Leave EMAIL_ENABLED False to make all sends
    # no-op (logged as "skipped") until credentials/domain are ready.
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "QuantorSignal <alerts@quantorsignal.com>"
    EMAIL_REPLY_TO: str = ""  # optional; empty means no Reply-To header
    EMAIL_ENABLED: bool = False
    # Public base URL used to build unsubscribe links (must route /api/v1/* to
    # this backend). Falls back to the marketing domain.
    PUBLIC_APP_URL: str = "https://quantorsignal.com"

    # ===== DAILY MARKET BRIEF =====
    # Master switch for the once-per-day AI market brief email (Trader/Elite).
    # When False, the scheduled job exits early (no LLM call, no sends).
    DAILY_BRIEF_ENABLED: bool = True

    # ===== ELITE DAILY WATCHLIST AI DIGEST =====
    # Feature flag for the morning "Daily Watchlist AI Digest" email sent to
    # Elite users. When False, the scheduled job logs and exits (an admin can
    # still force a run for testing). EMAIL_ENABLED is a separate hard gate.
    WATCHLIST_DIGEST_ENABLED: bool = True
    # Max number of watchlist tickers analyzed per user's digest (oldest first).
    # Caps per-user LLM cost; extra tickers are noted as "showing N of M".
    ELITE_DIGEST_MAX_STOCKS: int = 10
    # Global safety cap on fresh LLM report generations across a single digest
    # run. Once exceeded, remaining users get digests built from cached reports
    # only (no new LLM calls). Cached (already-generated-today) reports are free.
    DIGEST_MAX_LLM_CALLS_PER_RUN: int = 300

    @field_validator('BACKEND_CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors(cls, v):
        """Accept JSON array or comma-separated origins and normalize them."""
        parsed_origins: List[str] = []
        if isinstance(v, str):
            value = v.strip()
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        parsed_origins = [str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()]
                except json.JSONDecodeError:
                    pass
            if not parsed_origins:
                parsed_origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        elif isinstance(v, list):
            parsed_origins = [str(origin).strip().rstrip("/") for origin in v if str(origin).strip()]

        merged = [origin.rstrip("/") for origin in [*DEFAULT_CORS_ORIGINS, *parsed_origins] if origin]
        # De-duplicate while preserving order
        unique_origins = list(dict.fromkeys(merged))
        return unique_origins

    @field_validator('ADMIN_EMAILS', mode='before')
    @classmethod
    def parse_admin_emails(cls, v):
        """Accept JSON array or comma-separated admin emails."""
        parsed: List[str] = []
        if isinstance(v, str):
            value = v.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    maybe_list = json.loads(value)
                    if isinstance(maybe_list, list):
                        parsed = [str(email).strip().lower() for email in maybe_list if str(email).strip()]
                except json.JSONDecodeError:
                    pass
            if not parsed:
                parsed = [email.strip().lower() for email in value.split(",") if email.strip()]
        elif isinstance(v, list):
            parsed = [str(email).strip().lower() for email in v if str(email).strip()]
        return list(dict.fromkeys(parsed))
    
    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        case_sensitive = True

settings = Settings()
