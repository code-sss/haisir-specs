# hAIsir — Implementation Phase Guide

> Details live in `target/requirements/`. Update this file when phase ordering
> or scope changes significantly.
>
> Long-term vision phasing is in `vision/phases.md`.

---

## Phase 0 — Foundation ✓ (completed 2026-03-26)

Auth, schema, onboarding.

---

## Phase 1 — Board Content Management (Platform Admin)

Split into sub-phases to keep each deployable unit small:

| Sub-phase | Scope | Depends on |
|---|---|---|
| **1a** ✓ — Owner_type visibility enforcement | Backend-only: apply BR-DATA-003 WHERE clause on all student + admin endpoints | — |
| **1b** ✓ — Admin tree UI + node CRUD | `/admin` + `/admin/boards` pages; `PATCH`/`DELETE` course_path_nodes; full-subtree CTE fetch; admin shell layout | 1a |
| **1c-pre** ✓ — X-Current-Role enforcement | Backend: split `current_active_user` into strict (400 if header missing) + lenient (3 exempt onboarding endpoints). Frontend: confirm all calls send header; fix `position`→`order` dev note | 1b |
| **1c** ✓ — Topics panel | Right-panel topic list + CRUD for selected node; `PATCH`/`DELETE` topics; status toggle (draft/live) | 1c-pre |
| **1c-post** ✓ — Admin UX alignment | Fix Add Board modal (missing `path_type`); chip selector for node types (9 enum values); dashboard stats endpoint + rich cards; inline description edit; sibling-type filtering; 3-tier hierarchy enforcement | 1c |
| **1d** — Topic content upload | PDF/video/text content management per topic; `PATCH`/`DELETE` topic_contents | 1c-post |

See `progress.md` → Next Phase for the detailed scope of the current active sub-phase.
