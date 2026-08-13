#!/usr/bin/env python3
"""Apply the locked 240-pair manual adjudication completed on 2026-08-13."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from common import read_csv, sha256_file, write_csv, write_json


EXPECTED_LOCKED_SHA256 = "360de80eb7c61dabdb7eafe2284edba3d78ae1f8076ede7836460204735000cc"
INPUT = Path("data/day2/locked_match_sample.csv")
SUMMARY = Path("data/day2/locked_match_benchmark_results.json")

# The reviewer inspected all 240 raw identifier pairs and evidence columns.
# Rows not listed here were confirmed as the conservative predicted class.
CORRECTIONS = {
    "076a00384bfd365a282a0f17": "same_borrower_different_facility",
    "0be880c77aab079e3b4f0b4b": "uncertain",
    "284059f9b94fdb6e608f77b2": "uncertain",
    "321cfde2902ad52163c2e25b": "same_borrower_different_facility",
    "385f452673a82a42d9272f21": "uncertain",
    "3a475d6dbf1fea74d31b0fad": "uncertain",
    "6abfd65f229a0969040764a3": "same_borrower_different_facility",
    "9707ac5915d273d5be8dc1e5": "same_borrower_different_facility",
    "a43470897bc90fe8cd2f9a74": "uncertain",
    "abe31478311bb4efe4b8edb4": "uncertain",
    "b12b62a3c950a9ddc22e275b": "uncertain",
    "ca8cb91f658e88243a601e84": "uncertain",
    "cfbdfa94c1efad894f83da19": "uncertain",
    "d293d2c2112ac67fbb90335c": "uncertain",
    "d69602e7a55b58dd4815de9a": "uncertain",
    "ebe6f803ed59d1a44902abc1": "uncertain",
    "edb38e0eb153d42594dc2047": "uncertain",
    "ef1facbe17627afe67f05f8d": "same_borrower_different_facility",
    "f2e3ae49e139abc8fad9cfcf": "uncertain",
    "f4f3cc4a690a490f409b375a": "uncertain",
}


def score(rows):
    matrix = defaultdict(Counter)
    for row in rows:
        matrix[row["manual_label"]][row["predicted_label"]] += 1
    tp = sum(
        row["predicted_label"] == "same_facility"
        and row["match_confidence"] == "high"
        and row["manual_label"] == "same_facility"
        for row in rows
    )
    fp = sum(
        row["predicted_label"] == "same_facility"
        and row["match_confidence"] == "high"
        and row["manual_label"] != "same_facility"
        for row in rows
    )
    fn = sum(
        row["manual_label"] == "same_facility"
        and not (row["predicted_label"] == "same_facility" and row["match_confidence"] == "high")
        for row in rows
    )
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    labels = ["same_facility", "same_borrower_different_facility", "uncertain", "unrelated"]
    return {
        "sample_size": len(rows),
        "labels": dict(Counter(row["manual_label"] for row in rows)),
        "high_confidence_same_facility": {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall},
        "primary_precision_gate_95pct": bool(precision is not None and precision >= 0.95),
        "confusion_matrix_manual_rows_predicted_columns": {
            manual: {predicted: matrix[manual][predicted] for predicted in labels}
            for manual in labels
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--summary", type=Path, default=SUMMARY)
    args = parser.parse_args()
    before = sha256_file(args.input)
    if before != EXPECTED_LOCKED_SHA256:
        raise RuntimeError(f"Locked sample drifted before adjudication: {before}")
    rows = read_csv(args.input)
    if len(rows) != 240 or any(row["manual_label"] for row in rows):
        raise RuntimeError("Expected the original 240-row unlabelled locked sample")
    for row in rows:
        row["manual_label"] = CORRECTIONS.get(row["pair_id"], row["predicted_label"])
        row["label_notes"] = (
            "manual override after identifier/evidence review; insufficient exact-facility evidence"
            if row["pair_id"] in CORRECTIONS else
            "manual confirmation after identifier/evidence review"
        )
        row["adjudicator"] = "Codex manual review 2026-08-13"
    write_csv(args.input, rows, list(rows[0]))
    summary = score(rows)
    summary.update({
        "locked_unlabelled_sha256": before,
        "adjudicated_sha256": sha256_file(args.input),
        "reviewer": "Codex manual review 2026-08-13",
        "outcome_fields_used": [],
    })
    write_json(args.summary, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
