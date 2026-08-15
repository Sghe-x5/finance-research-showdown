# Day 5 Phase C structural-review protocol

Input: `data/day5/day5_target_current_structural_review_blind.csv`

## Reviewer isolation

The reviewers are **Day 5 Structural Reviewer I** and **Day 5 Structural Reviewer J**. Both must be new independent reviewers who did not perform or adjudicate the Day 5 event review. They work in separate isolated chats and receive only the structural CSV and this protocol.

They must not receive:

- STRICT/SUPPORTING membership;
- Phase A labels, notes, consensus, or inclusion decisions;
- Day 4 results;
- the other reviewer's answers;
- web, GitHub, SEC, filing, or private-mapping access;
- principal, cost, fair value, FV/principal, marks, movements, predictions, errors, returns, or any outcome calculation.

Opaque evidence IDs are non-navigable references. Reviewers must not try to reverse them. Blank/`UNKNOWN` attributes are missing evidence, not proof of equality.

## Required labels

### `target_current_same_facility`

Use exactly `yes`, `no`, or `uncertain`.

- `yes`: target-prior and target-current represent the same continuing economic facility. Ordinary repricing, maturity extension, or amendment may preserve identity when the rest of the structure remains coherent.
- `no`: the current row is a different tranche/facility, including incompatible debt type, revolver/term/delayed-draw form, lien, currency, funded status, or clearly replacing refinancing.
- `uncertain`: the displayed structural evidence does not support a reliable decision.

Borrower equality alone is insufficient. Lot suffixes and lender-specific wording alone prove neither sameness nor difference. A spread or maturity change alone may be an amendment and does not automatically imply a new facility.

### `target_current_aggregation_valid`

Use exactly `yes`, `no`, or `uncertain`.

- `yes`: the displayed target-current constituents form one coherent economic facility.
- `no`: the aggregate combines distinct facilities, tranches, liens, currencies, or funded/unfunded instruments.
- `uncertain`: descriptions or structural fields are insufficient to judge the grouping.

When no current candidate is displayed, use `uncertain` for aggregation validity rather than inferring validity.

### `position_status`

Use exactly one:

- `continuing`;
- `partial_repayment`;
- `full_repayment`;
- `sale_exit`;
- `refinancing_amendment`;
- `unmatched_disappearance`;
- `uncertain`.

Use `continuing` only when the same facility continues. Use `refinancing_amendment` when structural evidence supports an amendment/refinancing state but exact continuity needs that classification. A blank target-current candidate can support `unmatched_disappearance`, but it does not distinguish repayment from sale without additional permitted evidence; use `uncertain` when that distinction cannot be made.

Use `structural_notes` for a concise explanation based only on displayed structure.

## Consensus

Reviewer I and Reviewer J complete their files independently and do not see one another's labels. Every disagreement requires explicit adjudication by a separate clean adjudicator under the same outcome-blind restrictions. No majority vote, automatic preference, row replacement, or outcome-based decision is allowed.

Every frozen row remains in the denominator. `uncertain` rows are retained and never replaced. Structural consensus must be frozen in a separate commit before any numeric target-current value may be materialized.
