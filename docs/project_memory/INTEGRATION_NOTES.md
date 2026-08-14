# Project Memory Integration Notes

## Provenance

- Integrated on: **2026-08-14**.
- Source archive: `project_memory_pack.zip` supplied by the repository owner.
- Integration branch: `docs/persistent-project-memory`.
- Repository base commit: `d83f91fe27048070200fe8f4af7c0d65bdd20873`.
- Source pack reference state: `research/day4-shadow-nav-confirmatory` at `11cf1f44055beb88b1a0fed4c5bf09d5e2ae3414`.
- The 32 supplied files were committed unchanged first, before repository pointers and maintenance files were added.

## Snapshot differences recorded without rewriting history

The memory pack is a dated visible-research snapshot. Several files correctly
describe the next task *as it stood at* commit `11cf1f4`: sanitize the Day 4
review packet, replace navigable evidence links, add a structural reveal phase,
and harden the numeric evaluator.

The integration base commit `d83f91f` already completed that bounded patch:

- `data/day4/confirmatory_event_review_blind_v2.csv` is the sanitized 40-row packet;
- its metadata records the same 40 observation IDs and 37 source-event clusters;
- `docs/research/DAY4_EVENT_REVIEW_PROTOCOL.md` defines clean review and adjudication;
- `docs/research/PREREGISTRATION_V3_CONFIRMATORY_DRAFT.md` contains the four-phase review/freeze/reveal sequence;
- the evaluator requires structural consensus and exact frozen-ID authorization before numeric access.

Therefore the following supplied memory files are historical at the integration
base, not instructions to repeat the sanitation work:

- `00_START_HERE.md`;
- `02_CURRENT_STATE_2026-08-14.md`;
- `11_DATA_PIPELINE_AND_REPOSITORY_STATE.md`;
- `12_CURRENT_OPEN_QUESTIONS_AND_NEXT_STEPS.md`;
- `updates/2026-08-14/SESSION_SNAPSHOT.md`.

Their claims and decision history are preserved exactly. Current canonical
research documents under `docs/research/` take precedence when a dated memory
snapshot and the repository differ.

## Existing repository overview

The root `README.md` still preserves its original Day 1 showdown framing,
including the then-correct statement that no flagship had been selected. The
later visible memory records ShadowNAV as the **provisional**, still unproven
flagship after the Japan access gates and Day 3 measurement repair. The README
was not historically rewritten during this integration; it now points readers
to the dated memory and canonical research record.

## Protected boundary

This integration used only the supplied visible memory pack and public/canonical
repository documents. It did not inspect or copy `private/`, hidden reviewer
mappings, target-outcome keys, protected target-current outcomes, or raw licensed
vendor data. References to prohibited file categories inside policy documents
are safety instructions, not embedded protected content.
