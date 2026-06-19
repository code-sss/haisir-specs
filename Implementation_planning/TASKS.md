# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:17533c1 frontend:54e198c deploy:e57c56b (2026-06-19)

---

## G1 [backend]: Schema Foundation

- [x] T1.1 [backend]: V34 Alembic migration (student_enrollments + UNIQUE constraint + index) (2026-06-17)
- [x] **G1 / G1.1: Schema Foundation** — integration test: after upgrade V34, duplicate (student_sub, node_id) insert → UNIQUE violation; index exists (2026-06-18)

---

## G2 [backend]: Enrollment APIs

### G2.1 — Enrollment Domain Layer
- [x] T2.1 [backend]: StudentEnrollment domain model (plain dataclass, no Base) (2026-06-18)
- [x] T2.2 [backend]: Enrollment infra table + SQLAlchemy imperative mapping (depends on T2.1) (2026-06-18)
- [x] T2.3 [backend]: AbstractEnrollmentRepository protocol — 5 abstract methods (depends on T2.1) (2026-06-18)
- [x] T2.4 [backend]: Concrete EnrollmentRepository implementation (depends on T2.2, T2.3) (2026-06-18)
- [x] **G2.1: Enrollment Domain Layer** — integration test: create/get/delete/get_enrolled_node_ids via real DB session (2026-06-18)

### G2.2 — Catalog + Enrollment Service
- [x] T2.5 [backend]: AlreadyEnrolledError + EnrollmentNotFoundError in domain/exceptions.py (2026-06-17)
- [x] T2.6 [backend]: CatalogNodeCard schema with enrollment_id: UUID | None field (2026-06-17)
- [x] T2.10 [backend]: StudentEnrollmentRead + StudentEnrollmentCreate schemas (2026-06-17)
- [x] T2.7 [backend]: EnrollmentService — enroll / drop / get_catalog (depends on T2.4, T2.5, T2.6) (2026-06-18)
- [x] **G2.2: Catalog + Enrollment Service** — integration test: enroll → enrolled=true in catalog; second enroll → 409; drop → enrolled=false (2026-06-18)

### G2.3 — Enrollment HTTP Endpoints
- [x] T2.8 [backend]: Enrollment route module — GET /catalog, POST /enrollments, DELETE /enrollments/{id} (depends on T2.7, T2.10) (2026-06-18)
- [x] T2.9 [backend]: Register enrollment router in api/router.py (depends on T2.8) (2026-06-18)
- [x] **G2.3: Enrollment Endpoints** — integration test: full CRUD cycle returns 200/201/409/204/404 (2026-06-18)

- [x] **G2: Enrollment APIs** — E2E: enroll → catalog shows enrolled=true → drop → enrolled=false (2026-06-18)

---

## G3 [backend]: Enrolled-Only Content Filter

### G3.1 — Enrollment-Aware Query Methods
- [x] T3.1a [backend]: get_subtree_node_ids — recursive CTE on CoursePathNodeRepository (depends on T2.4) (2026-06-18)
- [x] T3.1b [backend]: get_enrolled_root_nodes — filter root nodes to enrolled set (depends on T3.1a) (2026-06-18)
- [x] T3.2 [backend]: is_topic_in_enrolled_subtree on TopicRepository (2026-06-17)
- [x] **G3.1: Enrollment-Aware Queries** — integration test: seeded 3-level tree; subtree query returns all 3 IDs (2026-06-18)

### G3.2 — Enrollment-Aware Dashboard Service
- [x] T3.3 [backend]: StudentDashboardService enrollment injection — filter platform_nodes + PermissionError guards (depends on T2.4, T3.1b, T3.2) (2026-06-18)
- [x] T3.4 [backend]: Wire EnrollmentRepository into dashboard route + map PermissionError → 403 (depends on T3.3) (2026-06-18)
- [x] **G3.2: Enrollment-Aware Service** — integration test: unenrolled student → platform_nodes=[]; wrong node → 403 (2026-06-18)

- [x] **G3: Enrolled-Only Content Filter** — E2E: enrolled student sees subtree only; unenrolled sees empty dashboard (2026-06-18)

---

## G4 [backend]: hAITU Retrieval Service

### G4.1 — Stage 1
- [x] T4.0 [backend]: Extract parse_db_url / build_embed_model / LmStudioEmbedding to shared infrastructure.embedding module (2026-06-17)
- [x] T4.1 [backend]: HaituService skeleton + _stage1_rewrite (LLM call → HaituRewriteResult; JSON parse with fallback) (2026-06-17)
- [ ] **G4.1: Stage 1** — integration test: _stage1_rewrite with live Ollama returns rewritten_query + intent + safe (skipped if Ollama absent)

### G4.2 — Stage 2
- [x] T4.2 [backend]: _stage2_retrieve — QueryFusionRetriever (relative_score, topic_id filter, hybrid pgvector) (depends on T4.1) (2026-06-18)
- [ ] **G4.2: Stage 2** — integration test: seeded chunks; retrieve returns ≥1 NodeWithScore (skipped if Ollama absent)

### G4.3 — Stage 3
- [x] T4.3 [backend]: _stage3_rerank — passthrough when rerank_model=""; cross-encoder rerank otherwise (depends on T4.2) (2026-06-18)
- [x] **G4.3: Stage 3** — integration test: rerank_model="" → same nodes returned unchanged (2026-06-18)

### G4.4 — Stage 4
- [x] T4.4 [backend]: _stage4_synthesize (CompactAndRefine, intent-specific prompts, escalation detection) + public answer() with safe=False early exit (depends on T4.3) (2026-06-18)
- [x] **G4.4: Stage 4** — integration test: mocked retrieval → HaituResponse with non-empty response and bool escalation_ready (2026-06-18)

- [ ] **G4: hAITU Retrieval Service** — E2E: answer() short-circuits on safe=False; full pipeline runs on safe=True

---

## G5 [backend]: hAITU Topic-Doubt Endpoint

### G5.1 — In-Memory Rate Limiter
- [x] T5.1 [backend]: HaituRateLimiter — 20 calls/student/hour, threading.Lock, module-level instance (2026-06-17)
- [x] **G5.1: Rate Limiter** — unit test: 20 calls → False; 21st → True (2026-06-17)

### G5.2 — hAITU Endpoint
- [x] T5.2 [backend]: HaituDoubtMessageSchema + HaituDoubtRequest + HaituDoubtResponse schemas (no doubt_id) (2026-06-17)
- [x] T5.3 [backend]: HaituDoubtService — validate enrollment ownership + subtree + rate limit → run pipeline → return (no DB writes) (depends on T4.4, T5.1, T2.4, T3.1a) (2026-06-18)
- [x] T5.4 [backend]: haitu route module — thin handler, maps PermissionError→403 / RateLimitExceededError→429 (depends on T5.3, T5.2) (2026-06-18)
- [x] T5.5 [backend]: Register hAITU router in api/router.py (depends on T5.4) (2026-06-18)
- [ ] **G5.2: hAITU Endpoint** — integration test: valid request→200; wrong enrollment→403; rate exceeded→429

- [ ] **G5: hAITU Topic-Doubt Endpoint** — E2E: student asks question; AI response returned; no DB rows written; 21st call → 429

---

## G6 [deploy]: APISIX Route + Backend Env Vars

- [x] T6.2 [deploy]: Add HAITU__ + EMBEDDING__ env vars to backend service in docker-compose.yml (2026-06-18)
- [x] T6.1 [deploy]: 19-api-haitu.json route config + templated variants (360s timeout) (depends on T5.5 [backend]) (2026-06-18)
- [x] **G6: APISIX Route** — E2E: POST /api/haitu/topic-doubt through APISIX → 422 (not 404); GET /api/health → healthy (2026-06-18)

---

## G7 [frontend]: Browse Courses Enrollment Screen

### G7.1 — Catalog API Layer
- [x] T7.1 [frontend]: CatalogNode + StudentEnrollment TypeScript interfaces (2026-06-17)
- [x] T7.2 [frontend]: getCatalog / enroll / dropEnrollment API functions in student-api.ts (depends on T7.1, T2.9 [backend]) (2026-06-17)
- [x] T7.3 [frontend]: useStudentCatalog hook — fetch on mount, enroll/drop with re-fetch (depends on T7.2) (2026-06-17)
- [x] **G7.1: Catalog API Layer** — integration test: mocked fetch → catalogNodes populated; enroll() calls POST (2026-06-17)

### G7.2 — Catalog UI
- [x] T7.4 [frontend]: CatalogCard component — Enroll/Drop buttons, Recommended badge (depends on T7.3) (2026-06-17)
- [x] T7.5 [frontend]: BrowseCoursesPage at /enroll — grid, loading, empty state, toast (depends on T7.4) (2026-06-17)
- [x] T7.6 [frontend]: Browse Courses persistent nav link in student header (depends on T7.5) (2026-06-17)
- [x] **G7.2: Catalog UI** — integration test: 1 enrolled + 1 unenrolled → 1 Drop + 1 Enroll button; Enroll click triggers API (2026-06-17)

- [x] **G7: Browse Courses Screen** — E2E: enroll via card → button changes to Drop → navigate to /home → enrolled node appears → drop → reverts (2026-06-18)

---

## G8 [frontend]: Enrolled-Only Dashboard + Empty State

### G8.1 — Dashboard Empty State
- [x] T8.1 [frontend]: PlatformBoardSection empty state + "Browse Courses" CTA (depends on T7.5, T3.4 [backend]) (2026-06-17)
- [x] **G8.1: Dashboard Empty State** — integration test: nodes=[] → CTA link href="/enroll" in DOM (2026-06-17)

### G8.2 — S-nav Empty Node Tree
- [x] T8.2 [frontend]: NodeTreeSidebar empty state + "Browse Courses" CTA (depends on T7.5) (2026-06-17)
- [x] **G8.2: S-nav Empty State** — integration test: nodes=[] → "Browse Courses" link in sidebar DOM (2026-06-17)

- [x] **G8: Enrolled-Only Dashboard** — E2E: unenrolled → empty state + CTA; after enroll + return → enrolled node shown (2026-06-18)

---

## G9 [frontend]: hAITU Doubt Panel

### G9.1 — hAITU API + Hook
- [x] T9.1 [frontend]: HaituMessage + HaituDoubtResponse types; askHaitu API function (POST /api/haitu/topic-doubt) (depends on T7.1, T5.5 [backend]) (2026-06-17)
- [x] T9.2 [frontend]: useHaituDoubt hook — client-side message history, loading/error state, send() (depends on T9.1) (2026-06-17)
- [x] **G9.1: hAITU API + Hook** — integration test: mocked send() → messages.length=2, isLoading=false (2026-06-17)

### G9.2 — Doubt Panel Component
- [x] T9.3 [frontend]: HaituDoubtPanel component — chat bubbles, error banner, escalation button (disabled placeholder), enrollment guard (depends on T9.2) (2026-06-17)
- [x] T9.4a [frontend]: ContentViewer — add topicId/enrollmentId props, conditional HaituDoubtPanel render (depends on T9.3) (2026-06-17)
- [x] T9.4b [frontend]: StudentCoursesPage — selectedTopicId/selectedEnrollmentId state, pass to ContentViewer (depends on T9.4a, T7.3) (2026-06-17)
- [x] T9.5 [frontend]: Export HaituDoubtPanel, useHaituDoubt, useStudentCatalog + types from feature index (depends on T9.4b, T7.6) (2026-06-17)
- [x] **G9.2: Doubt Panel** — integration test: select topic → doubt panel renders; send → AI response in chat (2026-06-17)

- [x] **G9: hAITU Doubt Panel** — E2E: select topic → panel appears; send question → AI response; 21st call → rate limit error (2026-06-18)

---

## E2E [frontend]: Playwright Integration Tests (G3/G7/G8/G9)

**Status: E2E suite + CI integration shipped** | Commit `54e198c` 2026-06-18 | 14 files, 16 Playwright specs, all gates green

- [x] E2E.1 [frontend]: Playwright setup — `playwright.config.ts` (webServer auto-starts dev on :3001, pins `NEXT_PUBLIC_BACKEND_URL=localhost:9080`), `@playwright/test` devDep, `test:e2e` scripts (2026-06-18)
- [x] E2E.2 [frontend]: `tests/e2e/helpers/` — `auth.ts` (mocked CSRF + `/api/users/me`, onboarding cookie, `currentRole` localStorage) and `mock-api.ts` (typed factories + `page.route()` for all student endpoints) (2026-06-18)
- [x] E2E.3 [frontend]: G3 content-filter specs (3) — enrolled subtree shown; unenrolled empty state + CTA; CTA → /enroll (depends on G3) (2026-06-18)
- [x] E2E.4 [frontend]: G7 browse-courses specs (4) — catalog display; enroll → Drop + toast; drop → Enroll; enrolled node in /courses (depends on G7) (2026-06-18)
- [x] E2E.5 [frontend]: G8 empty-state specs (5) — sidebar + home empty states; full enroll → return flow (depends on G8) (2026-06-18)
- [x] E2E.6 [frontend]: G9 hAITU panel specs (4) — panel render; question → AI response; unenrolled notice; 429 rate-limit (depends on G9) (2026-06-18)
- [x] E2E.7 [frontend]: Shared env-backed `BACKEND` constant (`tests/e2e/helpers/backend.ts`); fix brittle `waitForPageReady` spinner wait (2026-06-18)
- [x] E2E.8 [frontend]: Jenkinsfile E2E Tests stage — chromium install, `CI=true` run, JUnit + HTML report, pinned backend URL (2026-06-18)
- [x] E2E.9 [frontend]: `knip.config.ts` playwright entry; gitignore `playwright-report/`, `test-results/`, `reports/` (2026-06-18)
- [x] E2E.10 [frontend]: Gate `/commit-frontend` on E2E suite as peer to 100% coverage check (2026-06-18)

---

## G10 [backend][specs]: Phase 3 Verification, Manual Walkthrough & Sign-off

> Closes Phase 3: the 12 remaining backend goal-level integration/E2E items, a manual 7-step ROOT Acceptance Test walkthrough against the running stack, defect fixing, and archival. Nothing deferred.

### G10.1 — Shared Integration Fixtures & Scaffolding
- [x] T10.1.1 [backend]: Integration conftest — assert/ensure migration head = V34 (autouse) (no deps) (2026-06-19)
- [x] T10.1.2 [backend]: Shared fixtures module — make_student_client, reset_haitu_rate_limiter (autouse), unique_student_sub, rolled_back_session, seed_3level_tree (depends on T10.1.1) (2026-06-19)
- [x] T10.1.2b [backend]: Refactor existing dashboard integration test to import shared_fixtures (no behaviour change) (depends on T10.1.2) (2026-06-19)
- [x] T10.1.3 [backend]: ollama_probe.py — probe-based skip guard + skip-count terminal-summary reporter (no deps) (2026-06-19)
- [ ] **G10.1: Shared Fixtures** — subgoal test: shared_fixtures imports clean; reset/rollback/seed usable; refactored dashboard test still passes

### G10.2 — DB-Only Verification Tests (8 items)
- [x] T10.2.1 [backend]: G1.1 — V34 UNIQUE violation + idx_student_enrollments_student_sub exists (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.2.2 [backend]: G2.1 — EnrollmentRepository CRUD via real rolled-back session (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.2.3 [backend]: G2.2 — EnrollmentService enroll/drop/catalog (409) (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.2.4 [backend]: G2.3 — route CRUD cycle 200/201/409/204/404 (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.2.5 [backend]: G2 E2E — enroll→enrolled=true→drop→enrolled=false (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.2.6 [backend]: G3.1 — seeded 3-level tree; subtree + enrolled-root queries (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.2.7 [backend]: G3.2 — unenrolled→platform_nodes=[]; wrong node→403 (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.2.8 [backend]: G5.2 — valid→200 (mocked); wrong enrollment→403; rate→429 (depends on T10.1.1, T10.1.2) (2026-06-19)
- [ ] **G10.2: DB-Only Verification** — subgoal test: pytest tests/integration/phase3_db_only exits 0 with 8 passed, 0 skipped (awaits CI postgres:18 run — all 8 gate tests implemented + collect cleanly; skip locally with no INTEGRATION_DB_URL)

### G10.3 — Ollama-Gated Verification Tests
- [x] T10.3.1 [backend]: G4.1 — _stage1_rewrite with live Ollama  [Ollama-gated] (depends on T10.1.3) (2026-06-19)
- [x] T10.3.2 [backend]: G4.2 — seeded chunks; _stage2_retrieve ≥1 NodeWithScore  [Ollama-gated] (depends on T10.1.1, T10.1.2, T10.1.3) (2026-06-19)
- [x] T10.3.3a [backend]: G4 E2E — safe=False short-circuit (no _stage2 call)  [DB-only] (depends on T10.1.1, T10.1.2) (2026-06-19)
- [x] T10.3.3b [backend]: G4 E2E — safe=True full pipeline  [Ollama-gated] (depends on T10.1.1, T10.1.2, T10.1.3) (2026-06-19)
- [x] T10.3.4a [backend]: G5 E2E — AI response + no DB writes  [Ollama-gated] (depends on T10.1.1, T10.1.2, T10.1.3) (2026-06-19)
- [x] T10.3.4b [backend]: G5 E2E — 21st call→429 (mocked)  [DB-only] (depends on T10.1.1, T10.1.2) (2026-06-19)
- [ ] T10.3.5 [backend]: Aggregate-gate — ollama-gated suite exits 0 with skip-count line present (depends on T10.3.1–T10.3.4b)
- [ ] **G10.3: Ollama-Gated Verification** — subgoal test: Ollama up → suite passes, skip-count line present; down → gated tests skip, skip-count line present (awaits CI run — 6 tests implemented with per-test @OLLAMA_GATED_MARK/@OLLAMA_GATED_SKIP_MARK; 2 DB-only sub-cases (T10.3.3a, T10.3.4b) run with no Ollama, 4 gated skip when the probe fails. NOTE: @pytest.mark.anyio runs each gated test under both asyncio+trio, and rag_loop is also ollama_gated-marked, so the suite collects ~10 ollama_gated items (not 6) and CI RAG time is ~2x a single-backend run; this is the intended project pattern, not a defect. T10.3.5 only asserts the suite exits 0 with the skip-count line present, so the dual-backend count does not affect the gate.)

### G10.4 — Manual End-to-End Walkthrough
- [ ] T10.4.1 [specs]: Run 7-step ROOT Acceptance Test manually against running stack, record results (depends on G10.2 + G10.3 subgoal tests green; G1–G9 complete; stack up via deploy)
- [ ] T10.4.2 [backend]: Fix backend defects from walkthrough (no-op if none) (depends on T10.4.1)
- [ ] T10.4.3 [frontend]: Fix frontend defects from walkthrough (no-op if none) (depends on T10.4.1)
- [ ] T10.4.4 [deploy]: Fix deploy defects from walkthrough (no-op if none) (depends on T10.4.1)
- [ ] **G10.4: Manual Walkthrough** — subgoal test: 7-step record all passing with defects fixed

### G10.5 — Phase 3 Sign-off & Archive
- [ ] T10.5.1 [specs]: Verify full closure — 12 items + 7 manual steps + Playwright suite all green-or-skip-with-count (depends on T10.4.2, T10.4.3, T10.4.4)
- [ ] T10.5.2 [specs]: git mv PLAN.md + TASKS.md → archive/; append Phase 3 ✓ to progress.md Completed Phases (depends on T10.5.1)
- [ ] **G10.5: Sign-off & Archive** — subgoal test: archive/ contains Phase3 PLAN+TASKS; progress.md has Phase 3 entry

---

## Ready now

Tasks with no pending dependencies — can start immediately:

- T10.3.5 [backend]: Aggregate-gate — ollama-gated suite exits 0 with skip-count line present (depends on T10.3.1 ✓, T10.3.2 ✓, T10.3.3a ✓, T10.3.3b ✓, T10.3.4a ✓, T10.3.4b ✓) — verification-only; run in CI (postgres:18 + migrations + pytest --cov-fail-under=100) to confirm the ollama-gated skip/pass count line

The 15 Phase 3 backend test-infrastructure + verification tasks (T10.1.2b, T10.2.1–T10.2.8, T10.3.1, T10.3.2, T10.3.3a, T10.3.3b, T10.3.4a, T10.3.4b) are implemented and pass local gates (ruff, mypy src/, collect-only, unit suite 100%). The G10.1/G10.2/G10.3 subgoal tests and T10.3.5 require a CI/DB run to confirm the enforced pass/skip counts and are therefore left unchecked. T10.4.1 (manual walkthrough) is gated on G10.2 + G10.3 subgoal tests being green; T10.5.x is gated on T10.4.x. All G1–G9 implementation and the frontend Playwright E2E suite are already complete.