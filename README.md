# QuantorSignal

Stock screener and analysis app: screener, stock pages, watchlists, backtester,
AI swing-analysis reports, earnings/insider/macro pages, and email digests, with
Stripe-billed tiers (Free / Pro / Trader / Elite).

## Stack

- **Backend** (`backend/`): Python 3.13, FastAPI, SQLAlchemy 2 + Alembic
  (PostgreSQL), Redis cache, APScheduler jobs, yfinance/yahooquery market data,
  Stripe, Resend, OpenAI/Anthropic.
- **Frontend** (`frontend/`): Next.js 16 (App Router), React 19, TypeScript,
  Tailwind CSS 3, TanStack Query.

## Running locally

Backend (needs PostgreSQL and Redis; see `.env.example` for optional keys):

```bash
cd backend
python -m venv venv && source venv/Scripts/activate   # venv/bin/activate on macOS/Linux
pip install -r requirements.txt
# backend/.env must set at least DATABASE_URL, REDIS_URL, SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload            # http://localhost:8000/docs
```

Frontend:

```bash
cd frontend
npm ci
# frontend/.env.local: NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev                              # http://localhost:3000
```

## Tests and checks

```bash
# backend/: no DB or network needed (in-memory SQLite, mocks)
pip install pytest && pytest tests
# frontend/
npm run lint && npm run typecheck && npm run build
```

Live Yahoo tests are skipped unless `RUN_LIVE_MARKET_DATA_TESTS=1`.
CI (`.github/workflows/ci.yml`) runs both on every push and pull request.

## Deployment

- **Backend**: Railway, `backend/Procfile` (`uvicorn app.main:app`), Python
  version from `backend/runtime.txt`. Schema migrations run via
  `Dockerfile.migrate` (`alembic upgrade head`).
- **Frontend**: Vercel, from `frontend/`.

See `LAUNCH_CHECKLIST.md` for required env vars and one-time setup.
