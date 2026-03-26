---
name: describe-current-state
description: Snapshot current schema, API endpoints, and UI flows from sibling repos into current/ directory
---

Read `Implementation_planning/progress.md` for any existing `## Current State` context.

Next, launch **three Explore sub-agents in parallel** to read the sibling repos simultaneously:

**Agent 1 — Schema & API (backend):**
- Find SQLAlchemy imperative mappings and domain models in `../haisir-backend` (`domain/models/`, `infrastructure/persistence/` or equivalent). List every table and column.
- Find route files (`routers/`, `api/`). List every endpoint: method, path, auth role, request/response shape.

**Agent 2 — UI flows (frontend):**
- Find page files in `../haisir-frontend` (`app/`, `pages/`). List every implemented screen and its purpose.

**Agent 3 — Infrastructure:**
- Read `../haisir-deploy/common` and `../haisir-deploy/dev` Docker Compose files and gateway config. Note which services are running, gateway routes, and DB migration tooling. Staging/prod overrides are out of scope.

Collect results from all three agents before proceeding.

---

Draft three spec-level summaries of what is implemented **today** using these fixed formats:

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

**Before presenting to the user, run a Challenger agent** with this prompt:

> "You are reviewing a current-state snapshot of a fullstack app. Given the drafted schema, API, and UI summaries, identify: (1) any tables or endpoints that are likely missing from the snapshot based on what the UI implies should exist, (2) any UI screens that reference data not covered by the listed endpoints, (3) any obvious inconsistencies between the three summaries. Be concise."

Incorporate or note the challenger's findings in your presentation.

**Present all three drafted summaries plus any challenger flags to the user before writing any files.** Ask if anything looks wrong, missing, or needs adjustment.

Do NOT write any files during this review.

Once the user confirms (e.g. "looks good", "write it", "update it", "done"), do the following in one pass:

1. Write (overwrite) `current/schema.md`, `current/api_contracts.md`, and `current/ui_flows.md` with the agreed content. These are snapshots — overwriting on each run is correct.
2. Update the `## Current State` section in `Implementation_planning/progress.md` to a single clear paragraph summarising what the system can do today.

After writing, briefly summarise what was captured across the three files.
