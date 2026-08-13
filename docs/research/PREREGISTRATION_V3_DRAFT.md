# Preregistration v3 — draft measurement guard

Status: **DRAFT ONLY — not approved, not a freeze authorization**.

This file records the corrected unit and power guard before preregistration v3
is finalized. No target same-quarter outcomes were read to produce these
counts. No new ShadowNAV sample may be frozen or revealed from this draft.

## Economic unit

All movement calculations use one aggregated economic facility:

`BDC × quarter_end × borrower × facility/tranche × lien × currency × reference-rate family × spread bucket × maturity month × funded status`.

Lots inside that unit are summed. Individual XBRL slices are never movement
events. Funded/unfunded, revolver/term and different currencies remain separate.

## Global development exclusion

The following borrowers are excluded from every period, not only 2025Q3:

PetVet Care Centers, MRI Software, Anaplan, Viant Medical, Hyland Software,
Fortis Solutions, PPV Intermediate, Ping Identity, Pye-Barker, Auctane and
Medallia.

They remain available only as non-blind development or regression fixtures.

## Movement definition

`abs(source_current_aggregated_mark - source_prior_aggregated_mark) >= 0.005`

The source/current and source/prior rows must pass exact-facility matching.
Events are deduplicated to unique source BDC × quarter × economic facility.

## Pre-reveal power counts

| period | classification | eligible after exclusion | movement eligible IDs | independent movement facilities |
|---|---|---:|---:|---:|
| 2025Q1 | untouched target outcomes | 16 | 3 | 3 |
| 2025Q2 | untouched target outcomes | 15 | 3 | 3 |
| 2025Q3 | development; excluded | 12 | 4 | 4 |

Untouched total: **6 independent movement events**.

Power guard: if the untouched total is below 20 after aggregation,
deduplication, global development-borrower exclusion and exact-facility
filtering, do not freeze or reveal. Expand history and/or the eligible fund and
reporting-order universe first. The current total is 6, so the guard fails.

## Still required before finalization

- literal definitions of every predictor and baseline;
- an approved independent matching benchmark;
- the expanded fund/reporting-order universe;
- a fixed eligible-ID generator and evaluator hash;
- explicit clustering/permutation/leave-one-borrower-out rules;
- approval of the final preregistration before any new freeze.
