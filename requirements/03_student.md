# hAIsir — Student Specification
> Version 1.1 | Updated to reflect actual baseline from `haisir_current.md`.
> The student role (`student`) already exists in Keycloak and the codebase.
> Existing routes `/assess` and `/exam` remain unchanged. New routes extend the student experience.
> → Depends on: `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`
> → Prototype: `haisir_student_flow.html`

---

## 1. Persona Summary

**Role:** `student`
**Topbar colour:** `#0A1F5C` (navy)
**Can:** Study topics, ask hAITU doubts, take assessments, request teacher help, track own progress, browse and enroll in open courses, generate parent link code.
**Cannot:** See other students' data, modify curriculum, access institution-level analytics.

---

## 2. Screen Inventory

**Existing routes (do not replace — extend or leave as-is):**

| Route | Status | Action |
|---|---|---|
| `/assess` | ✅ Existing | Leave as-is — student quiz experience unchanged |
| `/exam` | ✅ Existing | Leave as-is — student exam browsing unchanged |
| `/home` | ✅ Existing (single-course view) | Extend — add unified dashboard as default view |

**New screens (new routes):**

| # | Screen ID | Route | Name | Entry point |
|---|---|---|---|---|
| S01 | `home` | `/home/dashboard` | Home dashboard | Login / app root (replaces single-course as default) |
| S02 | `enroll-institution` | `/home/join-institution` | Join institution | Home → "+ Join institution" |
| S03 | `browse-open` | `/home/browse` | Browse open courses | Home → "+ Open course" |
| S04 | `topic-navigator` | `/home/topics/:enrollment_id` | Topic navigator | Home → enrollment card |
| S05 | `exam-review` | `/home/review/:attempt_id` | Post-exam AI review | Home → "Review exam" |
| S06 | `tutor-discovery` | `/tutors` | Find a tutor | Home → "Browse tutors" |
| S07 | `tutor-profile` | `/tutors/:keycloak_sub` | Tutor profile | Tutor discovery → card |
| S08 | `doubt-inbox` | `/doubts` | My doubts | Topbar → "Doubts" |
| S09 | `doubt-thread` | `/doubts/:doubt_id` | Doubt thread | Doubt inbox → row |
| S10 | `profile` | `/profile` | Student profile | Topbar → "Profile" |

---

## 3. Screen Specifications

---

### S01 — Home Dashboard

**Purpose:** Central hub showing all enrollments, due items, and quick actions.

**States:**
- **Returning student (has enrollments):** Shows continue card, due items strip, enrollment cards grid, find-tutor CTA, review-exam CTA.
- **New student (no enrollments):** Shows empty state with two CTA cards — "Join institution" and "Start open learning".

**Data shown:**
- Continue card: last-studied topic title, enrollment name, "Resume →" button.
- Due items strip: all pending assignments across all enrollments with source label and due badge (Tomorrow / Upcoming). Sorted by due date ascending.
- Enrollment cards: one card per active enrollment. Each card shows: enrollment name, source (institution name or tutor name), track pill (School / Open), progress bar (%), weak topic alerts, due item alerts, next session info (if tutor), last studied date.
- Institutions section and Open courses section are separately grouped.
- Find-tutor CTA card (purple) at bottom.
- Review-exam CTA card (blue) at bottom — links to most recent completed assessment.

**Actions:**
- Click enrollment card → S04 Topic Navigator scoped to that enrollment.
- "Browse topics" button on card → S04.
- "+ Join institution" button → S02.
- "+ Open course" button → S03.
- "Browse tutors" → S06.
- "Review exam" → S05.
- Topbar "Doubts" button → S08. Shows unread count badge if pending/answered doubts exist.
- Topbar "Profile" → S10.

**Business rules:**
- **BR-STU-001:** Home renders all enrollments where `status = 'active'`.
- **BR-STU-002:** Due items show all `class_assignments` where `due_at` is within the next 7 days and student has not yet submitted.
- **BR-STU-003:** "Continue where you left off" uses the enrollment with the most recent `last_active_at`.
- **BR-STU-004:** A topic is flagged as weak on the enrollment card if `enrollment_topics.status = 'weak'`. Count shown as "X weak topics".
- **BR-STU-005:** The Doubts badge count = `doubts` where `student_keycloak_sub = self` and `status IN ('pending', 'answered')`.

**API calls:**
```
GET /api/students/me/home
→ Auth: student
→ Returns: {
    enrollments: [{id, type, label, sublabel, progress, weak_count, due_items, last_topic, session_info}],
    recent_attempt: {assessment_id, title, score, submitted_at} | null,
    unread_doubts: int
  }
```

---

### S02 — Join Institution

**Purpose:** Enroll in a school or institution via invite code or name search.

**Data shown:**
- Invite code input field.
- Validation message (found / not found) on code input.
- Institution search results (name, board, grade) when searching by name.
- Selected institution highlighted with checkmark.

**Actions:**
- Type invite code → live validation on each keystroke (debounced 500ms).
- "Apply" button → validates code, shows institution details.
- Search by name → shows matching institutions from catalog.
- Click institution in results → selects it.
- "Enroll" button → creates enrollment → navigates to S04 for that enrollment.

**Business rules:**
- **BR-STU-006:** Invite codes are case-insensitive. Normalise to uppercase before validation.
- **BR-STU-007:** A student cannot join the same class twice. If they attempt to use an invite code for a class they're already in, show error: "You are already enrolled in this class."
- **BR-STU-008:** Institution search shows only `active` organizations.

**API calls:**
```
GET /api/classes/by-invite-code/{code}
→ Auth: student
→ Returns: {class_id, class_name, organization_name, board, grade, instructor_name} | 404

GET /api/organizations/search?q={query}
→ Auth: student
→ Returns: [{id, name, board, city, grade_range}]

POST /api/enrollments
→ Auth: student
→ Body: {type: "structured", class_id: uuid} | {type: "structured", invite_code: string}
→ Returns: {enrollment_id}
→ Errors: 409 already enrolled, 404 class not found
```

---

### S03 — Browse Open Courses

**Purpose:** Browse and add open courses from tutors or self-directed catalog.

**Data shown:**
- Left sidebar: subject filter chips. Active chip highlighted purple.
- Search bar across top.
- Results grouped by tutor (tutor name as section header). Each course row: icon, title, subject, tutor pill, "+ Add" / "✓ Added" toggle button.
- Cart badge on "Add to my courses" button showing count of courses in cart.

**Actions:**
- Click subject chip → filters results.
- Type in search → filters by course title and tutor name.
- "+ Add" on course → adds to cart (local state, not yet enrolled).
- "Add to my courses" button → creates enrollments for all carted courses, grouped by tutor → navigates home.

**Business rules:**
- **BR-STU-009:** Cart is local state only — not persisted. If user navigates away, cart is cleared.
- **BR-STU-010:** Adding courses from the same tutor creates one enrollment for that tutor and maps all courses to it. Adding self-directed courses creates a single self-directed enrollment.
- **BR-STU-011:** Open course catalog shows only `status = 'live'` topics where `owner_type IN ('tutor', 'platform')`.

**API calls:**
```
GET /api/open-catalog?subject={subject}&q={query}
→ Auth: student
→ Returns: [{topic_id, title, subject, tutor_keycloak_sub, tutor_name, topic_count, icon}]

POST /api/enrollments/open/bulk
→ Auth: student
→ Body: {items: [{topic_id, tutor_keycloak_sub | null}]}
→ Returns: {enrollment_ids: [uuid]}
```

---

### S04 — Topic Navigator

**Purpose:** Browse and study all topics within one enrollment context.

**Layout:**
- Enrollment tab strip at top — one tab per active enrollment. Active tab highlighted blue (structured) or purple (open). "+ Add" tab opens S03.
- Context bar below strip — shows board, grade, subject for structured; tutor name for open.
- Collapsible left sidebar with filter chips: Status (Needs attention / In progress / Completed / Not started) and Subject (structured only).
- Active filter pills above results (removable with ×).
- Search bar.
- Result count label.
- Topics list, grouped by status (Needs attention first, then In progress, Completed, Not started). Locked topics shown at bottom in greyed-out state.

**Per topic row:**
- Subject icon, topic title, breadcrumb (board · grade · subject · course).
- Source tag (institution name or tutor name).
- Status badge (Needs attention / In progress / Completed / Not started) with mastery score.
- "Ask hAITU" button.

**hAITU chat panel (slide-in, scoped to topic):**
- Opens from the right when "Ask hAITU" is clicked on any topic row.
- Header shows topic title and "Scoped to this topic" subtitle.
- Student types a question → hAITU responds.
- After hAITU has sent at least one response, a "Still need help? Request teacher help →" button appears at the bottom of the panel.
- Clicking "Request teacher help →" creates a doubt record and navigates to S09 thread.
- The panel can be dismissed with a close button (×) without creating a doubt.

**Content rating prompt:**
- When a topic's `enrollment_topics.status` transitions to `completed` or `weak`, a rating prompt appears inline in the topic row (below the status badge): "Rate this topic's content: ★ ★ ★ ★ ★". Selecting a star immediately submits the rating (no confirm step). An optional comment field appears after submission.
- Once rated, the prompt is replaced with the student's submitted rating (read-only).

**Actions:**
- Click enrollment tab → switches active enrollment, re-renders topics list.
- Click filter chip → adds/removes filter, updates pills and results.
- Click × on pill → removes filter.
- Type in search → filters topics live.
- ☰ toggle → collapses/expands sidebar.
- "Ask hAITU" on a topic row → opens hAITU chat panel scoped to that topic.
- "Request teacher help →" inside the hAITU panel (shown after first hAITU response) → creates a doubt and navigates to S09 thread.
- Click topic row → opens topic study view (out of scope for this version — stub with toast).

**Business rules:**
- **BR-STU-012:** Locked topics (`locked = true`) are shown but not clickable. They show a lock icon and "Locked — next grade" label. `locked` is a derived field in the API response — not a stored column. The backend computes it by traversing the topic's `course_path_node` ancestry to find the nearest ancestor with `node_type = 'grade'`, then comparing that grade to the student's `student_profiles.grade`. If the topic's grade is higher than the student's grade, `locked = true`.
- **BR-STU-013:** Switching enrollment tabs resets filters and search.
- **BR-STU-014:** There is no "Ask teacher" button on topic rows. Teacher escalation is only available from within the hAITU chat panel, after hAITU has sent at least one response. The "Request teacher help →" button appears at the bottom of the panel once `escalation_suggested = true` is returned by `POST /api/haitu/topic-doubt`, or after the student has received at least one hAITU response (the button is always shown after the first exchange, regardless of escalation signal). Clicking it creates a `doubt` record with `haitu_attempted = true` and navigates to S09.

**API calls:**
```
GET /api/enrollments/{enrollment_id}/topics?status={}&subject={}&q={}
→ Auth: student
→ Returns: [{topic_id, title, subject, course, status, mastery_score, locked, source_label}]

GET /api/students/me/enrollments
→ Auth: student
→ Returns: [{id, type, label, sublabel, icon, board, grade, tutor_name}]

POST /api/haitu/topic-doubt
→ Auth: student
→ Body: {topic_id, enrollment_id, message, history: [{role, content}]}
→ Returns: {response: str, escalation_suggested: bool}
→ See: `08_haitu_ai_layer.md #topic-doubt`
→ Note: used by the hAITU chat panel in the topic navigator. After the first response,
  the frontend always shows "Request teacher help →" regardless of escalation_suggested.

POST /api/doubts
→ Auth: student
→ Body: {topic_id, enrollment_id, initial_message}
→ Returns: {doubt_id}
→ Note: called when student clicks "Request teacher help →" inside the hAITU panel.
  Server sets haitu_attempted = true automatically on this path.

POST /api/topics/{topic_id}/reviews
→ Auth: student
→ Body: {enrollment_id, rating: int (1–5), comment?: str}
→ Returns: {review_id, created_at}
→ Errors: 409 already reviewed, 403 topic not completed or weak for this student
```

---

### S05 — Post-Exam AI Review

**Purpose:** Review a completed exam question by question with hAITU explanations for wrong answers.

**Note on question types:** The existing exam system supports two question types — regular `questions` (MCQ, true/false, short answer) and `paragraph_questions` (reading passages with multiple embedded questions). The review screen must handle both. Paragraph questions display the passage body above the embedded questions; each embedded question is reviewed individually within the passage context.

**Layout:**
- Score summary bar at top: score %, correct count, wrong count, skipped count, total.
- Left panel: scrollable list of question cards.
- Right panel: hAITU chat scoped to this exam.

**Per regular question card:**
- Question number badge (green = correct, red = wrong, grey = skipped).
- Question text.
- Result label (✓ Correct / ✗ Wrong / — Skipped).
- Collapsed by default. Click header to expand.
- Expanded state shows: all answer options with correct (green ✓) and student's wrong answer (red ✗) highlighted. hAITU explanation for wrong/skipped questions.
- "Ask hAITU to explain this" button for wrong/skipped questions without a pre-loaded explanation.

**Per paragraph question card:**
- Passage title and body shown at top of the card group.
- Each embedded question rendered as a sub-card within the passage card.
- Sub-cards follow the same correct/wrong/skipped rendering as regular questions.
- hAITU explanations are per embedded question, with passage context included in the prompt.

**hAITU chat panel:**
- Pre-loaded with pattern analysis message on load: identifies the most common mistake pattern across all wrong answers.
- Student can type follow-up questions — responses are generated by hAITU API.
- Chat is scoped to this attempt — hAITU has access to all question, answer and explanation data for this attempt.

**Business rules:**
- **BR-STU-015:** Only `submitted` or `reviewed` `exam_session` records can be reviewed. `in_progress` sessions cannot be reviewed.
- **BR-STU-016:** All wrong and skipped questions are pre-expanded on load. Correct questions are collapsed.
- **BR-STU-017:** The hAITU pattern analysis message is generated once on load and cached client-side for the session.
- **BR-STU-018:** For paragraph questions, the passage body is included in the hAITU context when generating explanations for embedded questions.

**API calls:**
```
GET /api/exam-sessions/{session_id}/review
→ Auth: student (own session only)
→ Returns: {
    session: {id, exam_title, score, correct, wrong, skipped, total},
    items: [
      {
        type: "question",
        id, order_index, body, options, correct_answer,
        student_answer, is_correct, explanation
      } | {
        type: "paragraph",
        id, passage_body,
        questions: [{
          id, order_index, body, options, correct_answer,
          student_answer, is_correct, explanation
        }]
      }
    ]
  }

POST /api/haitu/exam-review-chat
→ Auth: student
→ Body: {session_id: uuid, message: str, history: [{role, content}]}
→ Returns: {response: str}
→ See: `08_haitu_ai_layer.md #exam-review-chat`
```

---

### S06 — Tutor Discovery

**Purpose:** Browse tutors by subject and find one to enroll with.

**Layout:**
- Left sidebar: Subject filter, Grade filter, Availability filter.
- Search bar.
- Tutor cards in main area: avatar, name, subjects, topic tags, rating, student count, rate, availability, "View profile" button.

**Actions:**
- Click subject chip → filters tutor list.
- Search → filters by name, subjects, topics.
- Click tutor card or "View profile" → S07 Tutor Profile.

**Business rules:**
- **BR-STU-019:** Only tutors where `marketplace_listed = true` and `marketplace_suspended = false` are shown.
- **BR-STU-020:** Tutors are sorted by rating descending by default.

**API calls:**
```
GET /api/tutors/marketplace?subject={}&grade={}&q={}
→ Auth: student
→ Returns: [{
    keycloak_sub, name, initials, color, subjects, grades,
    topics: [str], content_rating: float | null, review_count: int,
    student_count, rate_per_session, availability
  }]
```

---

### S07 — Tutor Profile

**Purpose:** Full tutor profile with bio, topics, and content reviews. Informational only — no session booking in this phase.

**Layout:**
- Hero: avatar, name, subjects, grade range, bio, content rating (aggregate stars + count), student count, rate and availability (shown as info text — no booking button).
- Left main: About section, Topics covered (with per-topic avg rating shown as small stars next to each topic pill), Content reviews.
- Right sidebar: "Enroll with this tutor" CTA (starts open enrollment — same flow as S03), "Why hAIsir" trust card.

**Content reviews section:**
- Each review row: student avatar initials, topic name pill, star rating, optional comment, date.
- Label: "Content reviews" (not "Student reviews").

**Actions:**
- "Enroll with this tutor" → creates an open enrollment for this tutor → navigates to S04 scoped to that enrollment.

**Business rules:**
- **BR-STU-021:** Rate and availability are displayed as informational text only. There is no slot picker or booking flow.
- **BR-STU-022:** Content rating shown is `teacher_profiles.content_rating` — the aggregate across all of the tutor's topics. Tutors with no reviews yet show "No reviews yet" instead of a star rating.

**API calls:**
```
GET /api/tutors/{keycloak_sub}/profile
→ Auth: student
→ Returns: {
    keycloak_sub, name, bio, subjects, grades, topics,
    content_rating: float | null, review_count: int, student_count,
    rate_per_session, availability,
    reviews: [{
      reviewer_initials, reviewer_color, topic_title,
      rating: int, comment: str | null, created_at
    }]
  }

POST /api/enrollments/open/bulk
→ Auth: student
→ Body: {items: [{tutor_keycloak_sub}]}
→ Returns: {enrollment_ids: [uuid]}
```

---

### S08 — Doubt Inbox

**Purpose:** See all doubts the student has raised, across all topics and enrollments.

**Layout:**
- Filter tabs: All / Pending / Answered / Resolved.
- Doubt rows sorted by most recent activity first.

**Per doubt row:**
- Status left border (amber = pending, blue = answered, green = resolved).
- Topic icon, topic name, enrollment source.
- Preview of last message with sender prefix.
- Message count, time label.
- Status badge (Waiting for teacher / Teacher responded / Resolved).

**Actions:**
- Click filter tab → filters list.
- Click doubt row → S09 Doubt Thread.

**Business rules:**
- **BR-STU-023:** Shows all doubts where `student_keycloak_sub = self`, all statuses.
- **BR-STU-024:** Unread count in topbar badge = doubts where `status IN ('pending', 'answered')`.

**API calls:**
```
GET /api/students/me/doubts?status={}
→ Auth: student
→ Returns: [{
    id, topic_id, topic_title, enrollment_id, course_label,
    status, created_at, message_count,
    last_message: {sender_type, body_preview, created_at}
  }]
```

---

### S09 — Doubt Thread

**Purpose:** Full conversation for a single doubt — student question, hAITU attempts, teacher response.

**Layout:**
- Context bar: topic name, enrollment source, "Go to topic →" button.
- Status divider pill in message stream (Waiting for teacher response / Teacher has responded / Resolved).
- Message bubbles: student (right, grey), hAITU (left, blue), teacher (left, green).
- Each message shows sender label and timestamp.
- Bottom input area:
  - If `resolved`: "✓ This doubt is resolved" + "Ask a follow-up" button.
  - If `answered` or `pending`: textarea + "Send" button + "Mark resolved ✓" button (if `answered`).

**Actions:**
- Type in textarea + "Send" → adds student message, sets `doubt.status = 'pending'`, shows in thread.
- "Mark resolved ✓" → sets `doubt.status = 'resolved'`.
- "Ask a follow-up" (resolved state) → re-opens input, sets status back to `pending`.
- "Go to topic →" → S04 navigator scoped to that enrollment.

**Business rules:**
- **BR-DOUBT-008:** Student follow-up messages are allowed on doubts in any status including `resolved`. Sending a message on a resolved doubt re-opens it to `pending`.
- **BR-DOUBT-009:** Messages are displayed in `created_at` ascending order.
- **BR-DOUBT-010:** The context bar always shows the topic and enrollment the doubt was raised in.

**API calls:**
```
GET /api/doubts/{doubt_id}
→ Auth: student (own doubt only)
→ Returns: {
    id, topic_id, topic_title, enrollment_id, enrollment_label,
    status, created_at, auto_close_at,
    messages: [{id, sender_type, sender_name, body, created_at}]
  }

POST /api/doubts/{doubt_id}/messages
→ Auth: student
→ Body: {body: str}
→ Returns: {message_id, created_at}
→ Side effect: sets doubt.status = 'pending', triggers notification to teacher

PATCH /api/doubts/{doubt_id}/resolve
→ Auth: student
→ Returns: {status: "resolved", resolved_at: datetime}
```

---

### S10 — Student Profile

**Purpose:** View and edit profile, manage enrollments, generate parent link code.

**Sections:**
- Profile header: avatar initials, name, email, grade, "Edit" button.
- Account details card: name, email, grade, active role pill, member since.
- Enrollments card: all active enrollments with type badge and progress %. "+ Institution" and "+ Open course" buttons.
- Parent link code card: explains parent linking, "Generate parent link code" button.
  - After generation: shows code in large text, expiry date, "Copy code" button, "Share via WhatsApp" button, "Regenerate" button.
- Settings card: notifications link, language, log out.

**Actions:**
- "Generate parent link code" → generates code, shows it. Invalidates any previous code.
- "Copy code" → copies to clipboard.
- "Regenerate" → generates a new code (confirms first — warns previous code will be invalidated).
- Log out → Keycloak logout.

**Business rules:**
- **BR-PARENT-001** (see data model): One active link code at a time.
- **BR-STU-025:** Link code format: `{FIRST_NAME}-{YEAR}` in uppercase. If collision, append random 4-digit suffix.
- **BR-STU-026:** Code expiry is 7 days from generation.

**API calls:**
```
GET /api/students/me/profile
→ Auth: student
→ Returns: {keycloak_sub, first_name, last_name, grade, subjects, created_at}

PATCH /api/students/me/profile
→ Auth: student
→ Body: {first_name?, last_name?, grade?, subjects?}
→ Returns: updated profile

POST /api/students/me/parent-link-code
→ Auth: student
→ Returns: {code: str, expires_at: datetime}
→ Side effect: invalidates previous code

GET /api/students/me/parent-link-code
→ Auth: student
→ Returns: {code: str, expires_at: datetime, linked_parents: int} | null
```

---

## 4. Edge Cases

| Scenario | Behaviour |
|---|---|
| Student has no enrollments | Show empty state home with two CTA cards |
| Student tries to enroll in same class twice | 409 error → show "Already enrolled" message |
| Invite code expired | Show "This code has expired — ask your school admin for a new one" |
| Assessment attempt timer reaches zero | Auto-submit attempt (out of scope for this version — note for future) |
| Doubt escalation target teacher is inactive | Show "Your teacher is currently unavailable. Your doubt has been logged and will be addressed when they return." |
| Parent link code used by more than one parent | Each parent uses the same code and all get linked. Code expires after 7 days regardless of how many parents used it. |
| Student views review for an in-progress attempt | 403 — return "This assessment has not been submitted yet" |
| Network error on doubt send | Show inline error, keep message text in input, allow retry |
