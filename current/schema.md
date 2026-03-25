## categories
- `id` (UUID PK) — unique category identifier
- `name` (String) — display name
- `path_type` (Enum: PathType) — board/curriculum type
- `description` (String, nullable) — optional description

## course_path_nodes
- `id` (UUID PK)
- `name` (String) — node display name
- `node_type` (Enum: grade | subject | course) — **currently an enum, not a free string** (diverges from Target State)
- `category_id` (UUID FK → categories.id)
- `parent_id` (UUID FK → course_path_nodes.id, nullable) — self-referential tree
- `order` (Integer, nullable)
- `owner_type` (String, default "platform") — platform / institution / tutor
- `owner_id` (Integer, nullable) — owner reference (no FK constraint)

## topics
- `id` (UUID PK)
- `title` (String)
- `course_path_node_id` (UUID FK → course_path_nodes.id)
- `order` (Integer, nullable)
- `status` (String, default "live")
- `owner_type` (String, default "platform")
- `owner_id` (Integer, nullable)

## topic_contents
- `id` (UUID PK)
- `topic_id` (UUID FK → topics.id)
- `content_type` (Enum: video | pdf | text | question | question_answer)
- `title` (String)
- `url` (String, nullable) — filesystem-relative path for file-backed content
- `text` (String, nullable) — inline text content
- `order` (Integer)
- `description` (String, nullable)

## questions
- `id` (UUID PK)
- `question_text` (String)
- `question_type` (Enum: single_choice | multiple_choice | true_false | fill_in_the_blank | essay)
- `options` (JSONB) — list of {id, text, image_url}
- `correct_answers` (JSONB) — list of correct option IDs or text values
- `explanation` (String, nullable)
- `difficulty` (Enum: easy | medium | hard)
- `tags` (JSONB, nullable)
- `image_url` (String, nullable)

## paragraph_questions
- `id` (UUID PK)
- `content` (String) — the passage/paragraph text
- `title` (String)
- `question_ids` (UUID[], PG array) — ordered list of child question IDs
- `paragraph_type` (Enum: ParagraphType)
- `tags` (JSONB, nullable)
- `difficulty` (Enum: easy | medium | hard, nullable)

## assessments
- `id` (UUID PK)
- `topic_id` (UUID FK → topics.id)
- `question_ids` (UUID[], PG array)
- `paragraph_question_ids` (UUID[], PG array, nullable)
- `title` (String)

## assessment_attempts
- `id` (UUID PK)
- `user_id` (UUID) — Keycloak sub cast to UUID, no FK
- `assessment_id` (UUID FK → assessments.id)
- `started_at` (DateTime tz)
- `finished_at` (DateTime tz, nullable)
- `score` (Float, nullable)
- `status` (Enum: pending | ongoing | completed | failed)

## assessment_answers
- `id` (UUID PK)
- `attempt_id` (UUID FK → assessment_attempts.id)
- `question_id` (UUID FK → questions.id)
- `selected_options` (String[], nullable)
- `text_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `submitted_at` (DateTime tz)

## exam_templates
- `id` (UUID PK)
- `course_path_node_id` (UUID FK → course_path_nodes.id)
- `title` (String)
- `description` (String, nullable)
- `mode` (Enum: static | dynamic | custom)
- `ruleset` (JSON, nullable) — for dynamic/custom modes
- `duration_minutes` (Integer, nullable)
- `passing_score` (Float, nullable)
- `created_by` (UUID) — Keycloak sub, no FK
- `is_active` (Boolean, default true)
- `owner_type` (String, default "platform")
- `organization_id` (Integer, nullable)
- `purpose` (String, default "exam")

## exam_template_questions
- `id` (UUID PK)
- `exam_template_id` (UUID FK → exam_templates.id)
- `question_id` (UUID FK → questions.id)
- `order` (Integer)
- `points` (Integer)
- `paragraph_question_id` (UUID FK → paragraph_questions.id, nullable)

## exam_sessions
- `id` (UUID PK)
- `user_id` (UUID) — Keycloak sub, no FK
- `exam_template_id` (UUID FK → exam_templates.id, nullable)
- `course_path_node_id` (UUID FK → course_path_nodes.id)
- `mode` (Enum: static | dynamic | custom)
- `ruleset` (JSON, nullable)
- `created_at` (DateTime tz, nullable)
- `started_at` (DateTime tz, nullable)
- `finished_at` (DateTime tz, nullable)
- `score` (Float, nullable)
- `status` (Enum: pending | ongoing | completed | failed)

## exam_session_questions
- `id` (UUID PK)
- `exam_session_id` (UUID FK → exam_sessions.id)
- `question_id` (UUID FK → questions.id)
- `order` (Integer)
- `points` (Integer)
- `user_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `earned_points` (Float, nullable)

## answers
- `id` (UUID PK)
- `user_id` (UUID) — Keycloak sub, no FK
- `session_id` (UUID) — exam session reference, no FK
- `question_id` (UUID FK → questions.id)
- `selected_options` (String[], nullable)
- `text_answer` (String, nullable)
- `is_correct` (Boolean, nullable)
- `submitted_at` (DateTime tz)

## user_metadata
- `idp_sub` (String PK) — Keycloak sub claim
- `onboarding_completed_at` (DateTime tz, nullable)

## student_profiles
- `id` (UUID PK)
- `idp_sub` (String, unique)
- `first_name` (String)
- `last_name` (String)
- `phone` (String, nullable)
- `avatar_url` (String, nullable)
- `grade` (String, nullable)
- `subjects` (JSON, default [])

## teacher_profiles
- `id` (UUID PK)
- `idp_sub` (String, unique)
- `first_name` (String)
- `last_name` (String)
- `phone` (String, nullable)

## parent_link_codes
- `id` (UUID PK)
- `code` (String, unique)
- `child_sub` (String) — Keycloak sub of the child
- `created_at` (DateTime tz)
- `expires_at` (DateTime tz)
- `is_used` (Boolean, default false)

## parent_child_links
- `id` (UUID PK)
- `parent_sub` (String) — Keycloak sub
- `child_sub` (String) — Keycloak sub
- `created_at` (DateTime tz)
- unique constraint on (parent_sub, child_sub)

## class_invite_codes
- `id` (UUID PK)
- `code` (String, unique)
- `course_path_node_id` (UUID FK → course_path_nodes.id)
- `created_at` (DateTime tz)
- `expires_at` (DateTime tz, nullable)

---

## Not yet implemented (Target State gaps)
- `topic_content_chunks` — pgvector RAG table for LlamaIndex ingestion pipeline (hAITU)
- `parent_profiles` — domain model exists but no infrastructure mapping or migration
