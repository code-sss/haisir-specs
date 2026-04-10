# TASKS — Phase 1c-post: Admin UX Alignment ✓ COMPLETE

> Generated from PLAN.md on 2026-04-06. Completed 2026-04-09.
> Commits: haisir-backend `819893c`, haisir-frontend `dec3ab8`
> Archived plan: `Implementation_planning/archive/phase1c-post-plan.md`

---

## Ready now — Backend (`haisir-backend`)

> A1 and A2 are independent — work in parallel. A3 depends on A1 + A2.

- [x] **A1** — `src/domain/models/course_path_node.py`: add 6 values to `NodeType(StrEnum)`: `chapter`, `module`, `section`, `unit`, `week`, `skill`. New Alembic migration `V25_expand_nodetype_enum.py`: `ALTER TYPE nodetype ADD VALUE IF NOT EXISTS` for each.
- [x] **A2** — New `src/schemas/admin.py` (`BoardTopicStats`, `PlatformTotals`, `BoardStatsRead`); new `src/api/routes/admin.py` (`GET /api/admin/board-stats`, admin-only); registered in `src/api/router.py` at prefix `/api/admin`. Also added ancestor-type exclusion + sibling-type consistency validation to `POST /api/course-path-nodes` (409 on violation). `TopicCreate` now accepts `status` field.
- [x] **A3** — Tests: all passing; 100% coverage maintained.

---

## Ready now — Frontend (`haisir-frontend`)

> B1 and B2 are independent — start in parallel.
> B3 depends on A2 (needs stats endpoint).
> B4 depends on B3.
> B5 depends on B1–B4.

- [x] **B1** — `add-board-modal.tsx`: description textarea added; `path_type: "structured"` hardcoded; `CreateBoardInput` + `AddBoardFormSchema` updated; `createBoard()` sends full payload.
- [x] **B2** — `add-node-modal.tsx`: chip selector grid with 9 types (add-node-modal.module.css new). `ancestorTypes` prop enforces 3-tier hierarchy (root=grade only, under grade=subject only, deeper=any non-ancestor). `isTypeDisabled` pure fn in `admin-node-domain.ts`. `AddNodeFormSchema` uses `z.enum([...NODE_TYPES])`.
- [x] **B3** — Rich dashboard: `getBoardStats()`, `useBoardStats()`, 4-stat Platform Overview cards, rich board cards (emoji, name, live/draft counts, Live badge, Manage button), `admin-dashboard.module.css` new. Also added `ChildNodesPanel` + `TopicTreeRows` (inline topics in tree). `NodeDetailPanel` now conditionally renders ChildNodesPanel (reserved types) or TopicPanel (others).
- [x] **B4** — `updateBoardDescription()` + `useUpdateBoardDescription()` added. Inline description edit on dashboard.
- [x] **B5** — All tests passing; 100% coverage maintained.

---

## Verification checklist

Run these before marking the phase complete.

### Backend
- [x] `pytest` exits 0 with 100% coverage
- [x] `NodeType` enum has 9 values (grade, subject, course, chapter, module, section, unit, week, skill)
- [x] `POST /api/course-path-nodes` with `node_type: "chapter"` → 201
- [x] `POST /api/course-path-nodes` with `node_type: "skill"` → 201
- [x] `GET /api/admin/board-stats` returns correct aggregates
- [x] `GET /api/admin/board-stats` as non-admin → 403
- [x] V25 migration adds enum values without errors

### Frontend
- [x] `pnpm test` exits 0 with 100% coverage
- [x] "+ Add board" creates a board successfully (no 422)
- [x] Board appears on dashboard with stats (or "0 live topics · 0 drafts")
- [x] Platform Overview shows correct aggregate numbers
- [x] Add Node modal shows chip grid; grade/subject have 🔒 icon
- [x] Already-used reserved types at same level are disabled (3-tier hierarchy)
- [x] Dashboard description inline edit saves via PATCH
- [x] "Manage" button navigates to `/admin/boards?board={id}`

---

## Blocked

> Nothing blocked at time of writing.

---

## Notes for implementers

- Full step-by-step detail: `Implementation_planning/PLAN.md`
- Critical rules (CSRF, role header, oracle protection, imperative mapping): `CLAUDE.md`
- Visual spec: open `target/prototypes/haisir_admin_flow.html` in a browser — it is the authoritative layout reference
- Backend pattern files: `src/api/routes/category.py` (category CRUD), `src/api/routes/course_path_node.py` (node CRUD + guards)
- Frontend pattern files: `src/features/admin/components/rename-node-inline.tsx` (inline edit pattern), `src/features/admin/components/node-type-chip.tsx` (reserved type logic)
- Alembic note: `ALTER TYPE ... ADD VALUE` cannot run inside a transaction. Use `autocommit` or `connection.execution_options(isolation_level="AUTOCOMMIT")`.
