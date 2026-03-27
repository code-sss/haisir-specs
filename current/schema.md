## categories
- `id` (UUID PK)
- `name` (String) — category name
- `path_type` (Enum: PathType) — structured or flexible
- `description` (String, nullable)

## course_path_nodes
- `id` (UUID PK)
- `name` (String)
- `node_type` (Enum: NodeType — course/module/unit/etc.) — **currently an enum, not free-string**
- `category_id` (UUID FK→categories.id)
- `parent_id` (UUID FK→course_path_nodes.id, nullable) — self-referential
- `order` (Integer, nullable)
- `owner_type` (String, default: platform) — platform/organization
- `owner_id` (Integer, nullable) — org reference

## topics
- `id` (UUID PK)
- `title` (String)
- `course_path_node_id` (UUID FK→course_path_nodes.id)
- `order` (Integer, nullable)
- `status` (String, default: live)
- `owner_type` (String, default: platform)
- `owner_id` (Integer, nullable)

## topic_contents
- `id` (UUID PK)
- `topic_id` (UUID FK→topics.id)
- `content_type` (Enum: ContentType — text/video/pdf/...)
- `title` (String)
- `url` (String, nullable) — video/PDF URL
- `text` (String, nullable) — embedded text
- `order` (Integer)
- `description` (String, nullable)

## questions
- `id` (UUID PK)
- `question_text` (String)
- `question_type` (Enum: QuestionType — multiple_choice/fitb/essay)
- `options` (JSONB)
- `correct_answers` (JSONB)
- `explanation` (String, nullable)
- `difficulty` (Enum: DifficultyLevel — easy/medium/hard)
- `tags` (JSONB, nullable)
- `image_url` (String, nullable)

## paragraph_questions
- `id` (UUID PK)
- `content` (String) — passage/scenario text
- `title` (String)
- `question_ids` (ARRAY(UUID))
- `paragraph_type` (Enum: ParagraphType)
- `tags` (JSONB, nullable)
- `difficulty` (Enum: DifficultyLevel, nullable)

## exam_templates
- `id` (UUID PK)
- `course_path_node_id` (UUID FK→course_path_nodes.id)
- `title` (String)
- `description` (String, nullable)
- `mode` (Enum: ExamMode — static/dynamic)
- `ruleset` (JSON, nullable)
- `duration_minutes` (Integer, nullable)
- `passing_score` (Float, nullable)
- `created_by` (UUID) — creator idp_sub
- `is_active` (Boolean, default: true)
- `owner_type` (String, default: platform)
- `organization_id` (Integer, nullable)
- `purpose` (String, default: exam) — exam/quiz

## exam_template_questions
- `id` (UUID PK)
- `exam_template_id` (UUID FK→exam_templates.id)
- `question_id` (UUID FK→questions.id)
- `order` (Integer)
- `points` (Integer)
- `paragraph_question_id` (UUID FK→paragraph_questions.id, nullable)

## exam_sessions
- `id` (UUID PK)
- `user_id` (UUID) — student idp_sub
- `exam_template_id` (UUID FK→exam_templates.id, nullable)
- `course_path_node_id` (UUID FK→course_path_nodes.id)
- `mode` (Enum: ExamMode)
- `ruleset` (JSON, nullable)
- `created_at` (DateTime tz)
- `started_at` (DateTime tz, nullable)
- `finished_at` (DateTime tz, nullable)
- `score` (Float, nullable) — raw earned score
- `status` (Enum: ExamStatus — pending/ongoing/completed)

## exam_session_questions
- `id` (UUID PK)
- `exam_session_id` (UUID FK→exam_sessions.id)
- `question_id` (UUID FK→questions.id)
- `order` (Integer)
- `points` (Integer)
- `user_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `earned_points` (Float, nullable)

## assessments _(deprecated — use exam_templates with purpose='quiz')_
- `id` (UUID PK)
- `topic_id` (UUID FK→topics.id)
- `question_ids` (ARRAY(UUID))
- `paragraph_question_ids` (ARRAY(UUID), nullable)
- `title` (String)

## assessment_attempts _(deprecated)_
- `id` (UUID PK)
- `user_id` (UUID)
- `assessment_id` (UUID FK→assessments.id)
- `started_at` (DateTime tz)
- `finished_at` (DateTime tz, nullable)
- `score` (Float, nullable)
- `status` (Enum: AssessmentStatus — ongoing/completed)

## assessment_answers _(deprecated)_
- `id` (UUID PK)
- `attempt_id` (UUID FK→assessment_attempts.id)
- `question_id` (UUID FK→questions.id)
- `selected_options` (ARRAY(String), nullable)
- `text_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `submitted_at` (DateTime tz)

## answers _(orphaned — answer tracking now via exam_session_questions / assessment_answers)_
- `id` (UUID PK)
- `user_id` (UUID)
- `session_id` (UUID)
- `question_id` (UUID FK→questions.id)
- `selected_options` (ARRAY(String), nullable)
- `text_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `submitted_at` (DateTime tz)

## user_metadata
- `idp_sub` (String PK) — Keycloak subject UUID
- `onboarding_completed_at` (DateTime tz, nullable)

## student_profiles
- `id` (UUID PK)
- `idp_sub` (String, unique)
- `first_name`, `last_name` (String)
- `phone` (String, nullable)
- `avatar_url` (String, nullable)
- `grade` (String, nullable)
- `subjects` (JSON, default: [])

## teacher_profiles
- `id` (UUID PK)
- `idp_sub` (String, unique)
- `first_name`, `last_name` (String)
- `phone` (String, nullable)

## parent_profiles
- `id` (UUID PK)
- `idp_sub` (String, unique)
- `first_name`, `last_name` (String)
- `phone` (String, nullable)

## parent_link_codes
- `id` (UUID PK)
- `code` (String, unique)
- `child_sub` (String) — child's idp_sub
- `created_at`, `expires_at` (DateTime tz)
- `is_used` (Boolean, default: false)

## parent_child_links
- `id` (UUID PK)
- `parent_sub` (String)
- `child_sub` (String)
- `created_at` (DateTime tz)
- Unique constraint: (parent_sub, child_sub)

## class_invite_codes
- `id` (UUID PK)
- `code` (String, unique)
- `course_path_node_id` (UUID FK→course_path_nodes.id)
- `created_at` (DateTime tz)
- `expires_at` (DateTime tz, nullable)
