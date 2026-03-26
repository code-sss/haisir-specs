# Implementation Progress

## Target State

hAIsir is a multi-persona edtech platform serving six roles — student, instructor, tutor, institution admin, parent, and platform admin (SuperAdmin). Content is organised in a self-referential `course_path_nodes` tree of arbitrary depth (free-string `node_type`; only `grade` and `subject` have reserved system behaviour), with `topics` attached exclusively to leaf nodes and up to one `topic_contents` item per type (PDF, video, text) per topic. A LlamaIndex ingestion pipeline chunks and embeds PDF/text content into `topic_content_chunks` (pgvector, `all-MiniLM-L6-v2`, 600-char / 100-char overlap) so that hAITU — the embedded AI tutor — can answer student topic doubts via RAG retrieval (top-5 chunks scoped by `topic_id`) rather than context-stuffing; video-only topics fall back to `text_extracted`. The platform supports structured board curricula (NCERT, CBSE, ICSE, Cambridge, IB MYP) and tutor-built open courses (modular, flat, week-based, section-based), with institution adoption cloning board content into institution-owned copies. The curriculum builder (T04 for tutors, SA02 for platform admins) exposes an arbitrary-depth node tree with a type-picker UI (default chips + custom free text; reserved types shown with 🔒) and enforces the leaf-node rule at the API layer. Assessments (quizzes and exams) are authored via `exam_templates` and assigned to classes with due dates; post-assignment results drive hAITU exam analysis and teacher recommendations. A full notification pipeline covers doubt escalations, assignment due dates, exam results, and at-risk student alerts across all personas. Onboarding flows handle student, teacher/tutor, parent, and institution admin registration including role migration from existing `instructor`/`admin` Keycloak roles. Auth is APISIX-injected JWT with `X-Current-Role` header and CSRF on all mutations; identity is Keycloak `sub` with no local users table.

## Current State
The core content-delivery and assessment loop is fully implemented. The backend has 21 mapped tables covering categories, a three-level course path node tree (grade/subject/course enum — not yet a free string), topics, topic contents (PDF/video/text), questions, paragraph questions, assessments with attempt/answer tracking, static exam templates with per-question points, exam sessions with weighted scoring and pass/fail, and a complete user-metadata layer (onboarding state, student profiles, teacher profiles, parent-child invite codes, class invite codes). All 17 route modules are wired with CSRF validation and role-based guards (`student`, `instructor`, `admin`); the `assign-role` endpoint is fully wired — `KeycloakAdminClient` in `src/infrastructure/keycloak_admin.py` performs the client-credentials token exchange and POSTs to `/admin/realms/{realm}/users/{id}/role-mappings/realm`; Keycloak Admin credentials are configured via `OAUTH__KEYCLOAK__ADMIN_CLIENT_ID` / `OAUTH__KEYCLOAK__ADMIN_CLIENT_SECRET`. The frontend (Next.js) covers the course dashboard with hierarchical navigation, assessment flow (take / resume / review), static exam flow (instructor create/edit, student take/review with timer and weighted results), category management for admins, and a full onboarding flow. The onboarding flow always starts at ON01 Welcome (`/onboarding`) — a "Get started" button leads to ON02 role selection; there is no auto-skip to role selection for first-time users. After `assign-role`, ON03 (`/onboarding/student-ready`) and ON05 (`/onboarding/parent-ready`) each show View A with a Relogin button, then View B with CTAs after JWT refresh. Relogin is a silent OIDC re-authentication (`prompt=none`) and does NOT log the user out. However, in the current deploy APISIX's `/auth/login` route has a static `redirect` plugin pointing to `/home` — it does not initiate the Keycloak OIDC flow and ignores the `redirect_uri` param, so Relogin currently lands the user on `/home` rather than refreshing the JWT and returning to View B. Infrastructure runs PostgreSQL 16, Keycloak 26.4, and APISIX with Coraza WAF, CrowdSec, and rate limiting. The deploy-side Keycloak realm roles (`institution_admin`, `tutor`, `parent`) have been added to `common/keycloak/02-roles.json`. **Not yet built:** the `topic_content_chunks` pgvector table and LlamaIndex RAG pipeline (hAITU), curriculum builder UI, notifications, institution admin flows, parent dashboard, and tutor course builder.

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
