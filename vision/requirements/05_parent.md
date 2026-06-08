# hAIsir — Parent Specification
> Version 1.1 | Part A extracted from `05_06_07_personas.md`.
> Parent is an entirely new persona and role.
> → Depends on: `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`
> → Prototype: `haisir_parent_flow.html`
> → See also: `06_institution_admin.md`, `07_platform_admin.md`

---

# PART A — Parent

## A.1 Persona Summary

**Role:** `parent`
**Topbar colour:** `#3D2000` (warm brown)
**Can:** View linked child's progress in plain language, see quiz/exam results (scores only), read teacher responses in doubt threads, message tutors (not institutional teachers), generate and manage child links.
**Cannot:** See raw quiz/exam questions, modify any content, access other children's data, contact institutional teachers directly.

---

## A.2 Screen Inventory

| # | Screen ID | Name |
|---|---|---|
| P01 | `parent-home` | Home — overview tab |
| P02 | `parent-progress` | Progress tab |
| P03 | `parent-results` | Results tab (quizzes + exams) |
| P04 | `parent-teachers` | Teachers & tutors tab |
| P05 | `parent-link` | Link child (onboarding / add child) |

All tabs live within one screen with a child switcher strip at the top (if multiple children linked).

---

## A.3 Screen Specifications

### P01 — Home (Overview Tab)

**Child switcher strip:** One tab per linked child. Active child highlighted amber. "+ Link child" at end → P05.

**Snapshot banner (dark brown):** Child name, week at a glance stats — day streak, topics this week, active courses count, weak topic count.

**Status banner:**
- Green: "On track this week" (no weak topics, no overdue items).
- Amber: "Needs some attention" (1–3 weak topics).
- Red: "Needs urgent attention" (>3 weak topics or mastery < 40% on multiple topics).
Button → Progress tab.

**Due soon strip (amber border):** All upcoming assignments across all child's enrollments. Sorted by due date.

**Course cards grid:** One per enrollment. Shows: enrollment name, source (institution / tutor), track pill, progress bar, weak topic alerts, due item alerts, next session info (if tutor), last studied date.

**Weekly report card:** "Report sent every Monday" + "View last report" + "Get report now" buttons.

**Business rules:**
- **BR-PAR-001:** Only shows data for children where `parent_child_links.status = 'linked'`.
- **BR-PAR-002:** Week streak = consecutive days with at least one `enrollment_topics.last_studied_at` update.
- **BR-PAR-003:** "Topics this week" = distinct topics with `last_studied_at` in the current ISO week.
- **BR-PAR-004:** Status banner level is determined by: ok = no weak topics (mastery ≥ 60 on all topics); warn = 1–3 topics with mastery 40–59%; danger = any topic mastery < 40% OR more than 3 weak topics. The warn level aligns with the student weak threshold (< 60) while the danger level is stricter (< 40).
- **BR-PAR-005:** "Get report now" triggers hAITU to generate a plain-language progress summary. See `08_haitu_ai_layer.md #parent-report`.

**API calls:**
```
GET /api/parents/me/children
→ Auth: parent
→ Returns: [{
    idp_sub, name, grade, color, initials,
    streak, topics_this_week, active_courses,
    overall_status: "ok"|"warn"|"danger",
    courses: [{
      enrollment_id, type, name, source, progress,
      weak_topics: [str], due_items: [str], last_studied_at
    }]
  }]

GET /api/parents/me/children/{child_sub}/due-items
→ Auth: parent
→ Returns: [{title, source, due_at, enrollment_type}]
```

### P02 — Progress Tab

**Subject cards:** One per enrollment. Header: enrollment icon, name, source, overall %. Per topic row inside each card:
- Topic name.
- Plain-language description (e.g. "Struggling — scored below 60% in last 3 attempts").
- Status badge: Doing well / On track / Needs attention / Not started.
- "Explain this" button (shown only for "Needs attention" topics) → calls hAITU to generate a plain-language parent-facing explanation.

**hAITU summary card (sidebar):** Pre-generated on load. Shows: streak, active courses, main weak areas in plain English, mention of any teacher response to a doubt. Three action buttons: "Full progress report", "How can I help at home?", "Talk to a tutor".

**Activity timeline (sidebar):** Chronological feed of child's activity. Entries:
- Study sessions.
- Quiz/exam completions with score.
- Doubts raised / teacher responses (highlighted in green with "New response" tag).
- Course enrollments.

**Business rules:**
- **BR-PAR-006:** Plain-language topic descriptions are displayed per topic based on mastery score.
  - **Phase 1 (static fallback):** Static strings based on `mastery_score`: < 40% → "Struggling — needs urgent attention"; 40–59% → "Needs attention — scoring below target"; 60–74% → "On track — progressing steadily"; ≥ 75% → "Doing well — topic mastered".
  - **Phase 2 (AI upgrade):** hAITU-generated prose descriptions replace the static strings — cached per child per day. See `08_haitu_ai_layer.md #parent-topic-descriptions`. No UI changes required to upgrade from Phase 1 to Phase 2.
- **BR-PAR-007:** Teacher response entries in the timeline are shown when a `doubt_message` with `sender_type = 'teacher'` is created and the doubt is linked to this child.
- **BR-PAR-008:** "Explain this" generates a parent-friendly explanation of why a topic is difficult and what the child can do. Not the same as a student-facing hAITU explanation.

**API calls:**
```
GET /api/parents/me/children/{child_sub}/progress
→ Auth: parent
→ Returns: {
    courses: [{
      enrollment_id, name, source, progress,
      topics: [{
        topic_id, title, mastery_score, status,
        plain_description: str, last_attempted_at
      }]
    }],
    timeline: [{
      type: "study"|"quiz"|"exam"|"doubt_replied"|"enrollment",
      text: str, time: str, is_new_teacher_response: bool
    }],
    haitu_summary: str  // cached daily
  }
```

### P03 — Results Tab (Quizzes + Exams)

**Stat row:** Average score (across all completed sessions), Improving topics count, Upcoming count.

**Upcoming section:** Quizzes/exams due soon with amber left border. Type badge (Quiz / Exam) on each.

**Past results:** Chronological list, newest first. Each item:
- Title, type badge (Quiz / Exam), source course, date.
- Score % (large, colour-coded).
- Trend indicator: ↑ Improving / ↓ Dropped / → Steady (based on comparison with previous attempt on same topic).

**Info note (blue):** "For detailed question-level feedback, ask their teacher directly."

**Business rules:**
- **BR-PAR-009:** Parent sees `score` from `exam_sessions` but NOT the question list or individual answers.
- **BR-PAR-010:** Trend is calculated by comparing current score to the previous session on the same template. First attempt shows no trend.
- **BR-PAR-011:** "Improving topics" = distinct topics where the most recent mastery score is higher than the one before it.

**API calls:**
```
GET /api/parents/me/children/{child_sub}/results
→ Auth: parent
→ Returns: {
    stats: {avg_score: float, improving_topics: int, upcoming: int},
    upcoming: [{title, purpose, course, due_at}],
    completed: [{
      session_id, title, purpose, course, submitted_at,
      score: float, trend: "up"|"down"|"flat"|null
    }]
  }
```

### P04 — Teachers & Tutors Tab

**Teacher/tutor cards:** One per teacher or tutor interacting with the child.

**Institutional teacher card:**
- Name, role, institution, class, subjects covering, last assignment.
- Grey info box: "To contact {name}, reach out through {institution}."
- No direct messaging.

**Tutor card:**
- Name, role, next session, rate, subjects covering.
- Live message thread: shows last 3 messages (parent ↔ tutor). "Message {tutor}" input + send button.
- "View profile" button (navigates to tutor profile on the student marketplace).
- "View profile" button.

**Browse tutors card (purple):** "Need extra support? Browse tutors who specialise in {child name}'s weak topics." → links to tutor marketplace.

**Business rules:**
- **BR-PAR-012:** Institutional teachers are sourced from `classes` where the child is enrolled, via `class_enrollments`.
- **BR-PAR-013:** Parent messages to tutors are stored in a `parent_tutor_messages` table (not the same as student doubt threads — this is a separate direct message channel). Messages in `parent_tutor_messages` are **not visible to the student**.
- **BR-PAR-014:** Parent cannot message institutional teachers. The contact note is always shown for institutional teacher cards.

**API calls:**
```
GET /api/parents/me/children/{child_sub}/educators
→ Auth: parent
→ Returns: {
    instructors: [{
      idp_sub, name, role, institution, class_name,
      subjects: [str], last_assignment: str
    }],
    tutors: [{
      idp_sub, name, role, next_session: str | null,
      rate: int | null, subjects: [str],
      messages: [{from: "parent"|"tutor", text, time}]
    }]
  }

POST /api/parents/me/messages/{tutor_sub}
→ Auth: parent
→ Body: {child_sub: str, message: str}
→ Returns: {message_id, created_at}
```

### P05 — Link Child

**Purpose:** Onboarding flow for parent to link a child account.

**Fields:** Single code input (large, centre-aligned, uppercase).

**Validation:** Live — on input, validates against `parent_child_links` table. Shows found child's name, grade, and school on match.

**"How does this work" info box:** Step-by-step for parents.

**Actions:**
- Valid code entered → "Link account" button enabled → click → creates link → navigates to home showing child.
- "Skip" → goes to home (child-less empty state).

**Business rules:**
- **BR-PARENT-001** (see data model): One active code per student at a time.
- **BR-PARENT-002**: Code expires 7 days from generation.
- **BR-PAR-015:** After successful link, send CHILD_WEEKLY_DIGEST notification to parent (first digest) within 24 hours.
  - **Phase 1 content (stats-only):** child name, week streak, topics studied this week, active courses count, count of weak topics. No AI-generated prose. The `body` field of the notification carries this content.
  - **Phase 2 content:** hAITU-generated plain-language prose summary replaces the stats-only content. No notification schema change required.

**API calls:**
```
GET /api/parent-link-codes/{code}
→ Auth: parent
→ Returns: {student_name, grade, school} | 404

POST /api/parent-child-links
→ Auth: parent
→ Body: {code: str}
→ Returns: {link_id, student_idp_sub, student_name}
→ Errors: 404 code not found, 410 code expired, 409 already linked, 422 maximum children exceeded

**BR-PAR-016:** Maximum of 10 children per parent account for v1. `POST /api/parent-child-links` must reject the request with 422 and message "Maximum of 10 children can be linked to one parent account." if the parent already has 10 active `parent_child_links` records.
```

---

## Edge Cases (Parent)

| Scenario | Behaviour |
|---|---|
| Child link code expired | Show "Code expired. Ask your child to generate a new one." |
| All children's links revoked | Show empty state — "No children linked" with link child CTA |
| Child has no quiz/exam results | Results tab shows empty state with explanation |
