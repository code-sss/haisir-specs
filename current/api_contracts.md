# Current API Contracts Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | f5ef54f2f4ccdeb2c295a8546462e57ba0ba17c7 |
| haisir-frontend | a8f710580075ed2c1552f970d607860a1c844abb |
| haisir-deploy | 94bfd1ccee72d8562aaa3ef2d02cdd10176a2026 |

> Next session: run `git diff f5ef54f2..HEAD` in haisir-backend to see only what changed since this snapshot.

---

## Auth & User

### GET /api/auth/csrf
- Purpose: Return a CSRF token
- Auth: None (public)
- Response: `{ csrfToken: string }`

### GET /api/users/me
- Purpose: Return current user profile from JWT
- Auth: Any authenticated user
- Response: id, sub, name, email, email_verified, roles[], current_role, onboarding_completed_at

### POST /api/users/me/assign-role
- Purpose: Assign a role to the current user via Keycloak Admin API
- Auth: Any authenticated user
- Request: `{ role: "student" | "parent" }`
- Response: `{ message: string }`

### PATCH /api/users/me/onboarding-complete
- Purpose: Mark onboarding as complete; sets onboarding_completed_at timestamp
- Auth: Any authenticated user
- Request: `{}`
- Response: `{ onboarding_completed_at: datetime }`

### POST /api/users/me/profile [student]
- Purpose: Create student profile
- Auth: student
- Request: first_name, last_name, phone?, avatar_url?, grade?, subjects?
- Response: id, idp_sub, first_name, last_name, phone, avatar_url, grade, subjects

### POST /api/users/me/profile [parent]
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
- Auth: student, instructor (instructor outside current increment)
- Response: array of `{ id, name, path_type, description }`

### GET /api/categories/{category_id}
- Purpose: Get single category
- Auth: student, instructor (instructor outside current increment)
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
- Auth: student, instructor (instructor outside current increment)
- Query: parent_id (optional)
- Response: array of node objects

### GET /api/course-path-nodes
- Purpose: Get nodes filtered by category_id and node_type
- Auth: student, instructor (instructor outside current increment)
- Query: category_id, node_type
- Response: array of node objects

### GET /api/course-path-nodes/parent/{parent_id}
- Purpose: Get child nodes of a given node
- Auth: student, instructor (instructor outside current increment)
- Query: node_type (optional)
- Response: array of node objects

### GET /api/course-path-nodes/{node_id}
- Purpose: Get a single node
- Auth: student, instructor (instructor outside current increment)
- Response: id, name, node_type, category_id, parent_id, order, owner_type, owner_id

### POST /api/course-path-nodes
- Purpose: Create a node
- Auth: admin (admin outside current increment)
- Request: name, node_type, category_id, parent_id?, order?
- Response: node object

### GET /api/course-path-nodes/path-to-root/{node_id}
- Purpose: Get ancestor path from a node to the root
- Auth: student, instructor (instructor outside current increment)
- Response: array of node objects (root → leaf order)

> Note: no owner_type filtering enforced on any node endpoint yet. All nodes returned regardless of owner_type.

---

## Topics

### GET /api/topics/{course_path_node_id}
- Purpose: List topics for a node
- Auth: student, instructor (instructor outside current increment)
- Response: array of `{ id, title, course_path_node_id, order, status, owner_type, owner_id }`

### POST /api/topics
- Purpose: Create a topic
- Auth: admin (admin outside current increment)
- Request: title, course_path_node_id, order?
- Response: topic object

> Note: no owner_type filtering enforced. All topics returned regardless of owner_type.

---

## Topic Contents

### GET /api/topic-contents/{topic_id}
- Purpose: List content items for a topic
- Auth: student
- Response: array of `{ id, topic_id, content_type, title, url, text, order, description }`

### GET /api/topic-contents/{content_type}/{topic_id}
- Purpose: Serve PDF file for a topic
- Auth: student
- Response: FileResponse (PDF binary)

### POST /api/topic-contents
- Purpose: Create a content item
- Auth: instructor (outside current target increment)
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
- Auth: student
- Response: array of `{ id, course_path_node_id, title }`

### POST /api/exams/session/create
- Purpose: Create an exam session for the current student
- Auth: student
- Request: `{ exam_template_id: UUID }`
- Response: session object (id, user_id, exam_template_id, course_path_node_id, mode, status, created_at)

### POST /api/exams/session/{session_id}/start
- Purpose: Mark a session as started; records started_at
- Auth: student
- Response: updated session object

### GET /api/exams/session/{session_id}/questions
- Purpose: Get questions for an exam session
- Auth: student
- Response: `{ questions[], paragraph_questions[] }` with point allocations

### POST /api/exams/session/{session_id}/submit
- Purpose: Submit all answers for a session; triggers grading
- Auth: student
- Request: `{ answers: [{ question_id, selected_options?, text_answer? }] }`
- Response: session object with finished_at, status

### GET /api/exams/session/unfinished/{exam_template_id}
- Purpose: Check for an existing unfinished session (resume support)
- Auth: student
- Response: session object or empty

### GET /api/exams/session/all/{exam_template_id}
- Purpose: List all sessions for the current student for a template
- Auth: student
- Query: limit (default 5)
- Response: array of session objects with score as percentage

### GET /api/exams/session/{session_id}/answers
- Purpose: Get graded results for a session
- Auth: student
- Response: results[], score, total, total_marks, total_questions, pending_review_count, passed

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
