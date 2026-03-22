# hAIsir — Teacher / Tutor Specification
> Version 1.1 | Updated to reflect actual baseline from `haisir_current.md`.
> The `instructor` role already exists. Existing routes `/add-assessment` and `/add-exam` remain unchanged.
> The `tutor` role is new. New teacher routes are listed below.
> → Depends on: `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`
> → Prototype: `haisir_teacher_flow.html`

---

## 0. Existing Routes (do not replace — extend or leave as-is)

| Route | Status | Action |
|---|---|---|
| `/add-assessment` | ✅ Existing | **Rewrite** to use `exam_templates` with `purpose = 'quiz'`. Class-scoped assignment flow (assigning to a class with a due date) is a new modal on the class dashboard. |
| `/add-exam` | ✅ Existing | Leave as-is. Already supports `paragraph_questions`. New exam builder features (if any) extend this page. |
| `/manage-categories` | ✅ Existing | Will be superseded by `/institution/curriculum` for institution-scoped work, but remains for backward compatibility. |

**New routes to add:**

| Route | Purpose |
|---|---|
| `/teacher` | Teacher home dashboard |
| `/teacher/class/:class_id` | Class dashboard |
| `/teacher/student/:student_sub` | Student detail |
| `/teacher/doubts` | Student doubt inbox |
| `/teacher/doubts/:doubt_id` | Doubt reply thread |
| `/teacher/exam-results/:assignment_id` | Post-exam class results |
| `/teacher/curriculum/:context_id` | Curriculum builder (tutor namespace) |
| `/teacher/profile` | Teacher/tutor profile |

---

## 1. Persona Summary

A single user can hold both `instructor` and `tutor` roles. The workspace adapts based on the active role.

**Instructor role** (`instructor`):
- Topbar colour: `#0A3D2B` (dark teal)
- Teaches at an institution, assigned to classes by institution admin
- Cannot modify curriculum structure (institution admin owns this)
- Can add supplemental content to class topics
- Answers doubts from students in assigned classes

**Tutor role** (`tutor`):
- Topbar colour: `#3C1F6E` (deep purple, shown as teal in combined view)
- Operates independently — owns their curriculum fully
- Publishes courses; students subscribe and unsubscribe on their own
- Can send invites to students (student chooses to accept)
- Marketplace listing is immediate (no approval gate) — admin can suspend post-hoc
- Answers doubts from subscribed students
- Student roster is read-only — tutor cannot remove students

When both roles are active, the home screen shows both contexts. The teacher home topbar uses `#0A3D2B`. Role context within the home is visual (section labels and card borders distinguish institutional from open).

**Cannot:** See other teachers' students, modify institution-level settings, access institution analytics dashboard.

---

## 2. Screen Inventory

| # | Screen ID | Name | Entry point |
|---|---|---|---|
| T01 | `teacher-home` | Teacher home | Login / app root (instructor role) |
| T02 | `class-dashboard` | Class dashboard | Home → class card |
| T03 | `student-detail` | Student detail | Class dashboard → student row, or from doubt inbox |
| T04 | `curriculum-builder` | Curriculum builder | Home → "Build curriculum" / class dashboard → "Add content" |
| T05 | `teacher-profile` | Teacher / tutor profile | Topbar → "My profile" |
| T06 | `doubt-inbox` | Student doubt inbox | Topbar → "Doubts" button |
| T07 | `doubt-reply` | Doubt reply thread | Doubt inbox → doubt row |
| T08 | `exam-results` | Class exam results | Home alert → "View results" / class dashboard → assignment |

---

## 3. Screen Specifications

---

### T01 — Teacher Home

**Purpose:** Overview of all teaching contexts — institutional classes and open tutoring students — plus actionable alerts.

**Alert cards (injected at top on render, if applicable):**
- Amber alert: "{N} student doubt(s) waiting for your reply" → links to T06.
- Green alert: "{Quiz/Exam name} results are ready" → links to T08.
- Red alert: "{Student name} is at risk" (triggered by STUDENT_AT_RISK notification) → links to T03.

**Sections:**
- **My classes (institutional):** One card per assigned class. Card shows: institution name, class name, subject, average progress, at-risk count, active assignments, "View class →" and "Add content" buttons. Dashed "+ Join institution" card at end.
- **Open tutoring:** One card per published course. Card shows: subscriber count, subject, at-risk count, "View course →" button. Dashed "+ New open course" card at end.

**Topbar:** "Doubts" button with amber badge showing count of new (unanswered) doubts.

**Actions:**
- Click class card or "View class →" → T02 Class Dashboard.
- "Add content" on class card → T04 Curriculum Builder for that class.
- Click open tutoring card → T02 (tutor context).
- "My profile" → T05.
- "Doubts" → T06.

**Business rules:**
- **BR-TCH-001:** Shows only classes where `instructor_idp_sub = self` and `status = 'active'`.
- **BR-TCH-002:** Doubt badge count = `doubts` where `escalated_to = self` and `status = 'pending'`.
- **BR-TCH-003:** Average progress per class = mean of `enrollment_topics.mastery_score` across all students in that class, for all topics in that class.
- **BR-TCH-004:** At-risk count = students in class where `enrollment_topics.mastery_score < 50` across 3 or more topics (after at least one attempt). This matches the institution-level definition (BR-INST-001).

**API calls:**
```
GET /api/teachers/me/home
→ Auth: instructor OR tutor
→ Returns: {
    instructor_contexts: [{
      class_id, class_name, organization_name, subject, grade,
      student_count, avg_progress, at_risk_count,
      active_assignments: [{name, due_at, submitted_count, total_count}]
    }],
    tutor_contexts: [{
      enrollment_count, subject, at_risk_count
    }],
    pending_doubts: int,
    recent_exam_result: {assessment_title, class_id, submitted_at} | null
  }
```

---

### T02 — Class Dashboard

**Purpose:** Per-class view showing student roster, topic heatmap, and assignments.

**Works for both instructor (structured) and tutor (open) contexts.** Layout adapts:
- Instructor: shows class name, institution, subject, grade. Student roster with assignment column. Topic performance heatmap.
- Tutor: shows course label. Read-only subscriber list with current topic and progress columns (no heatmap — tutor curriculum is per-course not per-class). Tutor cannot remove subscribers.

**Stat row:**
- Students, Class average (instructor) / Students on track (tutor), Needs attention, At-risk / Sessions this week.

**Student roster table:**
- Columns: Student name, Progress bar + %, Weak topics badge, Last active, Action ("View →").
- Rows sorted by progress ascending (at-risk first).

**Topic heatmap (instructor only):**
- Per topic: topic name, horizontal bar, class average %. Colour: green ≥75%, amber 50–74%, red <50%.
- "Add content" button → T04.

**Assignments panel (instructor only):**
- List of assigned quizzes/exams: name, type badge (Quiz/Exam), due date, submission count vs total, average score (if completed).
- "+ Assign quiz/exam" button → opens assignment modal.

**Actions:**
- Click student row or "View →" → T03 Student Detail.
- "+ Assign quiz/exam" → modal with template picker (filtered by purpose), due date, optional note.
- Click topic in heatmap (future) → topic detail.
- "Add content" → T04.

**Business rules:**
- **BR-TCH-005:** Last active = most recent `enrollment_topics.last_studied_at` across all topics for that student in this class.
- **BR-TCH-006:** Heatmap shows only topics assigned to this class's curriculum (`class.board_adoption_id` or custom topics).
- **BR-TCH-007:** Assignment modal template picker shows `exam_templates` available for the class's subject/grade, with a purpose filter (Quiz / Exam / All).

**API calls:**
```
GET /api/classes/{class_id}/dashboard
→ Auth: instructor (own class only)
→ Returns: {
    class: {id, name, organization, subject, grade, student_count},
    students: [{
      idp_sub, name, initials, color, progress,
      weak_topics: int, last_active_at, status
    }],
    topic_perf: [{topic_id, title, class_avg}],
    assignments: [{id, title, due_at, submitted: int, total: int, avg_score?}]
  }

POST /api/classes/{class_id}/assignments
→ Auth: instructor (own class only)
→ Body: {exam_template_id: uuid, due_at: datetime, note?: str}
→ Returns: {assignment_id}
→ Side effect: creates notification ASSIGNMENT_DUE_SOON for all enrolled students
```

---

### T03 — Student Detail

**Purpose:** Deep-dive on a single student — progress per topic, doubt history, teacher notes.

**Works for both instructor and tutor contexts.** Layout:
- Profile card: student name + avatar, class/context, overall % + weak topic count.
- Topic performance table: topic name, score, status badge, last attempted.
- Session/doubt history (tutor only): dated entries with teacher notes per session — but **no live sessions** in scope. This section shows async interaction history (doubts raised, content viewed).
- Private notes card: teacher-only textarea, "Save" button. Notes stored in `tutor_student_relationships.teacher_notes`.
- hAITU sidebar: AI analysis of student ("Based on their performance across 4 topics…") + 3 one-click action buttons: "Plan next session content", "Generate practice questions for weak topics", "Generate progress report".

**Actions:**
- hAITU sidebar "Plan next session content" → calls hAITU API, shows generated content plan in sidebar.
- "Generate practice questions" → calls hAITU API, shows question suggestions.
- "Generate progress report" → calls hAITU API, returns formatted report text (copy-able).
- "Save notes" → saves teacher notes.

**Business rules:**
- **BR-TCH-008:** Topic performance table shows all topics the student has started or been assigned in this context, with their individual mastery scores.
- **BR-TCH-009:** Teacher notes are private — only the teacher/tutor who wrote them can read them. Not visible to student, parent, or institution admin.
- **BR-TCH-010:** The hAITU analysis is generated fresh on each page load. It analyses: weak topics, recent attempt trends, doubt frequency.
- **BR-TCH-011:** The tutor student detail view (T03) is always opened with an enrollment context. When a student appears on the tutor's roster, each enrollment is shown as a separate row. The `enrollment_id` from that row is passed to T03 and used to scope all API calls, including `teacher_notes` lookup. A student with two active enrollments with the same tutor appears as two separate rows in the roster.

**API calls:**
```
GET /api/classes/{class_id}/students/{student_idp_sub}
→ Auth: instructor (own class only) OR institution_admin (own org only; teacher_notes excluded per BR-INST-015)
→ Returns: {
    student: {idp_sub, name, initials, grade},
    overall_progress: float,
    weak_topic_count: int,
    topic_perf: [{topic_id, title, mastery_score, status, last_attempted_at}],
    doubt_history: [{doubt_id, topic_title, status, created_at, message_count}]
  }

GET /api/tutors/me/students/{student_idp_sub}?enrollment_id={id}
→ Auth: tutor
→ Returns: same shape + teacher_notes field
→ Errors: 404 if enrollment_id does not belong to this tutor–student pair

PATCH /api/tutors/me/students/{student_idp_sub}/notes?enrollment_id={id}
→ Auth: tutor
→ Body: {notes: str}
→ Returns: {updated_at}
→ Errors: 404 if enrollment_id does not belong to this tutor–student pair

POST /api/haitu/teacher-tools
→ Auth: instructor OR tutor
→ Body: {
    tool: "plan_session" | "generate_questions" | "progress_report",
    student_idp_sub: str,
    context: {weak_topics, recent_scores, enrollment_label}
  }
→ Returns: {output: str}
→ See: `08_haitu_ai_layer.md #teacher-tools`
```

---

### T04 — Curriculum Builder

**Purpose:** Build and manage curriculum — topics, sub-topics, and content uploads.

**Layout:**
- Left tree: hierarchical topic tree (chapter → sub-topic level). Click to select. "+ Add chapter" button at bottom.
- Right detail panel: selected topic's sub-topic pills. Below: content items list (type icon, title, upload date). Upload zone at bottom. "Students on this topic" list (tutor only).

**Instructor vs Tutor distinction:**
- **Instructor:** Blue notice bar: "Core structure owned by institution admin. You can add supplemental content only." Tree is read-only (cannot add/rename chapters). Upload zone available. Cannot delete platform/institution-owned content items.
- **Tutor:** Full control. Can add chapters, rename, reorder, delete. Can upload any content. Sees "Students on this topic" list.

**Content item types:** PDF (file upload), Video link (URL input), Text notes (rich text), Question bank (future).

**Quiz and exam authoring:** The `/add-exam` route is the unified authoring tool for both quizzes (`purpose = 'quiz'`) and exams (`purpose = 'exam'`), including `paragraph_questions` (reading passages with embedded question IDs). The curriculum builder does not duplicate this — it links to the existing authoring tool. "Add questions" actions in the curriculum builder open the `/add-exam` flow scoped to this topic.

**Actions:**
- Click tree node → loads content for that topic in right panel.
- "+ Add chapter" (tutor only) → adds new chapter node.
- "Upload content" → opens upload modal (file picker for PDF, URL for video, textarea for notes).
- Click content item → preview (PDF viewer stub / video link).
- Delete content item (tutor only) → confirms, removes.
- "Publish" button (tutor only) → sets topic status to `live`.

**Business rules:**
- **BR-TCH-025:** Instructors can only add content items to topics they are assigned to via their class. They cannot add content to topics outside their class curriculum.
- **BR-TCH-012:** Tutors can only modify topics where `owner_type = 'tutor'` and `owner_id = self`.
- **BR-TCH-013:** A topic with `status = 'draft'` is not visible to students.
- **BR-TCH-014:** Uploaded PDFs are stored server-side. File size limit: 20MB. Accepted types: PDF only.
- **BR-TCH-015:** Video links must be valid URLs. No file upload for video — link only.

**API calls:**
```
GET /api/curriculum/{context_id}/tree
→ Auth: instructor OR tutor
→ Returns: [{id, title, level, parent_id, order_index, status, children: [...]}]

POST /api/topics
→ Auth: tutor (own curriculum only)
→ Body: {parent_id?: uuid, title: str, level: str, owner_id: uuid}
→ Returns: {topic_id}

POST /api/topics/{topic_id}/content
→ Auth: instructor OR tutor
→ Body: multipart/form-data {type, title, file? | url? | body?}
→ Returns: {content_item_id}

DELETE /api/content/{content_item_id}
→ Auth: tutor (own content only)
→ Returns: 204
```

---

### T05 — Teacher / Tutor Profile

**Purpose:** Edit professional profile and manage tutor marketplace listing.

**Sections:**
- Bio and details: name, subjects, grades, years of experience, bio text (textarea).
- Availability: free text field (e.g. "Mon–Fri 4–8pm").
- Marketplace toggle: "List me in tutor marketplace" checkbox. If off, profile is not discoverable by students.
- Stats (read-only): active students, topics built, average student progress, content rating (aggregate of `topic_reviews` across all owned topics — shows "No reviews yet" if `review_count = 0`).

**Business rules:**
- **BR-TCH-016:** Toggling marketplace listing to `on` immediately makes the profile public (`marketplace_listed = true`). No admin approval gate — the marketplace uses a federated model with post-hoc moderation. Platform Admin can suspend a tutor at any time by setting `marketplace_suspended = true`, which immediately hides them from student discovery regardless of `marketplace_listed`. If suspended, show: "Your marketplace listing has been suspended by the platform admin. Contact support for details."
- **BR-TCH-017:** Toggling listing off immediately hides the profile from the marketplace (`marketplace_listed = false`).

**API calls:**
```
GET /api/teachers/me/profile
→ Auth: instructor OR tutor
→ Returns: {idp_sub, first_name, last_name, teacher_type, subjects, grades, years_experience, bio, availability, marketplace_listed, marketplace_suspended}

PATCH /api/teachers/me/profile
→ Auth: instructor OR tutor
→ Body: {first_name?, last_name?, bio?, subjects?, grades?, availability?, marketplace_listed?}
→ Returns: updated profile
```

---

### T06 — Student Doubt Inbox

**Purpose:** All doubts escalated to this teacher/tutor, grouped by status.

**Stat row:** Awaiting your reply, Replied, Total this week.

**Doubt sections:**
- "Awaiting your reply" (status = `pending`) — amber left border.
- "Replied" (status = `answered`) — green left border.

**Per doubt row:**
- Student avatar + name, topic name, course label.
- First student message (truncated).
- Last message preview with sender prefix.
- Message count, time.
- Status badge.
- "View" button → T07.

**Info note:** "Doubts are escalated here when hAITU cannot fully resolve a student's question. Your reply will be sent back to the student in their doubt thread."

**Actions:**
- Click doubt row or "View" → T07 Doubt Reply Thread.

**Business rules:**
- **BR-TCH-018:** Shows all doubts where `escalated_to = self` and `status IN ('pending', 'answered')`. Resolved doubts are shown in "Replied" section for 7 days after resolution, then archived.
- **BR-TCH-019:** "Awaiting your reply" doubts are sorted by `created_at` ascending (oldest first — fairness to students who have waited longest).

**API calls:**
```
GET /api/teachers/me/doubts?status={}
→ Auth: instructor OR tutor
→ Returns: [{
    id, student_name, student_initials, student_color,
    topic_title, course_label, enrollment_type,
    status, created_at, message_count,
    first_student_message: str,
    last_message: {sender_type, body_preview, created_at}
  }]
```

---

### T07 — Doubt Reply Thread

**Purpose:** Full conversation thread for one student doubt. Teacher reads and responds.

**Layout:**
- Context bar: student name, topic, course, time, message count. "View student →" button → T03.
- Message stream: student messages (grey, left), hAITU messages (blue, left), teacher messages (green, right).
- Context note (amber): "hAITU could not fully resolve this. Your explanation will appear in the student's thread."
- Reply area:
  - If `pending` or `answered`: large textarea + "Send reply" + "Send & resolve" buttons.
  - If `resolved` (teacher viewing past thread): "✓ Resolved" message + textarea for additional messages if needed.

**Actions:**
- "Send reply" → adds teacher message, sets `doubt.status = 'answered'`, triggers DOUBT_TEACHER_REPLIED notification to student.
- "Send & resolve" → adds message, sets `doubt.status = 'resolved'`, triggers notification.
- "View student →" → T03 Student Detail.

**Business rules:**
- **BR-DOUBT-011:** Teacher cannot edit or delete their own messages once sent.
- **BR-DOUBT-012:** Sending a reply to a `resolved` doubt re-opens it to `answered`.
- **BR-DOUBT-013:** Teacher reply must not be empty. Minimum 10 characters.

**API calls:**
```
GET /api/doubts/{doubt_id}
→ Auth: instructor OR tutor (escalated_to = self)
→ Returns: full thread (same shape as student GET, includes all messages)

POST /api/doubts/{doubt_id}/messages
→ Auth: instructor OR tutor
→ Body: {body: str, resolve?: bool}
→ Returns: {message_id, created_at}
→ Side effects:
    - Sets doubt.status = 'answered' (or 'resolved' if resolve=true)
    - Creates notification DOUBT_TEACHER_REPLIED for student
    - Creates notification CHILD_DOUBT_REPLIED for linked parents
```

---

### T08 — Class Exam Results

**Purpose:** Post-exam/quiz analysis for teacher after a class completes an assigned quiz or exam.

**Layout:**
- Header (dark teal): template title, type badge (Quiz/Exam), class name, date. Stats: class average %, passed count, below 60% count, total submitted.
- Two-column grid:
  - Left: Per-student score table — name, progress bar, score %, status badge (Good / Review / Struggling), "View" action.
  - Right:
    - Question heatmap: coloured cells per question (green ≥75%, amber 55–74%, red <55% correct across class).
    - hAITU recommendations panel: 3–5 bullet points on what to address next class, generated by hAITU.
    - Weak topics card: topics with high failure rates. "Generate remedial assignment" button.

**Actions:**
- Click student row → T03 Student Detail.
- Click question cell → tooltip showing which students got it wrong (future).
- "Generate remedial assignment" → calls hAITU API to generate a focused assessment on weak topics → opens assignment modal pre-filled.

**Business rules:**
- **BR-TCH-020:** Only accessible for assignments where all enrolled students have submitted, OR due date has passed (whichever comes first).
- **BR-TCH-021:** Question heatmap score = `(students who answered correctly / total submissions) * 100`. Sourced from `exam_session_questions`.
- **BR-TCH-022:** hAITU recommendations are generated once per attempt batch and cached. See `08_haitu_ai_layer.md #exam-analysis`.
- **BR-TCH-023:** Publishing a draft topic (`draft → live`) takes effect immediately — no confirmation modal. The topic becomes visible to enrolled students.
- **BR-TCH-024:** Unpublishing (`live → draft`) is not allowed. To hide a topic, archive it (`live → archived`). Archiving shows a confirmation: "Students will no longer see this topic. This cannot be undone."

**API calls:**
```
GET /api/classes/{class_id}/assignments/{assignment_id}/results
→ Auth: instructor (own class only)
→ Returns: {
    template: {title, purpose, question_count, assigned_at, due_at},
    class: {id, name, student_count},
    summary: {avg_score, passed: int, failed: int, submitted: int},
    student_results: [{
      idp_sub, name, initials, color,
      score, status
    }],
    question_perf: [{question_id, order_index, pct_correct}],
    weak_topics: [str],
    haitu_recommendations: [str]  // cached on first generation
  }
```

---

## 4. Edge Cases

| Scenario | Behaviour |
|---|---|
| Teacher has no assigned classes | Show home with only dashed "join institution" card in instructor section |
| Doubt escalated to teacher who has since been removed from class | Still show in inbox — teacher should respond. Institution admin sees unassigned doubts separately |
| Student sends follow-up on a resolved doubt | Doubt status returns to `pending`, teacher sees it in inbox again |
| Teacher reply textarea is empty | "Send" button disabled; "Send & resolve" button disabled |
| Assignment with no submissions yet | T08 shows "No submissions yet" state. Heatmap empty. Recommendations not generated |
| Tutor with no subscribers | Home shows open tutoring section with dashed card only |
| PDF upload over 20MB | Client-side validation before upload. Error: "File too large — maximum 20MB" |
| Video URL invalid | Server validates URL format. Error: "Please enter a valid URL" |
| Teacher types reply < 10 characters | Show validation: "Reply must be at least 10 characters" |
