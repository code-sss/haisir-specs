# Current Schema Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | c24d17e (Phase 5 G3.1/G3.2 — parent curriculum + adopt endpoints, V38-V40 migrations, 2026-07-10) |
| haisir-frontend | a830a83 (Phase 5 G2 — parent workspace shell + /profile page, 2026-07-10) |
| haisir-deploy | ee39f9c (rerank client + WAF/dep hardening, 2026-07-09) |

> Next session: run `git diff c24d17e..HEAD` in haisir-backend, `git diff a830a83..HEAD` in haisir-frontend, and `git diff ee39f9c..HEAD` in haisir-deploy to see only what changed since this snapshot.

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
| V31_pgvector_extension | `CREATE EXTENSION IF NOT EXISTS vector` — enables pgvector column type and ANN index operators. Downgrade: intentional no-op (dropping may corrupt chunk table). |
| V32_rag_vector_table_shim | Creates `data_topic_content_chunks` (BigInteger PK, text, metadata_ JSON, node_id VARCHAR, embedding vector(1024)). Registration shim only — LlamaIndex PGVectorStore owns this table; autogenerate diffs are suppressed. Downgrade: `DROP TABLE data_topic_content_chunks`. |
| V33_add_text_search_tsv_to_chunks | Adds `text_search_tsv TSVECTOR` to `data_topic_content_chunks`; creates `fn_chunks_tsv_update()` BEFORE INSERT/UPDATE trigger that populates it via `to_tsvector('english', ...)`; backfills existing rows; creates GIN index `ix_chunks_text_search_tsv`. Required because V32 shim omitted this column which LlamaIndex `hybrid_search=True` expects to already exist. Downgrade: drops index, trigger, function, column. |
| V34_student_enrollments | Creates `student_enrollments` table (UUID PK, `student_sub TEXT`, `course_path_node_id UUID FK→course_path_nodes ON DELETE CASCADE`, `enrolled_at TIMESTAMPTZ DEFAULT now()`, `enrollment_source VARCHAR(20) DEFAULT 'self'`). UNIQUE constraint `uq_student_enrollments_sub_node` on `(student_sub, course_path_node_id)`; index `idx_student_enrollments_student_sub` on `student_sub`. |
| V35_doubts | Creates `doubts` table (UUID PK, `student_sub TEXT`, `topic_id`/`course_path_node_id` UUID FK nullable, `title TEXT`, `status VARCHAR(20)` CHECK 6-value enum default `'new'`, `escalated_to TEXT`, `haitu_attempted BOOLEAN`, `auto_close_at TIMESTAMPTZ` default `now() + interval '7 days'`, `resolved_at`, `created_at`/`updated_at`; partial index on `auto_close_at WHERE status != 'resolved'`) and `doubt_messages` table (UUID PK, `doubt_id` FK→doubts CASCADE, `sender_type VARCHAR(10)` CHECK 4-value enum, `content TEXT`, `created_at`; index on `doubt_id`). |
| V36_notifications | Creates `notifications` table (UUID PK, `recipient_idp_sub TEXT` nullable, `recipient_role VARCHAR(20)`, `type VARCHAR(40)`, `title TEXT`, `body TEXT` nullable, `action_url TEXT` nullable, `read BOOLEAN` default false, `created_at TIMESTAMPTZ` default now()). Four indexes: `idx_notifications_recipient (recipient_idp_sub)`; `idx_notifications_role_unread (recipient_role, read)`; `idx_notifications_unread_personal (recipient_idp_sub) WHERE read=false AND recipient_idp_sub IS NOT NULL` (partial); `idx_notifications_shared_unread (recipient_role) WHERE read=false AND recipient_idp_sub IS NULL` (partial). |
| V37_mastery_enrollment_topics | Adds `questions.topic_id UUID NULL` + `ix_questions_topic_id` index. Creates `enrollment_topics` table (UUID PK gen_random_uuid(), `student_enrollment_id UUID FK→student_enrollments CASCADE`, `topic_id UUID FK→topics`, `status VARCHAR(20)` CHECK 4-value enum `not_started\|in_progress\|completed\|weak`, `mastery_score FLOAT NULL` CHECK 0–100, `last_studied_at TIMESTAMPTZ NULL`, `created_at`/`updated_at TIMESTAMPTZ`; UNIQUE `uq_enrollment_topics_enrollment_topic (student_enrollment_id, topic_id)`; index `idx_enrollment_topics_enrollment` on `student_enrollment_id`; index `idx_enrollment_topics_topic_status` on `(topic_id, status)`). Creates `student_risk_state` table (`student_sub TEXT PK`, `at_risk_active BOOLEAN` default false, `last_fired_at TIMESTAMPTZ NULL`). Status column size set to `VARCHAR(20)` (follow-up fix in 7fd5cd7 after initial `VARCHAR(10)`). |
| V38_relax_student_profile_name_nullable | Alters `student_profiles.first_name`/`last_name` from `NOT NULL` → nullable, enabling a grade-only profile upsert (Pre-Phase-5 G6 onboarding grade picker). |
| V39_partial_unique_parent_child_link | Drops the blanket unique constraint `uq_parent_child` on `parent_child_links(parent_sub, child_sub)`; replaces it with a partial unique index `uq_parent_child_active` on the same columns scoped to `WHERE revoked_at IS NULL` — a revoked pair can be re-linked via a fresh code (BR-PAR-014) while at most one active link per pair is still enforced. |
| V40_adopt_lineage_source_node_id | Adds `course_path_nodes.source_node_id UUID NULL` + partial unique index `ux_course_path_nodes_adopt_lineage` on `(owner_id, source_node_id) WHERE source_node_id IS NOT NULL` — enforces adopt idempotency (BR-DATA-006): a parent adopting the same platform subtree twice hits the DB constraint, surfaced as 409. |

---

## user_metadata
- `idp_sub` (String, PK) — Keycloak subject claim; primary identity key
- `onboarding_completed_at` (DateTime TZ, nullable) — timestamp when onboarding was marked complete

## student_profiles
- `id` (UUID, PK)
- `idp_sub` (String, UNIQUE) — links to user_metadata
- `first_name` (String, nullable as of V38 — was `NOT NULL`; enables a grade-only profile upsert)
- `last_name` (String, nullable as of V38 — was `NOT NULL`)
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

> As of Phase 5 G1: `POST /api/student/parent-link-codes` generates codes from the student side (deactivating any prior unused code); `GET /api/student/parent-link-codes` fetches the current one.

## parent_child_links
- `id` (UUID, PK)
- `parent_sub` (String) — parent's idp_sub
- `child_sub` (String) — child's idp_sub
- `created_at` (DateTime TZ)
- `revoked_at` (DateTime TZ, nullable) — NULL = active link; revoked from either side (`DELETE /api/student/parent-links/{id}` or `DELETE /api/parent/children/{child_sub}/link`)
- Partial UNIQUE index `uq_parent_child_active` on `(parent_sub, child_sub) WHERE revoked_at IS NULL` (as of V39, replacing a blanket unique constraint) — a revoked pair may be re-linked via a fresh code; at most one active link per pair is enforced
- Max 10 active links per parent (BR-PAR-016) enforced at redemption time (`POST /api/parent-child-links` → 422 over cap)

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
- `source_node_id` (UUID, nullable, self-FK → course_path_nodes) — set on a parent-adopted node to the platform node it was cloned from (V40); NULL for platform nodes and parent nodes built from scratch. Partial unique index on `(owner_id, source_node_id) WHERE source_node_id IS NOT NULL` enforces one adopt per parent per source (BR-DATA-006, 409 on repeat).

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
- `topic_id` (UUID, nullable) — links the question to a topic; used by `MasteryService` for post-exam mastery attribution; indexed (`ix_questions_topic_id`); existing rows NULL after V37 (no backfill)

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

## student_enrollments
> Created by V34. Records a student's self-enrollment in a course-path node.

- `id` (UUID, PK)
- `student_sub` (Text) — Keycloak subject; no FK (no local users table)
- `course_path_node_id` (UUID, FK → course_path_nodes.id, ON DELETE CASCADE)
- `enrolled_at` (TIMESTAMPTZ, default `now()`)
- `enrollment_source` (VARCHAR 20, default `'self'`) — origin of enrolment; `'self'` is the only value this phase

Constraints: UNIQUE `(student_sub, course_path_node_id)` — duplicate enroll attempt → 409.
Index: `idx_student_enrollments_student_sub` on `student_sub` for per-student lookups.

## enrollment_topics
> Created by V37. Per-student, per-topic mastery progress record within an enrollment.

- `id` (UUID, PK, gen_random_uuid())
- `student_enrollment_id` (UUID, FK → student_enrollments.id ON DELETE CASCADE)
- `topic_id` (UUID, FK → topics.id)
- `status` (VARCHAR(20)) — `not_started` | `in_progress` | `completed` | `weak`; CHECK enforced by `ck_enrollment_topics_status`
- `mastery_score` (Float, nullable) — 0–100; CHECK `ck_enrollment_topics_mastery_score`
- `last_studied_at` (TIMESTAMPTZ, nullable)
- `created_at` / `updated_at` (TIMESTAMPTZ)
- UNIQUE: `uq_enrollment_topics_enrollment_topic (student_enrollment_id, topic_id)`
- Index: `idx_enrollment_topics_enrollment` on `student_enrollment_id`
- Index: `idx_enrollment_topics_topic_status` on `(topic_id, status)`

## student_risk_state
> Created by V37. One row per student; tracks whether the at-risk flag is currently active.

- `student_sub` (Text, PK) — Keycloak subject identifier
- `at_risk_active` (Boolean, NOT NULL, default false) — true when ≥ 3 weak topics; cleared when `weak_count == 0`
- `last_fired_at` (TIMESTAMPTZ, nullable) — timestamp of the most recent at-risk notification fire

---

## doubts
> Created by V35. Records a student's doubt about a topic or course-path node.

- `id` (UUID, PK)
- `student_sub` (Text, NOT NULL) — Keycloak subject; no FK (no local users table)
- `topic_id` (UUID, FK → topics.id, nullable)
- `course_path_node_id` (UUID, FK → course_path_nodes.id, nullable)
- `title` (Text, nullable) — optional short title
- `status` (VARCHAR 20, NOT NULL, default `'new'`) — CHECK: `'new' | 'ai_answered' | 'escalated' | 'answered' | 'resolved' | 'auto_closed'`
- `escalated_to` (Text, nullable) — identifier of escalation target
- `haitu_attempted` (BOOLEAN, NOT NULL, default false)
- `auto_close_at` (TIMESTAMPTZ, NOT NULL, default `now() + interval '7 days'`)
- `resolved_at` (TIMESTAMPTZ, nullable)
- `created_at` / `updated_at` (TIMESTAMPTZ, NOT NULL, default `now()`)

Indexes: `idx_doubts_student_sub` on `student_sub`; `idx_doubts_status` on `status`; `idx_doubts_auto_close` on `auto_close_at` WHERE `status != 'resolved'` (partial).

## doubt_messages
> Created by V35. A single message in a doubt thread.

- `id` (UUID, PK)
- `doubt_id` (UUID, FK → doubts.id, ON DELETE CASCADE)
- `sender_type` (VARCHAR 10, NOT NULL) — CHECK: `'student' | 'ai' | 'teacher' | 'system'`
- `content` (Text, NOT NULL)
- `created_at` (TIMESTAMPTZ, NOT NULL, default `now()`)

Index: `idx_doubt_messages_doubt_id` on `doubt_id`.

## notifications
> Created by V36. Personal or shared-role-queue notification records. Emitted by doubt lifecycle events (escalate, teacher reply, auto-close) and the auto-close cron worker.

- `id` (UUID, PK)
- `recipient_idp_sub` (Text, nullable) — Keycloak sub of the recipient; **NULL = shared-queue notification** visible to all users of `recipient_role` (e.g. the instructor queue for `new_doubt_escalated`)
- `recipient_role` (VARCHAR 20, NOT NULL) — role that receives this notification (`student`, `instructor`, `parent`)
- `type` (VARCHAR 40, NOT NULL) — event type string: `new_doubt_escalated`, `doubt_teacher_replied`, `doubt_auto_closed`, `child_doubt_replied`, `child_doubt_auto_closed`
- `title` (Text, NOT NULL) — short human-readable title
- `body` (Text, nullable) — optional longer body text
- `action_url` (Text, nullable) — optional deep-link URL (e.g. `/doubts/{id}`, `/teacher/doubts/{id}`, `/parent`)
- `read` (Boolean, NOT NULL, default false)
- `created_at` (TIMESTAMPTZ, NOT NULL, default now())

Indexes: `idx_notifications_recipient (recipient_idp_sub)`; `idx_notifications_role_unread (recipient_role, read)`; `idx_notifications_unread_personal (recipient_idp_sub) WHERE read=false AND recipient_idp_sub IS NOT NULL` (partial — personal unread); `idx_notifications_shared_unread (recipient_role) WHERE read=false AND recipient_idp_sub IS NULL` (partial — shared-queue unread by role).

> **v1 limitation:** shared-queue rows have no per-user read tracking — marking one read marks it read globally for all users of that role. Personal rows (`recipient_idp_sub IS NOT NULL`) are tracked per-user.

## data_topic_content_chunks
- `id` (BigInteger, PK autoincrement) — LlamaIndex-managed row ID
- `text` (Text, nullable) — chunked text content (SentenceSplitter chunk_size=512, chunk_overlap=100)
- `metadata_` (JSON, nullable) — chunk metadata: `content_id`, `topic_id`, `topic_title`, `node_name`, `parent_name`, `grandparent_name`, `page_order`; used by hAITU retriever for `MetadataFilters`
- `embedding` (vector(1024), nullable) — bge-m3 dense embedding via `_LmStudioEmbedding` (openai SDK, `lmstudio://model@host:port/path` spec) or `OllamaEmbedding` for plain Ollama specs; dispatch via `_build_embed_model()`; HNSW index (m=16, ef_construction=64, ef_search=40, `vector_cosine_ops`)
- `node_id` (VARCHAR, nullable) — LlamaIndex internal node UUID
- `text_search_tsv` (tsvector) — added by **V33 migration** via `fn_chunks_tsv_update()` BEFORE INSERT/UPDATE trigger (`to_tsvector('english', ...)`); GIN index `ix_chunks_text_search_tsv`; enables sparse leg of hybrid retrieval

Managed by LlamaIndex `PGVectorStore`; V32 is the registration shim, V33 adds the tsvector column the store requires. Do not add this table to Alembic autogenerate targets.

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

### EmbeddingSettings
- Source: `src/shared/config.py`, nested under `settings.embedding`
- Env vars (`EMBEDDING__*`): `MODEL_SPEC` (default: `bge-m3`), `OLLAMA_BASE_URL` (default: `http://localhost:11434`), `BATCH_SIZE` (default: 10), `EMBED_DIM` (default: 1024), `POLL_INTERVAL_SECONDS` (default: 5)
- `EMBED_DIM` must stay `1024` to match the `vector(1024)` column in V32 — changing without recreating the HNSW index causes query errors
- Used by `rag_outbox_loop.py`; all vars wired as bare `${EMBEDDING__*}` in the Docker Compose worker service (defaults live in `Settings`)

### HaituSettings
- Source: `src/shared/config.py`, nested under `settings.haitu`
- Env vars (`HAITU__*`): `MODEL_SPEC` (default: ""), `OLLAMA_BASE_URL` (default: `http://localhost:11434`), `MAX_TOKENS` (default: 2048), `TOP_K` (default: 5), `RERANK_MODEL` (default: ""), `LLM_CONTEXT_WINDOW` (default: 4096), `LLM_REQUEST_TIMEOUT` (default: 360.0), `LLM_THINKING` (default: false)
- Config-only in this phase; retrieval endpoint (`POST /api/haitu/topic-doubt`) not yet implemented — planned for next cycle once vectors are populated
- All 8 vars wired as bare `${HAITU__*}` in the Docker Compose worker service
- `RERANK_MODEL` is now a future-hook only: the inline cross-encoder (`SentenceTransformerRerank`) and the `sentence-transformers`/`torch` deps were removed in G0.3. `_stage3_rerank` is a no-op passthrough; a non-empty `rerank_model` logs a warning and returns nodes unordered. An external rerank API client will be wired here later.

### MasteryService
- Location: `src/domain/services/mastery_service.py`
- `recompute_for_session(student_sub, session_id)` — groups scored questions by `topic_id`, computes `mastery_score = 0.6×new + 0.4×existing` (EWA), upserts `enrollment_topics`. Emits `topic_marked_weak` notification on weak transition; emits `student_at_risk` notification (instructor shared queue) when ≥ 3 weak topics via `student_risk_state.claim_if_inactive`; clears flag when `weak_count == 0`.
- Attribution: `get_path_to_root(course_path_node_id)` traversal to find the deepest enrolled ancestor for each question's topic.
- Triggered from: `submit_exam()` on `ExamStatus.completed`, `confirm_grade()`, `override_grade()`, and essay grading `_maybe_autocomplete_session()` (auto_release mode in the worker).

### RubricResolver
- Location: `src/domain/services/rubric_resolver.py`
- `resolve_rubric(question)` → returns the question's custom `rubric` JSONB if present, or a built-in default keyed by `essay_subtype` (`analytical`, `critical`, `extended`, `narrative`, `reflective`, `short`, or generic fallback)
- All built-in rubrics use `scale_max=4` with weighted criteria summing to 1.0
