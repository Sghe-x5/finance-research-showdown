# Source Registry

Sources are separated from hypotheses. A source can support one link in a mechanism without proving the full trading chain.

## S001 — SEC Business Development Company Data Sets
- **Topic:** ShadowNAV data
- **Type:** official primary
- **Status:** verified 2026-08-14
- **URL:** https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets
- **Supports:** Official free XBRL-derived BDC flat files, including Schedule of Investments; history and download inventory.
- **Limitations:** Registrant-provided structured data can contain tagging/extraction errors; full filings remain authoritative.
- **Project impact:** Core historical data source.

## S002 — SEC BDC Data Sets announcement
- **Topic:** ShadowNAV data
- **Type:** official primary
- **Status:** verified 2026-08-14
- **URL:** https://www.sec.gov/newsroom/whats-new/2506-bdc-data-sets
- **Supports:** SEC launched BDC datasets in June 2025 and describes flat-file/XBRL scope.
- **Limitations:** Announcement, not schema documentation.
- **Project impact:** Supports freshness/new availability of the public dataset.

## S003 — SEC Developer Resources
- **Topic:** Data access
- **Type:** official primary
- **Status:** known official
- **URL:** https://www.sec.gov/about/developer-resources
- **Supports:** Fair-access and identification requirements for automated SEC retrieval.
- **Limitations:** Operational guidance, not research evidence.
- **Project impact:** Downloader policy.

## S004 — Houlihan Lokey BDC Monitor
- **Topic:** BDC universe
- **Type:** industry research
- **Status:** verified 2026-08-14
- **URL:** https://hl.com/insights/bdc-monitor/
- **Supports:** Quarterly BDC universe/trend research covering more than 170 BDCs.
- **Limitations:** Commercial/industry publication; methodology may not be fully open.
- **Project impact:** Universe scale and cross-holding context.

## S005 — SOLVE Workstation — BDC Data
- **Topic:** Vendor competition
- **Type:** vendor
- **Status:** verified 2026-08-14
- **URL:** https://solvefixedincome.com/solutions/bdc-data-analytics-workstation/
- **Supports:** Commercial normalization, co-investor mapping, same-asset valuation comparison, historical BDC coverage.
- **Limitations:** Marketing claims; no public validation of predictive accuracy.
- **Project impact:** Invalidates 'nobody links co-holder marks'; novelty must be predictive.

## S006 — KBRA — BDC Portfolio Valuations are Rigorous
- **Topic:** Valuation consistency
- **Type:** rating-agency research
- **Status:** verified 2026-08-14
- **URL:** https://www.kbra.com/publications/BStQZsyc
- **Supports:** Identical-asset marks usually show limited variance; larger differences may appear in stressed assets.
- **Limitations:** Uses a commercial database and rated-BDC perspective.
- **Project impact:** Both supports mark propagation and warns that alpha may be quickly understood.

## S007 — CreditSights — The opaque side of BDCs
- **Topic:** Valuation heterogeneity
- **Type:** industry journalism/research
- **Status:** verified 2026-08-14
- **URL:** https://know.creditsights.com/us-insight-the-opaque-side-of-bdcs-private-credits-most-transparent-market/
- **Supports:** Examples of divergent marks; lead/agent information-right differences; stressed assets have wider dispersion.
- **Limitations:** Case examples and interviews, not a causal panel study.
- **Project impact:** Motivates lender-bias and information-right controls.

## S008 — Moody's — Entry Pricing or Credit Deterioration?
- **Topic:** Entry basis
- **Type:** research
- **Status:** verified 2026-08-14
- **URL:** https://www.moodys.com/web/en/us/insights/credit-risk/private-credit/entry-pricing-or-credit-deterioration.html
- **Supports:** Below-par marks often reflect entry basis; post-origination change is more informative.
- **Limitations:** Cross-sectional descriptive analysis; cost is an imperfect entry-price proxy.
- **Project impact:** Rejects raw below-par signal; supports source-delta design.

## S009 — KBRA — Khoros potential default
- **Topic:** First-reporter cases
- **Type:** rating-agency case research
- **Status:** verified 2026-08-14
- **URL:** https://www.kbra.com/publications/QVQcBRRM/kbra-releases-research-private-credit-khoros-potential-default-sprinkled-across-private-credit
- **Supports:** A documented case where one BDC markdown preceded broader markdown/non-accrual reporting.
- **Limitations:** Single distressed borrower case.
- **Project impact:** Concrete example of the proposed mechanism.

## S010 — KBRA — Pluralsight restructuring exposure
- **Topic:** Cross-held exposure
- **Type:** rating-agency case research
- **Status:** verified 2026-08-14
- **URL:** https://www.kbra.com/publications/mpftfNbZ/private-credit-impact-of-pluralsight-s-potential-restructuring-will-be-widely-dispersed-and-no-effect-on-ratings-expected
- **Supports:** One private-credit facility can be distributed across many BDCs and managers.
- **Limitations:** Exposure case, not predictive test.
- **Project impact:** Supports cross-holder network scale.

## S011 — RFS — How to Talk When a Machine Is Listening
- **Topic:** Machine readers
- **Type:** peer-reviewed academic
- **Status:** verified 2026-08-14
- **URL:** https://academic.oup.com/rfs/article-abstract/36/9/3603/7087110
- **Supports:** Firms adapt disclosures to growing machine readership.
- **Limitations:** Does not prove LLM reading errors cause tradable price errors.
- **Project impact:** Supports AI Reader Distortion mechanism but not full alpha chain.

## S012 — JPX Company Announcements Service
- **Topic:** Japan rule
- **Type:** official primary
- **Status:** verified 2026-08-14
- **URL:** https://www.jpx.co.jp/english/listing/disclosure/
- **Supports:** Prime Market simultaneous Japanese/English requirement from April 2025; 31-day public service window.
- **Limitations:** Historical archive beyond service window requires paid/other access.
- **Project impact:** Core institutional treatment for Japan hypothesis.

## S013 — JPX English Disclosure via TDnet
- **Topic:** Japan rule
- **Type:** official primary
- **Status:** verified 2026-08-14
- **URL:** https://www.jpx.co.jp/english/equities/listed-co/disclosure-gate/service/
- **Supports:** Scope and process of English disclosure through TDnet; summary/excerpt acceptable.
- **Limitations:** Rule page, not historical event-level treatment data.
- **Project impact:** Defines treatment complexity.

## S014 — JPX English Disclosure Survey end-2024
- **Topic:** Japan pre-treatment
- **Type:** official primary
- **Status:** verified 2026-08-14
- **URL:** https://www.jpx.co.jp/english/corporate/news/news-releases/0060/20250122-01.html
- **Supports:** Before April 2025, many Prime companies still needed to improve simultaneous English timing.
- **Limitations:** Aggregate survey, not event-level timestamps.
- **Project impact:** Supports heterogeneous treatment intensity.

## S015 — JPX 2025 overseas investor survey
- **Topic:** Japan investor demand
- **Type:** official primary
- **Status:** verified 2026-08-14
- **URL:** https://www.jpx.co.jp/english/corporate/news/news-releases/0060/20250902-01.html
- **Supports:** Overseas investors value improvements and still request broader/full English disclosure.
- **Limitations:** Survey evidence, not return causality.
- **Project impact:** Supports user value of a normalized English feed.

## S016 — Yanoshin unofficial TDnet API
- **Topic:** Japan historical index
- **Type:** unofficial index/API
- **Status:** verified 2026-08-14
- **URL:** https://webapi.yanoshin.jp/tdnet/
- **Supports:** Date/range queries, JSON/XML/RSS/HTML event index, timestamps and document links.
- **Limitations:** Unofficial; provides index/links, not guaranteed historical document retention.
- **Project impact:** Historical event-universe construction.

## S017 — J-Quants
- **Topic:** Japan data
- **Type:** official/commercial service
- **Status:** known; access blocked in current environment
- **URL:** https://jpx-jquants.com/en/
- **Supports:** Potential daily price and financial-summary data path.
- **Limitations:** Regional/CDN access, plan limits, licensing and delay constraints.
- **Project impact:** Required for reactivation of historical Japan track.

## S018 — JPX TDnet paid database service
- **Topic:** Japan archive
- **Type:** official paid service
- **Status:** known official
- **URL:** https://www.jpx.co.jp/english/markets/paid-info-listing/tdnet/02.html
- **Supports:** Longer historical TDnet access.
- **Limitations:** Paid; outside initial budget.
- **Project impact:** Potential institutional reactivation path.

## S019 — FASB ASU 2023-07 segment reporting
- **Topic:** RegimeShift
- **Type:** official standard setter
- **Status:** topic verified in prior research; exact document URL should be rechecked
- **URL:** https://www.fasb.org/
- **Supports:** New significant segment expense disclosures.
- **Limitations:** Heterogeneous custom tags and incomplete segment P&L reconstruction.
- **Project impact:** Feature candidate, not flagship.

## S020 — FASB ASU 2023-09 income taxes
- **Topic:** RegimeShift
- **Type:** official standard setter
- **Status:** topic verified in prior research; exact document URL should be rechecked
- **URL:** https://www.fasb.org/
- **Supports:** New tax reconciliation and jurisdictional disclosures.
- **Limitations:** Short mandatory history as of 2026.
- **Project impact:** Future feature/live dataset.

## S021 — FASB ASU 2024-03 DISE
- **Topic:** RegimeShift
- **Type:** official standard setter
- **Status:** topic verified in prior research; exact document URL should be rechecked
- **URL:** https://www.fasb.org/
- **Supports:** Future expense disaggregation disclosures.
- **Limitations:** Main mandatory history arrives later.
- **Project impact:** Not suitable for immediate historical alpha test.

## S022 — FASB ASU 2022-04 supplier finance
- **Topic:** Supplier finance
- **Type:** official standard setter
- **Status:** prior research source
- **URL:** https://www.fasb.org/Page/Document?pdf=ASU%202022-04.pdf
- **Supports:** Mandatory supplier-finance program disclosures.
- **Limitations:** Existing research and vendor competition.
- **Project impact:** Financial-normalization feature.

## S023 — European Commission public country-by-country reporting
- **Topic:** EU CbCR
- **Type:** official primary
- **Status:** prior research source
- **URL:** https://finance.ec.europa.eu/financial-markets/company-reporting-and-auditing/company-reporting/public-country-country-reporting_en
- **Supports:** New public jurisdiction-level tax/profit/employment disclosure framework.
- **Limitations:** Minimal historical sample.
- **Project impact:** Strong live-first future dataset.

## S024 — FERC large-load orders/remarks
- **Topic:** PowerQueue
- **Type:** official regulator
- **Status:** prior research source
- **URL:** https://www.ferc.gov/news-events/news/commissioner-rosners-remarks-large-load-show-cause-orders-e-7-e-12-june-18-2026
- **Supports:** Large-load/data-center queue duplication and readiness concerns.
- **Limitations:** Docket data fragmented and long-horizon.
- **Project impact:** Rejected current flagship; possible future project.

## S025 — USAspending Federal Spending Guide
- **Topic:** Government contracts
- **Type:** official primary
- **Status:** prior research source
- **URL:** https://www.usaspending.gov/data/Federal-Spending-Guide.pdf
- **Supports:** Award actions and deobligation semantics.
- **Limitations:** Negative obligations are not automatically lost future revenue.
- **Project impact:** Rejected as current flagship.

## S026 — ARCC 2025-12-31 filing
- **Topic:** ShadowNAV filing fixture
- **Type:** official filing
- **Status:** prior research source
- **URL:** https://www.sec.gov/Archives/edgar/data/1287750/000128775026000006/arcc-20251231.htm
- **Supports:** Auctane calculation fixture.
- **Limitations:** Contaminated development example; never confirmatory.
- **Project impact:** Regression test only.

## S027 — FSK 2025-12-31 filing
- **Topic:** ShadowNAV filing fixture
- **Type:** official filing
- **Status:** prior research source
- **URL:** https://www.sec.gov/Archives/edgar/data/1422183/000162828026011734/fsk-20251231.htm
- **Supports:** Medallia target fixture.
- **Limitations:** Contaminated development example.
- **Project impact:** Regression test only.
