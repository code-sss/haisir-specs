# Platform Admin Persona

> **Target state scope:** Platform Admin (platform board content manager). Scoped exclusively to `owner_type = 'platform'` content.
> → See `vision/requirements/07_platform_admin.md` for the full SuperAdmin vision spec (institution manager, tutor marketplace, user management, platform settings).

---

## Overview

Platform Admin (`admin` role) manages the authoritative platform board content. Scoped exclusively to `owner_type = 'platform'` content. Cannot read or modify parent-owned content or any student/parent user data.

## Screens

| Screen ID | Name | Route |
|---|---|---|
| SA-dashboard | Admin Dashboard | `/admin` |
| SA-boards | Board Content Manager | `/admin/boards` |

---

## SA-dashboard — Admin Dashboard

- Summary stats: total platform nodes, total topics, total live topics, total published exam templates.
- Quick-access list of top-level board nodes (grade groups or curriculum roots).
- Navigation to SA-boards.

---

## SA-boards — Board Content Manager

### Board selector strip (top)
- Lists top-level platform `course_path_nodes` (root boards, e.g. NCERT, CBSE).
- "Add Board" button → creates a new root node with `owner_type = 'platform'`.

### Left panel — Node tree (for selected board)
- Full hierarchical tree of platform nodes under the selected board.
- Node type displayed inline (chip/badge). Reserved types (`grade`, `subject`) shown with a 🔒 indicator.
- Controls: "Add Child Node", "Rename", "Delete" (blocked if child has live topics or published exams).

### Right panel — Node detail
- Selected node: name, type, breadcrumb.
- **Topic list:** each topic card shows title, status badge (`draft` / `live`), content count, content rows, in-progress extraction job rows, and a `+ Add content` button.
- "Add Topic" button below the list.
- **Publish toggle per topic:** `draft` → `live` (visible to all students) or `live` → `draft`.
- **Publish Board modal:** preview of all draft changes, confirmation to publish.

### Add Content modal (Phase 1d-real)

Replaces the URL-only stub shipped in Phase 1d. Native `<dialog>`, 560 px wide.

- Type chip selector: **PDF** (extracted to text) · **Image(s)** (OCR via vision LLM) · **Video URL** (YouTube/Vimeo) · **Text** (paste/write markdown).
- For PDF / Image: drag-drop zone + click-to-browse, file list with size + remove buttons. **Max 10 files per submission.** Max 50 MB per file.
- Cost preview band (e.g. "Est. $0.50–$2.00") shown next to Upload button. For estimates >$2: confirmation checkbox required.
- On Upload click: **modal closes immediately**. For each file, frontend creates a client-side pseudo-job (`status='uploading'`) on the topic card, then POSTs in parallel. On 201 the pseudo-job is replaced by the real `pending` job; on error it becomes `upload_failed` with a Retry button.
- For Video / Text: existing `POST /api/topic-contents` flow; modal closes on success.

### Topic card — IN PROGRESS strip (Phase 1d-real)

Single source of truth for upload + extraction progress. Visible only when ≥1 job is `pending`/`extracting`/`upload_failed`/`extraction_failed`.

- Per-job row: filename, page count, progress bar, status pill (Queued / Uploading X% / Extracting / Failed), Cancel + Retry actions.
- Polls `GET /api/admin/topics/{id}/extraction-jobs` every 2s while active; 10s when none; stops after 60s of all-done.
- Sends `If-None-Match` for ETag-based 304s.
- On `done`: row removed, content list refetched, materialized rows show provenance badge ("Extracted from chapter1.pdf · page 14").

Full behaviour and business rules in `target/requirements/12_content_extraction.md`.

### Exam builder — per-question topic picker (Phase 4 / G4.1)

The exam builder (`/add-exam`, edit at `?template_id=`) authors a static exam template under a
course-path node. Each question editor carries a **Topic** dropdown so the admin can attach the
question to a topic — this sets `questions.topic_id`, the single source of truth for per-topic
mastery attribution (G4.2).

- The dropdown lists all topics for the exam's node via `GET /api/topics/{course_path_node_id}`
  (guarded `require_any_platform_role()` — admin + instructor; returns both `draft` and `live`
  topics so a question can be attached to a not-yet-published topic). Note: this is the actual
  built route; the `/api/admin/nodes/:node_id/topics` path in the API table below is an aspirational
  stub pending a contract reconciliation pass.
- `topic_id` is **optional at the API boundary** (`QuestionItemV2` / `StaticQuestionPatchItem`:
  `topic_id: UUID4 | None = None`) and **required in the UI** — the picker defaults to "No topic"
  but every authored question should set one, or its score is excluded from mastery recalculation
  (`MasteryService` skips `topic_id IS NULL` questions).
- On edit, the picker pre-populates from `GET .../questions-with-details` (which returns
  `topic_id`). Selecting "No topic" explicitly clears it (PATCH sends `topic_id: null`); leaving
  it untouched preserves the existing value (PATCH omits the field).
- **Bulk "Apply topic to all" (pre-Phase-5 G2, issue 2):** the builder carries a control above the
  questions list — a Topic `<select>` (same `topics` source) + "Apply to all questions" button —
  that sets `topic_id` on **every** question at once (standalone questions AND every
  paragraph-embedded question). This removes the tedium of setting the same topic on 20+ questions
  one-by-one for a same-topic exam. Individual per-question Topic dropdowns remain for override
  after a bulk apply (and for multi-topic / mock exams where different questions carry different
  `topic_id`s — which MasteryService handles per-topic, see `03_student.md` "Mastery, Focus Areas &
  Weak-Topic Deep-Linking").

**Business rules:**
- BR-ADM-001: Platform Admin can only write `owner_type = 'platform'` content.
- BR-ADM-002: Platform Admin cannot read or modify `owner_type = 'parent'` content.
- BR-ADM-003: Deleting a node is blocked if it has any `live` topics with active (in-progress) exam sessions.
- BR-ADM-004: Platform content published to `live` is immediately visible to all authenticated students.
- BR-ADM-005: Platform Admin cannot access student profiles, exam sessions, or parent-child links.
- BR-ADM-006: Platform Admin extraction quota is APISIX-gated only (20 uploads/hr token-rate). No application-layer quota in v1.
- BR-ADM-007: Every question authored via the exam builder SHOULD carry a `topic_id` (set via the per-question Topic dropdown) so its score contributes to per-topic mastery. `topic_id` is optional at the API (legacy / NULL-topic questions are skipped by mastery recalc, not rejected); the UI makes it effectively required.

---

## Platform Admin API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/admin/nodes` | List all platform root nodes |
| `GET` | `/api/admin/nodes/:node_id` | Get node detail + children |
| `POST` | `/api/admin/nodes` | Create a platform node |
| `PATCH` | `/api/admin/nodes/:node_id` | Update a platform node |
| `DELETE` | `/api/admin/nodes/:node_id` | Delete a platform node |
| `GET` | `/api/admin/nodes/:node_id/topics` | List topics for a node |
| `POST` | `/api/admin/nodes/:node_id/topics` | Create a topic |
| `PATCH` | `/api/admin/topics/:topic_id` | Update topic (title, status) |
| `DELETE` | `/api/admin/topics/:topic_id` | Delete a topic |
| `POST` | `/api/admin/topics/:topic_id/extraction-jobs` | Upload PDF/image for extraction (multipart, ≤50MB, 1 file/request) |
| `GET` | `/api/admin/topics/:topic_id/extraction-jobs` | List active + recent extraction jobs (ETag/If-None-Match supported) |
| `GET` | `/api/admin/extraction-jobs/:job_id` | Job detail |
| `DELETE` | `/api/admin/extraction-jobs/:job_id` | Cancel job (hard for `pending`, soft-request for `extracting`) |
| `POST` | `/api/admin/extraction-jobs/:job_id/retry` | Re-queue a failed job using the existing source file |
| `POST` | `/api/topic-contents` | Create video URL or text content (existing endpoint) |
| `GET` | `/api/admin/system/workers` | Worker liveness / health |
| `GET` | `/api/admin/exams` | List platform exam templates |
| `POST` | `/api/admin/exams` | Create platform exam template |
| `PATCH` | `/api/admin/exams/:exam_id` | Update exam template |
| `DELETE` | `/api/admin/exams/:exam_id` | Delete exam template |
| `POST` | `/api/admin/exams/:exam_id/questions` | Add a question |
| `PATCH` | `/api/admin/exams/:exam_id/questions/:q_id` | Update a question |
| `DELETE` | `/api/admin/exams/:exam_id/questions/:q_id` | Delete a question |
