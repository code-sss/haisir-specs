# Data Model

> **Target state scope:** Student, Parent, Platform Admin. See `vision/requirements/01_data_model.md` for the full vision schema.

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
- `topic_contents` → ~~`topic_content_chunks`~~ **superseded** — the RAG service's `rag_chunks` table covers this and more (multi-source, BM25, metadata JSONB, ownership). `topic_content_chunks` will not be created.

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
| `status` | VARCHAR | NOT NULL, DEFAULT `'live'` | `'draft'` \| `'live'` \| `'archived'` |

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
- **Not cloned:** `topic_contents`, `topic_content_chunks`, `questions`, `exam_templates`, `exam_template_questions`. Parent populates their own content and exams after adoption.
- Platform updates to the original board do **not** propagate to parent copies. Each parent copy is independent.

**BR-DATA-006 — Adopt is idempotent per grade-subject:**
If a parent has already adopted the same subtree, a second adopt request returns 409 Conflict rather than creating duplicate nodes.

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
| `essay` | Manual | `essay_subtype` is a rendering hint (see valid values below); no grading impact |
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

### 1 column added to existing `topic_contents` (additive, nullable)

```sql
ALTER TABLE topic_contents
  ADD COLUMN source_extraction_job_id UUID NULL;
```

| Column | Type | Constraint | Notes |
|---|---|---|---|
| `source_extraction_job_id` | UUID | NULL | Soft pointer (no FK per CLAUDE.md identity convention). Set only for rows materialized by an extraction job. Joins to `extraction_job_audit.job_id` for provenance display. |

**Migration:** No backfill required. Existing rows remain `NULL`.

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
    status        VARCHAR NOT NULL DEFAULT 'pending',   -- 'pending' | 'done' | 'failed'
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

**BR-DATA-008 — Extraction produces text-only content:**
A successful job materializes `topic_contents` rows with `content_type='text'` only. The source PDF/image is **not** stored as a `topic_contents` row. No new `content_type` enum value is added.

**BR-DATA-009 — Source files are transient; audit is permanent:**
`extraction_jobs.source_path` files and `extraction_jobs` rows are purged per status TTL. `extraction_job_audit` rows are **never purged** — they preserve provenance for materialized `topic_contents`.

**BR-DATA-010 — Provenance is preserved across content deletes:**
Manually deleting a `topic_contents` row via `DELETE /api/topic-contents/{id}` does not cascade to `extraction_job_audit`. The audit retains "this job extracted N pages on date X by user Y" forever.

**BR-DATA-011 — Owner-type is re-validated by the worker:**
The worker re-reads `topics.owner_type` and `topics.owner_id` inside the finalize TX. Mismatch with `extraction_jobs.expected_owner_type` (and `created_by` for parent jobs) → `status='extraction_failed'`, `error_message='ownership_violation'`. Defence in depth — the API gate already enforces ownership at request time.

**BR-DATA-012 — `topic_contents.content_order` is base-shifted:**
On finalize, the worker computes `base = COALESCE(MAX(content_order), 0) FROM topic_contents WHERE topic_id = :t FOR UPDATE` and inserts new rows at `base + page_no`. Prevents collision with manually-added content and re-runs.
