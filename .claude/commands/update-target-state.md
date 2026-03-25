Read the following files to understand the full spec and the current target state:

**Source-of-truth specs:**
- `target/requirements/00_overview.md` — architecture, personas, design decisions
- `target/requirements/01_data_model.md` — existing schema (extend, never drop/rename)
- `target/requirements/02_auth_and_roles.md` — auth patterns, roles, permission matrix
- Any other `target/requirements/*.md` files relevant to the domain being discussed
- `target/requirements/ui-mapping/` — UI mapping files for frontend screen details
- `target/prototypes/*.html` — visual reference for UI flows and screen IDs (read only if UI flows are being discussed)

Present a concise summary of what the requirements say across the three domains (schema, API, UI). Note any areas that seem incomplete or ambiguous.

Then ask the user what they want to change, add, or remove. Engage in discussion — ask clarifying questions, flag conflicts with the critical rules in CLAUDE.md (e.g. no dropping columns, no new roles without migration steps), and surface any implications for `Implementation_planning/progress.md` or the implementation sequence.

Do NOT update any files during discussion.

Once the user explicitly signals that the discussion is finalised (e.g. "looks good", "update it", "done", "finalise"), update the relevant `target/requirements/*.md` files — only the files that changed. Preserve all existing content that was not discussed.

Then update the `## Target State` section in `Implementation_planning/progress.md` to reflect the new agreed target state as a single clear paragraph.

After updating, briefly summarise what changed across the files.
