from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

class StockBase(BaseModel):
    ticker: str
    name: Optional[str] = None

class StockCreate(StockBase):
    pass

class StockDetail(StockBase):
    # Basic info
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None
    
    # Valuation
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    peg_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    
    # Profitability
    eps: Optional[float] = None
    profit_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    
    # Growth
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    
    # Financial health
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    
    # Dividends
    dividend_yield: Optional[float] = None
    dividend_rate: Optional[float] = None
    payout_ratio: Optional[float] = None
    
    # Trading
    current_price: Optional[float] = None
    day_change_percent: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    
    # Metadata
    last_updated: datetime
    
    class Config:
        from_attributes = True  # Allows SQLAlchemy model → Pydantic conversion

class StockFilter(BaseModel):
    # Valuation filters
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None
    min_market_cap: Optional[int] = None
    max_market_cap: Optional[int] = None
    
    # Sector/Industry
    sectors: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    
    # Dividends
    min_dividend_yield: Optional[float] = None
    
    # Financial health
    max_debt_to_equity: Optional[float] = None
    
    # Price
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    
    # Pagination
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)
    
    # Sorting
    sort_by: Optional[str] = Field(default="market_cap", pattern="^(market_cap|pe_ratio|dividend_yield|current_price|ticker)$")
    sort_order: Optional[str] = Field(default="desc", pattern="^(asc|desc)$")

class StockPriceHistory(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    class Config:
        from_attributes = True

class StockWithPrices(StockDetail):
    prices: List[StockPriceHistory] = []