# Implementation Progress

## Target State

This increment targets three personas only: **Student**, **Parent**, and **Platform Admin**. Institutions, instructors, tutors, classes, doubts, hAITU, and notifications are explicitly deferred.

Content is tagged with an `owner_type` discriminator (`'platform'` or `'parent'`) and `owner_id` (NULL for platform; parent `idp_sub` for parent-owned), added via additive `ALTER TABLE` to `course_path_nodes`, `topics`, and `exam_templates`. Platform Admin manages the authoritative platform board (arbitrary-depth `course_path_nodes` tree, topics, exam templates with `owner_type = 'platform'`). Students see two sections on their dashboard: "Platform Board" (blue) containing all platform content, and "Home Study" (green) containing content from their linked parent — visible only if an active `parent_child_links` record exists. Parents are content creators: they can adopt a platform board subtree (deep clone of nodes + topics only; content and exams not cloned) or build their own curriculum from scratch, upload notes per topic, and create private exams. Parent content is visible only to their linked child. Parents view child exam results for their own exams only (not platform exams). Token refresh after role assignment uses explicit logout (`/auth/logout`) — not `prompt=none`. Auth is APISIX-injected JWT with `X-Current-Role` header and CSRF on all mutations; identity is `idp_sub` (Keycloak `sub` as raw UUID string) with no local users table.

## Current State

> Snapshot baseline: haisir-backend `a293bf8` (Phase 1b complete), haisir-frontend `cc9d69a` (Phase 1b-fix complete), haisir-deploy `94bfd1cc` (2026-04-01).
> Next session: `git diff a293bf8..HEAD` in haisir-backend and `git diff cc9d69a..HEAD` in haisir-frontend instead of re-reading the full codebases.

Onboarding for Student and Parent is fully implemented end-to-end. The backend has 21 mapped tables: `user_metadata`, `student_profiles`, `teacher_profiles` (retained, instructor persona deferred), `parent_profiles`, `parent_link_codes`, `parent_child_links`, `class_invite_codes` (retained, class flow deferred), `categories`, a self-referential `course_path_nodes` tree, `topics`, `topic_contents`, `questions`, `paragraph_questions`, an orphaned `answers` table, deprecated `assessments`/`assessment_attempts`/`assessment_answers`, and the unified exam layer: `exam_templates`, `exam_template_questions`, `exam_sessions`, `exam_session_questions`. `owner_type`/`owner_id` columns exist on `course_path_nodes`, `topics`, and `exam_templates`; visibility filtering (BR-DATA-003, BR-SEC-005) is **fully enforced** on all GET endpoints. All error messages are sanitised (generic 403/500 detail strings; role context logged server-side only). Path traversal is hardened in file-serving routes. All route modules are wired with CSRF validation and role-based guards; `assign-role` calls the Keycloak Admin API and accepts only `student` or `parent`. The admin board content manager is fully built end-to-end: backend PATCH/DELETE/tree endpoints plus the admin UI (`/admin`, `/admin/boards`) with board selector, hierarchical node tree, inline rename, add-node modal, and delete confirmation. The admin shell layout is aligned to the prototype: a resizable 190px dark left sidenav (`AdminSidenav`), role-aware root redirect (`/` → `/admin` for admin, `/parent` for parent, `/home` for student/default), `AdminRouteGuard` blocking non-admin access with redirect to `/home`, a resizable 240px node-tree panel, a 60px vertical `BoardSelectorStrip` with emoji icons and "+" add button, and tree node labels at 14px with overflow tooltip — shared `useResize` drag-handle hook used for both panels (no external lib). The frontend (Next.js) also covers: full onboarding flow, course dashboard with hierarchical node navigation and inline PDF viewer, student exam-taking with timer and session resume, plus retained-but-deferred screens. The two-section student dashboard (Platform Board / Home Study split) is not yet built. **Not yet built:** two-section dashboard, parent dashboard and curriculum builder, link-code generation endpoint, pgvector/RAG pipeline, admin topics/content management.

## Completed Phases

### Phase 0 — Onboarding end-to-end: fix ON03/ON05 to spec + onboarding guards ✓

**Completed:** 2026-03-26

**What was done:**
- Replaced `on03-student-profile.tsx` → `on03-student-ready.tsx` (CTA-only: "Join your school", "Browse open courses", "Skip" — no form, per BR-ON-008)
- Replaced `on05-parent-link.tsx` → `on05-parent-ready.tsx` (CTA-only: "Link your child", "Skip" — no inline code input, per BR-ON-015)
- Both ON03/ON05 call `PATCH /api/users/me/onboarding-complete` before any navigation
- Added `onboardingCompleted` state to `useAuth` hook (reads `onboarding_completed_at` from backend)
- Root page (`/`) and home page (`/home`) guard against incomplete onboarding — redirect to `/onboarding`
- Optimistic role pattern: `setCurrentRole()` to localStorage after `assign_role`, `useAuth` falls back to it when backend returns `roles: []`
- Updated routes: `student-profile` → `student-ready`, `parent-link` → `parent-ready`
- Removed unused code: old form components, unused API functions, unused hooks, unused types
- 100% test coverage maintained

**Known issue (pending team discussion):**
- `GET /api/users/me` returns `roles: []` after `assign_role` because APISIX hasn't refreshed the JWT yet (~300 s expiry). Iframe and full-page redirect approaches for forcing JWT refresh are unreliable (cross-origin cookie blocking, redirect loops). The optimistic localStorage fallback works for onboarding navigation but role-gated API calls may fail until the JWT auto-refreshes. Likely needs a backend-side solution (e.g., read roles from DB instead of JWT, or expose a token refresh endpoint).

---

### Phase 1a — owner_type visibility enforcement (BR-DATA-003, BR-SEC-005) ✓

**Completed:** 2026-03-31
**Commit:** haisir-backend `aa5ddf7`

**What was done:**
- Added `OwnerType(StrEnum)` domain type (`platform` / `parent`) to replace raw strings; used across all domain models, schemas, and visibility logic
- Created `src/infrastructure/visibility.py` with `student_visibility_clause(table, viewer_sub)` (BR-DATA-003) and `admin_visibility_clause(table)` (BR-SEC-005) SQL clause builders
- Added visibility-dispatched `*_for_viewer(user: CurrentUser)` methods to `CoursePathNodeService`, `TopicService`, `ExamService`, `TopicContentService` (role dispatch: student → visible, admin → platform_only, instructor → unfiltered / default → platform_only for exams)
- Added matching `*_visible(viewer_sub)` and `*_platform_only()` abstract + concrete repository methods for all four aggregates
- Updated all student/admin-facing GET routes to use the new `*_for_viewer` service methods with `require_any_platform_role()` (student | instructor | admin) guards
- Fixed `exam_session.py` create/get-answers to call `get_by_id_for_viewer` instead of `get_by_id` — closed the session-creation bypass
- Changed `POST /api/topic-contents` from instructor to admin guard
- Fixed TopicContent URL construction to `topics/{content_type}/{filename}`
- Added V23 migration: `owner_id` Integer→String on nodes/topics; `owner_id` added to `exam_templates`; `revoked_at` added to `parent_child_links`
- Added V24 migration: covering index `(child_sub, revoked_at) INCLUDE (parent_sub)` on `parent_child_links`
- Added named permission helper methods (`require_admin`, `require_any_platform_role`, etc.) to `src/auth/permission.py`
- 1708 tests, 100% coverage maintained

**Deviations from original spec:**
- Physical `parent_child_links` columns are `parent_sub`/`child_sub` (not `parent_idp_sub`/`child_idp_sub`); schema is sacred
- Instructor gets `platform_only` (not unfiltered) for exam template listing — data isolation by default; explicit override required if full access is ever needed
- `case _:` default in all service dispatch methods ensures any future role safely defaults to platform-only

---

### Security hardening — error message sanitisation + path traversal ✓

**Completed:** 2026-04-01
**Commit:** haisir-backend `492b320` (+ `589db61` alembic index fix)

**What was done:**
- All 403 responses now return generic `"Forbidden: insufficient permissions"` — role context logged server-side only (no role enumeration in HTTP responses)
- `PATCH /api/users/me/onboarding-complete` tightened to require `student` or `parent` role (was any authenticated user)
- Added `require_student_or_parent()` composite helper to `permission.py`
- Added `SQLAlchemy IntegrityError` handler → `409 "Data conflict"` (prevents schema details leaking to clients)
- Added catch-all `Exception` handler → `500 "Internal server error"` (suppresses stack traces)
- Replaced `JSONResponse` with `ORJSONResponse` project-wide in exception handlers
- Fixed path traversal in `topic_content.py` (FileResponse) and `imageutil.py` (`encode_image_to_base64` / `save_base64_image`) — resolves paths relative to `data_dir` and rejects anything that escapes it
- Fixed bare `except:` (Python-2 style) in `parent.py`
- Alembic V24: added `IF NOT EXISTS` guard for the visibility index (was failing on fresh-then-migrated DBs)
- 1723 tests, 100% coverage maintained

---

### Phase 1b — Admin Board Content Manager: Tree UI + Node CRUD (backend) ✓

**Completed:** 2026-04-02
**Commit:** haisir-backend `a293bf8`

**What was done:**
- `PATCH /api/course-path-nodes/{id}` — rename/reorder platform-owned nodes (admin only)
  - Returns `404` for both not-found and non-platform-owned nodes (oracle protection)
  - `name` validated: `min_length=1`, `max_length=255`; empty string → `422`
  - No-op early return when both `name` and `order` are `None` — avoids pointless `UPDATE` round-trip
- `DELETE /api/course-path-nodes/{id}` — hard-delete node and full subtree (admin only)
  - Returns `409` if any node in the subtree has a `pending` or `ongoing` exam session
  - 12-step cascade: `exam_session_questions` → `exam_sessions` → `exam_template_questions` → `exam_templates` → `assessment_answers` → `assessment_attempts` → `assessments` → `topic_contents` → `topics` → `course_path_nodes` (all atomically; PostgreSQL `ON DELETE NO ACTION` deferred to end of statement for self-referential FK)
- `GET /api/course-path-nodes/tree/{category_id}` — full nested tree for a category (all platform roles)
  - Role-dispatches per Phase 1a visibility rules: `admin` → `platform_only`, `student` → `visible`, `instructor`/default → `get_by_category`
  - Assembles flat DB result into nested tree in Python (`_build_tree`); zero N+1
- 1810 tests, 100% coverage maintained

**Deviations from original spec:**
- Category GET endpoints (`GET /api/categories`, `GET /api/categories/{id}`) were guarded with `require_instructor_or_student()`, silently blocking admin from the board selector sidebar. Changed to `require_any_platform_role()` as a prerequisite bug fix (not in Phase 1b scope but required for the frontend to function).
- Active-session check evaluates `exam_sessions.status IN ('pending', 'ongoing')` directly on subtree nodes. The spec phrased this as "descendant topic has an active exam_session"; since `exam_sessions` link to `course_path_node_id` (not `topic_id`), the CTE traversal over nodes is the correct implementation.

---

### Phase 1b — Admin Board Content Manager: Tree UI + Node CRUD (frontend) ✓

**Completed:** 2026-04-02
**Commit:** haisir-frontend `1923050`

**What was done:**
- New `src/features/admin/` bounded context: API layer, types, hooks, components, domain logic — all isolated
- New routes: `/admin` (AdminDashboard — board list + link to boards manager) and `/admin/boards` (AdminBoardsPage — full board content manager)
- `AdminDashboard`: fetches and lists all boards via `GET /api/categories`; links directly to `/admin/boards?board={id}`
- `AdminBoardsPage`: board selector strip (fetches categories, highlights selected), hierarchical node tree (fetches via `GET /api/course-path-nodes/tree/{categoryId}`), node detail panel (empty state "Select a node" — topics panel is Phase 1c)
- `NodeTree` + `NodeTreeRow`: expand/collapse tree, inline rename on click (`PATCH`), add-child-node modal, delete confirmation dialog (blocks with message on 409)
- `AddBoardModal`: `POST /api/categories` to create a new board
- `AddNodeModal`: `POST /api/course-path-nodes` with `owner_type: "platform"` hardcoded
- `RenameNodeInline`: inline edit with save/cancel, sends `PATCH /api/course-path-nodes/{id}` with `{ name }`
- `DeleteNodeDialog`: sends `DELETE /api/course-path-nodes/{id}`; catches `AdminDeleteBlockedError` (409) and shows reason to admin
- `useFocusTrap` hook: traps keyboard focus inside open modals (accessibility)
- Route guard: `/admin` prefix added to `useAuth` route gates requiring `admin` role
- `?board=` URL param validated against `/^[\w-]+$/` before use (XSS guard)
- 58 files, full test coverage maintained

**Deviations from original spec:**
- Route is `/admin` + `/admin/boards` (not `/admin/board-content` as originally scoped)
- `CreateNodeInput.position` field name differs from backend's `order` field — backend accepts and ignores extra fields; no functional impact but worth aligning in a follow-up

---

### Phase 1b-fix — Admin Layout Alignment + Routing (frontend) ✓

**Completed:** 2026-04-02
**Commit:** haisir-frontend `cc9d69a`

**What was done:**
- `src/app/page.tsx` — role-aware redirect: `admin` → `/admin`, `parent` → `/parent`, default → `/home`; waits for `isLoading === false` before redirecting
- `src/app/admin/layout.tsx` + `AdminRouteGuard` — blocks non-admin role, redirects to `/home`; shows spinner while auth resolves
- `AdminSidenav` — dark sidebar, 190px default, 140–300px resizable range, 2 nav items (🏠 Dashboard, 📚 Board content); active item highlighted via `usePathname()`
- `BoardSelectorStrip` — 60px vertical dark strip (`#080F17`), 40×40px emoji icon buttons cycling 📗📘📙, "+" add button pinned at bottom
- `useResize` hook — vanilla `mousedown`/`mousemove`/`mouseup` drag-handle; 240px default / 160–500px for tree panel
- Sidenav resize — same `useResize` hook reused; 190px default / 140–300px
- Node label text-size audit — 14px (0.875rem, ≥ 13px spec), `title={node.name}` browser tooltip, `text-overflow: ellipsis`

**Deviations from original spec:**
- Sidenav background uses `#1e293b` (dark slate) instead of spec's `#080F17`; all other dimensions and layout match the prototype exactly

---

## Next Phase
<!-- The agreed next concrete step. Updated after each /plan-next-state discussion. -->

### Phase 1c-pre — X-Current-Role Enforcement Audit (backend only)

**Goal:** Audit all backend endpoints to ensure `X-Current-Role` header is required on all role-gated routes. Currently `BR-SEC-006` silently defaults to first JWT role if header is missing — change to `400 Bad Request` ("X-Current-Role header required") for role-gated endpoints. Onboarding endpoints (`/api/users/me`, `/api/users/me/onboarding-complete`, `/api/users/me/assign-role`) remain exempt.

### Then: Phase 1c — Admin Topics Management

Topics panel (right side of board content manager): topic CRUD, content upload, status toggle (Draft ↔ Live), publish flow. As originally scoped.
