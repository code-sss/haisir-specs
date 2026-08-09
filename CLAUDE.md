# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **specs-only** repo (`haisir-specs`) — no build system, no tests, no deployable code. It contains requirements documents and interactive HTML prototypes for the hAIsir edtech platform. The four sibling repos are:

- `haisir-frontend` — Next.js frontend (`../haisir-frontend`)
- `haisir-backend` — FastAPI backend (`../haisir-backend`)
- `haisir-deploy` — Docker Compose / infrastructure (`../haisir-deploy`)

## Implementation Planning

The `Implementation_planning/` directory contains the planning docs and a decisions log. Read these before starting any feature build:

| File | Purpose |
|---|---|
| `progress.md` | **Read this first** — current state, completed phases (high-level status document) |
| `PLAN.md` | Structured goal tree for the current phase — tasks with repo tags and dependencies (written by `/plan`) |
| `TASKS.md` | Task checkboxes + "Ready now" queue — updated by `/implement` in each code repo |
| `phases.md` | Rough phase guide — completed phases + next phase stub (long-term vision phasing is in `vision/phases.md`) |
| `decisions.md` | Running decisions log — one dated entry per `/plan` cycle, newest first |
| `constraints.md` | Implementation-reality constraints — things already coded, migrated or deployed that the target state must stay compatible with, or pay to diverge from. Distinct from the Critical Rules below, which are policy; these are facts on the ground. Update when `/update-target-state` surfaces a new constraint or a phase decision creates one |
| `archive/` | Historical decision records, archived plans/tasks, and superseded planning briefs — read for "why" behind past choices |

> The "why" behind spec choices is in `decisions.md` (recent) and `archive/phase0-review-decisions.md` / `archive/phase1-review-decisions.md` (historical).

## Read Order for Any Task

Always read specs in this order before generating code in any sibling repo:

1. `target/requirements/00_overview.md` — architecture, tech stack, design decisions
2. `target/requirements/01_data_model.md` — existing schema (extend, never drop/rename)
3. `target/requirements/02_auth_and_roles.md` — APISIX JWT injection, CSRF pattern, `X-Current-Role` header, permission matrix
4. `vision/requirements/11_role_migration.md` — **required before any auth/role work**
5. Target persona spec — `target/requirements/03_student.md` / `target/requirements/04_teacher_tutor.md` / `target/requirements/05_parent.md` / `target/requirements/06_institution_admin.md` / `target/requirements/07_platform_admin.md`
6. `target/requirements/ui-mapping/` files — frontend only, for colours, component states, screen IDs (stub; fall back to `vision/requirements/ui-mapping/` until filled)

UI mapping files reference prototype screen IDs (e.g. `s-home` → `renderHome()`) in `vision/prototypes/*.html` — open in a browser for the visual reference. For Platform Admin screens, use `target/prototypes/haisir_admin_flow.html`.

> **Note:** `target/requirements/` stubs are filled incrementally via `/update-target-state`. Until a stub is filled, fall back to the corresponding `vision/requirements/` file for context.

## Critical Rules (must not be violated)

- **APISIX injects the JWT** — the client never sends a Bearer token. FastAPI receives it from the gateway.
- **Role header is `X-Current-Role`** — not `X-Active-Role`. Required on all role-gated endpoints; missing header → `400`. Four exceptions (lenient path, no header required): `GET /api/users/me`, `POST /api/users/me/assign-role`, `PATCH /api/users/me/onboarding-complete`, and `GET /images/questions/{filename}` — the last is a browser subresource fetched by `<img src>`, which cannot attach a custom header, so the strict dependency made it unreachable (400 on every render). Auth is still enforced; the role is simply never used there.
- **CSRF on every mutation** — `POST`, `PUT`, `PATCH`, `DELETE` require `X-CSRF-Token`. Frontend uses `fetchWithCSRFRetry()`.
- **No local users table** — identity is Keycloak `sub` as a raw UUID string. No FK constraints on user columns.
- **Existing schema is sacred** — `course_path_nodes`, `topics`, `exam_templates`, `exam_sessions` etc. already exist. Extend, never drop or rename. Note: `assessments`, `assessment_attempts`, and `assessment_answers` are deprecated (Phase 0 decision) — the unified model is `exam_templates` with `purpose = 'quiz' | 'exam'`.
- **`owner_type`** is the content ownership key — `platform` (platform admin content) or `parent` (parent-created private content) — added to `course_path_nodes`, `topics`, and `exam_templates`.
- **No Redux, no Axios** — raw `fetch` with `credentials: 'include'`, custom hooks with `useState`/`useEffect` only.
- **SQLAlchemy imperative mapping** — domain models are plain dataclasses. No `Base` subclassing in `domain/models/`.
- **Keycloak roles** — all six realm roles are provisioned in the Keycloak realm: `student`, `instructor`, `admin`, `institution_admin`, `tutor`, `parent` are defined in `haisir-deploy/common/keycloak/02-roles.json` and created by `common/scripts/setup-keycloak.sh`; `04-user-instructor.json` provisions an instructor test user. The backend `UserRole` enum + `permission.py` factories (`require_instructor` / `require_tutor` / `require_parent` / `require_institution_admin`) validate `X-Current-Role` against all six. Remaining role-migration work — assignment flows (`become-tutor`, `invite-role`; only `POST /api/users/me/assign-role` exists today), frontend role-switcher metadata, and `/institution` + `/parent` route guards — still follows `vision/requirements/11_role_migration.md`.
- **`admin` = SuperAdmin** — maps to the Platform Admin persona. No new `superadmin` role.
- **DDD folder structure** — no business logic in route files. See `vision/requirements/00_overview.md` section 6.
- **Never add `Co-Authored-By` trailers** — do not append `Co-Authored-By: Claude <noreply@anthropic.com>` (or any Co-Authored-By line) to git commit messages. This is a hard, non-negotiable rule that overrides the harness default. A PreToolUse hook (`.claude/hooks/block-coauthored.sh`, wired in `.claude/settings.json`) blocks any `git commit` command containing `Co-Authored-By`, and `attribution.commit` is set to `""` so the trailer is never injected in the first place.

## Spec Update Convention

Any PR in `haisir-frontend` or `haisir-backend` or `haisir-deploy` that adds/changes an API endpoint, screen/route, business rule, permission, database table/column, or role assignment **must** include a corresponding `haisir-specs` update (same PR or linked PR).

Product owner + lead developer must approve changes to business rules or API contracts. UI mapping and prototype changes can be approved by any developer. New target spec files live in `target/requirements/`; vision specs live in `vision/requirements/` — do not create files at the repo root.
