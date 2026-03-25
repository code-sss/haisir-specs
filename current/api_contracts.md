## GET /api/health/status
- Purpose: Health check
- Auth: none
- Response: `{"status": "OK"}`

## GET /api/auth/csrf
- Purpose: Issue a CSRF token (set as cookie and returned in body)
- Auth: none
- Response: `{csrf_token: string}`

---

## GET /api/users/me
- Purpose: Return authenticated user info and onboarding state
- Auth: any authenticated user
- Response: `{id, sub, name, email, email_verified, roles, current_role, onboarding_completed_at}`

## POST /api/users/me/assign-role
- Purpose: Self-service role assignment (student or parent); Keycloak Admin API wire-up is a TODO — endpoint defined but not fully operational
- Auth: any authenticated user
- Request: `{role: "student" | "parent"}`
- Response: `{message: string}`

## PATCH /api/users/me/onboarding-complete
- Purpose: Set `onboarding_completed_at = now()` for the current user
- Auth: any authenticated user
- Response: `{onboarding_completed_at: ISO timestamp}`

---

## GET /api/categories
- Purpose: List all categories
- Auth: any authenticated user
- Response: `[{id, name, path_type, description}]`

## GET /api/categories/{category_id}
- Purpose: Get a single category by ID
- Auth: any authenticated user
- Response: `{id, name, path_type, description}`

## POST /api/categories/
- Purpose: Create a new category
- Auth: admin
- Request: `{name, path_type, description?}`
- Response: `{id, name, path_type, description}`

## PATCH /api/categories/{category_id}
- Purpose: Update category description
- Auth: admin
- Request: `{description}`
- Response: `{id, name, path_type, description}`

---

## GET /api/course-path-nodes/category/{category_id}
- Purpose: Get nodes by category; optional `parent_id` query param to filter by parent
- Auth: student, instructor
- Response: `[{id, name, node_type, category_id, parent_id, order, owner_type, owner_id}]`

## GET /api/course-path-nodes/
- Purpose: Get nodes by `category_id` + `node_type` query params
- Auth: student, instructor
- Response: `[{id, name, node_type, ...}]`

## GET /api/course-path-nodes/parent/{parent_id}
- Purpose: Get child nodes by parent_id; `node_type` query param required
- Auth: student, instructor
- Response: `[{id, name, node_type, ...}]`

## GET /api/course-path-nodes/{node_id}
- Purpose: Get a single node by ID
- Auth: student, instructor
- Response: `{id, name, node_type, category_id, parent_id, order, owner_type, owner_id}`

## POST /api/course-path-nodes/
- Purpose: Create a new course path node
- Auth: admin
- Request: `{name, node_type, category_id, parent_id?, order?}`
- Response: `{id, name, node_type, ...}`

## GET /api/course-path-nodes/path-to-root/{node_id}
- Purpose: Walk ancestors from a node up to the root
- Auth: student, instructor
- Response: `[{id, name, node_type, ...}]` — ordered from node to root

---

## GET /api/topics/{course_path_node_id}
- Purpose: List topics attached to a node
- Auth: student, instructor
- Response: `[{id, title, course_path_node_id, order, status, owner_type, owner_id}]`

## POST /api/topics/
- Purpose: Create a new topic on a node
- Auth: instructor
- Request: `{title, course_path_node_id, order?}`
- Response: `{id, title, ...}`

---

## GET /api/topic-contents/{topic_id}
- Purpose: List all content items for a topic
- Auth: student (any role via require_any_role)
- Response: `[{id, topic_id, content_type, title, url, text, order, description}]`

## GET /api/topic-contents/{content_type}/{topic_id}
- Purpose: Serve the actual file (PDF) for a content_type on a topic
- Auth: student
- Response: FileResponse (`application/pdf`)

## POST /api/topic-contents/
- Purpose: Create a new content item for a topic
- Auth: instructor
- Request: `{topic_id, content_type, title, url?, text?, order, description?}`
- Response: `{id, topic_id, content_type, title, url, text, order, description}`

---

## GET /api/questions/
- Purpose: Get questions filtered by `tags` query param
- Auth: student, instructor
- Response: `[{id, question_text, question_type, options, correct_answers, difficulty, tags, image_url}]`

## GET /api/questions/assessment/{assessment_id}
- Purpose: Get questions for a given assessment
- Auth: student
- Response: `[{...question fields...}]`

## POST /api/questions/
- Purpose: Create a new question
- Auth: instructor
- Request: `{question_text, question_type, options, correct_answers, difficulty, tags?, explanation?, image_url?}`
- Response: `{id, ...}`

---

## GET /api/assessments/topic/{topic_id}
- Purpose: Get assessments for a topic
- Auth: student
- Response: `[{id, topic_id, question_ids, paragraph_question_ids, title}]`

## POST /api/assessments/
- Purpose: Create an assessment for a topic
- Auth: instructor
- Request: `{topic_id, question_ids, paragraph_question_ids?, title}`
- Response: `{id, ...}`

## POST /api/assessments/start
- Purpose: Start an assessment attempt
- Auth: student
- Request: `{assessment_id}`
- Response: `{id, assessment_id, started_at, status}`

## POST /api/assessments/submit/{attempt_id}
- Purpose: Submit a single answer within an ongoing attempt
- Auth: student
- Request: `{question_id, selected_options?, text_answer?}`
- Response: `{is_correct, ...}`

## POST /api/assessments/submit-all/{attempt_id}
- Purpose: Submit all answers at once and finalise the attempt
- Auth: student
- Request: `[{question_id, selected_options?, text_answer?}]`
- Response: `{score, status, ...}`

## GET /api/assessments/{attempt_id}
- Purpose: Get current attempt state
- Auth: student
- Response: `{id, assessment_id, started_at, status, score?}`

## GET /api/assessments/{assessment_id}/attempts
- Purpose: Get past attempts for an assessment
- Auth: student
- Response: `[{id, started_at, finished_at, score, status}]`

## GET /api/assessments/result/{attempt_id}
- Purpose: Get graded results with per-question breakdown
- Auth: student
- Response: `{score, answers: [{question_id, is_correct, selected_options, text_answer, ...}]}`

## GET /api/assessments/unfinished-attempt/{assessment_id}
- Purpose: Get the current user's unfinished attempt for an assessment, if one exists
- Auth: student
- Response: `{id, assessment_id, started_at, status}` or null

---

## GET /api/exams/template
- Purpose: Get instructor's own exam templates; `node_id` query param required
- Auth: instructor
- Response: `[{id, title, description, mode, duration_minutes, passing_score, is_active}]`

## POST /api/exams/template
- Purpose: Create an exam template
- Auth: instructor
- Request: `{course_path_node_id, title, description?, mode, ruleset?, duration_minutes?, passing_score?}`
- Response: `{id, ...}`

## PATCH /api/exams/template/{template_id}
- Purpose: Update exam template metadata
- Auth: instructor
- Request: partial `{title?, description?, duration_minutes?, passing_score?}`
- Response: `{id, ...}`

## DELETE /api/exams/template/{template_id}
- Purpose: Soft-delete an exam template (sets `is_active = false`)
- Auth: instructor
- Response: 204

## GET /api/exams/course/{node_id}
- Purpose: Get active exam templates for a course node (student view)
- Auth: student
- Response: `[{id, title, description, mode, duration_minutes, passing_score}]`

## POST /api/exams/template-question
- Purpose: Link a single question to an exam template
- Auth: instructor
- Request: `{exam_template_id, question_id, order, points, paragraph_question_id?}`
- Response: `{id, ...}`

## GET /api/exams/template/{template_id}/questions-with-details
- Purpose: Get full template with question details; images returned as base64
- Auth: instructor, student
- Response: `{template: {...}, questions: [{...question with base64 image_url...}]}`

## POST /api/exams/{node_id}/static
- Purpose: Create a complete static exam in one shot (template + all questions)
- Auth: instructor
- Request: `{title, description?, duration_minutes?, passing_score?, questions: [{...}]}`
- Response: `{id, ...}`

## PATCH /api/exams/{node_id}/static
- Purpose: Upsert questions on an existing static exam; `template_id` query param required
- Auth: instructor
- Request: `{questions: [{...}]}`
- Response: `{id, ...}`

---

## POST /api/exam-sessions/session/create
- Purpose: Create a new exam session; `exam_template_id` query param required
- Auth: student
- Response: `{id, exam_template_id, status, created_at}`

## GET /api/exam-sessions/session/unfinished/{exam_template_id}
- Purpose: Get an unfinished session for a template, if one exists
- Auth: student
- Response: session object or null

## GET /api/exam-sessions/session/{session_id}/questions
- Purpose: Get ordered questions for an exam session
- Auth: student
- Response: `[{question fields..., order, points}]`

## POST /api/exam-sessions/session/{session_id}/start
- Purpose: Mark session as started (sets `started_at`)
- Auth: student
- Response: `{id, started_at, status}`

## POST /api/exam-sessions/session/{session_id}/submit
- Purpose: Submit all answers, grade, and finalise the session
- Auth: student
- Request: `{answers: [{question_id, user_answer}]}`
- Response: `{score, status, passed}`

## GET /api/exam-sessions/session/all/{exam_template_id}
- Purpose: Get all sessions for a template (scores as percentages)
- Auth: student
- Response: `[{id, score, status, started_at, finished_at}]`

## GET /api/exam-sessions/session/{session_id}/answers
- Purpose: Get detailed results with weighted scoring and pass/fail
- Auth: student
- Response: `{score, passed, answers: [{question_id, is_correct, earned_points, user_answer, ...}]}`

---

## POST /api/students/me/profile
- Purpose: Create or update the authenticated student's profile
- Auth: student
- Request: `{first_name, last_name, phone?, avatar_url?, grade?, subjects?}`
- Response: `{id, idp_sub, first_name, last_name, phone, avatar_url, grade, subjects}`

## POST /api/parent-child-links
- Purpose: Link a parent to a child using an invite code
- Auth: parent
- Request: `{code}`
- Response: `{id, parent_sub, child_sub, created_at}`

## GET /api/parent-link-codes/{code}
- Purpose: Validate a parent invite code and retrieve child info
- Auth: any authenticated user
- Response: `{child_sub, expires_at, is_used}`

## GET /api/courses/enrolled
- Purpose: Get courses the student is enrolled in — **stub, always returns []**
- Auth: student
- Response: `[]`
