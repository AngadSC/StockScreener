# Implementation Checklist — QuantorSignal

A suggested order of work for porting the design in this folder into a real codebase.
Pair this with `README.md` (full spec + design tokens) and the PNGs in `screens/`.

## 0. Project setup
- [ ] Confirm framework. Prototype is React; **React + TypeScript + Vite** (or Next.js) is the path of least resistance.
- [ ] Add the three Google fonts: **Spectral**, **Geist**, **Geist Mono** (see `<link>` in `Quantor.html`).
- [ ] Pick a styling approach (CSS variables + CSS modules, or Tailwind with the tokens mapped into the theme).

## 1. Design system first (do this before any screen)
- [ ] Port every CSS custom property from the `<style>` block in `Quantor.html` (colors, shadows, easing). This is the source of truth.
- [ ] Build base primitives as components: `Button` (variants: primary / ghost / quiet / bare; sizes sm/xs), `Chip`/`Status`, `Card`, `Segmented` control, `Input` + range slider, `Checkbox`, `Toggle`, `Bar` (progress).
- [ ] Port the typographic helpers (`serif`, `serif-tight`, `serif-num`, `readout`, `smallcap`, `smallcap-low`) as classes or a `<Text>` component.
- [ ] Port `Icon` (inline stroke SVGs) — or swap to **Lucide** (closest match, 1.4px stroke) and map names.
- [ ] Port `Mark` (the SVG vault-crest logo) verbatim.

## 2. Data layer
- [ ] Define the row type from `data.jsx`: `ticker, name, sector, industry, price, chg, mcap, vol, pe, roe, divy, beta, rev_g, w52l, w52h` + a price series.
- [ ] Wire a real quotes/fundamentals API; keep `data.jsx` as a fixture for tests/Storybook.
- [ ] Implement `Sparkline` + `AreaChart` against your real series (or swap for a charting lib — visvalingam/lightweight-charts/visx — but match the styling in the README).

## 3. App shell + routing
- [ ] Sidebar (logo, search button, nav, Pro card, user row) with active-state indicator.
- [ ] Routes: `/` Markets, `/screener`, `/stocks/:ticker`, `/ai`, plus `/watchlist` + `/backtester` stubs.
- [ ] Command palette (⌘K / Ctrl-K global listener, Esc to close, routes to stock on pick).
- [ ] **Page entrance**: transform-only slide-up — never gate visibility on opacity (see README note).

## 4. Screens (in this order)
- [ ] **Markets** (`screens/1-markets.png`) — header, index row, featured+watchlist, movers, sector flow, brief + wire.
- [ ] **Screener** (`screens/2-screener.png`) — filter rail (live `useMemo`), sortable + selectable table, saved-view chips, pagination.
- [ ] **Stock detail** (`screens/4-stock-detail.png`) — hero, 52w bar, stat strip, tabs, chart + research brief + factor scores, signal snapshot + news + fundamentals + peers. **No trade ticket.**
- [ ] **AI Analyst** (`screens/3-ai-analyst.png`) — ask bar, conviction queue (selectable), generated brief panel, recent briefs.

## 5. Polish & QA
- [ ] Hover states on cards (HUD brackets), rows, buttons, chips.
- [ ] Keyboard: ⌘K palette, Esc, focus rings (`--forest-soft`), tab order.
- [ ] Empty states (screener "no matches") and loading skeletons for async data.
- [ ] Responsive: sidebar collapse + grid reflow below ~1100px (prototype hides some labels via `.hide-md`).
- [ ] Number formatting: tabular figures everywhere (`fmtPrice/fmtPct/fmtMcap/fmtVol` in `components.jsx`).
- [ ] Accessibility: color is not the only signal for up/down (keep the ↑/↓ glyphs), aria labels on icon-only buttons.

## Gotchas carried over from the prototype
- The visual system is **one big `<style>` block** in `Quantor.html` — read it before splitting files.
- Up = `--up #5ba879`, Down = `--dn #c25a3a` (warm, not pure red). Primary accent is **platinum** `--forest #aeb9c7` (the var is historically named "forest" — it is NOT green). Sapphire is the technical/live accent. Amber is alerts only.
- All data is mock; sparkline values are generated, not real.
