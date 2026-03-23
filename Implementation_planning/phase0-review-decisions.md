# hAIsir Specs — Phase 0 Review Decisions
> **Review date:** 2026-03-22
> **Reviewer:** Product Manager
> **Scope:** Phase 0 Foundation — Role Migration, Schema Extensions, User Metadata, Onboarding
> **Status:** Complete ✅

---

## How to Use This Document

This file records all PM decisions made during the Phase 0 review. It serves as traceability for why decisions were made and a reference for developers implementing Phase 0.

---

## Item 1: Role Migration

### 1.1 New Roles Confirmed

| Decision | Outcome |
|---|---|
| 3 new roles: `institution_admin`, `tutor`, `parent` | ✅ Confirmed correct and complete for v1 |

### 1.2 Tutor Model Redefined

| Decision | Outcome | Rationale |
|---|---|---|
| Tutors are publishers, not student managers | ✅ Changed | Tutors publish courses; students subscribe/unsubscribe independently. Tutor roster is read-only. |
| Tutors cannot remove students | ✅ Changed | Students control their own enrollment. BR-ENROLL-002 removed. |
| Tutor can send invites | ✅ Confirmed | Student chooses to accept — no forced enrollment. |

**Spec files updated:** `00_overview.md`, `01_data_model.md`, `04_teacher_tutor.md`

### 1.3 Role Assignment Model Overhauled

| Role | Assignment Method | Change from original |
|---|---|---|
| `student` | Self-select at onboarding | Unchanged |
| `parent` | Self-select at onboarding; institution_admin can also invite to link to a student | Unchanged for onboarding; added institutional invite path |
| `tutor` | Separate "Become a tutor" flow (like Udemy) | **Changed** — was self-selectable at onboarding |
| `instructor` | Invited by institution_admin via email/userid | **Changed** — was self-selectable at onboarding |
| `institution_admin` | Assigned by platform admin | Unchanged |
| `admin` | Dedicated accounts only | Unchanged |

**New endpoints:**
- `POST /api/users/me/assign-role` — student/parent only (was all 4 self-assignable roles)
- `POST /api/users/me/become-tutor` — new explicit tutor registration
- `POST /api/admin/invite-role` — new institution_admin invite flow for instructor/parent

**Spec files updated:** `11_role_migration.md`, `09_onboarding.md`

### 1.4 Admin Isolation

| Decision | Outcome |
|---|---|
| `admin` cannot combine with any other role (BR-ROLE-004) | ✅ Confirmed |

### 1.5 Multi-Role Combinations

| Decision | Outcome |
|---|---|
| All non-admin role combinations allowed without restriction | ✅ Confirmed |

---

## Item 2: Schema Extensions

### 2.1 `course_path_nodes` — owner_type + owner_id

| Decision | Outcome |
|---|---|
| Add `owner_type` (`platform`/`institution`/`tutor`) and `owner_id` columns | ✅ Approved |
| Backfill: all existing rows → `owner_type = 'platform'`, `owner_id = NULL` | ✅ Approved |

### 2.2 `topics` — status + owner_type + owner_id

| Decision | Outcome |
|---|---|
| Add `status` (`draft`/`live`/`archived`), `owner_type`, `owner_id` columns | ✅ Approved |
| Backfill: `status = 'live'`, `owner_type = 'platform'`, `owner_id = NULL` | ✅ Approved |
| Tutors can clone archived topics to create corrected versions (BR-CONTENT-005) | ✅ **Resolved** — was pending from Phase 1 review |

**Spec files updated:** `01_data_model.md`, `gap-analysis.md`, `phase1-review-decisions.md`

### 2.3 `exam_templates` — owner_type + organization_id + purpose

| Decision | Outcome | Rationale |
|---|---|---|
| Add `owner_type`, `organization_id` columns | ✅ Approved | |
| Add `purpose` field (`'quiz'` \| `'exam'`) | ✅ **New** | Assessment module deprecated — exam_templates is the unified model |

### 2.4 `exam_template_questions` — paragraph_question_id

| Decision | Outcome |
|---|---|
| Add `paragraph_question_id` (nullable FK, mutually exclusive with `question_id`) | ✅ Approved |

### 2.5 Assessment Module Deprecation (Major Decision)

| Decision | Outcome | Rationale |
|---|---|---|
| Deprecate `assessments`, `assessment_attempts`, `assessment_answers` tables | ✅ Decided | Exam templates are the more flexible model. No need for two parallel systems. |
| `exam_templates` becomes unified model for quizzes and exams | ✅ Decided | `purpose` field distinguishes formative (quiz) from summative (exam) |
| Existing `/assess` and `/add-assessment` routes rewritten to use exam_templates | ✅ Decided | Routes stay, backend switches to exam_templates under the hood |
| Existing assessment data needs one-time Alembic migration | ✅ Planned | Migrate as `mode = 'static'`, `purpose = 'quiz'` |

**Impact:** 45+ references updated across 11 spec files. Notification types renamed (`assessment_due_soon` → `assignment_due_soon`, `assessment_results_ready` → `quiz_results_ready`, `child_assessment_due` → `child_assignment_due`). Parent "Assessments tab" renamed to "Results tab".

**Spec files updated:** `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`, `03_student.md`, `04_teacher_tutor.md`, `05_06_07_personas.md`, `08_haitu_ai_layer.md`, `10_notifications.md`, `ui-mapping/ui_parent_institution_admin.md`, `ui-mapping/ui_notifications.md`, `ui-mapping/ui_teacher.md`

---

## Item 3: User Metadata + Onboarding Endpoints

### 3.1 `user_metadata` Table

| Decision | Outcome |
|---|---|
| Minimal table: `idp_sub` (PK) + `onboarding_completed_at` | ✅ Approved |
| Admin/institution_admin get `onboarding_completed_at = now()` on first login | ✅ Approved |

### 3.2 Profile Tables

| Decision | Outcome |
|---|---|
| `student_profiles` — added `phone` and `avatar_url` fields | ✅ Changed |
| `teacher_profiles` — added `phone`, removed `rate_per_session` | ✅ Changed |
| `parent_profiles` — added `phone` | ✅ Changed |

**Rationale for removing `rate_per_session`:** No payment processing in v1, and tutors are publishers (not session-based). Rate can be added in a future phase when payment is introduced.

### 3.3 IdP-Agnostic Naming

| Decision | Outcome | Rationale |
|---|---|---|
| Rename all `keycloak_sub` → `idp_sub` across specs | ✅ Changed | Keep specs and schema identity-provider-agnostic. Current IdP is Keycloak but naming should not be coupled. |

**Impact:** 90 occurrences renamed across 9 spec files. Identity convention section in `01_data_model.md` updated with naming convention note.

### 3.4 Onboarding Endpoints

| Endpoint | Purpose | Status |
|---|---|---|
| `GET /api/users/me` | User identity + onboarding flag | ✅ Approved |
| `POST /api/users/me/assign-role` | Assign student or parent role | ✅ Approved |
| `POST /api/students/me/profile` | Create student profile | ✅ Approved |
| `POST /api/parent-child-links` | Link parent to child via code | ✅ Approved |
| `PATCH /api/users/me/onboarding-complete` | Mark onboarding done | ✅ Approved |
| `GET /api/parent-link-codes/{code}` | Validate parent link code | ✅ Approved |
| `GET /api/classes/by-invite-code/{code}` | Validate class invite code | ✅ Approved |

---

## Item 4: Onboarding Frontend

### 4.1 Screens Removed

| Screen | Status | Reason |
|---|---|---|
| ON04 (Teacher/Instructor setup) | ❌ Removed from onboarding | Instructors are invited by institution_admin. Profile setup happens on first login. |
| ON06 (Tutor setup) | ❌ Removed from onboarding | Separate "Become a tutor" flow, not part of onboarding. |

### 4.2 Single Role Selection at Onboarding

| Decision | Outcome | Rationale |
|---|---|---|
| ON02 is single-select: Student OR Parent (not both) | ✅ Changed | Simplifies onboarding. Users can add the other role later from profile/settings. |

**Final onboarding flow (6 screens, 4 active):**
```
ON01 (Welcome/Sign-up)
  → ON02 (Pick Student or Parent — single select)
    → ON03 (if Student: name, phone, avatar, grade, subjects, optional invite code)
    → ON05 (if Parent: link child via code, optional)
  → ON07 (Role switcher demo)
  → ON08 (Success — launch dashboard)
```

---

## Summary of All Spec Files Modified

| File | Changes |
|---|---|
| `requirements/00_overview.md` | Open track wording, IdP naming, route updates, assessment deprecation |
| `requirements/01_data_model.md` | IdP naming convention, assessment deprecation, exam_templates `purpose` field, paragraph_question_id, profile table updates (phone, avatar), BR-ENROLL-002 removed, BR-CONTENT-005 (topic clone), BR-EXAM-001 updated |
| `requirements/02_auth_and_roles.md` | IdP naming, permission matrix updated for unified quiz/exam model, notification type renames |
| `requirements/03_student.md` | IdP naming, assessment → quiz/exam references |
| `requirements/04_teacher_tutor.md` | Tutor model (publisher not manager), subscriber language, rate_per_session removed, assessment → quiz/exam, IdP naming |
| `requirements/05_06_07_personas.md` | Parent results tab (was assessments), institution admin wording, IdP naming |
| `requirements/08_haitu_ai_layer.md` | Prompt template updates, IdP naming |
| `requirements/09_onboarding.md` | ON02 single-select, ON04/ON06 removed, rate_per_session removed, IdP naming |
| `requirements/10_notifications.md` | Notification type renames |
| `requirements/11_role_migration.md` | Role assignment model overhaul, 4 sub-flows (onboarding, become-tutor, instructor invite, parent-child linking), IdP naming |
| `requirements/ui-mapping/ui_parent_institution_admin.md` | Results tab rename |
| `requirements/ui-mapping/ui_notifications.md` | Notification type renames |
| `requirements/ui-mapping/ui_teacher.md` | Assignment modal updates |
| `requirements/ui-mapping/ui_student.md` | IdP naming |
| `gap-analysis.md` | Topic clone resolved |
| `phase1-review-decisions.md` | Topic clone resolved |

---

## Still Pending

| Item | Status | Owner |
|---|---|---|
| Phase 1 persona review (Student, Teacher/Tutor, Parent, Institution Admin, Platform Admin screens) | 🔜 Not started | PM |
| Search backend decision (PostgreSQL full-text or dedicated service) | ❓ Unresolved | Tech Lead |
| Assessment data migration plan (existing data → exam_templates) | ✅ Complete — migration already handled. Existing data migrated to `exam_templates` with `mode = 'static'` and `purpose = 'quiz'`. | — |
