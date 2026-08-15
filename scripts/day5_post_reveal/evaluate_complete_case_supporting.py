#!/usr/bin/env python3
"""POST-REVEAL EXPLORATORY complete-case Day 5 diagnostics only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
DAY4_LOGIC = ROOT / "scripts/day4/evaluate_confirmatory_shadow_nav.py"
DAY4_LOGIC_SHA256 = "bcea297f43603316d4d3bc5fef9762bc2749eaddf36a3253222af66e8f132615"
PROTECTED = {
    "data/day5/day5_revealed_replication_outcomes.csv": "24b8b38d214580a17ea6ba6b1d2a2666d422f65d0d3f6a6bca3bd2bc5cae20ee",
    "data/day5/day5_structural_mapping_consensus.csv": "44cacbe1fd93b030a51e1e4a9bac270c746a0baef6558372fab384221a50365e",
    "data/day5/day5_strict_included_sample.csv": "a42c462a83d960ed241fc48d91b89035a7cd0be44aeca0dcac5d20453b5719dd",
    "data/day5/day5_supporting_included_sample.csv": "d4890bcbce1f8880cb56ca9ffe86071d3514064d4ff8488c685ef5f3cb62b50f",
    "data/day5/day5_event_review_human_consensus.csv": "aef9a7d0e5fc89ef9e6d019f0ea0f1f09495089fcad74590e4747b4e27c2902b",
    "docs/research/DAY5_REPLICATION_PREREGISTRATION.md": "909b4068e335cedbe1c819ed47c0e35ffbd6f0ebc9b8bd89ad8f99365a39f1fb",
}
REQUIRED_MARKS = ("target_prior_mark", "source_prior_mark", "source_current_mark", "target_current_mark")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def frozen_logic():
    if sha256_file(DAY4_LOGIC) != DAY4_LOGIC_SHA256:
        raise RuntimeError("Frozen Day 4 statistical logic changed")
    spec = importlib.util.spec_from_file_location("day4_frozen_diagnostic", DAY4_LOGIC)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen Day 4 logic")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def concentration(clusters: list[dict], field: str) -> dict:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in clusters:
        if field == "fund_pair":
            key = f"{row['source_ticker']}→{','.join(row['target_tickers'])}"
        else:
            key = str(row[field])
        groups[key].append(row["mean_paired_error_difference"])
    all_values = [value for values in groups.values() for value in values]
    group_sums = {key: sum(values) for key, values in groups.items()}
    abs_total = sum(abs(value) for value in group_sums.values())
    details = {}
    for key, values in sorted(groups.items()):
        remaining = [value for other, other_values in groups.items() if other != key for value in other_values]
        details[key] = {
            "clusters": len(values),
            "mean_paired_difference": mean(values),
            "signed_sum": sum(values),
            "absolute_group_contribution_share": None if abs_total == 0 else abs(sum(values)) / abs_total,
            "leave_group_out_mean_paired_difference": None if not remaining else mean(remaining),
        }
    ranked = sorted(details, key=lambda key: abs(details[key]["signed_sum"]), reverse=True)
    leave_values = [value["leave_group_out_mean_paired_difference"] for value in details.values() if value["leave_group_out_mean_paired_difference"] is not None]
    return {
        "group_count": len(groups),
        "overall_mean_paired_difference": mean(all_values),
        "largest_absolute_contributor": ranked[0] if ranked else None,
        "largest_absolute_contribution_share": details[ranked[0]]["absolute_group_contribution_share"] if ranked else None,
        "leave_one_group_out_min": min(leave_values) if leave_values else None,
        "leave_one_group_out_max": max(leave_values) if leave_values else None,
        "leave_one_group_out_all_negative": bool(leave_values) and all(value < 0 for value in leave_values),
        "groups": details,
    }


def diagnostic(module, rows: list[dict[str, str]], label: str) -> dict:
    core = module.evaluate_revealed_rows(rows)
    errors, missing = module.continuing_errors(rows)
    clusters = module.aggregate_source_event_clusters(errors)
    if missing:
        raise RuntimeError("Complete-case diagnostic contains missing marks")
    loo = core["leave_one_borrower_out"]
    return {
        "label": label,
        "cannot_change_official_day5_status": True,
        "observations": len(rows),
        "independent_clusters": len(clusters),
        "unique_borrowers": len({row["borrower_norm"] for row in rows}),
        "frozen_day4_core_output": core,
        "leave_one_borrower_out_min": min(loo.values()) if loo else None,
        "leave_one_borrower_out_max": max(loo.values()) if loo else None,
        "leave_one_borrower_out_all_negative": bool(loo) and all(value < 0 for value in loo.values()),
        "concentration": {
            "borrower": concentration(clusters, "borrower_norm"),
            "period": concentration(clusters, "report_period_label"),
            "fund_pair": concentration(clusters, "fund_pair"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=Path("data/day5_post_reveal/complete_case_supporting_results.json"))
    args = parser.parse_args()
    repo = args.repo.resolve()
    for relative, expected in PROTECTED.items():
        if sha256_file(repo / relative) != expected:
            raise RuntimeError(f"Protected Day 5 file changed: {relative}")
    supporting_sample = read_csv(repo / "data/day5/day5_supporting_included_sample.csv")
    strict_sample = read_csv(repo / "data/day5/day5_strict_included_sample.csv")
    support_ids = [row["review_observation_id"] for row in supporting_sample]
    strict_ids = [row["review_observation_id"] for row in strict_sample]
    event = {row["review_observation_id"]: row for row in read_csv(repo / "data/day5/day5_event_review_human_consensus.csv")}
    structure = {row["review_observation_id"]: row for row in read_csv(repo / "data/day5/day5_structural_mapping_consensus.csv")}
    outcomes = {row["review_observation_id"]: row for row in read_csv(repo / "data/day5/day5_revealed_replication_outcomes.csv")}
    if set(outcomes) != set(support_ids) or not set(strict_ids) <= set(support_ids):
        raise RuntimeError("Frozen layer ID relationship changed")
    if any(event[value]["include_for_replication"] != "yes" for value in support_ids):
        raise RuntimeError("Frozen SUPPORTING sample contains non-included event review")
    complete_support = [
        outcomes[value] for value in support_ids
        if structure[value]["position_status"] == "continuing"
        and all(outcomes[value][field] for field in REQUIRED_MARKS)
    ]
    complete_strict = [outcomes[value] for value in strict_ids if value in {row["review_observation_id"] for row in complete_support}]
    if len(complete_support) != 45 or len(complete_strict) != 12:
        raise RuntimeError("Frozen complete-case counts changed")
    module = frozen_logic()
    payload = {
        "analysis_label": "POST_REVEAL_EXPLORATORY_COMPLETE_CASE_SUPPORTING",
        "official_day5_status": "data_quality_inconclusive",
        "cannot_change_official_day5_status": True,
        "selection_rule": "frozen membership AND event include=yes AND structural continuing AND all four frozen marks present",
        "no_additional_filtering_or_tuning": True,
        "protected_input_sha256": PROTECTED,
        "frozen_day4_logic_sha256": DAY4_LOGIC_SHA256,
        "primary_strict_complete_case": diagnostic(module, complete_strict, "POST_REVEAL_EXPLORATORY_STRICT_UNDERPOWERED"),
        "secondary_supporting_complete_case": diagnostic(module, complete_support, "POST_REVEAL_EXPLORATORY_COMPLETE_CASE_SUPPORTING"),
    }
    destination = repo / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(destination), "sha256": sha256_file(destination)}, indent=2))


if __name__ == "__main__":
    main()
