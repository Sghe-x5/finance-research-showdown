# Field Lineage and Manager Audit

Status date: 2026-08-14. This is a pre-reveal measurement audit. No human labels, hidden matcher strata, private v2 keys, target-current outcomes, freeze, or reveal were used.

## Field-lineage scope

The audit checked all eight official SEC BDC archives (`2024q1` through `2025q4`) and verified the complete ten-member ZIP inventory: `soi.tsv`, `sub.tsv`, `tag.tsv`, `cal.tsv`, `pre.tsv`, `num.tsv`, `txt.tsv`, `non.tsv`, `readme.htm`, and `bdc_metadata.json`. Counts were restricted to the 19-fund universe and qualifying facility-like SOI rows. No value was inferred from investment-identifier prose.

| Field | Official-source finding | Exact loss stage | Original normalized | Corrected normalized | Aggregation/export loss | Diagnosis |
|---|---|---|---:|---:|---|---|
| maturity | Direct SOI values existed; additional `InvestmentMaturityDate` / `InvestmentDueDate` facts existed in `datasets/txt.tsv` | supporting XBRL facts → normalized join | 12,668 | 14,988 | 0 / 0 | `join_loss`; 2,320 exact-key values restored |
| currency | `Currency Axis` exists in the schema, but there were zero explicitly tagged currency values on qualifying facility rows and zero investment-context currency facts | official source coverage | 0 | 0 | 0 / 0 | `source_absent` for the audited facility population |
| reference_rate | Official rate-type members existed; the old canonicalizer discarded some recognized families and supporting facts were not joined | raw SOI → normalized parser, plus small supporting join | 12,430 | 12,439 | 0 / 0 | `parser_loss`; 9 missing values restored and 2 inferred values replaced by official members |
| acquisition_date | Direct values existed; additional `InvestmentAcquisitionDate` and issuer extension facts existed in `datasets/txt.tsv` | supporting XBRL facts → normalized join | 3,077 | 6,426 | 0 / 0 | `join_loss`; 3,349 exact-key values restored |

The raw audit records 159 direct reference-rate rows whose official value did not survive the old normalizer. Most are generic values such as “floating rate,” not a usable benchmark family; the repair only populated 9 unambiguous families and did not manufacture a family from prose. There were no silent losses in economic aggregation and no blind-export losses.

The corrected join key is exact: archive, accession (`adsh`), observation date, and the explicitly tagged `Investment Identifier Axis` member. Ambiguous multi-value keys are not applied. Corrected normalized and aggregate data remain in the ignored external cache; only method, metadata, counts, and hashes are committed.

## Conditional blind action

Because official fields were lost before normalization, `blind_facility_pairs_v2.csv` is now marked `superseded_parser_or_join_omission`. Its bytes and SHA-256 remain unchanged, and its private key was not opened.

A corrected candidate universe was generated from the repaired normalized data. Its bytes happen to be identical to the old candidate universe because the restored TSLX/HTGC fields do not occur in the exact borrower-overlap pairs. Nevertheless, the required fresh seed and sample were applied. Clean reviewers must receive `data/day3/blind_facility_pairs_v3.csv`, with 60/30/30 hidden strata, randomized sides, no labels, and all 11 seen borrowers excluded.

The v3 sample still has zero coverage for all four fields. That is now an audited candidate-population information ceiling rather than an untested pipeline omission. The matcher must therefore expose `high-confidence`, `uncertain`, and `abstain` decisions; future reporting must include precision, recall within blocking, coverage, and abstention rate.

The alias benchmark does not require rebuilding. Its source is ARCC and its populated candidates are only NMFC/OBDC; none of the restored HTGC/TSLX supporting fields enters its rows or changes its facility-level display.

## Canonical manager map

The 19-row map uses each fund’s official 2024Q4 SEC periodic filing as evidence and groups legal advisers under a canonical manager platform. The minimum required relationships are confirmed:

- ARCC / ASIF: Ares Management;
- OBDC / OCIC: Blue Owl Credit;
- BCRED / BXSL: Blackstone Credit & Insurance.

Legal-adviser names and the exact official SEC filing URL are retained in `data/day3/bdc_manager_map.csv`. Internally managed HTGC and MAIN are each treated as their own canonical manager.

## Same-manager versus cross-manager

| Layer | Same-manager | Cross-manager | Cross-manager share |
|---|---:|---:|---:|
| Full facility candidate universe | 18,252 | 22,088 | 54.75% |
| Blind facility v3 | 84 | 36 | 30.00% |
| Eligible pre-reveal observations | 0 | 131 | 100.00% |
| Untouched movement observations | 0 | 40 | 100.00% |
| Untouched unique movement source facilities | 0 | 37 | 100.00% |

The 37 cross-manager untouched movement facilities exceed the decision guard of 20. Cross-manager is therefore permitted as a primary preregistration stratum, but this audit does not authorize a freeze or reveal. The blind sample’s 70% same-manager composition remains important for interpreting its future human precision estimate.

## Periodic-fallback audit

All 100 periodic fallback rows were checked against every earlier 8-K in the report-period-to-fallback window. The audit checked 8-Ks beyond the old Item 2.02/7.01 filter and kept the two clocks separate:

- target cutoff: earliest verified results/NAV disclosure;
- source facility timestamp: earliest exact facility mark, otherwise SOI/10-Q/10-K acceptance.

No earlier verified target cutoff was found, no 8-K contained a full SOI, and no exact facility mark was found. Therefore target cutoffs shifted in 0/100 rows, source mark timestamps shifted in 0/100 rows, and the two timestamps differed in 0/100 rows. The untouched movement count remains 37 before and after the audit, above the guard of 20.

## Provenance outputs

- `data/day3/field_lineage_audit.csv`
- `data/day3/field_lineage_audit_summary.json`
- `data/day3/bdc_normalized_lineage_v2_metadata.json`
- `data/day3/bdc_facilities_agg_lineage_v2_metadata.json`
- `data/day3/facility_candidates_lineage_v2_metadata.json`
- `data/day3/bdc_manager_map.csv`
- `data/day3/manager_overlap_audit.csv`
- `data/day3/manager_overlap_audit_summary.json`
- `data/day3/fallback_audit.csv`
- `data/day3/fallback_audit_summary.json`
