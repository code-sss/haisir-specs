# Current UI Flows Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | dd7da7f (fix(admin): remove response_model from get_board_stats endpoint, 2026-04-20) |
| haisir-frontend | 43fa83d (fix: reorder import for RESERVED_NODE_TYPES, 2026-04-18) |
| haisir-deploy | ccdbad5 (feat(data): add Citizenship, 2026-04-20) |

> Next session: run `git diff 43fa83d..HEAD` in haisir-frontend to see only what changed since this snapshot.

---

## Auth & Root

- Screen: `/` — Landing page for unauthenticated users. Authenticated users are redirected: `admin` role → `/admin`; onboarding incomplete → `/onboarding`; `parent` role → `/parent`; else → `/home`. Waits for `isLoading === false` before redirecting (no premature navigation on cold load).

---

## Onboarding — Student

- Screen: `/onboarding` — Entry guard (ON01). No visible UI. Routes based on auth state:
  - No roles assigned → `/onboarding/role`
  - Roles exist + onboarding complete → `/home`
  - Roles exist + onboarding incomplete → role-aware redirect to ready screen with `?next=proceed`

- Screen: `/onboarding/role` (ON02) — Role selection. User picks "Student" or "Parent" from two cards. On "Continue": calls `POST /api/users/me/assign-role`, writes optimistic role to localStorage, navigates to the matching ready screen (View A).

- Screen: `/onboarding/student-ready` View A — Shown immediately after role assignment while JWT still lacks the student role. Single "Relogin" button that redirects to `/auth/logout` → Keycloak login → fresh JWT with new role.
  - Key behaviour: Relogin uses explicit logout, not `prompt=none` (Safari ITP / Firefox ETP block silent re-auth in iframes).

- Screen: `/onboarding/student-ready` View B (`?next=proceed`) — Shown after relogin once JWT carries the student role. Two CTAs:
  - "Join your school" → `/join-school` (not yet built)
  - "Browse open courses" → `/courses` (not yet built)
  - "Skip — go to dashboard" → `/home`
  - All three exits call `PATCH /api/users/me/onboarding-complete` before navigating and set `haisir_onboarding_done` cookie.
  - Key behaviour: No form fields on this screen (BR-ON-008).

---

## Onboarding — Parent

- Screen: `/onboarding/parent-ready` View A — Same pattern as student View A. "Relogin" → `/auth/logout`.

- Screen: `/onboarding/parent-ready` View B (`?next=proceed`) — One CTA:
  - "Link your child" → `/link-child` (not yet built)
  - "Skip — link later from dashboard" → `/home`
  - All exits call `PATCH /api/users/me/onboarding-complete` before navigating.
  - Key behaviour: No inline code entry on this screen (BR-ON-015); deferred to `/link-child`.

---

## Home Dashboard

- Screen: `/home` — Category grid; hierarchical node navigation (grade → subject → course); topics list for the selected terminal node; inline PDF viewer when a content item is opened. Links to `/exam` and `/assess` per node/topic.
  - Key behaviour: Onboarding guard redirects unauthenticated or non-onboarded users. Breadcrumb tracks navigation path.
  - NOT yet built: two-section layout (Platform Board / Home Study split). Currently shows a single unified content tree with no owner_type filtering.
  - API: `GET /api/categories`, `GET /api/course-path-nodes/*`, `GET /api/topics/{node_id}`, PDF file fetch

---

## Exam Flow (Student)

- Screen: `/exam?node_id=...` (list) — Lists active exam templates for the node. Shows title, description, duration, passing score. "Try Exam" opens summary modal; "View Results" opens attempts list.

- Screen: `/exam` (active session) — Timed exam form. Questions (MCQ + paragraph-based). Timer counts down from `duration_minutes`. Image zoom modal for questions with images. "Submit" sends all answers in one call.
  - API: `POST /api/exams/session/create`, `POST /api/exams/session/{id}/start`, `GET /api/exams/session/{id}/questions`, `POST /api/exams/session/{id}/submit`

- Screen: `/exam` (results) — Score, pass/fail badge, answer review with correct answers highlighted.
  - API: `GET /api/exams/session/{id}/answers`

- Screen: `/exam` (attempts list) — All past sessions with scores. Drill in to review any attempt.
  - API: `GET /api/exams/session/all/{template_id}`

- Key behaviour: Unfinished session resume supported via `GET /api/exams/session/unfinished/{template_id}` check on load.

---

## Legacy Assessment Flow (deprecated — still accessible)

- Screen: `/assess?topic_id=...` — Lists assessments for a topic. Student can start, answer, submit, and review attempts.
  - API: deprecated `/api/assessments/*` endpoints
  - Note: deprecated flow; no new development. Retained as-is.

---

## Exam Template Management (outside current target increment — retained)

- Screen: `/exam` (instructor view) — Template list with Edit/Delete buttons. "+ Add Exam" button navigates to `/add-exam`.
- Screen: `/add-exam` — Multi-field exam authoring form with question builder for MCQ and paragraph questions. Create or edit mode based on `template_id` query param.
  - Note: instructor persona deferred. Screens remain functional in codebase.

---

## Assessment Upload (outside current target increment — retained)

- Screen: `/add-assessment` — Multi-step: upload PDF/file → extracted text review → AI MCQ generation → review and edit MCQs → save.
  - Note: instructor persona deferred. Screen remains functional in codebase.

---

## Admin: Category Management (outside current target increment — retained)

- Screen: `/manage-categories` — Create categories (name, path_type, description) and edit descriptions inline. Admin-role guard redirects non-admins to `/home`.
  - API: `GET/POST /api/categories`, `PATCH /api/categories/{id}`
  - Note: Pre-Phase-1b category management screen. Superseded by the new Admin Board Content Manager below for board/node management; this screen is still functional in the codebase.

---

## Admin: Board Content Manager (Phase 1b)

Route guard: `AdminRouteGuard` in `src/app/admin/layout.tsx` shows a spinner while auth resolves then redirects non-admin to `/home`. Backend also rejects non-admin API calls (defence-in-depth).

**Shell layout** — All `/admin` routes render inside `AdminShell`: topbar + flex-row(`AdminSidenav` | `main`). `AdminSidenav` is a resizable dark sidebar (190px default, 140–300px range) with 2 nav items (🏠 Dashboard → `/admin`, 📚 Board content → `/admin/boards`) and a drag handle on its right edge. Active item highlighted via `usePathname()`.

- Screen: `/admin` — AdminDashboard. **Platform Overview** — 4 stat cards (Platform boards / Live topics / Draft topics / Total topics) fetched from `GET /api/admin/board-stats`. Stat cards use colour-coded left borders (blue / green / amber / gray). If the stats endpoint is unavailable, an alert is shown and cards display “—”. **Boards section** — header with "+ Add board" button (opens AddBoardModal directly from dashboard). Each board renders as a rich card: emoji icon (cycling 📗📘📙…), board name, "{live} live topics · {draft} drafts" subtitle, unconditional "Live" green badge, "Manage" link to `/admin/boards?board={id}`. Click-to-edit board description: click shows inline textarea, Enter/blur calls `PATCH /api/categories/{id}` with `{ description }`, Escape cancels. Empty state: "No boards yet." with the "+ Add board" button still visible.
  - API: `GET /api/categories`, `GET /api/admin/board-stats`, `POST /api/categories`, `PATCH /api/categories/{id}`

- Screen: `/admin/boards` — AdminBoardsPage. Three-panel layout:
  1. **BoardSelectorStrip** — 60px vertical dark strip (`#080F17`), rendered as semantic `<ul>/<li>`. Each board = 40×40px emoji icon `<button>` cycling 📗📘📙, active board highlighted; "+ Add board" `<li>` pinned at bottom. Board change resets the selected node. `?board=` query param validated against `/^[\w-]+$/`; invalid values silently ignored.
  2. **NodeTree** — hierarchical tree of nodes for the active board, fetched via `GET /api/course-path-nodes/tree/{categoryId}`. Tree rebuilt client-side via `buildNestedTree()` (handles both flat and nested API shapes). Each row (`NodeTreeRow`) shows: expand/collapse toggle (disabled for leaf nodes), node name + `NodeTypeChip`, inline actions (+ add child, ✎ rename, × delete) hidden when node has topics. Topics displayed inline as `TopicTreeRows` below their node (live/draft coloured dot + title) — always visible for leaf nodes, visible when expanded for branch nodes. Panel resizable (240px default, 160–500px). `ancestorTypes` passed down the tree for hierarchy enforcement.
  3. **NodeDetailPanel** — shown when a node is selected. **Conditionally renders** based on node type: reserved types (`grade`, `subject`) → `ChildNodesPanel`; non-reserved types → `TopicPanel`. Header shows breadcrumb path, node name chip, and "Type: X · Owner: platform" meta line.
  - API: `GET /api/course-path-nodes/tree/{categoryId}`, `POST /api/course-path-nodes`, `PATCH /api/course-path-nodes/{id}`, `DELETE /api/course-path-nodes/{id}`, `POST /api/categories`, `GET /api/topics/{nodeId}`, `POST /api/topics/`, `PATCH /api/topics/{id}`, `DELETE /api/topics/{id}`
  - Layout wrapper: `AdminProviders` (in `src/app/admin/layout.tsx`) wraps all `/admin` routes; `src/app/admin/error.tsx` is the error boundary.

- Panel: **TopicPanel** — fetches topics for the selected node via `GET /api/topics/{nodeId}`; shows loading spinner, error state, topic list (one TopicRow per topic), and an "+ Add topic" button.

- Row: **TopicRow** — individual topic card with: inline rename (click title → RenameTopicInline), draft/live status toggle ("Set live" / "Set draft" button calling `PATCH /api/topics/{id}`), and a delete (×) button opening DeleteTopicDialog. Now also renders a **content management section** below the topic header: fetches `GET /api/topic-contents/{topicId}`; shows a "Content" label + "Add Content" button (admin accent blue); lists `ContentItemRow`s sorted by `order`; empty state "No content yet — add some." State: `addContentOpen`, `editingContent`, `deletingContent` drive three sub-components.
  - API: `GET /api/topic-contents/{topicId}`, `POST /api/topic-contents/`, `PATCH /api/topic-contents/{id}`, `DELETE /api/topic-contents/{id}`

- Row: **ContentItemRow** — one row per content item: type icon (🎬 video / 📄 pdf / 📝 text / ❓ question / 💬 question_answer), title, optional description (truncated, full text in `title` tooltip), order badge, "Edit" button, × delete button. Edit/delete callbacks passed from `TopicRow`.

- Modal: **AddContentModal** — native `<dialog>`; `mode: 'create' | 'edit'`. Content type selector (`video`/`pdf`/`text` only shown, `disabled` in edit mode — `content_type` immutable after creation). URL field shown for video/pdf; textarea for text content; title, order (number input), description always visible. Zod-validated via React Hook Form (`zodResolver`). Submit shows "Saving…" spinner; inline error on failure. `useFocusTrap` traps keyboard focus.

- Dialog: **DeleteContentDialog** — native `<dialog>` confirmation: "Delete '[title]'? This cannot be undone." Cancel + "Confirm Delete" (danger style); loading state on confirm. Calls `DELETE /api/topic-contents/{id}`; 404 treated as already-gone.

- Inline: **RenameTopicInline** — controlled text input; Enter or blur saves (calls `PATCH /api/topics/{id}` with `{title}`), Escape cancels.

- Modal: **AddTopicModal** — triggered by "+ Add topic". Fields: `title` (required, React Hook Form + Zod). Submits `POST /api/topics/` with `{title, course_path_node_id}`.

- Dialog: **DeleteTopicDialog** — confirmation modal for topic deletion. Calls `DELETE /api/topics/{id}`; handles 409 (`AdminDeleteBlockedError`) by showing a dismissal state with the backend `detail` message directly.

- Modal: **AddNodeModal** — triggered from NodeDetailPanel or NodeTreeRow. Fields: `name` (required, label "Node label", placeholder "e.g. Grade 8, Algebra, Chapter 3…"), `node_type` (chip selector grid, required). **9 chips**: course, chapter, module, section, unit, week, skill (regular — neutral chips), grade, subject (reserved — 🔒 amber chips). Hierarchy enforcement via `isTypeDisabled(type, ancestorTypes)`: root-level → only `grade` enabled; under a single `grade` → only `subject` enabled; deeper → any type not in ancestor chain. Default selection = first enabled type. Modal title: "Add top-level node" or "Add child node" ("Under: {parentNodeName}" subtitle). `owner_type` hardcoded to `"platform"` (not user-editable). Submits `POST /api/course-path-nodes`.

- Modal: **AddBoardModal** — triggered from BoardSelectorStrip and Admin Dashboard header. Fields: `name` (required), `description` (optional textarea, placeholder "e.g. Calgary Board of Education"). `path_type` hardcoded to `"structured"` (not shown to user). Submits `POST /api/categories`.

- Panel: **ChildNodesPanel** — shown in NodeDetailPanel when a reserved-type node (`grade` or `subject`) is selected. Lists direct child nodes as cards showing: 🔒 lock icon (if child is also reserved), child name, topic count (via `useTopics`), and `NodeTypeChip`. Empty state: "No child nodes yet."

- Rows: **TopicTreeRows** — inline topic display within NodeTree rows. Renders for non-reserved node types only (`isReservedType` guard). Each topic shown as a tree row with a coloured dot (green = live, gray = draft) and title. Leaf nodes always show topics; branch nodes show topics only when expanded.

- Domain: **admin-node-domain.ts** — pure functions (no React/Next imports): `isReservedType`, `isTypeDisabled` (hierarchy enforcement), `findNodeById`, `buildBreadcrumb`, `sortNodesByPosition`, `buildNestedTree` (handles both flat and pre-nested API shapes).

- Inline: **RenameNodeInline** — double-click on a node name activates an inline text input. On blur or Enter: submits `PATCH /api/course-path-nodes/{id}` with `{name}` only. Escape cancels without saving.

- Dialog: **DeleteNodeDialog** — triggered from NodeTreeRow action menu. Shows node name and a confirm button. On 409 response from backend: displays a human-readable blocked reason (node has children or topics). On success: removes node from tree and clears node selection if the deleted node was selected.

- Accessibility: `useFocusTrap` hook traps keyboard focus inside any open modal (AddNodeModal, AddBoardModal, DeleteNodeDialog).

---

## Utility

- Screen: `/health` — `GET` returns 204. No UI.
- Screen: `/csp-report` — `POST` accepts CSP violation reports; returns 204. No UI.
- Screen: `/*` (not-found) — 404 fallback page.
