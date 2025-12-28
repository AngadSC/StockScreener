from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, ForeignKey, JSON, Date, Boolean,  UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class User(Base) :
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    tier = Column(String(20), default="free")  # free, premium
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    watchlists = relationship("Watchlist", back_populates = "user", cascade = "all, delete-orphan")

class Stock(Base): 
    __tablename__ = "stocks"
    ticker = Column(String(10), primary_key=True, index=True)
    name = Column(String(255))
    
    # Basic info
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    market_cap = Column(BigInteger, index=True)
    
    # Valuation metrics
    pe_ratio = Column(Float, index=True)
    forward_pe = Column(Float)
    peg_ratio = Column(Float)
    pb_ratio = Column(Float)
    ps_ratio = Column(Float)
    ev_to_ebitda = Column(Float)
    
    # Profitability
    eps = Column(Float)
    profit_margin = Column(Float)
    operating_margin = Column(Float)
    roe = Column(Float)
    roa = Column(Float)
    
    # Growth
    revenue_growth = Column(Float)
    earnings_growth = Column(Float)
    
    # Financial health
    debt_to_equity = Column(Float, index=True)
    current_ratio = Column(Float)
    quick_ratio = Column(Float)
    
    # Dividends
    dividend_yield = Column(Float, index=True)
    dividend_rate = Column(Float)
    payout_ratio = Column(Float)
    
    # Trading
    current_price = Column(Float)
    day_change_percent = Column(Float)
    volume = Column(BigInteger)
    avg_volume = Column(BigInteger)
    beta = Column(Float)
    fifty_two_week_high = Column(Float)
    fifty_two_week_low = Column(Float)
    
    # Full data storage (JSONB)
    raw_data = Column(JSON)
    
    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="stock", cascade="all, delete-orphan")

class StockPrice(Base):
    __tablename__ = "stock_prices"
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='unique_ticker_date'),
    )
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    
    # Relationships
    stock = relationship("Stock", back_populates="prices")

class Watchlist(Base) :
    __tablename__ = "watchlists"
    __table_args__ = (
        UniqueConstraint('user_id', 'ticker', name='unique_user_stock'),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(10), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    stock = relationship("Stock", back_populates="watchlists")

    
    
    