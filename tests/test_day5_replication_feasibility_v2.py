import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def csv_rows(relative):
    with (ROOT / relative).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def payload(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def test_monthly_manifest_is_official_and_complete():
    rows = csv_rows("data/day5/sec_bdc_archive_manifest.csv")
    assert [row["archive_id"] for row in rows] == [
        "2026_01", "2026_02", "2026_03", "2026_04", "2026_05", "2026_06"
    ]
    assert all(row["source_url"].startswith("https://www.sec.gov/") for row in rows)
    assert all(len(row["sha256"]) == 64 and int(row["bytes"]) > 0 for row in rows)
    june = rows[-1]
    assert june["status"] == "downloaded_no_financial_soi_table"
    assert june["soi_member"] == ""


def test_raw_archive_hashes_match_external_cache():
    for row in csv_rows("data/day5/sec_bdc_archive_manifest.csv"):
        path = Path("/private/tmp/finance-day5-sec-cache/raw") / row["sec_filename"]
        assert path.exists()
        assert digest(path) == row["sha256"]


def test_locked_facility_pipeline_recovered_both_context_periods():
    data = payload("data/day5/new_quarter_facility_metadata.json")
    assert data["normalization_rules_changed"] is False
    assert data["aggregation_rules_changed"] is False
    assert data["matcher_rules_changed"] is False
    assert data["required_periods_recovered"]["2025-12-31"] > 0
    assert data["required_periods_recovered"]["2026-03-31"] > 0


def test_independence_audit_excludes_2025q4_and_allows_2026q1():
    data = payload("data/day5/new_period_independence_audit.json")
    q4 = data["periods"]["2025Q4"]
    q1 = data["periods"]["2026Q1"]
    assert q4["conditions"]["target_outcomes_not_inspected"] == "FAIL"
    assert q4["included_as_replication_outcome_period"] is False
    assert q1["overall_status"] == "PASS_UNTOUCHED"
    assert all(value == "PASS" for value in q1["conditions"].values())


def test_verified_manager_and_listing_files_are_complete():
    managers = csv_rows("data/day5/new_fund_manager_map_verified.csv")
    listings = csv_rows("data/day5/new_fund_listing_status_verified.csv")
    assert len(managers) == 31
    assert {row["cik"] for row in managers} == {row["cik"] for row in listings}
    assert all(row["verification_status"] == "verified" for row in managers)
    assert all(row["evidence_source"].startswith("https://www.sec.gov/") for row in managers)
    assert sum(row["listing_status"] == "verified_listed_equity" for row in listings) == 15


def test_reporting_rows_are_explicit_and_official():
    rows = csv_rows("data/day5/new_fund_reporting_order_verified.csv")
    assert len(rows) == 53
    assert all(row["verification_status"] in {
        "verified", "excluded_not_verified_listed_equity", "explicit_missing"
    } for row in rows)
    assert all(
        not row["evidence_source"] or row["evidence_source"].startswith("https://www.sec.gov/")
        for row in rows
    )


def test_v2_candidates_have_no_target_numeric_or_prediction_columns():
    path = ROOT / "data/day5/replication_universe_candidates_v2.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        fields = set(csv.DictReader(handle).fieldnames or [])
    forbidden = {
        "target_current_mark", "target_fair_value", "target_current_fair_value",
        "prediction_B0", "prediction_SN", "error", "absolute_error",
        "source_current_mark", "source_prior_mark", "source_delta_mark",
    }
    assert not (fields & forbidden)
    assert not any("fair_value" in field.lower() for field in fields)
    assert not any("prediction" in field.lower() for field in fields)


def test_v2_periods_cutoffs_and_primary_relationships_are_clean():
    rows = csv_rows("data/day5/replication_universe_candidates_v2.csv")
    assert rows
    assert all(row["period_end"] not in {"2025-09-30", "2025-12-31"} for row in rows)
    assert any(row["period_end"] == "2026-03-31" for row in rows)
    assert all(row["target_cutoff_basis"] == "verified_earliest_results_day3" for row in rows)
    strict = [row for row in rows if row["strict_new_borrower_universe"] == "True"]
    supporting = [row for row in rows if row["new_fund_universe"] == "True"]
    assert all(row["manager_relationship"] == "cross_manager" for row in strict + supporting)
    assert all(row["overlap_day4_source_event_id"] == "False" for row in strict + supporting)


def test_v2_summary_counts_and_duplicate_audit_match_rows():
    rows = csv_rows("data/day5/replication_universe_candidates_v2.csv")
    data = payload("data/day5/replication_feasibility_summary_v2.json")
    strict = [row for row in rows if row["strict_new_borrower_universe"] == "True"]
    supporting = [row for row in rows if row["new_fund_universe"] == "True"]
    assert data["strict_new_borrower"]["observations"] == len(strict)
    assert data["supporting_new_fund"]["observations"] == len(supporting)
    assert data["duplicate_vote_audit"] == {"duplicate_identities": 0, "duplicate_rows": 0}
    assert data["planning_target"]["appears_feasible"] is False
    assert data["prohibitions"]["target_same_period_numeric_values_materialized"] is False
    assert data["prohibitions"]["sample_frozen"] is False
    assert data["prohibitions"]["result_tag_created"] is False
