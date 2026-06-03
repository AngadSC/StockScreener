from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
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
    description: Optional[str] = None
    
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
    last_updated: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class StockFilter(BaseModel):
    # Valuation filters
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None
    min_market_cap: Optional[int] = None
    max_market_cap: Optional[int] = None

    # Search
    search: Optional[str] = None
    
    # Sector/Industry
    sectors: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    
    # Dividends
    min_dividend_yield: Optional[float] = None
    
    # Financial health
    max_debt_to_equity: Optional[float] = None
    max_beta: Optional[float] = None
    min_roe: Optional[float] = None
    min_revenue_growth: Optional[float] = None
    
    # Price
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_volume: Optional[int] = None
    min_avg_volume: Optional[int] = None
    
    # Pagination
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)
    
    # Sorting
    sort_by: str = Field(default="market_cap")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

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

# Response models for new endpoints
class BacktestDataResponse(BaseModel):
    ticker: str
    source: str  # "cache", "database", or "yfinance"
    cached: bool = False
    start_date: str
    end_date: str
    data_points: int
    indicators_included: bool
    columns: List[str]
    data: List[Dict[str, Any]]


BacktestStrategyFamily = Literal[
    "leaders_carry_everything",
    "sector_rotation_momentum",
    "earnings_momentum",
    "mean_reversion_extremes",
    "gap_fill_reflex",
    "losers_keep_losing",
    "volatility_regimes",
    "overnight_intraday_edge",
    "index_drag_problem",
    "crowding_risk",
    "trend_following",
    "mean_reversion",
    "momentum_breakout",
    "oversold_reversal",
    "moving_average_pullback",
    "volume_breakout",
    "golden_cross",
    "macd_trend",
    "rsi_trend_filter",
    "price_momentum",
    "sector_momentum",
    "extreme_reversal",
    "gap_fill",
    "momentum_filter",
    "volatility_regime",
    "overnight_edge",
    "relative_strength",
]


class BacktestStrategyConfig(BaseModel):
    family: BacktestStrategyFamily = "trend_following"
    params: Dict[str, Any] = Field(default_factory=dict)


class BacktestRiskControls(BaseModel):
    stop_loss_pct: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    trailing_stop_pct: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    take_profit_pct: Optional[float] = Field(default=None, ge=0.0, le=5.0)


class BacktestTuningRange(BaseModel):
    values: List[float] = Field(default_factory=list)
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = Field(default=None, gt=0.0)


BacktestObjective = Literal[
    "total_return_pct",
    "cagr_pct",
    "max_drawdown_pct",
    "win_rate_pct",
    "average_trade_return_pct",
    "profit_factor",
    "sharpe_ratio",
    "trade_count",
    "average_holding_period_bars",
    "expectancy_pct",
]


class BacktestTuningConfig(BaseModel):
    enabled: bool = False
    objective: BacktestObjective = "sharpe_ratio"
    max_combinations: int = Field(default=100, ge=1, le=500)
    parameter_ranges: Dict[str, BacktestTuningRange] = Field(default_factory=dict)


class BacktestRunRequest(BaseModel):
    start_date: str
    end_date: str
    mode: Literal["automated", "indicator"] = "automated"
    universe: Literal["sp500", "custom", "sector_etfs"] = "custom"
    tickers: List[str] = Field(default_factory=list)
    allocation_weights: Dict[str, float] = Field(default_factory=dict)
    timeframe: Literal["1d", "1wk", "1mo"] = "1d"
    initial_capital: float = Field(default=10000.0, gt=0.0)
    tc_bps: float = Field(default=5.0, ge=0.0, le=500.0)
    allow_fractional_shares: bool = True
    strategy: BacktestStrategyConfig
    risk_controls: Optional[BacktestRiskControls] = None
    tuning: Optional[BacktestTuningConfig] = None
    include_buy_and_hold: bool = True
    generate_plots: bool = True


class BacktestRunResponse(BaseModel):
    ticker: str
    tickers: List[str]
    mode: Literal["automated", "indicator"] = "automated"
    universe: Literal["sp500", "custom", "sector_etfs"] = "custom"
    allocation_weights: Dict[str, float] = Field(default_factory=dict)
    cash_reserve_pct: float = 0.0
    source: Literal["database", "yfinance", "mixed"]
    data_sources: Dict[str, str]
    cached: bool = False
    start_date: str
    end_date: str
    timeframe: Literal["1d", "1wk", "1mo"]
    strategy_family: BacktestStrategyFamily
    strategy_params: Dict[str, Any]
    risk_controls: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    stats: Dict[str, Any]
    equity_curve: List[Dict[str, Any]]
    buy_and_hold: Optional[Dict[str, Any]] = None
    trade_log: List[Dict[str, Any]]
    selected_holdings: List[Dict[str, Any]] = Field(default_factory=list)
    current_holdings: List[Dict[str, Any]] = Field(default_factory=list)
    tuning_summary: Optional[Dict[str, Any]] = None
    equity_curve_image: Optional[str] = None


class IndicatorBacktestRunRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    timeframe: Literal["1d", "1wk", "1mo"] = "1d"
    indicators: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    atr_gate: Optional[Dict[str, Any]] = None
    long_threshold: float = Field(default=0.5, ge=-1.0, le=1.0)
    short_threshold: float = Field(default=-0.5, ge=-1.0, le=1.0)
    exec_lag: int = Field(default=1, ge=0, le=5)
    tc_bps: float = Field(default=5.0, ge=0.0, le=500.0)
    allow_position_hold: bool = True
    generate_plots: bool = True
    generate_roc: bool = False


class IndicatorBacktestRunResponse(BaseModel):
    ticker: str
    mode: Literal["indicator"] = "indicator"
    source: Literal["database", "yfinance", "mixed"]
    cached: bool = False
    start_date: str
    end_date: str
    timeframe: Literal["1d", "1wk", "1mo"]
    warnings: List[str] = Field(default_factory=list)
    stats: Dict[str, Any]
    selected_indicators: List[str]
    equity_curve: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    equity_curve_image: Optional[str] = None
    roc_auc: Optional[float] = None
    roc_curve_image: Optional[str] = None

class MLFeaturesResponse(BaseModel):
    ticker: str
    source: str
    data_points: int
    features: List[str]
    description: Dict[str, int]
    data: List[Dict[str, Any]]
