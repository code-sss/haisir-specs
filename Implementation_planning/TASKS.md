# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:`c82d466` frontend:`67a883c` deploy:`861705b` (2026-07-27)
> Phase 6.5 scoped 2026-07-27 — see `PLAN.md` for the goal tree, the spec-review corrections table
> and the scope locks. Phase 7 (Gateway WAF) archived unstarted; resume after this phase.

## G1 [backend]: Schema foundation — `image` type and `visibility_status`
- [x] T1.1 [backend]: Add `image` to the `contenttype` enum — `ALTER TYPE ... ADD VALUE` in an Alembic autocommit block, plus `ContentType.image` (2026-07-28)
- [x] T1.2 [backend]: Add `visibility_status VARCHAR NOT NULL DEFAULT 'draft'` — column, imperative mapping, dataclass field; no DB CHECK (2026-07-28)
- [x] T1.3 [backend]: Pydantic surface — `Literal["draft","published"]` on `TopicContentRead`; omitted from Create/Update (2026-07-28)
- [ ] **G1: Schema foundation** — integration test

## G2 [deploy]: One-shot content reset runbook
- [ ] T2.1 [deploy]: Confirm-gated script truncating the six content tables and clearing `{data_dir}/topics/` (depends on T1.2 [backend])
- [ ] **G2: Content reset runbook** — acceptance test

## G3 [backend]: The raw file is materialized and servable
- [x] T3.1 [backend]: `copy_to_content_store` — collision-safe copy from the extraction root into `{data_dir}/topics/{content_type}/` (2026-07-28)
- [ ] T3.2 [backend]: `finalize()` appends the raw row at `order = N` with its path in `url`; text-row ordering untouched (depends on T3.1, T1.1, T1.2)
- [ ] T3.3 [backend]: Regression test — the raw row never enters `rag_indexing_outbox` (depends on T3.2)
- [ ] T3.4 [backend]: `GET /api/topic-contents/{content_id}/file` — sniffed media type, path safety, student/admin/parent gating (depends on T1.2)
- [ ] T3.5 [backend]: Delete the legacy `GET /api/topic-contents/{content_type}/{topic_id}` route (depends on T5.4 [frontend])
- [ ] **G3: Raw file materialized and servable** — integration test

## G4 [backend]: Publish as an atomic per-group decision
- [x] T4.1 [backend]: Upload-group resolver — `(topic_id, source_extraction_job_id)`, NULL job id means group of one (2026-07-28)
- [ ] T4.2 [backend]: `PATCH /api/topic-contents/{content_id}/publish` — one transaction, drafts the opposite side (depends on T4.1, T1.3)
- [ ] T4.3 [backend]: Parent-scoped publish mirror under `/api/parent/curriculum/`, owner-scoped 404 (depends on T4.1)
- [ ] T4.4 [backend]: Student read paths gain the `visibility_status='published'` AND-condition (depends on T1.2)
- [ ] **G4: Atomic per-group publish** — integration test

## G5 [frontend]: Shared content viewer
- [x] T5.1 [frontend]: Promote `ContentViewer` out of `features/student/` to shared — pure move, no behaviour change (2026-07-28)
- [x] T5.2 [frontend]: Add `"image"` to the `content_type` unions/zod schemas in student, admin, parent and content-management (2026-07-28)
- [x] T5.3 [frontend]: Add the `case "image"` image viewer — **same commit as T5.2**, `noImplicitReturns` makes the union member without its case a compile error (depends on T5.1, T5.2) (2026-07-28)
- [ ] T5.4 [frontend]: Repoint `SecurePdfViewer`'s `pdfUrl` at the per-content file endpoint (depends on T3.4 [backend])
- [ ] T5.5 [frontend]: YouTube IFrame Player API / Vimeo Player SDK with external-link fallback, replacing the raw `<iframe src>` (depends on T5.1)
- [ ] **G5: Shared content viewer** — integration test

## G6 [frontend]: Uploader review and publish UI
- [ ] T6.1 [frontend]: Content row — View button and publish-state pill; View replaces Edit on `pdf`/`image` (depends on T5.1)
- [ ] T6.2 [frontend]: Publish toggle — one call per switch, server owns mutual exclusivity (depends on T4.2, T4.3 [backend], T6.1)
- [x] T6.3 [frontend]: Markdown editor with live preview via the shared `MarkdownText` component (2026-07-28)
- [x] T6.4 [frontend]: Correct the provenance tooltip — the source file is no longer discarded (2026-07-28; no-op — shipped tooltip already correct, see decisions)
- [ ] **G6: Uploader review and publish UI** — integration test

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T2.1 [deploy]: Confirm-gated content reset script (deps T1.2 [backend] done)
- T3.2 [backend]: `finalize()` appends the raw row at `order = N` (deps T3.1, T1.1, T1.2 done)
- T3.4 [backend]: `GET /api/topic-contents/{content_id}/file` — sniffed media type, path safety, role gating (dep T1.2 done)
- T4.2 [backend]: `PATCH /api/topic-contents/{content_id}/publish` — one transaction, drafts the opposite side (deps T4.1, T1.3 done)
- T4.3 [backend]: Parent-scoped publish mirror under `/api/parent/curriculum/`, owner-scoped 404 (dep T4.1 done)
- T4.4 [backend]: Student read paths gain the `visibility_status='published'` AND-condition (dep T1.2 done)
- T5.5 [frontend]: YouTube IFrame Player API / Vimeo Player SDK with external-link fallback (depends on T5.1)
- T6.1 [frontend]: Content row — View button and publish-state pill; View replaces Edit on `pdf`/`image` (depends on T5.1)
