#!/usr/bin/env python3
"""Build a verified BDC results calendar for report periods 2023Q4-2025Q3."""

import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import requests
except ModuleNotFoundError:  # Read-only helpers remain importable with stdlib-only Python.
    requests = None

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import read_csv, sha256_file, write_csv, write_json  # noqa: E402
from reporting_text_utils import (  # noqa: E402
    classify_exhibit_text, normalize_html, parse_submission_documents,
)


PERIOD_ENDS = (
    "2023-12-31", "2024-03-31", "2024-06-30", "2024-09-30",
    "2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30",
)
PRESERVE_PERIODS = {"2025-03-31", "2025-06-30", "2025-09-30"}
NONLISTED = {"BCRED", "HPS", "ASIF", "OCIC"}
MAX_LAG_DAYS = 120
REQUEST_DELAY_SECONDS = 0.16

DEFAULT_EXISTING = Path("02_showdown/reporting_order.csv")
DEFAULT_OUTPUT = Path("data/day3/reporting_order_extended.csv")
DEFAULT_META = Path("data/day3/reporting_order_extended_meta.json")
DEFAULT_CACHE = Path("/private/tmp/finance-day3-sec-cache/reporting_order_extended")

FIELDS = [
    "report_period_end", "report_period_label", "ticker", "cik", "listed_status",
    "form", "accession", "acceptance_timestamp_utc", "acceptance_timestamp_et",
    "market_session", "event_type", "exhibit_url", "periodic_filing_accession",
    "periodic_filing_url", "verification_status", "verification_evidence",
    "exclusion_reason", "days_after_period_end", "candidate_search_window_days",
]


def report_period_label(period_end):
    parsed = date.fromisoformat(period_end)
    return f"{parsed.year}Q{(parsed.month - 1) // 3 + 1}"


def parse_timestamp(value):
    value = (value or "").replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def timestamp_et(value):
    if not value:
        return ""
    return parse_timestamp(value).astimezone(ZoneInfo("America/New_York")).isoformat()


def market_session(value):
    if not value:
        return ""
    local = parse_timestamp(value).astimezone(ZoneInfo("America/New_York"))
    if (local.hour, local.minute) < (9, 30):
        return "pre-market"
    if local.hour >= 16:
        return "after-market"
    return "market-hours"


def lag_days(period_end, accepted):
    if not accepted:
        return None
    delta = parse_timestamp(accepted).date() - date.fromisoformat(period_end)
    return delta.days


def require_user_agent():
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SystemExit("SEC_USER_AGENT must contain a descriptive name and contact email")
    return value


def fetch_cached(session, url, cache_path, user_agent, as_json=False):
    if cache_path.exists():
        text = cache_path.read_text(encoding="utf-8")
        return json.loads(text) if as_json else text
    response = session.get(url, headers={"User-Agent": user_agent}, timeout=60)
    response.raise_for_status()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    time.sleep(REQUEST_DELAY_SECONDS)
    return response.json() if as_json else response.text


def filing_rows(payload):
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


def period_text_matches(text, period_end):
    lower = normalize_html(text).lower()
    parsed = date.fromisoformat(period_end)
    month = parsed.strftime("%B").lower()
    day = str(parsed.day)
    year = str(parsed.year)
    date_patterns = (
        rf"{month}\s+0?{day},?\s+{year}",
        rf"{parsed.month:02d}[/-]{parsed.day:02d}[/-]{year}",
        rf"{year}[/-]{parsed.month:02d}[/-]{parsed.day:02d}",
    )
    if any(re.search(pattern, lower) for pattern in date_patterns):
        return True, f"exact period-end date {period_end} found in exhibit"
    quarter = (parsed.month - 1) // 3 + 1
    quarter_words = {1: "first", 2: "second", 3: "third", 4: "fourth"}
    quarter_patterns = (
        rf"\bq{quarter}\b[^.]{{0,60}}\b{year}\b",
        rf"\b{quarter_words[quarter]} quarter\b[^.]{{0,60}}\b{year}\b",
    )
    if any(re.search(pattern, lower) for pattern in quarter_patterns):
        return True, f"quarter/year language for {report_period_label(period_end)} found in exhibit"
    return False, f"no exact period evidence for {period_end} in exhibit"


def classify_8k_for_period(raw_submission, period_end, item_202):
    documents = parse_submission_documents(raw_submission)
    exhibits = [row for row in documents if row["type"].upper().startswith("EX-99")]
    if not exhibits:
        return None, "8-K has no EX-99 exhibit"
    reasons = []
    for exhibit in exhibits:
        accepted, base_event_type, reason = classify_exhibit_text(exhibit["text"])
        if not accepted:
            reasons.append(reason)
            continue
        exact_period, period_evidence = period_text_matches(exhibit["text"], period_end)
        if not exact_period:
            reasons.append(period_evidence)
            continue
        event_type = "8-K_ITEM_2.02_RESULTS" if item_202 else base_event_type
        return {
            "event_type": event_type,
            "filename": exhibit["filename"],
            "evidence": f"verified EX-99 results/NAV metrics; {period_evidence}",
        }, ""
    return None, "; ".join(dict.fromkeys(reason for reason in reasons if reason))


def accession_base(cik, accession):
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}"


def periodic_candidate(rows, period_end, cik):
    candidates = []
    for filing in rows:
        if filing["form"] not in {"10-Q", "10-K"} or filing["reportDate"] != period_end:
            continue
        lag = lag_days(period_end, filing["acceptanceDateTime"])
        if lag is None or not 0 <= lag <= MAX_LAG_DAYS:
            continue
        base = accession_base(cik, filing["accessionNumber"])
        candidates.append({
            **filing,
            "event_type": filing["form"],
            "exhibit_url": "",
            "periodic_url": f"{base}/{filing['primaryDocument']}",
            "verification_status": "verified_periodic_filing_fallback",
            "verification_evidence": f"{filing['form']} reportDate exactly equals {period_end}",
        })
    return min(candidates, key=lambda row: row["acceptanceDateTime"], default=None)


def eight_k_candidates(session, rows, period_end, ticker, cik, cache_dir, user_agent):
    accepted = []
    exclusions = []
    for filing in rows:
        if filing["form"] != "8-K":
            continue
        lag = lag_days(period_end, filing["acceptanceDateTime"])
        if lag is None or not 0 <= lag <= MAX_LAG_DAYS:
            continue
        items = filing.get("items") or ""
        item_202 = "2.02" in items
        if not item_202 and "7.01" not in items:
            continue
        accession = filing["accessionNumber"]
        base = accession_base(cik, accession)
        raw = fetch_cached(
            session, f"{base}/{accession}.txt",
            cache_dir / "filings" / str(cik) / f"{accession}.txt", user_agent,
        )
        result, reason = classify_8k_for_period(raw, period_end, item_202)
        if result:
            accepted.append({
                **filing,
                **result,
                "exhibit_url": f"{base}/{result['filename']}",
                "periodic_url": "",
                "verification_status": "verified_exhibit_content",
                "verification_evidence": result["evidence"],
            })
        elif reason:
            exclusions.append(f"{accession}: {reason}")
    return accepted, exclusions


def preserved_row(existing, periodic, exclusions):
    period_end = existing["period_end"]
    timestamp = existing["first_results_timestamp_utc"]
    event_type = existing["event_type"]
    form = event_type if event_type in {"10-Q", "10-K"} else "8-K"
    reasons = [existing.get("exclusion_reason", ""), *exclusions]
    return {
        "form": form,
        "accessionNumber": existing["accession"],
        "acceptanceDateTime": timestamp,
        "event_type": event_type,
        "exhibit_url": existing["source_url"] if form == "8-K" else "",
        "periodic_accession": periodic["accessionNumber"] if periodic else (existing["accession"] if form != "8-K" else ""),
        "periodic_url": periodic["periodic_url"] if periodic else (existing["source_url"] if form != "8-K" else ""),
        "verification_status": existing["verification_status"] + "_preserved",
        "verification_evidence": "selection and timestamp preserved from verified Day 1/Day 2 reporting_order.csv",
        "exclusion_reason": " | ".join(dict.fromkeys(reason for reason in reasons if reason)),
        "report_period_end": period_end,
    }


def output_row(ticker, cik, period_end, selected, periodic, exclusions):
    listed_status = "non-listed" if ticker in NONLISTED else "listed"
    if selected is None:
        return {
            "report_period_end": period_end,
            "report_period_label": report_period_label(period_end),
            "ticker": ticker,
            "cik": cik,
            "listed_status": listed_status,
            "form": "",
            "accession": "",
            "acceptance_timestamp_utc": "",
            "acceptance_timestamp_et": "",
            "market_session": "",
            "event_type": "missing",
            "exhibit_url": "",
            "periodic_filing_accession": periodic["accessionNumber"] if periodic else "",
            "periodic_filing_url": periodic["periodic_url"] if periodic else "",
            "verification_status": "explicit_missing",
            "verification_evidence": "no verified results/NAV event or exact-reportDate periodic filing in 0-120 day window",
            "exclusion_reason": " | ".join(exclusions),
            "days_after_period_end": "",
            "candidate_search_window_days": "0-120",
        }
    timestamp = selected["acceptanceDateTime"]
    return {
        "report_period_end": period_end,
        "report_period_label": report_period_label(period_end),
        "ticker": ticker,
        "cik": cik,
        "listed_status": listed_status,
        "form": selected["form"],
        "accession": selected["accessionNumber"],
        "acceptance_timestamp_utc": timestamp,
        "acceptance_timestamp_et": timestamp_et(timestamp),
        "market_session": market_session(timestamp),
        "event_type": selected["event_type"],
        "exhibit_url": selected.get("exhibit_url", ""),
        "periodic_filing_accession": selected.get("periodic_accession", "") or (periodic["accessionNumber"] if periodic else ""),
        "periodic_filing_url": selected.get("periodic_url", "") or (periodic["periodic_url"] if periodic else ""),
        "verification_status": selected["verification_status"],
        "verification_evidence": selected["verification_evidence"],
        "exclusion_reason": selected.get("exclusion_reason", "") or " | ".join(exclusions),
        "days_after_period_end": lag_days(period_end, timestamp),
        "candidate_search_window_days": "0-120",
    }


def quantiles(values):
    if not values:
        return None, None, None
    if len(values) == 1:
        return values[0], values[0], values[0]
    p25, _, p75 = statistics.quantiles(values, n=4, method="inclusive")
    return p25, statistics.median(values), p75


def build_meta(rows, exclusions, output_path, source_path):
    lags = [int(row["days_after_period_end"]) for row in rows if row["days_after_period_end"] != ""]
    p25, median, p75 = quantiles(lags)
    coverage = {}
    for period_end in PERIOD_ENDS:
        period_rows = [row for row in rows if row["report_period_end"] == period_end]
        coverage[report_period_label(period_end)] = {
            "expected": len(period_rows),
            "verified": sum(row["verification_status"] != "explicit_missing" for row in period_rows),
            "periodic_fallback": sum(row["event_type"] in {"10-Q", "10-K"} for row in period_rows),
            "missing": sum(row["verification_status"] == "explicit_missing" for row in period_rows),
        }
    return {
        "report_periods": list(PERIOD_ENDS),
        "candidate_search_window_days": [0, MAX_LAG_DAYS],
        "normal_range_diagnostic_days": [20, 80],
        "normal_range_is_hard_filter": False,
        "fund_count": len({row["ticker"] for row in rows}),
        "expected_fund_period_rows": len(rows),
        "verified": sum(row["verification_status"] != "explicit_missing" for row in rows),
        "fallback_periodic_filing": sum(row["event_type"] in {"10-Q", "10-K"} for row in rows),
        "missing": sum(row["verification_status"] == "explicit_missing" for row in rows),
        "excluded_scheduling": sum("scheduling announcement" in reason for reason in exclusions),
        "excluded_candidate_reasons": dict(sorted(Counter(exclusions).items())),
        "filing_lag_days": {
            "min": min(lags) if lags else None,
            "p25": p25,
            "median": median,
            "p75": p75,
            "max": max(lags) if lags else None,
            "inside_20_80": sum(20 <= lag <= 80 for lag in lags),
            "outside_20_80_but_inside_0_120": sum(not 20 <= lag <= 80 for lag in lags),
        },
        "coverage_matrix": coverage,
        "preserved_periods_from_day1_day2": sorted(PRESERVE_PERIODS),
        "existing_reporting_order_sha256": sha256_file(source_path),
        "output_sha256": sha256_file(output_path),
        "raw_sec_cache": "outside Git",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing", type=Path, default=DEFAULT_EXISTING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_META)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args()
    user_agent = require_user_agent()
    existing_rows = read_csv(args.existing)
    funds = {}
    existing = {}
    for row in existing_rows:
        funds[row["ticker"]] = str(int(row["cik"]))
        existing[(row["ticker"], row["period_end"])] = row

    if requests is None:
        raise SystemExit("requests is required to rebuild reporting_order_extended")
    session = requests.Session()
    output = []
    all_exclusions = []
    for ticker, cik in sorted(funds.items()):
        print(f"SEC reporting-order: {ticker}", flush=True)
        payload = fetch_cached(
            session, f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json",
            args.cache_dir / "submissions" / f"CIK{int(cik):010d}.json", user_agent,
            as_json=True,
        )
        filings = filing_rows(payload)
        for period_end in PERIOD_ENDS:
            periodic = periodic_candidate(filings, period_end, cik)
            verified_8ks, exclusions = eight_k_candidates(
                session, filings, period_end, ticker, cik, args.cache_dir, user_agent,
            )
            all_exclusions.extend(exclusions)
            if period_end in PRESERVE_PERIODS and (ticker, period_end) in existing:
                selected = preserved_row(existing[(ticker, period_end)], periodic, exclusions)
            else:
                candidates = list(verified_8ks)
                if periodic:
                    candidates.append(periodic)
                selected = min(candidates, key=lambda row: row["acceptanceDateTime"], default=None)
                if selected is not None:
                    selected = dict(selected)
                    selected["exclusion_reason"] = " | ".join(exclusions)
            output.append(output_row(ticker, cik, period_end, selected, periodic, exclusions))

    output.sort(key=lambda row: (row["report_period_end"], row["acceptance_timestamp_utc"] or "9999", row["ticker"]))
    write_csv(args.output, output, FIELDS)
    write_json(args.metadata, build_meta(output, all_exclusions, args.output, args.existing))
    print(json.dumps(json.loads(args.metadata.read_text(encoding="utf-8")), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
