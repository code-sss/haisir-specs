# Current UI Flows Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | a293bf8 (Phase 1b — admin board content manager backend) |
| haisir-frontend | 1923050 (Phase 1b — admin board content manager frontend) |
| haisir-deploy | 94bfd1ccee72d8562aaa3ef2d02cdd10176a2026 |

> Next session: run `git diff 1923050..HEAD` in haisir-frontend to see only what changed since this snapshot.

---

## Auth & Root

- Screen: `/` — Landing page for unauthenticated users. Authenticated users are redirected: onboarding incomplete → `/onboarding`; onboarding complete → `/home`.

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

Route guard: `useAuth` blocks access to any `/admin*` path for non-`admin` roles (redirects to `/home`).

- Screen: `/admin` — AdminDashboard. Lists all boards via `GET /api/categories`. Each board renders as a card with a "Manage Boards →" link to `/admin/boards?board={id}`. Shows an error alert on fetch failure (`isError` state). No empty state message defined yet.
  - API: `GET /api/categories`

- Screen: `/admin/boards` — AdminBoardsPage. Three-panel layout:
  1. **BoardSelectorStrip** — horizontal strip of category buttons; active board highlighted. Board change resets the selected node. `?board=` query param is validated against `/^[\w-]+$/`; invalid values are silently ignored.
  2. **NodeTree** — hierarchical tree of nodes for the active board, fetched via `GET /api/course-path-nodes/tree/{categoryId}`. Each row (NodeTreeRow) shows a NodeTypeChip (grade / subject / course), an inline rename field (RenameNodeInline), and an expand/collapse toggle for children. Selected node is highlighted; click sets the active node in component state.
  3. **NodeDetailPanel** — shown when a node is selected. Currently displays a "Select a node to view its topics" empty state (topics/content panel is Phase 1c). Contains the "Add Node" button to open AddNodeModal.
  - API: `GET /api/course-path-nodes/tree/{categoryId}`, `POST /api/course-path-nodes`, `PATCH /api/course-path-nodes/{id}`, `DELETE /api/course-path-nodes/{id}`, `POST /api/categories`
  - Layout wrapper: `AdminProviders` (in `src/app/admin/layout.tsx`) wraps all `/admin` routes; `src/app/admin/error.tsx` is the error boundary.

- Modal: **AddNodeModal** — triggered from NodeDetailPanel. Fields: `name` (required), `node_type` (grade/subject/course, required), `parent_id` (auto-sets to selected node's id). `owner_type` is hardcoded to `"platform"` (not user-editable). Submits `POST /api/course-path-nodes`.
  - Known deviation: frontend type sends `position?: number` but backend field is named `order`. Backend ignores unknown fields; functionally harmless but must be aligned.

- Modal: **AddBoardModal** — triggered from BoardSelectorStrip. Fields: `name` (required), `path_type` (required), `description` (optional). Submits `POST /api/categories`.

- Inline: **RenameNodeInline** — double-click on a node name activates an inline text input. On blur or Enter: submits `PATCH /api/course-path-nodes/{id}` with `{name}` only. Escape cancels without saving.

- Dialog: **DeleteNodeDialog** — triggered from NodeTreeRow action menu. Shows node name and a confirm button. On 409 response from backend: displays a human-readable blocked reason (node has children or topics). On success: removes node from tree and clears node selection if the deleted node was selected.

- Accessibility: `useFocusTrap` hook traps keyboard focus inside any open modal (AddNodeModal, AddBoardModal, DeleteNodeDialog).

---

## Utility

- Screen: `/health` — `GET` returns 204. No UI.
- Screen: `/csp-report` — `POST` accepts CSP violation reports; returns 204. No UI.
- Screen: `/*` (not-found) — 404 fallback page.
