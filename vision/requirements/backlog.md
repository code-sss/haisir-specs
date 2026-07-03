# hAIsir — Product Backlog

> Unscoped items that need spec work before implementation. Add new items here with a date, status, and enough context to pick up later. Do not implement without first moving to a requirements spec.

---

## Format

```
### BL-NNN — Short Title
**Raised:** YYYY-MM-DD
**Status:** Unscoped | Speccing | Ready | Deferred
**Related specs:** list of relevant requirement files

Context and open questions.
```

---

## Items

### BL-001 — Post-Onboarding Secondary Role Addition (Student ↔ Parent)
**Raised:** 2026-03-26
**Status:** Unscoped
**Related specs:** `09_onboarding.md` (BR-ON-006a), `11_role_migration.md` §6.1 + §8, `02_auth_and_roles.md` §4

**Context:**
ON02 is single-select — users pick Student OR Parent during onboarding. BR-ON-006a already states that a user can add the other role later from their profile/settings page via `POST /api/users/me/assign-role`, triggering an inline setup flow. However, no screens or UI spec exist for this path.

**What needs to be spec'd:**
- The profile/settings page entry point — where does the user discover "Add role"? (user menu? settings page? dedicated section?)
- Inline setup flow for adding `parent` role to an existing student account:
  - What does the user see? (a condensed ON05-equivalent step, or just a confirmation?)
  - Token refresh handling after assignment (same iframe mechanism as onboarding)
  - Redirect after completion — back to profile or to parent dashboard?
- Inline setup flow for adding `student` role to an existing parent account:
  - Same questions as above
- Edge case: user already holds the target role (e.g. somehow has `student` already) — graceful no-op or informational message
- Screen IDs for any new inline screens (follow `ON__` naming or introduce `PROF__` namespace?)

**Open questions:**
- Should this be a modal/sheet inline on the current page, or a full-page flow?
- Does adding `parent` role prompt the user to immediately link a child, or is that deferred to the parent dashboard?
- Is there a settings page spec planned at all? If not, this item may need a broader "Account settings" screen to be spec'd first.

---

### BL-002 — Teacher At-Risk / Student Detail View
**Raised:** 2026-07-02
**Status:** Deferred (Phase 6 — with role migration / teacher tooling)
**Related specs:** `04_teacher_tutor.md` (At-Risk Student Detection), `10_notifications.md` (BR-NOTIF-010 `student_at_risk`), `03_student.md` (mastery / focus areas)

**Context:**
The `student_at_risk` notification (Phase 4 G4.2 — fires when a student has ≥ 3 weak topics) is a
shared-queue notification for the `instructor` role. Its `action_url` should deep-link the teacher
to a per-student view of the at-risk student's weak topics and recent exam results. **No such
view exists today** — the only teacher route is `/teacher/doubts` (the doubt queue), which is the
wrong destination. Pre-Phase-5 (G8) sets `action_url = NULL` as the interim so the notification
does not navigate teachers to the wrong page; the feed click marks the notification read with no
navigation.

**What needs to be spec'd (Phase 6 pickup):**
- A `/teacher/students/{student_sub}` page (screen ID TBD — `T08` or a `T-student` namespace)
  showing: the at-risk student's display name, their `weak_topics` list (the `weak_topics` shape
  already exists on `GET /api/student/dashboard` for the student-self path — reuse the aggregate
  for an instructor-facing read), recent exam results (per-topic mastery scores, last attempt per
  topic), and a "View doubts for this student" affordance into the existing `/teacher/doubts`
  filtered by the student.
- An instructor-facing endpoint to fetch a single at-risk student's weak-topics + recent results
  (no instructor endpoint exists today; the student dashboard service is student-self only).
- Wiring: `student_at_risk` notification `action_url` → `/teacher/students/{student_sub}` (carrying
  the at-risk student's sub in the notification payload — currently the body is generic; enrich
  with the student's display name when the lookup is available in the `MasteryService` call path).
- Permission: `require_instructor()` + scope rules (shared-queue model — any instructor can view any
  at-risk student in v1; class/section scoping comes with the orgs model).

**Open questions:**
- Does the instructor need a roster/list view of all at-risk students, or only the per-student
  detail view reached via the notification? (A `/teacher/students` roster is a natural companion.)
- Should the at-risk view surface a "message student" affordance, or route through the existing
  doubt thread? (The latter avoids building a separate messaging surface.)

---

### BL-003 — LaTeX / Math Rendering Pipeline
**Raised:** 2026-07-02
**Status:** Ready (approach agreed — ships as a focused content-rendering follow-up)
**Related specs:** `12_content_extraction.md` (§11 Content Rendering — added 2026-07-02), `03_student.md` (S-nav content viewer, S-exam question rendering, S05 review), `07_platform_admin.md` (exam builder — authored `question_text`)

**Context:**
Educational content carries LaTeX math (inline `$\frac{a}{b}$`, block `$$...$$`, `\sqrt{...}`,
etc.). The through-Phase-4 frontend has **no math-rendering library** installed (no `katex`,
`remark-math`, `rehype-katex`, or `mathjax` in `package.json`). Every text surface interpolates
strings as plain React text children, so LaTeX renders as raw literal characters (visible `$` and
backslashes) in: topic `text` content (`content-viewer.tsx:49`), exam `question_text`
(`question-renderer.tsx:231`), option text (`single-choice-input.tsx:48` et al.), and the review
question list (`exam-review-question-list.tsx:63`). The shared `MarkdownText`
(`react-markdown` + `remark-gfm`) is used only for AI chat bubbles and even there has no math
plugin — `$...$` would render as literal `$` in chat too.

**Agreed approach (spec'd in `12_content_extraction.md` §11):**
- Add `remark-math` + `rehype-katex` (+ the `katex` package + its CSS) to the frontend.
- Wire the math plugins into the shared `MarkdownText` so chat bubbles, and any markdown surface,
  render math.
- Route the plain-text surfaces through a math-aware renderer instead of raw `<p>`/`<span>` text
  interpolation: `ContentViewer` (topic `text` rows), `QuestionRenderer` (`question_text`), the
  option-input components (option `text`), and `ExamReviewQuestionList` (review `question_text`).
- KaTeX (not MathJax) — synchronous, smaller, sufficient for authored educational content;
  MathJax's async rendering model is heavier than needed here.

**What needs to be spec'd / decided on pickup:**
- Delimiter convention: support inline `$...$` and block `$$...$$` (KaTeX default via
  `remark-math`); confirm whether `\(...\)` / `\[...\...\\]` should also be recognised (some
  extraction sources may emit those). Recommendation: accept both `$` and `\(\)` families.
- Security: KaTeX escapes by default (no `trust`/`\url` macros) — confirm the extraction pipeline's
  restructured markdown is still sanitised by `MarkdownText`'s no-`rehype-raw` policy so math
  rendering doesn't open an HTML injection path.
- SSR consideration: KaTeX renders client-side; confirm no layout shift / hydration mismatch on
  the content viewer and exam pages (render math in an effect or use `katex`'s server-side render
  for the static parts).

**Why deferred from pre-Phase-5:** the hardening pass is a set of small, surgical fixes; a math
pipeline touches five+ render surfaces, adds a dependency, and needs SSR/security review. It is
self-contained and ships better as one focused follow-up than as part of the hardening pass.
