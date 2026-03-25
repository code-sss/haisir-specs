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
| `progress.md` | **Read this first** — current state, next phase (updated each plan-next-state cycle) |
| `phases.md` | Rough phase guide — P0–P3 items and dependency graph (updated only when phase scope changes) |
| `decisions.md` | Running decisions log — one dated entry per plan-next-state cycle, newest first |
| `archive/` | Historical decision records — read for "why" behind past choices |

> The "why" behind spec choices is in `decisions.md` (recent) and `archive/phase0-review-decisions.md` / `archive/phase1-review-decisions.md` (historical).

## Read Order for Any Task

Always read specs in this order before generating code in any sibling repo:

1. `target/requirements/00_overview.md` — architecture, tech stack, all 6 personas, content ownership model, design decisions
2. `target/requirements/01_data_model.md` — existing schema (extend, never drop/rename)
3. `target/requirements/02_auth_and_roles.md` — APISIX JWT injection, CSRF pattern, `X-Current-Role` header, permission matrix
4. `target/requirements/11_role_migration.md` — **required before any auth/role work**
5. Target persona spec — `target/requirements/03_student.md` / `target/requirements/04_teacher_tutor.md` / `target/requirements/05_06_07_personas.md`
6. `target/requirements/ui-mapping/` files — frontend only, for colours, component states, screen IDs

UI mapping files reference prototype screen IDs (e.g. `s-home` → `renderHome()`) in `target/prototypes/*.html` — open in a browser for the visual reference.

## Critical Rules (must not be violated)

- **APISIX injects the JWT** — the client never sends a Bearer token. FastAPI receives it from the gateway.
- **Role header is `X-Current-Role`** — not `X-Active-Role`. Every API request must include it.
- **CSRF on every mutation** — `POST`, `PUT`, `PATCH`, `DELETE` require `X-CSRF-Token`. Frontend uses `fetchWithCSRFRetry()`.
- **No local users table** — identity is Keycloak `sub` as a raw UUID string. No FK constraints on user columns.
- **Existing schema is sacred** — `course_path_nodes`, `topics`, `exam_templates`, `exam_sessions` etc. already exist. Extend, never drop or rename. Note: `assessments`, `assessment_attempts`, and `assessment_answers` are deprecated (Phase 0 decision) — the unified model is `exam_templates` with `purpose = 'quiz' | 'exam'`.
- **`owner_type`** is the content ownership key — `platform` / `institution` / `tutor` — added to `course_path_nodes`.
- **No Redux, no Axios** — raw `fetch` with `credentials: 'include'`, custom hooks with `useState`/`useEffect` only.
- **SQLAlchemy imperative mapping** — domain models are plain dataclasses. No `Base` subclassing in `domain/models/`.
- **Keycloak roles** — `student`, `instructor`, `admin` are active in the current Keycloak realm. `institution_admin`, `tutor`, `parent` are implemented in the backend (`UserRole` enum + `permission.py`) but not yet added to the Keycloak realm — follow `target/requirements/11_role_migration.md` steps before enabling them.
- **`admin` = SuperAdmin** — maps to the Platform Admin persona. No new `superadmin` role.
- **DDD folder structure** — no business logic in route files. See `target/requirements/00_overview.md` section 6.

## Spec Update Convention

Any PR in `haisir-frontend` or `haisir-backend` or `haisir-deploy` that adds/changes an API endpoint, screen/route, business rule, permission, database table/column, or role assignment **must** include a corresponding `haisir-specs` update (same PR or linked PR).

Product owner + lead developer must approve changes to business rules or API contracts. UI mapping and prototype changes can be approved by any developer. Spec files live in `target/requirements/` — do not create files at the repo root.
