## GET /api/auth/csrf
- Purpose: Fetch CSRF token for mutations
- Auth: none
- Response: { csrfToken: string }

## GET /api/health/status
- Purpose: Health check
- Auth: none
- Response: { status: "OK" }

## GET /api/users/me
- Purpose: Get current user identity, roles, and onboarding state
- Auth: any authenticated user
- Response: { id, sub, name, email, email_verified, roles[], current_role, onboarding_completed_at }

## POST /api/users/me/assign-role
- Purpose: Assign initial Keycloak role to new user (onboarding)
- Auth: any authenticated user
- Request: { role: "student" | "parent" }
- Response: { message: string }

## PATCH /api/users/me/onboarding-complete
- Purpose: Mark onboarding complete
- Auth: any authenticated user
- Response: { onboarding_completed_at: datetime }

## POST /api/students/me/profile
- Purpose: Create student profile
- Auth: student
- Request: { first_name, last_name, phone?, avatar_url?, grade?, subjects? }
- Response: StudentProfile

## POST /api/parents/me/profile
- Purpose: Create parent profile
- Auth: parent
- Request: { first_name, last_name, phone? }
- Response: ParentProfile

## POST /api/parent-child-links
- Purpose: Link parent to child via invite code
- Auth: parent
- Request: { invite_code: string }
- Response: ParentChildLink

## GET /api/parent-link-codes/{code}
- Purpose: Look up a parent link code
- Auth: parent
- Response: ParentLinkCode

## GET /api/classes/by-invite-code/{code}
- Purpose: Look up a class by invite code
- Auth: student
- Response: ClassInviteCode

## GET /api/courses/enrolled
- Purpose: List enrolled courses (placeholder — not yet implemented)
- Auth: student
- Response: none (stub)

## GET /api/categories
- Purpose: List all categories
- Auth: student, instructor
- Response: [Category]

## GET /api/categories/{category_id}
- Purpose: Get a single category
- Auth: student, instructor
- Response: Category | null

## POST /api/categories/
- Purpose: Create a new category
- Auth: admin
- Request: { name, path_type, description? }
- Response: Category

## PATCH /api/categories/{category_id}
- Purpose: Update category description
- Auth: admin
- Request: { description }
- Response: Category | null

## GET /api/course-path-nodes/category/{category_id}
- Purpose: List root-level nodes for a category
- Auth: student, instructor
- Response: [CoursePathNode]

## GET /api/course-path-nodes/?category_id&node_type
- Purpose: List nodes filtered by category and type
- Auth: student, instructor
- Response: [CoursePathNode]

## GET /api/course-path-nodes/parent/{parent_id}
- Purpose: List children of a node
- Auth: student, instructor
- Response: [CoursePathNode]

## GET /api/course-path-nodes/{node_id}
- Purpose: Get a single node
- Auth: student, instructor
- Response: CoursePathNode | null

## GET /api/course-path-nodes/path-to-root/{node_id}
- Purpose: Get breadcrumb path from node to root
- Auth: student, instructor
- Response: [CoursePathNode]

## POST /api/course-path-nodes/
- Purpose: Create a new course path node
- Auth: admin
- Request: { name, node_type, category_id, parent_id?, order? }
- Response: CoursePathNode

## GET /api/topics/{course_path_node_id}
- Purpose: List topics for a node
- Auth: student, instructor
- Response: [Topic]

## POST /api/topics/
- Purpose: Create a topic
- Auth: admin
- Request: { title, course_path_node_id, order? }
- Response: Topic

## GET /api/topics-contents/{topic_id}
- Purpose: List all content items for a topic
- Auth: student
- Response: [TopicContent]

## GET /api/topics-contents/{content_type}/{topic_id}
- Purpose: Serve a topic's file content (PDF)
- Auth: student
- Response: FileResponse

## POST /api/topics-contents/
- Purpose: Add content to a topic
- Auth: instructor
- Request: { topic_id, content_type, title, url?, text?, order, description? }
- Response: TopicContent

## GET /api/questions/?tags
- Purpose: List questions filtered by tags
- Auth: student, instructor
- Response: [Question]

## GET /api/questions/assessment/{assessment_id}
- Purpose: Get questions for an assessment (deprecated flow)
- Auth: student
- Response: { questions: [], paragraph_questions: [] }

## POST /api/questions/
- Purpose: Create a question
- Auth: instructor
- Request: { question_text, question_type, options_obj, correct_answers, explanation?, difficulty, tags? }
- Response: Question

## POST /api/paragraph-questions/
- Purpose: Create a paragraph question group
- Auth: instructor
- Request: { content, title, questions[], paragraph_type, tags?, difficulty? }
- Response: ParagraphQuestion

## GET /api/paragraph-questions/{id}/questions
- Purpose: Get paragraph with all embedded questions
- Auth: student
- Response: { id, content, title, ..., questions: [] }

## GET /api/paragraph-questions/{id}
- Purpose: Get a paragraph question
- Auth: student
- Response: ParagraphQuestion | null

## GET /api/answers/{id}
- Purpose: Get a single answer record (legacy)
- Auth: student
- Response: Answer | null

## POST /api/answers/
- Purpose: Submit an answer (legacy — used by old assessment flow)
- Auth: student
- Request: { session_id, question_id, selected_options?, text_answer? }
- Response: Answer

## GET /api/exams/template?node_id
- Purpose: List exam templates for a course node (instructor view)
- Auth: instructor
- Response: [ExamTemplate]

## POST /api/exams/template
- Purpose: Create an exam template
- Auth: instructor
- Request: { course_path_node_id, title, description?, mode, ruleset?, duration_minutes?, passing_score? }
- Response: ExamTemplate

## PATCH /api/exams/template/{template_id}
- Purpose: Update an exam template
- Auth: instructor
- Request: same as POST
- Response: ExamTemplate | null

## DELETE /api/exams/template/{template_id}
- Purpose: Delete an exam template
- Auth: instructor
- Response: { message: string }

## GET /api/exams/course/{node_id}
- Purpose: List available exam templates for a node (student view)
- Auth: student
- Response: [ExamTemplate]

## POST /api/exams/template-question
- Purpose: Add a question to an exam template
- Auth: instructor
- Request: { exam_template_id, question_id, order, points }
- Response: ExamTemplateQuestion

## GET /api/exams/template/{template_id}/questions-with-details
- Purpose: Get all questions for a template with full details
- Auth: student, instructor
- Response: ExamTemplateQuestionsResponse

## POST /api/exams/{node_id}/static
- Purpose: Create a full static exam with questions in one shot
- Auth: instructor
- Request: StaticExamV2Body
- Response: ExamTemplate

## PATCH /api/exams/{node_id}/static
- Purpose: Update questions on a static exam template
- Auth: instructor
- Request: [StaticQuestionPatchItem]
- Response: StaticExamPatchResponse

## POST /api/exam-sessions/session/create?exam_template_id
- Purpose: Create a new exam session
- Auth: student
- Response: ExamSession

## GET /api/exam-sessions/session/unfinished/{exam_template_id}
- Purpose: Get any unfinished session for this template
- Auth: student
- Response: ExamSession | {}

## GET /api/exam-sessions/session/{session_id}/questions
- Purpose: Get questions for an active session
- Auth: student
- Response: ExamSessionQuestionDisplayResponse

## POST /api/exam-sessions/session/{session_id}/submit
- Purpose: Submit all answers and score the session
- Auth: student
- Request: [{ question_id, text_answer?, selected_options? }]
- Response: ExamSession

## GET /api/exam-sessions/session/all/{exam_template_id}
- Purpose: Get all completed sessions for a template (student's history)
- Auth: student
- Response: [ExamSessionRead]

## GET /api/exam-sessions/session/{session_id}/answers
- Purpose: Get answers and scoring for a completed session
- Auth: student
- Response: ExamSessionAnswerResponse

## POST /api/exam-sessions/session/{session_id}/start
- Purpose: Start (activate) an exam session
- Auth: student
- Response: ExamSession

## GET /api/assessments/topic/{topic_id}
- Purpose: List assessments for a topic (deprecated flow)
- Auth: student
- Response: [Assessment]

## POST /api/assessments/
- Purpose: Create an assessment (deprecated flow)
- Auth: instructor
- Request: { topic_id, question_ids[], paragraph_question_ids[]?, title }
- Response: Assessment

## POST /api/assessments/start
- Purpose: Start an assessment attempt (deprecated flow)
- Auth: student
- Request: { assessment_id }
- Response: AssessmentAttempt

## POST /api/assessments/submit/{attempt_id}
- Purpose: Submit a single answer in an attempt (deprecated flow)
- Auth: student
- Request: { question_id, selected_options?, text_answer? }
- Response: AssessmentAnswer

## POST /api/assessments/submit-all/{attempt_id}
- Purpose: Submit all answers at once (deprecated flow)
- Auth: student
- Request: [{ question_id, selected_options?, text_answer? }]
- Response: [AssessmentAnswer]

## GET /api/assessments/{attempt_id}
- Purpose: Get attempt status (deprecated flow)
- Auth: student
- Response: AssessmentAttempt | null

## GET /api/assessments/{assessment_id}/attempts
- Purpose: List all attempts for an assessment (deprecated flow)
- Auth: student
- Response: [AssessmentAttempt]

## GET /api/assessments/result/{attempt_id}
- Purpose: Get scored review for a completed attempt (deprecated flow)
- Auth: student
- Response: AssessmentReviewResponse

## GET /api/assessments/unfinished-attempt/{assessment_id}
- Purpose: Get any in-progress attempt (deprecated flow)
- Auth: student
- Response: AssessmentAttempt | {}
