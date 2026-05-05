---
name: sync-spec
description: >
  Pull spec files from a sibling container (backend or frontend), diff against
  the git baseline, and merge — keeping backend completions while restoring any
  spec-ahead planning content the container didn't have. Use when the user says
  "sync specs from backend/frontend", "I pulled the spec files", "pull specs",
  or "sync-spec backend/frontend".
argument-hint: "backend|frontend"
---

# sync-spec — Pull, Diff, and Merge Spec Files

This skill syncs spec files from a named container into the `haisir-specs` repo.
The key challenge: the container may have completed tasks and added new lines, but
also may be missing spec-ahead planning content that was added here after the last
push. The skill must keep both sets of changes.

---

## Step 0 — Resolve the source

If the user did not specify `backend` or `frontend`, ask:
> "Which source — `backend` or `frontend`?"

Use the answer as `{source}` for the rest of this skill.

---

## Step 1 — Baseline

Record the current HEAD SHA before touching anything:

```bash
git -C /home/gulzar/Workspace/haisir-specs rev-parse HEAD
```

Save this as `{pre_pull_sha}`. If the pull has **already happened** (files already
overwritten in working tree), skip the actual `./sync-specs.sh pull` call in Step 2
and go straight to Step 3 using the current working-tree state vs `HEAD`.

---

## Step 2 — Pull (skip if already done)

Run the pull command:

```bash
cd /home/gulzar/Workspace/haisir-specs && ./sync-specs.sh pull {source}
```

This overwrites `target/`, `Implementation_planning/`, and `CLAUDE.md` with files
from the container. **No other directories are touched.**

---

## Step 3 — Diff

Run:

```bash
git -C /home/gulzar/Workspace/haisir-specs diff HEAD
```

Capture the full diff output. This shows every change the pull made relative to the
committed spec state.

---

## Step 4 — Analyze each changed file

For every file in the diff, categorise each hunk:

### Lines REMOVED (`-` in diff)

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

### Lines ADDED (`+` in diff)

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

### Conflicts (same line changed differently)

If a line was changed in both the container and the spec since the last push, surface
it explicitly to the user and ask which version to keep.

---

## Step 5 — Check push-SHA baseline

Read `sync-specs.push-shas.md` in the repo root if it exists. This records the spec-
side HEAD SHA at the time of the last `push` to each container. If a push SHA exists
for `{source}`:

- Run `git diff {push_sha}..HEAD -- Implementation_planning/ target/ CLAUDE.md`
  to see what spec-side changes accumulated since the last push
- Any spec-side additions in that range that are now missing from the pulled files →
  treat as spec-ahead and RESTORE automatically (no ambiguity)

If `sync-specs.push-shas.md` does not exist or has no entry for `{source}`, proceed
without a baseline (use manual judgment per Step 4 rules).

---

## Step 6 — Present reconciliation summary

Before writing any files, present this table to the user:

```
## Reconciliation summary — pull from {source}

### Kept from {source} container
| File | Lines / sections kept | Reason |
|---|---|---|
| ... | ... | ... |

### Restored from spec (container was behind)
| File | Lines / sections restored | Reason |
|---|---|---|
| ... | ... | ... |

### New files inside synced directories (kept as-is)
| File | Reason |
|---|---|
| ... | ... |

> Only files under `Implementation_planning/`, `target/`, or `CLAUDE.md` can appear
> here. Files at the repo root (other than `CLAUDE.md`) are not produced by the pull —
> do not include them in this table.

### Ambiguous items (need your input)
| File | Description | Options |
|---|---|---|
| ... | ... | A / B |
```

Do NOT write any files during this step. Wait for the user to confirm or adjust.

---

## Step 7 — Write merged files

Once the user confirms (e.g. "looks good", "proceed", "do it"):

For each file that needs changes, apply the merged content using `replace_string_in_file`
(surgical edits) rather than full rewrites — this keeps git diffs clean.

Apply in this order:
1. `Implementation_planning/TASKS.md` (task completions first — smallest/safest change)
2. `Implementation_planning/PLAN.md` (restore spec-ahead task specs)
3. Any `target/` files changed
4. `CLAUDE.md` if changed

---

## Step 8 — Update push-SHA tracking

After writing all merged files, update (or create) `sync-specs.push-shas.md`:

```markdown
## Last Push SHAs

Record the spec-side HEAD SHA when `./sync-specs.sh push {source}` was last run.
Used by the `sync-spec` skill as the merge base when pulling changes back.

| Container | SHA | Pushed |
|---|---|---|
| backend  | {sha} | YYYY-MM-DD |
| frontend | {sha} | YYYY-MM-DD |

> Update this file immediately after every `./sync-specs.sh push` run.
> To update: replace the SHA and date for the relevant container.
```

If this is a pull (not a push), leave the existing push SHA unchanged — only update
it on the next push operation.

Remind the user:
> **After your next `./sync-specs.sh push {source}` run, record the spec HEAD SHA
> here so future pulls have a clean merge baseline.**

---

## Step 9 — Recommend follow-up actions

Print:

```
## What to do next

- [ ] Run `describe-current-state` if {source} completed new API endpoints or
      schema changes — this updates `current/api_contracts.md`, `current/schema.md`,
      and `current/ui_flows.md`.
- [ ] Run `./sync-specs.sh push {source}` after any spec updates to keep the
      container in sync, then update `sync-specs.push-shas.md` with the new SHA.
- [ ] Update `Implementation_planning/progress.md` ## Current State paragraph if
      significant new work was completed (use the task completion dates as a guide).
```

---

## Scope boundary (important)

`./sync-specs.sh` only syncs: `target/`, `Implementation_planning/`, `CLAUDE.md`.

The following are **NOT** synced and must be updated separately:
- `current/` — use `describe-current-state`
- `vision/` — always edited only in this repo
- `experiments/` — never synced
- `sync-specs.push-shas.md` — managed manually per this skill

---

## Quick-reference merge rules

| Situation | Action |
|---|---|
| Backend removed a spec task block from PLAN.md | Restore (spec was ahead) |
| Backend removed a `[x]` done task from TASKS.md | Restore as `[x]` (preserve history) |
| Backend added `[x]` with date to a previously `[ ]` task | Keep (backend completed it) |
| Backend updated "Ready now" queue | Keep (reflects real unblocked state) |
| Backend changed deploy SHA in TASKS.md header | Keep |
| New file inside `Implementation_planning/` or `target/` | Keep as-is |
| File changed at repo root other than `CLAUDE.md` | **Ignore** — not from this pull |
| Same line changed both sides differently | Ask user |
