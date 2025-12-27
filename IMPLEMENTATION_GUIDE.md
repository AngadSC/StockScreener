# Stock Screener & Strategy Backtester - Complete Implementation Guide

## 📋 Table of Contents
1. [Tech Stack](#tech-stack)
2. [System Architecture](#system-architecture)
3. [Prerequisites](#prerequisites)
4. [Phase 1: Project Setup](#phase-1-project-setup)
5. [Phase 2: Backend Development](#phase-2-backend-development)
6. [Phase 3: Frontend Development](#phase-3-frontend-development)
7. [Phase 4: Integration & Testing](#phase-4-integration--testing)
8. [Phase 5: Deployment](#phase-5-deployment)
9. [Phase 6: Backtester Integration](#phase-6-backtester-integration)
10. [Database Schema](#database-schema)
11. [API Endpoints](#api-endpoints)
12. [Development Workflow](#development-workflow)

---

## 🛠 Tech Stack

### **Backend**
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.10+ | Backend language |
| **FastAPI** | 0.104+ | REST API framework |
| **SQLAlchemy** | 2.0+ | ORM for database operations |
| **Alembic** | 1.12+ | Database migrations |
| **PostgreSQL** | 15+ | Primary database |
| **Redis** | 7+ | Caching layer |
| **Pydantic** | 2.5+ | Data validation & serialization |
| **python-jose** | 3.3+ | JWT token generation |
| **passlib** | 1.7+ | Password hashing (bcrypt) |
| **yfinance** | 0.2.33+ | Stock data fetching |
| **pandas** | 2.1+ | Data manipulation |
| **numpy** | 1.26+ | Numerical computations |
| **uvicorn** | 0.24+ | ASGI server |
| **python-multipart** | 0.0.6+ | File uploads support |
| **python-dotenv** | 1.0+ | Environment variable management |
| **APScheduler** | 3.10+ | Job scheduling (nightly updates) |
| **httpx** | 0.25+ | Async HTTP client |
| **redis-py** | 5.0+ | Redis client |
| **psycopg2-binary** | 2.9+ | PostgreSQL adapter |

### **Frontend**
| Technology | Version | Purpose |
|------------|---------|---------|
| **Node.js** | 18+ | JavaScript runtime |
| **Next.js** | 14+ | React framework (App Router) |
| **React** | 18+ | UI library |
| **TypeScript** | 5+ | Type safety |
| **Tailwind CSS** | 3.4+ | Styling framework |
| **shadcn/ui** | Latest | Component library |
| **Radix UI** | Latest | Headless UI primitives (shadcn dependency) |
| **React Query (TanStack Query)** | 5+ | Server state management |
| **Axios** | 1.6+ | HTTP client |
| **Recharts** | 2.10+ | Charting library |
| **Zustand** | 4.4+ | Lightweight state management |
| **React Hook Form** | 7.48+ | Form handling |
| **Zod** | 3.22+ | Schema validation |
| **date-fns** | 3.0+ | Date utilities |
| **clsx** | 2.0+ | Conditional classnames |
| **tailwind-merge** | 2.0+ | Tailwind class merging |
| **lucide-react** | 0.292+ | Icon library |
| **next-themes** | 0.2+ | Dark mode support |

### **Backtesting (Phase 2)**
| Technology | Version | Purpose |
|------------|---------|---------|
| **ta (Technical Analysis)** | 0.11+ | Technical indicators |
| **scikit-learn** | 1.3+ | ML metrics (ROC AUC, etc.) |
| **matplotlib** | 3.8+ | Chart generation |

### **Development Tools**
| Tool | Purpose |
|------|---------|
| **Git** | Version control |
| **VS Code** | IDE (recommended) |
| **Postman/Thunder Client** | API testing |
| **pgAdmin** / **DBeaver** | Database management (optional) |
| **Redis Insight** | Redis GUI (optional) |

### **Deployment & Infrastructure**
| Service | Purpose | Tier |
|---------|---------|------|
| **Railway** | Backend hosting, PostgreSQL, Redis | Free (MVP) |
| **Vercel** | Frontend hosting | Free |
| **GitHub** | Code repository, CI/CD | Free |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         USER BROWSER                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    VERCEL (Frontend)                         │
│  Next.js 14 + React + TypeScript + Tailwind + shadcn/ui    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Pages: Home, Screener, Stock Detail, Watchlist     │  │
│  │  Components: FilterPanel, StockTable, Charts        │  │
│  │  State: React Query + Zustand                       │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS/REST
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   RAILWAY (Backend)                          │
│  FastAPI + Python 3.10+ + Uvicorn                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Routes: /stocks, /screener, /watchlist, /auth      │  │
│  │  Services: DataFetcher, Screener, Cache, Auth       │  │
│  │  Jobs: Nightly stock loader (APScheduler)           │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬────────────────────────┬─────────────────────────────┘
       │                        │
       ▼                        ▼
┌──────────────────┐   ┌──────────────────┐
│  PostgreSQL      │   │      Redis       │
│  (Railway)       │   │    (Railway)     │
│                  │   │                  │
│  Tables:         │   │  Cache:          │
│  - users         │   │  - stock_data    │
│  - stocks        │   │  - screener_res  │
│  - stock_prices  │   │  TTL: 24h        │
│  - watchlists    │   │                  │
└──────────────────┘   └──────────────────┘
       │
       │ Nightly Job (9pm ET)
       ▼
┌──────────────────────────────────┐
│     yfinance API                 │
│  Fetch fundamentals + prices     │
│  Rate limit: ~1,000 stocks/hour  │
└──────────────────────────────────┘
```

---

## ✅ Prerequisites

### **Required Software**
- [ ] **Python 3.10+** - [Download](https://www.python.org/downloads/)
  - Verify: `python --version`
- [ ] **Node.js 18+** - [Download](https://nodejs.org/)
  - Verify: `node --version`
  - npm comes with Node.js
- [ ] **Git** - [Download](https://git-scm.com/)
  - Verify: `git --version`

### **Required Accounts**
- [ ] **GitHub Account** - [Sign up](https://github.com/join)
- [ ] **Railway Account** - [Sign up](https://railway.app/) (login with GitHub)
- [ ] **Vercel Account** - [Sign up](https://vercel.com/signup) (login with GitHub)

### **Optional (Helpful)**
- [ ] **VS Code** - [Download](https://code.visualstudio.com/)
  - Extensions: Python, Pylance, ESLint, Prettier, Tailwind CSS IntelliSense
- [ ] **Postman** or **Thunder Client** (VS Code extension) - API testing

---

## 📦 Phase 1: Project Setup

### **Step 1.1: Initialize Git Repository**

```bash
# Navigate to your project directory
cd StockScreener

# Verify git is initialized (should already be done)
git status

# Create directory structure
mkdir -p backend/app/{models,services,routes,database,utils,jobs}
mkdir -p backend/tests
mkdir -p frontend

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
*.egg-info/
dist/
build/
.pytest_cache/

# Environment variables
.env
.env.local
.env.*.local

# Database
*.db
*.sqlite3

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Node.js
node_modules/
.next/
out/
.cache/
*.log

# Misc
*.log
.cache
.coverage
htmlcov/
EOF
```

### **Step 1.2: Create Backend Structure**

```bash
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
# FastAPI & Server
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9

# Caching
redis==5.0.1

# Auth & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0

# Data & API
yfinance==0.2.33
pandas==2.1.3
numpy==1.26.2
httpx==0.25.2

# Job Scheduling
apscheduler==3.10.4

# Validation
pydantic==2.5.2
pydantic-settings==2.1.0

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
EOF

# Install dependencies
pip install -r requirements.txt

# Create __init__.py files
touch app/__init__.py
touch app/models/__init__.py
touch app/services/__init__.py
touch app/routes/__init__.py
touch app/database/__init__.py
touch app/utils/__init__.py
touch app/jobs/__init__.py
```

### **Step 1.3: Create Frontend Structure**

```bash
cd ../frontend

# Create Next.js app with TypeScript and Tailwind
npx create-next-app@latest . --typescript --tailwind --app --no-src --import-alias "@/*"

# Answer prompts:
# ✔ Would you like to use ESLint? Yes
# ✔ Would you like to use Turbopack? No
# ✔ Would you like to customize the default import alias? No

# Install additional dependencies
npm install axios @tanstack/react-query zustand react-hook-form zod recharts date-fns clsx tailwind-merge lucide-react next-themes

# Install shadcn/ui CLI
npx shadcn-ui@latest init

# Answer prompts (recommended defaults):
# ✔ Would you like to use TypeScript? yes
# ✔ Which style would you like to use? Default
# ✔ Which color would you like to use as base color? Slate
# ✔ Where is your global CSS file? app/globals.css
# ✔ Would you like to use CSS variables for colors? yes
# ✔ Where is your tailwind.config.js located? tailwind.config.ts
# ✔ Configure the import alias for components: @/components
# ✔ Configure the import alias for utils: @/lib/utils

# Install shadcn/ui components (we'll add more as needed)
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add card
npx shadcn-ui@latest add table
npx shadcn-ui@latest add select
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add form
npx shadcn-ui@latest add label
npx shadcn-ui@latest add skeleton
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add badge
```

### **Step 1.4: Setup Railway Infrastructure**

```bash
# 1. Go to https://railway.app/
# 2. Sign in with GitHub
# 3. Click "New Project"
# 4. Select "Deploy from GitHub repo" and choose your StockScreener repo
# 5. Add PostgreSQL:
#    - Click "+ New" → "Database" → "Add PostgreSQL"
# 6. Add Redis:
#    - Click "+ New" → "Database" → "Add Redis"
# 7. Copy connection strings:
#    - Click PostgreSQL service → "Connect" → Copy DATABASE_URL
#    - Click Redis service → "Connect" → Copy REDIS_URL
```

### **Step 1.5: Create Environment Files**

```bash
cd ../backend

# Create .env file
cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql://user:password@host:port/database
# Get this from Railway PostgreSQL → Connect tab

# Redis
REDIS_URL=redis://default:password@host:port
# Get this from Railway Redis → Connect tab

# JWT Secret (generate random string)
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Settings
API_V1_PREFIX=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://yourdomain.vercel.app"]

# Stock Data Settings
STOCK_UPDATE_HOUR=21  # 9pm ET
STOCK_UPDATE_BATCH_SIZE=1000
STOCK_CACHE_TTL=86400  # 24 hours

# Environment
ENVIRONMENT=development
EOF

cd ../frontend

# Create .env.local file
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
# Change to your Railway backend URL for production
EOF
```

---

## 🔨 Phase 2: Backend Development

### **Step 2.1: Database Configuration**

**File: `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings
from typing import List
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

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Stock Settings
    STOCK_UPDATE_HOUR: int = 21
    STOCK_UPDATE_BATCH_SIZE: int = 1000
    STOCK_CACHE_TTL: int = 86400

    # Environment
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**File: `backend/app/database/connection.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### **Step 2.2: Database Models (SQLAlchemy)**

**File: `backend/app/database/models.py`**

```python
from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime, ForeignKey, JSON, Date, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    tier = Column(String(20), default="free")  # free, premium
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")

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

    # Unique constraint
    __table_args__ = (
        {"schema": None},
    )

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(10), ForeignKey("stocks.ticker", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="watchlists")
    stock = relationship("Stock", back_populates="watchlists")

    # Unique constraint
    __table_args__ = (
        {"schema": None},
    )
```

### **Step 2.3: Pydantic Schemas**

**File: `backend/app/models/stock.py`**

```python
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
        from_attributes = True

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
```

**File: `backend/app/models/user.py`**

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    tier: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None
```

**File: `backend/app/models/watchlist.py`**

```python
from pydantic import BaseModel
from datetime import datetime
from typing import List
from app.models.stock import StockDetail

class WatchlistItemBase(BaseModel):
    ticker: str

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItemResponse(WatchlistItemBase):
    id: int
    added_at: datetime
    stock: StockDetail

    class Config:
        from_attributes = True

class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]
    total: int
```

### **Step 2.4: Copy & Extend Your Data Fetcher**

**File: `backend/app/utils/data_fetcher.py`**

```python
# Copy your existing data_fetcher.py here
# Then add this new function below it:

from typing import Optional, Dict, Any
import yfinance as yf

def fetch_stock_fundamentals(ticker: str, quiet: bool = False) -> Optional[Dict[str, Any]]:
    """
    Fetch fundamental data for a stock from yfinance.
    Returns a cleaned dict of fundamental metrics.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info or len(info) < 5:
            if not quiet:
                print(f"Warning: No fundamental data for {ticker}")
            return None

        # Extract and normalize data
        fundamentals = {
            # Basic info
            "ticker": ticker.upper(),
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),

            # Valuation
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "ev_to_ebitda": info.get("enterpriseToEbitda"),

            # Profitability
            "eps": info.get("trailingEps"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),

            # Growth
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),

            # Financial health
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),

            # Dividends
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),

            # Trading
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "day_change_percent": info.get("regularMarketChangePercent"),
            "volume": info.get("volume"),
            "avg_volume": info.get("averageVolume"),
            "beta": info.get("beta"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),

            # Store full raw data
            "raw_data": info
        }

        if not quiet:
            print(f"Fundamentals for {ticker} fetched successfully")

        return fundamentals

    except Exception as e:
        if not quiet:
            print(f"Error fetching fundamentals for {ticker}: {e}")
        return None
```

### **Step 2.5: Services**

**File: `backend/app/services/cache.py`**

```python
import redis
import json
from typing import Optional, Any
from app.config import settings

class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with optional TTL (seconds)"""
        try:
            ttl = ttl or settings.STOCK_CACHE_TTL
            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern (e.g., 'stock:*')"""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache clear error: {e}")
            return False

cache_service = CacheService()
```

**File: `backend/app/services/auth.py`**

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database.connection import get_db
from app.database.models import User
from app.models.user import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
```

**File: `backend/app/services/screener.py`**

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.database.models import Stock
from app.models.stock import StockFilter
from typing import List, Tuple

def screen_stocks(db: Session, filters: StockFilter) -> Tuple[List[Stock], int]:
    """
    Apply filters to stocks and return matching stocks + total count
    """
    query = db.query(Stock)

    # Apply filters
    conditions = []

    if filters.min_pe is not None:
        conditions.append(Stock.pe_ratio >= filters.min_pe)
    if filters.max_pe is not None:
        conditions.append(Stock.pe_ratio <= filters.max_pe)

    if filters.min_market_cap is not None:
        conditions.append(Stock.market_cap >= filters.min_market_cap)
    if filters.max_market_cap is not None:
        conditions.append(Stock.market_cap <= filters.max_market_cap)

    if filters.sectors:
        conditions.append(Stock.sector.in_(filters.sectors))

    if filters.industries:
        conditions.append(Stock.industry.in_(filters.industries))

    if filters.min_dividend_yield is not None:
        conditions.append(Stock.dividend_yield >= filters.min_dividend_yield)

    if filters.max_debt_to_equity is not None:
        conditions.append(Stock.debt_to_equity <= filters.max_debt_to_equity)

    if filters.min_price is not None:
        conditions.append(Stock.current_price >= filters.min_price)
    if filters.max_price is not None:
        conditions.append(Stock.current_price <= filters.max_price)

    # Apply all conditions
    if conditions:
        query = query.filter(and_(*conditions))

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Stock, filters.sort_by, Stock.market_cap)
    if filters.sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    stocks = query.offset(filters.skip).limit(filters.limit).all()

    return stocks, total
```

**File: `backend/app/services/stock_service.py`**

```python
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
from app.database.models import Stock, StockPrice
from app.utils.data_fetcher import fetch_stock_fundamentals, fetch_stock_data
from app.services.cache import cache_service
import pandas as pd

def needs_update(stock: Stock) -> bool:
    """Check if stock data needs updating (>24 hours old)"""
    if not stock.last_updated:
        return True
    return (datetime.utcnow() - stock.last_updated) > timedelta(hours=24)

def get_or_fetch_stock(db: Session, ticker: str) -> Optional[Stock]:
    """
    Get stock from DB, or fetch from yfinance if not exists/outdated
    """
    ticker = ticker.upper()

    # Check cache first
    cache_key = f"stock:{ticker}"
    cached = cache_service.get(cache_key)
    if cached:
        return Stock(**cached)

    # Check database
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()

    # If exists and fresh, return it
    if stock and not needs_update(stock):
        cache_service.set(cache_key, stock.__dict__)
        return stock

    # Fetch fresh data from yfinance
    fundamentals = fetch_stock_fundamentals(ticker, quiet=True)
    if not fundamentals:
        return None

    # Update or create stock
    if stock:
        for key, value in fundamentals.items():
            if key != "raw_data":
                setattr(stock, key, value)
        stock.raw_data = fundamentals["raw_data"]
        stock.last_updated = datetime.utcnow()
    else:
        stock = Stock(**fundamentals)
        db.add(stock)

    db.commit()
    db.refresh(stock)

    # Cache it
    cache_service.set(cache_key, stock.__dict__)

    return stock

def get_stock_price_history(
    db: Session,
    ticker: str,
    start_date: str,
    end_date: str
) -> List[StockPrice]:
    """
    Get historical price data for a stock
    """
    ticker = ticker.upper()

    # Check if we have it in DB
    existing_prices = db.query(StockPrice).filter(
        StockPrice.ticker == ticker,
        StockPrice.date >= start_date,
        StockPrice.date <= end_date
    ).order_by(StockPrice.date).all()

    # If we have enough data, return it
    if len(existing_prices) > 200:  # Arbitrary threshold
        return existing_prices

    # Otherwise, fetch from yfinance
    df = fetch_stock_data(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        auto_adjust=True,
        suffix_with_ticker=True,
        add_forward_return=False,
        dropna=True,
        quiet=True
    )

    if df is None or df.empty:
        return existing_prices

    # Parse the data and save to DB
    prices = []
    for date, row in df.iterrows():
        price = StockPrice(
            ticker=ticker,
            date=date.date(),
            open=row.get(f"Open_{ticker}"),
            high=row.get(f"High_{ticker}"),
            low=row.get(f"Low_{ticker}"),
            close=row.get(f"Close_{ticker}"),
            volume=row.get(f"Volume_{ticker}")
        )

        # Check if already exists
        exists = db.query(StockPrice).filter(
            StockPrice.ticker == ticker,
            StockPrice.date == date.date()
        ).first()

        if not exists:
            db.add(price)
            prices.append(price)

    db.commit()

    # Return all prices in range
    return db.query(StockPrice).filter(
        StockPrice.ticker == ticker,
        StockPrice.date >= start_date,
        StockPrice.date <= end_date
    ).order_by(StockPrice.date).all()
```

### **Step 2.6: API Routes**

**File: `backend/app/routes/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database.connection import get_db
from app.database.models import User
from app.models.user import UserCreate, UserLogin, UserResponse, Token
from app.services.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_active_user
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    db_user = User(
        email=user.email,
        password_hash=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Find user
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return current_user
```

**File: `backend/app/routes/stocks.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.connection import get_db
from app.models.stock import StockDetail, StockPriceHistory
from app.services.stock_service import get_or_fetch_stock, get_stock_price_history
from datetime import datetime, timedelta

router = APIRouter(prefix="/stocks", tags=["stocks"])

@router.get("/{ticker}", response_model=StockDetail)
def get_stock(ticker: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific stock"""
    stock = get_or_fetch_stock(db, ticker)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock

@router.get("/{ticker}/history", response_model=List[StockPriceHistory])
def get_stock_history(
    ticker: str,
    period: str = Query("1y", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|max)$"),
    db: Session = Depends(get_db)
):
    """Get historical price data for a stock"""
    # Convert period to dates
    end_date = datetime.now().strftime("%Y-%m-%d")

    period_map = {
        "1d": 1,
        "5d": 5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "max": 3650
    }

    days = period_map.get(period, 365)
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    prices = get_stock_price_history(db, ticker, start_date, end_date)
    return prices

@router.get("/search/{query}")
def search_stocks(query: str, db: Session = Depends(get_db)):
    """Search for stocks by ticker or name"""
    from app.database.models import Stock

    results = db.query(Stock).filter(
        (Stock.ticker.ilike(f"%{query}%")) |
        (Stock.name.ilike(f"%{query}%"))
    ).limit(10).all()

    return [{"ticker": s.ticker, "name": s.name} for s in results]
```

**File: `backend/app/routes/screener.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.stock import StockFilter, StockDetail
from app.services.screener import screen_stocks
from typing import List

router = APIRouter(prefix="/screener", tags=["screener"])

@router.post("/screen", response_model=dict)
def screen(filters: StockFilter, db: Session = Depends(get_db)):
    """Screen stocks based on filters"""
    stocks, total = screen_stocks(db, filters)

    return {
        "stocks": [StockDetail.from_orm(s) for s in stocks],
        "total": total,
        "page": filters.skip // filters.limit + 1,
        "pages": (total + filters.limit - 1) // filters.limit
    }

@router.get("/sectors")
def get_sectors(db: Session = Depends(get_db)):
    """Get list of all sectors"""
    from app.database.models import Stock
    sectors = db.query(Stock.sector).distinct().filter(Stock.sector.isnot(None)).all()
    return {"sectors": sorted([s[0] for s in sectors])}

@router.get("/industries")
def get_industries(db: Session = Depends(get_db)):
    """Get list of all industries"""
    from app.database.models import Stock
    industries = db.query(Stock.industry).distinct().filter(Stock.industry.isnot(None)).all()
    return {"industries": sorted([i[0] for i in industries])}
```

**File: `backend/app/routes/watchlist.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import User, Watchlist, Stock
from app.models.watchlist import WatchlistItemCreate, WatchlistItemResponse, WatchlistResponse
from app.services.auth import get_current_active_user
from app.services.stock_service import get_or_fetch_stock

router = APIRouter(prefix="/watchlist", tags=["watchlist"])

@router.get("", response_model=WatchlistResponse)
def get_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's watchlist"""
    items = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id
    ).all()

    return {
        "items": items,
        "total": len(items)
    }

@router.post("", response_model=WatchlistItemResponse, status_code=201)
def add_to_watchlist(
    item: WatchlistItemCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add stock to watchlist"""
    # Ensure stock exists
    stock = get_or_fetch_stock(db, item.ticker)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    # Check if already in watchlist
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == item.ticker.upper()
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Stock already in watchlist")

    # Add to watchlist
    watchlist_item = Watchlist(
        user_id=current_user.id,
        ticker=item.ticker.upper()
    )
    db.add(watchlist_item)
    db.commit()
    db.refresh(watchlist_item)

    return watchlist_item

@router.delete("/{ticker}", status_code=204)
def remove_from_watchlist(
    ticker: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove stock from watchlist"""
    item = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ticker == ticker.upper()
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")

    db.delete(item)
    db.commit()

    return None
```

### **Step 2.7: Main FastAPI Application**

**File: `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import auth, stocks, screener, watchlist
from app.database.connection import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Stock Screener & Strategy Backtester API"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(stocks.router, prefix=settings.API_V1_PREFIX)
app.include_router(screener.router, prefix=settings.API_V1_PREFIX)
app.include_router(watchlist.router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {"message": "Stock Screener API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

### **Step 2.8: Database Migrations (Alembic)**

```bash
cd backend

# Initialize Alembic
alembic init alembic

# Edit alembic.ini - update sqlalchemy.url line to:
# sqlalchemy.url =

# Edit alembic/env.py - replace target_metadata line:
```

**File: `backend/alembic/env.py`** (modify these lines):

```python
# Add these imports at the top
from app.database.connection import Base
from app.database.models import User, Stock, StockPrice, Watchlist
from app.config import settings

# Replace target_metadata line with:
target_metadata = Base.metadata

# Replace sqlalchemy.url retrieval with:
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### **Step 2.9: Nightly Stock Loader Job**

**File: `backend/app/jobs/stock_loader.py`**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.services.stock_service import get_or_fetch_stock
from app.config import settings
import httpx
import time

def get_us_stock_tickers():
    """
    Fetch list of US stock tickers from GitHub
    Returns list of ticker symbols
    """
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        tickers = [line.strip() for line in response.text.split('\n') if line.strip()]
        return tickers[:10000]  # Limit to first 10,000
    except Exception as e:
        print(f"Error fetching ticker list: {e}")
        return []

def load_stocks_batch(tickers: list, batch_size: int = 1000):
    """
    Load a batch of stocks from yfinance
    """
    db = SessionLocal()
    loaded = 0
    failed = []

    for ticker in tickers[:batch_size]:
        try:
            stock = get_or_fetch_stock(db, ticker)
            if stock:
                loaded += 1
                print(f"✓ Loaded {ticker} ({loaded}/{len(tickers[:batch_size])})")
            else:
                failed.append(ticker)
                print(f"✗ Failed {ticker}")

            # Rate limiting - ~1 request per second
            time.sleep(1)

        except Exception as e:
            print(f"Error loading {ticker}: {e}")
            failed.append(ticker)

    db.close()

    print(f"\nBatch complete: {loaded} loaded, {len(failed)} failed")
    return loaded, failed

def nightly_stock_update():
    """
    Job that runs nightly to update stocks
    """
    print(f"Starting nightly stock update at {settings.STOCK_UPDATE_HOUR}:00 ET")

    tickers = get_us_stock_tickers()
    if not tickers:
        print("No tickers found, skipping update")
        return

    print(f"Found {len(tickers)} tickers")

    # Load batch
    load_stocks_batch(tickers, settings.STOCK_UPDATE_BATCH_SIZE)

    print("Nightly update complete")

def start_scheduler():
    """
    Start the APScheduler for nightly jobs
    """
    scheduler = BackgroundScheduler()

    # Schedule nightly update at specified hour (ET)
    scheduler.add_job(
        nightly_stock_update,
        trigger='cron',
        hour=settings.STOCK_UPDATE_HOUR,
        minute=0,
        timezone='America/New_York'
    )

    scheduler.start()
    print(f"Scheduler started - nightly updates at {settings.STOCK_UPDATE_HOUR}:00 ET")

    return scheduler
```

**Update `backend/app/main.py`** to start scheduler:

```python
# Add at the top
from app.jobs.stock_loader import start_scheduler

# Add after app creation
@app.on_event("startup")
def startup_event():
    start_scheduler()
```

### **Step 2.10: Run Backend Locally**

```bash
cd backend

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Server should start at http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## ⚛️ Phase 3: Frontend Development

### **Step 3.1: API Client Setup**

**File: `frontend/src/lib/api.ts`**

```typescript
import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/auth/login';
    }
    return Promise.reject(error);
  }
);
```

**File: `frontend/src/lib/stocks.ts`**

```typescript
import { api } from './api';

export interface Stock {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  pe_ratio: number;
  current_price: number;
  day_change_percent: number;
  dividend_yield: number;
  // ... add all other fields
}

export interface StockFilter {
  min_pe?: number;
  max_pe?: number;
  min_market_cap?: number;
  max_market_cap?: number;
  sectors?: string[];
  min_dividend_yield?: number;
  max_debt_to_equity?: number;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: string;
}

export const stockService = {
  getStock: async (ticker: string) => {
    const response = await api.get<Stock>(`/stocks/${ticker}`);
    return response.data;
  },

  getStockHistory: async (ticker: string, period: string = '1y') => {
    const response = await api.get(`/stocks/${ticker}/history`, {
      params: { period },
    });
    return response.data;
  },

  searchStocks: async (query: string) => {
    const response = await api.get(`/stocks/search/${query}`);
    return response.data;
  },

  screenStocks: async (filters: StockFilter) => {
    const response = await api.post('/screener/screen', filters);
    return response.data;
  },

  getSectors: async () => {
    const response = await api.get('/screener/sectors');
    return response.data;
  },

  getWatchlist: async () => {
    const response = await api.get('/watchlist');
    return response.data;
  },

  addToWatchlist: async (ticker: string) => {
    const response = await api.post('/watchlist', { ticker });
    return response.data;
  },

  removeFromWatchlist: async (ticker: string) => {
    await api.delete(`/watchlist/${ticker}`);
  },
};
```

**File: `frontend/src/lib/auth.ts`**

```typescript
import { api } from './api';

export interface LoginData {
  username: string; // email
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

export const authService = {
  login: async (data: LoginData) => {
    const formData = new FormData();
    formData.append('username', data.username);
    formData.append('password', data.password);

    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });

    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    return response.data;
  },

  register: async (data: RegisterData) => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
};
```

### **Step 3.2: TypeScript Types**

**File: `frontend/src/types/index.ts`**

```typescript
export interface Stock {
  ticker: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  peg_ratio: number | null;
  pb_ratio: number | null;
  ps_ratio: number | null;
  ev_to_ebitda: number | null;
  eps: number | null;
  profit_margin: number | null;
  operating_margin: number | null;
  roe: number | null;
  roa: number | null;
  revenue_growth: number | null;
  earnings_growth: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  quick_ratio: number | null;
  dividend_yield: number | null;
  dividend_rate: number | null;
  payout_ratio: number | null;
  current_price: number | null;
  day_change_percent: number | null;
  volume: number | null;
  avg_volume: number | null;
  beta: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  last_updated: string;
}

export interface StockPrice {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockFilter {
  min_pe?: number;
  max_pe?: number;
  min_market_cap?: number;
  max_market_cap?: number;
  sectors?: string[];
  industries?: string[];
  min_dividend_yield?: number;
  max_debt_to_equity?: number;
  min_price?: number;
  max_price?: number;
  skip?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface User {
  id: number;
  email: string;
  tier: string;
  is_active: boolean;
  created_at: string;
}

export interface WatchlistItem {
  id: number;
  ticker: string;
  added_at: string;
  stock: Stock;
}
```

### **Step 3.3: Key Components**

**File: `frontend/src/components/screener/FilterPanel.tsx`**

```typescript
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StockFilter } from '@/types';

interface FilterPanelProps {
  onApply: (filters: StockFilter) => void;
  sectors: string[];
}

export function FilterPanel({ onApply, sectors }: FilterPanelProps) {
  const [filters, setFilters] = useState<StockFilter>({
    skip: 0,
    limit: 50,
    sort_by: 'market_cap',
    sort_order: 'desc',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onApply(filters);
  };

  const handleReset = () => {
    const resetFilters: StockFilter = {
      skip: 0,
      limit: 50,
      sort_by: 'market_cap',
      sort_order: 'desc',
    };
    setFilters(resetFilters);
    onApply(resetFilters);
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Filters</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* P/E Ratio */}
          <div className="space-y-2">
            <Label>P/E Ratio</Label>
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder="Min"
                value={filters.min_pe || ''}
                onChange={(e) =>
                  setFilters({ ...filters, min_pe: parseFloat(e.target.value) || undefined })
                }
              />
              <Input
                type="number"
                placeholder="Max"
                value={filters.max_pe || ''}
                onChange={(e) =>
                  setFilters({ ...filters, max_pe: parseFloat(e.target.value) || undefined })
                }
              />
            </div>
          </div>

          {/* Market Cap */}
          <div className="space-y-2">
            <Label>Market Cap</Label>
            <Select
              value={filters.min_market_cap?.toString() || 'any'}
              onValueChange={(value) =>
                setFilters({
                  ...filters,
                  min_market_cap: value === 'any' ? undefined : parseInt(value),
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any</SelectItem>
                <SelectItem value="1000000000">&gt; $1B (Large Cap)</SelectItem>
                <SelectItem value="10000000000">&gt; $10B (Mega Cap)</SelectItem>
                <SelectItem value="100000000000">&gt; $100B</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Sector */}
          <div className="space-y-2">
            <Label>Sector</Label>
            <Select
              value={filters.sectors?.[0] || 'any'}
              onValueChange={(value) =>
                setFilters({
                  ...filters,
                  sectors: value === 'any' ? undefined : [value],
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="any">Any</SelectItem>
                {sectors.map((sector) => (
                  <SelectItem key={sector} value={sector}>
                    {sector}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Dividend Yield */}
          <div className="space-y-2">
            <Label>Min Dividend Yield (%)</Label>
            <Input
              type="number"
              step="0.1"
              placeholder="0"
              value={filters.min_dividend_yield || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  min_dividend_yield: parseFloat(e.target.value) || undefined,
                })
              }
            />
          </div>

          {/* Debt to Equity */}
          <div className="space-y-2">
            <Label>Max Debt/Equity</Label>
            <Input
              type="number"
              step="0.1"
              placeholder="No limit"
              value={filters.max_debt_to_equity || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  max_debt_to_equity: parseFloat(e.target.value) || undefined,
                })
              }
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-2">
            <Button type="submit" className="flex-1">
              Apply Filters
            </Button>
            <Button type="button" variant="outline" onClick={handleReset}>
              Reset
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
```

**File: `frontend/src/components/screener/StockTable.tsx`**

```typescript
'use client';

import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Stock } from '@/types';
import { useRouter } from 'next/navigation';
import { Star } from 'lucide-react';

interface StockTableProps {
  stocks: Stock[];
  onAddToWatchlist?: (ticker: string) => void;
}

export function StockTable({ stocks, onAddToWatchlist }: StockTableProps) {
  const router = useRouter();

  const formatNumber = (num: number | null) => {
    if (num === null) return 'N/A';
    return num.toLocaleString('en-US', { maximumFractionDigits: 2 });
  };

  const formatMarketCap = (cap: number | null) => {
    if (cap === null) return 'N/A';
    if (cap >= 1e12) return `$${(cap / 1e12).toFixed(2)}T`;
    if (cap >= 1e9) return `$${(cap / 1e9).toFixed(2)}B`;
    if (cap >= 1e6) return `$${(cap / 1e6).toFixed(2)}M`;
    return `$${cap.toFixed(2)}`;
  };

  const formatPercent = (pct: number | null) => {
    if (pct === null) return 'N/A';
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  return (
    <Table>
      <TableCaption>Stock screening results</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead>Ticker</TableHead>
          <TableHead>Name</TableHead>
          <TableHead className="text-right">Price</TableHead>
          <TableHead className="text-right">Change %</TableHead>
          <TableHead className="text-right">Market Cap</TableHead>
          <TableHead className="text-right">P/E</TableHead>
          <TableHead className="text-right">Div Yield</TableHead>
          <TableHead className="text-center">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {stocks.map((stock) => (
          <TableRow
            key={stock.ticker}
            className="cursor-pointer hover:bg-muted"
            onClick={() => router.push(`/stocks/${stock.ticker}`)}
          >
            <TableCell className="font-medium">{stock.ticker}</TableCell>
            <TableCell>{stock.name}</TableCell>
            <TableCell className="text-right">
              ${formatNumber(stock.current_price)}
            </TableCell>
            <TableCell
              className={`text-right ${
                stock.day_change_percent && stock.day_change_percent >= 0
                  ? 'text-green-600'
                  : 'text-red-600'
              }`}
            >
              {formatPercent(stock.day_change_percent)}
            </TableCell>
            <TableCell className="text-right">
              {formatMarketCap(stock.market_cap)}
            </TableCell>
            <TableCell className="text-right">
              {formatNumber(stock.pe_ratio)}
            </TableCell>
            <TableCell className="text-right">
              {stock.dividend_yield
                ? `${(stock.dividend_yield * 100).toFixed(2)}%`
                : 'N/A'}
            </TableCell>
            <TableCell className="text-center">
              {onAddToWatchlist && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={(e) => {
                    e.stopPropagation();
                    onAddToWatchlist(stock.ticker);
                  }}
                >
                  <Star className="h-4 w-4" />
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

**File: `frontend/src/components/stock/StockChart.tsx`**

```typescript
'use client';

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StockPrice } from '@/types';
import { format } from 'date-fns';

interface StockChartProps {
  ticker: string;
  prices: StockPrice[];
}

const periods = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max'];

export function StockChart({ ticker, prices: initialPrices }: StockChartProps) {
  const [period, setPeriod] = useState('1y');
  const [prices, setPrices] = useState(initialPrices);

  useEffect(() => {
    // Fetch new data when period changes
    const fetchPrices = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/stocks/${ticker}/history?period=${period}`
        );
        const data = await response.json();
        setPrices(data);
      } catch (error) {
        console.error('Error fetching price data:', error);
      }
    };

    fetchPrices();
  }, [period, ticker]);

  const chartData = prices.map((price) => ({
    date: price.date,
    price: price.close,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Price Chart</CardTitle>
        <div className="flex gap-2 flex-wrap">
          {periods.map((p) => (
            <Button
              key={p}
              size="sm"
              variant={period === p ? 'default' : 'outline'}
              onClick={() => setPeriod(p)}
            >
              {p.toUpperCase()}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => format(new Date(value), 'MMM dd')}
            />
            <YAxis domain={['auto', 'auto']} />
            <Tooltip
              labelFormatter={(value) => format(new Date(value), 'MMM dd, yyyy')}
              formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
            />
            <Line type="monotone" dataKey="price" stroke="#8884d8" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

### **Step 3.4: Pages**

**File: `frontend/src/app/page.tsx`** (Home page)

```typescript
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function Home() {
  return (
    <div className="container mx-auto px-4 py-16">
      <div className="max-w-4xl mx-auto text-center space-y-8">
        <h1 className="text-5xl font-bold">
          Find Undervalued Stocks with Quantor Signal
        </h1>
        <p className="text-xl text-muted-foreground">
          Advanced stock screening and backtesting platform for value investors
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/screener">
            <Button size="lg">Start Screening</Button>
          </Link>
          <Link href="/auth/register">
            <Button size="lg" variant="outline">
              Sign Up Free
            </Button>
          </Link>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-8 mt-16">
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Advanced Filters</h3>
            <p className="text-muted-foreground">
              Screen stocks by P/E, market cap, sector, dividend yield, and more
            </p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Real-time Data</h3>
            <p className="text-muted-foreground">
              Up-to-date stock fundamentals and price data
            </p>
          </div>
          <div className="p-6 border rounded-lg">
            <h3 className="text-xl font-semibold mb-2">Strategy Testing</h3>
            <p className="text-muted-foreground">
              Backtest trading strategies with historical data
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

**File: `frontend/src/app/screener/page.tsx`**

```typescript
'use client';

import { useState, useEffect } from 'react';
import { FilterPanel } from '@/components/screener/FilterPanel';
import { StockTable } from '@/components/screener/StockTable';
import { stockService } from '@/lib/stocks';
import { Stock, StockFilter } from '@/types';
import { toast } from '@/components/ui/use-toast';

export default function ScreenerPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [sectors, setSectors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Load sectors
    stockService.getSectors().then((data) => setSectors(data.sectors));

    // Load initial stocks
    handleApplyFilters({
      skip: 0,
      limit: 50,
      sort_by: 'market_cap',
      sort_order: 'desc',
    });
  }, []);

  const handleApplyFilters = async (filters: StockFilter) => {
    setLoading(true);
    try {
      const data = await stockService.screenStocks(filters);
      setStocks(data.stocks);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load stocks',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleAddToWatchlist = async (ticker: string) => {
    try {
      await stockService.addToWatchlist(ticker);
      toast({
        title: 'Success',
        description: `${ticker} added to watchlist`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to add to watchlist',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Stock Screener</h1>
      <div className="grid lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <FilterPanel onApply={handleApplyFilters} sectors={sectors} />
        </div>
        <div className="lg:col-span-3">
          {loading ? (
            <div>Loading...</div>
          ) : (
            <StockTable stocks={stocks} onAddToWatchlist={handleAddToWatchlist} />
          )}
        </div>
      </div>
    </div>
  );
}
```

**File: `frontend/src/app/stocks/[ticker]/page.tsx`**

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { StockChart } from '@/components/stock/StockChart';
import { stockService } from '@/lib/stocks';
import { Stock, StockPrice } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function StockDetailPage() {
  const params = useParams();
  const ticker = params.ticker as string;

  const [stock, setStock] = useState<Stock | null>(null);
  const [prices, setPrices] = useState<StockPrice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [stockData, priceData] = await Promise.all([
          stockService.getStock(ticker),
          stockService.getStockHistory(ticker, '1y'),
        ]);
        setStock(stockData);
        setPrices(priceData);
      } catch (error) {
        console.error('Error loading stock:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [ticker]);

  if (loading) return <div>Loading...</div>;
  if (!stock) return <div>Stock not found</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold">
          {stock.ticker} - {stock.name}
        </h1>
        <div className="flex items-center gap-4 mt-2">
          <span className="text-3xl font-semibold">
            ${stock.current_price?.toFixed(2) || 'N/A'}
          </span>
          <span
            className={
              stock.day_change_percent && stock.day_change_percent >= 0
                ? 'text-green-600'
                : 'text-red-600'
            }
          >
            {stock.day_change_percent
              ? `${stock.day_change_percent >= 0 ? '+' : ''}${stock.day_change_percent.toFixed(2)}%`
              : 'N/A'}
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="mb-8">
        <StockChart ticker={ticker} prices={prices} />
      </div>

      {/* Metrics Grid */}
      <div className="grid md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Valuation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">P/E Ratio:</span>
              <span className="font-medium">{stock.pe_ratio?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Forward P/E:</span>
              <span className="font-medium">
                {stock.forward_pe?.toFixed(2) || 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">PEG Ratio:</span>
              <span className="font-medium">{stock.peg_ratio?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">P/B Ratio:</span>
              <span className="font-medium">{stock.pb_ratio?.toFixed(2) || 'N/A'}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Profitability</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">EPS:</span>
              <span className="font-medium">${stock.eps?.toFixed(2) || 'N/A'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Profit Margin:</span>
              <span className="font-medium">
                {stock.profit_margin ? `${(stock.profit_margin * 100).toFixed(2)}%` : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">ROE:</span>
              <span className="font-medium">
                {stock.roe ? `${(stock.roe * 100).toFixed(2)}%` : 'N/A'}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dividends</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Yield:</span>
              <span className="font-medium">
                {stock.dividend_yield
                  ? `${(stock.dividend_yield * 100).toFixed(2)}%`
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Payout Ratio:</span>
              <span className="font-medium">
                {stock.payout_ratio ? `${(stock.payout_ratio * 100).toFixed(2)}%` : 'N/A'}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

### **Step 3.5: Run Frontend Locally**

```bash
cd frontend

# Install dependencies (if not done)
npm install

# Run development server
npm run dev

# App should start at http://localhost:3000
```

---

## 🧪 Phase 4: Integration & Testing

### **Step 4.1: Test Backend Endpoints**

```bash
# Using curl or Postman

# 1. Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: multipart/form-data" \
  -F "username=test@example.com" \
  -F "password=password123"
# Copy the access_token from response

# 3. Get stock
curl http://localhost:8000/api/v1/stocks/AAPL

# 4. Screen stocks
curl -X POST http://localhost:8000/api/v1/screener/screen \
  -H "Content-Type: application/json" \
  -d '{"min_pe":10,"max_pe":20,"limit":10}'

# 5. Add to watchlist (requires auth token)
curl -X POST http://localhost:8000/api/v1/watchlist \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"ticker":"AAPL"}'
```

### **Step 4.2: Manual Testing Checklist**

- [ ] User registration works
- [ ] User login works and returns token
- [ ] Stock detail page loads data
- [ ] Stock chart displays correctly
- [ ] Screener filters work
- [ ] Watchlist add/remove works
- [ ] Authentication redirects work
- [ ] Error messages display properly

---

## 🚀 Phase 5: Deployment

### **Step 5.1: Deploy Backend to Railway**

```bash
cd backend

# Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create runtime.txt
echo "python-3.10.12" > runtime.txt

# Commit changes
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

**In Railway Dashboard**:
1. Go to your project
2. Click backend service → Settings
3. Add build command: `pip install -r requirements.txt`
4. Add start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env`
6. Deploy!
7. Copy the public URL (e.g., `https://yourapp.railway.app`)

### **Step 5.2: Deploy Frontend to Vercel**

```bash
cd frontend

# Update .env.local with Railway backend URL
# NEXT_PUBLIC_API_URL=https://yourapp.railway.app/api/v1

# Commit
git add .
git commit -m "Update API URL for production"
git push origin main
```

**Deploy to Vercel**:
1. Go to [vercel.com](https://vercel.com)
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Set root directory to `frontend`
5. Add environment variable: `NEXT_PUBLIC_API_URL=https://yourapp.railway.app/api/v1`
6. Click "Deploy"
7. Your site will be live at `https://yourproject.vercel.app`

### **Step 5.3: Initial Stock Data Load**

```bash
# SSH into Railway or run locally pointing to production DB

python -c "
from app.jobs.stock_loader import load_stocks_batch, get_us_stock_tickers
tickers = get_us_stock_tickers()
load_stocks_batch(tickers[:500], batch_size=500)
"

# This will load first 500 stocks (S&P 500)
# Nightly job will continue loading more
```

---

## 🔬 Phase 6: Backtester Integration (Later)

### **Step 6.1: Copy Backtesting Code**

```bash
cd backend

# Create backtests directory structure
mkdir -p app/backtests
mkdir -p app/backtests/utils

# Copy your existing files:
# - Copy your backtester files to app/backtests/
# - Copy data_fetcher.py to app/backtests/utils/
```

### **Step 6.2: Create Backtest API**

**File: `backend/app/routes/backtest.py`**

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.models import User
from app.services.auth import get_current_active_user
# Import your backtest functions
from app.backtests.strategies import backtest_rsi, backtest_macd

router = APIRouter(prefix="/backtest", tags=["backtesting"])

@router.post("/run")
def run_backtest(
    ticker: str,
    strategy: str,
    start_date: str,
    end_date: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Run a backtest (as background job)"""
    # Queue backtest job
    # Return job ID
    pass

@router.get("/strategies")
def list_strategies():
    """List available strategies"""
    return {
        "strategies": [
            {"id": "rsi", "name": "RSI Threshold"},
            {"id": "macd", "name": "MACD Crossover"},
            {"id": "sma_cross", "name": "SMA Crossover"},
            # ... more
        ]
    }

@router.get("/results/{job_id}")
def get_backtest_results(job_id: str):
    """Get backtest results"""
    # Fetch from DB
    pass
```

### **Step 6.3: Backtester Frontend**

Create pages similar to screener but for backtesting:
- `/backtest` - Strategy selection
- `/backtest/results/[id]` - Results visualization

---

## 📊 Database Schema Reference

```sql
-- Complete schema created by Alembic migrations

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    tier VARCHAR(20) DEFAULT 'free',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE stocks (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    pe_ratio DOUBLE PRECISION,
    forward_pe DOUBLE PRECISION,
    peg_ratio DOUBLE PRECISION,
    pb_ratio DOUBLE PRECISION,
    ps_ratio DOUBLE PRECISION,
    ev_to_ebitda DOUBLE PRECISION,
    eps DOUBLE PRECISION,
    profit_margin DOUBLE PRECISION,
    operating_margin DOUBLE PRECISION,
    roe DOUBLE PRECISION,
    roa DOUBLE PRECISION,
    revenue_growth DOUBLE PRECISION,
    earnings_growth DOUBLE PRECISION,
    debt_to_equity DOUBLE PRECISION,
    current_ratio DOUBLE PRECISION,
    quick_ratio DOUBLE PRECISION,
    dividend_yield DOUBLE PRECISION,
    dividend_rate DOUBLE PRECISION,
    payout_ratio DOUBLE PRECISION,
    current_price DOUBLE PRECISION,
    day_change_percent DOUBLE PRECISION,
    volume BIGINT,
    avg_volume BIGINT,
    beta DOUBLE PRECISION,
    fifty_two_week_high DOUBLE PRECISION,
    fifty_two_week_low DOUBLE PRECISION,
    raw_data JSONB,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) REFERENCES stocks(ticker) ON DELETE CASCADE,
    date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    UNIQUE(ticker, date)
);

CREATE TABLE watchlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    ticker VARCHAR(10) REFERENCES stocks(ticker) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, ticker)
);

-- Indexes for performance
CREATE INDEX idx_stocks_sector ON stocks(sector);
CREATE INDEX idx_stocks_pe_ratio ON stocks(pe_ratio);
CREATE INDEX idx_stocks_market_cap ON stocks(market_cap);
CREATE INDEX idx_stocks_dividend_yield ON stocks(dividend_yield);
CREATE INDEX idx_stocks_debt_to_equity ON stocks(debt_to_equity);
CREATE INDEX idx_stocks_last_updated ON stocks(last_updated);
CREATE INDEX idx_stock_prices_ticker_date ON stock_prices(ticker, date);
CREATE INDEX idx_watchlists_user_id ON watchlists(user_id);
```

---

## 🛣 API Endpoints Reference

### **Authentication**
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT)
- `GET /api/v1/auth/me` - Get current user info

### **Stocks**
- `GET /api/v1/stocks/{ticker}` - Get stock details
- `GET /api/v1/stocks/{ticker}/history?period=1y` - Get price history
- `GET /api/v1/stocks/search/{query}` - Search stocks

### **Screener**
- `POST /api/v1/screener/screen` - Screen stocks with filters
- `GET /api/v1/screener/sectors` - Get list of sectors
- `GET /api/v1/screener/industries` - Get list of industries

### **Watchlist** (requires auth)
- `GET /api/v1/watchlist` - Get user's watchlist
- `POST /api/v1/watchlist` - Add stock to watchlist
- `DELETE /api/v1/watchlist/{ticker}` - Remove from watchlist

### **Backtesting** (Phase 2)
- `POST /api/v1/backtest/run` - Run backtest
- `GET /api/v1/backtest/strategies` - List strategies
- `GET /api/v1/backtest/results/{id}` - Get results

---

## 💻 Development Workflow

### **Daily Development**

1. **Start Backend**:
```bash
cd backend
venv\Scripts\activate  # Windows
uvicorn app.main:app --reload
```

2. **Start Frontend**:
```bash
cd frontend
npm run dev
```

3. **Make Changes**:
- Edit code
- Test in browser
- Check API docs at http://localhost:8000/docs

4. **Commit**:
```bash
git add .
git commit -m "Description of changes"
git push origin main
```

5. **Auto-deploy**:
- Railway and Vercel will auto-deploy on push to main

### **Adding New Features**

1. **Backend**:
- Add database model in `app/database/models.py`
- Create Pydantic schema in `app/models/`
- Create service in `app/services/`
- Create route in `app/routes/`
- Create migration: `alembic revision --autogenerate -m "description"`
- Apply: `alembic upgrade head`

2. **Frontend**:
- Add type in `src/types/index.ts`
- Add API call in `src/lib/`
- Create component in `src/components/`
- Create page in `src/app/`

---

## 🎯 Next Steps After MVP

### **Phase 1 Completion Checklist**
- [ ] Backend API running on Railway
- [ ] Frontend deployed on Vercel
- [ ] S&P 500 stocks loaded in database
- [ ] User registration/login working
- [ ] Stock screener functional
- [ ] Stock detail pages showing data
- [ ] Charts displaying correctly
- [ ] Watchlist CRUD working
- [ ] Nightly job running

### **Future Enhancements**
1. Add backtester integration (Phase 2)
2. Implement Stripe for payments
3. Add premium features (export to CSV, alerts, etc.)
4. Improve ML undervaluation scoring
5. Add more stock exchanges (international)
6. Mobile app (React Native)
7. Email notifications
8. Social features (share watchlists)
9. Advanced charting (TradingView integration)
10. Portfolio tracking

---

## 📞 Support & Resources

### **Documentation**
- FastAPI: https://fastapi.tiangolo.com/
- Next.js: https://nextjs.org/docs
- SQLAlchemy: https://docs.sqlalchemy.org/
- shadcn/ui: https://ui.shadcn.com/
- Railway: https://docs.railway.app/
- Vercel: https://vercel.com/docs

### **Troubleshooting**
- Check Railway logs for backend errors
- Check Vercel logs for frontend errors
- Use browser DevTools Network tab for API issues
- Check PostgreSQL logs in Railway dashboard

---

## ✅ Summary

This guide covers:
- ✅ Complete tech stack (40+ technologies)
- ✅ Step-by-step setup for both backend & frontend
- ✅ Database schema with migrations
- ✅ Authentication with JWT
- ✅ Stock data fetching & caching
- ✅ Screener with filters
- ✅ Stock detail pages with charts
- ✅ Watchlist functionality
- ✅ Nightly stock loading job
- ✅ Deployment to Railway & Vercel
- ✅ Future backtester integration

**Total Estimated Development Time**: 2-3 weeks for Phase 1 MVP

Good luck with your project!
