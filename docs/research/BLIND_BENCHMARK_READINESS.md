# Blind Benchmark Readiness

## Status

`CURRENT_BLIND_SUPERSEDED_PIPELINE_LOSS`

Official SEC supporting XBRL facts for maturity and acquisition date were omitted at the raw-to-normalized join, and a smaller set of official reference-rate members was lost during canonicalization. The old public file and its SHA-256 are unchanged, but `data/day3/blind_facility_pairs_v2.csv` must not be given to additional clean reviewers.

The exact CSV for clean reviewers is:

`data/day3/blind_facility_pairs_v3.csv`

SHA-256: `f4ec256bf4502f5cb6979ff218d3b5457481f0ae21bdb75841d4bb3c1d357c2b`

The v3 sample contains 120 unlabeled rows: 60 hidden predicted same-facility/high, 30 hidden hard same-borrower/different-facility, and 30 hidden uncertain/alias/distractor. Side order is randomized. All 11 seen development borrowers are excluded in every period. Row-level strata, model decisions, and candidate IDs exist only in the ignored v3 private key; the old v2 and alias private keys were not opened.

The repaired candidate universe is byte-identical to the prior candidate universe because the restored fields do not occur in the overlapping borrower pairs. Consequently the v3 public sample still has no populated maturity, currency, reference-rate, or acquisition-date values. This is an audited source/candidate coverage ceiling. Reviewers should expect the eventual matcher to abstain when spread, lien, and tranche evidence are insufficient.

The alias CSV remains valid and unchanged:

`data/day3/blind_alias_candidates.csv`

SHA-256: `d37f5daeb4eb6cee9e4ddb2e7690978a6ac899c30305b4fda268bb7424a8b64e`

The alias sample is ARCC against NMFC/OBDC (plus explicit no-candidate rows), while the restored supporting facts affected HTGC/TSLX. No facility-level alias display or label definition changed, so no alias rebuild is required.

At this readiness stage: No human labels were accepted, entered, or inspected. The later independent consensus was frozen separately in commit `f6abde5700ae1afc20d342cad335112fdd156817`; its aggregate measurement evaluation is documented in `BLIND_BENCHMARK_RESULTS.md`. No ShadowNAV target reveal or target-error calculation was performed.
