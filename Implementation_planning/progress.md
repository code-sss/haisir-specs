# Implementation Progress

## Target State

This increment targets three personas only: **Student**, **Parent**, and **Platform Admin**. Institutions, instructors, tutors, classes, doubts, hAITU, and notifications are explicitly deferred.

Content is tagged with an `owner_type` discriminator (`'platform'` or `'parent'`) and `owner_id` (NULL for platform; parent `idp_sub` for parent-owned), added via additive `ALTER TABLE` to `course_path_nodes`, `topics`, and `exam_templates`. Platform Admin manages the authoritative platform board (arbitrary-depth `course_path_nodes` tree, topics, exam templates with `owner_type = 'platform'`). Students see two sections on their dashboard: "Platform Board" (blue) containing all platform content, and "Home Study" (green) containing content from their linked parent — visible only if an active `parent_child_links` record exists. Parents are content creators: they can adopt a platform board subtree (deep clone of nodes + topics only; content and exams not cloned) or build their own curriculum from scratch, upload notes per topic, and create private exams. Parent content is visible only to their linked child. Parents view child exam results for their own exams only (not platform exams). Token refresh after role assignment uses explicit logout (`/auth/logout`) — not `prompt=none`. Auth is APISIX-injected JWT with `X-Current-Role` header and CSRF on all mutations; identity is `idp_sub` (Keycloak `sub` as raw UUID string) with no local users table.

## Current State

> Snapshot baseline: haisir-backend `f5ef54f2`, haisir-frontend `a8f71058`, haisir-deploy `94bfd1cc` (2026-03-29).
> Next session: `git diff <commit>..HEAD` in each repo instead of re-reading the full codebase.

Onboarding for Student and Parent is fully implemented end-to-end. The backend has 21 mapped tables: `user_metadata`, `student_profiles`, `teacher_profiles` (retained, instructor persona deferred), `parent_profiles`, `parent_link_codes`, `parent_child_links`, `class_invite_codes` (retained, class flow deferred), `categories`, a self-referential `course_path_nodes` tree (node_type is a fixed enum — grade/subject/course — not yet a free string), `topics`, `topic_contents`, `questions`, `paragraph_questions`, an orphaned `answers` table, deprecated `assessments`/`assessment_attempts`/`assessment_answers`, and the unified exam layer: `exam_templates`, `exam_template_questions`, `exam_sessions`, `exam_session_questions`. `owner_type`/`owner_id` columns exist on `course_path_nodes`, `topics`, and `exam_templates` but visibility filtering (platform always visible, parent-owned only if active `parent_child_links`) is not yet enforced in any endpoint. All route modules are wired with CSRF validation and role-based guards; `assign-role` calls the Keycloak Admin API and accepts only `student` or `parent`. The frontend (Next.js) covers: the full onboarding flow (ON01 guard → ON02 role select → ON03/ON05 ready screens, Relogin via `/auth/logout`, View B CTAs, `PATCH /onboarding-complete` on all exits), a course dashboard with hierarchical node navigation and inline PDF viewer, student exam-taking with timer and session resume, plus retained-but-deferred screens for exam template authoring (`/add-exam`), AI MCQ upload (`/add-assessment`), and admin category management (`/manage-categories`). The two-section student dashboard (Platform Board / Home Study split) is not yet built — the dashboard currently shows a single unified content tree. Routes not yet built: `/join-school`, `/link-child`, `/courses`, `/parent`. No endpoint exists to generate parent link codes from the student side. Infrastructure: PostgreSQL 16, Keycloak 26.4, APISIX with Coraza WAF (OWASP CRS v4 PL2), CrowdSec, rate limiting. **Not yet built:** owner_type visibility filter on all student queries, two-section dashboard, parent dashboard and curriculum builder, link-code generation endpoint, pgvector/RAG pipeline.

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

## Next Phase
<!-- The agreed next concrete step. Updated after each /plan-next-state discussion. -->

**Phase 0 — Fix onboarding flow: skip ON01 welcome, explicit logout for Relogin, ON01 role-aware redirect**

Rationale: Three frontend-only fixes to the onboarding flow. ON01's "Get started" button is unnecessary friction for new users. The Relogin approach is switching from `prompt=none` (silent re-auth) to explicit logout + fresh Keycloak login, which gives a clean JWT with the new role. APISIX's existing `/auth/logout` route and post-logout OIDC re-auth handle the session cycle automatically — no deploy changes needed.

Scope (frontend only):
- **haisir-frontend:**
  - `on01-welcome.tsx`: replace "Get started" button with auto-redirect logic:
    - No roles + onboarding incomplete → auto-redirect to `/onboarding/role` (skip welcome screen)
    - Has roles + onboarding incomplete → auto-redirect to View B of appropriate ready screen (`/onboarding/student-ready?next=go` or `/onboarding/parent-ready?next=go`)
    - Has roles + onboarding complete → redirect to `/onboarding/role-switcher` (existing behaviour, unchanged)
  - `on03-student-ready.tsx` View A: change Relogin `href` from `/auth/login?prompt=none&...` to `/auth/logout`; drop `prompt=none` entirely
  - `on05-parent-ready.tsx` View A: same change as ON03
  - Flow after Relogin: `/auth/logout` → Keycloak login → `/` → `/home` → onboarding guard → `/onboarding` → ON01 role-aware redirect → View B
  - `PATCH /api/users/me/onboarding-complete` remains on View B exit (already wired — no change)
