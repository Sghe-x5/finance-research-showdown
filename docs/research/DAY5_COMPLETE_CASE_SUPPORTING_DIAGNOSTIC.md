# Day 5 complete-case supporting diagnostic

Status: **POST_REVEAL_EXPLORATORY_COMPLETE_CASE_SUPPORTING**
Boundary: **CANNOT CHANGE OFFICIAL DAY5 STATUS**

The diagnostic applies no new outcome filter. It uses exactly the frozen SUPPORTING and STRICT memberships, event-review `include=yes`, structural `position_status=continuing`, and the rows whose four marks were already present in the frozen revealed-outcome file. No row is clipped, winsorized, shrunk, replaced, or selected by performance.

## SUPPORTING complete cases

- Observations / independent clusters / borrowers: **45 / 45 / 22**.
- Cluster MAE B0: **0.010383834051111119**.
- Cluster MAE ShadowNAV: **0.015876849817777778**.
- Mean paired error difference, ShadowNAV minus B0: **+0.005493015766666659**.
- Relative “improvement”: **−0.5289968752995317**, meaning ShadowNAV MAE is about 52.9% worse.
- Borrower-clustered one-sided permutation p: **0.9328406715932841**.
- Borrower bootstrap 95% CI: **[−0.001156068629722242, +0.01341551780337863]**.
- Leave-one-borrower-out range: **[+0.0036869479431818064, +0.007657100328205128]**; every value is positive.
- Periods with negative paired difference: **1 of 7**.
- All six Day 4 diagnostic criteria: **false**.

This reverses the Day 4 point-estimate direction. A positive paired difference means ShadowNAV has greater absolute error than persistence.

## STRICT complete cases

Label: **POST_REVEAL_EXPLORATORY_STRICT_UNDERPOWERED**

- Observations / independent clusters / borrowers: **12 / 12 / 8**.
- Cluster MAE B0: **0.01529400557500001**.
- Cluster MAE ShadowNAV: **0.03439617358333335**.
- Mean paired difference: **+0.019102168008333337**.
- Relative “improvement”: **−1.2489970606234282**, meaning ShadowNAV MAE is about 124.9% worse.
- Permutation p: **0.979980200197998**.
- Borrower bootstrap 95% CI: **[+0.004622970258823496, +0.03997554023400002]**.
- Leave-one-borrower-out range: **[+0.013115092372727262, +0.0245217286777778]**; every value is positive.
- Periods with negative paired difference: **0 of 5**.
- All six diagnostic criteria: **false**.

The STRICT layer remains far below the frozen 25-cluster / 15-borrower guard and cannot be called a confirmatory replication result. Its direction nevertheless agrees with the broader SUPPORTING diagnostic: the unshrunk transferred change worsens marks relative to persistence.

## Concentration

For SUPPORTING, the largest absolute signed contributors are:

- borrower: `opco borrower`, 15.2% of absolute borrower-group contribution;
- period: 2024Q1, 32.6%;
- source-target pair: CSWC→WHF, 18.3%.

Removing any one borrower leaves the mean paired difference positive. Removing any one period also leaves it positive, as does removing any one source-target pair. The reversal is therefore not entirely one borrower, period, or fund pair.

The full deterministic output, group tables, leave-one-group-out values, and diagnostic criteria are in `data/day5_post_reveal/complete_case_supporting_results.json`.
