# Current API Contracts Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | f6bdf2b (G4-patch-2 + G4-patch-3 — pattern-analysis inline-stream fix + stream-failure hardening, 2026-07-01) |
| haisir-frontend | 302ac06 (G4-patch — Take Exam nav + streaming review chat + markdown rendering, 2026-07-01) |
| haisir-deploy | 457de26 (G4-patch — pattern-analysis route timeouts fixed for streaming, 2026-07-01) |

> Next session: run `git diff f6bdf2b..HEAD` in haisir-backend, `git diff 302ac06..HEAD` in haisir-frontend, and `git diff 457de26..HEAD` in haisir-deploy to see only what changed since this snapshot.

---

## Auth & User

> **BR-SEC-006 (enforced as of Phase 1c-pre):** `X-Current-Role` is required on all role-gated endpoints. Missing header returns `400 "X-Current-Role header required"`. The three onboarding endpoints below are explicitly exempt (use lenient dependency that defaults to `roles[0]`).

> **Token introspection (on by default as of bb69798):** After JWKS validation, `verify_token` calls `TokenIntrospectionClient` (RFC 7662). `active: false` → 401 `"Token has been revoked"`. Keycloak unreachable → 503 `"Authentication service unavailable"`. Disable with `KEYCLOAK__INTROSPECTION_ENABLED=false`.

### GET /api/auth/csrf
- Purpose: Return a CSRF token
- Auth: None (public)
- Response: `{ csrfToken: string }`

### GET /api/users/me
- Purpose: Return current user profile from JWT
- Auth: Any authenticated user — **exempt from `X-Current-Role` requirement** (lenient dependency)
- Response: id, sub, name, email, email_verified, roles[], current_role, onboarding_completed_at

### POST /api/users/me/assign-role
- Purpose: Assign a role to the current user via Keycloak Admin API
- Auth: Any authenticated user — **exempt from `X-Current-Role` requirement** (lenient dependency)
- Request: `{ role: "student" | "parent" }`
- Response: `{ message: string }`

### PATCH /api/users/me/onboarding-complete
- Purpose: Mark onboarding as complete; sets onboarding_completed_at timestamp
- Auth: student or parent only — **exempt from `X-Current-Role` requirement** (lenient dependency); enforces student/parent via inline role check (`403` if other role)
- Request: `{}`
- Response: `{ onboarding_completed_at: datetime }`

### POST /api/students/me/profile
- Purpose: Create student profile
- Auth: student
- Request: first_name, last_name, phone?, avatar_url?, grade?, subjects?
- Response: id, idp_sub, first_name, last_name, phone, avatar_url, grade, subjects

### POST /api/parents/me/profile
- Purpose: Create parent profile
- Auth: parent
- Request: first_name, last_name, phone?
- Response: id, idp_sub, first_name, last_name, phone

---

## Parent–Child Linking

### POST /api/parent-child-links
- Purpose: Link a parent to a child using an invite code
- Auth: parent
- Request: `{ invite_code: string }`
- Response: id, parent_sub, child_sub, created_at

### GET /api/parent-link-codes/{code}
- Purpose: Look up a parent link code
- Auth: parent
- Response: id, code, child_sub, created_at, expires_at, is_used

> Note: no endpoint yet to generate a new link code from the student side. /join-school and /link-child UI flows not yet built.

---

## Classes (outside current target increment — retained)

### GET /api/classes/by-invite-code/{code}
- Purpose: Look up a class node by invite code
- Auth: student
- Response: id, code, course_path_node_id, created_at, expires_at

---

## Categories

### GET /api/categories
- Purpose: List all categories
- Auth: student, instructor, admin (any platform role)
- Response: array of `{ id, name, path_type, description }`
- Note: auth guard changed from `require_instructor_or_student` to `require_any_platform_role` so admin can reach the board selector sidebar.

### GET /api/categories/{category_id}
- Purpose: Get single category
- Auth: student, instructor, admin (any platform role)
- Response: id, name, path_type, description

### POST /api/categories
- Purpose: Create a category
- Auth: admin (admin outside current increment)
- Request: name, path_type, description?
- Response: id, name, path_type, description

### PATCH /api/categories/{category_id}
- Purpose: Update category description
- Auth: admin (admin outside current increment)
- Request: `{ description: string }`
- Response: updated category object

---

## Course Path Nodes

### GET /api/course-path-nodes/category/{category_id}
- Purpose: Get nodes for a category; optionally filter by parent_id
- Auth: student, instructor, admin
- Query: parent_id (optional)
- Response: array of node objects
- Note: BR-DATA-003 enforced — student sees platform + linked-parent nodes; admin sees platform-only; instructor sees all.

### GET /api/course-path-nodes
- Purpose: Get nodes filtered by category_id and node_type
- Auth: student, instructor, admin
- Query: category_id, node_type
- Response: array of node objects

### GET /api/course-path-nodes/parent/{parent_id}
- Purpose: Get child nodes of a given node
- Auth: student, instructor, admin
- Query: node_type (optional)
- Response: array of node objects

### GET /api/course-path-nodes/{node_id}
- Purpose: Get a single node
- Auth: student, instructor, admin
- Response: id, name, node_type, category_id, parent_id, order, owner_type

### POST /api/course-path-nodes
- Purpose: Create a node
- Auth: admin (admin outside current increment)
- Request: name, node_type, category_id, parent_id?, **order**? (field name is `order`, not `position`)
- Response: node object
- Errors: **409** if (A) the new node_type already appears in an ancestor node on the same branch (ancestor-type exclusion), or (B) existing platform-owned siblings at the same level use a different type (sibling-type consistency). Both checks run before INSERT.

### GET /api/course-path-nodes/path-to-root/{node_id}
- Purpose: Get ancestor path from a node to the root
- Auth: student, instructor, admin
- Response: array of node objects (root → leaf order)
- Note: student sees only platform nodes + parent-owned nodes with active link (BR-DATA-003); admin sees platform-only (BR-SEC-005); instructor sees all. Returns 404 if the starting node is invisible to the caller.

### GET /api/course-path-nodes/tree/{category_id}
- Purpose: Return full nested tree for a category in a single query (no N+1)
- Auth: student, instructor, admin (any platform role)
- Response: array of root `CoursePathNodeRead` objects with `children` populated recursively
- Note: assembles flat DB result into nested tree in Python; role-dispatches visibility per Phase 1a rules (admin → platform_only, student → visible, instructor → get_by_category).

### PATCH /api/course-path-nodes/{node_id}
- Purpose: Rename and/or reorder a platform-owned node
- Auth: admin only
- Request: `{ name?: string (1–255 chars), order?: int }`
- Response: updated `CoursePathNodeRead`
- Errors: 404 if node not found or `owner_type != 'platform'` (indistinguishable — oracle protection); 422 if name is empty string; no-op if both fields are null.

### DELETE /api/course-path-nodes/{node_id}
- Purpose: Hard-delete a platform-owned node and its entire subtree
- Auth: admin only
- Response: 204 No Content
- Errors: 404 if not found or not platform-owned; **409 if any topic in the subtree has `status = 'live'` (checked first, via recursive CTE)**; 409 if any subtree node has a `pending` or `ongoing` exam session
- Note: 12-step cascade in a single transaction: `exam_session_questions` → `exam_sessions` → `exam_template_questions` → `exam_templates` → `assessment_answers` → `assessment_attempts` → `assessments` → `topic_contents` → `topics` → `course_path_nodes`.

---

## Topics

### GET /api/topics/{course_path_node_id}
- Purpose: List topics for a node
- Auth: student, instructor, admin
- Response: array of `{ id, title, course_path_node_id, order, status, owner_type }`
- Note: student sees platform + linked-parent topics; admin sees platform-only; instructor sees all (BR-DATA-003 / BR-SEC-005 enforced).

### POST /api/topics
- Purpose: Create a topic
- Auth: admin (admin outside current increment)
- Request: title, course_path_node_id, **status** (`"draft"` | `"live"`, required), order?
- Response: topic object

### PATCH /api/topics/{topic_id}
- Purpose: Partial-update a platform-owned topic's title, order, and/or status
- Auth: admin only (CSRF required)
- Request: `{ title?: string (min 1), order?: int, status?: "draft" | "live" }`
- Response: updated `TopicRead` (id, title, course_path_node_id, order, status, owner_type)
- Errors: 404 if not found or `owner_type != 'platform'` (indistinguishable — oracle protection); 400 if title is empty string; no-op early return if all fields are null

### DELETE /api/topics/{topic_id}
- Purpose: Hard-delete a platform-owned topic and all FK-dependent rows
- Auth: admin only (CSRF required)
- Response: 204 No Content
- Errors: 404 if not found or not platform-owned; cascade order: `assessment_answers` → `assessment_attempts` → `assessments` → `topic_contents` → `topics`

---

## Topic Contents

### GET /api/topics-contents/{topic_id}
- Purpose: List content items for a topic
- Auth: student | instructor | admin (any platform role)
- Response: array of `{ id, topic_id, content_type, title, url, text, order, description, source_extraction_job_id, provenance: { source_filename, page_no } | null }` — `provenance` is populated via LEFT JOIN on `extraction_job_audit` when the item was produced by the extraction worker; `null` for manually-created items
- Note: visibility scoped by the parent topic's owner_type — student sees only items whose parent topic is visible to them.

### GET /api/topics-contents/{content_type}/{topic_id}
- Purpose: Serve a media file for a topic (PDF, video, etc.)
- Auth: student | instructor | admin (any platform role)
- Response: FileResponse (binary)
- Note: stored files follow the path `topics/{content_type}/{filename}` on disk (e.g. `topics/pdf/filename.pdf`).

### POST /api/topics-contents
- Purpose: Create a content item
- Auth: admin
- Request: topic_id, content_type, title, url?, text?, order, description?
- Response: content object
- Validation: `url` field — if content_type is `video`: must be `https://` scheme and hostname in allowlist (`youtube.com`, `www.youtube.com`, `youtu.be`, `vimeo.com`, `www.vimeo.com`); local paths (no scheme/netloc) pass through; returns 422 on failure.
- WAF: OWASP CRS rule 931130 is suppressed for `POST /api/topics-contents/` to allow external video URLs in the body (Coraza SecRule chain in `03-secured-api.json`); SSRF/XSS risk mitigated by backend allowlist.

### PATCH /api/topics-contents/{content_id}
- Purpose: Partially update a platform-owned content item
- Auth: admin (X-Current-Role: admin), CSRF required
- Request: any of `title`, `order`, `description`, `url`, `text` (all optional; `content_type` is immutable)
- Response: updated content object (200); empty payload returns current state unchanged
- Errors: 404 if not found or not platform-owned; 403 if non-admin or missing CSRF; 400 if `url` fails allowlist validation (ValueError → HTTP 400)
- Validation: same `url` allowlist rules as POST above.

### DELETE /api/topics-contents/{content_id}
- Purpose: Delete a platform-owned content item
- Auth: admin (X-Current-Role: admin), CSRF required
- Response: 204 No Content
- Errors: 404 if not found or not platform-owned; 403 if non-admin or missing CSRF

---

## Admin Extraction Jobs

> All endpoints require `X-Current-Role: admin` and CSRF on mutating methods. The upload route passes through a dedicated APISIX plugin config (`04-secured-api-upload.json`) which raises the Coraza body size limit to 50 MB.

### POST /api/admin/topics/{topic_id}/extraction-jobs
- Purpose: Upload a PDF or image file for extraction; creates an `extraction_jobs` row with `status='pending'`
- Auth: admin
- Request: multipart/form-data — `file` (binary), `idempotency_key` (UUID string)
- Headers: `X-Force-Reextract: true` (optional) to bypass SHA dedup
- Response: `ExtractionJobRead` (201)
- Errors: 404 if topic not found or not platform-owned; 409 if SHA dedup match (same file already queued/done for this topic); 409 if idempotency replay returns the existing job
- Note: file saved to `STORAGE_ROOT/extraction_sources/{idp_sub}/{uuid}_{filename}` before DB insert; MIME-sniffed (not trusted from Content-Type header)

### GET /api/admin/topics/{topic_id}/extraction-jobs
- Purpose: List extraction jobs for a topic, newest first
- Auth: admin
- Response: array of `ExtractionJobRead`; supports ETag/304
- Note: includes derived `progress` field (0–100 percentage)

### GET /api/admin/extraction-jobs/{job_id}
- Purpose: Get a single extraction job detail
- Auth: admin
- Response: `ExtractionJobRead` (200) or 404

### DELETE /api/admin/extraction-jobs/{job_id}
- Purpose: Cancel an extraction job
- Auth: admin, CSRF required
- Response: updated `ExtractionJobRead`
- Behaviour: `pending` → hard cancel (status=`cancelled`, file deleted); `extracting` → soft cancel (sets `cancel_requested=true`, worker reads flag between pages)
- Errors: 404 if not found; 409 if job is already terminal (`done`/`cancelled`/`upload_failed`)

### POST /api/admin/extraction-jobs/{job_id}/retry
- Purpose: Re-queue a failed extraction job
- Auth: admin, CSRF required
- Request: `{ idempotency_key: UUID }` (new key to avoid idempotency collision)
- Response: new `ExtractionJobRead` (201)
- Errors: 404 if not found; 409 if job is not in `extraction_failed` state; 422 if source file no longer on disk

### GET /api/admin/system/workers
- Purpose: List all registered worker heartbeats with liveness annotation
- Auth: admin
- Response: `{ workers: [{ worker_id, started_at, last_seen, job_id, is_stale }], active_count, stale_count }` where `is_stale = (now - last_seen) > 60 s` (BR-EXT-031; defined by `_STALE_THRESHOLD_SECONDS = 60` in `extraction_service.py`)

---

## Parent Extraction Jobs

> All endpoints require `X-Current-Role: parent` and CSRF on mutating methods. Prefix: `/api/parent/curriculum`. APISIX routes these through the same upload plugin config as admin (50 MB body limit). Per-parent quota: max 3 concurrent jobs and max 20 daily jobs (hardcoded in `extraction_service.py`).

### POST /api/parent/curriculum/topics/{topic_id}/extraction-jobs
- Purpose: Upload a PDF or image file for extraction on a parent-owned topic; enforces quota, SHA-256 dedup, topic ownership
- Auth: parent, CSRF required
- Request: multipart/form-data — `file` (binary); `Idempotency-Key` header (UUID, required)
- Headers: `X-Force-Reextract: true` (optional) to bypass SHA dedup
- Response: `ExtractionJobRead` (201)
- Errors: 400 if `Idempotency-Key` missing or invalid UUID; 404 if topic not found or not owned by calling parent; 409 if SHA dedup match (file already queued/done); 413 if file > 50 MB; 415 if unsupported MIME type; 429 if concurrent or daily quota exceeded (body: `{ detail: "Concurrent job limit exceeded" | "Daily job limit exceeded" }`)
- Note: quota atomically incremented on job insert (`INSERT … ON CONFLICT DO UPDATE` — no read-modify-write race); decremented when job completes (finalize) or is cancelled

### GET /api/parent/curriculum/topics/{topic_id}/extraction-jobs
- Purpose: List the calling parent's extraction jobs for a topic, filtered to `created_by = caller`
- Auth: parent, CSRF required
- Response: `{ jobs: ExtractionJobRead[] }`; supports ETag/304

### GET /api/parent/curriculum/extraction-jobs/{job_id}
- Purpose: Get a single extraction job owned by the calling parent
- Auth: parent, CSRF required
- Response: `ExtractionJobRead` (200)
- Errors: 404 if not found **or** owned by another parent (enumeration prevention — BR-SEC-002)

### DELETE /api/parent/curriculum/extraction-jobs/{job_id}
- Purpose: Cancel a pending or extracting job owned by the calling parent
- Auth: parent, CSRF required
- Response: updated `ExtractionJobRead` (200) or `{ detail: "cancellation requested" }` for extracting jobs
- Behaviour: `pending` → hard cancel (status=`cancelled`) + quota concurrent counter decremented; `extracting` → soft cancel (`cancel_requested=true`); `done` → 404 (hidden); terminal non-done statuses (`extraction_failed`, `cancelled`, `upload_failed`) → 409
- Errors: 404 if not found, belongs to another parent, or status is `done`; 409 if already in a non-cancellable terminal status

### POST /api/parent/curriculum/extraction-jobs/{job_id}/retry
- Purpose: Re-queue a failed extraction job (`extraction_failed`) owned by the calling parent
- Auth: parent, CSRF required
- Request: `Idempotency-Key` header (UUID, required — new key for the retry)
- Response: `ExtractionJobRead` (201)
- Errors: 400 if `Idempotency-Key` missing/invalid or job not in `extraction_failed` status; 404 if not found, belongs to another parent, or source file has been purged

---

## Questions

### GET /api/questions
- Purpose: List questions by tags
- Auth: student, instructor (instructor outside current increment)
- Query: tags[] (required)
- Response: array of `QuestionReadStudent` objects — `rubric` and `model_answer` are intentionally excluded (internal AI-grading fields; not safe to expose in public question bank)

### GET /api/questions/assessment/{assessment_id}
- Purpose: Get questions for a deprecated assessment
- Auth: student
- Response: `{ questions[], paragraph_questions[] }`

### POST /api/questions
- Purpose: Create a question
- Auth: instructor (outside current target increment)
- Request: question_text, question_type, options[], correct_answers[], explanation, difficulty, tags?, image_url?
- Response: question object

---

## Paragraph Questions

### POST /api/paragraph-questions
- Purpose: Create a paragraph question group
- Auth: instructor (outside current target increment)
- Request: content, title, questions[], paragraph_type, tags?, difficulty?
- Response: paragraph question object

### GET /api/paragraph-questions/{paragraph_id}
- Purpose: Get a paragraph question
- Auth: student
- Response: paragraph question object

### GET /api/paragraph-questions/{paragraph_id}/questions
- Purpose: Get paragraph + all its questions
- Auth: student
- Response: paragraph data with `questions[]`

---

## Assessments (deprecated — routes still live)

> Deprecated. Superseded by exam_templates. Retained as-is; no new development against these endpoints.

### GET /api/assessments/topic/{topic_id}
### POST /api/assessments
### POST /api/assessments/start
### POST /api/assessments/submit/{attempt_id}
### POST /api/assessments/submit-all/{attempt_id}
### GET /api/assessments/{attempt_id}
### GET /api/assessments/{assessment_id}/attempts
### GET /api/assessments/result/{attempt_id}
### GET /api/assessments/unfinished-attempt/{assessment_id}

---

## Answers (orphaned — routes still live)

> Orphaned from an earlier iteration. No active write path from UI. Retained as-is.

### GET /api/answers/{answer_id}
### POST /api/answers

---

## Exam Templates

### GET /api/exams/template
- Purpose: List exam templates for a node
- Auth: instructor (outside current target increment)
- Query: node_id
- Response: array of template objects

### POST /api/exams/template
- Purpose: Create an exam template
- Auth: instructor (outside current target increment)
- Request: course_path_node_id, title, description?, mode, ruleset?, duration_minutes?, passing_score?
- Response: template object

### PATCH /api/exams/template/{template_id}
- Purpose: Update an exam template
- Auth: instructor (outside current target increment)
- Request: template fields
- Response: updated template object

### DELETE /api/exams/template/{template_id}
- Purpose: Delete an exam template
- Auth: instructor (outside current target increment)
- Response: `{ message: string }`

### POST /api/exams/template-question
- Purpose: Add a question to a template
- Auth: instructor (outside current target increment)
- Request: exam_template_id, question_id, order, points
- Response: link object

### GET /api/exams/template/{template_id}/questions-with-details
- Purpose: Get all questions for a template with full question data
- Auth: student, instructor
- Response: `{ template_id, title, description, questions[], paragraph_questions[] }`

### GET /api/exams/template/{template_id}/summary
- Purpose: Get question count and mark breakdown for a template
- Auth: student, instructor
- Response: total_questions, total_marks, type_breakdown[]

### POST /api/exams/{node_id}/static
- Purpose: Create a static exam template with questions in one call
- Auth: instructor (outside current target increment)
- Request: title, description, mode, duration_minutes, passing_score, `essay_grading_mode?: 'auto_release' | 'review_first'` (template-level, defaults to `'auto_release'`), items[] — each item supports: `working_required: bool` (problem_solving), `essay_subtype: string | null` (essay), `penalty_matching: bool` (matching), `model_answer: str | null` (essay only — prose shown to students after grade release), `rubric: object | null` (essay only — custom grading rubric JSONB), `auto_grade_essay: bool` (essay only)
- Response: template object

### PATCH /api/exams/{node_id}/static
- Purpose: Upsert questions on a static template
- Auth: instructor (outside current target increment)
- Request: template_id, questions[], duration_minutes?, passing_score? — each question supports: `working_required: bool`, `essay_subtype: string | null`, `penalty_matching: bool`, `clear_essay_subtype: bool` (explicit null-clear for essay_subtype), `model_answer: str | null`, `clear_model_answer: bool` (explicit null-clear), `rubric: object | null`, `clear_rubric: bool` (explicit null-clear), `auto_grade_essay: bool`
- Response: updated template with questions

---

## Exam Sessions (Student)

### GET /api/exams/course/{node_id}
- Purpose: List active exam templates for a node
- Auth: student, instructor, admin (any platform role); visibility enforced per BR-DATA-003
- Response: array of `{ id, course_path_node_id, title }`

### POST /api/exam-sessions/session/create
- Purpose: Create an exam session for the current student
- Auth: student
- Query: `exam_template_id` (UUID, required)
- Request: (no body)
- Response: session object (id, user_id, exam_template_id, course_path_node_id, mode, status, created_at)
- Errors: 404 if template not found or not visible; 400 if static template has no questions

### GET /api/exam-sessions/session/{session_id}/questions
- Purpose: Get questions for an exam session
- Auth: student (session owner) — returns 404 if session does not belong to the caller
- Response: `{ questions[], paragraph_questions[], duration_minutes: int | null }` with point allocations; images base64-encoded. Each question includes: `shuffle_seed: int | null` (matching only — frontend uses this with `seededShuffle` LCG to replicate right-column ordering); `working_required: bool` (problem_solving only — when true, UI renders a working textarea); `essay_subtype: string | null` (essay only — one of `analytical | critical | extended | narrative | reflective | short`). Each option includes `side: "left" | "right" | null` (matching only).

### POST /api/exam-sessions/session/{session_id}/answer
- Purpose: Record or update a single answer during an active session
- Auth: student (session owner)
- Request: `{ question_id: UUID, user_answer: string, working_text?: string }` — `working_text` (problem_solving only, optional) stored to `exam_session_questions.working_text`; omitting it does not clear a previously saved value (only non-null values are persisted)
- Response: `{ message: "Answer recorded" }`

### POST /api/exam-sessions/session/{session_id}/submit
- Purpose: Submit session; scores non-essay questions inline; enqueues `essay` questions (where `auto_grade_essay=true`) to `essay_grading_jobs`; sets `status = 'grading_pending'` if any jobs were enqueued, otherwise `'completed'`; calls `recompute_score()` atomically after all writes
- Auth: student (session owner), CSRF required
- Request: (no body)
- Response: session object including `sessionStatus: 'completed' | 'grading_pending'`; if `'completed'`, includes full per-question results and final score; if `'grading_pending'`, score reflects non-essay points only
- Errors: 409 if session already `'completed'` or `'grading_pending'`
- WAF: protected by dedicated APISIX route `18-api-exam-session-submit.json` (PL2 Coraza); `text_answer` (matching questions submit JSON pair arrays) and `working_text` (may contain mathematical notation) have targeted CRS rule exclusions for RCE/SQLi/XSS false positives; session cookies exempt from rules 942440/932220; all other CRS rules remain active

### GET /api/exam-sessions/session/{session_id}/answers
- Purpose: Get the graded review payload (S05, called by the frontend `/exam/[session_id]/review` page) for a completed or failed session
- Auth: student (session owner); exam owner (parent who owns the template, or admin) additionally receives `ai_rationale` per essay question
- Response: `ExamReviewPayload { session_id, template_title, subject, board, score, total_marks, correct_count, wrong_count, skipped_count, total_count, items: ExamReviewItem[] }`
  - `ExamReviewItem { question_id, question_text, question_type, options, correct_answer_options: str[] (option IDs), user_answer_options: str[] (option IDs), is_correct, points, earned_points, explanation, ai_feedback, model_answer, grading_status, ai_rationale }` — **reworked 2026-07-01** from the prior `ExamSessionAnswer`/`ExamSessionAnswerResponse` shapes: `question` renamed to `question_text`, answer options are now ID lists rather than full option objects, `earned_points` rounded to 2dp, and `passed`/`passing_ratio`/`pending_review_count` were dropped in favour of `correct_count`/`wrong_count`/`skipped_count`
  - `grading_status: str | null` — for essay questions: `pending | ai_graded | released | finalized | overridden | disputed | error`; null for non-essay
  - `ai_feedback: str | null` — visible when `grading_status in ('released','finalized','overridden')`; null otherwise
  - `model_answer: str | null` — the prose model answer set by the exam author; visible to students only when `grading_status in ('released','finalized','overridden')`; null otherwise
  - `explanation: str | null` — the mark scheme/rubric notes set by the exam author; for essay questions gated to same released grade statuses; for non-essay questions always returned
  - `ai_rationale: dict | null` — full LLM output; visible only to exam owner; always null for student callers
- Errors: 403 if session not owned or `status not in ('completed', 'failed')` (**tightened 2026-07-01** — was 400 for any incomplete attempt, now also 403 and now permits `failed` sessions to be reviewed)
- Side effect: calls `_finalize_session()` — sets `finished_at` if unset; only transitions `status` `grading_pending → completed` (**bug fix 2026-07-01**: previously any non-`completed` status, including `failed`, was unconditionally overwritten back to `completed`)

### POST /api/exam-sessions/session/{session_id}/questions/{question_id}/dispute
- Purpose: Student disputes a released AI grade on an essay question
- Auth: student (session owner), CSRF required
- Pre-condition: `grading_status == 'released'`
- Effect: `grading_status → 'disputed'`
- Response: 204 No Content
- Errors: 403 if not session owner; 404 if session or question not found; 409 if `grading_status != 'released'`

### POST /api/exam-sessions/session/{session_id}/questions/{question_id}/confirm-grade
- Purpose: Exam owner confirms the AI-assigned grade as final without change
- Auth: parent or admin, CSRF required; ownership check: parent → `caller.sub == template.owner_id`; admin → `X-Current-Role: admin`
- Pre-condition: `grading_status in ('ai_graded', 'disputed')`
- Effect: `earned_points = ai_score`; `is_correct = earned_points / points >= 0.5`; `grading_status → 'finalized'`; `recompute_score()` called on the session
- Response: `{ grading_status, earned_points, is_correct }`
- Errors: 403 if not exam owner; 404; 409 if precondition not met

### PATCH /api/exam-sessions/session/{session_id}/questions/{question_id}/grade
- Purpose: Exam owner overrides the AI-assigned grade with a manual score and feedback
- Auth: parent or admin, CSRF required; same ownership check as confirm-grade
- Pre-condition: `grading_status != 'pending'`
- Request: `{ score: float, feedback: str }`
- Validation: `0 <= score <= question.points`
- Effect: `override_score`, `override_feedback`, and `earned_points` all set to `body.score`; `is_correct = score / points >= 0.5`; `grading_status → 'overridden'`; `graded_by = user.sub`; `graded_at = now()`; `recompute_score()` called
- Response: `{ grading_status, earned_points, override_score, override_feedback }`
- Errors: 403 if not exam owner; 400 if score out of range; 404; 409 if `grading_status == 'pending'`

### GET /api/exam-sessions/session/unfinished/{exam_template_id}
- Purpose: Check for an existing unfinished session (resume support)
- Auth: student
- Response: session object or empty

### GET /api/exam-sessions/session/all/{exam_template_id}
- Purpose: List all sessions for the current student for a template
- Auth: student
- Query: limit (default 5)
- Response: array of session objects with score as percentage

---

## Courses

### GET /api/courses/enrolled
- Purpose: Stub — returns None
- Auth: student

---

## Admin

### GET /api/admin/board-stats
- Purpose: Return per-board topic statistics and platform-wide aggregate totals for the admin dashboard
- Auth: admin only (CSRF not required — GET)
- Response: `{ boards: [{ id, name, live_topics, draft_topics, total_topics }], platform_totals: { live_topics, draft_topics, total_topics } }`
- Note: single LEFT JOIN query `categories → course_path_nodes (owner_type='platform') → topics (owner_type='platform')`, grouped by category. Categories with zero topics appear with zero counts. Frontend maps response to `AdminDashboardStats` shape (board_id/board_name aliases, overview.platform_boards = boards.length). `response_model` removed from FastAPI decorator (dd7da7f) — output shape unchanged.

---

## Student Dashboard

### GET /api/student/dashboard
- Purpose: Return platform root nodes and parent-link status for the logged-in student
- Auth: student (`X-Current-Role: student`; wrong role → 403; missing header → 400)
- Note: uses `Depends(validate_csrf)` — `X-CSRF-Token` required despite being a GET (deviation from spec which said GET-only needs no CSRF)
- Response: `StudentDashboardRead { platform_nodes: PlatformNodeCard[], has_parent_link: bool, weak_topics: WeakTopic[] }`
  - `PlatformNodeCard { id: UUID, name: str, node_type: str, topic_count: int, owner_type: str, children: list[PlatformNodeCard] }`
  - `WeakTopic { enrollment_id: UUID, topic_id: UUID, topic_title: str, status: str, mastery_score: float | null }` — sourced from `enrollment_topics WHERE status='weak'` for the authenticated student; empty list when no weak topics

### GET /api/student/nodes
- Purpose: Return the node tree for a given owner (platform or parent), enforcing parent-link access
- Auth: student
- Query params: `owner_type: str` (required), `owner_id: str` (required when `owner_type=parent`)
- Response: `list[PlatformNodeCard]` — fully nested tree; each card carries `children: list[PlatformNodeCard]` recursively
- Errors: 400 if `owner_type=parent` and `owner_id` absent; 403 if no active `parent_child_links` row for the requested parent
- `topic_count` computed via **recursive CTE subtree sum** — parent nodes (grade/subject) aggregate live topic counts from all descendants, not just direct children

### GET /api/student/nodes/{node_id}/topics
- Purpose: Return live topics for a course-path node filtered to student visibility
- Auth: student
- Response: `list[StudentTopicRead { id, title, status, order, has_exam }]` — `has_exam` now reflects a real lookup against `exam_templates`, scoped to BR-DATA-003 visibility + enrolled-subtree authorization (G4p.6, backend `d612a66`; was hardcoded `false`)
- Only `status='live'` topics returned; draft topics silently excluded

### GET /api/student/topics/{topic_id}/content
- Purpose: Return content items for a live topic; empty list if topic missing or not live
- Auth: student
- Response: `list[StudentTopicContentRead { id, content_type, title, text, url }]`

> **Enrolled-only filter (G3, backend 9379bb7):** `GET /api/student/dashboard` and `GET /api/student/nodes` now filter platform nodes to the student's enrolled subtrees. An `EnrollmentRepository` is injected into `StudentDashboardService`; unenrolled students see `platform_nodes=[]`, and requests for nodes/topics outside an enrolled subtree raise `PermissionError` → 403.

---

## Student Enrollment (G7)

### GET /api/student/catalog
- Purpose: Return the platform course-path node catalog with per-student enrollment state and a recommended flag
- Auth: student (`X-Current-Role: student`; wrong role → 403; missing header → 400); CSRF required (validate_csrf applied even on GET)
- Response: `list[CatalogNodeCard { id: UUID, name: str, node_type: str, owner_type: str, enrolled: bool, recommended: bool, topic_count: int (default 0), enrollment_id: UUID | null }]`
- `recommended=true` when the node's grade matches the student's profile grade (most students have `grade=null` → none recommended)

### POST /api/student/enrollments
- Purpose: Self-enroll the authenticated student in a platform course-path node
- Auth: student; CSRF required
- Request: `StudentEnrollmentCreate { course_path_node_id: UUID }`
- Response: 201 `StudentEnrollmentRead { id: UUID, student_sub: str, course_path_node_id: UUID, enrolled_at: datetime, enrollment_source: str (default 'self') }`
- Errors: 409 `"Already enrolled in this node"` (AlreadyEnrolledError); 404 if node not found or not platform-owned (ValueError)

### DELETE /api/student/enrollments/{enrollment_id}
- Purpose: Drop (delete) one of the student's own enrollments
- Auth: student; CSRF required
- Response: 204 No Content
- Errors: 404 `"Enrollment not found"` (no matching enrollment for this student — oracle-protected, non-owned IDs look identical to missing)

---

## Student Doubt Inbox + Thread (G1)

### GET /api/students/me/doubts
- Purpose: List the authenticated student's doubts, newest-first by `updated_at`
- Auth: `X-Current-Role: student` (missing header → 400); no CSRF
- Response: `DoubtListResponse { items: list[DoubtSummaryRead] }` — each item includes `topic_name: str` (resolved from topics JOIN) and `last_activity_at: datetime` (most recent message timestamp, else `updated_at`)

### GET /api/students/me/doubts/{doubt_id}
- Purpose: Return a single doubt thread for the authenticated student
- Auth: `X-Current-Role: student`; no CSRF
- Response: `DoubtThreadResponse { doubt: DoubtSummaryRead, messages: list[DoubtMessageRead] }` (messages in `created_at` order)
- Errors: 404 if doubt doesn't exist or `student_sub` doesn't match the caller (oracle-protected)

### POST /api/students/me/doubts/{doubt_id}/messages
- Purpose: Append a student follow-up message to an existing doubt thread
- Auth: `X-Current-Role: student`; CSRF required
- Request: `CreateDoubtMessageRequest { content: str (min_length=1) }`
- Response: `DoubtThreadResponse` with updated thread (new message appended last)
- Errors: 404 if doubt doesn't exist or not owned by caller

---

## Teacher Escalation Queue (G2)

### POST /api/doubts/{doubt_id}/escalate
- Purpose: Student escalates an owned doubt to the shared teacher queue
- Auth: `X-Current-Role: student`; CSRF required
- Request: no body required
- Response: `DoubtThreadResponse` with status='escalated' and a new system message appended
- Errors: 404 if doubt doesn't exist or not owned by caller; 409 if status not `new` or `ai_answered`
- **Side effect (G3):** emits a `new_doubt_escalated` notification to the instructor shared queue (`recipient_role='instructor'`, `recipient_idp_sub=NULL`), body includes the student name resolved from `student_profiles`.

### GET /api/teachers/me/doubts
- Purpose: Return the shared escalated-doubt queue for the authenticated instructor
- Auth: `X-Current-Role: instructor` (missing header → 400); no CSRF
- Response: `TeacherDoubtListResponse { items: list[TeacherDoubtRead] }` — unclaimed (`escalated_to IS NULL`) plus claimed-by-me, newest-first. Each item: `doubt: DoubtRead`, `student_name: str`, `topic_title: str`, `escalated_to: str | None`, `last_message_at: datetime`

### GET /api/teachers/me/doubts/{doubt_id}
- Purpose: Return a single escalated doubt thread for the authenticated instructor
- Auth: `X-Current-Role: instructor`; no CSRF
- Response: `DoubtThreadResponse` (same shape as student thread response)
- Errors: 404 if doubt doesn't exist, status not in `escalated`/`answered`, or claimed by a different instructor

### POST /api/teachers/me/doubts/{doubt_id}/claim
- Purpose: Atomically claim an escalated doubt (sets `escalated_to=instructor_sub` WHERE `escalated_to IS NULL`); idempotent re-claim of own doubt returns 200
- Auth: `X-Current-Role: instructor`; CSRF required
- Request: no body required
- Response: `ClaimResponse { doubt_id: UUID, escalated_to: str }`
- Errors: 404 if doubt doesn't exist or not escalated; 409 if already claimed by another instructor

### POST /api/teachers/me/doubts/{doubt_id}/messages
- Purpose: Append a teacher reply to a doubt thread and transition status to `answered`
- Auth: `X-Current-Role: instructor`; CSRF required
- Request: `CreateDoubtMessageRequest { content: str (min_length=1) }`
- Response: `DoubtThreadResponse` with full updated thread
- Errors: 404 if doubt doesn't exist
- **Side effect (G3):** emits a `doubt_teacher_replied` notification to the student (`recipient_role='student'`, body includes the teacher name resolved from `teacher_profiles`) and calls the parent fan-out stub (`child_doubt_replied`, v1 no-op).

---

## Notifications (G3)

> All four endpoints require `X-Current-Role` (any valid role). The two PATCH mutations additionally require `X-CSRF-Token`. APISIX route `20-api-notifications.json` — priority 15, `secured-api` OIDC plugin config, `limit-count` (60 req/min per IP → 429), `request-validation` (requires `Content-Type: application/json` → 400 if absent). Worker also runs an hourly `auto_close_doubts_loop` that resolves overdue doubts and emits `doubt_auto_closed` notifications (no HTTP endpoint — background cron).

### GET /api/notifications/me
- Purpose: Return the authenticated user's notification feed — personal notifications (`recipient_idp_sub = caller.sub`) plus shared-queue notifications for the caller's active role, within the last 90 days, newest-first
- Auth: any valid role (`X-Current-Role` required); no CSRF
- Query: `limit` (1–200, default 50), `offset` (>=0, default 0)
- Response: `NotificationFeedResponse { unread_count: int, items: NotificationRead[] }` — each `NotificationRead`: `id, type, title, body, action_url, read, created_at`; the `group` field classifies each item by recency (`today` | `yesterday` | `earlier` | `older`)

### GET /api/notifications/me/unread-count
- Purpose: Lightweight unread count for topbar badge polling (no full payload fetch)
- Auth: any valid role; no CSRF
- Response: `UnreadCountResponse { count: int }`

### PATCH /api/notifications/me/read-all
- Purpose: Mark all unread notifications read for the caller's current role
- Auth: any valid role; CSRF required
- Request: `ReadAllRequest { role: str }` — must match the `X-Current-Role` header value
- Response: `ReadAllResponse { marked_count: int }`
- Errors: 403 `"Role mismatch: body.role must match X-Current-Role"` if `body.role` differs from the active role

### PATCH /api/notifications/{notification_id}/read
- Purpose: Mark a single notification read
- Auth: any valid role; CSRF required
- Response: `{ read: true }`
- Errors: 404 if the notification is not found or not accessible (personal row not owned by the caller, or shared-queue row whose `recipient_role` doesn't match the caller's active role)
- Note: marking a **shared-queue** notification read marks it read globally for all users of that role — v1 limitation, no per-user read tracking on shared rows. Personal rows are tracked per-user.

---

## hAITU Doubt Resolution (G9 + G1)

### POST /api/haitu/topic-doubt
- Purpose: Run a student's doubt question through the 4-stage RAG pipeline (rewrite → retrieve → rerank → synthesize) scoped to an enrolled topic's subtree
- Auth: student; CSRF required
- Request: `HaituDoubtRequest { topic_id: UUID, enrollment_id: UUID, message: str, history: list[HaituDoubtMessage { role: "user"|"assistant"|"system", content: str }] (default []) }`
- Response: **SSE stream** (`Content-Type: text/event-stream`). Frames (each `data: {…}\n\n`): `event: doubt_id` with `{"doubt_id": "<uuid>"}` **(emitted first, before any tokens)** → incremental `{"token": str}` → `{"escalation_ready": bool}` → terminal `{"done": true}`. 15 s `: ping` keepalives. Client disconnect (`request.is_disconnected()`) cancels the stream. The streaming Stage-4 path uses a single QA-mirroring prompt (bypasses `CompactAndRefine`, which the non-streaming `answer()` retains).
- Pipeline: stage 1 rewrites the query (LLM → JSON, safe fallback); stage 2 retrieves via QueryFusionRetriever (hybrid pgvector, topic_id filter); stage 3 is a passthrough (inline cross-encoder removed in G0.3; `rerank_model` retained as a future-hook for an external rerank API — a non-empty value logs a warning and returns nodes unordered); stage 4 synthesizes (intent-specific prompts, escalation detection). `safe=False` from stage 1 short-circuits before retrieval.
- Errors: 403 (enrollment invalid or topic outside enrolled subtree); 429 `"Rate limit exceeded"` (HaituRateLimiter: 20 calls/student/hour, in-process) — both returned as HTTP errors **before** the stream starts. DB session closed before streaming begins.
- **Doubt persistence (G1):** creates/upserts a `doubts` row + student `doubt_messages` row in the validation phase (post rate-limit, before stream starts). On 429 no doubt row is created (no orphan). After the stream ends, a fire-and-forget background task opens a fresh DB session and persists the full accumulated AI reply as an `ai` `doubt_messages` row. On early disconnect the partial text is still persisted.
- **G2-patch (commit 9d27e8c):** `find_or_create_doubt` now treats `answered` doubts as closed for thread-reuse — a follow-up question about a topic opens a **fresh thread** with the full escalation path instead of reusing an existing `answered` thread (which previously hid the teacher-help button permanently). The find-open exclusion set (`answered` excluded) is deliberately distinct from the auto-close terminal set (`answered` remains auto-closeable until it hits the 7-day `auto_close_at`).
- APISIX gateway (`19-api-haitu.json`): route priority 20 (beats api-write 10 so the 6 s default read timeout does not 504 long-running calls); send/read timeout **600 s** (backend `HAITU__LLM_REQUEST_TIMEOUT` default is 360 s — the gateway is the higher ceiling); `proxy-buffering` disabled (required for SSE); `limit-count` (20 req/min per IP → 429, separate from the in-process per-student/hour limiter); `limit-conn` (20 concurrent connections/IP → 503); `request-validation` (requires `Content-Type: application/json` → 400 if absent); `secured-api` plugin config (OIDC deny on unauthenticated) with a WAF exclusion (Coraza id:199110) for `POST /api/haitu/*` — rules 942200/942131/942130/942340/942380/942400/942410 removed **per-transaction** via `ctl:ruleRemoveById` (not `ctl:ruleRemoveTargetById`, which is unreliable in Coraza WASM on APISIX 3.17); rule 942200 added to suppress educational text false positives (e.g. propulsion/physics phrases matching MySQL comment obfuscation). All other routes retain full SQLi inspection. Backend service has `HAITU__*` + `EMBEDDING__*` env vars wired in `common/docker-compose.yml`.

---

## hAITU Post-Exam Review (G4.3 + G4-patch streaming, 2026-07-01)

### POST /api/haitu/exam-review-chat
- Purpose: Stream a review chat (no RAG — model sees conversation only) about a completed exam session
- Auth: student (`X-Current-Role: student`); CSRF required
- Request: `ExamReviewChatRequest { attempt_id: UUID, message: str, history: list[{role, content}] (default []) }` — `session_id` accepted as a deprecated alias, copied to `attempt_id` via a `model_validator` when `attempt_id` is absent
- Response: **SSE stream** (`response_model=None`) when the caller sends `Accept: text/event-stream` — frames `data: {"token": str}` repeated, then `data: {"done": true}`; a mid-stream `data: {"error": str}` frame signals failure. **JSON fallback** `ExamReviewChatFallbackResponse { response: str }` when the Accept header is absent.
- No hardcoded token cap (**changed 2026-07-01**, was `max_tokens=500`) — falls back to the configured `HAITU__MAX_TOKENS` default (2048); the prior 500 cap could truncate reasoning-model output since those models spend part of the budget on hidden `reasoning_content` before visible text
- A mid-stream pump failure (e.g. the LLM backend goes unreachable) now pushes an explicit `data: {"error": "I couldn't generate a response right now. Please try again in a moment."}` frame before the terminal `done` (**changed 2026-07-01** — was a silent end-of-stream indistinguishable from a short-but-complete answer)
- Rate limiting: `HaituRateLimiter` (20 calls/student/hour, in-process) — **newly enforced on this endpoint**; 429 on exceeded
- Errors: 403 if session not found, not owned by the authenticated student, or `status not in ('completed', 'failed')` (was `!= completed` only)
- APISIX route `21-api-haitu-exam-review.json`: priority 20 (beats api-write), send/read timeout 600 s, `proxy-buffering` disabled (streaming), `limit-count` 20/60s per IP → 429, `request-validation` (requires `Content-Type: application/json`; body must include `attempt_id` (UUID), `message` (string), `history` (array)); WAF NL exclusion inherited from secured-api

### POST /api/haitu/pattern-analysis
- Purpose: Analyse incorrect answers in a completed exam session and return a markdown pattern + recommendation summary; result is **cached per `attempt_id`** in a bounded in-process dict (`_PATTERN_ANALYSIS_CACHE`, FIFO eviction once over 10,000 entries — lost on worker restart, acceptable at current scale)
- Auth: student (`X-Current-Role: student`); CSRF required
- Request: `PatternAnalysisRequest { attempt_id: UUID }` — `session_id` accepted as a deprecated alias (same aliasing pattern as exam-review-chat)
- Response:
  - **Cache hit:** SSE (`Accept: text/event-stream`) replays the cached string as a single `data: {"token": <full analysis>}` frame then `data: {"done": true}`; JSON fallback returns `PatternAnalysisFallbackResponse { analysis: str }` immediately.
  - **Cache miss (2026-07-01, G4-patch-2 — no longer 202):** computed **inline in this request/worker** — SSE callers get **real incremental tokens** as the LLM generates them (same `stream_no_rag` machinery as exam-review-chat); JSON callers `await` the full result inline (bounded by the 30 s LLM timeout) and return `{analysis: str}`. The cache is populated once the stream/call finishes, so a student's *first* S05 visit now sees the real analysis (previously: always 202, background task, never surfaced on the first load — see `Implementation_planning/decisions.md` 2026-07-01).
  - **The 202 `PatternAnalysisPendingResponse` contract is retired outright** — the route has no pending/not-ready response of any kind (not even a rare fallback). A concurrent request for the same `attempt_id` on the *same* worker `asyncio.shield`s the in-flight `asyncio.Task` and receives the real result. A concurrent request landing on a *different* worker (in-memory cache is per-worker, `--workers 2` is the real deployed default) has no visibility into that task and simply runs its own independent live computation — its own LLM call, its own rate-limit charge, its own eventual cache entry. This is an accepted rare/low-cost edge case, not engineered around, since nothing in the frontend polls on a pending state anyway.
  - Neutral message `"Great work — no wrong answers to analyse on this attempt."` when there are no incorrect answers (no LLM call made)
  - **Response format changed** from structured `{patterns: [...], recommendations: [...]}` JSON to free-form markdown text — the system prompt now asks for plain markdown, no JSON envelope
  - No hardcoded token cap (**changed 2026-07-01**, was `max_tokens=500`) — falls back to `HAITU__MAX_TOKENS` (2048), same rationale as exam-review-chat
  - A mid-stream pump failure now pushes an explicit `data: {"error": "I couldn't generate an explanation right now. Please try again in a moment."}` frame before `done` (**changed 2026-07-01**, was silent truncation)
- Errors: 403 if session not found or not owned by the caller — **ownership is now verified on every call before consulting the cache** (2026-07-01 IDOR fix: previously only checked on cache miss, so once an analysis existed any authenticated student could read another student's cached result by `attempt_id`)
- APISIX route `22-api-haitu-pattern-analysis.json`: priority 20, send/read timeout **600 s / 600 s** (was 10 s / 60 s — this was the direct cause of the 504 that blocked G4.3 test item 7g), `proxy-buffering` disabled, `limit-count` 20/60s per IP → 429, **`limit-conn` 20 concurrent/IP → 503** (newly added), `request-validation` (requires `Content-Type: application/json`; body must include `attempt_id` (UUID)); WAF NL exclusion inherited from secured-api

---

## Health

### GET /api/health/status
- Purpose: Health check
- Auth: None
- Response: `{ status: "OK" }`
