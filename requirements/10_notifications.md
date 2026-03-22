# hAIsir — Notifications Specification
> Version 1.0 | Notification feed, delivery model, per-persona types, and API.
> → Depends on: `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`
> → UI mapping: `ui-mapping/ui_notifications.md`

---

## 1. Overview

Notifications are server-generated events delivered to a per-user, per-role feed. They are **not real-time push** — they are polled. The notification bell in the topbar shows an unread count badge. Clicking it opens a notification panel or navigates to `/notifications`.

Each notification belongs to a specific role context. A user with multiple roles has separate notification feeds per role, filtered by `X-Current-Role`.

---

## 2. Delivery Model

**Polling:** Frontend polls `GET /api/notifications/me` on page load and every 60 seconds while the tab is active. No WebSocket or SSE in this version.

**Unread badge:** Shows count of `notifications` where `read = false` for `recipient_keycloak_sub = self` and `recipient_role = current_role`.

**Grouping:** Notifications are grouped by recency — Today, Yesterday, Earlier this week, Older.

**Mark read:** Clicking a notification marks it read (single). "Mark all read" marks all unread in the current role's feed.

**Retention:** Notifications are never deleted. Older than 90 days are archived (hidden from feed but retained in DB).

**BR-NOTIF-001:** Notifications are never deleted — only marked read or archived.
**BR-NOTIF-002:** Unread count resets to 0 when "Mark all read" is triggered. Individual read state updates on click.
**BR-NOTIF-003:** Polling stops when the tab is hidden (`document.visibilityState === 'hidden'`) and resumes on tab focus.
**BR-NOTIF-004:** Each notification has an `action_url` deep link. Clicking the notification navigates to that URL and marks it read.

---

## 3. Notification Types Per Persona

### 3.1 Student (`student` role)

| Type | Trigger | Title | Body | Action URL |
|---|---|---|---|---|
| `doubt_teacher_replied` | Teacher sends message on a doubt | "Teacher replied to your doubt" | "{teacher_name} answered your question about {topic_title}" | `/doubts/{doubt_id}` |
| `assessment_due_soon` | 24hrs before `class_assignment.due_at` | "Assessment due tomorrow" | "{assessment_title} — due {due_at}" | `/assess` |
| `assessment_results_ready` | `assessment_attempts` submitted and scored | "Your results are ready" | "You scored {score}% on {assessment_title}" | `/assess/review/{attempt_id}` |
| `exam_results_ready` | `exam_sessions.status` → `submitted` and score computed | "Your exam results are ready" | "You scored {score}% on {exam_title}" | `/exam/review/{session_id}` |
| `topic_marked_weak` | `enrollment_topics.status` → `weak` | "Topic needs attention" | "{topic_title} has been flagged as a weak area" | `/home/topics/{enrollment_id}` |
| `new_content_uploaded` | Instructor adds content to a topic | "New content available" | "{instructor_name} added content to {topic_title}" | `/home/topics/{enrollment_id}` |
| `doubt_auto_closed` | Doubt auto-closed after 7 days (cron) | "Your doubt was closed" | "Your question about {topic_title} was automatically closed after 7 days. You can raise a new doubt anytime." | `/doubts/{doubt_id}` |

### 3.2 Instructor (`instructor` role)

| Type | Trigger | Title | Body | Action URL |
|---|---|---|---|---|
| `new_doubt_escalated` | Student clicks "Request teacher help" | "Student needs your help" | "{student_name} has a question about {topic_title}" | `/teacher/doubts/{doubt_id}` |
| `class_exam_submitted` | All students in class submit (or due_at passes) | "Class exam complete" | "{class_name} — {submitted}/{total} submitted. Avg: {avg_score}%" | `/teacher/exam-results/{assignment_id}` |
| `student_at_risk` | Student mastery < 50% across 3+ topics | "Student needs attention" | "{student_name} is struggling across multiple topics" | `/teacher/student/{student_sub}` |
| `content_published` | Institution admin imports a board curriculum (I02) or uploads new content to a topic assigned to instructor's class | "Curriculum updated" | "{org_name} updated the curriculum for {subject}" | `/teacher/curriculum/{context_id}` |
| `teacher_added_to_org` | Institution admin adds teacher to org (new or existing account) | "Added to institution" | "{org_name} has added you as a teacher" | `/teacher` |

### 3.3 Tutor (`tutor` role)

| Type | Trigger | Title | Body | Action URL |
|---|---|---|---|---|
| `new_doubt_escalated` | Student escalates doubt in open enrollment | "Student needs your help" | "{student_name} has a question about {topic_title}" | `/teacher/doubts/{doubt_id}` |
| `student_at_risk` | Tutor's student mastery drops | "Student needs attention" | "{student_name} is struggling with {topic_title}" | `/teacher/student/{student_sub}` |

### 3.4 Parent (`parent` role)

| Type | Trigger | Title | Body | Action URL |
|---|---|---|---|---|
| `child_doubt_replied` | Teacher replies to child's doubt | "Teacher responded to {child_name}" | "{teacher_name} answered {child_name}'s question about {topic_title}" | `/parent` (progress tab) |
| `child_assessment_due` | 24hrs before child's assessment due | "{child_name} has an assessment due" | "{assessment_title} — due tomorrow" | `/parent` (assessments tab) |
| `child_weekly_digest` | Every Monday 8am | "Weekly update for {child_name}" | "{child_name} studied {n} topics this week. {status_summary}" | `/parent` |
| `child_streak_milestone` | Child hits 7, 14, 30 day streak | "{child_name} is on a streak! 🎉" | "{child_name} has studied for {n} days in a row" | `/parent` |
| `child_doubt_auto_closed` | Child's doubt auto-closed after 7 days | "{child_name}'s question was closed" | "{child_name}'s question about {topic_title} was closed after 7 days without resolution" | `/parent` (progress tab) |

### 3.5 Institution Admin (`institution_admin` role)

| Type | Trigger | Title | Body | Action URL |
|---|---|---|---|---|
| `class_no_teacher` | Class has no instructor after 48hrs | "Class needs a teacher" | "{class_name} has no teacher assigned" | `/institution/classes` |
| `student_at_risk_admin` | Class average drops below 50% | "Class performance alert" | "{class_name} average has dropped to {avg}%" | `/institution/analytics` |
| `board_content_updated` | Admin publishes board update | "Curriculum update available" | "{board_name} v{version} has been published. Your adopted curriculum has been updated." | `/institution/curriculum` |

### 3.6 Admin (`admin` role)

| Type | Trigger | Title | Body | Action URL |
|---|---|---|---|---|
| `institution_registration` | New institution registers | "New institution registration" | "{institution_name} from {city} has requested to join" | `/admin/institutions` |
| `tutor_published` | Tutor goes live in marketplace | "New tutor listed" | "{tutor_name} is now live in the marketplace" | `/admin/tutors` |
| `haitu_resolution_dropped` | Monthly hAITU resolution rate < threshold (default 80%) | "hAITU resolution rate dropped" | "Platform resolution rate is {rate}% this month — below the {threshold}% threshold" | `/admin` |
| `board_publish_confirmed` | SuperAdmin publishes board content | "Board content published" | "{board_name} v{version} published to {n} institutions" | `/admin/boards` |

---

## 4. Generation Rules

**BR-NOTIF-005:** Notifications are generated server-side by domain services — not by route handlers. Each service that triggers a notification calls a `NotificationService.create()` method.

**BR-NOTIF-006:** `doubt_teacher_replied` is generated when `POST /api/doubts/{doubt_id}/messages` is called with `sender_type = 'teacher'`. It fires for the student AND for each linked parent (`child_doubt_replied`).

**BR-NOTIF-007:** `assessment_due_soon` is generated by a scheduled job (cron) running every hour, looking for assignments where `due_at` is between now and now+24hrs and no `assessment_due_soon` notification has already been sent for that assignment+student combination.

**BR-NOTIF-008:** `child_weekly_digest` is generated by a cron job every Monday at 8am IST. It generates one notification per linked parent per child.

**BR-NOTIF-009:** `haitu_resolution_dropped` fires at most once per week. If rate is still below threshold the following week, it fires again.

**BR-NOTIF-010:** `student_at_risk` (for instructor) fires when a student's mastery drops below 50% on a third topic. It does not re-fire until the student recovers above 60% on all topics and drops again — prevents notification spam.

**BR-NOTIF-011:** Doubt auto-close is performed by a scheduled job (cron) running every hour. It queries `doubts` where `status != 'resolved'` and `auto_close_at <= now()` (uses `idx_doubts_auto_close` index). For each matched doubt: set `status = 'resolved'`, `resolved_at = now()`, and append a system `doubt_message` with `sender_type = 'ai'`, `body = "This doubt was automatically closed after 7 days."`. A `doubt_auto_closed` notification is sent to the student, and a `child_doubt_auto_closed` notification is sent to each linked parent.

---

## 5. Inline Actions

Some notifications have inline action buttons rendered directly in the notification item — so the user can act without navigating away:

| Type | Inline action |
|---|---|
| `new_doubt_escalated` | "Reply now →" — navigates to doubt reply thread |
| `class_no_teacher` | "Assign teacher →" — navigates to class detail |
| `institution_registration` | "Review →" — navigates to pending institutions |
| `tutor_published` | "View →" — navigates to published tutors |
| `class_exam_submitted` | "View results →" — navigates to exam results |

---

## 6. Filter Tabs Per Persona

Each persona's notification feed has filter tabs to narrow the feed:

| Persona | Filter tabs |
|---|---|
| Student | All / Doubts / Assessments / Content |
| Instructor | All / Doubts / Exams / Alerts |
| Tutor | All / Doubts / Alerts |
| Parent | All / {child_name} (one tab per linked child) |
| Institution Admin | All / Classes / People / Curriculum |
| Admin | All / Institutions / Tutors / System |

---

## 7. API Endpoints

```
GET /api/notifications/me?role={}&filter={}&limit=50&offset=0
→ Auth: any role
→ Query: role defaults to X-Current-Role header
→ Returns: {
    unread_count: int,
    items: [{
      id, type, title, body, action_url,
      read, created_at, group: "today"|"yesterday"|"earlier"|"older"
    }]
  }

PATCH /api/notifications/{notification_id}/read
→ Auth: any role (own notification only)
→ Returns: {read: true}

PATCH /api/notifications/me/read-all
→ Auth: any role
→ Body: {role: str}
→ Returns: {marked_count: int}
→ Side effect: sets read=true on all unread notifications for recipient+role

GET /api/notifications/me/unread-count
→ Auth: any role
→ Returns: {count: int}
→ Used for topbar badge polling (lightweight — no full payload)
```

---

## 8. Edge Cases

| Scenario | Behaviour |
|---|---|
| User has 0 notifications | Show empty state: icon + "You're all caught up" |
| Notification `action_url` points to deleted resource | Navigate to URL; destination page handles 404 gracefully |
| Parent has 2 linked children | Per-child filter tabs in parent notification feed |
| `haitu_resolution_dropped` — rate recovers then drops again | New notification fires on each new week it's below threshold |
| User offline when notification generated | Notification persists in DB — delivered on next poll |
| Notification generated for a suspended user | Still stored — delivered when account is restored |
