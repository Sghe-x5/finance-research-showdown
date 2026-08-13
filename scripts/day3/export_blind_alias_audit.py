#!/usr/bin/env python3
"""Create a debt-only blind alias audit; keep every similarity score private."""

import argparse
import json
import random
import sys
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
DAY3 = Path(__file__).resolve().parent
sys.path.insert(0, str(DAY2))
sys.path.insert(0, str(DAY3))

from common import SEED, canonical_json, read_csv, sha256_bytes, sha256_file, stable_id, write_csv, write_json  # noqa: E402
from build_alias_recall_audit import TARGET_FUNDS, is_alias_candidate, similarity  # noqa: E402
from export_blind_match_benchmark import SEEN_DEVELOPMENT_BORROWERS  # noqa: E402


DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_OUTPUT = Path("data/day3/blind_alias_candidates.csv")
DEFAULT_META = Path("data/day3/blind_alias_candidates_meta.json")
DEFAULT_PRIVATE_KEY = Path("private/day3/blind_alias_key.json")

BLIND_FIELDS = [
    "blind_alias_id", "period_end", "source_ticker", "source_borrower_norm",
    "source_identifier", "source_facility_type", "source_lien", "source_currency",
    "source_reference_rate", "source_spread", "source_maturity", "source_funded_status",
    "candidate_ticker", "candidate_borrower_norm", "candidate_identifier",
    "candidate_facility_type", "candidate_lien", "candidate_currency",
    "candidate_reference_rate", "candidate_spread", "candidate_maturity",
    "candidate_funded_status", "manual_same_borrower", "manual_same_facility",
    "review_notes",
]


def excluded(value):
    aliases = {alias for values in SEEN_DEVELOPMENT_BORROWERS.values() for alias in values}
    return value in aliases


def build(rows, period_end="2025-09-30", sample_size=30, seed=SEED):
    current = [
        row for row in rows
        if row["period_end"] == period_end and row["is_current_period"] == "True"
        and row["debt_equity"] == "debt" and not excluded(row["borrower_norm"])
    ]
    sources = [row for row in current if row["ticker"] == "ARCC" and len(row["borrower_norm"]) >= 4]
    targets = [row for row in current if row["ticker"] in TARGET_FUNDS and len(row["borrower_norm"]) >= 4]
    borrowers = sorted({row["borrower_norm"] for row in sources})
    if len(borrowers) < sample_size:
        raise RuntimeError(f"Need {sample_size} debt borrowers, found {len(borrowers)}")
    rng = random.Random(seed)
    sampled = sorted(rng.sample(borrowers, sample_size))
    paired = []
    for borrower in sampled:
        for source in (row for row in sources if row["borrower_norm"] == borrower):
            candidates = []
            for target in targets:
                if not is_alias_candidate(borrower, target["borrower_norm"]):
                    continue
                substring, sequence, jaccard, shared = similarity(borrower, target["borrower_norm"])
                candidates.append((sequence, jaccard, len(shared), substring, target, shared))
            candidates.sort(key=lambda item: (-item[0], -item[1], -item[2], item[4]["economic_facility_id"]))
            if not candidates:
                paired.append((source, None, (False, 0.0, 0.0, [])))
            else:
                for sequence, jaccard, _, substring, target, shared in candidates[:12]:
                    paired.append((source, target, (substring, sequence, jaccard, shared)))
    rng.shuffle(paired)
    blind = []
    private = []
    for position, (source, target, scores) in enumerate(paired):
        blind_id = "BA2_" + stable_id(seed, position, source["economic_facility_id"], target["economic_facility_id"] if target else "NONE", length=22)
        blind.append({
            "blind_alias_id": blind_id,
            "period_end": period_end,
            "source_ticker": source["ticker"],
            "source_borrower_norm": source["borrower_norm"],
            "source_identifier": source["investment_identifier"],
            "source_facility_type": source["facility_type"],
            "source_lien": source["lien"],
            "source_currency": source["currency"],
            "source_reference_rate": source["reference_rate"],
            "source_spread": source["spread"],
            "source_maturity": source["maturity"],
            "source_funded_status": source["funded_status"],
            "candidate_ticker": target["ticker"] if target else "",
            "candidate_borrower_norm": target["borrower_norm"] if target else "",
            "candidate_identifier": target["investment_identifier"] if target else "",
            "candidate_facility_type": target["facility_type"] if target else "",
            "candidate_lien": target["lien"] if target else "",
            "candidate_currency": target["currency"] if target else "",
            "candidate_reference_rate": target["reference_rate"] if target else "",
            "candidate_spread": target["spread"] if target else "",
            "candidate_maturity": target["maturity"] if target else "",
            "candidate_funded_status": target["funded_status"] if target else "",
            "manual_same_borrower": "",
            "manual_same_facility": "",
            "review_notes": "",
        })
        substring, sequence, jaccard, shared = scores
        private.append({
            "blind_alias_id": blind_id,
            "source_facility_id": source["economic_facility_id"],
            "candidate_facility_id": target["economic_facility_id"] if target else None,
            "exact_borrower_block": bool(target and source["borrower_norm"] == target["borrower_norm"]),
            "substring_match": substring,
            "sequence_similarity": sequence,
            "token_jaccard": jaccard,
            "shared_long_tokens": shared,
        })
    return blind, private, sampled


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_META)
    parser.add_argument("--private-key", type=Path, default=DEFAULT_PRIVATE_KEY)
    parser.add_argument("--period-end", default="2025-09-30")
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    blind, private_rows, borrowers = build(read_csv(args.input), args.period_end, args.sample_size, args.seed)
    write_csv(args.output, blind, BLIND_FIELDS)
    args.private_key.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.private_key, {"seed": args.seed, "rows": private_rows})
    metadata = {
        "design_status": "ready_for_blind_labeling",
        "seed": args.seed,
        "period_end": args.period_end,
        "primary_audit_debt_facilities_only": True,
        "seen_borrowers_excluded_all_periods": True,
        "sampled_borrower_count": len(borrowers),
        "blind_candidate_row_count": len(blind),
        "candidate_order_randomized": True,
        "similarity_scores_in_blind_file": False,
        "manual_labels_entered": False,
        "aggregated_input_sha256": sha256_file(args.input),
        "sampled_borrower_ids_sha256": sha256_bytes(canonical_json(borrowers).encode("utf-8")),
        "blind_file_sha256": sha256_file(args.output),
        "private_key_sha256": sha256_file(args.private_key),
        "private_key_tracked_by_git": False,
    }
    write_json(args.metadata, metadata)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
