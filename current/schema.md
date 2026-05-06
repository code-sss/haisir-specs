# Current Schema Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | e18508c (feat(extraction): add document extraction pipeline, 2026-04-30) |
| haisir-frontend | 7633f19 (feat(admin): add extraction status panel, toast system, and upload fixes, 2026-05-05) |
| haisir-deploy | eea5152 (fix(apisix): add dedicated route for empty-body POST action endpoints, 2026-05-05) |

> Next session: run `git diff e18508c..HEAD` in haisir-backend, `git diff 7633f19..HEAD` in haisir-frontend, and `git diff eea5152..HEAD` in haisir-deploy to see only what changed since this snapshot.

---

## Applied Migrations (as of snapshot)

| Migration | What it does |
|---|---|
| V23_visibility_enforcement | Alters `course_path_nodes.owner_id` and `topics.owner_id` from Integer → String; adds `exam_templates.owner_id` (String, nullable); adds `parent_child_links.revoked_at` (DateTime TZ, nullable) |
| V24_add_visibility_indexes | Adds covering index `ix_parent_child_links_child_sub_revoked` on `(child_sub, revoked_at) INCLUDE (parent_sub)` for BR-DATA-003 subquery performance |
| V25_expand_nodetype_enum | Adds 6 new values to the `nodetype` PostgreSQL enum: `chapter`, `module`, `section`, `unit`, `week`, `skill`. Uses `ALTER TYPE nodetype ADD VALUE IF NOT EXISTS` (run outside transaction). No downgrade path — PostgreSQL does not support removing enum values. |
| V26_extraction_tables | Installs `touch_updated_at()` trigger function. Adds `source_extraction_job_id` (UUID nullable) to `topic_contents`. Creates 6 new tables: `extraction_jobs`, `extraction_job_pages`, `extraction_job_audit`, `rag_indexing_outbox`, `worker_heartbeats`, `parent_quota_counters`, with all indexes. |

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

## questions
- `id` (UUID, PK)
- `question_text` (String)
- `question_type` (Enum: single_choice | multiple_choice | true_false | fill_in_the_blank | essay)
- `options` (JSONB) — array of {id, text, image_url}
- `correct_answers` (JSONB) — array of option IDs
- `explanation` (String, nullable)
- `difficulty` (Enum: easy | medium | hard)
- `tags` (JSONB, nullable)
- `image_url` (String, nullable)

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
- `status` (Enum: pending | ongoing | completed | failed)

## exam_session_questions
- `id` (UUID, PK)
- `exam_session_id` (UUID, FK → exam_sessions)
- `question_id` (UUID, FK → questions)
- `order` (Integer)
- `points` (Integer)
- `user_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `earned_points` (Float, nullable)

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
