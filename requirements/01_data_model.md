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

**`categories`** — top-level groupings (e.g. "NCERT", "JNV").

**`course_path_nodes`** — self-referential tree representing the full curriculum hierarchy from grade down to course level. This is the existing content tree. Fields include `parent_id` (self-referential), `name`, `node_type`, `order_index`.

> Extension required: add `owner_type` and `owner_id` columns to `course_path_nodes` to support multi-persona content ownership. See section 3.3.

**`topics`** — leaf nodes within a `course_path_node`. Each topic is a specific study unit (e.g. "Fractions").

**`topic_contents`** — content items attached to a topic. Types: PDF (file stored on disk), video (URL), text notes.

> Image storage: question images are stored at `data_dir/images/questions/` on disk, base64-encoded at the API layer before sending to the frontend. Do not change this pattern for existing content — apply it to new question types too.

### 2.2 Question Bank

**`questions`** — shared question bank. Fields include body, image reference, answer options (MCQ), correct answer, explanation.

**`paragraph_questions`** — reading passages with embedded question IDs. A `paragraph_question` contains a passage body and an array of `question_id` references from the `questions` table. Used in exams where students read a passage and answer several questions about it.

> `question_ids` on `assessments` and `paragraph_questions` uses PostgreSQL **ARRAY** columns — not join tables. This is an existing design decision. New question grouping must follow the same pattern.

### 2.3 Assessments (topic-based quizzes)

**`assessments`** — topic-based quizzes authored by instructors. Fields include `topic_id`, `question_ids` (ARRAY), `time_limit_minutes`.

**`assessment_attempts`** — one record per student per attempt. Fields include `assessment_id`, `student_id` (Keycloak sub), `status`, `score`, `started_at`, `submitted_at`.

**`assessment_answers`** — individual answer records per question per attempt.

### 2.4 Exams (formal timed exams)

**`exam_templates`** — instructor-authored exam blueprints. Fields include `title`, `instructor_id`, `is_active` (soft delete flag). Contains mixed question types including `paragraph_questions`.

**`exam_template_questions`** — ordered list of questions (regular + paragraph) within a template.

**`exam_sessions`** — per-student exam instances. **Key design decision: questions are copied from the template at session creation time.** Template edits after session creation do not affect in-progress sessions.

**`exam_session_questions`** — the snapshot copy of questions for a specific session.

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
- `live` → visible to students within their enrollment scope.
- `archived` → hidden from students and read-only. Cannot be reverted to `live` (create a new topic instead).

**Transitions:** `draft → live` (creator publishes), `live → archived` (creator or admin archives). No other transitions are valid.

### 3.3 `exam_templates` — add owner columns

```sql
ALTER TABLE exam_templates
  ADD COLUMN owner_type VARCHAR(20) NOT NULL DEFAULT 'instructor'
    CHECK (owner_type IN ('instructor', 'tutor', 'institution')),
  ADD COLUMN organization_id UUID NULL;  -- FK → organizations (new table)
```

---

## 4. New Tables

All tables below are new additions. They must not conflict with the existing schema.

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
    created_at: datetime
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
```

**`enrollment_topics`** ❌ NEW — tracks a student's progress per topic within an enrollment context.

```python
class EnrollmentTopic(BaseModel):
    id: UUID
    enrollment_id: UUID         # FK → enrollments
    topic_id: UUID              # FK → topics (existing table)
    status: Literal['not_started', 'in_progress', 'completed', 'weak']
    mastery_score: float | None # 0.0–100.0
    last_studied_at: datetime | None
    updated_at: datetime
```

**BR-PROGRESS-001:** A topic is `weak` if `mastery_score < 60.0` after at least one assessment attempt.
**BR-PROGRESS-002:** A topic is `completed` if `mastery_score >= 75.0` and at least one attempt submitted.
**BR-PROGRESS-003:** `mastery_score` recalculation: `(latest_score * 0.6) + (previous_mastery * 0.4)`.

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
```

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
**BR-DOUBT-005:** Escalation target is determined automatically: for structured enrollments, `escalated_to` = the `instructor_keycloak_sub` of the class linked to the enrollment. For open enrollments, `escalated_to` = the `tutor_keycloak_sub` on the enrollment. If no instructor is assigned to the class, the doubt is created with `escalated_to = NULL` and surfaces in the institution admin's unassigned doubts list.

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
    note: str | None
    created_at: datetime
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
  ('haitu_max_tokens_student', '400', NOW()),
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
    entity_id: str | None        # ID of affected entity
    description: str             # human-readable summary
    created_at: datetime
```

**BR-EVENT-001:** Platform events are append-only — no editing or deletion.
**BR-EVENT-002:** The SuperAdmin dashboard shows the most recent 20 events (see BR-SA-002).

---

## 5. Key Indexes

```sql
-- Profiles
CREATE UNIQUE INDEX idx_student_profiles_sub ON student_profiles(keycloak_sub);
CREATE UNIQUE INDEX idx_teacher_profiles_sub ON teacher_profiles(keycloak_sub);
CREATE UNIQUE INDEX idx_parent_profiles_sub  ON parent_profiles(keycloak_sub);

-- Classes
CREATE UNIQUE INDEX idx_classes_invite_code ON classes(invite_code);

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

-- Platform events
CREATE INDEX idx_platform_events_recent ON platform_events(created_at DESC);
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
