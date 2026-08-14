# Maintaining Persistent Project Memory

This folder is a curated, visible research record. It is not a raw transcript
dump and must not become a substitute for canonical artifacts in
[`docs/research/`](../research/).

## Required workflow

1. After every meaningful research session, add
   `updates/YYYY-MM-DD/SESSION_SNAPSHOT.md` using the supplied template.
2. Update the current state, timeline, claims ledger, next steps, and source
   registry when the visible evidence or decision state changes.
3. Preserve dated snapshots append-only. Mark changed claims as superseded or
   invalidated; never silently rewrite the history that produced a decision.
4. Integrate a new incremental memory ZIP as source material only. Verify its
   inventory and hashes, compare it with current canonical artifacts, record
   conflicts in `INTEGRATION_NOTES.md`, and do not invent missing conclusions.
5. Use the commit pattern
   `docs(memory): update project state YYYY-MM-DD` for later memory updates.
6. Never add secrets, credentials, personal SEC contact details, private
   reviewer mappings, outcome keys, protected outcomes, licensed raw data, or
   hidden model chain-of-thought.
7. Rerun `scripts/update_manifest.py` after every update and commit the refreshed
   `MANIFEST.json`.

## Update checklist

- Separate facts, hypotheses, decisions, invalidated claims, and open questions.
- Link every new factual claim to a public or otherwise shareable source.
- Record the repository branch, starting commit, ending commit, and checks in the
  dated session snapshot.
- Keep source limitations next to the claims they support.
- Preserve research-stage boundaries such as preregistration, freeze, structural
  reveal, and numeric reveal.
- Run Markdown link checks, Python compilation for the manifest generator,
  `git diff --check`, and the repository safety scan before committing.

## Regenerating the manifest

From the repository root, run:

```bash
python3 docs/project_memory/scripts/update_manifest.py \
  --base-commit <integration-or-update-base-commit>
```

The manifest intentionally excludes itself and records the generated UTC time,
base commit, relative path, byte size, and SHA-256 for every other memory file.
