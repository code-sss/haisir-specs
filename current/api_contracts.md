# Current API Contracts Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | d8713ad (Phase 1c-pre + skill updates, 2026-04-06) |
| haisir-frontend | c7084e5 (dep upgrades + minor test/config fixes, 2026-04-06) |
| haisir-deploy | b814471 (skill updates, 2026-04-06) |

> Next session: run `git diff d8713ad..HEAD` in haisir-backend and `git diff c7084e5..HEAD` in haisir-frontend to see only what changed since this snapshot.

---

## Auth & User

> **BR-SEC-006 (enforced as of Phase 1c-pre):** `X-Current-Role` is required on all role-gated endpoints. Missing header returns `400 "X-Current-Role header required"`. The three onboarding endpoints below are explicitly exempt (use lenient dependency that defaults to `roles[0]`).

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
- Errors: 404 if not found or not platform-owned; 409 if any subtree node has a `pending` or `ongoing` exam session
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
- Request: title, course_path_node_id, order?
- Response: topic object

---

## Topic Contents

### GET /api/topic-contents/{topic_id}
- Purpose: List content items for a topic
- Auth: student | instructor | admin (any platform role)
- Response: array of `{ id, topic_id, content_type, title, url, text, order, description }`
- Note: visibility scoped by the parent topic's owner_type — student sees only items whose parent topic is visible to them.

### GET /api/topic-contents/{content_type}/{topic_id}
- Purpose: Serve a media file for a topic (PDF, video, etc.)
- Auth: student | instructor | admin (any platform role)
- Response: FileResponse (binary)
- Note: stored files follow the path `topics/{content_type}/{filename}` on disk (e.g. `topics/pdf/filename.pdf`).

### POST /api/topic-contents
- Purpose: Create a content item
- Auth: admin
- Request: topic_id, content_type, title, url?, text?, order, description?
- Response: content object

---

## Questions

### GET /api/questions
- Purpose: List questions by tags
- Auth: student, instructor (instructor outside current increment)
- Query: tags[] (required)
- Response: array of question objects

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
- Request: title, description, mode, duration_minutes, passing_score, items[]
- Response: template object

### PATCH /api/exams/{node_id}/static
- Purpose: Upsert questions on a static template
- Auth: instructor (outside current target increment)
- Request: template_id, questions[], duration_minutes?, passing_score?
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
- Auth: student (session owner)
- Response: `{ questions[], paragraph_questions[] }` with point allocations; images base64-encoded

### POST /api/exam-sessions/session/{session_id}/answer
- Purpose: Record or update a single answer during an active session
- Auth: student (session owner)
- Request: `{ question_id: UUID, user_answer: string }`
- Response: `{ message: "Answer recorded" }`

### POST /api/exam-sessions/session/{session_id}/submit
- Purpose: Submit session; triggers auto-grading; sets status = 'completed'
- Auth: student (session owner)
- Request: (no body)
- Response: session with score, finished_at, and per-question results (correct answers + explanations)

### GET /api/exam-sessions/session/{session_id}/review
- Purpose: Get graded results for a completed session
- Auth: student (session owner)
- Response: same shape as submit response

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

## Health

### GET /api/health/status
- Purpose: Health check
- Auth: None
- Response: `{ status: "OK" }`
