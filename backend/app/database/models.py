from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, ForeignKey, Date, Boolean, Index, SmallInteger, REAL, Text, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

# ============================================
# USER MODEL
# ============================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    tier = Column(String(20), default="free")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")


# ============================================
# TICKER LOOKUP TABLE
# ============================================

class Ticker(Base):
    __tablename__ = "tickers"
    
    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255))
    exchange = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    prices = relationship("DailyOHLCV", back_populates="ticker", cascade="all, delete-orphan")
    splits = relationship("StockSplit", back_populates="ticker", cascade="all, delete-orphan")
    dividends = relationship("Dividend", back_populates="ticker", cascade="all, delete-orphan")
    fundamentals = relationship("StockFundamental", back_populates="ticker", uselist=False, cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="ticker", cascade="all, delete-orphan")


# ============================================
# DAILY OHLCV DATA (Optimized)
# ============================================

class DailyOHLCV(Base):
    __tablename__ = "daily_ohlcv"
    
    ticker_id = Column(SmallInteger, ForeignKey("tickers.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    open = Column(REAL)
    high = Column(REAL)
    low = Column(REAL)
    close = Column(REAL)
    volume = Column(BigInteger)
    
    # Relationship
    ticker = relationship("Ticker", back_populates="prices")
    
    # Indexes
    __table_args__ = (
        Index('idx_ohlcv_ticker', 'ticker_id'),
        Index('idx_ohlcv_date', 'date'),
        {'postgresql_fillfactor': 90}  # Leave room for daily updates
    )


# ============================================
# STOCK SPLITS
# ============================================

class StockSplit(Base):
    __tablename__ = "stock_splits"
    
    ticker_id = Column(SmallInteger, ForeignKey("tickers.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    ratio = Column(REAL, nullable=False)
    
    # Relationship
    ticker = relationship("Ticker", back_populates="splits")


# ============================================
# DIVIDENDS
# ============================================

class Dividend(Base):
    __tablename__ = "dividends"
    
    ticker_id = Column(SmallInteger, ForeignKey("tickers.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    date = Column(Date, nullable=False, primary_key=True)
    amount = Column(REAL, nullable=False)
    
    # Relationship
    ticker = relationship("Ticker", back_populates="dividends")


# ============================================
# STOCK FUNDAMENTALS (Hybrid: Columns + JSONB)
# ============================================

class StockFundamental(Base):
    __tablename__ = "stock_fundamentals"
    
    ticker_id = Column(SmallInteger, ForeignKey("tickers.id", ondelete="CASCADE"), primary_key=True)
    
    # Valuation Metrics
    pe_ratio = Column(REAL, index=True)
    forward_pe = Column(REAL)
    peg_ratio = Column(REAL)
    price_to_book = Column(REAL)
    price_to_sales = Column(REAL)
    ev_to_ebitda = Column(REAL)
    
    # Profitability Metrics
    profit_margin = Column(REAL)
    operating_margin = Column(REAL)
    roe = Column(REAL, index=True)
    roa = Column(REAL)
    
    # Financial Health
    debt_to_equity = Column(REAL, index=True)
    current_ratio = Column(REAL)
    quick_ratio = Column(REAL)
    
    # Growth Metrics
    revenue_growth = Column(REAL)
    earnings_growth = Column(REAL)
    
    # Dividend Metrics
    dividend_yield = Column(REAL, index=True)
    dividend_rate = Column(REAL)
    payout_ratio = Column(REAL)
    
    # Size & Trading
    market_cap = Column(BigInteger, index=True)
    volume = Column(BigInteger)
    avg_volume = Column(BigInteger)
    beta = Column(REAL)
    
    # Current Price Info
    current_price = Column(REAL)
    day_change_percent = Column(REAL)
    fifty_two_week_high = Column(REAL)
    fifty_two_week_low = Column(REAL)
    
    # Sector/Industry
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    
    # Additional data (JSONB for flexibility)
    additional_data = Column(JSONB)
    
    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    ticker = relationship("Ticker", back_populates="fundamentals")


# ============================================
# BULK POPULATION PROGRESS TRACKING
# ============================================

class PopulationProgress(Base):
    __tablename__ = "population_progress"
    
    batch_number = Column(Integer, primary_key=True)
    ticker_list = Column(ARRAY(String))
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    status = Column(String(20))  # 'in_progress', 'completed', 'failed'
    error_message = Column(Text)
    records_inserted = Column(Integer, default=0)


# ============================================
# FAILED TICKER RETRY QUEUE
# ============================================

class FailedTicker(Base):
    __tablename__ = "failed_tickers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    batch_number = Column(Integer)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default='pending')  # 'pending', 'retrying', 'permanent_failure'


# ============================================
# WATCHLIST
# ============================================

class Watchlist(Base):
    __tablename__ = "watchlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker_id = Column(SmallInteger, ForeignKey("tickers.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="watchlists")
    ticker = relationship("Ticker", back_populates="watchlists")
    
    # Unique constraint
    __table_args__ = (
        Index('idx_user_ticker', 'user_id', 'ticker_id', unique=True),
    )
