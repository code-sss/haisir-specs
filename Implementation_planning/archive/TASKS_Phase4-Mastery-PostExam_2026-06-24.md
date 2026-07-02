# Progress — Phase 4 (CLOSED 2026-07-02)

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Final baseline: backend:0cb36bd frontend:df7067e deploy:98912f8 (2026-07-02 — Phase 4 signed off; this file archived to `archive/TASKS_Phase4-Mastery-PostExam_2026-06-24.md`)
> Order: G0 → G1 → G2 → G3 → G4 (acyclic). All of G0–G4 + G2-patch + G4-patch/-2/-3/-4 are done.
> `g4_test_plan.md` T1–T10 all verified live against the real admin-built UI post-T4.1.4
> (2026-07-02) — no open items at close. See `progress.md` Completed Phases → Phase 4 for the
> sign-off record.

## G0 — Stabilize HEAD (P0 blocker) [backend][frontend][deploy][specs]

### G0.1 — Fix Python-2 SyntaxErrors + merge feature/rag → main
- [x] T0.1 [backend]: Fix 5 Python-2 except-clause SyntaxErrors (2026-06-24)
- [x] T0.2 [backend]: Merge feature/rag → main (depends on T0.1) (2026-06-24)
- [x] T0.3 [frontend]: Merge feature/rag → main (2026-06-24)
- [x] T0.4 [deploy]: Merge feature/rag → main (2026-06-24)

### G0.2 — Re-verify Phase 3 at HEAD + CI guard + correct stale docs
- [x] T0.5 [backend]: Re-run Phase 3 integration suites at HEAD (depends on T0.2) (2026-06-24)
- [x] T0.6 [frontend]: Re-run Playwright E2E at HEAD (depends on T0.3) (2026-06-24)
- [x] T0.7 [backend]: CI grep guard against Python-2 except syntax (depends on T0.5) (2026-06-25)
- [x] T0.8 [specs]: Correct stale CLAUDE.md Keycloak-roles claim (2026-06-24)

### G0.3 — Remove inline-ML deps + stub the reranker (external-API future-hook)
- [x] T0.9 [backend]: Stub _stage3_rerank to a no-op (depends on T0.2) (2026-06-25)
- [x] T0.10 [backend]: Update the reranker unit tests (depends on T0.9) (2026-06-25)
- [x] T0.11 [backend]: Remove sentence-transformers + torch + uv torch-CPU pin from pyproject (depends on T0.9, T0.10) (2026-06-25)
- [x] T0.12 [backend]: Verify post-cleanup — imports + Phase 3 hAITU suite + lock clean (depends on T0.11, T0.5) (2026-06-25)
- [x] **G0: Stabilize HEAD (P0 blocker)** — integration test (2026-06-25)

## G1 — Doubt persistence + hAITU thread completion [specs][backend][frontend]

### G1.1 — Doubt schema + spec contracts (V35)
- [x] T1.1.1 [specs]: Doubt lifecycle + persistence contracts in 11/03 (2026-06-25)
- [x] T1.1.2 [backend]: V35 migration: doubts + doubt_messages (depends on T1.1.1, T0.2) (2026-06-25)
- [x] T1.1.3 [backend]: Doubt + DoubtMessage domain models (imperative) (depends on T1.1.2) (2026-06-25)
- [x] T1.1.4 [backend]: Doubt Pydantic schemas (depends on T1.1.3) (2026-06-25)
- [x] T1.1.5 [backend]: DoubtRepository + DoubtMessageRepository (depends on T1.1.3) (2026-06-25)
- [x] T1.1.6 [backend]: DoubtService (find-or-create + message writers) (depends on T1.1.5) (2026-06-25)
- [x] T1.1.7 [backend]: Student doubt read routes (S08/S09) (depends on T1.1.4, T1.1.6) (2026-06-25)

### G1.2 — hAITU persistence + doubt_id SSE
- [x] T1.2.1 [backend]: Persist doubt + student message in validation phase (post rate-limit) (depends on T1.1.6, T1.1.7) (2026-06-25)
- [x] T1.2.2 [backend]: Emit doubt_id SSE + persist AI message post-stream (fresh session) (depends on T1.2.1) (2026-06-25)
- [x] T1.2.3 [backend]: No-orphan-on-429 + no-duplicate-on-retry test (depends on T1.2.2) (2026-06-25)
- [x] T1.2.4 [backend]: Disconnect/partial-text persistence test (depends on T1.2.2) (2026-06-25)

### G1.3 — Student doubt inbox (S08) + thread (S09) UI
- [x] T1.3.1 [backend]: Student follow-up message endpoint (depends on T1.1.7) (2026-06-26)
- [x] T1.3.2 [frontend]: Doubt API client + types (depends on T1.3.1) (2026-06-26)
- [x] T1.3.3 [frontend]: S08 doubt inbox page (depends on T1.3.2) (2026-06-26)
- [x] T1.3.4 [frontend]: S09 doubt thread page (depends on T1.3.3) (2026-06-26)
- [x] T1.3.5 [frontend]: Link hAITU panel to persisted thread (doubt_id) (depends on T1.3.4, T1.2.2) (2026-06-26)
- [x] T1.3.6 [frontend]: Student "My Doubts" nav link (depends on T1.3.3) (2026-06-26)
- [x] **G1: Doubt persistence + hAITU thread completion** — integration test (2026-06-26)

## G2 — Teacher escalation [specs][backend][frontend]

### G2.1 — Teacher doubt routes (shared instructor queue)
- [x] T2.1.1 [specs]: Teacher doubt contracts in 04/11 (depends on T1.1.1) (2026-06-27)
- [x] T2.1.2a [backend]: Escalate endpoint + mount doubts router at /api/doubts (depends on T1.1.6, T1.1.7) (2026-06-27)
- [x] T2.1.2b [backend]: Teacher queue GET + claim (mount /api/teachers) (depends on T2.1.2a) (2026-06-27)
- [x] T2.1.2c [backend]: Teacher reply endpoint (depends on T2.1.2b) (2026-06-27)
- [x] T2.1.3 [backend]: Teacher doubt schemas (depends on T2.1.2b, T2.1.2c) (2026-06-27)

### G2.2 — Teacher doubt inbox (T06) + reply (T07) UI
- [x] T2.2.1 [frontend]: Teacher doubt API client + types (depends on T2.1.3) (2026-06-27)
- [x] T2.2.2 [frontend]: T06 teacher doubt inbox page (depends on T2.2.1) (2026-06-27)
- [x] T2.2.3 [frontend]: T07 teacher thread + reply page (depends on T2.2.2) (2026-06-27)
- [x] T2.2.4 [frontend]: Teacher "Doubt Queue" nav link (depends on T2.2.2) (2026-06-27)

### G2.3 — Student "Request teacher help" activation
- [x] T2.3.1 [frontend]: Escalate CTA in S09 + hAITU panel (depends on T2.2.3, T2.1.2a, T1.3.5) (2026-06-27)
- [x] **G2: Teacher escalation** — integration test (2026-06-27)

## G3 — Notifications subsystem [specs][backend][frontend][deploy]

### G3.1 — Notification schema + service
- [x] T3.1.1 [specs]: Fill 10_notifications.md with the notification contract (2026-06-28)
- [x] T3.1.2 [backend]: V36 migration: notifications (depends on T3.1.1, T1.1.2) (2026-06-28)
- [x] T3.1.3 [backend]: Notification model + repository (depends on T3.1.2) (2026-06-28)
- [x] T3.1.4 [backend]: NotificationService + pluggable parent fan-out stub (depends on T3.1.3) (2026-06-28)

### G3.2 — Notification endpoints + APISIX routes
- [x] T3.2.1 [backend]: 4 notification routes + schemas (depends on T3.1.4) (2026-06-28)
- [x] T3.2.2 [deploy]: APISIX route for /api/notifications/* (doubt paths already covered) (depends on T3.2.1) (2026-06-27)

### G3.3 — Notification bell + feed UI
- [x] T3.3.1 [frontend]: Notification types + API + useNotifications (60s poll) (depends on T3.2.1) (2026-06-28)
- [x] T3.3.2 [frontend]: NotificationBell + feed page (depends on T3.3.1) (2026-06-28)
- [x] T3.3.3 [frontend]: Wire bell into shared topbar (all roles) (depends on T3.3.2) (2026-06-28)

### G3.4 — Auto-close cron + wire doubt events
- [x] T3.4.1 [backend]: Auto-close cron loop in worker (depends on T3.1.4, T1.1.2, T1.1.5) (2026-06-28)
- [x] T3.4.2 [backend]: Wire new_doubt_escalated into escalate endpoint (depends on T2.1.2a, T3.1.4) (2026-06-28)
- [x] T3.4.3 [backend]: Wire doubt_teacher_replied into teacher reply (depends on T2.1.2c, T3.1.4) (2026-06-28)
- [x] T3.4.4 [backend]: Wire doubt_auto_closed parent fan-out stub (depends on T3.4.1, T3.1.4) (2026-06-28)
- [x] **G3: Notifications subsystem** — integration test (2026-06-28)

## G2-patch — Re-escalation after teacher answer [backend][frontend][specs]

> **Context:** `find_or_create_doubt` reuses any non-resolved doubt for the same (student, topic), including `answered` doubts. This means a student who asks a follow-up question after a teacher has already replied cannot escalate to a teacher again — the thread is permanently locked. Fix: treat `answered` as closed in `find_or_create_doubt` so a new doubt thread is created, restoring full escalation for new questions on the same topic.

- [x] T2p.1 [specs]: Update 11_haitu_ai_layer.md — add `answered` to the closed-status exclusion in `find_or_create_doubt` (alongside `resolved`); update status machine note (2026-06-28)
- [x] T2p.2 [backend]: `find_or_create_doubt` — treat `answered` like `resolved` (do not reuse); depends on T2p.1 (2026-06-29)
- [x] T2p.3 [frontend]: `canEscalate` in `doubt-status.ts` already correct — smoke-test that teacher-help button appears on the new thread; no code change expected (2026-06-29)

## G4 — Mastery + post-exam review [specs][backend][frontend][deploy]

> Refined 2026-06-28. Key reconciliation: `questions.topic_id` does NOT exist in live code —
> V37 must ADD it (NULLABLE, no backfill). `exam_templates.topic_id` is NOT added.
> Review endpoint is `GET /api/exam-sessions/session/{id}/answers` (not `.../review`).
> New T4.2.1d covers the manual essay release/finalize/override mastery path. Both
> `UNRESOLVED` items resolved 2026-06-28 (second look): enrollment↔topic direction confirmed
> via `get_subtree_node_ids` (deepest-match attribution, skip-if-uncovered); recovery gate =
> dedicated `student_risk_state` table folded into V37 (T4.1.2).

### G4.1 — Exam↔topic linkage + enrollment_topics schema (V37)
- [x] T4.1.1 [specs]: Author all G4 spec deltas + lock divergences (01/03/11/04) (no deps)
- [x] T4.1.2 [backend]: V37 migration: add questions.topic_id (NULLABLE) + enrollment_topics + student_risk_state (depends on T4.1.1) (2026-06-29)
- [x] T4.1.3a [backend]: EnrollmentTopic domain model + repository (depends on T4.1.2) (2026-06-29)
- [x] T4.1.3b [backend]: Map questions.topic_id in Question model + repo (depends on T4.1.2) (2026-06-29)
- [x] T4.1.4 — Wire `questions.topic_id` into the exam builder (re-open 2026-07-01).
  T4.1.1/T4.1.3b were marked done but only covered the V37 column + the Question domain/repo
  mapping; the creation/patch path the admin exam builder actually uses
  (`POST/PATCH /api/exams/{node_id}/static`) never accepts or persists `topic_id`. Without it,
  `MasteryService.recompute_for_session` skips every question (`question.topic_id is None`,
  `src/domain/services/mastery_service.py:142`), so G4.2/G4.4 are unreachable through the real
  admin→student flow — the 2026-06-30 integration tests passed only by setting `topic_id` directly.
  The service layer is already complete (`QuestionExtras.topic_id`, `QuestionUpdateExtras.topic_id`
  + `clear_topic_id`); only schemas + route wiring + frontend + tests remain. A challenger pass
  (2026-07-01) found three additional paths the original 3-task proposal would have missed:
  the edit-hydration response (`ExamTemplateQuestionWithDetails`), the frontend state converter
  (`toQuestionV2`), and JSON import/export. See `decisions.md` 2026-07-01.
  - [x] T4.1.4a [backend][specs]: Add `topic_id: UUID4 | None = None` to `QuestionItemV2`,
    `StaticQuestionPatchItem`, and `ExamTemplateQuestionWithDetails` in `src/schemas/exam.py`. (2026-07-02)
  - [x] T4.1.4b [backend]: Wire `topic_id` in `src/api/routes/exam.py`: `_create_v2_question`
    → `QuestionExtras(topic_id=item.topic_id)`; `_process_patch_item` →
    `QuestionUpdateExtras(topic_id=item.topic_id, clear_topic_id=("topic_id" in
    item.model_fields_set and item.topic_id is None))` mirroring `clear_model_answer`; the
    edit-hydration builder `_build_with_details` → `ExamTemplateQuestionWithDetails(topic_id=
    question.topic_id)` so the picker pre-populates on edit. (2026-07-02)
  - [x] T4.1.4c [backend][tests]: Extend `tests/unit/schemas/test_exam.py`
    (`TestQuestionItemV2NewFields`/`TestStaticQuestionPatchItemNewFields`: `test_topic_id_accepted`
    + default-None assertion). Add a phase4 integration test: create a static exam with
    `topic_id` → PATCH (set + clear) → assert `questions.topic_id` persisted + `GET
    .../questions-with-details` returns it; add a mastery E2E (question with `topic_id` via the
    admin builder → student takes exam → submit → `enrollment_topics` row written — the path
    currently untestable, which is why the gap went undetected). (2026-07-02)
  - [x] T4.1.4d [frontend]: Add `topic_id?: string | null` to `QuestionV2`
    (`src/features/exam/types/exam.types.ts`); map it in `toQuestionV2` + add
    `ApiTemplateQuestion.topic_id` (`src/features/exam/hooks/use-exam-authoring.ts`); expose
    `nodeId` from the `useExamAuthoring` return (read from `?node_id=`). (2026-07-02)
  - [x] T4.1.4e [frontend]: Emit `topic_id` in the `toItem` create-body builder
    (`src/features/exam/api/exam-api.ts`). The PATCH body already `JSON.stringify`s the
    `QuestionV2` array directly, so the three states map correctly with no extra work:
    `undefined` → omitted by `JSON.stringify` → backend preserves; `null` → sent → backend clears
    (`clear_topic_id`); `string` → sent → backend sets. Add `topic_id` to `PlanV2Item` /
    `normalizePlanItem` / `serializeQuestion` in `src/features/exam/domain/json-importer.ts` for
    JSON round-trip (soft pointer — no validation; a dangling UUID after cross-node import just
    means mastery skips that question, per `01_data_model.md`). (2026-07-02)
  - [x] T4.1.4f [frontend]: Add a topic `<select>` to `question-editor.tsx`. Implemented with one
    deviation from the original task text (challenger-reviewed, 2026-07-02): `useTopics(nodeId)`
    is called **once in `ExamBuilder`**, not inside `question-editor.tsx`/threaded as `nodeId` all
    the way down — matches this codebase's existing one-active-fetcher-plus-passive-consumers
    precedent (`node-tree-row.tsx` + `topic-tree-rows.tsx`) and avoids N redundant `useQuery`
    subscriptions per exam. `ExamBuilder` fetches `topics` via `@/features/admin`'s `useTopics`
    (now exported from `admin/index.ts`) and passes `topics: Topic[]` down through
    `ParagraphEditor` to `QuestionEditor` as a plain prop. Picker value = `topic_id ?? ""`;
    selecting "" sets `topic_id: null` (explicit clear); any other value sets `topic_id: <id>`.
    Pre-populates on edit via the T4.1.4b with-details field. Lists draft + live topics unfiltered,
    per spec. (2026-07-02)
  - [x] T4.1.4g [specs]: Update `07_platform_admin.md` exam-builder contract (per-question
    topic picker + reconcile the topics endpoint `/api/admin/nodes/:node_id/topics` → actual
    `/api/topics/{course_path_node_id}`); record `topic_id` optional-at-API / UI-required in the
    `01_data_model.md` exam-builder note. (done 2026-07-01)
- [x] **T4.1.4 — Wire `questions.topic_id` into the exam builder** — all of a–g done (2026-07-02).
  Frontend (d/e/f): `pnpm lint`, `pnpm typecheck`, `pnpm test:coverage` all pass clean (2771/2771
  tests, 100% statements/branches/functions/lines) against the live backend contract from
  T4.1.4a/b/c.
- [x] **G4.1: Exam↔topic linkage + enrollment_topics schema (V37)** — CLOSED 2026-07-02. Backend
  (`haisir-backend@0cb36bd`) and frontend (`haisir-frontend@df7067e`) code verified directly in
  this session: `topic_id` present and wired through `QuestionItemV2` / `StaticQuestionPatchItem` /
  `ExamTemplateQuestionWithDetails`, `_create_v2_question` / `_process_patch_item` /
  `_build_with_details`, plus an added `_validate_topic_ids` guard (400 if a submitted `topic_id`
  doesn't belong to the target course node — not in the original task text, a reasonable hardening
  found during code review). Full backend suite: 4143 passed, 29 skipped, 100% coverage. Frontend
  wiring confirmed in `exam.types.ts`, `use-exam-authoring.ts`, `exam-api.ts`, `json-importer.ts`,
  `question-editor.tsx`, `exam-builder.tsx` (topics fetched once in `ExamBuilder`, passed down —
  per T4.1.4f's documented deviation). `g4_test_plan.md` T2 (admin sets topic via builder UI, saves,
  student takes exam, `enrollment_topics` written) and T10 (essay mastery path) manually verified
  live by the user 2026-07-02 — topic dropdown renders in the builder, exam-taking and focus-areas
  strip work end-to-end.

### G4.2 — MasteryService + notifications
- [x] T4.2.1a [backend]: MasteryService.recompute_for_session algorithm (depends on T4.1.3a, T4.1.3b, T4.2.2) (2026-06-29)
- [x] T4.2.1b [backend]: Wire MasteryService into submit_exam completed branch (depends on T4.2.1a, T4.2.2) (2026-06-29)
- [x] T4.2.1c [backend]: Wire MasteryService into essay-grading auto-complete + worker DI (depends on T4.2.1a, T4.2.2) (2026-06-29)
- [x] T4.2.1d [backend]: Wire MasteryService into manual release/finalize/override path (depends on T4.2.1a, T4.2.2) (2026-06-29)
- [x] T4.2.2 [backend]: topic_marked_weak + student_at_risk w/ persistence recovery gate (depends on T4.2.1a, T3.1.4) (2026-06-29)
- [x] **G4.2: MasteryService + notifications** — integration test (2026-06-30)

### G4.3 — Post-exam hAITU review (S05)
- [x] T4.3.1a [backend]: Public no-RAG LLM methods on HaituService (no deps) (2026-06-29)
- [x] T4.3.1b [backend]: POST /api/haitu/exam-review-chat + POST /api/haitu/pattern-analysis (depends on T4.3.1a, T4.1.3b, T4.1.1) (2026-06-29)
- [x] T4.3.1c [deploy]: APISIX routes for both endpoints (depends on T4.3.1b, T4.1.1) (2026-06-29)
- [x] T4.3.2 [frontend]: S05 review screen + hAITU review chat (depends on T4.3.1b, T4.3.1c, T4.1.1) (2026-06-29)
- [x] **G4.3: Post-exam hAITU review (S05)** — integration test (2026-06-30) — 7a–7f verified manually; 7g (pattern-analysis SSE streaming) blocked by gateway timeout, tracked as G4-patch T4p.2.2/T4p.4.2

### G4.4 — Weak-topic flags + dashboard
- [x] T4.4.1 [backend]: StudentDashboardRead exposes weak_topics (depends on T4.1.3a) (2026-06-29)
- [x] T4.4.2 [frontend]: Focus areas weak-topic strip on /home (depends on T4.4.1) (2026-06-29)
- [x] **G4.4: Weak-topic flags + dashboard** — integration test (2026-06-30) — strip renders with correct topics and mastery %; link bug (href undefined) found and fixed (T4p.5.3/T4p.5.4); strip absent after recovery verified (T6)

## G4-patch — S05 streaming + bug fixes found during G4 testing [backend][frontend][deploy][specs]

> Found during manual G4 walkthrough (2026-06-30). Root cause: exam-review-chat and
> pattern-analysis are slow no-RAG LLM calls behind a gateway with a ~60 s idle timeout —
> the same issue that triggered the topic-doubt SSE conversion in Phase 3. Also captures
> three bug fixes (action_url, focus-areas-strip href, WeakTopicRead.enrollment_id) already
> applied, and one open gap (has_exam hardcoded false).

### G4p.1 — Spec update
- [x] T4p.1.1 [specs]: Update 11_haitu_ai_layer.md §8 — SSE wire format for exam-review-chat
  + pattern-analysis; 202 pending state; 8.7 gateway requirements; 8.8 frontend degradation
  contract (2026-06-30)

### G4p.2 — Backend: stream both endpoints
- [x] T4p.2.1 [backend]: Stream POST /api/haitu/exam-review-chat over SSE (token frames +
  heartbeats + done; JSON fallback {"response":str}; history[].content required; accept
  session_id as deprecated alias for attempt_id) (depends on T4p.1.1) (2026-07-01)
- [x] T4p.2.2 [backend]: Stream POST /api/haitu/pattern-analysis over SSE + add 202 pending
  state (token frames + heartbeats + done; 202 {"status":"pending"} when not ready; idempotent
  per attempt_id; JSON fallback {"analysis":str}) (depends on T4p.1.1) (2026-07-01)
- [x] T4p.2.3 [backend]: DTO alignment — pin exam-review-chat JSON fallback to {"response":str}
  object form only; canonicalize attempt_id (document session_id as deprecated alias); pin
  pattern-analysis fallback to {"analysis":str}; verify /answers shape matches spec (items,
  question_text, string-ID *_answer_options) (depends on T4p.2.1, T4p.2.2) (2026-07-01)

### G4p.3 — Deploy: gateway timeouts
- [x] T4p.3.1 [deploy]: Update APISIX routes 21-api-haitu-exam-review.json and
  22-api-haitu-pattern-analysis.json — proxy_read_timeout 600 s, proxy_send_timeout 600 s,
  proxy-buffering false (was missing, causing 504s) (depends on T4p.1.1) (2026-06-30)
- [x] **G4p.3: Deploy: gateway timeouts** — integration test (2026-06-30) — both route JSON
  files validated with `jq`; 21-api-haitu-exam-review.json already had 600s/proxy-buffering
  from T4.3.1c; 22-api-haitu-pattern-analysis.json updated to match (was 60s/10s, no
  proxy-buffering — the 504 cause for pattern-analysis specifically)

### G4p.4 — Frontend: streaming consumer + graceful opening
- [x] T4p.4.1 [frontend]: Stream exam-review-chat on the frontend — add Accept:
  text/event-stream to askExamReviewChat, route through consumeHaituSSE, lazy AI bubble on
  first token, abort on attempt-id switch/unmount, 45 s idle / 300 s total backstop, JSON
  fallback; resend badge only on clean failure (no tokens received) (depends on T4p.2.1) (2026-07-01)
- [x] T4p.4.2 [frontend]: Stream pattern-analysis + graceful opening — seed chat with friendly
  fallback opening before the call; on first token replace seed + append; on
  202/timeout/error keep seed + show non-blocking notice; update useExamReviewChat effect
  (depends on T4p.2.2) (2026-07-01)
- [x] T4p.4.3 [frontend]: Update unit tests for streaming (lazy bubble, token append, abort,
  JSON fallback, resend still works, seed→replace for pattern-analysis, seed kept on
  empty/pending/timeout); maintain 100% coverage (depends on T4p.4.1, T4p.4.2) (2026-07-01)

### G4p.5 — Bug fixes applied during testing (already fixed, tracked for record)
- [x] T4p.5.1 [backend]: Fix topic_marked_weak action_url — was /home/topics/{enrollment_id}
  (wrong ID type + non-existent route); fixed to /courses?topic={topic_id} (2026-06-30)
- [x] T4p.5.2 [backend]: Fix student_at_risk action_url — was /teacher/student/{sub}
  (non-existent route); fixed to /teacher/doubts (2026-06-30)
- [x] T4p.5.3 [backend]: Add enrollment_id to WeakTopicRead schema — field was declared in
  frontend WeakTopic type but never returned by the API (2026-06-30)
- [x] T4p.5.4 [frontend]: Fix focus-areas-strip chip href — was /home/topics/{enrollment_id}
  (undefined + non-existent route); fixed to /courses?topic={topic_id} (2026-06-30)

### G4p.6 — Open gap: has_exam hardcoded false
- [x] T4p.6.1 [backend]: Wire has_exam in GET /api/student/nodes/{id}/topics — currently
  hardcoded false (comment: "exam linkage not yet implemented"); query exam_templates for a
  published template scoped to the topic's node and return true when one exists. This is
  required for the "Take Exam" button to appear in the new /courses student navigator.
  Until fixed, students must use the legacy /exam?node_id= page to start exams. (2026-07-01)
- [x] T4p.6.2 [frontend]: Once T4p.6.1 lands, wire "Take Exam" click in TopicListPanel to
  navigate to /exam?node_id={nodeId} (or start a session directly) (depends on T4p.6.1) (2026-07-01)

## G4-patch-2 — pattern-analysis never resolves on first load [backend][specs][deploy]

> Found during G4 test-plan item T7g (`Implementation_planning/g4_test_plan.md`) — the
> pattern-analysis opening message never appears on a student's first visit to S05. Root cause:
> `POST /api/haitu/pattern-analysis` always returns 202 pending on cache-miss and kicks off a
> detached `asyncio.create_task` background computation; per spec §8.8.3 (shipped in G4-patch,
> T4p.4.2) the frontend correctly keeps the static seed bubble and does not retry on 202 — so the
> real analysis is only reachable via a second, separate page load, and even then only if it lands
> on the same backend worker process that originally computed it. A client-side polling fix was
> proposed and **rejected** — see `decisions.md` 2026-07-01 — in favour of a backend-only fix that
> computes the analysis inline within the same request/worker via the SSE machinery already proven
> for `exam-review-chat`, removing 202-as-the-common-path entirely.
>
> **Why polling was rejected:** the backend runs `--workers 2` (`haisir-backend/Dockerfile:102`),
> confirmed as the actual deployed default with no shared cache, sticky routing, or clustered
> rate-limit policy anywhere in `haisir-deploy` (APISIX `limit-count` on this route is
> `policy: "local"`). `_PATTERN_ANALYSIS_CACHE` is a worker-local dict. A poll landing on the
> *other* worker process re-triggers `HaituRateLimiter.check_and_increment` (the same 20/hr budget
> shared with `topic-doubt`/`exam-review-chat`) and launches a duplicate LLM computation — the
> opposite of the "costs nothing extra" assumption behind the polling proposal.

### G4p2.1 — Spec correction
- [x] T4p2.1 [specs]: Update `target/requirements/11_haitu_ai_layer.md` §8.2 ("Generated once per
  attempt on S05 page load"), §8.3 (202 contract), §8.4 (caching — document 202 as a rare
  cross-worker fallback, not the common first-call path), §8.8 (note no frontend change is
  needed — real tokens now arrive on the first call) (2026-07-01)

### G4p2.2 — Backend: inline-stream the cache-miss path
- [x] T4p2.2 [backend]: In `post_pattern_analysis` (`src/api/routes/haitu.py`), replace the
  fire-and-forget `asyncio.create_task(_compute_and_cache_pattern_analysis(...))` + immediate 202
  with inline computation on cache-miss: SSE callers get real tokens via the same
  `_generate_sse_from_tokens`/`_pump_token_events`/`HaituService.stream_no_rag` machinery already
  used by `exam-review-chat`; JSON-fallback callers `await answer_no_rag(...)` inline and return
  `{"analysis": ...}` directly. Populate `_PATTERN_ANALYSIS_CACHE[attempt_id]` when the stream
  ends, exactly as today (unchanged replay behaviour on a second load). (depends on T4p2.1) (2026-07-01)
- [x] T4p2.3 [backend]: Concurrent-request guard — replace the `None` in-flight sentinel with the
  detached `asyncio.Task` object itself; a second request for the same `attempt_id` landing on the
  *same* worker while the first is still computing awaits that task via `asyncio.shield(task)`
  (NOT a per-request-owned `Future` — a disconnect on one request must not cancel or hang another
  request awaiting the same shared computation). The cross-worker race (different worker, no
  visibility into the task) is NOT special-cased with 202 — it falls through to its own
  independent live computation on that worker; see the 2026-07-01 correction in
  `target/requirements/11_haitu_ai_layer.md` §8.4 (depends on T4p2.2) (2026-07-01)
- [x] T4p2.4 [backend]: Apply the same shielded-shared-task fix to `_persist_task` in
  `post_topic_doubt` (`haitu.py` ~line 275-279) — identical fire-and-forget
  `asyncio.create_task(...); del _bg`-style pattern with the same factually-incorrect justifying
  comment ("the event loop holds a reference to the task until it completes" — contradicts
  asyncio's own docs on weak task references). Same file, same root cause, cheap to fix while
  touching this pattern; not the cause of the T7g bug itself (topic-doubt is fire-and-forget by
  design — this is a hardening pass, not a behaviour change). (depends on T4p2.3) (2026-07-01)
- [x] T4p2.5 [backend]: Rewrite the now-invalid tests in
  `tests/unit/routes/test_haitu_review.py::TestPostPatternAnalysis` —
  `test_first_call_with_incorrect_answers_returns_202` (TC-PA1),
  `test_cache_sentinel_returns_202` (TC-PA3), `test_failed_session_returns_202` (TC-PA8),
  `test_background_task_populates_cache` (TC-PA10),
  `test_background_task_failure_clears_cache_sentinel` — to assert inline SSE/JSON streaming +
  cache population on cache-miss; add a same-worker concurrent-request test (second request
  awaits the shared task and receives the real result, not 202). TC-PA2/4/5/6/7/9 (cache-hit,
  neutral message, ownership/IDOR, rate-limit, SSE-cache-hit-replay, attempt_id-alias) are
  unaffected — no change expected. Maintain 100% coverage. (depends on T4p2.2, T4p2.3) (2026-07-01)

### G4p2.3 — Deploy: verify gateway readiness (no config change expected)
- [x] T4p2.6 [deploy]: Verify `22-api-haitu-pattern-analysis.json` needs no change —
  `proxy-buffering` disabled + 600s send/read timeouts already shipped in G4p.3 are sufficient for
  a request that now holds the connection open for the full generation instead of returning
  instantly. Note as a watch-item (not a blocker at current scale): longer-held connections make
  the existing `limit-conn: 20 / burst 10 per remote_addr` easier to reach under bursty same-IP
  load (e.g. a classroom finishing exams around the same time). (depends on T4p2.2) (2026-07-01) —
  verified against `haisir-backend@0bcb289` (inline-stream + `asyncio.shield` fix): `jq` confirms
  `upstream.timeout.read`/`send` = 600, `proxy-buffering.disable_proxy_buffering` = true; no file
  change required

### G4p2.4 — Frontend: none required
- No frontend changes. The existing `useExamReviewChat`/`consumeHaituSSE` consumer (shipped in
  G4-patch, T4p.4.2) already replaces the seed bubble on the first SSE token — tokens now arrive
  on the very first call instead of never arriving. No polling loop is being added.

## G4-patch-3 — Silent truncation on stream failure + reasoning-model token starvation [backend][specs]

> Found opportunistically while hardening the G4p2 streaming paths. Both `exam-review-chat` and
> `pattern-analysis` capped `stream_no_rag`/`answer_no_rag` at a hardcoded `max_tokens=500`. Two
> problems: (1) reasoning-capable models spend part of that budget on hidden `reasoning_content`
> before any visible output, so 500 could truncate the visible answer to a few words or nothing;
> (2) a mid-stream pump failure (e.g. the LLM backend going unreachable) silently ended the SSE
> stream with a bare `{"done":true}` — indistinguishable from a short-but-complete answer, in
> violation of the already-written BR-AI-001 error-frame contract.

- [x] T4p3.1 [specs]: Update `target/requirements/11_haitu_ai_layer.md` §8.3 (drop the stale
  "Token limit: 500" line) + §8.6 (2026-07-01 correction note: token-cap removal rationale +
  explicit `{"error":...}` frame on pump failure) (2026-07-01)
- [x] T4p3.2 [backend]: Remove the hardcoded `_REVIEW_TOKEN_LIMIT=500` override from both
  `stream_no_rag`/`answer_no_rag` call sites in `post_exam_review_chat` and
  `_compute_pattern_analysis_stream`/`_compute_pattern_analysis_json` — both now fall back to the
  configured `HAITU__MAX_TOKENS` default (2048) (2026-07-01)
- [x] T4p3.3 [backend]: `HaituService.stream_no_rag` pump failures now push the raised exception
  through the queue (not just `None`) so the consumer re-raises after any tokens already yielded;
  `_pump_token_events` catches that and pushes an explicit `{"error": "I couldn't generate a
  response right now. Please try again in a moment."}` frame before the terminal `None`, matching
  the existing `_PATTERN_ANALYSIS_ERROR_MESSAGE` pattern (depends on T4p3.2) (2026-07-01)
- [x] **G4-patch-3: silent truncation fix** — backend `f6bdf2b` (via `fb121aa`); unit tests
  updated in `test_haitu_service.py` + `test_haitu_review.py`; no frontend change needed — the
  SSE consumer already surfaces `{"error":...}` frames per T4p.4.1 (2026-07-01)

## G4-patch-4 — Deploy: narrow hAITU Coraza WAF exclusion to chat endpoints only [deploy]

> Found via live browser testing while verifying G4.3's exam-review-chat manually. Not filed as a
> task before the fix landed — recorded here retroactively so the audit trail is complete before
> Phase 4 closes.

- [x] T4p4.1 [deploy]: `common/plugin_configs/03-secured-api.json` — exam-review-chat's
  AI-generated markdown feedback (numbered lists, headings, words like "system") was tripping
  RCE/PHP/SQLi false positives (932200, 933160, 942350, 942370, 942430, 942440) beyond the
  existing SQLi exclusion set (942200, 942131/130/340/380/400/410), causing 403s. Narrowed the
  exemption's URI match from the whole `/api/haitu/*` prefix to just `topic-doubt` and
  `exam-review-chat` (pattern-analysis's body is only an `attempt_id` UUID and gets no benefit,
  so it keeps full WAF inspection). Re-confirmed `ctl:ruleRemoveTargetById` (field-scoped removal)
  is unreliable on this Coraza WASM build (APISIX 3.17) via live browser re-test — same finding as
  rule 931130 on `/api/topics-contents/` — so full `ctl:ruleRemoveById` remains the only working
  form; residual risk (all 13 rule IDs disabled request-wide, not just the JSON body, for these
  two endpoints) is accepted and documented inline in the plugin config. (2026-07-01)
- [x] **G4-patch-4: narrow hAITU WAF exclusion** — deploy `98912f8` (2026-07-01)

## Ready now
- **T4.1.4 (all of a–g) DONE and COMMITTED (2026-07-02)** — backend committed as
  `haisir-backend@0cb36bd` ("feat(exam): wire topic_id through static exam create/patch/read");
  frontend committed as `haisir-frontend@df7067e` ("feat(exam): attribute questions to topics for
  per-topic mastery (G4.2)"). Baselined SHAs at the top of this file updated accordingly. Verified
  directly this session: backend full suite 4143 passed / 29 skipped / 100% coverage; code
  inspection confirms `topic_id` wired end-to-end in both repos, plus an added
  `_validate_topic_ids` 400-guard (topic must belong to the target course node) not in the
  original task text. Frontend `useTopics` is called once in `ExamBuilder` and passed down as a
  plain `topics` prop (T4.1.4f's documented deviation from literal `nodeId`-threading).
- **G4.1 goal line CLOSED (2026-07-02)** — `g4_test_plan.md` T2 and T10 manually verified by the
  user against the live stack: topic dropdown renders in the admin exam builder, a full student
  exam attempt runs end-to-end, and the focus-areas strip appears correctly.
- **T7 and T8 (`g4_test_plan.md`) are verified against the live stack (2026-07-01)**: T7 including
  7g (pattern-analysis SSE streaming on first load — confirmed fixed by G4-patch-2); T8's four
  guard scenarios (8a–8d — ownership/IDOR, status-gate, missing-role-header) all returned the
  expected `403`/`400` against a real backend session (student `sub=576ed7e1-...`). Not tracked as
  TASKS.md checkboxes — tracked in `g4_test_plan.md`'s own closing checklist. **T2–T6, T9, T10 all
  verified live (2026-07-02)** — see G4.1 closure note above. `g4_test_plan.md`'s closing checklist
  is fully ticked; no open items remain.
- **G4-patch-2 [backend][specs] DONE (2026-07-01)**: T4p2.1 (spec correction) + T4p2.2–T4p2.5
  (backend) — pattern-analysis cache-miss now computes inline: SSE callers stream real tokens
  on the first call via a detached `asyncio.Task` that broadcasts to a per-request queue; JSON
  callers `await answer_no_rag` inline and return `{"analysis": ...}`; concurrent same-worker
  requests `asyncio.shield` the shared in-flight task and replay the real result (no 202);
  `_persist_task` in `post_topic_doubt` hardened with a strong-reference registry. 202 contract
  and its `PatternAnalysisPendingResponse` schema removed entirely (not merely unreachable
  same-worker) — the cross-worker race case falls through to its own independent live
  computation instead, an accepted rare/low-cost edge case (corrected 2026-07-01, see
  `decisions.md`). 100% coverage held (4115 tests).
- **G4p2.3 [deploy] DONE (2026-07-01)**: T4p2.6 — verified `22-api-haitu-pattern-analysis.json`
  needs no change against `haisir-backend@0bcb289`; `jq` confirms 600s read/send timeouts +
  proxy-buffering disabled already present.
- **G4p.2 [backend] DONE (2026-07-01)**: T4p.2.1/T4p.2.2/T4p.2.3 — exam-review-chat and
  pattern-analysis now SSE-streamed (token frames + 15 s heartbeats + done event; 202 pending
  pattern; JSON fallback {"response":str} / {"analysis":str}; attempt_id canonical,
  session_id alias; rate-limit skips cache hits); 100% coverage held (4099 tests).