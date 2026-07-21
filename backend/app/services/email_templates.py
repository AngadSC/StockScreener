"""Dependency-free HTML email templates for QuantorSignal.

Everything here is plain f-strings with inline CSS so the emails render in
Gmail / Outlook / Apple Mail without an external template engine or CSS files.
Later features (daily market brief, watchlist AI digest, weekly recap) compose
their bodies from the small block helpers below and wrap them with
``render_base``.

Design: clean minimal fintech look — dark text on white, a single blue accent,
a 600px max-width centered card, and green/red coloring for changes.
"""

from __future__ import annotations

import html
from typing import Iterable, Optional

# ----------------------------------------------------------------------------
# Palette / tokens
# ----------------------------------------------------------------------------
BRAND_NAME = "QuantorSignal"
ACCENT = "#2563EB"          # primary blue accent
INK = "#0f172a"             # near-black body text (slate-900)
MUTED = "#64748b"           # secondary text (slate-500)
BORDER = "#e2e8f0"          # hairline borders (slate-200)
CANVAS = "#f1f5f9"          # outer page background (slate-100)
CARD = "#ffffff"
POSITIVE = "#16a34a"        # green
NEGATIVE = "#dc2626"        # red
FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, "
        "Arial, sans-serif")


def _esc(text: object) -> str:
    """Escape text destined for HTML *content* (not attributes)."""
    return html.escape("" if text is None else str(text))


def _esc_attr(value: object) -> str:
    """Escape a value destined for an HTML attribute (e.g. href)."""
    return html.escape("" if value is None else str(value), quote=True)


# ----------------------------------------------------------------------------
# Block helpers — later emails compose these into a body_html string
# ----------------------------------------------------------------------------
def heading(text: str) -> str:
    """Section heading."""
    return (
        f'<h2 style="margin:24px 0 8px;font-family:{FONT};font-size:18px;'
        f'line-height:1.3;font-weight:700;color:{INK};">{_esc(text)}</h2>'
    )


def paragraph(text: str) -> str:
    """Body paragraph. ``text`` is treated as plain text and escaped."""
    return (
        f'<p style="margin:0 0 14px;font-family:{FONT};font-size:15px;'
        f'line-height:1.55;color:{INK};">{_esc(text)}</p>'
    )


def _change_color(change_pct: Optional[float]) -> str:
    if change_pct is None:
        return MUTED
    return POSITIVE if change_pct >= 0 else NEGATIVE


def _format_change(change_pct: Optional[float]) -> str:
    if change_pct is None:
        return ""
    arrow = "▲" if change_pct >= 0 else "▼"  # ▲ / ▼
    return f"{arrow} {change_pct:+.2f}%"


def stat_row(label: str, value: str, change_pct: Optional[float] = None) -> str:
    """A single label / value row with optional green/red % change."""
    change_html = ""
    if change_pct is not None:
        change_html = (
            f'<span style="font-family:{FONT};font-size:13px;font-weight:600;'
            f'color:{_change_color(change_pct)};margin-left:8px;">'
            f'{_esc(_format_change(change_pct))}</span>'
        )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;">'
        f'<tr>'
        f'<td style="padding:8px 0;border-bottom:1px solid {BORDER};'
        f'font-family:{FONT};font-size:14px;color:{MUTED};">{_esc(label)}</td>'
        f'<td align="right" style="padding:8px 0;border-bottom:1px solid {BORDER};'
        f'font-family:{FONT};font-size:14px;font-weight:600;color:{INK};">'
        f'{_esc(value)}{change_html}</td>'
        f'</tr></table>'
    )


def ticker_card(symbol: str, name: str, lines: Iterable[str]) -> str:
    """A bordered card for one ticker: symbol + name header and a list of lines.

    ``lines`` items are plain text (escaped). Compose them from short facts,
    e.g. ["Price $182.40 (+1.2%)", "RSI 61 · above 50DMA"].
    """
    line_items = "".join(
        f'<div style="font-family:{FONT};font-size:13px;line-height:1.5;'
        f'color:{MUTED};margin-top:4px;">{_esc(line)}</div>'
        for line in lines
    )
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:separate;border:1px solid {BORDER};'
        f'border-radius:10px;margin:0 0 12px;">'
        f'<tr><td style="padding:14px 16px;">'
        f'<div style="font-family:{FONT};">'
        f'<span style="font-size:16px;font-weight:700;color:{INK};">{_esc(symbol)}</span>'
        f'<span style="font-size:13px;color:{MUTED};margin-left:8px;">{_esc(name)}</span>'
        f'</div>'
        f'{line_items}'
        f'</td></tr></table>'
    )


def cta_button(text: str, url: str) -> str:
    """A filled accent call-to-action button."""
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;margin:20px 0;"><tr>'
        f'<td align="center" style="border-radius:8px;background:{ACCENT};">'
        f'<a href="{_esc_attr(url)}" target="_blank" '
        f'style="display:inline-block;padding:12px 24px;font-family:{FONT};'
        f'font-size:15px;font-weight:600;color:#ffffff;text-decoration:none;'
        f'border-radius:8px;">{_esc(text)}</a>'
        f'</td></tr></table>'
    )


def divider() -> str:
    """A thin horizontal rule."""
    return f'<hr style="border:none;border-top:1px solid {BORDER};margin:20px 0;"/>'


# ----------------------------------------------------------------------------
# Base wrapper
# ----------------------------------------------------------------------------
def render_base(
    title: str,
    preheader: str,
    body_html: str,
    unsubscribe_url: str,
) -> str:
    """Wrap a composed ``body_html`` in the branded responsive shell.

    Args:
        title: Shown as the H1 wordmark subtitle / used by clients.
        preheader: Hidden preview text shown in the inbox list.
        body_html: Pre-rendered HTML (compose with the block helpers above).
        unsubscribe_url: One-click unsubscribe link shown in the footer.
    """
    year = 2026
    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="x-apple-disable-message-reformatting"/>
<meta http-equiv="X-UA-Compatible" content="IE=edge"/>
<title>{_esc(title)}</title>
</head>
<body style="margin:0;padding:0;background:{CANVAS};-webkit-text-size-adjust:100%;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:{CANVAS};">{_esc(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CANVAS};border-collapse:collapse;">
<tr>
<td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:100%;border-collapse:collapse;">
<!-- Header / wordmark -->
<tr>
<td style="padding:8px 4px 16px;">
<span style="font-family:{FONT};font-size:20px;font-weight:800;letter-spacing:-0.2px;color:{INK};">Quantor<span style="color:{ACCENT};">Signal</span></span>
</td>
</tr>
<!-- Card -->
<tr>
<td style="background:{CARD};border:1px solid {BORDER};border-radius:14px;padding:28px 28px 24px;">
<h1 style="margin:0 0 16px;font-family:{FONT};font-size:22px;line-height:1.25;font-weight:700;color:{INK};">{_esc(title)}</h1>
{body_html}
</td>
</tr>
<!-- Footer -->
<tr>
<td style="padding:20px 12px 8px;">
<p style="margin:0 0 6px;font-family:{FONT};font-size:12px;line-height:1.5;color:{MUTED};">
You are receiving this email because you have a {BRAND_NAME} account.
</p>
<p style="margin:0 0 6px;font-family:{FONT};font-size:12px;line-height:1.5;color:{MUTED};">
<a href="{_esc_attr(unsubscribe_url)}" target="_blank" style="color:{MUTED};text-decoration:underline;">Unsubscribe</a>
from this type of email at any time.
</p>
<p style="margin:0;font-family:{FONT};font-size:12px;line-height:1.5;color:{MUTED};">
&copy; {year} {BRAND_NAME}. Informational only &mdash; not investment advice.
</p>
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>"""


def render_notice_page(title: str, message: str) -> str:
    """Small self-contained HTML page for browser responses (e.g. unsubscribe).

    Intentionally standalone (no external assets) so it renders anywhere.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{_esc(title)} &middot; {BRAND_NAME}</title>
</head>
<body style="margin:0;padding:0;background:{CANVAS};font-family:{FONT};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;min-height:100vh;">
<tr><td align="center" valign="middle" style="padding:40px 16px;">
<table role="presentation" width="480" cellpadding="0" cellspacing="0" style="width:480px;max-width:100%;background:{CARD};border:1px solid {BORDER};border-radius:14px;">
<tr><td style="padding:32px 28px;text-align:center;">
<div style="font-size:20px;font-weight:800;letter-spacing:-0.2px;color:{INK};margin-bottom:18px;">Quantor<span style="color:{ACCENT};">Signal</span></div>
<h1 style="margin:0 0 10px;font-size:20px;font-weight:700;color:{INK};">{_esc(title)}</h1>
<p style="margin:0;font-size:15px;line-height:1.55;color:{MUTED};">{_esc(message)}</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
