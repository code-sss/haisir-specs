# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:681d97a frontend:0446707 deploy:32e028c (2026-06-08)

## G1 [backend]: Schema extended

- [x] T1.1 [backend]: Alembic V27 non-transactional migration — AUTOCOMMIT enum extension + 4 new columns (2026-06-06)
- [x] T1.2 [backend]: SQLAlchemy imperative table mappings updated (essay_subtype, working_required on questions; working_text, shuffle_seed on exam_session_questions) (depends on T1.1) (2026-06-06)
- [ ] **G1: Schema extended** — integration test: insert rows with all 4 new fields; assert round-trip via SQLAlchemy

## G2 [backend]: Domain layer supports new types

- [x] T2.1 [backend]: QuestionType enum + QuestionOption.side field (2026-06-06)
- [x] T2.2 [backend]: Question.validate() for new types + canonical matching correct_answers format (depends on T2.1) (2026-06-06)
- [x] T2.3 [backend]: ExamSessionQuestion domain model new fields (working_text, shuffle_seed) (2026-06-06)
- [ ] **G2: Domain layer** — integration test: validate() for each new type; load from DB; confirm field persistence

## G3 [backend]: Grading handles new types

- [x] T3.1 [backend]: Grading cases for one_word_response + problem_solving in grading.py (depends on T2.1) (2026-06-06)
- [x] T3.2 [backend]: _grade_matching helper — partial credit formula, JSON pair parsing (depends on T2.1, T2.2, T2.3) (2026-06-06)
- [x] T3.3 [backend]: _resolve_answer_options updated for matching display in exam results (depends on T2.1, T3.2) (2026-06-06)
- [ ] **G3: Grading** — integration test: full Question from DB, grade_question() end-to-end, assert partial credit

## G4 [backend]: Session creation seeds matching shuffle

- [x] T4.1 [backend]: shuffle_seed generation in POST /session/create + QuestionService injection + service method extension (depends on T1.2, T2.1, T2.3) (2026-06-06)
- [x] T4.2 [backend]: working_text capture in POST /session/{id}/submit — AnswerCreate extension (depends on T2.1, T2.3) (2026-06-06)
- [ ] **G4: Session seeding** — integration test: create session → shuffle_seed non-null for matching; submit problem_solving with working_text → assert persisted

## G5 [backend]: API contracts expose new fields

- [x] T5.1a [backend]: Question Pydantic schemas — QuestionBase (essay_subtype, working_required), QuestionOptionBase (side) (depends on T2.1, T2.2) (2026-06-06)
- [x] T5.1b [backend]: Session-question display schema + route wiring for shuffle_seed — shuffle_seed_map, working_required, essay_subtype in ExamSessionQuestionDisplay (depends on T2.1, T2.2, T2.3, T4.1, T5.1a) (2026-06-06)
- [ ] **G5: API contracts** — integration test: GET /session/{id}/questions returns shuffle_seed, working_required, essay_subtype per question

## G6 [frontend]: Student exam UI renders new types

- [x] T6.0 [frontend]: Extend frontend type system — QuestionType union, ExamQuestionType interface, QuestionAnswer variants, AnswerPayload (2026-06-06)
- [x] T6.0b [frontend]: Update question-type-utils.ts + answer-transformer.ts for all 3 new types (depends on T6.0) (2026-06-06)
- [x] T6.1 [frontend]: Seeded Fisher-Yates utility (LCG) — seeded-shuffle.ts (2026-06-06)
- [x] T6.2 [frontend]: one_word_response question component (depends on T6.0, T6.0b) (2026-06-06)
- [x] T6.3 [frontend]: matching question component — two-column dropdown + seeded shuffle (depends on T6.0, T6.0b, T6.1) (2026-06-06)
- [x] T6.4 [frontend]: problem_solving question component — answer input + optional working textarea (depends on T6.0, T6.0b) (2026-06-06)
- [x] T6.5 [frontend]: essay_subtype rendering hint in essay-input.tsx (depends on T6.0) (2026-06-06)
- [x] **G6: Student exam UI** — integration test: render QuestionRenderer for all 8 types; assert components + payload shapes (2026-06-06)

## ROOT acceptance test

- [ ] **ROOT [e2e]: Full question type extension flow** — Playwright: one_word_response, matching (shuffled, partial credit), problem_solving (working captured), essay_subtype hint

---

## Ready now

All leaf tasks (G1–G5 backend, G6 frontend) are complete. Ready to run integration tests — can be started in parallel:

- **G1 integration test** [backend]: insert rows with all 4 new fields; assert round-trip via SQLAlchemy
- **G2 integration test** [backend]: validate() for each new type; load from DB; confirm field persistence
- **G3 integration test** [backend]: full Question from DB, grade_question() end-to-end, assert partial credit
- **G4 integration test** [backend]: create session → shuffle_seed non-null for matching; submit problem_solving with working_text → assert persisted
- **G5 integration test** [backend]: GET /session/{id}/questions returns shuffle_seed, working_required, essay_subtype per question

ROOT acceptance test requires G1–G5 integration tests above (G6 is already done).
