#!/usr/bin/env python3
"""Write the frozen Day 5 result report without changing calculations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def display(value):
    return value if value is not None else "not calculated (frozen missing-mark rule)"


def layer_lines(title: str, layer: dict, frozen_summary: dict, supporting: bool = False) -> str:
    primary = layer.get("primary", {})
    criteria = primary.get("criteria", {})
    power = layer.get("power_guard", {})
    attrition = layer.get("attrition_flow", {})
    prefix = "- label: `secondary_supporting`\n- cannot modify primary status: `true`\n" if supporting else f"- final primary status: `{layer.get('status')}`\n"
    criteria_text = json.dumps(criteria, sort_keys=True) if criteria else "not evaluated"
    all_six = all(criteria.values()) if criteria else "not evaluated"
    return f"""### {title}

{prefix}- attrition: `{json.dumps(attrition, sort_keys=True)}`
- structurally continuing observations/clusters/borrowers: {frozen_summary['continuing_observations']} / {frozen_summary['continuing_source_event_clusters']} / {frozen_summary['continuing_unique_borrowers']}
- continuing rows with complete marks: {layer.get('continuing_rows_with_complete_marks')}
- continuing rows missing required marks: {layer.get('continuing_rows_missing_marks')}
- complete-mark continuing clusters: {layer.get('independent_continuing_clusters_with_complete_marks')}
- primary test run: `{layer.get('primary_test_run')}`
- power guard: `{power.get('status') or 'not evaluated after data-quality stop'}`
- cluster MAE B0: {display(primary.get('cluster_level_mae_b0'))}
- cluster MAE ShadowNAV: {display(primary.get('cluster_level_mae_sn'))}
- mean paired error difference: {display(primary.get('mean_paired_error_difference'))}
- relative MAE improvement: {display(primary.get('relative_mae_improvement'))}
- borrower-clustered permutation p: {display(primary.get('borrower_clustered_one_sided_sign_flip_permutation_p'))}
- borrower bootstrap 95%: {display(primary.get('borrower_cluster_bootstrap_95'))}
- leave-one-borrower-out: {display(layer.get('leave_one_borrower_out'))}
- period direction: {display(layer.get('period_direction'))}
- six criteria: {criteria_text}
- all six criteria true: `{all_six}`
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("data/day5/day5_replication_results.json"))
    parser.add_argument("--day4", type=Path, default=Path("data/day4/confirmatory_results.json"))
    parser.add_argument("--structural-freeze", type=Path, default=Path("data/day5/day5_structural_mapping_freeze.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/DAY5_REPLICATION_RESULTS.md"))
    args = parser.parse_args()
    result = json.loads(args.results.read_text())
    day4 = json.loads(args.day4.read_text())
    structural = json.loads(args.structural_freeze.read_text())
    strict = result["primary_strict"]
    supporting = result["secondary_supporting"]
    day4_primary = day4["primary"]
    text = f"""# Day 5 ShadowNAV replication results

Status: **{result['status']}**

The top-level status is determined only by the frozen STRICT new-borrower layer. It remains `underpowered_inconclusive` unless a stricter data-quality condition applies. The SUPPORTING new-fund layer is descriptive secondary evidence and cannot alter that status. No threshold, formula, layer membership, or human label was changed after freeze.

{layer_lines('Primary STRICT', strict, structural['strict'])}
The STRICT layer had already failed the frozen power guards because it has {structural['strict']['continuing_source_event_clusters']} continuing clusters (<25) and {structural['strict']['continuing_unique_borrowers']} continuing borrowers (<15). The two missing continuing marks trigger the stricter `data_quality_inconclusive` rule before any primary statistic is calculated.

{layer_lines('Secondary SUPPORTING', supporting, structural['supporting'], True)}
### Frozen Day 4 comparison — descriptive only

- Day 4 status: `{day4['status']}`
- cluster MAE B0: {day4_primary['cluster_level_mae_b0']}
- cluster MAE ShadowNAV: {day4_primary['cluster_level_mae_sn']}
- relative improvement: {day4_primary['relative_mae_improvement']}
- borrower-clustered permutation p: {day4_primary['borrower_clustered_one_sided_sign_flip_permutation_p']}
- borrower bootstrap 95%: `{json.dumps(day4_primary['borrower_cluster_bootstrap_95'], sort_keys=True)}`

Day 4 and Day 5 are not pooled. The comparison changes no decision rule.
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
