import json
import importlib.util
from pathlib import Path

import pytest
import run_japan_valid_window_gate as japan_gate

from aggregate_facilities import aggregate, validate
from build_alias_recall_audit import build as build_alias_audit
from export_blind_match_benchmark import FORBIDDEN_SOURCE_FIELDS, SEEN_DEVELOPMENT_BORROWERS, export
from run_japan_valid_window_gate import (
    END, START, monthly_periods, reconstruct_forecast_pair,
)


_DAY3_EVALUATOR_SPEC = importlib.util.spec_from_file_location(
    "day3_evaluate_nowcasts", Path("scripts/day3/evaluate_nowcasts.py")
)
_DAY3_EVALUATOR = importlib.util.module_from_spec(_DAY3_EVALUATOR_SPEC)
_DAY3_EVALUATOR_SPEC.loader.exec_module(_DAY3_EVALUATOR)
verify_frozen_evaluator = _DAY3_EVALUATOR.verify_frozen_evaluator


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
        facility_row_id="row-b", investment_identifier="Borrower First Lien Term Loan",
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


def test_aggregation_uses_exact_spread_maturity_and_tranche_within_bdc():
    base = raw_facility()
    close_spread = raw_facility(
        facility_row_id="row-spread", spread="0.052", raw_provenance="2025q4:2",
    )
    same_month_maturity = raw_facility(
        facility_row_id="row-maturity", maturity="2028-10-15", raw_provenance="2025q4:3",
    )
    other_tranche = raw_facility(
        facility_row_id="row-tranche", investment_identifier="Borrower First Lien Term Loan B",
        raw_provenance="2025q4:4",
    )
    facilities, _ = aggregate([base, close_spread, same_month_maturity, other_tranche])
    assert len(facilities) == 4


def test_aggregation_unknown_tranche_is_not_merged_aggressively():
    left = raw_facility(
        facility_row_id="row-left", investment_identifier="Borrower LLC", facility_type="other_debt",
        lien="unknown", reference_rate="UNKNOWN", spread="", maturity="", raw_provenance="2025q4:1",
    )
    right = raw_facility(
        facility_row_id="row-right", investment_identifier="Borrower LLC", facility_type="other_debt",
        lien="unknown", reference_rate="UNKNOWN", spread="", maturity="", raw_provenance="2025q4:2",
    )
    facilities, _ = aggregate([left, right])
    assert len(facilities) == 2


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
    excluded_aliases = {alias for aliases in SEEN_DEVELOPMENT_BORROWERS.values() for alias in aliases}
    assert all(
        row[side] not in excluded_aliases
        for row in exported for side in ("left_borrower_norm", "right_borrower_norm")
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
    japan_summary = json.loads(Path("data/day3/japan_valid_window_summary.json").read_text(encoding="utf-8"))
    movement = json.loads(Path("data/day3/movement_power_guard.json").read_text(encoding="utf-8"))
    blind = Path("data/day3/blind_facility_pairs.csv").read_text(encoding="utf-8").lower()
    assert legacy["design_status"] == "invalid_window_design"
    assert valid["design_status"] == "valid_window_frozen"
    assert valid["sample_size"] == 20
    assert valid["outcomes_used_for_selection"] == []
    assert japan_summary["status_code"] == "pending_jquants_execution"
    assert japan_summary["jquants_requests_made"] == 0
    assert japan_summary["historical_tdnet_recovered"] == 0
    assert japan_summary["wayback_recovered"] == 0
    assert japan_summary["issuer_ir_status"] == "not_attempted"
    assert japan_summary["gate_verdict"] == "not_evaluated"
    assert movement["untouched_movement_source_facility_events_total"] == 6
    assert movement["power_guard_passed_for_planning"] is False
    excluded_aliases = {alias for aliases in SEEN_DEVELOPMENT_BORROWERS.values() for alias in aliases}
    assert all(name not in blind for name in excluded_aliases)


def test_corrected_blind_files_hide_strata_predictions_and_similarity_scores():
    import csv

    facility_path = Path("data/day3/blind_facility_pairs_v2.csv")
    with facility_path.open(newline="", encoding="utf-8") as handle:
        facility_rows = list(csv.DictReader(handle))
    assert len(facility_rows) == 120
    facility_headers = {name.lower() for name in facility_rows[0]}
    assert not any(
        token in header
        for header in facility_headers
        for token in ("hidden", "predicted", "confidence", "evidence", "stratum")
    )
    assert all(not row["manual_label"] for row in facility_rows)

    facility_meta = json.loads(Path("data/day3/blind_facility_pairs_v2_meta.json").read_text(encoding="utf-8"))
    assert facility_meta["aggregate_hidden_stratum_counts"] == {
        "hard_same_borrower_different_facility": 30,
        "predicted_same_facility_high": 60,
        "uncertain_alias_distractor": 30,
    }
    assert facility_meta["private_key_tracked_by_git"] is False

    with Path("data/day3/blind_alias_candidates.csv").open(newline="", encoding="utf-8") as handle:
        alias_rows = list(csv.DictReader(handle))
    forbidden = ("exact_borrower_block", "substring", "sequence_similarity", "token_jaccard", "shared")
    assert not any(token in header.lower() for header in alias_rows[0] for token in forbidden)
    alias_meta = json.loads(Path("data/day3/blind_alias_candidates_meta.json").read_text(encoding="utf-8"))
    assert alias_meta["primary_audit_debt_facilities_only"] is True
    assert alias_meta["sampled_borrower_count"] == 30


def test_japan_full_eligible_universe_matches_frozen_hash():
    import hashlib

    meta = json.loads(Path("data/day3/japan_valid_window_meta.json").read_text(encoding="utf-8"))
    rows = Path("data/day3/japan_valid_window_universe_ids.csv").read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == len(set(rows)) == 3999
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == meta["clean_universe_ids_sha256"]
    assert meta["selection_uses_recovery_success"] is False
    assert meta["failed_rows_replaceable"] is False


def jq_record(**overrides):
    row = {
        "DiscDate": "2025-05-01", "DiscTime": "15:00:00", "Code": "12340",
        "DiscNo": "old-record", "DocType": "FYFinancialStatements",
        "CurFYSt": "2025-01-01", "CurFYEn": "2025-12-31",
        "FSales": 100, "FOP": 10, "FOdP": 9, "FNP": 6,
    }
    row.update(overrides)
    return row


def test_jquants_reconstruction_requires_exact_revision_type_and_preserves_provenance():
    event = {"publication_timestamp_jst": "2025-08-01 15:00:00"}
    revision = jq_record(
        DiscDate="2025-08-01", DiscTime="15:00:00", DiscNo="new-record",
        DocType="EarnForecastRevision", FSales=90, FOP=7, FOdP=6, FNP=4,
    )
    status, values, _ = reconstruct_forecast_pair(
        event, [jq_record(), revision], {"EarnForecastRevision"},
    )
    assert status == "recovered"
    assert values["old_source_record_id"] == "old-record"
    assert values["new_source_record_id"] == "new-record"
    assert values["old_revenue"] == "100"
    assert values["new_revenue"] == "90"
    assert values["basis"] == "consolidated"


def test_jquants_reconstruction_separates_prior_outside_window():
    event = {"publication_timestamp_jst": "2024-10-01 15:00:00"}
    revision = jq_record(
        DiscDate="2024-10-01", DiscNo="new-record", DocType="EarnForecastRevision",
        CurFYSt="2024-04-01", CurFYEn="2025-03-31",
    )
    status, values, _ = reconstruct_forecast_pair(event, [revision], {"EarnForecastRevision"})
    assert status == "prior_outside_window"
    assert values == {}


def test_jquants_reconstruction_does_not_guess_document_type():
    event = {"publication_timestamp_jst": "2025-08-01 15:00:00"}
    quarterly = jq_record(DiscDate="2025-08-01", DiscNo="quarterly", DocType="FYFinancialStatements")
    status, _, _ = reconstruct_forecast_pair(event, [quarterly], {"EarnForecastRevision"})
    assert status == "revision_record_not_found"


def test_jquants_pagination_is_complete_and_cached_outside_git(monkeypatch, tmp_path):
    first = jq_record(DiscNo="one")
    second = jq_record(DiscNo="two", DiscDate="2025-06-01")
    payloads = iter([
        {"data": [first], "pagination_key": "next-page"},
        {"data": [second]},
    ])
    monkeypatch.setattr(japan_gate, "request_jquants_page", lambda api_key, params: next(payloads))
    monkeypatch.setattr(japan_gate, "RAW_CACHE_DIR", tmp_path)
    monkeypatch.setattr(japan_gate.time, "sleep", lambda seconds: None)
    rows, meta = japan_gate.fetch_jquants_rows("secret-not-written", "1234")
    assert [row["DiscNo"] for row in rows] == ["one", "two"]
    assert meta["page_count"] == 2
    assert len(meta["raw_cache_sha256"]) == 64
    assert (tmp_path / "fin_summary_1234.json").exists()


def test_jquants_429_uses_backoff(monkeypatch):
    class Response:
        def __init__(self, status, payload=None):
            self.status_code = status
            self.headers = {"Retry-After": "13"} if status == 429 else {}
            self._payload = payload or {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise AssertionError("unexpected status")

        def json(self):
            return self._payload

    responses = iter([Response(429), Response(200, {"data": []})])
    waits = []
    monkeypatch.setattr(japan_gate.requests, "get", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(japan_gate.time, "sleep", waits.append)
    assert japan_gate.request_jquants_page("secret", {"code": "12340"}) == {"data": []}
    assert waits == [13.0]
