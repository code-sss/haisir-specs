# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:9d27e8c frontend:23e1a45 deploy:2ca21d4 (2026-06-28 — refined; G0–G3 + G2-patch complete, G4 remaining)
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
- [ ] T4.1.2 [backend]: V37 migration: add questions.topic_id (NULLABLE) + enrollment_topics + student_risk_state (depends on T4.1.1)
- [ ] T4.1.3a [backend]: EnrollmentTopic domain model + repository (depends on T4.1.2)
- [ ] T4.1.3b [backend]: Map questions.topic_id in Question model + repo (depends on T4.1.2)
- [ ] **G4.1: Exam↔topic linkage + enrollment_topics schema (V37)** — integration test

### G4.2 — MasteryService + notifications
- [ ] T4.2.1a [backend]: MasteryService.recompute_for_session algorithm (depends on T4.1.3a, T4.1.3b, T4.2.2)
- [ ] T4.2.1b [backend]: Wire MasteryService into submit_exam completed branch (depends on T4.2.1a, T4.2.2)
- [ ] T4.2.1c [backend]: Wire MasteryService into essay-grading auto-complete + worker DI (depends on T4.2.1a, T4.2.2)
- [ ] T4.2.1d [backend]: Wire MasteryService into manual release/finalize/override path (depends on T4.2.1a, T4.2.2)
- [ ] T4.2.2 [backend]: topic_marked_weak + student_at_risk w/ persistence recovery gate (depends on T4.2.1a, T3.1.4)
- [ ] **G4.2: MasteryService + notifications** — integration test

### G4.3 — Post-exam hAITU review (S05)
- [ ] T4.3.1a [backend]: Public no-RAG LLM methods on HaituService (no deps)
- [ ] T4.3.1b [backend]: POST /api/haitu/exam-review-chat + POST /api/haitu/pattern-analysis (depends on T4.3.1a, T4.1.3b, T4.1.1)
- [ ] T4.3.1c [deploy]: APISIX routes for both endpoints (depends on T4.3.1b, T4.1.1)
- [ ] T4.3.2 [frontend]: S05 review screen + hAITU review chat (depends on T4.3.1b, T4.3.1c, T4.1.1)
- [ ] **G4.3: Post-exam hAITU review (S05)** — integration test

### G4.4 — Weak-topic flags + dashboard
- [ ] T4.4.1 [backend]: StudentDashboardRead exposes weak_topics (depends on T4.1.3a)
- [ ] T4.4.2 [frontend]: Focus areas weak-topic strip on /home (depends on T4.4.1)
- [ ] **G4.4: Weak-topic flags + dashboard** — integration test

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T4.1.2 [backend]: V37 migration — questions.topic_id + enrollment_topics + student_risk_state (T4.1.1 spec deltas now authored; depends on T4.1.1 ✅)
- T4.3.1a [backend]: Public no-RAG LLM methods on HaituService (no deps — HaituService + rate limiter exist from G3)

T4.1.1 (specs) is complete. T4.1.2 unblocks the G4.1 schema work; the hAITU no-RAG method is
independent of the spec deltas.
