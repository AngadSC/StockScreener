# Launch Checklist

Everything below is required to fully activate what shipped in the July 2026
wave (emails, Trader/Elite tiers, macro page). The app runs fine with these
unset — features degrade gracefully (emails no-op, unconfigured tiers return
503 at checkout, macro page shows a setup notice) — so deploy first, then work
down this list. Placeholder keys are already stubbed in `backend/.env` locally
and documented in `.env.example`.

## 1. Database migration (required first)

```bash
cd backend && alembic upgrade head
```

Adds 5 tables (email_preferences, email_send_log, insider_transactions,
earnings_events, macro_observations) in one linear chain. On Railway, run it
via `Dockerfile.migrate` or a one-off shell.

## 2. Stripe — activate Trader & Elite checkout

1. Dashboard → Products: add two recurring monthly Prices — $39.99 (Trader)
   and $79.99 (Elite). Same test/live mode as the existing Pro price.
2. Set `STRIPE_TRADER_PRICE_ID` and `STRIPE_ELITE_PRICE_ID` in the backend env
   (Railway variables + local `.env`), restart.
3. Customer Portal settings: put Pro/Trader/Elite Prices in the same product
   set so subscribers can switch plans in-portal (plan changes flow through
   `customer.subscription.updated` and set the right tier automatically).
4. Verify with `stripe listen --forward-to localhost:8000/webhooks/stripe`,
   card `4242 4242 4242 4242`, then check `GET /api/v1/auth/me` shows the tier.

## 3. Resend — activate all email features

1. resend.com → add and verify the sending domain (SPF + DKIM records).
2. Set `RESEND_API_KEY`, confirm `EMAIL_FROM` uses the verified domain, then
   flip `EMAIL_ENABLED=true`. (While false, digests/briefs also skip their
   LLM calls — no wasted tokens.)
3. `PUBLIC_APP_URL` must route `/api/v1/*` to the backend (unsubscribe links).
4. Smoke test as admin:
   - `POST /api/v1/admin/email/test {"to":"you@..."}` — deliverability
   - `GET /api/v1/admin/brief/preview` — renders the Daily Market Brief HTML
   - `GET /api/v1/admin/digest/preview?user_id=<id>` — renders a Watchlist Digest
   - `POST /api/v1/admin/brief/run {"user_id":<you>,"force":true}` — real send

## 4. FRED — activate the /macro page

Free key: fred.stlouisfed.org → API key → set `FRED_API_KEY`. First sync runs
at 6:00 AM ET, or trigger manually:
`python -c "from app.jobs.macro_sync import sync_macro_observations; sync_macro_observations(manual_trigger=True)"`

## 5. One-time data backfills (optional but recommended)

```bash
# Insider filings — last 7 days of Form 4s (auto-runs on first empty sync too)
python -c "from app.jobs.insider_sync import run_insider_sync; run_insider_sync()"
# Earnings calendar
python -c "from app.jobs.earnings_sync import sync_earnings_events; sync_earnings_events(manual_trigger=True)"
```

Sectors/heatmap need no action — the nightly 9 PM ET job now populates
`stock_fundamentals.sector` correctly (assetProfile fix) and the scanner cache
warms at 10:30 PM ET.

## Daily schedule after full activation (all ET)

| Time | Job |
|---|---|
| 06:00 | FRED macro sync |
| 07:00 Mon–Fri | Elite Watchlist AI Digest emails |
| 07:45 Mon–Fri | Trader/Elite Daily Market Brief email |
| 18:45 Mon–Fri | SEC Form 4 insider sync |
| 21:00 | OHLCV + fundamentals nightly update |
| 22:30 | Market scanners cache warm |
| 23:15 | Earnings calendar sync |
| Sun 03:00 | Old price data trim |

## Cost expectations

- Daily Market Brief: ~1 LLM call/day total (≈ $0.01/day) regardless of users.
- Watchlist Digest: ≤10 stocks/user/day, hard cap 300 LLM calls per run
  (`DIGEST_MAX_LLM_CALLS_PER_RUN`), reuses any report already generated that
  day, never consumes users' monthly quotas.
- Resend free tier: 3,000 emails/month, then ~$20/mo for 50k.
- FRED + SEC EDGAR: free APIs, no keys sold. EDGAR politeness (UA header +
  throttle) is built in.
