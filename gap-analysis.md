# hAIsir Gap Analysis — Specs vs Current Implementation

## What Exists Today (Baseline)

| Layer | Current State |
|-------|--------------|
| **Backend** | 11 domain entities, 40+ endpoints, 3 roles (student/instructor/admin), CRUD for courses/topics/questions/assessments/exams, CSRF, JWT validation, 100% test coverage |
| **Frontend** | 6 pages (home, exam, add-exam, assess, add-assessment, manage-categories), auth hooks, CSRF retry, exam authoring, PDF viewer |
| **Deploy** | APISIX gateway (20 plugins, WAF, rate limiting), Keycloak OIDC, PostgreSQL, Docker Compose (dev/staging/prod), release manifests |

---

## Gap Summary by Domain

| Domain | New Tables | New Endpoints | New Frontend Routes | Priority |
|--------|-----------|---------------|-------------------|----------|
| **Role Migration** | 0 (Keycloak config) | 1 (assign-role) | Role switcher, route guards | P0 — blocks everything |
| **User Profiles** | 3 (student/teacher/parent_profiles) + user_metadata | ~8 (CRUD + onboarding) | /profile, /onboarding (8 screens) | P0 |
| **Organizations** | 4 (organizations, org_members, classes, class_enrollments) | ~12 | /teacher/class/*, /institution/* (6 screens) | P1 |
| **Enrollments** | 2 (enrollments, enrollment_topics) | ~6 | /home/dashboard, /home/join-institution, /home/browse | P1 |
| **Doubts** | 2 (doubts, doubt_messages) | ~6 | /doubts, /doubts/:id (4 screens) | P1 |
| **hAITU AI** | 0 (uses Claude API) | 5 (topic-doubt, exam-review, pattern-analysis, teacher-tools, parent-report) | Chat panel (slide-in), exam review panel | P2 |
| **Notifications** | 1 (notifications) + platform_settings | ~4 (list, mark-read, preferences) | Notification bell + feed | P2 |
| **Parent Portal** | 2 (parent_child_links, parent_tutor_messages) | ~8 | /parent (5 screens) | P2 |
| **Tutor Features** | 2 (tutor_student_relationships, topic_reviews) | ~6 | /tutors, /tutors/:sub (discovery + profile) | P2 |
| **Institution Admin** | 1 (board_adoptions) | ~8 | /institution/* (6 screens) | P2 |
| **Platform Admin** | 1 (platform_events) | ~6 | /admin/* (6 screens) | P3 |
| **Schema Extensions** | ALTER on 3 existing tables | Migration endpoints | N/A | P0 |

---

## Breaking Changes Required

### Database (Alembic migrations needed)

| Change | Type | Risk | Detail |
|--------|------|------|--------|
| ADD `owner_type`, `owner_id` to `course_path_nodes` | ALTER TABLE | **Medium** | Existing rows need backfill (`owner_type = 'platform'`, `owner_id = NULL`). All queries touching this table need updating. |
| ADD `status`, `owner_type`, `owner_id` to `topics` | ALTER TABLE | **Medium** | Existing topics get `status = 'live'`, `owner_type = 'platform'`. Topic service must enforce state transitions. |
| ADD `owner_type`, `organization_id` to `exam_templates` | ALTER TABLE | **Low** | Backfill `owner_type = 'platform'`. |
| ADD `paragraph_question_id` to `exam_template_questions` | ALTER TABLE | **Low** | Nullable FK → `paragraph_questions`. Required for paragraph question support in exams (see BR-EXAM-001 in `01_data_model.md`). Plan backfill: existing rows get `paragraph_question_id = NULL`. |
| 24 new tables | CREATE TABLE | **None** | Additive, no existing data affected. |

### Backend Code Changes

| Change | Type | Risk | Detail |
|--------|------|------|--------|
| `UserRole` enum: add `institution_admin`, `tutor`, `parent` | **Breaking** | **High** | Every role check, permission guard, and test that hardcodes roles must be updated. |
| `auth/permission.py`: add 3 new role factories | **Breaking** | **Medium** | `require_institution_admin()`, `require_tutor()`, `require_parent()` |
| `auth/user.py`: role filtering logic | **Breaking** | **Medium** | Currently filters to only student/instructor/admin. Must accept 6 roles. |
| Existing domain models: add `owner_type` fields | **Breaking** | **Medium** | `CoursePathNode`, `Topic`, `ExamTemplate` dataclasses need new fields. |
| Existing repositories: update queries for `owner_type` | **Breaking** | **Medium** | Filtering by ownership affects every query. |
| Existing services: ownership-aware logic | **Breaking** | **High** | CRUD operations must enforce ownership rules (who can create/edit/delete). |
| New DDD layers for 10+ new domains | **Additive** | **Low** | New models, repos, services, routes, schemas for each new domain. |
| Config: add AI/Claude settings, notification settings | **Additive** | **Low** | New pydantic-settings classes. |

### Frontend Code Changes

| Change | Type | Risk | Detail |
|--------|------|------|--------|
| `useAuth` hook: support 6 roles | **Breaking** | **Medium** | Role switching, localStorage key, role metadata (colours, routes). |
| `buildApiHeaders()`: no change needed | **Safe** | **None** | Already sends X-Current-Role from localStorage. |
| `fetchWithCSRFRetry()`: no change needed | **Safe** | **None** | Generic utility. |
| New route guards for `/institution`, `/parent`, `/admin` expanded | **Additive** | **Low** | New middleware/layout checks. |
| 30+ new pages/routes | **Additive** | **Low** | All new, no conflict with existing 6 pages. |
| New components (hAITU chat panel, doubt thread, etc.) | **Additive** | **Low** | New component library additions. |

### Deploy Changes

| Change | Type | Risk | Detail |
|--------|------|------|--------|
| Keycloak: 3 new realm roles | **Config** | **Low** | Via Admin API or console. Non-breaking — existing roles unchanged. |
| APISIX: new route patterns for `/api/students/*`, `/api/haitu/*`, etc. | **Config** | **Low** | Additive routes. Existing routes unchanged. |
| APISIX: role-aware rate limiting (optional) | **Config** | **Low** | Enhancement, not required. |
| Environment variables: Claude API key, AI config | **Config** | **Low** | New env vars for hAITU integration. |

---

## Recommended Implementation Phases

### Phase 0 — Foundation (unblocks everything)
1. Role migration (Keycloak + backend + frontend) per `11_role_migration.md`
2. Schema extensions (ALTER 4 tables + backfill) — `course_path_nodes`, `topics`, `exam_templates`, and `exam_template_questions` (paragraph question support, see BR-EXAM-001)
3. User metadata + onboarding endpoints
4. Onboarding frontend (8 screens)

### Phase 1 — Core Personas
5. Organizations + classes + class enrollments — **must be first**; unblocks structured enrollments and teacher class management
6. Student dashboard + enrollment system — requires classes from item 5 for `POST /api/enrollments` with `type: "structured"` (parallel with 7)
7. Teacher/tutor home + class dashboard — requires classes from item 5 (parallel with 6)
8. Curriculum builder (instructor supplements + tutor full) — requires teacher/tutor home from item 7; makes the system end-to-end usable (teachers need content to put in classes)
9. Doubt system (doubts + messages + escalation) — requires enrollments from item 6 (doubts are scoped to `enrollment_id` + `topic_id`)

> **Dependency graph:** 5 → {6, 7} (parallel) → 8 → 9

### Phase 2 — AI, Notifications & Parent
10. hAITU AI layer (Claude integration, 8 interaction types)
11. Notification system (22 types, polling, cron jobs)
12. Parent portal (5 screens + child linking) — depends on doubt system (Phase 1 item 9) and notification types (`child_doubt_replied`, `child_doubt_auto_closed`, `child_weekly_digest`)

### Phase 3 — Extended Personas
13. Institution admin (6 screens + analytics) — requires doubt stats (Phase 1) and hAITU resolution rates (Phase 2)
14. Platform admin (6 screens + feature flags)
15. Tutor marketplace (discovery, profiles, reviews) — most optional, nothing blocks on it

---

## Decisions Needed Before Implementation

1. ~~**Tutor marketplace gate**: Immediate visibility or admin approval required?~~ **Resolved:** Immediate on toggle, admin can suspend post-hoc. See `02_auth_and_roles.md` section 2.3.
2. ~~**Pagination strategy**: Cursor-based or offset-based? Max page size?~~ **Resolved:** Cursor-based for append-heavy feeds (notifications, activity timeline, doubt threads, chat history); offset-based for management/admin tables (page default 1, page_size default 20, max 100). See `00_overview.md` pagination convention.
3. ~~**File storage**: S3/cloud or local disk for PDFs/images?~~ **Resolved:** Local disk in v1 via `StorageBackend` abstract interface in `infrastructure/storage/`. `STORAGE_BACKEND` env var selects backend (default: `local`). S3/GCS/Azure can be swapped in later. See `00_overview.md` file storage convention.
4. **Search backend**: PostgreSQL full-text or dedicated search service?
5. ~~**Dynamic exam algorithm**: Random, weighted, or coverage-based question selection?~~ **Resolved:** Random selection within matching candidates, with difficulty fallback (`hard → medium → easy`). Full ruleset JSON schema defined in `01_data_model.md` under `exam_templates`. Validated at creation time.
6. **Topic archived correction**: Can tutors clone an archived topic to create a corrected version?
7. ~~**Mastery initial value**: First attempt — is previous_mastery = 0 or = latest_score?~~ **Resolved:** First attempt sets `mastery_score = latest_score` directly. See `01_data_model.md` BR-PROGRESS-003.
8. ~~**Payment extensibility** (flagged): Payment processing is deferred. Before building the tutor-student enrollment record, Tech Lead must confirm the `enrollments` or `tutor_student_relationships` table has a clean place to attach payment/subscription status later without restructuring. No build action needed now — confirmation only.~~ **Resolved:** `subscription_status` (`'free'`|`'paid'`, default `'free'`) and `payment_id` (nullable) columns have been added to `enrollments` and `tutor_student_relationships` tables to support future payment integration without restructuring. All records default to free tier in v1. See `01_data_model.md` BR-ENROLL-PAY-001 and BR-TUTOR-PAY-001.
