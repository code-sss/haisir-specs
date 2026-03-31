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

Split into four sub-phases to keep each deployable unit small:

| Sub-phase | Scope | Depends on |
|---|---|---|
| **1a** — Owner_type visibility enforcement | Backend-only: apply BR-DATA-003 WHERE clause on all student + admin endpoints | — |
| **1b** — Admin tree UI + node CRUD | New `/admin/board-content` page; `PATCH`/`DELETE` course_path_nodes; full-subtree CTE fetch | 1a |
| **1c** — Topics panel | Right-panel topic list + CRUD for selected node; `PATCH`/`DELETE` topics | 1b |
| **1d** — Topic content upload | PDF/video/text content management per topic; `PATCH`/`DELETE` topic_contents | 1c |

See `progress.md` → Next Phase for the detailed scope of the current active sub-phase.
