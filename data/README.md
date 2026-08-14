# Data directory

Only compact, provenance-aware outputs belong in Git. Large raw archives,
scraped pages, bulk API responses, credentials, and private blind mappings are
stored outside the repository.

## Layout

| Path | Contents |
|---|---|
| `templates/` | Manual input and decision-table schemas |
| `day2/` | Frozen Day 2 pilot outputs and manifests |
| `day3/` | Append-only measurement repairs, audits, power analysis, and blind-review files |

## Current reviewer artifacts

| File | Status | SHA-256 |
|---|---|---|
| [`day3/blind_facility_pairs_v3.csv`](day3/blind_facility_pairs_v3.csv) | Current facility benchmark for clean reviewers | `f4ec256bf4502f5cb6979ff218d3b5457481f0ae21bdb75841d4bb3c1d357c2b` |
| [`day3/blind_alias_candidates.csv`](day3/blind_alias_candidates.csv) | Current alias-recall benchmark | `d37f5daeb4eb6cee9e4ddb2e7690978a6ac899c30305b4fda268bb7424a8b64e` |

Superseded files remain tracked for auditability:

- `blind_facility_pairs.csv`: wrong simple-random sampling design;
- `blind_facility_pairs_v2.csv`: superseded after official field-lineage repair;
- `blind_match_sample.csv`: earlier development sample.

Do not delete, relabel, or silently replace frozen/superseded artifacts. Add a
new version plus metadata and hashes when a design changes.

## Provenance convention

Generated research outputs should identify, directly or through adjacent
metadata:

- source artifact hashes;
- deterministic seed or seed derivation;
- generation script and classifier commit;
- row counts and schema version;
- whether target-current outcomes or human labels were read;
- the exact supersession relationship, if any.

Files in `private/` are ignored by Git. Their hashes may be public, but their
contents must not be committed or sent to reviewers.
