# hAIsir — Decisions Log

> Running log of decisions made during `plan-next-state` cycles. Newest entry first. Append only — do not edit past entries.

---

## 2026-03-27 — Target state reset: Student + Parent + Platform Admin increment

- **Target state scoped to three personas only:** Student, Parent, Platform Admin. Institutions, instructors, tutors, classes, doubts, hAITU, and notifications explicitly deferred to a future increment.
- **Parent as content creator:** Parents are modelled similarly to tutors (content publishers) but their content is private to one linked child only — no marketplace, no instructor oversight. Parents are solely responsible for quality of content and exams they create.
- **`owner_type` discriminator introduced:** New columns `owner_type` (VARCHAR, NOT NULL, DEFAULT `'platform'`) and `owner_id` (UUID, NULL) added to `course_path_nodes`, `topics`, and `exam_templates` via additive `ALTER TABLE`. `owner_type = 'platform'` for all existing rows (backfill migration provided). `owner_type = 'parent'` for parent-created content with `owner_id = parent.idp_sub`.
- **Content visibility rule:** Platform content visible to all authenticated students. Parent content (`owner_type = 'parent'`) visible only to students with an active (non-revoked) `parent_child_links` record where `parent_idp_sub = owner_id`. Applied as a WHERE clause on all student queries.
- **Adopt/clone flow:** When a parent adopts a platform board subtree, a deep copy of `course_path_nodes` rows + `topics` rows is created with `owner_type = 'parent'`. `topic_contents`, `topic_content_chunks`, `questions`, `exam_templates`, and `exam_template_questions` are NOT cloned — parent populates their own content after adoption. Platform updates to the original do not propagate to parent copies; each copy is independent.
- **Adopt is idempotent:** Second adopt of the same subtree root returns 409 Conflict — no duplicates created.
- **No instructor review gate for parent exams:** Parents create and publish exams directly. No approval flow.
- **Home Study section on student dashboard:** Two distinct sections — "Platform Board" (blue, `#185FA5`) and "Home Study" (green, `#1D9E75`). Home Study section is hidden entirely if no active parent link exists.
- **Token refresh after role assignment:** Explicit logout (`/auth/logout`) not `prompt=none`. Safari ITP and Firefox ETP block third-party cookies in iframes, making silent re-auth unreliable. (Confirmed from 2026-03-26 decision; applies equally to parent role.)
- **Target state prototypes created:** `target/prototypes/haisir_student_flow.html`, `target/prototypes/haisir_parent_flow.html`, `target/prototypes/haisir_admin_flow.html` — interactive HTML prototypes for the three personas.
- **`admin` = Platform Admin only in this increment:** Scoped to platform board content management. No user management, no institution management.
- **Parent exam results scoping:** Parents see child results for parent-owned exams only (`exam_templates.owner_id = parent.idp_sub`). Platform exam results not visible to parents.

---

## 2026-03-27 — Phase 0 onboarding flow — Relogin approach revised + ON01 skip

- Switched Relogin from `prompt=none` silent re-auth to **explicit logout + fresh Keycloak login** (`/auth/logout`). The `prompt=none` approach was already partially implemented but relied on APISIX honouring `redirect_uri` on `/auth/login`, which it does not (static redirect to `/home`). Explicit logout is simpler and gives a guaranteed clean JWT with the new role.
- APISIX `07-auth-login.json` (static redirect to `/home`) left as-is — OIDC plugin on `secured-authenticated` handles auth automatically on any protected route; nobody navigates to `/auth/login` directly.
- ON01 Welcome screen eliminated for first-time users: `/onboarding` auto-redirects to `/onboarding/role` when no roles are present (no "Get started" button click required).
- ON01 gains role-aware redirect for returning users with incomplete onboarding: `student` role → `/onboarding/student-ready?next=go`; `parent` role → `/onboarding/parent-ready?next=go`. This handles the post-Relogin re-entry point cleanly without any APISIX config changes.

---

## 2026-03-26 — Phase 0 onboarding flow — JWT refresh approach

- Replaced iframe `prompt=none` silent refresh with an explicit **Relogin button** on ON03/ON05 View A. Safari ITP and Firefox ETP block third-party cookies in iframes, making the silent refresh fail silently. Full-page `prompt=none` redirect is first-party and works in all browsers; APISIX updates the session cookie during the OIDC flow so no client-side refresh logic is needed.
- ON03 and ON05 split into two views: View A ("You're all set!" + Relogin button) and View B (CTAs). Onboarding is not marked complete until the user exits View B.
- ON07 (role-switcher demo) and ON08 (ready screen) removed from the onboarding flow. Users complete onboarding with a single role; the role switcher is post-onboarding persistent topbar only.
- `PATCH /api/users/me/onboarding-complete` moved from ON08 to ON03/ON05 View B exit (any CTA or skip link).

---

## 2026-03-23 — Phase 1 persona review (Teacher/Tutor, Parent, Institution Admin, Platform Admin)

- Teacher reply edit window: 5-minute window after sending; messages locked after that. `edited_at` (nullable) added to `doubt_messages`.
- Exam results while assignment is open: two-state model — open → submission count + total only (all result fields null); after due date or full submission → full results.
- "Generate remedial assignment" (T08): deferred to Phase 2 entirely — no stub or disabled state in Phase 1.
- Parent status banner thresholds: ok = no weak topics; warn = 1–3 topics mastery 40–59%; danger = any topic < 40% OR more than 3 weak topics.
- Parent max children: capped at 10 per account (BR-PAR-016), enforced at POST /api/parent-child-links with 422.
- CSV enroll for unknown student emails: generate invite links instead of skipping. Backend returns `{email, invite_url}` list; student auto-enrolled on first login via invite URL.
- Board publish propagation: modified topics preserved; unchanged topics updated to new board version.
- Institution admin SA03: no pending state in v1 — Active + Inactive tabs only. Pending tab deferred to when institution self-registration is built.
- Platform admin feature flags: 6 total — added `haitu_enabled_global` (global AI on/off) and `institution_self_registration` (flag defined now, form deferred).
- AI log retention: configurable via `ai_log_retention_days` (default 90 days); scope is `doubt_messages` with `sender_type = 'ai'` only.
- P02 plain-language descriptions: Phase 1 uses static score-based strings; Phase 2 replaces with hAITU prose (no UI change needed).
- Weekly digest: Phase 1 stats-only (streak, topics, courses, weak count); Phase 2 adds hAITU prose.

---

## 2026-03-22 — Phase 0 review (Role Migration, Schema Extensions, User Metadata, Onboarding)

- Tutor model: publishers not session managers — students subscribe independently, tutor cannot remove students.
- Role assignment: `student` and `parent` self-select at onboarding; `tutor` via explicit "Become a tutor" flow; `instructor` invited by institution_admin; `institution_admin` assigned by platform admin; `admin` dedicated accounts only.
- Assessment module deprecated: `assessments`, `assessment_attempts`, `assessment_answers` tables deprecated. `exam_templates` is the unified model with `purpose = 'quiz' | 'exam'`. Existing data migrated as `mode = 'static'`, `purpose = 'quiz'`.
- `keycloak_sub` renamed to `idp_sub` across all specs (IdP-agnostic naming).
- `rate_per_session` removed from teacher profiles (no payment in v1; tutors are publishers not session-based).
- ON02 single-select: Student OR Parent only at onboarding (not both). Other role added later from profile.
- ON04 (Instructor setup) and ON06 (Tutor setup) removed from onboarding flow.
- `user_metadata` table: minimal — `idp_sub` (PK) + `onboarding_completed_at` only.

---

## 2026-03-22 — Phase 1 foundation review (Data model, Auth, Roles)

- Mastery formula: first attempt = raw score; subsequent = (0.6 × latest) + (0.4 × previous). Thresholds: <60 weak, 60–75 progressing, ≥75 completed.
- Pagination: cursor-based for feeds (notifications, doubt threads, chat history); offset-based for management tables (default page=1, page_size=20, max 100).
- File storage: local disk in v1 via `StorageBackend` abstract interface; `STORAGE_BACKEND` env var selects backend. S3/GCS/Azure swappable later.
- Dynamic exam ruleset: `total_questions` required; `difficulty_mix`, `topics`, `tags_include`, `tags_exclude`, `question_types` optional. Random selection with difficulty fallback (hard → medium → easy). Validated at creation time.
- hAITU escalation: structured JSON output (`escalation_ready: true/false`) — not phrase-match on "ask your teacher".
- Payment extensibility: `subscription_status` (`free`/`paid`, default `free`) and `payment_id` (nullable) added to `enrollments` and `tutor_student_relationships` now; all records default to free in v1.
- Search backend: PostgreSQL hybrid — full-text (`tsvector` + GIN) + `pgvector` semantic search. Embedding model: `all-MiniLM-L6-v2` (384-dim, self-hosted sidecar).
- Exam correct-answer mutation risk: UI warning only (no backend lock). Warning shown when editing a question used in completed exam sessions.
- `admin` role isolation: cannot combine with any other role (BR-ROLE-004). Tutor marketplace: immediate visibility on toggle, admin can suspend post-hoc.
