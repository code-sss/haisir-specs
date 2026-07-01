# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:9841027 frontend:efc33d8 deploy:fc29884 (2026-07-01 — refined; G0–G3 + G2-patch complete, G4 remaining)
> Order: G0 → G1 → G2 → G3 → G4 (acyclic). G0–G3 + G2-patch are done; G4 is the remaining work.

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
- [x] **G4.1: Exam↔topic linkage + enrollment_topics schema (V37)** — integration test (2026-06-30)

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
- [ ] T4p2.2 [backend]: In `post_pattern_analysis` (`src/api/routes/haitu.py`), replace the
  fire-and-forget `asyncio.create_task(_compute_and_cache_pattern_analysis(...))` + immediate 202
  with inline computation on cache-miss: SSE callers get real tokens via the same
  `_generate_sse_from_tokens`/`_pump_token_events`/`HaituService.stream_no_rag` machinery already
  used by `exam-review-chat`; JSON-fallback callers `await answer_no_rag(...)` inline and return
  `{"analysis": ...}` directly. Populate `_PATTERN_ANALYSIS_CACHE[attempt_id]` when the stream
  ends, exactly as today (unchanged replay behaviour on a second load). (depends on T4p2.1)
- [ ] T4p2.3 [backend]: Concurrent-request guard — replace the `None` in-flight sentinel with the
  detached `asyncio.Task` object itself; a second request for the same `attempt_id` landing on the
  *same* worker while the first is still computing awaits that task via `asyncio.shield(task)`
  (NOT a per-request-owned `Future` — a disconnect on one request must not cancel or hang another
  request awaiting the same shared computation). 202 remains only for the genuine cross-worker
  race (different worker, no visibility into the task). (depends on T4p2.2)
- [ ] T4p2.4 [backend]: Apply the same shielded-shared-task fix to `_persist_task` in
  `post_topic_doubt` (`haitu.py` ~line 275-279) — identical fire-and-forget
  `asyncio.create_task(...); del _bg`-style pattern with the same factually-incorrect justifying
  comment ("the event loop holds a reference to the task until it completes" — contradicts
  asyncio's own docs on weak task references). Same file, same root cause, cheap to fix while
  touching this pattern; not the cause of the T7g bug itself (topic-doubt is fire-and-forget by
  design — this is a hardening pass, not a behaviour change). (depends on T4p2.3)
- [ ] T4p2.5 [backend]: Rewrite the now-invalid tests in
  `tests/unit/routes/test_haitu_review.py::TestPostPatternAnalysis` —
  `test_first_call_with_incorrect_answers_returns_202` (TC-PA1),
  `test_cache_sentinel_returns_202` (TC-PA3), `test_failed_session_returns_202` (TC-PA8),
  `test_background_task_populates_cache` (TC-PA10),
  `test_background_task_failure_clears_cache_sentinel` — to assert inline SSE/JSON streaming +
  cache population on cache-miss; add a same-worker concurrent-request test (second request
  awaits the shared task and receives the real result, not 202). TC-PA2/4/5/6/7/9 (cache-hit,
  neutral message, ownership/IDOR, rate-limit, SSE-cache-hit-replay, attempt_id-alias) are
  unaffected — no change expected. Maintain 100% coverage. (depends on T4p2.2, T4p2.3)

### G4p2.3 — Deploy: verify gateway readiness (no config change expected)
- [ ] T4p2.6 [deploy]: Verify `22-api-haitu-pattern-analysis.json` needs no change —
  `proxy-buffering` disabled + 600s send/read timeouts already shipped in G4p.3 are sufficient for
  a request that now holds the connection open for the full generation instead of returning
  instantly. Note as a watch-item (not a blocker at current scale): longer-held connections make
  the existing `limit-conn: 20 / burst 10 per remote_addr` easier to reach under bursty same-IP
  load (e.g. a classroom finishing exams around the same time). (depends on T4p2.2)

### G4p2.4 — Frontend: none required
- No frontend changes. The existing `useExamReviewChat`/`consumeHaituSSE` consumer (shipped in
  G4-patch, T4p.4.2) already replaces the seed bubble on the first SSE token — tokens now arrive
  on the very first call instead of never arriving. No polling loop is being added.

## Ready now
- **G4-patch-2 [backend][specs][deploy] BLOCKING G4 integration testing (2026-07-01)**: T7(g) of
  `g4_test_plan.md` failed — pattern-analysis stuck on 202 pending on first load. Start with
  T4p2.1 (spec correction), then T4p2.2 → T4p2.3 → T4p2.4 → T4p2.5 (backend), T4p2.6 (deploy
  verification only). No frontend task. Once closed, resume G4 test-plan items T7(g) and T8.
- **G4p.2 [backend] DONE (2026-07-01)**: T4p.2.1/T4p.2.2/T4p.2.3 — exam-review-chat and
  pattern-analysis now SSE-streamed (token frames + 15 s heartbeats + done event; 202 pending
  pattern; JSON fallback {"response":str} / {"analysis":str}; attempt_id canonical,
  session_id alias; rate-limit skips cache hits); 100% coverage held (4099 tests).