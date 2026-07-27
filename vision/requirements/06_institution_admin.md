# hAIsir — Institution Admin Specification
> ⚠ DEFERRED (2026-07-27): persona intentionally out of scope. Do not promote to
> `target/requirements/06_institution_admin.md` until this vision file has been explicitly
> revisited and updated by the user first. See `Implementation_planning/decisions.md` 2026-07-27
> entry.
> Version 1.1 | Part B extracted from `05_06_07_personas.md`.
> Institution Admin is an entirely new persona and role.
> → Depends on: `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`
> → Prototype: `haisir_institution_flow.html`
> → See also: `05_parent.md`, `07_platform_admin.md`

---

# PART B — Institution Admin

## B.1 Persona Summary

**Role:** `institution_admin`
**Topbar colour:** `#0D1B2A` (near-black navy)
**Can:** Manage institution, classes, people (teachers + students + parents), curriculum, view class-level analytics.
**Cannot:** View individual student quiz/exam answers or doubt content, access other organizations' data, self-register (invited by SuperAdmin only).

---

## B.2 Screen Inventory

| # | Screen ID | Name |
|---|---|---|
| I01 | `inst-home` | Institution home dashboard |
| I02 | `inst-curriculum` | Curriculum manager |
| I03 | `inst-people` | People manager |
| I04 | `inst-classes` | Classes manager |
| I05 | `inst-analytics` | Analytics dashboard |
| I06 | `inst-class-detail` | Class detail |

Navigation via persistent main nav tabs (Dashboard / Classes / Curriculum / People / Analytics).

---

## B.3 Screen Specifications

### I01 — Institution Home Dashboard

**Stat row (5 cards):** Teachers, Students, Active classes, School avg progress %, At-risk students count.

**Action required strip (amber):** Surfaces: classes without teacher assigned, students without parent link, students at risk. Each item has a "Fix now →" link.

**Quick action cards (2×2 grid):** New class, Invite teacher, Enroll students, Manage curriculum.

**Classes overview:** First 4 class cards. "View all →" → I04.

**Business rules:**
- **BR-INST-001:** At-risk count = students where any `enrollment_topics.mastery_score < 50` across 3+ topics.
- **BR-INST-002:** "Classes without teacher" = classes where `instructor_idp_sub IS NULL` and `status = 'active'`.
- **BR-INST-003:** School avg progress = mean of all `enrollment_topics.mastery_score` for all active students in this organization.

**API calls:**
```
GET /api/organizations/{org_id}/dashboard
→ Auth: institution_admin (own org only)
→ Returns: {
    stats: {teachers, students, classes, avg_progress, at_risk},
    alerts: [{type, message, fix_url}],
    classes: [{id, name, subject, grade, teacher_name?, avg_progress, at_risk, status}]
  }
```

### I02 — Curriculum Manager

**Layout:**
- Top: "Import from board" banner with board picker and "Import" button.
- Main area: left tree (grade → subject → course hierarchy) + right detail panel.

**Tree:** Grade and subject nodes are expandable. Selecting a course shows its topics in the right panel.

**Right detail panel per topic:**
- Topic name, class completion %, content item count.
- Warning if no content uploaded: "No content uploaded — teachers cannot deliver this topic yet."
- Actions: Edit topic name, Upload content, View questions.
- "Add topic" button at top of panel.

**Import flow:**
- Select board (NCERT / JNV / CBE).
- Click "Import board curriculum" → copies board's topic tree into institution namespace.
- Existing custom content is preserved.

**Business rules:**
- **BR-INST-004:** Institution admin can add topics but cannot delete platform-adopted topics. Only topics with `owner_type = 'institution'` can be deleted.
- **BR-INST-005:** Completion % per topic = mean of `enrollment_topics.mastery_score` across all students in all classes that have this topic assigned.
- **BR-INST-006:** Board import (board adoption) performs the following in a single transaction:
  1. Creates a `board_adoptions` record (`status = 'active'`).
  2. Clones `course_path_nodes` and `topics` from the platform board as institution-owned copies (`owner_type = 'institution'`, `owner_id = org_id`). Platform originals are unchanged.
  3. Clones all `exam_templates` associated with the board's `course_path_nodes` as institution-owned copies (`owner_type = 'institution'`, `organization_id = org_id`) per BR-EXAM-OWNER-002 in `01_data_model.md`. Platform originals are unchanged.
  4. Institution admins can then customize cloned topics and exam templates without affecting the platform source.
  - **Board publish propagation:** When SuperAdmin publishes a board update (BR-SA-005), only topics whose content still matches the board original (i.e. not modified since adoption) are updated to the new board version. Topics with `owner_type = 'institution'` that have been edited since adoption are never overwritten.
- **BR-INST-018:** Board import matches existing topics by `(course_path_node_id, title)`. Three outcomes per topic: new (no match) — create with `owner_type = 'institution'`; exists and unchanged — skip silently; exists but content differs — skip and preserve institution's version. Import shows a preview summary (N new, N skipped, N conflicts) before confirmation. **Conflict resolution is automatic — institution version is always preserved. Per-topic override UI is deferred to a future phase.** Institution-created custom topics not in the board are never touched.

**API calls:**
```
GET /api/organizations/{org_id}/curriculum/tree
→ Auth: institution_admin
→ Returns: [{id, title, level, parent_id, completion_pct, content_count, status}]

POST /api/organizations/{org_id}/curriculum/import-board
→ Auth: institution_admin
→ Body: {board_id: uuid}
→ Returns: {topics_imported: int, adoption_id: uuid}

POST /api/topics/{topic_id}/content
→ Auth: institution_admin OR instructor (supplemental)
→ Body: multipart/form-data
→ Returns: {content_item_id}
```

### I03 — People Manager

**Three tabs: Teachers | Students | Parents**

**Teachers tab:**
- Table: Name, Subjects, Classes assigned, Students count, Avg class progress, Status (Active / Pending / New).
- "View" and "Assign" row actions.
- "+ Invite teacher" button → modal (email, role, optional class assignment).

**Students tab:**
- Table: Name, Grade, Section, Classes, Progress bar, Parent linked status.
- Filters: grade, section.
- "Export CSV" and "+ Enroll students" buttons.
- Enroll modal: CSV upload OR share invite code.

**Parents tab:**
- Table: Student name, Parent status (Linked / Not linked), Grade.
- "Share invite link" button — generates a bulk URL students can use to trigger parent code generation.
- "View" / "Invite" row actions.

**Business rules:**
- **BR-INST-007:** Institution admin cannot view or modify individual student quiz/exam answers or doubt message bodies.
- **BR-INST-008:** Adding a teacher by email works in two paths depending on whether the email exists in Keycloak: (a) **New account** — backend calls Keycloak Admin API to create the account, assigns the `instructor` role, and adds the user to `organization_members` with `status = 'active'`; a Keycloak-managed welcome email is sent so the teacher can set their password. (b) **Existing account** — skip account creation, assign `instructor` role if not already held, and add to `organization_members` with `status = 'active'`. In both paths: no acceptance step is required — the institution admin is the authority for their organization. A `teacher_added_to_org` in-app notification is sent to the teacher. **Note:** No `teacher_profiles` row is created at invite time. The teacher completes their profile via the onboarding flow (ON04) on first login. API endpoints that display teacher data (e.g. class roster, people manager) must handle a missing `teacher_profiles` row gracefully — show the teacher's name from Keycloak claims and "Profile not completed" status until ON04 is done.
- **BR-INST-009:** CSV enroll columns: `first_name, last_name, email, grade, section`. Email used to match or create Keycloak accounts.
- **BR-INST-016:** Removed — merged into BR-INST-008.
- **BR-INST-017:** CSV upload validates row-by-row. Per-row outcomes: duplicate row within CSV — skip silently (process first occurrence only); student already enrolled in class — skip with warning "Already enrolled"; email exists in Keycloak — enroll directly; email not in Keycloak — **generate a signup invite link** tied to the CSV row's name/grade/section data (do not skip). Response returns `{enrolled: int, skipped: int, invited: [{email, invite_url}], errors: [{row, email, reason}]}`. Valid rows succeed even if others fail. The institution admin receives the list of `{email, invite_url}` to forward to students. Student is auto-enrolled on first login via the invite link. See also note in `11_role_migration.md` §6.4 for onboarding handling of pre-populated enrollment context.

**API calls:**
```
GET /api/organizations/{org_id}/members?role=instructor
→ Auth: institution_admin
→ Returns: [{idp_sub, name, subjects, classes: [str], student_count, avg_progress, status}]

POST /api/organizations/{org_id}/invite-teacher
→ Auth: institution_admin
→ Body: {email: str, role: str, class_id?: uuid}
→ Returns: {invite_id, expires_at}

GET /api/organizations/{org_id}/students
→ Auth: institution_admin
→ Query: ?grade=&section=&limit=&offset=
→ Returns: [{idp_sub, name, grade, section, classes: [str], progress, parent_linked: bool}]

POST /api/organizations/{org_id}/enroll-students/csv
→ Auth: institution_admin
→ Body: multipart/form-data {file: csv, class_id: uuid}
→ Returns: {enrolled: int, skipped: int, invited: [{email, invite_url}], errors: [{row, reason}]}
```

### I04 — Classes Manager

**Stat row:** Total classes, No teacher, Need attention, At-risk.

**Classes grid:** Cards. Each card: class name, subject, grade, teacher (or "No teacher assigned" in red), at-risk badge, avg progress, assignments count, "View class →" and "Assign teacher" (if no teacher) / "View assignments" buttons.

**Dashed card:** "+ Create new class" → modal.

**Create class modal:**
- Class name, academic year, grade, subject.
- Assign teacher (dropdown of org's instructors).
- Curriculum (board adoption dropdown or custom).
- Creates class → optionally invite students.

**Actions:**
- Click class card → I06 Class Detail.
- "Assign teacher" → modal to pick instructor from org members.

**Business rules:**
- **BR-INST-010:** Class status = danger if avg progress < 50%, warn if < 65%, ok otherwise.
- **BR-INST-011:** A class can be created without a teacher. But STUDENT_AT_RISK_ADMIN and CLASS_NO_TEACHER notifications will fire if teacher remains unassigned after 48 hours.

**API calls:**
```
GET /api/organizations/{org_id}/classes
→ Auth: institution_admin
→ Returns: [{id, name, subject, grade, teacher_name?, avg_progress, at_risk, assignments: int, status}]

POST /api/organizations/{org_id}/classes
→ Auth: institution_admin
→ Body: {name, grade, subject, academic_year, instructor_sub?: str, board_adoption_id?: uuid}
→ Returns: {class_id, invite_code}

PATCH /api/classes/{class_id}/instructor
→ Auth: institution_admin (own org only)
→ Body: {instructor_idp_sub: str}
→ Returns: {updated_at}
```

### I05 — Analytics Dashboard

**Stat row (5):** School avg, Active students, At-risk students, Assignment completion %, Assessments run.

**Doubt metrics row (4):** Doubts raised, Resolved by hAITU %, Escalated to teacher %, Escalations resolved %.

**Charts (2×3 grid):**
- Subject performance (horizontal bars).
- Weakest topics (horizontal bars).
- Teacher class averages (horizontal bars). Disclaimer: *"Class averages reflect the assigned student cohort, not a measure of teacher performance."*
- Doubt resolution by teacher (% replied within 24hrs, per teacher).
- Cohort comparison (grade-level cards).
- Most escalated topics (count bars).

**At-risk students table:** Name, Grade, Progress bar, Weak topics, Teacher.

**Business rules:**
- **BR-INST-012:** All analytics are scoped to `organization_id = self`. No cross-org data.
- **BR-INST-013:** hAITU resolution rate = `doubts where haitu_attempted = true AND status = 'resolved' AND escalated_to IS NULL` / `total doubts`.
- **BR-INST-014:** Teacher response rate = `doubts where escalated_to IS NOT NULL AND status IN ('answered', 'resolved')` / `doubts where escalated_to IS NOT NULL`.

**API calls:**
```
GET /api/organizations/{org_id}/analytics
→ Auth: institution_admin
→ Query: ?period=month|term|all (default: month)
  → month = calendar month to date
  → term = current academic term (4-month window if institution term not configured)
  → all = since institution was created
→ Returns: {
    stats: {avg_progress, student_count, at_risk, assignment_completion, templates_used},
    doubt_stats: {total, haitu_resolved_pct, escalated_pct, teacher_resolved_pct},
    subject_perf: [{subject, avg}],
    weak_topics: [{topic, avg}],
    teacher_avgs: [{teacher_name, avg}],
    teacher_response_rates: [{teacher_name, pct_within_24h}],
    cohorts: [{grade, avg, student_count}],
    escalated_topics: [{topic, count}],
    at_risk_students: [{name, grade, progress, weak_topics, teacher_name}]
  }
```

### I06 — Class Detail

**Purpose:** Deep view of one class — students, progress, assignments.

**Breadcrumb:** Home → Classes → {Class name}

**Class header:** Class name, subject, grade, student count, teacher info or "Assign teacher" button.

**Stat row:** Students, Avg progress, At-risk, Assignments.

**Student roster table:** Name, Progress bar, Weak topics count, Status badge, "View" button. Clicking "View" navigates to the instructor view of student detail (T03, scoped to this class).

**Topic heatmap:** Same as T02 — per-topic class average bars. Read-only for institution admin (no "Add content" button).

**Note:** Institution admin sees the full T02 layout (roster, heatmap, assignments) in read-only mode. They cannot take actions (assign quizzes/exams, add content, message students). This is consistent with "NO individual answers/doubts" — they see mastery scores and progress but cannot access T03's doubt history or individual quiz/exam answers.

**Business rules:**
- **BR-INST-015:** Institution admin accessing T03 from I06 sees the teacher's student detail view **without** `teacher_notes` (private to the teacher) and **without** doubt message bodies (aggregate doubt status only — count and status, not content). They can see topic performance scores and overall progress.

**API calls:**
```
GET /api/classes/{class_id}/detail
→ Auth: institution_admin (own org only)
→ Returns: {
    class: {id, name, subject, grade, teacher_name?, student_count},
    stats: {avg_progress, at_risk, assignments},
    students: [{idp_sub, name, progress, weak_topics, status}]
  }
```

---

## Edge Cases (Institution Admin)

| Scenario | Behaviour |
|---|---|
| No classes created yet | Home shows empty quick action cards and "Create your first class" CTA |
| Board import conflicts with existing topics | Show diff — new topics highlighted, existing preserved. Admin confirms merge. |
| Teacher invite email already registered | Skip Keycloak invite, directly link existing account to org |
