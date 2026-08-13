import csv
import json
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
