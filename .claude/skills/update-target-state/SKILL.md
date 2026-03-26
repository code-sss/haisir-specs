---
name: update-target-state
description: Review and update target requirements specs in target/requirements/ via guided discussion
---

Launch **two Explore sub-agents in parallel** to read the relevant files simultaneously:

**Agent 1 — Core specs:**
- `target/requirements/00_overview.md` — architecture, personas, design decisions
- `target/requirements/01_data_model.md` — existing schema (extend, never drop/rename)
- `target/requirements/02_auth_and_roles.md` — auth patterns, roles, permission matrix

**Agent 2 — Domain-specific specs and UI:**
- Any other `target/requirements/*.md` files relevant to the domain being discussed
- `target/requirements/ui-mapping/` — UI mapping files for frontend screen details
- `target/prototypes/*.html` — visual reference for UI flows and screen IDs (read only if UI flows are being discussed)

Collect results from both agents before proceeding.

Present a concise summary of what the requirements say across the three domains (schema, API, UI). Note any areas that seem incomplete or ambiguous.

Then ask the user what they want to change, add, or remove. Engage in discussion — ask clarifying questions, flag conflicts with the critical rules in CLAUDE.md (e.g. no dropping columns, no new roles without migration steps), and surface any implications for `Implementation_planning/progress.md` or the implementation sequence.

Do NOT update any files during discussion.

---

Once the user explicitly signals that the discussion is finalised (e.g. "looks good", "update it", "done", "finalise"):

**Before writing, run a Challenger agent** with this prompt:

> "You are reviewing proposed changes to requirements specs for a fullstack edtech app. The proposed changes are: [summarise the agreed changes]. Check for: (1) conflicts with these critical rules — APISIX injects JWT (no Bearer tokens from client), role header is X-Current-Role, CSRF required on all mutations, no local users table (identity is idp_sub as UUID), existing schema is sacred (no drop/rename), no Redux/Axios, SQLAlchemy imperative mapping; (2) inconsistencies with the existing data model or auth spec; (3) downstream implications for the implementation sequence or other personas. Flag anything that should be reconsidered before writing. Be concise."

Present the challenger's findings to the user. If any critical conflicts are flagged, pause and discuss before writing. If only minor notes, proceed and mention them in the summary.

---

Once confirmed (accounting for any challenger flags), update the relevant `target/requirements/*.md` files — only the files that changed. Preserve all existing content that was not discussed.

Then update the `## Target State` section in `Implementation_planning/progress.md` to reflect the new agreed target state as a single clear paragraph.

After updating, briefly summarise what changed across the files.
