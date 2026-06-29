# Student Persona

> **Target state scope:** Student experience with platform content, parent Home Study content, and the **doubt thread** (S08/S09 — Phase 4). Institutions, classes, and notifications wiring are out of scope for this increment; the doubt persistence + hAITU thread lifecycle is defined in `11_haitu_ai_layer.md`.

---

## Screens

| Screen ID | Name | Route |
|---|---|---|
| S-home | Dashboard | `/home` |
| S-nav | Content Navigator | `/courses` |
| S-exam | Exam Taking | `/exam/:session_id` |
| S-results | Exam Results | `/exam/:session_id/results` |
| S05 | Post-Exam AI Review | `/exam/:session_id/review` |
| S-profile | Student Profile | `/profile` |
| S08 | Doubt Inbox | `/doubts` |
| S09 | Doubt Thread | `/doubts/:doubt_id` |

---

## S-home — Dashboard

Two distinct sections on the dashboard:

### Platform Content section (blue, `#185FA5`)
- Heading: "Platform Board"
- Grid of subject cards (platform `course_path_nodes` with `owner_type = 'platform'` at the top level / grade level).
- Each card: subject name, topic count, a "Continue" or "Start" CTA.
- Clicking a card opens S-nav with `source = 'platform'`.

### Home Study section (green, `#1D9E75`)
- Heading: "Home Study"
- Shown **only** if the student has at least one active `parent_child_links` record.
- If no active link: show a placeholder card "No Home Study content yet — ask your parent to link their account."
- Grid of subject cards from the linked parent's adopted/built curriculum (`owner_type = 'parent'`, `owner_id = parent.idp_sub`).
- Clicking a card opens S-nav with `source = 'parent'`.

**Business rules:**
- BR-STU-001: Content visibility uses BR-DATA-003 filter — platform content always visible; parent content only if active `parent_child_links` exists.
- BR-STU-002: Home Study section is hidden entirely if there are zero active parent links.

---

## S-nav — Content Navigator

Two source tabs: **Platform** | **Home Study**.

- Active tab = the source passed when navigating from S-home (or defaults to Platform).
- Home Study tab is disabled (greyed) if no active parent link exists.

### Left sidebar — Node tree
- Hierarchical tree of `course_path_nodes` filtered by the selected source.
- Platform tab: `owner_type = 'platform'`.
- Home Study tab: `owner_type = 'parent'` where `owner_id` is the linked parent's `idp_sub`.
- Expandable/collapsible nodes. Leaf nodes show topic count badge.
- Selecting a leaf node loads the topic list on the right.

### Right panel — Topic list
- Lists topics for the selected node.
- Each row: topic title, content type icons (PDF / video / text), status badge (`live` only — draft topics not shown to students), "Take Exam" button if an exam template is linked.
- Clicking a topic opens the topic content viewer (inline PDF, video embed, or text).
- "Take Exam" → creates a new `exam_session` and navigates to S-exam.

**Business rules:**
- BR-STU-003: Students only see topics with `status = 'live'`.
- BR-STU-004: "Take Exam" is shown if the topic's parent node has at least one published `exam_template` scoped to that node.
- BR-STU-005: Exam sessions are per-student; `exam_sessions.user_id = student.idp_sub`.

---

## S-exam — Exam Taking

- Timer displayed (countdown from `exam_templates.time_limit_minutes`; no time limit → no timer shown).
- Questions rendered one per page or all-at-once (controlled by `exam_templates.display_mode`; default: all-at-once).
- "Submit" button — disabled until at least one question answered.
- Confirmation modal before submission.
- On submit: `POST /api/student/exam-sessions/:session_id/submit`.

**Question rendering by type:**

| Type | UI element |
|---|---|
| `single_choice` | Radio button group |
| `multiple_choice` | Checkbox group |
| `true_false` | Two radio buttons: "True" / "False" |
| `fill_in_the_blank` | Multi-word text input |
| `one_word_response` | Compact single-word inline input |
| `essay` (`short`) | Text area; hint: "Write 4–5 sentences" |
| `essay` (`long`) | Text area; hint: "Write 1–2 paragraphs" |
| `matching` | Two columns; right-column items displayed in shuffled order (seeded per-session); student pairs via drag-and-drop or dropdown selectors |
| `problem_solving` | Single-line answer input; when `working_required = true`, a free-text working area is shown below the answer field |

**Exam color theme:**
- Platform exams: blue accent (`#185FA5`).
- Home Study / parent exams: green accent (`#1D9E75`).

**Business rules:**
- BR-STU-006: Students can only submit their own exam sessions.
- BR-STU-007: Once submitted, the session is locked — no re-submission.
- BR-STU-008: Timer expiry triggers auto-submit with answers recorded so far.

---

## S-results — Exam Results

Shown immediately after submission.

- Score: `X / Y` and percentage (essay questions excluded from score until graded).
- Pass / Fail badge (based on `exam_templates.pass_mark`).
- Per-question breakdown: question text, student's answer, correct answer (where applicable), points awarded.
- "Back to Home Study" or "Back to Platform" CTA (context-aware based on exam source).

### Essay question states in results (API contract — Phase 1, UI is Phase 2)

`GET /api/student/exam-sessions/:session_id/results` returns `grading_status` per essay question:

| grading_status | What the student sees (Phase 2 UI) |
|---|---|
| `pending` | "Grading in progress…" |
| `ai_graded` (review_first, held) | "Pending review" |
| `released` | AI score + `ai_feedback` + "Dispute" action |
| `disputed` | "Under review" (score shown but locked pending owner action) |
| `finalized` | Score + feedback |
| `overridden` | Score + `override_feedback` |
| `error` | "Grading unavailable — contact your exam creator" |

### Dispute flow (API)

Student calls `POST /api/exam-sessions/session/{session_id}/questions/{question_id}/dispute`
(CSRF + `X-Current-Role: student`). Pre-condition: `grading_status = 'released'`. Effect:
`grading_status → 'disputed'`. Response: `204`.

**Business rules:**
- BR-STU-009: Results are shown immediately after submission — no teacher review gate in this increment.
- BR-STU-010: Students can re-visit their own results from S-home or via direct URL.
- BR-STU-013: For `auto_release` exams, essay AI score and feedback are shown to the student immediately after the worker grades the essay. The student sees the score in `S-results` when they re-visit.
- BR-STU-014: For `review_first` exams, the student sees "Pending review" for essay questions until the owner confirms or overrides. The session pass/fail badge is deferred until all essays are resolved.

---

## S05 — Post-Exam AI Review

Review a completed exam question by question, with hAITU explanations for wrong answers and a
pre-computed mistake-pattern analysis. Reached from S-results ("Review exam with hAITU") or the
/home "Focus areas" strip for weak topics.

**Note on question types:** The existing exam system supports two question types — regular
`questions` (MCQ, true/false, short answer) and `paragraph_questions` (reading passages with
multiple embedded questions). The review screen must handle both. Paragraph questions display the
passage body above the embedded questions; each embedded question is reviewed individually within
the passage context.

**Layout:**
- Score summary bar at top: score %, correct count, wrong count, skipped count, total.
- Left panel: scrollable list of question cards.
- Right panel: hAITU chat scoped to this attempt.

**Per regular question card:**
- Question number badge (green = correct, red = wrong, grey = skipped).
- Question text.
- Result label (✓ Correct / ✗ Wrong / — Skipped).
- Collapsed by default. Click header to expand.
- Expanded state shows: all answer options with the correct one (green ✓) and the student's wrong
  answer (red ✗) highlighted, plus the hAITU explanation for wrong/skipped questions.
- "Ask hAITU to explain this" button for wrong/skipped questions without a pre-loaded explanation.

**Per paragraph question card:**
- Passage title and body shown at top of the card group.
- Each embedded question rendered as a sub-card within the passage card.
- Sub-cards follow the same correct/wrong/skipped rendering as regular questions.
- hAITU explanations are per embedded question, with passage context included in the prompt.

**hAITU chat panel:**
- Pre-loaded with the pattern-analysis opening message on load: identifies the single most common
  mistake pattern across all wrong answers (2–3 sentences).
- Student can type follow-up questions — responses are generated by the `exam-review-chat` API.
- Chat is scoped to this attempt — hAITU has access to all question, answer and explanation data
  for the attempt (no RAG retrieval; see `11_haitu_ai_layer.md` §8).

**Data:**
- `GET /api/exam-sessions/session/{session_id}/answers` — the live review/answers endpoint (NOT a
  `.../review` path). Returns per-question `is_correct`, `earned_points`, `points`,
  `explanation`, `user_answer_options`, `correct_answer_options`, `ai_feedback`,
  `grading_status`. See `08_essay_ai_grading.md` (the existing `GET /session/{sid}/answers`
  contract).
- The two hAITU review endpoints canonicalize the body param to **`attempt_id`** (= `exam_sessions.id`,
  i.e. the same value as the path `session_id`) — see `11_haitu_ai_layer.md` §8:
  - `POST /api/haitu/pattern-analysis` — body `{attempt_id}` → `{analysis}`; called once on page
    load to render the opening message.
  - `POST /api/haitu/exam-review-chat` — body `{attempt_id, message, history}` → `{response}`;
    called for each follow-up.

**Business rules (renumbered from the vision 015–018 to avoid collision with the doubt rules
above):**
- BR-STU-019: Only `completed` or `failed` `exam_sessions` can be reviewed. Ongoing / pending /
  `grading_pending` sessions cannot be reviewed (the hAITU endpoints return 403/400 in those
  states — see `11_haitu_ai_layer.md` §8).
- BR-STU-020: All wrong and skipped questions are pre-expanded on load. Correct questions are
  collapsed.
- BR-STU-021: The hAITU pattern-analysis message is generated once on load and cached per
  `attempt_id` (in-memory per worker, v1 limitation — see `11_haitu_ai_layer.md` §8).
- BR-STU-022: For paragraph questions, the passage body is included in the hAITU context when
  generating explanations for embedded questions.

---

## S-profile — Student Profile

- Display name, email (read-only, from IdP).
- **Parent Link Code** section:
  - Shows the student's current link code (`parent_link_codes.code`).
  - "Generate new code" button → `POST /api/student/parent-link-codes` (invalidates previous code).
  - Copy-to-clipboard button.
  - Instructions: "Share this code with your parent to give them access to your Home Study."
- **Linked Parents** section:
  - List of active `parent_child_links` for this student: parent display name, linked date.
  - "Remove" button → `DELETE /api/student/parent-links/:link_id` (sets `revoked_at`).

**Business rules:**
- BR-STU-011: A student may have multiple linked parents (e.g., both parents link separately).
- BR-STU-012: Revoking a link removes the parent's access to the student's exam results and removes the student's access to that parent's Home Study content immediately.

---

## S08 — Doubt Inbox

A student's list of their persisted hAITU doubt threads. Reached via the "My Doubts" nav link
(visible only for `X-Current-Role: student`).

- Renders one row per doubt: title, topic, status chip (`new` / `ai_answered` / `escalated` /
  `answered` / `resolved`), and last-activity timestamp. Each row links to `/doubts/{doubt_id}`
  (S09).
- Status chip colour: `new`/`ai_answered` neutral, `escalated` amber, `answered` green,
  `resolved`/`auto_closed` grey.
- Sorted by last activity (most recent first).
- Empty state: a friendly "No doubts yet — ask hAITU a question from any topic" message with a
  link back to the content navigator (S-nav).
- Data: `GET /api/students/me/doubts` (CSRF not required on GET; `X-Current-Role: student`).

**Business rules:**
- BR-STU-015: A student sees only their own doubts — the backend filters by
  `doubts.student_sub = user.sub`; another student's doubt_id → 404 on the thread endpoint.

---

## S09 — Doubt Thread

A single doubt thread rendered as a chat: student questions on the right, `ai`/`teacher`/
`system` messages on the left, in chronological order. The bubble layout reuses the
`HaituDoubtPanel` pattern from the topic page.

- Header: doubt title + topic name + status chip + a back link to `/doubts`.
- Message list: each message is a chat bubble tagged by `sender_type`:
  - `student` → right-aligned, blue/green accent by source (platform blue `#185FA5`,
    Home Study green `#1D9E75`).
  - `ai` → left-aligned, neutral surface with a hAITU label.
  - `teacher` → left-aligned, distinct teacher styling.
  - `system` → centred, muted note (e.g. "Escalated to a teacher — you'll be notified when
    they reply").
- Follow-up composer: a textarea + "Send" button. Submit calls
  `POST /api/students/me/doubts/{doubt_id}/messages`; the returned updated thread is rendered
  with the new `student` bubble appended last.
- Escalation CTA: a "Request teacher help" button, visible only when
  `status IN ('new','ai_answered')`. On success it sets the status chip to `escalated`,
  appends a `system` note "Escalated to a teacher — you'll be notified when they reply", and
  hides the button. (The button targets `POST /api/doubts/{doubt_id}/escalate` — documented in
  `04_teacher_tutor.md`; the hAITU panel's escalation button is enabled by the same flow.)
- Data: `GET /api/students/me/doubts/{doubt_id}` (thread with messages).

**Business rules:**
- BR-STU-016: A student can only open their own doubt thread —
  `doubt.student_sub == user.sub` else 404.
- BR-STU-017: Follow-ups append a `student` message and return the updated thread; the
  composer is disabled while a request is in flight.
- BR-STU-018: Escalation is one-way from the student side — once `escalated` or `answered`, the
  "Request teacher help" CTA is hidden.

> **Persistence link from the hAITU panel:** after a hAITU topic-doubt reply streams, the
> panel receives a `doubt_id` SSE event (see `11_haitu_ai_layer.md` §2) and shows a "View
> thread" link to `/doubts/{doubt_id}`. Re-opening the panel for a topic with an existing open
> doubt pre-loads the persisted thread via `GET /api/students/me/doubts/{doubt_id}` so history
> is continuous (not client-side-only).

---

## API Endpoints (student role)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/student/dashboard` | Platform + Home Study top-level nodes for dashboard cards |
| `GET` | `/api/student/nodes` | Node tree for a given `owner_type` and `owner_id` |
| `GET` | `/api/student/nodes/:node_id/topics` | Topics for a leaf node (live only) |
| `GET` | `/api/student/topics/:topic_id/content` | Topic content item(s) |
| `POST` | `/api/student/exam-sessions` | Create a new exam session |
| `GET` | `/api/student/exam-sessions/:session_id` | Get session questions |
| `POST` | `/api/student/exam-sessions/:session_id/submit` | Submit answers |
| `GET` | `/api/student/exam-sessions/:session_id/results` | Get results after submission (includes `grading_status` per essay question) |
| `GET` | `/api/exam-sessions/session/{session_id}/answers` | Live per-question review payload for S05 (own session only) |
| `POST` | `/api/haitu/pattern-analysis` | Pre-computed mistake-pattern opening message for S05; body `{attempt_id}`; `student` + CSRF |
| `POST` | `/api/haitu/exam-review-chat` | Per-question/follow-up hAITU explanation in S05; body `{attempt_id, message, history}`; `student` + CSRF |
| `POST` | `/api/exam-sessions/session/{session_id}/questions/{question_id}/dispute` | Dispute an AI essay grade (`auto_release` mode; CSRF required) |
| `GET` | `/api/student/parent-link-codes` | Get current link code |
| `POST` | `/api/student/parent-link-codes` | Generate new link code |
| `GET` | `/api/student/parent-links` | List active parent links |
| `DELETE` | `/api/student/parent-links/:link_id` | Revoke a parent link |
| `GET` | `/api/students/me/doubts` | List the student's doubt threads (S08); `X-Current-Role: student` |
| `GET` | `/api/students/me/doubts/:doubt_id` | Get a doubt thread with messages (S09); 404 if not owned by the student |
| `POST` | `/api/students/me/doubts/:doubt_id/messages` | Append a student follow-up to a doubt thread (CSRF + `X-Current-Role: student` + ownership) |
