# Japanese Language Wall Research Memo

## Original hypothesis

Prime Market simultaneous Japanese/English disclosure became mandatory in April 2025.
Standard Market did not receive the same treatment.

Potential natural experiment:

```text
post-April-2025
× prior English lag
× Prime/Standard
× foreign ownership
```

If language processing causes delayed incorporation, the strongest decline in drift should be
among previously weak-English Prime firms with high foreign ownership.

## Why it was attractive

- recent institutional change;
- clear candidate slow actor: overseas investors;
- thousands of disclosure events;
- possible difference-in-differences/triple-difference design;
- useful normalized English event feed even at null.

## What was verified

- Official JPX rule: simultaneous English disclosure for domestic Prime companies from April 2025.
- Yanoshin unofficial API provides historical event index queries by date/range.
- Thousands of forecast-revision titles exist.
- Daily-data research could target T+1…T+10 rather than intraday latency.

## What failed under current constraints

- Historical TDnet document links in the tested sample returned 404.
- Wayback returned no useful snapshots in the frozen gate.
- Free J-Quants access was blocked under the researcher's current regional/network conditions.
- A scalable legal historical old/new numerical forecast path was not demonstrated.
- Treatment fields (full/summary/none, English timestamp, prior behavior, foreign ownership)
  were not reconstructed at scale.

## Current status

Demoted to:

> live Japanese disclosure normalization product under current constraints

Retained assets:
- 2023–2026 event index;
- timestamps;
- security codes;
- event titles/classes;
- 4,448 raw and 3,999 clean revision-intent events in the valid window;
- prospective live collection design.

Reactivation conditions:
- working J-Quants access;
- licensed historical TDnet;
- institutional data source;
- scalable issuer-IR archive recovery with acceptable terms;
- or prospective collection long enough to support a live study.
