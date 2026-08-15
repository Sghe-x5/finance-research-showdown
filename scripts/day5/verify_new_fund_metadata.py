#!/usr/bin/env python3
"""Verify new-fund listing, adviser, and reporting cutoffs from official SEC filings."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import importlib.util
import json
import os
import re
import time
from datetime import date
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[2]
V2_PATH = ROOT / "scripts/day5/build_replication_feasibility_v2.py"
REPORTING_PATH = ROOT / "scripts/day3/build_reporting_order_extended.py"

V2_SPEC = importlib.util.spec_from_file_location("day5_v2", V2_PATH)
v2 = importlib.util.module_from_spec(V2_SPEC)
assert V2_SPEC.loader is not None
V2_SPEC.loader.exec_module(v2)

REPORTING_SPEC = importlib.util.spec_from_file_location("day3_reporting", REPORTING_PATH)
reporting = importlib.util.module_from_spec(REPORTING_SPEC)
assert REPORTING_SPEC.loader is not None
REPORTING_SPEC.loader.exec_module(reporting)


REQUEST_DELAY = 0.16

MANAGER_FIELDS = (
    "cik", "fund_id", "filer_name", "canonical_manager", "legal_adviser",
    "verification_status", "evidence_source", "evidence_accession",
    "evidence_statement", "evidence_excerpt_sha256", "confidence",
)
LISTING_FIELDS = (
    "cik", "fund_id", "filer_name", "verified_equity_ticker",
    "verified_exchange", "listing_status", "verification_status",
    "evidence_source", "evidence_accession", "evidence_statement",
    "evidence_excerpt_sha256",
)
REPORTING_FIELDS = (
    "report_period_end", "report_period_label", "ticker", "cik", "form",
    "accession", "acceptance_timestamp_utc", "event_type",
    "verification_status", "evidence_source", "verification_evidence",
    "days_after_period_end",
)


# Expected adviser names are classification rules only.  A row is marked
# verified only if the named token appears in the official 10-K evidence.
ADVISERS = {
    "17313": ("Capital Southwest", "internally managed", ("internally managed",)),
    "1143513": ("Gladstone Management", "Gladstone Management Corporation", ("gladstone management corporation",)),
    "1321741": ("Gladstone Management", "Gladstone Management Corporation", ("gladstone management corporation",)),
    "1370755": ("BlackRock", "BlackRock Capital Investment Advisors, LLC", ("blackrock capital investment advisors", "tennenbaum capital partners")),
    "1383414": ("PennantPark", "PennantPark Investment Advisers, LLC", ("pennantpark investment advisers",)),
    "1487918": ("OFS Capital Management", "OFS Capital Management, LLC", ("ofs capital management", "ofs advisor")),
    "1504619": ("PennantPark", "PennantPark Investment Advisers, LLC", ("pennantpark investment advisers",)),
    "1534254": ("CION Investment Management", "CION Investment Management, LLC", ("cion investment management",)),
    "1535778": ("Main Street Capital", "MSC Adviser I, LLC", ("msc adviser i",)),
    "1551901": ("Stellus Capital Management", "Stellus Capital Management, LLC", ("stellus capital management",)),
    "1552198": ("H.I.G. WhiteHorse", "H.I.G. WhiteHorse Advisers, LLC", ("whitehorse advisers",)),
    "1655887": ("Blue Owl Credit", "Blue Owl Credit Advisors LLC", ("blue owl credit advisors", "owl rock capital advisors")),
    "1661306": ("OFS Capital Management", "OFS Capital Management, LLC", ("ofs capital management", "ofs advisor")),
    "1715933": ("TCW", "TCW Asset Management Company LLC", ("tcw asset management",)),
    "1766037": ("New Mountain Capital", "New Mountain Finance Advisers BDC, L.L.C.", ("new mountain",)),
    "1781870": ("New Mountain Capital", "New Mountain Guardian III BDC Adviser, L.L.C.", ("new mountain",)),
    "1737924": ("Nuveen Churchill", "Churchill DLC Advisor LLC", ("churchill dlc advisor", "churchill asset management")),
    "1747777": ("Blue Owl Credit", "Blue Owl Technology Credit Advisors II LLC", ("blue owl technology credit advisors", "owl rock technology advisors")),
    "1782524": ("Morgan Stanley Investment Management", "MS Capital Partners Adviser Inc.", ("ms capital partners adviser",)),
    "1794776": ("Palmer Square Capital Management", "Palmer Square BDC Advisor LLC", ("palmer square bdc advisor", "palmer square capital management")),
    "1807427": ("Blue Owl Credit", "Blue Owl Credit Advisors LLC", ("blue owl credit advisors", "owl rock capital advisors")),
    "1811972": ("Barings", "Barings LLC", ("barings llc",)),
    "1843162": ("Chicago Atlantic", "Chicago Atlantic BDC Advisers, LLC", ("chicago atlantic bdc advisers",)),
    "1859919": ("Barings", "Barings LLC", ("barings llc",)),
    "1869453": ("Blue Owl Credit", "Blue Owl Technology Credit Advisors LLC", ("blue owl technology credit advisors", "owl rock technology advisors")),
    "1872371": ("Oaktree Capital Management", "Oaktree Fund Advisors, LLC", ("oaktree fund advisors",)),
    "1889668": ("Blue Owl Credit", "Blue Owl Technology Credit Advisors II LLC", ("blue owl technology credit advisors", "owl rock technology advisors")),
    "1901037": ("Stellus Capital Management", "Stellus Capital Management, LLC", ("stellus capital management",)),
    "1923622": ("PGIM", "PGIM Private Capital", ("pgim private capital", "pgim investments")),
    "1925531": ("New Mountain Capital", "New Mountain Guardian IV BDC Adviser, L.L.C.", ("new mountain",)),
    "1976719": ("New Mountain Capital", "New Mountain Guardian IV Income Fund Adviser, L.L.C.", ("new mountain",)),
}

MANAGER_VERIFICATION_CLOSURE_CIKS = {"1766037", "1781870", "1925531", "1976719"}

EXPECTED_EQUITY_TICKERS = {
    "17313": "CSWC", "1143513": "GLAD", "1321741": "GAIN",
    "1370755": "TCPC", "1383414": "PNNT", "1487918": "OFS",
    "1504619": "PFLT", "1534254": "CION", "1551901": "SCM",
    "1552198": "WHF", "1737924": "NCDL", "1747777": "OTF",
    "1782524": "MSDL", "1794776": "PSBD", "1843162": "LIEN",
}


def require_user_agent() -> str:
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SystemExit("SEC_USER_AGENT must contain a descriptive name and contact email")
    return value


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def plain_text(raw: str) -> str:
    value = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", raw)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


class SecClient:
    def __init__(self, user_agent: str):
        self.session = requests.Session()
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "identity"}

    def text(self, url: str) -> str:
        response = self.session.get(url, headers=self.headers, timeout=120)
        response.raise_for_status()
        value = response.text
        time.sleep(REQUEST_DELAY)
        return value

    def json(self, url: str) -> dict:
        return json.loads(self.text(url))


def recent_rows(payload: dict) -> list[dict[str, str]]:
    recent = payload["filings"]["recent"]
    fields = (
        "form", "accessionNumber", "acceptanceDateTime", "reportDate", "items",
        "primaryDocument",
    )
    count = len(recent["form"])
    return [
        {field: recent.get(field, [""] * count)[index] for field in fields}
        for index in range(count)
    ]


def historical_rows(client: SecClient, payload: dict) -> list[dict[str, str]]:
    rows = recent_rows(payload)
    for item in payload["filings"].get("files", []):
        old = client.json(f"https://data.sec.gov/submissions/{item['name']}")
        fields = (
            "form", "accessionNumber", "acceptanceDateTime", "reportDate", "items",
            "primaryDocument",
        )
        count = len(old.get("form", []))
        rows.extend([
            {field: old.get(field, [""] * count)[index] for field in fields}
            for index in range(count)
        ])
    unique = {row["accessionNumber"]: row for row in rows if row["accessionNumber"]}
    return list(unique.values())


def latest_10k(rows: list[dict[str, str]]) -> dict[str, str] | None:
    candidates = [row for row in rows if row["form"] == "10-K"]
    return max(candidates, key=lambda row: row["acceptanceDateTime"], default=None)


def filing_url(cik: str, filing: dict[str, str]) -> str:
    accession = filing["accessionNumber"].replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/"
        f"{filing['primaryDocument']}"
    )


def verify_manager(cik: str, meta: dict, filing: dict, raw: str) -> dict[str, str]:
    expected = ADVISERS.get(cik)
    text = plain_text(raw).lower()
    canonical = legal = ""
    token = ""
    if expected:
        canonical, legal, tokens = expected
        token = next((value for value in tokens if value in text), "")
    verified = bool(token)
    excerpt = ""
    if token:
        start = max(0, text.find(token) - 80)
        excerpt = text[start:start + len(token) + 160]
    return {
        "cik": cik,
        "fund_id": meta["fund_id"],
        "filer_name": meta["filer_name"],
        "canonical_manager": canonical if verified else "",
        "legal_adviser": legal if verified else "",
        "verification_status": "verified" if verified else "unverified",
        "evidence_source": filing_url(cik, filing),
        "evidence_accession": filing["accessionNumber"],
        "evidence_statement": (
            f"Official 10-K contains the adviser evidence token '{token}'."
            if verified else "Expected adviser identity was not reproducibly located in the latest official 10-K."
        ),
        "evidence_excerpt_sha256": digest_text(excerpt) if excerpt else "",
        "confidence": "high" if verified else "low",
    }


def verify_listing(cik: str, meta: dict, payload: dict, filing: dict, raw: str) -> dict[str, str]:
    expected = EXPECTED_EQUITY_TICKERS.get(cik, "")
    tickers = [str(value) for value in payload.get("tickers", [])]
    exchanges = [str(value) for value in payload.get("exchanges", [])]
    ticker_exchange = dict(zip(tickers, exchanges))
    text = plain_text(raw)
    lower = text.lower()
    evidence = ""
    verified = False
    exchange = ticker_exchange.get(expected, "")
    if expected and expected in tickers:
        for match in re.finditer(rf"\b{re.escape(expected)}\b", text, re.I):
            window = lower[max(0, match.start() - 500):match.end() + 500]
            if "common stock" in window and (
                "nasdaq" in window or "new york stock exchange" in window or "nyse" in window
            ):
                evidence = text[max(0, match.start() - 200):match.end() + 300]
                verified = True
                break
    return {
        "cik": cik,
        "fund_id": meta["fund_id"],
        "filer_name": meta["filer_name"],
        "verified_equity_ticker": expected if verified else "",
        "verified_exchange": exchange if verified else "",
        "listing_status": "verified_listed_equity" if verified else "not_verified_as_listed_equity",
        "verification_status": "verified" if verified else "unverified_or_nonlisted",
        "evidence_source": filing_url(cik, filing),
        "evidence_accession": filing["accessionNumber"],
        "evidence_statement": (
            f"Official 10-K cover evidence links common stock ticker {expected} to {exchange}."
            if verified else "No reproducible official 10-K cover match established a listed common-equity ticker."
        ),
        "evidence_excerpt_sha256": digest_text(evidence) if evidence else "",
    }


def date_lag(period_end: str, timestamp: str) -> int:
    return (reporting.parse_timestamp(timestamp).date() - date.fromisoformat(period_end)).days


def verify_reporting_row(
    client: SecClient,
    cik: str,
    meta: dict,
    period_end: str,
    filings: list[dict[str, str]],
    listed: bool,
) -> dict[str, str]:
    base = {
        "report_period_end": period_end,
        "report_period_label": reporting.report_period_label(period_end),
        "ticker": meta["fund_id"],
        "cik": cik,
    }
    if not listed:
        return {
            **base, "form": "", "accession": "", "acceptance_timestamp_utc": "",
            "event_type": "", "verification_status": "excluded_not_verified_listed_equity",
            "evidence_source": "", "verification_evidence": "Target equity listing was not verified.",
            "days_after_period_end": "",
        }
    candidates = []
    exclusion_reasons = []
    for filing in filings:
        if filing["form"] != "8-K":
            continue
        lag = date_lag(period_end, filing["acceptanceDateTime"])
        if not 0 <= lag <= 120:
            continue
        items = filing.get("items") or ""
        item_202 = "2.02" in items
        if not item_202 and "7.01" not in items:
            continue
        accession = filing["accessionNumber"]
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession.replace('-', '')}/{accession}.txt"
        )
        raw = client.text(url)
        result, reason = reporting.classify_8k_for_period(raw, period_end, item_202)
        if result:
            candidates.append({**filing, **result, "evidence_source": (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession.replace('-', '')}/{result['filename']}"
            )})
        elif reason:
            exclusion_reasons.append(f"{accession}: {reason}")
    periodic = reporting.periodic_candidate(filings, period_end, cik)
    selected = min(candidates, key=lambda row: row["acceptanceDateTime"], default=None)
    if selected:
        return {
            **base,
            "form": "8-K",
            "accession": selected["accessionNumber"],
            "acceptance_timestamp_utc": selected["acceptanceDateTime"],
            "event_type": selected["event_type"],
            "verification_status": "verified",
            "evidence_source": selected["evidence_source"],
            "verification_evidence": selected["evidence"],
            "days_after_period_end": date_lag(period_end, selected["acceptanceDateTime"]),
        }
    if periodic:
        return {
            **base,
            "form": periodic["form"],
            "accession": periodic["accessionNumber"],
            "acceptance_timestamp_utc": periodic["acceptanceDateTime"],
            "event_type": periodic["event_type"],
            "verification_status": "verified",
            "evidence_source": periodic["periodic_url"],
            "verification_evidence": periodic["verification_evidence"],
            "days_after_period_end": date_lag(period_end, periodic["acceptanceDateTime"]),
        }
    return {
        **base, "form": "", "accession": "", "acceptance_timestamp_utc": "",
        "event_type": "", "verification_status": "explicit_missing",
        "evidence_source": "",
        "verification_evidence": "; ".join(exclusion_reasons[:5]) or "No verified results or exact-period periodic filing in 0-120 days.",
        "days_after_period_end": "",
    }


def write_csv(path: Path, rows: list[dict[str, str]], fields) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager-output", type=Path, default=v2.DEFAULT_MANAGER_VERIFIED)
    parser.add_argument("--listing-output", type=Path, default=v2.DEFAULT_LISTING_VERIFIED)
    parser.add_argument("--reporting-output", type=Path, default=v2.DEFAULT_REPORTING_VERIFIED)
    args = parser.parse_args()
    client = SecClient(require_user_agent())
    context = v2.provisional_context()
    new_ciks = v2.new_fund_scope(context) | MANAGER_VERIFICATION_CLOSURE_CIKS
    targets = v2.target_scope(context)
    target_ciks = {cik for cik, _ in targets}
    all_ciks = sorted(new_ciks | target_ciks, key=int)
    payloads = {}
    filings_by_cik = {}
    manager_rows = []
    listing_rows = []
    for cik in all_ciks:
        payload = client.json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json")
        filings = historical_rows(client, payload)
        latest = latest_10k(filings)
        if cik in target_ciks:
            payloads[cik] = payload
            filings_by_cik[cik] = filings
        if cik in new_ciks:
            meta = context["metadata"][cik]
            if latest:
                raw = client.text(filing_url(cik, latest))
                manager_rows.append(verify_manager(cik, meta, latest, raw))
                listing_rows.append(verify_listing(cik, meta, payload, latest, raw))
            else:
                manager_rows.append({
                    "cik": cik, "fund_id": meta["fund_id"], "filer_name": meta["filer_name"],
                    "canonical_manager": "", "legal_adviser": "", "verification_status": "unverified",
                    "evidence_source": "", "evidence_accession": "", "evidence_statement": "No official 10-K located.",
                    "evidence_excerpt_sha256": "", "confidence": "low",
                })
                listing_rows.append({
                    "cik": cik, "fund_id": meta["fund_id"], "filer_name": meta["filer_name"],
                    "verified_equity_ticker": "", "verified_exchange": "",
                    "listing_status": "not_verified_as_listed_equity", "verification_status": "unverified_or_nonlisted",
                    "evidence_source": "", "evidence_accession": "", "evidence_statement": "No official 10-K located.",
                    "evidence_excerpt_sha256": "",
                })
        print(f"SEC metadata: {cik} {context['metadata'][cik]['filer_name']}")
    manager_rows.sort(key=lambda row: int(row["cik"]))
    listing_rows.sort(key=lambda row: int(row["cik"]))
    listing_map = {row["cik"]: row for row in listing_rows}
    reporting_rows = []
    for cik, period_end in sorted(targets, key=lambda value: (value[1], int(value[0]))):
        listed = (
            cik in context["existing_ciks"]
            or listing_map.get(cik, {}).get("listing_status") == "verified_listed_equity"
        )
        reporting_rows.append(verify_reporting_row(
            client, cik, context["metadata"][cik], period_end,
            filings_by_cik[cik], listed,
        ))
        print(f"reporting: {cik} {period_end} {reporting_rows[-1]['verification_status']}")

    write_csv(args.manager_output, manager_rows, MANAGER_FIELDS)
    write_csv(args.listing_output, listing_rows, LISTING_FIELDS)
    write_csv(args.reporting_output, reporting_rows, REPORTING_FIELDS)
    print(json.dumps({
        "new_funds": len(new_ciks),
        "manager_verified": sum(row["verification_status"] == "verified" for row in manager_rows),
        "listed_equity_verified": sum(row["listing_status"] == "verified_listed_equity" for row in listing_rows),
        "reporting_rows": len(reporting_rows),
        "reporting_verified": sum(row["verification_status"] == "verified" for row in reporting_rows),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
