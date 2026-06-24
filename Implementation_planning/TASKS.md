# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:a139208 frontend:47e4ec2 deploy:3178451 (2026-06-24)
> Order: G0 → G1 → G2 → G3 → G4 (acyclic). G0 is the P0 stabilization that must land first.

## G0 — Stabilize HEAD (P0 blocker) [backend][frontend][deploy][specs]

### G0.1 — Fix Python-2 SyntaxErrors + merge feature/rag → main
- [x] T0.1 [backend]: Fix 5 Python-2 except-clause SyntaxErrors (2026-06-24)
- [x] T0.2 [backend]: Merge feature/rag → main (depends on T0.1) (2026-06-24)
- [x] T0.3 [frontend]: Merge feature/rag → main (2026-06-24)
- [x] T0.4 [deploy]: Merge feature/rag → main (2026-06-24)

### G0.2 — Re-verify Phase 3 at HEAD + CI guard + correct stale docs
- [ ] T0.5 [backend]: Re-run Phase 3 integration suites at HEAD (depends on T0.2)
- [ ] T0.6 [frontend]: Re-run Playwright E2E at HEAD (depends on T0.3)
- [ ] T0.7 [backend]: CI grep guard against Python-2 except syntax (depends on T0.5)
- [ ] T0.8 [specs]: Correct stale CLAUDE.md Keycloak-roles claim

### G0.3 — Remove inline-ML deps + stub the reranker (external-API future-hook)
- [ ] T0.9 [backend]: Stub _stage3_rerank to a no-op (depends on T0.2)
- [ ] T0.10 [backend]: Update the reranker unit tests (depends on T0.9)
- [ ] T0.11 [backend]: Remove sentence-transformers + torch + uv torch-CPU pin from pyproject (depends on T0.9, T0.10)
- [ ] T0.12 [backend]: Verify post-cleanup — imports + Phase 3 hAITU suite + lock clean (depends on T0.11, T0.5)
- [ ] **G0: Stabilize HEAD (P0 blocker)** — integration test

## G1 — Doubt persistence + hAITU thread completion [specs][backend][frontend]

### G1.1 — Doubt schema + spec contracts (V35)
- [ ] T1.1.1 [specs]: Doubt lifecycle + persistence contracts in 11/03
- [ ] T1.1.2 [backend]: V35 migration: doubts + doubt_messages (depends on T1.1.1, T0.2)
- [ ] T1.1.3 [backend]: Doubt + DoubtMessage domain models (imperative) (depends on T1.1.2)
- [ ] T1.1.4 [backend]: Doubt Pydantic schemas (depends on T1.1.3)
- [ ] T1.1.5 [backend]: DoubtRepository + DoubtMessageRepository (depends on T1.1.3)
- [ ] T1.1.6 [backend]: DoubtService (find-or-create + message writers) (depends on T1.1.5)
- [ ] T1.1.7 [backend]: Student doubt read routes (S08/S09) (depends on T1.1.4, T1.1.6)

### G1.2 — hAITU persistence + doubt_id SSE
- [ ] T1.2.1 [backend]: Persist doubt + student message in validation phase (post rate-limit) (depends on T1.1.6, T1.1.7)
- [ ] T1.2.2 [backend]: Emit doubt_id SSE + persist AI message post-stream (fresh session) (depends on T1.2.1)
- [ ] T1.2.3 [backend]: No-orphan-on-429 + no-duplicate-on-retry test (depends on T1.2.2)
- [ ] T1.2.4 [backend]: Disconnect/partial-text persistence test (depends on T1.2.2)

### G1.3 — Student doubt inbox (S08) + thread (S09) UI
- [ ] T1.3.1 [backend]: Student follow-up message endpoint (depends on T1.1.7)
- [ ] T1.3.2 [frontend]: Doubt API client + types (depends on T1.3.1)
- [ ] T1.3.3 [frontend]: S08 doubt inbox page (depends on T1.3.2)
- [ ] T1.3.4 [frontend]: S09 doubt thread page (depends on T1.3.3)
- [ ] T1.3.5 [frontend]: Link hAITU panel to persisted thread (doubt_id) (depends on T1.3.4, T1.2.2)
- [ ] T1.3.6 [frontend]: Student "My Doubts" nav link (depends on T1.3.3)
- [ ] **G1: Doubt persistence + hAITU thread completion** — integration test

## G2 — Teacher escalation [specs][backend][frontend]

### G2.1 — Teacher doubt routes (shared instructor queue)
- [ ] T2.1.1 [specs]: Teacher doubt contracts in 04/11 (depends on T1.1.1)
- [ ] T2.1.2a [backend]: Escalate endpoint + mount doubts router at /api/doubts (depends on T1.1.6, T1.1.7)
- [ ] T2.1.2b [backend]: Teacher queue GET + claim (mount /api/teachers) (depends on T2.1.2a)
- [ ] T2.1.2c [backend]: Teacher reply endpoint (depends on T2.1.2b)
- [ ] T2.1.3 [backend]: Teacher doubt schemas (depends on T2.1.2b, T2.1.2c)

### G2.2 — Teacher doubt inbox (T06) + reply (T07) UI
- [ ] T2.2.1 [frontend]: Teacher doubt API client + types (depends on T2.1.3)
- [ ] T2.2.2 [frontend]: T06 teacher doubt inbox page (depends on T2.2.1)
- [ ] T2.2.3 [frontend]: T07 teacher thread + reply page (depends on T2.2.2)
- [ ] T2.2.4 [frontend]: Teacher "Doubt Queue" nav link (depends on T2.2.2)

### G2.3 — Student "Request teacher help" activation
- [ ] T2.3.1 [frontend]: Escalate CTA in S09 + hAITU panel (depends on T2.2.3, T2.1.2a, T1.3.5)
- [ ] **G2: Teacher escalation** — integration test

## G3 — Notifications subsystem [specs][backend][frontend][deploy]

### G3.1 — Notification schema + service
- [ ] T3.1.1 [specs]: Fill 10_notifications.md with the notification contract
- [ ] T3.1.2 [backend]: V36 migration: notifications (depends on T3.1.1, T1.1.2)
- [ ] T3.1.3 [backend]: Notification model + repository (depends on T3.1.2)
- [ ] T3.1.4 [backend]: NotificationService + pluggable parent fan-out stub (depends on T3.1.3)

### G3.2 — Notification endpoints + APISIX routes
- [ ] T3.2.1 [backend]: 4 notification routes + schemas (depends on T3.1.4)
- [ ] T3.2.2 [deploy]: APISIX route for /api/notifications/* (doubt paths already covered) (depends on T3.2.1)

### G3.3 — Notification bell + feed UI
- [ ] T3.3.1 [frontend]: Notification types + API + useNotifications (60s poll) (depends on T3.2.1)
- [ ] T3.3.2 [frontend]: NotificationBell + feed page (depends on T3.3.1)
- [ ] T3.3.3 [frontend]: Wire bell into shared topbar (all roles) (depends on T3.3.2)

### G3.4 — Auto-close cron + wire doubt events
- [ ] T3.4.1 [backend]: Auto-close cron loop in worker (depends on T3.1.4, T1.1.2, T1.1.5)
- [ ] T3.4.2 [backend]: Wire new_doubt_escalated into escalate endpoint (depends on T2.1.2a, T3.1.4)
- [ ] T3.4.3 [backend]: Wire doubt_teacher_replied into teacher reply (depends on T2.1.2c, T3.1.4)
- [ ] T3.4.4 [backend]: Wire doubt_auto_closed parent fan-out stub (depends on T3.4.1, T3.1.4)
- [ ] **G3: Notifications subsystem** — integration test

## G4 — Mastery + post-exam review [specs][backend][frontend]

### G4.1 — Exam→topic linkage + enrollment_topics schema
- [ ] T4.1.1 [specs]: 01/03/11 — enrollment_topics + exam→topic decision + S05 + exam-review
- [ ] T4.1.2 [backend]: V37 migration: enrollment_topics (+ questions.topic_id only if absent) (depends on T4.1.1, T3.1.2)
- [ ] T4.1.3a [backend]: EnrollmentTopic model + repository (depends on T4.1.2)
- [ ] T4.1.3b [backend]: Map questions.topic_id in the Question model (depends on T4.1.2)

### G4.2 — Mastery recalc service
- [ ] T4.2.1a [backend]: MasteryService + per-topic recalc algorithm (depends on T4.1.3a, T4.1.3b)
- [ ] T4.2.1b [backend]: Wire MasteryService into submit_exam (depends on T4.2.1a)
- [ ] T4.2.1c [backend]: Wire MasteryService into essay-grading auto-complete (depends on T4.2.1a)
- [ ] T4.2.2 [backend]: topic_marked_weak + student_at_risk notifications (depends on T4.2.1a, T3.1.4)

### G4.3 — Post-exam hAITU review (S05)
- [ ] T4.3.1a [backend]: POST /api/haitu/exam-review-chat (depends on T4.1.3b)
- [ ] T4.3.1b [backend]: POST /api/haitu/pattern-analysis (in-memory cache) (depends on T4.1.3b)
- [ ] T4.3.2 [frontend]: S05 exam review screen + hAITU review chat (depends on T4.3.1a, T4.3.1b)

### G4.4 — Weak-topic flags + dashboard
- [ ] T4.4.1 [backend]: Student home API exposes weak-topic flags (depends on T4.1.3a)
- [ ] T4.4.2 [frontend]: Weak-topic flags on student dashboard (depends on T4.4.1)
- [ ] **G4: Mastery + post-exam review** — integration test

## Ready now
Tasks with no pending dependencies — can be started immediately (the G0 merges can proceed in parallel):
- T0.5 [backend]: Re-run Phase 3 integration suites at HEAD (depends on T0.2 — done)
- T0.6 [frontend]: Re-run Playwright E2E at HEAD (dep T0.3 done)
- T0.8 [specs]: Correct stale CLAUDE.md Keycloak-roles claim (no deps)
- T0.9 [backend]: Stub _stage3_rerank to a no-op (depends on T0.2 — done)
- T1.1.1 [specs]: Doubt lifecycle + persistence contracts in 11/03 (no deps)
- T3.1.1 [specs]: Fill 10_notifications.md with the notification contract (no deps)
- T4.1.1 [specs]: 01/03/11 — enrollment_topics + exam→topic decision + S05 + exam-review (no deps)