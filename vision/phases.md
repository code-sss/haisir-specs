# hAIsir — Implementation Phase Guide

> Long-term vision phasing. Near-term target phasing lives in `Implementation_planning/phases.md`; simplified target specs in `target/requirements/`.

---

## Phase 0 — Foundation

> Unblocks everything. Must complete before Phase 1.

| Item | Scope |
|---|---|
| 01 · Role migration | Keycloak realm: add `institution_admin`, `tutor`, `parent`. Backend: `UserRole` enum + permission factories. Frontend: `useAuth` role switcher. |
| 02 · Schema extensions | ALTER 4 tables + backfill: `course_path_nodes` (owner_type, owner_id), `topics` (status, owner_type, owner_id), `exam_templates` (owner_type, organization_id, purpose), `exam_template_questions` (paragraph_question_id). |
| 03 · User metadata + onboarding endpoints | `user_metadata` table, 3 profile tables (student/teacher/parent), 7 endpoints incl. assign-role, become-tutor, onboarding-complete. |
| 04 · Onboarding frontend | 4 screens (ON04/ON06/ON07/ON08 removed): ON01 auto-redirects (no "Get started" click) → ON02 (student or parent) → ON03/ON05 (two views each: View A explicit logout Relogin button → View B CTAs). ON01 also handles post-Relogin re-entry (roles present + onboarding incomplete → View B). `PATCH onboarding-complete` on View B exit. |

---

## Phase 1 — Core Personas

> Dependency graph: **05 → {06, 07} (parallel) → 08 → 09**

| Item | Scope | Depends on |
|---|---|---|
| 05 · Organizations + classes | `organizations`, `org_members`, `classes`, `class_enrollments` tables + ~12 endpoints. Everything else in Phase 1 depends on this. | Phase 0 |
| 06 · Student dashboard + enrollment | S01–S07 screens, browse, join institution, topic navigator. `enrollments`, `enrollment_topics` tables. | 05 |
| 07 · Teacher / tutor home | T01–T08 screens, class dashboard, doubt inbox. Two-state exam results (open → counts only / closed → full). 5-min reply edit window. | 05 |
| 08 · Curriculum builder | Instructor supplemental content + tutor full curriculum control. Arbitrary-depth node tree UI. | 07 |
| 09 · Doubt system | `doubts`, `doubt_messages` tables + hAITU escalation chain (structured JSON `escalation_ready` flag). | 06 |

---

## Phase 2 — AI, Notifications & Parent

> Gate: Phase 1 persona review complete (done 2026-03-23). Item 12 unblocked.

| Item | Scope | Depends on |
|---|---|---|
| 10 · hAITU AI layer | 8 interaction types, Claude API, RAG via LlamaIndex + pgvector (`all-MiniLM-L6-v2`). Rate limits: 20/student/hr, 50/teacher/hr. | Phase 1 |
| 11 · Notification system | All notification types, 60s polling, cron jobs (hourly due_soon, weekly digest). | Phase 1 |
| 12 · Parent portal | P01–P05 screens, child linking (max 10), two-level thresholds (warn 40–59% / danger <40%), activity feed, tutor messaging. | 09, 11 |

---

## Phase 3 — Extended Personas

| Item | Scope | Depends on |
|---|---|---|
| 13 · Institution admin | I01–I06 screens, analytics (month/term/all), board adoption, invite links for unknown emails, auto-resolve conflicts. | Phase 1 doubt stats + Phase 2 hAITU rates |
| 14 · Platform admin | SA01–SA06 screens, 6 feature flags: `marketplace`, `open_learning`, `parent_portal`, `public_tutor_profiles`, `haitu_enabled_global`, `institution_self_registration`. | Phase 2 |
| 15 · Tutor marketplace | Discovery, profiles, topic reviews. Most optional — nothing blocks on it. | Phase 2 |

---

## Deferred (post-launch)

- hAITU granular rate limiting (per-interaction-type, burst, cost-based)
- Teacher notes admin override — requires audit-logged feature + legal review
- "Generate remedial assignment" button (T08) — Phase 2 alongside hAITU build
- P02 hAITU plain-language descriptions — Phase 2 upgrade, no UI change needed
- Weekly digest hAITU prose — Phase 2, no notification schema change
- Institution self-registration — flag defined in v1, public form deferred
