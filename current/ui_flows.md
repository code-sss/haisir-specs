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
- Screen: `/onboarding` — Entry point; checks `onboarding_completed_at`; already-onboarded users are bypassed
- Screen: `/onboarding/role` — Role selection: student or parent; calls POST /api/users/me/assign-role
- Screen: `/onboarding/student-profile` — Student enters name, grade, subject preferences; calls POST /api/students/me/profile
- Screen: `/onboarding/parent-link` — Parent enters child's invite code to establish link; calls POST /api/parent-child-links
- Screen: `/onboarding/role-switcher` — Switch active role when a user holds multiple roles
- Screen: `/onboarding/complete` — Confirmation screen; calls PATCH /api/users/me/onboarding-complete
- Key behaviour: flow state managed by React context in `onboarding/providers.tsx`; role determines which steps are shown (student gets profile step, parent gets link step); only steps relevant to the selected role are rendered

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
