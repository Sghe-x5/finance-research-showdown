import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTED = {
    "data/day5/day5_replication_results.json": "cd6c1af0424fc73ae197b9c3377ebc366486af2cb3252f06906a4f2337b84032",
    "docs/research/DAY5_REPLICATION_RESULTS.md": "43eb5d45525830067fe41bcc247f3f3a1f224f5d84e8cb25430ea2431fc2863d",
    "data/day5/day5_reveal_authorization.json": "0da4eb36f9ec900db9b664e529c219c022ba2b4a5dc9cc99bf285d5117778861",
    "data/day5/day5_revealed_replication_outcomes.csv": "24b8b38d214580a17ea6ba6b1d2a2666d422f65d0d3f6a6bca3bd2bc5cae20ee",
    "data/day5/day5_structural_mapping_consensus.csv": "44cacbe1fd93b030a51e1e4a9bac270c746a0baef6558372fab384221a50365e",
    "data/day5/day5_strict_included_sample.csv": "a42c462a83d960ed241fc48d91b89035a7cd0be44aeca0dcac5d20453b5719dd",
    "data/day5/day5_supporting_included_sample.csv": "d4890bcbce1f8880cb56ca9ffe86071d3514064d4ff8488c685ef5f3cb62b50f",
    "docs/research/DAY5_REPLICATION_PREREGISTRATION.md": "909b4068e335cedbe1c819ed47c0e35ffbd6f0ebc9b8bd89ad8f99365a39f1fb",
    "scripts/day5/evaluate_day5_replication.py": "ecc92fb08bbf18781b88a24ba44a2d2c152eb9ac2d8d62d582606b5091f73ac4",
}


def test_official_day5_files_are_immutable():
    for relative, expected in PROTECTED.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_missing_mark_audit_has_exact_source_absent_rows():
    with (ROOT / "data/day5_post_reveal/missing_mark_root_cause.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert {r["review_observation_id"] for r in rows} == {
        "D5EV_4bcc43807ee299de5de2ca0a", "D5EV_f438ca82f7a27e794a1837a9"
    }
    assert all(r["target_prior_missing_classification"] == "source_absent" for r in rows)
    assert all(r["target_current_missing_classification"] == "source_absent" for r in rows)
    assert all(float(r["target_prior_official_principal"]) == 0 for r in rows)
    assert all(float(r["target_current_official_principal"]) == 0 for r in rows)
    assert all(not r["recoverable_diagnostic_value"] for r in rows)


def test_complete_case_diagnostic_is_adverse_and_non_confirmatory():
    result = json.loads((ROOT / "data/day5_post_reveal/complete_case_supporting_results.json").read_text())
    supporting = result["secondary_supporting_complete_case"]
    strict = result["primary_strict_complete_case"]
    assert result["cannot_change_official_day5_status"] is True
    assert (supporting["observations"], supporting["independent_clusters"], supporting["unique_borrowers"]) == (45, 45, 22)
    assert (strict["observations"], strict["independent_clusters"], strict["unique_borrowers"]) == (12, 12, 8)
    for layer in (supporting, strict):
        primary = layer["frozen_day4_core_output"]["primary"]
        assert primary["cluster_level_mae_sn"] > primary["cluster_level_mae_b0"]
        assert primary["mean_paired_error_difference"] > 0
        assert not any(primary["criteria"].values())
        assert layer["leave_one_borrower_out_all_negative"] is False


def test_decision_memo_does_not_claim_profitability():
    text = (ROOT / "docs/research/SHADOWNAV_GO_NO_GO_FOR_TRADABILITY.md").read_text()
    assert "Decision: **STOP_SHADOWNAV**" in text
    assert "No profitability claim is made." in text
    assert "facility-mark predictive signal" in text
    assert "tradable equity alpha" in text
