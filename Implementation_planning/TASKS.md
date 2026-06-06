# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:bb69798 frontend:64c20ec deploy:32e028c (2026-06-05)

## G1 [backend]: Schema extended

- [ ] T1.1 [backend]: Alembic V27 non-transactional migration — AUTOCOMMIT enum extension + 4 new columns
- [ ] T1.2 [backend]: SQLAlchemy imperative table mappings updated (essay_subtype, working_required on questions; working_text, shuffle_seed on exam_session_questions) (depends on T1.1)
- [ ] **G1: Schema extended** — integration test: insert rows with all 4 new fields; assert round-trip via SQLAlchemy

## G2 [backend]: Domain layer supports new types

- [ ] T2.1 [backend]: QuestionType enum + QuestionOption.side field
- [ ] T2.2 [backend]: Question.validate() for new types + canonical matching correct_answers format (depends on T2.1)
- [ ] T2.3 [backend]: ExamSessionQuestion domain model new fields (working_text, shuffle_seed)
- [ ] **G2: Domain layer** — integration test: validate() for each new type; load from DB; confirm field persistence

## G3 [backend]: Grading handles new types

- [ ] T3.1 [backend]: Grading cases for one_word_response + problem_solving in grading.py (depends on T2.1)
- [ ] T3.2 [backend]: _grade_matching helper — partial credit formula, JSON pair parsing (depends on T2.1, T2.2, T2.3)
- [ ] T3.3 [backend]: _resolve_answer_options updated for matching display in exam results (depends on T2.1, T3.2)
- [ ] **G3: Grading** — integration test: full Question from DB, grade_question() end-to-end, assert partial credit

## G4 [backend]: Session creation seeds matching shuffle

- [ ] T4.1 [backend]: shuffle_seed generation in POST /session/create + QuestionService injection + service method extension (depends on T1.2, T2.1, T2.3)
- [ ] T4.2 [backend]: working_text capture in POST /session/{id}/submit — AnswerCreate extension (depends on T2.1, T2.3)
- [ ] **G4: Session seeding** — integration test: create session → shuffle_seed non-null for matching; submit problem_solving with working_text → assert persisted

## G5 [backend]: API contracts expose new fields

- [ ] T5.1a [backend]: Question Pydantic schemas — QuestionBase (essay_subtype, working_required), QuestionOptionBase (side) (depends on T2.1, T2.2)
- [ ] T5.1b [backend]: Session-question display schema + route wiring for shuffle_seed — shuffle_seed_map, working_required, essay_subtype in ExamSessionQuestionDisplay (depends on T2.1, T2.2, T2.3, T4.1, T5.1a)
- [ ] **G5: API contracts** — integration test: GET /session/{id}/questions returns shuffle_seed, working_required, essay_subtype per question

## G6 [frontend]: Student exam UI renders new types

- [ ] T6.0 [frontend]: Extend frontend type system — QuestionType union, ExamQuestionType interface, QuestionAnswer variants, AnswerPayload
- [ ] T6.0b [frontend]: Update question-type-utils.ts + answer-transformer.ts for all 3 new types (depends on T6.0)
- [ ] T6.1 [frontend]: Seeded Fisher-Yates utility (LCG) — seeded-shuffle.ts
- [ ] T6.2 [frontend]: one_word_response question component (depends on T6.0, T6.0b)
- [ ] T6.3 [frontend]: matching question component — two-column dropdown + seeded shuffle (depends on T6.0, T6.0b, T6.1)
- [ ] T6.4 [frontend]: problem_solving question component — answer input + optional working textarea (depends on T6.0, T6.0b)
- [ ] T6.5 [frontend]: essay_subtype rendering hint in essay-input.tsx (depends on T6.0)
- [ ] **G6: Student exam UI** — integration test: render QuestionRenderer for all 8 types; assert components + payload shapes

## ROOT acceptance test

- [ ] **ROOT [e2e]: Full question type extension flow** — Playwright: one_word_response, matching (shuffled, partial credit), problem_solving (working captured), essay_subtype hint

---

## Ready now

Tasks with no pending dependencies — can be started immediately in parallel:

- T1.1 [backend]: Alembic V27 migration (no deps)
- T2.1 [backend]: QuestionType enum + QuestionOption.side (no deps; deploy after T1.1)
- T2.3 [backend]: ExamSessionQuestion domain model new fields (no deps)
- T6.0 [frontend]: Extend frontend type system (no deps)
- T6.1 [frontend]: Seeded Fisher-Yates LCG utility (no deps)
