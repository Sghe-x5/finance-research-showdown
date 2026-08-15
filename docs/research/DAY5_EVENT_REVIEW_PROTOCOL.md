# Day 5 outcome-blind event-review protocol

Status: clean-review instructions for the pre-outcome candidate packet

Input: `data/day5/day5_event_review_blind.csv`

## Reviewer isolation

The two reviewers are **Day 5 Event Reviewer F** and **Day 5 Event Reviewer G**. Both must be new, independent, isolated chats that did not construct the Day 5 candidates or perform Day 5 measurement work.

Each reviewer receives only this protocol and a separate untouched copy of the blind CSV. Reviewers must not receive:

- STRICT/SUPPORTING membership or any layer key;
- Day 4 results;
- the other reviewer's labels or notes;
- web, GitHub, SEC, filing, or private-key access;
- target-current structure or any target-current data;
- principal, cost, fair value, FV/principal, marks, movements, predictions, errors, returns, or model performance.

Reviewers must not try to reverse opaque evidence IDs. They decide only from the structural fields printed in the packet. `UNKNOWN` and blank values mean missing evidence, not agreement.

## Required labels

For every row, independently label these four fields with exactly `yes`, `no`, or `uncertain`:

### 1. `source_temporal_same_facility`

Question: do source-prior and source-current represent the same economic facility through time?

- `yes`: borrower, facility/tranche, lien/seniority, currency, funded status, and available terms are consistent with continuation; an ordinary amendment or repricing may preserve identity.
- `no`: evidence identifies different facilities, such as term loan versus revolver/delayed draw, different currency, incompatible lien/seniority, clearly distinct tranche, or refinancing into a genuinely new obligation.
- `uncertain`: identity is plausible but missing/ambiguous fields prevent a defensible decision.

### 2. `source_to_target_prior_same_facility`

Question: do source-current and target-prior represent the same cross-lender economic facility?

- `yes`: the structural evidence identifies the same borrower facility/tranche despite harmless lender-specific wording.
- `no`: it identifies a different facility or tranche, or a material conflict makes same-facility identity untenable.
- `uncertain`: borrower equality is present but facility-level evidence is insufficient or contradictory without resolution.

### 3. `source_aggregation_valid`

Question: are the source-current aggregate and its source-prior comparison each coherent representations of one economic facility?

- `yes`: constituent descriptions and lot count reflect repeated lots/slices of one economic facility.
- `no`: aggregation combines structurally distinct facilities, tranches, currencies, liens, or funded/unfunded instruments.
- `uncertain`: descriptions are too generic or missing to determine whether the grouped lots are coherent.

### 4. `target_prior_aggregation_valid`

Question: is target-prior a coherent representation of one economic facility?

- `yes`: all displayed constituents are compatible lots/slices of one facility.
- `no`: the aggregate combines distinct facilities or incompatible structural terms.
- `uncertain`: displayed evidence does not establish either conclusion.

## Economic-facility principles

- Same normalized borrower is necessary for this packet but never sufficient for same-facility identity.
- `UNKNOWN` is missing evidence and cannot, by itself, support equality or conflict.
- A lot suffix, footnote marker, row suffix, or lender-specific description alone proves neither sameness nor difference.
- Revolver, term loan, delayed-draw, first-lien, second-lien, funded/unfunded, currency, and explicit tranche conflicts matter.
- A spread change alone may be a repricing or amendment and does not automatically create a new facility.
- A maturity extension or other amendment may preserve economic-facility identity when the rest of the structure is consistent.
- A refinancing that replaces the old obligation with a structurally different facility is `no`; ambiguous amendment/refinancing evidence is `uncertain`.
- Catch-all types such as `other_debt` and missing fields require use of the complete displayed descriptions. They must not be treated as exact facility labels.
- When the evidence cannot support a reliable choice, use `uncertain`; do not guess.

## Mechanical inclusion field

After the four checks, fill `include_for_replication` mechanically:

- `yes` only when all four checks are `yes`;
- `no` when at least one check is `no`;
- `uncertain` when no check is `no` and at least one check is `uncertain`.

Use `review_notes` for a short structural explanation, especially for `no` or `uncertain`. Do not introduce additional categories or outcome-based reasons.

## Consensus and adjudication

Reviewer F and Reviewer G work separately and do not see each other's files. Their completed files are compared only after both are final. Every disagreement requires an explicit decision by a separate adjudicator who also has no access to layers, private mappings, target-current data, valuations, or outcomes. There is no majority vote and no automatic preference for `yes`, `no`, or `uncertain`.

Rows labelled `no` or `uncertain` remain in the audit denominator and are never replaced. Consensus may remove a candidate under the locked rule; it cannot add a candidate, alter its pre-review layer, or promote a supporting-only candidate into STRICT.
