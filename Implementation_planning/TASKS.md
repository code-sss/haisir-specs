# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> **Last baselined: backend:`67b6cc3` frontend:`784f700` deploy:`790e29d` (2026-08-20)** — all three
> working trees clean at scoping. Specs baseline `510bbd8`. Alembic head V43; this phase adds V44.
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
- [ ] T0.2 [specs]: Correct the B49 backlog entry
- [ ] **G0: B49 record corrected, prod render path confirmed** — E2E test

## G1 [backend][frontend][specs]: Per-child Home Study binding

### G1.1 — Binding schema + behaviour-preserving migration
- [x] T1.3 [specs]: BR-DATA-026 DDL types child_sub as String
- [x] T1.4 [specs]: BR-DATA-026 backfill binds revoked pairs too
- [ ] T1.2 [backend]: root_node_id column on the three owner-scoped tables
- [ ] T1.1 [backend]: parent_content_bindings table model (depends on T1.3)
- [ ] T1.5 [backend]: V44 schema half (depends on T1.1, T1.2)
- [ ] T1.6 [backend]: V44 root_node_id backfill (depends on T1.5)
- [ ] T1.7 [backend]: V44 bindings backfill (depends on T1.5, T1.4)
- [ ] **G1.1: Binding schema + behaviour-preserving migration** — integration test

### G1.2 — Write path stamps root_node_id and bindings
- [ ] T1.10 [backend]: child_subs on the two create payloads
- [ ] T1.19 [backend]: GET /api/parent/children?include_revoked=true
- [ ] T1.8 [backend]: ParentContentBindingRepository (depends on T1.1)
- [ ] T1.9 [backend]: Bind-time validation is all-or-nothing (depends on T1.8)
- [ ] T1.11 [backend]: create_node stamps root_node_id (depends on T1.2)
- [ ] T1.13 [backend]: adopt_node stamps root_node_id on every clone (depends on T1.2)
- [ ] T1.12 [backend]: create_node binds the named children (depends on T1.9, T1.11, T1.10)
- [ ] T1.14 [backend]: adopt_node binds the named children (depends on T1.9, T1.13, T1.10)
- [ ] T1.15 [backend]: Parent topic create stamps root_node_id (depends on T1.11)
- [ ] T1.16 [backend]: POST /nodes/{root_id}/bindings (depends on T1.9)
- [ ] T1.17 [backend]: DELETE /nodes/{root_id}/bindings/{child_sub} (depends on T1.8)
- [ ] T1.18 [backend]: child_subs on parent root reads (depends on T1.8)
- [ ] **G1.2: Write path stamps root_node_id and bindings** — integration test

### G1.3 — Read path enforces both terms, everywhere
- [ ] T1.20 [backend]: The clause gains the binding EXISTS (depends on T1.2, T1.6)
- [ ] T1.21 [backend]: _resolve_parent_nodes filters service-side (depends on T1.8) ← **the failure mode**
- [ ] T1.22 [backend]: hAITU gate gains the binding term (depends on T1.8, T1.2)
- [ ] **G1.3: Read path enforces both terms, everywhere** — integration test

### G1.4 — Parent binds content at create time (ships in lockstep with G1.2)
- [x] T1.23 [frontend]: Child multi-select in the Add Root modal (2026-08-21)
- [x] T1.25 [frontend]: Child multi-select in the Adopt modal (2026-08-21)
- [ ] T1.24 [frontend]: createNode sends child_subs (depends on T1.23, T1.10 [backend])
- [ ] T1.26 [frontend]: adoptSubtree sends child_subs (depends on T1.25, T1.10 [backend])
- [ ] T1.27 [frontend]: Privacy pill renders the real binding set (depends on T1.18 [backend])
- [ ] T1.28 [frontend]: Binding editor on an existing root (depends on T1.16, T1.17 [backend], T1.27)
- [ ] T1.29 [frontend]: Revoked-but-bound child greyed in the pill (depends on T1.19 [backend], T1.27)
- [ ] **G1.4: Parent binds content at create time** — integration test

### G1.5 — Regression fixtures survive the breaking change
- [ ] T1.30 [backend]: linked_child fixture helper (depends on T1.8)
- [ ] T1.31 [backend]: Rewrite the cross-owner 404 sweep (depends on T1.30, T1.20)
- [ ] T1.32 [backend]: Rewrite the E2E journey test (depends on T1.30, T1.21)
- [ ] **G1.5: Regression fixtures survive the breaking change** — integration test

### G1.6 — Specs stop contradicting the shipped rule
- [ ] T1.33 [specs]: 03_student.md BR-STU-001 two-term rewrite
- [ ] T1.34 [specs]: docs/parent-guide.md §7 per-child flip
- [ ] T1.35 [specs]: 05_06_07_personas.md parent section resynced
- [ ] T1.36 [specs]: 05_parent.md API table — 2 missing live contracts
- [ ] T1.37 [specs]: current/schema.md V42/V43/V44 + new schema objects (depends on T1.7 [backend])
- [ ] **G1.6: Specs stop contradicting the shipped rule** — integration test

- [ ] **G1: Per-child Home Study binding** — E2E test

## G2 [frontend][backend]: Parent shell, child switcher, tab nav

### G2.1 — Grade reaches the client
- [ ] T2.1 [backend]: grade on the children DTO
- [ ] T2.2 [frontend]: Child model carries grade (depends on T2.1 [backend])
- [ ] **G2.1: Grade reaches the client** — integration test

### G2.2 — Parent chrome
- [x] T2.3 [frontend]: ParentShell renders a parent header (modify, do not duplicate) (2026-08-21)
- [x] T2.4 [frontend]: + Link child in the topbar (depends on T2.3) (2026-08-21)
- [x] **G2.2: Parent chrome** — integration test (2026-08-21)

### G2.3 — Child and tab navigation
- [ ] T2.5 [frontend]: ParentChildStrip (depends on T2.2)
- [ ] T2.6 [frontend]: Active child shared across the surface (depends on T2.5)
- [ ] T2.7 [frontend]: Curriculum | Results tab bar (depends on T2.6)
- [ ] T2.8 [frontend]: Results coming-soon placeholder (depends on T2.7)
- [ ] T2.9 [frontend]: Zero-children state hides the tabs (depends on T2.7)
- [ ] **G2.3: Child and tab navigation** — integration test

- [ ] **G2: Parent shell, child switcher, tab nav** — E2E test

## G3 [frontend][backend]: Curriculum tab shows only derivable numbers

### G3.1 — Server derives the card metrics
- [ ] T3.1 [backend]: Root stats on GET /nodes (depends on T1.11)
- [ ] **G3.1: Server derives the card metrics** — integration test

### G3.2 — The daily quota is actually daily
- [ ] T3.2 [backend]: daily_window_start actually rolls ← **live bug: 100/day is a lifetime cap today**
- [ ] T3.3 [backend]: GET /api/parent/curriculum/quota (depends on T3.2)
- [ ] **G3.2: The daily quota is actually daily** — integration test

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
- [ ] T4.3 [frontend]: Show pages expander (depends on T4.2)
- [ ] T4.4 [frontend]: Segmented Document | Text toggle (depends on T4.2)
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

**Critical path — all of G1 hangs off these three:**
- T1.3 [specs]: BR-DATA-026 DDL child_sub → String (no deps) — unblocks T1.1 and the whole G1.1 chain
- T1.2 [backend]: root_node_id columns (no deps)
- T1.10 [backend]: child_subs on the two create payloads (no deps) — carries the ~32-function test update

**Also startable now:**
- T0.1 [deploy]: prod render confirmation (no deps — opportunistic, next prod window)
- T0.2 [specs]: correct the B49 entry (no deps)
- T1.4 [specs]: backfill includes revoked pairs (no deps) — unblocks T1.7
- T1.33 [specs]: 03_student.md BR-STU-001 (no deps)
- T1.34 [specs]: docs/parent-guide.md §7 (no deps)
- T1.35 [specs]: 05_06_07_personas.md resync (no deps)
- T1.36 [specs]: 05_parent.md API table (no deps)
- T1.19 [backend]: ?include_revoked=true (no deps)
- T2.1 [backend]: grade on the children DTO (no deps)
- T3.2 [backend]: daily quota window roll (no deps)
- T4.3 [frontend]: Show pages expander (dep T4.2 done 2026-08-21) — newly ready
- T4.4 [frontend]: Segmented Document | Text toggle (dep T4.2 done 2026-08-21) — newly ready

15 of 62 tasks are startable, spread across all four repos — no repo is blocked waiting on another to
begin. T1.23/T1.25/T2.3/T4.1/T4.6/T2.4/T4.2/T4.5/T4.7 [frontend] landed 2026-08-21; T1.24/T1.26 stay
blocked on T1.10 [backend]. G2.2 closed (parent chrome done); G4.2's leaf tasks are done but its goal
test is E2E (Playwright), not runnable in the unit suite.
