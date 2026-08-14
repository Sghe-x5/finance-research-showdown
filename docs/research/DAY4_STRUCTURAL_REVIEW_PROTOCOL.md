# Day 4 Phase C Structural Review Protocol

## Purpose and isolation

Phase C decides whether each frozen target-prior facility can be mapped to the displayed target-current non-valuation structure. It does not evaluate ShadowNAV and does not use principal, cost, fair value, FV/principal, any mark, source movement size, prediction, error, or return.

Two new clean reviewers are required:

- **Structural Reviewer D**;
- **Structural Reviewer E**.

Each reviewer must work in a separate, newly created isolated chat and must not have performed Phase A. Each receives only:

1. `data/day4/target_current_structural_review_blind.csv`;
2. this protocol.

Reviewers must not receive Phase A labels, notes, adjudication, consensus, inclusion decisions, source movement sizes, numeric valuation fields, private mappings, or any outcome file. They must not use web search, GitHub, SEC/EDGAR, issuer websites, or the opaque evidence-ID mapping. The opaque IDs are integrity handles, not research links.

## Frozen rows

The packet contains exactly 37 frozen `review_observation_id` values in 34 source-event clusters. No row may be dropped, replaced, duplicated, or substituted. A row with no displayed target-current candidate remains in the packet and must receive an appropriate uncertainty or disappearance classification.

Do not infer anything from row order or opaque evidence IDs.

## Review fields

### 1. `target_current_same_facility`

Allowed labels: `yes`, `no`, `uncertain`.

- **yes** — the target-current structure is the same economic facility as the target-prior structure. Borrower identity, debt facility/tranche type, lien, funded status, and any available currency, reference-rate, spread, maturity, and constituent wording jointly support continuity. A documented-looking repricing or amendment can remain the same facility when the structural continuity is otherwise clear.
- **no** — the displayed target-current structure is a different contractual facility or tranche. Examples include revolver versus term loan, first lien versus second lien, funded term debt versus an unfunded commitment, or a clearly different facility identifier when another prior relationship is not supported.
- **uncertain** — the visible fields do not distinguish continuity from a different facility. Use this when the target-current structure is absent, when several interpretations remain plausible, or when unknown fields remove the attributes needed to decide.

Evidence required: cite the specific displayed prior/current fields that determine the label. Do not rely on the shared borrower name alone.

### 2. `target_current_aggregation_valid`

Allowed labels: `yes`, `no`, `uncertain`.

- **yes** — the displayed target-current constituent descriptions and lot count represent one coherent economic facility under `economic_facility_v2`. Multiple lots may be grouped only when their complete facility descriptions and structural attributes are compatible.
- **no** — the target-current aggregation visibly combines distinct facilities or tranches, such as different lien levels, funded statuses, facility types, currencies, reference-rate families, spreads, maturities, or conflicting tranche wording.
- **uncertain** — there is insufficient displayed detail to tell whether the aggregation is valid, including an absent target-current candidate.

Evidence required: refer to constituent descriptions, aggregation lot count, and any structural conflicts. A numeric suffix or lot suffix alone neither proves nor disproves a common facility.

### 3. `position_status`

Use exactly one label:

- `continuing` — the same facility is present in the target-current structure, including ordinary repricing that does not create a new economic facility;
- `partial_repayment` — the same facility remains, while displayed non-valuation structure clearly shows that only part of the prior position or constituent set continues;
- `full_repayment` — the displayed non-valuation evidence explicitly identifies repayment and no continuing facility;
- `sale_exit` — the displayed non-valuation evidence explicitly identifies a sale or exit rather than repayment;
- `refinancing_amendment` — the prior facility has a structurally identifiable successor produced by refinancing or a material amendment, rather than simple unchanged continuation;
- `unmatched_disappearance` — no exact target-current structural candidate is displayed and the packet cannot attribute the disappearance to repayment, sale, or refinancing;
- `uncertain` — more than one status remains plausible or the visible structure is insufficient.

Principal is intentionally hidden. Do not infer partial or full repayment from an imagined balance change. When repayment versus sale versus unmatched disappearance cannot be distinguished from the packet, use `unmatched_disappearance` or `uncertain`, not outside knowledge.

### 4. `structural_notes`

Write a short, decision-focused explanation naming the prior/current structural fields used. Do not include links, accessions, guesses about marks, numerical valuation estimates, or research performed outside the packet.

## Special cases

- **Unknown fields:** `UNKNOWN` or blank values are missing evidence, not matches. They may be compatible, but never create a `yes` by themselves.
- **Lot suffixes:** suffixes such as lot numbers or lettered slices may be disclosure formatting. Treat them as the same facility only when the full description and other structural fields support that conclusion.
- **Catch-all facility types:** `other_debt` is weak evidence. Require lien, funded status, identifier/tranche wording, spread, maturity, or another displayed discriminator.
- **Spread changes:** a spread change can be a repricing or amendment and does not automatically mean a different facility. Large or unexplained changes combined with other structural changes may require `refinancing_amendment` or `uncertain`.
- **Amendments and refinancings:** continuity of borrower and lien alone is insufficient. Use `refinancing_amendment` when the displayed structure supports a successor relationship but not unchanged contractual continuity. Use `uncertain` when a successor cannot be distinguished from a separate facility.
- **Several target facilities for one borrower:** match on the complete facility/tranche structure. Borrower equality alone is never enough.
- **No displayed target-current structure:** keep the row. Normally label both mapping checks `uncertain` and use `unmatched_disappearance` or `uncertain` for status, depending on whether disappearance itself is clear.

## Independence and adjudication

Reviewers D and E complete their files independently. They do not see each other's labels or notes. After both files are frozen and hashed, disagreements are sent to a separate adjudicator who receives only the structural packet, this protocol, and the two conflicting structural decisions.

No majority vote substitutes for explicit adjudication. Adjudication also occurs without valuation numbers, marks, predictions, errors, Phase A material, web access, or private evidence mappings.

The final structural consensus must preserve all 37 frozen IDs. Uncertain rows stay reported and are never replaced. Only after that consensus is committed and hashed in a separate structural-mapping freeze can Phase D numeric reveal be considered.
