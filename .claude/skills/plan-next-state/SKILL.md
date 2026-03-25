---
name: plan-next-state
description: Analyse gap between current and target state and recommend the next implementation step to agree on
---

Read the following files to understand the desired end state:
- `target/requirements/00_overview.md`
- `target/requirements/01_data_model.md`
- `target/requirements/02_auth_and_roles.md`
- Any other `target/requirements/*.md` files relevant to the domain being discussed
- `target/prototypes/*.html` — if the discussion involves UI flows

Then read the current state snapshot if it exists (created by `/describe-current-state`):
- `current/schema.md`
- `current/api_contracts.md`
- `current/ui_flows.md`

Then read these two planning files:
- `Implementation_planning/progress.md` — agreed current state summary and what has already been agreed as the next phase
- `Implementation_planning/phases.md` — rough phase guide for context on ordering and dependencies

If `current/` files do not exist, or if the user's message mentions a specific domain (schema / API / UI / a specific feature), also read the relevant code in the sibling repos (`../haisir-backend`, `../haisir-frontend`, or `../haisir-deploy`) to get precise detail on what is and isn't implemented.

Based on the gap between current state and target state, produce a ranked list of **2–4 possible next implementation steps** in this format:

```
Next implementation possibilities:

1. ✅ Recommended: <step name>
   Why now: <reason — no blockers, unblocks most downstream work, etc.>
   Scope: <what files/areas change>

2. <step name>
   Why not yet: <blocker or dependency>
   Scope: <what files/areas change>

3. ...
```

Rules:
- Rank by: fewest blockers first, then by how many downstream steps each one unblocks.
- Mark the top pick with ✅ Recommended.
- Be explicit about any prerequisites that are not yet met.
- Do NOT update any files yet. Wait for the user to confirm a next step.
- Once the user agrees on a step, update ONLY the `## Next Phase` section of `Implementation_planning/progress.md` with the agreed step and a one-line rationale.

After updating `progress.md`, perform the following maintenance checks without waiting for user confirmation:

### Maintenance checks (run automatically after each confirmed next-phase update)

**1. `Implementation_planning/decisions.md` — append session decisions**
- Add a new entry at the top of the file (below the header, above previous entries) in this format:
  ```
  ## YYYY-MM-DD — <phase/feature>
  - <decision>
  - <decision>
  ```
- Include only non-obvious decisions made during this session: scope choices, deferred items, architecture calls, constraint changes. Skip if no meaningful decisions were made.

**2. `Implementation_planning/phases.md` — update if phase scope changed**
- If this session changes phase ordering, promotes/defers an item, or splits/adds a phase item — update `phases.md` accordingly.
- Otherwise leave it untouched.

**3. `CLAUDE.md` — Critical Rules**
- If the backend `UserRole` enum or `permission.py` have changed, update the Keycloak roles bullet to reflect what is done in the backend vs. what still needs Keycloak realm provisioning.
- If any table listed in "schema is sacred" has been deprecated by a phase decision, remove it from the example list and add a deprecation note.
- If any file path in "Read Order" or "Critical Rules" no longer exists at the referenced location, fix the path.

**4. `CLAUDE.md` — Implementation Planning table**
- Ensure every file actively used in planning sessions is listed in the table.
- Add a row for any new file added to `Implementation_planning/` since the last run.

Apply all housekeeping fixes directly. Only flag items to the user if a change requires a product or architecture decision.
