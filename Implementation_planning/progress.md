# Implementation Progress

## Target State

hAIsir is a multi-persona edtech platform serving six roles — student, instructor, tutor, institution admin, parent, and platform admin (SuperAdmin). Content is organised in a self-referential `course_path_nodes` tree of arbitrary depth (free-string `node_type`; only `grade` and `subject` have reserved system behaviour), with `topics` attached exclusively to leaf nodes and up to one `topic_contents` item per type (PDF, video, text) per topic. A LlamaIndex ingestion pipeline chunks and embeds PDF/text content into `topic_content_chunks` (pgvector, `all-MiniLM-L6-v2`, 600-char / 100-char overlap) so that hAITU — the embedded AI tutor — can answer student topic doubts via RAG retrieval (top-5 chunks scoped by `topic_id`) rather than context-stuffing; video-only topics fall back to `text_extracted`. The platform supports structured board curricula (NCERT, CBSE, ICSE, Cambridge, IB MYP) and tutor-built open courses (modular, flat, week-based, section-based), with institution adoption cloning board content into institution-owned copies. The curriculum builder (T04 for tutors, SA02 for platform admins) exposes an arbitrary-depth node tree with a type-picker UI (default chips + custom free text; reserved types shown with 🔒) and enforces the leaf-node rule at the API layer. Assessments (quizzes and exams) are authored via `exam_templates` and assigned to classes with due dates; post-assignment results drive hAITU exam analysis and teacher recommendations. A full notification pipeline covers doubt escalations, assignment due dates, exam results, and at-risk student alerts across all personas. Onboarding flows handle student, teacher/tutor, parent, and institution admin registration including role migration from existing `instructor`/`admin` Keycloak roles. Auth is APISIX-injected JWT with `X-Current-Role` header and CSRF on all mutations; identity is Keycloak `sub` with no local users table.

## Current State
The core content-delivery and assessment loop is fully implemented. The backend has 21 mapped tables covering categories, a three-level course path node tree (grade/subject/course enum — not yet a free string), topics, topic contents (PDF/video/text), questions, paragraph questions, assessments with attempt/answer tracking, static exam templates with per-question points, exam sessions with weighted scoring and pass/fail, and a complete user-metadata layer (onboarding state, student profiles, teacher profiles, parent-child invite codes, class invite codes). All 17 route modules are wired with CSRF validation and role-based guards (`student`, `instructor`, `admin`); the `assign-role` endpoint is defined but the Keycloak Admin API call is a TODO stub. The frontend (Next.js) covers the course dashboard with hierarchical navigation, assessment flow (take / resume / review), static exam flow (instructor create/edit, student take/review with timer and weighted results), category management for admins, and a full onboarding flow (role selection, student profile, parent-child linking, role switcher). Infrastructure runs PostgreSQL 16, Keycloak 26.4, and APISIX with Coraza WAF, CrowdSec, and rate limiting. **Not yet built:** the `topic_content_chunks` pgvector table and LlamaIndex RAG pipeline (hAITU), curriculum builder UI, notifications, institution admin flows, parent dashboard, and tutor course builder.

## Next Phase
<!-- The agreed next concrete step. Updated after each /plan-next-state discussion. -->

**Phase 0 — Onboarding end-to-end: wire assign_role + fix ON03/ON05 to spec**

Rationale: `assign_role()` is a 501 stub (Keycloak Admin API not wired), making the entire onboarding dead. ON03 and ON05 were built against the old spec — ON03 has a profile form (removed by BR-ON-008) and ON05 has a link-code form (removed by BR-ON-015). Fixing these together completes the Student and Parent onboarding paths end-to-end.

Scope:
- **haisir-deploy:** Add 3 Keycloak realm roles (`institution_admin`, `tutor`, `parent`)
- **haisir-backend:** Wire Keycloak Admin REST API call in `user_metadata_service.py:assign_role()`; add Keycloak Admin client credentials to `shared/config.py`
- **haisir-frontend:**
  - Replace `on03-student-profile.tsx` → `on03-student-ready.tsx` ("You're all set, there!" + "Join your school" + "Browse open courses" CTAs, no form — per BR-ON-008)
  - Replace `on05-parent-link.tsx` → `on05-parent-ready.tsx` ("You're all set, there!" + "Link your child" CTA, no inline code input — per BR-ON-015)
  - Add silent iframe JWT refresh (`prompt=none`) in `use-onboarding.ts` after `assign_role` succeeds
  - Confirm `onboarding_completed` redirect guard fires on root page load
