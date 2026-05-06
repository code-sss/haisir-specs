# PLAN — Phase 1d-real: PDF/Image Content Extraction

> Written: 2026-04-24  
> Spec: `target/requirements/12_content_extraction.md`  
> Schema deltas: `target/requirements/01_data_model.md` § "Schema Extensions (Phase 1d-real)"  
> Prototype (Playwright-validated): `target/prototypes/haisir_admin_flow.html`
>
> **What already exists from Phase 1d-stub (do not re-implement):**
> - `PATCH /api/topic-contents/{id}` and `DELETE /api/topic-contents/{id}` (backend)
> - `TopicContentUpdate` schema (`title`, `order`, `description`, `url`, `text` — `content_type` immutable)
> - `update_platform_content` / `delete_platform_content` infra repo methods (oracle JOIN protection)
> - Frontend: `TopicContent` type, `ContentItemRow`, `AddContentModal` (create/edit), `DeleteContentDialog`, `useTopicContents` hook — all working for video URL + text types
>
> **Status as of 2026-05-06 (reconciled):**
> ✅ Shipped: V26 migration (6 tables + column), domain layer (models/protocols/service), infra repos (ExtractionJobRepository, ExtractionSourceStorage), admin API (T5.1–T5.6), APISIX upload route, rebuilt AddContentModal (G9), topic card jobs strip (G10), CSRF gate (G8).
> ❌ Remaining: GlmOcrProvider (T4.1), PdfiumReader (T4.2), worker process (G7), worker Docker Compose (G1), worker health page (G12), provenance + editing (G11), parent extraction API (G6).

---

## Problem Statement

Platform admins can add video URLs and pasted text to topics, but cannot upload PDF/image files for extraction. Phase 1d-real closes the gap: multipart upload → Postgres queue → `pypdfium2`/`glm-ocr` worker → N `topic_contents` rows of `content_type='text'`, with real-time progress polling, permanent provenance, inline editing, and a worker health dashboard.

---

## Architecture Decisions (from decisions.md 2026-04-23)

1. Same `haisir-backend` Docker image, two process modes: `python -m haisir.api` / `python -m haisir.worker`
2. Worker `replicas: 2` from day one — `FOR UPDATE SKIP LOCKED` requires N≥2 to be meaningful
3. No Redis/ARQ/Celery — Postgres-only queue for current scale (5–10 admins, ~50–200 PDFs/week)
4. `pypdfium2` (Apache/BSD) for PDF. **PyMuPDF BANNED** — AGPL §13 SaaS clause
5. `glm-ocr` from `../haiguru/glm_ocr/` (copy into haisir-backend); prefix-dispatch model spec
6. ONE upload → N `topic_contents` rows of `content_type='text'`. No new enum value
7. Source files are transient; `extraction_job_audit` is permanent (never purged)
8. `source_extraction_job_id` NEVER cleared by `PATCH /api/topic-contents/{id}` (BR-EXT-023a)
9. No upload-time title for PDF/image — auto-derived from first H1, fallback `"Page N — {filename}"` (BR-EXT-023b)
10. RAG embedding via `rag_indexing_outbox` — haiguru owns outbox draining (see T7.4 UNRESOLVED)

---

## Goal Tree

### G1 [deploy]: Worker service provisioned

**Purpose:** The worker process must run as a second process from the same Docker image. Without this, the rest of the plan cannot be tested end-to-end.

##### T1.1 [deploy]: Add worker service to Docker Compose
- **Build:** In `haisir-deploy` (dev compose file), add a `worker` service reusing the same image as `api`:
  - `command: python -m haisir.worker`
  - `replicas: 2`
  - Env vars: `EXTRACTION_MODEL_SPEC` (default: `lmstudio://localhost:1234/v1`), `MAX_PER_JOB_USD=20`, `MAX_DAILY_PLATFORM_USD=200`, `STORAGE_ROOT=/data/storage`, `WORKER_HEARTBEAT_INTERVAL=10`
  - `depends_on: [db, api]`
  - Same network as `api`
- **Done when:** `docker compose up --scale worker=2 -d` starts 2 worker containers and they exit 0 (graceful if no `worker/__main__.py` yet, or fail fast with missing-module error — not crash-loop). After T7.6, they stay running.
- **Test:** `docker compose ps` shows 2 worker containers in running state after `worker/__main__.py` exists.
- **Depends on:** None

##### T1.2 [deploy]: STORAGE_ROOT volume + api mount
- **Build:** Define a `extraction_sources` named volume in compose. Mount it to both `api` and `worker` at `/data/storage/extraction_sources`. Add `STORAGE_ROOT=/data/storage` to api service env as well.
- **Done when:** File written by api container at `$STORAGE_ROOT/extraction_sources/test/file.pdf` is readable by worker container.
- **Test:** `docker compose exec api ls /data/storage/extraction_sources && docker compose exec worker ls /data/storage/extraction_sources`
- **Depends on:** T1.1

**G1 integration test:** `docker compose up` → 2 worker containers appear in `docker compose ps`; no crash-loop.

---

### G2 [backend]: Schema ready

**Purpose:** All 6 new tables + 1 new column must exist before any domain/infra code can reference them.

##### T2.1 [backend]: Alembic migration V26 — extraction tables ✅ shipped 2026-04-30
- **Note:** Shipped as `V26_extraction_tables.py` (V25 was already used for `expand_nodetype_enum`). Build spec below preserved for reference.
- **Build:** Create `alembic/versions/V26_extraction_tables.py`. Include in a single migration:
  1. `ALTER TABLE topic_contents ADD COLUMN source_extraction_job_id UUID NULL`
  2. `CREATE TABLE extraction_jobs` (all columns per `01_data_model.md`; `updated_at` trigger: `CREATE TRIGGER trg_extraction_jobs_touch BEFORE UPDATE ON extraction_jobs FOR EACH ROW EXECUTE FUNCTION touch_updated_at()`)
  3. All indexes: `ix_extraction_jobs_queue (status, created_at)`, `ix_extraction_jobs_topic (topic_id, status)`, `ix_extraction_jobs_purge (purge_at) WHERE purge_at IS NOT NULL`, UNIQUE `ux_extraction_jobs_idempotency (created_by, idempotency_key)`, UNIQUE `ux_extraction_jobs_dedup (topic_id, source_sha256) WHERE status NOT IN ('cancelled','upload_failed')`
  4. `CREATE TABLE extraction_job_pages` (composite PK `(job_id, page_no)`)
  5. `CREATE TABLE extraction_job_audit` with indexes `ix_extraction_job_audit_topic (topic_id)`, `ix_extraction_job_audit_user_day (idp_sub, finished_at DESC)`
  6. `CREATE TABLE rag_indexing_outbox` with index `ix_rag_outbox_pending (status, created_at) WHERE status = 'pending'`; `updated_at` trigger
  7. `CREATE TABLE worker_heartbeats`
  8. `CREATE TABLE parent_quota_counters`; `updated_at` trigger
  - Note: Status values are VARCHAR strings, NOT a Postgres ENUM — avoids migration churn when adding states
- **Done when:** `alembic upgrade head` completes with no errors. `psql -c "\dt"` shows 6 new tables. `psql -c "\d topic_contents"` shows `source_extraction_job_id uuid`. All 5 indexes on `extraction_jobs` exist.
- **Test:** `pytest tests/integration/test_migrations.py` verifies all tables exist with correct columns/indexes.
- **Depends on:** None

**G2 integration test:** `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` round-trips cleanly.

---

### G3 [backend]: Domain layer

**Purpose:** Domain models and protocols define the shapes that all other layers use. Must be repo/DB-agnostic (plain dataclasses, no SQLAlchemy imports).

##### T3.1 [backend]: Domain models — `domain/models/extraction_job.py`
- **Build:** Plain Python dataclasses (no `Base` subclassing per CLAUDE.md):
  - `ExtractionJobStatus(StrEnum)`: `pending`, `extracting`, `done`, `upload_failed`, `extraction_failed`, `cancelled`
  - `ExtractionJob(dataclass)`: all fields from migration (id UUID, topic_id UUID, created_by str, expected_owner_type str, job_type str, source_type str, source_filename str, source_size_bytes int, source_path str, source_sha256 str, status ExtractionJobStatus, pages_total int|None, pages_completed int, cancel_requested bool, error_message str|None, idempotency_key UUID, running_cost_usd Decimal, created_at datetime, updated_at datetime, started_at datetime|None, finished_at datetime|None, purge_at datetime|None, locked_at datetime|None, locked_by str|None)
  - `ExtractionJobPage(dataclass)`: job_id UUID, page_no int, markdown_text str, sha256 str, extracted_at datetime
  - `ExtractionJobAudit(dataclass)`: job_id UUID, topic_id UUID, idp_sub str, source_filename str, source_sha256 str, source_type str, job_type str, model_spec_used str, pages_extracted int, cost_usd Decimal, final_status str, started_at datetime, finished_at datetime
  - `RagIndexingOutbox(dataclass)`: content_id UUID, status str, retry_count int, last_error str|None, created_at datetime, updated_at datetime, locked_at datetime|None, locked_by str|None
  - `WorkerHeartbeat(dataclass)`: worker_id str, started_at datetime, last_seen datetime, job_id UUID|None
  - `ParentQuotaCounter(dataclass)`: idp_sub str, concurrent_jobs int, daily_jobs int, daily_window_start datetime, updated_at datetime
- **Done when:** `from haisir.domain.models.extraction_job import ExtractionJob, ExtractionJobStatus` succeeds; all fields match migration schema.
- **Test:** `pytest tests/unit/domain/test_extraction_job_models.py` — instantiation, field defaults, StrEnum values.
- **Depends on:** None

##### T3.2 [backend]: Domain protocols — `domain/protocols/extraction.py`
- **Build:** Python `Protocol` classes:
  - `ExtractionProvider(Protocol)`: `def process(self, *, image: bytes, prompt: str) -> str: ...` (returns full markdown text from vision LLM)
  - `PdfReader(Protocol)`: `def page_count(self, pdf_bytes: bytes) -> int: ...`, `def extract_text(self, pdf_bytes: bytes, page_no: int) -> str: ...`, `def image_coverage(self, pdf_bytes: bytes, page_no: int) -> float: ...` (returns 0.0–1.0 ratio), `def render(self, pdf_bytes: bytes, page_no: int, scale: float = 2.0) -> bytes: ...` (returns JPEG bytes)
- **Done when:** Protocol methods are inspectable via `inspect.get_annotations`. A mock class implementing both protocols passes `isinstance` check with `runtime_checkable`.
- **Test:** `pytest tests/unit/domain/test_extraction_protocols.py` — assert mock impls satisfy protocol.
- **Depends on:** None

##### T3.3 [backend]: Extraction service — `domain/services/extraction_service.py`
- **Build:** `ExtractionService` class injected with `ExtractionJobRepository`, `ExtractionSourceStorage`, `ExtractionProvider`, `PdfReader`. Methods:
  - `create_admin_job(topic_id, file_bytes, filename, idempotency_key, x_force_reextract, current_user) -> ExtractionJob` — validates `topics.owner_type='platform'`, idempotency replay, SHA dedup, save file, insert job
  - `list_jobs(topic_id, current_user) -> list[ExtractionJob]` — filtered by role (admin sees all for topic; parent sees own only)
  - `get_job(job_id, current_user) -> ExtractionJob | None`
  - `cancel_job(job_id, current_user) -> ExtractionJob` — hard cancel for pending, soft for extracting
  - `retry_job(job_id, new_idempotency_key, current_user) -> ExtractionJob` — validates extraction_failed + source still on disk
  - `create_parent_job(topic_id, file_bytes, filename, idempotency_key, x_force_reextract, current_user) -> ExtractionJob` — same as admin + quota check FOR UPDATE on parent_quota_counters
  - `get_worker_health() -> list[WorkerHeartbeat]` — reads worker_heartbeats, annotates is_stale
  - Permission gate: admin methods → require `X-Current-Role: admin`; parent methods → require `X-Current-Role: parent`; both return 400 if header missing, 404 for wrong owner
- **Done when:** `pytest tests/unit/services/test_extraction_service.py` passes with all methods tested against mocked repos.
- **Test:** Unit tests using pytest fixtures with Mock repos — cover: idempotency replay returns same job; SHA dedup 409 behaviour; quota exceeded raises 429; wrong owner_type raises 404.
- **Depends on:** T3.1, T3.2

**G3 integration test:** `pytest tests/unit/services/` all pass — no DB required.

---

### G4 [backend]: Infrastructure layer

**Purpose:** Concrete implementations of protocols and repositories. All I/O isolated here.

##### T4.1 [backend]: GLM-OCR provider — `infrastructure/extraction/glm_ocr_provider.py`
- **Build:** Copy `../haiguru/glm_ocr/` into `src/infrastructure/extraction/glm_ocr/`. Write `GlmOcrProvider` implementing `ExtractionProvider`:
  - Parse model spec from env `EXTRACTION_MODEL_SPEC`: `lmstudio://host:port/base_path` → OpenAI-compat; `openai://model-name` → OpenAI API; `anthropic://model-name` → Anthropic; plain string → Ollama
  - Streaming call with tuple protocol: yield `('__first_token__', None)`, `('chunk', text)`, `('__done__', full_text)`
  - `process(image, prompt)` accumulates stream → returns full markdown string
  - Add to `requirements.txt`: `openai>=1.0`, `anthropic>=0.20` (for provider dispatch; Ollama uses httpx directly)
- **Done when:** `GlmOcrProvider(model_spec='lmstudio://localhost:1234/v1').process(image=b'...', prompt='...')` returns a non-empty string (requires local model or mock). Unit test with mocked HTTP client passes.
- **Test:** `pytest tests/unit/infrastructure/test_glm_ocr_provider.py` with patched HTTP — assert (a) lmstudio:// path calls OpenAI-compat base URL; (b) anthropic:// path calls Anthropic API; (c) streaming chunks accumulated correctly.
- **Depends on:** T3.2

##### T4.2 [backend]: pypdfium2 reader — `infrastructure/extraction/pdfium_reader.py`
- **Build:** `PdfiumReader` implementing `PdfReader`:
  - `page_count(pdf_bytes)` — open document, return `len(doc)`
  - `extract_text(pdf_bytes, page_no)` — get textpage, return full text string
  - `image_coverage(pdf_bytes, page_no)` — count image objects on page, estimate area / page area; return float 0.0–1.0
  - `render(pdf_bytes, page_no, scale=2.0)` — render page at scale, export as JPEG bytes
  - Add `pypdfium2>=4.0` to `requirements.txt`
  - **PyMuPDF / fitz imports MUST NOT appear anywhere** — CI lint check required
- **Done when:** `PdfiumReader().page_count(b'%PDF...')` returns an int; unit test with a real 1-page PDF fixture passes all 4 methods.
- **Test:** `pytest tests/unit/infrastructure/test_pdfium_reader.py` with a minimal PDF fixture in `tests/fixtures/sample.pdf`.
- **Depends on:** T3.2

##### T4.3 [backend]: Extraction job repository — `infrastructure/repositories/extraction_job_repository.py`
- **Build:** SQLAlchemy imperative mapping (no Base subclassing). `ExtractionJobRepository` with:
  - `claim_next() -> ExtractionJob | None` — `SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1` where `status='pending' OR (status='extracting' AND locked_at < NOW()-INTERVAL '5min')`; UPDATE to `status='extracting', locked_at=NOW(), locked_by=hostname`; return job or None
  - `insert_job(job: ExtractionJob) -> ExtractionJob`
  - `update_job(job_id, **fields) -> None` — partial UPDATE
  - `get_by_id(job_id) -> ExtractionJob | None`
  - `get_by_topic(topic_id, created_by: str | None = None) -> list[ExtractionJob]`
  - `get_by_idempotency(created_by, idempotency_key) -> ExtractionJob | None`
  - `get_sha_exists(topic_id, sha256) -> ExtractionJob | None` — checks dedup index
  - `insert_page(page: ExtractionJobPage) -> None`
  - `get_pages(job_id) -> list[ExtractionJobPage]` ordered by page_no
  - `delete_pages(job_id) -> None`
  - `get_max_page_no(job_id) -> int | None`
  - `write_audit(audit: ExtractionJobAudit) -> None`
  - `upsert_heartbeat(heartbeat: WorkerHeartbeat) -> None`
  - `get_all_heartbeats() -> list[WorkerHeartbeat]`
  - `get_quota(idp_sub) -> ParentQuotaCounter | None`
  - `upsert_quota(idp_sub, **fields) -> ParentQuotaCounter` — FOR UPDATE inside TX
  - `get_expired_jobs() -> list[ExtractionJob]` — `purge_at < NOW()` AND final status
  - `get_outbox_batch(batch_size=10) -> list[RagIndexingOutbox]` — SKIP LOCKED
  - `update_outbox(content_id, **fields) -> None`
  - `delete_outbox_done_rows() -> None` — delete done rows older than 24h
- **Done when:** `pytest tests/integration/repositories/test_extraction_job_repository.py` passes; SKIP LOCKED claim verified with 2 concurrent DB sessions in same test.
- **Test:** Integration tests with real test DB (pytest-asyncio or sync with test transaction rollback). Verify: (a) two workers calling `claim_next()` concurrently never claim the same job; (b) idempotency lookup returns same row; (c) dedup query excludes cancelled/upload_failed.
- **Depends on:** T3.1, T2.1

##### T4.4 [backend]: Extraction source storage — `infrastructure/storage/extraction_source.py`
- **Build:** `ExtractionSourceStorage`:
  - `save_file(job_id: UUID, filename: str, data: bytes | BinaryIO) -> Path` — write to `STORAGE_ROOT/extraction_sources/{job_id}/{safe_filename}`; `safe_filename = Path(filename).name` (strips path separators); assert resolved path `is_relative_to(STORAGE_ROOT)` (BR-EXT-029 path traversal guard); create parent dirs; return relative path
  - `delete_file(relative_path: str) -> None` — silent if not found
  - `get_path(relative_path: str) -> Path`
  - `file_exists(relative_path: str) -> bool`
  - Add `python-magic>=0.4` to `requirements.txt`; MIME sniff helper: `sniff_mime(first_8kb: bytes) -> str` returning MIME type; raise `UnsupportedMimeType` if not in whitelist (`application/pdf`, `image/png`, `image/jpeg`, `image/webp`)
- **Done when:** `save_file(uuid4(), 'chapter1.pdf', b'%PDF')` creates file at correct path; `save_file(uuid4(), '../etc/passwd', b'x')` raises `ValueError` (path traversal).
- **Test:** `pytest tests/unit/infrastructure/test_extraction_source_storage.py` — path traversal test with `../evil`, `%2F..%2F`, `\x00` in filename.
- **Depends on:** T3.1

**G4 integration test:** `pytest tests/unit/infrastructure/ tests/integration/repositories/test_extraction_job_repository.py` all pass.

---

### G5 [backend]: Admin extraction API (6 endpoints)

**Purpose:** All admin-facing extraction endpoints. Pattern reference: existing `src/api/routes/topic.py` for oracle protection and `src/auth/permission.py` for `require_admin`.

##### T5.0 [deploy]: APISIX dedicated plugin config and route for multipart extraction upload
- **Root cause — Bug 1 (400):** `05-api-write.json` has `request-validation` → `body_schema: { type: [object, array] }`. APISIX JSON-decodes the raw multipart body, fails at character 1 (`--boundary...`), and returns 400. Zero latency and `- - -` upstream in the access log confirm it never reaches FastAPI. Direct `curl` to port 8000 returns 200.
- **Root cause — Bug 2 (413):** All shared plugin configs (`01/02/03`) set `tx.max_file_size=1048576` and `tx.combined_file_sizes=1048576` (1 MB). Coraza CRS rule 920160 blocks any upload > 1 MB with 413. The backend spec allows up to 50 MB. Raising the shared limit would weaken Coraza protection on all other API routes.
- **Affected routes:** `POST /api/admin/topics/*/extraction-jobs` and `POST /api/parent/curriculum/topics/*/extraction-jobs`
- **Build:**
  - **File 1 — `common/plugin_configs/04-secured-api-upload.json`:** Clone of `03-secured-api.json`. Add Coraza rule `id:199004` that overrides only three variables:
    - `setvar:tx.max_file_size=52428800` (50 MB)
    - `setvar:tx.combined_file_sizes=52428800` (50 MB)
    - `SecRequestBodyLimit 54525952` (52 MB — buffer above the combined limit so Coraza does not truncate the body before WAF rules can inspect multipart part headers; `@recommended-conf` default is ~13 MB)
    - Everything else preserved exactly: OWASP CRS PL2, anomaly scoring, OIDC (`unauth_action: deny` → 401), rate limiting, UA/referer/URI blocking, all arg limits (`max_num_args`, `arg_name_length`, `arg_length`, `total_arg_length`)
    - **Implementer note:** verify `id:199004` is in the project's Coraza rule ID namespace — check existing override rule IDs in `03-secured-api.json` for the convention
  - **File 2 — `common/routes/15-api-extraction-upload.json`:**
    - URIs: `/api/admin/topics/*/extraction-jobs` and `/api/parent/curriculum/topics/*/extraction-jobs`, method `POST` only
    - `priority: 20` — higher than `05-api-write.json` (`priority: 10`) so it matches first
    - `plugin_config_id: "secured-api-upload"` (the new plugin config above)
    - Route-level `request-validation` with `header_schema` only: enforces `Content-Type: multipart/form-data` via pattern `(?i)^multipart/form-data(;.*)?$`; **no `body_schema`** — multipart body is binary not JSON; Coraza WAF (CRS PL2) inspects multipart field values; FastAPI + MIME sniff own file content validation
    - Upstream `read` timeout: `120s` (50 MB uploads on slow connections; default 6s would timeout mid-upload)
    - `backend:8000` upstream, same as all other API routes
- **Done when:**
  - `POST multipart/form-data` with a PDF > 1 MB via APISIX port 9080/9443 → FastAPI response (not 400 or 413)
  - `POST application/json` to the same URI → 400 (header_schema rejects non-multipart)
  - `jq '.' common/plugin_configs/04-secured-api-upload.json` exits 0
  - `jq '.' common/routes/15-api-extraction-upload.json` exits 0
- **Test:** `curl -X POST http://localhost:9080/api/admin/topics/{id}/extraction-jobs -F file=@tests/fixtures/sample.pdf -H 'Content-Type: multipart/form-data; boundary=xxx'` → reaches FastAPI (not 400 or 413). `curl` with `-H 'Content-Type: application/json'` → 400.
- **Manifest flags when deploying:** `apisix_routes: true`, `apisix_plugins: true`
- **Depends on:** None — can be deployed standalone; prerequisite for T5.1 to be testable end-to-end through the gateway

##### T5.1 [backend]: POST /api/admin/topics/{topic_id}/extraction-jobs
- **Build:** Route in `src/api/routes/admin/extraction.py`. Dependencies: `require_admin`, CSRF, `current_active_user`.
  - Streaming multipart parser: reject if `content_length > 50_000_000` before buffering → 413
  - Sniff first 8 KB via `ExtractionSourceStorage.sniff_mime` → 415 if not whitelisted
  - Stream to SHA-256 hasher while saving to `ExtractionSourceStorage.save_file`
  - `Idempotency-Key` header → 400 if missing; idempotency lookup → return 201 with existing job if found
  - `X-Force-Reextract` header check: if `'true'` skip dedup; else dedup check → 409 with `{"detail": "...", "existing_job_id": "..."}`
  - Oracle check: `topics.owner_type='platform'` → 404 if not (join `topics` table, return 404 not 403)
  - `INSERT extraction_jobs` with `status='pending'`, `expected_owner_type='platform'`
  - Return 201 with full `ExtractionJobRead` schema
- **Done when:** `pytest tests/integration/api/test_admin_extraction.py::test_post_create_job` passes. Also: missing `Idempotency-Key` → 400; file > 50MB → 413; `.exe` file → 415; same hash on same topic → 409; idempotency replay → 201 same body; missing `X-Current-Role` → 400.
- **Test:** Integration test using `httpx.AsyncClient` with test app; real DB; real file fixture.
- **Depends on:** T4.3, T4.4, T3.3, T2.1

##### T5.2 [backend]: GET /api/admin/topics/{topic_id}/extraction-jobs
- **Build:** Query `extraction_jobs WHERE topic_id=? ORDER BY created_at DESC`. Compute `progress = pages_completed * 100 / NULLIF(pages_total, 0)`. ETag = `str(MAX(updated_at))`. If `If-None-Match` matches → 304. Return `{"jobs": [ExtractionJobListItem]}`.
- **Done when:** Response includes `progress` field; ETag header present; 304 returned on second identical call.
- **Test:** `pytest tests/integration/api/test_admin_extraction.py::test_list_jobs_etag` — first call returns 200 + ETag; second call with same ETag returns 304.
- **Depends on:** T4.3, T2.1

##### T5.3 [backend]: GET /api/admin/extraction-jobs/{job_id}
- **Build:** Lookup by `job_id`; 404 if not found or not admin-created (`created_by` check omitted for admin — admins see all platform topic jobs; but topic must be `owner_type='platform'`). Return `ExtractionJobRead`.
- **Done when:** 200 with full job object; 404 for unknown id.
- **Test:** Unit test for service; integration test for 404 on unknown id.
- **Depends on:** T4.3, T2.1

##### T5.4 [backend]: DELETE /api/admin/extraction-jobs/{job_id}
- **Build:**
  - `status='pending'` → `UPDATE status='cancelled', purge_at=NOW()+24h`; `ExtractionSourceStorage.delete_file(job.source_path)`; return 200
  - `status='extracting'` → `UPDATE cancel_requested=true`; return 200 with `{"detail": "cancellation requested"}`
  - `status='done'` → 404 (use Delete `/api/topic-contents/{id}` for materialized rows)
  - `status` in `('extraction_failed', 'cancelled', 'upload_failed')` → 409 with current status
- **Done when:** Each status branch returns correct code. 
- **Test:** `pytest tests/integration/api/test_admin_extraction.py::test_cancel_*`
- **Depends on:** T4.3, T4.4, T2.1

##### T5.5 [backend]: POST /api/admin/extraction-jobs/{job_id}/retry
- **Build:** Requires `status='extraction_failed'`; `ExtractionSourceStorage.file_exists(job.source_path)` → 404 with `{"detail": "source file purged; re-upload required"}` if missing; new `Idempotency-Key` header required; `UPDATE status='pending', started_at=NULL, pages_completed=0, cancel_requested=false, error_message=NULL, purge_at=NULL`; return 201.
- **Done when:** Retry of `extraction_failed` job → 201 with status `pending`; retry after purge → 404.
- **Test:** `pytest tests/integration/api/test_admin_extraction.py::test_retry_*`
- **Depends on:** T4.3, T4.4, T2.1

##### T5.6 [backend]: GET /api/admin/system/workers
- **Build:** `SELECT * FROM worker_heartbeats`. Annotate each with `is_stale: bool = (last_seen < NOW()-INTERVAL '60s')`. Return `{"workers": [...], "active_count": N, "stale_count": N}`. Admin-only.
- **Done when:** Response includes `is_stale` field; stale detection threshold is 60s.
- **Test:** `pytest tests/integration/api/test_admin_system.py::test_worker_health` — seed 2 heartbeats (1 fresh, 1 stale by timestamp); assert response counts.
- **Depends on:** T4.3, T2.1

**G5 integration test:** `pytest tests/integration/api/test_admin_extraction.py` all pass; also run CSRF-missing test (→ 403) and `X-Current-Role` missing test (→ 400) for every mutable endpoint.

---

### G6 [backend]: Parent extraction API (parity + quota)

**Purpose:** Parent API mirrors admin API but scopes to `owner_type='parent' AND owner_id=idp_sub` and enforces quota. Pattern: same service methods, different permission gate.

##### T6.1 [backend]: POST /api/parent/curriculum/topics/{topic_id}/extraction-jobs
- **Build:** Same pipeline as T5.1. Additions:
  - Oracle: `topics.owner_type='parent' AND owner_id = current_user.idp_sub` → 404 if not
  - Quota check inside POST handler TX: `UPSERT parent_quota_counters FOR UPDATE`; if `concurrent_jobs >= 5` → 429 `{"detail": "max 5 concurrent jobs"}` (BR-EXT-024); if `daily_jobs >= 100` → 429 (BR-EXT-024); increment `concurrent_jobs` and `daily_jobs` on insert; reset `daily_jobs=0, daily_window_start=NOW()` if `daily_window_start < NOW()-INTERVAL '24h'`
  - Set `expected_owner_type='parent'` on job row
- **Done when:** Concurrent quota: 6th concurrent POST returns 429. Daily quota: 101st daily POST returns 429. Wrong parent topic → 404.
- **Test:** `pytest tests/integration/api/test_parent_extraction.py::test_quota_*`
- **Depends on:** T4.3, T4.4, T3.3, T2.1

##### T6.2 [backend]: GET /api/parent/curriculum/topics/{topic_id}/extraction-jobs
- **Build:** List filtered by `created_by = current_user.idp_sub`. ETag same logic as T5.2.
- **Done when:** Parent A cannot see Parent B's jobs on the same topic.
- **Test:** Seed 2 jobs from 2 different parents; assert each parent sees only their own.
- **Depends on:** T4.3, T2.1

##### T6.3 [backend]: GET /api/parent/curriculum/extraction-jobs/{job_id}
- **Build:** 404 if job not found OR `job.created_by != current_user.idp_sub`.
- **Done when:** Parent B gets 404 for Parent A's job_id.
- **Test:** Cross-parent isolation test.
- **Depends on:** T4.3, T2.1

##### T6.4 [backend]: DELETE /api/parent/curriculum/extraction-jobs/{job_id}
- **Build:** Same logic as T5.4. Guard `job.created_by == current_user.idp_sub` → 404 otherwise. On successful cancel of `pending`, decrement `parent_quota_counters.concurrent_jobs`.
- **Done when:** Cancel decrements quota counter.
- **Test:** Quota counter decrement verified.
- **Depends on:** T4.3, T4.4, T2.1

##### T6.5 [backend]: POST /api/parent/curriculum/extraction-jobs/{job_id}/retry
- **Build:** Same as T5.5. Guard `job.created_by == current_user.idp_sub`.
- **Done when:** Parent B cannot retry Parent A's job.
- **Test:** Cross-parent isolation test.
- **Depends on:** T4.3, T4.4, T2.1

**G6 integration test:** `pytest tests/integration/api/test_parent_extraction.py` all pass including quota and isolation tests.

---

### G7 [backend]: Worker process

**Purpose:** The background process that claims pending jobs, extracts content page-by-page, and materializes `topic_contents` rows.

##### T7.1 [backend]: Extraction loop — `worker/extraction_loop.py`
- **Build:** `async def extraction_loop(repo, provider, pdf_reader, storage) -> None` (runs forever):
  ```
  while True:
      await asyncio.sleep(2)
      job = repo.claim_next()
      if not job: continue
      
      pages = enumerate_pages(job, storage, pdf_reader)  # list of (page_no, data)
      resume_from = repo.get_max_page_no(job.id) or -1
      
      for page_no, page_data in pages[resume_from + 1:]:
          if repo.get_by_id(job.id).cancel_requested:
              repo.update_job(job.id, status='cancelled', finished_at=now(), purge_at=now()+24h)
              return
          try:
              md = extract_page(job, page_no, page_data, provider, pdf_reader)
              repo.insert_page(ExtractionJobPage(job_id=job.id, page_no=page_no, markdown_text=md, ...))
              repo.update_job(job.id, pages_completed=page_no, locked_at=now(), running_cost_usd=...)
          except Exception as e:
              repo.update_job(job.id, status='extraction_failed', error_message=str(e), finished_at=now(), purge_at=now()+30d)
              return
          if job.running_cost_usd > MAX_PER_JOB_USD:
              repo.update_job(job.id, status='extraction_failed', error_message='per-job cost cap exceeded', ...)
              return
      
      finalize(job, repo)  # see T7.2
  ```
  - `extract_page` routing (BR-EXT-009): if `source_type='image'` → `provider.process(image=page_data, prompt=prompt_for(job_type))`; if `source_type='pdf'` AND `pdf_reader.extract_text(...)` length ≥50 AND `image_coverage(...) < 0.95` → return native text; else `pdf_reader.render(...) → provider.process(...)`
  - `prompt_for(job_type)`: reads `prompts/contents_prompt.md` or `prompts/exercises_prompt.md`
  - `enumerate_pages(job, storage, pdf_reader)`: for PDF → list `range(page_count)`; for image → `[0]` (single page)
- **Done when:** `pytest tests/integration/worker/test_extraction_loop.py` — seed pending PDF job → run loop for one iteration → extraction_job_pages row created; cancelled job check works.
- **Test:** Integration test with real DB + mocked provider (returns fixed markdown). Assert page row created; status becomes `extracting`; cancel check stops loop.
- **Depends on:** T4.1, T4.2, T4.3, T4.4, T2.1

##### T7.2 [backend]: Finalize transaction — `worker/finalize.py`
- **Build:** `def finalize(job, repo, session)` — runs as one atomic TX:
  1. `SELECT owner_type, owner_id FROM topics WHERE id=:topic_id FOR UPDATE` — re-validate (BR-DATA-011, BR-EXT-010): platform job → assert `owner_type='platform'`; parent job → assert `owner_type='parent' AND owner_id=job.created_by`. Mismatch → `UPDATE status='extraction_failed', error_message='ownership_violation'`, ROLLBACK
  2. `base = COALESCE(MAX(content_order), 0) FROM topic_contents WHERE topic_id=:t FOR UPDATE` (BR-DATA-012)
  3. Read all staged pages from `extraction_job_pages` ordered by page_no
  4. For each page: parse first H1 from markdown_text → title; fallback `f"Page {page_no + 1} — {job.source_filename}"` (BR-EXT-023b)
  5. `INSERT INTO topic_contents (id, topic_id, content_type='text', title, text=markdown_text, content_order=base+page_no, source_extraction_job_id=job.id) RETURNING id`
  6. `INSERT INTO rag_indexing_outbox (content_id, status='pending') VALUES (:returned_id, ...)` for each (BR-EXT-012)
  7. `INSERT INTO extraction_job_audit (job_id, topic_id, idp_sub=job.created_by, source_filename, source_sha256, source_type, job_type, model_spec_used=EXTRACTION_MODEL_SPEC, pages_extracted=N, cost_usd=job.running_cost_usd, final_status='done', started_at, finished_at=NOW())`
  8. `DELETE FROM extraction_job_pages WHERE job_id=:job`
  9. `UPDATE extraction_jobs SET status='done', finished_at=NOW(), purge_at=NOW()+7d WHERE id=:job`
  10. COMMIT
- **Done when:** After finalize: `topic_contents` has N rows with `source_extraction_job_id=job.id`; `extraction_job_pages` empty; `extraction_job_audit` has 1 row; `rag_indexing_outbox` has N rows; job status `done`.
- **Test:** `pytest tests/integration/worker/test_finalize.py` — seed job + pages → call finalize → assert all outcomes in single test. Include ownership_violation case: mismatched owner_type → job status `extraction_failed`, no topic_contents rows.
- **Depends on:** T4.3, T2.1

##### T7.3 [backend]: Purge loop — `worker/purge_loop.py`
- **Build:** `async def purge_loop(repo, storage) -> None`:
  - Runs check every 1 hour (in-memory `last_ran` clock, not a new DB table)
  - `jobs = repo.get_expired_jobs()` — `purge_at < NOW()` AND `status IN ('done','extraction_failed','cancelled','upload_failed')`
  - For each: `storage.delete_file(job.source_path)` (silent on missing); `repo.delete_job(job.id)`
  - Also: `repo.delete_outbox_done_rows()` — done outbox rows older than 24h
- **Done when:** Job with `purge_at = NOW() - 1s` is deleted; source file removed; rag_outbox done rows cleaned.
- **Test:** `pytest tests/integration/worker/test_purge_loop.py` — seed expired job + source file → run purge → assert job row gone + file deleted.
- **Depends on:** T4.3, T4.4, T2.1

##### T7.4 [backend]: RAG outbox loop — `worker/rag_outbox_loop.py`
<!-- UNRESOLVED: No RAG embedding infrastructure exists in haisir-backend. The haiguru service (../haiguru/) uses the same Postgres DB and owns rag_chunks. T7.4 must resolve HOW haisir's worker delivers embeddings: 
  Option A (recommended): haiguru worker polls rag_indexing_outbox directly (it already has DB access + embedding pipeline). haisir's rag_outbox_loop.py is a stub that only cleans up done rows.
  Option B: haisir worker calls a haiguru HTTP API endpoint per content_id to trigger embedding. Adds HTTP dep.
  Resolve this before starting T7.4. Check ../haiguru/README.md and the haiguru worker entrypoint for guidance. -->
- **Build (pending resolution):** `async def rag_outbox_loop(repo) -> None` — claim SKIP LOCKED batch of 10 from `rag_indexing_outbox WHERE status='pending'`; call embedding for each; mark `status='done'`; on fail: `retry_count++`, `last_error=str(e)`; after 3 retries mark `status='failed'` (halts embedding, content still visible).
- **Done when:** Outbox rows transition from pending → done after worker runs.
- **Test:** `pytest tests/integration/worker/test_rag_outbox_loop.py`
- **Depends on:** T4.3, T2.1

##### T7.5 [backend]: Heartbeat — `worker/heartbeat.py`
- **Build:** `async def heartbeat_loop(repo) -> None`:
  - On startup: delete stale rows `WHERE last_seen < NOW() - INTERVAL '5min'` (stale workers from previous run)
  - `UPSERT worker_heartbeats SET last_seen=NOW(), job_id=current_job_id WHERE worker_id=hostname` every 10s
- **Done when:** After 10s, `GET /api/admin/system/workers` shows this worker as active.
- **Test:** `pytest tests/unit/worker/test_heartbeat.py` — mock repo; assert upsert called every 10s with hostname.
- **Depends on:** T4.3, T2.1

##### T7.6 [backend]: Worker entrypoint — `worker/__main__.py` + prompt files
- **Build:**
  - `src/worker/__main__.py`: `asyncio.gather(extraction_loop(...), purge_loop(...), rag_outbox_loop(...), heartbeat_loop(...))` — concurrent tasks; graceful `SIGTERM` handler: cancel all tasks, wait up to 5s
  - Startup validation: if `EXTRACTION_MODEL_SPEC` missing → `sys.exit(1)` with message; if `STORAGE_ROOT` missing → `sys.exit(1)`
  - `prompts/contents_prompt.md`: copy verbatim from `../haiguru/glm_ocr/prompts/` (or equivalent). Purpose: extract teaching content as markdown with H1/H2 structure.
  - `prompts/exercises_prompt.md`: copy verbatim from `../haiguru/glm_ocr/prompts/`. Purpose: extract questions + answers as structured JSON (used in Phase 1d-real-2; `exercises` job type column already wired).
  - `python -m haisir.worker` entrypoint in `pyproject.toml` or `setup.cfg`
- **Done when:** `python -m haisir.worker` starts without errors when `EXTRACTION_MODEL_SPEC` and `STORAGE_ROOT` are set. `SIGTERM` shuts down within 5s.
- **Test:** `pytest tests/unit/worker/test_main.py` — mock all loops; assert SIGTERM triggers graceful shutdown; assert startup validates env vars.
- **Depends on:** T7.1, T7.2, T7.3, T7.4, T7.5

**G7 integration test:** End-to-end: seed `pending` job with real PDF fixture → start worker loops for 10s → assert `topic_contents` rows created (N = PDF page count) + `extraction_job_audit` row + `extraction_job_pages` empty + job `status='done'`. Run with mocked LLM provider (returns fixed markdown).

---

### G8 [frontend]: CSRF + FormData gate (blocking for G9, G10, G11, G12)

**Purpose:** `fetchWithCSRFRetry` must work correctly with FormData. If this breaks, multipart upload silently sends empty bodies on CSRF retry. Must pass as CI gate before any modal code is written.

##### T8.1 [frontend]: CSRF + FormData integration test
- **Build:** Add test to `src/__tests__/integration/csrf-formdata.test.ts`. Verify:
  1. First request with stale CSRF token → mock returns 403 → `fetchWithCSRFRetry` fetches new CSRF token
  2. Retry uses **new FormData instance** with identical file content (the original `body` is a consumed stream after first send — must be re-created, not re-sent)
  3. Retry sends correct new CSRF token in `X-CSRF-Token` header
  4. File content is identical in first and second attempts (not empty on retry)
  - Implementation fix (if needed): in `fetchWithCSRFRetry`, if request body is FormData, accept a `bodyFactory: () => FormData` callback instead of a FormData instance, so the factory is called fresh on each attempt. Update all callers that pass FormData to pass a factory.
- **Done when:** Test passes in CI; `fetchWithCSRFRetry` with FormData sends correct file content after CSRF retry.
- **Test:** Jest test with MSW interceptors simulating 403 then 200; assert file content bytes identical.
- **Depends on:** None

**G8 integration test:** THIS IS the integration test. CI gate: G9, G10, G11, G12 work MUST NOT start until T8.1 is green in CI.

---

### G9 [frontend]: Add Content modal rebuilt

**Purpose:** Replace the existing `AddContentModal` (text/video only) with a file-upload-capable version. Reuse existing `TopicContent` type with extension.

##### T9.1 [frontend]: Extraction types + API layer
- **Build:**
  - **Extend** (not replace) `TopicContent` type: add `source_extraction_job_id?: string | null` and `provenance?: { source_filename: string; page_no: number } | null`
  - New types: `ExtractionJobStatus = 'pending' | 'extracting' | 'done' | 'upload_failed' | 'extraction_failed' | 'cancelled' | 'uploading'` (note: `'uploading'` is frontend-only pseudo-state); `ExtractionJob` matching GET list response shape (id, status, source_filename, pages_total, pages_completed, progress, source_size_bytes, started_at, estimated_cost_usd, created_at, error_message?)
  - New file `src/features/admin/api/extraction-api.ts`:
    - `createExtractionJob(topicId, file, idempotencyKey, csrfFactory, xCurrentRole)` → `fetchWithCSRFRetry` with FormData factory (per T8.1 fix); returns `ExtractionJob`
    - `listExtractionJobs(topicId, etag, xCurrentRole)` → `GET` with `If-None-Match`; returns `{ jobs, etag } | null` (null on 304)
    - `cancelExtractionJob(jobId, xCurrentRole, csrfFactory)` → DELETE
    - `retryExtractionJob(jobId, idempotencyKey, xCurrentRole, csrfFactory)` → POST
    - `listAdminWorkers()` → GET `/api/admin/system/workers`
- **Done when:** All API functions have MSW mock tests passing. `ExtractionJob` type compiles without errors.
- **Test:** `pytest tests/unit/api/test_extraction_api.ts` with MSW — each function tested for happy path + 4xx error propagation.
- **Depends on:** T8.1, T5.1 [backend], T5.2 [backend], T5.4 [backend], T5.5 [backend]

##### T9.2 [frontend]: useExtractionJobs hook — `hooks/use-extraction-jobs.ts`
- **Build:** `useExtractionJobs(topicId: string)` hook (separate from existing `useTopicContents`):
  - State: `jobs: (ExtractionJob | PseudoJob)[]` — merged list; `PseudoJob` is an in-memory-only object with `status: 'uploading', progress: number, filename: string, id: string` (temp UUID)
  - `addPseudoJob(filename, size)` — push to in-memory state
  - `replacePseudoJob(tempId, realJob)` — called on 201 response
  - `markPseudoJobFailed(tempId, errorMsg)` — called on upload error
  - Polling: `setInterval` at 2s while any job is `pending` or `extracting`; backoff to 10s when all done; stop after 60s of all-done; sends `If-None-Match` header; on 304 no state update (no flash)
  - `cancelJob(jobId)`, `retryJob(jobId)` actions
  - On any job reaching `done`: call `onJobDone()` callback (parent passes `() => invalidate(["admin","topic-contents",topicId])` to refresh content list)
- **Done when:** Hook starts polling on mount; stops after 60s of idle; pseudo-job lifecycle works (add → replace on 201 → fail on error).
- **Test:** `tests/unit/hooks/use-extraction-jobs.test.ts` — fake timers; mock API; assert polling intervals; pseudo-job replacement.
- **Depends on:** T9.1

##### T9.3 [frontend]: Rebuild AddContentModal
- **Build:** REPLACE existing `AddContentModal` (which currently handles `mode: 'create' | 'edit'` for video/text). New version:
  - Type chips: PDF / Image(s) / Video URL / Text (note: existing create/edit for Video/Text retained)
  - For PDF / Image chips:
    - Drag-drop zone (`ondragover` + `ondrop`) + "Browse" button → hidden `<input type="file" accept=".pdf,image/*" multiple>`
    - File list: each row shows filename, size (human-readable), remove button. Max 10 files enforced client-side.
    - Cost preview heuristic: `estimated_pages = file_size_bytes / 50_000`; `estimated_cost = estimated_pages * 0.03`; show "Est. $X.XX–$Y.YY". If estimate > $2.00: show confirmation checkbox "I understand this may cost ~$X" (required to enable Upload button).
    - Upload button label: "Upload N PDF(s)" or "Upload N Image(s)"
    - **On Upload click: modal closes immediately** (BR-EXT-019, no waiting for response)
    - For each file: call `addPseudoJob(filename, size)`, then fire parallel `createExtractionJob(...)` (with `crypto.randomUUID()` as idempotency key)
    - On 201: `replacePseudoJob(tempId, realJob)`; on error: `markPseudoJobFailed(tempId, error)`
  - For Video / Text chips: retain existing instant-creation behaviour (`useCreateTopicContent`) unchanged
  - Edit mode (existing): `mode='edit'` still opens a title+body editor for materialized rows; type selector disabled
  - Provenance line in edit mode: if `initialValues.source_extraction_job_id` is set, show `"✨ Extracted from {initialValues.provenance.source_filename} · page {initialValues.provenance.page_no}. Edits don't affect the audit record."` at top of modal
- **Done when:** Drop 2 PDFs → Upload → modal closes immediately → 2 pseudo-jobs appear on topic card (T10.2 required). Video/Text creation still works unchanged.
- **Test:** `tests/unit/components/add-content-modal.test.tsx` — file drop; cost preview; Upload closes modal; confirm checkbox shown for >$2; video/text path unchanged.
- **Depends on:** T9.2, T8.1

**G9 integration test:** Playwright `tests/e2e/content-upload-modal.spec.ts` — drop 2 PDFs → modal closes → pseudo-jobs appear on topic card. (requires T10.2)

---

### G10 [frontend]: Topic card jobs strip

**Purpose:** The topic card is the single source of truth for all extraction state after the modal closes.

##### T10.1 [frontend]: ExtractionJobRow component
- **Build:** New `src/features/admin/components/extraction-job-row.tsx`:
  - Props: `job: ExtractionJob | PseudoJob`, `onCancel: (jobId: string) => void`, `onRetry: (jobId: string) => void`
  - For pseudo-job (`status='uploading'`): show spinner + filename + "Uploading X%" progress bar
  - For real job `pending`: "Queued" pill + filename + Cancel button
  - For `extracting`: "Extracting" pill + filename + progress bar (pages_completed/pages_total) + Cancel button
  - For `extraction_failed`: "Failed" pill + filename + error_message (truncated) + Retry button
  - For `upload_failed`: "Upload Failed" pill + filename + error_message + (no retry — must re-upload)
  - For `cancelled`: "Cancelled" pill + filename (greyed out, 24h then disappears)
  - For `done`: rendered but hidden (strip hides done rows after brief flash)
- **Done when:** All status variants render without errors; callbacks fire with correct jobId.
- **Test:** `tests/unit/components/extraction-job-row.test.tsx` — render each status variant; cancel/retry callbacks.
- **Depends on:** T9.1

##### T10.2 [frontend]: Extend TopicRow with IN PROGRESS strip
- **Build:** Extend existing `TopicRow` component:
  - Call `useExtractionJobs(topic.id)` inside `TopicRow`, passing `onJobDone: () => invalidateTopicContents(topic.id)` callback
  - Add `.tc-jobs` section above the existing content section (`.tc-content`):
    - Only shown when `jobs.length > 0`
    - Header: "IN PROGRESS" label (admin accent color)
    - Render `ExtractionJobRow` for each job
  - Wire `AddContentModal`'s upload actions into `useExtractionJobs` (pass `addPseudoJob`, `replacePseudoJob`, `markPseudoJobFailed` down or via context)
  - On `onJobDone`: call `queryClient.invalidateQueries(['admin','topic-contents',topic.id])` to refresh content section
- **Done when:** Upload 2 PDFs → topic card shows IN PROGRESS strip with 2 rows; after worker completes → strip disappears + content section shows new rows.
- **Test:** `tests/unit/components/topic-row.test.tsx` — mock `useExtractionJobs` with active jobs; assert strip renders; mock done event; assert invalidation called.
- **Depends on:** T10.1, T9.2, T9.3

**G10 integration test:** Playwright `tests/e2e/topic-card-strip.spec.ts` — MSW mock job status transitions `pending → extracting → done`; assert strip progresses and disappears; content list refetched.

---

### G11 [backend + frontend]: Provenance + editing affordances

**Purpose:** Extracted rows must show permanent provenance badges and support two edit paths, without ever losing `source_extraction_job_id`.

##### T11.1 [backend]: PATCH regression guard — `source_extraction_job_id` never cleared
- **Build:** In `src/infrastructure/repositories/topic_content_repository.py`, audit the `update_platform_content` (and equivalent parent method) UPDATE statement. The current implementation strips `None` fields before updating — verify that `source_extraction_job_id` is **not in the update dict** and cannot be overwritten. If the UPDATE uses `SET column = :value` for every column in `TopicContentUpdate`, it will leave `source_extraction_job_id` untouched (column not in schema). Add explicit assertion in the infra repo: `assert 'source_extraction_job_id' not in update_dict, "source_extraction_job_id must not be cleared by PATCH"` — this fires at dev time if future code mistakenly adds the field to the update schema.
- **Done when:** `pytest tests/integration/repositories/test_topic_content_repository.py::test_patch_preserves_provenance` — create `topic_contents` row with `source_extraction_job_id` set; call `update_platform_content` with title change; assert `source_extraction_job_id` unchanged.
- **Test:** The regression test itself is the test.
- **Depends on:** T2.1 [backend]

##### T11.2 [backend]: Extend GET /api/topic-contents response with provenance
- **Build:** Extend `TopicContentRead` schema to include:
  - `source_extraction_job_id: UUID | None`
  - `provenance: {"source_filename": str, "page_no": int} | None` — resolved via JOIN `topic_contents → extraction_job_audit ON topic_contents.source_extraction_job_id = extraction_job_audit.job_id`; null for manual rows
  - Update `get_by_topic` service + infra repo to include LEFT JOIN to `extraction_job_audit` in the query
  - Note: `extraction_job_audit` survives purge of `extraction_jobs` row, so this JOIN always resolves while the `topic_contents` row exists
- **Done when:** GET `/api/topic-contents/{topicId}` returns `provenance: {"source_filename": "chapter1.pdf", "page_no": 1}` for extracted rows; `provenance: null` for video/text rows.
- **Test:** `pytest tests/integration/api/test_topic_contents.py::test_get_returns_provenance` — seed extracted row + audit row; assert provenance in response.
- **Depends on:** T11.1, T2.1

##### T11.3 [frontend]: Extend ContentItemRow + editing affordances
- **Build:** Extend existing `ContentItemRow` component:
  - If `item.provenance` is set: show provenance badge `"✨ from {source_filename} · p.{page_no}"` on meta line (`.cr-prov` CSS class per prototype). Badge tooltip: `"Edits don't affect the audit record"`. Badge visible even after admin edits title/body.
  - **Inline title rename:** Click on title text → `<span contenteditable="true">` activates; Enter key → `useUpdateTopicContent({title: newTitle})` → PATCH request; Esc → revert; empty title → revert. Sends `{title}` only (not body).
  - **Edit button** → open `AddContentModal` in `mode='edit'` with `initialValues=item`. Edit modal shows provenance line at top for extracted rows. Save sends `{title, text}` or `{title, url}` via existing `useUpdateTopicContent`.
  - **Delete button** → `DeleteContentDialog` — confirm text updated to: "Delete this content? The extraction audit record will be preserved." (acknowledges BR-EXT-023 to admin)
- **Done when:** Extracted row shows badge; click title → editable; Edit modal shows provenance line; Delete confirms with audit message.
- **Test:** `tests/unit/components/content-item-row.test.tsx` — render with provenance; assert badge text; assert inline edit saves on Enter, reverts on Esc, reverts on empty; assert Edit modal opens.
- **Depends on:** T11.2 [backend], T10.2 [frontend]

**G11 integration test:** Playwright `tests/e2e/content-provenance.spec.ts` — extracted row shows badge; inline rename → badge still present after save; Edit modal shows provenance line; delete confirm shows audit message.

---

### G12 [frontend]: Worker health page

**Purpose:** Admins need visibility into whether workers are running. Shows liveness based on `worker_heartbeats` (BR-EXT-031).

##### T12.1 [frontend]: Admin system/workers page
- **Build:** New page `src/app/(admin)/system/workers/page.tsx`:
  - Calls `listAdminWorkers()` on mount; auto-refreshes every 30s
  - Table: hostname, started_at, last_seen (relative time), current job_id (if any), status pill (Active / Stale)
  - Stale = `is_stale: true` from API response
  - Shows: "0 active workers — extraction is paused" warning banner when no active workers
  - Add nav link in admin sidebar: "System → Workers" (admin role only)
- **Done when:** Page renders at `/admin/system/workers`; stale workers shown in red; auto-refreshes.
- **Test:** `tests/unit/pages/workers-page.test.tsx` — mock API with 1 active + 1 stale worker; assert pill colours.
- **Depends on:** T5.6 [backend], T9.1 [frontend]

**G12 integration test:** Playwright — health page shows live worker (seeded heartbeat); stale worker highlighted.

---

## ROOT acceptance test

Playwright full-flow `tests/e2e/extraction-full-flow.spec.ts`:
1. Admin logs in, navigates to a topic
2. Opens Add Content modal → drops a 2-page PDF
3. Clicks Upload → modal closes immediately
4. Topic card shows IN PROGRESS strip with 1 job in "Queued" state
5. MSW mocks job state `pending → extracting (pages_completed=1) → done`
6. Strip progress bar advances to 100% then disappears
7. Topic content section shows 2 new rows with provenance badges
8. Click row 1 title → inline rename → badge persists after save
9. Click Edit on row 2 → modal shows provenance line at top
10. Navigate to `/admin/system/workers` → worker shown as active

---

## Implementation Notes

**Backend pattern references (existing code to follow):**
- Oracle protection: `src/infrastructure/repositories/topic_repository.py` (JOIN on owner_type)
- Auth guards: `src/auth/permission.py` → `require_admin()`, `require_any_platform_role()`
- Route pattern: `src/api/routes/topic_content.py` (PATCH/DELETE handlers with CSRF)
- SQLAlchemy imperative: `src/infrastructure/repositories/*.py` (no Base subclassing, plain `Table()` + `mapper_registry`)

**Frontend pattern references (existing code to follow):**
- `fetchWithCSRFRetry`: `src/lib/fetch-with-csrf-retry.ts` — NOTE: must be extended per T8.1 for FormData body factory
- Hook pattern: `src/features/admin/hooks/use-topics.ts` (query + mutation + cache invalidation)
- Native dialog: `src/features/admin/components/add-board-modal.tsx` (no div modals, `useFocusTrap`)
- Existing content types in `AddContentModal`: `'video'` and `'text'` create paths must remain intact through rebuild

**Visual authority:** `target/prototypes/haisir_admin_flow.html` (Playwright-validated) — `.tc-jobs`, `.cr-name`, `.cr-prov`, `.cr-meta` CSS class names are canonical. `target/requirements/ui-mapping/ui_parent_institution_admin.md` § "SA-boards" for component state table.

**Key rules (must not be violated):**
- `content_type` immutable — never patchable after creation
- `source_extraction_job_id` NEVER overwritten by PATCH (BR-EXT-023a)
- No `'uploading'` status in DB — frontend-only pseudo-state
- Oracle protection = 404 for both "not found" AND "wrong owner" (never 403)
- 100% test coverage maintained in both repos
- `X-Current-Role` missing → 400 (not 403) per CLAUDE.md
- `Idempotency-Key` missing on POST → 400

<!-- plan-baseline: backend:e18508caa46148916f6c5f55a8e685a173fd9395 frontend:7633f198e5c3c1fcccf45ca59e79d0972039fb72 deploy:eea51520a266219ebac9641f9527a179bb6c931d -->
