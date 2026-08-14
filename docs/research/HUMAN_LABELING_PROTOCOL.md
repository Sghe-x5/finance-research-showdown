# Human labeling protocol and consensus freeze

Date: 2026-08-14

## Scope

This package freezes the human consensus labels for:

1. the 120-row blind facility benchmark v3;
2. the 128-row blind borrower-alias audit.

No private model mapping, hidden stratum, predicted label or private key was opened during labeling, comparison or adjudication.

## Roles

- Reviewer B: clean Claude chat, independently labeled the two blind CSVs.
- Reviewer C: clean ChatGPT chat, independently labeled the same two blind CSVs.
- Adjudicator: the pre-existing Claude project chat, received only disagreement rows with reviewer identities anonymized as X/Y.

## Source blind files

- `blind_facility_pairs_v3.csv`
  - expected SHA-256: `f4ec256bf4502f5cb6979ff218d3b5457481f0ae21bdb75841d4bb3c1d357c2b`
  - 120 rows.
- `blind_alias_candidates.csv`
  - expected SHA-256: `d37f5daeb4eb6cee9e4ddb2e7690978a6ac899c30305b4fda268bb7424a8b64e`
  - 128 rows.

The independent reviewer outputs had identical blind IDs, row order and non-review columns.

## Independent-review agreement

### Facility

- Exact agreement: 111/120 = 92.5%.
- Disagreements adjudicated: 9.
- Cohen's kappa before adjudication: 0.8763.

### Alias

- Exact joint agreement on borrower + facility: 73/128 = 57.0%.
- Disagreements adjudicated: 55.
- Cohen's kappa before adjudication: 0.1129.

## Adjudication policies

The adjudicator declared these policies before applying them to the disputed rows:

1. A blank candidate side is a non-observation, not evidence that no match exists.
   - Final label: `uncertain / uncertain`.
   - Such rows must be excluded from precision/recall denominators and must not be counted as true negatives.
2. Spread differences of 10 basis points or more are treated as a contractual conflict.
   A 1-bp difference is treated as compatible rounding.
3. Parser catch-all types such as `other_debt` and `secured_unspecified` are not treated as economic facility types.
   Catch-all versus a concrete type is generally `uncertain`, not automatically a different facility.
4. Numeric lot suffixes do not prove a different facility by themselves.
5. In the NAMSA/Cardinal alias cluster, direct co-mention of Cardinal entities was treated as evidence of the same borrower group; facility identity was then assessed separately.

These are post-blind adjudication policies, not pre-registered model rules.

## Final consensus distributions

### Facility labels

{
  "same_facility": 64,
  "uncertain": 25,
  "same_borrower_different_facility": 31
}

### Alias borrower labels

{
  "no": 71,
  "yes": 18,
  "uncertain": 39
}

### Alias facility labels

{
  "not_applicable": 71,
  "uncertain": 41,
  "no": 16
}

Blank candidate rows: 37.  
Nonblank candidate rows: 91.  
Blank-row final labels: {('uncertain', 'uncertain'): 37}.

## Interpretation constraints

- The facility sample is stratified and cannot be used for unweighted population accuracy.
- Facility evaluation should report precision, unresolved/uncertain rate, coverage and manager strata.
- Population recall is not identified by this benchmark; recall remains conditional on candidate generation/blocking.
- Blank alias candidate rows are excluded as non-observations.
- The alias audit should report nonblank row-level results and source-borrower group-level results separately.
- Human consensus must be committed and hashed before any private mapping is opened.
