# Teacher & Tutor Personas

> Status: stub — to be defined based on current state.
> See `vision/requirements/04_teacher_tutor.md` for the long-term vision spec.

---

## Essay Grading (deferred — role migration prerequisite)

Instructor and tutor roles are configured in the backend (`UserRole` enum + `permission.py`) but
are **not yet active in the Keycloak realm**. Before adding any instructor/tutor grading
permissions, the role migration steps in `vision/requirements/11_role_migration.md` must be
completed.

In the current increment, essay grading override is a parent responsibility (for parent-owned
exams) and a Platform Admin responsibility (for platform exams). Instructor/tutor essay grading
is explicitly deferred.

When instructor scope is added:
- Instructors will be able to override AI essay grades for exams in their assigned classes.
- Tutors will be able to override AI essay grades for exams they administer.
- The `PATCH .../grade` and `POST .../confirm-grade` permission matrix (in
  `02_auth_and_roles.md`) will be extended with `instructor` and `tutor` roles at that time.

---

## Phase 4 — Doubt Escalation (G2)

Phase 4 introduces the teacher-facing doubt flow: a student can escalate a hAITU doubt to a
teacher, any instructor can see and claim escalated doubts from a shared queue, and the
teacher's reply is persisted into the thread and visible to the student — with no orgs/classes
model (shared instructor queue, `escalated_to=NULL` until claimed).

> **Auth:** all `/api/teachers/me/*` endpoints require `X-Current-Role: instructor` (strict —
> 400 if header missing or any other role; see `02_auth_and_roles.md`). All mutations require
> `X-CSRF-Token`. The student escalate endpoint requires `X-Current-Role: student` + CSRF.

### Student escalate endpoint

| Method | Path | Guard | Effect |
|---|---|---|---|
| `POST` | `/api/doubts/{doubt_id}/escalate` | `student` + CSRF + ownership | Sets `status='escalated'`, `escalated_to=NULL`; 404 if `doubt.student_sub != user.sub` |

Allowed only when `status IN ('new', 'ai_answered')` — the "Request teacher help" CTA in S09
is hidden once the doubt is already `escalated` or `answered`. On success a `system` message
("Escalated to a teacher — you'll be notified when they reply") is appended to the thread.

---

### T06 — Teacher Doubt Inbox (Shared Queue)

**Route:** `/teacher/doubts`

The instructor's shared escalation queue. Shows all escalated doubts that are either unclaimed
(`escalated_to IS NULL`) or claimed by this instructor (`escalated_to = user.sub`), sorted
newest-escalated first.

**Screen elements:**
- Doubt rows: student name, topic title, question preview (truncated), time since escalation,
  status chip (`escalated` / `answered`).
- **"Claim"** button (visible when `escalated_to IS NULL`) → calls claim endpoint; on 409
  (already claimed by another instructor) shows a toast and refreshes the list.
- **"Open"** link (visible when `escalated_to = user.sub` — already mine) → navigates to T07.
- "Doubt Queue" nav link visible only for `X-Current-Role: instructor`; students do not see it.
- Empty state ("No escalated doubts — all caught up") when the shared queue is empty.

**Endpoints:**

| Method | Path | Guard | Response |
|---|---|---|---|
| `GET` | `/api/teachers/me/doubts` | `instructor` | `TeacherDoubtListResponse { items: TeacherDoubtRead[] }` — unclaimed + mine, newest first |
| `POST` | `/api/teachers/me/doubts/{doubt_id}/claim` | `instructor` + CSRF | `ClaimResponse { doubt_id, escalated_to }` — sets `escalated_to=user.sub`; 409 if already claimed by another |

`TeacherDoubtRead` includes: `doubt` (id, status, created_at), `student_name`, `topic_title`,
`escalated_to`, `last_message_at`.

The shared-queue semantics (who sees what and the claim race condition) are documented in
`11_haitu_ai_layer.md` §3.4.

---

### T07 — Teacher Doubt Thread + Reply

**Route:** `/teacher/doubts/[id]`

The instructor's view of a specific doubt thread — all messages in chronological order
(student, AI, teacher, system) plus a reply composer.

**Screen elements:**
- Header: student name + topic title; back link to `/teacher/doubts`.
- Ordered message bubbles using the same pattern as S09 (`03_student.md`), with teacher
  messages rendered in a distinct style (left-aligned, instructor-labelled).
- **Reply composer:** textarea + "Send" button → `POST /api/teachers/me/doubts/{id}/messages`;
  on success appends a `teacher` message bubble and reflects `status='answered'`.
- Status chip reflecting current `status`.

**Endpoint:**

| Method | Path | Guard | Response |
|---|---|---|---|
| `POST` | `/api/teachers/me/doubts/{doubt_id}/messages` | `instructor` + CSRF | Updated `DoubtThreadResponse`; appends a `teacher` `doubt_message`, sets `status='answered'` |

> The `doubt_teacher_replied` notification (emitted to the student after the teacher reply) is
> wired in G3.4 (`10_notifications.md`), not in this endpoint. The reply endpoint itself only
> persists the message and updates the status.
