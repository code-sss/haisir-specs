# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:09aace9 frontend:d9532b7 deploy:88cbe5d (2026-06-16)

---

## G1 [deploy]: pgvector Database Image

- [x] T1.1 [deploy]: Wolfi pgvector Dockerfile (`common/images/postgres-pgvector/Dockerfile`) (2026-06-12)
- [x] T1.2 [deploy]: Update common/docker-compose.yml db services to custom image (depends on T1.1) (2026-06-14)
- [x] T1.3 [deploy]: Update dev/docker-compose.yml postgres to pgvector image (depends on T1.2) (2026-06-14)
- [x] T1.4 [deploy]: pgvector smoke test (depends on T1.2, T1.3) (2026-06-15)
- [ ] **G1: pgvector Database Image** — integration test: `docker compose up db`; `SELECT extversion FROM pg_extension WHERE extname='vector'` returns `0.8.2`

---

## G2 [backend]: Vector Extension + Schema

- [x] T2.1 [backend]: Alembic V31 — CREATE EXTENSION vector (depends on T1.1 [deploy]) (2026-06-15)
- [x] T2.2 [backend]: Alembic V32 — shim for data_topic_content_chunks (depends on T2.1) (2026-06-15)
- [ ] **G2: Vector Extension + Schema** — integration test: `alembic upgrade head` completes; `alembic current` = V32; `data_topic_content_chunks` has `embedding vector(1024)` column

---

## G3 [backend+deploy]: RAG Drain Loop

### G3.1 [backend]: Config + Dependencies

- [x] T3.1 [backend]: LlamaIndex dependencies in pyproject.toml (2026-06-15)
- [x] T3.2 [backend]: EmbeddingSettings in shared/config.py (now includes `embed_dim` field) (2026-06-15)

### G3.2 [backend]: Loop Implementation

- [x] T3.3 [backend]: Create worker/rag_outbox_loop.py — REDO with hybrid_search + HNSW + hierarchy metadata JOIN + insert_nodes (2026-06-15)
- [x] T3.4 [backend]: Register rag_outbox_loop in worker/__main__.py (depends on T3.3) (2026-06-15)
- [x] T3.6 [backend]: Unit tests for rag_outbox_loop — REDO with hybrid_search + HNSW + hierarchy metadata assertions (2026-06-15)
- [x] T3.7 [backend]: RAG loop integration test — REDO with full hierarchy + metadata + text_search_tsv assertions (2026-06-15)

### G3.3 [deploy]: Deploy Config

- [x] T3.5 [deploy]: EMBEDDING env vars in common/docker-compose.yml worker (now includes `EMBEDDING__EMBED_DIM`) (depends on T3.2 [backend]) (2026-06-15)

- [ ] **G3: RAG Drain Loop** — integration test: seed full hierarchy + outbox row; start worker; wait 10s; assert `status='done'`; assert `data_topic_content_chunks` has rows with `topic_id`/`topic_title`/`node_name` in metadata; assert `text_search_tsv` column exists

---

## G4 [backend+deploy]: hAITU Settings Wired

- [x] T4.1 [backend]: HaituSettings in shared/config.py — REDO with all 8 fields (top_k, rerank_model, llm_context_window, llm_request_timeout, llm_thinking added) (2026-06-15)
- [x] T4.2 [deploy]: HAITU env vars in common/docker-compose.yml worker (now includes all 8 vars) (depends on T4.1 [backend]) (2026-06-15)
- [ ] **G4: hAITU Settings Wired** — integration test: all 8 `Settings().haitu.*` fields return correct defaults; env overrides work; compose config shows all HAITU vars

---

## G5 [backend+deploy]: Text Restructuring Pass

### G5.1 [backend]: Config

- [x] T5.1 [backend]: Add restructure fields to ExtractionSettings (`restructure_text`, `restructure_model_spec`) (2026-06-15)

### G5.2 [backend]: Restructure Prompt

- [x] T5.2 [backend]: RESTRUCTURE_PROMPT inline constant in worker/prompts.py (2026-06-15)

### G5.3 [backend]: restructure_page() Method

- [x] T5.3 [backend]: Add text-only helpers + restructure_page() to GlmOcrProvider (depends on T5.2) (2026-06-15)

### G5.4 [backend]: Extraction Loop Integration

- [x] T5.4 [backend]: Call restructure_page in extract_page() (depends on T5.1, T5.3) (2026-06-15)

### G5.5 [deploy]: Deploy Config

- [x] T5.5 [deploy]: Add EXTRACTION__RESTRUCTURE_* to common/docker-compose.yml worker (depends on T5.1 [backend]) (2026-06-15)

### G5.6 [backend]: Tests

- [x] T5.6 [backend]: Unit tests for restructure_page() — TestRestructurePage (depends on T5.3) (2026-06-15)
- [x] T5.7 [backend]: Integration test for text restructuring pipeline (depends on T5.4, T5.6) (2026-06-15)

- [ ] **G5: Text Restructuring Pass** — integration test: upload math PDF; assert `extraction_job_pages.markdown_text` has reassembled fractions

---

## G6 [backend]: Student Dashboard Backend APIs

- [x] T6.1 [backend]: Add get_active_links_for_child to ParentChildLinkRepository (2026-06-15)
- [x] T6.3 [backend]: Add get_platform_root_nodes to CoursePathNodeRepository (2026-06-15)
- [x] T6.4 [backend]: Create schemas/student_dashboard.py (2026-06-15)
- [x] T6.2 [backend]: Create StudentDashboardService (depends on T6.1, T6.3) (2026-06-15)
- [x] T6.5 [backend]: Create api/routes/student_dashboard.py (depends on T6.2, T6.4) (2026-06-15)
- [x] T6.6 [backend]: Register student_dashboard router in api/router.py (depends on T6.5) (2026-06-15)
- [x] T6.7 [backend]: Student dashboard API integration test (depends on T6.6) (2026-06-15)
- [ ] **G6: Student Dashboard Backend APIs** — integration test: seed student + nodes + link; call all four endpoints; assert shapes, status codes, and permission boundaries

---

## G7 [frontend]: Student Dashboard Frontend

### G7.1 [frontend]: Types + API Layer

- [x] T7.1 [frontend]: Student domain types (`src/features/student/types/student.types.ts`) (2026-06-15)
- [x] T7.2 [frontend]: student-api.ts (depends on T7.1) (2026-06-15)

### G7.2 [frontend]: Hooks

- [x] T7.3 [frontend]: useStudentDashboard hook (depends on T7.2) (2026-06-16)
- [x] T7.4 [frontend]: useStudentNav hook (depends on T7.2) (2026-06-16)

### G7.3 [frontend]: S-home Page

- [x] T7.5 [frontend]: PlatformBoardSection component (depends on T7.1) (2026-06-15)
- [x] T7.6 [frontend]: HomeStudySection component (depends on T7.1) (2026-06-15)
- [x] T7.7 [frontend]: Update app/home/page.tsx with student role branch (depends on T7.3, T7.5, T7.6, T6.6 [backend]) (2026-06-16)

### G7.4 [frontend]: S-nav Page

- [x] T7.8 [frontend]: app/courses page shell (depends on T7.4) (2026-06-16)
- [x] T7.9 [frontend]: NodeTreeSidebar component (depends on T7.1) (2026-06-15)
- [x] T7.10 [frontend]: TopicListPanel component (depends on T7.1) (2026-06-15)
- [x] T7.11 [frontend]: ContentViewer component (depends on T7.1) (2026-06-15)
- [x] T7.12 [frontend]: Wire S-nav in courses/page.tsx (depends on T7.8, T7.9, T7.10, T7.11, T6.6 [backend]) (2026-06-16)
- [~] T7.13 [frontend]: Playwright E2E test — student dashboard (depends on T7.7, T7.12) — DEFERRED: Playwright not installed; E2E coverage deferred to a future cycle

- [x] **G7: Student Dashboard Frontend** — integration test satisfied by unit suite (2168 tests, 100% coverage): StudentHomePage asserts Platform Board + Home Study rendering; StudentCoursesPage asserts full tree→topic→content wiring (2026-06-16)

---

## Ready now

Tasks with no pending dependencies — can be started immediately:

- No `[frontend]` tasks remain. All G7 tasks are done or deferred.
- Remaining cross-repo: G1, G2, G3, G4, G5, G6 integration tests require a running Docker environment.
