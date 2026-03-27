## Public / Unauthenticated
- Screen: `/` (landing) — Hero section, feature cards, "Sign in" button → `/auth/login` (Keycloak OIDC)
- Key behaviour: Auto-redirects authenticated users: onboarding incomplete → `/onboarding`, complete → `/home`

## Onboarding Flow
- Screen: `/onboarding` — Entry guard; auto-routes based on state:
  - No roles → `/onboarding/role`
  - Has roles + onboarding incomplete → `/onboarding/student-ready?next=proceed` or `/onboarding/parent-ready?next=proceed`
  - Has roles + onboarding complete → `/home`
- Screen: `/onboarding/role` (ON02) — Role selection: Student or Parent; calls `POST /api/users/me/assign-role`, sets localStorage fallback, redirects to ready screen
- Screen: `/onboarding/student-ready` (ON03) View A — Shows "Relogin" button; clicking navigates to `/auth/logout` for fresh JWT with new role
- Screen: `/onboarding/student-ready` (ON03) View B (`?next=proceed`) — CTAs: "Join your school" (→ `/join-school`, unimplemented), "Browse open courses" (→ `/courses`, unimplemented), "Skip"; all exits call `PATCH /api/users/me/onboarding-complete`
- Screen: `/onboarding/parent-ready` (ON05) View A — Same Relogin flow as ON03 View A
- Screen: `/onboarding/parent-ready` (ON05) View B (`?next=proceed`) — CTA: "Link your child" (→ `/link-child`, unimplemented), "Skip"; all exits call `PATCH /api/users/me/onboarding-complete`
- Key behaviour: Optimistic role — role written to localStorage immediately after assign-role; `useAuth` falls back to it when backend returns `roles: []` while JWT refreshes (5-min Keycloak token expiry). Cookie `haisir_onboarding_done` set on completion for middleware skip.

## Dashboard / Home
- Screen: `/home` — Welcome banner, category grid, cascading course hierarchy (Category → node children → topics), topic content area
- Key behaviour: Redirects to `/onboarding` if `onboardingCompleted !== true`. Role-aware CTAs: instructor sees "Add Assessment" + exam icon; student sees "Assess" + exam icon. PDF viewer inline-loads on "View PDF". Navigation state preserved in URL query params.

## Exam Flow (Student)
- Screen: `/exam` — Lists available exam templates for a node; "Try" opens exam summary modal → "Begin" creates session and starts timer
- Screen: `/exam` (active) — Renders questions (MC, single choice, FITB, essay, paragraph); timer countdown; Submit button
- Screen: `/exam` (results) — Score display, weighted per-question breakdown, correct answer review
- Screen: `/exam` (history modal) — All past attempts for a template; select to view detailed review
- Key behaviour: State via `useExamPage()`. Session create → start → submit flow. Unlimited retries. Timer enforced client-side.

## Exam Authoring (Instructor)
- Screen: `/exam` (instructor view) — Lists templates for a node; Edit/Delete per template
- Screen: `/add-exam` — Exam builder: title, description, duration, passing score; add/edit/delete questions and paragraph blocks; JSON bulk import; saves via `POST /api/exams/{node_id}/static` or `PATCH /api/exams/{node_id}/static`

## Assessment Flow (Student)
- Screen: `/assess` — Lists assessments for a topic; "Try" → Begin modal → assessment questions (no timer); Submit → instant score; unlimited retries
- Screen: `/assess` (results) — Score and full answer review with explanations
- Key behaviour: State via `useAssessmentState()`. Uses deprecated assessments table flow — no timer.

## Assessment Upload (Instructor)
- Screen: `/add-assessment` Step 1 — Cascading dropdowns (category → grade → subject → chapter), file upload (PDF/text/image); all required before upload
- Screen: `/add-assessment` Step 2 — Review extracted text; "Generate MCQs" (AI call)
- Screen: `/add-assessment` Step 3 — Inline edit/delete generated MCQs; answer must match an option before save; "Confirm & Save" → `POST /api/assessments/` and `POST /api/questions/`

## Category Management (Admin)
- Screen: `/manage-categories` — Create category (name + path_type required, description optional); list all categories; inline edit description
- Key behaviour: Hard redirect to `/home` if `currentRole !== "admin"`.

## Unimplemented Routes (referenced in UI, no screens or backend yet)
- `/join-school` — Student class enrollment via invite code
- `/link-child` — Parent linking child via code entry
- `/courses` — Open course browser
- `/institution` — Institution admin dashboard
- `/parent` — Parent dashboard
