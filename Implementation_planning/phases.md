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

## Phase 4 — Doubt Persistence + Teacher Escalation + Notifications + Mastery / Post-Exam Review ✓ (completed 2026-07-02)

> Root goal: a student's hAITU doubt becomes a persistent thread a teacher can escalate into and reply to, with notifications; the student gains per-topic mastery tracking and a post-exam hAITU review. Two major features, deliberately sequenced (Feature 1 → Feature 2) with a P0 stabilization goal first.

| Sub-goal | Concern | Repos |
|---|---|---|
| **G0** ✓ — Stabilize HEAD (P0 blocker) | Fix 5 Python-2 `except`-clause SyntaxErrors, merge `feature/rag`→`main` across repos, re-verify Phase 3 at HEAD + CI grep guard + correct stale CLAUDE.md Keycloak claim, and remove inline-ML deps (stub the dormant reranker; drop `sentence-transformers`/`torch`/uv torch-CPU pin; future reranker = external HTTP API) | backend, frontend, deploy, specs |
| **G1** ✓ — Doubt persistence + hAITU thread completion | V35 (`doubts` + `doubt_messages`); Doubt/DoubtMessage domain models, repos, schemas, service; student S08 inbox + S09 thread UI; hAITU persists the doubt + student message pre-stream and the AI message post-stream with a `doubt_id` SSE frame; no-orphan-on-429 + no-duplicate-on-retry + disconnect/partial-text persistence tests | specs, backend, frontend |
| **G2** ✓ (+ G2-patch) — Teacher escalation | Escalate endpoint mounting at `/api/doubts`; teacher queue `GET`+claim and reply routes mounting under `/api/teachers` (`require_instructor`); shared-instructor-queue model; T06 teacher inbox + T07 reply UI; student "Request teacher help" CTA wired into S09 + the hAITU panel; G2-patch fixed re-escalation after a teacher answer (`answered` now treated as closed in `find_or_create_doubt`) | specs, backend, frontend |
| **G3** ✓ — Notifications subsystem | V36 `notifications`; NotificationService with a pluggable parent fan-out stub; 4 endpoints (list/unread-count/mark-read/mark-all-read) + APISIX route; bell + feed UI polled every 60s in the shared topbar (all roles); hourly auto-close cron in the worker (7-day) wired to `new_doubt_escalated` / `doubt_teacher_replied` / `doubt_auto_closed` events | specs, backend, frontend, deploy |
| **G4** ✓ (+ G4-patch/-2/-3/-4) — Mastery + post-exam review | V37 **adds** `questions.topic_id` (NULLABLE) + `enrollment_topics` (FK to `student_enrollments(id)`) + `student_risk_state`; EnrollmentTopic model/repo + Question.topic_id mapping wired all the way through the admin exam builder (T4.1.4, the last gap — re-opened 2026-07-01, closed 2026-07-02); MasteryService per-topic recalc (BR-PROGRESS-001/002/003) wired into `submit_exam` completed branch, essay auto-complete, AND manual release/finalize/override path; persistence-based `student_at_risk` recovery gate + `topic_marked_weak`; post-exam hAITU review via a new public no-RAG `HaituService` method (`POST /api/haitu/exam-review-chat`, `POST /api/haitu/pattern-analysis`, both SSE-streamed after G4-patch/-2) + S05 review screen consuming `GET /api/exam-sessions/session/{id}/answers`; weak-topic "Focus areas" strip on the student dashboard | specs, backend, frontend, deploy |

DAG: G0 → G1 → G2 → G3 → G4 (acyclic). Dependencies flow `specs` contracts ahead of `backend` migrations ahead of `frontend` UI; G3 notifications are consumed by G2 (escalate events) and G4 (mastery events).

Sign-off 2026-07-02: all sub-goals ✓, `g4_test_plan.md` T1–T10 fully verified live against the
real admin-built UI (post-T4.1.4). Archived: `archive/PLAN_Phase4-Mastery-PostExam_2026-06-24.md`,
`archive/TASKS_Phase4-Mastery-PostExam_2026-06-24.md`. Walkthrough record:
`Implementation_planning/g4_test_plan.md`. Final baseline SHAs: backend `0cb36bd`, frontend
`df7067e`, deploy `98912f8`.

**Carried into Phase 5:** Parent curriculum builder (adopt board subtree, create own
nodes/topics, upload notes), parent link-code generation/redemption, remaining role-migration
work (`vision/requirements/11_role_migration.md`: `become-tutor`/`invite-role` flows, frontend
role-switcher metadata, `/institution` + `/parent` route guards).

---

## Pre-Phase 5 — Phase 4 Release-Hardening Pass ✓ (completed 2026-07-06)

> Root goal: make the through-Phase-4 build release-ready for user testing by fixing 14 issues
> found in manual testing (plus one latent bug, issue 15, found during plan review — see below).
> Full goal tree: `PLAN_PrePhase5-Hardening_2026-07-02.md` /
> `TASKS_PrePhase5-Hardening_2026-07-02.md`. **Specs-repo plan** — code tasks are tickets for the
> sibling repos; the `[specs]` tasks (T6.3, T7.4, T8.2, T8.3, T8.4) are written as part of the plan.

| Goal | Issues | Repos | Disposition |
|---|---|---|---|
| **G1** — Exam review navigation wired | 1, 8, 15 | frontend | Fix — wire `/exam/[id]/review` from post-submit, AttemptsModal, Results button; fix pending-grading mislabeled as "Skipped" (T1.4, gap found in review) |
| **G2** — Exam builder bulk-topic + sample JSON | 2, 4 | frontend, deploy | Fix — "Apply topic to all" control; `qa-sample.json` carries `topic_id` |
| **G3** — Topic-filtered exam taking | 5 | backend, frontend | Fix — optional `topic_id` filter on `GET /api/exams/course/{node_id}`; "Take Exam" passes it |
| **G4** — Deep-link + tree interaction | 6, 7 | frontend | Fix — `/courses?topic=` consumed (expand ancestors + select); NodeTreeSidebar chevron separated from label select+expand |
| **G5** — Catalog grade label | 10 | frontend | Fix — "Grade N" display on grade root nodes |
| **G6** — Student grade/profile + onboarding | 13, 14 | frontend, backend, specs | Fix — grade picker in student onboarding View B → `POST /api/students/me/profile`; 09_onboarding amended; Phase 5 `/profile` makes it editable |
| **G7** — Inbox UX targeted polish | 12 | frontend, specs | Fix — bell dropdown, status filters, last-message previews; 10_notifications + 03_student + 04_teacher_tutor specced |
| **G8** — At-risk notif interim + deferred docs | 3, 9, 11 | backend, specs | Interim + spec — `action_url=NULL`; teacher at-risk view (BL-002, Phase 6); NULL-topic mastery limit documented; LaTeX rendering requirement (BL-003, follow-up) |

**Gate:** pre-Phase-5 must close before Phase 5 starts. Phase 5's `/profile` page (T1.5) extends
the grade field G6/T6.1 introduces; the parent onboarding dead-link (T2.6) is untouched here.
**No Alembic migrations** — all fixes ride on existing schema (V37 `questions.topic_id`,
`student_profiles.grade`, `notifications.action_url`). **No deploy gateway work** except the
`qa-sample.json` content edit. Baseline: backend `0cb36bd`, frontend `df7067e`, deploy `98912f8`.

**Deferred (not in pre-Phase-5):**
- **Issue 3 (subject-level mastery)** — accepted v1 limitation; `topic_id=NULL` questions are
  silently skipped by `MasteryService`. Documented in `03_student.md`; subject-level rollup
  deferred.
- **Issue 9 (teacher at-risk view)** — `action_url=NULL` interim; the
  `/teacher/students/{sub}` view is Phase 6 (backlog BL-002).
- **Issue 11 (LaTeX rendering)** — requirement + approach specced in
  `12_content_extraction.md` §11; ships as a focused follow-up (backlog BL-003, Status: Ready).

**Gap found during plan review (2026-07-02), documented not fixed:** skipping the G6/T6.1 grade
step at onboarding leaves a student with **no UI path** to set `student_profiles.grade` until
Phase 5 ships `/profile` (T1.5) — onboarding doesn't re-run once complete, and no other screen in
the through-Phase-4 build writes to that field. Documented as an accepted interim limitation in
`09_onboarding.md` (testers should not skip if they want `recommended` to activate pre-Phase-5).

**Manually verified 2026-07-06:** all 15 issues (14 reported + T1.4) retested end-to-end against
the fixes above and confirmed working. Issues 3 and 11 confirmed correctly deferred (spec-only,
not implemented) per the scope decisions. Phase 5 is cleared to start.

---

## Phase 5 — Parent Curriculum Builder + Link Codes, RAG-Connected (planned 2026-07-02)

> Root goal: a parent links to their child, builds/adopts a private curriculum, uploads content
> that flows through extraction + RAG embedding, and the linked child studies it in Home Study
> and asks hAITU questions grounded in the parent's notes. Full goal tree: `PLAN.md` / `TASKS.md`.

| Sub-goal | Concern | Repos |
|---|---|---|
| **G1** — Parent–child linking lifecycle | Student link-code generation/rotation + link management endpoints and new `/profile` page; parent children list + revoke; max-10 cap | backend, frontend, specs |
| **G2** — Parent workspace shell | Guarded `/parent` app area (route guard, layout, P-home dashboard, P-link page, dead-CTA fix) | frontend, specs |
| **G3** — Parent curriculum builder | V38 adopt-lineage migration; owner-scoped node/topic CRUD + hierarchy rules; idempotent adopt/clone (409); parent instant content + owner-scoped PATCH/DELETE; builder UI reusing parameterized admin content components | backend, frontend, specs |
| **G4** — RAG ingestion + re-ingestion lifecycle | Outbox enqueue on create, upsert-with-reset on update, chunk+outbox cleanup on delete (incl. cascade), worker delete-stale-before-insert; "No notes yet" UI states | backend, frontend, specs |
| **G5** — hAITU on parent-owned topics | Optional `enrollment_id`; parent-link authorization gate in `HaituDoubtService`; severance + cross-family 403 tests; Home Study hAITU panel | backend, frontend, specs |
| **G6** — Student Home Study surface | Live-only + revocation enforcement tests on all student read paths; source-aware empty states; content-viewing verification | backend, frontend |
| **G7** — Phase acceptance | CI-safe E2E journey + Ollama-gated grounded variant; frontend suites + manual walkthrough record | backend, frontend |

DAG spine: G1 → G2 → G3 → G4 → G5 → G6 → G7; G5/G6 backend tests are fixture-driven and can run
in parallel with G1–G3. No deploy-repo work (existing APISIX wildcard routes cover all new
endpoints). Baseline: backend `9532392`, frontend `df7067e`, deploy `98912f8`.

**Deferred to Phase 6 (candidates):** remaining role migration (`become-tutor`/`invite-role`,
role-switcher metadata, `/institution` route guards); RAG ops backlog (external HTTP reranker for
the stubbed Stage 3, bundled inference service in deploy, hAITU Prometheus monitoring — still
blocked on Chainguard licensing); per-child audience scoping of parent content; parent-facing
hAITU endpoints (vision §3.5–3.7).
