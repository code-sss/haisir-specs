# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **specs-only** repo (`haisir-specs`) — no build system, no tests, no deployable code. It contains requirements documents and interactive HTML prototypes for the hAIsir edtech platform. The three sibling repos are:

- `haisir-frontend` — Next.js frontend (`../haisir-frontend`)
- `haisir-backend` — FastAPI backend (`../haisir-backend`)
- `haisir-deploy` — Docker Compose / infrastructure (`../haisir-deploy`)

## Implementation Planning

The `Implementation_planning/` directory contains the planning docs and a decisions log. Read these before starting any feature build:

| File | Purpose |
|---|---|
| `progress.md` | **Read this first** — current state, completed phases (high-level status document) |
| `PLAN.md` | Structured goal tree for the current phase — tasks with repo tags and dependencies (written by `/plan`) |
| `TASKS.md` | Task checkboxes + "Ready now" queue — updated by `/implement-backend`, `/implement-frontend`, `/implement-deploy` |
| `phases.md` | Rough phase guide — completed phases + next phase stub (long-term vision phasing is in `vision/phases.md`) |
| `decisions.md` | Running decisions log — one dated entry per `/plan` cycle, newest first |
| `constraints.md` | Implementation-reality constraints — facts on the ground (already coded, migrated or deployed) the target state must stay compatible with. Distinct from the Critical Rules below, which are policy. Update when `/update-target-state` surfaces a new constraint or a phase decision creates one |
| `archive/` | Historical decision records, archived plans/tasks, and superseded planning briefs — read for "why" behind past choices |

PLAN.md / TASKS.md line formats are defined once in `.claude/references/tasks-plan-contract.md`.

> The "why" behind spec choices is in `decisions.md` (recent) and `archive/phase0-review-decisions.md` / `archive/phase1-review-decisions.md` (historical).

## Read Order for Any Task

Specs are large: read them on demand (subagents read and summarise; never load all of them into the main session up front). When a task needs them, this is the order before generating code in any sibling repo:

1. `target/requirements/00_overview.md` — architecture, tech stack, design decisions
2. `target/requirements/01_data_model.md` — existing schema (extend, never drop/rename); read the relevant sections only
3. `target/requirements/02_auth_and_roles.md` — APISIX JWT injection, CSRF pattern, `X-Current-Role` header, permission matrix
4. `vision/requirements/11_role_migration.md` — **required before any auth/role work**
5. Target persona spec — `target/requirements/03_student.md` / `target/requirements/04_teacher_tutor.md` / `target/requirements/05_parent.md` / `target/requirements/06_institution_admin.md` / `target/requirements/07_platform_admin.md`
6. UI mapping (frontend only; colours, component states, screen IDs) — `target/requirements/ui-mapping/` where a file exists (`ui_student.md`, `ui_parent_institution_admin.md`), otherwise `vision/requirements/ui-mapping/`

UI mapping files reference prototype screen IDs (e.g. `s-home` → `renderHome()`). Use `target/prototypes/` first (admin, parent, student flows), then `vision/prototypes/` (host-only; not synced into containers).

> **Note:** `target/requirements/` stubs are filled incrementally via `/update-target-state`. Until a stub is filled, fall back to the corresponding `vision/requirements/` file.

## Critical Rules (must not be violated)

- **APISIX injects the JWT** — the client never sends a Bearer token. FastAPI receives it from the gateway.
- **Role header is `X-Current-Role`** — not `X-Active-Role`. Required on all role-gated endpoints; missing header → `400`. Exactly four lenient-path exceptions (`GET /api/users/me`, `POST /api/users/me/assign-role`, `PATCH /api/users/me/onboarding-complete`, `GET /images/questions/{filename}`); why: BR-SEC-006 in `target/requirements/02_auth_and_roles.md`.
- **CSRF on every request** — the frontend sends `X-CSRF-Token` on every request, GET included (`buildApiHeaders()` + `fetchWithCSRFRetry()`). Every mutation (`POST`, `PUT`, `PATCH`, `DELETE`) must validate it; GET routes validating it too is intentional.
- **No local users table** — identity is Keycloak `sub` as a raw UUID string. No FK constraints on user columns.
- **Existing schema is sacred** — `course_path_nodes`, `topics`, `exam_templates`, `exam_sessions` etc. already exist. Extend, never drop or rename. `assessments`, `assessment_attempts`, `assessment_answers` are deprecated — the unified model is `exam_templates` with `purpose = 'quiz' | 'exam'`.
- **`owner_type`** is the content ownership key — `platform` (platform admin content) or `parent` (parent-created private content) — on `course_path_nodes`, `topics`, and `exam_templates`.
- **No Redux, no Axios** — raw `fetch` with `credentials: 'include'` (via `fetchWithCSRFRetry()`). Server state uses TanStack Query v5 hooks; `useState`/`useEffect` only for local UI state (owner decision 2026-10-08; older `useEffect`-fetch hooks migrate when touched).
- **SQLAlchemy imperative mapping** — domain models are plain dataclasses. No `Base` subclassing in `domain/models/`.
- **Keycloak roles** — all six (`student`, `instructor`, `admin`, `institution_admin`, `tutor`, `parent`) are provisioned and validated by the backend; the assignment flows, role-switcher metadata and `/institution` + `/parent` guards are not built yet. Details: `Implementation_planning/constraints.md` ("auth — all six realm roles…"); remaining work follows `vision/requirements/11_role_migration.md`.
- **`admin` = SuperAdmin** — maps to the Platform Admin persona. No new `superadmin` role.
- **DDD folder structure** — no business logic in route files. See `vision/requirements/00_overview.md` section 6.
- **Never add `Co-Authored-By` trailers** — `attribution` is `""` in `.claude/settings.json`; the local `commit-msg` hook rejects them. Fresh clone: `ln -sf ../../scripts/check_no_coauthored.sh .git/hooks/commit-msg`.

## Spec Update Convention

Any PR in `haisir-frontend` or `haisir-backend` or `haisir-deploy` that adds/changes an API endpoint, screen/route, business rule, permission, database table/column, or role assignment **must** include a corresponding `haisir-specs` update (same PR or linked PR).

Product owner + lead developer must approve changes to business rules or API contracts. UI mapping and prototype changes can be approved by any developer. New target spec files live in `target/requirements/`; vision specs live in `vision/requirements/` — do not create new files at the repo root.

## Working in this repo (Claude)

- **Keep the main context lean.** The main session orchestrates; specs, PLAN/TASKS bodies and sibling repos are read by subagents from paths (never pasted) that return fixed-format results. Handoffs go through `.claude/plans/` (gitignored).
- **Compact output**: use the scripts, not prose lookups — `python3 .claude/skills/plan/scripts/plan_tool.py lint|ready|stats|drift`, `python3 .claude/skills/describe-current-state/scripts/snapshot.py`, `bash scripts/test_sync_specs.sh`; `jq empty <file>` to validate JSON.
- **Rules live once**: policy in Critical Rules above, facts on the ground in `Implementation_planning/constraints.md`, PLAN/TASKS format in `.claude/references/tasks-plan-contract.md`. Link them; don't copy.
- **Skills**: `/plan`, `/update-target-state`, `/describe-current-state`, `/sync-spec` — see the Skills table in `README.md`.
- **Container sync**: commit, then `./sync-specs.sh push [frontend|backend|all]`; bring container edits back with `/sync-spec <frontend|backend>`.
- **Models**: use `sonnet` only for mechanical bookkeeping agents (marking tasks, recomputing Ready now).
