# PLAN — Question Type Extension

> Written: 2026-06-05
> Spec: `target/2026-06-05_question_types_extension.md`
> Schema deltas: `target/requirements/01_data_model.md` § "Question Types Extension"

---

## Problem Statement

The exam format requires three question types not yet in the `QuestionType` enum: `one_word_response`, `matching`, and `problem_solving`. The `essay` type also needs an `essay_subtype` distinction. This plan extends the schema, domain, grading, session creation, API contracts, and student exam UI to support all four new capabilities.

---

## Architecture Decisions

1. **PostgreSQL enum extension**: `ALTER TYPE questiontype ADD VALUE` is non-transactional in PG 12+. Migration V27 must use `op.get_bind().execution_options(isolation_level="AUTOCOMMIT")` before each `ALTER TYPE` call, then switch back for the `ADD COLUMN` statements. Pattern differs from V25 which used bare `op.execute()` — V27 must be explicit.
2. **Deployment order**: V27 migration MUST be applied to the database before deploying application code that references new `QuestionType` values.
3. **No backend shuffle**: The backend generates a random `shuffle_seed` (uint31 int) at session creation time and stores it. The frontend reads that seed and applies an LCG-based Fisher-Yates shuffle to right-column matching options. The backend never shuffles.
4. **LCG cross-stack contract**: Both sides use `next_state = (current_state * 1664525 + 1013904223) >>> 0` (uint32 via unsigned right shift). Fisher-Yates: iterate `i` from `len−1` down to `1`, swap `arr[i]` with `arr[lcgNext() % (i+1)]`. Python uses `>>> 0` semantics via `& 0xFFFFFFFF`; TypeScript uses `>>> 0`.
5. **working_text at submit time**: There is no per-question answer endpoint; `working_text` is submitted alongside all answers at `POST /session/{id}/submit`. `AnswerCreate` schema gains an optional `working_text` field; only `problem_solving` question answers store it.
6. **Canonical matching format**: `correct_answers` for `matching` questions is a list of `"Lx:Ry"` strings where `Lx`/`Ry` are option IDs with `side="left"`/`side="right"` respectively. User answers serialize as JSON: `[{"left_id": "L1", "right_id": "R1"}, ...]`.
7. **essay_subtype is a rendering hint only**: No validation rule changes; `essay_subtype` controls UI guidance text. Existing essay questions are unaffected (`essay_subtype = null`).

---

## Goal Tree

### G1 — Schema Extended
**Goal**: The PostgreSQL database gains three new enum values and four new nullable/defaulted columns so no existing data is broken and all new fields can be written by the application.
**Goal test**: Run `alembic upgrade V27` against test DB; verify new columns (`essay_subtype`, `working_required` on `questions`; `working_text`, `shuffle_seed` on `exam_session_questions`) + 8 enum values; existing rows read without error.
**Repos**: [backend]

---

##### T1.1 [backend] — Alembic V27 non-transactional migration
- **Build**: Create `alembic/versions/V27_add_new_question_types.py` with `revision="V27"`, `down_revision="V26"`. In `upgrade()`:
  1. Obtain `conn = op.get_bind()`.
  2. Call `conn.execution_options(isolation_level="AUTOCOMMIT")` then execute three statements: `ALTER TYPE questiontype ADD VALUE IF NOT EXISTS 'matching'`, `ALTER TYPE questiontype ADD VALUE IF NOT EXISTS 'one_word_response'`, `ALTER TYPE questiontype ADD VALUE IF NOT EXISTS 'problem_solving'`. After all three, call `conn.execution_options(isolation_level="READ COMMITTED")` to restore normal isolation.
  3. Inside a normal `op.batch_alter_table` or direct `op.add_column` block, add four columns: `essay_subtype VARCHAR(10) NULL` and `working_required BOOLEAN NOT NULL DEFAULT false` on `questions`; `working_text TEXT NULL` and `shuffle_seed INTEGER NULL` on `exam_session_questions`.
  In `downgrade()`: drop the four columns with `op.drop_column`. Document in a comment that enum value removal is not supported without manual steps.
- **Done when**: `alembic upgrade V27` completes without error; `alembic downgrade V26` drops all four columns without error; `SELECT enum_range(NULL::questiontype)` returns 8 values; rows inserted before migration read without error.
- **Test**: `pytest tests/unit/migrations/test_v27.py` — imports the migration module and verifies `upgrade`/`downgrade` functions are callable; integration test (if DB available) runs upgrade/downgrade round-trip.
- **Depends on**: None

##### T1.2 [backend] — SQLAlchemy imperative table mappings updated
- **Build**:
  - In `src/infrastructure/models/question.py`, add inside the `questions` Table definition: `Column("essay_subtype", String(10), nullable=True)` and `Column("working_required", Boolean, nullable=False, server_default="false")`.
  - In `src/infrastructure/models/exam_session.py`, add inside the **`exam_session_questions`** Table definition (NOT `exam_sessions`): `Column("working_text", Text, nullable=True)` and `Column("shuffle_seed", Integer, nullable=True)`. Import `Text` and `Integer` from sqlalchemy if not already present.
  - The SQLAlchemy imperative mapper (`mapper_registry.map_imperatively(ExamSessionQuestion, exam_session_questions)`) automatically maps columns to dataclass fields by name — no additional mapper config needed once T2.3 adds the fields to the dataclass.
- **Done when**: `alembic check` shows no autogenerate diff (requires T1.1 migration to have run); `from src.infrastructure.models.exam_session import exam_session_questions; assert "shuffle_seed" in [c.name for c in exam_session_questions.columns]`.
- **Test**: Import both table objects; assert new column names exist and have correct types.
- **Depends on**: T1.1

**G1 integration test**: Against the test DB, insert a `questions` row with `essay_subtype='short'` and `working_required=True`, and an `exam_session_questions` row with `shuffle_seed=42` and `working_text="my work"`. Read back via SQLAlchemy and assert all four values round-trip correctly.

---

### G2 — Domain Layer Supports New Types
**Goal**: The Python domain model recognises all eight question types, validates each type's constraints, and carries the two new `ExamSessionQuestion` fields.
**Goal test**: Call `Question.validate()` for each new type with valid and invalid data; load a `Question` with `essay_subtype='extended'` from the DB and confirm the field is accessible; instantiate `ExamSessionQuestion` with `working_text` and `shuffle_seed` and assert the fields are present.
**Repos**: [backend]

---

##### T2.1 [backend] — QuestionType enum + QuestionOption.side field
- **Build**: In `src/domain/models/question.py`:
  - Add three values to `QuestionType(StrEnum)`: `matching = "matching"`, `one_word_response = "one_word_response"`, `problem_solving = "problem_solving"`.
  - Add `side: str | None = None` as a new optional field on the `QuestionOption` dataclass (after `image_url`).
  - Update `options_to_obj`: when constructing `QuestionOption(**opt)`, the `side` key in the dict will map automatically since the field now exists with a default.
  - Update `obj_to_options`: include `side=option.side` in the output dict (so `side` is persisted to JSONB).
  - Note: must be deployed in the same release as V27 migration (T1.1).
- **Done when**: `QuestionType("matching")` doesn't raise; `QuestionOption(id="L1", side="left").side == "left"`; `options_to_obj([{"id": "L1", "text": "foo", "side": "left"}])` returns `QuestionOption` with `side="left"`; `obj_to_options` on a matching option includes `side` in the output dict.
- **Test**: In `tests/unit/domain/test_models/test_question.py`, assert each new enum value and `QuestionOption` side field round-trip through `options_to_obj`/`obj_to_options`.
- **Depends on**: None (but must deploy after T1.1)

##### T2.2 [backend] — Question.validate() for new types + canonical matching format
- **Build**: In `src/domain/models/question.py`:
  - Add `essay_subtype: str | None = None` and `working_required: bool = False` fields to the `Question` dataclass.
  - Extend `validate()`: remove the `# pragma: no branch` annotation on the existing `elif` branch. Add explicit branches for:
    - `QuestionType.one_word_response`: delegate to `_validate_text_question()`.
    - `QuestionType.problem_solving`: delegate to `_validate_text_question()` (options must be empty, `correct_answers` must be non-empty).
    - `QuestionType.matching`: call new private `_validate_matching_question()` (see below).
  - Add a final `else: raise ValueError(f"Unhandled question type: {self.question_type}")` as a safety net.
  - Add private method `_validate_matching_question()`: verify (a) `options` has at least 2 items with `side="left"` and 2 with `side="right"`; (b) each item in `correct_answers` matches the `"Lx:Ry"` pattern (colon-separated left and right IDs); (c) each referenced left ID exists in options with `side="left"` and each right ID exists with `side="right"`.
  - **Canonical matching `correct_answers` format**: a list of strings `"<left_id>:<right_id>"` (e.g., `["L1:R2", "L2:R1"]`). This format is the contract between authoring, validation, grading (T3.2), and the frontend.
- **Done when**: `matching` with valid pairs passes; matching with bad pair ID raises `ValueError`; `one_word_response` with empty options passes; `problem_solving` with options raises; `validate()` raises on unknown type; `# pragma: no branch` is removed.
- **Test**: Add `TestNewQuestionTypes` class in `tests/unit/domain/test_models/test_question.py` with test cases for each new type: valid path, invalid options, invalid `correct_answers` format for matching.
- **Depends on**: T2.1

##### T2.3 [backend] — ExamSessionQuestion domain model new fields
- **Build**: In `src/domain/models/exam_session.py`, add two fields to the `ExamSessionQuestion` dataclass with defaults at the end: `working_text: str | None = None` and `shuffle_seed: int | None = None`. Existing callers that construct `ExamSessionQuestion` without these args continue to work.
- **Done when**: `ExamSessionQuestion(..., working_text="show work", shuffle_seed=12345)` instantiates without error; `ExamSessionQuestion(...)` without new args also works; `.working_text` and `.shuffle_seed` default to `None`.
- **Test**: In `tests/unit/domain/test_models/test_exam_session.py`, assert instantiation with and without the new fields.
- **Depends on**: None

**G2 integration test**: Call `Question.validate()` for each new type through the service layer against a real DB; load a `Question` with `essay_subtype='extended'` seeded in DB; confirm field value; confirm `ExamSessionQuestion` with `shuffle_seed=99` persists and reloads via SQLAlchemy session.

---

### G3 — Grading Handles New Types
**Goal**: `grade_question()` returns the correct `(is_correct, earned_points)` tuple for all three new auto-graded types, and exam results display correctly for `matching` answers.
**Goal test**: Call `grade_question()` for `one_word_response`, `problem_solving`, and `matching` with correct, partially-correct, and incorrect inputs; verify returned tuples match the partial credit formula.
**Repos**: [backend]

---

##### T3.1 [backend] — Grading cases for one_word_response and problem_solving
- **Build**: In `src/shared/grading.py`, extend the `match` statement in `grade_question()`:
  - Remove `# pragma: no branch` from the `essay` case.
  - Add `case QuestionType.one_word_response | QuestionType.problem_solving:` before the essay case, both delegating to `_grade_fill_in_blank(user_question, question)`.
  - Add `case _: raise ValueError(f"Unhandled question type: {question.question_type}")` as the final branch.
  - `working_text` on `problem_solving` is not scored in this phase — the grade function only grades `user_answer`.
- **Done when**: `grade_question(uq, q)` where `q.question_type == QuestionType.one_word_response` and `uq.user_answer == "photosynthesis"` returns `(True, points)` when `correct_answers == ["Photosynthesis"]` (normalized case-insensitive via `_grade_fill_in_blank`); `problem_solving` with correct answer returns full points; `essay` still returns `(None, 0.0)`; unknown type raises `ValueError`.
- **Test**: Add `TestGradeOneWordResponse` and `TestGradeProblemSolving` classes to `tests/unit/shared/test_grading.py`, mirroring the structure of `TestGradeFillInBlank`.
- **Depends on**: T2.1

##### T3.2 [backend] — `_grade_matching` helper
- **Build**: In `src/shared/grading.py`, add private function `_grade_matching(user_question: ExamSessionQuestion, question: Question) -> tuple[bool, float]`:
  - Parse `question.correct_answers` as a set of `"Lx:Ry"` strings (per T2.2 canonical format).
  - Parse `user_question.user_answer` using `json.loads()`; expected shape `[{"left_id": "L1", "right_id": "R1"}, ...]`; convert to set of `"L1:R1"` strings; on any JSON parse error or `None`, return `(False, 0.0)`.
  - `total_pairs = len(correct_set)`; if `total_pairs == 0`, return `(True, 0.0)`.
  - `correct_pairs = len(submitted_set & correct_set)`.
  - `earned = correct_pairs / total_pairs * user_question.points`.
  - `is_correct = (correct_pairs == total_pairs)`.
  - Add `case QuestionType.matching: return _grade_matching(user_question, question)` in the match statement (before the `case _` safety net).
- **Done when**: Full match returns `(True, points)`; one of two pairs correct returns `(False, points/2.0)`; empty/null answer returns `(False, 0.0)`; malformed JSON returns `(False, 0.0)`; zero total pairs returns `(True, 0.0)`.
- **Test**: Add `TestGradeMatching` class in `tests/unit/shared/test_grading.py` covering all five cases.
- **Depends on**: T2.1, T2.2, T2.3

##### T3.3 [backend] — `_resolve_answer_options` updated for matching display
- **Build**: In `src/api/routes/exam_session.py`, extend `_resolve_answer_options` with a `matching` branch: if `question.question_type == QuestionType.matching`, deserialize `user_answer` as JSON pairs and produce display strings in the format `"<left_text> → <right_text>"` (look up text from `question.options` by ID; fall back to ID if text not found). Also add explicit guards to the existing `fill_in_the_blank / essay` text-wrapping block: `if question.question_type in (QuestionType.fill_in_the_blank, QuestionType.essay, QuestionType.one_word_response, QuestionType.problem_solving):` — so new text-style types render as text, not as broken option lookups.
- **Done when**: `get_exam_answers` for a completed `matching` session returns human-readable pair display (e.g., "Mitochondria → Powerhouse of the cell"); `one_word_response` and `problem_solving` answers display as text; existing choice and FITB types are unaffected.
- **Test**: Unit test for `_resolve_answer_options` with a `matching` question type: supply known options and pairs, assert display strings.
- **Depends on**: T2.1, T3.2

**G3 integration test**: Full `Question` domain object of type `matching` loaded from the test DB; call `grade_question()` end-to-end with a partially-correct user answer; assert partial credit score is `points/2.0` when one of two pairs is correct.

---

### G4 — Session Creation Seeds Matching Shuffle
**Goal**: When a `matching` question is added to a session, a `shuffle_seed` is generated and stored; `working_text` is captured for `problem_solving` answers at submit time.
**Goal test**: Call `POST /session/create` with a template containing a `matching` question; assert the resulting `exam_session_questions` row has a non-null integer `shuffle_seed`; submit a `problem_solving` answer with `working_text`; assert the value persists in the DB.
**Repos**: [backend]

---

##### T4.1 [backend] — shuffle_seed generation in POST /session/create
- **Build**: In `src/api/routes/exam_session.py` in `create_exam_session`:
  1. Add `question_service: Annotated[QuestionService, Depends(get_question_service)]` to the function signature (`get_question_service` already exists in the file).
  2. In the `for template_question in template_questions:` loop, fetch `question = await question_service.get_by_id(template_question.question_id)`.
  3. If `question.question_type == QuestionType.matching`, generate `shuffle_seed = random.randint(0, 2**31 - 1)` (uint31 range); else `shuffle_seed = None`. Import `random` at the top of the file.
  4. Extend `ExamSessionQuestionService.create()` (in `src/domain/services/exam_session_service.py`) to accept `shuffle_seed: int | None = None` and pass it when constructing `ExamSessionQuestion(...)`. Default to `None` to avoid breaking existing callers.
  5. Pass `shuffle_seed=shuffle_seed` to `session_question_service.create(...)` in the route loop.
  - **Contract note**: The seed is a random uint31 integer stored as-is. The frontend uses it as the initial LCG state to deterministically shuffle right-column options (see T6.1). The backend does NOT shuffle.
- **Done when**: After session creation with a `matching` question, `exam_session_questions.shuffle_seed` is a non-null integer; for non-matching questions, `shuffle_seed` is `None`; `ExamSessionQuestionService.create()` accepts the new parameter without breaking existing callers.
- **Test**: Mock `QuestionService.get_by_id` returning a `matching` question; assert `ExamSessionQuestionService.create` was called with a non-None `shuffle_seed`; mock returning a `single_choice` question; assert `shuffle_seed=None`.
- **Depends on**: T1.2, T2.1, T2.3

##### T4.2 [backend] — working_text capture in POST /session/{id}/submit
- **Build**: In `src/schemas/answer.py`, add `working_text: str | None = None` to `AnswerCreate`. In `src/api/routes/exam_session.py` in `submit_exam`:
  1. Build a `question_map = {q.id: q for q in questions}` from the already-loaded questions list (confirm `question_service` is already injected into `submit_exam`; if not, add it).
  2. In the answer loop, after setting `uq.user_answer = answer.user_answer`, check: `if question_map[answer.question_id].question_type == QuestionType.problem_solving and answer.working_text is not None: uq.working_text = answer.working_text`.
  3. For all other types, `working_text` on the payload is silently ignored.
- **Done when**: Submitting a `problem_solving` answer with `working_text="my derivation"` stores the value in `exam_session_questions.working_text`; submitting a `single_choice` answer with `working_text` present leaves `working_text=None` in the DB.
- **Test**: Mock `QuestionService`; mock `ExamSessionQuestionService.update`; assert `uq.working_text` is set for `problem_solving` and is `None` for `single_choice`.
- **Depends on**: T2.1, T2.3

**G4 integration test**: Against the test DB, create a session with a template containing a `matching` question and a `problem_solving` question; assert `shuffle_seed` is non-null for the matching row; submit all answers including `working_text` for the problem-solving question; assert `working_text` is persisted.

---

### G5 — API Contracts Expose New Fields
**Goal**: Pydantic response schemas expose all new domain fields so the frontend receives them in JSON; the student exam questions endpoint delivers `shuffle_seed`, `working_required`, and `essay_subtype` per question.
**Goal test**: Call `GET /session/{id}/questions` via FastAPI test client after creating a session with one question of each new type; assert JSON includes `shuffle_seed` (non-null int) for matching, `working_required: true` for a problem_solving question with `working_required` set, and `essay_subtype: "short"` for a short essay question.
**Repos**: [backend]

---

##### T5.1a [backend] — Question Pydantic schemas updated
- **Build**: In `src/schemas/question.py`:
  - Add `essay_subtype: str | None = None` and `working_required: bool = False` to `QuestionBase`.
  - Add `side: str | None = None` to `QuestionOptionBase`.
  - Update `QuestionOptionBase.from_question_option()` to include `side=option.side` in the constructor.
  - Update `QuestionOptionBase.to_question_option()` to include `side=option.side`.
  - Update `QuestionBase.from_domain()` to map `essay_subtype=question.essay_subtype` and `working_required=question.working_required` from the `Question` domain object.
- **Done when**: `QuestionBase.from_domain(question)` serializes with `essay_subtype` and `working_required`; `QuestionOptionBase` round-trips `side`; TypeScript receives matching options with `side` field in JSON.
- **Test**: Schema serialization tests for new fields in `tests/unit/schemas/test_question.py`.
- **Depends on**: T2.1, T2.2

##### T5.1b [backend] — Session-question display schema + route wiring for shuffle_seed
- **Build**:
  - In `src/schemas/exam_session.py`, add `shuffle_seed: int | None = None`, `working_required: bool = False`, and `essay_subtype: str | None = None` to `ExamSessionQuestionDisplay`. Add `shuffle_seed: int | None = None` and `working_text: str | None = None` to `ExamSessionQuestionRead`.
  - In `get_questions_for_exam_session` route in `exam_session.py`, before `_build_display`, build `shuffle_seed_map = {uq.question_id: uq.shuffle_seed for uq in user_questions}`. Update `_build_display(q: Question)` closure to also accept/close over `shuffle_seed_map` and pass `shuffle_seed=shuffle_seed_map.get(q.id)`, `working_required=q.working_required`, `essay_subtype=q.essay_subtype` when constructing `ExamSessionQuestionDisplay`.
- **Done when**: `GET /session/{id}/questions` response includes `shuffle_seed` (non-null for matching rows, null for others), `working_required`, and `essay_subtype` per question.
- **Test**: In `tests/unit/schemas/test_exam_session.py`, assert `ExamSessionQuestionDisplay(shuffle_seed=42, ...).model_dump()` includes `"shuffle_seed": 42`; mock route test asserts JSON shape.
- **Depends on**: T2.1, T2.2, T2.3, T4.1, T5.1a

**G5 integration test**: Call `GET /session/{id}/questions` via FastAPI test client with a session containing one matching, one problem_solving, and one short essay question; assert the JSON for each includes the correct new field values.

---

### G6 — Student Exam UI Renders New Types
**Goal**: Students see appropriate input controls for all three new question types and the essay subtype hint; their answers serialize correctly to the submission payload.
**Goal test**: Render `QuestionRenderer` for each of the 8 question types with realistic mock props; assert the correct input component is mounted and `answersToPayload` produces the expected `text_answer` / `selected_options` / `working_text` shape for each.
**Repos**: [frontend]

---

##### T6.0 [frontend] — Extend frontend type system for new question types
- **Build**: In `src/features/exam/types/exam.types.ts`:
  - Add `'one_word_response' | 'matching' | 'problem_solving'` to the `QuestionType` union.
  - Add `shuffle_seed?: number | null`, `working_required?: boolean`, `essay_subtype?: EssaySubtype | null` to `ExamQuestionType` interface, where `EssaySubtype = 'short' | 'extended' | 'critical' | 'narrative' | 'analytical' | 'reflective'` (backend-defined enum; original plan said `'short' | 'long'` but backend uses the six-value form).
  - Add new discriminated union variants to `QuestionAnswer`: `| { type: 'one_word_response'; text: string } | { type: 'matching'; pairs: { left_id: string; right_id: string }[] } | { type: 'problem_solving'; text: string; working_text?: string }`.
  - Add `working_text?: string | null` to `AnswerPayload` (optional; only populated for `problem_solving`).
- **Done when**: TypeScript compiles with zero errors; `const t: QuestionType = 'matching'` compiles; `ExamQuestionType` accepts `shuffle_seed: 42`.
- **Test**: Type-only compilation test — TypeScript strict mode with no errors is the test assertion.
- **Depends on**: None

##### T6.0b [frontend] — Update question-type-utils.ts and answer-transformer.ts for new types
- **Build**:
  - In `src/features/exam/domain/question-type-utils.ts`: add entries for all three new types in every `Record<QuestionType, ...>` map (`getTypeInstruction`, `getTypeShortLabel`, `isAutoGradable` — `matching` and `one_word_response` return true, `problem_solving` returns false; `requiresOptions` — `matching` returns true; `isTextInput` — `one_word_response` and `problem_solving` return true).
  - In `src/features/exam/domain/answer-transformer.ts`: extend `answersToPayload`, `answerToDisplayString`, `defaultAnswer`, and `isAnswered` for all three new types:
    - `one_word_response`: `text_answer: answer.text`, same as fill_in_the_blank.
    - `matching`: `text_answer: JSON.stringify(answer.pairs)`, `selected_options: []`.
    - `problem_solving`: `text_answer: answer.text`, `working_text: answer.working_text ?? null`.
  - `defaultAnswer('matching')` returns `{ type: 'matching', pairs: [] }`.
- **Done when**: No TypeScript exhaustiveness errors; `answersToPayload` produces correct shapes for all 8 types; `defaultAnswer('matching')` returns the correct shape.
- **Test**: Unit tests for each new type in `tests/unit/features/exam/domain/answer-transformer.test.ts` and `question-type-utils.test.ts`.
- **Depends on**: T6.0

##### T6.1 [frontend] — Seeded Fisher-Yates utility (LCG)
- **Build**: Create `src/features/exam/domain/seeded-shuffle.ts`. Export `seededShuffle<T>(arr: T[], seed: number): T[]`:
  - Makes a copy of `arr`.
  - LCG: `let state = seed >>> 0; const next = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state; }`.
  - Fisher-Yates: `for (let i = copy.length - 1; i > 0; i--) { const j = next() % (i + 1); [copy[i], copy[j]] = [copy[j], copy[i]]; }`.
  - Returns the shuffled copy (original not mutated).
  - **Backend contract**: seed is a uint31 integer from `ExamSessionQuestion.shuffle_seed` generated by Python's `random.randint(0, 2**31-1)`. Python shuffle equivalent: `state = seed & 0xFFFFFFFF; next() = (state * 1664525 + 1013904223) & 0xFFFFFFFF`.
- **Done when**: `seededShuffle([1,2,3,4], 12345)` produces a known deterministic output (recorded as snapshot); same seed + same list always produces same result; empty array returns `[]`; single element returns `[element]`; original array not mutated.
- **Test**: Snapshot test for `seed=12345` with `['R1','R2','R3','R4']`; immutability test; empty and single-element edge cases.
- **Depends on**: None

##### T6.2 [frontend] — one_word_response question component
- **Build**: Create `src/features/exam/components/exam-form/one-word-response-input.tsx`. Render a `<div>` with a `<label>` and `<input type="text" />` (single line, compact — narrower than a textarea). In `question-renderer.tsx`'s `renderInput` switch, add `case 'one_word_response':` passing `answer.text` and calling `onChange({ type: 'one_word_response', text: v })`.
- **Done when**: Renders `<input type="text">`; `onChange` fires with `{ type: 'one_word_response', text: '...' }`; answer transformer produces `text_answer`.
- **Test**: `one-word-response-input.test.tsx` — renders input; onChange fires; `answersToPayload` test for this type.
- **Depends on**: T6.0, T6.0b

##### T6.3 [frontend] — matching question component (two-column dropdown + seeded shuffle)
- **Build**: Create `src/features/exam/components/exam-form/matching-input.tsx`. Props: `question: ExamQuestionType`, `value: { left_id: string; right_id: string }[]`, `onChange: (pairs: { left_id: string; right_id: string }[]) => void`. Logic:
  - `leftItems = question.options.filter(o => o.side === 'left')` in original order.
  - `rightItems = seededShuffle(question.options.filter(o => o.side === 'right'), question.shuffle_seed ?? 0)`.
  - Render a two-column layout: left column lists each left item's text; right column renders a `<select>` per left item whose options are the shuffled right items plus a blank "— select —" option.
  - On dropdown change, update the pairs array and call `onChange`.
  - In `question-renderer.tsx`, add `case 'matching':` passing `question` (which has `shuffle_seed` per T6.0) and current `pairs` from `answer.pairs`.
- **Done when**: Right items render in seed-deterministic order for a given seed (matches `seededShuffle` snapshot); selecting a dropdown fires `onChange` with correct pairs; answer transformer produces `text_answer: JSON.stringify(pairs)`.
- **Test**: `matching-input.test.tsx` — right items order matches known `seededShuffle` output for seed=42; onChange fires with updated pairs; answer transformer serializes correctly.
- **Depends on**: T6.0, T6.0b, T6.1

##### T6.4 [frontend] — problem_solving question component
- **Build**: Create `src/features/exam/components/exam-form/problem-solving-input.tsx`. Props: `value: string`, `onChange: (v: string) => void`, `workingText: string`, `onWorkingTextChange: (wt: string) => void`, `workingRequired: boolean`. Render: (a) always render a standard `<input type="text" />` for the answer; (b) if `workingRequired === true`, render a `<textarea>` labelled "Show your working". In `question-renderer.tsx`, add `case 'problem_solving':` reading `question.working_required` (from T6.0 on `ExamQuestionType`). In `exam-api.ts`'s `submitAnswers`, include `working_text: answer.working_text ?? null` in the payload item only for `problem_solving` answers (omit for other types to keep payload clean).
- **Done when**: `workingRequired=true` renders textarea; `workingRequired=false` does not render textarea; submitted payload includes `working_text` for problem-solving; other types do not include `working_text`.
- **Test**: `problem-solving-input.test.tsx` — `workingRequired=true` shows textarea; `false` does not; payload shape test for both.
- **Depends on**: T6.0, T6.0b

##### T6.5 [frontend] — essay_subtype rendering hint
- **Build**: In `src/features/exam/components/exam-form/essay-input.tsx`, add optional prop `essaySubtype?: EssaySubtype | null`. Render a guidance `<p>` for each subtype value using a lookup map (`ESSAY_GUIDANCE: Record<EssaySubtype, string>`): `short` → "Aim for 4–5 sentences.", `extended` → "Aim for 2–3 paragraphs.", `critical` → "Analyse the topic and support your view with evidence.", `narrative` → "Write a story with a clear beginning, middle, and end.", `analytical` → "Break down the topic and examine each part in detail.", `reflective` → "Describe your experience and what you learned from it." When `null`/`undefined`: render nothing. In `question-renderer.tsx`, update the essay case to pass `essaySubtype={question.essay_subtype}` to `<EssayInput>`.
- **Done when**: Each of the 6 subtypes renders the correct guidance text; `null`/`undefined` shows nothing; existing essay tests pass.
- **Test**: Test all 6 subtype values plus null/undefined in `essay-input.test.tsx`.
- **Depends on**: T6.0
- **Implementation note**: Original plan specified `'short' | 'long'`; backend uses the full 6-value enum. The `'long'` value is not valid — use `'extended'` instead.

**G6 integration test**: Render `QuestionRenderer` via React Testing Library for each of the 8 question types with appropriate mock props; assert correct child component is mounted (`getByRole('textbox')` for one_word_response, two `<select>` elements for a 2-pair matching question, `<textarea>` for problem_solving with `workingRequired=true`, guidance text for short essay); call `answersToPayload` on a mock answer for each type and assert shape.

---

## ROOT Acceptance Test

Playwright `tests/e2e/question-type-extension.spec.ts`:
1. Student logs in, navigates to an exam session containing one question of each new type (mocked via MSW or seeded DB).
2. `one_word_response` — student types a single word; answer appears in review.
3. `matching` — student sees two columns; right column is in shuffled order derived from `shuffle_seed`; student selects all pairings; answer appears in review.
4. `problem_solving` (with `workingRequired=true`) — student types final answer + working; both fields appear in submit payload.
5. `essay` (with `essaySubtype='short'`) — "Aim for 4–5 sentences" guidance appears below textarea.
6. Student submits; session status becomes `completed`; results show partial credit for matching (1 of 2 pairs correct).

---

## Implementation Notes

**Backend pattern references (existing code to follow):**
- Grading: `src/shared/grading.py` — existing `_grade_fill_in_blank` helper is the pattern for new grading cases
- Domain model: `src/domain/models/question.py` — `QuestionOption` dataclass + `options_to_obj`/`obj_to_options` static methods
- Exam session route: `src/api/routes/exam_session.py` — `create_exam_session`, `submit_exam`, `get_questions_for_exam_session`
- SQLAlchemy imperative mapping: `src/infrastructure/models/question.py` and `exam_session.py`

**Frontend pattern references (existing code to follow):**
- Question renderer: `src/features/exam/components/exam-form/question-renderer.tsx` — add new `case` branches
- Answer transformer: `src/features/exam/domain/answer-transformer.ts` — extend all switch/map functions
- Type utils: `src/features/exam/domain/question-type-utils.ts` — extend all `Record<QuestionType, ...>` maps
- Existing component: `fill-in-blank-input.tsx` — pattern for `one_word_response`

**Open Points (deferred, requires separate spec):**
1. P-exam question creator UI for `matching`, `one_word_response`, `problem_solving` — not specced yet (`target/requirements/ui-mapping/ui_parent_institution_admin.md`)
2. S-results rendering for `matching` — per-pair breakdown display format
3. S-results rendering for `problem_solving` — whether `working_text` is shown in student results view
4. Instructor scoring of `problem_solving.working_text` — deferred to when instructor scope is added

## Implementation Deviations (recorded 2026-06-08)

- **T4.1 — shuffle_seed generation**: Plan specified `random.randint(0, 2**31-1)`; implementation uses `secrets.randbelow(2**31)` — security improvement, no contract change.
- **T4.2 — working_text capture**: Plan said captured at submit (`POST /submit`); implementation captures it at answer-recording time (`POST /answer` — `AnswerCreate.working_text`) then persists on `ExamSessionQuestion` when non-null. Semantically equivalent.
- **V28 migration (unplanned)**: After V27 shipped, a V28 migration was added: widens `essay_subtype` from `VARCHAR(10)` → `VARCHAR(50)` (needed for 6-value enum values), adds CHECK constraint on valid subtype values (`analytical|critical|extended|narrative|reflective|short`), and adds `questions.penalty_matching BOOLEAN NOT NULL DEFAULT false` (enables score-reduction mode for matching: `max(0, (correct − wrong) / total) × points`). Grading, domain model, Pydantic schemas, and frontend types were extended accordingly. All V28 work is complete.
- **duration_minutes in GET /questions response**: Not in original plan scope; the session-question display endpoint now also returns `duration_minutes: int | null` from the template. Done as part of T5.1b.

<!-- plan-baseline: backend:681d97aa488fac2aaf8ab9b8215dbbcc9a4c7596 frontend:044670747b0641b03b490bc62bda41fcca8a0225 deploy:0dfc6c026336fb873137d2f1dd40f5f3b20ea59e -->
