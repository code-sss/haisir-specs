# Parent Persona
> **Target state scope:** Parent (content creator, private curriculum for linked child).
> → See `vision/requirements/05_parent.md` for the full vision-level Parent spec (progress monitoring, teacher messages, weekly reports).

---

## Overview

Parents are content creators — they build or adopt a private curriculum for their linked child. Their content is never public or marketplace-facing. Parents are fully responsible for the quality of content and exams they create; no instructor oversight in this increment.

## Screens

| Screen ID | Name | Route |
|---|---|---|
| P-home | Parent Dashboard | `/parent` |
| P-curriculum | Curriculum Builder | `/parent/curriculum` |
| P-topic | Topic Content Manager | `/parent/curriculum/:node_id/topics/:topic_id` |
| P-exam | Exam Creator | `/parent/exams` |
| P-results | Child Results | `/parent/children/:child_idp_sub/results` |
| P-link | Link Child | `/parent/link-child` |

---

## Routing & guard

- `/parent/*` requires the active role to be `parent`. Enforced two ways:
  - **Server/route-table config:** `ROUTE_ROLE_REQUIREMENTS` in `use-auth.ts` has a `/parent` prefix entry (`requiredRole: "parent"`), consumed by `canAccessRoute`.
  - **Client component guard:** `ParentRouteGuard` (`src/features/parent/components/parent-route-guard.tsx`) wraps the `/parent` layout. It is a thin binding over a shared `RouteGuard` component (`src/shared/components/route-guard.tsx`, `requiredRole="parent"`) — the same shared component `AdminRouteGuard` binds with `requiredRole="admin"`. The two guard layers are intentionally redundant (mirrors the admin pattern) and are not deduplicated.
- **Redirect matrix:**
  - Unauthenticated (`userName` falsy) → `/`.
  - Authenticated, `currentRole !== "parent"` → `/home`.
  - Authenticated, `currentRole === "parent"` → renders `/parent/*` children.
  - While `useAuth` is loading → renders a spinner, no redirect yet.
- The top-level `/` route also redirects a parent-role user straight to `/parent` (`app/page.tsx`).
- **Onboarding CTA path:** the parent-ready onboarding screen's View B CTA (`on05-parent-ready.tsx`) currently links to `/link-child`, a route that does not exist — a dead link pending the repoint to `/parent/link-child` (tracked separately as T2.6, not yet shipped).

---

## P-home — Parent Dashboard

- **Child selector strip** at the top: shows all linked children (name + avatar). Clicking switches the active child context.
- If no child linked: prominent "Link your child" card with navigation to P-link.

### Tabs (per active child)
1. **Overview** — summary cards: topics uploaded, exams created, last exam score, weak topics count.
2. **Curriculum** — shortcut to P-curriculum filtered for this child's view.
3. **Results** — shortcut to P-results for this child.

---

## P-curriculum — Curriculum Builder

Two entry paths:
- **Adopt from Platform** — imports a platform board subtree (deep copy) as a starting point.
- **Build from scratch** — creates a new root node manually.

### Left panel — Node tree
- Hierarchical tree of the parent's own `course_path_nodes` (`owner_type = 'parent'`, `owner_id = parent.idp_sub`).
- Controls: "Add Node" (child of selected node), "Rename", "Delete" (cascade delete; only if no live exam sessions under this subtree).
- "Adopt from Platform" button at the top opens the Adopt modal.

### Right panel — Node detail / Topic list
- When a leaf node is selected: list of topics with `status` badge (Draft / Live), "Add Topic", "Edit", "Delete".
- Topic row actions: "Upload Content", "Create Exam".
- "Publish" toggle per topic: `draft` → `live` (visible to linked child) or `live` → `draft` (hidden).

### Adopt modal (Import from Platform)
- Browseable tree of platform `course_path_nodes`.
- **Platform-browse access:** the browse tree is fetched via the existing shared endpoints — `GET /api/categories`, `GET /api/course-path-nodes/category/:category_id`, `GET /api/course-path-nodes/parent/:parent_id`, `GET /api/course-path-nodes/:node_id` — not a parent-specific browse endpoint. These routes accept `parent` role via `require_any_platform_role_or_parent()` and, when the caller's role is `parent` (or `admin`), transparently filter to platform-owned rows only (same code path admin uses to browse the platform tree, not the student visibility filter). Like the P-link code-check GET, these GETs also require `X-CSRF-Token` (shipped quirk, not a REST convention).
- Parent selects a subtree root (e.g., a Grade node).
- "Adopt" button → `POST /api/parent/curriculum/adopt` with `source_node_id`.
- On success: deep copy of the selected subtree + attached topics is created under the parent's curriculum with `owner_type = 'parent'`, topics at `status = 'draft'`.
- Idempotent: if the same subtree root was already adopted, returns 409 Conflict. Parent is shown a message: "You have already adopted this board."
- **What is cloned:** `course_path_nodes` subtree + `topics` rows only.
- **What is NOT cloned:** `topic_contents`, questions, `exam_templates`. Parent uploads their own content after adoption.

**Business rules:**
- BR-PAR-001: Parent can only read/write nodes where `owner_id = parent.idp_sub`.
- BR-PAR-002: Adopted subtree is an independent copy — platform updates to the original do not propagate.
- BR-PAR-003: Adopt is idempotent per subtree root — second adopt returns 409.
- BR-PAR-004: Delete node cascades to child nodes and topics. Not allowed if any topic has active (in-progress) exam sessions.
- BR-PAR-005: Topic `status = 'draft'` is not visible to the linked child. Set to `live` to make it visible.

---

## P-topic — Topic Content Manager

- Topic title (editable).
- Content actions: same Add Content modal as Platform Admin (PDF / Image / Video / Text). PDF and Image trigger the extraction pipeline; Video and Text save instantly.
- IN PROGRESS strip on each topic mirrors the admin UX (status pills, progress bars, Cancel + Retry actions).
- Materialized text rows from extraction show a provenance badge ("Extracted from notes.pdf · page 3").
- All endpoints under `/api/parent/curriculum/...`.
- See `target/requirements/12_content_extraction.md` for full extraction behaviour.

### Indexing status & retry (RAG embedding — Phase 6)

Extraction (above) is a separate, already-visible pipeline from **embedding**: once a `text`-type content item exists (whether typed instantly or materialized by extraction), it is queued in `rag_indexing_outbox` for chunking + `bge-m3` embedding by the worker (`rag_outbox_loop`) before hAITU can ground answers in it. Before this section, that step had zero parent-facing visibility and no retry action — a row that failed 3 times sat permanently and silently stuck. Fixed by mirroring the existing extraction-job status-pill pattern, one level down the pipeline:

- **Grain:** per content item (`content_id`), matching `rag_indexing_outbox`'s primary key — a topic with multiple content items shows one independent pill per item, not one per topic.
- **Status → pill**, sourced directly from `rag_indexing_outbox.status` (5 real states — see `target/requirements/01_data_model.md` BR-DATA-023 / status lifecycle note; do **not** infer "processing" from `locked_at`, and do **not** collapse `retry` into a silent no-pill state, which would reproduce the same invisibility bug this fixes):

  | `rag_indexing_outbox.status` | Pill |
  |---|---|
  | `pending` | Grey "⏱ Queued for indexing" |
  | `processing` | Purple pulsing "🌀 Indexing" (indeterminate activity bar — unlike extraction's upload step, there is no page count to show a real percentage here) |
  | `retry` | "🔁 Retrying (`retry_count`/3)" — visible, not folded into "Indexing" |
  | `failed` | Red "✕ Indexing failed" + a **Retry** button |
  | `done` | Pill clears — content shows with no persistent badge, same as today |

- **Retry action:** `POST /api/parent/curriculum/topic-contents/{content_id}/retry-indexing` (see BR-DATA-023) — visible only on `failed` rows, mirrors the extraction retry button's placement.
- **Polling:** same cadence as the extraction status strip — 2s while any content item in the topic is `pending`/`processing`/`retry`, back off to 10s once idle, stop after 60s once every item is `done` or `failed`.
- **Not in scope:** Platform Admin content has the identical invisible-permanent-failure gap and is not addressed here — tracked as a follow-up for `target/requirements/07_platform_admin.md`, not silently dropped.

**Business rules:**
- BR-PAR-006: Parent can upload to their own topics only (`owner_id = parent.idp_sub`). Wrong owner → 404 (oracle protection).
- BR-PAR-007: File uploads go through the same `StorageBackend` interface as platform content (local disk v1).
- BR-PAR-008a: Parent extraction quota — max 5 concurrent jobs (`status IN ('pending','extracting')`) and max 100 jobs/day. Enforced application-layer via `parent_quota_counters` row lock inside the POST handler TX. APISIX rate limit (50/day per parent token) is a coarse second-line defence.
- BR-PAR-020: Parent can view indexing status and trigger a manual retry only for content under their own topics (`owner_id = parent.idp_sub`) — same 404-oracle ownership pattern as BR-PAR-006. See BR-DATA-023 for the retry mechanics and the cooldown-window abuse guard.

---

## P-exam — Exam Creator

- Lists all `exam_templates` where `owner_type = 'parent'` and `owner_id = parent.idp_sub`.
- "Create Exam" → modal with: title, linked node (optional), time limit, pass mark.
- Questions tab: add MCQ questions (stem + 4 options + correct answer) or paragraph questions.
- "Publish" toggle: draft → live (available for the linked child to take).

**Business rules:**
- BR-PAR-008: Parent can create, edit, and delete their own exam templates freely.
- BR-PAR-009: Published exams (`status = 'live'`) appear as "Take Exam" on the student's S-nav for this parent's content.
- BR-PAR-010: Deleting a published exam template is blocked if there are completed `exam_sessions` for it. Parent must archive instead.
- BR-PAR-011: No instructor review gate — parent is solely responsible for exam quality.

---

## P-results — Child Results

- Scope: `exam_sessions` where:
  - `user_id = child.idp_sub`
  - `exam_templates.owner_id = parent.idp_sub` (parent's own exams only)
  - Active `parent_child_links` record exists for this parent-child pair.
- Table: exam name, date taken, score, pass/fail. Essays with pending grading show "Grading in progress" or "Pending review" in the score column (Phase 2 UI).
- Clicking a row: per-question breakdown (student's answer, correct answer, points, `grading_status` for essays).

**Business rules:**
- BR-PAR-012: Parents do NOT see results for platform exams the child has taken.
- BR-PAR-013: Results access is revoked immediately if the `parent_child_links` record is revoked.

---

## P-essay-grading — Essay Grade Review

Parents are the grading owners for their private exams. They see:
- `ai_score`, `ai_feedback`, and (owner-only) `ai_rationale` (per-criterion breakdown) for each graded essay.
- `grading_status` for each essay question.
- A "Confirm" button (review_first mode) and an "Override" form (all modes) per essay.

### Grading modes

- **`auto_release` (default):** The AI score is immediately visible to the student after grading.
  The parent can override at any time. If the child disputes, the parent sees a "Dispute" flag and
  can confirm or override.
- **`review_first` (opt-in):** Set on the exam template. The AI score is hidden from the student
  until the parent confirms. The parent sees the AI score + per-criterion rationale in P-results
  and chooses to confirm or override before the student sees anything.

The parent sets `essay_grading_mode` when creating or editing an exam template in P-exam.

### Override flow (API)

`PATCH /api/exam-sessions/session/{session_id}/questions/{question_id}/grade`
(CSRF + `X-Current-Role: parent`). Body: `{ "score": float, "feedback": "..." }`.
Effect: `override_score` stored; `earned_points` updated; session score recomputed.
Allowed when `exam_templates.owner_id = parent.idp_sub` (own exams only — BR-SEC-012).

### Confirm-grade flow (API, review_first only)

`POST /api/exam-sessions/session/{session_id}/questions/{question_id}/confirm-grade`
(CSRF + `X-Current-Role: parent`). Effect: `earned_points = ai_score`; `grading_status →
'finalized'`; student can now see the score.

**Business rules:**
- BR-PAR-017: Parents can only override essay grades for exams where `exam_templates.owner_id = parent.idp_sub`. Platform exam grading is outside parent scope.
- BR-PAR-018: When a student disputes an essay grade (`grading_status = 'disputed'`), the parent sees the dispute flag in P-results. The parent can confirm the original AI grade (confirm-grade) or override with a different score.
- BR-PAR-019: The `ai_rationale` (per-criterion breakdown from the LLM) is visible to the parent only — never returned to the student. This prevents coaching answers based on criterion feedback before a dispute.

---

## P-link — Link Child

- Input field for the child's link code (8-char, uppercase `A–Z2–9`, 72h TTL — see `target/requirements/03_student.md` S-profile).
- On entry, validate via `GET /api/parent-link-codes/{code}` and show the child's name for confirmation. **This GET requires `X-CSRF-Token`** (live route has `Depends(validate_csrf)` despite being a read) — a quirk of the shipped implementation, not a REST convention to follow elsewhere.
- "Link" button → `POST /api/parent-child-links` with body `{ "invite_code": "<code>" }` (CSRF required).
- On success (201): child appears in the child selector strip on P-home.
- Error states, matching live semantics exactly:
  - **404** — unknown code → "Invalid code".
  - **410** — code expired or already used → "Code expired or already used".
  - **409** — this parent is already actively linked to the code's child → "This child is already linked".
  - **422** — parent already has 10 active child links (BR-PAR-016) → "Maximum of 10 children".

**Business rules:**
- BR-PAR-014: A link code is single-use — redeeming it marks it used. A student may only have one *active* (unused, unexpired) code at a time; generating a new one deactivates the prior one. A revoked parent-child pair can be re-linked via a fresh code.
- BR-PAR-015: A parent can be linked to multiple children.
- BR-PAR-016: Maximum 10 *active* children per parent account — 422 if exceeded on redemption. Revoked links do not count against the cap.

---

## Parent API Endpoints

> Link-code redemption lives at its own top-level paths, not nested under the children collection
> — kept as shipped rather than moved to match an earlier draft's nested-alias shape (see
> `target/requirements/03_student.md` for the student-side link-code endpoints).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/parent-link-codes/:code` | Validate a link code, return child info for confirmation. **Requires `X-CSRF-Token`** even though it's a GET (shipped quirk). 404 unknown / 410 expired-or-used. |
| `POST` | `/api/parent-child-links` | Redeem a link code — body `{ invite_code }`. 201 on success; 404 unknown code, 410 expired/used, 409 already linked, 422 max-10 (BR-PAR-016) |
| `GET` | `/api/parent/children` | List active linked children (`[{child_sub, first_name, last_name, linked_at}]`) |
| `DELETE` | `/api/parent/children/:child_sub/link` | Revoke link to a child (sets `revoked_at`); 404 if no active link |
| `GET` | `/api/parent/curriculum/nodes` | List parent's curriculum root nodes |
| `GET` | `/api/parent/curriculum/nodes/:node_id` | Get node detail + children |
| `POST` | `/api/parent/curriculum/nodes` | Create a new node |
| `PATCH` | `/api/parent/curriculum/nodes/:node_id` | Rename a node |
| `DELETE` | `/api/parent/curriculum/nodes/:node_id` | Delete a node (cascade) |
| `POST` | `/api/parent/curriculum/adopt` | Adopt a platform subtree (clone) |
| `GET` | `/api/parent/curriculum/nodes/:node_id/topics` | List topics for a node |
| `POST` | `/api/parent/curriculum/nodes/:node_id/topics` | Create a topic |
| `PATCH` | `/api/parent/curriculum/topics/:topic_id` | Update topic (title, status) |
| `DELETE` | `/api/parent/curriculum/topics/:topic_id` | Delete a topic |
| `GET` | `/api/parent/curriculum/topics/:topic_id/content` | List content items for a topic, each including its RAG indexing `status`/`last_error` joined from `rag_indexing_outbox` (drives the status pills in P-topic) |
| `POST` | `/api/parent/curriculum/topics/:topic_id/content` | Create video URL or text content (instant) |
| `PATCH` | `/api/parent/curriculum/topic-contents/:content_id` | Update a content item (title/order/description/url/text) — note the path is `topic-contents`, not nested under `topics/:topic_id` |
| `DELETE` | `/api/parent/curriculum/topic-contents/:content_id` | Delete a content item |
| `POST` | `/api/parent/curriculum/topic-contents/:content_id/retry-indexing` | Reset a `failed` (or stuck) indexing row to `pending` via the BR-DATA-020 upsert-with-reset (BR-PAR-020 / BR-DATA-023); 404 if not owned, 429 inside the cooldown window |
| `POST` | `/api/parent/curriculum/topics/:topic_id/extraction-jobs` | Upload PDF/image for extraction (multipart, ≤50MB, 1 file/request, parent-quota gated, requires `Idempotency-Key` header) |
| `GET` | `/api/parent/curriculum/topics/:topic_id/extraction-jobs` | List active + recent extraction jobs |
| `GET` | `/api/parent/curriculum/extraction-jobs/:job_id` | Job detail |
| `DELETE` | `/api/parent/curriculum/extraction-jobs/:job_id` | Cancel job |
| `POST` | `/api/parent/curriculum/extraction-jobs/:job_id/retry` | Retry a failed job |
| `GET` | `/api/parent/exams` | List parent's exam templates |
| `POST` | `/api/parent/exams` | Create an exam template |
| `PATCH` | `/api/parent/exams/:exam_id` | Update exam template |
| `DELETE` | `/api/parent/exams/:exam_id` | Delete an exam template |
| `POST` | `/api/parent/exams/:exam_id/questions` | Add a question |
| `PATCH` | `/api/parent/exams/:exam_id/questions/:q_id` | Update a question |
| `DELETE` | `/api/parent/exams/:exam_id/questions/:q_id` | Delete a question |
| `GET` | `/api/parent/children/:child_idp_sub/exam-sessions` | Child's exam results (parent-owned only) |
| `GET` | `/api/parent/children/:child_idp_sub/exam-sessions/:session_id` | Per-question breakdown (incl. `ai_rationale` for essays) |
| `POST` | `/api/exam-sessions/session/{session_id}/questions/{question_id}/dispute` | Dispute essay grade on behalf of linked child (parent-owned exam) |
| `POST` | `/api/exam-sessions/session/{session_id}/questions/{question_id}/confirm-grade` | Confirm AI grade (review_first mode; parent-owned exam only) |
| `PATCH` | `/api/exam-sessions/session/{session_id}/questions/{question_id}/grade` | Override AI essay grade (parent-owned exam only) |
| `PATCH` | `/api/parent/exams/:exam_id` | Update exam template incl. `essay_grading_mode` |
