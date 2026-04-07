# TASKS — Phase 1c-post: Admin UX Alignment

> Generated from PLAN.md on 2026-04-06.
> Implementers: check off tasks as done. Add blockers to the Blocked section.
> Read `PLAN.md` for full step-by-step detail on each task.

---

## Ready now — Backend (`haisir-backend`)

> A1 and A2 are independent — work in parallel. A3 depends on A1 + A2.

- [ ] **A1** — `src/domain/models/course_path_node.py`: add 6 values to `NodeType(StrEnum)`: `chapter`, `module`, `section`, `unit`, `week`, `skill`. New Alembic migration `V25_extend_nodetype_enum.py`: `ALTER TYPE nodetype ADD VALUE IF NOT EXISTS` for each (autocommit mode required).
- [ ] **A2** — New `src/schemas/admin_stats.py` (`BoardStats`, `PlatformOverview`, `AdminDashboardStats`); new `src/api/routes/admin_stats.py` (`GET /api/admin/board-stats`, admin-only); register in `src/api/router.py` at prefix `/api/admin`. Single JOIN query: `categories → course_path_nodes (platform) → topics (LEFT JOIN)`, grouped by `categories.id`. Add comment: `# If this query becomes slow at scale, consider a materialized view over the same join`.
- [ ] **A3** — Tests: `NodeType` has 9 values; `POST /api/course-path-nodes` accepts `chapter`/`skill`/etc.; `GET /api/admin/board-stats` correct aggregates, zero-topic boards, non-admin 403, missing header 400; maintain 100% coverage.

---

## Ready now — Frontend (`haisir-frontend`)

> B1 and B2 are independent — start in parallel.
> B3 depends on A2 (needs stats endpoint).
> B4 depends on B3.
> B5 depends on B1–B4.

- [ ] **B1** — `add-board-modal.tsx`: add "Description" text field (optional); hardcode `path_type: "structured"` in submit; update `CreateBoardInput` + `AddBoardFormSchema` in `admin.types.ts`; update `createBoard()` in `admin-api.ts` to send `{ name, path_type: "structured", description }`. Title → "Add new board", subtitle per prototype.
- [ ] **B2** — `add-node-modal.tsx`: replace free-text "Type" input with chip selector grid. 9 chips: course, chapter, module, section, unit, week, skill (regular), grade, subject (reserved 🔒 yellow). Default selection: `chapter`. Accept `siblingTypes` prop; disable reserved types already used at same level. New CSS module `add-node-modal.module.css`. Update `AddNodeFormSchema` to `z.enum([...9 values])`. Add `NODE_TYPES` + `RESERVED_NODE_TYPES` constants in `admin.types.ts`. Thread `siblingTypes` from `node-tree.tsx` / `node-tree-row.tsx`.
- [ ] **B3** — Rich dashboard: add `getBoardStats()` API call, `BoardStats`/`AdminDashboardStats` types, `useBoardStats()` hook. Rewrite `admin-dashboard.tsx`: Platform Overview (4 stat cards), rich board cards (emoji, name, stats subtitle, Live badge, Manage button). New CSS module `admin-dashboard.module.css`. Remove "Manage Boards →" link.
- [ ] **B4** — Inline description edit on dashboard board cards: click-to-edit, `PATCH /api/categories/{id}` with `{ description }`. Add `updateBoardDescription()` API + `useUpdateBoardDescription()` mutation. Pattern: copy `RenameNodeInline`.
- [ ] **B5** — Tests for B1 (modal payload fix), B2 (chip grid, reserved types, sibling filtering), B3 (stats rendering), B4 (inline edit); maintain 100% coverage.

---

## Verification checklist

Run these before marking the phase complete.

### Backend
- [ ] `pytest` exits 0 with 100% coverage
- [ ] `NodeType` enum has 9 values (grade, subject, course, chapter, module, section, unit, week, skill)
- [ ] `POST /api/course-path-nodes` with `node_type: "chapter"` → 201
- [ ] `POST /api/course-path-nodes` with `node_type: "skill"` → 201
- [ ] `GET /api/admin/board-stats` returns correct aggregates
- [ ] `GET /api/admin/board-stats` as non-admin → 403
- [ ] V25 migration adds enum values without errors

### Frontend
- [ ] `pnpm test` exits 0 with 100% coverage
- [ ] "+ Add board" creates a board successfully (no 422)
- [ ] Board appears on dashboard with stats (or "0 live topics · 0 drafts")
- [ ] Platform Overview shows correct aggregate numbers
- [ ] Add Node modal shows chip grid; grade/subject have 🔒 icon
- [ ] Already-used reserved types at same level are disabled
- [ ] Dashboard description inline edit saves via PATCH
- [ ] "Manage" button navigates to `/admin/boards?board={id}`

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
