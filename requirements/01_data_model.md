# hAIsir — Data Model
> Version 1.1 | Updated to reflect actual baseline schema from `haisir_current.md`.
> Existing tables are documented as-is. New tables are marked ❌ NEW.
> All tables are PostgreSQL. Migrations managed by Alembic.
> → Depends on: `00_overview.md`

---

## 1. Identity Convention

There is **no local `users` table**. All user identity comes from Keycloak.

Every table that references a user stores a raw UUID from the Keycloak JWT `sub` claim. There are **no foreign key constraints** on these columns — Keycloak is the authority. This is an existing design decision in the baseline and must be maintained.

---

## 2. Existing Schema (baseline — do not drop or restructure these tables)

The following tables exist in the current production database. They are documented here for reference. New features must extend these, not replace them.

### 2.1 Content Hierarchy

```
categories
  └── course_path_nodes   (self-referential tree: grade → subject → course)
        └── topics
              └── topic_contents   (PDF, video, text)
```

> **Terminology:** The UI and persona specs use the word "board" (e.g. "board content", "board adoption", "board management"). A "board" maps directly to a `categories` row — there is no separate `boards` table. `categories` is the canonical table name in the database.

> **Note on existing tables:** The backend implementation is the authority on exact column names if any discrepancy arises. Schemas below are inferred from existing spec references and API contracts.

**`categories`** — top-level board groupings (e.g. "NCERT", "CBSE", "JNV"). Referenced as FK in `organizations.primary_board_category_id` and `board_adoptions.category_id`.

```python
class Category(BaseModel):
    id: UUID
    name: str           # e.g. "NCERT", "CBSE", "JNV"
    path_type: str      # 'structured' | 'flexible' (Enum: PathType)
    description: str | None
```

**`course_path_nodes`** — self-referential tree representing the full curriculum hierarchy from grade down to course level.

```python
class CoursePathNode(BaseModel):
    id: UUID
    parent_id: UUID | None      # self-referential; null = root node under a category
    category_id: UUID           # FK → categories (the board this node belongs to)
    name: str
    node_type: str              # e.g. 'grade', 'subject', 'course' (Enum: NodeType)
    order: int | None           # nullable in existing schema
    # Extended columns (section 3.1 — added via ALTER TABLE):
    owner_type: str             # 'platform' | 'institution' | 'tutor'
    owner_id: UUID | None       # org_id or keycloak_sub; null for platform-owned
```

> Extension required: see section 3.1 for the `owner_type` / `owner_id` ALTER TABLE migration.

**`topics`** — leaf nodes within a `course_path_node`. Each topic is a specific study unit (e.g. "Fractions").

```python
class Topic(BaseModel):
    id: UUID
    course_path_node_id: UUID   # FK → course_path_nodes
    title: str                  # NOTE: column is 'title', not 'name'
    order: int | None           # nullable in existing schema; NOTE: column is 'order', not 'order_index'
    # Extended columns (section 3.2 — added via ALTER TABLE):
    status: str                 # 'draft' | 'live' | 'archived'
    owner_type: str             # 'platform' | 'institution' | 'tutor'
    owner_id: UUID | None       # org_id or keycloak_sub; null for platform-owned
```

> Extension required: see section 3.2 for the `status` / `owner_type` / `owner_id` ALTER TABLE migration.

> **`locked` is not a column on `topics`.** It is a derived field computed at the API layer when building topic list responses for students. A topic is `locked = true` when its nearest `course_path_node` ancestor with `node_type = 'grade'` represents a grade higher than the requesting student's `student_profiles.grade`. No migration or stored column is needed.

**`topic_contents`** — content items attached to a topic. Types: PDF (file stored on disk), video (URL), text notes.

> Image storage: question images are stored at `data_dir/images/questions/` on disk, base64-encoded at the API layer before sending to the frontend. Do not change this pattern for existing content — apply it to new question types too.

### 2.2 Question Bank

**`questions`** — shared question bank. Fields include `question_text` (NOTE: not `body`), `question_type` (`single_choice` | `multiple_choice` | `true_false` | `fill_in_the_blank` | `essay`), `options` (JSONB), `correct_answers` (JSONB), `explanation`, `difficulty` (`easy` | `medium` | `hard`), `tags` (JSONB, nullable), `image_url`.

**`paragraph_questions`** — reading passages with embedded question IDs. A `paragraph_question` contains a passage body and an array of `question_id` references from the `questions` table. Used in exams where students read a passage and answer several questions about it.

> `question_ids` on `assessments` and `paragraph_questions` uses PostgreSQL **ARRAY** columns — not join tables. This is an existing design decision. New question grouping must follow the same pattern.

### 2.3 Assessments (topic-based quizzes)

**`assessments`** — topic-based quizzes authored by instructors. Fields include `topic_id`, `question_ids` (ARRAY), `paragraph_question_ids` (ARRAY, nullable), `title`.

**`assessment_attempts`** — one record per student per attempt. Fields include `assessment_id`, `user_id` (Keycloak sub — NOTE: column is `user_id`, not `student_id`), `status` (`pending` | `ongoing` | `completed` | `failed`), `score`, `started_at`, `finished_at` (NOTE: column is `finished_at`, not `submitted_at`).

**`assessment_answers`** — individual answer records per question per attempt.

### 2.4 Exams (formal timed exams)

> **Note:** These are existing tables. The backend implementation is the authority on exact column names if any discrepancy arises. The schemas below are inferred from the existing spec references, design decisions, and API contracts.

**`exam_templates`** — instructor-authored exam blueprints.

```python
class ExamTemplate(BaseModel):
    id: UUID
    course_path_node_id: UUID   # FK → course_path_nodes
    title: str
    description: str | None
    mode: str                   # 'static' | 'dynamic' | 'custom' (Enum: ExamMode)
    ruleset: dict | None        # JSON ruleset for dynamic exam generation. Required when mode = 'dynamic', null otherwise. Schema below.
    duration_minutes: int | None  # NOTE: column is 'duration_minutes', not 'time_limit_minutes'
    passing_score: float | None # 0.0–1.0
    created_by: UUID            # Keycloak sub of creating instructor; NOTE: column is 'created_by', not 'instructor_id'
    is_active: bool             # soft delete — False means archived
```

**`ruleset` JSON schema (for `mode = 'dynamic'`):**
```json
{
  "total_questions": 10,
  "difficulty_mix": {
    "easy": 4,
    "medium": 4,
    "hard": 2
  },
  "topics": ["uuid-1", "uuid-2"],
  "tags_include": ["algebra", "fractions"],
  "tags_exclude": ["advanced"],
  "question_types": ["single_choice", "multiple_choice", "fill_in_the_blank"]
}
```

**Ruleset validation rules:**
- `total_questions` is required. All other fields are optional.
- Question selection is random within matching candidates.
- **Difficulty fallback:** If insufficient questions exist at a requested difficulty level, remaining slots are filled from the next difficulty down (`hard → medium → easy`). If still insufficient after fallback, return an error at exam creation time indicating how many questions are available vs requested.
- Ruleset is validated at `POST /api/exam-templates` creation time, not at session creation time.
- `difficulty_mix` values must sum to `total_questions` if both are provided — validate at creation time.

**`exam_template_questions`** — ordered list of questions within a template.

```python
class ExamTemplateQuestion(BaseModel):
    id: UUID
    exam_template_id: UUID      # FK → exam_templates
    question_id: UUID           # FK → questions
    order: int                  # NOTE: column is 'order', not 'order_index'
    points: int                 # points awarded for this question
```

**BR-EXAM-001:** Paragraph questions in exam templates are not yet supported in the existing schema. The `exam_template_questions` table currently references only `questions` via `question_id`. Paragraph question support in exams will require an ALTER TABLE migration to add `paragraph_question_id` — plan this as part of the new work.

**`exam_sessions`** — per-student exam instances. **Key design decision: exam session questions reference live question rows via FK — no JSONB snapshot.** Template edits after session creation may affect question content — the current design does not snapshot. **Accepted risk:** If a teacher edits a question after a student has completed an exam, the student's review screen will show the edited question text, not the original. This is a known trade-off for simplicity — teachers should be aware that question edits are retroactive across all past sessions.

```python
class ExamSession(BaseModel):
    id: UUID
    user_id: UUID               # Keycloak sub; NOTE: column is 'user_id', not 'student_id'
    exam_template_id: UUID | None  # FK → exam_templates; nullable
    course_path_node_id: UUID   # FK → course_path_nodes
    mode: str                   # 'static' | 'dynamic' | 'custom' (Enum: ExamMode)
    ruleset: dict | None        # JSON — snapshotted from template or custom
    created_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None  # NOTE: column is 'finished_at', not 'submitted_at'
    score: float | None         # computed and stored on completion
    status: str                 # 'pending' | 'ongoing' | 'completed' | 'failed' (Enum: ExamStatus)
```

**`exam_session_questions`** — per-question records for a specific session. **Key design decision: exam session questions reference live question rows via FK, not JSONB snapshots.** Answers (`user_answer`, `is_correct`, `earned_points`) are stored directly on the session question row. Template edits after session creation may affect question content — the current design does not snapshot.

> **UI note:** When a teacher edits a question that has been used in one or more completed exam sessions, the frontend must display a warning: "This question has been used in X completed exams. Editing it will affect how those exams display and may affect grading if correct answers are changed." Editing is not blocked — this is awareness only.

```python
class ExamSessionQuestion(BaseModel):
    id: UUID
    exam_session_id: UUID       # FK → exam_sessions
    question_id: UUID           # FK → questions (references live question row, not a snapshot)
    order: int                  # NOTE: column is 'order', not 'order_index'
    points: int                 # points available for this question
    user_answer: str | None     # student's submitted answer
    is_correct: bool | None     # grading result
    earned_points: float | None # points earned
```

---

## 3. Schema Extensions (alter existing tables)

These are ALTER TABLE operations on the existing schema — not new tables.

### 3.1 `course_path_nodes` — add ownership columns

```sql
ALTER TABLE course_path_nodes
  ADD COLUMN owner_type VARCHAR(20) NOT NULL DEFAULT 'platform'
    CHECK (owner_type IN ('platform', 'institution', 'tutor')),
  ADD COLUMN owner_id UUID NULL;  -- org_id or keycloak_sub, null for platform-owned
```

**Backfill:** Set all existing rows to `owner_type = 'platform'`, `owner_id = NULL`.

**BR-CONTENT-001:** `owner_type = 'platform'` → only `admin` role can modify. `owner_type = 'institution'` → only `institution_admin` of that org can modify. `owner_type = 'tutor'` → only the owning tutor can modify.

**BR-CONTENT-002 (inheritance):** When a new child node or topic is created under a parent `course_path_node`, it inherits the creator's ownership context — not the parent's. For example, if an institution admin adds a topic under a platform-owned node, the new topic gets `owner_type = 'institution'` and `owner_id = org_id`. The parent node retains `owner_type = 'platform'`. Visibility follows ownership: institution-owned content is visible only to that institution's students; platform-owned content is visible to all.

### 3.2 `topics` — add status and ownership columns

```sql
ALTER TABLE topics
  ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'live'
    CHECK (status IN ('draft', 'live', 'archived')),
  ADD COLUMN owner_type VARCHAR(20) NOT NULL DEFAULT 'platform'
    CHECK (owner_type IN ('platform', 'institution', 'tutor')),
  ADD COLUMN owner_id UUID NULL;  -- org_id or keycloak_sub, null for platform-owned
```

**Backfill:** Set all existing rows to `status = 'live'`, `owner_type = 'platform'`, `owner_id = NULL`.

**Status lifecycle:**
- `draft` → topic created but not visible to students. Only the creator can view and edit.
- `live` → visible to students within their enrollment scope. **Content (title, topic_contents) remains editable in-place** — the creator can fix errors, add content, or update materials without changing the topic's status. Status transitions remain one-way.
- `archived` → hidden from students and read-only. Cannot be reverted to `live` (create a new topic instead).

> **UI note:** The frontend must show a confirmation dialog before archiving a topic: "This cannot be undone — are you sure you want to archive this topic?" No revert mechanism is needed at the data layer.

**Transitions:** `draft → live` (creator publishes), `live → archived` (creator or admin archives). No other transitions are valid. Note: while status transitions are one-way, topic content (title, attached content items) can be edited at any status except `archived`.

**BR-CONTENT-003:** A topic's `owner_type` and `owner_id` are set at creation based on the creator's role context — not inherited from the parent `course_path_node`:
- Creator is `admin` → `owner_type = 'platform'`, `owner_id = NULL`
- Creator is `institution_admin` → `owner_type = 'institution'`, `owner_id = org_id`
- Creator is `instructor` (adding supplemental content) → `owner_type = 'institution'`, `owner_id = org_id` of their organization
- Creator is `tutor` → `owner_type = 'tutor'`, `owner_id = tutor_keycloak_sub`

**BR-CONTENT-004:** `topic_contents` items do not carry their own `owner_type`. They inherit access rules from their parent `topic`. No ownership columns are needed on `topic_contents`.

### 3.3 `exam_templates` — add owner columns

```sql
ALTER TABLE exam_templates
  ADD COLUMN owner_type VARCHAR(20) NOT NULL DEFAULT 'instructor'
    CHECK (owner_type IN ('instructor', 'tutor', 'institution')),
  ADD COLUMN organization_id UUID NULL;  -- FK → organizations (new table)
```

> **Why `instructor` instead of `platform`:** Unlike `course_path_nodes` and `topics`, exam templates are always authored by a specific person — there is no concept of "platform-owned" exam content that the SuperAdmin publishes. The `instructor` value means an individual teacher within an institution created the template. `institution` means it was created at the org level by an institution admin. `tutor` means an independent tutor created it. This is intentionally different from the `('platform', 'institution', 'tutor')` set used on `course_path_nodes` and `topics`.

---

## 4. New Tables

All tables below are new additions. They must not conflict with the existing schema.

### 4.0 User Metadata

**`user_metadata`** ❌ NEW — cross-role user state, keyed on Keycloak `sub`. Applies to all personas including admin and institution_admin who skip the onboarding flow.

```python
class UserMetadata(BaseModel):
    keycloak_sub: str                      # PK — no FK constraint
    onboarding_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

**Row lifecycle:**
- Created (upsert) on the user's first authenticated request to `GET /api/users/me`.
- `onboarding_completed_at` is set by `PATCH /api/users/me/onboarding-complete` (called at ON08).
- For `admin` and `institution_admin` users who are Keycloak-invited and skip onboarding, the row is created with `onboarding_completed_at = now()` at the time the backend processes their first login — they never see the onboarding flow.

**BR-META-001:** `GET /api/users/me` returns `onboarding_completed: bool` derived from `onboarding_completed_at IS NOT NULL`. The frontend uses this on every page load to decide whether to redirect to `/onboarding`.

**BR-META-002:** `PATCH /api/users/me/onboarding-complete` does not require `X-Current-Role` — users may not have an active role yet at ON08. This is an explicit exception to BR-SEC-006.

### 4.1 Profile Tables

No local users table exists. Profile data is stored in role-specific tables keyed on Keycloak `sub`.

**`student_profiles`** ❌ NEW
```python
class StudentProfile(BaseModel):
    id: UUID
    keycloak_sub: str           # Keycloak sub — no FK constraint
    first_name: str
    last_name: str
    grade: str                  # e.g. "6", "7", "Undergraduate"
    subjects: list[str]
    created_at: datetime
    updated_at: datetime
```

**`teacher_profiles`** ❌ NEW
```python
class TeacherProfile(BaseModel):
    id: UUID
    keycloak_sub: str
    first_name: str
    last_name: str
    teacher_type: Literal['institutional', 'tutor', 'both']
    subjects: list[str]
    grades: list[str]
    years_experience: int
    bio: str | None
    rate_per_session: int | None    # INR; null if not a tutor
    availability: str | None        # free text e.g. "Mon–Fri 4–8pm"
    marketplace_listed: bool        # tutor controls visibility
    marketplace_suspended: bool     # admin can suspend — overrides marketplace_listed
    created_at: datetime
    updated_at: datetime
```

**`parent_profiles`** ❌ NEW
```python
class ParentProfile(BaseModel):
    id: UUID
    keycloak_sub: str
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime
```

### 4.2 Organizations

**`organizations`** ❌ NEW
```python
class Organization(BaseModel):
    id: UUID
    name: str
    city: str
    primary_board_category_id: UUID | None  # FK → categories (existing table)
    plan: Literal['starter', 'school', 'enterprise']
    status: Literal['pending', 'active', 'inactive']
    invite_code_prefix: str     # e.g. "STMARY"
    created_at: datetime
    activated_at: datetime | None
```

**`organization_members`** ❌ NEW
```python
class OrganizationMember(BaseModel):
    id: UUID
    organization_id: UUID       # FK → organizations
    keycloak_sub: str           # the user — no FK constraint
    role: Literal['institution_admin', 'instructor']
    invited_by: str | None      # keycloak_sub of inviter
    joined_at: datetime | None
    status: Literal['invited', 'active', 'removed']
```

**`classes`** ❌ NEW
```python
class Class(BaseModel):
    id: UUID
    organization_id: UUID       # FK → organizations
    name: str                   # e.g. "Grade 6 – Section A"
    grade: str
    subject: str
    academic_year: str          # e.g. "2025-2026"
    instructor_keycloak_sub: str | None
    invite_code: str            # e.g. "STMARY-2026-G6" — unique platform-wide
    board_adoption_id: UUID | None  # FK → board_adoptions; null = no board curriculum assigned yet
    created_at: datetime
    updated_at: datetime
```

**`class_enrollments`** ❌ NEW
```python
class ClassEnrollment(BaseModel):
    id: UUID
    class_id: UUID              # FK → classes
    student_keycloak_sub: str
    enrolled_at: datetime
    enrolled_by: Literal['invite_code', 'csv_upload', 'admin_manual']
    status: Literal['active', 'removed']
```

**BR-CLASS-001:** Invite codes are unique platform-wide.
**BR-CLASS-002:** A student cannot be enrolled in the same class twice (`UNIQUE` on `class_id` + `student_keycloak_sub` where `status = 'active'`).

### 4.3 Enrollments and Progress

**`enrollments`** ❌ NEW — represents a student's enrollment in a learning context (structured class or open).

```python
class Enrollment(BaseModel):
    id: UUID
    student_keycloak_sub: str
    type: Literal['structured', 'open']
    class_id: UUID | None           # for structured enrollments
    tutor_keycloak_sub: str | None  # for open tutor-led; null = self-directed
    status: Literal['active', 'paused', 'completed', 'removed']
    enrolled_at: datetime
    last_active_at: datetime | None
    subscription_status: str    # 'free' | 'paid' — default 'free', not null
    payment_id: str | None      # null for free courses; populated when payment processing is added
```

**BR-ENROLL-PAY-001:** All enrollments default to `subscription_status = 'free'` on launch. A future per-course setting will determine whether enrollment requires payment. Payment processing is out of scope for v1 — `payment_id` will be `null` for all records in this phase.

**`enrollment_topics`** ❌ NEW — tracks a student's progress per topic within an enrollment context.

```python
class EnrollmentTopic(BaseModel):
    id: UUID
    enrollment_id: UUID         # FK → enrollments
    topic_id: UUID              # FK → topics (existing table)
    status: Literal['not_started', 'in_progress', 'completed', 'weak']
    mastery_score: float | None # 0.0–100.0
    last_studied_at: datetime | None
    created_at: datetime
    updated_at: datetime
```

**BR-PROGRESS-001:** A topic is `weak` if `mastery_score < 60.0` after at least one assessment attempt.
**BR-PROGRESS-002:** A topic is `completed` if `mastery_score >= 75.0` and at least one attempt submitted.
**BR-PROGRESS-003:** `mastery_score` recalculation: On the **first attempt**, `mastery_score = latest_score` (raw score directly). From the **second attempt onward**, `mastery_score = (latest_score * 0.6) + (previous_mastery * 0.4)`. This prevents false weak-topic flags from a single attempt (e.g., scoring 80% would give mastery 48% if previous_mastery defaulted to 0).

**Enrollment deactivation rules:**

**BR-ENROLL-001:** A student can unenroll from **open enrollments only** (tutor-led or self-directed). Sets `enrollments.status = 'removed'`. Structured (class-based) enrollments can only be removed by the institution admin — students cannot leave a class themselves.

**BR-ENROLL-002:** A tutor can remove a student from their open enrollment. Sets `enrollments.status = 'removed'` and `tutor_student_relationships.status = 'ended'`.

**BR-ENROLL-003:** An institution admin can remove a student from a class. Sets `class_enrollments.status = 'removed'` AND the linked `enrollments.status = 'removed'`.

**BR-ENROLL-004:** When admin sets an institution to `inactive` (BR-SA-009), all `class_enrollments` and linked `enrollments` for that org are bulk-set to `removed`.

**BR-ENROLL-005 (side effects):** When an enrollment is removed:
- `enrollment_topics` data is preserved as a read-only historical record (student can see past progress if re-enrolled).
- Open doubts (`status = 'pending'`) are auto-resolved with system message "Enrollment ended".
- Pending `class_assignments` for that student are excluded from due items.

**BR-ENROLL-006:** Removal is not reversible. To re-enroll, create a new enrollment. Previous `enrollment_topics` data is not carried over — student starts fresh.

**BR-ENROLL-007 (structured enrollment invariant):** For every structured enrollment, a `class_enrollments` row and an `enrollments` row with `type = 'structured'` must always exist as a pair. The backend service layer is responsible for creating and removing both atomically within a single database transaction.

- **Creation:** When a student joins a class (via invite code, CSV upload, or admin manual), the service creates both rows in one transaction. If either insert fails, both are rolled back.
- **Source of truth for class membership:** `class_enrollments` is authoritative for "is this student on the class roster". `enrollments` is authoritative for learning progress, doubts, topics, and reviews.
- **Access check:** A student's access to class content requires `class_enrollments.status = 'active'` AND `enrollments.status = 'active'`. If the two ever diverge (data integrity failure), the more restrictive state governs — treat the student as unenrolled and alert via application logs.

### 4.4 Tutor–Student Relationships

**`tutor_student_relationships`** ❌ NEW
```python
class TutorStudentRelationship(BaseModel):
    id: UUID
    tutor_keycloak_sub: str
    student_keycloak_sub: str
    enrollment_id: UUID         # FK → enrollments
    status: Literal['active', 'paused', 'ended']
    started_at: datetime
    ended_at: datetime | None
    teacher_notes: str | None   # private — only tutor can read/write
    subscription_status: str    # 'free' | 'paid' — default 'free', not null
    payment_id: str | None      # null for free courses; populated when payment processing is added
```

**BR-TUTOR-PAY-001:** All tutor courses default to `subscription_status = 'free'` on launch. A future per-course setting will determine whether enrollment requires payment. Payment processing is out of scope for v1 — `payment_id` will be `null` for all records in this phase.

### 4.5 Parent–Child Links

**`parent_child_links`** ❌ NEW
```python
class ParentChildLink(BaseModel):
    id: UUID
    parent_keycloak_sub: str
    student_keycloak_sub: str
    link_code: str              # generated by student
    link_code_expires_at: datetime  # 7 days from generation
    linked_at: datetime | None
    status: Literal['pending', 'linked', 'revoked']
```

**BR-PARENT-001:** One active link code per student at a time. Generating a new code invalidates the previous.
**BR-PARENT-002:** Link code expires 7 days after generation.
**BR-PARENT-003:** A parent can link to multiple children. A child can have multiple linked parents.

### 4.6 Doubts

**`doubts`** ❌ NEW
```python
class Doubt(BaseModel):
    id: UUID
    student_keycloak_sub: str
    enrollment_id: UUID         # FK → enrollments
    topic_id: UUID              # FK → topics (existing table)
    status: Literal['pending', 'answered', 'resolved']
    haitu_attempted: bool       # must be true before escalation allowed
    escalated_to: str | None    # keycloak_sub of teacher/tutor
    created_at: datetime
    resolved_at: datetime | None
    auto_close_at: datetime     # created_at + 7 days
```

**`doubt_messages`** ❌ NEW
```python
class DoubtMessage(BaseModel):
    id: UUID
    doubt_id: UUID              # FK → doubts
    sender_type: Literal['student', 'ai', 'teacher']
    sender_keycloak_sub: str | None  # null for 'ai'
    body: str
    created_at: datetime
```

**BR-DOUBT-001:** Escalation only allowed when `haitu_attempted = true`.
**BR-DOUBT-002:** Messages are append-only — no editing or deletion.
**BR-DOUBT-003:** Auto-close at 7 days if not manually resolved.
**BR-DOUBT-004:** When teacher sends a message, `doubt.status` → `answered`. When marked resolved, `status` → `resolved` and `resolved_at` is set.
**BR-DOUBT-005:** `escalated_to` is resolved by `domain/services/doubts_service.py` at `POST /api/doubts` creation time — not at hAITU interaction time, and not in the route handler. Resolution chain:
- **Structured enrollment:** `enrollment.class_id` → `classes.instructor_keycloak_sub`. If `instructor_keycloak_sub` is NULL (class has no teacher), set `escalated_to = NULL` — the doubt surfaces in the institution admin's unassigned doubts list and triggers a `class_no_teacher` notification if one has not already fired for this class within 48 hours.
- **Open enrollment:** `enrollment.tutor_keycloak_sub`. If NULL (self-directed with no tutor), set `escalated_to = NULL` — the doubt is visible only to the student and platform admin.

### 4.7 Class Assignments

**Assessments vs Exams:**
- **Assessments** are formative (practice). Tied to one topic. Students can take them anytime via the topic navigator. Teachers can also assign them to a class via `class_assignments`.
- **Exams** are summative (evaluation). Span multiple topics via `exam_templates`. Teachers create them and assign them to a class. Students access exams only when assigned.

Both appear under "Due items" in the student home with a type badge ("Quiz" for assessments, "Exam" for exams).

**`class_assignments`** ❌ NEW — tracks when an instructor assigns an assessment or exam to a class.

```python
class ClassAssignment(BaseModel):
    id: UUID
    class_id: UUID              # FK → classes
    assessment_id: UUID | None  # FK → assessments (formative) — mutually exclusive with exam_template_id
    exam_template_id: UUID | None  # FK → exam_templates (summative) — mutually exclusive with assessment_id
    assigned_by: str            # instructor keycloak_sub
    due_at: datetime
    note: str | None            # max 500 chars
    created_at: datetime
    updated_at: datetime
```

**BR-ASSESS-001:** A `class_assignment` must have exactly one of `assessment_id` or `exam_template_id` set — never both, never neither. Enforce with a database CHECK constraint: `CHECK (num_nonnulls(assessment_id, exam_template_id) = 1)`.
**BR-ASSESS-002:** The student-facing "Due items" list shows both types. The `type` field in the API response is derived: `'quiz'` if `assessment_id` is set, `'exam'` if `exam_template_id` is set.

### 4.8 Notifications

**`notifications`** ❌ NEW
```python
class Notification(BaseModel):
    id: UUID
    recipient_keycloak_sub: str
    recipient_role: str         # which role context this belongs to
    type: str                   # NotificationType enum value
    title: str
    body: str
    action_url: str | None      # deep link
    read: bool
    created_at: datetime
```

**`platform_settings`** ❌ NEW — key-value store for feature flags and AI config.

```sql
CREATE TABLE platform_settings (
    key   VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Default rows to seed:
```sql
INSERT INTO platform_settings VALUES
  ('haitu_model', 'claude-sonnet-4-6', NOW()),
  ('haitu_enabled_student', 'true', NOW()),
  ('haitu_enabled_teacher', 'true', NOW()),
  ('haitu_enabled_parent', 'true', NOW()),
  ('haitu_max_tokens_topic_doubt',              '400',  NOW()),
  ('haitu_max_tokens_exam_review_chat',         '500',  NOW()),
  ('haitu_max_tokens_escalation_attempt',       '400',  NOW()),
  ('haitu_max_tokens_teacher_tools_plan',       '600',  NOW()),
  ('haitu_max_tokens_teacher_tools_questions',  '800',  NOW()),
  ('haitu_max_tokens_teacher_tools_report',     '300',  NOW()),
  ('haitu_max_tokens_parent_topic_description', '200',  NOW()),
  ('haitu_max_tokens_parent_report',            '350',  NOW()),
  ('haitu_max_tokens_parent_topic_explain',     '200',  NOW()),
  ('haitu_max_tokens_exam_analysis',            '600',  NOW()),
  ('marketplace_enabled', 'true', NOW()),
  ('open_learning_enabled', 'true', NOW()),
  ('parent_portal_enabled', 'true', NOW()),
  ('maintenance_mode', 'false', NOW());
```

### 4.9 Parent–Tutor Messages

**`parent_tutor_messages`** ❌ NEW — direct messages between parents and tutors (separate from student doubt threads).

```python
class ParentTutorMessage(BaseModel):
    id: UUID
    parent_keycloak_sub: str
    tutor_keycloak_sub: str
    student_keycloak_sub: str    # the child this conversation is about
    sender: Literal['parent', 'tutor']
    body: str
    created_at: datetime
```

**BR-MSG-001:** Messages are scoped per (parent, tutor, child) triple — each child has a separate thread with each tutor.
**BR-MSG-002:** Parents cannot message institutional teachers (only tutors). See BR-PAR-014.

### 4.10 Board Adoptions

**`board_adoptions`** ❌ NEW — tracks when an institution adopts a platform board curriculum.

```python
class BoardAdoption(BaseModel):
    id: UUID
    organization_id: UUID        # FK → organizations
    category_id: UUID            # FK → categories (the board being adopted)
    adopted_by: str              # keycloak_sub of institution_admin
    status: Literal['active', 'inactive']
    adopted_at: datetime
    updated_at: datetime
```

**BR-ADOPT-001:** On board import, topics are created with `owner_type = 'institution'` and `owner_id = org_id` (see BR-INST-006).
**BR-ADOPT-002:** When a platform admin publishes a board update, institutions with active adoptions receive updated platform-owned content. Institution-created custom topics are preserved.

### 4.11 Platform Events

**`platform_events`** ❌ NEW — audit log for the SuperAdmin activity feed.

```python
class PlatformEvent(BaseModel):
    id: UUID
    event_type: str              # e.g. 'institution_approved', 'tutor_suspended', 'board_published'
    actor_keycloak_sub: str      # who performed the action
    actor_role: str              # role at time of action
    entity_type: str | None      # e.g. 'organization', 'tutor', 'board'
    entity_id: str | None        # ID of affected entity — intentionally str, not UUID, to support heterogeneous entity types (org IDs, keycloak subs, board names)
    description: str             # human-readable summary
    created_at: datetime
```

**BR-EVENT-001:** Platform events are append-only — no editing or deletion.
**BR-EVENT-002:** The SuperAdmin dashboard shows the most recent 20 events (see BR-SA-002).

### 4.12 Topic Reviews

**`topic_reviews`** ❌ NEW — student ratings of topics after studying them. Aggregate scores feed the tutor marketplace content rating.

```python
class TopicReview(BaseModel):
    id: UUID
    topic_id: UUID               # FK → topics
    reviewer_keycloak_sub: str   # student — no FK constraint
    enrollment_id: UUID          # FK → enrollments (ensures student studied via this context)
    rating: int                  # 1–5 stars
    comment: str | None          # optional short text
    created_at: datetime
```

**BR-REVIEW-001:** One review per student per topic — enforced by unique index on `(topic_id, reviewer_keycloak_sub)`.

**BR-REVIEW-002:** A student can only submit a review for a topic where their `enrollment_topics.status` is `completed` or `weak` (i.e. they have genuinely attempted the topic at least once).

**BR-REVIEW-003:** Reviews are immutable once submitted — no editing or deletion by the student.

**BR-REVIEW-004:** `teacher_profiles.content_rating` and `teacher_profiles.review_count` are cached aggregates recomputed when a new review is submitted for any topic owned by that tutor (`topics.owner_type = 'tutor'` and `topics.owner_id = tutor_keycloak_sub`). Platform and institution-owned topics do not feed tutor ratings.

**`teacher_profiles` extension** — add two cached aggregate columns:
```sql
ALTER TABLE teacher_profiles
  ADD COLUMN content_rating NUMERIC(3,2) NULL,   -- avg of topic_reviews.rating across tutor's topics
  ADD COLUMN review_count   INT NOT NULL DEFAULT 0;
```

---

## 5. Key Indexes

```sql
-- User metadata
-- keycloak_sub is the PK — no additional index needed

-- Profiles
CREATE UNIQUE INDEX idx_student_profiles_sub ON student_profiles(keycloak_sub);
CREATE UNIQUE INDEX idx_teacher_profiles_sub ON teacher_profiles(keycloak_sub);
CREATE UNIQUE INDEX idx_parent_profiles_sub  ON parent_profiles(keycloak_sub);

-- Classes
CREATE UNIQUE INDEX idx_classes_invite_code ON classes(invite_code);
CREATE INDEX idx_classes_board_adoption
  ON classes(board_adoption_id)
  WHERE board_adoption_id IS NOT NULL;

-- Class enrollments
CREATE UNIQUE INDEX idx_class_enrollment_active
  ON class_enrollments(class_id, student_keycloak_sub)
  WHERE status = 'active';

-- Enrollments
CREATE UNIQUE INDEX idx_enrollment_student_class
  ON enrollments(student_keycloak_sub, class_id)
  WHERE status = 'active' AND type = 'structured';

-- Parent links
CREATE UNIQUE INDEX idx_parent_child_linked
  ON parent_child_links(parent_keycloak_sub, student_keycloak_sub)
  WHERE status = 'linked';

-- Doubts
CREATE INDEX idx_doubts_student   ON doubts(student_keycloak_sub, status);
CREATE INDEX idx_doubts_escalated ON doubts(escalated_to, status);
CREATE INDEX idx_doubt_messages   ON doubt_messages(doubt_id, created_at);

-- Notifications
CREATE INDEX idx_notifications_recipient
  ON notifications(recipient_keycloak_sub, recipient_role, read, created_at DESC);

-- course_path_nodes (new columns)
CREATE INDEX idx_cpn_owner ON course_path_nodes(owner_type, owner_id);

-- Topics (new columns)
CREATE INDEX idx_topics_owner ON topics(owner_type, owner_id);
CREATE INDEX idx_topics_status ON topics(status);

-- Parent-tutor messages
CREATE INDEX idx_ptm_thread
  ON parent_tutor_messages(parent_keycloak_sub, tutor_keycloak_sub, student_keycloak_sub, created_at DESC);

-- Board adoptions
CREATE UNIQUE INDEX idx_board_adoption_active
  ON board_adoptions(organization_id, category_id)
  WHERE status = 'active';

-- Doubts auto-close
CREATE INDEX idx_doubts_auto_close
  ON doubts(auto_close_at)
  WHERE status != 'resolved';

-- Platform events
CREATE INDEX idx_platform_events_recent ON platform_events(created_at DESC);

-- Topic reviews
CREATE UNIQUE INDEX idx_topic_review_once
  ON topic_reviews(topic_id, reviewer_keycloak_sub);
CREATE INDEX idx_topic_reviews_topic ON topic_reviews(topic_id, rating);
```

---

## 6. Soft Delete Convention

The existing codebase uses `is_active` flag on `exam_templates` for soft deletes. New tables use a `status` field instead — this is consistent with the new table designs but do not retrofit `status` onto existing tables. Follow the existing pattern for existing tables, the new pattern for new tables.

**Note on status values:** New tables intentionally use domain-specific terminal status values (`removed`, `ended`, `revoked`) rather than a single universal enum, because each value carries semantic meaning in its domain context (e.g. a tutor relationship is "ended", not "removed"; a parent link is "revoked", not "ended"). Do not normalize these to a common value.

| Table | Soft delete mechanism |
|---|---|
| `exam_templates` (existing) | `is_active BOOLEAN` |
| `organization_members` (new) | `status = 'removed'` |
| `class_enrollments` (new) | `status = 'removed'` |
| `enrollments` (new) | `status = 'removed'` |
| `tutor_student_relationships` (new) | `status = 'ended'` |
| `parent_child_links` (new) | `status = 'revoked'` |
