import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/day5/build_replication_feasibility.py"
OUTPUT = ROOT / "data/day5/replication_universe_candidates.csv"
SUMMARY = ROOT / "data/day5/replication_feasibility_summary.json"

spec = importlib.util.spec_from_file_location("day5_feasibility", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def rows():
    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_locked_hypothesis_and_no_result_calculation():
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert payload["status"] == "outcome_blind_replication_feasibility_only"
    assert payload["day4_result_status_carried_forward_without_reinterpretation"] == "exploratory_inconclusive"
    assert payload["locked_hypothesis"]["day4_six_decision_criteria_unchanged"] is True
    assert payload["prohibitions"]["target_numeric_outcomes_materialized"] is False
    assert payload["prohibitions"]["predictions_materialized"] is False
    assert payload["prohibitions"]["errors_calculated"] is False
    assert payload["prohibitions"]["inferential_statistics_calculated"] is False
    assert payload["prohibitions"]["sample_frozen"] is False


def test_output_has_no_numeric_target_or_prediction_fields():
    with OUTPUT.open(newline="", encoding="utf-8") as handle:
        headers = set(csv.DictReader(handle).fieldnames or [])
    assert not (headers & module.FORBIDDEN_OUTPUT_COLUMNS)
    assert not any("fair_value" in name.lower() for name in headers)
    assert not any("prediction" in name.lower() for name in headers)
    assert not any("error" in name.lower() for name in headers)


def test_strict_universe_is_new_source_and_clean_borrower():
    strict = [row for row in rows() if row["strict_new_borrower_universe"] == "True"]
    assert strict
    assert all(row["source_is_new_fund"] == "True" for row in strict)
    assert all(row["manager_relationship"] == "cross_manager" for row in strict)
    assert all(row["overlap_day4_borrower"] == "False" for row in strict)
    assert all(row["overlap_day4_source_event_id"] == "False" for row in strict)
    assert all(row["overlap_development_borrower"] == "False" for row in strict)


def test_development_period_not_in_candidates():
    assert all(row["period_end"] != module.DEVELOPMENT_PERIOD for row in rows())


def test_duplicate_vote_audit_is_clear():
    payload = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert payload["duplicate_vote_audit"]["duplicate_identities"] == 0
    assert payload["duplicate_vote_audit"]["duplicate_rows"] == 0
    assert payload["duplicate_vote_audit"]["status"] == "clear"


def test_output_marks_all_candidates_for_human_review():
    assert all(row["requires_human_facility_review"] == "True" for row in rows())


def test_strict_same_facility_rejects_hard_conflict():
    base = {
        "borrower_norm": "sample borrower",
        "debt_equity": "debt",
        "facility_type": "term_loan",
        "lien": "first_lien",
        "currency": "USD",
        "reference_rate": "SOFR",
        "spread": "0.05",
        "maturity": "2028-01-15",
        "funded_status": "funded",
    }
    other = dict(base, lien="second_lien")
    assert module.strict_same_facility(base, other) is False
