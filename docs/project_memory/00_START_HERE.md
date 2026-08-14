# Start Here

## Current project in one sentence

**ShadowNAV** tests whether the first public change in the fair-value mark of a
private-credit facility at one BDC predicts the still-unreported same-quarter mark
of a later-reporting, cross-manager listed BDC that holds the same economic facility.

## Current status as of 2026-08-14

- ShadowNAV is the **provisional flagship**, not a proven strategy.
- Japanese Language Wall was demoted to a **prospective live-data product under
  current budget/access constraints**; it is not dead.
- The Day 2 ShadowNAV pilot is a preserved failed/exploratory pilot.
- Facility matching human benchmark:
  - 58/60 hidden high-confidence positives confirmed;
  - point precision 96.7%;
  - exact one-sided 95% lower bound 89.9%;
  - production precision ≥95% is **not** statistically established.
- Cross-manager benchmark: 11/11 confirmed, but small.
- Untouched source-movement planning set: 37 independent cross-manager source events
  across 2024Q1–2025Q2.
- Day 4 prepared an outcome-blind review packet:
  - 40 source-target observations;
  - 37 source-event clusters;
  - current packet at commit `11cf1f...` must be sanitized because filing URLs can
    indirectly expose protected outcomes.
- Before numeric reveal, the protocol still requires:
  1. sanitized human event-review packet;
  2. independent event review and adjudication;
  3. final preregistration;
  4. sample freeze;
  5. structural non-numeric target-current reveal and freeze;
  6. numeric reveal.

## Read order for a new model

1. `01_PROJECT_GOAL_AND_CONSTRAINTS.md`
2. `02_CURRENT_STATE_2026-08-14.md`
3. `03_PROJECT_TIMELINE_AND_DECISIONS.md`
4. `04_SHADOWNAV_RESEARCH.md`
5. `10_METHODS_PREREGISTRATION_AND_GUARDS.md`
6. `11_DATA_PIPELINE_AND_REPOSITORY_STATE.md`
7. `12_CURRENT_OPEN_QUESTIONS_AND_NEXT_STEPS.md`
8. `13_SOURCE_REGISTRY.md`
9. `20_CLAIMS_LEDGER.md`
10. `21_DO_NOT_REPEAT.md`

## Rule for new chats

Do not propose a new flagship until the current ShadowNAV mechanism test is
completed or explicitly killed. Do not cite the Day 2 `0.068 pp` number as evidence.
Do not reopen Japanese historical-alpha work without a new scalable data-access path.
