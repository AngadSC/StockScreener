"""
SEC EDGAR client + Form 4 (insider activity) ingestion.

EDGAR is a free, no-API-key data source. The only hard requirement is
*politeness*:
  - every request MUST send a descriptive ``User-Agent`` (we send
    ``settings.EDGAR_USER_AGENT``),
  - requests are throttled to stay well under EDGAR's fair-access ceiling
    (~10 req/sec) -- we target ~4.5 req/sec via a simple sleep,
  - 403 / 429 responses are retried with exponential backoff.

Ingestion strategy
------------------
1. Load the ticker -> CIK map from company_tickers.json (cached for a day).
2. For a given date, download the daily index (``form.YYYYMMDD.idx``) and keep
   the rows whose form type is exactly ``4`` and whose CIK maps to a ticker in
   *our* ``tickers`` table (i.e. the issuer is a company we track).
3. For each such filing, download the full submission text, extract the
   ``<ownershipDocument>`` XML and parse the non-derivative transactions,
   keeping only purchases (``P``) and sales (``S``).
4. Upsert each transaction, deduped on ``(accession_no, txn_index)`` so the
   whole pipeline is idempotent and safe to re-run.

The pure-parsing function :func:`parse_form4_xml` performs no network I/O and is
the unit under test in ``backend/tests/test_edgar_parser.py``.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import InsiderTransaction, Ticker
from app.services.cache import cache_service
from app.utils.market_calendar import today_et

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEC_BASE = "https://www.sec.gov"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
CIK_MAP_CACHE_KEY = "edgar:cik_map"

# Transaction codes we care about: open-market/private purchase and sale.
KEEP_CODES = {"P", "S"}

# In-memory CIK map cache so we do not hit Redis (or the network) on every call.
_CIK_MAP_MEM: Optional[Dict[str, int]] = None
_CIK_MAP_MEM_AT: float = 0.0

# regex over daily index rows -- the 8-digit (YYYYMMDD) date is anchored so the
# (possibly space/number-containing) issuer name is captured unambiguously.
# Example row:
#   4                ABM INDUSTRIES INC /DE/    771497   20260717   edgar/data/771497/0001225208-26-006655.txt
_INDEX_ROW_RE = re.compile(
    r"^(?P<form>\S+)\s+(?P<company>.+?)\s+(?P<cik>\d+)\s+"
    r"(?P<date>\d{8})\s+(?P<file>\S+)\s*$"
)

_OWNERSHIP_RE = re.compile(
    r"<ownershipDocument>.*?</ownershipDocument>", re.DOTALL | re.IGNORECASE
)


# ---------------------------------------------------------------------------
# HTTP client (throttled + polite)
# ---------------------------------------------------------------------------


class EdgarClient:
    """Thin, throttled wrapper around ``httpx.Client`` for sec.gov requests."""

    def __init__(
        self,
        user_agent: Optional[str] = None,
        min_interval: Optional[float] = None,
        timeout: float = 30.0,
    ):
        self.user_agent = user_agent or settings.EDGAR_USER_AGENT
        self.min_interval = (
            min_interval
            if min_interval is not None
            else settings.EDGAR_MIN_REQUEST_INTERVAL
        )
        self._client = httpx.Client(
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov",
            },
            timeout=timeout,
            follow_redirects=True,
        )
        self._last_request_at = 0.0

    # -- context manager sugar --------------------------------------------
    def __enter__(self) -> "EdgarClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # -- throttling --------------------------------------------------------
    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = self.min_interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def get(self, url: str, max_retries: int = 4) -> Optional[httpx.Response]:
        """
        GET ``url`` with throttling + backoff.

        Returns the response on success, or ``None`` for a *missing resource* --
        a 404, or a 403 ``AccessDenied`` (EDGAR's index/archive files live on S3,
        where a non-existent key -- e.g. a weekend/holiday daily-index file --
        returns 403 AccessDenied rather than 404).

        Genuine rate-limit / transient responses (429, a non-AccessDenied 403,
        5xx) are retried with exponential backoff. If they persist past
        ``max_retries`` the method logs and returns ``None`` rather than raising,
        so a single bad request never crashes the whole ingest job.
        """
        backoff = 1.0
        for attempt in range(max_retries):
            self._throttle()
            try:
                resp = self._client.get(url)
            except httpx.HTTPError as exc:  # network hiccup -> retry
                print(
                    f"[edgar] network error for {url}: {exc}; "
                    f"retry {attempt + 1}/{max_retries}"
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            # Missing resource (not an error we should retry or raise on).
            if resp.status_code == 404:
                return None
            if resp.status_code == 403 and "AccessDenied" in resp.text:
                return None

            # Rate-limit / transient server error -> back off and retry.
            if resp.status_code in (403, 429, 500, 502, 503, 504):
                retry_after = resp.headers.get("Retry-After")
                try:
                    sleep_for = float(retry_after) if retry_after else backoff
                except ValueError:
                    sleep_for = backoff
                print(
                    f"[edgar] {resp.status_code} (rate-limit?) for {url}; "
                    f"retry {attempt + 1}/{max_retries} in {sleep_for:.1f}s"
                )
                time.sleep(sleep_for)
                backoff *= 2
                continue

            resp.raise_for_status()
            return resp

        print(f"[edgar] giving up on {url} after {max_retries} attempts")
        return None


# ---------------------------------------------------------------------------
# Ticker -> CIK map
# ---------------------------------------------------------------------------


def get_cik_map(client: EdgarClient, force_refresh: bool = False) -> Dict[str, int]:
    """
    Return ``{TICKER: cik_int}`` from company_tickers.json.

    Cached in-process and in Redis for ``settings.EDGAR_CIK_MAP_TTL`` seconds.
    """
    global _CIK_MAP_MEM, _CIK_MAP_MEM_AT

    now = time.monotonic()
    if (
        not force_refresh
        and _CIK_MAP_MEM is not None
        and (now - _CIK_MAP_MEM_AT) < settings.EDGAR_CIK_MAP_TTL
    ):
        return _CIK_MAP_MEM

    if not force_refresh:
        cached = cache_service.get(CIK_MAP_CACHE_KEY)
        if cached:
            mapping = {k: int(v) for k, v in cached.items()}
            _CIK_MAP_MEM, _CIK_MAP_MEM_AT = mapping, now
            return mapping

    resp = client.get(COMPANY_TICKERS_URL)
    if resp is None:
        raise RuntimeError("[edgar] company_tickers.json returned 404")

    raw = resp.json()
    mapping: Dict[str, int] = {}
    # company_tickers.json is keyed by row index: {"0": {"cik_str":.., "ticker":..}}
    for row in raw.values():
        ticker = str(row.get("ticker", "")).upper().strip()
        cik = row.get("cik_str")
        if ticker and cik is not None:
            mapping[ticker] = int(cik)

    cache_service.set(CIK_MAP_CACHE_KEY, mapping, ttl=settings.EDGAR_CIK_MAP_TTL)
    _CIK_MAP_MEM, _CIK_MAP_MEM_AT = mapping, now
    return mapping


# ---------------------------------------------------------------------------
# Daily index
# ---------------------------------------------------------------------------


@dataclass
class IndexRow:
    form_type: str
    company: str
    cik: int
    filed_date: str
    file_name: str

    @property
    def accession_no(self) -> str:
        # file_name -> edgar/data/<cik>/<accession>.txt
        base = self.file_name.rsplit("/", 1)[-1]
        return base[:-4] if base.endswith(".txt") else base

    @property
    def submission_url(self) -> str:
        return f"{SEC_BASE}/Archives/{self.file_name}"


def daily_index_url(target_date: date) -> str:
    quarter = (target_date.month - 1) // 3 + 1
    return (
        f"{SEC_BASE}/Archives/edgar/daily-index/{target_date.year}/"
        f"QTR{quarter}/form.{target_date.strftime('%Y%m%d')}.idx"
    )


def parse_daily_index(text: str) -> List[IndexRow]:
    """Parse a ``form.YYYYMMDD.idx`` file into rows. Header lines are skipped."""
    rows: List[IndexRow] = []
    for line in text.splitlines():
        m = _INDEX_ROW_RE.match(line)
        if not m:
            continue
        try:
            cik = int(m.group("cik"))
        except ValueError:
            continue
        rows.append(
            IndexRow(
                form_type=m.group("form").strip(),
                company=m.group("company").strip(),
                cik=cik,
                filed_date=m.group("date"),
                file_name=m.group("file").strip(),
            )
        )
    return rows


def fetch_daily_index(client: EdgarClient, target_date: date) -> List[IndexRow]:
    """Fetch + parse the daily form index. Returns [] if the index is absent."""
    resp = client.get(daily_index_url(target_date))
    if resp is None:
        return []
    return parse_daily_index(resp.text)


# ---------------------------------------------------------------------------
# Ownership document (Form 4 XML)
# ---------------------------------------------------------------------------


def extract_ownership_xml(submission_text: str) -> Optional[str]:
    """Pull the ``<ownershipDocument>...</ownershipDocument>`` block out of a
    full submission ``.txt`` file (SGML wrapper around the XML)."""
    m = _OWNERSHIP_RE.search(submission_text)
    return m.group(0) if m else None


def fetch_ownership_xml(client: EdgarClient, row: IndexRow) -> Optional[str]:
    resp = client.get(row.submission_url)
    if resp is None:
        return None
    return extract_ownership_xml(resp.text)


# ---------------------------------------------------------------------------
# Pure parser (unit-tested, no network)
# ---------------------------------------------------------------------------


@dataclass
class ParsedTransaction:
    txn_index: int
    transaction_code: str
    transaction_date: Optional[date]
    shares: Optional[float]
    price: Optional[float]
    value: Optional[float]


@dataclass
class ParsedForm4:
    issuer_ticker: Optional[str]
    issuer_cik: Optional[str]
    issuer_name: Optional[str]
    owner_name: Optional[str]
    owner_title: Optional[str]
    is_officer: bool
    is_director: bool
    transactions: List[ParsedTransaction] = field(default_factory=list)


def _text(el: Optional[ET.Element]) -> Optional[str]:
    if el is None or el.text is None:
        return None
    stripped = el.text.strip()
    return stripped or None


def _child_text(parent: Optional[ET.Element], tag: str) -> Optional[str]:
    """Return a child's text, transparently unwrapping a ``<value>`` element."""
    if parent is None:
        return None
    el = parent.find(tag)
    if el is None:
        return None
    value_el = el.find("value")
    return _text(value_el) if value_el is not None else _text(el)


def _to_bool(raw: Optional[str]) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "y", "yes"}


def _to_float(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return None


def _to_date(raw: Optional[str]) -> Optional[date]:
    """Parse a date from either ``YYYY-MM-DD`` (Form 4 XML) or ``YYYYMMDD``
    (daily index) representations."""
    if not raw:
        return None
    raw = raw.strip()
    for fmt, length in (("%Y-%m-%d", 10), ("%Y%m%d", 8)):
        try:
            return datetime.strptime(raw[:length], fmt).date()
        except ValueError:
            continue
    return None


def parse_form4_xml(xml_string: str) -> ParsedForm4:
    """
    Parse a Form 4 ``ownershipDocument`` XML string.

    Only non-derivative transactions with code ``P`` (purchase) or ``S`` (sale)
    are returned. Derivative transactions are ignored. ``txn_index`` is the
    0-based position of the transaction among ALL ``nonDerivativeTransaction``
    elements, so it is stable across re-parses (idempotent ingestion).
    """
    root = ET.fromstring(xml_string)

    issuer = root.find("issuer")
    issuer_ticker = _child_text(issuer, "issuerTradingSymbol")
    if issuer_ticker:
        issuer_ticker = issuer_ticker.upper().strip()
    issuer_cik = _child_text(issuer, "issuerCik")
    issuer_name = _child_text(issuer, "issuerName")

    # Use the first reporting owner (Form 4 almost always has exactly one).
    owner = root.find("reportingOwner")
    owner_name = None
    owner_title = None
    is_officer = False
    is_director = False
    if owner is not None:
        owner_id = owner.find("reportingOwnerId")
        owner_name = _child_text(owner_id, "rptOwnerName")
        rel = owner.find("reportingOwnerRelationship")
        if rel is not None:
            is_officer = _to_bool(_child_text(rel, "isOfficer"))
            is_director = _to_bool(_child_text(rel, "isDirector"))
            owner_title = _child_text(rel, "officerTitle")

    transactions: List[ParsedTransaction] = []
    non_deriv = root.find("nonDerivativeTable")
    if non_deriv is not None:
        for idx, txn in enumerate(non_deriv.findall("nonDerivativeTransaction")):
            coding = txn.find("transactionCoding")
            code = _child_text(coding, "transactionCode")
            if code is None:
                continue
            code = code.strip().upper()
            if code not in KEEP_CODES:
                continue

            amounts = txn.find("transactionAmounts")
            shares = _to_float(_child_text(amounts, "transactionShares"))
            price = _to_float(_child_text(amounts, "transactionPricePerShare"))
            value = (
                round(shares * price, 2)
                if shares is not None and price is not None
                else None
            )
            transactions.append(
                ParsedTransaction(
                    txn_index=idx,
                    transaction_code=code,
                    transaction_date=_to_date(_child_text(txn, "transactionDate")),
                    shares=shares,
                    price=price,
                    value=value,
                )
            )

    return ParsedForm4(
        issuer_ticker=issuer_ticker,
        issuer_cik=issuer_cik,
        issuer_name=issuer_name,
        owner_name=owner_name,
        owner_title=owner_title,
        is_officer=is_officer,
        is_director=is_director,
        transactions=transactions,
    )


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def _our_symbol_to_id(db: Session) -> Dict[str, int]:
    return {sym.upper(): tid for sym, tid in db.query(Ticker.symbol, Ticker.id).all()}


def sync_form4_for_date(
    target_date: date,
    db: Session,
    client: Optional[EdgarClient] = None,
) -> Dict[str, int]:
    """
    Ingest all Form 4 purchases/sales filed on ``target_date`` for tickers we
    track. Idempotent -- safe to re-run for the same date.

    Returns a stats dict.
    """
    owns_client = client is None
    client = client or EdgarClient()
    stats = {
        "index_rows": 0,
        "form4_rows": 0,
        "matched_filings": 0,
        "transactions_inserted": 0,
        "filings_failed": 0,
    }

    try:
        symbol_to_id = _our_symbol_to_id(db)
        if not symbol_to_id:
            print("[edgar] no tickers in DB; nothing to sync")
            return stats

        cik_map = get_cik_map(client)  # TICKER -> cik
        # CIK -> ticker, but only for tickers we actually track.
        our_cik_to_symbol: Dict[int, str] = {
            cik: sym for sym, cik in cik_map.items() if sym in symbol_to_id
        }

        rows = fetch_daily_index(client, target_date)
        stats["index_rows"] = len(rows)
        if not rows:
            print(f"[edgar] no daily index for {target_date} (weekend/holiday?)")
            return stats

        # form 4 filings whose issuer CIK is one we track (dedupe by accession)
        seen_accessions: set = set()
        candidates: List[IndexRow] = []
        for row in rows:
            if row.form_type != "4":
                continue
            stats["form4_rows"] += 1
            if row.cik not in our_cik_to_symbol:
                continue
            if row.accession_no in seen_accessions:
                continue
            seen_accessions.add(row.accession_no)
            candidates.append(row)

        for row in candidates:
            try:
                inserted = _ingest_filing(
                    client, db, row, target_date, symbol_to_id, our_cik_to_symbol
                )
                if inserted > 0:
                    stats["matched_filings"] += 1
                    stats["transactions_inserted"] += inserted
            except Exception as exc:  # never let one bad filing kill the job
                stats["filings_failed"] += 1
                print(f"[edgar] failed filing {row.accession_no}: {exc}")

        if stats["transactions_inserted"] > 0:
            cache_service.clear_pattern("insider:*")

        print(
            f"[edgar] {target_date}: {stats['form4_rows']} form-4 rows, "
            f"{len(candidates)} tracked filings, "
            f"{stats['transactions_inserted']} txns inserted, "
            f"{stats['filings_failed']} failed"
        )
        return stats
    finally:
        if owns_client:
            client.close()


def _ingest_filing(
    client: EdgarClient,
    db: Session,
    row: IndexRow,
    filed_date: date,
    symbol_to_id: Dict[str, int],
    cik_to_symbol: Dict[int, str],
) -> int:
    """Fetch, parse and upsert one filing. Returns number of rows inserted."""
    xml_string = fetch_ownership_xml(client, row)
    if not xml_string:
        return 0

    parsed = parse_form4_xml(xml_string)
    if not parsed.transactions:
        return 0  # no non-derivative P/S transactions -> skip

    # Prefer the ticker from the XML; fall back to the CIK->symbol mapping.
    symbol = (parsed.issuer_ticker or cik_to_symbol.get(row.cik) or "").upper()
    ticker_id = symbol_to_id.get(symbol)
    if ticker_id is None:
        ticker_id = symbol_to_id.get((cik_to_symbol.get(row.cik) or "").upper())
    if ticker_id is None:
        return 0

    filed = _to_date(row.filed_date) or filed_date
    values = []
    for txn in parsed.transactions:
        values.append(
            {
                "ticker_id": ticker_id,
                "accession_no": row.accession_no,
                "txn_index": txn.txn_index,
                "filed_date": filed,
                "transaction_date": txn.transaction_date,
                "owner_name": (parsed.owner_name or "")[:255] or None,
                "owner_title": parsed.owner_title[:255]
                if parsed.owner_title
                else None,
                "is_officer": parsed.is_officer,
                "is_director": parsed.is_director,
                "transaction_code": txn.transaction_code,
                "shares": txn.shares,
                "price": txn.price,
                "value": txn.value,
            }
        )

    stmt = pg_insert(InsiderTransaction).values(values)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["accession_no", "txn_index"]
    )
    result = db.execute(stmt)
    db.commit()
    # rowcount reflects rows actually inserted (conflicts skipped)
    return result.rowcount if result.rowcount is not None else len(values)


def backfill(
    days: int = None,
    db: Session = None,
    client: Optional[EdgarClient] = None,
) -> Dict[str, int]:
    """
    Backfill the last ``days`` calendar days of Form 4 filings.

    Non-trading days simply have no daily index and contribute nothing. A
    dedicated ``db`` session must be supplied by the caller.
    """
    if db is None:
        raise ValueError("backfill() requires a db session")
    days = days if days is not None else settings.EDGAR_BACKFILL_DAYS

    owns_client = client is None
    client = client or EdgarClient()
    totals = {
        "days_scanned": 0,
        "matched_filings": 0,
        "transactions_inserted": 0,
        "filings_failed": 0,
    }
    try:
        # ET date, not host date: backfill() is invoked from the 22:45 ET sync
        # (already the next day in UTC), and EDGAR indexes are keyed by ET day.
        today = today_et()
        for offset in range(days, -1, -1):
            day = today - timedelta(days=offset)
            stats = sync_form4_for_date(day, db, client=client)
            totals["days_scanned"] += 1
            totals["matched_filings"] += stats["matched_filings"]
            totals["transactions_inserted"] += stats["transactions_inserted"]
            totals["filings_failed"] += stats["filings_failed"]
        print(
            f"[edgar] backfill complete over {totals['days_scanned']} days: "
            f"{totals['transactions_inserted']} txns inserted"
        )
        return totals
    finally:
        if owns_client:
            client.close()
