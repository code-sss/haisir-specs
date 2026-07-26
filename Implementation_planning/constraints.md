# hAIsir — Implementation Constraints

> Things the current implementation imposes on the target state. Surface these when evolving requirements so the target stays compatible with what is already built — or so the cost of diverging is made explicit.
>
> This is distinct from `CLAUDE.md` Critical Rules, which are policy/architecture decisions. Entries here are implementation-reality constraints: things already coded, migrated, or deployed that would require non-trivial rework to change.
>
> **Maintainer:** Update this file when `/update-target-state` surfaces a new constraint, or when a phase decision creates one.

---

## schema — deprecated assessment tables

**What:** `assessments`, `assessment_attempts`, and `assessment_answers` tables are deprecated. The unified model is `exam_templates` with `purpose = 'quiz' | 'exam'`. Existing data migrated as `mode = 'static'`, `purpose = 'quiz'`.
**Why it exists:** Phase 0 consolidation decision (2026-03-22) — two overlapping models were merged.
**Impact on target state:** Any spec referencing `assessments` or `assessment_attempts` must be rewritten to use `exam_templates`. Do not add new columns or endpoints for the deprecated tables.

---

## schema — user identity is `idp_sub`, not a local users table

**What:** There is no local `users` table. Identity is Keycloak `sub` stored as a raw UUID string (`idp_sub`). No FK constraints on user columns.
**Why it exists:** Keycloak is the identity provider; the backend never owns user records.
**Impact on target state:** Any spec that needs to reference a user must use `idp_sub` as a plain UUID column (no FK). No target design can assume a joinable `users` table.

---

## schema — `user_metadata` is minimal by design

**What:** `user_metadata` table contains only `idp_sub` (PK) and `onboarding_completed_at`. No profile data.
**Why it exists:** Phase 0 decision — profile data lives in persona-specific tables (`student_profiles`, `teacher_profiles`, etc.), not a central user record.
**Impact on target state:** Do not add profile fields to `user_metadata`. Route new user attributes to the appropriate persona profile table.

---

## schema — `rate_per_session` removed from teacher profiles

**What:** `rate_per_session` was removed from teacher/tutor profiles. No payment model in v1.
**Why it exists:** Tutors are publishers, not session-based service providers. Payment extensibility is via `subscription_status` / `payment_id` on `enrollments` and `tutor_student_relationships`.
**Impact on target state:** Any monetisation spec must use the `enrollments.subscription_status` / `payment_id` fields, not session-rate columns.

---

## auth — unprovisioned Keycloak roles

**What:** `institution_admin`, `tutor`, and `parent` roles exist in the backend (`UserRole` enum + `permission.py`) but are **not yet added to the Keycloak realm**.
**Why it exists:** Role migration is a controlled process (see `target/requirements/11_role_migration.md`). Backend is ahead of the IdP.
**Impact on target state:** Specs that rely on these roles being active end-to-end cannot be marked "ready to implement" until the Keycloak provisioning steps in `11_role_migration.md` are completed. Flag this when scoping work involving these roles.

---

## auth — APISIX injects the JWT; client never sends Bearer

**What:** The API gateway (APISIX) validates and forwards the JWT as headers to the FastAPI backend. The client sends session cookies; it never constructs or sends a `Authorization: Bearer` header.
**Why it exists:** Security boundary — token validation is centralised at the gateway.
**Impact on target state:** No spec may introduce a client-side Bearer token flow. Any new protected endpoint is automatically covered by the APISIX plugin — no extra auth wiring needed in the spec.

---

## auth — `admin` role cannot be combined

**What:** The `admin` role (Platform Admin) cannot be combined with any other role on the same account (BR-ROLE-004).
**Why it exists:** Privilege isolation.
**Impact on target state:** Any multi-role or role-switching spec must exclude `admin` from the combination matrix.

---

## api — role assignment flows

**What:** Role assignment is not self-service for all roles. `student` and `parent` self-select at onboarding; `tutor` via an explicit "Become a tutor" flow; `instructor` is invited by `institution_admin`; `institution_admin` is assigned by platform admin; `admin` is dedicated accounts only.
**Why it exists:** Phase 0 decision to match trust levels with assignment mechanisms.
**Impact on target state:** Any spec that adds a new role or changes how a role is acquired must be consistent with this assignment model.

---

## ui — ON04 and ON06 removed from onboarding

**What:** Instructor setup (ON04) and Tutor setup (ON06) screens were removed from the onboarding flow.
**Why it exists:** Phase 0 decision — these roles are not self-initiated at onboarding.
**Impact on target state:** Do not re-add these screens to onboarding. Post-onboarding profile completion is the right home for instructor/tutor setup.

---

## ui — institution admin SA03 has no pending tab in v1

**What:** SA03 (student management) has Active + Inactive tabs only. Pending tab is deferred until institution self-registration is built.
**Why it exists:** Phase 1 scope decision — pending state requires a self-registration flow that isn't built yet.
**Impact on target state:** Do not spec pending-state UI for SA03 until institution self-registration is in scope.
