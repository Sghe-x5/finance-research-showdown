#!/usr/bin/env python3
"""Download and inventory official monthly SEC BDC archives for Day 5.

Raw ZIP files remain outside Git.  Existing cache files are never overwritten.
The manifest records months with no financial/SOI table explicitly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


INDEX_URL = "https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets"
DEFAULT_CACHE = Path("/private/tmp/finance-day5-sec-cache/raw")
DEFAULT_MANIFEST = Path("data/day5/sec_bdc_archive_manifest.csv")
DEFAULT_MONTHS = [f"2026_{month:02d}" for month in range(1, 7)]
MANIFEST_FIELDS = (
    "archive_id", "sec_filename", "source_url", "retrieved_utc", "bytes",
    "sha256", "member_count", "inventory_json", "inventory_sha256",
    "submission_member", "soi_member", "submission_header_sha256",
    "soi_header_sha256", "status",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_user_agent() -> str:
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SystemExit("SEC_USER_AGENT must contain a descriptive name and real contact email")
    return value


def fetch(url: str, user_agent: str, minimum_interval: float = 0.2) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": user_agent, "Accept-Encoding": "identity"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    time.sleep(minimum_interval)
    return payload


def discover_monthly(html: bytes) -> dict[str, str]:
    hrefs = re.findall(r"href=[\"']([^\"']+\.zip)[\"']", html.decode("utf-8", "replace"), re.I)
    output = {}
    for href in hrefs:
        match = re.search(r"(20\d{2}_[01]\d)_bdc\.zip$", href, re.I)
        if match:
            output[match.group(1)] = urllib.parse.urljoin(INDEX_URL, href)
    if not output:
        raise RuntimeError("Official SEC BDC index exposed no monthly ZIP archives")
    return output


def header(archive: zipfile.ZipFile, member: str) -> tuple[str, set[str]]:
    with archive.open(member) as handle:
        value = handle.readline().decode("utf-8-sig", "strict").rstrip("\r\n")
    return value, set(value.split("\t"))


def inspect_archive(path: Path) -> dict:
    if not zipfile.is_zipfile(path):
        raise RuntimeError(f"Official payload is not a ZIP: {path}")
    with zipfile.ZipFile(path) as archive:
        inventory = [
            {"name": item.filename, "bytes": item.file_size, "crc32": f"{item.CRC:08x}"}
            for item in archive.infolist()
            if not item.is_dir()
        ]
        candidates = []
        for item in archive.infolist():
            if item.is_dir() or not item.filename.lower().endswith((".tsv", ".txt")):
                continue
            value, fields = header(archive, item.filename)
            candidates.append((item.filename, value, fields))
        submissions = [
            item for item in candidates if {"adsh", "cik", "period", "accepted"} <= item[2]
        ]
        soi = [
            item for item in candidates
            if {"adsh", "cik", "ddate", "period", "Investment, Identifier Axis"} <= item[2]
            and any("fair value" in field.lower() for field in item[2])
        ]
        if len(submissions) != 1:
            raise RuntimeError(
                f"Unexpected monthly submission schema: {len(submissions)} candidates; "
                f"inventory={json.dumps(inventory, sort_keys=True)}"
            )
        if len(soi) > 1:
            raise RuntimeError(f"Unexpected monthly SOI schema: {len(soi)} candidates")
        return {
            "inventory": inventory,
            "submission": submissions[0],
            "soi": soi[0] if soi else None,
        }


def download_one(archive_id: str, url: str, cache: Path, user_agent: str) -> dict[str, object]:
    cache.mkdir(parents=True, exist_ok=True)
    filename = Path(urllib.parse.urlparse(url).path).name
    path = cache / filename
    if path.exists():
        retrieved = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0)
    else:
        payload = fetch(url, user_agent)
        path.write_bytes(payload)
        retrieved = datetime.now(timezone.utc).replace(microsecond=0)
    inspection = inspect_archive(path)
    inventory_json = json.dumps(
        inspection["inventory"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    submission = inspection["submission"]
    soi = inspection["soi"]
    return {
        "archive_id": archive_id,
        "sec_filename": filename,
        "source_url": url,
        "retrieved_utc": retrieved.isoformat().replace("+00:00", "Z"),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "member_count": len(inspection["inventory"]),
        "inventory_json": inventory_json,
        "inventory_sha256": sha256_bytes(inventory_json.encode("utf-8")),
        "submission_member": submission[0],
        "soi_member": soi[0] if soi else "",
        "submission_header_sha256": sha256_bytes(submission[1].encode("utf-8")),
        "soi_header_sha256": sha256_bytes(soi[1].encode("utf-8")) if soi else "",
        "status": "downloaded_and_schema_validated" if soi else "downloaded_no_financial_soi_table",
    }


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", nargs="+", default=DEFAULT_MONTHS)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    user_agent = require_user_agent()
    discovered = discover_monthly(fetch(INDEX_URL, user_agent))
    rows = []
    for archive_id in args.months:
        if archive_id not in discovered:
            raise RuntimeError(f"{archive_id} is not linked from the official SEC BDC index")
        row = download_one(archive_id, discovered[archive_id], args.cache_dir, user_agent)
        rows.append(row)
        print(
            f"{archive_id}: {row['sec_filename']} {row['bytes']} bytes "
            f"sha256={row['sha256']} status={row['status']}"
        )
    write_manifest(args.manifest, rows)
    print(f"manifest={args.manifest}; raw_cache={args.cache_dir}; historical_cache_unchanged=true")


if __name__ == "__main__":
    main()
