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

## Incremental capture via git SHAs

Check `current/snapshot_shas.md` for previously recorded commit SHAs. If a SHA exists for a sibling
repo **and** the repo's `HEAD` matches that SHA, skip that repo entirely — its current/ file is
already up to date. If the SHA exists but HEAD has moved, instruct the sub-agent to run
`git diff <old-sha>..HEAD -- <relevant-paths>` to capture only what changed, then merge the diff
into the existing current/ file rather than re-reading the whole repo.

If `snapshot_shas.md` does not exist or a repo has no recorded SHA, do a full read for that repo.

## Gather information

Launch **three parallel Agent tool calls** to read the sibling repos simultaneously:

**Agent 1 — Schema & API (backend):**
- If doing a full read: find SQLAlchemy imperative mappings and domain models in `../haisir-backend` (`domain/models/`, `infrastructure/persistence/` or equivalent). List every table and column. Find route files (`routers/`, `api/`). List every endpoint: method, path, auth role, request/response shape.
- If doing an incremental update: run `git diff <old-sha>..HEAD` in `../haisir-backend` scoped to model, persistence, and router paths. Report only additions, removals, and changes.
- In both cases, also report the current `git rev-parse HEAD` output.

**Agent 2 — UI flows (frontend):**
- If doing a full read: find page files in `../haisir-frontend` (`app/`, `pages/`). List every implemented screen and its purpose.
- If doing an incremental update: run `git diff <old-sha>..HEAD` in `../haisir-frontend` scoped to page/component paths. Report only additions, removals, and changes.
- In both cases, also report the current `git rev-parse HEAD` output.

**Agent 3 — Infrastructure:**
- If doing a full read: read `../haisir-deploy/common` and `../haisir-deploy/dev` Docker Compose files and gateway config. Note which services are running, gateway routes, and DB migration tooling. Staging/prod overrides are out of scope.
- If doing an incremental update: run `git diff <old-sha>..HEAD` in `../haisir-deploy` scoped to common/ and dev/ paths. Report only additions, removals, and changes.
- In both cases, also report the current `git rev-parse HEAD` output.

Collect results from all three agents before proceeding.

---

## Draft summaries

Draft (or update) three spec-level summaries of what is implemented **today** using these fixed formats:

### `current/schema.md`
```
## <table_name>
- `column_name` (type) — purpose / notes
```
Only include tables/columns that actually exist in the codebase.

### `current/api_contracts.md`
```
## <METHOD> /path/to/endpoint
- Purpose: what it does
- Auth: which roles can call it (X-Current-Role values)
- Request: key fields
- Response: key fields
```
Only include endpoints that are actually implemented.

### `current/ui_flows.md`
```
## <Flow or persona name>
- Screen: <screen-id or route> — <what the user sees / can do>
- Key behaviour: any notable business rules enforced in the UI
```
Only include screens/flows that are actually implemented.

---

## Review and write

**Present all three drafted summaries to the user before writing any files.** Ask if anything looks wrong, missing, or needs adjustment.

Do NOT write any files during this review.

Once the user confirms (e.g. "looks good", "write it", "update it", "done"), do the following in one pass:

1. Write (overwrite) `current/schema.md`, `current/api_contracts.md`, and `current/ui_flows.md` with the agreed content. These are snapshots — overwriting on each run is correct.
2. Write (overwrite) `current/snapshot_shas.md` recording the HEAD commit SHA of each sibling repo captured in this run, using this format:
   ```
   ## Snapshot SHAs
   - haisir-backend: <sha>
   - haisir-frontend: <sha>
   - haisir-deploy: <sha>
   - captured: <YYYY-MM-DD>
   ```
3. Update the `## Current State` section in `Implementation_planning/progress.md` to a single clear paragraph summarising what the system can do today.

After writing, briefly summarise what was captured and whether each repo was a full read or incremental update.
