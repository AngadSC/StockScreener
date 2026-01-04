from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database.connection import engine, Base
from app.routes import stocks, screener, auth, watchlist, admin
from app.jobs.stock_loader import start_scheduler
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
    
    # Start the background job scheduler
    start_scheduler()
    
    yield
    
    # Shutdown
    print("👋 Shutting down Stock Screener API...")

app = FastAPI(
    title = settings.PROJECT_NAME,
    description="Stock Screener & Backtesting API - Filter stocks by fundamentals, backtest strategies, and train ML models",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

#CORS middleware

app.add_middleware( 
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials = True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#include the routers

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(stocks.router, prefix=settings.API_V1_PREFIX)
app.include_router(screener.router, prefix=settings.API_V1_PREFIX)
app.include_router(watchlist.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)

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

