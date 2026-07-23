from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.database.connection import engine, Base
from app.routes import stocks, screener, auth, watchlist, admin, ai_reports, billing, email_prefs, brief, digest, market_scans, insiders, earnings_macro
from app.jobs.stock_loader import start_scheduler
from app.services.rate_limit import check_rate_limit
import uvicorn

#Lifespan manager for startup and shutdown 
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    - Startup: Start background job scheduler
    - Shutdown: Cleanup resources
    """
    # Startup
    print(" Starting up Stock Screener API...")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Database: Connected")
    print(f"   CORS origins: {settings.BACKEND_CORS_ORIGINS}")
    
    # Start the background job scheduler
    start_scheduler()
    
    yield
    
    # Shutdown
    print("👋 Shutting down Stock Screener API...")

is_production = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title = settings.PROJECT_NAME,
    description="Stock Screener & Backtesting API - Filter stocks by fundamentals, backtest strategies, and train ML models",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

#CORS middleware

app.add_middleware( 
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        # Use first IP from proxy chain.
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"

def _resolve_rate_limit(path: str):
    api_prefix = settings.API_V1_PREFIX

    if path == f"{api_prefix}/auth/login":
        return ("login", settings.RATE_LIMIT_LOGIN_PER_MINUTE, 60)
    if path == f"{api_prefix}/auth/register":
        return ("register", settings.RATE_LIMIT_REGISTER_PER_5_MINUTES, 300)
    if path.endswith("/backtest-data") or path.endswith("/backtest") or path.endswith("/ml-features") or path.endswith("/intraday") or path.endswith("/backtests/run"):
        return ("heavy", settings.RATE_LIMIT_HEAVY_PER_MINUTE, 60)
    if path.startswith(f"{api_prefix}/screener"):
        return ("screener", settings.RATE_LIMIT_SCREENER_PER_MINUTE, 60)
    if path.startswith(api_prefix):
        return ("default", settings.RATE_LIMIT_DEFAULT_PER_MINUTE, 60)
    return None

def _is_allowed_origin(origin_or_referrer: str) -> bool:
    candidate = origin_or_referrer.rstrip("/")
    for allowed in settings.BACKEND_CORS_ORIGINS:
        normalized = allowed.rstrip("/")
        if candidate == normalized or candidate.startswith(f"{normalized}/"):
            return True
    return False

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response

@app.middleware("http")
async def csrf_origin_check_middleware(request: Request, call_next):
    """
    Protect cookie-authenticated state-changing requests from cross-site forgery.
    Header-based Bearer auth is excluded because it is not sent automatically by browsers.
    """
    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}
    has_cookie_auth = bool(request.cookies.get(settings.AUTH_COOKIE_NAME))
    has_header_auth = bool(request.headers.get("authorization"))

    if request.method in unsafe_methods and has_cookie_auth and not has_header_auth:
        origin = request.headers.get("origin") or request.headers.get("referer")
        if not origin or not _is_allowed_origin(origin):
            return JSONResponse(
                status_code=403,
                content={"detail": "Cross-site request blocked"},
            )

    return await call_next(request)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not settings.RATE_LIMIT_ENABLED:
        return await call_next(request)

    rate_limit_config = _resolve_rate_limit(request.url.path)
    if not rate_limit_config:
        return await call_next(request)

    scope, limit, window_seconds = rate_limit_config
    client_id = _get_client_identifier(request)
    allowed, current, ttl = check_rate_limit(
        identifier=client_id,
        scope=scope,
        limit=limit,
        window_seconds=window_seconds,
    )

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
            headers={"Retry-After": str(ttl)},
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(limit - current, 0))
    response.headers["X-RateLimit-Reset"] = str(ttl)
    return response

#include the routers

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(stocks.router, prefix=settings.API_V1_PREFIX)
app.include_router(stocks.backtests_router, prefix=settings.API_V1_PREFIX)
app.include_router(screener.router, prefix=settings.API_V1_PREFIX)
app.include_router(market_scans.router, prefix=settings.API_V1_PREFIX)
app.include_router(watchlist.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)
app.include_router(billing.router, prefix=settings.API_V1_PREFIX)
app.include_router(billing.webhook_router)
app.include_router(ai_reports.router)
app.include_router(email_prefs.router, prefix=settings.API_V1_PREFIX)
app.include_router(brief.router, prefix=settings.API_V1_PREFIX)
app.include_router(digest.router, prefix=settings.API_V1_PREFIX)
app.include_router(insiders.router, prefix=settings.API_V1_PREFIX)
app.include_router(earnings_macro.router, prefix=settings.API_V1_PREFIX)

#Root endpoint 
@app.get("/")
def root():
    """ApI root ednpoit"""
    return {
        "message": "Stock Screener & Backtesting API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "api_version": "1.0.0"
    }

# Run with: uvicorn app.main:app --reload
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False
    )

