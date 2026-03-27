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
- `topic_contents` → `topic_content_chunks` (pgvector, for hAITU RAG — future)

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
- `parent_idp_sub` (UUID string) — the parent's `idp_sub`
- `child_idp_sub` (UUID string) — the student's `idp_sub`
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
