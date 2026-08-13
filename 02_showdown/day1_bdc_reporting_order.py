"""Rebuild the BDC first-public-results calendar from SEC filings.

SEC sometimes labels an earnings-date announcement as Item 2.02.  This script
therefore verifies the attached EX-99 text instead of treating every 2.02 8-K
as quarterly results.  Set SEC_USER_AGENT to a descriptive value containing a
real contact email before running.
"""

import csv
import html
import itertools
import os
import re
import statistics
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


TICKERS = [
    "ARCC", "OBDC", "BXSL", "FSK", "GBDC", "MAIN", "HTGC", "TSLX",
    "OCSL", "NMFC", "BBDC", "GSBD", "MFIC", "PSEC", "CGBD",
]
NONTRADED = {
    "BCRED": 1803498,
    "HPS": 1838126,
    "ASIF": 1918712,
    "OCIC": 1812554,
}
START_ACCEPTANCE = "2025-04"
OUTPUT = Path(__file__).with_name("reporting_order.csv")
SUMMARY_OUTPUT = Path(__file__).with_name("reporting_order_summary.csv")

SCHEDULING_PATTERNS = (
    r"schedules? (?:earnings )?release",
    r"schedules? release of .*results",
    r"will (?:release|report|announce) (?:its )?financial results",
    r"plans? to (?:release|report|announce) (?:its )?financial results",
)
DIVIDEND_PATTERNS = (
    r"declares? (?:a )?(?:quarterly )?(?:cash )?(?:dividend|distribution)",
    r"dividend declaration",
)
ACTUAL_RESULTS_PATTERNS = (
    r"net investment income",
    r"net asset value(?: per share)?",
    r"NAV per share",
    r"earnings per share",
    r"financial highlights",
)
RELEASE_PATTERNS = (
    r"(?:announces?|reports?|reported) .*financial results",
    r"financial results for the .*quarter ended",
    r"preliminary .*net asset value",
    r"estimated .*net asset value",
)


def normalize_html(raw):
    text = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", raw,
                  flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_submission_documents(raw):
    documents = []
    for block in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", raw, re.I | re.S):
        def field(name):
            match = re.search(rf"<{name}>([^\r\n<]+)", block, re.I)
            return match.group(1).strip() if match else ""

        text_match = re.search(r"<TEXT>(.*)", block, re.I | re.S)
        documents.append({
            "type": field("TYPE"),
            "filename": field("FILENAME"),
            "description": field("DESCRIPTION"),
            "text": normalize_html(text_match.group(1) if text_match else block),
        })
    return documents


def classify_exhibit_text(text):
    """Return (is_results, event_type, exclusion_reason)."""
    lower = text.lower()
    scheduling = any(re.search(p, lower) for p in SCHEDULING_PATTERNS)
    dividend = any(re.search(p, lower) for p in DIVIDEND_PATTERNS)
    actual_metrics = sum(bool(re.search(p, lower)) for p in ACTUAL_RESULTS_PATTERNS)
    release_language = any(re.search(p, lower) for p in RELEASE_PATTERNS)
    has_numbers = bool(re.search(r"\$\s?\d|\b\d+\.\d+\b", lower))

    if scheduling and actual_metrics < 2:
        return False, "", "scheduling announcement; future results date only"
    if dividend and actual_metrics < 2:
        return False, "", "dividend/distribution announcement without results or NAV"
    if actual_metrics >= 2 and has_numbers:
        event_type = "8-K_EX-99_RESULTS" if release_language else "8-K_EX-99_NAV"
        return True, event_type, ""
    return False, "", "Item 2.02 exhibit lacks verified quarterly results/NAV metrics"


def classify_8k_documents(documents):
    exhibits = [d for d in documents if d["type"].upper().startswith("EX-99")]
    if not exhibits:
        return False, "", "", "Item 2.02 filing has no EX-99 results/NAV exhibit"

    reasons = []
    for document in exhibits:
        accepted, event_type, reason = classify_exhibit_text(document["text"])
        if accepted:
            return True, event_type, document["filename"], ""
        reasons.append(reason)
    return False, "", "", "; ".join(dict.fromkeys(reasons))


def previous_quarter_end(timestamp):
    dt = datetime.fromisoformat(timestamp[:10])
    if dt.month <= 3:
        return f"{dt.year - 1}-12-31"
    if dt.month <= 6:
        return f"{dt.year}-03-31"
    if dt.month <= 9:
        return f"{dt.year}-06-30"
    return f"{dt.year}-09-30"


def quarter_label(period_end):
    dt = datetime.fromisoformat(period_end)
    return f"{dt.year}Q{(dt.month - 1) // 3 + 1}"


def market_session(timestamp):
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    dt_et = dt.astimezone(ZoneInfo("America/New_York"))
    if dt_et.hour < 9 or (dt_et.hour == 9 and dt_et.minute < 30):
        return "pre-market"
    if dt_et.hour >= 16:
        return "after-market"
    return "market-hours"


def timestamp_et(timestamp):
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.astimezone(ZoneInfo("America/New_York")).isoformat()


def require_user_agent():
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SystemExit(
            "Set SEC_USER_AGENT to a descriptive SEC User-Agent with a real "
            "contact email, e.g. 'ShadowNAV research name@example.com'."
        )
    return {"User-Agent": value}


def fetch_json(session, url, headers):
    response = session.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    time.sleep(0.15)
    return response.json()


def fetch_text(session, url, headers):
    response = session.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    time.sleep(0.15)
    return response.text


def candidate_events(ticker, cik, filings, session, headers):
    events = []
    exclusions = {}
    fields = zip(
        filings["form"], filings["accessionNumber"],
        filings["acceptanceDateTime"], filings.get("items", []),
        filings["reportDate"], filings["primaryDocument"],
    )
    for form, accession, accepted, items, report_date, primary_document in fields:
        if accepted < START_ACCEPTANCE:
            continue
        accession_flat = accession.replace("-", "")
        base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_flat}"

        if form == "8-K" and "2.02" in (items or ""):
            raw = fetch_text(session, f"{base}/{accession}.txt", headers)
            documents = parse_submission_documents(raw)
            verified, event_type, filename, reason = classify_8k_documents(documents)
            period_end = ""
            if verified:
                # Results filings in this pilot arrive in the next reporting
                # season. Do not parse a comparative prior-year date from the
                # exhibit as the current period end.
                period_end = previous_quarter_end(accepted)
                events.append({
                    "ticker": ticker,
                    "cik": int(cik),
                    "quarter": quarter_label(period_end),
                    "period_end": period_end,
                    "first_results_timestamp_utc": accepted,
                    "first_results_timestamp_et": timestamp_et(accepted),
                    "market_session": market_session(accepted),
                    "event_type": event_type,
                    "accession": accession,
                    "source_url": f"{base}/{filename}",
                    "verification_status": "verified_exhibit_content",
                    "exclusion_reason": "",
                })
            else:
                q = quarter_label(previous_quarter_end(accepted))
                exclusions.setdefault(q, []).append(f"{accession}: {reason}")

        elif form in ("10-Q", "10-K") and report_date:
            events.append({
                "ticker": ticker,
                "cik": int(cik),
                "quarter": quarter_label(report_date),
                "period_end": report_date,
                "first_results_timestamp_utc": accepted,
                "first_results_timestamp_et": timestamp_et(accepted),
                "market_session": market_session(accepted),
                "event_type": form,
                "accession": accession,
                "source_url": f"{base}/{primary_document}",
                "verification_status": "verified_filing_fallback",
                "exclusion_reason": "",
            })
    return events, exclusions


def select_first_events(events, exclusions):
    first = {}
    for event in events:
        key = (event["ticker"], event["quarter"])
        if key not in first or event["first_results_timestamp_utc"] < first[key]["first_results_timestamp_utc"]:
            first[key] = event
    for key, event in first.items():
        excluded = exclusions.get(key, [])
        if excluded:
            event["exclusion_reason"] = " | ".join(excluded)
    return list(first.values())


def quantiles(values):
    p25, _, p75 = statistics.quantiles(values, n=4, method="inclusive")
    return p25, statistics.median(values), p75


def build_summary(rows):
    by_quarter = {}
    for row in rows:
        if row["ticker"] in TICKERS:
            by_quarter.setdefault(row["quarter"], []).append(row)
    complete = [q for q, values in by_quarter.items() if len(values) == len(TICKERS)]
    complete = sorted(complete)[-5:]

    windows = []
    summary_rows = []
    for quarter in complete:
        ordered = sorted(by_quarter[quarter], key=lambda row: row["first_results_timestamp_utc"])
        quarter_windows = []
        for early, late in itertools.combinations(ordered, 2):
            a = datetime.fromisoformat(early["first_results_timestamp_utc"].replace("Z", "+00:00"))
            b = datetime.fromisoformat(late["first_results_timestamp_utc"].replace("Z", "+00:00"))
            days = (b - a).total_seconds() / 86400
            if days > 0:
                quarter_windows.append(days)
                windows.append(days)
        p25, median, p75 = quantiles(quarter_windows)
        summary_rows.append({
            "quarter": quarter,
            "n_windows": len(quarter_windows),
            "p25_days": round(p25, 3),
            "median_days": round(median, 3),
            "p75_days": round(p75, 3),
            "gt_1d": sum(value > 1 for value in quarter_windows),
            "gt_3d": sum(value > 3 for value in quarter_windows),
            "gt_5d": sum(value > 5 for value in quarter_windows),
        })
    if windows:
        p25, median, p75 = quantiles(windows)
        summary_rows.append({
            "quarter": "ALL_COMPLETE",
            "n_windows": len(windows),
            "p25_days": round(p25, 3),
            "median_days": round(median, 3),
            "p75_days": round(p75, 3),
            "gt_1d": sum(value > 1 for value in windows),
            "gt_3d": sum(value > 3 for value in windows),
            "gt_5d": sum(value > 5 for value in windows),
        })
    return complete, summary_rows


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    headers = require_user_agent()
    session = requests.Session()
    ticker_payload = fetch_json(session, "https://www.sec.gov/files/company_tickers.json", headers)
    ticker_to_cik = {value["ticker"]: value["cik_str"] for value in ticker_payload.values()}
    ciks = {ticker: ticker_to_cik[ticker] for ticker in TICKERS}
    ciks.update(NONTRADED)

    all_events = []
    all_exclusions = {}
    for ticker, cik in ciks.items():
        print(f"Fetching and classifying {ticker}...", flush=True)
        payload = fetch_json(
            session,
            f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json",
            headers,
        )
        events, exclusions = candidate_events(
            ticker, cik, payload["filings"]["recent"], session, headers
        )
        all_events.extend(events)
        for quarter, reasons in exclusions.items():
            all_exclusions.setdefault((ticker, quarter), []).extend(reasons)

    rows = sorted(
        select_first_events(all_events, all_exclusions),
        key=lambda row: (row["quarter"], row["first_results_timestamp_utc"], row["ticker"]),
    )
    fields = [
        "ticker", "cik", "quarter", "period_end", "first_results_timestamp_utc",
        "first_results_timestamp_et", "market_session", "event_type", "accession", "source_url",
        "verification_status", "exclusion_reason",
    ]
    write_csv(OUTPUT, rows, fields)
    complete, summary = build_summary(rows)
    write_csv(SUMMARY_OUTPUT, summary, list(summary[0]) if summary else ["quarter"])

    print("\n=== VERIFIED FIRST RESULTS ORDER ===")
    for quarter in sorted({row["quarter"] for row in rows}):
        ordered = [row for row in rows if row["quarter"] == quarter]
        print(quarter, " -> ".join(
            f"{row['ticker']}({row['first_results_timestamp_utc'][5:10]})" for row in ordered
        ))
    print(f"\nComplete listed quarters used for windows: {complete}")
    for row in summary:
        print(row)
    print(f"\nWrote {OUTPUT} and {SUMMARY_OUTPUT}")


if __name__ == "__main__":
    main()
