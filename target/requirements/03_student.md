# Student Persona

> **Target state scope:** Student experience with platform content and parent Home Study content. Institutions, classes, doubts, hAITU, and notifications are out of scope for this increment.

---

## Screens

| Screen ID | Name | Route |
|---|---|---|
| S-home | Dashboard | `/home` |
| S-nav | Content Navigator | `/courses` |
| S-exam | Exam Taking | `/exam/:session_id` |
| S-results | Exam Results | `/exam/:session_id/results` |
| S-profile | Student Profile | `/profile` |

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
- MCQ options are radio buttons; paragraph questions show a text area.
- "Submit" button — disabled until at least one question answered.
- Confirmation modal before submission.
- On submit: `POST /api/student/exam-sessions/:session_id/submit`.

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

- Score: `X / Y` and percentage.
- Pass / Fail badge (based on `exam_templates.pass_mark`).
- Per-question breakdown: question text, student's answer, correct answer, points awarded.
- "Back to Home Study" or "Back to Platform" CTA (context-aware based on exam source).

**Business rules:**
- BR-STU-009: Results are shown immediately after submission — no teacher review gate in this increment.
- BR-STU-010: Students can re-visit their own results from S-home or via direct URL.

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
| `GET` | `/api/student/exam-sessions/:session_id/results` | Get results after submission |
| `GET` | `/api/student/parent-link-codes` | Get current link code |
| `POST` | `/api/student/parent-link-codes` | Generate new link code |
| `GET` | `/api/student/parent-links` | List active parent links |
| `DELETE` | `/api/student/parent-links/:link_id` | Revoke a parent link |
