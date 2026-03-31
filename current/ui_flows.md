# Current UI Flows Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | f5ef54f2f4ccdeb2c295a8546462e57ba0ba17c7 |
| haisir-frontend | a8f710580075ed2c1552f970d607860a1c844abb |
| haisir-deploy | 94bfd1ccee72d8562aaa3ef2d02cdd10176a2026 |

> Next session: run `git diff a8f71058..HEAD` in haisir-frontend to see only what changed since this snapshot.

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
  - Note: Platform Admin persona is in current target scope but the full admin flow is not yet built. This is the only admin UI present.

---

## Utility

- Screen: `/health` — `GET` returns 204. No UI.
- Screen: `/csp-report` — `POST` accepts CSP violation reports; returns 204. No UI.
- Screen: `/*` (not-found) — 404 fallback page.
