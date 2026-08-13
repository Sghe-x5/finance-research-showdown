#!/usr/bin/env python3
"""Discover, download and inventory official SEC BDC flat-file archives."""

import argparse
import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from common import sha256_bytes, sha256_file, write_csv


INDEX_URL = "https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets"
DEFAULT_CACHE = Path("/private/tmp/finance-day2-sec-cache")
DEFAULT_MANIFEST = Path("data/day2/raw_manifest.csv")
MANIFEST_FIELDS = [
    "archive_id", "source_url", "retrieved_utc", "bytes", "sha256",
    "member_count", "inventory_json", "inventory_sha256", "submission_member",
    "soi_member", "submission_header_sha256", "soi_header_sha256", "status",
]


def require_user_agent():
    value = os.environ.get("SEC_USER_AGENT", "").strip()
    if "@" not in value:
        raise SystemExit("SEC_USER_AGENT must contain a real contact email")
    return value


def fetch(url, user_agent, minimum_interval=0.15):
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    time.sleep(minimum_interval)
    return payload


def discover_archives(html, base_url=INDEX_URL):
    text = html.decode("utf-8", errors="replace")
    hrefs = re.findall(r"href=[\"']([^\"']+\.zip)[\"']", text, flags=re.I)
    discovered = {}
    for href in hrefs:
        match = re.search(r"(20\d{2}q[1-4])[^/]*\.zip$", href, flags=re.I)
        if match:
            discovered[match.group(1).lower()] = urllib.parse.urljoin(base_url, href)
    if not discovered:
        raise RuntimeError("SEC BDC index contained no discoverable quarterly ZIP links")
    return discovered


def header_fields(archive, member):
    with archive.open(member) as handle:
        header = handle.readline().decode("utf-8-sig", errors="strict").rstrip("\r\n")
    return header, set(header.split("\t"))


def identify_schema(archive):
    inventory = [
        {"name": item.filename, "bytes": item.file_size, "crc32": f"{item.CRC:08x}"}
        for item in archive.infolist() if not item.is_dir()
    ]
    candidates = []
    for item in archive.infolist():
        if item.is_dir() or not item.filename.lower().endswith((".tsv", ".txt")):
            continue
        header, fields = header_fields(archive, item.filename)
        candidates.append((item.filename, header, fields))

    submission = [entry for entry in candidates if {"adsh", "cik", "period", "accepted"} <= entry[2]]
    soi = [
        entry for entry in candidates
        if {"adsh", "cik", "ddate", "period"} <= entry[2]
        and "Investment, Identifier Axis" in entry[2]
        and any("Fair Value" in field or "fair value" in field for field in entry[2])
    ]
    if len(submission) != 1 or len(soi) != 1:
        raise RuntimeError(
            f"Unexpected SEC BDC schema: submission candidates={len(submission)}, "
            f"SOI candidates={len(soi)}; inventory={json.dumps(inventory)}"
        )
    return inventory, submission[0], soi[0]


def download_period(period, url, cache_dir, user_agent):
    cache_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(urllib.parse.urlparse(url).path).name
    archive_path = cache_dir / filename
    retrieved = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if not archive_path.exists():
        archive_path.write_bytes(fetch(url, user_agent))
    else:
        retrieved = datetime.fromtimestamp(archive_path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()

    if not zipfile.is_zipfile(archive_path):
        raise RuntimeError(f"Downloaded payload is not a ZIP: {archive_path}")
    with zipfile.ZipFile(archive_path) as archive:
        inventory, submission, soi = identify_schema(archive)
    inventory_json = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "archive_id": period,
        "source_url": url,
        "retrieved_utc": retrieved,
        "bytes": archive_path.stat().st_size,
        "sha256": sha256_file(archive_path),
        "member_count": len(inventory),
        "inventory_json": inventory_json,
        "inventory_sha256": sha256_bytes(inventory_json.encode("utf-8")),
        "submission_member": submission[0],
        "soi_member": soi[0],
        "submission_header_sha256": sha256_bytes(submission[1].encode("utf-8")),
        "soi_header_sha256": sha256_bytes(soi[1].encode("utf-8")),
        "status": "downloaded_and_schema_validated",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--periods", nargs="+", default=["2025q3", "2025q4"])
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    user_agent = require_user_agent()
    discovered = discover_archives(fetch(INDEX_URL, user_agent))
    rows = []
    for period in args.periods:
        period = period.lower()
        if period not in discovered:
            raise RuntimeError(f"Requested {period} is not linked from the official SEC index")
        row = download_period(period, discovered[period], args.cache_dir, user_agent)
        rows.append(row)
        inventory = json.loads(row["inventory_json"])
        print(f"{period}: {row['bytes']} bytes sha256={row['sha256']} members={len(inventory)}")
        for item in inventory:
            print(f"  {item['name']} {item['bytes']} bytes crc32={item['crc32']}")
    write_csv(args.manifest, rows, MANIFEST_FIELDS)
    print(f"Wrote {args.manifest}; raw ZIPs remain outside Git in {args.cache_dir}")


if __name__ == "__main__":
    main()
