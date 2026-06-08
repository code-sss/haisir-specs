# Implementation Progress

## Target State

This increment targets three personas only: **Student**, **Parent**, and **Platform Admin**. Institutions, instructors, tutors, classes, doubts, hAITU, and notifications are explicitly deferred.

Content is tagged with an `owner_type` discriminator (`'platform'` or `'parent'`) and `owner_id` (NULL for platform; parent `idp_sub` for parent-owned), added via additive `ALTER TABLE` to `course_path_nodes`, `topics`, and `exam_templates`. Platform Admin manages the authoritative platform board (arbitrary-depth `course_path_nodes` tree, topics, exam templates with `owner_type = 'platform'`). Topic content is created in two ways: (a) instant types — video URL and pasted text — written directly to `topic_contents`; (b) **extraction types — PDF and image — uploaded via multipart, queued in `extraction_jobs`, picked up by a worker process that uses `pypdfium2` for native PDF text and `glm-ocr` (vision LLM) for scanned PDFs / images, then materialized as N `topic_contents` rows of `content_type='text'` with permanent provenance back to the source filename via `source_extraction_job_id` + indefinite `extraction_job_audit`.** Students see two sections on their dashboard: "Platform Board" (blue) containing all platform content, and "Home Study" (green) containing content from their linked parent — visible only if an active `parent_child_links` record exists. Parents are content creators: they can adopt a platform board subtree (deep clone of nodes + topics only; content and exams not cloned) or build their own curriculum from scratch, upload notes per topic (extraction pipeline is shared with admin, gated by per-parent quota), and create private exams. Parent content is visible only to their linked child. Parents view child exam results for their own exams only (not platform exams). Token refresh after role assignment uses explicit logout (`/auth/logout`) — not `prompt=none`. Auth is APISIX-injected JWT with `X-Current-Role` header and CSRF on all mutations; identity is `idp_sub` (Keycloak `sub` as raw UUID string) with no local users table. The backend independently verifies each JWT: local JWKS RS256 decode is the fast first gate, and — when `introspection_enabled` — a feature-flagged OAuth2 token introspection call (RFC 7662) confirms the token is still active, catching revocation that stateless validation cannot. Introspection uses the existing `haisir-backend-admin` service-account client, caches results per token for a short TTL, and fails closed (Keycloak unreachable → 503, inactive → 401); Keycloak 26 requires the `token-introspection` scope and the backend client in the token `aud`, provisioned declaratively by deploy (see decisions.md 2026-06-02, TASKS.md G14). The `questions.question_type` enum is extended with three new values: `one_word_response` (compact inline input, auto-graded by normalized match), `matching` (two-column pair UI, partial credit per pair, right-column shuffled per-session using seeded Fisher-Yates with seed stored in `exam_session_questions.shuffle_seed`), and `problem_solving` (auto-graded final answer + optional working area captured in `exam_session_questions.working_text` but unscored this phase — instructor scoring deferred). The `essay` type gains an `essay_subtype` column as a rendering hint; valid values: `analytical`, `critical`, `extended`, `narrative`, `reflective`, `short` (6-value enum enforced by DB CHECK constraint). Schema additions via V27+V28: `questions` gains `essay_subtype VARCHAR(50) NULL` (widened from initial `VARCHAR(10)` in V28 with CHECK constraint), `working_required BOOLEAN DEFAULT false`, and `penalty_matching BOOLEAN DEFAULT false` (enables score-reduction mode for matching: `max(0, (correct − wrong) / total) × points`); `exam_session_questions` gains `working_text TEXT NULL` and `shuffle_seed INT NULL`. (See `target/2026-06-05_question_types_extension.md`.)

## Current State

> Snapshot baseline: haisir-backend `681d97a` (fix(exam_session): replace random seed generation with secrets for improved security, 2026-06-06), haisir-frontend `0446707` (fix(exam): resolve 9 SonarQube issues from last CI build, 2026-06-06), haisir-deploy `0dfc6c0` (fix(scripts): use exact version boundary match for image tag stale-bump, 2026-06-08).
> Next session: `git diff 681d97a..HEAD` in haisir-backend, `git diff 0446707..HEAD` in haisir-frontend, and `git diff 0dfc6c0..HEAD` in haisir-deploy instead of re-reading the full codebases.

The platform admin board content manager is fully implemented end-to-end. The AdminDashboard shows a 4-card Platform Overview (boards count, live topics, draft topics, total) sourced from `GET /api/admin/board-stats`, and per-board rich cards with emoji, live/draft topic counts, a "Live" badge, a "Manage" link, and click-to-edit inline description. The AddNodeModal uses a 9-type chip selector (course, chapter, module, section, unit, week, skill, grade 🔒, subject 🔒) with 3-tier hierarchy enforcement: root = grade only, under grade = subject only, deeper = any non-ancestor type; the backend validates both ancestor-type exclusion and sibling-type consistency (409 on violation). The NodeTree renders TopicTreeRows inline (live/draft dot + title) for non-reserved nodes; the NodeDetailPanel shows ChildNodesPanel (child cards with type chip + topic count) for reserved-type nodes and TopicPanel for all others. Topic CRUD (create, rename, toggle draft/live, delete) is fully implemented. Topic content CRUD is fully implemented for instant types (video URL, text) and the **frontend upload pipeline for PDF/image is complete** (G8–G9 done 2026-05-02): the `AddContentModal` was rebuilt with a 4-chip selector (PDF, Image, Video URL, Text), a drag-and-drop file zone, cost estimate preview with confirmation, and an upload-closes-immediately pattern. `useExtractionJobs` hook polls server jobs (3 s active / 5 s cooldown / stop after 60 s idle) and manages pseudo-jobs for in-flight uploads. The TopicRow now shows an **extraction jobs strip** (last 3 jobs, with status, progress, Cancel/Retry) and fires a toast + content invalidation when a job completes. A Toast system was added to `AdminProviders`. The APISIX upload route (`POST /api/admin/topics/*/extraction-jobs`) is deployed with a dedicated plugin config raising Coraza file-size limits to 50 MB (T5.0, 2026-05-04). Backend extraction API endpoints T5.1–T5.6 are complete (2026-04-30); backend schema (T2.1), domain layer (T3.1–T3.3), and the **full infrastructure layer (T4.1–T4.5)** are complete (2026-04-24 to 2026-05-07): `ExtractionJobRepository`, `ExtractionSourceStorage` (incl. `read()`), `GlmOcrProvider` (prefix-dispatch to LM Studio / OpenAI / Anthropic / Ollama cloud), and `PdfiumReader` (pypdfium2, no AGPL dep). The APISIX gateway suppresses the `Server` response header at the nginx level. A “Citizenship & Immigration” board with a “Discover Canada” course node has been added to seed data.

**Phase 1d-real specification + clickable prototype shipped 2026-04-23.** The full extraction pipeline (multipart upload → Postgres queue → worker → `pypdfium2` / `glm-ocr` → N text rows with permanent provenance) is fully designed and challenger-hardened. Spec: `target/requirements/12_content_extraction.md`. Schema deltas: `target/requirements/01_data_model.md` § “Schema Extensions (Phase 1d-real)”. Prototype (Playwright-validated, zero JS errors): `target/prototypes/haisir_admin_flow.html`.

**Also newly complete (2026-05-14):** Worker process (G7 — T7.1–T7.6) and Worker Docker Compose service (G1 — T1.1–T1.2) are fully built and deployed: `python -m haisir.worker` runs an `asyncio.gather` of extraction_loop, purge_loop, and heartbeat_loop; deployed as 2 replicas in Docker Compose sharing the `haisir-extraction-sources` volume. Worker health page (T12.1) ships at `/admin/system/workers` with a live table (Active/Stale pill, relative last-seen, 30s auto-refresh) and a zero-active banner. WAF exclusion (T13.1): Coraza SecRule chain suppresses OWASP CRS rule 931130 for `POST /api/topics-contents/` to allow external video URLs. URL validation (T13.2): backend Pydantic schema validates `url` field — https-only + hostname allowlist (`youtube.com`, `www.youtube.com`, `youtu.be`, `vimeo.com`, `www.vimeo.com`); local paths pass through; ValueError → HTTP 400.

**Also complete (2026-05-15):** Two rounds of SonarQube / security hardening: (1) 14 SonarQube issues resolved in the worker — `_process_single_page` helper extracted from `extraction_loop.py`, redundant `response_model=` annotations removed from 3 routes, Pydantic `None` defaults added to all Optional fields, worker graceful shutdown improved; (2) DoS regex hotspot mitigated in `GlmOcrProvider`, LM Studio transport protocol now configurable via `EXTRACTION__LMSTUDIO_USE_HTTPS=true` env var (default `false` = local `http://`). Frontend: SonarQube quality fixes across `add-content-modal`, `topic-row`, `admin-workers-page`, `utils.ts`, and `toast.tsx`. No new endpoints, tables, or screens.

**Also complete (2026-05-18):** `GlmOcrProvider` extended with Ollama cloud API support — new `ollama-cloud://` model spec prefix dispatches HTTP calls with Bearer token auth via `EXTRACTION__OLLAMA_CLOUD_API_KEY` env var. No schema, API, or UI changes.

**Also complete (2026-05-18 — G6 + G11):** Parent extraction API (G6 — T6.1–T6.5) is fully implemented: five endpoints under `/api/parent/curriculum` (create job with quota gate, list jobs with ETag/304, get single job with enumeration prevention, cancel with quota decrement, retry failed). Quota is enforced atomically (INSERT … ON CONFLICT DO UPDATE for increments; `GREATEST(0, concurrent_jobs - 1)` UPDATE for decrements) to prevent TOCTOU races. Provenance is now returned by `GET /api/topics-contents/{topic_id}` via a `LEFT JOIN extraction_job_audit` on `source_extraction_job_id` — response includes `provenance: { source_filename, page_no } | null`. Frontend: **ContentItemRow** now supports inline title rename (click-to-edit `<button>` → `<input>`, Enter/Escape/blur, `isTitleSaving` disabled state) and a **provenance badge** (`✨ from {filename} · p.{N}` pill, tooltip "Edits don't affect the audit record"); **DeleteContentDialog** updated to "Delete this content? The extraction audit record will be preserved."; **TopicRow** wires `handleRenameContent` via `useUpdateTopicContent` mutation.

**Also complete (2026-05-19 — refactor + bug fix):** `ExtractionSourcePurgedError` introduced as a dedicated `ExtractionJobNotRetryableError` subclass in `domain/exceptions.py`; `retry_job` service now raises it (instead of generic exception with string payload), and the retry route handler catches it with a typed `except` clause — eliminating fragile `"no longer exists" in str(exc)` inspection. **Bug fix** in `worker/finalize.py`: quota decrement condition was comparing `OwnerType.parent.value` (string) against the enum — always `False`, silently skipping quota release on job completion. Fixed to `OwnerType.parent`. No API contract changes; no schema changes; no UI changes.

**Also complete (2026-06-02 — G14 backend: T14.3–T14.6):** Backend token introspection fully implemented: `KeycloakSettings` extended with `introspection_enabled: bool = False` and `introspection_cache_ttl_seconds: int = 30` (T14.3); new `TokenIntrospectionClient` in `src/infrastructure/token_introspection.py` — calls `POST .../protocol/openid-connect/token/introspect` with client-credentials auth, caches per-token by `sha256(token)` with TTL `min(config, token exp)`, retries on transport errors via tenacity, raises `ExternalServiceUnavailableError` on unreachable (T14.4); wired into `verify_token` in `src/auth/user.py` — after local JWKS decode, when `introspection_enabled` calls the client; `active:false` → 401, unreachable → 503; `verify_token` converted to `async` (T14.5); full unit test suite added: `tests/unit/infrastructure/test_token_introspection.py` (cache hit avoids second HTTP call, active/inactive, unreachable) and extended `tests/unit/auth/test_user.py` (T14.6). All G14 implementation tasks T14.0–T14.7 are now complete.

**Also complete (2026-06-02 — frontend CSRF self-healing):** CSRF handling made self-healing across the entire frontend: `src/lib/utils.ts` now maintains a module-level CSRF token store (`getStoredCsrfToken`, `setStoredCsrfToken`, `refreshCsrfToken`) with single-flight deduplication to avoid thundering-herd; `buildApiHeaders()` falls back to the stored token automatically when none is passed; `fetchWithCSRFRetry()` now retries on HTTP 422 in addition to 400/401/403 (422 covers FastAPI's `InvalidHeaderError` for a missing `X-CSRF-Token` header); all bare `fetch()` call sites across api/, features/, and hooks/ replaced with unconditional `fetchWithCSRFRetry()`. `use-auth.ts` seeds the shared module store when a fresh token arrives. No new screens, no new endpoints, no schema changes.

**Also complete (2026-06-02 — G14 deploy: T14.1, T14.2, T14.7):** Keycloak token introspection infrastructure deployed: `common/keycloak/07-client-scopes.json` provisions the `token-introspection` client scope declaratively (`include.in.token.scope=false`, `display.on.consent.screen=false`); `setup-keycloak.sh` creates the scope idempotently and assigns it as a default scope to `haisir-backend-admin` (T14.1). `common/keycloak/03-client.json` adds an `oidc-audience-mapper` that injects `haisir-backend-admin` into the `aud` claim of every APISIX-issued access token, satisfying the RFC 7662 requirement that the introspecting client appear in `aud` (T14.2). OIDC integration test `10-test-oidc.sh` updated to introspect a live token using `haisir-backend-admin` creds, asserting `active==true`; `config.sh` adds `KC_BACKEND_ADMIN_CLIENT_ID`/`KC_BACKEND_ADMIN_CLIENT_SECRET` for staging and prod (T14.7).

**Also complete (2026-06-02 — backend minor + deploy infra):** Backend: worker `__main__.py` now forwards `ollama_api_key` to `GlmOcrProvider` (bug fix — key was set in config but not passed through); Starlette pip-audit vulnerability patched. Deploy: Postgres upgraded 16→18, Keycloak 26.4→26.6, etcd v3.6.6→v3.6.11 in `dev/docker-compose.yml`; worker service block removed from dev compose (defined only in common); APISIX Coraza WASM memory limit raised to 128 MB; `SecRequestBodyInMemoryLimit` set to 52 MB on the upload plugin config; extraction volume path changed to `/data/storage/extraction` (was `/data/storage/extraction_sources`); deploy script provisions extraction volume ownership (busybox chown to UID 65532); NPM proxy subnet added to Keycloak admin route trusted addresses; APISIX readiness wait extended to 60 attempts.

**Also complete (2026-06-04 — T15.1, T15.2 frontend):** Board tile click-through and tree row expand. Admin Dashboard board cards are fully clickable — an invisible stretch `<button>` (`position: absolute; inset: 0`) covers the whole card and calls `router.push('/admin/boards?board={id}')`; the description textarea and "Manage" link each call `stopPropagation` to prevent double-navigation. Node tree row expand: an invisible stretch button (`aria-hidden`, `tabIndex=-1`) covers the full row and fires `onToggle(node.id)` when the node has children and is not in rename mode; clicking the node label also triggers expand/collapse in addition to selecting the node.

**Also complete (2026-06-04 — backend config fix):** `introspection_enabled` default changed `False` → **`True`** in `KeycloakSettings` (fix commits ba594f4/b9d5545). Token introspection is now **on by default** for fresh deployments. Disable with `KEYCLOAK__INTROSPECTION_ENABLED=false`. Note: progress.md previously documented the default as `False` — actual shipped default is `True`.

**Also complete (2026-06-04 — deploy APISIX hardening):** Three deploy fixes: (1) Keycloak admin console route (`common/routes/13-keycloak-admin.json`) gains a `serverless-post-function` plugin in the `header_filter` phase — a Lua function rewrites `Location` headers on 3xx redirects to strip scheme/host and use the request host with HTTPS, preventing internal port numbers from leaking to clients; (2) `KEYCLOAK_ADMIN_ALLOWED_CIDR_2` env var added to the ip-restriction plugin on the admin route, allowing a second CIDR range for admin console access; (3) `common/scripts/template-configs.sh` enhanced with CIDR-expansion logic — detects JSON placeholders whose names contain "CIDR", converts comma-separated values into properly-quoted JSON arrays (handles whitespace trimming and empty-value filtering), maintaining backwards compatibility with single-value entries.

**Also complete (2026-06-04 — deploy):** Keycloak realm config gains `"attributes": { "frontendUrl": "{{FRONTEND_URL}}" }` in `common/keycloak/01-realm.json` — enables Keycloak-generated email links (password reset, verification, etc.) to resolve to the correct frontend URL. Release manifest v2026.3.1 added.

**Also complete (2026-06-06 — question type extension G1–G5 backend + G6 frontend):** V27 Alembic migration adds three new `questiontype` enum values (`matching`, `one_word_response`, `problem_solving`) and four new columns (`questions.essay_subtype`, `questions.working_required`, `exam_session_questions.working_text`, `exam_session_questions.shuffle_seed`). V28 migration widens `essay_subtype` to `VARCHAR(50)` with CHECK constraint (6 valid values: `analytical`, `critical`, `extended`, `narrative`, `reflective`, `short`) and adds `questions.penalty_matching BOOLEAN DEFAULT false` (enables partial-credit deduction mode for matching). Domain layer updated: `QuestionType` enum extended, `Question.validate()` handles all 8 types including `_validate_matching_question()`, `ExamSessionQuestion` carries `working_text` + `shuffle_seed`. Grading: `grade_question()` handles `one_word_response` (normalized match), `problem_solving` (answer text match), and `matching` (partial credit with optional penalty mode). Session creation generates `shuffle_seed` via `secrets.randbelow(2**31)` for matching questions; submit endpoint captures `working_text`. Pydantic schemas expose `essay_subtype`, `working_required`, `penalty_matching`, `shuffle_seed` per question in `GET /session/{id}/questions`. Frontend (commit `0446707`): `ExamQuestionType` interface extended with 6-value `EssaySubtype`, `shuffle_seed`, `working_required`; `seededShuffle` LCG utility matches backend algorithm; `OneWordResponseInput`, `MatchingInput`, `ProblemSolvingInput` components added; `EssayInput` gains `ESSAY_GUIDANCE` lookup map for all 6 subtypes; `question-type-utils.ts` and `answer-transformer.ts` cover all 8 types. Integration tests (G1–G5) and ROOT e2e Playwright test remain.

**Also complete (2026-06-08 — deploy + frontend fixes):** Deploy: new APISIX route `18-api-exam-session-submit.json` protects `POST /api/exam-sessions/session/*/submit` with PL2 Coraza WAF and targeted rule exclusions — `text_answer` (matching question JSON pairs) and `working_text` (math expressions) bypass RCE/SQLi/XSS false-positive rules; session cookies exempt from rules 942440/932220; all other CRS rules remain active (cc445cf). Deploy script (`deploy.sh`) overhauled with intelligent image tag management: auto-derives stale image tags for backend/frontend/gateway using exact version boundary match (`v<old>` or `v<old>-<suffix>` — avoids substring corruption), only updates `VERSION` in remote `.env` when all three haisir services are deployed together (prevents partial-deploy version drift). Release manifest v2026.3.3 added (bcbf11c). Frontend: auto-scroll after answering choice questions removed (was causing UX friction); `useCourseNavigation` now requires both `csrfToken` AND `currentRole` before fetching categories — eliminates the role-header race where JWT refresh completed before `buildApiHeaders` received the new role.

**Not yet built:** Two-section student dashboard, parent curriculum builder (adopt board subtree, create own nodes/topics, upload notes), parent link-code generation and redemption, board version display. Remaining gate tests for this increment: G1–G5 backend integration tests (schema round-trip, domain validate(), grading end-to-end, session seeding, API contract), ROOT e2e. Older gate tests still pending: G6 integration test (quota 429 + cross-parent isolation), G7 integration test, G9/G10/G11/G12/G13 Playwright tests, G14 integration test.

## Completed Phases

### Phase 1d — Topic Content Management (A1–A6 backend + B1–B8 frontend) ✓

**Completed:** 2026-04-20
**Commits:** haisir-backend `54d6e23`, haisir-frontend `7de033e`

**What was done:**
- Added `TopicContentUpdate` Pydantic schema (`title`, `order`, `description`, `url`, `text` — all optional; `content_type` excluded as immutable after creation)
- Added `update_platform_content` and `delete_platform_content` abstract + infra repo methods with platform-oracle JOIN protection (`topic_contents → topics WHERE owner_type = 'platform'`); returns `None`/`False` for both "not found" and "non-platform" (indistinguishable to caller)
- Added `update_platform_content` and `delete_platform_content` service methods (service strips `None` fields before delegating)
- `PATCH /api/topic-contents/{content_id}` (200 / 404) and `DELETE /api/topic-contents/{content_id}` (204 / 404); both admin-only, CSRF required
- Frontend types: `ContentType`, `TopicContent`, `CreateTopicContentInput`, `UpdateTopicContentInput`
- Frontend API functions: `getTopicContents`, `createTopicContent`, `updateTopicContent`, `deleteTopicContent` (mutations use `fetchWithCSRFRetry`)
- `useTopicContents` hook: query (disabled when `topicId` is null) + create/update/delete mutations with cache invalidation
- `ContentItemRow` component: type icon (🎬/📄/📝/❓/💬), title, description, order badge, edit/delete callbacks
- `AddContentModal`: native `<dialog>`, `mode: 'create' | 'edit'`, content type selector (`video`/`pdf`/`text`, disabled in edit mode), conditional URL/textarea fields, Zod + React Hook Form validation, `useFocusTrap`
- `DeleteContentDialog`: native `<dialog>` confirmation with loading state
- `TopicRow` extended: content section below topic header with sorted `ContentItemRow` list, "Add Content" button, empty state
- 100% test coverage maintained in both repos

---

### Phase 0 — Onboarding end-to-end: fix ON03/ON05 to spec + onboarding guards ✓

**Completed:** 2026-03-26

**What was done:**
- Replaced `on03-student-profile.tsx` → `on03-student-ready.tsx` (CTA-only: "Join your school", "Browse open courses", "Skip" — no form, per BR-ON-008)
- Replaced `on05-parent-link.tsx` → `on05-parent-ready.tsx` (CTA-only: "Link your child", "Skip" — no inline code input, per BR-ON-015)
- Both ON03/ON05 call `PATCH /api/users/me/onboarding-complete` before any navigation
- Added `onboardingCompleted` state to `useAuth` hook (reads `onboarding_completed_at` from backend)
- Root page (`/`) and home page (`/home`) guard against incomplete onboarding — redirect to `/onboarding`
- Optimistic role pattern: `setCurrentRole()` to localStorage after `assign_role`, `useAuth` falls back to it when backend returns `roles: []`
- Updated routes: `student-profile` → `student-ready`, `parent-link` → `parent-ready`
- Removed unused code: old form components, unused API functions, unused hooks, unused types
- 100% test coverage maintained

**Known issue (pending team discussion):**
- `GET /api/users/me` returns `roles: []` after `assign_role` because APISIX hasn't refreshed the JWT yet (~300 s expiry). Iframe and full-page redirect approaches for forcing JWT refresh are unreliable (cross-origin cookie blocking, redirect loops). The optimistic localStorage fallback works for onboarding navigation but role-gated API calls may fail until the JWT auto-refreshes. Likely needs a backend-side solution (e.g., read roles from DB instead of JWT, or expose a token refresh endpoint).

---

### Phase 1a — owner_type visibility enforcement (BR-DATA-003, BR-SEC-005) ✓

**Completed:** 2026-03-31
**Commit:** haisir-backend `aa5ddf7`

**What was done:**
- Added `OwnerType(StrEnum)` domain type (`platform` / `parent`) to replace raw strings; used across all domain models, schemas, and visibility logic
- Created `src/infrastructure/visibility.py` with `student_visibility_clause(table, viewer_sub)` (BR-DATA-003) and `admin_visibility_clause(table)` (BR-SEC-005) SQL clause builders
- Added visibility-dispatched `*_for_viewer(user: CurrentUser)` methods to `CoursePathNodeService`, `TopicService`, `ExamService`, `TopicContentService` (role dispatch: student → visible, admin → platform_only, instructor → unfiltered / default → platform_only for exams)
- Added matching `*_visible(viewer_sub)` and `*_platform_only()` abstract + concrete repository methods for all four aggregates
- Updated all student/admin-facing GET routes to use the new `*_for_viewer` service methods with `require_any_platform_role()` (student | instructor | admin) guards
- Fixed `exam_session.py` create/get-answers to call `get_by_id_for_viewer` instead of `get_by_id` — closed the session-creation bypass
- Changed `POST /api/topic-contents` from instructor to admin guard
- Fixed TopicContent URL construction to `topics/{content_type}/{filename}`
- Added V23 migration: `owner_id` Integer→String on nodes/topics; `owner_id` added to `exam_templates`; `revoked_at` added to `parent_child_links`
- Added V24 migration: covering index `(child_sub, revoked_at) INCLUDE (parent_sub)` on `parent_child_links`
- Added named permission helper methods (`require_admin`, `require_any_platform_role`, etc.) to `src/auth/permission.py`
- 1708 tests, 100% coverage maintained

**Deviations from original spec:**
- Physical `parent_child_links` columns are `parent_sub`/`child_sub` (not `parent_idp_sub`/`child_idp_sub`); schema is sacred
- Instructor gets `platform_only` (not unfiltered) for exam template listing — data isolation by default; explicit override required if full access is ever needed
- `case _:` default in all service dispatch methods ensures any future role safely defaults to platform-only

---

### Security hardening — error message sanitisation + path traversal ✓

**Completed:** 2026-04-01
**Commit:** haisir-backend `492b320` (+ `589db61` alembic index fix)

**What was done:**
- All 403 responses now return generic `"Forbidden: insufficient permissions"` — role context logged server-side only (no role enumeration in HTTP responses)
- `PATCH /api/users/me/onboarding-complete` tightened to require `student` or `parent` role (was any authenticated user)
- Added `require_student_or_parent()` composite helper to `permission.py`
- Added `SQLAlchemy IntegrityError` handler → `409 "Data conflict"` (prevents schema details leaking to clients)
- Added catch-all `Exception` handler → `500 "Internal server error"` (suppresses stack traces)
- Replaced `JSONResponse` with `ORJSONResponse` project-wide in exception handlers
- Fixed path traversal in `topic_content.py` (FileResponse) and `imageutil.py` (`encode_image_to_base64` / `save_base64_image`) — resolves paths relative to `data_dir` and rejects anything that escapes it
- Fixed bare `except:` (Python-2 style) in `parent.py`
- Alembic V24: added `IF NOT EXISTS` guard for the visibility index (was failing on fresh-then-migrated DBs)
- 1723 tests, 100% coverage maintained

---

### Phase 1b — Admin Board Content Manager: Tree UI + Node CRUD (backend) ✓

**Completed:** 2026-04-02
**Commit:** haisir-backend `a293bf8`

**What was done:**
- `PATCH /api/course-path-nodes/{id}` — rename/reorder platform-owned nodes (admin only)
  - Returns `404` for both not-found and non-platform-owned nodes (oracle protection)
  - `name` validated: `min_length=1`, `max_length=255`; empty string → `422`
  - No-op early return when both `name` and `order` are `None` — avoids pointless `UPDATE` round-trip
- `DELETE /api/course-path-nodes/{id}` — hard-delete node and full subtree (admin only)
  - Returns `409` if any node in the subtree has a `pending` or `ongoing` exam session
  - 12-step cascade: `exam_session_questions` → `exam_sessions` → `exam_template_questions` → `exam_templates` → `assessment_answers` → `assessment_attempts` → `assessments` → `topic_contents` → `topics` → `course_path_nodes` (all atomically; PostgreSQL `ON DELETE NO ACTION` deferred to end of statement for self-referential FK)
- `GET /api/course-path-nodes/tree/{category_id}` — full nested tree for a category (all platform roles)
  - Role-dispatches per Phase 1a visibility rules: `admin` → `platform_only`, `student` → `visible`, `instructor`/default → `get_by_category`
  - Assembles flat DB result into nested tree in Python (`_build_tree`); zero N+1
- 1810 tests, 100% coverage maintained

**Deviations from original spec:**
- Category GET endpoints (`GET /api/categories`, `GET /api/categories/{id}`) were guarded with `require_instructor_or_student()`, silently blocking admin from the board selector sidebar. Changed to `require_any_platform_role()` as a prerequisite bug fix (not in Phase 1b scope but required for the frontend to function).
- Active-session check evaluates `exam_sessions.status IN ('pending', 'ongoing')` directly on subtree nodes. The spec phrased this as "descendant topic has an active exam_session"; since `exam_sessions` link to `course_path_node_id` (not `topic_id`), the CTE traversal over nodes is the correct implementation.

---

### Phase 1b — Admin Board Content Manager: Tree UI + Node CRUD (frontend) ✓

**Completed:** 2026-04-02
**Commit:** haisir-frontend `1923050`

**What was done:**
- New `src/features/admin/` bounded context: API layer, types, hooks, components, domain logic — all isolated
- New routes: `/admin` (AdminDashboard — board list + link to boards manager) and `/admin/boards` (AdminBoardsPage — full board content manager)
- `AdminDashboard`: fetches and lists all boards via `GET /api/categories`; links directly to `/admin/boards?board={id}`
- `AdminBoardsPage`: board selector strip (fetches categories, highlights selected), hierarchical node tree (fetches via `GET /api/course-path-nodes/tree/{categoryId}`), node detail panel (empty state "Select a node" — topics panel is Phase 1c)
- `NodeTree` + `NodeTreeRow`: expand/collapse tree, inline rename on click (`PATCH`), add-child-node modal, delete confirmation dialog (blocks with message on 409)
- `AddBoardModal`: `POST /api/categories` to create a new board
- `AddNodeModal`: `POST /api/course-path-nodes` with `owner_type: "platform"` hardcoded
- `RenameNodeInline`: inline edit with save/cancel, sends `PATCH /api/course-path-nodes/{id}` with `{ name }`
- `DeleteNodeDialog`: sends `DELETE /api/course-path-nodes/{id}`; catches `AdminDeleteBlockedError` (409) and shows reason to admin
- `useFocusTrap` hook: traps keyboard focus inside open modals (accessibility)
- Route guard: `/admin` prefix added to `useAuth` route gates requiring `admin` role
- `?board=` URL param validated against `/^[\w-]+$/` before use (XSS guard)
- 58 files, full test coverage maintained

**Deviations from original spec:**
- Route is `/admin` + `/admin/boards` (not `/admin/board-content` as originally scoped)
- `CreateNodeInput.position` field name differs from backend's `order` field — backend accepts and ignores extra fields; no functional impact but worth aligning in a follow-up

---

### Phase 1b-fix — Admin Layout Alignment + Routing (frontend) ✓

**Completed:** 2026-04-02
**Commit:** haisir-frontend `cc9d69a`

**What was done:**
- `src/app/page.tsx` — role-aware redirect: `admin` → `/admin`, `parent` → `/parent`, default → `/home`; waits for `isLoading === false` before redirecting
- `src/app/admin/layout.tsx` + `AdminRouteGuard` — blocks non-admin role, redirects to `/home`; shows spinner while auth resolves
- `AdminSidenav` — dark sidebar, 190px default, 140–300px resizable range, 2 nav items (🏠 Dashboard, 📚 Board content); active item highlighted via `usePathname()`
- `BoardSelectorStrip` — 60px vertical dark strip (`#080F17`), 40×40px emoji icon buttons cycling 📗📘📙, "+" add button pinned at bottom
- `useResize` hook — vanilla `mousedown`/`mousemove`/`mouseup` drag-handle; 240px default / 160–500px for tree panel
- Sidenav resize — same `useResize` hook reused; 190px default / 140–300px
- Node label text-size audit — 14px (0.875rem, ≥ 13px spec), `title={node.name}` browser tooltip, `text-overflow: ellipsis`

**Deviations from original spec:**
- Sidenav background uses `#1e293b` (dark slate) instead of spec's `#080F17`; all other dimensions and layout match the prototype exactly

---

### Phase 1c-pre — X-Current-Role Enforcement (backend + frontend) ✓

**Completed:** 2026-04-03
**Commit:** haisir-backend `899127e`, haisir-frontend `b4b9495`

**What was done:**
- Split `src/auth/user.py` into `current_active_user` (strict — `400` when `X-Current-Role` absent) and `current_active_user_lenient` (old behaviour — defaults to `roles[0]`). All `require_*()` helpers depend on strict variant and inherit enforcement automatically.
- Switched three exempt onboarding endpoints (`GET /me`, `POST /me/assign-role`, `PATCH /me/onboarding-complete`) to `current_active_user_lenient`; `PATCH /me/onboarding-complete` adds inline student/parent check (`403` for other roles)
- Removed `require_student_or_parent()` helper from `permission.py` (no longer needed)
- Updated auth tests: `test_valid_payload_default_role` → asserts `400`; added `TestCurrentActiveUserLenient` class; updated route test apps to override both `current_active_user` and `current_active_user_lenient`
- Frontend: `buildApiHeaders()` was already correct (always sends header); added JSDoc documenting BR-SEC-006 contract and three exempt endpoints
- Fixed Phase 1b deviation: `CreateNodeInput.position` → `order` (backend field name); added two tests confirming `order` serialised correctly

---

### Phase 1c-post — Admin UX Alignment ✓

**Completed:** 2026-04-18
**Commits:** haisir-backend `819893c`, `c4abe28`, `6dc7595`; haisir-frontend `dec3ab8`, `3d0dd72`, `afaf2d7`, `43fa83d`
**Archived plan:** `Implementation_planning/archive/phase1c-post-plan.md`

**What was done:**
- V25 Alembic migration: expanded `nodetype` PostgreSQL enum from 3 → 9 values (added `chapter`, `module`, `section`, `unit`, `week`, `skill` via `ALTER TYPE nodetype ADD VALUE IF NOT EXISTS`)
- `GET /api/admin/board-stats` — new admin-only endpoint; single LEFT JOIN query returning per-board `live_topics`/`draft_topics`/`total_topics` and platform-wide totals
- `GET /api/admin/board-stats` now also returns `platform_boards` count in `PlatformTotals` (total number of platform-owned boards); backed by `BoardPlatformTotals` TypedDict in `category.py` domain model for typed service return
- Added `response_model=BoardStatsRead` to `GET /api/admin/board-stats` (was missing)
- Fixed `POST /api/course-path-nodes/` to return `201 Created` (was incorrectly returning 200)
- `POST /api/course-path-nodes` — added two tree-structure invariants: (A) ancestor-type exclusion (new type must not appear in any ancestor), (B) sibling-type consistency (all platform-owned siblings share one type). Both violations return 409.
- `POST /api/topics` / `TopicCreate` schema — `status: "draft" | "live"` is now a required field at API boundary (no silent default)
- `CategoryCreate` schema — `path_type` defaults to `"structured"`
- AdminDashboard rewritten: 4-stat Platform Overview cards (blue/green/amber/gray), rich per-board cards (emoji, live/draft counts, Live badge, Manage link, click-to-edit description)
- `useBoardStats` + `useUpdateBoardDescription` hooks added
- AddNodeModal: chip selector grid (9 types, 3-tier hierarchy enforcement via `isTypeDisabled`; reserved types show 🔒 amber chips; default = first enabled type)
- NodeDetailPanel: conditionally renders `ChildNodesPanel` (for `grade`/`subject`) or `TopicPanel` (others)
- `ChildNodesPanel`: child node cards with type chip + live topic count
- `TopicTreeRows`: inline live/draft dot + title rows inside NodeTree for non-reserved nodes
- `admin-node-domain.ts`: pure domain functions (`buildNestedTree`, `isTypeDisabled`, `buildBreadcrumb`, `findNodeById`, `sortNodesByPosition`)
- All modals converted to native `<dialog>`; `BoardSelectorStrip` uses semantic `<ul>/<li>`; `AdminRouteGuard` spinner uses `<output>`
- AddBoardModal: description textarea field added; `path_type` hardcoded to `"structured"`
- Added parametrized tests for all 9 `NodeType` enum values and `platform_boards` behaviour
- Dependency fix: `python-multipart` → 0.0.26; added `mako` and `pytest` to dependency manifest
- `admin-dashboard.tsx`: board description is now click-to-edit — inline `<input>` activates on click; Enter commits via `PATCH /api/categories/{id}`; Escape cancels; double-fire guard (`isCommittingRef`) prevents `onBlur` re-firing after Enter; save failures surface an error alert below the input
- `admin-dashboard.module.css`: replaced hardcoded hex values with design tokens (`--color-text-secondary`, `--color-surface`, `--color-text-primary`)
- `admin-node-domain.ts`: `RESERVED_TYPES` set now derived from canonical `RESERVED_NODE_TYPES` export in `admin.types.ts` — eliminated duplicate literal
- Next.js upgraded to 16.2.3 (patched GHSA-q4gf-8mx6-v5v3: DoS via Server Components, affected ≥16.0.0-beta.0 <16.2.3)
- 30 unit tests added for B4; 100% coverage maintained

**Deviations from original plan:**
- Schema/route files named `admin.py` (plan said `admin_stats.py`); response type names differ (`BoardTopicStats`/`PlatformTotals`/`BoardStatsRead` vs. plan's `BoardStats`/`PlatformOverview`/`AdminDashboardStats`)
- Hierarchy enforcement is a 3-tier rule (root=grade only, under grade=subject only, deeper=any non-ancestor) rather than simple sibling-type disable
- ChildNodesPanel and TopicTreeRows added (not in plan)
- Native `<dialog>` + semantic HTML improvements throughout (SonarQube-driven, not planned)

---

### Phase 1c — Admin Topics Management ✓

**Completed:** 2026-04-06
**Commit:** haisir-backend `78a5490`, haisir-frontend `8b349e5`

**What was done:**
- `PATCH /api/topics/{id}` — partial-update a platform-owned topic's `title`, `order`, and/or `status` (admin only, CSRF required); oracle-protected 404 for non-platform-owned topics
- `DELETE /api/topics/{id}` — hard-delete a platform-owned topic with FK cascade: `assessment_answers → assessment_attempts → assessments → topic_contents → topics`
- `TopicRead` now includes `status: str` field (column existed since Phase 1a, was not exposed in schema)
- Added `TopicUpdate` Pydantic schema with `title?`, `order?`, `status?: Literal["draft", "live"]`
- BR-STU-003 fix: `get_by_course_path_node_visible` now filters `status = 'live'` — students no longer see draft topics
- Live-topic guard on node delete: `DELETE /api/course-path-nodes/{id}` returns 409 `"Cannot delete: this node has live topics."` (checked before active-session guard) via `has_live_topics_in_subtree` recursive CTE
- Frontend `NodeDetailPanel` now renders a live `TopicPanel` (replacing Phase 1c placeholder)
- `TopicPanel`: fetches topics for selected node, shows loading/error/empty states, "+ Add topic" button
- `TopicRow`: inline rename (`RenameTopicInline`), draft/live status toggle, delete (×) with `DeleteTopicDialog`
- `AddTopicModal`: React Hook Form + Zod, submits `POST /api/topics/`
- `DeleteTopicDialog`: handles 409 (`AdminDeleteBlockedError`) by showing backend `detail` message
- New hooks: `useTopics`, `useCreateTopic`, `useUpdateTopic`, `useDeleteTopic`
- All mutations invalidate `["admin", "topics", nodeId]` query key

---

