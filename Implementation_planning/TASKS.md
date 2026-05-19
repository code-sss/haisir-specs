# Progress

> Auto-generated from PLAN.md. Updated by `/implement-deploy` in each code repo.
> Last baselined: backend:7dccbe6 frontend:f7d0a2a deploy:eea5152 (2026-05-14)

## G1 [deploy]: Worker service provisioned
- [x] T1.1 [deploy]: Add worker service to Docker Compose (replicas:2, env vars, depends_on) (2026-05-12)
- [x] T1.2 [deploy]: STORAGE_ROOT volume mount to api + worker (depends on T1.1) (2026-05-12)
- [ ] **G1: Worker service provisioned** — integration test: `docker compose ps` shows 2 worker containers

## G2 [backend]: Schema ready
- [x] T2.1 [backend]: Alembic migration V26 — 6 new tables + source_extraction_job_id column + all indexes (2026-04-30)
- [ ] **G2: Schema ready** — integration test: `alembic upgrade head && downgrade -1 && upgrade head` *(requires real DB — not run in CI yet)*

## G3 [backend]: Domain layer
- [x] T3.1 [backend]: Domain models — ExtractionJob, ExtractionJobPage, ExtractionJobAudit, RagIndexingOutbox, WorkerHeartbeat, ParentQuotaCounter dataclasses (2026-04-24)
- [x] T3.2 [backend]: Domain protocols — ExtractionProvider + PdfReader (2026-04-24)
- [x] T3.3 [backend]: ExtractionService — all 7 service methods with permission gates (depends on T3.1, T3.2) (2026-04-24)
- [ ] **G3: Domain layer** — integration test: `pytest tests/unit/services/test_extraction_service.py`

## G4 [backend]: Infrastructure layer
- [x] T4.5 [backend]: ExtractionSourceStorage.read() — add `async def read(self, path: str) -> bytes` to protocol (domain/protocols/extraction.py) and impl (infrastructure/storage/extraction_source.py); uses _resolve_safe + asyncio.to_thread(read_bytes); add unit test (depends on T4.4) (2026-05-07)
- [x] T4.1 [backend]: GlmOcrProvider — copy glm_ocr from haiguru; prefix-dispatch; streaming protocol (depends on T3.2) (2026-05-07)
- [x] T4.2 [backend]: PdfiumReader — pypdfium2 wrapping; extract_text, image_coverage, render, page_count (depends on T3.2) (2026-05-07)
- [x] T4.3 [backend]: ExtractionJobRepository — SQLAlchemy imperative; all methods including claim_next SKIP LOCKED (depends on T3.1, T2.1) (2026-04-30)
- [x] T4.4 [backend]: ExtractionSourceStorage — save_file with path-traversal guard; MIME sniff; delete_file; python-magic (depends on T3.1) (2026-04-30)
- [ ] **G4: Infrastructure layer** — integration test: SKIP LOCKED claim with 2 concurrent DB sessions

## G5 [backend]: Admin extraction API
- [x] T5.0 [deploy]: APISIX dedicated plugin config and route for multipart extraction upload (2026-05-04)
- [x] T5.1 [backend]: POST /api/admin/topics/{topic_id}/extraction-jobs — streaming multipart, MIME sniff, SHA dedup, idempotency, oracle 404, file save, INSERT job (depends on T4.3, T4.4, T3.3, T2.1) (2026-04-30)
- [x] T5.2 [backend]: GET /api/admin/topics/{topic_id}/extraction-jobs — ETag/304, derived progress (depends on T4.3, T2.1) (2026-04-30)
- [x] T5.3 [backend]: GET /api/admin/extraction-jobs/{job_id} — detail (depends on T4.3, T2.1) (2026-04-30)
- [x] T5.4 [backend]: DELETE /api/admin/extraction-jobs/{job_id} — hard cancel pending / soft cancel extracting (depends on T4.3, T4.4, T2.1) (2026-04-30)
- [x] T5.5 [backend]: POST /api/admin/extraction-jobs/{job_id}/retry — re-queue extraction_failed (depends on T4.3, T4.4, T2.1) (2026-04-30)
- [x] T5.6 [backend]: GET /api/admin/system/workers — worker liveness with is_stale flag (depends on T4.3, T2.1) (2026-04-30)
- [ ] **G5: Admin extraction API** — integration test: full API test suite including CSRF/header guard tests

## G6 [backend]: Parent extraction API
- [x] T6.1 [backend]: POST /api/parent/curriculum/topics/{topic_id}/extraction-jobs — with quota gate (depends on T4.3, T4.4, T3.3, T2.1) (2026-05-18)
- [x] T6.2 [backend]: GET /api/parent/curriculum/topics/{topic_id}/extraction-jobs — filtered to own jobs (depends on T4.3, T2.1) (2026-05-18)
- [x] T6.3 [backend]: GET /api/parent/curriculum/extraction-jobs/{job_id} — isolation (depends on T4.3, T2.1) (2026-05-18)
- [x] T6.4 [backend]: DELETE /api/parent/curriculum/extraction-jobs/{job_id} — cancel + quota decrement (depends on T4.3, T4.4, T2.1) (2026-05-18)
- [x] T6.5 [backend]: POST /api/parent/curriculum/extraction-jobs/{job_id}/retry — filtered by created_by (depends on T4.3, T4.4, T2.1) (2026-05-18)
- [ ] **G6: Parent extraction API** — integration test: quota 429 + cross-parent isolation

## G7 [backend]: Worker process
> **Pre-implementation gap resolved (2026-05-08):** `source_extraction_job_id` now exists in both `TopicContent` domain model and SQLAlchemy table mapping.
- [x] T7.1 [backend]: worker/extraction_loop.py — claim loop, extract_page routing, per-page staging, cancel check, cost cap (depends on T4.1, T4.2, T4.3, T4.4, T2.1) (2026-05-08)
- [x] T7.2 [backend]: worker/finalize.py — atomic TX: ownership re-validate, content_order base, INSERT N topic_contents, INSERT N rag_outbox, INSERT audit, DELETE pages, UPDATE job done (depends on T4.3, T2.1) (2026-05-08)
- [x] T7.3 [backend]: worker/purge_loop.py — hourly expired job purge + outbox cleanup (depends on T4.3, T4.4, T2.1) (2026-05-12)
- [ ] T7.4 [backend]: worker/rag_outbox_loop.py — **DEFERRED to haiguru repo**: outbox rows are written by finalize but drain is haiguru's concern; haisir worker does not implement this loop
- [x] T7.5 [backend]: worker/heartbeat.py — UPSERT every 10s + stale cleanup on startup (depends on T4.3, T2.1) (2026-05-12)
- [x] T7.6 [backend]: worker/__main__.py + prompt module — asyncio.gather all loops (T7.1/T7.2/T7.3/T7.5 only), SIGTERM handler, env validation (EXTRACTION__MODEL_SPEC required); prompt as src/worker/prompts.py Python constant (no haiguru copy needed) (depends on T7.1, T7.2, T7.3, T7.5) (2026-05-12)
- [ ] **G7: Worker process** — integration test: seed pending job → run worker → assert N topic_contents + audit row + job done

## G8 [frontend]: CSRF + FormData gate ⚠️ BLOCKING for G9–G12
- [x] T8.1 [frontend]: CSRF + FormData integration test — verify re-clone on retry; fix fetchWithCSRFRetry if needed (2026-04-24)
- [x] **G8: CSRF gate** — test IS the integration test; must pass in CI before G9 work starts (2026-04-24)

## G9 [frontend]: Add Content modal rebuilt
- [x] T9.1 [frontend]: ExtractionJob types + extraction-api.ts — createExtractionJob (FormData factory), listExtractionJobs (ETag), cancel, retry (depends on T8.1, T5.1 [backend], T5.2 [backend], T5.4 [backend], T5.5 [backend]) — done 2026-05-01
- [x] T9.2 [frontend]: useExtractionJobs hook — polling 2s/10s/stop-60s, pseudo-job state machine, onJobDone callback (depends on T9.1) — done 2026-05-02
- [x] T9.3 [frontend]: Rebuild AddContentModal — file drop zone, type chips, cost preview, Upload-closes-immediately, retain Video/Text create/edit (depends on T9.2, T8.1) — done 2026-05-02
- [ ] **G9: Add Content modal** — Playwright: drop 2 PDFs → modal closes → pseudo-jobs on topic card

## G10 [frontend]: Topic card jobs strip
- [x] T10.1 [frontend]: ExtractionJobRow component — all status variants, cancel/retry callbacks (depends on T9.1) — done 2026-05-05 (inline in topic-row.tsx)
- [x] T10.2 [frontend]: Extend TopicRow with IN PROGRESS strip + useExtractionJobs + onJobDone invalidation (depends on T10.1, T9.2, T9.3) — done 2026-05-05
- [ ] **G10: Topic card strip** — Playwright: mock job transitions → strip updates → content list refetched

## G11 [backend + frontend]: Provenance + editing
- [x] T11.1 [backend]: PATCH regression guard — assert source_extraction_job_id never overwritten; add test (depends on T2.1) (2026-05-18)
- [x] T11.2 [backend]: Extend GET /api/topic-contents — include provenance {source_filename, page_no} via audit JOIN (depends on T11.1, T2.1) (2026-05-18)
- [x] T11.3 [frontend]: Extend ContentItemRow — provenance badge, inline title rename, Edit modal provenance line, Delete audit message (depends on T11.2 [backend], T10.2 [frontend]) (2026-05-18)
- [ ] **G11: Provenance + editing** — Playwright: badge shows; inline rename preserves badge; Edit modal shows provenance line

## G12 [frontend]: Worker health page
- [x] T12.1 [frontend]: Admin /system/workers page — worker table, is_stale highlight, 30s auto-refresh, sidebar link (depends on T5.6 [backend], T9.1 [frontend]) (2026-05-13)
- [ ] **G12: Worker health page** — Playwright: active + stale workers rendered correctly

## G13 [deploy + backend]: WAF exclusion + URL validation for topic content
> **Context:** `POST /api/topics-contents/` accepts a `url` field for video links (e.g. YouTube). OWASP CRS rule 931130 ("RFI: Off-Domain Reference/Link") blocks any external URL in a POST body. Fix requires a scoped WAF exclusion in deploy **and** backend-side allowlist validation to prevent SSRF / stored XSS now that the WAF no longer blocks the field.
- [x] T13.1 [deploy]: Add Coraza rule exclusion to 03-secured-api.json — `ctl:ruleRemoveTargetById=931130;ARGS:url` scoped to `REQUEST_URI @beginsWith /api/topics-contents/`; reload APISIX plugin configs via release manifest (`apisix_plugins: true`) (2026-05-14)
- [x] T13.2 [backend]: Validate `url` field in `POST /api/topics-contents/` Pydantic schema — scheme must be `https`; hostname must be in allowlist (`youtube.com`, `www.youtube.com`, `youtu.be`, `vimeo.com`, `www.vimeo.com`); return HTTP 422 with clear error on failure; if URL is ever fetched server-side, apply same allowlist and disallow redirect chains to off-allowlist domains (2026-05-14)
- [ ] **G13: WAF exclusion + URL validation** — manual: `POST /api/topics-contents/` with `https://www.youtube.com/watch?v=xxx` returns 2xx; `http://...`, `javascript:...`, or any non-allowlisted domain returns 422; APISIX no longer blocks the request

## ROOT acceptance test
- [ ] **ROOT [e2e]: Full extraction flow** — Playwright: upload PDF → modal closes → strip → progress → done → content rows with provenance → inline rename → Edit modal provenance → health page

---

## Ready now
Tasks with no pending dependencies — can be started immediately in parallel:

*(none — all individual tasks complete; only Playwright gate tests and integration tests remain)*
