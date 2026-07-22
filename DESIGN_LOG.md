# QuantorSignal Design Log

Running record of every color scheme and major UI change, so we can cycle
between schemes without losing history. When trying a new scheme: add it as a
new version section (don't delete old ones), implement it by changing the
primitive values at the top of `frontend/src/app/globals.css` (the semantic
variable names stay stable), and note the date + verdict.

---

## Color research (what the evidence says)

- **Blue-cyan is the most-preferred hue region, cross-culturally.** Palmer &
  Schloss's ecological valence theory (PNAS, 2010): people prefer colors of
  things they like — clear sky, clean water — which lands on blue/cyan; the
  least-liked region is dark yellow/olive/brown.
- **Blue is the most trusted color for financial sites; green is second** (Ha
  2009; Cyr et al. "Colour appeal in website design"; NN/g). Cooler hues and
  *lower saturation* both read as more trustworthy.
- **Pleasure rises with brightness more than saturation** (Valdez & Mehrabian,
  "Effects of Color on Emotions"). A palette can be muted and still feel good
  if its accent is *luminous*; a palette that is muted AND dim feels murky —
  exactly the v6 failure mode.
- **Red causes measurable avoidance behavior in investors** (Bazley, Cronqvist
  & Mormann, "Visual Finance: The Pervasive Effects of Red on Investor
  Behavior", *Management Science*). Losses shown in red reduce risk-taking and
  return expectations; the effect vanishes for colorblind users and in China.
  → Red/rust is reserved for negative deltas ONLY. Never for brand, CTAs, or
  emphasis.
- Sources: [Palmer & Schloss PNAS](https://www.pnas.org/doi/10.1073/pnas.0906172107) ·
  [Color as trustworthiness cue](https://www.researchgate.net/publication/233605112_Color_Matters_Color_as_Trustworthiness_Cue_in_Web_Sites) ·
  [Bazley et al.](https://pubsonline.informs.org/doi/10.1287/mnsc.2020.3747) ·
  [Valdez & Mehrabian](https://www.semanticscholar.org/paper/Effects-of-color-on-emotions.-Valdez-Mehrabian/d15bdf485f3a64abb59e4d0d1d1b18a9fc652bf9)

## The "AI-generated look" blacklist (lean away from all of these)

Documented tells of AI-generated sites (see
["Why Your AI Keeps Building the Same Purple Gradient Website"](https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website) and the
["AI purple problem"](https://dev.to/jaainil/ai-purple-problem-make-your-ui-unmistakable-3ono)):

1. **Purple/indigo/violet accents and gradients** — the single biggest tell
   (our v5 was exactly this; permanently banned).
2. Inter font everywhere (we use Spectral serif + Geist — keep).
3. Three identical icon-boxes in a grid on the landing page.
4. Gradient text in heroes; glassmorphism cards.
5. Timid, low-chroma "safe" palettes with no committed accent (v6's failure).
6. Emoji in headings; "Unlock the power of…" copy; exclamation marks.

What keeps us un-AI-looking: the serif display face, the HUD corner-bracket
panels, mono uppercase kickers, one committed non-purple accent, factual copy.

---

## Scheme history

### v1 — shadcn defaults (initial build)
Stock `shadcn/ui` HSL tokens, light-ish greys, accent `210 40% 96%` /
`217 33% 17%`. Verdict: placeholder, never a real identity.

### v2 — "Retro terminal" pure orange (`aece72e`)
Pure orange `#ff8800` (33 100% 50%) on black, terminal aesthetic.
Verdict: distinctive but harsh; orange at full saturation reads alarm/caution
(and per the research, warm + saturated = less trust).

### v3 — TradingView blue (`80af9ea`)
Bright blue `210 100% 56%` (~`#1e9bff`), clean fintech look.
Verdict: trustworthy but generic — indistinguishable from every broker.

### v4 — Gold/mustard (`44 64% 52%`)
Warm gold accent. Verdict: dark-yellow territory is literally the
least-preferred hue region in the preference studies. Dropped.

### v5 — Indigo on ink (`#5b5bd6` on `#08080e`)
Violet-indigo accent, `#4ade80`/`#f87171` Tailwind pos/neg.
Verdict: **the AI-purple look.** Permanently banned. (A leftover
`rgba(91,91,214,…)` glow was still in the stock page until v7 removed it.)

### v6 — "Obsidian luxe" parchment (`2a2c0b6`, the GPT one-shot)
Warm parchment text `#d8d2c0` on near-black `#050405`; accent `--forest`
`#aeb9c7` — a nearly achromatic silver-blue; sapphire `#5b9cd6` secondary;
heavy vignette. Typography/HUD language introduced here was good and survives.
Verdict: elegant but murky — sepia cast, no focal color, nothing to like on
open. Per Valdez & Mehrabian: muted + dim = low pleasure. Kept: fonts, layout
language, corner brackets. Replaced: every color value.

### v7 — "Harbor" (CURRENT, July 2026)
**Idea:** petrol cyan — the midpoint of blue (trust #1) and green (trust #2 /
money) — on a cool blue-black. The only hue family untried in v1–v6, luminous
enough to give the eye an anchor, and nowhere near AI-purple.

| Role | Token(s) | Value |
|---|---|---|
| Base background | `--bone` / `--bg-base` | `#070b0c` |
| Deep inset | `--bone-deep`, `--ivory` | `#040709`, `#0b1113` |
| Surfaces 1/2/3 | `--surface`, `--surface-2`, `-3` | `#0e1416`, `#141c1f`, `#1a2427` |
| Primary text ("chalk") | `--ink` | `#dde4e1` |
| Secondary / muted text | `--ink-2`, `--mute` | `#a3aeaa`, `#74807c` |
| **Accent (petrol)** | `--forest`, `--accent` | **`#31a9c4`**, hover `#55c0d6` |
| Status/live (ice) | `--sapphire` | `#45b5d0` |
| Positive | `--up`, `--positive` | `#5ec973` |
| Negative (rust, losses only) | `--dn`, `--negative` | `#c14f36` |
| Warning | `--amber` | `#dfa042` |

Validated with the dataviz palette validator on surface `#0e1416`:
accent↔positive ΔE 17.0 normal / 16.4 CVD (targets 15 / 8), all colors ≥3:1
contrast. Vignette softened (0.5 → 0.32) to kill the v6 murk. Note: the
`--forest`/`--ink`/`--bone` names are legacy from v6 and now describe petrol/
chalk/blue-black — kept so component classes didn't need a mass rename.

Verdict: _pending — live on main since 2026-07-21._

---

## UI change log

### Pre-July-2026 layout (for the record)
Fixed 248px left sidebar with a flat, ungrouped link list (mobile menu was
missing several pages); homepage was two stacked heroes plus a uniform
three-card feature grid; "luxury market intelligence" copy.

### July 2026 — navigation + homepage overhaul (on main)
- Sidebar nav grouped into labeled sections (Tools / Account on main; a
  Markets group with Scanners, Earnings, Insiders, Macro pages exists on
  `feat/wave1-release` and lights up when that ships). Full mobile parity.
- Footer: flat row → columns + legal row.
- Homepage: product-ladder flow — factual hero + live spotlight → live market
  movers → free-tools index → paid ladder (Pro today; Trader/Elite teased as
  coming soon on main, purchasable on the release branch).
- Login/register honor a sanitized `?redirect=` param (open-redirect safe).
- De-AI copy pass: hero, pricing, metadata rewritten to factual feature lists;
  no gradient text, no emoji headings anywhere.
- Brand mark + all hardcoded component colors resynced to the active palette
  (v5 indigo remnant removed from the stock page).

### Pending on `feat/wave1-release` (not on main yet)
Five new free pages (/markets /earnings /insiders /macro /compare), email
preferences UI, Trader/Elite checkout, and the email/AI backend. Its Header/
Footer/homepage supersets main's versions — when merging, take the branch
versions and re-strip nothing.
