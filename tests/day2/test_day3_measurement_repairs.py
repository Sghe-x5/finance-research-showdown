import json
from pathlib import Path

import pytest

from aggregate_facilities import aggregate, validate
from build_alias_recall_audit import build as build_alias_audit
from evaluate_nowcasts import verify_frozen_evaluator
from export_blind_match_benchmark import FORBIDDEN_SOURCE_FIELDS, SEEN_DEVELOPMENT_BORROWERS, export
from run_japan_valid_window_gate import END, START, monthly_periods


def raw_facility(**overrides):
    row = {
        "facility_row_id": "row-a", "archive_id": "2025q4", "adsh": "adsh-a",
        "accepted": "2025-10-24T12:00:00Z", "cik": "1", "ticker": "ARCC",
        "filer_name": "Ares", "form": "10-Q", "filed": "2025-10-24",
        "period_end": "2025-09-30", "observation_date": "2025-09-30",
        "investment_identifier": "Borrower First Lien Term Loan", "borrower_raw": "Borrower LLC",
        "borrower_norm": "borrower", "debt_equity": "debt", "facility_type": "term_loan",
        "lien": "first_lien", "currency": "USD", "reference_rate": "SOFR",
        "spread": "0.05", "total_interest_rate": "0.10", "pik_rate": "",
        "maturity": "2028-10-01", "funded_status": "funded", "acquisition_date": "2022-01-01",
        "principal": "100", "cost": "98", "fair_value": "99", "non_accrual": "False",
        "restructuring_flag": "False", "issuer_affiliation": "", "raw_provenance": "2025q4:1",
    }
    row.update(overrides)
    return row


def candidate(pair_id):
    row = {
        "pair_id": pair_id, "period_end": "2025-09-30", "quarter": "2025Q3",
        "left_ticker": "ARCC", "right_ticker": "OBDC", "left_adsh": "a", "right_adsh": "b",
        "left_identifier": "Loan A", "right_identifier": "Loan B",
        "left_borrower_norm": "borrower", "right_borrower_norm": "borrower",
        "left_debt_equity": "debt", "right_debt_equity": "debt",
        "left_facility_type": "term_loan", "right_facility_type": "term_loan",
        "left_lien": "first_lien", "right_lien": "first_lien",
        "left_currency": "USD", "right_currency": "USD",
        "left_reference_rate": "SOFR", "right_reference_rate": "SOFR",
        "left_spread": "0.05", "right_spread": "0.05",
        "left_maturity": "2028-10-01", "right_maturity": "2028-10-01",
        "left_funded_status": "funded", "right_funded_status": "funded",
        "left_acquisition_date": "2022-01-01", "right_acquisition_date": "2022-01-01",
    }
    row.update({field: "fixture" for field in FORBIDDEN_SOURCE_FIELDS})
    return row


def test_aggregation_sums_lots_but_separates_economic_facilities():
    lot_b = raw_facility(
        facility_row_id="row-b", investment_identifier="Borrower First Lien Term Loan tranche B",
        principal="50", cost="49", fair_value="48", raw_provenance="2025q4:2",
    )
    revolver = raw_facility(
        facility_row_id="row-c", investment_identifier="Borrower Revolver", facility_type="revolver",
        principal="25", cost="24", fair_value="23", raw_provenance="2025q4:3",
    )
    unfunded = raw_facility(
        facility_row_id="row-d", investment_identifier="Borrower Unfunded Revolver",
        facility_type="revolver", funded_status="unfunded", principal="10", cost="0", fair_value="0",
        raw_provenance="2025q4:4",
    )
    facilities, dropped = aggregate([raw_facility(), lot_b, revolver, unfunded])
    assert not dropped
    assert len(facilities) == 3
    term = next(row for row in facilities if row["facility_type"] == "term_loan")
    assert float(term["principal"]) == pytest.approx(150)
    assert float(term["fair_value"]) == pytest.approx(147)
    assert term["source_row_count"] == 2
    assert {row["funded_status"] for row in facilities if row["facility_type"] == "revolver"} == {"funded", "unfunded"}
    validate(facilities)


def test_aggregation_drops_unspecified_borrower_total():
    total = raw_facility(
        facility_row_id="row-total", investment_identifier="Borrower Total", principal="",
        facility_type="other_debt", lien="unknown", reference_rate="UNKNOWN", spread="", maturity="",
        cost="98", fair_value="99", raw_provenance="2025q4:9",
    )
    facilities, dropped = aggregate([raw_facility(), total])
    assert len(facilities) == 1
    assert [row["facility_row_id"] for row in dropped] == ["row-total"]


def test_blind_export_removes_prediction_and_evidence_columns():
    rows = [candidate(f"pair-{index:03d}") for index in range(80)]
    rows[0]["left_borrower_norm"] = "petvet care centers"
    exported = export(rows, 60, 20260813)
    assert len(exported) == 60
    assert not (set(exported[0]) & FORBIDDEN_SOURCE_FIELDS)
    assert all(not row["manual_label"] for row in exported)
    assert all(
        name not in " ".join((row["left_borrower_norm"], row["right_borrower_norm"]))
        for row in exported for name in SEEN_DEVELOPMENT_BORROWERS
    )


def test_alias_export_has_30_locked_borrowers_and_no_outcomes():
    rows = []
    for index in range(35):
        rows.append({
            **raw_facility(
                facility_row_id=f"arcc-{index}", borrower_norm=f"borrower{index:02d}",
                investment_identifier=f"Borrower {index:02d} Loan",
            ),
            "economic_facility_id": f"ef-arcc-{index}", "is_current_period": "True",
        })
    rows.append({
        **raw_facility(
            facility_row_id="obdc-1", ticker="OBDC", borrower_norm="borrower00",
            investment_identifier="Borrower 00 Loan",
        ),
        "economic_facility_id": "ef-obdc-1", "is_current_period": "True",
    })
    exported, borrowers = build_alias_audit(rows, sample_size=30, seed=20260813)
    assert len(borrowers) == 30
    assert {"manual_same_borrower", "manual_same_facility"} <= set(exported[0])
    assert all("fair_value" not in row and "mark_fv_to_principal" not in row for row in exported)


def test_evaluator_hash_lock_rejects_post_freeze_change(tmp_path):
    evaluator = tmp_path / "evaluate.py"
    evaluator.write_text("print('frozen')\n", encoding="utf-8")
    import hashlib

    frozen_hash = hashlib.sha256(evaluator.read_bytes()).hexdigest()
    assert verify_frozen_evaluator({"evaluation_script_sha256": frozen_hash}, evaluator) == frozen_hash
    evaluator.write_text("print('changed')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Evaluator changed after freeze"):
        verify_frozen_evaluator({"evaluation_script_sha256": frozen_hash}, evaluator)


def test_day2_frozen_sample_remains_byte_identical():
    path = Path("data/day2/frozen_nowcast_sample.json")
    import hashlib

    assert hashlib.sha256(path.read_bytes()).hexdigest() == "ff8bd2262a83463fe8f01f4897421dcb579ccf77fa958c8da58c2282ce8d871d"
    assert json.loads(path.read_text(encoding="utf-8"))["outcomes_revealed"] is False


def test_japan_valid_window_month_chunks_are_exact_and_bounded():
    periods = monthly_periods()
    assert periods[0] == "20240901-20240930"
    assert periods[-1] == "20260501-20260515"
    assert START.isoformat() == "2024-09-01"
    assert END.isoformat() == "2026-05-15"


def test_day3_freezes_and_power_guard_are_explicit():
    legacy = json.loads(Path("data/day3/japan_gate_meta.json").read_text(encoding="utf-8"))
    valid = json.loads(Path("data/day3/japan_valid_window_meta.json").read_text(encoding="utf-8"))
    movement = json.loads(Path("data/day3/movement_power_guard.json").read_text(encoding="utf-8"))
    blind = Path("data/day3/blind_facility_pairs.csv").read_text(encoding="utf-8").lower()
    assert legacy["design_status"] == "invalid_window_design"
    assert valid["design_status"] == "valid_window_frozen"
    assert valid["sample_size"] == 20
    assert valid["outcomes_used_for_selection"] == []
    assert movement["untouched_movement_source_facility_events_total"] == 10
    assert movement["power_guard_passed_for_planning"] is False
    assert all(name not in blind for name in SEEN_DEVELOPMENT_BORROWERS)
