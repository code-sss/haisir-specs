# Question Types Extension
*Discussion notes — 2026-06-05*

---

## Context

The target exam format (see `target/screenshots/image.png`) includes question types not yet represented in the current `QuestionType` enum or `questions` table schema:

| Type (exam format) | Current backend enum | Gap |
|---|---|---|
| Multiple-choice | `single_choice`, `multiple_choice` | Covered |
| True or False | `true_false` | Covered |
| Fill in the blanks | `fill_in_the_blank` | Covered |
| Written Response (Short / Long) | `essay` | Partial — no short/long distinction |
| **Match the following** | — | Missing |
| **One word response** | — | Missing |
| **Problem-solving / application** | — | Missing |

---

## New Question Types

### 1. `one_word_response`

A fill-in-the-blank variant where the expected answer is a single word (or short phrase — e.g., a name, term, or number). Graded by exact/normalized string match, same as `fill_in_the_blank`.

**Why a separate type instead of reusing `fill_in_the_blank`?**
UI rendering differs: one-word questions display a compact inline input, not a multi-word blank. The distinction also allows exam templates to cap one-word questions independently in `question_types`.

**Schema:** no new columns needed. Reuses `options` (empty), `correct_answers` (list of acceptable single-word answers), `explanation`.

**Grading:** auto-graded — same `_grade_fill_in_blank` normalized-text-match logic as `fill_in_the_blank`. Wire into `grading.py` match as a new case delegating to the existing helper.

---

### 2. `matching`

A "Match the following" question. Students pair items from two columns (left → right).

**Structure:**
- `options` (JSONB) — array of objects, each with an `id`, a `side` (`"left"` | `"right"`), and a `text`. Example:
  ```json
  [
    {"id": "L1", "side": "left",  "text": "Mitochondria"},
    {"id": "L2", "side": "left",  "text": "Nucleus"},
    {"id": "R1", "side": "right", "text": "Powerhouse of the cell"},
    {"id": "R2", "side": "right", "text": "Controls cell activity"}
  ]
  ```
- `correct_answers` (JSONB) — array of `"Lx:Rx"` pair strings. Example: `["L1:R1", "L2:R2"]`.

**Grading:** auto-graded. Formula: `correct_pairs / total_pairs × available_points`. No penalty for wrong pairings.

**Shuffle:** right-column items are shuffled per-session using seeded Fisher-Yates. The backend generates `shuffle_seed` (INT) at session-creation time and stores it on the `exam_session_questions` row. The frontend replicates the same seeded Fisher-Yates algorithm using the stored seed — this is a cross-stack contract; both sides must use the same algorithm.

**UI:** renders two columns with drag-and-drop or dropdown selectors. Right-column items are displayed in shuffled order derived from `shuffle_seed`.

**Implementation note:** The existing `QuestionOption` dataclass (`id`, `text`, `image_url`) does not have a `side` field. The `options_to_obj` static method does `QuestionOption(**opt)` — this will raise `TypeError` for matching questions. `QuestionOption` must be extended to support an optional `side: str | None = None` field, or matching uses a separate option parsing path.

---

### 3. `problem_solving`

A two-part question: a **final answer** (auto-gradable) plus an optional **working area** (free-text, captured but not scored in this phase).

**Structure:**
- `correct_answers` (JSONB, existing) — list of acceptable final answer strings. Auto-graded by normalized match.
- `options` (JSONB, existing) — empty/unused.
- `working_required` (BOOLEAN, new column, DEFAULT `false`) — when `true`, the exam UI renders a free-text working area alongside the answer field.

**`exam_session_questions` extension:**
- `working_text` (TEXT, nullable) — student's submitted working/method. Null for all other types. Captured and stored on submit. **Not scored in this phase** — visible to the parent who owns the exam (via the existing exam results read) for reference, but carries no `earned_points`.

**Grading:** final answer auto-graded by normalized match against `correct_answers`, using the existing `points` column on `exam_template_questions`/`exam_session_questions`. Working is captured but unscored. Instructor scoring of `working_text` is deferred to a future phase when instructor scope is added.

---

## `essay` Sub-type: Short vs. Long Answer

The current `essay` type collapses short answer (4–5 sentences) and long answer (1–2 paragraphs) into one. Exam templates need to control the mix independently.

**Approach:** add an `essay_subtype` column to `questions` (rendering hint only — no validation rule changes).

- `essay_subtype` (VARCHAR(10), nullable, DEFAULT `null`) — `'short'` | `'long'` | `null` (legacy rows).
- All other columns and grading behaviour unchanged.
- Exam templates reference `question_type = 'essay'` as before; `essay_subtype` is an optional additive filter.
- UI uses `essay_subtype` to set expected response length guidance (e.g., "Write 4–5 sentences" vs. "Write 1–2 paragraphs").

---

## Summary of Schema Changes

### `questions` table — new columns

```sql
ALTER TABLE questions
  ADD COLUMN essay_subtype    VARCHAR(10) NULL,
  ADD COLUMN working_required BOOLEAN     NOT NULL DEFAULT false;
```

| Column | Type | Default | Notes |
|---|---|---|---|
| `question_type` | enum | — | Add `one_word_response`, `matching`, `problem_solving` to existing enum |
| `essay_subtype` | VARCHAR(10) | `null` | `'short'` \| `'long'` \| `null`; rendering hint only |
| `working_required` | BOOLEAN | `false` | `problem_solving` only; controls working area UI |

### `exam_session_questions` table — new columns

```sql
ALTER TABLE exam_session_questions
  ADD COLUMN working_text  TEXT NULL,
  ADD COLUMN shuffle_seed  INT  NULL;
```

| Column | Type | Default | Notes |
|---|---|---|---|
| `working_text` | TEXT | `null` | Student working for `problem_solving`; captured, not scored this phase |
| `shuffle_seed` | INT | `null` | `matching` only; seed for seeded Fisher-Yates right-column shuffle; set at session creation |

---

## Grading Matrix (full picture)

| Type | Auto-graded | Partial credit | Manual review |
|---|---|---|---|
| `single_choice` | Yes | No | No |
| `multiple_choice` | Yes | Yes | No |
| `true_false` | Yes | No | No |
| `fill_in_the_blank` | Yes | No | No |
| `one_word_response` | Yes | No | No |
| `matching` | Yes | Yes (per pair: correct/total) | No |
| `essay` | No | — | Yes (instructor / AI) |
| `problem_solving` | Yes (answer only) | No | Deferred (working unscored this phase) |

---

## Implementation Notes for Backend

1. **`grading.py` match exhaustiveness** — the `match` on `QuestionType` has `# pragma: no branch - all QuestionType values handled`. Adding three new enum members will produce `MatchError` at runtime for any new type until explicit cases are added. Add cases for `one_word_response` (delegate to `_grade_fill_in_blank`), `matching` (new `_grade_matching` helper), and `problem_solving` (delegate to `_grade_fill_in_blank` on the answer field; `working_text` is not scored).

2. **`Question.validate()` dispatch** — add explicit validation paths for `matching` (verify all pair IDs in `correct_answers` reference valid option IDs) and `problem_solving` (same as `fill_in_the_blank` validation: options empty, correct_answers non-empty).

3. **`QuestionOption` dataclass** — extend with `side: str | None = None` to support `matching` options without breaking existing question types.

4. **Shuffle seed timing** — `shuffle_seed` must be generated and written to `exam_session_questions` at session-creation time (`POST /api/student/exam-sessions`), not at submission time, so the student sees the same right-column order on page refresh.
