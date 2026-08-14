import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "day2"))
sys.path.insert(0, str(ROOT / "scripts" / "day3"))
sys.path.insert(0, str(ROOT / "scripts" / "day4"))
sys.path.insert(0, str(ROOT / "02_showdown"))
