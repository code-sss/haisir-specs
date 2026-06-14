# Current Schema Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | 5925a0ce (hotfix v2026.3.5 — essay fields wired in create/update routes + SonarQube, 2026-06-13) |
| haisir-frontend | ad0c923f (hotfix v2026.3.5 — released-grade results view + essay authoring UX, 2026-06-13) |
| haisir-deploy | f7d63b57 (postgres-docker pgvector image + tailscale fix, 2026-06-13) |

> Next session: run `git diff 5925a0ce..HEAD` in haisir-backend, `git diff ad0c923f..HEAD` in haisir-frontend, and `git diff f7d63b57..HEAD` in haisir-deploy to see only what changed since this snapshot.

---

## Applied Migrations (as of snapshot)

| Migration | What it does |
|---|---|
| V23_visibility_enforcement | Alters `course_path_nodes.owner_id` and `topics.owner_id` from Integer → String; adds `exam_templates.owner_id` (String, nullable); adds `parent_child_links.revoked_at` (DateTime TZ, nullable) |
| V24_add_visibility_indexes | Adds covering index `ix_parent_child_links_child_sub_revoked` on `(child_sub, revoked_at) INCLUDE (parent_sub)` for BR-DATA-003 subquery performance |
| V25_expand_nodetype_enum | Adds 6 new values to the `nodetype` PostgreSQL enum: `chapter`, `module`, `section`, `unit`, `week`, `skill`. Uses `ALTER TYPE nodetype ADD VALUE IF NOT EXISTS` (run outside transaction). No downgrade path — PostgreSQL does not support removing enum values. |
| V26_extraction_tables | Installs `touch_updated_at()` trigger function. Adds `source_extraction_job_id` (UUID nullable) to `topic_contents`. Creates 6 new tables: `extraction_jobs`, `extraction_job_pages`, `extraction_job_audit`, `rag_indexing_outbox`, `worker_heartbeats`, `parent_quota_counters`, with all indexes. |
| V27_add_new_question_types | Adds three values to the `questiontype` PostgreSQL enum (`matching`, `one_word_response`, `problem_solving`) via `ALTER TYPE … ADD VALUE IF NOT EXISTS` in AUTOCOMMIT block. Adds four columns: `questions.essay_subtype VARCHAR(10) NULL`, `questions.working_required BOOLEAN NOT NULL DEFAULT false`, `exam_session_questions.working_text TEXT NULL`, `exam_session_questions.shuffle_seed INTEGER NULL`. No downgrade path for enum values. |
| V28_essay_subtype_constraint_and_penalty_matching | Widens `questions.essay_subtype` from `VARCHAR(10)` → `VARCHAR(50)`. Adds CHECK constraint `ck_questions_essay_subtype` enforcing valid values: `analytical`, `critical`, `extended`, `narrative`, `reflective`, `short`. Adds `questions.penalty_matching BOOLEAN NOT NULL DEFAULT false`. |
| V29_essay_grading | Adds `rubric` (JSONB nullable), `model_answer` (TEXT nullable), `auto_grade_essay` (BOOLEAN NOT NULL DEFAULT true) to `questions`. Adds `essay_grading_mode` (VARCHAR NOT NULL DEFAULT 'auto_release', CHECK IN ('auto_release','review_first')) to `exam_templates`. Adds 9 grading-state columns to `exam_session_questions` (`grading_status`, `ai_score`, `ai_feedback`, `ai_rationale`, `grader_confidence`, `graded_by`, `graded_at`, `override_score`, `override_feedback`). Creates `essay_grading_jobs` table with partial index on queued status. |
| V30_grading_pending_status | Adds `grading_pending` to the `examstatus` PostgreSQL enum via `ALTER TYPE … ADD VALUE IF NOT EXISTS` (run outside transaction). No downgrade path — PostgreSQL does not support removing enum values. |

---

## user_metadata
- `idp_sub` (String, PK) — Keycloak subject claim; primary identity key
- `onboarding_completed_at` (DateTime TZ, nullable) — timestamp when onboarding was marked complete

## student_profiles
- `id` (UUID, PK)
- `idp_sub` (String, UNIQUE) — links to user_metadata
- `first_name` (String)
- `last_name` (String)
- `phone` (String, nullable)
- `avatar_url` (String, nullable)
- `grade` (String, nullable)
- `subjects` (JSON, default []) — array of subject tags

## teacher_profiles
> Outside current target increment (instructor persona deferred). Retained as-is.

- `id` (UUID, PK)
- `idp_sub` (String, UNIQUE)
- `first_name`, `last_name` (String)
- `phone` (String, nullable)

## parent_profiles
- `id` (UUID, PK)
- `idp_sub` (String, UNIQUE)
- `first_name`, `last_name` (String)
- `phone` (String, nullable)

## parent_link_codes
- `id` (UUID, PK)
- `code` (String, UNIQUE)
- `child_sub` (String) — child's idp_sub
- `created_at` (DateTime TZ)
- `expires_at` (DateTime TZ)
- `is_used` (Boolean, default false)

> Note: no endpoint yet to generate new codes from the student side; table is write-orphaned until /join-school is built.

## parent_child_links
- `id` (UUID, PK)
- `parent_sub` (String) — parent's idp_sub
- `child_sub` (String) — child's idp_sub
- `created_at` (DateTime TZ)
- `revoked_at` (DateTime TZ, nullable) — NULL = active link; set to revoke (future endpoint — Phase 1c+)
- UNIQUE constraint on (parent_sub, child_sub)

> **Column name note:** Physical columns are `parent_sub` / `child_sub`. The data-model spec (target/requirements/01_data_model.md) uses the logical aliases `parent_idp_sub` / `child_idp_sub`. Schema is sacred — the physical names will not change; the spec alias is documenting intent only.

## class_invite_codes
> Outside current target increment (class/institution flow deferred). Retained as-is.

- `id` (UUID, PK)
- `code` (String, UNIQUE)
- `course_path_node_id` (UUID, FK → course_path_nodes)
- `created_at` (DateTime TZ)
- `expires_at` (DateTime TZ, nullable)

## categories
- `id` (UUID, PK)
- `name` (String)
- `path_type` (Enum: structured | flexible) — defaults to `structured` on create
- `description` (String, nullable)

## course_path_nodes
- `id` (UUID, PK)
- `name` (String)
- `node_type` (Enum: grade | subject | course | chapter | module | section | unit | week | skill) — 9 values as of V25. `grade` and `subject` are reserved types (🔒); `course`, `chapter`, `module`, `section`, `unit`, `week`, `skill` are regular. Creation enforces: (A) ancestor-type exclusion — new node type must not appear in any ancestor; (B) sibling-type consistency — all platform-owned siblings share the same type. Both violations return 409.
- `category_id` (UUID, FK → categories)
- `parent_id` (UUID, FK → course_path_nodes, nullable) — self-referential tree
- `order` (Integer, nullable)
- `owner_type` (String, default "platform") — discriminator: "platform" or "parent"; enforced via `OwnerType(StrEnum)` in domain layer
- `owner_id` (String, nullable) — parent's `idp_sub` for parent-owned nodes, NULL for platform nodes

> **Visibility enforced (as of V23 / commit aa5ddf7):** BR-DATA-003 and BR-SEC-005 are fully enforced on all GET endpoints. Students see platform nodes + parent-owned nodes where an active (non-revoked) `parent_child_links` record exists. Admins see platform-only nodes.

## topics
- `id` (UUID, PK)
- `title` (String)
- `course_path_node_id` (UUID, FK → course_path_nodes)
- `order` (Integer, nullable)
- `status` (String, default "live") — **exposed in `TopicRead` responses** (column pre-existed; exposed as of commit 78a5490); required in `TopicCreate` (no default at API boundary — caller must pass `"draft"` or `"live"`).
- `owner_type` (String, default "platform")
- `owner_id` (String, nullable) — parent's `idp_sub` for parent-owned topics, NULL for platform topics

> **Visibility enforced (as of V23 / commit aa5ddf7):** same as course_path_nodes — BR-DATA-003 / BR-SEC-005 enforced on all GET endpoints.

## topic_contents
- `id` (UUID, PK)
- `topic_id` (UUID, FK → topics)
- `content_type` (Enum: video | pdf | text | question | question_answer)
- `title` (String)
- `url` (String, nullable)
- `text` (String, nullable)
- `order` (Integer)
- `description` (String, nullable)
- `source_extraction_job_id` (UUID, nullable) — provenance link to the extraction job that created this row; set by the worker finalize step; **never cleared by PATCH** (BR-EXT-023a)
- `provenance` — **transient, not a DB column**; populated by the repository via `LEFT JOIN extraction_job_audit ON source_extraction_job_id = job_id`; exposed in `GET /api/topics-contents/{topic_id}` response as `{ source_filename: str, page_no: int } | null`

## questions
- `id` (UUID, PK)
- `question_text` (String)
- `question_type` (Enum: single_choice | multiple_choice | true_false | fill_in_the_blank | essay | one_word_response | matching | problem_solving) — 8 values as of V27
- `options` (JSONB) — array of `{id, text, image_url}` for most types; for `matching`, each item also carries `side: "left" | "right"`
- `correct_answers` (JSONB) — array of option IDs for choice types; for `matching`, array of `"<left_id>:<right_id>"` pair strings (e.g. `["L1:R2", "L2:R1"]`)
- `explanation` (String, nullable)
- `difficulty` (Enum: easy | medium | hard)
- `tags` (JSONB, nullable)
- `image_url` (String, nullable)
- `essay_subtype` (VARCHAR(50), nullable) — `essay` questions only; valid values: `analytical`, `critical`, `extended`, `narrative`, `reflective`, `short`; rendering hint only, no grading impact (V27+V28)
- `working_required` (BOOLEAN, default false) — `problem_solving` only; when true, UI renders a free-text working area (V27)
- `penalty_matching` (BOOLEAN, default false) — `matching` only; when true, wrong pairings reduce score: `max(0, (correct − wrong) / total) × points` (V28)
- `rubric` (JSONB, nullable) — `essay` questions only; custom grading rubric: `{ scale_max: 3|4|5, criteria: [{name, weight, descriptors}] }`; 3–6 criteria; weights must sum to 1.0 (±0.01 tolerance); validated by Pydantic on create/update (V29)
- `model_answer` (TEXT, nullable) — `essay` questions only; hint text passed to the LLM as grading context; returned to students via the review endpoint when `grading_status` is `released`, `finalized`, or `overridden` (V29; visibility gated in hotfix v2026.3.5)
- `auto_grade_essay` (BOOLEAN, NOT NULL, default true) — `essay` questions only; when false, the question is skipped by the AI grading pipeline on session submit (V29)

## paragraph_questions
- `id` (UUID, PK)
- `content` (String) — paragraph text
- `title` (String)
- `question_ids` (ARRAY UUID)
- `paragraph_type` (Enum: reading_comprehension | case_study | data_interpretation)
- `tags` (JSONB, nullable)
- `difficulty` (Enum, nullable)

## answers
> Orphaned from an earlier iteration. No active write path. Retained as-is.

- `id` (UUID, PK)
- `user_id` (UUID)
- `session_id` (UUID)
- `question_id` (UUID, FK → questions)
- `selected_options` (ARRAY String, nullable)
- `text_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `submitted_at` (DateTime TZ)

## assessments
> Deprecated. Superseded by exam_templates (purpose='quiz'). Routes and table retained as-is.

- `id` (UUID, PK)
- `topic_id` (UUID, FK → topics)
- `question_ids` (ARRAY UUID)
- `paragraph_question_ids` (ARRAY UUID, nullable)
- `title` (String)

## assessment_attempts
> Deprecated. Retained as-is.

- `id` (UUID, PK)
- `user_id` (UUID)
- `assessment_id` (UUID, FK → assessments)
- `started_at`, `finished_at` (DateTime TZ)
- `score` (Float, nullable)
- `status` (Enum: pending | ongoing | completed | failed)

## assessment_answers
> Deprecated. Retained as-is.

- `id` (UUID, PK)
- `attempt_id` (UUID, FK → assessment_attempts)
- `question_id` (UUID, FK → questions)
- `selected_options` (ARRAY String, nullable)
- `text_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `submitted_at` (DateTime TZ)

## exam_templates
- `id` (UUID, PK)
- `course_path_node_id` (UUID, FK → course_path_nodes)
- `title` (String)
- `description` (String, nullable)
- `mode` (Enum: static | dynamic | custom)
- `ruleset` (JSON, nullable) — dynamic exam config: total_questions, difficulty_mix, topics, tags
- `duration_minutes` (Integer, nullable)
- `passing_score` (Float, nullable) — threshold 0.0–1.0
- `created_by` (UUID) — creator's UUID
- `is_active` (Boolean, default true)
- `owner_type` (String, default "platform")
- `owner_id` (String, nullable) — added via V23 migration; parent's `idp_sub` for parent-owned templates, NULL for platform
- `organization_id` (Integer, nullable)
- `purpose` (String, default "exam") — "exam" or "quiz"
- `essay_grading_mode` (VARCHAR, NOT NULL, default `'auto_release'`) — CHECK IN ('auto_release', 'review_first'); `auto_release`: AI score released to student immediately after grading; `review_first`: score held in `ai_graded` state until exam owner confirms or overrides (V29)

> **Visibility enforced (as of V23 / commit aa5ddf7):** BR-DATA-003 / BR-SEC-005 enforced on all GET endpoints. Students see platform + linked-parent exam templates; admins see platform-only; instructors see all.

## exam_template_questions
- `id` (UUID, PK)
- `exam_template_id` (UUID, FK → exam_templates)
- `question_id` (UUID, FK → questions)
- `order` (Integer)
- `points` (Integer)
- `paragraph_question_id` (UUID, FK → paragraph_questions, nullable)

## exam_sessions
- `id` (UUID, PK)
- `user_id` (UUID) — student's UUID
- `exam_template_id` (UUID, FK → exam_templates, nullable)
- `course_path_node_id` (UUID, FK → course_path_nodes)
- `mode` (Enum: static | dynamic | custom)
- `ruleset` (JSON, nullable)
- `created_at`, `started_at`, `finished_at` (DateTime TZ, nullable)
- `score` (Float, nullable)
- `status` (Enum: pending | ongoing | completed | failed | grading_pending) — `grading_pending` added via V30; set when submit enqueues essay grading jobs; transitions to `completed` once all jobs finish (worker calls `_maybe_autocomplete_session`)

## exam_session_questions
- `id` (UUID, PK)
- `exam_session_id` (UUID, FK → exam_sessions)
- `question_id` (UUID, FK → questions)
- `order` (Integer)
- `points` (Integer)
- `user_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `earned_points` (Float, nullable)
- `working_text` (TEXT, nullable) — `problem_solving` only; student's working captured at submit time, unscored this phase (V27)
- `shuffle_seed` (INTEGER, nullable) — `matching` only; generated at session creation via `secrets.randbelow(2**31)`; frontend uses this to replicate the same Fisher-Yates shuffle for right-column ordering (V27)
- `grading_status` (VARCHAR, NOT NULL, default `'pending'`) — CHECK IN ('pending','ai_graded','released','finalized','overridden','disputed','error'); `essay` questions only; non-essay questions remain `'pending'` throughout (V29)
- `ai_score` (FLOAT, nullable) — worker-computed: `sum(level / scale_max × weight) × points`; set when status reaches `ai_graded` or `released` (V29)
- `ai_feedback` (TEXT, nullable) — student-facing feedback text from LLM; visible when `grading_status in ('released','finalized','overridden')` (V29)
- `ai_rationale` (JSONB, nullable) — full LLM output including per-criterion breakdown; exposed only to exam owner (parent who owns the template, or admin) (V29)
- `grader_confidence` (FLOAT, nullable) — LLM self-reported confidence score [0,1] (V29)
- `graded_by` (VARCHAR, nullable) — model spec string (worker) or user sub (manual override) (V29)
- `graded_at` (TIMESTAMP TZ, nullable) — when `grading_status` last changed to a terminal state (V29)
- `override_score` (FLOAT, nullable) — manual score set by exam owner via `PATCH .../grade` (V29)
- `override_feedback` (TEXT, nullable) — manual feedback set by exam owner via `PATCH .../grade` (V29)

## extraction_jobs
- `id` (UUID, PK)
- `topic_id` (UUID) — target topic
- `created_by` (String) — creator's `idp_sub`
- `expected_owner_type` (String) — snapshot of topic's owner_type at upload time; used by worker finalize to detect ownership race
- `job_type` (String, default `'contents'`) — always `'contents'` for now
- `source_type` (String) — `'pdf'` or `'image'`
- `source_filename` (String)
- `source_size_bytes` (BigInteger)
- `source_path` (String) — path relative to `STORAGE_ROOT`
- `source_sha256` (CHAR 64) — SHA-256 of uploaded file bytes
- `status` (String) — `pending` | `extracting` | `done` | `upload_failed` | `extraction_failed` | `cancelled`
- `pages_total` (Integer, nullable) — set once PDF page count is known
- `pages_completed` (Integer, default 0)
- `cancel_requested` (Boolean, default false) — soft cancel flag read by worker between pages
- `error_message` (Text, nullable)
- `idempotency_key` (UUID) — client-supplied dedup key
- `running_cost_usd` (Numeric 10,4, default 0)
- `created_at`, `updated_at` (DateTime TZ) — `updated_at` auto-maintained via `touch_updated_at()` trigger
- `started_at`, `finished_at`, `purge_at` (DateTime TZ, nullable)
- `locked_at` (DateTime TZ, nullable), `locked_by` (String, nullable) — worker row-lock state

Indexes: `ix_extraction_jobs_queue (status, created_at)`, `ix_extraction_jobs_topic (topic_id, status)`, `ix_extraction_jobs_purge (purge_at) WHERE purge_at IS NOT NULL`, UNIQUE `ux_extraction_jobs_idempotency (created_by, idempotency_key)`, UNIQUE `ux_extraction_jobs_dedup (topic_id, source_sha256) WHERE status NOT IN ('cancelled','upload_failed')`

## extraction_job_pages
> Ephemeral staging table — rows deleted atomically when job finalises.

- `job_id` (UUID, PK composite) — FK → extraction_jobs
- `page_no` (Integer, PK composite)
- `markdown_text` (Text) — extracted page content
- `sha256` (CHAR 64) — hash of markdown_text
- `extracted_at` (DateTime TZ)

## extraction_job_audit
> Permanent provenance record — never purged.

- `job_id` (UUID, PK)
- `topic_id` (UUID)
- `idp_sub` (String) — who submitted
- `source_filename` (String)
- `source_sha256` (CHAR 64)
- `source_type` (String)
- `job_type` (String)
- `model_spec_used` (String) — value of `EXTRACTION_MODEL_SPEC` env var at job time
- `pages_extracted` (Integer)
- `cost_usd` (Numeric 10,4)
- `final_status` (String)
- `started_at`, `finished_at` (DateTime TZ)

Indexes: `ix_extraction_job_audit_topic (topic_id)`, `ix_extraction_job_audit_user_day (idp_sub, finished_at DESC)`

## rag_indexing_outbox
> Written by worker finalize step; drained by haiguru (embedding handoff — UNRESOLVED).

- `content_id` (UUID, PK) — FK → topic_contents
- `status` (String) — `pending` | `locked` | `done` | `failed`
- `retry_count` (Integer, default 0)
- `last_error` (Text, nullable)
- `created_at`, `updated_at` (DateTime TZ)
- `locked_at` (DateTime TZ, nullable), `locked_by` (String, nullable)

Index: `ix_rag_outbox_pending (status, created_at) WHERE status = 'pending'`

## worker_heartbeats
- `worker_id` (String, PK) — unique worker instance identifier
- `started_at` (DateTime TZ)
- `last_seen` (DateTime TZ) — updated every 10 s by the worker loop
- `job_id` (UUID, nullable) — current job being processed (NULL = idle)

## parent_quota_counters
- `idp_sub` (String, PK) — parent's identity key
- `concurrent_jobs` (Integer, default 0) — active extraction jobs count
- `daily_jobs` (Integer, default 0) — jobs started today
- `daily_window_start` (DateTime TZ)
- `updated_at` (DateTime TZ)

## essay_grading_jobs
- `id` (UUID, PK)
- `exam_session_question_id` (UUID, FK → exam_session_questions.id, NOT NULL)
- `status` (VARCHAR, default `'queued'`) — `queued` | `processing` | `done` | `error`
- `attempts` (INTEGER, default 0)
- `last_error` (TEXT, nullable)
- `grading_model` (VARCHAR, nullable) — model spec string recorded by worker on pick-up
- `locked_at` (TIMESTAMP TZ, nullable) — set when worker claims the row via `FOR UPDATE SKIP LOCKED`
- `locked_by` (VARCHAR, nullable) — worker hostname
- `created_at` (TIMESTAMP TZ, NOT NULL, default `NOW()`)
- `updated_at` (TIMESTAMP TZ, auto-maintained via `touch_updated_at()` trigger)

Indexes: `ix_essay_grading_jobs_queue (status, created_at) WHERE status='queued'` (partial), `ix_essay_grading_jobs_session_question (exam_session_question_id)`

---

## Read-only projections (not DB tables)

### BoardStatRow
> In-memory projection returned by `GET /api/admin/board-stats`. Not a table.

- `id` (UUID) — category id
- `name` (String) — category name
- `live_topics` (int) — count of platform-owned topics with `status = 'live'`
- `draft_topics` (int) — count of platform-owned topics with `status = 'draft'`
- `total_topics` (int) — `live_topics + draft_topics`

Query: single LEFT JOIN `categories → course_path_nodes (owner_type='platform') → topics (owner_type='platform')`, grouped by `categories.id`. Categories with zero nodes/topics return zero counts.

---

## Infrastructure Components (not DB tables)

### GlmOcrProvider
- Location: `src/infrastructure/extraction/glm_ocr_provider.py`
- Implements: `ExtractionProvider` protocol
- Backends (prefix-dispatch): `lmstudio://host:port/base_path` (OpenAI-compat), `openai://model-name` (official OpenAI), `anthropic://model-name` (Anthropic Messages), plain model name (Ollama via httpx)
- Key method: `process(image: bytes, prompt: str) -> str` — synchronous; call via `asyncio.to_thread()` in the worker
- Factory: `GlmOcrProvider.from_settings(settings.extraction)`
- Config reads from `ExtractionSettings` (`EXTRACTION__MODEL_SPEC`, `EXTRACTION__MAX_TOKENS`, `EXTRACTION__OLLAMA_BASE_URL`)
- OPENAI_API_KEY / ANTHROPIC_API_KEY read directly by their SDKs — not in ExtractionSettings

### PdfiumReader
- Location: `src/infrastructure/extraction/pdfium_reader.py`
- Implements: `PdfReader` protocol
- Dependency: `pypdfium2` (Apache/BSD licence — PyMuPDF / fitz MUST NOT be imported: AGPL §13 SaaS clause)
- Methods:
  - `page_count(pdf_bytes) -> int`
  - `extract_text(pdf_bytes, page_no) -> str` — 0-indexed page
  - `image_coverage(pdf_bytes, page_no) -> float` — [0.0, 1.0] fraction of page area covered by image objects
  - `render(pdf_bytes, page_no, scale=2.0) -> bytes` — JPEG-encoded page at ~144 DPI
- All methods synchronous — designed for `asyncio.to_thread()` wrapping in the worker

### ExtractionSourceStorage.read()
- Added to protocol: `src/domain/protocols/extraction.py`
- Implemented in: `src/infrastructure/storage/extraction_source.py`
- Signature: `async def read(self, path: str) -> bytes`
- Path-traversal-safe (uses existing `_resolve_safe`); reads via `asyncio.to_thread(path.read_bytes)`

### ExtractionSettings
- Source: `src/shared/config.py`, nested under `settings.extraction`
- Env vars (nested via `EXTRACTION__*`): `MODEL_SPEC` (model URI string, default empty), `OLLAMA_BASE_URL` (default `http://localhost:11434`), `MAX_TOKENS` (int, default 4096)

### TokenIntrospectionClient
- Location: `src/infrastructure/token_introspection.py`
- Wired into `verify_token` (`src/auth/user.py`) when `KEYCLOAK__INTROSPECTION_ENABLED=true` (default: **`True`** as of bb69798)
- Calls `{keycloak_url}/realms/{realm}/protocol/openid-connect/token/introspect` (RFC 7662) using `haisir-backend-admin` client credentials
- Cache: in-process dict keyed by `sha256(token)`; TTL = `min(introspection_cache_ttl_seconds, token_remaining_exp)`
- Retries: up to 3× on `httpx.TransportError` with 1–10 s exponential backoff
- Failure modes: `active: false` → HTTP 401 `"Token has been revoked"`; Keycloak unreachable → HTTP 503 `"Authentication service unavailable"`

### KeycloakSettings (introspection fields)
- `introspection_enabled` (bool, default **`True`**) — feature flag for RFC 7662 introspection; env: `KEYCLOAK__INTROSPECTION_ENABLED`
- `introspection_cache_ttl_seconds` (int, default `30`, min `1`) — per-token cache TTL in seconds; env: `KEYCLOAK__INTROSPECTION_CACHE_TTL_SECONDS`

### EssayGraderProvider
- Location: `src/infrastructure/grading/essay_grader_provider.py`
- Backends (prefix-dispatch): `anthropic://model`, `openai://model`, `lmstudio://model@host/v1`, or plain Ollama model name
- Key method: `grade(question, answer, rubric, max_points) → GradeResult` — synchronous; call via `asyncio.to_thread()` in the worker
- Prompt: structured JSON with `<student_answer>` XML delimiters (prompt injection guard); strips `<think>…</think>` reasoning tokens (qwen3-family) before JSON parsing
- Score formula: `sum(level / scale_max × weight) × max_points`, clamped to `[0, max_points]`; no LLM arithmetic
- Retries up to 3 times with exponential backoff; permanent error after 3 attempts
- Factory: `EssayGraderProvider.from_settings(GradingSettings)`

### GradingSettings
- Source: `src/shared/config.py`, nested under `settings.grading`
- Env vars (`GRADING__*`): `MODEL_SPEC` (default: `qwen3:14b`), `OLLAMA_BASE_URL` (default: `http://localhost:11434`), `OLLAMA_API_KEY` (null), `LMSTUDIO_USE_HTTPS` (false), `MAX_TOKENS` (2048), `TEMPERATURE` (0.0)
- `MODEL_SPEC` supports the same prefix-dispatch URIs as `ExtractionSettings`; `GRADING__*` vars are wired into the Docker Compose worker service

### RubricResolver
- Location: `src/domain/services/rubric_resolver.py`
- `resolve_rubric(question)` → returns the question's custom `rubric` JSONB if present, or a built-in default keyed by `essay_subtype` (`analytical`, `critical`, `extended`, `narrative`, `reflective`, `short`, or generic fallback)
- All built-in rubrics use `scale_max=4` with weighted criteria summing to 1.0
