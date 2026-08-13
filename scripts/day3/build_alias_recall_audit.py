#!/usr/bin/env python3
"""Create a blind alias-recall audit for 30 random ARCC borrowers."""

import argparse
import json
import random
import sys
from difflib import SequenceMatcher
from pathlib import Path

DAY2 = Path(__file__).resolve().parents[1] / "day2"
sys.path.insert(0, str(DAY2))

from common import SEED, canonical_json, read_csv, sha256_bytes, sha256_file, write_csv, write_json  # noqa: E402


DEFAULT_INPUT = Path("/private/tmp/finance-day3-sec-cache/bdc_facilities_agg.csv")
DEFAULT_OUTPUT = Path("data/day3/alias_recall_audit.csv")
DEFAULT_METADATA = Path("data/day3/alias_recall_audit_meta.json")
TARGET_FUNDS = {"OBDC", "NMFC"}
GENERIC_TOKENS = {
    "and", "the", "parent", "intermediate", "holdco", "topco", "bidco",
    "buyer", "purchaser", "borrower", "acquisition", "investment", "investors",
    "partners", "management", "services", "solutions", "company", "group",
    "stock", "units", "class", "series", "member", "corporation", "corp",
}

FIELDS = [
    "sample_borrower_id", "period_end", "arcc_borrower_norm", "arcc_facility_id",
    "arcc_identifier", "arcc_facility_type", "arcc_lien", "arcc_currency",
    "arcc_reference_rate", "arcc_spread", "arcc_maturity", "arcc_funded_status",
    "target_ticker", "target_borrower_norm", "target_facility_id", "target_identifier",
    "target_facility_type", "target_lien", "target_currency", "target_reference_rate",
    "target_spread", "target_maturity", "target_funded_status", "exact_borrower_block",
    "substring_match", "sequence_similarity", "token_jaccard", "shared_long_tokens",
    "manual_same_borrower", "manual_same_facility", "review_notes",
]


def tokens(value):
    return {
        token for token in (value or "").split()
        if len(token) >= 4 and token not in GENERIC_TOKENS
    }


def similarity(left, right):
    left = left or ""
    right = right or ""
    left_tokens, right_tokens = tokens(left), tokens(right)
    union = left_tokens | right_tokens
    intersection = left_tokens & right_tokens
    sequence = SequenceMatcher(None, left, right).ratio()
    jaccard = len(intersection) / len(union) if union else 0.0
    substring = bool(left and right and (left in right or right in left))
    long_shared = sorted(token for token in intersection if len(token) >= 6)
    return substring, sequence, jaccard, long_shared


def is_alias_candidate(left, right):
    substring, sequence, jaccard, long_shared = similarity(left, right)
    return substring or sequence >= 0.72 or jaccard >= 0.50 or bool(long_shared)


def build(rows, period_end="2025-09-30", sample_size=30, seed=SEED):
    current = [row for row in rows if row["period_end"] == period_end and row["is_current_period"] == "True"]
    arcc = [row for row in current if row["ticker"] == "ARCC" and len(row["borrower_norm"]) >= 4]
    targets = [row for row in current if row["ticker"] in TARGET_FUNDS and len(row["borrower_norm"]) >= 4]
    borrowers = sorted({row["borrower_norm"] for row in arcc})
    if len(borrowers) < sample_size:
        raise RuntimeError(f"Need {sample_size} ARCC borrowers, found {len(borrowers)}")
    rng = random.Random(seed)
    sampled = sorted(rng.sample(borrowers, sample_size))
    output = []
    for borrower in sampled:
        source_rows = [row for row in arcc if row["borrower_norm"] == borrower]
        candidate_targets = [row for row in targets if is_alias_candidate(borrower, row["borrower_norm"])]
        if not candidate_targets:
            candidate_targets = [None]
        for source in source_rows:
            sample_id = "ALIAS_" + sha256_bytes(canonical_json([period_end, borrower]).encode("utf-8"))[:20]
            for target in candidate_targets:
                substring, sequence, jaccard, shared = similarity(borrower, target["borrower_norm"] if target else "")
                output.append({
                    "sample_borrower_id": sample_id,
                    "period_end": period_end,
                    "arcc_borrower_norm": borrower,
                    "arcc_facility_id": source["economic_facility_id"],
                    "arcc_identifier": source["investment_identifier"],
                    "arcc_facility_type": source["facility_type"],
                    "arcc_lien": source["lien"],
                    "arcc_currency": source["currency"],
                    "arcc_reference_rate": source["reference_rate"],
                    "arcc_spread": source["spread"],
                    "arcc_maturity": source["maturity"],
                    "arcc_funded_status": source["funded_status"],
                    "target_ticker": target["ticker"] if target else "",
                    "target_borrower_norm": target["borrower_norm"] if target else "",
                    "target_facility_id": target["economic_facility_id"] if target else "",
                    "target_identifier": target["investment_identifier"] if target else "",
                    "target_facility_type": target["facility_type"] if target else "",
                    "target_lien": target["lien"] if target else "",
                    "target_currency": target["currency"] if target else "",
                    "target_reference_rate": target["reference_rate"] if target else "",
                    "target_spread": target["spread"] if target else "",
                    "target_maturity": target["maturity"] if target else "",
                    "target_funded_status": target["funded_status"] if target else "",
                    "exact_borrower_block": str(bool(target and borrower == target["borrower_norm"])),
                    "substring_match": str(substring),
                    "sequence_similarity": f"{sequence:.6f}",
                    "token_jaccard": f"{jaccard:.6f}",
                    "shared_long_tokens": "|".join(shared),
                    "manual_same_borrower": "",
                    "manual_same_facility": "",
                    "review_notes": "",
                })
    output.sort(key=lambda row: (row["sample_borrower_id"], row["arcc_facility_id"], row["target_ticker"], row["target_facility_id"]))
    return output, sampled


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--period-end", default="2025-09-30")
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    output, borrowers = build(read_csv(args.input), args.period_end, args.sample_size, args.seed)
    write_csv(args.output, output, FIELDS)
    metadata = {
        "seed": args.seed,
        "period_end": args.period_end,
        "sampled_borrower_count": len(borrowers),
        "exported_review_rows": len(output),
        "target_funds": sorted(TARGET_FUNDS),
        "aggregated_input_sha256": sha256_file(args.input),
        "sampled_borrower_ids_sha256": sha256_bytes(canonical_json(borrowers).encode("utf-8")),
        "export_sha256": sha256_file(args.output),
        "outcome_columns_used": [],
        "manual_labels_entered": False,
        "sampled_borrowers": borrowers,
    }
    write_json(args.metadata, metadata)
    print(json.dumps({key: value for key, value in metadata.items() if key != "sampled_borrowers"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
