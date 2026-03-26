## Landing / Root
- Screen: `/` — Redirects authenticated users to `/home`; unauthenticated users redirected to Keycloak login

## Student / Instructor — Course Dashboard
- Screen: `/home` — Category picker (board/curriculum tabs), hierarchical node navigation (grade → subject → course), terminal node shows topic list with content actions
- Key behaviour: `useCourseNavigation` drives state machine; selecting a topic surfaces action buttons: view PDF, take assessment, take exam; instructor also sees "Add assessment"

## Student — Assessment Flow
- Screen: `/assess` — Lists assessments for the selected topic; begin a new attempt, resume an unfinished one, or view past attempt results
- Screen: `/add-assessment` — Instructor form: enter title, select questions from the pool; submits to POST /api/assessments/
- Key behaviour: unfinished attempt is detected on load and offered to resume; answers can be submitted per-question or all-at-once; results screen shows per-question correctness and score

## Student / Instructor — Exam Flow
- Screen: `/exam` — Students see active exam list for the current course; instructors see their own templates with edit and delete actions
- Screen: `/add-exam` — Instructor form to build a static exam: add individual questions and paragraph-grouped question blocks; question images encoded as base64 for preview
- Key behaviour: pre-exam summary modal shows question count, duration, and passing score before start; client-side timer enforced during exam; zoomed image modal for question images; past attempts shown in a modal with score history; weighted per-question points and pass/fail displayed in results

## Admin — Manage Categories
- Screen: `/manage-categories` — Create, edit categories (board/curriculum types)
- Key behaviour: admin role required; categories appear in the dashboard category picker

## Onboarding Flow
- Screen: `/onboarding` (ON01 Welcome) — Pure redirect screen; no visible UI for normal users. Auto-redirects based on state: no roles → `/onboarding/role`; roles present + onboarding incomplete → View B of the appropriate ready screen (`/onboarding/student-ready?next=go` or `/onboarding/parent-ready?next=go`); roles present + onboarding complete → `/onboarding/role-switcher`.
- Screen: `/onboarding/role` (ON02 Role Select) — Role selection: Student or Parent only. Calls `POST /api/users/me/assign-role` on "Continue". On success, sets the assigned role in localStorage as an optimistic fallback (the JWT will not include the new role until APISIX auto-refreshes ~300 s later) and navigates to the next step.
- Screen: `/onboarding/student-ready` (ON03 Student Ready) — Two-view screen keyed on `?next=go`:
  - View A (no `?next=go`): Displayed immediately after assign-role. Shows role badge (🎓 Student) and a "Relogin" button. Clicking Relogin navigates to `/auth/logout` — an explicit logout that revokes tokens and clears the APISIX session cookie. After logout, APISIX redirects to `{{BASE_URL}}` (root); root is protected so the OIDC plugin triggers Keycloak login; after login the user lands on `/home`, the onboarding guard redirects to `/onboarding`, and ON01's role-aware redirect sends them to View B (`?next=go`).
  - View B (`?next=go`): Shown after intended JWT refresh. CTAs: "Join your school" → `/join-school`, "Browse open courses" → `/courses`, "Skip — go to dashboard" → `/home`. All exits call `PATCH /api/users/me/onboarding-complete` before navigating.
- Screen: `/onboarding/parent-ready` (ON05 Parent Ready) — Same View A / View B structure as ON03:
  - View A: role badge (👨‍👩‍👧 Parent / Guardian) and Relogin button. Same `/auth/logout` navigation as ON03 — explicit logout → Keycloak login → `/home` → onboarding guard → ON01 role-aware redirect → View B.
  - View B: "Link your child" → `/link-child`, "Skip — link later from dashboard" → `/home`. Exits call `PATCH /api/users/me/onboarding-complete`.
- Screen: `/onboarding/role-switcher` (ON07) — Role switcher for users who hold multiple roles.
- Screen: `/onboarding/complete` (ON08) — Fallback completion screen; calls `PATCH /api/users/me/onboarding-complete`, sets `haisir_onboarding_done` cookie, redirects to `/home`.
- Key behaviour:
  - The `/` root page and `/home` both check `onboarding_completed_at` via `GET /api/users/me` and redirect to `/onboarding` when falsy.
  - Relogin is an explicit logout (`/auth/logout`). The Keycloak session is terminated, tokens are revoked, and the APISIX session cookie is cleared. After logout, the OIDC plugin re-triggers Keycloak login on the next protected request, minting a fresh JWT that carries the newly assigned role.

## Auth / Session (cross-cutting)
- Key behaviour: `useAuth` hook manages CSRF token lifecycle across all pages; `fetchWithCSRFRetry` auto-refreshes CSRF and retries on 403; `X-Current-Role` header sent on every API request; logout clears session via Keycloak

---

## Not yet implemented (Target State gaps)
- hAITU AI tutor chat UI — no screen or component exists
- Curriculum builder (T04 / SA02) — no screen for building arbitrary-depth node trees
- Notifications UI — no notification feed or badge component
- Institution admin flows — no screens for institution management or adoption of board content
- Parent dashboard — no screen to view linked children or their progress
- Tutor course builder — no screen for tutor-owned open courses
