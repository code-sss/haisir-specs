# hAIsir Specs — Phase 1 Review Decisions
> **Review date:** 2026-03-22
> **Reviewers:** Product Manager, Tech Lead
> **Scope:** Phase 1 foundation files — `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`, `11_role_migration.md`
> **Status:** Complete ✅

---

## How to Use This Document

This file is a record of all decisions made during the Phase 1 human review of hAIsir specs. It serves three purposes:
- **Traceability** — why a decision was made, not just what it is
- **Onboarding** — new team members can read this to understand the reasoning behind spec choices
- **Future reviews** — decisions marked "revisit post-launch" are flagged for follow-up

---

## PM Review Decisions

### Personas & Product Scope

| Decision | Outcome | Rationale |
|---|---|---|
| 6 personas (Student, Instructor, Tutor, Institution Admin, Parent, Platform Admin) | ✅ Confirmed correct and complete | No missing personas for v1 scope |
| Dual-track learning model (structured + open) | ✅ Confirmed | Core product model — both tracks must coexist |
| Student self-discovery of tutor courses | ✅ Confirmed intentional | Students can find and enroll in tutor courses without an invite |
| Payment processing | ✅ Deferred to later phase | No payment in v1 — but extensibility columns added now (see Tech Lead decisions) |
| Out of scope list (live video, mobile app, offline, multi-language, peer collaboration etc.) | ✅ Confirmed — no surprises | All deferred items are acceptable for v1 |

---

### Content & Data Model

| Decision | Outcome | Rationale |
|---|---|---|
| Mastery formula: first attempt = raw score, subsequent = (0.6 × latest) + (0.4 × previous) | ✅ Accepted for now | Pedagogically reasonable — revisit post-launch with real usage data |
| Mastery thresholds: <60 weak, 60–75 progressing, >75 completed | ✅ Accepted for now | Revisit post-launch |
| One-way topic archiving (no revert to live) | ✅ Accepted | UI confirmation dialog to be added as guard against accidental archives |
| Exam question snapshot | ✅ No snapshot — live FK references kept | Simplicity preferred. UI warning added for teachers editing questions used in completed exams |

---

### Permissions & Auth

| Decision | Outcome | Rationale |
|---|---|---|
| Parent privacy boundary | ✅ Confirmed | Parents see scores and doubt status — not question content or doubt message content |
| Parent-to-institutional-teacher contact | ✅ No in-app mechanism for v1 | "Contact goes through the institution" is sufficient for v1 |
| Multi-role combinations | ✅ All non-admin combos allowed | Independent workspaces handle data separation. See full matrix in `11_role_migration.md` §8 |
| `admin` role isolation | ✅ Admin must be a dedicated account — cannot combine with any other role | Enforced at Keycloak and backend API level. See BR-ROLE-004 |
| Role migration risk | ✅ Low | Platform is effectively greenfield — no existing user migration complexity |

---

## Tech Lead Review Decisions

### Payment Extensibility

**Decision:** Add `subscription_status` and `payment_id` columns to both `enrollments` and `tutor_student_relationships` tables now, even though payment processing is out of scope for v1.

| Column | Type | Default | Notes |
|---|---|---|---|
| `subscription_status` | `'free' \| 'paid'` | `'free'` | Not null |
| `payment_id` | `str \| None` | `null` | Null for all free courses |

**Rationale:** Avoids table restructuring when payment is added later. All records default to free tier in v1. Per-course paid/free setting to be added in a future phase.

**Spec updated:** `01_data_model.md` — BR-ENROLL-PAY-001, BR-TUTOR-PAY-001

---

### Pagination Strategy

**Decision:** Use both cursor-based and offset-based pagination depending on use case.

| Type | Used for | Params |
|---|---|---|
| Cursor-based | Notifications, activity timeline, doubt threads, hAITU chat history | `cursor` → response includes `next_cursor` (null when done) |
| Offset-based | Student lists, class rosters, institution people manager, admin tables | `page` (default 1), `page_size` (default 20, max 100) |

**Rule:** Each endpoint spec must explicitly state which pagination type it uses.

**Spec updated:** `00_overview.md` — pagination convention section

---

### File Storage

**Decision:** Local disk for v1. Storage abstraction layer to be built now for future swappability.

| Item | Detail |
|---|---|
| v1 storage | Local disk at `data_dir/` — follows existing question image pattern |
| Abstraction | `StorageBackend` interface in `infrastructure/storage/` with `upload(file, path) → url` and `download(path) → bytes` |
| v1 implementation | `LocalDiskBackend` |
| Config | `STORAGE_BACKEND` environment variable (default: `local`) |
| Future backends | `S3Backend`, `GCSBackend`, `AzureBackend` — swappable without application code changes |

**Rationale:** Platform may migrate to Google Cloud Storage, Azure, or S3 depending on cost and scale. Abstraction now avoids a painful refactor later.

**Spec updated:** `00_overview.md` — file storage convention section

---

### Dynamic Exam Ruleset Schema

**Decision:** Combination-based ruleset — difficulty mix, topics, tags, and question types.

```json
{
  "total_questions": 10,
  "difficulty_mix": {
    "easy": 4,
    "medium": 4,
    "hard": 2
  },
  "topics": ["uuid-1", "uuid-2"],
  "tags_include": ["algebra", "fractions"],
  "tags_exclude": ["advanced"],
  "question_types": ["single_choice", "multiple_choice", "fill_in_the_blank"]
}
```

| Rule | Detail |
|---|---|
| Required field | `total_questions` only — all other fields optional |
| Selection | Random within matching candidates |
| Difficulty fallback | If insufficient at requested level → fill from next level down (hard → medium → easy) |
| Insufficient questions | Return error at exam creation time with available vs requested count |
| Validation | At `POST /api/exam-templates` creation time, not at session creation time |
| Consistency check | `difficulty_mix` values must sum to `total_questions` if both provided |

**Spec updated:** `01_data_model.md` — `exam_templates` ruleset field definition

---

### hAITU Escalation Trigger

**Decision:** Replace phrase-match ("ask your teacher") with structured JSON output from Claude.

**Old approach (removed):** String match on LLM response text — fragile, Claude may rephrase.

**New approach:** Claude returns a JSON object for all `topic-doubt` and `escalation-attempt` interactions:

```json
{
  "response": "The explanation text shown to the student...",
  "escalation_ready": true
}
```

| Rule | Detail |
|---|---|
| `escalation_ready: true` | Claude cannot fully resolve the doubt |
| `escalation_ready: false` | All other cases |
| Backend action | Sets `doubt.haitu_attempted = true` when `escalation_ready: true` |
| Student action | Can also explicitly click "Request teacher help" at any time after `haitu_attempted = true` |
| Enforcement | System prompts in sections 3.1 and 3.3 instruct Claude to return JSON only — no prose outside JSON |

**Rationale:** LLM phrase-match is unreliable in production — Claude may rephrase the trigger phrase based on context. Structured output is deterministic and testable.

**Spec updated:** `08_haitu_ai_layer.md` — sections 3.1 and 3.3

---

### Exam Correct Answers Mutation Risk

**Decision:** No backend guard. UI warning only.

**Risk:** If a teacher edits `correct_answers` on a question after a student completes an exam, `is_correct` on existing `exam_session_questions` rows becomes stale.

**Resolution:** Frontend displays a warning when editing a question used in completed exam sessions:
> *"This question has been used in X completed exams. Editing it will affect how those exams display and may affect grading if correct answers are changed."*

**Rationale:** Adding a backend lock adds schema complexity. The risk is low in a greenfield platform with relatively few completed exams. Revisit if teacher edits cause grading disputes post-launch.

**Spec updated:** `01_data_model.md` — UI note on `exam_session_questions`

---

## UI Notes (for frontend spec)

| Note | Location in spec |
|---|---|
| Add "Are you sure?" confirmation before topic archive action | `01_data_model.md` — topics status lifecycle |
| Add warning when editing a question used in completed exam sessions | `01_data_model.md` — `exam_session_questions` |

---

## Still Pending

| Item | Status | Owner |
|---|---|---|
| Archived topic clone flow — can tutors clone an archived topic? | ❓ Unresolved | PM to decide |
| Phase 2 persona review (Student, Teacher/Tutor, Parent, Institution Admin, Platform Admin) | 🔜 Not started | PM + Tech Lead as needed |

---

## Spec Files Updated in This Review

| File | Changes |
|---|---|
| `requirements/00_overview.md` | Pagination convention, storage abstraction convention |
| `requirements/01_data_model.md` | UI notes for archiving and question edits, payment columns on enrollments and tutor_student_relationships, dynamic exam ruleset schema |
| `requirements/02_auth_and_roles.md` | BR-SEC-009 self-assignment restriction, multi-role combination reference |
| `requirements/08_haitu_ai_layer.md` | Structured JSON escalation output in sections 3.1 and 3.3 |
| `requirements/11_role_migration.md` | BR-ROLE-004, BR-ROLE-005, full combination matrix §8, enforcement layers, 4 new QA test cases |
| `gap-analysis.md` | Pagination, file storage, dynamic exam ruleset, payment extensibility marked resolved |
| `review-checklist.md` | New checks added, escalation trigger updated, doubt auto-close item cleaned up |

