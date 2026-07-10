# Content Extraction (PDF / Image → Text)

> **Phase 1d-real scope.** Replaces the incomplete URL-only Add Content modal shipped in Phase 1d. Applies to Platform Admin and Parent personas.
>
> **Persistence model:** ONE PDF/image upload → N `topic_contents` rows with `content_type='text'`. The source PDF/image is **transient** (purged after retention window). No new `content_type` enum value is introduced. Confirmed by haiguru's `etl_pipeline/load.py:_load_contents` proof-of-concept.

---

## 1 — Architecture Overview

```
┌─────────────┐  multipart/form-data    ┌──────────────┐                    ┌────────────┐
│  Frontend   │───── POST upload ──────▶│  FastAPI     │── INSERT job ─────▶│ Postgres   │
│ (modal +    │                         │  (api proc)  │                    │            │
│  topic card)│◀─── 201 + job ──────────│              │                    │ extraction │
└─────────────┘                         └──────────────┘                    │ _jobs      │
       │                                                                    │ _pages     │
       │ poll GET /jobs every 2s                                            │ _audit     │
       ▼                                                                    │ rag_       │
┌─────────────┐                         ┌──────────────┐                    │ indexing_  │
│   Topic     │                         │  Worker      │── SKIP LOCKED ────▶│ outbox     │
│   card      │                         │  (worker     │                    │            │
│   (truth)   │                         │   proc)      │── glm_ocr ────────▶│ topic_     │
└─────────────┘                         │              │   pypdfium2        │ contents   │
                                        └──────────────┘                    └────────────┘
```

- **Same `haisir-backend` repo**, two process modes from the same Docker image:
  - `command: python -m haisir.api` (FastAPI)
  - `command: python -m haisir.worker` (job loop)
- **Worker count:** Docker compose `replicas: 2` from day one. The `FOR UPDATE SKIP LOCKED` pattern requires N≥2 to be meaningful.
- **No Redis, no ARQ, no Celery.** Postgres advisory queue only. Decision rationale: 5–10 admins, ~50–200 PDFs/week — no scale signal yet.

---

## 2 — Data Model

See `target/requirements/01_data_model.md` § "Schema Extensions (Phase 1d-real)" for column-level definitions. Summary:

| Table | Purpose | Lifetime |
|---|---|---|
| `extraction_jobs` | Working state of an active job | Purged after final-state TTL |
| `extraction_job_pages` | Per-page extracted markdown — staging for resume-after-crash | Deleted after job finalize succeeds |
| `extraction_job_audit` | Indefinite provenance record | **Never purged** |
| `rag_indexing_outbox` | Async embedding queue for new `topic_contents` | Deleted after embed succeeds |
| `worker_heartbeats` | Worker liveness for health endpoint | TTL 1h |
| `parent_quota_counters` | Application-layer rate gate (parent only) | Persistent |
| `topic_contents.source_extraction_job_id` | Provenance back-pointer (additive nullable column) | — |

---

## 3 — Job Lifecycle

```
                                  ┌─── upload_failed (file write/sniff/SHA fail before INSERT)
                                  │
client uploads ── POST /jobs ── → pending ── worker picks up ── extracting ──┬── done
                                                                              │
                                                                              ├── extraction_failed (page or finalize error)
                                                                              │
                                                                              └── cancelled (admin requested soft-cancel, worker honoured between pages)
```

**No `uploading` state in the DB enum.** HTTP transfer is client-side; no row exists before the multipart handler completes. The frontend renders a **client-side pseudo-job** in `status='uploading'` for upload progress; the pseudo-job is replaced by the real backend job (returned in 201) on success, or marked `upload_failed` on failure.

### State transitions

| From | To | Trigger | Allowed by |
|---|---|---|---|
| (none) | `pending` | POST handler successfully wrote file + SHA + INSERT | API |
| (none) | `upload_failed` | File write/MIME sniff/SHA dedup violation | API |
| `pending` | `extracting` | Worker picked up via `FOR UPDATE SKIP LOCKED` | Worker |
| `extracting` | `extracting` (heartbeat) | Per-page commit, refresh `locked_at` | Worker |
| `extracting` | `done` | All pages staged + finalize TX succeeded | Worker |
| `extracting` | `extraction_failed` | Per-page error or finalize error | Worker |
| `extracting` | `cancelled` | `cancel_requested=true` checked at page boundary | Worker |
| `pending` | `cancelled` | Admin DELETE before worker pickup | API |
| `extraction_failed` | `pending` | Admin POST /retry (within source retention window) | API |
| `upload_failed` | (none) | Admin DELETE | API |

### Final-state TTLs (purge clock starts at `finished_at`)

| Final status | `purge_at` offset | Reason |
|---|---|---|
| `done` | +7 days | Source no longer needed; content is materialized |
| `extraction_failed` | +30 days | Admin needs window to retry without re-uploading |
| `cancelled` | +24 hours | Admin made an explicit choice; no need to keep source |
| `upload_failed` | +7 days | Source already deleted; row kept for audit visibility |

**The `extraction_job_audit` row is NEVER purged.** It carries the provenance link from `topic_contents` back to the source filename indefinitely.

---

## 4 — API Contract

All endpoints require: APISIX-injected JWT, `X-Current-Role` header, CSRF token (`X-CSRF-Token`) for mutations, and `Idempotency-Key: <uuid>` header for POST.

### Platform Admin endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/api/admin/topics/{topic_id}/extraction-jobs` | Create one job per file (multipart, ≤50MB) | admin |
| `GET` | `/api/admin/topics/{topic_id}/extraction-jobs` | List active + recent jobs for a topic | admin |
| `GET` | `/api/admin/extraction-jobs/{job_id}` | Job detail | admin |
| `DELETE` | `/api/admin/extraction-jobs/{job_id}` | Cancel (hard for `pending`, soft-request for `extracting`) | admin |
| `POST` | `/api/admin/extraction-jobs/{job_id}/retry` | Re-queue a failed job using existing source | admin |
| `GET` | `/api/admin/system/workers` | Worker liveness (health) | admin |

### Parent endpoints (parity)

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/api/parent/curriculum/topics/{topic_id}/extraction-jobs` | Same as admin, with parent quota enforcement | parent |
| `GET` | `/api/parent/curriculum/topics/{topic_id}/extraction-jobs` | List active + recent jobs for a parent-owned topic | parent |
| `GET` | `/api/parent/curriculum/extraction-jobs/{job_id}` | Job detail | parent |
| `DELETE` | `/api/parent/curriculum/extraction-jobs/{job_id}` | Cancel | parent |
| `POST` | `/api/parent/curriculum/extraction-jobs/{job_id}/retry` | Retry | parent |

### POST request — multipart fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `file` | binary | yes | Single file per request. Client makes parallel requests for multi-file. |
| `job_type` | string | no | `"contents"` (default) or `"exercises"` (Phase 1d-real-2; column added now to avoid migration churn) |

### POST request — headers

| Header | Required | Notes |
|---|---|---|
| `Idempotency-Key` | yes | UUID. Replay returns the original 201 with the same job. Unique index on `(created_by, idempotency_key)`. |
| `X-Force-Reextract` | no | `"true"` bypasses (topic_id, source_sha256) dedup. New job is created; both linked in audit. |
| `X-CSRF-Token` | yes | Standard CSRF guard. **Frontend MUST verify `fetchWithCSRFRetry` re-clones FormData on retry — see BR-EXT-018.** |

### POST response

| Code | Body | Meaning |
|---|---|---|
| `201 Created` | Full job object | New job (or replay of an existing job by Idempotency-Key) |
| `400` | `{ "detail": "X-Current-Role header required" }` | Missing role header |
| `409` | `{ "detail": "...", "existing_job_id": "..." }` | SHA-256 already extracted on this topic. Bypass with `X-Force-Reextract: true`. |
| `413` | `{ "detail": "File exceeds 50 MB" }` | Streaming parser rejected before full buffer |
| `415` | `{ "detail": "Unsupported MIME type" }` | python-magic sniff (first 8KB) rejected |
| `422` | `{ "detail": [...] }` | Other validation errors |
| `429` | `{ "detail": "..." }` | Quota exceeded (parent only) |

### GET list response

```json
{
  "jobs": [
    {
      "id": "...",
      "topic_id": "...",
      "status": "extracting",
      "source_filename": "chapter1.pdf",
      "source_size_bytes": 4_200_000,
      "source_type": "pdf",
      "job_type": "contents",
      "pages_total": 14,
      "pages_completed": 8,
      "progress": 57,
      "started_at": "2026-04-23T10:15:30Z",
      "estimated_cost_usd": 0.42
    }
  ]
}
```

- `progress` is **derived** (`pages_completed * 100 / NULLIF(pages_total, 0)`); not stored.
- `ETag: "<MAX(updated_at)>"` returned. Frontend sends `If-None-Match` → `304 Not Modified` when unchanged.
- Polling backoff (frontend): 2s while active, 10s when none active, stop after 60s of all-done.

---

## 5 — Worker Behaviour

> **Storage read contract:** The worker loads source file bytes via `await storage.read(job.source_path)` before passing them to pypdfium2 or the vision LLM. `ExtractionSourceStorage` protocol exposes `async def read(self, path: str) -> bytes` in addition to `save`, `exists`, and `delete`. Raises `ValueError` on path traversal.

```python
# Pseudocode — see haisir-backend/src/worker/extraction_loop.py
while True:
    sleep(2)
    write_heartbeat()
    purge_expired_jobs()  # hourly, gated by simple in-memory clock
    drain_rag_outbox()    # one batch of 10

    job = SELECT * FROM extraction_jobs
          WHERE (status='pending'
                 OR (status='extracting' AND locked_at < NOW()-INTERVAL '5min'))
          ORDER BY created_at
          FOR UPDATE SKIP LOCKED
          LIMIT 1

    if not job: continue

    UPDATE job SET status='extracting', locked_at=NOW(),
                   locked_by=HOSTNAME, started_at=COALESCE(started_at, NOW())

    pages = enumerate_pages(job)  # pypdfium2 for PDF; [single_image] for image

    # Resume from last staged page
    resume_from = SELECT MAX(page_no) FROM extraction_job_pages WHERE job_id=:job
    for page_no, page_data in pages[resume_from+1:]:
        if SELECT cancel_requested FROM extraction_jobs WHERE id=:job:
            UPDATE job SET status='cancelled', finished_at=NOW(), purge_at=NOW()+'24h'
            return

        try:
            md = extract_page(job, page_no, page_data)  # native text or vision LLM
            INSERT INTO extraction_job_pages (job_id, page_no, markdown_text, sha)
                VALUES (:job, :n, :md, :sha)
            UPDATE job SET pages_completed=:n, locked_at=NOW(),
                           updated_at=NOW(), running_cost_usd = :running
        except Exception as e:
            UPDATE job SET status='extraction_failed', error_message=str(e),
                           finished_at=NOW(), purge_at=NOW()+'30d'
            return

        if running_cost_usd > MAX_PER_JOB_USD:
            UPDATE job SET status='extraction_failed',
                           error_message='per-job cost cap exceeded'
            return

    finalize(job)  # see below
```

### `extract_page` routing

```
if source_type == 'image':
    return glm_ocr.process(image=page_data, prompt=prompt_for(job_type))

# source_type == 'pdf'
text = pypdfium2.extract_text(page_data)
image_area_ratio = pypdfium2.image_coverage(page_data)
if len(text) >= 50 and image_area_ratio < 0.95:
    if settings.extraction.restructure_text:
        restructured = provider.restructure_page(text)  # text-only LLM — fix fragmentation
        return restructured if restructured.strip() else text  # fallback to raw on empty
    return text  # native — no LLM (EXTRACTION__RESTRUCTURE_TEXT=false)
else:
    rendered = pypdfium2.render(page_data, scale=2)  # raster JPG
    return glm_ocr.process(image=rendered, prompt=prompt_for(job_type))
```

### `prompt_for(job_type)`

| `job_type` | Prompt file | Purpose |
|---|---|---|
| `contents` | `haisir-backend/prompts/contents_prompt.md` | Extract teaching content (markdown with H1/H2 structure) |
| `exercises` | `haisir-backend/prompts/exercises_prompt.md` | **Phase 1d-real-2.** Extract questions + answers as structured JSON. Out of scope for v1; column exists to avoid future migration. |

Both prompt files are copied verbatim from `../haiguru/glm_ocr/`.

---

### `restructure_page(raw_text)` — text-only LLM pass

Called on native-text PDF pages when `EXTRACTION__RESTRUCTURE_TEXT=true` (default). No image involved — this is a text-only LLM call using `EXTRACTION__RESTRUCTURE_MODEL_SPEC` (lighter model preferred over the vision model).

**Prompt** (stored in `haisir-backend/prompts/restructure_prompt.md`):

```
The text below was extracted from a PDF page (educational content).
The extraction may be fragmented: fractions may be split across lines, words may be
broken, and spacing or layout context may be lost.

Rewrite the text as clean, readable Markdown following these rules:
- Reassemble fractions: if a number sits alone on a line and the next line is also a
  lone number, they form a fraction — write them as numerator/denominator (e.g. 3
  then 4 → 3/4).
- Use ## for the page/section title, ### for sub-sections.
- Use numbered lists (1. 2. 3.) for questions, lettered sub-lists (a. b. c.) for parts.
- Preserve every number, symbol (≡ = < > ± × ÷ →), and word exactly — do NOT
  paraphrase, summarise, or add anything.
- Output ONLY the Markdown — no explanation, no code fences.

Extracted text:
---
{raw_text}
---
```

**Fallback**: if the LLM returns an empty response, `extract_page` returns the raw extracted text unchanged. This ensures native text extraction can never produce an empty page result.

**Two-model config**: `GlmOcrProvider` accepts an optional `restructure_model_spec` parameter. When set, text-only calls (`restructure_page`) use this spec; vision calls (`process`) use the primary `model_spec`. In `ExtractionSettings`:

| Env var | Default | Purpose |
|---|---|---|
| `EXTRACTION__RESTRUCTURE_TEXT` | `true` | Enable/disable the restructure pass (set `false` to skip LLM entirely for native-text pages) |
| `EXTRACTION__RESTRUCTURE_MODEL_SPEC` | `""` (falls back to `EXTRACTION__MODEL_SPEC`) | Separate, lighter text-only model for restructuring. E.g. `qwen3.5:9b`, `qwen3:8b`. |

### `finalize(job)` — single transaction

```sql
BEGIN;

-- Re-validate ownership (challenger #6)
SELECT owner_type, owner_id FROM topics WHERE id = :job.topic_id FOR UPDATE;
-- For platform jobs: assert owner_type='platform'
-- For parent jobs:   assert owner_type='parent' AND owner_id = :job.created_by
-- Mismatch → status='extraction_failed', error='ownership_violation', ROLLBACK

-- Compute order base (challenger #5)
SELECT COALESCE(MAX(content_order), 0) AS base
  FROM topic_contents WHERE topic_id = :job.topic_id;

-- Read all staged pages
SELECT page_no, markdown_text FROM extraction_job_pages
  WHERE job_id = :job ORDER BY page_no;

-- Materialize content rows
INSERT INTO topic_contents
  (id, topic_id, content_type, title, text, content_order, source_extraction_job_id)
VALUES
  (uuid(), :topic, 'text', :title, :md, :base + page_no, :job),
  ...
RETURNING id;

-- Outbox for async embedding (challenger #3)
INSERT INTO rag_indexing_outbox (content_id, status) VALUES (:returned_id, 'pending'), ...;

-- Audit (indefinite)
INSERT INTO extraction_job_audit
  (job_id, topic_id, idp_sub, source_filename, source_sha256, model_spec_used,
   finished_at, page_count, status)
VALUES (...);

-- Cleanup staging
DELETE FROM extraction_job_pages WHERE job_id = :job;

-- Mark job done
UPDATE extraction_jobs
  SET status='done', finished_at=NOW(), purge_at=NOW()+INTERVAL '7 days'
  WHERE id = :job;

COMMIT;
```

### Title derivation

For each extracted page markdown, parse the first H1 (`# Foo`); use as title. Fallback: `"Page N — {source_filename}"`.

**No upload-time title input for PDF/image** — one upload becomes N rows, so a single user-typed title cannot map cleanly. The filename is the upload-level identifier (carried in the provenance badge); page-level titles are auto-derived and editable post-hoc. Video and Text content types DO accept an optional/required title at upload (1 upload → 1 row).

### Editing materialized rows

After materialization, every `topic_contents` row supports two edit affordances:

| Affordance | Trigger | Scope | Persistence |
|---|---|---|---|
| **Inline title rename** | Click on title text in the content row | Title only | `PATCH /api/topic-contents/{id}` with `{title}` |
| **Full editor modal** | Click the row’s **Edit** button | Title + body (markdown for text, URL for video) | `PATCH /api/topic-contents/{id}` with `{title, body}` |

**Provenance is preserved across edits.** `topic_contents.source_extraction_job_id` is never cleared by an edit. The badge "Extracted from `chapter1.pdf` · page 3" continues to display, signalling "this row originated from extraction even though an admin has rewritten it". This is essential for traceability when LLM extraction errors are corrected.

**Delete preserves audit.** `DELETE /api/topic-contents/{id}` removes the row but does NOT cascade to `extraction_job_audit` (BR-DATA-010). The audit retains "this job extracted N pages on date X" indefinitely.

### Outbox handoff — re-ingestion contract (Phase 5)

The extraction finalize TX (above) is one of three producers into `rag_indexing_outbox`. Instant text-content create (`POST /api/topic-contents` with `content_type='text'`) and edits to a `text` row's `title`/`text` (`PATCH /api/topic-contents/{id}`) enqueue the same way. All three share one repository helper and one worker cleanup path, so the lifecycle is identical regardless of how the content was created.

**Upsert-with-reset (BR-DATA-020).** The enqueue helper is `ON CONFLICT (content_id) DO UPDATE`, not a bare `INSERT`:

```sql
INSERT INTO rag_indexing_outbox (content_id, status)
VALUES (:content_id, 'pending')
ON CONFLICT (content_id) DO UPDATE
  SET status = 'pending', retry_count = 0, last_error = NULL,
      locked_at = NULL, locked_by = NULL;
-- updated_at is NOT in the SET list — trg_rag_outbox_touch (V26) stamps it.
```

This is required because the purge sweep only clears `status='done'` rows after 24h — a same-day edit to a row that already embedded successfully would otherwise collide on the `content_id` primary key. A plain `INSERT` would fail; the upsert instead resets the row to `pending` so the worker re-drains it. Non-text content types (`video`, `url`) are never enqueued — only `text` rows carry embeddable body content.

**Worker delete-before-insert (BR-DATA-021).** `worker/rag_outbox_loop.py::_process_row` deletes the existing chunk set for `content_id` before calling `index.insert_nodes()`:

```python
# _process_row(row) — see worker/rag_outbox_loop.py
DELETE FROM data_topic_content_chunks WHERE metadata_->>'content_id' = :content_id  # raw SQL, LlamaIndex-owned table
index.insert_nodes(build_nodes(row.content_id, latest_text, latest_title))
_write_status(row, 'done')  # guarded: UPDATE ... WHERE status='processing' AND locked_by=:host
```

`data_topic_content_chunks` has no update-in-place path, so every drain — first embed or re-embed after an edit — deletes then inserts. This makes re-draining a `content_id` that already has chunks idempotent (no duplicate vectors), and also makes retry-after-partial-insert safe (a half-written chunk set from a crashed worker is deleted, not left to accumulate alongside the retry's new set).

`_write_status`'s `expected_locked_by` guard exists for the same reason a delete-first design needs care: if a content edit re-enqueues a row (upsert-with-reset, above) while a stale worker still holds a finalize write in flight for the *previous* text, that stale write is dropped instead of overwriting the fresh `pending` status — the row re-drains with the new text on the next pass.

**Accepted v1 gap — brief retrieval window.** Between the delete and the insert, a concurrent hAITU retrieval against that `content_id` sees zero chunks (not the old set, not the new set) for the duration of one worker batch. This is an availability gap, not a correctness gap: no duplicate or orphaned vectors are ever visible, and the window is bounded by one `insert_nodes()` call. Accepted for v1 — parent-authored edits are low-frequency and the gap is not user-visible in the UI (content shows as "indexing" via the outbox row, not "gone"). Locked decision; see `decisions.md` 2026-07-02.

**Delete-path cleanup.** `DELETE /api/topic-contents/{id}` on an embedded row deletes both the chunk set and the outbox row in the same TX as the content delete (not left for the worker to drain):

```sql
DELETE FROM data_topic_content_chunks WHERE metadata_->>'content_id' = :cid;
DELETE FROM rag_indexing_outbox WHERE content_id = :cid;
```

Topic delete and `course_path_nodes` subtree delete (parent and admin paths) run this same cleanup for every `content_id` under the deleted subtree, inside the cascade TX (BR-DATA-022) — no orphaned chunks or outbox rows survive their owning topic.

---

## 6 — Frontend Behaviour

### Add Content modal (rebuilt)

- Native `<dialog>`, 560 px wide.
- Type chip selector: PDF / Image(s) / Video URL / Text.
- For PDF / Image: drag-drop zone + click-to-browse, file list with size + remove buttons. **Max 10 files per submission.**
- "Upload N PDFs" button disabled until ≥1 file added; estimated cost band shown next to button (e.g. "Est. $0.50–$2.00"). For estimates >$2: confirmation checkbox required.
- On click: **modal closes immediately**. For each file:
  1. Frontend pushes a client-side pseudo-job onto `topic.jobs` with `status='uploading', progress=0` (UI only).
  2. Parallel `POST /api/admin/topics/{id}/extraction-jobs` requests with `Idempotency-Key`.
  3. On 201: pseudo-job replaced by real job (`status='pending'`).
  4. On error: pseudo-job updated to `status='upload_failed'` with retry button.
- For Video / Text: existing behaviour (instant `topic_contents` row creation via `POST /api/topic-contents`); modal closes after success.

### Topic card — IN PROGRESS strip

- Single source of truth for all job state (upload progress + extraction progress).
- Polls `GET /api/admin/topics/{id}/extraction-jobs` every 2s while any job is in `pending` or `extracting`.
- Backoff to 10s when no active jobs; stop polling after 60s of all-done.
- Sends `If-None-Match` for ETag-based 304s.
- Shows per-job: filename, page count, progress bar with status pill (Queued / Uploading X% / Extracting / Failed), Cancel button (always visible; sets `cancel_requested=true` for `extracting`), Retry button (for `extraction_failed`).
- On `done`: job row removed from strip; topic content list refetched (or new rows merged into local state).

### Provenance display

- `topic_contents` rows with `source_extraction_job_id IS NOT NULL` show a small badge: "✨ from `{source_filename}` · p.`{n}`" inline on the meta line.
- Filename + page resolved via JOIN with `extraction_job_audit`.
- Badge persists after admin edits the row (badge tooltip: "Edits don’t affect the audit record").

### Editing materialized rows (frontend)

- **Click on title** → inline contenteditable; Enter saves, Esc reverts. Empty value reverts. Sends `PATCH /api/topic-contents/{id}` with `{title}` only.
- **Edit button** → full editor modal (title input + markdown textarea / URL input for video). Save sends `PATCH /api/topic-contents/{id}` with `{title, body}`. Modal shows the provenance line at the top so admins know they are editing extracted content.
- **Delete button** → confirm dialog mentioning that audit record is preserved.

---

## 7 — Business Rules

### General

- **BR-EXT-001** — A job is created per file. Multi-file uploads are N parallel POST calls from the client, not N files in one POST.
- **BR-EXT-002** — Hard cap: 50 MB per file. Enforced via streaming multipart parser; reject before fully buffering.
- **BR-EXT-003** — Hard cap: 10 files per modal submission. Enforced client-side; server has no per-batch concept.
- **BR-EXT-004** — File MIME type sniffed from first 8 KB via python-magic. Whitelist: `application/pdf`, `image/png`, `image/jpeg`, `image/webp`. HEIC/HEIF out of scope v1.
- **BR-EXT-005** — `Idempotency-Key` header is required on POST. Replay (same `created_by` + same key) returns the original 201 unchanged.
- **BR-EXT-006** — Per-(topic_id, source_sha256) dedup. Same hash on same topic → 409. Bypass with `X-Force-Reextract: true`.

### Job execution

- **BR-EXT-007** — Worker uses `FOR UPDATE SKIP LOCKED` to claim jobs. Lease is 5 minutes (refreshed via heartbeat per page). Expired leases are reclaimable by other workers.
- **BR-EXT-008** — On worker death mid-extraction, another worker resumes from `MAX(page_no)+1` of staged pages. **No LLM-token waste from re-extraction.**
- **BR-EXT-009** — Native PDF text extraction skips the vision LLM (heuristic: text length ≥50 chars AND image area ratio <0.95). Scanned PDFs and all images go through the vision LLM. When `EXTRACTION__RESTRUCTURE_TEXT=true`, the text path still calls `restructure_page()` via a text-only LLM (BR-EXT-032).
- **BR-EXT-032** — When native PDF text extraction returns ≥50 chars and image coverage <0.95, and `EXTRACTION__RESTRUCTURE_TEXT=true` (default `true`), the worker passes the raw text through `provider.restructure_page()` before staging it. This corrects fragmentation artefacts common in educational PDFs: fractions split across lines, broken words, and layout ordering lost during text extraction. The method uses a text-only LLM call (no image). If the LLM returns an empty response, the raw extracted text is used unchanged.
- **BR-EXT-033** — `restructure_page()` uses `EXTRACTION__RESTRUCTURE_MODEL_SPEC` if set; falls back to `EXTRACTION__MODEL_SPEC` otherwise. A lighter text-only model (e.g. `qwen3.5:9b`) is preferred to reduce cost and latency, since no image is processed in this path.
- **BR-EXT-010** — Worker re-validates ownership of the target topic in the finalize transaction. Mismatch → `extraction_failed` with `error='ownership_violation'`.
- **BR-EXT-011** — Finalize is one TX: `topic_contents INSERT` + `rag_indexing_outbox INSERT` + `extraction_job_audit INSERT` + `extraction_job_pages DELETE` + `extraction_jobs UPDATE`. Atomic.
- **BR-EXT-012** — RAG embedding is async via outbox. Failure to embed never rolls back content. Content is visible immediately; searchable when outbox row drains.
- **BR-EXT-013** — Per-job cost cap: `MAX_PER_JOB_USD=20` (env-configurable). Worker tracks running cost from token counts × per-token prices; kills job that exceeds.
- **BR-EXT-014** — Per-day platform cost cap: `MAX_DAILY_PLATFORM_USD=200` (env-configurable). Worker queries today's `extraction_job_audit.cost_usd` sum before claiming a new job; if exceeded, sleeps 60s and retries.

### Cancellation

- **BR-EXT-015** — DELETE on `pending` → status flips to `cancelled` immediately, source file deleted, `purge_at=NOW()+24h`.
- **BR-EXT-016** — DELETE on `extracting` → sets `cancel_requested=true`. Worker checks at next page boundary; if true → `status='cancelled'`, partial pages staged are kept for forensic inspection but no `topic_contents` are written.
- **BR-EXT-017** — DELETE on `done` is rejected (404). Use `DELETE /api/topic-contents/{id}` to remove materialized rows individually.

### Frontend integration

- **BR-EXT-018** — `fetchWithCSRFRetry` MUST handle FormData correctly: re-clone FormData on CSRF retry (the original Body is consumed). Verify with integration test before any worker code is written. (Challenger #1)
- **BR-EXT-019** — Frontend renders client-side pseudo-jobs for upload-phase progress. Pseudo-job is in-memory only; backend never sees `'uploading'`. Replaced by real job on 201; marked `'upload_failed'` on error.
- **BR-EXT-020** — Topic card polling stops after 60s of no active jobs to avoid idle traffic.

### Provenance & audit

- **BR-EXT-021** — Each materialized `topic_contents` row carries `source_extraction_job_id` (nullable; only set for extracted rows). UI badge resolves filename via `extraction_job_audit` JOIN.
- **BR-EXT-022** — `extraction_job_audit` is **never purged**. It outlives the source file, the job row, and even (logically) the deleted `topic_contents` row.
- **BR-EXT-023** — `topic_contents` rows manually deleted via `DELETE /api/topic-contents/{id}` do not cascade-delete the audit row. The audit retains "this job extracted N pages on date X by user Y" forever.
- **BR-EXT-023a** — `PATCH /api/topic-contents/{id}` MUST NOT clear `source_extraction_job_id`. Edits change `title` and/or `body` only. Provenance is permanent.
- **BR-EXT-023b** — No upload-time title input is offered for PDF/image content types. Per-page titles are auto-derived from the first H1 in the extracted markdown (fallback: `"Page N — {filename}"`) and editable post-hoc via inline rename or the Edit modal. Video and Text uploads accept a title at creation time (1 upload → 1 row).

### Parent quota

- **BR-EXT-024** — Parent quota: max 5 concurrent jobs (`status IN ('pending','extracting')`) and 100 jobs/day (`created_at > NOW()-INTERVAL '24h'`).
- **BR-EXT-025** — Parent quota enforced application-layer inside the POST handler TX, with row-level lock on `parent_quota_counters`. APISIX rate limit (50/day per parent token) is a coarse second-line defence, not the primary gate.
- **BR-EXT-026** — Admin has no per-user quota in v1 (admin pool is small and trusted). APISIX rate limit (20/hr per admin token) provides a runaway-script bound.

### Ownership (admin vs parent)

- **BR-EXT-027** — Admin POST endpoints require `topics.owner_type='platform'` for the target topic. Parent POST endpoints require `topics.owner_type='parent' AND owner_id = current_user.idp_sub`. Wrong owner → 404 (oracle protection).
- **BR-EXT-028** — Worker is owner-agnostic at queue level (same `extraction_jobs` table). Owner is re-validated in finalize TX (BR-EXT-010).

### Source file lifecycle

- **BR-EXT-029** — Source files stored under `${STORAGE_ROOT}/extraction_sources/{job_id}/{filename}`. Path traversal hardened via `Path.resolve().is_relative_to(STORAGE_ROOT)`.
- **BR-EXT-030** — Purge worker runs hourly. Selects rows where `purge_at < NOW()` and status is final, deletes file from disk, deletes row.

### Health

- **BR-EXT-031** — Workers write `worker_heartbeats` row every 10s. `GET /api/admin/system/workers` returns workers with `last_seen > NOW()-INTERVAL '60s'` flagged as stale.

---

## 8 — Tooling Decisions

| Decision | Choice | Rationale |
|---|---|---|
| PDF library | **`pypdfium2`** (Apache/BSD) | Fast, handles both native text extract and rasterize. **PyMuPDF BANNED** — AGPL §13 SaaS clause forbids closed-source SaaS use. |
| Vision LLM provider | **`glm-ocr`** from `../haiguru/glm_ocr/` | Prefix-dispatch on model spec: `lmstudio://...`, `openai://...`, `anthropic://...`, plain → Ollama. Streaming tuple protocol (`__first_token__`, `chunk`, `__done__`). |
| Default vision model spec | env `EXTRACTION__MODEL_SPEC` | v1 platform-wide default for vision OCR. Per-upload model selection is backlog. Audit row records the resolved spec. |
| Restructure model spec | env `EXTRACTION__RESTRUCTURE_MODEL_SPEC` (default: same as vision spec) | Lighter text-only model for the text restructuring pass (BR-EXT-032). E.g. `qwen3.5:9b`. Defaults to `EXTRACTION__MODEL_SPEC` when unset. |
| Restructure text flag | env `EXTRACTION__RESTRUCTURE_TEXT` (default: `true`) | Enable/disable the text restructuring pass for native-text PDF pages. Set `false` for raw extraction only. |
| Text restructure method | `GlmOcrProvider.restructure_page(raw_text: str) -> str` | New text-only method on `GlmOcrProvider`. Uses `restructure_model_spec` if set. Falls back to raw text on empty LLM response. Adapted from `anhad-final-exam/src/pdf_to_markdown/ocr.py`. |
| MIME sniffer | `python-magic` (libmagic) | First 8 KB. Reject mismatch between sniffed and declared MIME. |
| Queue | Postgres `FOR UPDATE SKIP LOCKED` | No new infra. 5–10 admins / ~50–200 PDFs/week — no scale signal yet. SSE/Redis migration trigger documented as ">100 concurrent active jobs platform-wide". |
| File storage | Local disk via existing `StorageBackend` | Same interface as `topic_contents` files. S3/GCS swappable later. |
| Embedding | Existing `rag_chunks` pipeline + outbox | Decouples user-visible content from embed latency / failure. |

---

## 9 — Out of Scope (v1)

- **`exercises` job type** — column added now, worker dispatch wired, but UI / endpoint un-exposed. Ships in 1d-real-2.
- **Per-upload model selection UI** — env-default only.
- **HEIC / HEIF image support.**
- **Pre-upload virus scan (ClamAV)** — admins are internal-trusted; documented accepted risk for v1. Parent-side may need this in v2.
- **SSE / WebSocket progress** — polling sufficient for current scale.
- **Bulk re-extract by model upgrade** — admin would re-upload manually with `X-Force-Reextract`.
- **`.txt` file upload** — plain-text files handled by the `text` content type (direct `topic_contents` insert). No pipeline needed.
- **LLM-derived filenames** — `anhad-final-exam` suggests snake_case filenames via LLM. haisir-backend derives titles from first H1 or `"Page N — {filename}"` (BR-EXT-023b). LLM filename suggestion is backlog.

---

## 10 — Implementation Sequence (high-level)

1. **Infrastructure prep** (haisir-deploy): add `worker` service to compose, set `replicas: 2`, env vars for `EXTRACTION_MODEL_SPEC`, cost caps, storage paths.
2. **Schema + audit tables** (haisir-backend): Alembic migration for the 7 tables/columns. Backfill is empty.
3. **Domain models + protocols** (haisir-backend): `domain/services/extraction.py`, `domain/models/extraction_job.py`, Protocols for `ExtractionProvider` + `PdfReader`.
4. **Infrastructure** (haisir-backend): `infrastructure/extraction/glm_ocr_provider.py`, `infrastructure/extraction/pdfium_reader.py`, `infrastructure/repositories/extraction_job.py`, `infrastructure/storage/extraction_source.py`.
5. **API endpoints** (haisir-backend): admin + parent variants, multipart streaming parser, idempotency key handler, MIME sniff, SHA dedup, quota gate.
6. **Worker process** (haisir-backend): `worker/extraction_loop.py`, `worker/purge_loop.py`, `worker/rag_outbox_loop.py`, `worker/heartbeat.py`.
7. **CSRF + FormData verification** (haisir-frontend): integration test for `fetchWithCSRFRetry` with FormData. **Blocking gate before #8.**
8. **Frontend modal rebuild** (haisir-frontend): replace existing `AddContentModal` to match `target/prototypes/haisir_admin_flow.html`. Reuse `ContentItemRow` for materialized rows.
9. **Topic card jobs strip** (haisir-frontend): polling hook with ETag/304, status renderers, cancel/retry actions.
10. **Provenance badge** (haisir-frontend): display `source_extraction_job_id` filename via audit JOIN.
11. **Health endpoint UI** (haisir-frontend): admin sysadmin page showing worker liveness.
12. **Cost preview heuristic** (haisir-frontend): client-side estimate from file size; confirmation gate for >$2.

`/plan` will decompose this further into ordered tasks per repo.

---

## 11 — Content Rendering (LaTeX / Math)

> Added 2026-07-02 (pre-Phase-5 hardening pass, G8/T8.4). **Requirement only — no implementation
> in pre-Phase-5.** Tracked as backlog item `vision/requirements/backlog.md` BL-003 (Status: Ready).
> Ships as a focused content-rendering follow-up phase.

### Problem

Educational content carries LaTeX math. The through-Phase-4 frontend has **no math-rendering
library** installed (no `katex`, `remark-math`, `rehype-katex`, or `mathjax` in `package.json`).
Every text surface interpolates strings as plain React text children, so LaTeX renders as raw
literal characters (visible `$` and backslashes) across:

| Surface | File | Field |
|---|---|---|
| Topic `text` content (S-nav content viewer) | `content-viewer.tsx:49` | `item.text` |
| Exam `question_text` (S-exam) | `question-renderer.tsx:231` | `question.question_text` |
| Exam option text | `single-choice-input.tsx:48` (+ sibling input components) | `opt.text` |
| Review question list (S05) | `exam-review-question-list.tsx:63` | `item.question_text` |
| AI chat bubbles (hAITU doubt + exam-review chat) | `markdown-text.tsx` | `msg.content` (no math plugin) |

### Requirement

`question_text`, option text, topic `text` content, and review question bodies MUST render LaTeX
math (inline `$...$` and block `$$...$$`) as typeset mathematics, not raw literal text. The same
applies to AI-generated chat content (hAITU explanations, exam-review chat) which already flows
through `MarkdownText` but without a math plugin.

### Agreed approach

- **Library:** KaTeX (synchronous, smaller, sufficient for authored educational content) over
  MathJax (heavier async model). Add `katex`, `remark-math`, `rehype-katex` to the frontend.
- **Markdown path:** wire `remarkMath` + `rehypeKatex` into the shared `MarkdownText`
  (`react-markdown` plugins alongside the existing `remark-gfm`). Import `katex/dist/katex.min.css`
  once at the app root. This covers the AI chat bubbles and any markdown surface.
- **Plain-text path:** the four non-markdown surfaces (`ContentViewer`, `QuestionRenderer`, the
  option-input components, `ExamReviewQuestionList`) currently interpolate text directly. Route
  each through a math-aware renderer — either a shared `<MathText>` component (KaTeX `renderToString`
  on detected math spans) or promote them to `MarkdownText` (markdown + math) if authored content
  is expected to use markdown. Decision per surface on pickup (see BL-003 open questions).
- **Delimiters:** accept inline `$...$` and block `$$...$$` (KaTeX default via `remark-math`);
  confirm whether `\(...\)` / `\[...\]` should also be recognised (extraction sources may emit
  those). Recommendation: accept both `$` and `\(\)` families.
- **Security:** KaTeX escapes by default (no `trust` / `\url` macros). `MarkdownText` keeps its
  no-`rehype-raw` policy — math rendering must not open an HTML injection path. The extraction
  pipeline's restructured markdown remains sanitised.
- **SSR:** KaTeX renders client-side; confirm no layout shift / hydration mismatch on the content
  viewer and exam pages (render math in an effect or use KaTeX server-side render for static
  parts).

### Out of pre-Phase-5 scope

Implementation is deferred — this section states the requirement and the agreed approach only.
The follow-up phase that implements it will decompose the work into per-surface tasks.
