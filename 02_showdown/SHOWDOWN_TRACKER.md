# Showdown tracker — reconciled Day 1

Frozen: **2026-08-12**, before manual Day 2 outcomes.

## Decision status

**Flagship not selected.** ShadowNAV and Japanese Language Wall remain alive.
Old dashboard scores (89/82) and priors (52/48) are explicitly not selection
criteria.

## ShadowNAV

The reporting-order calendar now verifies the content of SEC EX-99 exhibits.
It excludes earnings-date, scheduling and dividend-only announcements even when
SEC labels the filing Item 2.02.

Known regression cases now excluded:

- OBDC 2025Q2 filing accepted `2025-07-01T12:00:20Z`;
- GBDC 2025Q2 filing accepted `2025-07-07T20:46:45Z`.

Their verified first events are OBDC's 10-Q at `2025-08-06T20:05:51Z` and
GBDC's EX-99 results release at `2025-08-04T20:02:24Z`.

### Corrected listed-BDC windows (provisional)

Five complete quarters, 15 listed funds, 105 ordered early→late pairs per
quarter:

| quarter | n | p25 days | median days | p75 days | >1d | >3d | >5d |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2025Q1 | 105 | 1.925 | 5.004 | 8.009 | 91 | 68 | 54 |
| 2025Q2 | 105 | 1.977 | 5.992 | 13.243 | 93 | 69 | 58 |
| 2025Q3 | 105 | 2.007 | 7.038 | 12.978 | 88 | 68 | 60 |
| 2025Q4 | 105 | 5.626 | 12.018 | 20.588 | 95 | 84 | 82 |
| 2026Q1 | 105 | 1.025 | 3.015 | 6.978 | 84 | 54 | 37 |
| **All** | **525** | **1.993** | **5.999** | **12.988** | **451** | **343** | **291** |

This is the regenerated SEC/EX-99 distribution; it remains provisional until
possible IR-only releases are manually checked. Windows exist, but they are
only calendar opportunity sets. The main Day 2 gate
is the number of **exact same facilities** after matching lien, facility type,
currency, base rate/spread, maturity and tranche details.

The core `non-traded-first` story remains refuted. Across the five complete
quarters, all 20 pilot observations occurred after the listed-fund median; 17
occurred after at least 13 of 15 listed BDCs. Niche late-target cases are not the
core thesis.

## Japanese Language Wall

| period | items | forecast-revision title matches | PDF alive | XBRL alive |
|---|---:|---:|---:|---:|
| 2023-01-10—2023-01-31 | 4,031 | 313 | 0/2 | 0/2 |
| 2023-07-01—2023-07-31 | 5,380 | 237 | 0/2 | 0/2 |
| 2024-01-10—2024-01-31 | 4,027 | 296 | 0/2 | 0/2 |
| 2024-07-01—2024-07-31 | 5,848 | 229 | 0/2 | 0/2 |
| 2025-01-10—2025-01-31 | 4,162 | 304 | 0/2 | 0/2 |
| 2025-07-01—2025-07-31 | 6,216 | 244 | 0/2 | 0/2 |

The historical index is alive. All tested old PDF/XBRL URLs returned 404 after
redirect, so underlying historical documents are not shown to be available.
The main Day 2 gate is reproducible recovery of numerical old/new earnings
forecast revisions and event-level Japanese/English treatment.

---

# Day 2 mechanism pilot — 2026-08-13

**Flagship still not selected.** Fixed seed `20260813`; freeze commit
`a495f39`.

## ShadowNAV Day 2

| stage/gate | result |
|---|---:|
| Official SEC archives | 2025 Q3 + Q4 |
| Raw SOI rows in 19-fund universe | 73,845 |
| Normalized facility rows | 54,285 |
| Candidate pairs | 13,672 |
| Locked match benchmark | 240 |
| High-confidence same-facility precision | Not adjudicated; reported 100% is an upper bound by construction |
| Eligible nowcast IDs | 45 |
| Frozen IDs before outcomes | 15 |
| Unique borrower/source/target clusters after reveal | 11 |
| Contaminated fixtures in estimates | 0 |

Frozen sample hash:
`6932fa6156029562badf9abf98605ce81fd240aee5f723a95dfbbd3dbe7c7c5f`.

| baseline | n | MAE pp | RMSE pp | median AE pp |
|---|---:|---:|---:|---:|
| B0 unchanged target mark | 15 | 0.3270 | 0.7668 | 0.0000 |
| B1 target momentum | 0 | — | — | — |
| B2 co-holder median | 15 | 0.3901 | 0.7775 | 0.0000 |
| B3 earliest exact co-holder | 15 | 0.8101 | 1.6034 | 0.0000 |
| B4 prior cross-lender median | 15 | 0.5648 | 1.0366 | 0.0000 |
| Prior-gap adjusted source | 15 | 0.0680 | 0.2348 | 0.0000 |

The naive earliest-co-holder rule failed against persistence. The 0.0680 pp
adjusted result is a failed-pilot diagnostic, not confirmatory evidence: its
definition changed after freeze, 13/15 predictions equal B0, and its entire
advantage is driven by PetVet. Leave-one-borrower-out eliminates the advantage;
without PetVet both adjusted and B0 MAE are 0.0696 pp. Four frozen IDs are also
repeated XBRL slices. The old sample remains untouched and will not be
recomputed. B1 and categorical transition tests lacked usable observations.
Same-manager/JV/appraiser exclusions were not observable.

## Japan Day 2

| stage/gate | result |
|---|---:|
| Historical forecast-revision universe | 678 |
| Frozen sample | 40 |
| Supplied seed rows retained provisionally | 8 |
| New rows independently recovered | 0/32 |
| Provisional total recovery | 8/40 (20%) |
| Old official/Tdnet links | 32/32 returned 404 |
| IRBank validation | HTTP 403 |
| First-ten treatment completion | 0/10 |

Locked Japan ID hash:
`5cc23bf6b10c149b16d479c455db8cf8df20aea1eec70e4d32cc3f243d30bbe4`.
Failures remain in the denominator and no price event study was run.

## Day 2 decision

No flagship. ShadowNAV did not clear an independently adjudicated matching gate
and did not beat persistence outside one PetVet movement event. Japan did not
clear reproducible numerical recovery or treatment classification. Full
evidence, the external audit and blockers are recorded in
`docs/research/DAY2_RESULTS.md` and
`docs/research/05_DAY2_EXTERNAL_AUDIT.md`.

---

# Day 3 measurement repair — pre-reveal, 2026-08-14

No new frozen nowcast sample, no reveal and no result tag.

| item | status |
|---|---|
| SEC history | 8 acceptance archives, 2024Q1–2025Q4 |
| Aggregated economic facilities | 188,999 under exact-key `economic_facility_v2` |
| Aggregated candidate pairs | 40,340 |
| Aggregation audit | 100 v1 multi-lot groups + 100 issuer-total drops; manual review pending |
| Blind match sample | corrected 120 unlabeled (60/30/30); old 60-row file superseded; 11 seen borrowers excluded globally |
| Alias audit | corrected debt-only blind file: 30 ARCC borrowers, 128 shuffled candidate rows; scores private |
| Untouched movement events | 2025Q1: 3; 2025Q2: 3; total 6 < guard 20 |
| Reveal permission | **No — expand fund/reporting-order universe first** |
| Old Japan Day 3 freeze | `invalid_window_design`, retained |
| Valid Japan universe | 2024-09-01…2026-05-15; 4,448 raw / 3,999 clean |
| Japan universe ID file | 3,999 IDs; original frozen universe SHA matched exactly |
| Valid Japan freeze | 20 IDs; hash `3a510bef6cfe937ac6eb192fef87ff311ac85826927fdd30053a9586f3cdc5a6` |
| Japan intermediate status | TDnet 0/20; Wayback 0/20; issuer IR not attempted; J-Quants pending |
| Japan gate verdict | Not evaluated; DocType probe then J-Quants pending local API key |

Full pre-reveal evidence: `docs/research/DAY3_MEASUREMENT_REPAIR.md`.
Draft guard only: `docs/research/PREREGISTRATION_V3_DRAFT.md` (not approved;
does not authorize freeze or reveal).
