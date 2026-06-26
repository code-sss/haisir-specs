# Implementation Progress

## Target State

This increment targets three personas only: **Student**, **Parent**, and **Platform Admin**. Institutions, instructors, tutors, classes, doubts, hAITU, and notifications are explicitly deferred.

**Essay AI Grading (newly added — Phase 1 backend + deploy only; Phase 2 UI deferred):** `essay` questions are now evaluated by an async AI-grading pipeline that reuses the existing LLM provider infrastructure (`glm-ocr` / Ollama pattern). The exam owner sets `essay_grading_mode` per exam template (`auto_release` default: AI score released to student immediately; `review_first` opt-in: score held until owner confirms). A per-question analytic rubric (JSONB, 3–6 weighted criteria with per-level descriptors) may be attached; if absent, a built-in default is selected by `essay_subtype`. The LLM outputs per-criterion levels only; the backend computes `ai_score = Σ(level/scale_max × weight) × points` (no LLM arithmetic). The worker polls `essay_grading_jobs` (new table, same `FOR UPDATE SKIP LOCKED` pattern as extraction) and writes `ai_score`, `ai_feedback`, `ai_rationale` to `exam_session_questions`. Students can dispute released AI grades; exam owners (parent for parent-owned exams, admin for platform exams) can confirm or override. A `GradingSettings` config block mirrors `ExtractionSettings` with `GRADING__MODEL_SPEC` defaulting to `qwen3:14b` (local, PII on-prem); Ollama-cloud (`gpt-oss:120b-cloud`) and `anthropic://` are opt-in. Schema: V29 migration adds 3 columns to `questions`, 1 to `exam_templates`, 9 to `exam_session_questions`, plus the `essay_grading_jobs` table. Auth: 2 new security rules (BR-SEC-011, BR-SEC-012) plus permission matrix rows for dispute (student/parent) and override/confirm (owner only). Instructor/tutor grading deferred until role migration.

Content is tagged with an `owner_type` discriminator (`'platform'` or `'parent'`) and `owner_id` (NULL for platform; parent `idp_sub` for parent-owned), added via additive `ALTER TABLE` to `course_path_nodes`, `topics`, and `exam_templates`. Platform Admin manages the authoritative platform board (arbitrary-depth `course_path_nodes` tree, topics, exam templates with `owner_type = 'platform'`). Topic content is created in two ways: (a) instant types — video URL and pasted text — written directly to `topic_contents`; (b) **extraction types — PDF and image — uploaded via multipart, queued in `extraction_jobs`, picked up by a worker process that uses `pypdfium2` for native PDF text and `glm-ocr` (vision LLM) for scanned PDFs / images, then materialized as N `topic_contents` rows of `content_type='text'` with permanent provenance back to the source filename via `source_extraction_job_id` + indefinite `extraction_job_audit`.** Students see two sections on their dashboard: "Platform Board" (blue) containing all platform content, and "Home Study" (green) containing content from their linked parent — visible only if an active `parent_child_links` record exists. Parents are content creators: they can adopt a platform board subtree (deep clone of nodes + topics only; content and exams not cloned) or build their own curriculum from scratch, upload notes per topic (extraction pipeline is shared with admin, gated by per-parent quota), and create private exams. Parent content is visible only to their linked child. Parents view child exam results for their own exams only (not platform exams). Token refresh after role assignment uses explicit logout (`/auth/logout`) — not `prompt=none`. Auth is APISIX-injected JWT with `X-Current-Role` header and CSRF on all mutations; identity is `idp_sub` (Keycloak `sub` as raw UUID string) with no local users table. The backend independently verifies each JWT: local JWKS RS256 decode is the fast first gate, and — when `introspection_enabled` — a feature-flagged OAuth2 token introspection call (RFC 7662) confirms the token is still active, catching revocation that stateless validation cannot. Introspection uses the existing `haisir-backend-admin` service-account client, caches results per token for a short TTL, and fails closed (Keycloak unreachable → 503, inactive → 401); Keycloak 26 requires the `token-introspection` scope and the backend client in the token `aud`, provisioned declaratively by deploy (see decisions.md 2026-06-02, TASKS.md G14). The `questions.question_type` enum is extended with three new values: `one_word_response` (compact inline input, auto-graded by normalized match), `matching` (two-column pair UI, partial credit per pair, right-column shuffled per-session using seeded Fisher-Yates with seed stored in `exam_session_questions.shuffle_seed`), and `problem_solving` (auto-graded final answer + optional working area captured in `exam_session_questions.working_text` but unscored this phase — instructor scoring deferred). The `essay` type gains an `essay_subtype` column as a rendering hint; valid values: `analytical`, `critical`, `extended`, `narrative`, `reflective`, `short` (6-value enum enforced by DB CHECK constraint). Schema additions via V27+V28: `questions` gains `essay_subtype VARCHAR(50) NULL` (widened from initial `VARCHAR(10)` in V28 with CHECK constraint), `working_required BOOLEAN DEFAULT false`, and `penalty_matching BOOLEAN DEFAULT false` (enables score-reduction mode for matching: `max(0, (correct − wrong) / total) × points`); `exam_session_questions` gains `working_text TEXT NULL` and `shuffle_seed INT NULL`. (See `target/2026-06-05_question_types_extension.md`.)

## Current State

> Snapshot baseline (superseded 2026-06-10): haisir-backend `9fcf14d` (essay AI grading backend complete, 2026-06-09), haisir-frontend `d0e9242` (grading_pending UI state + auto-grade checkbox, 2026-06-09), haisir-deploy `4261909` (GRADING env vars wired into worker service, 2026-06-09).

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

**Also complete (2026-06-09 — Essay AI Grading backend G7–G11 + deploy + frontend):** Full essay AI grading pipeline implemented. V29 migration adds `rubric` (JSONB), `model_answer` (TEXT), `auto_grade_essay` (BOOLEAN DEFAULT true) to `questions`; `essay_grading_mode` (VARCHAR, CHECK: 'auto_release'|'review_first') to `exam_templates`; nine grading-state columns to `exam_session_questions`; and the `essay_grading_jobs` table (same `FOR UPDATE SKIP LOCKED` pattern as extraction). V30 adds `grading_pending` to the `examstatus` enum. Submit endpoint enqueues `auto_grade_essay=true` essay questions and transitions session to `grading_pending` when jobs exist; `recompute_score()` runs atomically. Three new endpoints: `POST .../dispute` (student disputes released AI grade → `disputed`), `POST .../confirm-grade` (owner finalises AI score → `finalized`), `PATCH .../grade` (owner manual override → `overridden`, sets `override_score`/`override_feedback`). `GET .../review` now returns `grading_status`, `ai_feedback`, and `ai_rationale` (owner-only) per essay question. `EssayGraderProvider` dispatches to `anthropic://`, `openai://`, `lmstudio://`, or plain Ollama model; score formula is LLM-arithmetic-free (`sum(level/scale_max × weight) × points`). `RubricResolver` returns question's custom rubric or a built-in default by `essay_subtype`. `essay_grading_loop` polls every 5 s; in `auto_release` mode transitions `grading_status → released`, sets `earned_points = ai_score`, and auto-completes the session when all jobs finish. `GradingSettings` wired via 5 new `GRADING__*` env vars in the Docker Compose worker service. Frontend: `/exam` page renders a "Grading Pending" interstitial banner on `grading_pending` submit result with "View Attempts" / "Back to Exams" CTAs; attempts modal shows "Grading…" label and disables detail view for pending attempts; question editor gains "Auto-grade with AI" checkbox for essay questions (default on). SonarQube: 12 issues resolved across exam, grading, and shared modules (commit 9fcf14d).

**Also complete (2026-06-10 — backend SonarQube fix):** `_apply_answer_mutations()` helper extracted from the inline answer loop in `submit_exam()` (`exam_session.py`); FIXME comment removed from `request_middleware.py`. Pure refactor — no API, schema, or domain changes.

**Also complete (2026-06-10 — deploy script fixes):** Four deploy script improvements: (1) `template-configs.sh` CIDR-expansion fix — trailing newline and quote handling corrected so all CIDR entries are processed; (2) `deploy.sh` falls back to `rollback.previous_version` when `VERSION` lags (stale image-tag bump edge case); (3) worker auto-restarted alongside backend in every deploy (shares haisir-backend image); worker added to v2026.3.4 release manifest; (4) shell variable refs in image tags expanded before version comparison. All changes in `common/scripts/` — no service config, compose, or APISIX route changes.

**Also complete (2026-06-12 — deploy WAF fixes):** Two targeted Coraza rule exclusions added to `common/routes/12-api-exams-static.json`: (1) `explanation`, `question_text`, and `.text` fields excluded from `OWASP_CRS/ATTACK-PHP` to prevent false positives from science content ("respiratory system (inhalation)" matching PHP `system()` pattern); rule 932271 (Unix Shell Tilde Expression, PL2) excluded via ID-based selector for the same fields (tilde notation in scientific text); (2) `correct_answers` field excluded from `OWASP_CRS/ATTACK-SQLI` and `OWASP_CRS/ATTACK-RCE` — math fractions like "2 and 1/2" trigger libinjection rule 942100 as SQL `X AND Y/Z` patterns. No compose, service, or route changes.

**Also complete (2026-06-13 — hotfix v2026.3.5 backend):** Essay fields fully wired through the exam create and update routes. `POST /api/exams/{node_id}/static` now accepts `model_answer`, `rubric`, `auto_grade_essay` per question item (via new `QuestionExtras` dataclass) and `essay_grading_mode` at the template level — these columns existed in the DB since V29 but were not wired in the route handlers until this release. `PATCH /api/exams/{node_id}/static` likewise extended with `model_answer`, `rubric`, `auto_grade_essay`, and explicit `clear_*` booleans for null-clear. `GET /api/questions/` now returns `QuestionReadStudent` schema — `rubric` and `model_answer` excluded from the public question bank. Review endpoint: `model_answer` returned to students only when `grading_status in ('released','finalized','overridden')`; `explanation` (mark scheme) for essay questions gated to the same condition. `earned_points` and `earned_marks` rounded to 2 decimal places at both the per-question and session level. `EssayGradingMode` StrEnum added to domain layer. `_process_patch_item()` helper extracted from `update_static_exam_with_questions` (SonarQube — no behaviour change). Release tagged v2026.3.5.

**Also complete (2026-06-13 — hotfix v2026.3.5 frontend):** Exam authoring and results view reworked for essay grading. `ExamBuilder` gains an "Essay grading mode" dropdown (`auto_release` / `manual_release`; state managed in `useExamAuthoring`, sent as `essay_grading_mode` in the API payload). `QuestionEditor` essay section split into two separate fields: "Model answer" textarea (prose shown to students after grade release, sent as `model_answer`) and "Mark scheme / Rubric" textarea (grading criteria, stored as `explanation`). `AttemptsModal` major rework: essay questions use a dedicated expanded two-row layout (`renderEssayRows`) — main row shows the full submitted essay text and earned/total marks; a second row (shown only when grade is released/finalized/overridden) surfaces AI Feedback (blue box), Model Answer (teal box), and Mark Scheme/Explanation; non-essay questions use the compact `renderResultRow`. All results now sorted by `QUESTION_TYPE_ORDER` before rendering. `#` row-number column added. Points formatted to 2dp via `formatPoints()`. `ExamResult` type extended with `grading_status`, `ai_feedback`, `model_answer`, `explanation`; `QuestionV2` extended with `model_answer`. JSON import/export updated to carry `model_answer`. Release tagged v2026.3.5.

**Also complete (2026-06-13 — deploy T1.1: pgvector Postgres image):** New `postgres-docker/` directory added to `haisir-deploy` containing: `Dockerfile` (builds `haisir-postgres` image from Wolfi base, installs pgvector 0.8.2 alongside standard Postgres); `Jenkinsfile` (Jenkins pipeline to build and push the image to the container registry); `test.sh` (smoke-test script — starts the image, connects, asserts `SELECT extversion FROM pg_extension WHERE extname='vector'` returns `0.8.2`). The image is built and published independently from the service compose files; compose files (`common/` and `dev/`) not yet updated to use it — that is T1.2/T1.3, which are next on the `feature/rag` branch.

**Also complete (2026-06-14 — deploy T1.2, T1.3: pgvector image wired into compose):** `common/docker-compose.yml` and `dev/docker-compose.yml` updated to use the `haisir-postgres` custom pgvector image built by the T1.1 Dockerfile. Both db services now reference the new image. Backend services can assume pgvector extension availability from this point. Pending: T1.4 pgvector smoke test. `haisir-deploy` `feature/rag` at `88cbe5d`.

**Also complete (2026-06-15 — feature/rag backend: Phase 2 RAG drain loop + text restructuring + student dashboard):** Full RAG pipeline wired on `feature/rag`. V31 Alembic migration enables `vector` extension (T2.1); V32 adds `data_topic_content_chunks` table with `embedding vector(1024)` (T2.2). LlamaIndex deps + `OllamaEmbedding(bge-m3)` in `pyproject.toml` (T3.1). `EmbeddingSettings` with `embed_dim: int = Field(default=1024)` and `poll_interval_seconds=5` (T3.2). `rag_outbox_loop.py`: `PGVectorStore.from_params(hybrid_search=True, text_search_config="english", hnsw_kwargs={m:16, ef_construction:64, ef_search:40})` + 3-level hierarchy JOIN (`topic_contents → topics → course_path_nodes`) storing `topic_title`, `node_name`, `parent_name`, `grandparent_name`, `page_order` in chunk metadata; `VectorStoreIndex.from_vector_store()` + `index.insert_nodes(nodes)` pattern (not `vector_store.add`) (T3.3); registered in `worker/__main__.py` (T3.4); unit tests (T3.6); integration test seeds full hierarchy and asserts `text_search_tsv` column (T3.7). `HaituSettings` with all 8 fields wired (T4.1). Text restructuring via `_glm_restructure_mixin.py` on `GlmOcrProvider`; `RESTRUCTURE_PROMPT` in `src/shared/prompts.py` (re-exported from `worker/prompts.py`); `extract_page()` calls `restructure_page()` under 3-condition guard (T5.4, T5.6, T5.7 — T5.1–T5.3 done in prior commit). Student Dashboard: four GET endpoints at `/api/student/*`; deviation — `Depends(validate_csrf)` applied even on GET routes (T6.6, T6.7 — T6.1–T6.5 done prior). `get_by_owner()` added to `CoursePathNodeRepository` (not in plan spec but needed for parent node tree). `haisir-backend` `feature/rag` at `90b5601` (includes dep bumps + CI fixes on top of RAG commit `f179244`).

**Also complete (2026-06-15 — deploy T1.4, T3.5, T4.2, T5.5):** `haisir.smoke-test` LABEL added to `postgres-docker/Dockerfile` (T1.4). 14 env vars wired as bare `${VAR}` (no `:-` defaults — defaults live in Settings class) in `common/docker-compose.yml` worker service: EMBEDDING x4 (T3.5), HAITU x8 (T4.2), RESTRUCTURE x2 (T5.5). `haisir-deploy` `feature/rag` at `e57c56b`.

**Also complete (2026-06-15 — frontend T7.1):** `src/features/student/types/student.types.ts` created with 5 interfaces (`PlatformNodeCard`, `StudentDashboardResponse`, `StudentNode`, `StudentTopic`, `StudentTopicContent`); `src/features/student/index.ts` barrel export. `haisir-frontend` `feature/rag` at `d9532b7`.

> Snapshot baseline: haisir-backend `90b5601` (feature/rag, RAG + student dashboard + dep bumps, 2026-06-15), haisir-frontend `d9532b7` (feature/rag, T7.1 student types, 2026-06-15), haisir-deploy `e57c56b` (feature/rag, all RAG env vars wired, 2026-06-15).
> Next session: `git diff 90b5601..HEAD` in haisir-backend, `git diff d9532b7..HEAD` in haisir-frontend, `git diff e57c56b..HEAD` in haisir-deploy.

**Also complete (2026-06-16 — G3 fix + V33 + G7 frontend + G10 tests + gate verification):** RAG drain loop fully unblocked: `rag_outbox_loop.py` gained `_LmStudioEmbedding` adapter (openai SDK, parses `lmstudio://model@host:port/path` spec — `OllamaEmbedding` uses Ollama API format incompatible with LM Studio); V33 migration added `text_search_tsv TSVECTOR` + `fn_chunks_tsv_update()` BEFORE INSERT/UPDATE trigger + GIN index to `data_topic_content_chunks` (V32 shim omitted it). Post-fix: 10 outbox rows → `status='done'`, 27 chunks embedded. G5 text restructuring verified with `q-ocr.jpg` (Ratio Practice Exam — LaTeX fractions confirmed: `$28\frac{4}{5}\%$`, `$2\frac{1}{2}\text{ l}$` etc.). All gates verified: G1 ✓, G2 ✓, G3 ✓, G4 ✓, G5 ✓ (E2E via real image upload), G6 ✓, G7 ✓. Frontend T7.2–T7.12 complete (StudentHomePage + StudentCoursesPage + 7 components + 2 hooks + student-api.ts) with 11 unit test files at 100% coverage. `TestLmStudioEmbedding` + `TestBuildEmbedModel` + `pin_embedding_model_spec` fixture added to backend (G10 complete, `cb602a9`). **Gaps found and tracked in TASKS.md G8–G11:** student `GET /api/student/nodes` returns flat root nodes only — `NodeTreeSidebar` can't show hierarchy (G8 critical); `topic_count=0` always hardcoded (G9 medium); manual E2E walkthrough of S-nav with real data still needed (G11).

**Also complete (2026-06-16 — G8 backend + G9 backend):** `GET /api/student/nodes` now returns a fully nested `PlatformNodeCard` tree: `get_all_platform_nodes_visible(viewer_sub)` fetches all `owner_type='platform'` nodes across categories; `_build_node_tree()` (extracted as a module-level utility from `CoursePathNodeService`) assembles them. `PlatformNodeCard` schema gains `children: list[PlatformNodeCard]` (recursive self-reference via `model_rebuild()`). `topic_count` initially wired via flat GROUP BY. T8.1–T8.7 and T9.1–T9.3 complete.

**Also complete (2026-06-17 — G8 gate + G9 fix + G11 manual sign-off):** NodeTreeSidebar updated in frontend (`31062ab`) to consume recursive `children` — expandable grade ▶ → subject ▶ → course hierarchy confirmed in browser (G8 ✓). Backend `get_topic_counts_for_nodes` upgraded to recursive CTE (subtree sum via `WITH RECURSIVE`) so grade/subject parent nodes aggregate live topic counts from all descendants (`73607b4`, guard fix `2686279`); verified: Grade 5 = 6 topics, Grade 6 = 1 topic, Discover Canada = 0 (no live topics) (G9 ✓). Manual walkthrough (G11): student expands tree to Maths → Arithmetic → selects "Ratio" topic, LaTeX exam content renders correctly in ContentViewer (T11.2 ✓); Home Study shows placeholder with no parent link (T11.3 ✓). All G8–G11 gates closed.

> Snapshot baseline: haisir-backend `fc2eeb2` (feature/rag, live Ollama verification fixes: MockLLM + asyncio marks, 2026-06-20), haisir-frontend `7fc8811` (feature/rag, chore-only, 2026-06-19), haisir-deploy `59e42f3` (feature/rag, hAITU APISIX route + backend HAITU/EMBEDDING env vars, 2026-06-19).
> Next session: `git diff fc2eeb2..HEAD` in haisir-backend, `git diff 7fc8811..HEAD` in haisir-frontend, `git diff 59e42f3..HEAD` in haisir-deploy.

**Also complete (2026-06-24 — current-state snapshot, Phase 3 sign-off SSE contract):** All three sibling repos advanced since the 2026-06-20 snapshot; the only spec-level change is the hAITU topic-doubt endpoint's move from single-shot JSON to **SSE streaming** (captured in the Phase 3 section above). Backend `6ec91ab`: `POST /api/haitu/topic-doubt` now returns `text/event-stream` (`{"token":…}` → `{"escalation_ready":…}` → `{"done":true}`, 15 s `: ping` keepalives, `request.is_disconnected()` cancellation, DB session closed before streaming; 403/429 returned as HTTP errors before the stream starts); streaming Stage-4 path uses a single QA-mirroring prompt bypassing `CompactAndRefine` (non-streaming `answer()` retains it). Plus hAITU service refactor (cognitive-complexity reduction, DDD-boundary enforcement, re-raise `CancelledError`) and torch→CPU-only for CI. Frontend `47e4ec2`: `useHaituDoubt` consumes the SSE stream via `ReadableStream`/`TextDecoder` with resend-on-failure; `HaituDoubtPanel` rework + SonarQube new-code fixes; E2E CI image switched to Playwright host Chromium. Deploy `3178451`: `19-api-haitu.json` — send/read timeout 360 s → **600 s** (gateway is the higher ceiling over the 360 s `HAITU__LLM_REQUEST_TIMEOUT` default), route priority 20 (beats api-write 10), `proxy-buffering` disabled (required for SSE); `03-secured-api.json` gains Coraza id:199110 — targeted SQLi target-exclusion (rules 942130/942131/942340/942380/942400/942410) on `POST /api/haitu/*` chat-body ARGS (`json.*`) only, full inspection retained elsewhere; APISIX upgraded to 3.17.0-ubuntu, SonarQube DB → PostgreSQL 18. **No schema or migration changes** this cycle. `current/` spec files (api_contracts, ui_flows, schema) and `snapshot_shas.md` updated to the new baseline.

> Snapshot baseline: haisir-backend `d1564b0` (feature/rag + G0.3 — inline-ML deps removed, hAITU reranker stubbed to no-op passthrough, 2026-06-25), haisir-frontend `47e4ec2` (feature/rag, hAITU SSE consumer + SonarQube fixes, 2026-06-24), haisir-deploy `3178451` (feature/rag, hAITU SSE APISIX route + proxy-buffering + SQLi target-exclusion, 2026-06-24).
> Next session: `git diff d1564b0..HEAD` in haisir-backend, `git diff 47e4ec2..HEAD` in haisir-frontend, `git diff 3178451..HEAD` in haisir-deploy.

**Also complete (2026-06-26 — G1: Doubt persistence + hAITU thread):** V35 Alembic migration adds two new tables: `doubts` (UUID PK, `student_sub` TEXT, `topic_id`/`course_path_node_id` UUID FK nullable, `title` TEXT, `status` VARCHAR(20) CHECK 6-value enum default `'new'`, `escalated_to`, `haitu_attempted` BOOLEAN, `auto_close_at` TIMESTAMPTZ +7 days, `resolved_at`, `created_at`/`updated_at`; partial index on `auto_close_at WHERE status != 'resolved'`) and `doubt_messages` (UUID PK, `doubt_id` FK→doubts CASCADE, `sender_type` VARCHAR(10) CHECK 4-value enum, `content` TEXT, `created_at`). `Doubt`, `DoubtMessage`, `DoubtSummary` (non-mapped read-aggregate with `topic_name` + `last_activity_at`) domain models added; `DoubtRepository` + `DoubtMessageRepository` + `DoubtService` (find-or-create, message writers, finalize_ai_response) added. Three new student doubt routes under `/api/students/me/doubts` (list — no CSRF; get thread — no CSRF; post follow-up — CSRF required); all require `X-Current-Role: student`. `POST /api/haitu/topic-doubt` updated: creates/upserts a `Doubt` row + student message in the validation phase (post rate-limit, no orphan on 429); emits `event: doubt_id` SSE frame first; fire-and-forget background task persists full AI reply after stream ends (fresh session, tolerates early disconnect). Frontend: new `src/features/doubts/` feature module — `doubtApi` client, `DoubtSummary`/`DoubtMessage`/`DoubtThread`/`DoubtStatus` types, `DoubtInboxPage` (`/doubts`, S08) with status chips + relative timestamps + link-to-thread, `DoubtThreadPage` (`/doubts/[id]`, S09) with ordered message bubbles + follow-up textarea; student header gains "My Doubts" nav link; `HaituDoubtPanel` shows "View thread" link once `doubt_id` SSE arrives and preloads existing open thread on panel re-open. Backend integration tests in `tests/integration/phase4/test_g1_2_haitu_persistence.py` cover T1.2.3 (no-orphan-on-429, no-duplicate-on-retry) and T1.2.4 (disconnect/partial-text persistence). Deploy: Tailscale ACL only (`tag:in-dev2`) — no APISIX route changes.

**Also complete (2026-06-26 — G1 bug fixes):** Backend: `DoubtSummary` non-mapped read-aggregate added to `domain/models/doubt.py` with `topic_name: str` and `last_activity_at: datetime` fields (populated by enriched repository JOIN + correlated-subquery); `DoubtThread.doubt` changed from `Doubt` to `DoubtSummary`; `DoubtRead` Pydantic schema gains `topic_name` and `last_activity_at` fields (already reflected in G1 API contract entry above). Frontend: QueryClient crash fixed (doubts routes now have a `DoubtsProviders` layout wrapper with `QueryClientProvider`); `doubt-api.ts` adds a `DoubtBackendDTO`→`Doubt` mapping layer (`mapDoubt`/`mapThread`) so the DTO shape is decoupled from the frontend type; `DoubtListResponse` internal type aligned to flat array; `Number.isNaN` fix for timestamp validation; inbox row layout revised to flexbox with `rowMeta` column.

> Snapshot baseline: haisir-backend `1b0404c` (G1 bug fix — DoubtSummary + topic_name/last_activity_at, 2026-06-26), haisir-frontend `a31e6b3` (G1 bug fix — QueryClient crash + DTO mapping + NaN timestamp, 2026-06-26), haisir-deploy `8aa867b` (Tailscale ACL update only, 2026-06-26).
> Next session: `git diff 1b0404c..HEAD` in haisir-backend, `git diff a31e6b3..HEAD` in haisir-frontend, `git diff 8aa867b..HEAD` in haisir-deploy.

**Also complete (2026-06-25 — backend G0.3 + T0.7, commit `d1564b0`):** Inline-ML dependencies removed from the backend: `sentence-transformers` and `torch` dropped from `pyproject.toml`, and the uv torch-CPU pin + `pytorch-cpu` index removed — shrinking the lock footprint by ~2 GB of CUDA wheels. `HaituService._stage3_rerank()` is now a no-op passthrough: the inline `SentenceTransformerRerank` cross-encoder is gone; `rerank_model` is retained as a documented future-hook for an external rerank API (a non-empty value logs a warning and returns nodes unordered, no reranking). No schema, endpoint-contract, or UI changes — the hAITU retrieval pipeline (`POST /api/haitu/topic-doubt`) keeps its 4-stage shape; only Stage 3 behaviour changed. T0.7 adds `scripts/check_except_syntax.py`, a CI grep guard against Python-2 `except X, Y` syntax; except-tuples in `parent.py` and `worker/__main__.py` parenthesized to comply. Snapshot baseline advanced to backend `d1564b0` (2026-06-25); frontend `47e4ec2` and deploy `3178451` unchanged.

**Also complete (2026-06-20 — backend Phase 3 verification fixes, commit `fc2eeb2`):** Two fixes required to run the Ollama-gated integration suite with live models. `HaituService._stage2_retrieve()` now passes `llm=MockLLM()` to `QueryFusionRetriever`, preventing LlamaIndex from resolving `Settings.llm` to the default OpenAI model (`llama_index.llms.openai`), which is not a project dependency. The four Ollama-gated integration test files switched from `@pytest.mark.anyio` to the project-standard `@pytest.mark.asyncio`, resolving a `pytest-asyncio`/`anyio` fixture scope conflict. Verified locally against a temporary pgvector Postgres container with `qwen3:14b` and `bge-m3` models: G10.2 (`tests/integration/phase3_db_only/`) = 8 passed, 0 skipped; G10.3 (`tests/integration/phase3_ollama_gated/`) = 6 passed, 0 skipped, summary line `Ollama-gated: 0 skipped, 4 passed`; full unit suite = 3537 passed, 22 skipped, 100% coverage. G10 automated gates now closed.

**Also complete (2026-06-19 — backend Phase 3 verification suite, commit `f55c40c`):** Full Phase 3 verification test suite landed. `tests/integration/phase3_db_only/` expanded with Ollama probe and aggregate-gate test. G10.1 (unit) and G10.3 (Ollama-gated) gates now asserted: Ollama-up → suite passes with skip-count line present; Ollama-down → gated tests skip with skip-count line present. T10.3.1–T10.3.4b already complete; T10.3.5 aggregate gate now marked done in TASKS.md. No new schema, API, or UI changes — test-only commits.

**Also complete (2026-06-19 — deploy T6.1 + T6.2, G6 complete):** hAITU APISIX route `common/routes/19-api-haitu.json` ships: `POST /api/haitu/*`, 360s send/read timeout, `limit-count` (20 req/min per IP → 429, separate from the in-process per-student/hour limiter), `limit-conn` (20 concurrent/IP → 503), `request-validation` (requires `Content-Type: application/json`), `secured-api` OIDC plugin. `HAITU__*` + `EMBEDDING__*` env vars wired into backend service in `common/docker-compose.yml` (T6.2). G6 fully complete.

**Also complete (2026-06-19 — backend integration test gates G1–G3, commit `17533c1`):** DB-only integration test suite shipped: `tests/integration/phase3_db_only/` with shared fixtures (`make_student_client`, `reset_haitu_rate_limiter`, `unique_student_sub`, `rolled_back_session`, `seed_3level_tree`), integration conftest V34 head guard, Ollama probe. Tests written and green: G1.1 (V34 UNIQUE violation + index), G2.1 (EnrollmentRepository CRUD), G2.2 (EnrollmentService enroll/drop/409/catalog), G2.3 (route CRUD cycle 200/201/409/204/404), G2 E2E (lifecycle), G3.1 (subtree CTE + enrolled-root queries), G3.2 (unenrolled → platform_nodes=[]; wrong node → 403). CI wiring included.

**Also complete (2026-06-18 — enrollment domain + HaituService stages 1–3):** V34 Alembic migration creates `student_enrollments` table (UUID PK, `student_sub TEXT`, `course_path_node_id UUID FK→course_path_nodes CASCADE`, `enrolled_at TIMESTAMPTZ`, `enrollment_source VARCHAR(20)`; UNIQUE on `(student_sub, course_path_node_id)`; index on `student_sub`). `StudentEnrollment` dataclass + `AbstractEnrollmentRepository` (5 abstract methods) + `AbstractTopicRepository.is_topic_in_enrolled_subtree` added. Domain exceptions `AlreadyEnrolledError` / `EnrollmentNotFoundError` added. `HaituRateLimiter` (in-process 20 calls/student/hour, asyncio.Lock, hourly bucket eviction). `HaituService` skeleton with `_stage1_rewrite` (LLM → JSON, safe fallback), `_stage2_retrieve` (QueryFusionRetriever, hybrid pgvector, topic_id filter), `_stage3_rerank` (passthrough or cross-encoder). Concrete `EnrollmentRepository`, `EnrollmentService`, and HTTP routes (T2.4, T2.7–T2.9) are still open. `_stage4_synthesize` + public `answer()` (T4.4) still open.

**Also complete (2026-06-18 — frontend enrollment + hAITU panel):** Browse Courses screen (`/enroll` → `BrowseCoursesPage`) with `CatalogCard` grid (Enroll/Drop buttons, Recommended badge, toast). "Browse Courses" nav link added to student header. `PlatformBoardSection` and `NodeTreeSidebar` gain empty states with "Browse Courses" CTAs. `ContentViewer` gains `topicId`/`enrollmentId` props and renders `HaituDoubtPanel` below content when a topic is selected. `HaituDoubtPanel` shows chat bubbles, 429 rate-limit error, disabled escalation button, and enrollment guard. New hooks: `useStudentCatalog` (fetch/enroll/drop), `useHaituDoubt` (message history, loading/error). New types: `CatalogNode`, `StudentEnrollment`, `HaituMessage`, `HaituDoubtResponse`. Backend enrollment + hAITU routes not yet wired — frontend API calls return 404 until T2.8/T2.9 and T5.4/T5.5 land.

**Also complete (2026-06-18 — frontend E2E Playwright suite + backend route wiring):** Frontend Playwright E2E suite shipped (commit `54e198c`, 2026-06-18): `playwright.config.ts` (webServer auto-starts dev on :3001, pins `NEXT_PUBLIC_BACKEND_URL=localhost:9080`), `tests/e2e/helpers/` (`auth.ts` mocked CSRF + `/api/users/me` + onboarding cookie + `currentRole` localStorage; `mock-api.ts` typed factories + `page.route()` for all student endpoints; `backend.ts` shared env-backed `BACKEND` constant), 16 specs across G3 content-filter (3), G7 browse-courses (4), G8 empty-state (5), G9 hAITU panel (4) — all green; Jenkinsfile E2E Tests stage (chromium install, `CI=true`, JUnit + HTML report, pinned backend URL); `knip.config.ts` playwright entry; gitignore `playwright-report/`/`test-results/`/`reports/`; `/commit-frontend` gate now runs the E2E suite as a peer to the 100% coverage check. **Correction to the 2026-06-18 frontend entry above:** backend enrollment routes (T2.8/T2.9) and the hAITU route (T5.4/T5.5) **are now wired** at backend `9379bb7` — the "frontend API calls return 404" note is obsolete. Endpoints live: `GET /api/student/catalog`, `POST /api/student/enrollments` (201/409/404), `DELETE /api/student/enrollments/{id}` (204/404), `POST /api/haitu/topic-doubt` (200/403/429, no DB writes). G3/G7/G8/G9 goal-level E2E items closed.

> Snapshot baseline: haisir-backend `9379bb7` (feature/rag, enrollment APIs + enrolled-only filter + hAITU stages 2–4 + bug fix, 2026-06-18), haisir-frontend `54e198c` (feature/rag, Playwright E2E suite G3/G7/G8/G9 + CI integration, 2026-06-18), haisir-deploy `e57c56b` (feature/rag, all RAG env vars wired, 2026-06-15).
> Next session: `git diff 9379bb7..HEAD` in haisir-backend, `git diff 54e198c..HEAD` in haisir-frontend, `git diff e57c56b..HEAD` in haisir-deploy.

**Not yet built:** Parent curriculum builder (adopt board subtree, create own nodes/topics, upload notes), parent link-code generation and redemption. Playwright E2E tests deferred across all phases (Playwright not installed).

## Completed Phases

### Phase 3 — Student Enrollment + hAITU Topic-Doubt ✓

**Completed:** 2026-06-24
**Commits:** haisir-backend `6ec91ab` (feature/rag), haisir-frontend `47e4ec2` (feature/rag), haisir-deploy `3178451` (feature/rag)
**Archived plan:** `Implementation_planning/archive/PLAN_Phase3-Enrollment-Haitu_2026-06-18.md`
**Walkthrough record:** `Implementation_planning/phase3_manual_walkthrough_record.md`

**What was done:**
- V34 Alembic migration: `student_enrollments` table (UUID PK, `student_sub` TEXT, `course_path_node_id` UUID FK→`course_path_nodes` CASCADE, `enrolled_at`, `enrollment_source`; UNIQUE on `(student_sub, course_path_node_id)`; index on `student_sub`).
- Enrollment domain layer: `StudentEnrollment` dataclass, infra table + imperative mapping, `AbstractEnrollmentRepository` (5 methods), concrete `EnrollmentRepository`; `AlreadyEnrolledError` / `EnrollmentNotFoundError` exceptions.
- `EnrollmentService` (enroll / drop / get_catalog) with `recommended` = case-insensitive match of catalog node **name** vs student profile **grade**.
- Three enrollment endpoints: `GET /api/student/catalog`, `POST /api/student/enrollments` (201/409/404), `DELETE /api/student/enrollments/{id}` (204/404); CSRF + `X-Current-Role: student` required.
- Enrolled-only content filter: `get_subtree_node_ids` (recursive CTE), `get_enrolled_root_nodes`, `is_topic_in_enrolled_subtree`; `StudentDashboardService` filters `platform_nodes` + enforces subtree access (403 for unenrolled node/topic; empty list for unenrolled dashboard).
- hAITU 4-stage retrieval pipeline: Stage 1 query rewrite + intent + safety (`HaituRewriteResult`); Stage 2 hybrid retrieval (`QueryFusionRetriever`, `relative_score`, `topic_id` filter, bge-m3 embed via shared `infrastructure.embedding` — LM Studio + Ollama adapters); Stage 3 optional rerank (passthrough when `HAITU__RERANK_MODEL=""`); Stage 4 synthesis (`CompactAndRefine` in `answer()`, single-prompt in streaming).
- `HaituRateLimiter` (in-process 20 calls/student/hour) + `HaituDoubtService` orchestrator (enrollment ownership + subtree + rate limit; stateless — no DB writes).
- `POST /api/haitu/topic-doubt` — **streamed as SSE** (`text/event-stream`): incremental `{"token":…}` frames, a `{"escalation_ready":…}` frame, a final `{"done":true}` frame, 15 s `: ping` keepalives, `request.is_disconnected()` cancellation, DB session closed before streaming; 403/429 returned as HTTP errors before the stream starts. Converted from single-shot JSON to fix gateway 504s on long RAG pipelines.
- APISIX route `19-api-haitu.json` (600 s send/read timeout — bumped from 360 s in deploy commit `3178451`; 360 s is the backend `HAITU__LLM_REQUEST_TIMEOUT` default, not the gateway timeout, `limit-count` 20/min/IP, `limit-conn` 20/IP, `request-validation`, `secured-api` OIDC) + `HAITU__*` / `EMBEDDING__*` env vars wired into the backend service.
- Frontend: Browse Courses screen (`/enroll` → `BrowseCoursesPage` + `CatalogCard` grid + persistent nav link), dashboard empty states with "Browse Courses" CTA, `HaituDoubtPanel` (chat bubbles, 429 rate-limit message, disabled escalation button, enrollment guard) below content; `useStudentCatalog` + `useHaituDoubt` hooks; SSE consumer via `ReadableStream`/`TextDecoder` with resend-on-failure.
- Frontend Playwright E2E suite: 16 specs across G3/G7/G8/G9 + CI integration (Jenkinsfile E2E stage, JUnit+HTML report); `/commit-frontend` gates on the suite.
- Backend verification: 12 goal-level integration/E2E tests — 8 DB-only (`tests/integration/phase3_db_only/`) + 4 Ollama-gated (`tests/integration/phase3_ollama_gated/`); shared fixtures module + Ollama probe + skip-count terminal-summary reporter; full unit suite 3537 passed, 22 skipped, 100% coverage.
- Manual 7-step ROOT Acceptance Test walkthrough: all steps pass (record in `Implementation_planning/phase3_manual_walkthrough_record.md`); spec updated for the SSE contract change.

**Deviations:**
- hAITU `topic-doubt` converted from single-shot JSON to **SSE streaming** mid-phase to solve gateway 504s on long RAG pipelines; the streaming Stage-4 path bypasses `CompactAndRefine` (uses a single prompt mirroring the QA template) — non-streaming `answer()` retains `CompactAndRefine`. Spec updated in `vision/requirements/08_haitu_ai_layer.md` (§4, §3.1, BR-AI-002, BR-AI-009); design + trade-offs in `decisions.md` 2026-06-24.
- Ollama-gated tests skip-with-reported-count when the LLM is absent (never silently dropped); a `pytest_terminal_summary` line distinguishes a genuinely-green run from an all-skipped run.
- Stage 3 reranker is passthrough when `HAITU__RERANK_MODEL=""` (no cross-encoder configured) — design gap deferred to a later phase.
- Admin feature uses `@tanstack/react-query` (deviation from CLAUDE.md "custom hooks with useState/useEffect only"); pre-existing Phase 1 admin scope, not Phase 3 — deferred cleanup.
- Student profile grade has no UI screen (onboarding is CTA-only); set via `POST /api/students/me/profile`. `recommended=false` across the catalog until grade is set — acceptable for Phase 3.

**Note:** All work on `feature/rag` branch — not yet merged to main in any sibling repo.

---

### Phase 2 — RAG Infrastructure + Text Restructuring + Student Dashboard ✓

**Completed:** 2026-06-17
**Commits:** haisir-backend `2686279` (feature/rag), haisir-frontend `31062ab` (feature/rag), haisir-deploy `e57c56b` (feature/rag)
**Archived plan:** `Implementation_planning/archive/PLAN_Phase2-RAG-student_2026-06-17.md`

**What was done:**
- pgvector 0.8.2 added to Postgres via Wolfi multi-stage Dockerfile; wired in common and dev compose
- V31 enables `vector` extension; V32 shims `data_topic_content_chunks (embedding vector(1024))`; V33 adds `text_search_tsv` + trigger + GIN index for hybrid search
- `EmbeddingSettings` (bge-m3, dim=1024) + LlamaIndex deps wired in backend and deploy
- `rag_outbox_loop.py`: drains outbox → PGVectorStore with hybrid search + HNSW; 3-level hierarchy metadata stored per chunk; `_LmStudioEmbedding` adapter added for LM Studio API compatibility
- `HaituSettings` (8 fields) pre-wired for next cycle's hAITU endpoint
- Text restructuring: `GlmRestructureMixin.restructure_page()` on `GlmOcrProvider`; called in `extract_page()` under 3-condition guard
- Student dashboard backend: 4 GET endpoints at `/api/student/`; node tree returns fully nested hierarchy via `_build_node_tree()`; `topic_count` computed via recursive CTE subtree sum
- Student dashboard frontend: `StudentHomePage` + `StudentCoursesPage` (expandable `NodeTreeSidebar` + `TopicListPanel` + `ContentViewer`); 2 hooks; 11 unit test files at 100% coverage
- G8/G9 gap fixes: flat root-only tree replaced with recursive children; hardcoded `topic_count=0` replaced with recursive CTE
- G11 manual walkthrough: LaTeX content renders in ContentViewer; Home Study placeholder confirmed

**Deviations:**
- `GET /api/student/nodes` initially returned flat root nodes only (G8 found post-code-review); fixed mid-cycle
- `topic_count` initially used flat GROUP BY (G9); upgraded to recursive CTE
- Playwright E2E tests deferred (Playwright not installed across all phases)

**Note:** All work on `feature/rag` branch — not yet merged to main in any sibling repo.

---

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

