from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import Ticker, DailyOHLCV, StockFundamental
from app.services.cache import cache_service
from app.services.stock_service import get_stock_with_fundamentals, get_price_history
from app.providers.factory import ProviderFactory
from app.utils.data_fetcher import add_technical_indicators

from app.models.stock import StockDetail, BacktestDataResponse, MLFeaturesResponse
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd


router = APIRouter(prefix="/stocks", tags=["stocks"])

@router.get("/{ticker}", response_model=StockDetail)
def get_stock_detail(ticker: str, db: Session = Depends(get_db)):
    """Get detailed stock information including fundamentals"""
    ticker = ticker.upper()

    # Use the stock service which handles caching and DB queries
    stock_data = get_stock_with_fundamentals(db, ticker, use_cache=True)

    if not stock_data:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker} not found. Try the screener to find valid tickers."
        )

    return StockDetail(**stock_data)

@router.get("/{ticker}/prices")
def get_stock_prices(
    ticker: str,
    period: str = Query("1y", regex="^(1mo|3mo|6mo|1y)$", description="Time period"),
    db: Session = Depends(get_db)
):
    """Get historical price data for a stock"""
    ticker = ticker.upper()
    cache_key = f"prices:{ticker}:{period}"

    # Check the redis cache
    cached = cache_service.get(cache_key)
    if cached:
        return cached

    # Calculate the date range
    period_map = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}
    days = period_map[period]
    start_date = datetime.now().date() - timedelta(days=days)
    end_date = datetime.now().date()

    # Use the price history service
    df = get_price_history(db, ticker, start_date, end_date, use_cache=False)

    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No price data found for {ticker}"
        )

    # Format the response
    df_reset = df.reset_index()
    result = {
        "ticker": ticker,
        "period": period,
        "data_points": len(df_reset),
        "data": [
            {
                "date": row['date'].isoformat() if hasattr(row['date'], 'isoformat') else str(row['date']),
                "open": row['Open'],
                "high": row['High'],
                "low": row['Low'],
                "close": row['Close'],
                "volume": row['Volume']
            }
            for _, row in df_reset.iterrows()
        ]
    }

    # Cache for an hour
    cache_service.set(cache_key, result, ttl=3600)

    return result 

@router.post("/{ticker}/backtest-data")
def get_backtest_data(
    ticker: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    include_indicators: bool = Query(True, description="Include technical indicators (SMA, RSI, MACD, etc.)"),
    db: Session = Depends(get_db)
):
    """
     ON-DEMAND: Fetch extended historical data for backtesting.
    
    - Makes API call to yfinance (rate limited to 30/min)
    - Returns up to 10 years of daily OHLCV data
    - Optionally adds 15+ technical indicators
    - Cached for 2 hours (historical data doesn't change)
    
    Use cases:
    - Backtesting trading strategies
    - Historical analysis
    - Training ML models
    """
    ticker = ticker.upper()
    cache_key = f"backtest:{ticker}:{start_date}:{end_date}:{include_indicators}"
    
    # Check Redis cache first
    cached = cache_service.get(cache_key)
    if cached:
        return {
            "ticker": ticker,
            "source": "cache",
            "cached": True,
            **cached
        }
    
    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Stock {ticker} not found in database"
        )
    
    try:
        print(f"🔄 Fetching backtest data for {ticker} from yfinance...")

        # Use the historical provider (yfinance)
        provider = ProviderFactory.get_historical_provider()

        # Convert string dates to date objects
        from datetime import datetime as dt
        start = dt.strptime(start_date, "%Y-%m-%d").date()
        end = dt.strptime(end_date, "%Y-%m-%d").date()

        df = provider.get_historical_prices(ticker, start, end)

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data available for {ticker} in the specified period"
            )
        
        #ad technical indicators as neeeded

        if include_indicators:
            df = add_technical_indicators(df)
        
        #convert to tte json serializable format 
        df_reset = df.reset_index()
        df_reset['Date'] = df_reset['Date'].astype(str)  # Convert datetime to string
        data = df_reset.to_dict(orient='records')

        #perpare response
        result = {
            "start_date": start_date,
            "end_date": end_date,
            "data_points": len(data),
            "indicators_included": include_indicators,
            "columns": list(df.columns),
            "data": data
        }

        #cache for 2 hours 
        cache_service.set(cache_key, result, ttl=7200)
        
        return {
            "ticker": ticker,
            "source": "yfinance",
            "cached": False,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching backtest data: {str(e)}"
        )

@router.post("/{ticker}/ml-features")
def get_ml_features(
    ticker: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)", regex=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db)
):
    """
    ON-DEMAND: Generate ML-ready feature set for a stock.
    
    Returns:
    - OHLCV data
    - 23 technical indicators and features
    - Returns, volatility, momentum metrics
    - Ready for sklearn, TensorFlow, PyTorch
    
    Features included:
    - Price features (OHLCV)
    - Technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands)
    - Returns (1d, 5d, 20d)
    - Volatility (20d, 50d)
    - Momentum (10d, 20d)
    - Volume ratio
    
    Use case: Training machine learning models for price prediction
    """
    ticker = ticker.upper()
    cache_key = f"ml:{ticker}:{start_date}:{end_date}"
    
    # Check cache
    cached = cache_service.get(cache_key)
    if cached:
        return {
            "ticker": ticker,
            "source": "cache",
            "cached": True,
            **cached
        }
    
    # Check if we have the ticker

    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    
    try:
        # Fetch data from yfinance (rate limited)
        print(f"🤖 Generating ML features for {ticker}...")

        # Use the historical provider
        provider = ProviderFactory.get_historical_provider()

        # Convert string dates to date objects
        from datetime import datetime as dt
        start = dt.strptime(start_date, "%Y-%m-%d").date()
        end = dt.strptime(end_date, "%Y-%m-%d").date()

        df = provider.get_historical_prices(ticker, start, end)

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data available for {ticker}"
            )
        
        # Add technical indicators
        df = add_technical_indicators(df)
        
        # Add ML-specific features
        # Returns
        df['Returns_1d'] = df['Close'].pct_change(1)
        df['Returns_5d'] = df['Close'].pct_change(5)
        df['Returns_20d'] = df['Close'].pct_change(20)
        
        # Volatility
        df['Volatility_20d'] = df['Returns_1d'].rolling(20).std()
        df['Volatility_50d'] = df['Returns_1d'].rolling(50).std()
        
        # Momentum
        df['Momentum_10d'] = df['Close'] - df['Close'].shift(10)
        df['Momentum_20d'] = df['Close'] - df['Close'].shift(20)
        
        # Volume features
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA_20']
        
        # Drop NaN rows (from rolling calculations)
        df_clean = df.dropna()
        
        # Define feature columns
        feature_columns = [
            'Open', 'High', 'Low', 'Close', 'Volume',
            'SMA_20', 'SMA_50', 'SMA_200',
            'EMA_12', 'EMA_26', 'MACD', 'MACD_Signal',
            'RSI_14', 'BB_Upper', 'BB_Lower',
            'Returns_1d', 'Returns_5d', 'Returns_20d',
            'Volatility_20d', 'Volatility_50d',
            'Momentum_10d', 'Momentum_20d',
            'Volume_Ratio'
        ]
        
        # Convert to JSON
        df_reset = df_clean[feature_columns].reset_index()
        df_reset['Date'] = df_reset['Date'].astype(str)
        data = df_reset.to_dict(orient='records')
        
        result = {
            "data_points": len(data),
            "features": feature_columns,
            "data": data,
            "description": {
                "price_features": 5,
                "technical_indicators": 10,
                "momentum_features": 4,
                "volatility_features": 2,
                "volume_features": 2,
                "total_features": len(feature_columns)
            }
        }
        
        # Cache for 2 hours
        cache_service.set(cache_key, result, ttl=7200)
        
        return {
            "ticker": ticker,
            "source": "yfinance",
            "cached": False,
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating ML features: {str(e)}"
        )

       
@router.get("/{ticker}/intraday")
def get_intraday_data(
    ticker: str,
    interval: str = Query("5m", regex="^(1m|5m|15m|30m|60m)$", description="Time interval"),
    days: int = Query(5, ge=1, le=30, description="Number of days (max 30)"),
    db: Session = Depends(get_db)
):
    """
     ON-DEMAND: Get intraday (minute-level) data.
    
    - Intervals: 1m, 5m, 15m, 30m, 60m
    - Max 30 days (yfinance limitation)
    - Cached for 30 minutes
    
    Use case: Intraday pattern analysis, day trading strategies
    """
    ticker = ticker.upper()
    cache_key = f"intraday:{ticker}:{interval}:{days}"
    
    # Check cache
    cached = cache_service.get(cache_key)
    if cached:
        return {
            "ticker": ticker,
            "source": "cache",
            **cached
        }
    
    # Verify ticker exists
    ticker_obj = db.query(Ticker).filter(Ticker.symbol == ticker).first()
    if not ticker_obj:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    
    try:
        # Fetch intraday data from yfinance (interval-specific feature)
        import yfinance as yf

        stock = yf.Ticker(ticker)
        df = stock.history(
            period=f"{days}d",
            interval=interval,
            auto_adjust=True
        )

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No intraday data available for {ticker}"
            )
        
        # Convert to JSON
        df_reset = df.reset_index()
        df_reset['Date'] = df_reset['Date'].astype(str)
        data = df_reset.to_dict(orient='records')
        
        result = {
            "interval": interval,
            "days": days,
            "data_points": len(data),
            "data": data
        }
        
        # Cache for 30 minutes (intraday changes frequently)
        cache_service.set(cache_key, result, ttl=1800)
        
        return {
            "ticker": ticker,
            "source": "yfinance",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching intraday data: {str(e)}"
        )       
       
