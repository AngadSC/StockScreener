# Handoff: QuantorSignal — Stock Screener & Research Terminal

## Overview
QuantorSignal is a dark, editorial **stock screening + research terminal**. It has four working areas:
**Markets** (dashboard), **Screener**, **Stock detail**, and **AI Analyst**. The aesthetic is a
refined "after-hours trading desk": near-black obsidian surfaces, a brushed **platinum-steel** primary
accent, a **sapphire** secondary accent for technical/live moments, warm cream text, and a
literary serif (Spectral) for headlines and numbers.

## About the Design Files
The files in this bundle are **design references created in HTML/React-via-Babel** — runnable
prototypes showing the intended look and behavior, **not production code to copy directly**.
The task is to **recreate these designs in your target codebase** (React/Next, Vue, etc.) using its
established component patterns, routing, and data layer. If no front-end environment exists yet,
React + TypeScript + Vite (or Next.js) is a natural fit given the prototype is already React.

The prototype uses in-browser Babel and a single global `STOCKS` mock array. In production you'd
replace the mock data with a real quotes/fundamentals API and split the inline-styled components
into your own styling system (CSS modules, Tailwind, styled-components — your call).

## Fidelity
**High-fidelity.** Colors, typography, spacing, radii, and interactions are final. Recreate the UI
pixel-closely using the tokens below. The one thing that is deliberately mock is the **data** (a static
array of ~30 tickers with fabricated prices) and the sparkline/chart generator.

## Screens / Views

### 1. App shell
- **Layout**: Fixed **left sidebar** (248px) + fluid main column (`flex:1`, `min-width:0`, `border-left:1px solid --line`).
- **Sidebar** (top→bottom): crest logo + "Quantorsignal" wordmark ("signal" in italic platinum); a **Search** button (opens command palette, ⌘K); nav items (Markets, Screener, Watchlist, AI Analyst, Backtester); a spacer; a "Quantor Pro" upgrade card; a user row (avatar, name, gear).
- **Nav item**: 10×14px padding, 10px radius, icon + label; active state has `--surface-2` bg + a 3px platinum bar on the far left (`::before`, left:-16px).
- **Command palette**: ⌘K / Ctrl-K. Centered modal (max 640px) over a `rgba(0,0,0,0.65)` blur scrim. Search field (Spectral) + result rows (ticker in serif, name, sector, price, delta). Esc or backdrop closes.

### 2. Markets (dashboard) — `page-dashboard.jsx`
- **Page header**: big "Markets" title (Spectral, clamp 36–52px) + one-line subtitle + two buttons (Open screener / View today's brief). Left-aligned hero — keep this.
- **Index row**: 6 equal columns (S&P 500, NASDAQ 100, Russell 2000, Treasury 10Y, Gold, WTI Crude), each a label + serif number + delta. Separated by 1px vertical rules, framed top+bottom by hairlines.
- **Featured + Watchlist** (grid `1.6fr / 1fr`, gap 24):
  - *Featured card* (`.card .hud`): spotlight ticker, big serif price (readout), delta, range segmented control (1D/5D/1M/3M/YTD/1Y), area chart (with a slow sapphire scan-line sweep), a 4-stat row, and action buttons. Corner HUD brackets light up on hover.
  - *Watchlist card* (`.card .hud .hud-blue`): "Core six" rows — ticker, sector, sparkline, price, delta. Footer "Net position today".
- **Movers**: section title + two columns ("Advancing" / "Declining"), each a ranked list of 5 (rank, ticker+name, sector, sparkline, price, delta).
- **Sector flow**: two-column list of all sectors, each row = name + constituent count + a progress bar (magnitude) + signed % (green/red).
- **Editorial close**: an AI "morning brief" card (ivory surface, drop-cap, prose) beside a "Market wire" list (time · source · serif headline).

### 3. Screener — `page-screener.jsx`
- **Header**: "Screener" + subtitle. Below it a row of **saved-screen chips** (Quality / Deep value / Growth / Dividend / Mega tech); selected chip is filled `--ink`.
- **Body**: 2-col grid `280px / 1fr`, gap 32.
  - *Filter rail* (sticky): "Criteria" + Reset; fields = text search, price min/max inputs, market-cap range slider, max-P/E slider, min-ROE slider, sector checklist, two toggles (Dividend payers only, Profitable only). **All filters apply live.**
  - *Results*: a count readout ("NNN matches of 30"), a Columns button, and a **sortable table** (checkbox select, Symbol, Last, Day, Trend sparkline, Market cap, P/E, ROE, Yield, Volume, Sector). Clicking a header toggles sort asc/desc; clicking a row opens the stock detail; checkbox multi-select reveals a "Save selection / Backtest" action bar. Empty state + pagination footer.

### 4. Stock detail — `page-stock.jsx`
- **Breadcrumb** (Markets · Sector · TICKER) then a **hero**: giant ticker (Spectral, clamp 64–96px), company name (italic), industry line on the left; live timestamp, huge price readout (green/red), delta, and action buttons (AI analysis / Save / alerts) on the right.
- **52-week range** bar: gradient track (terracotta→steel→green) with a marker dot at the current position.
- **Key-stats strip**: 8 cells (Market cap, Volume, P/E, ROE, Beta, Dividend, Revenue, EPS).
- **Tabs**: overview / fundamentals / research / news / peers / filings (active tab has a 1.5px underline).
- **Main grid** `1.55fr / 1fr`:
  - Left: price chart card (range segmented control, area chart w/ scan line, OHLC row); a **research brief** (ivory) with conviction score, drop-cap narrative, bull/bear thesis columns, catalysts; a factor-scores card.
  - Right: a **Signal snapshot** card (conviction dial, recommendation, entry/target/stop levels, risk-reward); a news list; a fundamentals grid; a peers list.
- **Note**: there is intentionally **no trade ticket / order entry** — this is a research tool, not a broker.

### 5. AI Analyst — `page-ai.jsx`
- **Header**: "AI Analyst" + subtitle.
- **Ask bar** (`.glass .hud .hud-blue`): a natural-language input ("Ask the analyst to build a thesis or screen…") + Generate button, with a row of italic suggestion chips below.
- **Main grid** `1fr / 1.5fr`:
  - *Conviction queue*: ranked list of 8 ideas (rank, ticker, recommendation, score bar, score). Selecting one updates the brief on the right (brief panel dims ~480ms while "thinking").
  - *Generated brief* (ivory `.hud`): big ticker, conviction ring dial, a recommendation/last/target/trend strip, a drop-cap narrative, two-sided thesis, and action buttons (Open full detail / Regenerate / Save).
- **Recent briefs**: 3 hover-cards (ticker, headline, BULLISH/BEARISH status).

## Interactions & Behavior
- **Routing**: client-side, in `app.jsx` — `route = { name, ticker? }`. Names: `home`, `screener`, `stock`, `ai`, plus placeholders `watch`/`backtest` (ComingSoon). Replace with your router (e.g. `/`, `/screener`, `/stocks/:ticker`, `/ai`).
- **Command palette**: global ⌘K / Ctrl-K key listener; Esc closes; picking a result routes to that stock.
- **Screener filters**: pure `useMemo` over the `STOCKS` array — recompute the filtered+sorted list on every control change. No debounce needed for 30 rows; debounce text search against a real API.
- **Sorting**: click header → if same key flip direction, else set key + default desc.
- **Selection**: a `Set` of tickers; header checkbox toggles all.
- **AI queue select**: sets `thinking=true`, swaps selection, clears `thinking` after 480ms (purely cosmetic dim).
- **Page entrance**: `.page-enter` does a **transform-only** slide-up (no opacity) so content is never hidden if the animation doesn't run. Keep this principle.
- **HUD brackets / scan line**: decorative; brackets fade in on hover, the chart scan line is a 6s infinite sapphire sweep.

## State Management
- `route` (current view + optional ticker) — lift to your router.
- Screener: `search`, `sectorFilter (Set)`, `priceRange [min,max]`, `minMcap`, `maxPe`, `minRoe`, `dividendOnly`, `profitableOnly`, `sortBy`, `sortDir`, `savedView`, `selected (Set)`.
- Stock detail: `range`, `tab`, `watch`.
- AI Analyst: `selected (ticker)`, `thinking`.
- Command palette: `open`, query string.
- **Data**: replace the static `STOCKS` array with quotes + fundamentals from your API. Each row needs: `ticker, name, sector, industry, price, chg (%), mcap, vol, pe, roe, divy, beta, rev_g, w52l, w52h` plus a price series for sparklines/charts.

## Design Tokens

### Color (CSS custom properties, dark theme)
```
--bone        #050405   (app background)
--bone-deep   #020203
--ivory       #0c0b0e   (inset "paper" cards)
--surface     #0f0e13   (card background)
--surface-2   #16151c   (raised/hover)

--ink         #d8d2c0   (primary text, warm cream)
--ink-2       #a8a294   (secondary text)
--mute        #7a7568   (tertiary)
--whisper     #4f4a42
--ghost       #2a2730

--line        rgba(216,210,192,0.06)   (hairline)
--line-2      rgba(216,210,192,0.13)
--line-3      rgba(216,210,192,0.26)

--forest      #aeb9c7   (PRIMARY accent — brushed platinum-steel)
--forest-2    #c8d2de
--forest-soft rgba(174,185,199,0.10)
--forest-line rgba(174,185,199,0.28)

--sapphire      #5b9cd6  (SECONDARY accent — technical/live)
--sapphire-2    #7ab2e0
--sapphire-soft rgba(91,156,214,0.10)
--sapphire-glow rgba(91,156,214,0.22)

--amber       #e8a032   (high-priority alerts ONLY — used sparingly)

--up          #5ba879   (positive)   --up-soft   rgba(91,168,121,0.12)
--dn          #c25a3a   (negative)   --dn-soft   rgba(194,90,58,0.12)
```

### Shadows / depth
```
--shadow-1  0 0 0 1px rgba(216,210,192,0.05), 0 2px 12px rgba(0,0,0,0.6)
--shadow-2  0 0 0 1px rgba(216,210,192,0.06), 0 12px 32px rgba(0,0,0,0.7)
--shadow-3  0 0 0 1px rgba(216,210,192,0.09), 0 32px 80px rgba(0,0,0,0.85)
```

### Typography
- **Spectral** (Google) — display, headings, prices/numbers, italic asides. Weights 300/400/500/600 + italics. Class helpers: `.serif`, `.serif-tight` (headings, 500, tighter tracking), `.serif-num` (tabular lining numerals), `.readout` (big tabular price numbers).
- **Geist** (Google) — all UI/body text, buttons, labels. Weights 300–700.
- **Geist Mono** (Google) — small data/labels, timestamps, status codes, kbd hints.
- Base body: 13.5px / 1.6, letter-spacing -0.005em. Labels use `.smallcap` (uppercase, 0.16em tracking) or `.smallcap-low` (sentence-case muted).

### Radii / spacing
- Radii: buttons = 999px (pill); cards = 16px; inputs/inner = 8–12px; chips = 4px.
- Page gutter: 48px horizontal on content; cards padded 24–40px. Section gaps 16–32px.
- Motion easing: `cubic-bezier(0.22, 1, 0.36, 1)` (most), `cubic-bezier(0.16, 1, 0.3, 1)` (slow/entrance). Durations 160–560ms.

### Charts
- Area chart: 1.4px stroke in the up/down color, soft gradient fill (accent→transparent), dashed y-gridlines at `rgba(216,210,192,0.07)`, Spectral axis labels in `--mute`, a vertical guide + dot at the latest point. Sparklines: 1.25px stroke, end dot, no axes.

## Assets
- **No image assets.** The logo is an inline SVG "vault crest" (hexagon + serif Q, platinum gradient) in `components.jsx` → `Mark()`. All other icons are inline stroke SVGs in the `Icon()` component (1.4px stroke). Recreate with your icon set (Lucide is the closest match) or port the SVGs directly.
- Fonts load from Google Fonts (`<link>` in the HTML head).

## Files
- `Quantor.html` — entry; loads fonts, defines ALL CSS tokens + utility classes in one `<style>` block (this is your styling source of truth), mounts React, loads the scripts below.
- `src/data.jsx` — mock `STOCKS` array, sectors, news, and the `AI_REPORT` thesis object. **Replace with real data.**
- `src/components.jsx` — shared: formatters, `Icon`, `Mark` (logo), `Sparkline`, `AreaChart`, `Delta`, `Bar`, `Sidebar`, `PageHeader`, `CommandPalette`.
- `src/page-dashboard.jsx` — Markets.
- `src/page-screener.jsx` — Screener (filters, sortable table).
- `src/page-stock.jsx` — Stock detail.
- `src/page-ai.jsx` — AI Analyst.
- `src/app.jsx` — routing + shell.

> Tip: the entire visual system (colors, fonts, component classes like `.card`, `.btn`, `.seg`, `.chip`, `.hud`, `.input`, `.nav-item`) lives in the single `<style>` block in `Quantor.html`. Read that first — it's the design system.
