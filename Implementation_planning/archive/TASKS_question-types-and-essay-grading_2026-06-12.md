# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:681d97a frontend:0446707 deploy:11d65d0 (2026-06-08)

## G1 [backend]: Schema extended

- [x] T1.1 [backend]: Alembic V27 non-transactional migration — AUTOCOMMIT enum extension + 4 new columns (2026-06-06)
- [x] T1.2 [backend]: SQLAlchemy imperative table mappings updated (essay_subtype, working_required on questions; working_text, shuffle_seed on exam_session_questions) (depends on T1.1) (2026-06-06)
- [x] T1.3 [backend]: Alembic V28 migration (unplanned) — widens essay_subtype VARCHAR(10)→VARCHAR(50), adds CHECK constraint (6 valid values), adds penalty_matching BOOLEAN NOT NULL DEFAULT false; domain/schemas/frontend extended accordingly (2026-06-06)
- [ ] **G1: Schema extended** — integration test: insert rows with all 4 new fields + penalty_matching; assert round-trip via SQLAlchemy

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

## G7 [backend]: Schema extended (Essay AI Grading)

- [x] T7.1 [backend]: Alembic V29 migration — ADD COLUMN rubric/model_answer/auto_grade_essay on questions; essay_grading_mode on exam_templates; 9 AI grading columns on exam_session_questions; CREATE TABLE essay_grading_jobs with indexes + trigger (2026-06-09)
- [x] T7.2 [backend]: SQLAlchemy imperative table mappings — questions, exam_templates, exam_session_questions, new essay_grading_jobs table (depends on T7.1) (2026-06-09)
- [ ] **G7: Schema** — integration test: insert essay question with rubric; exam template with review_first mode; grading job; assert all fields round-trip

## G8 [backend]: Domain layer (Essay AI Grading)

- [x] T8.1 [backend]: EssayGradingJob dataclass + EssayGradingStatus StrEnum + abstract repository (2026-06-09)
- [x] T8.2 [backend]: Question domain model gains rubric, model_answer, auto_grade_essay fields (2026-06-09)
- [x] T8.3 [backend]: ExamSessionQuestion gains 9 AI grading fields; ExamTemplate gains essay_grading_mode (2026-06-09)
- [ ] **G8: Domain** — integration test: load Question with rubric from DB; instantiate + persist EssayGradingJob

## G9 [backend]: EssayGraderProvider + rubric resolver

- [x] T9.1 [backend]: GradingSettings in config.py — GRADING__MODEL_SPEC, OLLAMA_BASE_URL, OLLAMA_API_KEY, MAX_TOKENS, TEMPERATURE (depends on none) (2026-06-09)
- [x] T9.2 [backend]: EssayGraderProvider — prefix-dispatch (mirrors GlmOcrProvider), grade() method, JSON output, score-mapping formula, blank-answer guard, retry (depends on T9.1, T8.2) (2026-06-09)
- [x] T9.3 [backend]: RubricResolver — resolve_rubric(question) returns custom rubric or per-subtype default (depends on T8.2) (2026-06-09)
- [ ] **G9: Provider** — unit tests: mock Ollama endpoint; score formula; retry on malformed output; blank guard; rubric resolver for all 7 subtypes

## G10 [backend]: Worker essay grading loop

- [x] T10.1 [backend]: EssayGradingJobRepository (infra) — get_next_queued() SKIP LOCKED, update_status, mark_done, mark_error (depends on T7.2, T8.1) (2026-06-09)
- [x] T10.2 [backend]: essay_grading_loop.py — poll, process, auto_release vs review_first transitions, retry backoff, error state (depends on T8.3, T9.2, T9.3, T10.1) (2026-06-09)
- [x] T10.3 [backend]: Register loop in worker __main__.py alongside extraction loop (depends on T9.1, T10.2) (2026-06-09)
- [ ] **G10: Worker** — integration test: seed queued job; run loop; assert grading_status='released' + session score updated

## G11 [backend]: Submit enqueue + grading results API

- [x] T11.1 [backend]: submit_exam() enqueues essay_grading_jobs per essay answer (blank guard; skip if auto_grade_essay=false) (depends on T7.2, T8.1, T8.2) (2026-06-09)
- [x] T11.2 [backend]: GET /answers surfaces grading_status, ai_feedback, ai_rationale (owner-only); updated pending_review_count (depends on T8.3) (2026-06-09)
- [x] T11.3 [backend]: POST .../dispute, POST .../confirm-grade, PATCH .../grade endpoints (CSRF, X-Current-Role, auth guards BR-SEC-011/012) (depends on T8.3, T11.2) (2026-06-09)
- [x] T11.4 [backend]: Question + ExamTemplate create/update Pydantic schemas accept rubric, model_answer, auto_grade_essay, essay_grading_mode (depends on T8.2) (2026-06-09)
- [ ] **G11: API** — integration test: full submit→grade→dispute→override flow; assert state machine + session score at each step

## G12 [deploy]: Config & deploy wiring

- [x] T12.1 [deploy]: docker-compose.yml worker block — add GRADING__* env vars alongside EXTRACTION__* (depends on T9.1) (2026-06-09)
- [x] T12.2 [deploy]: .env.example — default qwen3:14b local; commented cloud/premium opt-in lines with PII-egress note (depends on T12.1) (2026-06-09)
- [x] **G12: Deploy** — integration test: fresh stack; worker starts; essay grading loop shows in worker health page (2026-06-09)

## ROOT acceptance test (Essay AI Grading)

- [ ] **ROOT [manual E2E]: Essay AI grading end-to-end** — local qwen3:14b: create essay question (no rubric → default), auto_release exam, student submits, worker grades, GET answers shows released score + feedback; repeat with custom rubric, review_first mode, dispute→override flows, blank answer guard, 3-failure error state

---

## Ready now

### From previous phase (Question Type Extension) — still outstanding:

**G1–G5 integration tests — ready in parallel [backend]:**
- **G1 integration test**: insert rows with all 4 new fields + `penalty_matching`; assert round-trip via SQLAlchemy
- **G2 integration test**: `validate()` for each new type through service layer; load `Question` with `essay_subtype='extended'` from DB; confirm field; confirm `ExamSessionQuestion` with `shuffle_seed=99` persists and reloads
- **G3 integration test**: full `Question` from DB, `grade_question()` end-to-end, assert partial credit (1 of 2 pairs = `points/2.0`); also assert `penalty_matching=True` reduces score on wrong pairs
- **G4 integration test**: create session with `matching` question → assert `shuffle_seed` non-null; submit `problem_solving` with `working_text` → assert persisted in DB
- **G5 integration test**: `GET /session/{id}/questions` via test client → assert JSON includes `shuffle_seed`, `working_required`, `essay_subtype`, `duration_minutes` per question

**ROOT e2e [frontend] — requires G1–G5 passing:**
- Playwright `tests/e2e/question-type-extension.spec.ts`: one_word_response answer flow, matching two-column shuffle + partial credit, problem_solving with working_text, essay with `essaySubtype='short'` guidance, submit → completed + results

### New phase (AI Essay Grading) — remaining tasks:

All G7–G11 leaf tasks are now complete (T7.1–T11.4 done 2026-06-09). G12 (deploy config) is also complete. Remaining:

- **G7–G11 integration tests** — require live DB + worker; not yet written
- **ROOT manual E2E**: qwen3:14b end-to-end essay grading flow
