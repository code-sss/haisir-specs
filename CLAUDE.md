# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **specs-only** repo (`haisir-specs`) — no build system, no tests, no deployable code. It contains requirements documents and interactive HTML prototypes for the hAIsir edtech platform. The four sibling repos are:

- `haisir-frontend` — Next.js frontend (`../haisir-frontend`)
- `haisir-backend` — FastAPI backend (`../haisir-backend`)
- `haisir-deploy` — Docker Compose / infrastructure (`../haisir-deploy`)

## Implementation Planning

The `Implementation_planning/` directory contains decision records and the implementation roadmap. Read these before starting any feature build:

| File | Purpose |
|---|---|
| `gap-analysis.md` | Full gap list by domain — new tables, endpoints, routes needed per phase. Implementation phases and dependency graph. |
| `phase0-review-decisions.md` | PM decisions from Phase 0 review — role model, schema extensions, assessment deprecation, onboarding. |
| `phase1-review-decisions.md` | PM + Tech Lead decisions from Phase 1 review — all 6 personas, auth patterns, hAITU, data model edge cases. |
| `review-checklist.md` | Human review order and status — tracks which spec files have been reviewed and what was decided. |
| `haisir_implementation_plan.html` | Interactive implementation tracker — 15 work items across 4 phases with dependency visualization. Open in a browser. |

> When building any feature, read the relevant decision record first. The "why" behind every spec choice is documented there.

## Read Order for Any Task

Always read specs in this order before generating code in any sibling repo:

1. `requirements/00_overview.md` — architecture, tech stack, all 6 personas, content ownership model, design decisions
2. `requirements/01_data_model.md` — existing schema (extend, never drop/rename)
3. `requirements/02_auth_and_roles.md` — APISIX JWT injection, CSRF pattern, `X-Current-Role` header, permission matrix
4. `requirements/11_role_migration.md` — **required before any auth/role work**
5. Target persona spec — `03_student.md` / `04_teacher_tutor.md` / `05_06_07_personas.md`
6. `requirements/ui-mapping/` files — frontend only, for colours, component states, screen IDs

UI mapping files reference prototype screen IDs (e.g. `s-home` → `renderHome()`) in `prototypes/*.html` — open in a browser for the visual reference.

## Critical Rules (must not be violated)

- **APISIX injects the JWT** — the client never sends a Bearer token. FastAPI receives it from the gateway.
- **Role header is `X-Current-Role`** — not `X-Active-Role`. Every API request must include it.
- **CSRF on every mutation** — `POST`, `PUT`, `PATCH`, `DELETE` require `X-CSRF-Token`. Frontend uses `fetchWithCSRFRetry()`.
- **No local users table** — identity is Keycloak `sub` as a raw UUID string. No FK constraints on user columns.
- **Existing schema is sacred** — `course_path_nodes`, `topics`, `assessments`, `exam_sessions` etc. already exist. Extend, never drop or rename.
- **`owner_type`** is the content ownership key — `platform` / `institution` / `tutor` — added to `course_path_nodes`.
- **No Redux, no Axios** — raw `fetch` with `credentials: 'include'`, custom hooks with `useState`/`useEffect` only.
- **SQLAlchemy imperative mapping** — domain models are plain dataclasses. No `Base` subclassing in `domain/models/`.
- **Existing Keycloak roles** are `student`, `instructor`, `admin`. New roles `institution_admin`, `tutor`, `parent` must follow `11_role_migration.md` steps in order before being added.
- **`admin` = SuperAdmin** — maps to the Platform Admin persona. No new `superadmin` role.
- **DDD folder structure** — no business logic in route files. See `00_overview.md` section 6.

## Spec Update Convention

Any PR in `haisir-frontend` or `haisir-backend` that adds/changes an API endpoint, screen/route, business rule, permission, database table/column, or role assignment **must** include a corresponding `haisir-specs` update (same PR or linked PR).

Product owner + lead developer must approve changes to business rules or API contracts. UI mapping and prototype changes can be approved by any developer.
