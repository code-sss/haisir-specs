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
