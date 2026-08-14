# CODEX — Integrate Persistent Project Memory into GitHub

Repository:
`Sghe-x5/finance-research-showdown`

Input archive:
`project_memory_pack.zip`

## Goal

Create a durable project-memory area so that a new ChatGPT/Claude/Codex session can recover
the full visible research context, sources, decisions, failed hypotheses, and current protocol
without repeating the research.

This is a documentation-only integration. Do not change research code, datasets, blind files,
private mappings, samples, preregistration formulas, or outcomes.

## 1. Branch

Start from the latest active research branch:

`research/day4-shadow-nav-confirmatory`

Create:

`docs/persistent-project-memory`

Do not force-push.

## 2. Destination

Unpack the archive and copy its contents to:

`docs/project_memory/`

Preserve the internal filenames and dated updates.

Also create a root pointer:

`PROJECT_MEMORY_START_HERE.md`

with a short link to:

`docs/project_memory/00_START_HERE.md`

Update the root `README.md` with a small section:

```markdown
## Persistent Project Memory

Start with [PROJECT_MEMORY_START_HERE.md](PROJECT_MEMORY_START_HERE.md).
This folder contains visible research summaries, source links, decision history,
invalidated claims, handoff prompts, and dated updates.
```

Do not overwrite or move existing canonical research files under `docs/research/`.

## 3. Integrity and safety

Before copying:

- verify archive inventory;
- reject path traversal;
- compute SHA-256 for every input file.

After copying, verify that the new folder contains no:

- `.env`;
- API keys/tokens;
- personal SEC User-Agent email;
- `/Users/...` paths;
- private blind mappings;
- target-outcome private keys;
- licensed raw vendor datasets;
- hidden model chain-of-thought claims.

The memory folder may contain only visible, shareable research summaries and explicit
decision rationale.

Never search for or copy:

- `private/day3/blind_facility_key.json`
- `private/day3/blind_alias_key.json`
- future `private/day4/*outcome*` or evidence mappings
- any hidden reviewer mapping.

## 4. Historical accuracy

Do not "improve" or rewrite conclusions.

Codex may:
- fix relative Markdown links;
- fix obvious filename/path inconsistencies;
- add an index table;
- record the Git commit used during integration.

Codex must not:
- change claim statuses;
- invent sources;
- merge invalidated claims back into active conclusions;
- remove embarrassing failed results;
- change dates/metrics.

If a statement conflicts with current canonical repo artifacts, add a visible note in:

`docs/project_memory/INTEGRATION_NOTES.md`

Do not silently reconcile it.

## 5. Index and manifest

Create:

`docs/project_memory/INDEX.md`

The index should group files into:
- start/current state;
- project history;
- ShadowNAV;
- Japan;
- alternatives;
- ChatGPT/Claude visible notes;
- methods/guards;
- sources;
- handoff prompts;
- maintenance/templates;
- dated updates.

Run or add:

`docs/project_memory/scripts/update_manifest.py`

to produce:

`docs/project_memory/MANIFEST.json`

Manifest fields:
- relative path;
- bytes;
- SHA-256;
- generated UTC timestamp;
- repository commit used as base.

Do not include the manifest itself in its own hash list.

## 6. Ongoing maintenance rule

Add a root contributor note:

`docs/project_memory/MAINTENANCE.md`

It should state:

1. After each meaningful research session, add:
   `docs/project_memory/updates/YYYY-MM-DD/SESSION_SNAPSHOT.md`.
2. Update current state, decision timeline, claims ledger, next steps, and source registry.
3. Preserve old snapshots append-only.
4. When ChatGPT or Claude produces a new incremental memory ZIP, Codex integrates it
   without inventing research.
5. Commit message pattern:
   `docs(memory): update project state YYYY-MM-DD`.
6. Never include secrets/private mappings/outcome keys.
7. Re-run the manifest script after every update.

The repository should treat this as a living research memory, not a raw chat dump.

## 7. Git

Suggested commits:

1. `docs(memory): add persistent research context and source archive`
2. `docs(memory): add maintenance workflow and repository pointers`

Run:
- Markdown path/link sanity check;
- Python `py_compile` for the manifest script;
- `git diff --check`;
- secret/path/private-key scan;
- existing tests only if documentation changes affect them.

Push branch:

`docs/persistent-project-memory`

Open a pull request to the default branch titled:

`Add persistent project memory and research archive`

Do not auto-merge if branch protections or conflicts exist.

If safe and explicitly permitted by the repository settings, also merge/cherry-pick the
docs-only commits into the current active research branch so the memory is available there.
Do not modify research-code commits.

## 8. Final response

Report:

- branch;
- commits;
- PR URL;
- destination path;
- file count;
- manifest SHA-256;
- README/root pointer changes;
- checks run;
- any conflicts found in `INTEGRATION_NOTES.md`;
- confirmation that no private keys, hidden mappings, secrets, or protected target outcomes
  were copied.

After this integration, stop. Do not start the next research/reveal task.
