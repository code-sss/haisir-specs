# PLAN — Phase 1c-post: Admin UX Alignment ✓ COMPLETE

> Written: 2026-04-06 · Completed: 2026-04-09
> Phase baseline:
> <!-- plan-baseline: backend:78a5490c08b8bfae5faf8c5bd9e3048043db215a frontend:8b349e55b7bbaaddde2aa8b7efd5182688caea99 deploy:b814471ac9a44b3566abe8a47a46957e2f195ec9 -->
> Completion snapshot:
> <!-- completion-snapshot: backend:819893c990e3db8922dbd239a6c9f4d6e4b90ad0 frontend:dec3ab89429d948c1d01f76b433b37e0b9aebf55 deploy:b814471ac9a44b3566abe8a47a46957e2f195ec9 -->

## Deviations from plan

| Area | Plan said | Implementation did |
|---|---|---|
| Schema/route file naming | `admin_stats.py` for schemas + routes | `admin.py` with `BoardTopicStats` / `PlatformTotals` / `BoardStatsRead` names |
| Node creation validation | No validation beyond enum check | Added ancestor-type exclusion + sibling-type consistency → 409 on violation |
| Topic creation | No `status` field in `TopicCreate` | Added `status: "draft" \| "live"` (required) to `TopicCreate` schema |
| Hierarchy enforcement | Disable reserved types used by siblings | 3-tier: root=grade only, under grade=subject only, deeper=any non-ancestor type |
| NodeDetailPanel | Always renders TopicPanel | Conditional: `ChildNodesPanel` for reserved types, `TopicPanel` for others |
| Inline topics in tree | Not planned | `TopicTreeRows` renders live/draft dot + title inline in NodeTree |
| Modal elements | `<div role="dialog">` | Native `<dialog>` (SonarQube-driven improvement) |
| BoardSelectorStrip | `<div role="list">` | Semantic `<ul>/<li>` |
| Domain logic module | Not planned | `admin-node-domain.ts` with `buildNestedTree`, `isTypeDisabled`, `buildBreadcrumb`, etc. |

---

Fix six UX gaps between the admin prototype (`target/prototypes/haisir_admin_flow.html`) and the current build, found after Phase 1c implementation. These are alignment fixes, not new features. All are scoped to the admin flow's dashboard and board content manager.

---

## Context

### What already exists (Phase 1c)
- `POST /api/categories` — backend accepts `name`, `path_type`, `description` but frontend only sends `name` (add-board broken)
- `NodeType` PG enum: `grade`, `subject`, `course` — prototype shows 9 types
- `AddNodeModal` — free-text input for `node_type`, should be chip selector
- Admin dashboard — bare board list with "Manage Boards →" link, no stats
- `NodeTypeChip` — already has `isReservedType()` logic for grade/subject 🔒
- `/manage-categories` page — full CRUD exists but not linked from admin sidenav
- Board version display — prototype shows "NCERT v2.4" but no `version` column exists in schema

### What is missing (Phase 1c-post scope)
- `AddBoardModal` sends incomplete payload → 422 error on creation
- Node type free-text instead of chip selector with 9 fixed types
- No aggregate stats endpoint (live topics, draft topics per board)
- Dashboard does not show prototype-style rich board cards or overview stats
- Dashboard does not allow inline description editing
- Sibling-type filtering on Add Node modal (no duplicate reserved types at same level)

### Deferred (out of scope)
- Board version/publish workflow — requires schema migration for `version` column on `categories` + publish modal. Tracked for Phase 2+.

---

## Phase A — Backend (`haisir-backend`)

A1 and A2 are independent — run in parallel. A3 depends on A1 + A2.

### A1 — Extend `NodeType` enum

The full node type set (9 values):

| Type | Reserved? |
|---|---|
| grade | Yes (🔒) |
| subject | Yes (🔒) |
| course | No |
| chapter | No |
| module | No |
| section | No |
| unit | No |
| week | No |
| skill | No |

**File:** `src/domain/models/course_path_node.py`
- Add six new values to `NodeType(StrEnum)`: `chapter`, `module`, `section`, `unit`, `week`, `skill`

**New file:** Alembic migration `V25_extend_nodetype_enum.py`
- Add six new enum values to the existing `nodetype` PG enum using `ALTER TYPE nodetype ADD VALUE`:
```python
def upgrade() -> None:
    op.execute("ALTER TYPE nodetype ADD VALUE IF NOT EXISTS 'chapter'")
    op.execute("ALTER TYPE nodetype ADD VALUE IF NOT EXISTS 'module'")
    op.execute("ALTER TYPE nodetype ADD VALUE IF NOT EXISTS 'section'")
    op.execute("ALTER TYPE nodetype ADD VALUE IF NOT EXISTS 'unit'")
    op.execute("ALTER TYPE nodetype ADD VALUE IF NOT EXISTS 'week'")
    op.execute("ALTER TYPE nodetype ADD VALUE IF NOT EXISTS 'skill'")
```
- No downgrade — PG enum value removal is not safely reversible.

> **Note:** `ALTER TYPE ... ADD VALUE` cannot run inside a transaction block in PostgreSQL. The migration must either set `autocommit=True` or use `op.execute()` outside a transaction. See Alembic docs for `transaction_per_migration = False` or use `connection.execution_options(isolation_level="AUTOCOMMIT")` in the migration.

No changes needed to:
- `src/schemas/course_path_node.py` — `CoursePathNodeCreate` already uses `NodeType` enum; new values auto-validate
- `src/schemas/course_path_node.py` — `CoursePathNodeRead` already uses `NodeType` enum; new values auto-serialize

### A2 — Add `GET /api/admin/board-stats` endpoint

New admin-only endpoint that returns aggregate topic counts per board (category) and platform-wide totals.

**New file:** `src/schemas/admin_stats.py`
```python
class BoardStats(BaseModel):
    board_id: UUID4
    board_name: str
    live_topics: int
    draft_topics: int
    total_topics: int

class PlatformOverview(BaseModel):
    platform_boards: int
    live_topics: int
    draft_topics: int
    total_topics: int

class AdminDashboardStats(BaseModel):
    overview: PlatformOverview
    boards: list[BoardStats]
```

**New file:** `src/api/routes/admin_stats.py`
```python
router = APIRouter()

@router.get("/board-stats", response_model=AdminDashboardStats)
async def get_board_stats(
    user: Annotated[CurrentUser, Depends(require_admin())],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AdminDashboardStats:
    """Aggregate topic stats per board for the admin dashboard."""
    ...
```

Implementation approach:
- Single SQL query joining `categories` → `course_path_nodes` (WHERE `owner_type = 'platform'`) → `topics` (LEFT JOIN), grouped by `categories.id`
- Use `CASE WHEN topics.status = 'live' THEN 1 ELSE 0 END` for live/draft counts
- LEFT JOIN ensures boards with zero topics still appear
- Platform overview sums all board stats
- Add inline comment: `# If this query becomes slow at scale, consider a materialized view over the same join`

**File:** `src/api/router.py`
- Register the new route: `app.include_router(admin_stats.router, prefix="/api/admin", tags=["Admin"])`

> **Note:** This endpoint lives at `/api/admin/board-stats`, not under `/api/categories`. It is admin-specific dashboard data, not part of the category CRUD contract.

### A3 — Tests

Required new test cases:
- `NodeType` enum has all 9 values (grade, subject, course, chapter, module, section, unit, week, skill)
- `POST /api/course-path-nodes` accepts new node types (chapter, module, skill, etc.)
- `GET /api/admin/board-stats` returns correct aggregates:
  - Board with mixed live/draft topics → correct counts
  - Board with zero topics → 0/0/0
  - Non-admin role → 403
  - Missing `X-Current-Role` header → 400
- Migration V25 adds enum values (integration test if applicable)
- Maintain 100% coverage

---

## Phase B — Frontend (`haisir-frontend`)

B1 and B2 are independent. B3 depends on A2 (needs stats endpoint spec). B4 depends on B3. B5 depends on B1–B4.

### B1 — Fix Add Board modal (Issue 1)

**Problem:** `createBoard()` sends only `{ name }` but backend requires `path_type`. Board creation fails with 422.

**File:** `src/features/admin/types/admin.types.ts`
- Update `CreateBoardInput`: add `path_type: string` and `description?: string`
- Update `AddBoardFormSchema` (Zod): add `description: z.string().optional()`

**File:** `src/features/admin/api/admin-api.ts`
- Update `createBoard()` to send `{ name, path_type: "structured", description }` in the request body

**File:** `src/features/admin/components/add-board-modal.tsx`
- Add "Description" text field below "Name" (optional, placeholder: "e.g. Calgary Board of Education")
- `path_type` is NOT shown to the user — hardcoded to `"structured"` in the submit handler
- Update modal title to match prototype: "Add new board"
- Add subtitle: "Platform boards can be adopted by parents as a starting structure for Home Study."

### B2 — Chip selector on Add Node modal (Issues 4 + 5)

**Problem:** `AddNodeModal` uses a free-text input for node_type. Prototype shows selectable chips with reserved types locked with 🔒.

**File:** `src/features/admin/types/admin.types.ts`
- Update `AddNodeFormSchema`: change `node_type` from `z.string()` to `z.enum(["grade", "subject", "course", "chapter", "module", "section", "unit", "week", "skill"])`
- Add constants:
  ```typescript
  export const NODE_TYPES = ["course", "chapter", "module", "section", "unit", "week", "skill", "grade", "subject"] as const;
  export const RESERVED_NODE_TYPES = ["grade", "subject"] as const;
  ```

**File:** `src/features/admin/components/add-node-modal.tsx`
- Replace the free-text "Type" input with a **chip selector grid** (`.type-grid` in CSS module)
- Regular types (course, chapter, module, section, unit, week, skill) shown as neutral white/gray chips
- Reserved types (grade, subject) shown as yellow chips with 🔒 prefix, per prototype styling
- Default selection: `chapter` (matches prototype)
- Accept new prop `siblingTypes?: string[]` — array of node types already used by sibling nodes at the same parent level
- If a reserved type (grade, subject) appears in `siblingTypes`, disable that chip (greyed out, not selectable, tooltip: "Already used at this level")
- Regular types are never disabled — they can repeat (e.g. multiple chapters under a subject)
- Update modal title: "Add child node" (with subtitle "Under: {parentNodeName}" or "Top-level node")
- Update field label: "Node label" (not "Name")
- Update placeholder: "e.g. Grade 8, Algebra, Chapter 3…"

**New file:** `src/features/admin/components/add-node-modal.module.css`
- `.typeGrid` — CSS grid wrapping chip buttons
- `.typeChip` — base chip style (border, padding, cursor)
- `.typeChipSelected` — selected state (dark background)
- `.typeChipReserved` — reserved styling (yellow/amber tint, 🔒 icon)
- `.typeChipDisabled` — greyed out, `pointer-events: none`

**File:** `src/features/admin/components/node-tree.tsx` (or `node-tree-row.tsx`)
- When opening AddNodeModal for a child, compute `siblingTypes` from the parent node's existing children:
  ```typescript
  const siblingTypes = parentNode.children
    .map(c => c.node_type)
    .filter(t => RESERVED_NODE_TYPES.includes(t));
  ```
- Pass `siblingTypes` prop to `AddNodeModal`
- For top-level "Add node" button, compute from root-level nodes of the active board

### B3 — Rich dashboard with stats (Issue 6)

**Problem:** Dashboard shows bare board names. Prototype shows Platform Overview stat cards and rich board cards with topic counts and status.

**File:** `src/features/admin/api/admin-api.ts`
- Add `getBoardStats()` → `GET /api/admin/board-stats`
- Returns `AdminDashboardStats` type

**File:** `src/features/admin/types/admin.types.ts`
- Add `BoardStats`, `PlatformOverview`, `AdminDashboardStats` interfaces (matching backend schema)

**File:** `src/features/admin/hooks/use-admin-boards.ts`
- Add `useBoardStats()` — React Query hook wrapping `getBoardStats()`
- Query key: `["admin", "board-stats"]`

**File:** `src/features/admin/components/admin-dashboard.tsx`

Replace the current simple board list with the prototype layout:

1. **Platform Overview** — 4 stat cards in a row:
   - "Platform boards" (blue left border) — count
   - "Live topics" (green left border) — count
   - "Draft topics" (amber left border) — count
   - "Total topics" (gray left border) — count
   - Uses data from `useBoardStats().data.overview`

2. **Boards section** — header with "+ Add board" button, then list of board cards:
   - Each card shows: board emoji icon (cycling 📗📘📙📕📔📓📒📃), board name, subtitle: "{live} live topics · {draft} drafts", a "Live" status badge (green), and a "Manage" button → navigates to `/admin/boards?board={id}`
   - Uses data from `useBoardStats().data.boards` merged with `useAdminBoards().data`

3. Remove the standalone "Manage Boards →" link — the per-board "Manage" button and the sidenav "Board content" link cover this.

**New file:** `src/features/admin/components/admin-dashboard.module.css`
- `.overviewGrid` — 4-column grid for stat cards
- `.statCard` — individual stat card (number + label, left border colour)
- `.boardCard` — board card with icon, name, subtitle, badge, button
- `.liveStatusBadge` — green "Live" pill

### B4 — Inline description edit on dashboard (Issue 2)

**Problem:** Category description editing is only available on the legacy `/manage-categories` page, which is not linked from the admin sidenav.

**File:** `src/features/admin/components/admin-dashboard.tsx`
- Add a click-to-edit description line on each board card (below the stats subtitle)
- If `description` is null/empty, show "Add description…" as placeholder text
- On click: inline text input appears (pattern: copy from `RenameNodeInline`)
- On Enter/blur: call `PATCH /api/categories/{id}` with `{ description }` — the endpoint already exists
- On Escape: cancel edit

**File:** `src/features/admin/api/admin-api.ts`
- Add `updateBoardDescription(id: string, description: string)` → `PATCH /api/categories/{id}` with body `{ description }`

**File:** `src/features/admin/hooks/use-admin-boards.ts`
- Add `useUpdateBoardDescription()` mutation, invalidates `["admin", "boards"]` and `["admin", "board-stats"]` query keys

> **Note:** The `/manage-categories` page is retained in the codebase but NOT linked from the admin sidenav. It is effectively deprecated — its "edit description" capability now lives on the dashboard.

### B5 — Tests

Required test cases:
- `AddBoardModal`: submits `name` + `description` + `path_type: "structured"` → no 422
- `AddBoardModal`: description field is optional → submits without it
- `AddNodeModal`: renders chip grid with 9 types
- `AddNodeModal`: reserved types show 🔒 icon
- `AddNodeModal`: sibling-used reserved types are disabled
- `AddNodeModal`: regular types are never disabled even if used by siblings
- `AddNodeModal`: default selection is "chapter"
- `AdminDashboard`: renders Platform Overview cards with counts from stats endpoint
- `AdminDashboard`: renders board cards with emoji, name, stats subtitle, Live badge, Manage button
- `AdminDashboard`: inline description edit calls PATCH and updates UI
- `AdminDashboard`: empty state (no boards) renders Add Board button
- Maintain 100% coverage

---

## Verification checklist

### Backend
- [ ] `pytest` exits 0 with 100% coverage
- [ ] `NodeType` enum has 9 values
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

## Files changed

### Backend (`haisir-backend`)
| File | Change |
|---|---|
| `src/domain/models/course_path_node.py` | Add 6 values to `NodeType` enum |
| `src/schemas/admin_stats.py` (NEW) | `BoardStats`, `PlatformOverview`, `AdminDashboardStats` schemas |
| `src/api/routes/admin_stats.py` (NEW) | `GET /api/admin/board-stats` endpoint |
| `src/api/router.py` | Register `admin_stats.router` at `/api/admin` |
| `alembic/versions/V25_extend_nodetype_enum.py` (NEW) | Add 6 enum values to `nodetype` PG enum |
| `tests/unit/routes/test_admin_stats.py` (NEW) | Stats endpoint tests |
| `tests/unit/routes/test_course_path_node.py` | New node type acceptance tests |

### Frontend (`haisir-frontend`)
| File | Change |
|---|---|
| `src/features/admin/types/admin.types.ts` | `NODE_TYPES`, `RESERVED_NODE_TYPES` constants; `CreateBoardInput` fix; `BoardStats`, `AdminDashboardStats` types; `AddNodeFormSchema` enum validation |
| `src/features/admin/api/admin-api.ts` | Fix `createBoard` payload; add `getBoardStats`, `updateBoardDescription` |
| `src/features/admin/hooks/use-admin-boards.ts` | Add `useBoardStats`, `useUpdateBoardDescription` hooks |
| `src/features/admin/components/add-board-modal.tsx` | Add description field; fix payload |
| `src/features/admin/components/add-node-modal.tsx` | Chip selector grid, sibling filtering, updated labels |
| `src/features/admin/components/add-node-modal.module.css` (NEW) | Chip grid styling |
| `src/features/admin/components/admin-dashboard.tsx` | Rich cards, stats overview, inline description edit |
| `src/features/admin/components/admin-dashboard.module.css` (NEW) | Dashboard styling |
| `src/features/admin/components/node-tree.tsx` / `node-tree-row.tsx` | Compute + pass `siblingTypes` |
