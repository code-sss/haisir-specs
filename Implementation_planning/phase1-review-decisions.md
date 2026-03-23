# hAIsir Specs — Phase 1 Review Decisions
> **Review date:** 2026-03-22
> **Reviewers:** Product Manager, Tech Lead
> **Scope:** Phase 1 — foundation files (`00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`, `11_role_migration.md`, `03_student`) and persona specs (`04_teacher_tutor`, `05_06_07_personas`)
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

---

## Persona Spec Review — Teacher / Tutor (`04_teacher_tutor.md`)
> Review date: 2026-03-23

| Decision | Outcome | Rationale |
|---|---|---|
| At-risk threshold — mastery < 50% on 3+ topics (BR-TCH-004) | ✅ Confirmed — no change | Intentional divergence from student weak threshold (< 60%). Stricter signal surfaces only genuinely at-risk students. BR-INST-001 already aligned. |
| Instructor content delete permissions | ✅ Added — BR-TCH-026 | Instructors can delete only their own uploaded supplemental content. Cannot delete platform-owned or institution-owned items. |
| Teacher notes admin visibility (BR-TCH-009) | ✅ Confirmed — note added | Absolute privacy in v1. No admin override path. Future safeguarding override requires dedicated audit-logged feature with legal review before implementation. |
| Two roster rows for same student + tutor (BR-TCH-011) | ✅ Confirmed — no change | Two separate rows per `enrollment_id`. Simpler implementation; T03 context unambiguous. |
| Topic publish / archive confirmation UX (BR-TCH-023, BR-TCH-024) | ✅ Confirmed — UI note added to T04 | Publish immediate — no confirmation modal. Archive requires modal: "Students will no longer see this topic. This cannot be undone." |
| Teacher reply edit window (BR-DOUBT-011) | ✅ Changed | 5-minute edit window allowed after sending. After 5 minutes, messages locked and immutable. `edited_at` (nullable datetime) added to `doubt_messages` in `01_data_model.md`. |
| Exam results visibility while assignment is open (BR-TCH-020) | ✅ Changed | Two-state model: while open → `submission_count` and `total` only, all result fields null. After due date or full submission → full results returned. |
| "Generate remedial assignment" button — Phase 1 | ✅ Deferred to Phase 2 | Excluded from Phase 1 T08 build entirely — no stub, no disabled state. Added in Phase 2 alongside the hAITU build. |

---

## Persona Spec Review — Parent (`05_06_07_personas.md` Part A)
> Review date: 2026-03-23

| Decision | Outcome | Rationale |
|---|---|---|
| P02 plain-language descriptions — Phase 1 fallback (BR-PAR-006) | ✅ Changed | Phase 1: static score-based strings (< 40% / 40–59% / 60–74% / ≥ 75%). Phase 2: hAITU prose replaces strings with no UI change required. |
| Parent question content boundary (BR-PAR-009) | ✅ Confirmed — no change | Scores only — no question text, correct answers, or individual answers. "For question-level detail, contact the teacher" info note stays. |
| Parent-teacher messaging asymmetry (BR-PAR-013, BR-PAR-014) | ✅ Confirmed — no change | Parent messages tutors only via `parent_tutor_messages`. Institutional teacher card shows contact-through-institution note only. |
| Status banner thresholds (BR-PAR-004) | ✅ Changed | ok = no weak topics (all mastery ≥ 60); warn = 1–3 topics with mastery 40–59%; danger = any topic mastery < 40% OR more than 3 weak topics. Aligns warn level with student weak threshold. |
| Weekly digest Phase 1 content (BR-PAR-015) | ✅ Changed | Phase 1: stats-only (streak, topics this week, active courses, weak topic count). Phase 2: hAITU-generated prose summary. No notification schema change required. |
| Maximum children per parent | ✅ Added — BR-PAR-016 | Cap at 10 per parent account in v1. Edge case (e.g. tutoring centre manager using parent role) justifies higher cap than 5. Enforced at `POST /api/parent-child-links` with 422. |
| Parent-tutor message visibility to student (BR-PAR-013) | ✅ Note added | `parent_tutor_messages` are not visible to the student. Keeps student's doubt thread clean. |

---

## Persona Spec Review — Institution Admin (`05_06_07_personas.md` Part B)
> Review date: 2026-03-23

| Decision | Outcome | Rationale |
|---|---|---|
| Board import conflict resolution (BR-INST-018) | ✅ Confirmed — note added | Auto-resolve in favour of institution version. No per-topic override UI in v1. Preview shows (N new, N skipped, N conflicts) but conflicts auto-resolve. |
| Board publish propagation (BR-SA-005, BR-INST-006) | ✅ Changed — notes added | Modified topics preserved; unchanged topics updated to new board version. Institution can safely customise without risk of overwrite on next board publish. |
| Teacher invite acceptance (BR-INST-008) | ✅ Confirmed — no change | Institution admin authority is sufficient — no in-app acceptance step needed. Immediate `org_members` add with `status = 'active'`. Welcome notification sent. |
| CSV enroll for unknown student emails (BR-INST-017) | ✅ Changed | Generate invite links for missing emails instead of skipping with error. Backend returns `{email, invite_url}` list; admin forwards to students. Student auto-enrolled on first login via invite link. |
| Teacher class averages — cohort disclaimer (I05) | ✅ Changed — disclaimer added | "Class averages reflect the assigned student cohort, not a measure of teacher performance." Chart stays visible. |
| Analytics time periods (I05 endpoint) | ✅ Changed | `?period=month\|term\|all` added. term = current 4-month academic window; all = since institution created. |
| Institution admin doubt content access (BR-INST-007, BR-INST-015) | ✅ Confirmed — no change | Aggregate only — count and status per student. Never message bodies, even in analytics. |

---

## Persona Spec Review — Platform Admin (`05_06_07_personas.md` Part C)
> Review date: 2026-03-23

| Decision | Outcome | Rationale |
|---|---|---|
| Board publish notification — opt-in per publish | ✅ Confirmed — no change | SuperAdmin controls `notify_admins` per publish call. Minor/internal edits can skip notifications. |
| User suspension — immediate Keycloak revocation (BR-SA-013) | ✅ Confirmed — no change | No grace period, no user warning. Moderation action — SuperAdmin has already made the determination. |
| Feature flags — total count (SA06) | ✅ Changed | 6 flags total. Added: (5) `haitu_enabled_global` — global AI on/off (when off, all hAITU calls return graceful "AI is currently unavailable"); (6) `institution_self_registration` — flag defined now, public-facing form implementation deferred. SA06 API response updated. |
| AI log retention period and purge scope (BR-SA-018) | ✅ Changed | Retention period configurable (default 90 days, via `ai_log_retention_days`). Scope: `doubt_messages` with `sender_type = 'ai'` only. Teacher-tools and parent-report outputs are on-demand, not stored — nothing to purge for those. |
| SA03 — institution pending state | ✅ Changed | No pending state in v1. SA03 shows Active + Inactive tabs only. "Pending approval" tab removed. Deferred to when institution self-registration is built. |

---

## Spec Files Updated — Persona Review

| File | Changes |
|---|---|
| `requirements/04_teacher_tutor.md` | BR-TCH-026 (instructor own-content delete only), BR-TCH-009 note (no admin override in v1), T04 UI note (publish immediate/no modal; archive confirmation text), BR-DOUBT-011 (5-min edit window), BR-TCH-020 (two-state results model), T08 phase note (remedial assignment deferred to Phase 2) |
| `requirements/05_06_07_personas.md` | BR-PAR-006 (Phase 1 static fallback + Phase 2 upgrade path), BR-PAR-004 (two-level warn/danger thresholds), BR-PAR-015 (Phase 1 stats-only digest note), BR-PAR-016 (max 10 children cap + 422 error), BR-PAR-013 note (parent-tutor messages not visible to student), BR-INST-006 note (publish propagation preserves modified topics), BR-INST-017 (invite links for unknown emails; endpoint response updated), BR-INST-018 note (auto-resolve confirmation), I05 teacher_avgs disclaimer, I05 analytics endpoint period options (month/term/all), SA01 stat row (pending → inactive), SA03 (Pending tab removed + endpoint updated), SA06 features card (6 flags), SA06 API response (haitu_enabled_global, institution_self_registration, ai_log_retention_days), BR-SA-005 (propagation detail), BR-SA-018 (configurable retention + scope clarification) |
| `requirements/01_data_model.md` | `doubt_messages` table: `edited_at: datetime \| None` field added; BR-DOUBT-002 updated to reflect 5-minute teacher edit window exception |
| `requirements/11_role_migration.md` | Note added to §6.4: invite-link enrollment requires onboarding to handle pre-populated enrollment context from invite URL |
| `review-checklist.md` | `04_teacher_tutor.md` and `05_06_07_personas.md` items marked `[x]`; all decisions noted inline |
| `gap-analysis.md` | Added deferred items: teacher notes admin override (post-launch), remedial assignment (Phase 2), P02 hAITU descriptions (Phase 2 upgrade), weekly digest AI prose (Phase 2), institution self-registration (future phase), invite-link enrollment (Phase 1 implementation note) |

---

## Still Pending

| Item | Status | Owner |
|---|---|---|
| Archived topic clone flow — can tutors clone an archived topic? | ✅ Yes — tutors can clone archived topics to create corrected versions (BR-CONTENT-005) | PM decided |
| Phase 1 persona review (Student, Teacher/Tutor, Parent, Institution Admin, Platform Admin) | ✅ Complete — persona specs reviewed and decisions applied in this document. | PM |
| Teacher notes admin override (safeguarding) | 🔜 Deferred post-launch — requires dedicated audit-logged override feature with legal review before implementation | PM + Legal |
| "Generate remedial assignment" button (T08) | 🔜 Phase 2 — excluded from Phase 1 T08 build entirely | PM |
| P02 hAITU plain-language descriptions | 🔜 Phase 2 — Phase 1 uses static score-based fallback text (BR-PAR-006) | PM |
| Weekly digest AI prose | 🔜 Phase 2 — Phase 1 uses stats-only digest (BR-PAR-015) | PM |
| Institution self-registration | 🔜 Flag `institution_self_registration` defined in v1; public-facing signup form + SA03 Pending tab deferred to future phase | PM |
| Invite-link enrollment flow | 🔜 Phase 1 implementation required — onboarding must accept pre-populated enrollment context from invite URL. See BR-INST-017 and `11_role_migration.md` §6.4 | Dev |

> **Note:** Phase 0 review (see `phase0-review-decisions.md`) made significant changes that supersede some Phase 1 decisions: assessment module deprecated (unified under `exam_templates`), role assignment model overhauled (instructor invited, tutor explicit flow), `keycloak_sub` renamed to `idp_sub`, BR-SEC-009 updated. Phase 1 decisions above remain valid as historical record but the current spec state reflects Phase 0 updates.

