# External audit of the Day 2 mechanism pilot

Date received: **2026-08-13**

Status: accepted as the specification for the pre-reveal Day 3 measurement
repair. The historical Day 2 commits, samples and tag remain immutable.

## Executive verdict

The Git freeze sequence was genuine: eligible IDs and the frozen sample existed
in commit `a495f39` before results appeared. The two contaminated fixtures were
excluded. However, the adjusted predictor was changed between freeze and reveal,
so it is exploratory rather than confirmatory.

The adjusted result is concentrated entirely in PetVet Care Centers. Thirteen
of fifteen rows reduce to the unchanged-target baseline. Removing PetVet makes
the adjusted and B0 MAE equal at approximately 0.070 percentage points. The
sample has one quarter, two source funds, two target funds and only one material
mark-movement event.

The reported 100% facility-matching precision and recall are not an independent
benchmark. The adjudication script assigned `manual_label = predicted_label` by
default, while its twenty overrides affected only predicted-unrelated rows. The
eighty predicted same-facility pairs therefore lacked blind independent labels.

The robust Day 2 findings are narrower:

1. naive copying of the earliest co-holder mark lost to persistence;
2. PetVet is one clean example in which a prior-gap/DiD transfer captured a
   later target markdown;
3. the current unit of analysis contains repeated XBRL slices;
4. Japan independent recovery was 0/32, but J-Quants and Wayback steps were not
   completed, so the preregistered recovery gate was not fully run.

## Findings accepted for repair

| Severity | Track | Finding | Required response |
|---|---|---|---|
| Fatal | ShadowNAV | benchmark defaulted manual labels to predictions | blind 60-pair export and independent labels |
| Fatal | ShadowNAV | adjusted advantage is one borrower | event-conditional design and leave-one-borrower-out |
| Major | ShadowNAV | adjusted formula changed after freeze | prereg v3 and evaluator hash lock before a new freeze |
| Major | ShadowNAV | exact borrower blocking has unmeasured alias recall | 30-borrower ARCC alias audit against OBDC/NMFC |
| Major | ShadowNAV | XBRL slices treated as observations | aggregate to economic facilities before matching |
| Moderate | ShadowNAV | source window starts before SOI availability | use max(results timestamp, SOI acceptance) |
| Moderate | ShadowNAV | disappearance hard-coded false | make disappearance a separate target outcome |
| Moderate | ShadowNAV | no Q4 eligible IDs | diagnose archive-quarter versus position-quarter mapping |
| Major | Japan | J-Quants not configured; Wayback not attempted | bounded 20-event final recovery gate |

## Day 3 order and freeze rule

Pre-reveal work:

1. diagnose the Q4 zero;
2. aggregate XBRL rows to BDC × quarter × borrower × economic facility;
3. download official SEC archives from 2024 Q1 through 2025 Q4;
4. mark the old sample as a failed pilot without changing its IDs or values;
5. export the blind match and alias-recall audits;
6. complete the bounded Japan recovery steps that access and credentials allow.

No new outcome reveal is authorized until preregistration v3 is supplied. The
next preregistration must define every predictor literally, make movement events
the primary stratum, cluster by borrower, require a paired comparison with B0,
and require leave-one-borrower-out sensitivity. A future freeze must store the
SHA-256 of its evaluator, and evaluation must refuse a mismatched script.

## Required report corrections

- The 0.068 pp adjusted result must be accompanied by: “Advantage is driven
  entirely by a single borrower (PetVet); leave-one-borrower-out eliminates it.”
- `entry_price_bias_adjusted_source` must be renamed
  `prior_gap_adjusted_source`; no entry price is used.
- The old frozen sample must be labelled a failed pilot because of the
  unit-of-analysis bug.
- Current matching accuracy must be labelled an upper bound by construction,
  not an independently measured 100% result.

## Japan decision gate

Select 20 clean corporate earnings-forecast revisions from the frozen historical
universe after excluding dividend-only, withdrawal and actual-versus-forecast
notices. Attempt official/J-Quants recovery first, then issuer IR and Wayback.
Retain every failure. Do not bypass HTTP 403.

- at least 12/20 reproducibly recovered: Japan remains a candidate;
- fewer than 12/20: demote it to a live-data product and close the showdown.

The quota is one half-day. Account creation, user authentication or tokens are
external prerequisites and must never be committed.
