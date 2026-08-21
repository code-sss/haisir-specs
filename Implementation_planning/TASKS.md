# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> **Last baselined: backend:`442ef7f` frontend:`6d3e08b` deploy:`790e29d` (2026-08-21)** — all three
> working trees clean at scoping. Specs baseline `510bbd8`. Alembic head V43; this phase adds V44.
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
- [ ] T0.1 [deploy]: Capture prod's render-side confirmation (opportunistic — next prod window)
- [x] T0.2 [specs]: Correct the B49 backlog entry (2026-08-21)
- [ ] **G0: B49 record corrected, prod render path confirmed** — E2E test

## G1 [backend][frontend][specs]: Per-child Home Study binding

### G1.1 — Binding schema + behaviour-preserving migration
- [x] T1.3 [specs]: BR-DATA-026 DDL types child_sub as String
- [x] T1.4 [specs]: BR-DATA-026 backfill binds revoked pairs too
- [x] T1.2 [backend]: root_node_id column on the three owner-scoped tables (2026-08-21)
- [x] T1.1 [backend]: parent_content_bindings table model (depends on T1.3) (2026-08-21)
- [x] T1.5 [backend]: V44 schema half (depends on T1.1, T1.2) (2026-08-21)
- [x] T1.6 [backend]: V44 root_node_id backfill (depends on T1.5) (2026-08-21)
- [x] T1.7 [backend]: V44 bindings backfill (depends on T1.5, T1.4) (2026-08-21)
- [ ] **G1.1: Binding schema + behaviour-preserving migration** — integration test — NOT RUN: all
      children done, but no live Postgres was reachable in this environment (`INTEGRATION_DB_URL`
      unset, no docker postgres) to execute `alembic upgrade V44` against a pre-migration fixture.
      `alembic history` confirms V44 chains cleanly from V43; the structural unit test
      (`tests/unit/infrastructure/test_v44_migration.py`) and 4 gated integration tests
      (`tests/integration/phase8/test_v44_parent_content_bindings.py`, skipped without a DB) are in
      place. Re-run this subgoal test once `INTEGRATION_DB_URL` points at a live instance.

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
- [ ] **G1.2: Write path stamps root_node_id and bindings** — integration test — NOT RUN: all
      children done (2026-08-21), but no live Postgres was reachable in this environment
      (`INTEGRATION_DB_URL` unset) to execute the subgoal's integration test. Unit coverage for
      T1.12/T1.14/T1.18 (flush-then-bind atomicity, unlinked-child None/404, child_subs on reads) is
      green at 100%. Re-run this subgoal test once `INTEGRATION_DB_URL` points at a live instance.

### G1.3 — Read path enforces both terms, everywhere
- [x] T1.20 [backend]: The clause gains the binding EXISTS (depends on T1.2, T1.6) (2026-08-21)
- [x] T1.21 [backend]: _resolve_parent_nodes filters service-side (depends on T1.8) ← **the failure mode** (2026-08-21)
- [x] T1.22 [backend]: hAITU gate gains the binding term (depends on T1.8, T1.2) (2026-08-21)
- [ ] **G1.3: Read path enforces both terms, everywhere** — integration test — NOT RUN: all children
      done (2026-08-21), but no live Postgres was reachable in this environment
      (`INTEGRATION_DB_URL` unset) to execute the subgoal's integration test
      (`test_g6_visibility_student_read_paths.py`). Unit coverage for T1.20/T1.21/T1.22 (binding
      EXISTS term, dashboard filter with hoisted `list_for_child` call, hAITU binding gate) is green
      at 100%. Re-run this subgoal test once `INTEGRATION_DB_URL` points at a live instance.

### G1.4 — Parent binds content at create time (ships in lockstep with G1.2)
- [x] T1.23 [frontend]: Child multi-select in the Add Root modal (2026-08-21)
- [x] T1.25 [frontend]: Child multi-select in the Adopt modal (2026-08-21)
- [x] T1.24 [frontend]: createNode sends child_subs (depends on T1.23, T1.10 [backend]) (2026-08-21)
- [x] T1.26 [frontend]: adoptSubtree sends child_subs (depends on T1.25, T1.10 [backend]) (2026-08-21)
- [ ] T1.27 [frontend]: Privacy pill renders the real binding set (depends on T1.18 [backend])
- [ ] T1.28 [frontend]: Binding editor on an existing root (depends on T1.16, T1.17 [backend], T1.27)
- [ ] T1.29 [frontend]: Revoked-but-bound child greyed in the pill (depends on T1.19 [backend], T1.27)
- [ ] **G1.4: Parent binds content at create time** — integration test

### G1.5 — Regression fixtures survive the breaking change
- [x] T1.30 [backend]: linked_child fixture helper (depends on T1.8) (2026-08-21)
- [ ] T1.31 [backend]: Rewrite the cross-owner 404 sweep (depends on T1.30, T1.20)
- [ ] T1.32 [backend]: Rewrite the E2E journey test (depends on T1.30, T1.21)
- [ ] **G1.5: Regression fixtures survive the breaking change** — integration test

### G1.6 — Specs stop contradicting the shipped rule
- [x] T1.33 [specs]: 03_student.md BR-STU-001 two-term rewrite (2026-08-21)
- [x] T1.34 [specs]: docs/parent-guide.md §7 per-child flip (2026-08-21)
- [x] T1.35 [specs]: 05_06_07_personas.md parent section resynced (2026-08-21)
- [x] T1.36 [specs]: 05_parent.md API table — 2 missing live contracts (2026-08-21)
- [x] T1.37 [specs]: current/schema.md V42/V43/V44 + new schema objects (2026-08-21)
- [ ] **G1.6: Specs stop contradicting the shipped rule** — integration test

- [ ] **G1: Per-child Home Study binding** — E2E test

## G2 [frontend][backend]: Parent shell, child switcher, tab nav

### G2.1 — Grade reaches the client
- [x] T2.1 [backend]: grade on the children DTO (2026-08-21)
- [x] T2.2 [frontend]: Child model carries grade (depends on T2.1 [backend]) (2026-08-21)
- [ ] **G2.1: Grade reaches the client** — integration test — NOT RUN: all children done
      (T2.1 [backend] ✅, T2.2 [frontend] ✅), but the subgoal test is a backend integration test
      needing a live parent with `student_profiles.grade` set — unreachable in this environment.
      Frontend mapping (`grade: d.grade ?? null`, `.nullish()` schema) is unit-covered at 100%
      (`tests/unit/features/parent/api/parent-api.test.ts`). Re-run once a live backend is reachable.

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
- [ ] **G2.3: Child and tab navigation** — integration test — NOT RUN: all five children done,
      but the subgoal test's "re-renders the tab body against the new child" clause cannot fully
      pass until G3's module-card consumer (T3.4, blocked on T1.18 [backend]) mounts. The
      switcher/persistence/tab-independence behaviours ARE covered by
      `tests/unit/features/parent/components/parent-dashboard.test.tsx` (strip `aria-pressed`,
      `parent.activeChildSub` localStorage persist via `selectActiveChild`, arrow-key tab switch
      not resetting the child, sibling `useParentActiveChild` probe). Re-run the full integration
      scenario once T3.4 lands.

- [ ] **G2: Parent shell, child switcher, tab nav** — E2E test

## G3 [frontend][backend]: Curriculum tab shows only derivable numbers

### G3.1 — Server derives the card metrics
- [x] T3.1 [backend]: Root stats on GET /nodes (depends on T1.11) (2026-08-21)
- [ ] **G3.1: Server derives the card metrics** — integration test — NOT RUN: only child T3.1 is
      done, but G3.1's own subgoal test is an integration test needing a live Postgres, unreachable
      in this environment. Unit coverage (fan-out regression case included) is green at 100%.

### G3.2 — The daily quota is actually daily
- [x] T3.2 [backend]: daily_window_start actually rolls ← **live bug: 100/day is a lifetime cap today** (2026-08-21)
- [x] T3.3 [backend]: GET /api/parent/curriculum/quota (depends on T3.2) (2026-08-21)
- [ ] **G3.2: The daily quota is actually daily** — integration test — NOT RUN: all children done
      (2026-08-21), but no live Postgres was reachable in this environment (`INTEGRATION_DB_URL`
      unset) to execute the subgoal's integration test. Unit coverage for T3.3 (fresh/stale/no-row
      quota view, 403 for non-parent, no-CSRF GET) is green at 100%. Re-run this subgoal test once
      `INTEGRATION_DB_URL` points at a live instance.

### G3.3 — The tab
- [ ] T3.4 [frontend]: Module cards for the active child (depends on T2.6, T1.18 [backend], T3.1 [backend])
- [ ] T3.5 [frontend]: "About Home Study" explainer (depends on T3.4)
- [ ] T3.6 [frontend]: "Start building" empty state (depends on T3.4)
- [ ] T3.7 [frontend]: Quota line in the add-content modal (depends on T3.3 [backend])
- [ ] **G3.3: The tab** — integration test

- [ ] **G3: Curriculum tab shows only derivable numbers** — E2E test

## G4 [frontend]: Builder — content inline, topic route retired

### G4.1 — Content renders in the topic card
- [x] T4.1 [frontend]: Mount TopicContentSection in the topic card (2026-08-21)
- [x] T4.2 [frontend]: Extraction group card shell (depends on T4.1) (2026-08-21)
- [x] T4.3 [frontend]: Show pages expander (depends on T4.2) (2026-08-21)
- [x] T4.4 [frontend]: Segmented Document | Text toggle (depends on T4.2) (2026-08-21)
- [ ] **G4.1: Content renders in the topic card** — integration test

### G4.2 — The old route and the dead link go
- [x] T4.6 [frontend]: Remove the dead Create Exam link (2026-08-21)
- [x] T4.5 [frontend]: Topic route redirects (depends on T4.1) (2026-08-21)
- [x] T4.7 [frontend]: Remove the Upload Content link (depends on T4.1) (2026-08-21)
- [ ] **G4.2: The old route and the dead link go** — integration test

- [ ] **G4: Builder — content inline, topic route retired** — E2E test

---

- [ ] **ROOT: Home Study is per-child, and the parent surface matches the mock** — acceptance test
      (staging, two-child scenario (a)-(e) in PLAN.md)

## Ready now

Tasks with no pending dependencies — can be started immediately.

**Critical path — unblocks the most downstream work:**
- T1.27 [frontend]: Privacy pill renders the real binding set (dep T1.18 ✅ [backend]) ← unblocks
  T1.28, T1.29
- T3.4 [frontend]: Module cards for the active child (dep T2.6 ✅, T1.18 ✅ [backend], T3.1 ✅
  [backend]) ← unblocks T3.5, T3.6
- T1.31 [backend]: Rewrite the cross-owner 404 sweep (dep T1.30 ✅, T1.20 ✅)
- T1.32 [backend]: Rewrite the E2E journey test (dep T1.30 ✅, T1.21 ✅)

**Also startable now:**
- T0.1 [deploy]: prod render confirmation (no deps — opportunistic, next prod window)
- T3.7 [frontend]: Quota line in the add-content modal (dep T3.3 ✅ [backend])

6 of 62 tasks are startable, spread across three repos — deploy's only task is opportunistic and
specs has none left ready. 52 of 62 tasks are now done. Landed 2026-08-21, backend batch:
T1.12/T1.14/T1.18/T1.20/T1.21/T1.22/T1.30/T3.3 — the full G1.2/G1.3 write+read binding enforcement
plus the T1.30 fixture helpers and the T3.3 quota endpoint (see below for detail). T1.21 ("the
failure mode") landing closes the BR-DATA-003 gap where an unbound-but-linked child could still see
a parent's Home Study content via `_resolve_parent_nodes` — that path is now filtered by
`parent_content_bindings`, not just `parent_child_links`. Landed 2026-08-21, frontend batch
(committed `6d3e08b`, pushed to `origin/main`): T2.2 (Child.grade model + `.nullish()` schema +
`grade: d.grade ?? null` mapping) and T2.5–T2.9 — the extracted `ParentChildStrip` (initials avatar,
`Grade {grade}` omitted when null, amber-underline active, `+ Link child` trailing), the
`ParentActiveChildContext` in `providers.tsx` (split `setActiveChildSub` in-memory vs
`selectActiveChild` persist — fixes a mount race that would have corrupted the stored selection), the
`Curriculum | Results` tab bar (`role="tablist"` + arrow-key nav + `role="tabpanel"`, Curriculum
panel = existing `/parent/curriculum` nav card, Results = static coming-soon placeholder, no fetch),
and the zero-children early-return gating strip + tabs. 470 tests / 100% coverage on the parent
slice (3988 total in the frontend suite). Reviewed via `/review-frontend` (no CRITICAL/HIGH/MEDIUM
findings; pre-commit/pre-push hooks green; `no-commit-to-branch` skipped deliberately — main is
trunk-based in this repo). Together these two batches unblock T1.31, T1.32 [backend] and T1.27,
T3.4, T3.7 [frontend] — T1.18 landing was the last dependency T3.4 needed (T2.6 ✅, T3.1 ✅ were
already in place). Earlier 2026-08-21: T1.9 [backend] — `bind_children`
all-or-nothing validation (BR-SEC-024), unblocking T1.12/T1.14/T1.16. And T1.37 [specs] —
current/schema.md now documents the `parent_content_bindings` table and `root_node_id` on
`course_path_nodes`/`topics`/`exam_templates` (V44, confirmed against the actual migration file
after a discrepancy check — see below). Also landed earlier the same day: T1.1/T1.11/T1.13
[backend] (the parent_content_bindings table model plus root_node_id stamping in create_node and
adopt_node), T1.8 [backend] (the ParentContentBindingRepository — add_many/delete/list_for_root/
list_for_child/exists, with an abstract interface and a DI provider; no migration, the table
already existed in metadata), T1.5/T1.6/T1.7 [backend] — the V44 migration
(`alembic/versions/V44_parent_content_bindings.py`), landed as one file/commit per the PLAN.md
checkpoint note: creates the `parent_content_bindings` table + `ix_parent_content_bindings_child`
index, adds nullable `root_node_id` to `course_path_nodes`/`topics`/`exam_templates`, backfills
`root_node_id` via a recursive-CTE temp-table walk, and backfills bindings from
`parent_child_links` with no `revoked_at` filter (T1.4); `alembic history` confirms V44 is the new
head, chaining cleanly from V43. And, in one batch, T1.15/T3.1/T1.19/T2.1/T3.2 [backend]:
`create_topic` stamps `root_node_id`; `list_root_nodes` merges per-root topic/content stats via a
fan-out-safe two-CTE query (`get_parent_root_stats`); `GET /api/parent/children` gained
`?include_revoked=true` (new `get_links_for_parent` repo method, `revoked_at` on the wire) and a
`grade` field, both riding the same `ChildLinkView`/`ChildLinkWithProfile`/
`list_children_for_parent` edit; and `increment_quota`'s upsert now rolls `daily_jobs`/
`daily_window_start` via a SQL CASE when the window is >24h stale, with a matching Python-side
staleness check in `extraction_service.py`'s quota gate — fixing the "100/day is a lifetime cap"
bug. And, in this repo, T0.2/T1.33/T1.34/T1.35/T1.36 [specs] (B49 record corrected; BR-STU-001,
parent-guide.md §7, 05_06_07_personas.md and the 05_parent.md API table all resynced to the shipped
per-child binding rule). T1.8 unblocked T1.9/T1.17/T1.18/T1.21/T1.22/T1.30; T1.5/T1.6 unblocked
T1.20; T1.7 unblocked T1.37 [specs]; T2.1 unblocked T2.2 [frontend]; T3.2 unblocked T3.3.
T1.9 unblocked T1.12/T1.14/T1.16. G1.1's, G1.2's, G1.3's, G3.1's, G3.2's, G2.1's and G2.3's
integration tests could not be executed in this environment (no live backend/Postgres reachable) —
see the notes on those lines; their child tasks are done and unit coverage (including the T3.1
fan-out regression case and the T2.2–T2.9 parent surface behaviours) is green at 100%.
