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
  status chip (`escalated` / `answered`), and a **one-line last-message preview excerpt**
  (latest `doubt_message.content` truncated) so the teacher can scan the queue without opening
  each thread.
- **Status / claim filter (pre-Phase-5 G7, issue 12):** a filter control (All / Unclaimed /
  Claimed by me / Answered) narrows the list client-side. "Unclaimed" is the default landing view
  so the queue surfaces actionable doubts first; claimed-by-others rows are hidden in that view
  (today they render as "Taken" with no way to hide them).
- **"Claim"** button (visible when `escalated_to IS NULL`) → calls claim endpoint; on 409
  (already claimed by another instructor) shows a toast and refreshes the list. A success toast
  confirms the claim (today the UI only surfaces claim errors, not successes).
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

---

## Phase 4 — At-Risk Student Detection (G4.2)

### BR-TCH-004 — `student_at_risk` shared-queue notification + recovery gate

A student with **≥ 3 weak topics** (status `'weak'` in `enrollment_topics`, per
BR-PROGRESS-001) produces a **`student_at_risk`** notification targeted at the `instructor`
shared queue (`recipient_idp_sub IS NULL` — any instructor can see/claim it, the same shared
queue model as escalated doubts in §3.4 of `11_haitu_ai_layer.md`). See `10_notifications.md`
BR-NOTIF-010 for the firing mechanism and notification shape.

**Recovery / re-fire hysteresis (exact, persistence-backed):**

- The notification fires **only on the rising edge** — when the student's weak-topic count
  crosses from `< 3` to `≥ 3` AND the `student_risk_state.at_risk_active` flag for that student
  is `false` (V37 table — see `01_data_model.md`). On firing, `at_risk_active` is set to `true`
  and `last_fired_at` is stamped.
- It **does not re-fire** until the student has fully recovered: `at_risk_active` is set back to
  `false` only when `count_weak_for_student == 0` — i.e. the student has risen **above 60%
  mastery on ALL weak topics** (every weak topic left the `'weak'` state).
- Once recovered (`at_risk_active = false`), a subsequent drop back below the threshold
  (weak count rising `0 → ≥ 3`) fires the notification again — a fresh rising edge.

This gives exact hysteresis: no re-fire while the student still has any weak topics, and a clean
re-fire only after a full recovery followed by a fresh decline. The dedicated `student_risk_state`
table is required because recovery leaves no record in the notifications table (a recovered
student has no active weak topics to query), so the recovery edge cannot be derived from
notifications alone.

> The actual recalculation of `enrollment_topics.status` / `mastery_score` is the
> `MasteryService`'s job (G4.2 — see `Implementation_planning/PLAN.md` T4.2.1a); this rule
> defines only the at-risk detection + notification gate that consumes the resulting weak-topic
> counts.

### At-risk notification routing (pre-Phase-5 G8, issue 9)

The `student_at_risk` notification carries an `action_url` that deep-links the teacher to the
at-risk student's detail view. **No such view exists today** — the only teacher route is
`/teacher/doubts` (the doubt queue), which is the wrong destination for an at-risk signal (an
at-risk student is not a doubt). Pre-Phase-5 (G8/T8.1) sets `action_url = NULL` as the interim:
clicking the notification in the feed marks it read with **no navigation**, so teachers are never
sent to the wrong page.

The proper destination — a `/teacher/students/{student_sub}` page surfacing the at-risk student's
weak topics and recent exam results — is **deferred to Phase 6** with the rest of the teacher /
role-migration tooling. It is tracked in `vision/requirements/backlog.md` BL-002 (Status:
Deferred). When BL-002 ships, `action_url` is set to `/teacher/students/{student_sub}` and the
notification body is enriched with the student's display name (today the body is generic; the
name lookup is a follow-up in the `MasteryService` call path).

Until then, the `10_notifications.md` notification-payload table lists the `student_at_risk`
`action_url` as **NULL (interim)** — not `/teacher/doubts` and not the not-yet-built
`/teacher/student/{student_sub}`.
