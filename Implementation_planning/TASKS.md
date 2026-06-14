# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:5925a0ce9 frontend:ad0c923f8 deploy:f12c465 (2026-06-14)

---

## G1 [deploy]: pgvector Database Image

- [x] T1.1 [deploy]: Wolfi pgvector Dockerfile (`common/images/postgres-pgvector/Dockerfile`) (2026-06-12)
- [x] T1.2 [deploy]: Update common/docker-compose.yml db services to custom image (depends on T1.1) (2026-06-14)
- [x] T1.3 [deploy]: Update dev/docker-compose.yml postgres to pgvector image (depends on T1.2) (2026-06-14)
- [ ] T1.4 [deploy]: pgvector smoke test (depends on T1.2, T1.3)
- [ ] **G1: pgvector Database Image** — integration test: `docker compose up db`; `SELECT extversion FROM pg_extension WHERE extname='vector'` returns `0.8.2`

---

## G2 [backend]: Vector Extension + Schema

- [ ] T2.1 [backend]: Alembic V31 — CREATE EXTENSION vector (depends on T1.1 [deploy])
- [ ] T2.2 [backend]: Alembic V32 — shim for data_topic_content_chunks (depends on T2.1)
- [ ] **G2: Vector Extension + Schema** — integration test: `alembic upgrade head` completes; `alembic current` = V32; `data_topic_content_chunks` has `embedding vector(1024)` column

---

## G3 [backend+deploy]: RAG Drain Loop

### G3.1 [backend]: Config + Dependencies

- [ ] T3.1 [backend]: LlamaIndex dependencies in pyproject.toml
- [ ] T3.2 [backend]: EmbeddingSettings in shared/config.py

### G3.2 [backend]: Loop Implementation

- [ ] T3.3 [backend]: Create worker/rag_outbox_loop.py (depends on T2.2, T3.1, T3.2)
- [ ] T3.4 [backend]: Register rag_outbox_loop in worker/__main__.py (depends on T3.3)
- [ ] T3.6 [backend]: Unit tests for rag_outbox_loop (depends on T3.3)
- [ ] T3.7 [backend]: RAG loop integration test (depends on T3.4, T3.6)

### G3.3 [deploy]: Deploy Config

- [ ] T3.5 [deploy]: EMBEDDING env vars in common/docker-compose.yml worker (depends on T3.2 [backend])

- [ ] **G3: RAG Drain Loop** — integration test: seed outbox row; start worker; wait 10s; assert `status='done'` and `data_topic_content_chunks` has rows

---

## G4 [backend+deploy]: hAITU Settings Wired

- [ ] T4.1 [backend]: HaituSettings in shared/config.py
- [ ] T4.2 [deploy]: HAITU env vars in common/docker-compose.yml worker (depends on T4.1 [backend])
- [ ] **G4: hAITU Settings Wired** — integration test: `Settings().haitu.model_spec` returns `""`; `HAITU__MODEL_SPEC=qwen3:14b` is respected; compose config shows HAITU vars

---

## G5 [backend+deploy]: Text Restructuring Pass

### G5.1 [backend]: Config

- [ ] T5.1 [backend]: Add restructure fields to ExtractionSettings (`restructure_text`, `restructure_model_spec`)

### G5.2 [backend]: Restructure Prompt

- [ ] T5.2 [backend]: Create prompts/restructure_prompt.md

### G5.3 [backend]: restructure_page() Method

- [ ] T5.3 [backend]: Add text-only helpers + restructure_page() to GlmOcrProvider (depends on T5.2)

### G5.4 [backend]: Extraction Loop Integration

- [ ] T5.4 [backend]: Call restructure_page in extract_page() (depends on T5.1, T5.3)

### G5.5 [deploy]: Deploy Config

- [ ] T5.5 [deploy]: Add EXTRACTION__RESTRUCTURE_* to common/docker-compose.yml worker (depends on T5.1 [backend])

### G5.6 [backend]: Tests

- [ ] T5.6 [backend]: Unit tests for restructure_page() — TestRestructurePage (depends on T5.3)
- [ ] T5.7 [backend]: Integration test for text restructuring pipeline (depends on T5.4, T5.6)

- [ ] **G5: Text Restructuring Pass** — integration test: upload math PDF; assert `extraction_job_pages.markdown_text` has reassembled fractions

---

## G6 [backend]: Student Dashboard Backend APIs

- [ ] T6.1 [backend]: Add get_active_links_for_child to ParentChildLinkRepository
- [ ] T6.3 [backend]: Add get_platform_root_nodes to CoursePathNodeRepository
- [ ] T6.4 [backend]: Create schemas/student_dashboard.py
- [ ] T6.2 [backend]: Create StudentDashboardService (depends on T6.1, T6.3)
- [ ] T6.5 [backend]: Create api/routes/student_dashboard.py (depends on T6.2, T6.4)
- [ ] T6.6 [backend]: Register student_dashboard router in api/router.py (depends on T6.5)
- [ ] T6.7 [backend]: Student dashboard API integration test (depends on T6.6)
- [ ] **G6: Student Dashboard Backend APIs** — integration test: seed student + nodes + link; call all four endpoints; assert shapes, status codes, and permission boundaries

---

## G7 [frontend]: Student Dashboard Frontend

### G7.1 [frontend]: Types + API Layer

- [ ] T7.1 [frontend]: Student domain types (`src/features/student/types/student.types.ts`)
- [ ] T7.2 [frontend]: student-api.ts (depends on T7.1)

### G7.2 [frontend]: Hooks

- [ ] T7.3 [frontend]: useStudentDashboard hook (depends on T7.2)
- [ ] T7.4 [frontend]: useStudentNav hook (depends on T7.2)

### G7.3 [frontend]: S-home Page

- [ ] T7.5 [frontend]: PlatformBoardSection component (depends on T7.1)
- [ ] T7.6 [frontend]: HomeStudySection component (depends on T7.1)
- [ ] T7.7 [frontend]: Update app/home/page.tsx with student role branch (depends on T7.3, T7.5, T7.6, T6.6 [backend])

### G7.4 [frontend]: S-nav Page

- [ ] T7.8 [frontend]: app/courses page shell (depends on T7.4)
- [ ] T7.9 [frontend]: NodeTreeSidebar component (depends on T7.1)
- [ ] T7.10 [frontend]: TopicListPanel component (depends on T7.1)
- [ ] T7.11 [frontend]: ContentViewer component (depends on T7.1)
- [ ] T7.12 [frontend]: Wire S-nav in courses/page.tsx (depends on T7.8, T7.9, T7.10, T7.11, T6.6 [backend])
- [ ] T7.13 [frontend]: Playwright E2E test — student dashboard (depends on T7.7, T7.12)

- [ ] **G7: Student Dashboard Frontend** — integration test: render StudentHomePage with mocked hook; assert Platform Board + Home Study; render courses page; assert full tree→topic→content interaction cycle

---

## Ready now

Tasks with no pending dependencies — can be started immediately:

- T1.4 [deploy]: pgvector smoke test (T1.2, T1.3 done)
- T2.1 [backend]: Alembic V31 — CREATE EXTENSION vector (T1.1 [deploy] done)
- T3.1 [backend]: LlamaIndex dependencies in pyproject.toml (no deps)
- T3.2 [backend]: EmbeddingSettings in shared/config.py (no deps)
- T4.1 [backend]: HaituSettings in shared/config.py (no deps)
- T5.1 [backend]: Add restructure fields to ExtractionSettings (no deps)
- T5.2 [backend]: Create prompts/restructure_prompt.md (no deps)
- T6.1 [backend]: Add get_active_links_for_child to ParentChildLinkRepository (no deps)
- T6.3 [backend]: Add get_platform_root_nodes to CoursePathNodeRepository (no deps)
- T6.4 [backend]: Create schemas/student_dashboard.py (no deps)
- T7.1 [frontend]: Student domain types (no deps)
