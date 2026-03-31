---
name: update-target-state
description: >
  Reviews and updates near-term target requirements specs in target/requirements/ via guided
  discussion, challenger review, and file updates. Use this whenever the user wants to change,
  add, or remove anything from the product requirements — even if phrased as "update the spec",
  "let's revise X", "I want to add a new field", "change how Z works", or "tweak the data model".
  Also use it for auth rule changes, UI spec updates, or persona flow revisions.
---

Launch **two parallel Agent tool calls** to read the relevant files simultaneously:

**Agent 1 — Core specs:**
- `target/requirements/00_overview.md` — architecture, personas, design decisions (if stub, fall back to `vision/requirements/00_overview.md`)
- `target/requirements/01_data_model.md` — existing schema (extend, never drop/rename)
- `target/requirements/02_auth_and_roles.md` — auth patterns, roles, permission matrix

**Agent 2 — Domain-specific specs and UI:**
- Any other `target/requirements/*.md` files relevant to the domain being discussed (if stub, read the corresponding `vision/requirements/` file for context)
- `target/requirements/ui-mapping/` — UI mapping files for frontend screen details
- `vision/prototypes/*.html` — visual reference for UI flows and screen IDs (read only if UI flows are being discussed)

Collect results from both agents before proceeding.

Present a concise summary using this structure:

```
## Schema
<key tables and columns relevant to the discussion domain>

## API
<key endpoints relevant to the discussion domain>

## UI
<key screens / flows relevant to the discussion domain>

## Gaps / Ambiguities
<anything incomplete, contradictory, or unclear in the current specs>
```

Then ask the user what they want to change, add, or remove. Engage in discussion — ask clarifying
questions, flag conflicts with the critical rules in `CLAUDE.md` (e.g. no dropping columns, no new
roles without migration steps), and surface any implications for `Implementation_planning/progress.md`
or the implementation sequence.

Do not update any files during discussion — changes made before the user has fully articulated their
intent are hard to undo and erode trust in the workflow.

---

Once the user explicitly signals that the discussion is finalised (e.g. "looks good", "update it", "done", "finalise"):

**Before writing, run a Challenger Agent tool call** with this prompt:

> "You are reviewing proposed changes to requirements specs for a fullstack edtech app. The proposed
> changes are: [summarise the agreed changes]. Read `CLAUDE.md` → Critical Rules for the authoritative
> list of constraints. Check for: (1) conflicts with those critical rules, (2) inconsistencies with the
> existing data model or auth spec, (3) downstream implications for the implementation sequence or other
> personas. Flag anything that should be reconsidered before writing. Be concise."

Present the challenger's findings to the user. Then ask explicitly: "Are you happy to proceed with the
write?" — even if the findings are minor. Do not assume silence means consent. If any critical
conflicts are flagged, pause and discuss before writing.

---

Once confirmed (accounting for any challenger flags), update the relevant `target/requirements/*.md` files — only the files that changed. Preserve all existing content that was not discussed.

Then update the `## Target State` section in `Implementation_planning/progress.md` to reflect the new agreed target state as a single clear paragraph.

After updating, summarise what changed using this format:

```
## Changes made
- `<filename>`: <one-line description of what changed and why>
- `<filename>`: <one-line description of what changed and why>

## Preserved unchanged
- <any files explicitly kept as-is>
```
