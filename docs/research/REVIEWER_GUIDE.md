# Independent blind review guide

This handoff is designed to keep human facility and alias judgments independent
of model decisions, prior development examples, and target outcomes.

## Files to review

| Task | Canonical public file | SHA-256 |
|---|---|---|
| Facility identity | [`../../data/day3/blind_facility_pairs_v3.csv`](../../data/day3/blind_facility_pairs_v3.csv) | `f4ec256bf4502f5cb6979ff218d3b5457481f0ae21bdb75841d4bb3c1d357c2b` |
| Borrower alias recall | [`../../data/day3/blind_alias_candidates.csv`](../../data/day3/blind_alias_candidates.csv) | `d37f5daeb4eb6cee9e4ddb2e7690978a6ac899c30305b4fda268bb7424a8b64e` |

Do **not** use any of the following for a new clean review:

- `blind_facility_pairs.csv` — superseded wrong sampling design;
- `blind_facility_pairs_v2.csv` — superseded after field-lineage repair;
- `blind_match_sample.csv` — earlier development artifact;
- any file under `private/` — hidden mapping keys, never reviewer material.

## Before labeling

1. Copy the two canonical public CSVs outside the repository.
2. Verify their hashes:

   ```bash
   shasum -a 256 blind_facility_pairs_v3.csv blind_alias_candidates.csv
   ```

3. Record reviewer name/code and review date separately.
4. Do not inspect model code, hidden strata, other reviewers' labels, private
   mappings, or target-current outcomes.

## Facility review

The v3 facility file contains 120 rows with randomized left/right order. The
sampling strata and model decisions are intentionally absent. For each pair,
the reviewer should choose exactly one judgment in their **separate working
copy**:

- `same_facility`;
- `same_borrower_different_facility`;
- `uncertain`;
- `unrelated`.

Use only displayed evidence. Do not infer missing maturity, currency, reference
rate, or acquisition date from free-form identifier text. When the evidence is
insufficient, prefer `uncertain` over a forced match.

## Alias review

The alias file tests whether exact borrower-name blocking misses plausible
cross-fund borrower identities. Candidate order is randomized and similarity
scores are hidden. Reviewers should decide borrower identity first; facility
identity remains a separate downstream question.

## Submission

- Do not edit or commit the canonical CSVs.
- Return only the reviewer's separate labeled copies to the research lead.
- Do not upload private keys, source caches, or other reviewers' work.
- Do not reconcile disagreements until all independent reviews are complete.

The research lead must verify the original hashes before adjudication. A new
freeze remains prohibited until blind precision passes, movement power remains
at least 20, and preregistration v3 is approved.
