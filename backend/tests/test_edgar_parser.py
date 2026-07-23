"""
Unit tests for the SEC EDGAR Form 4 parser (backend/app/services/edgar.py).

No network access -- every test operates on an embedded ownershipDocument XML
fixture string. Covers: a purchase (P), a sale (S), a derivative-only / no-P-S
filing (skipped), transaction-index stability when non-P/S codes are interleaved,
missing-price handling, and full-submission SGML extraction.
"""

from __future__ import annotations

import os
from datetime import date

# Provide dummy settings so importing app.config (transitively required by the
# edgar service) never fails when no .env / env vars are present.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://t:t@localhost/t")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from app.services.edgar import (  # noqa: E402
    extract_ownership_xml,
    parse_form4_xml,
)


# ---------------------------------------------------------------------------
# Fixtures (realistic Form 4 ownershipDocument XML)
# ---------------------------------------------------------------------------

BUY_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <schemaVersion>X0508</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2026-07-18</periodOfReport>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>APPLE INC</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001214128</rptOwnerCik>
            <rptOwnerName>LEVINSON ARTHUR D</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>0</isOfficer>
            <isTenPercentOwner>0</isTenPercentOwner>
            <isOther>0</isOther>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-07-18</value></transactionDate>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>P</transactionCode>
                <equitySwapInvolved>0</equitySwapInvolved>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1000</value></transactionShares>
                <transactionPricePerShare><value>210.50</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
            <ownershipNature>
                <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
            </ownershipNature>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

SELL_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0000789019</issuerCik>
        <issuerName>MICROSOFT CORP</issuerName>
        <issuerTradingSymbol>MSFT</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001234567</rptOwnerCik>
            <rptOwnerName>NADELLA SATYA</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>1</isOfficer>
            <officerTitle>Chief Executive Officer</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-07-15</value></transactionDate>
            <transactionCoding>
                <transactionCode>S</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>500</value></transactionShares>
                <transactionPricePerShare><value>195.25</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

# An option exercise + a stock award (code A). No P or S -> must yield nothing.
DERIVATIVE_ONLY_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0001045810</issuerCik>
        <issuerName>NVIDIA CORP</issuerName>
        <issuerTradingSymbol>NVDA</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerName>HUANG JEN HSUN</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>1</isOfficer>
            <officerTitle>President and CEO</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-07-10</value></transactionDate>
            <transactionCoding>
                <transactionCode>A</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>2000</value></transactionShares>
                <transactionPricePerShare><value>0</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
    <derivativeTable>
        <derivativeTransaction>
            <securityTitle><value>Employee Stock Option</value></securityTitle>
            <transactionDate><value>2026-07-10</value></transactionDate>
            <transactionCoding>
                <transactionCode>M</transactionCode>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1500</value></transactionShares>
                <transactionPricePerShare><value>25.00</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </derivativeTransaction>
    </derivativeTable>
</ownershipDocument>
"""

# Interleaved codes A, P, S -> only P (index 1) and S (index 2) are kept, with
# their ORIGINAL positions preserved.
MIXED_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0000051143</issuerCik>
        <issuerName>INTL BUSINESS MACHINES CORP</issuerName>
        <issuerTradingSymbol>IBM</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerName>DOE JANE</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>0</isDirector>
            <isOfficer>1</isOfficer>
            <officerTitle>CFO</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>100</value></transactionShares>
                <transactionPricePerShare><value>0</value></transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction>
            <transactionDate><value>2026-07-12</value></transactionDate>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>300</value></transactionShares>
                <transactionPricePerShare><value>150.00</value></transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
        <nonDerivativeTransaction>
            <transactionDate><value>2026-07-12</value></transactionDate>
            <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>200</value></transactionShares>
                <transactionPricePerShare><value>160.00</value></transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

# A purchase whose price is footnote-only (no <value>) -> price/value None.
MISSING_PRICE_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <documentType>4</documentType>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>APPLE INC</issuerName>
        <issuerTradingSymbol>AAPL</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId><rptOwnerName>SMITH JOHN</rptOwnerName></reportingOwnerId>
        <reportingOwnerRelationship><isDirector>1</isDirector><isOfficer>0</isOfficer></reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <transactionDate><value>2026-07-09</value></transactionDate>
            <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
            <transactionAmounts>
                <transactionShares><value>750</value></transactionShares>
                <transactionPricePerShare><footnoteId id="F1"/></transactionPricePerShare>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_parse_buy():
    parsed = parse_form4_xml(BUY_XML)

    assert parsed.issuer_ticker == "AAPL"
    assert parsed.issuer_name == "APPLE INC"
    assert parsed.owner_name == "LEVINSON ARTHUR D"
    assert parsed.is_director is True
    assert parsed.is_officer is False
    assert parsed.owner_title is None

    assert len(parsed.transactions) == 1
    txn = parsed.transactions[0]
    assert txn.txn_index == 0
    assert txn.transaction_code == "P"
    assert txn.transaction_date == date(2026, 7, 18)
    assert txn.shares == 1000.0
    assert txn.price == 210.50
    assert txn.value == 210500.0


def test_parse_sell():
    parsed = parse_form4_xml(SELL_XML)

    assert parsed.issuer_ticker == "MSFT"
    assert parsed.owner_name == "NADELLA SATYA"
    assert parsed.is_officer is True
    assert parsed.is_director is True
    assert parsed.owner_title == "Chief Executive Officer"

    assert len(parsed.transactions) == 1
    txn = parsed.transactions[0]
    assert txn.transaction_code == "S"
    assert txn.transaction_date == date(2026, 7, 15)
    assert txn.shares == 500.0
    assert txn.price == 195.25
    assert txn.value == 97625.0


def test_parse_derivative_only_yields_no_transactions():
    """A filing with only a stock award (A) + derivative exercise (M) and no
    P/S non-derivative transaction must produce zero transactions."""
    parsed = parse_form4_xml(DERIVATIVE_ONLY_XML)

    assert parsed.issuer_ticker == "NVDA"
    assert parsed.owner_name == "HUANG JEN HSUN"
    assert parsed.transactions == []


def test_txn_index_is_stable_across_filtered_codes():
    """Non-P/S codes are dropped but surviving transactions keep their original
    0-based position -> idempotent (accession_no, txn_index) keys."""
    parsed = parse_form4_xml(MIXED_XML)

    assert [t.transaction_code for t in parsed.transactions] == ["P", "S"]
    assert [t.txn_index for t in parsed.transactions] == [1, 2]

    buy, sell = parsed.transactions
    assert buy.value == 45000.0   # 300 * 150
    assert sell.value == 32000.0  # 200 * 160


def test_missing_price_leaves_value_none():
    parsed = parse_form4_xml(MISSING_PRICE_XML)

    assert len(parsed.transactions) == 1
    txn = parsed.transactions[0]
    assert txn.transaction_code == "P"
    assert txn.shares == 750.0
    assert txn.price is None
    assert txn.value is None


def test_extract_ownership_xml_from_full_submission():
    """The full submission .txt wraps the XML in SGML <DOCUMENT>/<XML> tags; we
    must be able to recover the ownershipDocument block and parse it."""
    submission = (
        "<SEC-DOCUMENT>0000320193-26-000123.txt\n"
        "<SEC-HEADER>...header junk...</SEC-HEADER>\n"
        "<DOCUMENT>\n<TYPE>4\n<SEQUENCE>1\n<FILENAME>form4.xml\n"
        "<TEXT>\n<XML>\n" + BUY_XML + "\n</XML>\n</TEXT>\n</DOCUMENT>\n"
        "</SEC-DOCUMENT>\n"
    )

    extracted = extract_ownership_xml(submission)
    assert extracted is not None
    assert extracted.startswith("<ownershipDocument>")
    assert extracted.rstrip().endswith("</ownershipDocument>")

    parsed = parse_form4_xml(extracted)
    assert parsed.issuer_ticker == "AAPL"
    assert len(parsed.transactions) == 1
    assert parsed.transactions[0].transaction_code == "P"
