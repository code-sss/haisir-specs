# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:d927209 frontend:d178c98 deploy:790e29d (2026-08-21)
> All three working trees clean at scoping. Specs baseline `510bbd8`. Alembic head V43; this phase adds V44.
> T2.2/T2.5–T2.9 [frontend] committed (`6d3e08b`) and pushed to `origin/main`.
>
> **Phase 8 — Parent UX Alignment.** Scoped 2026-08-20 via `/plan`. 62 leaf tasks across four repos.
> Goal tree, per-task Build/Done-when/Test, the scope locks and the four corrections taken at
> planning are in `PLAN.md`.
>
> **Start with T1.3, T1.2 and T1.10.** All of G1 hangs off those three. G0 is opportunistic and
> **nothing depends on it** — it is not a blocker, despite what the (now-corrected) B49 entry said.
>
> Bolded rows are goal/subgoal-level tests — they can only pass once every child task above them is
> checked.
>
> **Release-coupling**: G1.2 [backend] and G1.4 [frontend] must deploy in the same window —
> `child_subs` is a hard 400 with no fallback. **V44 is a migrating deploy**: stop the worker first
> (`constraints.md:117`), take the pre-deploy dump + datadir tarball (`:125`).

## G0 [deploy][specs]: B49 record corrected, prod render path confirmed
- [x] T0.1 [deploy]: Capture prod's render-side confirmation (2026-08-25)
- [x] T0.2 [specs]: Correct the B49 backlog entry (2026-08-21)
- [x] **G0: B49 record corrected, prod render path confirmed** — E2E test — PASSED 2026-08-25: Jenkins
      CI/CD prod deploy (v2026.8) log shows `template-configs.sh` Step 4 with zero
      `ERROR: unresolved secret placeholder(s)` occurrences (the `:355-373` scan covers
      `ALERT_SLACK_WEBHOOK` via `ALERTMANAGER_TEMPLATED_DIR`) and `DEPLOYMENT COMPLETE` / exit 0 on
      both staging and prod hosts. `phases.md` B49 marked CLOSED.

## G1 [backend][frontend][specs]: Per-child Home Study binding

### G1.1 — Binding schema + behaviour-preserving migration
- [x] T1.3 [specs]: BR-DATA-026 DDL types child_sub as String
- [x] T1.4 [specs]: BR-DATA-026 backfill binds revoked pairs too
- [x] T1.2 [backend]: root_node_id column on the three owner-scoped tables (2026-08-21)
- [x] T1.1 [backend]: parent_content_bindings table model (depends on T1.3) (2026-08-21)
- [x] T1.5 [backend]: V44 schema half (depends on T1.1, T1.2) (2026-08-21)
- [x] T1.6 [backend]: V44 root_node_id backfill (depends on T1.5) (2026-08-21)
- [x] T1.7 [backend]: V44 bindings backfill (depends on T1.5, T1.4) (2026-08-21)
- [x] **G1.1: Binding schema + behaviour-preserving migration** — integration test — PASSED
      2026-08-27 — executed in CI against a live Postgres. `haisir-backend/Jenkinsfile:99-160`
      starts a `pgvector/pgvector:pg18` container, applies `alembic upgrade head` (V44 included)
      to it, then runs the full `tests/` suite with `INTEGRATION_DB_URL` set — so the formerly
      `INTEGRATION_DB_URL`-gated integration tests executed and gated the build
      (`--cov-fail-under=100`, `junit allowEmptyResults: false`). That green build shipped as
      v2026.8 to staging and prod 2026-08-25. Covers
      `tests/integration/phase8/test_v44_parent_content_bindings.py` (4 tests) plus the `alembic
      upgrade head` step itself, which is this subgoal's migration test.

### G1.2 — Write path stamps root_node_id and bindings
- [x] T1.10 [backend]: child_subs on the two create payloads (2026-08-21)
- [x] T1.19 [backend]: GET /api/parent/children?include_revoked=true (2026-08-21)
- [x] T1.8 [backend]: ParentContentBindingRepository (depends on T1.1) (2026-08-21)
- [x] T1.9 [backend]: Bind-time validation is all-or-nothing (depends on T1.8) (2026-08-21)
- [x] T1.11 [backend]: create_node stamps root_node_id (depends on T1.2) (2026-08-21)
- [x] T1.13 [backend]: adopt_node stamps root_node_id on every clone (depends on T1.2) (2026-08-21)
- [x] T1.12 [backend]: create_node binds the named children (depends on T1.9, T1.11, T1.10) (2026-08-21)
- [x] T1.14 [backend]: adopt_node binds the named children (depends on T1.9, T1.13, T1.10) (2026-08-21)
- [x] T1.15 [backend]: Parent topic create stamps root_node_id (depends on T1.11) (2026-08-21)
- [x] T1.16 [backend]: POST /nodes/{root_id}/bindings (depends on T1.9) (2026-08-21)
- [x] T1.17 [backend]: DELETE /nodes/{root_id}/bindings/{child_sub} (depends on T1.8) (2026-08-21)
- [x] T1.18 [backend]: child_subs on parent root reads (depends on T1.8) (2026-08-21)
- [x] **G1.2: Write path stamps root_node_id and bindings** — integration test — PASSED 2026-08-27
      — executed in CI against a live Postgres. `haisir-backend/Jenkinsfile:99-160` starts a
      `pgvector/pgvector:pg18` container, applies `alembic upgrade head` (V44 included) to it,
      then runs the full `tests/` suite with `INTEGRATION_DB_URL` set — so the formerly
      `INTEGRATION_DB_URL`-gated integration tests executed and gated the build
      (`--cov-fail-under=100`, `junit allowEmptyResults: false`). That green build shipped as
      v2026.8 to staging and prod 2026-08-25.

### G1.3 — Read path enforces both terms, everywhere
- [x] T1.20 [backend]: The clause gains the binding EXISTS (depends on T1.2, T1.6) (2026-08-21)
- [x] T1.21 [backend]: _resolve_parent_nodes filters service-side (depends on T1.8) ← **the failure mode** (2026-08-21)
- [x] T1.22 [backend]: hAITU gate gains the binding term (depends on T1.8, T1.2) (2026-08-21)
- [x] **G1.3: Read path enforces both terms, everywhere** — integration test — PASSED 2026-08-27 —
      executed in CI against a live Postgres. `haisir-backend/Jenkinsfile:99-160` starts a
      `pgvector/pgvector:pg18` container, applies `alembic upgrade head` (V44 included) to it,
      then runs the full `tests/` suite with `INTEGRATION_DB_URL` set — so the formerly
      `INTEGRATION_DB_URL`-gated integration tests executed and gated the build
      (`--cov-fail-under=100`, `junit allowEmptyResults: false`). That green build shipped as
      v2026.8 to staging and prod 2026-08-25. Covers `test_g6_visibility_student_read_paths.py` —
      the T1.21 failure mode.

### G1.4 — Parent binds content at create time (ships in lockstep with G1.2)
- [x] T1.23 [frontend]: Child multi-select in the Add Root modal (2026-08-21)
- [x] T1.25 [frontend]: Child multi-select in the Adopt modal (2026-08-21)
- [x] T1.24 [frontend]: createNode sends child_subs (depends on T1.23, T1.10 [backend]) (2026-08-21)
- [x] T1.26 [frontend]: adoptSubtree sends child_subs (depends on T1.25, T1.10 [backend]) (2026-08-21)
- [x] T1.27 [frontend]: Privacy pill renders the real binding set (depends on T1.18 [backend]) (2026-08-22)
- [x] T1.28 [frontend]: Binding editor on an existing root (depends on T1.16, T1.17 [backend], T1.27) (2026-08-22)
- [x] T1.29 [frontend]: Revoked-but-bound child greyed in the pill (depends on T1.19 [backend], T1.27) (2026-08-22)
- [x] **G1.4: Parent binds content at create time** — integration test (2026-08-22) — subgoal test (vitest+MSW)
      behaviours covered at 100%: Add-Root submit-disabled-without-selection (T1.23), POST `child_subs`
      (T1.24), pill "Visible to Arjun and Meera" (T1.27), editor uncheck fires
      `DELETE /nodes/{root}/bindings/{sub}` (T1.28 — `parent-binding-editor` + `parent-curriculum-api`
      tests), pill re-derives "Visible to Arjun" after the tree refetch (T1.27/T1.28 invalidation).

### G1.5 — Regression fixtures survive the breaking change
- [x] T1.30 [backend]: linked_child fixture helper (depends on T1.8) (2026-08-21)
- [x] T1.31 [backend]: Rewrite the cross-owner 404 sweep (depends on T1.30, T1.20) (2026-08-22)
- [x] T1.32 [backend]: Rewrite the E2E journey test (depends on T1.30, T1.21) (2026-08-22)
- [x] **G1.5: Regression fixtures survive the breaking change** — integration test — PASSED
      2026-08-27 — executed in CI against a live Postgres. `haisir-backend/Jenkinsfile:99-160`
      starts a `pgvector/pgvector:pg18` container, applies `alembic upgrade head` (V44 included)
      to it, then runs the full `tests/` suite with `INTEGRATION_DB_URL` set — so the formerly
      `INTEGRATION_DB_URL`-gated integration tests executed and gated the build
      (`--cov-fail-under=100`, `junit allowEmptyResults: false`). That green build shipped as
      v2026.8 to staging and prod 2026-08-25. Covers the T1.31/T1.32 rewritten fixtures: the G3.1
      cross-owner 404 sweep and `test_g7_1_e2e_journey_integration.py`.

### G1.6 — Specs stop contradicting the shipped rule
- [x] T1.33 [specs]: 03_student.md BR-STU-001 two-term rewrite (2026-08-21)
- [x] T1.34 [specs]: docs/parent-guide.md §7 per-child flip (2026-08-21)
- [x] T1.35 [specs]: 05_06_07_personas.md parent section resynced (2026-08-21)
- [x] T1.36 [specs]: 05_parent.md API table — 2 missing live contracts (2026-08-21)
- [x] T1.37 [specs]: current/schema.md V42/V43/V44 + new schema objects (2026-08-21)
- [x] **G1.6: Specs stop contradicting the shipped rule** — integration test — PASSED 2026-08-27 —
      specs read-through (no CI covers this one). Every "all/every linked child" hit across
      `target/`, `vision/`, `docs/` and `current/` is either platform content (correctly "all
      students") or an explicit contrast against pre-Phase-8 behaviour (`01_data_model.md:165`,
      `:250`). The two-term rule reads consistently in `01_data_model.md`, `02_auth_and_roles.md`
      (BR-SEC-004), `03_student.md` (BR-STU-001/002), `05_parent.md`, `05_06_07_personas.md`,
      `11_haitu_ai_layer.md`, `ui_parent_institution_admin.md` and `current/schema.md`.

- [x] **G1: Per-child Home Study binding** — E2E test — PASSED 2026-08-27 — bubbled: G1.1–G1.6 all
      pass, evidence on each subgoal line.

## G2 [frontend][backend]: Parent shell, child switcher, tab nav

### G2.1 — Grade reaches the client
- [x] T2.1 [backend]: grade on the children DTO (2026-08-21)
- [x] T2.2 [frontend]: Child model carries grade (depends on T2.1 [backend]) (2026-08-21)
- [x] **G2.1: Grade reaches the client** — integration test — PASSED 2026-08-27 — executed in CI
      against a live Postgres. `haisir-backend/Jenkinsfile:99-160` starts a
      `pgvector/pgvector:pg18` container, applies `alembic upgrade head` (V44 included) to it,
      then runs the full `tests/` suite with `INTEGRATION_DB_URL` set — so the formerly
      `INTEGRATION_DB_URL`-gated integration tests executed and gated the build
      (`--cov-fail-under=100`, `junit allowEmptyResults: false`). That green build shipped as
      v2026.8 to staging and prod 2026-08-25.

### G2.2 — Parent chrome
- [x] T2.3 [frontend]: ParentShell renders a parent header (modify, do not duplicate) (2026-08-21)
- [x] T2.4 [frontend]: + Link child in the topbar (depends on T2.3) (2026-08-21)
- [x] **G2.2: Parent chrome** — integration test (2026-08-21)

### G2.3 — Child and tab navigation
- [x] T2.5 [frontend]: ParentChildStrip (depends on T2.2) (2026-08-21)
- [x] T2.6 [frontend]: Active child shared across the surface (depends on T2.5) (2026-08-21)
- [x] T2.7 [frontend]: Curriculum | Results tab bar (depends on T2.6) (2026-08-21)
- [x] T2.8 [frontend]: Results coming-soon placeholder (depends on T2.7) (2026-08-21)
- [x] T2.9 [frontend]: Zero-children state hides the tabs (depends on T2.7) (2026-08-21)
- [x] **G2.3: Child and tab navigation** — integration test — PASSED 2026-08-27 — executed in CI.
      `haisir-frontend/Jenkinsfile:136-209` gates the build on both the vitest suite (`junit
      allowEmptyResults: false`) and Playwright E2E against staging. That green build shipped as
      v2026.8 to staging and prod 2026-08-25.

- [x] **G2: Parent shell, child switcher, tab nav** — E2E test — PASSED 2026-08-27 — bubbled:
      G2.1, G2.2, G2.3 all pass, evidence on each subgoal line.

## G3 [frontend][backend]: Curriculum tab shows only derivable numbers

### G3.1 — Server derives the card metrics
- [x] T3.1 [backend]: Root stats on GET /nodes (depends on T1.11) (2026-08-21)
- [x] **G3.1: Server derives the card metrics** — integration test — PASSED 2026-08-27 — executed
      in CI against a live Postgres. `haisir-backend/Jenkinsfile:99-160` starts a
      `pgvector/pgvector:pg18` container, applies `alembic upgrade head` (V44 included) to it,
      then runs the full `tests/` suite with `INTEGRATION_DB_URL` set — so the formerly
      `INTEGRATION_DB_URL`-gated integration tests executed and gated the build
      (`--cov-fail-under=100`, `junit allowEmptyResults: false`). That green build shipped as
      v2026.8 to staging and prod 2026-08-25. Includes the T3.1 fan-out regression case on
      `get_parent_root_stats`.

### G3.2 — The daily quota is actually daily
- [x] T3.2 [backend]: daily_window_start actually rolls ← **live bug: 100/day is a lifetime cap today** (2026-08-21)
- [x] T3.3 [backend]: GET /api/parent/curriculum/quota (depends on T3.2) (2026-08-21)
- [x] **G3.2: The daily quota is actually daily** — integration test — PASSED 2026-08-27 —
      executed in CI against a live Postgres. `haisir-backend/Jenkinsfile:99-160` starts a
      `pgvector/pgvector:pg18` container, applies `alembic upgrade head` (V44 included) to it,
      then runs the full `tests/` suite with `INTEGRATION_DB_URL` set — so the formerly
      `INTEGRATION_DB_URL`-gated integration tests executed and gated the build
      (`--cov-fail-under=100`, `junit allowEmptyResults: false`). That green build shipped as
      v2026.8 to staging and prod 2026-08-25. Covers the daily-window roll fix (T3.2) against a
      real upsert.

### G3.3 — The tab
- [x] T3.4 [frontend]: Module cards for the active child (depends on T2.6, T1.18 [backend], T3.1 [backend]) (2026-08-22)
- [x] T3.5 [frontend]: "About Home Study" explainer (depends on T3.4) (2026-08-22)
- [x] T3.6 [frontend]: "Start building" empty state (depends on T3.4) (2026-08-22)
- [x] T3.7 [frontend]: Quota line in the add-content modal (depends on T3.3 [backend]) (2026-08-22)
- [x] **G3.3: The tab** — integration test (2026-08-22) — subgoal test (vitest) behaviours covered at
      100%: switching the active child swaps the rendered cards (T3.4 `filterCurriculumRootsForChild`),
      a child with no bound root renders the "Start building" prompt (T3.6), no `progressbar` role and
      no "0" placeholder anywhere in the tab (T3.4 renders neither).

- [x] **G3: Curriculum tab shows only derivable numbers** — E2E test — PASSED 2026-08-27 —
      bubbled: G3.1, G3.2, G3.3 all pass, evidence on each subgoal line.

## G4 [frontend]: Builder — content inline, topic route retired

### G4.1 — Content renders in the topic card
- [x] T4.1 [frontend]: Mount TopicContentSection in the topic card (2026-08-21)
- [x] T4.2 [frontend]: Extraction group card shell (depends on T4.1) (2026-08-21)
- [x] T4.3 [frontend]: Show pages expander (depends on T4.2) (2026-08-21)
- [x] T4.4 [frontend]: Segmented Document | Text toggle (depends on T4.2) (2026-08-21)
- [x] **G4.1: Content renders in the topic card** — integration test — PASSED 2026-08-27 —
      executed in CI. `haisir-frontend/Jenkinsfile:136-209` gates the build on both the vitest
      suite (`junit allowEmptyResults: false`) and Playwright E2E against staging. That green
      build shipped as v2026.8 to staging and prod 2026-08-25.

### G4.2 — The old route and the dead link go
- [x] T4.6 [frontend]: Remove the dead Create Exam link (2026-08-21)
- [x] T4.5 [frontend]: Topic route redirects (depends on T4.1) (2026-08-21)
- [x] T4.7 [frontend]: Remove the Upload Content link (depends on T4.1) (2026-08-21)
- [x] **G4.2: The old route and the dead link go** — integration test — PASSED 2026-08-27 —
      executed in CI. `haisir-frontend/Jenkinsfile:136-209` gates the build on both the vitest
      suite (`junit allowEmptyResults: false`) and Playwright E2E against staging. That green
      build shipped as v2026.8 to staging and prod 2026-08-25.

- [x] **G4: Builder — content inline, topic route retired** — E2E test — PASSED 2026-08-27 —
      bubbled: G4.1, G4.2 both pass, evidence on each subgoal line.

---

- [ ] **ROOT: Home Study is per-child, and the parent surface matches the mock** — acceptance test
      (staging, two-child scenario (a)-(e) in PLAN.md)

## Ready now

- None ready — all 62 leaf tasks are done; ROOT acceptance test pending.
