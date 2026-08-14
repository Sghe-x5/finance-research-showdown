# Project Memory Maintenance Protocol

## Canonical folder

`docs/project_memory/`

## After every meaningful research session

Update:
1. `02_CURRENT_STATE_YYYY-MM-DD.md` or the canonical current-state file.
2. `03_PROJECT_TIMELINE_AND_DECISIONS.md`.
3. `12_CURRENT_OPEN_QUESTIONS_AND_NEXT_STEPS.md`.
4. `20_CLAIMS_LEDGER.md`.
5. `13_SOURCE_REGISTRY.csv` and `.md` for new sources.
6. Add `updates/YYYY-MM-DD/SESSION_SNAPSHOT.md`.

## Required snapshot sections

- What was attempted.
- Inputs/commits/hashes.
- What was learned.
- What was invalidated.
- Current decision.
- New risks.
- Next exact action.
- Sources added.
- Private items deliberately excluded.

## Append-only history

Do not silently rewrite old dated snapshots.
If a claim changes:
- mark it invalidated/superseded in the claims ledger;
- preserve the old version;
- link to the new decision.

## Periodic model update packs

The user can ask ChatGPT or Claude:

> Prepare an incremental project-memory update pack from the latest visible research.

The model should output:
- changed canonical markdown files;
- a new dated snapshot;
- source-registry additions;
- a Codex merge prompt;
- a manifest of hashes.

Codex should merge updates, not invent research conclusions.

## Security/privacy

Never commit:
- private reviewer mappings;
- target-outcome keys before authorization;
- API keys;
- raw licensed third-party datasets;
- `.env`;
- personal SEC contact email;
- employer/internal data;
- hidden model chain-of-thought.

Only visible, shareable research summaries and explicit rationales belong here.
