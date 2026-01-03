-- ============================================
-- OPTIMIZED SCHEMA FOR STOCK SCREENER
-- Storage-efficient design for Railway
-- ============================================

-- Drop old tables if doing fresh start
-- DROP TABLE IF EXISTS stock_prices CASCADE;
-- DROP TABLE IF EXISTS stocks CASCADE;

-- ============================================
-- TICKER LOOKUP TABLE
-- Maps ticker symbols to small integer IDs
-- ============================================
CREATE TABLE IF NOT EXISTS tickers (
    id SMALLSERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255),
    exchange VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tickers_symbol ON tickers(symbol);

-- ============================================
-- DAILY OHLCV DATA (Optimized)
-- Uses REAL (4 bytes) instead of DOUBLE (8 bytes)
-- Uses ticker_id (2 bytes) instead of VARCHAR (10+ bytes)
-- ============================================
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    ticker_id SMALLINT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,      -- Adjusted close
    volume BIGINT,
    PRIMARY KEY (ticker_id, date),
    FOREIGN KEY (ticker_id) REFERENCES tickers(id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON daily_ohlcv(ticker_id);
CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv(date);

-- Set fill factor to leave room for daily updates
ALTER TABLE daily_ohlcv SET (fillfactor = 90);

-- ============================================
-- STOCK SPLITS (Separate tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS stock_splits (
    ticker_id SMALLINT NOT NULL,
    date DATE NOT NULL,
    ratio REAL NOT NULL,  -- e.g., 7.0 for 7:1 split
    PRIMARY KEY (ticker_id, date),
    FOREIGN KEY (ticker_id) REFERENCES tickers(id) ON DELETE CASCADE
);

-- ============================================
-- DIVIDENDS (Separate tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS dividends (
    ticker_id SMALLINT NOT NULL,
    date DATE NOT NULL,
    amount REAL NOT NULL,  -- Dividend amount in USD
    PRIMARY KEY (ticker_id, date),
    FOREIGN KEY (ticker_id) REFERENCES tickers(id) ON DELETE CASCADE
);

-- ============================================
-- FUNDAMENTALS (Hybrid: Columns + JSONB)
-- Main screener metrics as columns (fast indexing)
-- Everything else in JSONB (flexible)
-- ============================================
CREATE TABLE IF NOT EXISTS stock_fundamentals (
    ticker_id SMALLINT PRIMARY KEY,
    
    -- Valuation Metrics (Indexed for screening)
    pe_ratio REAL,
    forward_pe REAL,
    peg_ratio REAL,
    price_to_book REAL,
    price_to_sales REAL,
    ev_to_ebitda REAL,
    
    -- Profitability Metrics
    profit_margin REAL,
    operating_margin REAL,
    roe REAL,              -- Return on Equity
    roa REAL,              -- Return on Assets
    
    -- Financial Health
    debt_to_equity REAL,
    current_ratio REAL,
    quick_ratio REAL,
    
    -- Growth Metrics
    revenue_growth REAL,
    earnings_growth REAL,
    
    -- Dividend Metrics
    dividend_yield REAL,
    dividend_rate REAL,
    payout_ratio REAL,
    
    -- Size & Trading
    market_cap BIGINT,
    volume BIGINT,
    avg_volume BIGINT,
    beta REAL,
    
    -- Current Price Info
    current_price REAL,
    day_change_percent REAL,
    fifty_two_week_high REAL,
    fifty_two_week_low REAL,
    
    -- Sector/Industry
    sector VARCHAR(100),
    industry VARCHAR(100),
    
    -- Additional data (everything else in JSONB)
    additional_data JSONB,
    
    -- Metadata
    last_updated TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (ticker_id) REFERENCES tickers(id) ON DELETE CASCADE
);

-- Indexes for common screener filters
CREATE INDEX IF NOT EXISTS idx_fund_pe ON stock_fundamentals(pe_ratio);
CREATE INDEX IF NOT EXISTS idx_fund_mcap ON stock_fundamentals(market_cap);
CREATE INDEX IF NOT EXISTS idx_fund_debt_eq ON stock_fundamentals(debt_to_equity);
CREATE INDEX IF NOT EXISTS idx_fund_div_yield ON stock_fundamentals(dividend_yield);
CREATE INDEX IF NOT EXISTS idx_fund_sector ON stock_fundamentals(sector);
CREATE INDEX IF NOT EXISTS idx_fund_roe ON stock_fundamentals(roe);

-- ============================================
-- BULK POPULATION PROGRESS TRACKING
-- For checkpoint/resume during initial load
-- ============================================
CREATE TABLE IF NOT EXISTS population_progress (
    batch_number INT PRIMARY KEY,
    ticker_list TEXT[],
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20),  -- 'in_progress', 'completed', 'failed'
    error_message TEXT,
    records_inserted INT DEFAULT 0
);

-- ============================================
-- FAILED TICKER RETRY QUEUE
-- Tracks tickers that failed during bulk load
-- ============================================
CREATE TABLE IF NOT EXISTS failed_tickers (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    batch_number INT,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    last_attempt TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending'  -- 'pending', 'retrying', 'permanent_failure'
);

-- ============================================
-- USER-RELATED TABLES (Keep existing schema)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    tier VARCHAR(20) DEFAULT 'free',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watchlists (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    ticker_id SMALLINT NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (ticker_id) REFERENCES tickers(id) ON DELETE CASCADE,
    UNIQUE(user_id, ticker_id)
);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to get ticker_id from symbol (or create if not exists)
CREATE OR REPLACE FUNCTION get_or_create_ticker_id(p_symbol VARCHAR)
RETURNS SMALLINT AS $$
DECLARE
    v_ticker_id SMALLINT;
BEGIN
    -- Try to get existing
    SELECT id INTO v_ticker_id FROM tickers WHERE symbol = p_symbol;
    
    -- If not found, create it
    IF v_ticker_id IS NULL THEN
        INSERT INTO tickers (symbol) VALUES (p_symbol)
        RETURNING id INTO v_ticker_id;
    END IF;
    
    RETURN v_ticker_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VACUUM & ANALYZE
-- Run after initial population
-- ============================================
-- VACUUM ANALYZE daily_ohlcv;
-- VACUUM ANALYZE stock_fundamentals;
