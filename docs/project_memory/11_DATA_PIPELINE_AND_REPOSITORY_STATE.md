# Data Pipeline and Repository State

## Repository

`https://github.com/Sghe-x5/finance-research-showdown`

## Important historical references

### Day 1

- Branch: `research/day1-showdown-reconciled`
- Commits:
  - `b35443dab65c4853752cf1dbe8259ad52bd55d27`
  - `78de52baf8d01ee3bb9734b811b30805cb7d9786`
- Tag: `showdown-day1-reconciled-2026-08-12`

### Day 2

- Branch: `research/day2-mechanism-pilot`
- Freeze: `a495f3936abf766e484a40df035c9c5e549abdae`
- Results: `0cb5f8c2b46405d4358b765178eca52f947e6615`
- Tag: `showdown-day2-mechanism-2026-08-13`

### Day 3

Key commits:
- `00ee149b3708d6d24c546d9322e8993de82f3ee5`
- `05f982bd76da1499b10366bb52ae0281a138ec96`
- `60644ce1b50ec3b47774fed90369d6b67fc00657`
- human consensus freeze: `f6abde5700ae1afc20d342cad335112fdd156817`
- matcher evaluation: `9b0f85a736bb2aec6e0716e6238d4e1fe82987e9`

### Day 4

- Branch: `research/day4-shadow-nav-confirmatory`
- Pre-reveal preparation: `11cf1f44055beb88b1a0fed4c5bf09d5e2ae3414`

## Current pipeline

```text
SEC BDC ZIPs
→ submission/SOI/supporting-fact parsing
→ economic_facility_v2 aggregation
→ borrower blocking
→ facility candidate classification
→ reporting-order chronology
→ source movement construction
→ outcome-blind human review
→ freeze/reveal protocol
```

## Current dataset facts

- SEC official history used from 2023Q4 onward.
- Current 19-fund universe.
- 37 untouched cross-manager source movement facilities.
- 40 source-target review observations.
- 37 source-event clusters.
- Human matcher benchmark:
  - 120 blind facility pairs;
  - 128 alias candidates;
  - human consensus frozen before hidden mapping evaluation.

## Private files that must never enter Git

- `private/day3/blind_facility_key.json`
- `private/day3/blind_alias_key.json`
- any future target-outcome key;
- API keys;
- raw third-party licensed data;
- personal SEC contact email;
- local `.env`.
