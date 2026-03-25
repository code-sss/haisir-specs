Read `Implementation_planning/progress.md` for any existing `## Current State` context.

Next, read the sibling repos to discover what is currently implemented:

**Schema (from backend models):**
- `../haisir-backend` — find SQLAlchemy imperative mappings and domain models. Look for `domain/models/`, `infrastructure/persistence/` or equivalent. List every table and column that exists.

**API endpoints (from backend routes):**
- `../haisir-backend` — find route files (e.g. `routers/`, `api/`). List every endpoint: method, path, auth role, request/response shape.

**UI flows (from frontend pages/components):**
- `../haisir-frontend` — find page files (e.g. `app/`, `pages/`). List every implemented screen and its purpose.

**Infrastructure context:**
- `../haisir-deploy/common` and `../haisir-deploy/dev` — Docker Compose files and gateway config. Note which services are running, what the gateway routes are, and any DB migration tooling. Staging/prod overrides are out of scope.

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

**Present all three drafted summaries to the user before writing any files.** Ask if anything looks wrong, missing, or needs adjustment.

Do NOT write any files during this review.

Once the user confirms (e.g. "looks good", "write it", "update it", "done"), do the following in one pass:

1. Write (overwrite) `current/schema.md`, `current/api_contracts.md`, and `current/ui_flows.md` with the agreed content. These are snapshots — overwriting on each run is correct.
2. Update the `## Current State` section in `Implementation_planning/progress.md` to a single clear paragraph summarising what the system can do today.

After writing, briefly summarise what was captured across the three files.
