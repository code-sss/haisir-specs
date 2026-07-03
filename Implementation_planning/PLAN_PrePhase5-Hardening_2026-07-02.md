# PLAN — Pre-Phase 5: Phase 4 Release-Hardening Pass

> Written 2026-07-02 in response to 14 issues found while manually testing the through-Phase-4
> build. This is a **hardening pass to make Phase 4 release-ready for user testing**, sequenced
> **before** Phase 5 (`PLAN.md`). Phase 5's goal tree is unchanged; where pre-Phase-5 touches a
> surface Phase 5 also touches, the coordination is noted inline.
>
> **This is a specs-repo plan.** Tasks tagged `[backend]`/`[frontend]`/`[deploy]` are
> implementation tickets for the sibling repos to pick up — they are **not** executed here. Tasks
> tagged `[specs]` are specs-repo edits; the spec content for the `[specs]` tasks in G6/G7/G8 is
> written as part of this plan (see the spec files referenced in each task).
> Task checkboxes live in `TASKS_PrePhase5-Hardening_2026-07-02.md`; decisions are logged in
> `decisions.md` (2026-07-02 — pre-Phase-5 entry).

## Planning Inputs

- **Root goal:** The through-Phase-4 build is release-ready for user testing: every screen the
  user is meant to reach is reachable from in-app navigation, exam taking/review is end-to-end,
  topic-filtered exam selection works, weak-topic deep-links land on the right topic, the tree
  behaves, content labels are readable, recommended-grade activation has a UI path, and the
  notification/at-risk loop doesn't send users to the wrong page.
- **Repos:** `[backend]` haisir-backend, `[frontend]` haisir-frontend, `[deploy]` haisir-deploy,
  `[specs]` haisir-specs. **No Alembic migrations** — every fix rides on existing schema
  (V37 `questions.topic_id`, `student_profiles.grade`, `notifications.action_url`).
- **No deploy-repo gateway work** except the `qa-sample.json` content edit (no new APISIX routes,
  no timeout changes — all endpoints already live).
- **Scope decisions (taken with the recommended option on each; see `decisions.md`):**
  1. **Issue 9 (teacher at-risk notification → `/teacher/doubts`): defer the view, fix the
     `action_url`, spec the view for Phase 6.** Building a teacher at-risk/student-detail page is
     real teacher-side tooling that belongs with role migration; pre-Phase-5 sets `action_url`
     to a non-broken interim and records the view in the backlog + `04_teacher_tutor.md`.
  2. **Issue 11 (LaTeX rendering): defer to a dedicated content-rendering follow-up, spec note +
     backlog entry.** Adding `remark-math`/`rehype-katex` across ContentViewer, QuestionRenderer,
     options, and review is a self-contained content-rendering slice; pre-Phase-5 documents the
     requirement and ships it as a focused follow-up rather than ballooning the hardening pass.
  3. **Issue 12 (inbox UX): targeted polish now** — bell dropdown, status filters, last-message
     previews. No full redesign.
  4. **Issues 13/14 (recommended-grade / onboarding completeness): grade collection lands in
     pre-Phase-5 student onboarding + a note that Phase 5 T1.5 `/profile` will expose the editable
     grade.** Pre-Phase-5 makes `recommended` activatable for testers; Phase 5 makes it editable.

## Verified issue summary (from the 5 parallel investigations)

| # | Issue | Verified root cause | Disposition |
|---|---|---|---|
| 1 | No link to `/exam/[id]/review` | Route exists, **zero inbound links**; submit/modal/results all render inline | Fix (frontend) — G1 |
| 2 | Per-question topic_id tedious | `question-editor.tsx:462-481` per-question `<select>`; no bulk setter | Fix (frontend) — G2 |
| 3 | Multi-topic exams | Works per-topic; `topic_id=NULL` questions **silently skipped** → subject-level exams compute no mastery | Spec note — G8 (accepted v1 limit) |
| 4 | `qa-sample.json` lacks `topic_id` | No question has it; importer/exporter already round-trips it | Fix (deploy) — G2 |
| 5 | Take Exam shows all exams | `topic-list-panel.tsx:35` passes node_id not topic_id; backend has no `topic_id` filter | Fix (backend+frontend) — G3 |
| 6 | Focus Areas chip dead-links | `focus-areas-strip.tsx` → `/courses?topic=...` but `student-courses-page.tsx` never reads searchParams | Fix (frontend) — G4 |
| 7 | Tree collapses on topic click | `node-tree-sidebar.tsx:34-40` one button: leaf→select, non-leaf→toggle only | Fix (frontend) — G4 |
| 8 | "View Results" broken | Same root cause as #1 — inline render, never the review route | Fix (frontend) — G1 |
| 9 | "Student needs attention" → /teacher/doubts | `mastery_service.py:277` `action_url="/teacher/doubts"`; no at-risk view exists | Interim fix + spec — G8 |
| 10 | Enrollment shows "8" not "Grade 8" | `catalog-card.tsx:18` renders `node.name` verbatim | Fix (frontend) — G5 |
| 11 | LaTeX not rendered | No math lib; `content-viewer.tsx:49`, `question-renderer.tsx:231`, options all plain text | Spec note + backlog — G8 |
| 12 | Inbox UX weak | No filters/previews; bell is a plain link (`notification-bell.tsx:15-20`) | Fix (frontend) + spec — G7 |
| 13 | Recommended needs manual DB profile | `POST /api/students/me/profile` exists but no UI calls it; onboarding collects nothing | Fix (frontend) + spec — G6 |
| 14 | Onboarding completeness | Student + parent onboarding CTA-only by design (BR-ON-008/015); grade never collected | Ties to #13 — G6 |
| 15 | *(found in plan review, not user-reported)* Review page mislabels pending-grading questions | `review-helpers.ts:16-22` maps `is_correct===null` straight to `"skipped"`; ungraded essays (`grading_status: "pending"`, already mapped at `session-answers-mapper.ts:109` but unread) get the same treatment — latent while the route was unreachable, becomes user-visible once G1 wires navigation to it | Fix (frontend) — G1/T1.4 |

> **Onboarding grade skip has no recovery path pre-Phase-5 (verified, not fixed):** if a student
> clicks "Skip" on the G6/T6.1 grade step, there is **no other UI anywhere in the shipped
> frontend** to set `student_profiles.grade` afterwards — no `/profile` route exists yet (that's
> Phase 5 T1.5) and onboarding does not re-run once complete. This is now explicitly documented as
> an accepted interim limitation in `09_onboarding.md` rather than left implicit — see that file
> for the tester-facing guidance (don't skip if you want `recommended` to activate before Phase 5).

## Goal Tree (summary)

```
ROOT: Pre-Phase 5 — Phase 4 release-hardening pass
├── G1: Exam review navigation wired (issues 1, 8)          [frontend]
│   ├── T1.1 Post-submit "Review answers" CTA → /exam/{id}/review
│   ├── T1.2 AttemptsModal per-attempt "View" → /exam/{id}/review
│   ├── T1.3 "📊 Results" button → attempts list; each row routes to review
│   └── T1.4 Review page: pending-grading questions must not show as "Skipped" (gap found in review)
├── G2: Exam builder bulk-topic + sample JSON (issues 2, 4) [frontend, deploy]
│   ├── T2.1 [frontend] "Apply topic to all questions" control in ExamBuilder
│   ├── T2.2 [deploy]  Add topic_id to qa-sample.json question objects
│   └── T2.3 [frontend] JSON import/export round-trip test for topic_id
├── G3: Topic-filtered exam taking (issue 5)               [backend, frontend]
│   ├── T3.1 [backend]  Optional topic_id filter on GET /api/exams/course/{node_id}
│   ├── T3.2 [frontend] TopicListPanel "Take Exam" passes topic_id; /exam consumes it
│   └── T3.3 [backend]  Integration test — topic_id filter returns only matching templates
├── G4: Deep-link + tree interaction fixes (issues 6, 7)  [frontend]
│   ├── T4.1 /courses consumes ?topic= searchParam → expand ancestors + select topic
│   └── T4.2 NodeTreeSidebar: separate chevron toggle from label select+expand
├── G5: Catalog grade label (issue 10)                     [frontend]
│   └── T5.1 CatalogCard renders "Grade {name}" when node_type === "grade"
├── G6: Student grade/profile + onboarding (issues 13, 14)  [frontend, backend, specs]
│   ├── T6.1 [frontend] Grade picker in student onboarding View B → POST /api/students/me/profile
│   ├── T6.2 [backend]  Verify profile upsert accepts grade-only patch (verification + test)
│   └── T6.3 [specs]    09_onboarding.md: student View B collects grade (amends BR-ON-008) ✅ written
├── G7: Inbox UX targeted polish (issue 12)                [frontend, specs]
│   ├── T7.1 [frontend] NotificationBell dropdown (recent unread + mark-read + "View all")
│   ├── T7.2 [frontend] Doubt inboxes: status filter + last-message preview excerpt
│   ├── T7.3 [frontend] NotificationsPage: unread-only toggle + type/source icon
│   └── T7.4 [specs]    10_notifications.md + 03_student.md/04_teacher_tutor.md inbox UX contract ✅ written
└── G8: At-risk notif interim + deferred-items spec docs (issues 3, 9, 11) [backend, specs]
    ├── T8.1 [backend]  student_at_risk action_url → null (no broken nav) until view exists
    ├── T8.2 [specs]    04_teacher_tutor.md + backlog: teacher at-risk detail view (Phase 6) ✅ written
    ├── T8.3 [specs]    03_student.md mastery note: NULL topic_id questions contribute no mastery ✅ written
    └── T8.4 [specs]    12_content_extraction.md + backlog: LaTeX/math rendering requirement ✅ written
```

`✅ written` marks specs-repo deliverables that are completed as part of this plan (the spec
content is committed alongside the plan). All other tasks are implementation tickets for the
sibling repos.

---

## G1 — Exam review navigation wired (issues 1, 8)  · [frontend]

**Goal:** The fully-built `/exam/[session_id]/review` route (S05, `ExamReviewPage`) is reachable
from in-app navigation — after submitting an exam, from the per-attempt row in the AttemptsModal,
and from the exam-card "Results" action. The route is no longer orphaned.
**Root cause (verified):** `src/app/exam/[session_id]/review/page.tsx` exists and renders
`ExamReviewPage`, but **zero inbound links** exist. Post-submit (`hooks/use-exam-page.ts:13-38`)
opens the AttemptsModal inline; the modal's per-attempt "View" button
(`components/exam/attempts-modal.tsx:496-507`) fetches `/answers` and renders inline; the "📊
Results" button (`components/exam/exam-list.tsx:69-77`) does the same. Issue 8 ("View Results
broken") is the same root cause — the inline-render path is the dead "results page."

##### T1.1 [frontend] — Post-submit "Review answers" CTA → /exam/{id}/review
- **Build:** In `hooks/use-exam-page.ts` and `app/exam/page.tsx`, on a successful non-`grading_pending`
  submit, surface a "Review answers" CTA (in addition to or instead of auto-opening the AttemptsModal)
  that calls `router.push(`/exam/${sessionId}/review`)`. For `grading_pending`, keep the existing
  interstitial; the "View Attempts" CTA stays (graded attempts route to review via T1.2).
- **Done when:** Submitting a graded exam and clicking "Review answers" lands on
  `/exam/{sessionId}/review` with the review UI rendered.
- **Test:** `expect(routerPush).toHaveBeenCalledWith("/exam/<id>/review")` after submit + click.
- **Depends on:** None.

##### T1.2 [frontend] — AttemptsModal per-attempt "View" → /exam/{id}/review
- **Build:** In `components/exam/attempts-modal.tsx:496-507`, the per-attempt "View" button calls
  `onViewAttempt(attempt.id)`. Change `handleAttemptReviewClick` (`hooks/use-exam-state.ts:273-280`)
  to `router.push(`/exam/${attemptId}/review`)` instead of fetching `/answers` and rendering inline.
  Drop the inline render block (`attempts-modal.tsx:314-411`) — the review page owns that surface.
  Keep the attempts **list** in the modal (template + per-attempt rows: score, status, timestamp).
- **Done when:** Clicking "View" on an attempt row navigates to the review route.
- **Test:** `expect(routerPush).toHaveBeenCalledWith("/exam/<attempt_id>/review")` on "View" click.
- **Depends on:** T1.1 (soft).

##### T1.3 [frontend] — "📊 Results" button → attempts list (rows route to review)
- **Build:** The "📊 Results" button (`exam-list.tsx:69-77` → `handleViewResultsClick`,
  `use-exam-state.ts:259-271`) opens the AttemptsModal listing all attempts for the template. Keep
  that. With T1.2, each row's "View" routes to review, so the button is no longer "broken." Verify
  the attempts fetch (`GET /api/exam-sessions/session/all/{templateId}`, `api/exam.ts:175-184`)
  returns rows; if the "broken" symptom is a fetch/render error, fix it here.
- **Done when:** "📊 Results" opens a populated attempts list and each row reaches the review page.
- **Test:** row present → click → review route.
- **Depends on:** T1.2.

##### T1.4 [frontend] — Review page must not mislabel pending-grading questions as "Skipped"
- **Gap found in review (2026-07-02), not in the original 14 issues.** Wiring in-app navigation
  to `/exam/[session_id]/review` (T1.1–T1.3) exposes a **pre-existing latent bug** in the review
  page that was harmless while the route was unreachable: `getReviewQuestionStatus`
  (`src/features/exam/domain/review-helpers.ts:16-22`) maps `is_correct === null` straight to
  `"skipped"`. An ungraded essay (`grading_status: "pending"` — the field is already mapped onto
  `ExamReviewItem` by `session-answers-mapper.ts:109` but never read) also has `is_correct ===
  null`, so once users can reach this page they will see their submitted, ungraded essay answers
  labelled **"Skipped"** — factually wrong and likely to alarm a student who did answer. The
  **old** inline render in `attempts-modal.tsx` handled this correctly (disabled "View" while
  `attempt.status === "grading_pending"`; rendered a `⏳` pending mark keyed off `is_correct ===
  null` combined with grading context) — that logic was never carried over to the new review page.
- **Build:** In `review-helpers.ts`, extend `ReviewQuestionStatus` with `"pending"` and change
  `getReviewQuestionStatus` to check `item.grading_status === "pending"` (or equivalent ungraded
  marker) **before** falling back to the `is_correct === null → "skipped"` case. Render a distinct
  "Pending grading" badge/style for `"pending"` in `exam-review-question-list.tsx` (do not reuse
  the "Skipped" badge). This must ship in the same slice as T1.1–T1.3 — routing users into this
  page without the fix is a regression, not a neutral change.
- **Done when:** A submitted attempt with an ungraded essay question, viewed via
  `/exam/{id}/review`, shows that question as "Pending grading," not "Skipped."
- **Test:** `expect(getReviewQuestionStatus({ is_correct: null, grading_status: "pending" })).toBe("pending")`;
  unanswered question (`is_correct: null`, no `grading_status`) still resolves to `"skipped"`.
- **Depends on:** None (parallel to T1.1–T1.3; must land before or with them).

---

## G2 — Exam builder bulk-topic + sample JSON (issues 2, 4)  · [frontend, deploy]

**Goal:** Setting a topic on every question is no longer tedious for same-topic exams, and the QA
sample JSON exercises the `topic_id` field end-to-end.

##### T2.1 [frontend] — "Apply topic to all questions" control in ExamBuilder
- **Build:** In `features/exam/components/authoring/exam-builder.tsx`, add a control above the
  questions list (between the metadata section closing ~`:264` and the questions section `:308-311`)
  with a topic `<select>` (same `topics` source already fetched at `:96` via `useTopics(nodeId)`)
  and an "Apply to all questions" button. On click, map over the standalone `questions` array AND
  every `paragraphs[].questions` array setting `topic_id` to the chosen value, via the existing
  `onQuestionsChange` / `onParagraphsChange` props (`:90-91`). No hook change needed
  (`useExamAuthoring.setQuestions` already accepts a full array). Per-question `<select>` in
  `question-editor.tsx:462-481` stays for individual override.
- **Done when:** "Apply to all" sets every question's `topic_id`; individual questions still
  overridable; the API payload (`exam-api.ts:264`) carries `topic_id` on every question.
- **Test:** `expect(questions.every(q => q.topic_id === chosen))`.
- **Depends on:** None.

##### T2.2 [deploy] — Add topic_id to qa-sample.json question objects
- **Build:** Edit `haisir-deploy/docs/qa-sample.json`. Add a `topic_id` (UUID) to each question
  object in the sample, consistent with a topic belonging to the sample's course node. Add
  `topic_id` to at least one paragraph-embedded question too. Document the chosen id in a comment
  field if the sample is board-agnostic (or use a real seed topic id).
- **Done when:** `jq '.items[] | select(.type=="question") | .topic_id' qa-sample.json` returns
  non-null for standalone questions; import round-trips.
- **Test:** `grep -c topic_id qa-sample.json` ≥ expected count.
- **Depends on:** None.

##### T2.3 [frontend] — JSON import/export round-trip test for topic_id
- **Build:** `features/exam/domain/json-importer.ts` already round-trips `topic_id` (`:86` import,
  `:276` export). Add a unit test that imports a `topic_id`-carrying fixture and re-exports it,
  asserting `topic_id` is preserved on every question including paragraph-embedded ones.
- **Done when:** Test passes; `topic_id` survives import → export.
- **Test:** `expect(exported.questions[0].topic_id).toBe(sampleId)`.
- **Depends on:** T2.2 (fixture shape).

---

## G3 — Topic-filtered exam taking (issue 5)  · [backend, frontend]

**Goal:** Clicking "Take Exam" on a specific topic lists only exams that have questions tagged
with that topic — not every exam under the parent node.
**Root cause (verified):** `topic-list-panel.tsx:35-44` passes the **parent node id** to
`onTakeExam`; `student-courses-page.tsx:90-95` navigates `/exam?node_id=...`; `api/exam.ts:14-24`
calls `GET /api/exams/course/{nodeId}` with no `topic_id`; backend `routes/exam.py:410-439`
filters by node only.

##### T3.1 [backend] — Optional topic_id filter on GET /api/exams/course/{node_id}
- **Build:** In `src/api/routes/exam.py:410-439` (`@router.get("/course/{node_id}")`), add an
  optional `topic_id: UUID4 | None = Query(default=None)`. When provided, filter returned templates
  to those having **at least one question with `question.topic_id == topic_id`** (join
  `exam_template_questions → questions`). Apply the same filter to the instructor
  `GET /api/exams/template` (`routes/exam.py:230-257`) for symmetry. No schema change —
  `questions.topic_id` exists since V37.
- **Done when:** `GET /api/exams/course/{node_id}?topic_id={tid}` returns only templates containing
  a question tagged with `tid`; omitting `topic_id` returns all (unchanged).
- **Test:** `assert all(t has a question with topic_id==tid for t in filtered)`.
- **Depends on:** None.

##### T3.2 [frontend] — TopicListPanel "Take Exam" passes topic_id; /exam consumes it
- **Build:** `topic-list-panel.tsx:35-44` — change `onTakeExam` to pass **both** the node id and the
  **topic id** the button belongs to. `student-courses-page.tsx:90-95` — navigate
  `/exam?node_id=...&topic_id=...`. `app/exam/page.tsx:22-23` — read `topic_id`; `use-exam-state.ts`
  `loadExams(nodeId, topicId?)`; `api/exam.ts:14-24` `fetchExams(csrfToken, nodeId, topicId?)`
  appends `&topic_id=...` when present. The home-page node-level "Take Exam"
  (`app/home/page.tsx:80-94`) keeps node-only behaviour — unchanged.
- **Done when:** "Take Exam" on "Ratio" lists only exams containing Ratio-tagged questions; the
  node-level home button still lists all Maths exams.
- **Test:** `expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("topic_id="), …)`.
- **Depends on:** T3.1.

##### T3.3 [backend] — Integration test: topic_id filter
- **Build:** Seed a node with two topics and two templates — one with a question tagged to topic
  A, one tagged to topic B. `GET /course/{node}?topic_id=A` returns only template A; `?topic_id=B`
  only B; no param returns both.
- **Done when:** All three assertions pass.
- **Test:** This is the G3 goal test.
- **Depends on:** T3.1.

---

## G4 — Deep-link + tree interaction fixes (issues 6, 7)  · [frontend]

**Goal:** The Focus Areas weak-topic chip deep-links to `/courses?topic=...` and lands with the
  topic's ancestors expanded and the topic selected; clicking a non-leaf node label selects it and
  expands it (does not collapse).
**Root cause (verified):** (6) `focus-areas-strip.tsx:18-30` links to `/courses?topic={id}` but
  `student-courses-page.tsx` never reads `searchParams` and `NodeTreeSidebar` has no initial-expand
  support (`node-tree-sidebar.tsx:84`). (7) `node-tree-sidebar.tsx:34-40` — one row button does both
  jobs: leaf→`onSelectNode`, non-leaf→`onToggle`; clicking a non-leaf label only toggles.

##### T4.1 [frontend] — /courses consumes ?topic= searchParam → expand ancestors + select topic
- **Build:** `student-courses-page.tsx` — add `useSearchParams`; read `topic`. On load (and on
  `topic` change), resolve the topic to its owning node, set `selectedTopicId` + `selectedNodeId`,
  and compute the ancestor path from root to that node. Pass `initialExpandedIds` (the ancestor
  set) to `NodeTreeSidebar` and have the sidebar seed `expandedIds` from it on mount (not fight
  user toggles afterwards). If the topic isn't found (stale link, parent revoked), fall back to the
  collapsed tree with no error.
- **Done when:** Clicking a Focus Areas chip lands on `/courses` with the weak topic's ancestors
  expanded and the topic selected/visible.
- **Test:** Render with `?topic=<id>` mock → topic visible + ancestor rows expanded.
- **Depends on:** None.

##### T4.2 [frontend] — NodeTreeSidebar: separate chevron toggle from label select+expand
- **Build:** `node-tree-sidebar.tsx` — restructure each row so the **chevron is its own button**
  (toggle-only) and the **label is a separate button** that, for a non-leaf node, both selects it
  (`onSelectNode`) and expands it — and never collapses on label click. For a leaf, the label
  selects as today. Restore the dedicated chevron control removed in commit `656b825`, but as a
  **sibling button** (not a nested interactive span inside the row button — avoids the S6848 a11y
  regression). Keyboard: chevron tabbable with `aria-expanded`; label tabbable. Update
  `node-tree-sidebar.test.tsx`.
- **Done when:** Clicking a non-leaf label selects it and reveals children (no collapse); chevron
  toggles independently; keyboard works.
- **Test:** Click subject label → `expect(onSelectNode).toHaveBeenCalledWith(subjectId)` +
  children visible; click chevron → collapsed.
- **Depends on:** None.

---

## G5 — Catalog grade label (issue 10)  · [frontend]

**Goal:** Enrollment root nodes display as "Grade 8" rather than bare "8".
**Root cause (verified):** `catalog-card.tsx:18` renders `node.name` verbatim; no
`node_type === "grade"` prefixing. Backend `course_path_nodes.name` is the raw board name;
display-side prefixing is the right fix (name is shared with admin authoring).

##### T5.1 [frontend] — CatalogCard renders "Grade {name}" when node_type === "grade"
- **Build:** `features/student/components/catalog-card.tsx:17-19` — compute
  `displayName = node.node_type === "grade" && /^\d+$/.test(node.name) ? \`Grade ${node.name}\` : node.name;`
  Render `displayName`. No backend change.
- **Done when:** A root node named "8" of type "grade" renders the heading "Grade 8".
- **Test:** `expect(screen.getByText("Grade 8")).toBeInTheDocument()`.
- **Depends on:** None.

---

## G6 — Student grade/profile + onboarding (issues 13, 14)  · [frontend, backend, specs]

**Goal:** A student can set their grade via the UI (onboarding now, `/profile` editable in Phase 5)
  so `recommended` activates without a manual DB insert; onboarding completeness is confirmed for
  student (grade collected) and parent (CTA-only by design — link flow lands in Phase 5).
**Root cause (verified):** `POST /api/students/me/profile` exists (`routes/student_profile.py:21-41`,
  `StudentProfileUpsert.grade`) but **no UI calls it**; onboarding is CTA-only (BR-ON-008/015), so
  `student_profiles.grade` is NULL and `EnrollmentService.get_catalog` returns `recommended=False`
  for every node (`enrollment_service.py:127`).

##### T6.1 [frontend] — Grade picker in student onboarding View B
- **Build:** `features/onboarding/components/on03-student-ready.tsx` View B — add a minimal grade
  picker (a `<select>` of platform grade root names, fetched via `getCatalog`/`getNodes` and
  filtered `node_type === "grade"`; fall back to free-text). Before
  `PATCH /api/users/me/onboarding-complete`, call `POST /api/students/me/profile` with `{ grade }`
  (`fetchWithCSRFRetry` + `buildApiHeaders`, `X-Current-Role: student`). Allow "Skip" (recommended
  stays off until later). Keep existing CTAs. Spec'd exception to BR-ON-008 (recorded in T6.3).
- **Done when:** Selecting grade "8" and continuing posts the profile; catalog's Grade 8 node shows
  `recommended`.
- **Test:** profile POST observed with grade "8".
- **Depends on:** None.

##### T6.2 [backend] — Verify profile upsert accepts grade-only patch
- **Build:** Confirm `StudentProfileUpsert` (`schemas/user_metadata.py:66-74`) and
  `POST /api/students/me/profile` accept `{ "grade": "8" }` without other fields. Add a unit test if
  none covers the grade-only path. No code change expected — verification + test only.
- **Done when:** A grade-only POST succeeds and `student_profiles.grade` is set.
- **Test:** `assert profile.grade == "8"`.
- **Depends on:** None.

##### T6.3 [specs] — 09_onboarding.md: student View B collects grade (amends BR-ON-008)  ✅ written
- **Spec written:** `target/requirements/09_onboarding.md` amended — student onboarding View B
  collects **grade** as the one profile field gathered at onboarding, posted to
  `POST /api/students/me/profile` before `onboarding-complete`; feeds the catalog `recommended`
  badge; Phase 5 `/profile` (T1.5) will expose the editable grade. Parent onboarding stays CTA-only
  (BR-ON-015); the existing `on05-parent-ready.tsx:82` dead `/link-child` CTA is fixed by Phase 5
  T2.6.
- **Depends on:** T6.1 (behaviour final).

---

## G7 — Inbox UX targeted polish (issue 12)  · [frontend, specs]

**Goal:** Notifications + doubts inboxes are usable: bell previews recent unread inline, doubt
  rows show a last-message preview, both inboxes have a status filter.
**Root cause (verified):** `notification-bell.tsx:15-20` is a plain link (not a dropdown);
  `notification-feed-page.tsx` has no filters; `doubt-inbox-page.tsx` / `teacher-doubt-inbox-page.tsx`
  are flat lists with no filters/previews/pagination.

##### T7.1 [frontend] — NotificationBell dropdown
- **Build:** `features/notifications/components/notification-bell.tsx` — convert from a plain link
  to a dropdown panel (native `<dialog>` or controlled popover) showing the **recent 5–10 unread**
  (title + relative time + unread dot), each click → mark-read + `router.push(action_url)`; a
  "View all" footer → `/notifications`; "Mark all read" inline. Keep the unread badge, 60s poll,
  tab-hidden pause. Close on outside-click / Escape.
- **Done when:** Bell opens a dropdown with recent unread; item click marks read + navigates.
- **Test:** `expect(screen.getByRole("dialog")).toBeInTheDocument()` on bell click with unread.
- **Depends on:** None.

##### T7.2 [frontend] — Doubt inboxes: status filter + last-message preview
- **Build:** `doubt-inbox-page.tsx` and `teacher-doubt-inbox-page.tsx` — add a status filter
  (All / New / Escalated / Answered / Resolved; teacher adds "Claimed by me"). Filter client-side.
  Add a **last-message preview excerpt** to each row; prefer a backend `excerpt` field on the list
  endpoint to avoid N+1 thread fetches (if small, add it; otherwise truncate from existing fields
  and note the backend enhancement as a follow-up).
- **Done when:** "Escalated" filter shows only escalated; each row shows a one-line preview.
- **Test:** Select "Escalated" → only escalated rows.
- **Depends on:** None.

##### T7.3 [frontend] — NotificationsPage: unread-only toggle + type/source icon
- **Build:** `notification-feed-page.tsx` — add "Unread only" toggle + a type/source icon (or
  coloured dot) per item so the source (doubt vs mastery vs at-risk) is scannable. Keep
  Today/Yesterday/Earlier grouping.
- **Done when:** "Unread only" hides read items; icons render per type.
- **Test:** Toggle on → only unread rows.
- **Depends on:** None.

##### T7.4 [specs] — Inbox UX contract  ✅ written
- **Spec written:** `target/requirements/10_notifications.md` — bell dropdown contract (recent
  unread, mark-read, view-all) + feed filters (unread-only, type icon).
  `target/requirements/03_student.md` (doubts slice) and `target/requirements/04_teacher_tutor.md`
  (teacher queue) — status filter + last-message preview as the inbox UX contract.
- **Depends on:** T7.1, T7.2 (behaviour final).

---

## G8 — At-risk notif interim + deferred-items spec docs (issues 3, 9, 11)  · [backend, specs]

**Goal:** No notification sends a user to the wrong page; the three deferred items (subject-level
  mastery, teacher at-risk view, LaTeX rendering) are spec'd and backloged so a future phase picks
  them up cleanly.

##### T8.1 [backend] — student_at_risk action_url → null (no broken nav) until view exists
- **Build:** `src/domain/services/mastery_service.py:263-278` — change `action_url="/teacher/doubts"`
  to `action_url=None` for the `student_at_risk` notification. The feed handler already guards
  `if action_url.startswith("/")`. Optionally enrich `title`/`body` with the student's display name
  if a cheap `StudentProfileRepository.get_by_sub` lookup is in the call path; if not, leave generic
  and note name-enrichment as a follow-up. Do **not** point at `/teacher/doubts`.
- **Done when:** A fired `student_at_risk` notification has `action_url IS NULL`; clicking marks
  read with no navigation.
- **Test:** `assert notif.action_url is None`.
- **Depends on:** None.

##### T8.2 [specs] — Teacher at-risk detail view → Phase 6 (backlog + 04_teacher_tutor.md)  ✅ written
- **Spec written:** `vision/requirements/backlog.md` — "Teacher at-risk / student detail view": a
  `/teacher/students/{sub}` page + instructor-facing endpoint surfacing the at-risk student's weak
  topics (the `weak_topics` shape already exists on the student dashboard) and recent exam
  results; `student_at_risk` notification's `action_url` will point here once built. Status
  `Deferred`. `target/requirements/04_teacher_tutor.md` — short "At-risk routing" note referencing
  the backlog item and the interim `action_url=None`.
- **Depends on:** T8.1 (interim chosen).

##### T8.3 [specs] — Mastery note: NULL topic_id questions contribute no mastery  ✅ written
- **Spec written:** `target/requirements/03_student.md` (mastery / progress slice) — explicit note:
  `MasteryService` groups scored questions by `questions.topic_id`; questions with
  `topic_id = NULL` are **silently skipped** and contribute to no topic's mastery
  (`mastery_service.py:142`). Therefore a **subject-level exam with no per-question topic tagging
  computes no mastery** — accepted v1 limitation; subject-level mastery aggregation deferred.
  `target/requirements/07_platform_admin.md` exam-builder topic-attribution cross-reference so
  authors know topic tagging is required for mastery to fire.
- **Depends on:** None.

##### T8.4 [specs] — LaTeX/math rendering requirement (content-rendering follow-up)  ✅ written
- **Spec written:** `target/requirements/12_content_extraction.md` — "Content rendering" note:
  topic `text` content, exam `question_text`, option text, and review question bodies must render
  LaTeX math (inline `$...$` and block `$$...$$`); the current build renders them as raw literal
  text. Agreed approach: `remark-math` + `rehype-katex` (+ `katex` CSS) wired into the shared
  `MarkdownText` and routed through `ContentViewer`, `QuestionRenderer`, option inputs, and
  `ExamReviewQuestionList`. `vision/requirements/backlog.md` — "LaTeX/math rendering pipeline",
  Status `Ready`, ships as a focused follow-up phase. No implementation in pre-Phase-5.
- **Depends on:** None.

---

## Cross-repo dependency edges

| From (needs) | To (provides) |
|---|---|
| T1.2 [frontend] | T1.1 [frontend] (soft) |
| T1.3 [frontend] | T1.2 [frontend] |
| T2.3 [frontend] | T2.2 [deploy] (fixture) |
| T3.2 [frontend] | T3.1 [backend] (filter param) |
| T3.3 [backend]  | T3.1 [backend] |
| T6.3 [specs]    | T6.1 [frontend] (behaviour final) — spec written ahead |
| T7.4 [specs]    | T7.1, T7.2 [frontend] — spec written ahead |
| T8.2 [specs]    | T8.1 [backend] — spec written ahead |

**Ready now (no pending deps):** T1.1, T1.4, T2.1, T2.2, T3.1, T4.1, T4.2, T5.1, T6.1, T6.2, T7.1,
T7.2, T7.3, T8.1 — and the four `[specs]` tasks are already written.

**Sequencing:** G1–G7 are independent and can fan out across the frontend with the two backend
slices (T3.1, T8.1) and the deploy edit (T2.2) in parallel. **Gate:** pre-Phase-5 must close before
Phase 5 starts (Phase 5's `/profile` page, T1.5, will extend the grade field T6.1 introduces; the
parent onboarding dead-link T2.6 is untouched by pre-Phase-5).

<!-- plan-baseline: backend:0cb36bd frontend:df7067e deploy:98912f8 (Phase 4 sign-off baseline) -->