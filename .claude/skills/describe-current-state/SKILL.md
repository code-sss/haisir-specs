---
name: describe-current-state
description: >
  Use this skill whenever you need to capture what is actually built today across backend, frontend,
  and infrastructure. Run it before planning a new phase, after completing a phase, or any time the
  user asks "what's built?", "capture current state", "snapshot the codebase", or "what is
  implemented today". It reads the sibling repos, drafts three summary docs (schema, API, UI),
  and writes files only after user confirmation.
---

Read `Implementation_planning/progress.md` first to understand what was already captured — this
seeds your context so sub-agents know the baseline and can focus on what may have changed.

For sibling repo paths and folder conventions, use the **Repository Purpose** section of `CLAUDE.md`
as the authoritative source rather than hardcoded paths.

## Step 1 — Determine read mode per repo

Run these two commands in parallel:

```bash
cat current/snapshot_shas.md 2>/dev/null || echo "NO_SNAPSHOT"
```
```bash
git -C ../haisir-backend rev-parse HEAD && \
git -C ../haisir-frontend rev-parse HEAD && \
git -C ../haisir-deploy rev-parse HEAD
```

For each sibling repo, decide the **read mode**:

| Condition | Mode |
|---|---|
| No `snapshot_shas.md`, or repo has no recorded SHA | **full-read** — must use a sub-agent |
| SHA recorded AND `HEAD == recorded SHA` | **skip** — already up to date |
| SHA recorded AND `HEAD != recorded SHA` | **incremental** — run Bash diff in-context |

## Step 2 — Gather information

### Incremental repos (the common case after first run)

Run all incremental diffs **in parallel** with direct Bash tool calls — no sub-agents needed:

```bash
# Backend
git -C ../haisir-backend log <old-sha>..HEAD --oneline
git -C ../haisir-backend diff <old-sha>..HEAD -- \
  src/domain/models/ src/infrastructure/persistence/ \
  src/routers/ src/api/ src/auth/ migrations/
```
```bash
# Frontend
git -C ../haisir-frontend log <old-sha>..HEAD --oneline
git -C ../haisir-frontend diff <old-sha>..HEAD -- \
  src/app/ src/features/ src/components/ src/hooks/
```
```bash
# Deploy
git -C ../haisir-deploy log <old-sha>..HEAD --oneline
git -C ../haisir-deploy diff <old-sha>..HEAD -- common/ dev/
```

Analyse the diff output directly. Report only additions, removals, and changes.

### Full-read repos (first run, or SHA was never recorded)

Launch one sub-agent **per full-read repo** (skip repos that are incremental or unchanged):

**Sub-agent — Schema & API (backend full read):**
Find SQLAlchemy imperative mappings and domain models in `../haisir-backend`
(`domain/models/`, `infrastructure/persistence/`). List every table and column.
Find route files (`routers/`, `api/`). List every endpoint: method, path, auth role,
request/response shape. Report `git rev-parse HEAD`.

**Sub-agent — UI flows (frontend full read):**
Find page files in `../haisir-frontend` (`app/`, `pages/`). List every implemented
screen and its purpose. Report `git rev-parse HEAD`.

**Sub-agent — Infrastructure (deploy full read):**
Read `../haisir-deploy/common` and `../haisir-deploy/dev` Docker Compose files and
gateway config. Note services, routes, and DB migration tooling. Staging/prod overrides
are out of scope. Report `git rev-parse HEAD`.

---

## Step 3 — Draft summaries

Draft (or update) three spec-level summaries of what is implemented **today**.

### For incremental repos
Use targeted Edit calls on the existing `current/` files to splice in only the new/changed
sections. Do NOT rewrite entire files when only a few sections changed.

### For full-read repos
Produce the full file content using these formats:

#### `current/schema.md`
```
## <table_name>
- `column_name` (type) — purpose / notes
```
Only include tables/columns that actually exist in the codebase.

#### `current/api_contracts.md`
```
## <METHOD> /path/to/endpoint
- Purpose: what it does
- Auth: which roles can call it (X-Current-Role values)
- Request: key fields
- Response: key fields
```
Only include endpoints that are actually implemented.

#### `current/ui_flows.md`
```
## <Flow or persona name>
- Screen: <screen-id or route> — <what the user sees / can do>
- Key behaviour: any notable business rules enforced in the UI
```
Only include screens/flows that are actually implemented.

### Also update `/docs` user guides

`docs/*-guide.md` (e.g. `platform-admin-guide.md`, `parent-guide.md`, `student-guide.md`) are
user-facing guides, one per persona. Cross-reference what you just found in `current/schema.md`,
`current/api_contracts.md`, and `current/ui_flows.md` against the matching guide:

- New or changed screen, route, field, or business rule → update the relevant section of the
  guide (use targeted Edit, not a rewrite).
- Removed feature → remove or correct the stale section.
- No existing guide for that persona (e.g. teacher/tutor) → skip, don't create one speculatively.
- Backend/infra-only changes with no user-visible effect → skip, guides describe what a user sees.

---

## Step 4 — Review and write

**Present the drafted changes to the user before writing any files.**
For incremental updates, show only the additions/changes (not the full file).
Include any drafted `/docs/*-guide.md` edits from the previous step in the same review.
Ask if anything looks wrong, missing, or needs adjustment.

Do NOT write any files during this review.

Once the user confirms (e.g. "looks good", "write it", "yes"), do the following in one pass:

1. Apply the agreed changes:
   - **Incremental:** use Edit (targeted edits) on `current/schema.md`, `current/api_contracts.md`, `current/ui_flows.md`
   - **Full read:** use Write (overwrite) for the repos that needed a full read
   - **Docs:** use Edit (targeted edits) on the affected `docs/*-guide.md` file(s), if any
2. Write (overwrite) `current/snapshot_shas.md` with the current HEADs:
   ```
   ## Snapshot SHAs
   - haisir-backend: <sha>
   - haisir-frontend: <sha>
   - haisir-deploy: <sha>
   - captured: <YYYY-MM-DD>
   ```
3. Update the snapshot baseline and add an "Also complete" entry in `Implementation_planning/progress.md`.

After writing, briefly summarise what was captured and whether each repo was a full read or incremental update.

## Step 5 — SHA divergence check

Check whether `Implementation_planning/PLAN.md` exists. If it does, extract the
`<!-- plan-baseline: backend:<sha> frontend:<sha> deploy:<sha> -->` watermark.
Compare against the SHAs just written to `snapshot_shas.md`.

If any SHA differs, warn the user:

```
⚠ SHA drift detected: the current state snapshot is ahead of the plan baseline.
  Plan baseline:    backend:<plan-sha>  frontend:<plan-sha>  deploy:<plan-sha>
  Current snapshot: backend:<snap-sha>  frontend:<snap-sha>  deploy:<snap-sha>

This means code has changed since the plan was written. Consider running /plan
to reconcile the plan against the new code before starting implementation.
```

If the SHAs match (or PLAN.md does not exist), no warning is needed.
