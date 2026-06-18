# Current API Contracts Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | 0d5305d (feature/rag — enrollment domain layer, HaituService stages 1–3, 2026-06-18) |
| haisir-frontend | ab2c3a7 (feature/rag — browse-courses + hAITU panel SonarQube fix, 2026-06-18) |
| haisir-deploy | e57c56b (feature/rag — EMBEDDING/HAITU/RESTRUCTURE env vars wired, 2026-06-15) |

> Next session: run `git diff 0d5305d..HEAD` in haisir-backend, `git diff ab2c3a7..HEAD` in haisir-frontend, and `git diff e57c56b..HEAD` in haisir-deploy to see only what changed since this snapshot.

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

### GET /api/exam-sessions/session/{session_id}/review
- Purpose: Get graded results for a completed or grading_pending session
- Auth: student (session owner); exam owner (parent who owns the template, or admin) additionally receives `ai_rationale` per essay question
- Response: same shape as submit response; matching question answers decoded from raw JSON pairs to `"left_text → right_text"` strings for display (falls back to IDs if option text is unavailable); `earned_points` and `earned_marks` are rounded to 2 decimal places; each answer also includes:
  - `grading_status: str | null` — for essay questions: `pending | ai_graded | released | finalized | overridden | disputed | error`; null for non-essay
  - `ai_feedback: str | null` — visible when `grading_status in ('released','finalized','overridden')`; null otherwise
  - `model_answer: str | null` — the prose model answer set by the exam author; visible to students only when `grading_status in ('released','finalized','overridden')`; null otherwise
  - `explanation: str | null` — the mark scheme/rubric notes set by the exam author; for essay questions gated to same released grade statuses; for non-essay questions always returned
  - `ai_rationale: dict | null` — full LLM output; visible only to exam owner; always null for student callers

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
- Response: `StudentDashboardRead { platform_nodes: PlatformNodeCard[], has_parent_link: bool }`
  - `PlatformNodeCard { id: UUID, name: str, node_type: str, topic_count: int, owner_type: str, children: list[PlatformNodeCard] }`

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
- Response: `list[StudentTopicRead { id, title, status, order, has_exam (always false this phase) }]`
- Only `status='live'` topics returned; draft topics silently excluded

### GET /api/student/topics/{topic_id}/content
- Purpose: Return content items for a live topic; empty list if topic missing or not live
- Auth: student
- Response: `list[StudentTopicContentRead { id, content_type, title, text, url }]`

---

## Health

### GET /api/health/status
- Purpose: Health check
- Auth: None
- Response: `{ status: "OK" }`
