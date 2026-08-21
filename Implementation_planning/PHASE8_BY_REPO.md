# Phase 8 — Goal tree by repo (temp — delete at phase close)

> Reorganized from `PLAN.md`/`TASKS.md` (goal-wise) into repo-wise execution order. Source of truth
> stays `PLAN.md`; this file is just "what do I run next in repo X."
> Checkboxes are independent trackers — tick here AND in `TASKS.md`.

**Start-here, 3 tasks unlock most of G1**: `T1.3` [specs] → `T1.2` [backend] → `T1.10` [backend].

---

## backend (`haisir-backend`)

Order = dependency order. `←` marks what still blocks a task.

### G1.1 — schema + migration
- [ ] T1.2 — root_node_id column on 3 tables — *no deps*
- [ ] T1.1 — parent_content_bindings table model — ← T1.3 [specs]
- [ ] T1.5 — V44 schema half — ← T1.1, T1.2
- [ ] T1.6 — V44 root_node_id backfill — ← T1.5
- [ ] T1.7 — V44 bindings backfill — ← T1.5, T1.4 [specs]

### G1.2 — write path
- [ ] T1.10 — child_subs on create/adopt payloads (large, ~32 tests) — *no deps*
- [ ] T1.19 — GET /parent/children?include_revoked=true — *no deps*
- [ ] T1.8 — ParentContentBindingRepository — ← T1.1
- [ ] T1.9 — bind_children all-or-nothing validation — ← T1.8
- [ ] T1.11 — create_node stamps root_node_id — ← T1.2
- [ ] T1.13 — adopt_node stamps root_node_id — ← T1.2
- [ ] T1.12 — create_node binds named children — ← T1.9, T1.11, T1.10
- [ ] T1.14 — adopt_node binds named children — ← T1.9, T1.13, T1.10
- [ ] T1.15 — parent topic create stamps root_node_id — ← T1.11
- [ ] T1.16 — POST /nodes/{root}/bindings — ← T1.9
- [ ] T1.17 — DELETE /nodes/{root}/bindings/{child_sub} — ← T1.8
- [ ] T1.18 — child_subs on parent root reads — ← T1.8

### G1.3 — read-path enforcement
- [ ] T1.20 — visibility clause gains binding EXISTS — ← T1.2, T1.6
- [ ] T1.21 — **_resolve_parent_nodes filters service-side** ← T1.8 — *the failure-mode task, don't skip*
- [ ] T1.22 — hAITU gate gains binding term — ← T1.8, T1.2

### G1.5 — regression fixtures
- [ ] T1.30 — linked_child / bound_root fixture helper — ← T1.8
- [ ] T1.31 — rewrite cross-owner 404 sweep — ← T1.30, T1.20
- [ ] T1.32 — rewrite E2E journey test — ← T1.30, T1.21

### G2.1 — grade
- [ ] T2.1 — grade on children DTO — *no deps*

### G3.1 / G3.2 — metrics + quota
- [ ] T3.1 — root stats on GET /nodes — ← T1.11
- [ ] T3.2 — **daily_window_start actually rolls** — *no deps — live bug, fix regardless of UI order*
- [ ] T3.3 — GET /parent/curriculum/quota — ← T3.2

**Backend-only ready-now**: T1.2, T1.10, T1.19, T2.1, T3.2

---

## frontend (`haisir-frontend`)

> G1.4 ships in lockstep with backend G1.2 — `child_subs` is a hard 400, no fallback. Don't merge
> T1.24/T1.26 ahead of backend T1.10 landing.

### G1.4 — bind content at create time
- [ ] T1.23 — child multi-select, Add Root modal — *no deps*
- [ ] T1.25 — child multi-select, Adopt modal — *no deps*
- [ ] T1.24 — createNode sends child_subs — ← T1.23, T1.10 [backend]
- [ ] T1.26 — adoptSubtree sends child_subs — ← T1.25, T1.10 [backend]
- [ ] T1.27 — privacy pill renders real binding set — ← T1.18 [backend]
- [ ] T1.28 — binding editor on existing root — ← T1.16, T1.17 [backend], T1.27
- [ ] T1.29 — revoked-but-bound child greyed in pill — ← T1.19 [backend], T1.27

### G2.1 — grade
- [ ] T2.2 — child model carries grade — ← T2.1 [backend]

### G2.2 — parent chrome
- [ ] T2.3 — ParentShell renders parent header (modify, don't duplicate) — *no deps*
- [ ] T2.4 — + Link child in topbar — ← T2.3

### G2.3 — child + tab nav
- [ ] T2.5 — ParentChildStrip — ← T2.2
- [ ] T2.6 — active child shared via context — ← T2.5
- [ ] T2.7 — Curriculum | Results tab bar — ← T2.6
- [ ] T2.8 — Results coming-soon placeholder — ← T2.7
- [ ] T2.9 — zero-children state hides tabs — ← T2.7

### G3.3 — the tab
- [ ] T3.4 — module cards for active child — ← T2.6, T1.18 [backend], T3.1 [backend]
- [ ] T3.5 — "About Home Study" explainer — ← T3.4
- [ ] T3.6 — "Start building" empty state — ← T3.4
- [ ] T3.7 — quota line in add-content modal — ← T3.3 [backend]

### G4.1 — content inline
- [ ] T4.1 — mount TopicContentSection in topic card — *no deps*
- [ ] T4.2 — extraction group card shell — ← T4.1
- [ ] T4.3 — Show pages expander — ← T4.2
- [ ] T4.4 — Document | Text segmented toggle — ← T4.2

### G4.2 — old route + dead links
- [ ] T4.6 — remove dead Create Exam link — *no deps*
- [ ] T4.5 — topic route redirects — ← T4.1
- [ ] T4.7 — remove Upload Content link — ← T4.1

**Frontend-only ready-now**: T1.23, T1.25, T2.3, T4.1, T4.6

---

## specs (`haisir-specs`, this repo)

- [x] T1.3 — BR-DATA-026 DDL: child_sub → String — *no deps — unblocks backend T1.1*
- [x] T1.4 — BR-DATA-026 backfill binds revoked pairs too — *no deps — unblocks backend T1.7*
- [ ] T0.2 — correct B49 backlog entry — *no deps*
- [ ] T1.33 — 03_student.md BR-STU-001 two-term rewrite — *no deps*
- [ ] T1.34 — parent-guide.md §7 per-child flip — *no deps*
- [ ] T1.35 — 05_06_07_personas.md parent section resync — *no deps*
- [ ] T1.36 — 05_parent.md API table (2 missing contracts) — *no deps*
- [ ] T1.37 — current/schema.md → V44 — ← T1.7 [backend]

**Specs-only ready-now**: T1.3, T1.4, T0.2, T1.33, T1.34, T1.35, T1.36 — all 7, do these first, they unblock nothing on each other and T1.3 unblocks the whole G1.1 backend chain.

---

## deploy (`haisir-deploy`)

- [ ] T0.1 — capture prod render-side confirmation — *no deps, opportunistic — next prod deploy.sh window, not blocking Phase 8*

No APISIX routes needed this phase (new endpoints ride existing generic `/api/*` routes).

---

## Cross-repo release coupling (not a dependency, a deploy-timing constraint)

**G1.2 [backend] + G1.4 [frontend] must ship in the same release window.** `child_subs` is a breaking
400 with no fallback — an un-updated frontend 400s on every root create and every adopt.

V44 is a migrating deploy: stop the worker first, take the pre-deploy dump + datadir tarball before
running it.

---

## Suggested order across repos

1. **specs**: T1.3, T1.4 (unblock backend) + the four no-dep doc fixes (T1.33-36) + T0.2 — all in one sitting.
2. **backend**: T1.2, T1.10 in parallel with the specs work, then the G1.1 migration chain (T1.1→T1.5→T1.6→T1.7), then G1.2 write path, then G1.3 (T1.21 is the one that matters most), then G1.5 fixtures.
3. **frontend**: T1.23/T1.25/T2.3/T4.1/T4.6 can start immediately; hold T1.24/T1.26 until backend T1.10 is merged; the rest of G1.4/G2/G3/G4 follows its own chain.
4. **deploy**: T0.1 whenever the next prod window happens — don't wait on it.
