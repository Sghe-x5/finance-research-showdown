"""Small deterministic helpers shared by the Day 2 one-shot scripts."""

import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path


SEED = 20260813
CONTAMINATED_CASE_IDS = {
    "AUCTANE_ARCC_BXSL_2025Q4",
    "MEDALLIA_BXSL_FSK_2025Q4",
}


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(*values, length=24):
    payload = "\x1f".join(str(value or "") for value in values).encode("utf-8")
    return sha256_bytes(payload)[:length]


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if fieldnames is None:
        if not rows:
            raise ValueError(f"fieldnames required for empty CSV: {path}")
        fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def clean_member(value):
    value = re.sub(r"\s*\[Member\]\s*$", "", value or "", flags=re.I)
    return re.sub(r"\s+", " ", value).strip()


def normalize_text(value):
    value = clean_member(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


FACILITY_WORDS = re.compile(
    r"\b(first|second|third|senior|junior|lien|secured|unsecured|subordinated|unitranche|"
    r"term|loan|revolver|revolving|facility|delayed|draw|ddtl|notes?|bonds?|debt|"
    r"preferred|common|equity|warrants?|class|series|tranche|sofr|libor|euribor|"
    r"prime|pik|cash|funded|unfunded|due|maturity)\b",
    re.I,
)
LEGAL_SUFFIXES = re.compile(
    r"\b(incorporated|inc|llc|ltd|limited|lp|l p|corp|corporation|company|co|holdings?|group|plc)\b",
    re.I,
)


def normalize_borrower(value):
    value = normalize_text(value)
    value = re.sub(r"\b20\d{2}\b", " ", value)
    value = re.sub(r"\b\d+(?:st|nd|rd|th)?\b", " ", value)
    value = FACILITY_WORDS.sub(" ", value)
    value = LEGAL_SUFFIXES.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def debt_equity(*values):
    text = " ".join(normalize_text(value) for value in values if value)
    if re.search(r"\b(common|preferred|equity|unit|warrant|partnership interest)\b", text):
        return "equity"
    if re.search(r"\b(loan|debt|note|bond|revolver|revolving|lien|secured|unitranche)\b", text):
        return "debt"
    return "unknown"


def facility_type(*values):
    text = " ".join(normalize_text(value) for value in values if value)
    if "delayed draw" in text or "ddtl" in text:
        return "delayed_draw"
    if "revolver" in text or "revolving" in text:
        return "revolver"
    if "term loan" in text or "unitranche" in text:
        return "term_loan"
    if re.search(r"\b(note|bond)\b", text):
        return "note_or_bond"
    if "preferred" in text:
        return "preferred_equity"
    if re.search(r"\b(common|equity|unit|partnership interest)\b", text):
        return "common_equity"
    if "warrant" in text:
        return "warrant"
    if debt_equity(text) == "debt":
        return "other_debt"
    return "unknown"


def lien_category(*values):
    text = " ".join(normalize_text(value) for value in values if value)
    if re.search(r"\b(first|1st) lien\b", text):
        return "first_lien"
    if re.search(r"\b(second|2nd) lien\b", text):
        return "second_lien"
    if "subordinated" in text or "junior" in text:
        return "subordinated"
    if "unsecured" in text:
        return "unsecured"
    if "secured" in text:
        return "secured_unspecified"
    return "unknown"


def reference_rate(*values):
    text = " ".join(normalize_text(value) for value in values if value)
    for token in ("sofr", "libor", "euribor", "prime", "sonia", "ester"):
        if token in text:
            return token.upper()
    if "fixed" in text:
        return "FIXED"
    return "UNKNOWN"


def funded_status(*values):
    text = " ".join(normalize_text(value) for value in values if value)
    if "unfunded" in text or "commitment" in text:
        return "unfunded"
    if "delayed draw" in text:
        return "unknown"
    return "funded"


def decimal_or_none(value):
    if value in (None, "", "null", "None"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def iso_date_or_blank(value):
    value = (value or "").strip()[:10]
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return ""


def days_apart(left, right):
    left = iso_date_or_blank(left)
    right = iso_date_or_blank(right)
    if not left or not right:
        return None
    return abs((date.fromisoformat(left) - date.fromisoformat(right)).days)


def quarter_label(period_end):
    value = date.fromisoformat(period_end)
    return f"{value.year}Q{(value.month - 1) // 3 + 1}"


def previous_quarter_end(period_end):
    value = date.fromisoformat(period_end)
    mapping = {
        3: date(value.year - 1, 12, 31),
        6: date(value.year, 3, 31),
        9: date(value.year, 6, 30),
        12: date(value.year, 9, 30),
    }
    return mapping[value.month].isoformat()
