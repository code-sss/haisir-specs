# Phase 4 Implementation Plan — G4: Mastery + Post-Exam Review (refined)

> Refined via `/plan` reconciliation on 2026-06-28. The Phase 4 plan originally covered G0–G4
> (written 2026-06-24, baseline `6ec91ab`/`47e4ec2`/`3178451`). G0–G3 + the G2-patch are now
> **complete and built** — their detailed task breakdowns are preserved checked in
> `Implementation_planning/TASKS.md` and narrated in `Implementation_planning/progress.md`.
> This document now holds the **remaining** work: **G4 only**, reconciled against the
> now-built G1–G3 code and re-challenged (1 challenger round; amendments folded in; both
> `UNRESOLVED` items resolved on a second look 2026-06-28: enrollment↔topic direction
> confirmed against `get_subtree_node_ids`; recovery gate = dedicated `student_risk_state`
> table folded into V37).
>
> Baseline watermarked at the foot of this file: `backend:9d27e8c frontend:23e1a45 deploy:2ca21d4` (2026-06-28).
>
> **Critical reconciliation (flips the 2026-06-24 Decision #4):** the prior plan asserted
> `questions.topic_id` already existed as a NOT NULL soft FK and that V37 would only
> "verify" it. Live-code verification (2026-06-28) proves this is **false** — the column does
> not exist in any migration, the SQLAlchemy `questions` Table, the `Question` dataclass, or
> `QuestionRepository.get_by_ids`. **V37 must ADD it.** See T4.1.1 decision + T4.1.2.
>
> Confirmed decisions (2026-06-28 refine):
> - `questions.topic_id` is added **NULLABLE** in V37. NOT NULL is not enforceable because
>   legacy rows have no topic linkage and there is no clean backfill source. The application
>   layer requires `topic_id` for newly created questions; legacy rows stay NULL and mastery
>   recalc skips them.
> - `exam_templates.topic_id` is **NOT** added (avoid scope creep). `questions.topic_id` is
>   the single source of truth for mastery attribution and works for both quiz (single-topic)
>   and exam (multi-topic) purposes. Quiz scoping resolves via `questions.topic_id` uniformly.
> - `enrollment_topics` foreign-keys to **`student_enrollments(id)`** (the target table,
>   UNIQUE(`student_sub`, `course_path_node_id`) since V34) — NOT the vision spec's
>   nonexistent `enrollments` table.
> - The review endpoint is `GET /api/exam-sessions/session/{id}/answers` (live path) — NOT
>   `.../review`. S05 consumes `/answers`.
> - `HaituService` exposes only `answer()`/`stream_answer()` (full 4-stage RAG). G4.3 adds a
>   **public no-RAG method**; the private `_dispatch_llm`/`_stream_llm`/`_call_llm_raw` are
>   reused but not exposed outside the service.
> - The `student_at_risk` recovery/re-fire gate is **persistence-based** (query the
>   `notifications` table for an active/unresolved `student_at_risk` for the student), not
>   in-memory — in-memory does not survive worker restarts and breaks multi-worker.
> - Body params canonicalized to **`attempt_id`** (= `exam_sessions.id`) for both new hAITU
>   endpoints, resolving the vision student-spec (`session_id`) vs haitu-spec (`attempt_id`)
>   discrepancy.
> - **Spec-first ordering**: T4.1.1 resolves all divergences before any backend code
>   (user-chosen execution option 1).
> - **Enrollment↔topic coverage (UNRESOLVED #1 resolved 2026-06-28):** a topic's node is
>   covered by an enrollment when the enrolled node **is the topic's node or an ancestor of
>   it** — confirmed by `get_subtree_node_ids` expanding the root (enrolled) nodes downward
>   (recursive CTE `JOIN subtree s ON c.parent_id = s.id`, `course_path_node_repository.py:246-250`).
>   When multiple enrollments cover a topic, attribute to the **deepest (closest-ancestor)**
>   match; skip the topic (no `enrollment_topics` row) if no enrollment covers it.
> - **`student_at_risk` recovery gate (UNRESOLVED #2 resolved 2026-06-28):** a dedicated
>   `student_risk_state(student_sub TEXT PK, at_risk_active BOOLEAN NOT NULL DEFAULT false,
>   last_fired_at TIMESTAMPTZ NULL)` table, created in V37 (no extra migration — V37 is new).
>   Set `at_risk_active = true` when `student_at_risk` fires; set `false` when
>   `count_weak_for_student == 0`. Fire only on the rising edge (<3 → ≥3) AND
>   `at_risk_active == false`. This gives exact BR-TCH-004 hysteresis (no re-fire until a
>   full recovery). Rejected the pure-notifications-table derivation (cannot detect
>   "recovered since last fire" — recovery leaves no record) and the time-window
>   approximation (leaks refires after the window expires).

## ROOT GOAL — G4: Mastery + post-exam review

After any completed quiz or exam, the system recomputes per-topic mastery from the attempt,
flags weak topics, notifies the student (and instructors at 3+ weak), and offers the student
an AI-assisted per-question review of the attempt with pattern analysis.

**Acceptance test**: A student takes a 2-topic exam; topic A scores 50 (weak), topic B scores
100 (completed). A `topic_marked_weak` notification lands in the student's feed. The student
opens S05 post-exam review; the pattern-analysis opening message loads, and "Ask hAITU to
explain this" on a wrong question returns a coherent explanation. A second attempt on topic A
scores 80 → mastery = 0.6·80 + 0.4·50 = 68 (no longer weak). A third topic goes weak,
bringing the weak count to 3 → a `student_at_risk` notification appears in the instructor
shared queue and the "Focus areas" strip on /home shows the weak topics.

**Repos**: [specs] [backend] [frontend] [deploy]

---

## G4.1 — Exam↔topic linkage + enrollment_topics schema (V37)

**Subgoal**: The database and domain layer can attribute each exam-session question to a
topic (for per-topic mastery) and track per-enrollment, per-topic progress in a new
`enrollment_topics` table — all via an additive migration that never drops or renames
existing objects.

**Subgoal test**: V37 applies cleanly on a V36 DB; `Question` rows load with a `topic_id`
attribute (nullable for legacy rows); an `enrollment_topics` row can be inserted, and
`EnrollmentTopicRepository.get_by_enrollment_and_topic` returns it.

**Repos**: [specs] [backend]

### T4.1.1 [specs] — Author all G4 spec deltas and lock divergences

- **Build**:
  - `target/requirements/01_data_model.md`: add the `enrollment_topics` DDL block —
    `enrollment_topics(id UUID PK DEFAULT gen_random_uuid(), student_enrollment_id UUID
    REFERENCES student_enrollments(id) ON DELETE CASCADE, topic_id UUID REFERENCES
    topics(id), status VARCHAR(10) NOT NULL CHECK (status IN
    ('not_started','in_progress','completed','weak')), mastery_score FLOAT NULL CHECK
    (0 <= mastery_score <= 100), last_studied_at TIMESTAMPTZ NULL, created_at TIMESTAMPTZ
    NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())`;
    `UNIQUE(student_enrollment_id, topic_id)`; indexes on `(student_enrollment_id)` and
    `(topic_id, status)`. Note the FK target is `student_enrollments(id)` — NOT vision's
    nonexistent `enrollments`. Port **BR-PROGRESS-001/002/003** verbatim with edge-case rules:
    (a) essay questions with NULL `earned_points` while grading pending are skipped by
    mastery recalc and computed from available points; if ALL questions pending, recalc is
    deferred to the essay-grading auto-complete hook (T4.2.1c); (b) first attempt creates the
    `enrollment_topics` row (status derived from score); (c) questions with NULL `topic_id`
    are excluded from per-topic attribution; (d) multi-topic exams attribute each question
    via `questions.topic_id`. Record the two locked decisions above (questions.topic_id
    NULLABLE; exam_templates.topic_id NOT added).
  - `target/requirements/03_student.md`: add the **S05 exam-review screen** spec with the
    review endpoint path `GET /api/exam-sessions/session/{id}/answers` (NOT `.../review`),
    body params canonicalized to `attempt_id`, and the BR-STU-015/016/017/018 rules
    renumbered to avoid collision with the existing doubt rules in `03_student.md`.
  - `target/requirements/11_haitu_ai_layer.md`: port the exam-review-chat (§3.2) and
    pattern-analysis (§3.2a) contracts, the API contracts for
    `POST /api/haitu/exam-review-chat` and `POST /api/haitu/pattern-analysis` (both body
    param `attempt_id`), token limits (`exam-review-chat` 500), caching note
    (pattern-analysis cached per `attempt_id`, in-memory per-worker v1 limitation),
    BR-AI-001/002/003. Add explicit **403 guards**: 403 when the session is not owned by the
    calling student; 403 when the session status is not in `(completed, failed)`
    (ongoing / pending / grading_pending → 403/400).
  - `target/requirements/04_teacher_tutor.md`: **DEFINE BR-TCH-004** (currently grep-zero) —
    "A student with ≥ 3 weak topics produces a `student_at_risk` shared-queue notification
    for instructors; it does not re-fire until the student recovers above 60% mastery on ALL
    weak topics and then drops below the threshold again" — and reference BR-NOTIF-010 for
    the firing mechanism.
  - Add the per-worker in-memory cache caveat to the pattern-analysis spec (v1: cache is
    per-worker, not cross-process; acceptable for current scale).
- **Done when**: All four target spec files contain the blocks above; grep for
  `enrollment_topics`, `BR-PROGRESS-001`, `attempt_id`, `BR-TCH-004`, `exam-review-chat`,
  `pattern-analysis` returns hits in the expected files.
- **Test**: `grep -c "enrollment_topics" target/requirements/01_data_model.md` ≥ 1 AND
  `grep -c "BR-TCH-004" target/requirements/04_teacher_tutor.md` ≥ 1.
- **Depends on**: None (spec-first; resolves all divergences before any backend code).

### T4.1.2 [backend] — V37 migration adds questions.topic_id (NULLABLE) + enrollment_topics

- **Build**: Author `haisir-backend/alembic/versions/V37_mastery_enrollment_topics.py`
  (migrations live in `alembic/versions/`, NOT `migrations/versions/`). Additive only — no
  drop/rename. (1) `ALTER TABLE questions ADD COLUMN topic_id UUID NULL` (NULLABLE — do NOT
  add a NOT NULL constraint and do NOT attempt a backfill; legacy rows stay NULL). Add a
  B-tree index on `questions(topic_id)` to support the per-topic attribution query.
  (2) `CREATE TABLE enrollment_topics` with the DDL from T4.1.1 —
  `student_enrollment_id UUID REFERENCES student_enrollments(id) ON DELETE CASCADE`,
  `topic_id UUID REFERENCES topics(id)`, status CHECK, mastery_score CHECK,
  `last_studied_at TIMESTAMPTZ NULL`, `created_at`/`updated_at` defaults,
  `UNIQUE(student_enrollment_id, topic_id)`, `idx_enrollment_topics_enrollment
  (student_enrollment_id)`, `idx_enrollment_topics_topic_status (topic_id, status)`.
  `downgrade()` drops the table and the column. Do NOT add `exam_templates.topic_id`.
  (3) `CREATE TABLE student_risk_state(student_sub TEXT PRIMARY KEY, at_risk_active BOOLEAN
  NOT NULL DEFAULT false, last_fired_at TIMESTAMPTZ NULL)` — the persistence backing for the
  `student_at_risk` recovery gate (T4.2.2); folded into V37 so no second migration is needed.
  `downgrade()` drops it. No FK on `student_sub` (sacred no-FK-on-identity rule).
- **Done when**: `alembic upgrade head` on a V36 DB reaches V37 with no error and `\d questions`
  shows `topic_id` nullable; `\d enrollment_topics` matches the DDL; `alembic downgrade -1`
  removes both cleanly.
- **Test**: `assert engine.dialect.has_table(conn, "enrollment_topics")` and
  `inspect(conn).get_columns("questions")` contains `topic_id` with `nullable=True`.
- **Depends on**: T4.1.1 [specs] (DDL + decisions), G3 (V36 baseline applied).

### T4.1.3a [backend] — EnrollmentTopic domain model + repository

- **Build**: Add `EnrollmentTopic` plain dataclass in
  `src/domain/models/enrollment_topic.py` (fields: id, student_enrollment_id, topic_id,
  status, mastery_score, last_studied_at, created_at, updated_at — NO Base subclassing,
  SQLAlchemy imperative mapping). Add `AbstractEnrollmentTopicRepository` in
  `src/domain/repositories/enrollment_topic_repository.py` with methods:
  `upsert(student_enrollment_id, topic_id, status, mastery_score) -> EnrollmentTopic`,
  `get_by_enrollment_and_topic(student_enrollment_id, topic_id) -> EnrollmentTopic | None`,
  `get_weak_for_student(student_sub: str) -> list[EnrollmentTopic]` (JOINs
  `student_enrollments` on `student_enrollment_id` to filter by `student_sub`),
  `count_weak_for_student(student_sub: str) -> int`,
  `list_for_enrollment(student_enrollment_id) -> list[EnrollmentTopic]`. Implement in
  `src/infrastructure/repositories/enrollment_topic_repository.py` with the SQLAlchemy
  Table mapping in `src/infrastructure/models/enrollment_topic.py`. Wire into the DI
  factory used by the API and worker.
- **Done when**: `EnrollmentTopicRepository(...).get_by_enrollment_and_topic(eid, tid)`
  returns the row inserted by `upsert` on a V37 DB; `count_weak_for_student(sub)` returns 0
  before any weak rows and increments when a row is flipped to `weak`.
- **Test**: `assert repo.count_weak_for_student(sub) == 0` initially, then after upsert with
  `status='weak'`, `assert repo.count_weak_for_student(sub) == 1`.
- **Depends on**: T4.1.2 [backend].

### T4.1.3b [backend] — Map questions.topic_id in the Question model + repo

- **Build**: Extend the `Question` dataclass in `src/domain/models/question.py` with
  `topic_id: UUID | None = None`. Extend the SQLAlchemy Table in
  `src/infrastructure/models/question.py` to include the `topic_id` column (nullable).
  Extend `QuestionRepository.get_by_ids` and any other loaders used by the mastery path to
  load `topic_id`. Do NOT enforce NOT NULL at the ORM level (DB is nullable per T4.1.2;
  legacy rows are NULL). Update the `QuestionCreate`/`QuestionUpdate` schemas to accept an
  optional `topic_id`; the exam-authoring route stores it for new questions.
- **Done when**: `QuestionRepository.get_by_ids([...])` returns objects whose `.topic_id`
  matches the column value; a Question created via the API with a `topic_id` persists it and
  a Question loaded that has a NULL DB value reports `.topic_id is None`.
- **Test**: `assert loaded.topic_id == UUID(...)` for a freshly-inserted question;
  `assert legacy_q.topic_id is None` for a pre-V37 row.
- **Depends on**: T4.1.2 [backend].

* G4.1 integration test — V37 applies on V36; `QuestionRepository.get_by_ids` loads
  `topic_id` (NULL for legacy, set for new); `EnrollmentTopicRepository.upsert` +
  `get_by_enrollment_and_topic` round-trips; `count_weak_for_student` returns the correct
  count after status flips.

---

## G4.2 — MasteryService + notifications

**Subgoal**: A `MasteryService` recomputes per-topic mastery after every completed attempt
using the BR-PROGRESS-001/002/003 formula (with all edge-case exclusions), is wired into the
synchronous submit_exam completed branch, the essay-grading auto-complete hook, AND the
manual essay release/finalize/override path, and emits `topic_marked_weak` (to the student)
and `student_at_risk` (to the instructor shared queue, with recovery/re-fire throttling)
notifications.

**Subgoal test**: Documented scenario — topic A first attempt 50 → mastery 50 (weak),
`topic_marked_weak` fired; topic A second attempt 80 → mastery 0.6·80 + 0.4·50 = 68 (not
weak); when the student's weak-topic count crosses to ≥ 3, a single `student_at_risk`
notification appears in the instructor shared queue and does not re-fire until the student
recovers above 60% on all weak topics and drops again.

**Repos**: [backend]

### T4.2.1a [backend] — MasteryService.recompute_for_session algorithm

- **Build**: Add `MasteryService` in `src/domain/services/mastery_service.py` with
  `async recompute_for_session(student_sub: str, session_id: UUID) -> None`. Algorithm:
  load the `exam_sessions` row (must be status `completed`; do nothing if not). Load all
  `exam_session_questions` + their `questions` (via `QuestionRepository.get_by_ids`). Skip
  questions with `topic_id IS NULL` (legacy / unlinked — BR-PROGRESS edge case c). Skip
  questions with `earned_points IS NULL` (essay grading pending — edge case a); compute
  mastery from the remaining available points; if ALL questions are skipped (all pending),
  return without writing — the recalc is deferred to T4.2.1c. For each topic represented by
  the non-skipped questions, compute the per-topic score = sum(earned_points)/sum(max_points)
  × 100 for that topic. Resolve the `student_enrollment_id` (rule confirmed 2026-06-28 against
  `get_subtree_node_ids`): a topic maps to its `course_path_node`
  (`topics.course_path_node_id`, NOT NULL since V4); a topic is **covered** by an enrollment
  when the enrolled node **is the topic's node or an ancestor of it** — i.e. the topic's node
  appears in the descendant set of the enrolled node (expand each enrolled node downward via
  `CoursePathNodeRepository.get_subtree_node_ids(enrolled_node_ids)`, the enrolled nodes from
  `EnrollmentRepository.get_enrolled_node_ids(student_sub)`). When multiple enrollments cover
  a topic, attribute to the **deepest (closest-ancestor)** match. If no enrollment covers the
  topic, skip it (no `enrollment_topics` row). For each topic: load `EnrollmentTopic` via
  `EnrollmentTopicRepository.get_by_enrollment_and_topic`; if absent, first attempt —
  create the row with `mastery_score = per_topic_score` and status from score (<60 weak,
  60–75 in_progress, ≥75 completed) (BR-PROGRESS-001/002/003 + edge case b). If present,
  `mastery_score = 0.6 × per_topic_score + 0.4 × previous_mastery_score`; set status from the
  new score; update `last_studied_at = now()`. Persist via `upsert`. Inject
  `EnrollmentTopicRepository`, `EnrollmentRepository`, `CoursePathNodeRepository`,
  `QuestionRepository`, `ExamSessionRepository`, `TopicRepository`, `NotificationService`
  into the service constructor. No business logic in route files (DDD). (T4.2.2 adds the
  notification emission to this same method — both tasks edit `mastery_service.py`.)
- **Done when**: For a synthetic session with two topics (A: 1/2 = 50, B: 2/2 = 100),
  `recompute_for_session` writes `enrollment_topics` rows with `mastery_score` 50 (weak)
  and 100 (completed); a second call with A at 4/5 = 80 updates A to 68 and status
  in_progress.
- **Test**: `assert enrollment_topic_a.mastery_score == 68.0` after the second call.
- **Depends on**: T4.1.3a [backend], T4.1.3b [backend], T4.2.2 [backend] (notification
  emission is part of the same method).

### T4.2.1b [backend] — Wire MasteryService into submit_exam completed branch

- **Build**: In `src/api/routes/exam_session.py` `submit_exam` (the completed branch:
  non-essay / no pending jobs path that sets `status = 'completed'` at ~L879-886 and calls
  `recompute_score` at ~L889), add `await mastery_service.recompute_for_session(user.sub,
  session_id)` after the status is set to `completed`. Inject `MasteryService` via the
  route's existing DI factory. Do NOT call it on the `grading_pending` branch (that path is
  handled by T4.2.1c). Keep the route a thin handler — move orchestration into the service
  layer if the route is doing business logic (DDD rule). Notifications emit per T4.2.2 inside
  `recompute_for_session`.
- **Done when**: Submitting a non-essay exam and then querying the student's
  `enrollment_topics` shows the freshly-computed mastery scores; submitting an essay-bearing
  exam does NOT trigger a premature recalc (it lands on the `grading_pending` branch).
- **Test**: `assert any(et.mastery_score == expected for et in
  enrollment_topic_repo.list_for_enrollment(eid))` after `submit_exam` returns 200 on a
  completed (non-essay) session.
- **Depends on**: T4.2.1a [backend], T4.2.2 [backend].

### T4.2.1c [backend] — Wire MasteryService into essay-grading auto-complete + worker DI

- **Build**: Extend `_maybe_autocomplete_session` in `src/worker/essay_grading_loop.py`
  (~L75) so that when it transitions `grading_pending -> completed` it: (1) resolves the
  student sub via `fresh_session.user_id` -> `str()` (the current implementation does NOT
  resolve `student_sub`); (2) calls
  `mastery_service.recompute_for_session(student_sub, session_id)` (the deferred recalc for
  the all-questions-pending edge case from T4.2.1a — notifications emit inside it per T4.2.2).
  Wire the worker DI: extend `src/worker/__main__.py` so the worker's session/DI factory
  provides `MasteryService` (with all its injected repos) and `NotificationService` in
  addition to the existing repos. Verify the worker's async session factory can build the
  service. This code runs in the WORKER process, not the API process — ensure the DI factory
  used here is the worker's, not the API's.
- **Done when**: After the essay-grading loop completes the last pending job for a session
  and auto-completes it, the student's `enrollment_topics` mastery scores are populated and
  the appropriate notifications fire; a unit test driving `_maybe_autocomplete_session` with
  a fully-graded session asserts `recompute_for_session` was called with the correct
  `student_sub`.
- **Test**: `assert mock_mastery.recompute_for_session.await_count == 1` and
  `assert mock_mastery.recompute_for_session.await_args.args[0] == expected_student_sub`.
- **Depends on**: T4.2.1a [backend], T4.2.2 [backend], G3 (worker DI for NotificationService).

### T4.2.1d [backend] — Wire MasteryService into manual release/finalize/override path

- **Build**: The essay manual-release path (`POST .../confirm-grade` → `finalized`,
  `PATCH .../grade` → `overridden`, and the `dispute` flow) calls `recompute_score` at
  `exam_session.py` ~L1228 and ~L1323. After each of those transitions (which finalize a
  question's `earned_points`), add `await mastery_service.recompute_for_session(owner_sub
  or student_sub, session_id)` so a teacher-released essay exam updates mastery — without
  this, manually-graded essay exams never contribute to mastery (BR-PROGRESS coverage gap
  caught by the challenger). Resolve the student sub from `session.user_id` -> `str()`.
  Inject `MasteryService` into those route handlers' DI factories. Keep the route a thin
  handler (DDD).
- **Done when**: Releasing/finalizing/overriding an essay grade on a completed session
  updates the student's `enrollment_topics` mastery for the affected topics; a unit test
  asserts `recompute_for_session` is called once per release/finalize/override transition.
- **Test**: `assert mock_mastery.recompute_for_session.await_count == 1` after a
  `confirm-grade` call on a session with one essay question.
- **Depends on**: T4.2.1a [backend], T4.2.2 [backend].

### T4.2.2 [backend] — topic_marked_weak + student_at_risk notifications with recovery gate

- **Build**: In `MasteryService.recompute_for_session`, after each `enrollment_topics`
  `upsert`, diff the old vs new status: if a topic transitions INTO `weak` (old status !=
  `weak` and new == `weak`), call
  `NotificationService.create(recipient_sub=student_sub, recipient_role='student',
  event_type='topic_marked_weak', title='Topic needs attention', body='{topic_title} has
  been flagged as a weak area', action_url='/home/topics/{enrollment_id}')`. After all
  topics for the session are upserted, compute `count_weak_for_student(student_sub)`. If the
  count transitions from <3 to ≥3, AND no active/unresolved `student_at_risk` notification
  exists for the student, call
  `NotificationService.create(recipient_sub=None, recipient_role='instructor',
  event_type='student_at_risk', title='Student needs attention', body='{student_name} is
  struggling across multiple topics', action_url='/teacher/student/{student_sub}')` (shared
  queue). Implement the recovery/re-fire gate (BR-TCH-004 / BR-NOTIF-010) using the
  `student_risk_state` table created in T4.1.2: fire `student_at_risk` only on the rising
  edge (weak count <3 → ≥3) AND `student_risk_state.at_risk_active == false`; on firing, set
  `at_risk_active = true` + `last_fired_at = now()`. After the recalc, if
  `count_weak_for_student(student_sub) == 0` (all weak topics recovered above 60%), set
  `at_risk_active = false` so a future drop to ≥3 can fire again. This gives exact hysteresis
  with no re-fire through fluctuations around 3. Do NOT
  fan out `student_at_risk` to parents (the notifications spec scopes it to the instructor
  shared queue only). Inject `NotificationService` into `MasteryService`.
  `NotificationService.create(...)` and `fan_out_to_parents(...)` already exist from G3;
  `event_type` is a free-form string. Add a `StudentRiskState` dataclass +
  `StudentRiskStateRepository` (`get(student_sub)`, atomic `claim_if_inactive(student_sub)`
  via `UPDATE … SET at_risk_active=true WHERE student_sub=? AND at_risk_active=false
  RETURNING *`, `clear(student_sub)`) in `src/domain/models/` +
  `src/infrastructure/repositories/` (imperative mapping, same pattern as EnrollmentTopic in
  T4.1.3a) — the gate cannot persist state without it. **Concurrency:** `student_at_risk` may
  fire from both the API process (`submit_exam` T4.2.1b / manual release T4.2.1d) and the
  worker (auto-complete T4.2.1c) for the same student. Use the atomic `claim_if_inactive`
  conditional UPDATE so only one of two concurrent recalcs fires the notification (the
  notification is emitted only if the UPDATE returned a row) — mirrors the G2 doubt-claim
  atomic pattern. The `count_weak_for_student == 0 → clear` step is idempotent so concurrent
  clears are safe.
- **Done when**: Driving the documented scenario (topic A 50 then 80 → 68; accumulate to 3
  weak) produces exactly one `topic_marked_weak` per newly-weak topic, exactly one
  `student_at_risk` when the count first crosses to 3, and NO second `student_at_risk` on a
  subsequent weak addition until the student recovers and drops again.
- **Test**: `assert notif_repo.count_by_type('student_at_risk', recipient_role='instructor')
  == 1` after the count goes 2→3 and stays 1 after 3→4 without an intervening recovery.
- **Depends on**: T4.2.1a [backend] (runs inside recompute_for_session), G3
  (NotificationService).

* G4.2 integration test — documented scenario: topic A 50 (weak, mastery 50,
  topic_marked_weak fired) → second attempt 80 (mastery 0.6·80 + 0.4·50 = 68, not weak) →
  accumulate to 3 weak topics → exactly one `student_at_risk` in the instructor shared
  queue → no re-fire on 4th weak without recovery → after recovery (all >60%) and a new
  drop to 3 weak, `student_at_risk` fires again. Also: a teacher-released essay exam (manual
  path) updates mastery.

---

## G4.3 — Post-exam hAITU review (S05)

**Subgoal**: A student can review a completed attempt question-by-question with hAITU:
pattern analysis loads as the opening chat message, per-question "Ask hAITU to explain this"
returns a no-RAG LLM explanation, and a hAITU chat panel scoped to the attempt answers
follow-up questions — all served by two new backend endpoints fronted by APISIX and
rendered by a new S05 frontend screen, with 403 guards for not-owned and non-completed
sessions.

**Subgoal test**: A student opens S05 for an owned completed session; the pattern-analysis
message renders as the first chat bubble; clicking "Ask hAITU to explain this" on a wrong
question returns a coherent explanation; a follow-up typed message gets a coherent reply;
opening S05 for another student's session returns 403; opening an in-progress session
returns 403.

**Repos**: [backend] [frontend] [deploy]

### T4.3.1a [backend] — Public no-RAG LLM methods on HaituService

- **Build**: Add two PUBLIC methods to `HaituService` in
  `src/domain/services/haitu_service.py` that reuse the provider dispatch WITHOUT touching
  the RAG retrieval stages (`answer()`/`stream_answer()` run the full 4-stage RAG;
  `_dispatch_llm`/`_stream_llm`/`_call_llm_raw` are private and must not be called from
  outside the service): `answer_no_rag(messages: list[dict], max_tokens: int = 500) -> str`
  (synchronous, non-streaming, used by `exam-review-chat` and `pattern-analysis`) and
  `stream_no_rag(prompt: str, cancel_event: threading.Event | None = None) -> Iterator[str]`
  (streaming variant for future SSE use). Both build the provider from `HaituSettings` and
  call the provider dispatch directly — no retrieval, no rerank, no vector store. Reuse the
  existing `HaituRateLimiter` (module-level singleton, in-mem `(sub, hour_bucket)`, 20/hr)
  for both new endpoints. Honor BR-AI-001/002/003 (30s timeout, graceful fallback on
  provider failure).
- **Done when**: `HaituService.answer_no_rag([{"role":"user","content":"Say hi"}],
  max_tokens=10)` returns a non-empty string without invoking any vector-store or retrieval
  code path; `answer_no_rag` is `public` (no underscore).
- **Test**: `assert isinstance(svc.answer_no_rag([...]), str) and len(out) > 0` with the
  provider mocked to return a canned completion; assert the mock vector store was NOT
  called.
- **Depends on**: None (HaituService + rate limiter exist from G3).

### T4.3.1b [backend] — POST /api/haitu/exam-review-chat + POST /api/haitu/pattern-analysis

- **Build**: Add two route handlers under the existing `/api/haitu` router
  (`src/api/routes/haitu.py`). Both require `X-Current-Role: student` (strict) and
  `X-CSRF-Token` (mutation). `POST /api/haitu/exam-review-chat` body `{attempt_id: UUID,
  message: str, history: [{role, content}]}` (canonical `attempt_id` = `exam_sessions.id`):
  load the session via `ExamSessionRepository`, assert `session.user_id == user.sub` (else
  403 — not owned), assert `session.status in ('completed', 'failed')` (else 403 for
  non-completed), assemble the exam-review-chat context (assessment title, subject, board,
  all questions with body/correct answer/student answer/is_correct/explanation, the
  pre-computed pattern analysis if available, last 10 messages), call
  `HaituService.answer_no_rag` with the §3.2 system prompt and `max_tokens=500`. Return
  `{response: str}`. `POST /api/haitu/pattern-analysis` body `{attempt_id: UUID}`: same
  ownership + completed guard (403 otherwise), assemble the wrong-answers list, call
  `answer_no_rag` with the §3.2a pattern-analysis prompt, cache the result in a per-worker
  in-memory dict keyed by `attempt_id` (v1 limitation: per-worker, not cross-process —
  document in a code comment and in the spec T4.1.1); subsequent calls with the same
  `attempt_id` return the cached string. Apply `HaituRateLimiter` to both. Move context
  assembly into a `HaituExamReviewService` (DDD) — no business logic in the route files.
- **Done when**: Both endpoints return 200 with a non-empty `response`/`analysis` for an
  owned completed session; return 403 for a session owned by another student; return 403
  for an in-progress session; a second `pattern-analysis` call with the same `attempt_id`
  within the cache window returns the identical string without re-invoking the LLM.
- **Test**: `assert r.status_code == 403` for not-owned; `assert r2.status_code == 403` for
  in-progress; `assert analysis1 == analysis2` for the cache hit.
- **Depends on**: T4.3.1a [backend], T4.1.3b [backend] (Question.topic_id for per-question
  context), T4.1.1 [specs] (contracts + guards).

### T4.3.1c [deploy] — APISIX routes for exam-review-chat + pattern-analysis

- **Build**: Add two APISIX route files in `haisir-deploy/common/routes/`:
  `21-api-haitu-exam-review.json` and `22-api-haitu-pattern-analysis.json` (follow the
  patterns in `common/routes/20-api-notifications.json` and `19-api-haitu.json`). Both
  routes: `priority: 20`, `sec-api-oidc` (secured-api plugin), `limit-count` (per the
  existing hAITU rate config), `request-validation` JSON body schema matching the T4.1.1
  contracts (`attempt_id` UUID required; `exam-review-chat` also `message` + `history`).
  For `exam-review-chat`: set `proxy-buffering` disabled and send/read timeout 600s (mirror
  the doubt route `19-api-haitu.json` streaming config) — harmless if v1 ships as plain JSON.
  For `pattern-analysis`: normal JSON POST with default timeouts. Do NOT hand-create
  `.templated/` copies (the deploy script generates them).
- **Done when**: The repo's route-validation script passes for both files; hitting both
  endpoints through the gateway reaches the backend (403 without auth, 200 with a valid
  student session) — verified against a running stack.
- **Test**: `assert route.status == 200` in the deploy route validation suite for both new
  paths; manual curl through APISIX returns 403 without `X-Current-Role`.
- **Depends on**: T4.3.1b [backend] (endpoints exist to route to), T4.1.1 [specs] (contract
  shape for request-validation schema).

### T4.3.2 [frontend] — S05 exam-review screen + hAITU review chat

- **Build**: Build S05 at route `/home/review/:attempt_id` in `haisir-frontend/src/app/`
  (reusing the existing MainLayout + Header). Data source: `GET
  /api/exam-sessions/session/{id}/answers` (the correct path — NOT `.../review`) for the
  review payload (session summary + items with per-question student answer, correctness,
  explanation; handle both regular and paragraph question shapes per S05 spec). Render the
  score summary bar (score %, correct, wrong, skipped, total), the left scrollable question
  list (correct=green, wrong=red, skipped=grey; wrong/skipped expanded on load per
  BR-STU-016, correct collapsed), and a right hAITU chat panel scoped to this attempt. The
  chat panel reuses the `HaituDoubtPanel` chat-bubble pattern (from G1 hAITU doubt UI) but
  backed by a NEW `useExamReviewChat` hook (raw `fetch` + `credentials:'include'`, no Axios,
  no React Query — project rule). On mount, the hook calls `POST
  /api/haitu/pattern-analysis` with `{attempt_id}` and renders the returned `analysis` as
  the opening chat bubble; the result is cached client-side for the session (BR-STU-017).
  Per-question "Ask hAITU to explain this" button on wrong/skipped questions calls `POST
  /api/haitu/exam-review-chat` with `{attempt_id, message, history}` and renders the
  `response` inline below that question. Typed follow-up messages in the chat panel call the
  same endpoint. Add a back link to /home. Send `X-Current-Role: student` on every call via
  `buildApiHeaders`; mutations send `X-CSRF-Token` via `fetchWithCSRFRetry`. Handle 403 (not
  owned / non-completed) with a friendly "This exam isn't available for review yet" state.
- **Done when**: Navigating to `/home/review/<completed-attempt-id>` renders the score bar,
  the question list (wrong/skipped expanded), the pattern-analysis opening bubble, and
  clicking "Ask hAITU to explain this" appends an explanation below the question; a
  follow-up typed message gets a reply; navigating to another student's attempt_id renders
  the 403 friendly state.
- **Test**: `expect(screen.getByText(/pattern analysis/i)).toBeInTheDocument()` after mount;
  `expect(screen.getByText(/isn't available for review/i)).toBeInTheDocument()` on a 403
  response.
- **Depends on**: T4.3.1b [backend], T4.3.1c [deploy], T4.1.1 [specs] (S05 contract).

* G4.3 integration test — student opens S05 for an owned completed attempt: pattern-analysis
  loads as the opening message; "Ask hAITU to explain this" returns a coherent reply; a
  typed follow-up gets a reply; 403 for not-owned; 403 for in-progress; pattern-analysis
  cached on second open in the same session.

---

## G4.4 — Weak-topic flags + dashboard

**Subgoal**: The student dashboard surfaces the student's current weak topics as a
"Focus areas" strip on /home, backed by a new `weak_topics` field on the
`StudentDashboardRead` API response, populated from `enrollment_topics` where
`status = 'weak'`.

**Subgoal test**: A student with two `enrollment_topics` rows in `weak` status sees a
"Focus areas" strip listing both topic titles on `/home`; a student with zero weak topics
sees no strip.

**Repos**: [backend] [frontend]

### T4.4.1 [backend] — StudentDashboardRead exposes weak_topics

- **Build**: Add a `weak_topics: list[dict]` field to `StudentDashboardRead` in
  `src/schemas/student_dashboard.py` (each item: `{enrollment_id, topic_id, topic_title,
  status, mastery_score}`). In `StudentDashboardService.get_dashboard(user.sub)` (the
  service backing the route at `src/api/routes/student_dashboard.py:34-52`), query
  `EnrollmentTopicRepository.get_weak_for_student(user.sub)` and JOIN each row to
  `TopicRepository.get(topic_id)` for the title. Inject `EnrollmentTopicRepository` into
  the `get_student_dashboard_service` DI factory (the `TopicRepository` is already present
  there). Map the result into the `weak_topics` field. Do not change the existing
  `platform_nodes` or `has_parent_link` fields.
- **Done when**: `GET /api/student/dashboard` returns a `weak_topics` array whose length
  equals `count_weak_for_student(user.sub)` and whose items carry the correct topic titles;
  a student with no weak topics receives `[]`.
- **Test**: `assert resp.json()["weak_topics"] == expected_list` for a fixture student with
  two weak topics.
- **Depends on**: T4.1.3a [backend] (EnrollmentTopicRepository.get_weak_for_student).

### T4.4.2 [frontend] — Focus areas weak-topic strip on StudentHomePage

- **Build**: Add a "Focus areas" strip to `StudentHomePage` (the /home page component)
  consuming the new `weak_topics` dashboard field. The strip renders above (or within) the
  existing enrollment cards grid, shows one chip per weak topic (`{topic_title}` +
  mastery badge), and links each chip to `/home/topics/{enrollment_id}` (the
  `topic_marked_weak` action_url). Hide the strip entirely when `weak_topics` is empty (no
  empty-state placeholder). Use raw `fetch` + `credentials:'include'` via the existing
  dashboard hook; send `X-Current-Role: student`. No new polling — the strip refreshes when
  the dashboard data refreshes.
- **Done when**: A student fixture with two weak topics renders a "Focus areas" strip with
  two chips; a student fixture with zero weak topics renders no strip; the strip is absent
  from the DOM in the zero case.
- **Test**: `expect(screen.queryByText(/focus areas/i)).toBeNull()` when `weak_topics` is
  empty; `expect(screen.getAllByTestId("focus-area-chip")).toHaveLength(2)` when two weak.
- **Depends on**: T4.4.1 [backend].

* G4.4 integration test — a student with two `enrollment_topics` in `weak` status: `GET
  /api/student/dashboard` returns `weak_topics` of length 2 with correct titles; /home
  renders the "Focus areas" strip with 2 chips; a student with zero weak topics sees no
  strip on /home.

---

## ★ G4 root acceptance test

The documented end-to-end scenario runs against a live stack on V37: submit a 2-topic exam
(A:50, B:100) → MasteryService writes enrollment_topics (A=weak/50, B=completed/100), a
`topic_marked_weak` notification lands in the student feed; open S05 review → pattern-analysis
opening message loads, "Ask hAITU to explain this" returns a coherent explanation, typed
follow-up gets a reply, 403 for a not-owned attempt_id; second attempt on A at 80 → mastery
0.6·80 + 0.4·50 = 68 (status in_progress, no longer weak); drive two more topics weak → weak
count crosses to 3 → exactly one `student_at_risk` notification appears in the instructor
shared queue and does not re-fire on a 4th weak without recovery; "Focus areas" strip on
/home shows the current weak topics.

## Cross-repo dependency edges

| Edge | Meaning |
|---|---|
| T4.1.2 [backend] → T4.1.1 [specs] | Migration DDL + decisions come from the spec |
| T4.3.1b [backend] → T4.1.1 [specs] | Endpoint contracts + 403 guards from the spec |
| T4.3.1c [deploy] → T4.1.1 [specs] | APISIX request-validation schema from the spec |
| T4.3.1c [deploy] → T4.3.1b [backend] | Route targets must exist before APISIX routes |
| T4.3.2 [frontend] → T4.3.1b [backend] | S05 consumes the two new endpoints |
| T4.3.2 [frontend] → T4.3.1c [deploy] | S05 calls through the gateway, not direct |
| T4.3.2 [frontend] → T4.1.1 [specs] | S05 screen contract from the spec |
| T4.4.2 [frontend] → T4.4.1 [backend] | Focus areas strip consumes the `weak_topics` field |

## Ready now (no pending dependencies)

- **T4.1.1 [specs]** — author all G4 spec deltas + lock divergences (spec-first; unblocks the
  entire backend).
- **T4.3.1a [backend]** — public no-RAG LLM methods on `HaituService` (depends only on G3,
  which is done).

These two can start in parallel immediately — specs writing and the hAITU no-RAG method have
no interdependency.

<!-- plan-baseline: backend:9d27e8c26b9c1cc78edc0d541e4246696a3c8f29 frontend:23e1a4554cdf74218148c902e2c5bb00b694be00 deploy:2ca21d47b5b696a4f84410bea0b57f0102a6bdaf -->