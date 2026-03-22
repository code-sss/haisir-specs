# hAIsir — Requirements & UI Specification
> **Repo:** `haisir-specs` | Read this file first. It tells you exactly which files to open for your role.

---

## Repository Context

This is the `haisir-specs` repository — one of four hAIsir repos:

| Repo | Purpose |
|---|---|
| `haisir-specs` | **This repo.** Requirements, UI specs, prototypes. |
| `haisir-frontend` | Next.js frontend (`../haisir-frontend`) |
| `haisir-backend` | FastAPI backend (`../haisir-backend`) |
| `haisir-deploy` | Docker Compose, infrastructure (`../haisir-deploy`) |

**Why a separate repo?**
- Specs and code have different lifecycles, reviewers, and change cadences
- Stakeholders and designers can access specs without needing code repo access
- ClaudeCode and AI tools can be given the spec repo as a focused knowledge base
- Prototype HTML files are design artifacts — they don't belong in a code repo

---

## Repo Structure

```
haisir-specs/
├── README.md                              ← You are here
│
├── requirements/                          ← Spec files (what to build)
│   ├── 00_overview.md
│   ├── 01_data_model.md
│   ├── 02_auth_and_roles.md
│   ├── 03_student.md
│   ├── 04_teacher_tutor.md
│   ├── 05_06_07_personas.md
│   ├── 08_haitu_ai_layer.md
│   ├── 09_onboarding.md
│   ├── 10_notifications.md
│   ├── 11_role_migration.md
│   └── ui-mapping/                        ← UI mapping files (how it looks — frontend only)
│       ├── ui_student.md
│       ├── ui_teacher.md
│       ├── ui_parent_institution_admin.md
│       ├── ui_onboarding.md
│       └── ui_notifications.md
│
└── prototypes/                            ← Interactive HTML prototypes (open in browser)
    ├── haisir_student_flow.html
    ├── haisir_teacher_flow.html
    ├── haisir_parent_flow.html
    ├── haisir_institution_flow.html
    ├── haisir_superadmin_flow.html
    ├── haisir_onboarding_flow.html
    ├── haisir_notifications.html
    └── haisir_content_ownership_model.html
```

---

## Spec Update Convention

**Rule: specs must be updated before — or alongside — the code PR that implements a change.**

Specifically, any PR in `haisir-frontend` or `haisir-backend` that does any of the following must include a corresponding update to `haisir-specs` (either in the same PR description or as a linked `haisir-specs` PR):

- Adds or changes an API endpoint
- Adds or removes a screen or route
- Changes a business rule or permission
- Adds a new database table or column
- Changes how a role is assigned or validated

**PR description checklist (add to both frontend and backend PR templates):**

```
## Spec impact
- [ ] No spec change needed (bug fix / refactor only)
- [ ] Spec already up to date (link to relevant section)
- [ ] Spec updated in this PR (link to haisir-specs change)
- [ ] Spec update pending (link to haisir-specs issue/PR)
```

**Who reviews spec changes:** Product owner + lead developer must approve any PR to `haisir-specs` that changes business rules or API contracts. UI mapping and prototype changes can be approved by any developer.

---

## What is in this repo?

**Two types of files in `requirements/`:**
- **Spec files** (`00`–`11`) — the *what* and *why*. Business rules, API endpoints, data constraints. Backend and frontend both read these.
- **UI mapping files** (`ui-mapping/`) — the *how it looks*. Colours, component states, layout details, prototype screen IDs. Frontend only.

**Prototypes in `prototypes/`:**
The `.html` files are the definitive visual reference. Every UI mapping file links back to a specific screen ID in a specific prototype. Open the prototype in a browser alongside the mapping file when building frontend.

---

## Read This First — All Roles

**`requirements/00_overview.md`** — mandatory first read for everyone. Covers:
- System architecture (APISIX → Keycloak → FastAPI — read this before writing any auth code)
- Full tech stack with exact library versions
- All 6 personas and their roles
- Content ownership model (structured vs open tracks)
- Existing frontend routes and backend folder structure
- Key design decisions that must not be changed

---

## By Role

### Backend Developer

| Order | File | Why |
|---|---|---|
| 1 | `requirements/00_overview.md` | Architecture, tech stack, DDD folder structure, middleware |
| 2 | `requirements/01_data_model.md` | Existing schema + new tables, Pydantic models, indexes, Alembic migrations |
| 3 | `requirements/02_auth_and_roles.md` | APISIX JWT injection, CSRF pattern, `X-Current-Role`, permission matrix |
| 4 | `requirements/11_role_migration.md` | **Read before any auth or role work** — exact changes to existing codebase |
| 5 | Your persona spec | `03_student.md` / `04_teacher_tutor.md` / `05_06_07_personas.md` |
| 6 | `requirements/08_haitu_ai_layer.md` | If building any hAITU endpoint |
| 7 | `requirements/10_notifications.md` | If building notification generation or the polling endpoint |
| 8 | `requirements/09_onboarding.md` | If building onboarding API endpoints |

> Do not open `ui-mapping/` — it contains no backend-relevant information.

---

### Frontend Developer

| Order | File | Why |
|---|---|---|
| 1 | `requirements/00_overview.md` | Architecture, existing routes, `fetch` + CSRF + `X-Current-Role` conventions, no Redux rule |
| 2 | `requirements/02_auth_and_roles.md` | `X-Current-Role` header, role switching, `fetchWithCSRFRetry()` pattern |
| 3 | `requirements/11_role_migration.md` | **Read before touching `useAuth`** — new roles, metadata map, route guards |
| 4 | Your persona spec | `03_student.md` / `04_teacher_tutor.md` / `05_06_07_personas.md` / `09_onboarding.md` |
| 5 | Your UI mapping file | `ui-mapping/ui_student.md` etc. — screen IDs, colours, states, component layout |
| 6 | Open prototype in browser | `prototypes/haisir_student_flow.html` etc. — interactive visual reference |

> UI mapping files always reference a prototype screen ID (e.g. `s-home`) and a render function (e.g. `renderHome()`). Use these to find the exact screen in the prototype.

---

### ClaudeCode

Read files in this exact order for each task:

| Order | File | Why |
|---|---|---|
| 1 | `requirements/00_overview.md` | Understand the system before generating any code |
| 2 | `requirements/01_data_model.md` | Know the existing schema — extend, don't replace |
| 3 | `requirements/02_auth_and_roles.md` | Auth patterns are critical — wrong auth breaks everything |
| 4 | `requirements/11_role_migration.md` | If touching any role or auth code |
| 5 | Target spec file | The spec for the feature being built |
| 6 | UI mapping file | If generating frontend code — for colours, states, component structure |

**ClaudeCode rules:**
- Always check `01_data_model.md` section 2 (existing tables) before creating new tables — the schema already exists
- Never send Bearer tokens from the client — APISIX injects them. See `02_auth_and_roles.md` section 1
- Always use `X-Current-Role` (not `X-Active-Role`) — see `02_auth_and_roles.md` section 4.2
- Follow the DDD folder structure in `00_overview.md` section 6 — no business logic in route files
- Use imperative SQLAlchemy mapping — no `Base` subclasses in domain models
- Follow the `fetch` + CSRF + `X-Current-Role` pattern for all frontend API calls
- Do not add `institution_admin`, `tutor`, or `parent` to Keycloak until `11_role_migration.md` steps are followed in order

---

### QA / Test Engineer

| File | What to verify |
|---|---|
| `requirements/02_auth_and_roles.md` section 6 | Permission matrix — test each role cannot access other roles' data |
| `requirements/11_role_migration.md` section 9 | Role migration checklist — 17 explicit test cases |
| `requirements/03_student.md` Edge Cases | Empty states, error states, permission failures |
| `requirements/04_teacher_tutor.md` Edge Cases | Doubt reply validation, empty class states |
| `requirements/05_06_07_personas.md` Edge Cases | Parent link expiry, board publish conflicts |
| `requirements/09_onboarding.md` Edge Cases | Mid-flow abandonment, duplicate role setup |
| `requirements/10_notifications.md` section 4 | Generation rules — test cron-triggered notifications |
| `requirements/01_data_model.md` section 5 | Unique indexes — test constraint violations |
| `requirements/08_haitu_ai_layer.md` section 7 | Failure handling — test timeout and rate limit responses |

---

### DevOps / Infrastructure

| File | Section | Why |
|---|---|---|
| `requirements/00_overview.md` | Section 2 (Architecture) | APISIX config, Cloudflare, Keycloak setup |
| `requirements/00_overview.md` | Section 4 (Tech stack) | Exact versions for Docker images |
| `requirements/02_auth_and_roles.md` | Section 1 (Auth architecture) | APISIX JWT injection config |
| `requirements/02_auth_and_roles.md` | Section 2 (Keycloak config) | Realm settings, role setup |
| `requirements/11_role_migration.md` | Section 3 (Keycloak changes) | New realm roles to add |
| `requirements/01_data_model.md` | Section 5 (Indexes) | Indexes to create post-migration |
| `requirements/10_notifications.md` | Section 4 (Generation rules) | Cron job schedule requirements |

---

## File Index

### Spec Files (`requirements/`)

| File | Contents | Lines |
|---|---|---|
| `00_overview.md` | Architecture, tech stack, personas, content model, design decisions | ~200 |
| `01_data_model.md` | Existing schema, new tables, Pydantic models, indexes, migration notes | ~350 |
| `02_auth_and_roles.md` | APISIX auth flow, CSRF, role switching, permission matrix, security rules | ~300 |
| `03_student.md` | 11 student screens — business rules, API endpoints, edge cases | ~500 |
| `04_teacher_tutor.md` | 8 teacher/tutor screens — business rules, API endpoints, edge cases | ~450 |
| `05_06_07_personas.md` | Parent (5), Institution Admin (6), Admin (6) screens — all APIs | ~700 |
| `08_haitu_ai_layer.md` | 8 hAITU interaction types, prompt contracts, caching, token limits, failure handling | ~250 |
| `09_onboarding.md` | 8 onboarding screens, role switcher spec, 29 business rules | ~200 |
| `10_notifications.md` | Notification types, delivery model, generation rules, API | ~180 |
| `11_role_migration.md` | Exact changes to existing auth code for 3 new roles — Keycloak, backend, frontend | ~340 |

### UI Mapping Files (`requirements/ui-mapping/`)

| File | Covers | Links to prototype |
|---|---|---|
| `ui_student.md` | S01–S11 — colours, states, component layout | `prototypes/haisir_student_flow.html` |
| `ui_teacher.md` | T01–T08 — colours, states, heatmap thresholds | `prototypes/haisir_teacher_flow.html` |
| `ui_parent_institution_admin.md` | P01–P05, I01–I06, SA01–SA06 | `prototypes/haisir_parent_flow.html` etc. |
| `ui_onboarding.md` | ON01–ON08 — role cards, switcher, form states | `prototypes/haisir_onboarding_flow.html` |
| `ui_notifications.md` | All 5 persona feeds — icons, colours, filter tabs | `prototypes/haisir_notifications.html` |

### Prototype Files (`prototypes/` — open in browser)

| File | Personas covered | Screens |
|---|---|---|
| `haisir_student_flow.html` | Student | 11 |
| `haisir_teacher_flow.html` | Teacher / Tutor | 8 |
| `haisir_parent_flow.html` | Parent | 5 views |
| `haisir_institution_flow.html` | Institution Admin | 6 |
| `haisir_superadmin_flow.html` | Admin (SuperAdmin) | 6 |
| `haisir_onboarding_flow.html` | All roles — first-time setup | 8 |
| `haisir_notifications.html` | All roles — notification centre | 5 persona views |
| `haisir_content_ownership_model.html` | Reference — content ownership visualization | — |

---

## Key Things Every Developer Must Know

1. **APISIX injects the JWT** — the client never sends a Bearer token. FastAPI receives it from the gateway. See `02_auth_and_roles.md` section 1.

2. **The role header is `X-Current-Role`** — not `X-Active-Role`. Every API request must include it.

3. **CSRF on every mutation** — `POST`, `PUT`, `PATCH`, `DELETE` all require `X-CSRF-Token`. Use `fetchWithCSRFRetry()` on the frontend.

4. **No local users table** — user identity is Keycloak `sub` stored as a raw UUID string. No FK constraints on user columns.

5. **Existing schema is sacred** — `course_path_nodes`, `topics`, `assessments`, `exam_sessions` etc. already exist. Extend them, never drop or rename.

6. **`owner_type` is the content ownership key** — `platform` (admin only), `institution`, `tutor`. Added to `course_path_nodes` as a new column.

7. **No Redux, no Axios** — raw `fetch` with `credentials: 'include'`, custom hooks with `useState`/`useEffect` only.

8. **SQLAlchemy imperative mapping** — domain models are plain dataclasses. No `Base` subclassing anywhere in `domain/models/`.

9. **Existing roles are `student`, `instructor`, `admin`** — the new roles are `institution_admin`, `tutor`, `parent`. See `11_role_migration.md` for exact migration steps before adding them.

10. **`admin` = SuperAdmin** — the existing `admin` Keycloak role maps to the SuperAdmin/Platform Admin persona. No new `superadmin` role needed.

