import csv
import json
from datetime import datetime
from pathlib import Path


def read_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_generated_ids_are_unique_and_locked():
    candidates = read_rows("data/day2/facility_candidates.csv")
    benchmark = read_rows("data/day2/locked_match_sample.csv")
    japan = read_rows("data/day2/japan_revision_sample.csv")
    assert len({row["pair_id"] for row in candidates}) == len(candidates)
    assert len(benchmark) >= 200
    assert len({row["pair_id"] for row in benchmark}) == len(benchmark)
    assert all(row["sample_locked"] == "True" for row in benchmark)
    assert 30 <= len(japan) <= 50
    assert len({row["event_id"] for row in japan}) == len(japan)
    assert all(row["sample_locked"] == "True" for row in japan)


def test_manifest_schema_and_timestamps():
    manifest = read_rows("data/day2/raw_manifest.csv")
    assert {row["archive_id"] for row in manifest} == {"2025q3", "2025q4"}
    assert all(int(row["bytes"]) > 0 for row in manifest)
    assert all(len(row["sha256"]) == 64 for row in manifest)
    assert [row["retrieved_utc"] for row in manifest] == sorted(row["retrieved_utc"] for row in manifest)


def test_frozen_hash_metadata_precedes_recovery():
    meta = json.loads(Path("data/day2/japan_revision_sample_meta.json").read_text(encoding="utf-8"))
    assert meta["sample_size"] == 40
    assert len(meta["locked_event_ids_sha256"]) == 64


def test_eligible_timestamps_and_frozen_outcomes_are_clean():
    eligible = read_rows("data/day2/eligible_nowcast_ids.csv")
    frozen = json.loads(Path("data/day2/frozen_nowcast_sample.json").read_text(encoding="utf-8"))
    assert len(eligible) == 45
    assert len({row["observation_id"] for row in eligible}) == len(eligible)
    for row in eligible:
        source = datetime.fromisoformat(row["source_results_timestamp_utc"].replace("Z", "+00:00"))
        cutoff = datetime.fromisoformat(row["target_cutoff_timestamp_utc"].replace("Z", "+00:00"))
        assert source < cutoff
        assert row["source_public_before_target_cutoff"] == "True"
        assert row["target_held_previous_filing"] == "True"
        assert row["outcomes_revealed"] == "False"
    results = read_rows("data/day2/nowcast_results.csv")
    assert {row["observation_id"] for row in results} == set(frozen["observation_ids"])
    assert all(row["contaminated_fixture"] == "False" for row in results)


def test_benchmark_gate_and_japan_failures_are_explicit():
    benchmark = json.loads(Path("data/day2/locked_match_benchmark_results.json").read_text(encoding="utf-8"))
    assert benchmark["primary_precision_gate_95pct"] is None
    assert benchmark["computed_gate_before_external_audit"] is True
    assert benchmark["external_audit_status"] == "invalid_upper_bound_by_construction"
    japan = read_rows("data/day2/japan_revision_sample.csv")
    assert sum(row["recovery_status"] == "recovered_provisional" for row in japan) == 8
    assert sum(row["recovery_status"] == "failed" for row in japan) == 32
    assert sum(row["treatment_status"] == "complete" for row in japan[:10]) == 0
