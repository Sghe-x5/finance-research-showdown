import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSENSUS = ROOT / "data/day5/day5_structural_mapping_consensus.csv"
FREEZE = ROOT / "data/day5/day5_structural_mapping_freeze.json"
EXPECTED = "44cacbe1fd93b030a51e1e4a9bac270c746a0baef6558372fab384221a50365e"


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def test_consensus_is_exact_and_matches_supporting_order():
    assert hashlib.sha256(CONSENSUS.read_bytes()).hexdigest() == EXPECTED
    assert [r["review_observation_id"] for r in rows(CONSENSUS)] == [
        r["review_observation_id"] for r in rows(ROOT / "data/day5/day5_supporting_included_sample.csv")
    ]


def test_structural_freeze_binds_underpowered_strict_layer():
    frozen = json.loads(FREEZE.read_text())
    assert frozen["strict_power_guard"]["bound_primary_status"] == "underpowered_inconclusive"
    assert frozen["strict"]["continuing_source_event_clusters"] == 14
    assert frozen["strict"]["continuing_unique_borrowers"] == 10
    assert frozen["numeric_reveal_authorized_in_this_record"] is False


def test_consensus_contains_no_numeric_valuation_fields():
    with CONSENSUS.open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle))
    forbidden = ("principal", "cost", "fair_value", "fv_par", "mark", "prediction", "error")
    assert not any(token in field.casefold() for field in header for token in forbidden)


def test_private_keys_remain_untracked():
    tracked = subprocess.run(
        ["git", "ls-files", "private/day5"], cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout
    assert tracked == ""
