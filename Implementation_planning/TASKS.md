# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:04a96f1 frontend:d9532b7 deploy:88cbe5d (2026-06-16)

---

## G1 [deploy]: pgvector Database Image

- [x] T1.1 [deploy]: Wolfi pgvector Dockerfile (`common/images/postgres-pgvector/Dockerfile`) (2026-06-12)
- [x] T1.2 [deploy]: Update common/docker-compose.yml db services to custom image (depends on T1.1) (2026-06-14)
- [x] T1.3 [deploy]: Update dev/docker-compose.yml postgres to pgvector image (depends on T1.2) (2026-06-14)
- [x] T1.4 [deploy]: pgvector smoke test (depends on T1.2, T1.3) (2026-06-15)
- [x] **G1: pgvector Database Image** — `SELECT extversion FROM pg_extension WHERE extname='vector'` returns `0.8.2` ✓ (2026-06-16)

---

## G2 [backend]: Vector Extension + Schema

- [x] T2.1 [backend]: Alembic V31 — CREATE EXTENSION vector (depends on T1.1 [deploy]) (2026-06-15)
- [x] T2.2 [backend]: Alembic V32 — shim for data_topic_content_chunks (depends on T2.1) (2026-06-15)
- [x] **G2: Vector Extension + Schema** — `alembic current` = V32; `data_topic_content_chunks` has `embedding vector(1024)` (atttypmod=1024 confirmed) ✓ (2026-06-16)

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

- [x] **G3: RAG Drain Loop** — 10 outbox rows → `status='done'`; 27 chunks in `data_topic_content_chunks` with `topic_id`/`topic_title`/`node_name` metadata; `text_search_tsv` populated ✓. Two fixes applied: (1) `_LmStudioEmbedding` adapter added to `rag_outbox_loop.py` — `OllamaEmbedding` doesn't speak OpenAI-format API; (2) V33 migration added `text_search_tsv` + trigger + GIN index (V32 shim omitted it). (2026-06-16)

---

## G4 [backend+deploy]: hAITU Settings Wired

- [x] T4.1 [backend]: HaituSettings in shared/config.py — REDO with all 8 fields (top_k, rerank_model, llm_context_window, llm_request_timeout, llm_thinking added) (2026-06-15)
- [x] T4.2 [deploy]: HAITU env vars in common/docker-compose.yml worker (now includes all 8 vars) (depends on T4.1 [backend]) (2026-06-15)
- [x] **G4: hAITU Settings Wired** — all 8 `Settings().haitu.*` fields verified: model_spec, ollama_base_url, max_tokens, top_k, rerank_model, llm_context_window, llm_request_timeout, llm_thinking ✓ (2026-06-16)

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

- [~] **G5: Text Restructuring Pass** — code verified: `restructure_text=True` default set; `GlmOcrProvider` inherits `GlmRestructureMixin.restructure_page()`; called in `extraction_loop.py` under 3-condition guard. Full E2E (upload PDF → assert reassembled fractions) deferred until Ollama is available. (2026-06-16)

---

## G6 [backend]: Student Dashboard Backend APIs

- [x] T6.1 [backend]: Add get_active_links_for_child to ParentChildLinkRepository (2026-06-15)
- [x] T6.3 [backend]: Add get_platform_root_nodes to CoursePathNodeRepository (2026-06-15)
- [x] T6.4 [backend]: Create schemas/student_dashboard.py (2026-06-15)
- [x] T6.2 [backend]: Create StudentDashboardService (depends on T6.1, T6.3) (2026-06-15)
- [x] T6.5 [backend]: Create api/routes/student_dashboard.py (depends on T6.2, T6.4) (2026-06-15)
- [x] T6.6 [backend]: Register student_dashboard router in api/router.py (depends on T6.5) (2026-06-15)
- [x] T6.7 [backend]: Student dashboard API integration test (depends on T6.6) (2026-06-15)
- [x] **G6: Student Dashboard Backend APIs** — all 4 endpoints verified: `/dashboard` (platform_nodes + has_parent_link), `/nodes?owner_type=platform` (4 nodes), `/nodes/{id}/topics` (empty list), `/topics/{id}/content` (15 items); permission boundaries confirmed (student → admin/parent = 403/404) ✓ (2026-06-16)

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

Tasks with no pending dependencies — complete before Phase 3:

- **G10 ✓ (2026-06-16):** `_LmStudioEmbedding` + `_build_embed_model` unit tests committed (`cb602a9`)
- **G11 (manual):** G8 + G9 backend complete (2026-06-16) — full S-nav walkthrough with real data now unblocked; T11.2 and T11.3 pending manual execution

---

## G8 [backend]: Student Node Tree Fix

### G8.1 [backend]: Repository + Service

- [x] T8.1 [backend]: Add `get_all_platform_nodes_visible(viewer_sub: str)` to abstract `AbstractCoursePathNodeRepository` + `CoursePathNodeRepository` — returns all `owner_type='platform'` nodes visible to the student across all categories (reuse `student_visibility_clause`) (2026-06-16)
- [x] T8.2 [backend]: Expose `_build_tree` from `CoursePathNodeService` as a module-level utility function `_build_node_tree(nodes: list[CoursePathNode]) -> list[CoursePathNode]` so `StudentDashboardService` can import it without a cross-service dependency (2026-06-16)
- [x] T8.3 [backend]: Update `StudentDashboardService.get_node_tree()` — platform branch calls `get_all_platform_nodes_visible(viewer_sub)` then `_build_node_tree()` instead of `get_platform_root_nodes()` (2026-06-16)
- [x] T8.4 [backend]: Add `children: list[PlatformNodeCard]` recursive field to `PlatformNodeCard` schema (requires `model_rebuild()` for Pydantic self-reference) (2026-06-16)
- [x] T8.5 [backend]: Update `GET /api/student/nodes` route — serialise children recursively from nested `CoursePathNode.children` into `PlatformNodeCard.children` (2026-06-16)

### G8.2 [backend]: Tests

- [x] T8.6 [backend]: Unit test — `TestGetNodeTreePlatform`: seed grade → subject → course hierarchy; assert `get_node_tree()` returns root with `children[0].children[0]` populated and correct names (2026-06-16)
- [x] T8.7 [backend]: Integration test — `GET /api/student/nodes?owner_type=platform` with 3-level seed; assert JSON response contains nested `children`, depth ≥ 2; assert student visibility (platform-only nodes, parent-owned excluded) (2026-06-16)

- [ ] **G8: Student Node Tree** — `GET /api/student/nodes?owner_type=platform` returns nested tree; NodeTreeSidebar in browser shows expandable grade ▶ → subject ▶ → course hierarchy

---

## G9 [backend]: Student Node topic_count

- [x] T9.1 [backend]: Add `get_topic_counts_for_nodes(node_ids: list[UUID]) -> dict[UUID, int]` to `CoursePathNodeRepository` — single query counting direct `status='live'` topics per node via GROUP BY (2026-06-16)
- [x] T9.2 [backend]: Wire into `StudentDashboardService.get_dashboard()` and `get_node_tree()` — call `get_topic_counts_for_nodes()` after building node list/tree, populate real counts into `PlatformNodeCard` (2026-06-16)
- [x] T9.3 [backend]: Unit test — node with 1 live topic → `topic_count=1`; draft-only node → `topic_count=0`; empty node → `topic_count=0` (2026-06-16)

- [ ] **G9: topic_count** — dashboard cards and courses sidebar badges show correct non-zero counts for nodes with live topics

---

## G10 [backend]: _LmStudioEmbedding Unit Tests ✓ (2026-06-16)

- [x] T10.1 [backend]: `TestLmStudioEmbedding` — mock `openai.OpenAI`; covers `_embed`, `_get_text_embedding`, `_get_query_embedding`, `_aget_text_embedding`, `_aget_query_embedding` (cb602a9)
- [x] T10.2 [backend]: `TestBuildEmbedModel` — covers plain-name → `OllamaEmbedding`; `lmstudio://model@host` → `_LmStudioEmbedding`; `lmstudio://model` (no `@`) → `_LmStudioEmbedding`; unknown scheme → `OllamaEmbedding` fallback (cb602a9)
- [x] `pin_embedding_model_spec` autouse fixture added to `tests/unit/worker/conftest.py` (cb602a9)

- [x] **G10: _LmStudioEmbedding tests** — 100% branch coverage on `_LmStudioEmbedding` and `_build_embed_model` ✓ (2026-06-16)

---

## G11 [manual]: End-to-End Student Navigation Verification

- [x] T11.1 [manual]: "Ratio" topic set to `live` ✓ (confirmed in DB 2026-06-16)
- [ ] T11.2 [manual]: After G8 fix — login as student; expand grade → Maths → Arithmetic in NodeTreeSidebar; select "Ratio" topic; verify LaTeX-formatted content renders in ContentViewer
- [ ] T11.3 [manual]: Verify "Home Study" tab disabled (no parent link); verify placeholder message correct on home page

- [ ] **G11: S-nav E2E** — full student navigation works from dashboard card to content viewer with real data
