# hAIsir — System Overview
> Version 1.1 | Updated to reflect actual baseline from `haisir_current.md`.
> Read this before any other file.

---

## 1. What is hAIsir?

hAIsir is an AI-enabled education platform. It supports a full learning lifecycle: structured course navigation, content delivery (PDFs, videos), quizzes, and formal timed exams. The new work adds an AI tutor (hAITU), multi-persona support, and a structured/open dual-track learning model on top of this working foundation.

**Tagline:** "Think and try, learn with hAI."
**AI tutor name:** hAITU
**Domain:** haisir.in

---

## 2. System Architecture

```
Browser
  → Cloudflare CDN/Tunnel
    → APISIX Gateway (port 9080/443)
        ├── Coraza WASM WAF (OWASP CRS v4)
        ├── CrowdSec Bouncer
        ├── OIDC plugin → Keycloak 26 (+ Google SSO)
        └── Proxies to:
            ├── Next.js Frontend
            └── FastAPI Backend (/api/*)
                (JWT injected upstream by APISIX)
```

**Critical:** APISIX is the single entry point. The frontend and backend never communicate directly. APISIX handles TLS termination, WAF, CSRF, OIDC auth, and JWT injection. See `02_auth_and_roles.md` for full auth details.

---

## 3. Repos

| Repo | Local path | Purpose |
|---|---|---|
| `haisir-deploy` | `../haisir-deploy` | Docker Compose, infrastructure |
| `haisir-frontend` | `../haisir-frontend` | Next.js frontend |
| `haisir-backend` | `../haisir-backend` | FastAPI backend |

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, react-pdf 10 |
| Backend | FastAPI 0.135, Python 3.14, SQLAlchemy 2 async, asyncpg, Pydantic v2, structlog |
| Auth | Keycloak 26 (OIDC + Google SSO), PyJWT, fastapi-csrf-protect |
| Gateway | Apache APISIX, Coraza WASM WAF (OWASP CRS v4), CrowdSec Bouncer |
| Database | PostgreSQL, Alembic (migrations) |
| Infra | Docker Compose, Cloudflare Tunnel, Jenkins CI/CD, Tailscale VPN |
| AI | Anthropic Claude (model configurable by admin — default: `claude-sonnet-4-6`) |

---

## 5. Existing Frontend (baseline to extend)

**App Router pages that already exist — do not rewrite, extend:**

| Route | What it does |
|---|---|
| `/home` | Category/course navigation tree + PDF viewer |
| `/assess` | Student quiz-taking experience |
| `/add-assessment` | Instructor assessment authoring |
| `/exam` | Student exam browsing and sessions |
| `/add-exam` | Instructor exam builder (multi-question types, paragraphs) |
| `/manage-categories` | Category CRUD |

**New routes to add** (do not modify the existing ones above except where explicitly noted in the persona specs):

| Route | Purpose |
|---|---|
| `/onboarding` | First-time role selection and setup |
| `/home/dashboard` | New unified student home dashboard (replaces current `/home` single-course view) |
| `/doubts` | Student doubt inbox |
| `/tutors` | Tutor discovery marketplace |
| `/profile` | Student profile + parent link code |
| `/teacher` | Teacher home dashboard |
| `/teacher/class/:id` | Class dashboard |
| `/teacher/student/:id` | Student detail |
| `/teacher/doubts` | Teacher doubt inbox |
| `/teacher/exam-results/:id` | Post-exam results |
| `/teacher/curriculum/:id` | Curriculum builder |
| `/institution` | Institution admin dashboard |
| `/institution/classes` | Classes manager |
| `/institution/people` | People manager |
| `/institution/curriculum` | Curriculum manager |
| `/institution/analytics` | Analytics dashboard |
| `/parent` | Parent dashboard |
| `/admin` | SuperAdmin dashboard (extends existing admin role) |

**State management convention (existing — do not deviate):**
- No Redux, Zustand, or React Context.
- All state lives in custom hooks (`useAuth`, `useCourseNavigation`, `useAssessmentState`, etc.) with plain `useState`/`useEffect`.
- New hooks follow the same pattern — one hook per domain.

**API call convention (existing — all new code must follow):**
- Raw `fetch` with `credentials: 'include'`, `X-CSRF-Token`, and `X-Current-Role` headers.
- Use `fetchWithCSRFRetry()` wrapper for all mutations.
- No Axios or other HTTP libraries.

**Pagination convention (all new list endpoints must follow this):**
- **Cursor-based pagination** — used for append-heavy feeds: notifications, activity timeline, doubt threads, hAITU chat history. Response includes a `next_cursor` field, `null` when no more results. Request param: `cursor`.
- **Offset-based pagination** — used for management and admin tables: student lists, class rosters, institution people manager, platform admin views. Request params: `page` (default 1) and `page_size` (default 20, max 100).
- Each endpoint specification must explicitly state which pagination type it uses.

---

## 6. Backend Structure (DDD — do not deviate)

```
api/routes/          → HTTP layer only (routers, no business logic)
domain/models/       → Pure Python dataclasses (zero ORM imports)
domain/services/     → All business logic lives here
domain/repositories/ → Abstract interfaces
infrastructure/      → Concrete SQLAlchemy repos + imperative mapping
schemas/             → Pydantic v2 request/response models
auth/                → JWT validation, CSRF, role decorators
```

**SQLAlchemy imperative mapping:** Domain models are plain dataclasses. ORM mapping is defined separately in `infrastructure/`. Do not use SQLAlchemy's declarative `Base` subclassing anywhere.

**Middleware stack (existing — do not modify):**
```
ProxyHeaders → SecurityHeaders → SecurityValidation
(content-type enforcement, 10MB limit, file type/size)
→ request ID assignment → structlog structured logging
```

**File storage convention:**
- **v1: Local disk storage.** All files stored at `data_dir/` following existing pattern for question images. Applies to all new content uploads — PDFs, and any content uploaded by tutors and institution admins.
- **Architecture:** A `StorageBackend` abstract interface must be implemented in `infrastructure/storage/` with two methods: `upload(file, path) → url` and `download(path) → bytes`. A `LocalDiskBackend` concrete implementation is used in v1. Active backend is selected via `STORAGE_BACKEND` environment variable (default: `local`).
- **Future:** `S3Backend`, `GCSBackend`, `AzureBackend` can be swapped in without any application code changes — only a new concrete implementation and environment variable change required.

**Existing API routes (all prefixed `/api/`):**

| Prefix | Purpose |
|---|---|
| `/api/auth` | CSRF token issuance (`GET /api/auth/csrf`); token refresh (`POST /api/auth/refresh` — **APISIX-handled**, not a FastAPI route) |
| `/api/users` | Current user identity (`/me`) — returns `sub`, `email`, `roles`, `onboarding_completed` |
| `/api/categories` | Category CRUD |
| `/api/courses` | Course management |
| `/api/course-path-nodes` | Course hierarchy tree |
| `/api/topics` | Topics within a course path node |
| `/api/topics-contents` | Content items (PDF, video, text) per topic |
| `/api/questions` | Question bank CRUD |
| `/api/paragraph-questions` | Reading passages with embedded question IDs |
| `/api/assessments` | Topic-based quizzes + attempt lifecycle |
| `/api/exams` | Exam templates |
| `/api/exam-sessions` | Per-student exam session lifecycle |
| `/api/answers` | Answer submissions |
| `/api/health` | Health check (unauthenticated) |

**New API route prefixes to add:**

| Prefix | Purpose |
|---|---|
| `/api/students` | Student profile, enrollments, progress |
| `/api/teachers` | Teacher profile, class management |
| `/api/tutors` | Tutor profile, marketplace, student relationships |
| `/api/parents` | Parent profile, child data access |
| `/api/organizations` | Institution management |
| `/api/classes` | Class CRUD and enrollment |
| `/api/doubts` | Doubt threads |
| `/api/haitu` | AI layer — all hAITU interactions |
| `/api/notifications` | Notification feed |
| `/api/admin` | SuperAdmin — boards, institutions, users, settings |
| `/api/parent-link-codes` | Parent link code validation (onboarding) |

---

## 7. Personas

Six personas. Each has a distinct topbar colour and workspace.

| Persona | Keycloak Role | Topbar Colour | Status |
|---|---|---|---|
| Student | `student` | `#0A1F5C` Navy | ✅ Existing role — extend UI |
| Institutional Teacher | `instructor` | `#0A3D2B` Dark teal | ✅ Existing role — extend UI |
| Platform Admin (SuperAdmin) | `admin` | `#080F17` Near-black + red pill | ✅ Existing role — add new screens |
| Institution Admin | `institution_admin` | `#0D1B2A` Near-black navy | ❌ New role + new UI |
| Independent Tutor | `tutor` | `#3C1F6E` Deep purple | ❌ New role + new UI |
| Parent | `parent` | `#3D2000` Warm brown | ❌ New role + new UI |

---

## 8. Content Ownership Model

Two learning tracks that coexist. A student can be in both simultaneously.

### Structured Track
```
Platform Admin (admin role)
    └── maintains Board content in course_path_nodes (owner_type = 'platform')
            └── Institution Admin
                    └── adopts board content → institution namespace (owner_type = 'institution')
                            └── Instructor
                                    └── delivers to Class → Student
```

### Open Track
```
Independent Tutor
    └── builds own curriculum (owner_type = 'tutor')
            └── Student enrolls (tutor invite or self-discovery)
                    └── hAITU + async tutor support → Parent tracks
```

**Dual enrollment:** A student can be simultaneously enrolled in structured classes (one or more institutions) and open courses (one or more tutors or self-directed). These are independent `enrollment` records.

---

## 9. The Doubt Escalation Chain

```
Student asks question on a topic
    → hAITU attempts to answer (scoped to topic + enrollment context)
        → Resolved? → Student marks resolved (or auto-closes after 7 days)
        → Not resolved? → Student clicks "Request teacher help"
            → Doubt appears in teacher's inbox (instructor or tutor)
                → Teacher types async response
                    → Student sees response in doubt thread
                        → Parent sees "Teacher responded" in activity feed
                            → Institution admin sees escalation rate in analytics
                                → Platform admin sees platform-wide AI resolution rate
```

Key rule: hAITU must attempt before escalation is possible (`doubt.haitu_attempted = true`).

---

## 10. Key Design Decisions (Baseline — Do Not Change)

| Decision | Source |
|---|---|
| No local users table — Keycloak `sub` as identity | Existing |
| APISIX injects JWT upstream — clients never send Bearer tokens | Existing |
| CSRF double-submit cookie pattern (`fastapi-csrf-protect`) | Existing |
| `X-Current-Role` header for active role context | Existing |
| Raw `fetch` only — no HTTP client libraries | Existing |
| No Redux/Zustand — custom hooks + useState only | Existing |
| SQLAlchemy imperative mapping — domain models are plain dataclasses | Existing |
| `question_ids` as PostgreSQL ARRAY columns — not join tables | Existing |
| Exam session questions reference live question rows via FK (no JSONB snapshot) | Existing |
| Images stored on disk at `data_dir/images/questions/`, base64 at API layer | Existing |
| `is_active` soft delete on `exam_templates` | Existing |
| No local users table | Existing |

**New decisions (added for this build):**

| Decision | Rationale |
|---|---|
| `owner_type` / `owner_id` on `course_path_nodes` | Enables multi-persona curriculum ownership |
| No live sessions in this phase | Keeps infrastructure simple — async only |
| No payment processing in this phase | Tutor marketplace is discover-only |
| hAITU always attempts before escalation | Ensures AI handles volume; teachers see only genuinely hard doubts |
| Parent sees plain language — no raw scores | Parents are not educators |
| Notifications polled (not push) | Avoids WebSocket infrastructure complexity |

---

## 11. Prototype Artifacts (Visual Source of Truth)

The following HTML prototypes are the visual source of truth for all UI specifications.

| File | Covers |
|---|---|
| `haisir_student_flow.html` | Student — 11 screens |
| `haisir_teacher_flow.html` | Teacher/Tutor — 8 screens |
| `haisir_parent_flow.html` | Parent — 6 screens |
| `haisir_institution_flow.html` | Institution Admin — 6 screens |
| `haisir_superadmin_flow.html` | Platform Admin — 6 screens |
| `haisir_onboarding_flow.html` | Onboarding + role switcher |
| `haisir_notifications.html` | Notifications — all personas |

---

## 12. Out of Scope (Current Phase)

- Live video/audio sessions
- Student-initiated session booking and payment
- Real-time push notifications (polling only)
- Mobile native app (web only)
- Offline mode
- Multi-language UI (English only)
- AI-generated image content
- Student peer collaboration
