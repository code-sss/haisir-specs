# Notifications

> Phase 4 target spec (G3). See `vision/requirements/10_notifications.md` for the long-term persona/type catalogue.
> → Depends on: `01_data_model.md`, `02_auth_and_roles.md`, `11_haitu_ai_layer.md`

---

## 1. Data Model (V36)

### `notifications` table

```sql
notifications (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipient_idp_sub TEXT NULL,                          -- NULL = shared queue for the role
  recipient_role   VARCHAR(20) NOT NULL,                -- role that receives this notification
  type             VARCHAR(40) NOT NULL,                -- event type (see §3)
  title            TEXT        NOT NULL,
  body             TEXT,
  action_url       TEXT NULL,                           -- deep-link URL; may be NULL
  read             BOOLEAN     NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
)
```

**Indexes:**
- `idx_notifications_recipient` on `(recipient_idp_sub)`
- `idx_notifications_role_unread` on `(recipient_role, read)`
- `idx_notifications_unread_personal` partial: `WHERE read = false AND recipient_idp_sub IS NOT NULL`
- `idx_notifications_shared_unread` partial: `WHERE read = false AND recipient_idp_sub IS NULL`

**No FK** on `recipient_idp_sub` — identity is a Keycloak sub as a raw TEXT string, per the project rule (no local users table).

---

## 2. Shared-Queue Semantics

A notification is either **personal** or **shared-queue**:

| `recipient_idp_sub` | `recipient_role` | Meaning |
|---|---|---|
| `NULL` | `'instructor'` | Visible to every authenticated user with `X-Current-Role: instructor` |
| `<user sub>` | `'student'` | Visible only to that specific student |

**Feed query** (used by all four endpoints):

```sql
WHERE (recipient_idp_sub = :sub
       OR (recipient_idp_sub IS NULL AND recipient_role = :role))
  AND created_at >= now() - INTERVAL '90 days'
```

**Known v1 limitation:** Marking a shared-queue notification read via `PATCH /api/notifications/{id}/read` marks it read globally for all users of that role — there is no per-user read tracking on shared rows. This is documented in the endpoint docstring and known to the team.

---

## 3. Event Types (Phase 4)

These are the notification types wired in Phase 4 (G3.4). Additional types from the long-term vision (assignments, weekly digests, etc.) are deferred.

| Type | `recipient_role` | Shared queue? | Trigger |
|---|---|---|---|
| `new_doubt_escalated` | `instructor` | Yes (`recipient_idp_sub NULL`) | Student calls `POST /api/doubts/{id}/escalate` |
| `doubt_teacher_replied` | `student` | No (personal) | Teacher calls `POST /api/teachers/me/doubts/{id}/messages` |
| `doubt_auto_closed` | `student` | No (personal) | Hourly cron finds doubt past `auto_close_at` |
| `child_doubt_replied` | `parent` | No (personal, per parent) | Same trigger as `doubt_teacher_replied`; fan-out via `fan_out_to_parents` (no-op stub in v1 — no parent_child_links) |
| `child_doubt_auto_closed` | `parent` | No (personal, per parent) | Same trigger as `doubt_auto_closed`; fan-out stub in v1 |
| `topic_marked_weak` | `student` | No (personal) | `MasteryService` sets `enrollment_topics.status = 'weak'` (G4) |
| `student_at_risk` | `instructor` | Yes (shared) | Student has 3+ weak topics (G4) |

**Notification payload shapes:**

| Type | Title | Body template | Action URL |
|---|---|---|---|
| `new_doubt_escalated` | "Student needs your help" | "{student_name} has a question about {topic_title}" | `/teacher/doubts/{doubt_id}` |
| `doubt_teacher_replied` | "Teacher replied to your doubt" | "{teacher_name} answered your question about {topic_title}" | `/doubts/{doubt_id}` |
| `doubt_auto_closed` | "Your doubt was closed" | "Your question about {topic_title} was automatically closed after 7 days of inactivity." | `/doubts/{doubt_id}` |
| `child_doubt_replied` | "Teacher responded to {child_name}" | "{teacher_name} answered {child_name}'s question about {topic_title}" | `/parent` |
| `child_doubt_auto_closed` | "{child_name}'s question was closed" | "{child_name}'s question about {topic_title} was closed after 7 days of inactivity." | `/parent` |
| `topic_marked_weak` | "Topic needs attention" | "{topic_title} has been flagged as a weak area" | `/home/topics/{enrollment_id}` |
| `student_at_risk` | "Student needs attention" | "{student_name} is struggling across multiple topics" | `/teacher/student/{student_sub}` |

---

## 4. API Endpoints

All four endpoints live under `/api/notifications` (registered in `src/api/router.py`). All require a valid `X-Current-Role` header (any role); mutations additionally require `X-CSRF-Token`.

### GET /api/notifications/me

```
GET /api/notifications/me?limit=50&offset=0
X-Current-Role: <role>

200 OK
{
  "unread_count": 3,
  "items": [
    {
      "id": "...",
      "type": "new_doubt_escalated",
      "title": "Student needs your help",
      "body": "...",
      "action_url": "/teacher/doubts/...",
      "read": false,
      "created_at": "2026-06-27T10:00:00Z",
      "group": "today"           -- "today" | "yesterday" | "earlier" | "older"
    }
  ]
}
```

Filter logic: personal OR shared-queue rows for `(sub, role)` within the 90-day window, ordered newest first.

**BR-NOTIF-003:** The feed is capped at a 90-day sliding window — notifications older than 90 days are excluded from all API responses (retained in the DB but never deleted).

### PATCH /api/notifications/{notification_id}/read

```
PATCH /api/notifications/{id}/read
X-Current-Role: <role>
X-CSRF-Token: <token>

200 OK  { "read": true }
404     -- id not found or not accessible for this (sub, role)
```

Updates `read = true` where `id = :id AND (recipient_idp_sub = :sub OR (recipient_idp_sub IS NULL AND recipient_role = :role))`. Returns 404 when rowcount = 0.

**V1 caveat:** Marking a shared-queue row read marks it read globally for all members of the role — there is no per-user tracking on shared notifications.

### PATCH /api/notifications/me/read-all

```
PATCH /api/notifications/me/read-all
X-Current-Role: <role>
X-CSRF-Token: <token>
Content-Type: application/json
{ "role": "instructor" }

200 OK  { "marked_count": 5 }
403     -- body.role != X-Current-Role value
```

Marks all unread personal + shared-queue notifications read for `(sub, role)`.

### GET /api/notifications/me/unread-count

```
GET /api/notifications/me/unread-count
X-Current-Role: <role>

200 OK  { "count": 3 }
```

Lightweight count query — used for topbar badge polling (avoids fetching full payloads).

---

## 5. Polling Contract

**BR-NOTIF-003:** Frontend polls `GET /api/notifications/me/unread-count` every 60 seconds while the tab is active. The `useNotifications` hook registers a `visibilitychange` listener:
- `document.visibilityState === 'hidden'` → pause the polling interval
- `document.visibilityState === 'visible'` → resume interval and immediately refresh the count

Full feed (`GET /api/notifications/me`) is fetched on `/notifications` page load and after `markRead` / `markAllRead` mutations. **No WebSocket or SSE** in this version.

---

## 6. Auto-Close Cron (BR-NOTIF-011)

The worker runs an `auto_close_doubts_loop` coroutine (registered in `src/worker/__main__.py` as task `t6`). It polls hourly.

**Each tick:**
1. Query: `SELECT id, student_sub FROM doubts WHERE status != 'resolved' AND auto_close_at <= now()` (uses `idx_doubts_auto_close` partial index).
2. For each matched doubt:
   a. `UPDATE doubts SET status = 'resolved', resolved_at = now() WHERE id = :id`
   b. `INSERT INTO doubt_messages (doubt_id, sender_type, content) VALUES (:id, 'ai', 'This doubt was automatically closed after 7 days of inactivity.')`
   c. `NotificationService.create(recipient_sub=student_sub, recipient_role='student', type='doubt_auto_closed', title='Your doubt was closed', body='...', action_url='/doubts/{doubt_id}')`
   d. `NotificationService.fan_out_to_parents(child_sub=student_sub, type='child_doubt_auto_closed', ...)` — no-op stub in v1 (returns `[]` when no `parent_child_links` rows exist)
3. Commit per doubt (not batch).

The `doubts.auto_close_at` column defaults to `now() + interval '7 days'` at row creation (set in T1.1.2/V35 migration). It is not reset on follow-up messages in v1.

---

## 7. Generation Rules (Phase 4)

**BR-NOTIF-005:** Notifications are generated by domain services — not route handlers. Each lifecycle event calls `NotificationService.create()`.

**BR-NOTIF-006:** `doubt_teacher_replied` fires when `POST /api/teachers/me/doubts/{id}/messages` succeeds (`status = 'answered'`). It creates a personal notification for the student (`recipient_idp_sub = doubt.student_sub`). `fan_out_to_parents` is called but is a no-op stub in v1.

**BR-NOTIF-010:** `student_at_risk` (G4) fires when a student has ≥ 3 weak topics. It is a shared-queue notification for the `instructor` role (`recipient_idp_sub NULL`). It does not re-fire until the student recovers.

**BR-NOTIF-011:** See §6 (auto-close cron).

---

## 8. Retention

Notifications are **never deleted** from the database. The 90-day window is a display filter only (API excludes `created_at < now() - interval '90 days'`). DB archival is deferred.

---

## 9. UI Screens (Phase 4)

| Screen | Route | Description |
|---|---|---|
| Notification bell | Shared topbar (all roles) | Bell icon with unread-count badge (red pill, hidden when count=0); clicks navigate to `/notifications` |
| Notification feed | `/notifications` | Lists notifications grouped by recency (Today / Yesterday / Earlier / Older); "Mark all read" button; empty state "You're all caught up" |

Bell is rendered in `src/components/layout/header/header.tsx` for all authenticated roles (inside the existing `user.name ?` conditional). Feed page is `src/app/notifications/page.tsx` inside `MainLayout + Header`, guarded by `useAuth`.
