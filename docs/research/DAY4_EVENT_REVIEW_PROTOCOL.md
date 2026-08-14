# Day 4 Outcome-Blind Event Review Protocol

## Status and reviewer boundary

This protocol applies only to `data/day4/confirmatory_event_review_blind_v2.csv`. Reviewers must not receive the superseded v1 packet, the private evidence key, direct SEC links, numeric marks, principal, cost, fair value, target-current structure, model predictions, or outcomes.

Two reviewers label the packet independently. They must not compare answers before submitting their first-pass labels. Every disagreement is resolved by explicit adjudication based only on the sanitized packet. Majority voting without a written adjudication is prohibited.

Allowed labels for each measurement check are exactly `yes`, `no`, and `uncertain`.

## General evidence principles

- Use the complete raw facility descriptions and structured fields shown for source-current, source-prior, and target-prior observations.
- A blank or `UNKNOWN` field is missing evidence, not evidence of equality.
- Compatible missing fields do not automatically force `uncertain` when the remaining description uniquely identifies the same facility, but the reviewer must explain why the match remains unique.
- An explicit conflict in debt/equity character, lien, currency, funded status, or facility/tranche type normally prevents a `yes` unless the descriptions reproducibly show a documented amendment or continuation of the same economic facility.
- Numeric suffixes such as “1”, “2”, or “3” may identify disclosure lots, not contractual tranches. A suffix alone is never sufficient for either `yes` or `no`.
- Catch-all values such as `other_debt` and `unknown` provide weak evidence. They cannot override an explicit revolver, delayed-draw, term-loan, lien, currency, or funded-status conflict.
- A spread change over time can be consistent with the same facility after repricing or amendment. Across contemporaneous lenders, a spread conflict requires `uncertain` or `no` unless the raw descriptions and remaining terms establish the same tranche and a reproducible timing explanation exists.
- A refinancing that extinguishes and replaces the obligation is a different facility. An amendment or repricing that continues the same legal/economic facility may remain the same facility when the packet supplies sufficient identifying evidence. If replacement versus continuation cannot be distinguished, label `uncertain`.

## Check 1 — `source_temporal_same_facility`

Question: do `source_prior` and `source_current` represent the same source-fund economic facility across adjacent reporting periods?

### `yes`

- Borrower identity matches exactly in the packet.
- The facility/tranche descriptions are compatible across time.
- No explicit conflict indicates a different lien, currency, funded status, or facility type.
- Changes in spread, maturity, naming, or lot suffix are explainable as continuation, amendment, repricing, or disclosure formatting rather than replacement.

### `no`

- The rows identify different contractual facilities, such as revolver versus term loan, first lien versus second lien, funded versus unfunded, different currency, or a clearly replaced/refinanced tranche.
- The description shows repayment and origination of a new facility rather than continuation.

### `uncertain`

- The borrower matches but the packet lacks enough tranche detail to distinguish continuation from replacement.
- `UNKNOWN` or catch-all fields remove the evidence needed to resolve a material conflict.
- A maturity/spread change could represent either amendment or refinancing and the descriptions do not resolve it.

Required notes: cite the compatible or conflicting description, facility type, lien, spread, maturity, funded status, and any relevant lot suffix.

## Check 2 — `source_to_target_prior_same_facility`

Question: do `source_prior` and `target_prior` represent the same economic facility held by different managers before the movement event?

### `yes`

- Exact normalized borrower identity matches.
- The cross-lender descriptions identify the same facility/tranche.
- Available lien, currency, reference rate, spread, maturity, funded status, and facility type are compatible.
- Any missing field does not conceal a plausible competing facility in the displayed descriptions.

### `no`

- An explicit term identifies different facilities: different lien/seniority, revolver versus term loan, funded versus unfunded, different currency, equity versus debt, or a clearly different tranche.
- A spread/maturity combination and descriptions jointly identify a separate facility rather than lender-specific reporting variation.

### `uncertain`

- The same borrower has multiple plausible facilities and displayed terms do not uniquely identify one.
- Catch-all or unknown facility types prevent tranche-level resolution.
- Spread changes or lender descriptions are compatible with either the same tranche or separate tranches.

Required notes: explain why the displayed terms identify one cross-lender facility or why a competing facility remains possible.

## Check 3 — `source_aggregation_valid`

Question: are the source-current and source-prior constituent descriptions valid aggregations of one economic facility at each date?

### `yes`

- Every constituent description belongs to the displayed facility/tranche.
- Multiple lots are disclosure slices of the same economic facility, not separate revolver, term, delayed-draw, lien, currency, funded-status, or maturity tranches.
- Lot count and constituent descriptions are internally consistent.

### `no`

- The aggregation combines distinct facilities or tranches.
- Constituents contain explicit conflicts in facility type, lien, currency, funded status, or contractual identity.
- An issuer total or catch-all position is combined with detailed facilities in a way that double-counts exposure.

### `uncertain`

- Multiple constituents are shown but their descriptions are too generic to establish whether they are lots or distinct facilities.
- Numeric suffixes are the only evidence of grouping.
- Missing fields prevent evaluation of an otherwise plausible aggregation.

Required notes: identify the constituent descriptions and state whether each represents a lot or a separate facility.

## Check 4 — `target_prior_aggregation_valid`

Question: are the target-prior constituent descriptions a valid aggregation of one target economic facility before the source event?

Apply the same `yes`, `no`, and `uncertain` rules as `source_aggregation_valid`, specifically checking that target-prior lots do not combine separate lien, currency, revolver/term/delayed-draw, funded/unfunded, or maturity tranches.

Required notes: identify any constituent-level conflict or explain why multiple descriptions are disclosure lots of one facility.

## Inclusion and adjudication

`include_for_confirmatory_test=yes` is allowed only when the final adjudicated consensus is `yes` for all four checks:

1. `source_temporal_same_facility`;
2. `source_to_target_prior_same_facility`;
3. `source_aggregation_valid`;
4. `target_prior_aggregation_valid`.

If any check is `no`, inclusion is `no`. If no check is `no` but at least one is `uncertain`, inclusion is `uncertain`. Reviewers may not use knowledge of a source movement size, a target-current position, a mark, or an outcome to resolve uncertainty.

The adjudication record must preserve both independent labels, the final consensus label, a concise evidence-based reason, reviewer identities, and the consensus file SHA-256. Failed and uncertain observations remain in the denominator and cannot be replaced.
