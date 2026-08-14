#!/usr/bin/env python3
"""Generate a SHA-256 manifest for the visible project-memory folder."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--base-commit", default="")
    args = parser.parse_args()

    root = args.root.resolve()
    output = root / "MANIFEST.json"
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path == output:
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    payload = {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "base_commit": args.base_commit,
        "file_count": len(rows),
        "files": rows,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {output} ({len(rows)} files)")


if __name__ == "__main__":
    main()
