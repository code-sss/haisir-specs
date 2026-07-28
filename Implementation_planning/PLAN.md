# PLAN — Phase 6.5 (Content Viewing & Publish)

> Scoped 2026-07-27 via `/plan`. Phase 7 (Gateway WAF, CSP & security-review closeout) was fully
> unstarted and has been archived unchanged to
> `archive/PLAN_Phase7-GatewayWAF-CSP_2026-07-27.md` /
> `archive/TASKS_Phase7-GatewayWAF-CSP_2026-07-27.md` — it is deferred, not cancelled, and should be
> picked back up after this phase.
>
> Specs: `target/requirements/01_data_model.md` (BR-DATA-008/009/024/025),
> `target/requirements/12_content_extraction.md` (BR-EXT-012/034/035/036/037),
> `target/requirements/03_student.md` (BR-STU-025), `target/requirements/05_parent.md`
> (BR-PAR-021), `target/requirements/07_platform_admin.md` (BR-ADM-008), and both
> `target/requirements/ui-mapping/` files.

## Root goal

Uploaded content is viewable in its native format by both the uploader and the student, and student
visibility becomes an explicit per-item publish decision instead of an implicit side-effect of the
extraction pipeline finishing.

## Context — why now

Extraction was built to feed RAG embeddings, and student display was an accident of that pipeline:
whatever the extractor produced became what students saw, immediately, with no review step. Three
consequences motivated this increment:

1. **The raw upload was thrown away.** `extraction_jobs.source_path` is purged on a TTL and no
   `topic_contents` row ever pointed at the source file, so a well-formatted textbook page was
   permanently replaced by a lossy markdown transcription. Neither admin nor parent could look at
   what they had actually uploaded.
2. **There was no review gate.** BR-EXT-012 made content visible on creation. A bad OCR pass on a
   poor scan went straight to students.
3. **Viewing was half-built.** A PDF viewer and a `ContentViewer` already exist on the student side,
   but the uploader-facing screens had no viewer at all, and video playback used a raw
   `<iframe src>` that fails outright when a video owner disables embedding.

### Spec-review corrections folded into this plan

The target specs for this increment were drafted before being checked against the shipped code.
A challenger pass on 2026-07-27 found eight discrepancies; all are now fixed in the specs, and the
task breakdown below reflects the corrected text rather than the original draft:

| # | Draft claim | Ground truth |
|---|---|---|
| 1 | Raw file path goes in the `text` column | `topic_contents` has a dedicated **`url`** column; that is where video URLs and manually-uploaded PDF paths already live (`TopicContentService.create` normalizes to `{data_dir}/topics/{content_type}/{filename}`, and the file-serving route reads `url`). Using `text` would also slip the raw row past the RAG worker's `tc.text IS NOT NULL AND tc.text != ''` guard. |
| 2 | `content_type` is a VARCHAR; adding `'image'` is free | It is a **native Postgres enum** `contenttype` (`V4_topic.py`). Needs `ALTER TYPE ... ADD VALUE` in an Alembic autocommit block. |
| 3 | Inline PDF viewer is net-new | `SecurePdfViewer` (react-pdf + `usePDFBlob` + `PDFDocument`) already exists and is already wired into `ContentViewer`. Only the **image** viewer is net-new. |
| 4 | Text rows shift to `base + 1 + page_no` to seat the raw row first | `provenance.page_no` is derived from `topic_contents.order` (`TopicContentRepository._set_provenance`), so shifting silently renumbers every provenance badge. Raw row is **appended** at `order = N` instead; text ordering untouched. |
| 5 | BR-DATA-020's exclusion list must be extended to exclude `pdf`/`image` | The implemented enqueue gate is an **allowlist** (`content_type == ContentType.text`). `pdf`/`image` are excluded by construction — no code change, regression test only. |
| 6 | (unstated) | **No file-serving endpoint was specced at all.** The existing `GET /api/topic-contents/{content_type}/{topic_id}` is topic-keyed (cannot address one of N+1 rows), hardcodes `media_type="application/pdf"`, and is gated on `require_any_platform_role()` which excludes **parent**. |
| 7 | Groups keyed by `source_extraction_job_id` | That column is `NULL` for every manually-created video/text row — a naive `GROUP BY` collapses them all into one false group. NULL now means "group of one". |
| 8 | "all four `content_type` values" | The enum has six after `image`. `question` / `question_answer` are dead values (declared in the domain enum, referenced nowhere else in backend `src/`). They inherit the gate with no special-casing. |

### Scope locks

- **The truncate is a runbook, not a migration.** Alembic revisions run automatically on deploy; an
  irreversible `TRUNCATE` inside one fires against every environment the image reaches with no
  operator in the loop. Additive DDL goes in the revision; the destructive reset is confirm-gated
  and manually invoked (G2).
- **Publish is never a per-row write.** BR-DATA-024's mutual-exclusivity invariant cannot hold if a
  caller can set one row's `visibility_status` at a time, so `visibility_status` is absent from
  `TopicContentUpdate` and the only write path is the group-scoped publish endpoint (BR-EXT-037).
- **Video scope stays YouTube + Vimeo**, matching the existing hostname allowlist. No new providers.
- **Backend and frontend release together**, so T3.5's removal of the legacy route carries no
  cross-release ordering hazard (confirmed by product owner, 2026-07-27).

---

## G1 [backend]: Schema foundation — `image` type and `visibility_status`

Additive DDL only. Nothing destructive, nothing behavioural — this goal exists so every later task
has a column and an enum value to write against.

### T1.1 [backend]: Add `image` to the `contenttype` enum

Add `image = "image"` to `ContentType` in `src/domain/models/topic_content.py`, and an Alembic
revision issuing `ALTER TYPE contenttype ADD VALUE IF NOT EXISTS 'image';`.

The statement must run inside `with op.get_context().autocommit_block():` — Postgres will not let a
transaction use an enum value added in that same transaction, and Alembic wraps revisions in one by
default.

- **Done when:** `INSERT INTO topic_contents (..., content_type) VALUES (..., 'image')` succeeds
  against a freshly migrated database, and `ContentType.image` resolves in Python.
- **Test:** Migration test asserting the value is present in `pg_enum` after upgrade; unit test
  round-tripping a `TopicContent` with `content_type=ContentType.image` through the repository.

### T1.2 [backend]: Add the `visibility_status` column

`ALTER TABLE topic_contents ADD COLUMN visibility_status VARCHAR NOT NULL DEFAULT 'draft'` in the
same revision chain, mirrored into the imperative table definition
(`src/infrastructure/models/topic_content.py`) and the `TopicContent` dataclass.

No DB `CHECK` — same precedent as `topics.status`, which is a plain `sa.String()` with a
`server_default`. Validation lives at the Pydantic layer (T1.3).

- **Done when:** A newly inserted row defaults to `'draft'` without the caller supplying it, and the
  value survives a repository read/write round-trip.
- **Test:** Unit test on `TopicContentRepository` asserting the default on insert and persistence on
  update.

### T1.3 [backend]: Pydantic schema surface

Add `visibility_status: Literal["draft", "published"]` to `TopicContentRead`. Deliberately **omit**
it from `TopicContentUpdate` and `TopicContentCreate` — creation always yields `'draft'`
(BR-EXT-034) and the only mutation path is the group publish endpoint (BR-EXT-037).

- **Done when:** `TopicContentRead` serializes the field; a `PATCH /api/topic-contents/{id}` body
  carrying `visibility_status` is ignored rather than applied.
- **Test:** Schema unit test asserting the `Literal` rejects an unknown value, plus a route test
  asserting a `visibility_status` key in a PATCH body does not change the stored value.

- **G1 integration test:** Migrate a clean database, create one row of each `content_type`
  (including `image`), and assert every row reads back as `'draft'` with the correct type.

---

## G2 [deploy]: One-shot content reset runbook

The product decision is a clean reset rather than a backward-compatible migration. This goal makes
that reset explicit, confirm-gated, and complete — including the files on disk, which a table
truncate does not touch.

**Re-upload cost is low:** product owner confirmed 2026-07-27 that current content across all
environments is test data only, so nothing of value is lost. The confirmation gate stays regardless
— it protects future runs, when that may no longer be true.

### T2.1 [deploy]: Confirm-gated reset script

A script under `common/scripts/` that, after an explicit typed confirmation and an environment name
check, truncates `topic_contents`, `extraction_jobs`, `extraction_job_pages`,
`extraction_job_audit`, `rag_indexing_outbox` and `data_topic_content_chunks`, then clears
`{data_dir}/topics/`.

Truncating `topic_contents` alone would leave every file under `{data_dir}/topics/` orphaned on the
volume with no row pointing at it.

- **Depends on:** T1.2 [backend] — the column must exist before the reset, so re-uploaded content
  lands under the new model.
- **Done when:** Running the script against a seeded staging database leaves all six tables empty
  and `{data_dir}/topics/` empty; running it without the confirmation exits non-zero and changes
  nothing.
- **Test:** Dry-run mode asserted to change nothing; a staging execution verified by row counts and
  a directory listing.

- **G2 acceptance test:** After reset, a fresh PDF upload completes end to end and produces exactly
  N text rows plus one raw row, all `'draft'`.

---

## G3 [backend]: The raw file is materialized and servable

### T3.1 [backend]: `copy_to_content_store`

A method that copies a finished job's source file from the **extraction** storage root
(`ExtractionSourceStorageImpl`, rooted at the extraction dir) into the **content** store at
`{data_dir}/topics/{content_type}/{filename}` — the convention `TopicContentService.create` already
uses and the only root the file endpoint will resolve under.

The destination filename must be collision-safe: two uploads called `notes.pdf` on the same topic,
or across topics, must not overwrite one another. Prefix with the content row's UUID.

- **Done when:** Given a job whose source exists in the extraction root, the method returns a
  relative URL and the file is byte-identical at the destination; a second copy of an
  identically-named file produces a distinct path.
- **Test:** Unit test with a temp-dir storage root covering the happy path, the collision case, and
  path-traversal rejection.

### T3.2 [backend]: `finalize()` appends the raw row

Extend `src/worker/finalize.py` to build one additional `TopicContent` after the text rows:
`content_type` from `job.source_type` (already `"pdf"` / `"image"`), `title = job.source_filename`,
`url` = T3.1's returned path, `order = len(pages)`, same `source_extraction_job_id`, and
`visibility_status='draft'`.

Text rows keep `order = page.page_no` exactly as today. Do not introduce the base-shift BR-DATA-012
describes — it has never been implemented, and changing `order` renumbers provenance badges.

The row must be inside the same finalize transaction as the text rows, and the copy in T3.1 must
succeed before the transaction commits, so a failed copy does not leave a row pointing at a missing
file.

- **Depends on:** T3.1, T1.1, T1.2
- **Done when:** A finished PDF job with N pages yields N+1 `topic_contents` rows — N `text` at
  orders `0..N-1` and one `pdf` at order `N` — all sharing one `source_extraction_job_id` and all
  `'draft'`.
- **Test:** Worker integration test over a 3-page PDF job asserting row count, types, orders, shared
  job id, and that `provenance.page_no` on the text rows is unchanged from the pre-increment
  baseline.

### T3.3 [backend]: Regression test — the raw row is never enqueued

No production code change. The enqueue gate is already an allowlist
(`content_type == ContentType.text` in `TopicContentService`, and the worker enqueues only the text
rows it builds), so `pdf` and `image` are excluded by construction. This task locks that in against
a future refactor that flips the gate to a denylist.

- **Depends on:** T3.2
- **Done when:** A test asserts `rag_indexing_outbox` contains exactly N rows after an N-page job,
  none of them the raw row's id.
- **Test:** The assertion above, plus one asserting a manually-created `image` row produces no
  outbox entry.

### T3.4 [backend]: `GET /api/topic-contents/{content_id}/file`

New per-content file endpoint replacing the topic-keyed route.

- Resolves exactly one row by id; 404 on absent, on a `content_type` with no stored file, or on an
  empty `url`.
- Media type derived from the actual bytes via the existing `ExtractionSourceStorageImpl.sniff_mime`
  helper rather than a hardcoded `application/pdf` or a trusted file extension.
- Path resolved under `{data_dir}` with the traversal rejection the current route already performs.
- Role gating: **student** → 404 unless BR-DATA-003 visibility **and** `topics.status='live'`
  **and** `visibility_status='published'`; **admin** → platform-owned rows only (BR-SEC-005);
  **parent** → rows under topics with `owner_id = parent.idp_sub` only, 404 otherwise (the
  404-oracle pattern of BR-PAR-006).

Parent must be reachable here — `require_any_platform_role()` is student/instructor/admin only, so
today a parent cannot fetch a file at all.

- **Depends on:** T1.2
- **Done when:** Each of the three roles gets the correct 200/404 for owned, unowned, draft and
  published rows, and a PNG is served as `image/png` rather than `application/pdf`.
- **Test:** Route test matrix over {student, admin, parent} × {owned/unowned, draft/published} ×
  {pdf, image}, plus a traversal attempt asserting 400.

### T3.5 [backend]: Remove the legacy topic-keyed file route

Delete `GET /api/topic-contents/{content_type}/{topic_id}` and its service method once the frontend
is off it, leaving one file path to authorize.

- **Depends on:** T5.4 [frontend]
- **Done when:** The route is gone, no frontend call site references it, and the full test suite
  passes.
- **Test:** Route test asserting 404 for the old path; grep of the frontend asserting zero call
  sites.

- **G3 integration test:** Upload a PDF as admin, wait for extraction, fetch the raw row's file
  through the new endpoint as admin (200) and as an unlinked student (404 while draft).

---

## G4 [backend]: Publish as an atomic per-group decision

### T4.1 [backend]: Upload-group resolver

A helper resolving a `content_id` to its sibling group: rows on the same `topic_id` sharing a
**non-NULL** `source_extraction_job_id`. A row whose `source_extraction_job_id IS NULL` resolves to
a group containing only itself.

The NULL case is the trap: every manually-created video/text row has a NULL job id, so grouping
without excluding NULLs would treat all of a topic's manual content as one group and draft the lot
on any publish.

- **Done when:** The resolver returns N+1 rows for any member of an extraction group, and exactly
  one row for a manually-created video/text row, even when the topic holds several such rows.
- **Test:** Repository unit test over a topic holding one extraction group plus three manual rows,
  asserting group sizes from each member's perspective.

### T4.2 [backend]: `PATCH /api/topic-contents/{content_id}/publish` (admin)

Sets the addressed row's side to `'published'` and every other row in its group to `'draft'`, in a
single transaction. For an extraction group, "side" is raw-vs-text: publishing the raw row drafts
all N text rows, publishing any text row publishes all N and drafts the raw row.

- **Depends on:** T4.1, T1.3
- **Done when:** After publishing the raw side, the raw row is `'published'` and all text rows are
  `'draft'`; after publishing the text side, the inverse — with no intermediate state observable to
  a concurrent reader.
- **Test:** Route test asserting both directions and that exactly one side is published at all
  times; a concurrency test issuing two opposing publishes and asserting a consistent final state.

### T4.3 [backend]: Parent-scoped publish mirror

The same operation under `/api/parent/curriculum/topic-contents/{content_id}/publish`, 404 unless
the content resolves to a topic owned by the calling parent (BR-PAR-006's oracle protection).

- **Depends on:** T4.1
- **Done when:** A parent can publish within their own topic and receives 404 — not 403 — for
  another parent's content or for platform content.
- **Test:** Route test covering own content, another parent's content, and platform content.

### T4.4 [backend]: Student read paths gain the publish gate

Add `visibility_status = 'published'` as an AND-condition to the student visibility clause used by
the topic-content read paths, underneath the existing BR-DATA-003 `owner_type` / `parent_child_links`
and `topics.status='live'` gates. Uploader-facing paths (admin, parent) are unchanged — draft
content stays fully visible and editable to its owner.

- **Depends on:** T1.2
- **Done when:** A student listing a live topic sees only published rows; the admin and parent
  listings for the same topic still show every row.
- **Test:** Extend `tests/integration/routes/test_g6_visibility_student_read_paths.py` with a live
  topic holding one published and one draft row, asserting the student sees one and the owner sees
  two.

- **G4 integration test:** Full loop — upload, confirm nothing is student-visible, publish the raw
  side, confirm the student sees exactly the raw row, switch to the text side, confirm the student
  sees exactly the N text rows.

---

## G5 [frontend]: Shared content viewer

### T5.1 [frontend]: Promote `ContentViewer` to a shared location

Move `src/features/student/components/content-viewer.tsx` (and its CSS module) out of the student
feature into a shared location so admin and parent can mount the same component. Update the student
import.

Pure move — no behavioural change in this task, so any later regression is attributable to the
tasks that follow rather than to the relocation.

- **Done when:** The student topic view renders identically to before and no `features/admin` or
  `features/parent` module imports from `features/student`.
- **Test:** Existing student content-viewer tests pass unchanged against the new path.

### T5.2 [frontend]: Add `image` to the content-type unions

Add `"image"` to the `content_type` union in `src/features/student/types/student.types.ts` and to
the corresponding zod schemas in the admin, parent and content-management feature types.

- **Done when:** An API response carrying `content_type: "image"` parses without a zod error in all
  four consumers.
- **Test:** Schema unit test parsing an `image` content item in each of the four modules.

### T5.3 [frontend]: Image viewer case

Add `case "image"` to `ContentViewer`'s dispatch, rendering the file from the per-content endpoint
with sensible max-width behaviour.

Ships in the same change as T5.2: the switch is exhaustive over the `content_type` union, so adding
the union member without the case is a TypeScript compile error.

- **Depends on:** T5.1, T5.2
- **Done when:** An `image` content item renders inline; the project type-checks.
- **Test:** Component test rendering an `image` item and asserting the `img` element resolves to the
  file endpoint URL.

### T5.4 [frontend]: Repoint the PDF viewer at the per-content endpoint

Change the `pdfUrl` passed to `SecurePdfViewer` from the row's stored `url` to
`/api/topic-contents/{content_id}/file`. `usePDFBlob` already fetches with CSRF and
`credentials: 'include'`, so no fetch-layer change is needed.

- **Depends on:** T3.4 [backend]
- **Done when:** A student viewing a published PDF sees it render, with the network request going to
  the per-content endpoint.
- **Test:** Component test asserting the fetched URL; manual verification against a running stack.

### T5.5 [frontend]: SDK-based video player with fallback

Replace the raw `<iframe src>` at `content-viewer.tsx:40` with the YouTube IFrame Player API and the
Vimeo Player SDK. On an embed error — the common case being a video owner who has disabled
embedding — render a "Watch on YouTube" / "Watch on Vimeo" external-link button instead of a
silently broken frame. Scope stays YouTube + Vimeo, matching the existing hostname allowlist.

- **Depends on:** T5.1
- **Done when:** An embeddable video plays inline; an embed-restricted video shows the fallback link
  rather than an empty frame.
- **Test:** Component test simulating the SDK's error callback and asserting the fallback link
  renders with the correct external URL.

- **G5 integration test:** One topic holding a pdf, an image, a text and a video item renders all
  four correctly through the single shared viewer, in both the student and the admin mount.

---

## G6 [frontend]: Uploader review and publish UI

### T6.1 [frontend]: Content row — View button and publish-state pill

Each content row gains a View action opening the shared viewer, and a publish-state pill
(`● Published` green / `○ Draft` grey). `pdf` and `image` rows show View instead of Edit — there is
no editable body.

- **Depends on:** T5.1
- **Done when:** Every row in the admin and parent content lists shows its publish state, and View
  opens the correct viewer for its type.
- **Test:** Component test over a mixed content list asserting the pill state and the
  View/Edit affordance per `content_type`.

### T6.2 [frontend]: Publish toggle

For an extraction group, a two-way "Publish as Document" / "Publish as Text" control; for a
standalone video/text row, a simple Draft/Published toggle. Both issue a single call to the publish
endpoint — the UI never writes rows individually, since the server owns the mutual-exclusivity
invariant.

- **Depends on:** T4.2, T4.3 [backend], T6.1
- **Done when:** Switching sides updates every affected row's pill after one round-trip, for both
  the admin and the parent screens.
- **Test:** Component test asserting one request per switch; an end-to-end check that the student
  view changes accordingly.

### T6.3 [frontend]: Markdown editor with live preview

Replace the plain textarea in the edit-content modal with a textarea plus a rendered preview pane
using the same `MarkdownText` component the viewer uses, so the uploader previews exactly what gets
published (BR-EXT-036).

- **Done when:** Typing markdown in the editor updates the preview, and the preview output is
  identical to the student viewer's rendering of the same source.
- **Test:** Component test asserting the preview pane renders the same markup as `MarkdownText` for
  a sample containing a heading, a list and a code block.

### T6.4 [frontend]: Correct the provenance tooltip

The badge tooltip currently reads "The original PDF/image is no longer stored." That is now false —
the raw file is permanently retained. Update the copy.

- **Done when:** The tooltip no longer claims the source is discarded.
- **Test:** Component test asserting the tooltip string.

- **G6 integration test:** As an admin, upload a PDF, view both representations, publish the raw
  side, and confirm a linked student sees the document; repeat the same loop as a parent on a Home
  Study topic.

---

## Deferred, not dropped

- **Phase 7 (Gateway WAF, CSP, security-review closeout)** — archived unstarted; resume after this
  phase.
- **BR-DATA-012's base-shift** — specced but never implemented, and deliberately not fixed here
  (T3.2). Content order collides with manually-added rows on a re-run; pre-existing, unchanged by
  this increment.
- **Provenance page numbers are 0-indexed in the UI** — `provenance.page_no` is `content.order`
  (0-based) but is rendered as `p.{n}`, so page 1 displays as `p.0` while the title fallback uses
  1-based numbering. Pre-existing off-by-one; touching it would have been out of scope here, and
  T3.2 is specifically designed not to make it worse.
- **BR-DATA-020's "`video`, `url`" wording** names a `url` content type that does not exist. Left
  as-is rather than renumbered; BR-DATA-025 no longer propagates it.
- **BR-SEC-011/012 collision** between `02_auth_and_roles.md` and `13_secrets_management.md` —
  recorded during Phase 7 scoping, still unresolved.

<!-- plan-baseline: backend:c82d4661271406bc99765df65c47e6d455f2202c frontend:67a883c339c82c3ff9cc4a3810f64ea23db3250b deploy:861705bc29164ba73746297ad563ab1d6259e4de -->
