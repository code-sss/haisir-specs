# hAIsir — Implementation Phase Guide

> Details live in `target/requirements/`. Update this file when phase ordering
> or scope changes significantly.
>
> Long-term vision phasing is in `vision/phases.md`.

---

## Phase 0 — Foundation ✓ (completed 2026-03-26)

Auth, schema, onboarding.

---

## Phase 1 — Board Content Management (Platform Admin)

Split into sub-phases to keep each deployable unit small:

| Sub-phase | Scope | Depends on |
|---|---|---|
| **1a** ✓ — Owner_type visibility enforcement | Backend-only: apply BR-DATA-003 WHERE clause on all student + admin endpoints | — |
| **1b** ✓ — Admin tree UI + node CRUD | `/admin` + `/admin/boards` pages; `PATCH`/`DELETE` course_path_nodes; full-subtree CTE fetch; admin shell layout | 1a |
| **1c-pre** ✓ — X-Current-Role enforcement | Backend: split `current_active_user` into strict (400 if header missing) + lenient (3 exempt onboarding endpoints). Frontend: confirm all calls send header; fix `position`→`order` dev note | 1b |
| **1c** ✓ — Topics panel | Right-panel topic list + CRUD for selected node; `PATCH`/`DELETE` topics; status toggle (draft/live) | 1c-pre |
| **1c-post** ✓ — Admin UX alignment | Fix Add Board modal (missing `path_type`); chip selector for node types (9 enum values); dashboard stats endpoint + rich cards; inline description edit; sibling-type filtering; 3-tier hierarchy enforcement | 1c |
| **1d-stub** ✓ — Topic content URL/video/text CRUD (functionally incomplete) | Manual `topic_contents` rows for video URL and pasted text only. **No PDF/image upload** — the modal’s PDF chip is a stub. | 1c-post |
| **1d-real** — Topic content extraction (PDF/image → text via vision LLM) | Multipart upload → Postgres queue (FOR UPDATE SKIP LOCKED) → worker process → `pypdfium2` (native text) or `glm-ocr` (vision LLM) → N `topic_contents` rows. Inline title rename + Edit modal preserve provenance. See `target/requirements/12_content_extraction.md`. | 1d-stub |

---

## Phase 2 — RAG Infrastructure + Text Restructuring + Student Dashboard ✓ (completed 2026-06-17)

| Sub-phase | Scope | Depends on |
|---|---|---|
| **2a** — pgvector DB image | Wolfi multi-stage Dockerfile; `pgvector/pgvector:pg18` for dev; compose wired | 1d-real |
| **2b** — Vector schema | V31 (`CREATE EXTENSION vector`), V32 (Alembic shim for `data_topic_content_chunks`) | 2a |
| **2c** — RAG drain loop | `EmbeddingSettings`, LlamaIndex deps, `rag_outbox_loop.py` as 4th worker coroutine; outbox drained to pgvector | 2b |
| **2d** — hAITU config stub | `HaituSettings` in `shared/config.py`; HAITU env vars in compose (endpoint deferred to next cycle) | 2c |
| **2e** — Text restructuring | `restructure_page()` in `GlmOcrProvider`; wired in `extract_page()` behind `EXTRACTION__RESTRUCTURE_TEXT` flag | 1d-real |
| **2f** — Student dashboard backend | Four `GET /api/student/` endpoints; `X-Current-Role: student` enforcement; platform + parent-owned node trees | 2a |
| **2g** — Student dashboard frontend | S-home (Platform Board / Home Study sections) + S-nav (tree sidebar + topic list + content viewer) | 2f |

Plan doc: `Implementation_planning/PLAN.md` (written 2026-06-12).
Decisions: `Implementation_planning/decisions.md` (2026-06-12 entries: RAG+hAITU architecture, PDF text restructuring).

---

## Phase 3 — Student Enrollment + hAITU Topic-Doubt ✓ (completed 2026-06-24)

| Sub-phase | Scope | Depends on |
|---|---|---|
| **3a** ✓ — student_enrollments schema | V34 migration; StudentEnrollment domain model + repo | 2e/2f |
| **3b** ✓ — Enrollment APIs | GET /catalog (recommended), POST/DELETE /enrollments; enrolled-only content filter on all 4 student endpoints | 3a |
| **3c** ✓ — hAITU retrieval service | 4-stage pipeline: query rewrite + hybrid pgvector search + optional rerank + CompactAndRefine synthesis | 2c (pgvector + bge-m3 indexing) |
| **3d** ✓ — hAITU endpoint | POST /api/haitu/topic-doubt; HaituDoubtService (stateless); in-memory rate limiter (20/student/hour) | 3b, 3c |
| **3e** ✓ — APISIX route + env vars | 19-api-haitu.json with 360s timeout; HAITU__* + EMBEDDING__* env vars wired in backend service | 3d |
| **3f** ✓ — Enrollment frontend | S-enroll (/enroll) catalog page; enroll/drop CTA; Browse Courses nav link; empty-state handling in S-home + S-nav | 3b |
| **3g** ✓ — hAITU doubt panel | HaituDoubtPanel in ContentViewer; useHaituDoubt hook (client-side history); escalation button (disabled placeholder) | 3d, 3f |
| **3h** ✓ — Verification + manual walkthrough + sign-off (G10) | 12 backend goal-level integration/E2E tests (8 DB-only + 4 Ollama-gated with skip-count reporting); shared integration fixtures (migration-head V34 guard, dep-override wiring, rate-limiter reset, per-test isolation, Ollama probe); manual 7-step ROOT Acceptance Test against the running stack; per-repo defect fixes; archive PLAN.md/TASKS.md + mark Phase 3 ✓. **No deferral.** | 3a–3g |

Implementation for 3a–3g is complete (incl. frontend Playwright E2E suite). 3h sign-off landed 2026-06-24 — Phase 3 ✓. Archived: `archive/PLAN_Phase3-Enrollment-Haitu_2026-06-18.md`. APISIX hAITU timeout corrected 360s → 600s.

**Carried into Phase 4:** doubts + doubt_messages tables (V35), teacher escalation flow, mastery score tracking, parent features.

---

## Phase 4 — Doubt Persistence + Teacher Escalation + Notifications + Mastery / Post-Exam Review (active)

> Root goal: a student's hAITU doubt becomes a persistent thread a teacher can escalate into and reply to, with notifications; the student gains per-topic mastery tracking and a post-exam hAITU review. Two major features, deliberately sequenced (Feature 1 → Feature 2) with a P0 stabilization goal first.

| Sub-goal | Concern | Repos |
|---|---|---|
| **G0** — Stabilize HEAD (P0 blocker) | Fix 5 Python-2 `except`-clause SyntaxErrors, merge `feature/rag`→`main` across repos, re-verify Phase 3 at HEAD + CI grep guard + correct stale CLAUDE.md Keycloak claim, and remove inline-ML deps (stub the dormant reranker; drop `sentence-transformers`/`torch`/uv torch-CPU pin; future reranker = external HTTP API) | backend, frontend, deploy, specs |
| **G1** — Doubt persistence + hAITU thread completion | V35 (`doubts` + `doubt_messages`); Doubt/DoubtMessage domain models, repos, schemas, service; student S08 inbox + S09 thread UI; hAITU persists the doubt + student message pre-stream and the AI message post-stream with a `doubt_id` SSE frame; no-orphan-on-429 + no-duplicate-on-retry + disconnect/partial-text persistence tests | specs, backend, frontend |
| **G2** — Teacher escalation | Escalate endpoint mounting at `/api/doubts`; teacher queue `GET`+claim and reply routes mounting under `/api/teachers` (`require_instructor`); shared-instructor-queue model; T06 teacher inbox + T07 reply UI; student "Request teacher help" CTA wired into S09 + the hAITU panel | specs, backend, frontend |
| **G3** — Notifications subsystem | V36 `notifications`; NotificationService with a pluggable parent fan-out stub; 4 endpoints (list/unread-count/mark-read/mark-all-read) + APISIX route; bell + feed UI polled every 60s in the shared topbar (all roles); hourly auto-close cron in the worker (7-day) wired to `new_doubt_escalated` / `doubt_teacher_replied` / `doubt_auto_closed` events | specs, backend, frontend, deploy |
| **G4** — Mastery + post-exam review | V37 `enrollment_topics` (verifies existing `questions.topic_id`, never alters it); EnrollmentTopic model/repo + Question mapping; MasteryService per-topic recalc wired into `submit_exam` and essay-grading auto-complete; `topic_marked_weak` / `student_at_risk` notifications; post-exam hAITU review (`POST /api/haitu/exam-review-chat`, `POST /api/haitu/pattern-analysis` in-memory cache) + S05 review screen; weak-topic flags exposed on the student home API and dashboard | specs, backend, frontend |

DAG: G0 → G1 → G2 → G3 → G4 (acyclic). Dependencies flow `specs` contracts ahead of `backend` migrations ahead of `frontend` UI; G3 notifications are consumed by G2 (escalate events) and G4 (mastery events).

Plan doc: `Implementation_planning/PLAN.md` (written 2026-06-24). Decisions: `Implementation_planning/decisions.md` (2026-06-24 Phase 4 entry). Progress checkboxes: `Implementation_planning/TASKS.md`. Baseline SHAs: backend `6ec91ab`, frontend `47e4ec2`, deploy `3178451`.
