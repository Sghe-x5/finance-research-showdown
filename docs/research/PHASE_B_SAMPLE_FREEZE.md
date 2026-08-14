# Phase B Confirmatory Sample Freeze

## Freeze decision

Claude formally returned **APPROVE FOR PHASE B FREEZE** on 2026-08-15 after confirming that the three blocking methodological corrections were complete. This Phase B record freezes an outcome-blind ShadowNAV sample; it is not a structural reveal, numeric reveal, or result.

The freeze contains exactly:

- 37 included source-target observations;
- 34 independent source-event clusters;
- 20 unique normalized borrowers;
- only cross-manager observations;
- untouched periods 2024Q1–2025Q2;
- no 2025Q3 observations;
- no borrower aliases;
- three uncertain observations excluded and retained without replacement.

The borrower-cluster distribution is 13 borrowers with one cluster, three with two, two with three, one with four, and one with five. The maximum contribution is five clusters. The duplicate-vote audit was rerun before this freeze and found zero duplicate identities.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| Final Phase A human consensus | `2a0c763e423b5616b3f9093f54a0073d5e8577b0fe4f5769fb2ca60ff26f9591` |
| Included sample | `011da2ab9ccc39f5c2530295fee1b555377f4a2b36a302e45183873af603a670` |
| Ordered included observation IDs | `27794be82f7768a6695f59154d011f9c05d89aae1cfdc660ac1b2fec1d6b92ca` |
| Ordered unique source-event cluster IDs | `506a15321c58119c60836f7311e533cbf6e12b80f036a3460d0f6762cdbe119c` |
| Borrower-cluster distribution | `cfd3b83d03c47041427dce98f731e1c1d9423408003aac946a10339d26a0344d` |
| Duplicate-vote audit | `d62f9e30352ffb8b9574858b30881032022067c0a69c5c8d474695722d0a96e1` |
| Final preregistration | `6b19ee878c103122ae1734bfbd480aec2fdd88ae35b6368f24655a26b552fcdc` |
| Frozen evaluator | `bcea297f43603316d4d3bc5fef9762bc2749eaddf36a3253222af66e8f132615` |
| Sample-generation script | `1afae3c8905b2189bbbbc6bf498545e42256b14ec87718e3c03b1ee6b6f52590` |

The machine-readable record is [`data/day4/confirmatory_sample_freeze.json`](../../data/day4/confirmatory_sample_freeze.json). Observation-ID hashes use UTF-8 values joined by LF with a final LF. Observation order is the frozen CSV order; unique cluster order is first occurrence in that sample.

## Protected boundary

No target-current structural field, principal, cost, fair value, FV/principal ratio, source or target mark, prediction, or error was opened or stored in this commit. No numeric evaluation was run. No results tag was created.

Only after this Git commit exists may the separate Phase C commit materialize a non-numeric structural packet for exactly these 37 frozen observation IDs. Phase D remains prohibited until an independently reviewed structural consensus is frozen and a complete authorization record passes every evaluator check.
