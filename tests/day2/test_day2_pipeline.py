import csv
import io
import json
import zipfile

import pytest

from build_eligible_nowcasts import strict_same_facility
from build_facility_candidates import compare_pair
from day1_bdc_reporting_order import classify_exhibit_text
from download_sec_bdc_data import discover_archives, identify_schema
from evaluate_nowcasts import aggregate_mark, mark
from freeze_match_benchmark import locked_sample
from freeze_nowcast_sample import freeze
from parse_bdc_soi import normalize_row
from recover_japan_revisions import pct_change, revision_direction


def facility_row(**overrides):
    row = {
        "facility_row_id": "row-a", "period_end": "2025-09-30", "cik": "1", "ticker": "ARCC",
        "adsh": "adsh-a", "accepted": "2025-10-24T12:00:00Z", "investment_identifier": "Auctane First Lien Term Loan",
        "borrower_norm": "auctane", "debt_equity": "debt", "facility_type": "term_loan",
        "lien": "first_lien", "currency": "USD", "reference_rate": "SOFR", "spread": "0.0575",
        "maturity": "2028-10-01", "funded_status": "funded", "acquisition_date": "2022-01-01",
        "is_current_period": "True", "principal": "143.4", "fair_value": "143.4", "pik_rate": "",
        "non_accrual": "False", "restructuring_flag": "False",
    }
    row.update(overrides)
    return row


def test_discovery_does_not_assume_archive_filename():
    html = b'<a href="/files/custom/2025q3_bdc.zip">2025 Q3 BDC</a>'
    assert discover_archives(html)["2025q3"].endswith("/files/custom/2025q3_bdc.zip")


def test_zip_inventory_identifies_members_from_headers(tmp_path):
    archive_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("renamed/submission-data.txt", "adsh\tcik\tperiod\taccepted\n")
        archive.writestr(
            "renamed/investments.txt",
            "adsh\tcik\tddate\tperiod\tInvestment, Identifier Axis\tInvestment Owned, Fair Value\n",
        )
    with zipfile.ZipFile(archive_path) as archive:
        _, submission, soi = identify_schema(archive)
    assert submission[0] == "renamed/submission-data.txt"
    assert soi[0] == "renamed/investments.txt"


def test_normalize_soi_row_preserves_concepts_and_provenance():
    raw = {
        "ddate": "2025-09-30", "Investment, Identifier Axis": "Auctane First Lien Term Loan",
        "Investment Type Axis": "Debt Securities, First Lien [Member]",
        "RateType": "SOFR", "Investment, Basis Spread, Variable Rate": "0.0575",
        "Investment Maturity Date": "2028-10-01",
        "Investment Owned, Balance, Principal Amount": "143400000",
        "Adjusted cost basis": "143000000", "Initial fair value of Investment": "143400000",
    }
    submission = {
        "adsh": "0001", "cik": "1", "ticker": "ARCC", "filer_name": "Ares", "form": "10-Q",
        "filed": "20251024", "period_end": "2025-09-30", "accepted": "2025-10-24T12:00:00Z",
    }
    row = normalize_row(raw, submission, "2025q4", 99)
    assert row["borrower_norm"] == "auctane"
    assert row["lien"] == "first_lien"
    assert row["raw_provenance"] == "2025q4:99"
    assert "fair_value" in json.loads(row["source_concepts_json"])


def test_candidate_strict_facility_match_and_conflict():
    left = facility_row()
    right = facility_row(facility_row_id="row-b", cik="2", ticker="BXSL", adsh="adsh-b")
    pair = compare_pair(left, right)
    assert pair["predicted_label"] == "same_facility"
    assert pair["match_confidence"] == "high"
    different = compare_pair(left, facility_row(facility_row_id="row-c", cik="3", lien="second_lien"))
    assert different["predicted_label"] == "same_borrower_different_facility"


def test_locked_match_sample_is_deterministic_and_unlabelled():
    rows = []
    for index in range(260):
        rows.append({
            "pair_id": f"pair-{index:03d}",
            "predicted_label": "same_facility" if index % 2 else "uncertain",
            "match_confidence": "high" if index % 2 else "low",
        })
    first = locked_sample(rows, 240, 20260813)
    second = locked_sample(rows, 240, 20260813)
    assert [row["pair_id"] for row in first] == [row["pair_id"] for row in second]
    assert not any(row["manual_label"] for row in first)


def test_nowcast_freeze_is_deterministic_and_records_quarantine():
    rows = [{"observation_id": f"obs-{index:02d}"} for index in range(20)]
    first = freeze(rows, 15, 20260813)
    second = freeze(rows, 15, 20260813)
    assert first["observation_ids"] == second["observation_ids"]
    assert "AUCTANE_ARCC_BXSL_2025Q4" in first["contaminated_case_ids_excluded"]
    assert first["outcomes_revealed"] is False


def test_strict_same_facility_prefers_false_negatives():
    left = facility_row()
    assert strict_same_facility(left, facility_row(facility_row_id="row-b", cik="2"))
    assert not strict_same_facility(left, facility_row(facility_row_id="row-c", cik="2", maturity="2029-12-31"))


def test_fsk_january_2026_scheduling_announcement_is_not_results():
    text = """
    FS KKR Capital Corp. schedules release of fourth quarter and full year 2025
    financial results. FSK will report its financial results in February 2026.
    """
    accepted, _, reason = classify_exhibit_text(text)
    assert not accepted
    assert "scheduling" in reason


def test_facility_aggregation_deduplicates_rows():
    row = facility_row()
    duplicate = dict(row)
    assert aggregate_mark([row, duplicate]) == pytest.approx(1.0)
    second = facility_row(facility_row_id="row-b", principal="100", fair_value="90")
    assert aggregate_mark([row, second]) == pytest.approx((143.4 + 90) / (143.4 + 100))


def test_quarantined_arithmetic_fixtures_are_exact():
    with open("data/day2/bdc_contaminated_examples.csv", newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    auctane, medallia = rows
    assert abs(float(auctane["target_actual_mark"]) - float(auctane["target_prior_mark"])) * 100 == pytest.approx(0.2500266364)
    assert abs(float(auctane["target_actual_mark"]) - float(auctane["source_mark"])) * 100 == pytest.approx(1.4998046667)
    assert abs(float(medallia["target_actual_mark"]) - float(medallia["target_prior_mark"])) * 100 == pytest.approx(12.5111231417)
    assert abs(float(medallia["target_actual_mark"]) - float(medallia["source_mark"])) * 100 == pytest.approx(0.9798083251)
    assert all(row["contaminated"] == "True" for row in rows)


def test_japan_numeric_changes_preserve_zero_crossing():
    row = {
        "old_revenue": "100", "new_revenue": "90", "old_operating_profit": "10",
        "new_operating_profit": "-5", "old_ordinary_profit": "8", "new_ordinary_profit": "-4",
        "old_net_income": "3", "new_net_income": "-2",
    }
    assert pct_change("100", "90") == "-0.10000000"
    assert revision_direction(row) == "downward"
