# G4 Test Plan — Mastery + Post-Exam Review

> Reference only. Work through the four sub-goals in order: schema → mastery → review screen → dashboard strip.

---

## Prerequisites

| | What | How |
|---|---|---|
| P1 | App running (backend + worker + frontend + Postgres) | `docker-compose up` in `haisir-deploy` |
| P2 | V37 migration applied | `alembic current` in backend — must show `V37` at head |
| P3 | A test student account enrolled in at least one platform course node | Log in as student, enrol in a course |
| P4 | A platform exam with ≥ 2 MCQ/T-F questions, each with `topic_id` set | Created via Platform Admin exam builder |

---

## T1 — Schema verification (G4.1)

Confirm the migration landed before touching the app.

```sql
-- Run as postgres superuser / in the haisir DB

-- 1a. questions.topic_id exists and is nullable
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'questions' AND column_name = 'topic_id';
-- Expected: 1 row, data_type = 'uuid', is_nullable = 'YES'

-- 1b. enrollment_topics table exists with correct columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'enrollment_topics'
ORDER BY ordinal_position;
-- Expected: id, student_enrollment_id, topic_id, status, mastery_score,
--           last_studied_at, created_at, updated_at

-- 1c. UNIQUE constraint
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_name = 'enrollment_topics' AND constraint_type = 'UNIQUE';
-- Expected: 1 row (student_enrollment_id, topic_id)

-- 1d. student_risk_state table
SELECT column_name FROM information_schema.columns
WHERE table_name = 'student_risk_state';
-- Expected: student_sub, at_risk_active, last_fired_at

-- 1e. Questions already in DB have NULL topic_id (no backfill)
SELECT COUNT(*) FROM questions WHERE topic_id IS NOT NULL;
-- Expected: 0 (unless you already created new questions with topic_id set)
```

**Pass criteria:** All five queries return the expected rows without error.

---

## T2 — Admin: create questions with topic_id linked (G4.1 + G4.2 setup)

> **RESOLVED (2026-07-02):** T4.1.4 landed and was committed in both repos
> (`haisir-backend@0cb36bd`, `haisir-frontend@df7067e`) — the exam builder now has a per-question
> topic picker, and the static create/patch route persists `questions.topic_id` (plus a new
> `_validate_topic_ids` guard rejecting a `topic_id` that doesn't belong to the target course
> node). Verified live by the user 2026-07-02: the topic dropdown renders in the builder and a
> full student exam attempt runs end-to-end.

Via the Platform Admin exam builder:

1. Open an existing exam (or create one) attached to a node that has topics.
2. For each question in that exam, set the **topic** dropdown to a specific topic. The question editor must send `topic_id` in the `POST /api/exams/.../static` payload.
3. Save the exam.

```sql
-- Verify questions have topic_id set
SELECT q.id, q.question_text, q.topic_id, t.title
FROM questions q
JOIN topics t ON t.id = q.topic_id
WHERE q.topic_id IS NOT NULL
LIMIT 10;
```

**Pass criteria:** At least 2 questions appear with distinct topic IDs.

---

## T3 — First exam attempt: weak score on topic A (G4.2)

**Setup:** The exam must have questions for at least two distinct topics — topic A (mastery target: score < 60%) and topic B (target: score 100%).

**Steps:**

1. Log in as the test student. Navigate to the exam and start a session.
2. Answer **all topic A questions incorrectly** and **all topic B questions correctly**.
3. Submit the exam.

**DB check immediately after submission:**

```sql
-- 3a. enrollment_topics row created for topic A with status = 'weak'
SELECT et.status, et.mastery_score, t.title
FROM enrollment_topics et
JOIN topics t ON t.id = et.topic_id
WHERE et.status = 'weak';
-- Expected: topic A row, mastery_score ≈ 0 (or whatever the scored %)

-- 3b. enrollment_topics row for topic B with status = 'completed'
SELECT et.status, et.mastery_score, t.title
FROM enrollment_topics et
JOIN topics t ON t.id = et.topic_id
WHERE et.status = 'completed';
-- Expected: topic B row, mastery_score = 100

-- 3c. topic_marked_weak notification for the student
SELECT type, title, body, read
FROM notifications
WHERE type = 'topic_marked_weak'
ORDER BY created_at DESC LIMIT 5;
-- Expected: 1 notification for topic A
```

**UI check:**

4. Open the student notification bell → the `topic_marked_weak` notification must appear.

**Pass criteria:** `enrollment_topics` shows topic A as `weak`, topic B as `completed`; notification present.

---

## T4 — Second attempt: EWA mastery recalculation (G4.2)

Take the same exam again. This time answer topic A questions so the raw score is 80%.

**Formula to verify:** `new_mastery = 0.6 × 80 + 0.4 × old_mastery`

If old mastery was 0 → expected new mastery = 48. If old was e.g. 30 → expected = 60.

```sql
-- 4a. Verify updated mastery_score and status
SELECT et.status, et.mastery_score, t.title
FROM enrollment_topics et
JOIN topics t ON t.id = et.topic_id
WHERE t.title = '<topic A title>';
-- Expected: mastery_score ≈ (0.6×80 + 0.4×prior), status = 'weak' if < 60 else 'in_progress' / 'completed'
```

**Acceptance test cross-check:** If prior mastery was exactly 50 → new = 0.6×80 + 0.4×50 = 68 → status should no longer be `weak`.

**Pass criteria:** `mastery_score` matches the EWA formula; no new `topic_marked_weak` notification fired for topic A if it recovered.

---

## T5 — Third weak topic → student_at_risk (G4.2)

You need a **third distinct topic** going weak to trigger the instructor alert.

1. Create (or use an existing) exam with questions for a third topic (topic C). Take it and score below 60% on topic C.

```sql
-- 5a. Verify three weak topics
SELECT COUNT(*) FROM enrollment_topics et
JOIN student_enrollments se ON se.id = et.student_enrollment_id
WHERE se.student_sub = '<student_idp_sub>'
AND et.status = 'weak';
-- Expected: 3

-- 5b. student_at_risk notification in instructor shared queue (recipient_idp_sub = NULL)
SELECT type, recipient_idp_sub, recipient_role, title
FROM notifications
WHERE type = 'student_at_risk'
ORDER BY created_at DESC LIMIT 3;
-- Expected: 1 row, recipient_idp_sub = NULL, recipient_role = 'instructor'

-- 5c. student_risk_state updated
SELECT at_risk_active, last_fired_at
FROM student_risk_state
WHERE student_sub = '<student_idp_sub>';
-- Expected: at_risk_active = true, last_fired_at not null

-- 5d. No duplicate fire — take another weak exam and confirm at_risk_active stays true
--     but no second student_at_risk notification
```

**UI check:** Log in as instructor → check the notification bell → `student_at_risk` alert must appear.

**Pass criteria:** Exactly one `student_at_risk` notification; `student_risk_state.at_risk_active = true`.

---

## T6 — Recovery: at_risk clears when all weak topics recover (G4.2)

Take exams for topic A, B, C and score 80%+ on all of them so none are `weak`.

```sql
-- 6a. No weak topics remain
SELECT COUNT(*) FROM enrollment_topics et
JOIN student_enrollments se ON se.id = et.student_enrollment_id
WHERE se.student_sub = '<student_idp_sub>' AND et.status = 'weak';
-- Expected: 0

-- 6b. student_risk_state cleared
SELECT at_risk_active FROM student_risk_state
WHERE student_sub = '<student_idp_sub>';
-- Expected: at_risk_active = false

-- 6c. No new student_at_risk notification (count must still be 1 from T5)
SELECT COUNT(*) FROM notifications WHERE type = 'student_at_risk';
-- Expected: still 1 (no re-fire until next rising edge)
```

**Pass criteria:** Risk cleared; no spurious re-fire.

---

## T7 — Post-exam review screen (G4.3)

**Setup:** Use the completed session from T3 (at least some wrong answers present).

1. Navigate to `/exam/<session_id>/review`.

**UI checks:**

| # | What to verify | Pass if |
|---|---|---|
| 7a | Score summary bar renders | Shows correct %, correct count, wrong count, skipped count |
| 7b | Wrong/skipped question cards are expanded by default | Red/grey badges visible without clicking |
| 7c | Correct question cards are collapsed | Green badge; must click to expand |
| 7d | Correct answers highlighted green ✓ | Visible in expanded wrong card |
| 7e | Student's wrong answer highlighted red ✗ | Visible in same card |
| 7f | "Ask hAITU to explain this" button on wrong questions | Button visible on wrong/skipped cards |
| 7g | Pattern-analysis opening message loads in chat panel | AI text appears automatically on page load (may take a few seconds) |

> **RESOLVED (2026-07-01):** 7g previously failed on first visit — `POST /api/haitu/pattern-analysis`
> always returned 202 pending on cache-miss and the frontend correctly (per spec) kept the static
> seed bubble forever; the real analysis was never surfaced. Fixed by **G4-patch-2** (inline
> streaming on cache-miss — see `TASKS.md` / `decisions.md` 2026-07-01). Re-verified against the
> live stack 2026-07-01: pattern-analysis now streams real tokens on the first page load.

2. Click "Ask hAITU to explain this" on a wrong question.
   - **Pass:** A streaming explanation appears in the right-hand chat panel.

3. Type a follow-up question in the chat input and send.
   - **Pass:** `exam-review-chat` response streams back; conversation history is preserved in context.

**API-level check (curl):**

```bash
# Pattern analysis
curl -s -X POST https://<host>/api/haitu/pattern-analysis \
  -H "X-Current-Role: student" \
  -H "X-CSRF-Token: <token>" \
  -H "Content-Type: application/json" \
  -b "session=<cookie>" \
  -d '{"attempt_id": "<session_id>"}' | jq .
# Expected: { "analysis": "<2-3 sentence string>" }

# Exam review chat
curl -s -X POST https://<host>/api/haitu/exam-review-chat \
  -H "X-Current-Role: student" \
  -H "X-CSRF-Token: <token>" \
  -H "Content-Type: application/json" \
  -b "session=<cookie>" \
  -d '{"attempt_id": "<session_id>", "message": "Why was Q1 wrong?", "history": []}' \
  --no-buffer
# Expected: SSE stream — lines starting with data:{"token": ...} then data:{"done":true}
```

**Pass criteria:** Pattern analysis returns a string; chat streams; UI renders all question states correctly.

---

## T8 — Security guards on S05 (G4.3)

| # | Scenario | Expected | Result |
|---|---|---|---|
| 8a | `POST /api/haitu/pattern-analysis` with an ongoing session ID | `403` or `400` | ✅ `403` "Session not available or not completed" |
| 8b | `POST /api/haitu/exam-review-chat` with another student's completed session ID | `403` | ✅ `403` "Session not available or not completed" |
| 8c | Navigate to `/exam/<ongoing_session_id>/review` in the browser | Should redirect or show error; no review data displayed | ✅ verified at the API level — `GET /api/exam-sessions/session/{id}/answers` (the data S05 fetches) returns `403` "Cannot review an incomplete attempt" for an ongoing session; a real-browser click-through of the redirect/error UI itself is still recommended but not blocking |
| 8d | `POST /api/haitu/pattern-analysis` with no `X-Current-Role` header | `400` | ✅ `400` "X-Current-Role header required" |

**Verified 2026-07-01** against the live stack (`localhost:8000` direct backend, Bearer JWT for
`student1@haisir.in` / `sub=576ed7e1-94bf-4ce8-bc4e-1b03d26503cc`) using:
- 8b/8d: `attempt_id=fcc4d89f-50c8-434e-9661-1a0e6cfc65a8` (a different student's — `sub=7ac9adf3-3dd1-4d21-9569-61f85a5dd7df` — completed session) / `f391a13a-a0d1-4461-ab80-992e9c349674` respectively.
- 8a/8c: a fresh `pending`-status session (`8c3f30e5-1038-4d96-9b8e-33840bdacc67`) created via `POST /api/exam-sessions/session/create?exam_template_id=7275e5db-b395-4e13-a677-64a218d2c6b8` and left unsubmitted for the test.

---

## T9 — Focus areas strip on /home (G4.4)

**Condition:** Student currently has ≥ 1 weak topic (from T3 or T5).

1. Navigate to `/home`.
2. **Pass:** An orange "Focus areas" chip strip appears **above** the Platform Board section.
3. Each chip shows the weak topic name.
4. Click a chip — verify it navigates to the correct topic or node.

**Condition:** All topics are recovered (from T6).

5. Navigate to `/home`.
6. **Pass:** The "Focus areas" strip is **not rendered** at all.

**API-level check:**

```bash
curl -s https://<host>/api/student/dashboard \
  -H "X-Current-Role: student" \
  -b "session=<cookie>" | jq '.weak_topics'
# Expected: array of { topic_id, topic_title, mastery_score, status } when weak, [] when recovered
```

---

## T10 — Essay exam mastery path (G4.2)

If you have an essay exam with `auto_grade_essay = true`:

1. Submit the essay exam.
2. Wait for the worker to grade (check worker logs or poll `/admin/system/workers`).
3. After grading completes and the session auto-closes:

```sql
SELECT et.status, et.mastery_score FROM enrollment_topics et
WHERE et.student_enrollment_id IN (
  SELECT id FROM student_enrollments WHERE student_sub = '<sub>'
);
-- Expected: mastery row updated post-essay-grade (not before)
```

**Pass criteria:** Mastery is only computed after all essay grading is done, not at submission time.

---

## Closing checklist

| Sub-goal | Verified by | Status |
|---|---|---|
| G4.1 — Schema (V37) | T1 SQL checks | ✅ verified 2026-06-29 (migration applied at V37 head) |
| G4.1 — questions.topic_id in admin exam builder | T2 + SQL | ✅ 2026-07-02 — T4.1.4 landed + committed; topic picker verified live |
| G4.2 — EWA mastery formula | T3 + T4 | ✅ 2026-07-02 — verified live by user through the real admin-built UI (post-T4.1.4) |
| G4.2 — topic_marked_weak notification | T3 UI | ✅ 2026-07-02 — verified live by user |
| G4.2 — student_at_risk at 3 weak topics | T5 | ✅ 2026-07-02 — verified live by user |
| G4.2 — no-refire on second weak exam | T5d | ✅ 2026-07-02 — verified live by user |
| G4.2 — recovery clears risk state | T6 | ✅ 2026-07-02 — verified live by user |
| G4.2 — essay grading triggers mastery | T10 | ✅ 2026-07-02 — verified live by user |
| G4.3 — S05 question rendering | T7a–g | ✅ 2026-07-01 |
| G4.3 — pattern-analysis opening message | T7g | ✅ 2026-07-01 (G4-patch-2 fix confirmed live) |
| G4.3 — exam-review-chat streaming | T7 curl | ✅ 2026-07-01 |
| G4.3 — 403 guards on non-owner / ongoing session | T8 | ✅ 2026-07-01 |
| G4.4 — weak_topics in dashboard API | T9 curl | ✅ 2026-07-02 — verified live by user |
| G4.4 — FocusAreasStrip visible when weak | T9 (1–4) | ✅ 2026-07-02 — verified live by user |
| G4.4 — strip absent when recovered | T9 (5–6) | ✅ 2026-07-02 — verified live by user |

All rows ticked 2026-07-02 — G4 is done, Phase 4 is closed.
