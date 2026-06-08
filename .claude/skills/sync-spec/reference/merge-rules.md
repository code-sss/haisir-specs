# sync-spec — Merge Rules Reference

This file contains the detailed per-category merge rules and conflict resolution logic
used in Step 4 of the `sync-spec` skill.

---

## Lines REMOVED (`-` in diff)

These existed in the committed spec but are absent from the container. Ask:

**Was this content spec-ahead (written here after the last push to the container)?**
If yes → **RESTORE** (the container simply never had it).
If the removed content is already-done work that the container cleaned up → still
**RESTORE as `[x]`** in task lists so spec history is preserved.

Common patterns:
- A full task spec block removed from PLAN.md → spec was ahead; restore
- A `[x]` task removed from TASKS.md G5/G6 "ready now" → container cleaned up done
  work; restore with `[x]` marking and the date from TASKS.md pre-pull
- A whole section dropped → likely spec-ahead; restore

---

## Lines ADDED (`+` in diff)

These are new in the container but absent from the committed spec:

- `[x]` task completions with dates → **KEEP** (backend finished work)
- New endpoints, schema fields → **KEEP**
- Updated "Ready now" queue (removed completed tasks, added newly unblocked ones) →
  **KEEP**
- New files inside `Implementation_planning/` or `target/` → **KEEP** as-is (additive)
- Deploy SHA changes in TASKS.md header → **KEEP**

> **Important:** `./sync-specs.sh` only touches `target/`, `Implementation_planning/`,
> and `CLAUDE.md`. Any other changed file in the diff (e.g. files at the repo root other
> than `CLAUDE.md`) was **not** produced by this pull — ignore it in the reconciliation.

---

## Conflicts (same line changed differently)

If a line was changed in both the container and the spec since the last push, surface
it explicitly to the user and ask which version to keep.

---

## Quick-reference merge table

**Remember:** the container is ALWAYS stale on spec content. Default is to RESTORE
HEAD content and only KEEP things that represent real work done by the container.

| Situation | Action |
|---|---|
| Container removed any spec content (task specs, planning text, decisions) | **Restore** — container was stale, never had it |
| Container removed a `[x]` completion that WAS in HEAD | **Restore** as `[x]` — container was stale |
| Container changed a `[ ]` to `[x]` with a date | **Keep** — container completed real work |
| Container updated the "Ready now" queue | **Merge** — combine both sets of unblocked tasks, remove only tasks now marked `[x]` |
| Container updated deploy SHA / baseline date in TASKS.md header | **Keep** for the container's own repo SHA; preserve other repos' SHAs from HEAD |
| Container changed a `target/` file content (not just task status) | **Examine carefully** — keep only if it reflects an implementation-discovered correction; restore spec-ahead content |
| New file inside `Implementation_planning/` or `target/` | **Keep** as-is (additive) |
| File changed at repo root other than `CLAUDE.md` | **Ignore** — not produced by this pull |
| Same line changed both in HEAD (spec evolution) and container (implementation) | **Ask user** |
