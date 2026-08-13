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
