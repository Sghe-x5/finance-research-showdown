#!/usr/bin/env python3
"""Build the canonical BDC manager map and pre-reveal overlap audit."""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import read_csv, sha256_file, write_csv, write_json  # noqa: E402


MANAGERS = {
    "ARCC": ("Ares Management", "Ares Capital Management LLC"),
    "ASIF": ("Ares Management", "Ares Capital Management LLC"),
    "BBDC": ("Barings", "Barings LLC"),
    "BCRED": ("Blackstone Credit & Insurance", "Blackstone Private Credit Strategies LLC; Blackstone Credit BDC Advisors LLC (sub-adviser)"),
    "BXSL": ("Blackstone Credit & Insurance", "Blackstone Private Credit Strategies LLC; Blackstone Credit BDC Advisors LLC (sub-adviser)"),
    "CGBD": ("Carlyle", "Carlyle Global Credit Investment Management L.L.C."),
    "FSK": ("FS/KKR", "FS/KKR Advisor, LLC"),
    "GBDC": ("Golub Capital", "GC Advisors LLC"),
    "GSBD": ("Goldman Sachs Asset Management", "Goldman Sachs Asset Management, L.P."),
    "HPS": ("HPS Investment Partners", "HPS Advisors, LLC"),
    "HTGC": ("Hercules Capital", "internally managed"),
    "MAIN": ("Main Street Capital", "internally managed"),
    "MFIC": ("Apollo Global Management", "Apollo Investment Management, L.P."),
    "NMFC": ("New Mountain Capital", "New Mountain Finance Advisers BDC, L.L.C."),
    "OBDC": ("Blue Owl Credit", "Blue Owl Credit Advisors LLC"),
    "OCIC": ("Blue Owl Credit", "Blue Owl Credit Advisors LLC"),
    "OCSL": ("Oaktree Capital Management", "Oaktree Fund Advisors, LLC"),
    "PSEC": ("Prospect Capital Management", "Prospect Capital Management LLC"),
    "TSLX": ("Sixth Street", "Sixth Street Specialty Lending Advisers, LLC"),
}

MAP_FIELDS = [
    "ticker", "cik", "canonical_manager", "legal_adviser", "listed_status",
    "evidence_source", "evidence_period", "confidence",
]
AUDIT_FIELDS = [
    "layer", "report_period_label", "source_ticker", "target_ticker",
    "source_manager", "target_manager", "manager_relationship",
    "observation_count", "unique_source_facilities", "unique_borrowers",
]


def build_manager_map(reporting_rows):
    identities = {}
    evidence = {}
    for row in reporting_rows:
        identities[row["ticker"]] = (row["cik"], row["listed_status"])
        if row["report_period_label"] == "2024Q4":
            evidence[row["ticker"]] = row["periodic_filing_url"]
    if set(identities) != set(MANAGERS):
        raise RuntimeError(f"Manager-map universe mismatch: {sorted(set(identities) ^ set(MANAGERS))}")
    return [
        {
            "ticker": ticker,
            "cik": identities[ticker][0],
            "canonical_manager": MANAGERS[ticker][0],
            "legal_adviser": MANAGERS[ticker][1],
            "listed_status": identities[ticker][1],
            "evidence_source": evidence[ticker],
            "evidence_period": "2024Q4 official SEC 10-K",
            "confidence": "high",
        }
        for ticker in sorted(MANAGERS)
    ]


def manager(ticker):
    if ticker not in MANAGERS:
        raise KeyError(f"No manager for {ticker}")
    return MANAGERS[ticker][0]


def add_record(records, layer, period, left, right, facility_id, borrower):
    relationship = "same_manager" if manager(left) == manager(right) else "cross_manager"
    records.append({
        "layer": layer,
        "period": period,
        "left": left,
        "right": right,
        "left_manager": manager(left),
        "right_manager": manager(right),
        "relationship": relationship,
        "facility_id": facility_id,
        "borrower": borrower,
    })


def build_records(candidates, blind, eligible):
    records = []
    for row in candidates:
        add_record(
            records, "facility_candidate_universe", row["quarter"],
            row["left_ticker"], row["right_ticker"], row["left_row_id"],
            row["left_borrower_norm"],
        )
    for row in blind:
        add_record(
            records, "blind_facility_sample_v3", row["quarter"],
            row["left_ticker"], row["right_ticker"], row["blind_pair_id"],
            row["left_borrower_norm"],
        )
    for row in eligible:
        add_record(
            records, "eligible_pre_reveal", row["report_period_label"],
            row["source_ticker"], row["target_ticker"], row["source_facility_id"],
            row["borrower_norm"],
        )
        if (
            row["movement_eligible"] == "True"
            and row["report_period_label"] != "2025Q3"
            and row["development_borrower_excluded"] == "False"
        ):
            add_record(
                records, "untouched_movement_facilities", row["report_period_label"],
                row["source_ticker"], row["target_ticker"], row["source_facility_id"],
                row["borrower_norm"],
            )
    return records


def grouped_rows(records):
    groups = defaultdict(list)
    for row in records:
        key = (row["layer"], row["period"], row["left"], row["right"], row["relationship"])
        groups[key].append(row)
    output = []
    for key, rows in sorted(groups.items()):
        layer, period, left, right, relationship = key
        output.append({
            "layer": layer,
            "report_period_label": period,
            "source_ticker": left,
            "target_ticker": right,
            "source_manager": manager(left),
            "target_manager": manager(right),
            "manager_relationship": relationship,
            "observation_count": len(rows),
            "unique_source_facilities": len({row["facility_id"] for row in rows}),
            "unique_borrowers": len({row["borrower"] for row in rows}),
        })
    return output


def layer_summary(records, layer):
    rows = [row for row in records if row["layer"] == layer]
    by_relationship = Counter(row["relationship"] for row in rows)
    facilities = {
        relationship: len({(row["period"], row["facility_id"]) for row in rows if row["relationship"] == relationship})
        for relationship in ("same_manager", "cross_manager")
    }
    borrowers = {
        relationship: len({row["borrower"] for row in rows if row["relationship"] == relationship})
        for relationship in ("same_manager", "cross_manager")
    }
    total = len(rows)
    return {
        "observations": total,
        "same_manager_count": by_relationship["same_manager"],
        "same_manager_share": 0 if not total else by_relationship["same_manager"] / total,
        "cross_manager_count": by_relationship["cross_manager"],
        "cross_manager_share": 0 if not total else by_relationship["cross_manager"] / total,
        "unique_source_facilities_by_relationship": facilities,
        "unique_borrowers_by_relationship": borrowers,
        "unique_source_managers": len({row["left_manager"] for row in rows}),
        "unique_target_managers": len({row["right_manager"] for row in rows}),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reporting-order", type=Path, default=Path("data/day3/reporting_order_extended.csv"))
    parser.add_argument("--candidates", type=Path, default=Path("/private/tmp/finance-day3-sec-cache/facility_candidates_lineage_v2.csv"))
    parser.add_argument("--blind", type=Path, default=Path("data/day3/blind_facility_pairs_v3.csv"))
    parser.add_argument("--eligible", type=Path, default=Path("data/day3/eligible_prefreeze_extended.csv"))
    parser.add_argument("--manager-map", type=Path, default=Path("data/day3/bdc_manager_map.csv"))
    parser.add_argument("--audit", type=Path, default=Path("data/day3/manager_overlap_audit.csv"))
    parser.add_argument("--summary", type=Path, default=Path("data/day3/manager_overlap_audit_summary.json"))
    args = parser.parse_args()

    reporting = read_csv(args.reporting_order)
    manager_rows = build_manager_map(reporting)
    candidates = read_csv(args.candidates)
    blind = read_csv(args.blind)
    eligible = read_csv(args.eligible)
    if any(row.get("manual_label") or row.get("label_notes") for row in blind):
        raise RuntimeError("Human labels are present in blind v3")
    if any(row.get("target_current_outcome_used_for_eligibility") != "False" for row in eligible):
        raise RuntimeError("Target-current outcome flag is not uniformly false")

    records = build_records(candidates, blind, eligible)
    write_csv(args.manager_map, manager_rows, MAP_FIELDS)
    write_csv(args.audit, grouped_rows(records), AUDIT_FIELDS)
    layers = [
        "facility_candidate_universe", "blind_facility_sample_v3",
        "eligible_pre_reveal", "untouched_movement_facilities",
    ]
    summaries = {layer: layer_summary(records, layer) for layer in layers}
    movement = [row for row in records if row["layer"] == "untouched_movement_facilities"]
    cross_facilities = len({
        (row["period"], row["facility_id"])
        for row in movement if row["relationship"] == "cross_manager"
    })
    by_period = {}
    for period in sorted({row["period"] for row in movement}):
        period_rows = [row for row in movement if row["period"] == period]
        by_period[period] = {
            "same_manager_observations": sum(row["relationship"] == "same_manager" for row in period_rows),
            "cross_manager_observations": sum(row["relationship"] == "cross_manager" for row in period_rows),
            "cross_manager_unique_source_facilities": len({
                row["facility_id"] for row in period_rows if row["relationship"] == "cross_manager"
            }),
        }
    pair_counts = Counter(
        (row["left_manager"], row["right_manager"], row["relationship"])
        for row in movement
    )
    summary = {
        "manager_map_rows": len(manager_rows),
        "official_evidence_only": True,
        "layers": summaries,
        "untouched_movement_by_period": by_period,
        "top_movement_manager_pairs": [
            {"source_manager": key[0], "target_manager": key[1], "relationship": key[2], "observations": count}
            for key, count in pair_counts.most_common()
        ],
        "cross_manager_untouched_movement_facilities": cross_facilities,
        "cross_manager_movement_guard": 20,
        "cross_manager_primary_preregistration_stratum_allowed": cross_facilities >= 20,
        "freeze_authorized": False,
        "target_current_outcomes_read": False,
        "hidden_matcher_strata_read": False,
        "human_labels_read": False,
        "input_hashes": {
            "reporting_order": sha256_file(args.reporting_order),
            "candidates": sha256_file(args.candidates),
            "blind": sha256_file(args.blind),
            "eligible": sha256_file(args.eligible),
        },
    }
    write_json(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
