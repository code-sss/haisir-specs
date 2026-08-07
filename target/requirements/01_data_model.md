# Data Model

> **Target state scope:** Student, Parent, Platform Admin. See `vision/requirements/01_data_model.md` for the full vision schema.

<!--
## Table of Contents (section quick-jump)
  Identity Convention
  Existing Schema (baseline)
  Schema Extensions (this increment)
      1. course_path_nodes
      2. topics
      3. exam_templates
  Content Ownership Rules
  Parent Adopt (Clone) Flow
  Parent-Child Access
  Exam Results Visibility (parent)
  Schema Extensions (Question Types)
      question_type enum values
      matching options JSONB structure
      New columns on questions
      New columns on exam_session_questions
  Schema Extensions (Phase 1d-real — Content Extraction)
      1 column added to topic_contents
      New table — extraction_jobs
      New table — extraction_job_pages
      New table — extraction_job_audit
      New table — rag_indexing_outbox
      New table — worker_heartbeats
      New table — parent_quota_counters
      Extraction Business Rules
  Schema Extensions (Essay AI Grading)
      Updated question_type grading column
      New columns on questions (rubric)
      New column on exam_templates (essay_grading_mode)
      New columns on exam_session_questions (AI grading state)
      New table — essay_grading_jobs
      grading_status state machine
      Score-mapping formula
      Essay Grading Business Rules
-->

---

## Identity Convention

- No local `users` table. All user identity from IdP (Keycloak).
- All user-referencing columns use `idp_sub` — the JWT `sub` claim, a UUID stored as a string.
- No foreign key constraints on `idp_sub` columns.

---

## Existing Schema (baseline — do not drop or rename)

All 21 tables live in production. See `current/schema.md` for the authoritative column-level detail.

**Content hierarchy:**
- `categories` → `course_path_nodes` (self-referential tree, arbitrary depth)
- `course_path_nodes` → `topics` (leaf nodes only)
- `topics` → `topic_contents` (one per type: pdf, video, text)
- `topic_contents` → `data_topic_content_chunks` (managed by LlamaIndex PGVectorStore, seeded by `rag_indexing_outbox`; V32 Alembic shim registers it; do not drop or rename)

**Questions & Exams:**
- `questions`, `paragraph_questions`
- `exam_templates`, `exam_template_questions`
- `exam_sessions`, `exam_session_questions`

**User metadata:**
- `user_metadata` (idp_sub PK + onboarding_completed_at)
- `student_profiles`, `teacher_profiles`, `parent_profiles`
- `parent_link_codes`, `parent_child_links`, `class_invite_codes`

**Deprecated (still live, superseded):**
- `assessments`, `assessment_attempts`, `assessment_answers`, `answers`

---

## Schema Extensions (this increment)

Three `ALTER TABLE` statements. All columns are additive — nothing is dropped or renamed.

### 1. `course_path_nodes`

```sql
ALTER TABLE course_path_nodes
  ADD COLUMN owner_type VARCHAR NOT NULL DEFAULT 'platform',
  ADD COLUMN owner_id   UUID    NULL;
```

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `owner_type` | VARCHAR | NOT NULL, DEFAULT `'platform'` | `'platform'` or `'parent'` |
| `owner_id` | UUID | NULL | `NULL` for platform; parent `idp_sub` for parent-owned |

**Migration:** `UPDATE course_path_nodes SET owner_type = 'platform', owner_id = NULL;` (all existing rows are platform content).

### 2. `topics`

```sql
ALTER TABLE topics
  ADD COLUMN owner_type VARCHAR NOT NULL DEFAULT 'platform',
  ADD COLUMN owner_id   UUID    NULL,
  ADD COLUMN status     VARCHAR NOT NULL DEFAULT 'live';
```

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `owner_type` | VARCHAR | NOT NULL, DEFAULT `'platform'` | `'platform'` or `'parent'` |
| `owner_id` | UUID | NULL | `NULL` for platform; parent `idp_sub` for parent-owned |
| `status` | VARCHAR | NOT NULL, DEFAULT `'live'` | `'draft'` \| `'live'` — value set enforced at the Pydantic schema layer (`Literal["draft", "live"]`), no DB `CHECK` constraint |

**Migration:** `UPDATE topics SET owner_type = 'platform', owner_id = NULL, status = 'live';`

### 3. `exam_templates`

```sql
ALTER TABLE exam_templates
  ADD COLUMN owner_type VARCHAR NOT NULL DEFAULT 'platform',
  ADD COLUMN owner_id   UUID    NULL;
```

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `owner_type` | VARCHAR | NOT NULL, DEFAULT `'platform'` | `'platform'` or `'parent'` |
| `owner_id` | UUID | NULL | `NULL` for platform; parent `idp_sub` for parent-owned |

**Migration:** `UPDATE exam_templates SET owner_type = 'platform', owner_id = NULL;`

**Note:** Existing columns `created_by` (UUID) and `organization_id` (Integer) remain unchanged. For parent-owned exam templates: `created_by = parent.idp_sub`, `organization_id = NULL`, `owner_type = 'parent'`, `owner_id = parent.idp_sub`.

---

## Content Ownership Rules

**BR-DATA-001 — Platform content:**
`owner_type = 'platform'`, `owner_id = NULL`. Created and managed by `admin` role only. Visible to all authenticated students.

**BR-DATA-002 — Parent content:**
`owner_type = 'parent'`, `owner_id = parent.idp_sub`. Created by `parent` role. Visible only to students who have an active, non-revoked `parent_child_links` record where `parent_idp_sub = owner_id`.

**BR-DATA-003 — Visibility filter (applied on all student queries for nodes/topics/exams):**

> **Physical column name note:** The `parent_child_links` table uses physical columns `parent_sub` and `child_sub` (not `parent_idp_sub` / `child_idp_sub` as shown in the logical spec below). The physical schema is sacred and will not be renamed. All SQL in the codebase uses the physical names; the spec uses the logical aliases for readability only.

```sql
WHERE (owner_type = 'platform')
   OR (owner_type = 'parent' AND owner_id IN (
       SELECT parent_idp_sub FROM parent_child_links
       WHERE child_idp_sub = :current_user_idp_sub
         AND revoked_at IS NULL
   ))
```

**BR-DATA-004 — Parent sees only own content:**
Parent API endpoints filter `owner_id = current_user.idp_sub` for all write operations and their own curriculum reads.

---

## Parent Adopt (Clone) Flow

**BR-DATA-005 — Adopt clones structure only:**
When a parent adopts a platform board subtree:
- Deep copy of `course_path_nodes` rows (the selected subtree) with `owner_type = 'parent'`, `owner_id = parent.idp_sub`.
- Deep copy of attached `topics` rows with `owner_type = 'parent'`, `owner_id = parent.idp_sub`, `status = 'draft'`.
- **Not cloned:** `topic_contents`, `data_topic_content_chunks`, `questions`, `exam_templates`, `exam_template_questions`. Parent populates their own content and exams after adoption.
- Platform updates to the original board do **not** propagate to parent copies. Each parent copy is independent.

**BR-DATA-006 — Adopt is idempotent per source node, DB-enforced (V40):**
If a parent has already adopted a given platform subtree root, a second adopt request for the same `source_node_id` returns 409 Conflict rather than creating duplicate nodes. Enforced by a partial unique index on `course_path_nodes(owner_id, source_node_id) WHERE source_node_id IS NOT NULL` — see "Schema Extensions (Phase 5 — Parent Curriculum Builder)" below.

---

## Parent-Child Access

`parent_child_links` (already live) is the access gate. Key columns:
- `parent_sub` (`parent_idp_sub` in logical spec) (UUID string) — the parent's `idp_sub`
- `child_sub` (`child_idp_sub` in logical spec) (UUID string) — the student's `idp_sub`
- `revoked_at` (nullable timestamp) — NULL means active

Access is granted automatically when the link is created. Revoking (`revoked_at` set) removes access immediately — no cache.

---

## Exam Results Visibility (parent)

**BR-DATA-007 — Parent sees child results for parent-owned exams only:**
- `GET /api/parent/children/{child_idp_sub}/exam-sessions` returns `exam_sessions` where:
  - `exam_sessions.user_id = child_idp_sub`
  - `exam_templates.owner_id = current_parent.idp_sub` (parent-owned exams only)
  - Active `parent_child_links` record exists
- Parents do NOT see results for platform exams the child has taken.

---

## Schema Extensions (Question Types)

Adds three new `question_type` values and supporting columns. All columns are additive — nothing is dropped or renamed.

### `question_type` enum values

The `questions.question_type` column is a string enum. Full set after this extension:

| Value | Grading | Notes |
|---|---|---|
| `single_choice` | Auto | One correct option |
| `multiple_choice` | Auto, partial credit | Multiple correct options |
| `true_false` | Auto | Options must be exactly `True` / `False` |
| `fill_in_the_blank` | Auto, normalized match | |
| `one_word_response` | Auto, normalized match | Compact inline UI; template can cap count independently |
| `essay` | AI-graded async (configurable: auto_release / review_first) | `essay_subtype` is a rendering hint; grading via LLM pipeline — see `08_essay_ai_grading.md` |
| `matching` | Auto, partial credit per pair | `options` JSONB has `side` field; `correct_answers` are `"Lx:Rx"` pair strings; see `penalty_matching` |
| `problem_solving` | Auto (answer); working captured unscored | See below |

### `matching` options JSONB structure

```json
[
  {"id": "L1", "side": "left",  "text": "Mitochondria"},
  {"id": "L2", "side": "left",  "text": "Nucleus"},
  {"id": "R1", "side": "right", "text": "Powerhouse of the cell"},
  {"id": "R2", "side": "right", "text": "Controls cell activity"}
]
```

`correct_answers`: `["L1:R1", "L2:R2"]` (left-id:right-id pair strings).

> **`side` is derived, not required on input (added 2026-08-07).** The `L`/`R` ID prefix is the
> canonical source of truth — it is what `correct_answers` pair strings and the grader key on. The
> backend fills a missing `side` from that prefix (`L*` → `left`, `R*` → `right`) when constructing a
> `Question`; an explicitly supplied `side` is always preserved, so callers that set it are
> unaffected. This exists because the authoring UI omits `side`, which previously failed validation.
> Storage is unchanged — persisted rows still carry `side`, so readers and the grader see the shape
> documented above.

Grading formula (default, `penalty_matching = false`): `correct_pairs / total_pairs × available_points`. Wrong pairings are ignored.

Grading formula (penalty mode, `penalty_matching = true`): `max(0, (correct_pairs − extra_wrong_pairs) / total_pairs) × available_points`. Exam creators can enable this per-question to discourage guessing.

Right-column items are shuffled per-session using seeded Fisher-Yates. `shuffle_seed` (INT) is generated at session-creation time and stored on `exam_session_questions`. Frontend replicates the same algorithm — this is a cross-stack contract.

### New columns on `questions`

```sql
ALTER TABLE questions
  ADD COLUMN essay_subtype    VARCHAR(50) NULL
    CHECK (essay_subtype IS NULL
           OR essay_subtype IN ('analytical','critical','extended',
                                'narrative','reflective','short')),
  ADD COLUMN working_required BOOLEAN     NOT NULL DEFAULT false,
  ADD COLUMN penalty_matching BOOLEAN     NOT NULL DEFAULT false;
```

| Column | Type | Default | Notes |
|---|---|---|---|
| `essay_subtype` | VARCHAR(50) | `null` | Rendering hint for `essay` questions only. Valid values: `analytical`, `critical`, `extended`, `narrative`, `reflective`, `short`. No grading impact. |
| `working_required` | BOOLEAN | `false` | `problem_solving` only; when `true`, UI renders a free-text working area |
| `penalty_matching` | BOOLEAN | `false` | `matching` only; when `true`, extra wrong pairings reduce the score (see grading formula above). Set by exam creator at question level. |

**Migration (V28):** no backfill required. Existing rows remain `null` / `false`.

### New columns on `exam_session_questions`

```sql
ALTER TABLE exam_session_questions
  ADD COLUMN working_text  TEXT NULL,
  ADD COLUMN shuffle_seed  INT  NULL;
```

| Column | Type | Default | Notes |
|---|---|---|---|
| `working_text` | TEXT | `null` | Student's working for `problem_solving`; captured on submit, not scored this phase |
| `shuffle_seed` | INT | `null` | `matching` only; generated at session creation; drives seeded Fisher-Yates right-column display order |

**Migration:** no backfill required. Existing rows remain `null`.

---

## Schema Extensions (Phase 1d-real — Content Extraction)

> Detailed behaviour and business rules in `target/requirements/12_content_extraction.md`. This section defines the storage shape only.

### Columns added to existing `topic_contents` (additive)

```sql
ALTER TABLE topic_contents
  ADD COLUMN source_extraction_job_id UUID NULL;
```

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `source_extraction_job_id` | UUID | NULL | Soft pointer (no FK per CLAUDE.md identity convention). Set only for rows materialized by an extraction job. Joins to `extraction_job_audit.job_id` for provenance display. |

**Migration:** No backfill required. Existing rows remain `NULL`.

### Schema Extensions (Content Viewing & Publish — this increment)

```sql
ALTER TABLE topic_contents
  ADD COLUMN visibility_status VARCHAR NOT NULL DEFAULT 'draft'; -- 'draft' | 'published'
```

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `visibility_status` | VARCHAR | NOT NULL, DEFAULT `'draft'` | `'draft'` \| `'published'` — enforced at Pydantic schema layer only (`Literal["draft","published"]`), no DB CHECK, same pattern as `topics.status`. |

`content_type` gains a new value: **`'image'`** (`'pdf'` already exists in the baseline enum, previously unused for raw-file storage — see BR-DATA-024 below). Note this is a **native Postgres enum type**, not a VARCHAR — `topic_contents.content_type` was created as `sa.Enum(..., name="contenttype")` in `V4_topic.py`, so the value must be added with DDL of its own:

```sql
ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'image';
```

`ALTER TYPE ... ADD VALUE` cannot be run inside the transaction that then *uses* the new value, so the Alembic revision must issue it in an autocommit block (`with op.get_context().autocommit_block():`) ahead of any DML referencing `'image'`.

No column stores the raw file separately: the raw row reuses the existing **`url`** column, which is already the file-path/URL column for `topic_contents` (`video` rows hold their external URL there; `pdf` rows hold a local path there, normalized by `TopicContentService.create` to `{data_dir}/topics/{content_type}/{filename}`). The `text` column stays reserved for markdown bodies — putting a path in it would also defeat the RAG worker's `tc.text IS NOT NULL AND tc.text != ''` guard.

**Migration:** deliberate reset, not a backfill. `topic_contents`, `extraction_jobs`, `extraction_job_pages`, `extraction_job_audit`, `rag_indexing_outbox`, and `data_topic_content_chunks` are truncated as part of this rollout — existing content is discarded rather than migrated forward, by product decision. All content is re-uploaded fresh under the model below.

**The truncate must NOT ship inside the Alembic revision.** Migrations run automatically on deploy; an irreversible data-destroying statement inside one would fire against any environment the image reaches, with no operator in the loop. The additive DDL (`ALTER TYPE`, `ADD COLUMN`) goes in the revision; the truncate is a separate, manually-invoked runbook script requiring explicit confirmation, run once per environment. Orphaned files under `{data_dir}/topics/` must be cleared in the same runbook — truncating the rows does not delete them. (Absent that decision, the safe default would be `'published'`, not `'draft'`, mirroring `topics.status`'s `DEFAULT 'live'` — so existing rows would stay visible and only new inserts would be explicitly drafted. Worth remembering if a future increment ever adds a column like this against a deployment with content worth preserving.)

### New table — `extraction_jobs`

Working state of an active or recently-finished extraction job. Purged after final-state TTL (`done`=7d, `extraction_failed`=30d, `cancelled`=24h, `upload_failed`=7d). Audit trail lives in `extraction_job_audit` (indefinite).

```sql
CREATE TABLE extraction_jobs (
    id                   UUID PRIMARY KEY,
    topic_id             UUID NOT NULL,                       -- soft FK to topics.id
    created_by           VARCHAR NOT NULL,                    -- idp_sub
    expected_owner_type  VARCHAR NOT NULL,                    -- 'platform' | 'parent'
    job_type             VARCHAR NOT NULL DEFAULT 'contents', -- 'contents' | 'exercises'
    source_type          VARCHAR NOT NULL,                    -- 'pdf' | 'image'
    source_filename      VARCHAR NOT NULL,
    source_size_bytes    BIGINT  NOT NULL,
    source_path          VARCHAR NOT NULL,                    -- relative to STORAGE_ROOT
    source_sha256        CHAR(64) NOT NULL,
    status               VARCHAR NOT NULL,                    -- see § Job Lifecycle in 12_*
    pages_total          INT     NULL,
    pages_completed      INT     NOT NULL DEFAULT 0,
    cancel_requested     BOOLEAN NOT NULL DEFAULT FALSE,
    error_message        TEXT    NULL,
    idempotency_key      UUID    NOT NULL,
    running_cost_usd     NUMERIC(10,4) NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at           TIMESTAMPTZ NULL,
    finished_at          TIMESTAMPTZ NULL,
    purge_at             TIMESTAMPTZ NULL,
    locked_at            TIMESTAMPTZ NULL,
    locked_by            VARCHAR NULL                         -- worker hostname
);

CREATE INDEX ix_extraction_jobs_queue   ON extraction_jobs (status, created_at);
CREATE INDEX ix_extraction_jobs_topic   ON extraction_jobs (topic_id, status);
CREATE INDEX ix_extraction_jobs_purge   ON extraction_jobs (purge_at) WHERE purge_at IS NOT NULL;
CREATE UNIQUE INDEX ux_extraction_jobs_idempotency
    ON extraction_jobs (created_by, idempotency_key);
CREATE UNIQUE INDEX ux_extraction_jobs_dedup
    ON extraction_jobs (topic_id, source_sha256)
    WHERE status NOT IN ('cancelled','upload_failed');

-- Trigger: keep updated_at fresh for ETag generation
CREATE TRIGGER trg_extraction_jobs_touch BEFORE UPDATE ON extraction_jobs
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
```

**Status enum (string, not PG enum — easier to evolve):**
`pending` | `extracting` | `done` | `upload_failed` | `extraction_failed` | `cancelled`. **No `'uploading'` state** — HTTP transfer is client-side; frontend uses an in-memory pseudo-job until 201 returns the real `'pending'` row.

### New table — `extraction_job_pages`

Per-page extracted markdown. Staged during extraction so a worker death can resume from `MAX(page_no)+1` instead of re-running the LLM (challenger #2).

```sql
CREATE TABLE extraction_job_pages (
    job_id         UUID NOT NULL,        -- soft FK to extraction_jobs.id
    page_no        INT  NOT NULL,
    markdown_text  TEXT NOT NULL,
    sha256         CHAR(64) NOT NULL,
    extracted_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (job_id, page_no)
);
```

Rows for a job are deleted at finalize-TX time, after `topic_contents` are materialized.

### New table — `extraction_job_audit`

Indefinite provenance record. Survives purge of the working `extraction_jobs` row and the source file. Carries the link from `topic_contents.source_extraction_job_id` to the original filename.

```sql
CREATE TABLE extraction_job_audit (
    job_id           UUID PRIMARY KEY,         -- same id as the (now-purged) extraction_jobs.id
    topic_id         UUID NOT NULL,
    idp_sub          VARCHAR NOT NULL,
    source_filename  VARCHAR NOT NULL,
    source_sha256    CHAR(64) NOT NULL,
    source_type      VARCHAR NOT NULL,
    job_type         VARCHAR NOT NULL,
    model_spec_used  VARCHAR NOT NULL,
    pages_extracted  INT NOT NULL,
    cost_usd         NUMERIC(10,4) NOT NULL,
    final_status     VARCHAR NOT NULL,         -- 'done' | 'extraction_failed' | 'cancelled'
    started_at       TIMESTAMPTZ NOT NULL,
    finished_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_extraction_job_audit_topic ON extraction_job_audit (topic_id);
CREATE INDEX ix_extraction_job_audit_user_day
    ON extraction_job_audit (idp_sub, finished_at DESC);
```

### New table — `rag_indexing_outbox`

Async embedding queue (challenger #3). Decouples user-visible content materialization from embedding latency / failure. New `topic_contents` rows from any source (extraction, manual, future) enqueue here.

```sql
CREATE TABLE rag_indexing_outbox (
    content_id    UUID PRIMARY KEY,                     -- soft FK to topic_contents.id
    status        VARCHAR NOT NULL DEFAULT 'pending',   -- 'pending' | 'processing' | 'retry' | 'done' | 'failed'
    retry_count   SMALLINT NOT NULL DEFAULT 0,
    last_error    TEXT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at     TIMESTAMPTZ NULL,
    locked_by     VARCHAR NULL
);

CREATE INDEX ix_rag_outbox_pending
    ON rag_indexing_outbox (status, created_at)
    WHERE status = 'pending';
```

`status='done'` rows are deleted by the same hourly purge sweep.

**Status lifecycle (corrects a prior doc/code drift — this is what `worker/rag_outbox_loop.py` actually does):** `_claim_batch` atomically sets `status='processing'` in the same UPDATE that sets `locked_at`/`locked_by` (a row is never left `pending` with a lock — "processing" is a real, directly-readable state, not something to infer). On failure, `_process_row` sets `status='retry'` (with `retry_count` incremented) while `retry_count < 3`, and only reaches `status='failed'` once `retry_count >= 3` — at which point `_claim_batch`'s `WHERE retry_count < 3` permanently excludes the row from ever being reclaimed automatically. No DB CHECK constrains these values (plain `VARCHAR`); the 5-state set (`pending`/`processing`/`retry`/`done`/`failed`) is enforced only by the worker/service code, matching `tests/unit/worker/test_rag_outbox_loop.py`.

### New table — `worker_heartbeats`

Worker liveness for the `/api/admin/system/workers` health endpoint. Stale rows (`last_seen > NOW()-INTERVAL '60s'`) flagged in the API response.

```sql
CREATE TABLE worker_heartbeats (
    worker_id   VARCHAR PRIMARY KEY,        -- hostname
    started_at  TIMESTAMPTZ NOT NULL,
    last_seen   TIMESTAMPTZ NOT NULL,
    job_id      UUID NULL                   -- currently-executing job, if any
);
```

### New table — `parent_quota_counters`

Application-layer rate gate for parents (challenger #15). APISIX rate limits are coarse; this is the authoritative gate.

```sql
CREATE TABLE parent_quota_counters (
    idp_sub             VARCHAR PRIMARY KEY,                    -- parent's idp_sub
    concurrent_jobs     INT NOT NULL DEFAULT 0,                 -- pending + extracting
    daily_jobs          INT NOT NULL DEFAULT 0,
    daily_window_start  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Caps:** `concurrent_jobs ≤ 5`, `daily_jobs ≤ 100`. Locked `FOR UPDATE` inside the POST handler TX. Counter row created on first parent upload.

### Extraction Business Rules

**BR-DATA-008 — Extraction materializes both a raw content row and text rows (supersedes the prior text-only rule):**
A successful job now materializes: (a) **one** raw content row (`content_type='pdf'` or `'image'`, matching `extraction_jobs.source_type`) pointing at a permanently-retained copy of the source file, and (b) the **N** extracted `content_type='text'` rows, one per page, as before. Both sets share the same `source_extraction_job_id`. The raw row's file path is stored in the existing **`url`** column — the same column `video` and manually-uploaded `pdf` rows already use — so no new storage column is added. Both the raw row and the text rows default to `visibility_status='draft'`; see BR-DATA-024 for how one is chosen to publish.

**Ordering:** the raw row is **appended after** the text rows (`order = N`, where text rows keep their existing `order = page_no`, 0-indexed). Text-row ordering is deliberately left untouched because `provenance.page_no` is derived directly from `topic_contents.order` (`TopicContentRepository._set_provenance`) — shifting text rows to make room at the front would silently renumber every provenance badge. Uploader UIs that want the raw form listed first should sort client-side rather than encode it in `order`.

**BR-DATA-009 — The job's working copy is transient; the audit and the published raw file are permanent:**
`extraction_jobs.source_path` — the job's own working-directory copy of the upload — and the `extraction_jobs` row itself are still purged per status TTL, unchanged by BR-DATA-008. This purge is independent of the permanent raw `topic_contents` row (content_type `'pdf'`/`'image'`), whose file is a separate copy made at finalize time and is never subject to this TTL — it persists until the content row itself is deleted. `extraction_job_audit` rows are **never purged** — they preserve provenance for materialized `topic_contents` regardless of which representation (raw or text) was ultimately published.

**BR-DATA-010 — Provenance is preserved across content deletes:**
Manually deleting a `topic_contents` row via `DELETE /api/topic-contents/{id}` does not cascade to `extraction_job_audit`. The audit retains "this job extracted N pages on date X by user Y" forever.

**BR-DATA-011 — Owner-type is re-validated by the worker:**
The worker re-reads `topics.owner_type` and `topics.owner_id` inside the finalize TX. Mismatch with `extraction_jobs.expected_owner_type` (and `created_by` for parent jobs) → `status='extraction_failed'`, `error_message='ownership_violation'`. Defence in depth — the API gate already enforces ownership at request time.

**BR-DATA-012 — `topic_contents.content_order` is base-shifted:**
On finalize, the worker computes `base = COALESCE(MAX(content_order), 0) FROM topic_contents WHERE topic_id = :t FOR UPDATE` and inserts new rows at `base + page_no`. Prevents collision with manually-added content and re-runs.

**BR-DATA-020 — Outbox re-enqueue is upsert-with-reset, not insert-only:**
Any code path that needs a `topic_contents` row (re-)embedded — instant text create, extraction finalize, or a `text`/`title` edit on a `text` row — calls the same helper: `INSERT INTO rag_indexing_outbox (content_id, status) VALUES (:id, 'pending') ON CONFLICT (content_id) DO UPDATE SET status='pending', retry_count=0, last_error=NULL, locked_at=NULL, locked_by=NULL`. This resolves the PK collision when a `done`/`failed` row still exists for that `content_id` (the purge sweep only clears `done` rows after 24h, so a same-day re-edit would otherwise hit the PK). `updated_at` is not in the `SET` list — the existing `trg_rag_outbox_touch` BEFORE UPDATE trigger (V26) stamps it. Non-text content types (`video`, `url`) are never enqueued.

**BR-DATA-023 — Manual indexing retry reuses BR-DATA-020's upsert-with-reset, not a new insert path (Phase 6 — Parent Indexing Visibility):**
Before this rule, the only way to escape a permanently `failed` (`retry_count >= 3`) outbox row was the side-effect of re-saving the content's `text`/`title`. `POST /api/parent/curriculum/topic-contents/{content_id}/retry-indexing` exposes that same upsert-with-reset SQL as an explicit, owner-scoped, user-triggered action — no new enqueue logic, no new columns. Owner-scoped: 404 if `content_id` does not resolve to a `topic_contents` row under a topic owned by the calling parent (oracle protection, same pattern as BR-PAR-006). Abuse guard: reject with 429 if `rag_indexing_outbox.updated_at` for this `content_id` is inside a short cooldown window (e.g. 30s) — deliberately not routed through `parent_quota_counters`, which is scoped to `extraction_jobs` concurrency, a different resource. See `target/requirements/05_parent.md` P-topic for the parent-facing status-pill UI this unblocks. Platform-owned content has the identical invisible-failure gap and is **not** addressed by this rule — tracked as a follow-up for `target/requirements/07_platform_admin.md`.

**BR-DATA-021 — Chunk cleanup is delete-before-insert, not update-in-place:**
`data_topic_content_chunks` has no per-row update path — a re-embed always deletes the existing chunk set for a `content_id` (`DELETE FROM data_topic_content_chunks WHERE metadata_->>'content_id' = :cid`, raw SQL against the LlamaIndex-owned table) before `index.insert_nodes()` writes the new set. This applies both when the worker drains a re-enqueued (BR-DATA-020) outbox row and when a `topic_contents` row is deleted outright, in which case the outbox row for that `content_id` is deleted alongside the chunks (same TX as the content delete) instead of being left to drain. **Accepted v1 gap:** between the delete and the subsequent insert, a concurrent hAITU retrieval against that `content_id` sees zero chunks rather than the old or new set — a brief availability gap, not a correctness gap (no duplicate/orphaned vectors ever visible). No retry-side special-casing; re-running a drain against a `content_id` that already has chunks is idempotent because the delete always runs first.

**BR-DATA-022 — RAG cleanup cascades with the owning topic/node:**
Deleting a topic, or a `course_path_nodes` subtree, deletes every embedded `topic_contents` row's chunks and outbox row (BR-DATA-021's cleanup, applied per `content_id` in the subtree) inside the same cascade transaction as the topic/node delete. No orphaned chunks or outbox rows can outlive their owning topic.

**BR-DATA-024 — Publish is a per-upload, mutually exclusive choice between raw and extracted (Content Viewing & Publish):**
For a PDF/Image upload, the uploader (platform admin or parent, matching the topic's `owner_type`) publishes **either** the single raw row **or** the full set of extracted text rows sharing that upload's `source_extraction_job_id` — never both at once. Setting one side's `visibility_status='published'` requires the other side's rows to be (or be set to) `'draft'`. Enforced at the service/API layer only, no DB constraint — same precedent as `topics.status` having no DB CHECK. Typical case: raw is published because the source is a well-formatted document (e.g. a textbook page) that should be shown as-is; the extracted-text side is published instead only when the raw source is low-quality (e.g. a poor scan) and the uploader edits the extracted text into something more readable. Video and Text content types have no raw/extracted duality (the stored value already is the one representation) — they use the same `visibility_status` column directly, with no mutual-exclusivity rule to enforce.

**Grouping key:** an upload group is `(topic_id, source_extraction_job_id)` where `source_extraction_job_id IS NOT NULL`. A row with `source_extraction_job_id IS NULL` — every manually-created video/text row, and any legacy row — is **its own group of one**, never grouped with other NULL rows. Implementations must not `GROUP BY source_extraction_job_id` without excluding NULLs, or every manual row on a topic collapses into a single false group. The grouping survives `extraction_jobs` TTL purge (BR-DATA-009) because `source_extraction_job_id` is a soft reference with no FK.

**BR-DATA-025 — Student content visibility gains a content-item gate (companion to BR-DATA-003, does not replace it):**
BR-DATA-003 gates visibility at the topic/node/exam level (`owner_type` + `parent_child_links`). This increment adds one more AND-condition underneath it, applied uniformly to **every** `content_type`: a student sees a `topic_contents` row only when `topics.status='live'` **and** `topic_contents.visibility_status='published'`. Rows still in `'draft'` are invisible to students even inside an otherwise-live topic. (The `contenttype` enum also carries `question` and `question_answer`, which are dead values — declared in `domain/models/topic_content.py` and referenced nowhere else in the backend. They inherit the gate by default like any other value; no special-casing.)

This is orthogonal to `rag_indexing_outbox.status` (BR-PAR-020/BR-DATA-023) — indexing status governs hAITU search-groundedness, not student-facing visibility, and the two are deliberately decoupled: extraction's primary purpose is RAG, so every extracted `content_type='text'` row is enqueued at creation time **regardless of its own `visibility_status`** (extraction is why it exists, not whether a student can currently see it) — a text row kept in `'draft'` as the unpublished fallback (because the raw form was published instead, BR-DATA-024) is still searchable by hAITU.

**No enqueue change is required for the new raw rows.** BR-DATA-020's prose frames non-text types as an exclusion list, but the implemented gate is an *allowlist* — `TopicContentService` enqueues only when `content_type == ContentType.text`, and the extraction worker enqueues only the text rows it materializes. `pdf` and `image` are therefore already excluded by construction, published or not. (BR-DATA-020's parenthetical "`video`, `url`" names a `url` content type that does not exist in the enum; left as-is rather than renumbered, but do not propagate it.)

---

## Schema Extensions (Essay AI Grading)

> Full behaviour and business rules in `target/requirements/08_essay_ai_grading.md`. This section
> defines the storage shape and the grading-status state machine.

All columns are additive — nothing is dropped or renamed. Migration: **V29**.

### New columns on `questions`

```sql
ALTER TABLE questions
  ADD COLUMN rubric          JSONB    NULL,
  ADD COLUMN model_answer    TEXT     NULL,
  ADD COLUMN auto_grade_essay BOOLEAN NOT NULL DEFAULT true;
```

| Column | Type | Default | Notes |
|---|---|---|---|
| `rubric` | JSONB | NULL | Analytic rubric definition (see `08_essay_ai_grading.md` § Rubric Model). NULL → use default rubric by `essay_subtype`. Only meaningful for `essay` questions. |
| `model_answer` | TEXT | NULL | Reference answer / key points; passed to the LLM as grading context. Optional even when `rubric` is set. |
| `auto_grade_essay` | BOOLEAN | `true` | When `false`, essay question is skipped by the AI grading pipeline and stays `pending` for manual grading. Allows a creator to opt out of AI grading per-question. |

**Migration:** no backfill required. Existing essay questions default to `auto_grade_essay = true`
(AI grading will run when the worker is deployed).

### New column on `exam_templates`

```sql
ALTER TABLE exam_templates
  ADD COLUMN essay_grading_mode VARCHAR NOT NULL DEFAULT 'auto_release'
    CHECK (essay_grading_mode IN ('auto_release', 'review_first'));
```

| Column | Type | Default | Notes |
|---|---|---|---|
| `essay_grading_mode` | VARCHAR | `'auto_release'` | `auto_release` → AI score released to student immediately after grading. `review_first` → score held until owner confirms. Applies to all essay questions in this template. |

**Migration:** `UPDATE exam_templates SET essay_grading_mode = 'auto_release';`

### New columns on `exam_session_questions`

```sql
ALTER TABLE exam_session_questions
  ADD COLUMN ai_score         FLOAT      NULL,
  ADD COLUMN ai_feedback      TEXT       NULL,
  ADD COLUMN ai_rationale     JSONB      NULL,
  ADD COLUMN grader_confidence FLOAT     NULL,
  ADD COLUMN grading_status   VARCHAR    NOT NULL DEFAULT 'pending'
                               CHECK (grading_status IN (
                                 'pending', 'ai_graded', 'released', 'disputed',
                                 'finalized', 'overridden', 'error'
                               )),
  ADD COLUMN graded_by        VARCHAR    NULL,
  ADD COLUMN graded_at        TIMESTAMPTZ NULL,
  ADD COLUMN override_score   FLOAT      NULL,
  ADD COLUMN override_feedback TEXT      NULL;
```

| Column | Type | Default | Notes |
|---|---|---|---|
| `ai_score` | FLOAT | NULL | LLM-computed score, scaled to `points`. Computed by backend from per-criterion levels. |
| `ai_feedback` | TEXT | NULL | Student-facing narrative feedback (1–5 sentences). |
| `ai_rationale` | JSONB | NULL | Per-criterion levels + justifications. Owner/debug view only; not returned to student. |
| `grader_confidence` | FLOAT | NULL | Model confidence `[0, 1]`; future use for auto-flagging. |
| `grading_status` | VARCHAR | `'pending'` | State machine — see below. Applies only to `essay` questions; non-essay rows stay at `'pending'` (ignored). |
| `graded_by` | VARCHAR | NULL | Model spec string (e.g. `qwen3:14b`) when AI-graded; owner `idp_sub` when manually overridden. |
| `graded_at` | TIMESTAMPTZ | NULL | When grading (AI or override) was applied. |
| `override_score` | FLOAT | NULL | Owner's override score. If set, `earned_points = override_score`. |
| `override_feedback` | TEXT | NULL | Owner's override feedback shown to student instead of `ai_feedback`. |

**Note:** The existing `earned_points` column holds the **final authoritative score** used for
session totals. It is written only when the essay reaches a terminal graded state (released,
finalized, overridden). While an essay is pending or held, `earned_points` remains NULL and is
excluded from `exam_sessions.score`.

**Migration:** no backfill required.

### New table — `essay_grading_jobs`

```sql
CREATE TABLE essay_grading_jobs (
    id                       UUID PRIMARY KEY,
    exam_session_question_id UUID        NOT NULL,  -- soft FK to exam_session_questions.id
    status                   VARCHAR     NOT NULL DEFAULT 'queued',
                                                    -- 'queued' | 'processing' | 'done' | 'error'
    attempts                 INT         NOT NULL DEFAULT 0,
    last_error               TEXT        NULL,
    grading_model            VARCHAR     NULL,      -- model spec used (set on processing start)
    locked_at                TIMESTAMPTZ NULL,      -- worker lock timestamp
    locked_by                VARCHAR     NULL,      -- worker hostname
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_essay_grading_jobs_queue
    ON essay_grading_jobs (status, created_at)
    WHERE status = 'queued';
CREATE INDEX ix_essay_grading_jobs_session_question
    ON essay_grading_jobs (exam_session_question_id);

CREATE TRIGGER trg_essay_grading_jobs_touch BEFORE UPDATE ON essay_grading_jobs
    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
```

**One job per dispute/re-grade:** If a student disputes and the owner triggers a re-grade, a new
`essay_grading_jobs` row is inserted. The previous `done` job row is retained for audit. The
`exam_session_question_id` is not unique — multiple job rows per question are allowed.

### grading_status state machine

```
auto_release mode:
  pending → ai_graded → released  ← student sees score + feedback
                             ↓
                         disputed  ← student disputes (POST .../dispute)
                         ↙       ↘
               finalized         overridden
           (confirm-grade)     (PATCH .../grade)

review_first mode:
  pending → ai_graded  ← score held, student sees "Pending review"
              ↙       ↘
        finalized    overridden
    (confirm-grade)  (PATCH .../grade, directly)

Error path (any mode):
  pending → error  ← after 3 failed grading attempts
  (essay stays ungraded; owner sees "Grading unavailable"; session score excludes essay)
  (owner can recover via PATCH .../grade override from error state)
```

**Terminal states:** `released`, `finalized`, `overridden`, `error` — no further automatic
transitions. An owner can call the override endpoint (`PATCH .../grade`) from any non-`pending`
state, including `error`. `confirm-grade` is accepted from `'ai_graded'` (review_first) or
`'disputed'` (auto_release after dispute).

### Score-mapping formula

```
ai_score = Σ(level_i / scale_max × weight_i) × max_points
```

- Computed by the backend worker (never by the LLM).
- Clamped to `[0, max_points]` before storage.
- `earned_points` is set to `ai_score` on `released`/`finalized`, or to `override_score` on
  `overridden`.
- `is_correct = (earned_points / points >= 0.5)` (50% threshold for consistency with other
  question types).

### Essay Grading Business Rules

**BR-DATA-013 — AI grading is async:**
`POST /session/{id}/submit` enqueues a job but does not wait for grading. The submit response
returns immediately; `grading_status = 'pending'` until the worker processes the job.

**BR-DATA-014 — Blank answers bypass the LLM:**
`user_answer` that is NULL or `len(strip()) < 10` is scored `0` immediately without a worker job.
`ai_feedback = "No answer was submitted."` No `essay_grading_jobs` row is inserted.

**BR-DATA-015 — Error state is never a silent zero:**
A grading job that exhausts all retries sets `grading_status = 'error'`. `earned_points` remains
NULL. The session score excludes the essay. The owner is responsible for manually overriding if
they want a score assigned.

**BR-DATA-016 — Override rewrites earned_points and recomputes session score:**
`PATCH .../grade` writes `override_score` to `earned_points`, sets `is_correct`, and atomically
updates `exam_sessions.score = SUM(earned_points) WHERE session_id = :sid`.

**BR-DATA-017 — Rubric is resolved at grading time:**
The worker reads `question.rubric` at the time the job is processed. Changes to a question's rubric
after submission do not affect already-graded essays. A re-grade (new job after dispute) uses the
current rubric at that time.

**BR-DATA-018 — `auto_grade_essay = false` questions are never enqueued:**
If `question.auto_grade_essay = false`, no `essay_grading_jobs` row is inserted at submit time.
`grading_status` stays `'pending'` indefinitely — the owner must override manually.

**BR-DATA-019 — `graded_by` audit trail is immutable after override:**
Once `graded_by` is set (by AI or owner), it is never cleared. Each override appends to an
`overrides` array in `ai_rationale` (JSONB in-place, not a separate table in Phase 1).

`ai_rationale` shape after initial AI grading:
```json
{
  "per_criterion": [
    { "id": "thesis", "level": 3, "justification": "..." },
    { "id": "evidence", "level": 2, "justification": "..." }
  ],
  "confidence": 0.82,
  "overrides": []
}
```

Each owner override appends to `overrides`:
```json
{
  "overrides": [
    {
      "score": 7.5,
      "feedback": "Good effort, minor factual error.",
      "graded_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "graded_at": "2026-06-08T14:22:00Z"
    }
  ]
}
```

Append using `jsonb_set(ai_rationale, '{overrides}', (ai_rationale->'overrides') || new_entry)`.
If `ai_rationale` is NULL at override time (e.g., blank-answer path), initialise to `{"overrides": [new_entry]}`.

---

## Schema Extensions (Phase 3 — Student Enrollment)

Migration V34. All columns and tables are additive — nothing is dropped or renamed.

> **V35 (doubts + doubt_messages) deferred to Phase 4.** Phase 3 hAITU chat is session-only (client-side); nothing is written to the database. The doubts schema will be introduced alongside teacher escalation endpoints once the teacher role is active in Keycloak.

### New table — `student_enrollments` (V34)

Students self-enroll in platform course nodes. The enrollment record scopes what the student can access and is required for hAITU.

```sql
CREATE TABLE student_enrollments (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_sub         TEXT        NOT NULL,
    course_path_node_id UUID        NOT NULL REFERENCES course_path_nodes(id) ON DELETE CASCADE,
    enrolled_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    enrollment_source   VARCHAR(20) NOT NULL DEFAULT 'self',
    UNIQUE (student_sub, course_path_node_id)
);

CREATE INDEX idx_student_enrollments_student_sub ON student_enrollments(student_sub);
```

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `student_sub` | TEXT | Keycloak `sub` (no FK — identity is IdP-managed) |
| `course_path_node_id` | UUID | The node the student enrolled in. Any node level (grade, subject, course). Access extends to all descendant topics. |
| `enrolled_at` | TIMESTAMPTZ | Enrollment timestamp |
| `enrollment_source` | VARCHAR(20) | `'self'` (student self-enrolled), `'platform_admin'` (admin enrolled), `'parent'` (parent enrolled on behalf) |

**Access rules:**
- A student has access to all topics whose `course_path_node_id` is a descendant-or-equal of any enrolled `course_path_node_id`.
- Enrollment at grade level grants access to all subjects and courses under that grade.
- Enrollment does not expire — currently no `revoked_at` column. Unenroll = DELETE the row.
- hAITU `enrollment_id` field references this table. BR-AI-005 verifies the topic is within the enrolled subtree.

**Recommendation algorithm (Phase 3):**
When a student has no enrollments, `GET /api/student/catalog` returns all available platform nodes with a `recommended: true` flag on nodes whose ancestor grade node matches `student_profiles.grade`. No ML — grade string match only. Students browse the catalog and self-enroll.

---

### New tables — `doubts` + `doubt_messages` (V35 — deferred to Phase 4)

> **Deferred.** Phase 3 hAITU is fully stateless — no doubt records are written. The schema below is the intended design for Phase 4 when teacher escalation is introduced (requires teacher role in Keycloak).

```sql
-- Phase 4 only — do not create in Phase 3 migrations
CREATE TABLE doubts (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_sub      TEXT        NOT NULL,
    topic_id         UUID        NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    enrollment_id    UUID        NOT NULL REFERENCES student_enrollments(id) ON DELETE CASCADE,
    haitu_attempted  BOOLEAN     NOT NULL DEFAULT FALSE,
    status           VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_doubts_student_topic ON doubts(student_sub, topic_id, status);

CREATE TABLE doubt_messages (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    doubt_id     UUID        NOT NULL REFERENCES doubts(id) ON DELETE CASCADE,
    sender_type  VARCHAR(10) NOT NULL,  -- 'student' | 'ai' | 'teacher'
    content      TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_doubt_messages_doubt_id ON doubt_messages(doubt_id);
```

**Phase 4 behaviour (when introduced):**
- Find or create a `doubts` record per `(student_sub, topic_id, enrollment_id)`.
- AI responses saved as `doubt_messages(sender_type='ai')`.
- `escalation_ready=true` sets `doubts.haitu_attempted=true`.
- Teacher reply, escalation endpoint `POST /api/doubts/{id}/escalate`, and notification triggers introduced in Phase 4 alongside teacher Keycloak role.

**BR-DATA-008 — Doubt privacy (Phase 4):** Only the student who created a `doubts` row may read its messages. Teachers may read only escalated doubts assigned to them. No cross-student doubt access.

---

### New tables — `review_chat_threads` + `review_chat_messages` (Phase 7 G3.2 — designed, migration pending T3.2.2)

> **Designed, not yet migrated.** `exam-review-chat` is fully stateless today — `haitu.py:838-845`
> reads `body.history[-10:]` and persists nothing (`_PATTERN_ANALYSIS_CACHE` is an in-memory,
> per-worker cache for the sibling `pattern-analysis` endpoint, not a persistence layer). This
> section is T3.2.1's design output; the table below is the target for T3.2.2's migration.

**Why not reuse `doubts`/`doubt_messages`:** `doubts` is keyed on `(student_sub, topic_id)` and
carries a teacher-escalation lifecycle (`status`, `escalated_to`, `auto_close_at`,
`sender_type ∈ (student, ai, teacher, system)`). `exam-review-chat` is keyed on `attempt_id`
(`exam_sessions.id` — an attempt can span many topics), is student-only with no escalation path,
and never expires. Forcing it into `doubts`' shape would carry six lifecycle states and an
auto-close SLA that never apply, and require attempt-aware guards on every teacher-queue query to
keep review-chat rows out.

```sql
CREATE TABLE review_chat_threads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id  UUID NOT NULL REFERENCES exam_sessions(id),  -- no ON DELETE, matches
                                                               -- exam_session_questions precedent
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (attempt_id)
);

CREATE TABLE review_chat_messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id    UUID NOT NULL REFERENCES review_chat_threads(id) ON DELETE CASCADE,
    sender_type  VARCHAR(10) NOT NULL,       -- 'student' | 'ai'
    is_seed      BOOLEAN NOT NULL DEFAULT FALSE,
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (sender_type IN ('student', 'ai'))
);

CREATE INDEX idx_review_chat_messages_thread_id ON review_chat_messages(thread_id);
```

| Column | Notes |
|---|---|
| `review_chat_threads.attempt_id` | `UNIQUE` — one thread per exam attempt, always reused, never closed. Verified `exam_sessions` has no unique constraint on `(user_id, exam_template_id)`, so every retake gets a fresh row/PK and therefore a fresh thread. |
| `review_chat_messages.is_seed` | `TRUE` only for the opening message written by `pattern-analysis` (see below). Lets a `GET` filter it out so the frontend's existing seed-then-replace-on-first-token UI (§8.8 of `11_haitu_ai_layer.md`) needs no change. |

**Persistence contract (for T3.2.3):**
- `pattern-analysis` owns the seed write — `find_or_create_by_attempt(attempt_id)` then
  `add_message(thread_id, sender_type='ai', is_seed=true, content=...)`, on both the
  zero-wrong-answers neutral-message path (request session) and the real LLM-compute path (fresh
  session, post-stream). It does **not** read from `_PATTERN_ANALYSIS_CACHE` to seed the thread —
  that cache is per-worker (`--workers 2` deployed) and would silently drop or double-charge the
  rate limiter on a cross-worker miss.
- `exam-review-chat`'s student message is written **after** the `HaituRateLimiter` check succeeds
  (orphan-on-429 — a 429 must create zero rows, same guarantee as `topic-doubt` §5.1), before the
  request session closes. The AI reply is written by a post-stream background task on a fresh
  session, mirroring `topic-doubt`'s `_generate_events`/`finalize_ai_response` pattern.
- `find_or_create_by_attempt` must be `INSERT ... ON CONFLICT (attempt_id) DO NOTHING RETURNING
  id`, re-selecting on no row returned — **not** select-then-insert. Unlike `doubts` (no unique
  constraint, tolerates a duplicate row on a race), `review_chat_threads.attempt_id` is `UNIQUE`,
  and both `pattern-analysis` and `exam-review-chat` can race to create the same thread on a
  normal S05 page load (pattern-analysis fires on load; the student can start typing immediately).
  A naive insert would surface that race as a 500.
- Thread reads (`GET /api/haitu/exam-review-chat/{attempt_id}`, T3.2.3a) filter `is_seed = false`
  and order by `(created_at, id)`.

---

## Schema Extensions (Phase 4 G4 — Mastery + Enrollment Topics)

Migration **V37**. All columns and tables are additive — nothing is dropped or renamed.
> Behaviour and business rules in `target/requirements/04_teacher_tutor.md` (BR-TCH-004) and
> the mastery algorithm in `Implementation_planning/PLAN.md` (T4.2.1a).

### Locked decisions (2026-06-28 reconcile)

- **`questions.topic_id` is added NULLABLE.** NOT NULL is not enforceable: legacy rows have
  no topic linkage and there is no clean backfill source. The application layer **requires**
  `topic_id` for newly created questions; legacy rows stay NULL and mastery recalc skips
  them (BR-PROGRESS edge case c). Added in V37:
  ```sql
  ALTER TABLE questions ADD COLUMN topic_id UUID NULL;
  CREATE INDEX ix_questions_topic_id ON questions(topic_id);
  ```
  No backfill. A B-tree index supports the per-topic attribution query.
- **`exam_templates.topic_id` is NOT added.** The vision spec places `topic_id` on
  `exam_templates` (BR-EXAM-PURPOSE-001), but G4 needs per-question topic attribution for
  multi-topic exams, which only `questions.topic_id` provides. `questions.topic_id` is the
  single source of truth for mastery attribution and works for both quiz (single-topic) and
  exam (multi-topic) purposes. Quiz scoping resolves via `questions.topic_id` uniformly.
- **Enforcement (2026-07-01, G4.1 T4.1.4).** The "application layer requires `topic_id` for newly
  created questions" mandate is enforced **in the UI** (the exam builder's per-question Topic
  dropdown — see `07_platform_admin.md`), not as a hard 422 at the API boundary. `topic_id` is
  optional on `QuestionItemV2` / `StaticQuestionPatchItem` (`UUID4 | None = None`) so legacy rows,
  JSON-imported exams, and programmatic/test creation keep working; NULL-topic questions are
  skipped by mastery recalc, not rejected. The exam-builder create/patch routes
  (`POST`/`PATCH /api/exams/{node_id}/static`) carry `topic_id` end-to-end (schema →
  `QuestionExtras` → `Question` row), and `GET .../questions-with-details` returns it for
  edit-hydration. (T4.1.1 / T4.1.3b originally marked this done but only covered the column +
  domain/repo — the creation path itself is wired by T4.1.4; see `decisions.md` 2026-07-01.)

### New column on `questions` (V37)

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `topic_id` | UUID | NULL | Soft pointer to `topics(id)` (no hard FK — attribution is advisory; legacy rows are NULL). The single source of truth for mastery attribution. Required by the application layer for newly created questions. |

### New table — `enrollment_topics` (V37)

Tracks a student's per-topic progress within a `student_enrollments` context. The FK target is
`student_enrollments(id)` (V34, `UNIQUE(student_sub, course_path_node_id)`) — **NOT** the vision
spec's nonexistent `enrollments` table.

```sql
CREATE TABLE enrollment_topics (
    id                     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_enrollment_id  UUID        NOT NULL REFERENCES student_enrollments(id) ON DELETE CASCADE,
    topic_id               UUID        NOT NULL REFERENCES topics(id),
    status                 VARCHAR(10) NOT NULL CHECK (status IN
                                         ('not_started','in_progress','completed','weak')),
    mastery_score          FLOAT       NULL CHECK (0 <= mastery_score <= 100),
    last_studied_at        TIMESTAMPTZ NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (student_enrollment_id, topic_id)
);

CREATE INDEX idx_enrollment_topics_enrollment ON enrollment_topics(student_enrollment_id);
CREATE INDEX idx_enrollment_topics_topic_status ON enrollment_topics(topic_id, status);
```

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `student_enrollment_id` | UUID | FK → `student_enrollments(id)` (CASCADE). The enrollment context that scopes this progress row. |
| `topic_id` | UUID | FK → `topics(id)`. The topic this progress row tracks. |
| `status` | VARCHAR(10) | `'not_started'` \| `'in_progress'` \| `'completed'` \| `'weak'`. Derived from `mastery_score` on recalc (BR-PROGRESS-001/002/003). |
| `mastery_score` | FLOAT | `0.0`–`100.0`, NULL until the first attempt. |
| `last_studied_at` | TIMESTAMPTZ | Updated on each mastery recalc for this topic. |
| `created_at` / `updated_at` | TIMESTAMPTZ | Row timestamps. |

### New table — `student_risk_state` (V37)

Persistence backing for the `student_at_risk` recovery/re-fire gate (BR-TCH-004). Folded into V37
so no second migration is needed. No FK on `student_sub` (sacred no-FK-on-identity rule).

```sql
CREATE TABLE student_risk_state (
    student_sub      TEXT        PRIMARY KEY,
    at_risk_active   BOOLEAN     NOT NULL DEFAULT FALSE,
    last_fired_at    TIMESTAMPTZ NULL
);
```

| Column | Type | Notes |
|---|---|---|
| `student_sub` | TEXT | Keycloak `sub` (no FK — identity is IdP-managed). |
| `at_risk_active` | BOOLEAN | `true` while a `student_at_risk` state is active (≥3 weak topics); set `false` when `count_weak_for_student == 0`. |
| `last_fired_at` | TIMESTAMPTZ | When the `student_at_risk` notification last fired. |

### Mastery progress business rules

**BR-PROGRESS-001 — Weak topic:** A topic is `weak` if `mastery_score < 60.0` after at least one
quiz/exam attempt (`exam_sessions` with `status = 'completed'` for a template scoped to this
topic). Status set to `'weak'`.

**BR-PROGRESS-002 — Completed topic:** A topic is `completed` if `mastery_score >= 75.0` and at
least one attempt submitted. Status set to `'completed'`.

**BR-PROGRESS-003 — Mastery recalculation:** On the **first attempt**, `mastery_score =
latest_score` (raw score directly). From the **second attempt onward**, `mastery_score =
(latest_score * 0.6) + (previous_mastery * 0.4)`. This prevents false weak-topic flags from a
single attempt (e.g. scoring 80% would give mastery 48% if `previous_mastery` defaulted to 0).
Attempts are tracked via `exam_sessions` (both `purpose = 'quiz'` and `purpose = 'exam'`
contribute to mastery). Status is re-derived from the recomputed `mastery_score` per
BR-PROGRESS-001/002; scores in [60, 75) set `'in_progress'`.

**Edge-case rules (apply to all mastery recalc):**
- (a) Essay questions with NULL `earned_points` while grading is pending are **skipped** by the
  recalc and computed from the remaining available points. If **all** questions are pending
  (recalc has nothing to compute), the recalc is deferred to the essay-grading auto-complete hook
  (T4.2.1c) — no `enrollment_topics` row is written on this pass.
- (b) The first attempt creates the `enrollment_topics` row (status derived from score;
  `mastery_score = latest_score`).
- (c) Questions with NULL `topic_id` are **excluded** from per-topic attribution (legacy /
  unlinked rows).
- (d) Multi-topic exams attribute each question via `questions.topic_id` — each question's
  earned/max points feed the per-topic score of its own topic, not a single session-wide score.

---

## Schema Extensions (Phase 5 — Parent Curriculum Builder)

Migration **V40**. Additive only — no backfill, nothing dropped or renamed.
> Behaviour in `target/requirements/05_parent.md` (Adopt modal, P-curriculum, P-topic).

### New column on `course_path_nodes` (V40)

```sql
ALTER TABLE course_path_nodes ADD COLUMN source_node_id UUID NULL;

CREATE UNIQUE INDEX ux_course_path_nodes_adopt_lineage
  ON course_path_nodes (owner_id, source_node_id)
  WHERE source_node_id IS NOT NULL;
```

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `source_node_id` | UUID | NULL | Set only on the root node of a cloned subtree — points at the platform `course_path_nodes.id` it was adopted from. NULL for every other row (platform rows, non-root clones, scratch-built parent nodes). |

**Adopt-idempotency mechanics (BR-DATA-006):** only the cloned root carries `source_node_id`; the rest of the cloned subtree (and its topics) carries none. The partial unique index on `(owner_id, source_node_id)` means a given parent can adopt a given platform source node exactly once — a repeat `POST /api/parent/curriculum/adopt` with the same `source_node_id` hits the index and the service raises `AlreadyAdoptedError`, mapped to `409 Conflict` at the route. No application-side existence check races the DB — the index is the source of truth.

### Parent-tree hierarchy rules (application layer, `ParentCurriculumService`)

Not new columns, but validation rules load-bearing for `POST /api/parent/curriculum/nodes` and worth recording alongside V40 since they gate what adopt/scratch-build can produce:

- **Category rule for scratch roots:** a root node (`parent_id IS NULL`) must have `node_type = 'grade'` and requires a `category_id` (`400` if missing on a root create). Child nodes derive `category_id` from their owner-scoped parent — never supplied directly.
- **Depth-typing:** a node directly under a `grade` must be `node_type = 'subject'`; deeper nodes must not repeat any ancestor's `node_type` (checked via `get_path_to_root`).
- **Sibling-type consistency, scoped per-owner:** among a parent's existing children of the same node, all must share one established `node_type` — a create that would introduce a second type among siblings is rejected (`409`, `NodeHierarchyError`). This check is scoped to the caller's own rows (`get_children_by_parent_and_owner`) and is independent of whatever sibling types might exist under the same parent node for other owners.
- These rules apply only to parent-owned trees built via `POST /api/parent/curriculum/nodes`; adopted subtrees are cloned verbatim from an already-valid platform subtree and are not re-validated node-by-node.
