# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:2686279 frontend:31062ab deploy:e57c56b (2026-06-17)

---

## G1 [backend]: Schema Foundation

- [ ] T1.1 [backend]: V34 Alembic migration (student_enrollments + UNIQUE constraint + index)
- [ ] **G1 / G1.1: Schema Foundation** — integration test: after upgrade V34, duplicate (student_sub, node_id) insert → UNIQUE violation; index exists

---

## G2 [backend]: Enrollment APIs

### G2.1 — Enrollment Domain Layer
- [ ] T2.1 [backend]: StudentEnrollment domain model (plain dataclass, no Base)
- [ ] T2.2 [backend]: Enrollment infra table + SQLAlchemy imperative mapping (depends on T2.1)
- [ ] T2.3 [backend]: AbstractEnrollmentRepository protocol — 5 abstract methods (depends on T2.1)
- [ ] T2.4 [backend]: Concrete EnrollmentRepository implementation (depends on T2.2, T2.3)
- [ ] **G2.1: Enrollment Domain Layer** — integration test: create/get/delete/get_enrolled_node_ids via real DB session

### G2.2 — Catalog + Enrollment Service
- [ ] T2.5 [backend]: AlreadyEnrolledError + EnrollmentNotFoundError in domain/exceptions.py
- [ ] T2.6 [backend]: CatalogNodeCard schema with enrollment_id: UUID | None field
- [ ] T2.10 [backend]: StudentEnrollmentRead + StudentEnrollmentCreate schemas
- [ ] T2.7 [backend]: EnrollmentService — enroll / drop / get_catalog (depends on T2.4, T2.5, T2.6)
- [ ] **G2.2: Catalog + Enrollment Service** — integration test: enroll → enrolled=true in catalog; second enroll → 409; drop → enrolled=false

### G2.3 — Enrollment HTTP Endpoints
- [ ] T2.8 [backend]: Enrollment route module — GET /catalog, POST /enrollments, DELETE /enrollments/{id} (depends on T2.7, T2.10)
- [ ] T2.9 [backend]: Register enrollment router in api/router.py (depends on T2.8)
- [ ] **G2.3: Enrollment Endpoints** — integration test: full CRUD cycle returns 200/201/409/204/404

- [ ] **G2: Enrollment APIs** — E2E: enroll → catalog shows enrolled=true → drop → enrolled=false

---

## G3 [backend]: Enrolled-Only Content Filter

### G3.1 — Enrollment-Aware Query Methods
- [ ] T3.1a [backend]: get_subtree_node_ids — recursive CTE on CoursePathNodeRepository (depends on T2.4)
- [ ] T3.1b [backend]: get_enrolled_root_nodes — filter root nodes to enrolled set (depends on T3.1a)
- [ ] T3.2 [backend]: is_topic_in_enrolled_subtree on TopicRepository
- [ ] **G3.1: Enrollment-Aware Queries** — integration test: seeded 3-level tree; subtree query returns all 3 IDs

### G3.2 — Enrollment-Aware Dashboard Service
- [ ] T3.3 [backend]: StudentDashboardService enrollment injection — filter platform_nodes + PermissionError guards (depends on T2.4, T3.1b, T3.2)
- [ ] T3.4 [backend]: Wire EnrollmentRepository into dashboard route + map PermissionError → 403 (depends on T3.3)
- [ ] **G3.2: Enrollment-Aware Service** — integration test: unenrolled student → platform_nodes=[]; wrong node → 403

- [ ] **G3: Enrolled-Only Content Filter** — E2E: enrolled student sees subtree only; unenrolled sees empty dashboard

---

## G4 [backend]: hAITU Retrieval Service

### G4.1 — Stage 1
- [ ] T4.1 [backend]: HaituService skeleton + _stage1_rewrite (LLM call → HaituRewriteResult; JSON parse with fallback)
- [ ] **G4.1: Stage 1** — integration test: _stage1_rewrite with live Ollama returns rewritten_query + intent + safe (skipped if Ollama absent)

### G4.2 — Stage 2
- [ ] T4.2 [backend]: _stage2_retrieve — QueryFusionRetriever (relative_score, topic_id filter, hybrid pgvector) (depends on T4.1)
- [ ] **G4.2: Stage 2** — integration test: seeded chunks; retrieve returns ≥1 NodeWithScore (skipped if Ollama absent)

### G4.3 — Stage 3
- [ ] T4.3 [backend]: _stage3_rerank — passthrough when rerank_model=""; cross-encoder rerank otherwise (depends on T4.2)
- [ ] **G4.3: Stage 3** — integration test: rerank_model="" → same nodes returned unchanged

### G4.4 — Stage 4
- [ ] T4.4 [backend]: _stage4_synthesize (CompactAndRefine, intent-specific prompts, escalation detection) + public answer() with safe=False early exit (depends on T4.3)
- [ ] **G4.4: Stage 4** — integration test: mocked retrieval → HaituResponse with non-empty response and bool escalation_ready

- [ ] **G4: hAITU Retrieval Service** — E2E: answer() short-circuits on safe=False; full pipeline runs on safe=True

---

## G5 [backend]: hAITU Topic-Doubt Endpoint

### G5.1 — In-Memory Rate Limiter
- [ ] T5.1 [backend]: HaituRateLimiter — 20 calls/student/hour, threading.Lock, module-level instance
- [ ] **G5.1: Rate Limiter** — unit test: 20 calls → False; 21st → True

### G5.2 — hAITU Endpoint
- [ ] T5.2 [backend]: HaituDoubtMessageSchema + HaituDoubtRequest + HaituDoubtResponse schemas (no doubt_id)
- [ ] T5.3 [backend]: HaituDoubtService — validate enrollment ownership + subtree + rate limit → run pipeline → return (no DB writes) (depends on T4.4, T5.1, T2.4, T3.1a)
- [ ] T5.4 [backend]: haitu route module — thin handler, maps PermissionError→403 / RateLimitExceededError→429 (depends on T5.3, T5.2)
- [ ] T5.5 [backend]: Register hAITU router in api/router.py (depends on T5.4)
- [ ] **G5.2: hAITU Endpoint** — integration test: valid request→200; wrong enrollment→403; rate exceeded→429

- [ ] **G5: hAITU Topic-Doubt Endpoint** — E2E: student asks question; AI response returned; no DB rows written; 21st call → 429

---

## G6 [deploy]: APISIX Route + Backend Env Vars

- [ ] T6.2 [deploy]: Add HAITU__ + EMBEDDING__ env vars to backend service in docker-compose.yml
- [ ] T6.1 [deploy]: 19-api-haitu.json route config + templated variants (360s timeout) (depends on T5.5 [backend])
- [ ] **G6: APISIX Route** — E2E: POST /api/haitu/topic-doubt through APISIX → 422 (not 404); GET /api/health → healthy

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

- [ ] **G7: Browse Courses Screen** — E2E: enroll via card → button changes to Drop → navigate to /home → enrolled node appears → drop → reverts

---

## G8 [frontend]: Enrolled-Only Dashboard + Empty State

### G8.1 — Dashboard Empty State
- [ ] T8.1 [frontend]: PlatformBoardSection empty state + "Browse Courses" CTA (depends on T7.5, T3.4 [backend])
- [ ] **G8.1: Dashboard Empty State** — integration test: nodes=[] → CTA link href="/enroll" in DOM

### G8.2 — S-nav Empty Node Tree
- [ ] T8.2 [frontend]: NodeTreeSidebar empty state + "Browse Courses" CTA (depends on T7.5)
- [ ] **G8.2: S-nav Empty State** — integration test: nodes=[] → "Browse Courses" link in sidebar DOM

- [ ] **G8: Enrolled-Only Dashboard** — E2E: unenrolled → empty state + CTA; after enroll + return → enrolled node shown

---

## G9 [frontend]: hAITU Doubt Panel

### G9.1 — hAITU API + Hook
- [ ] T9.1 [frontend]: HaituMessage + HaituDoubtResponse types; askHaitu API function (POST /api/haitu/topic-doubt) (depends on T7.1, T5.5 [backend])
- [ ] T9.2 [frontend]: useHaituDoubt hook — client-side message history, loading/error state, send() (depends on T9.1)
- [ ] **G9.1: hAITU API + Hook** — integration test: mocked send() → messages.length=2, isLoading=false

### G9.2 — Doubt Panel Component
- [ ] T9.3 [frontend]: HaituDoubtPanel component — chat bubbles, error banner, escalation button (disabled placeholder), enrollment guard (depends on T9.2)
- [ ] T9.4a [frontend]: ContentViewer — add topicId/enrollmentId props, conditional HaituDoubtPanel render (depends on T9.3)
- [ ] T9.4b [frontend]: StudentCoursesPage — selectedTopicId/selectedEnrollmentId state, pass to ContentViewer (depends on T9.4a, T7.3)
- [ ] T9.5 [frontend]: Export HaituDoubtPanel, useHaituDoubt, useStudentCatalog + types from feature index (depends on T9.4b, T7.6)
- [ ] **G9.2: Doubt Panel** — integration test: select topic → doubt panel renders; send → AI response in chat

- [ ] **G9: hAITU Doubt Panel** — E2E: select topic → panel appears; send question → AI response; 21st call → rate limit error

---

## Ready now

Tasks with no pending dependencies — can start immediately across all three repos:

- T1.1 [backend]: V34 Alembic migration
- T2.5 [backend]: AlreadyEnrolledError + EnrollmentNotFoundError
- T2.6 [backend]: CatalogNodeCard schema
- T2.10 [backend]: StudentEnrollmentRead + StudentEnrollmentCreate schemas
- T3.2 [backend]: is_topic_in_enrolled_subtree
- T4.1 [backend]: HaituService skeleton + Stage 1
- T5.1 [backend]: HaituRateLimiter utility
- T5.2 [backend]: HaituDoubt request/response schemas
- T6.2 [deploy]: HAITU + EMBEDDING env vars in backend service
- T8.2 [frontend]: NodeTreeSidebar empty state + "Browse Courses" CTA (depends on T7.5 ✓)
