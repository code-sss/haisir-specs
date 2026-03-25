# hAIsir — UI Mapping: Teacher / Tutor Flow
> Maps requirement screen IDs to prototype screens and documents UX details.
> → Prototype file: `haisir_teacher_flow.html`
> → Spec file: `04_teacher_tutor.md`

---

## Screen Map

| Spec ID | Prototype screen ID | Route | Render function |
|---|---|---|---|
| T01 | `s-home` | `/teacher` | `renderHome()` |
| T02 | `s-class` | `/teacher/class/:class_id` | `renderClass()` |
| T03 | `s-student` | `/teacher/student/:student_sub` | `renderStudent()` |
| T04 | `s-builder` | `/teacher/curriculum/:context_id` | `renderBuilder()` |
| T05 | `s-profile` | `/teacher/profile` | `renderProfileScreen()` |
| T06 | `s-teacher-doubts` | `/teacher/doubts` | `renderTeacherDoubts()` |
| T07 | `s-teacher-reply` | `/teacher/doubts/:doubt_id` | `renderTeacherReply()` |
| T08 | `s-exam-results` | `/teacher/exam-results/:assignment_id` | `renderExamResults()` |

---

## T01 — Teacher Home (`s-home`)

### Topbar
- Background: `#0A3D2B` (dark teal)
- Left: "hAIsir" brand, "Teacher" role pill (`rgba(255,255,255,.15)` bg)
- Right: "Doubts" button with amber badge (`rgba(255,165,0,.3)` bg when count > 0), "My profile" button, avatar (`#1D9E75`)
- Doubts badge: count of `teacherDoubts` where `status = 'pending'`. ID: `doubt-count-badge`.

### Alert cards (injected at top by `renderHome` patch — above sections)

**Doubts alert (amber)** — shown when pending doubts > 0:
- `#FAEEDA` bg, amber left border (3px `#EF9F27`)
- Title: "📬 {N} student doubt(s) waiting for your reply"
- Sub: "Students have escalated doubts that hAITU couldn't fully resolve."
- Button: "View doubts →" (`#EF9F27` bg, white text) → T06

**Exam results alert (green)** — shown when recent exam result exists:
- `#E1F5EE` bg, green left border (3px `#1D9E75`)
- Title: "📊 {Assessment name} results are ready"
- Sub: "{Class name} · Avg {N}% · {N} students need attention"
- Button: "View results →" (`#0F6E56` bg) → T08

**At-risk alert (red)** — future, triggered by `STUDENT_AT_RISK` notification.

### My classes section (institutional)
- Section header: "MY CLASSES (INSTRUCTOR)" + "+ Join institution" button
- Cards: `card inst` class — green top border (`#0F6E56`), green icon bg (`#E1F5EE`)
- Card content: class name, institution · grade · students count, progress bar (green fill), alerts (at-risk red, due amber, ok green), footer buttons
- Dashed add card at end

### Open tutoring section
- Section header: "OPEN TUTORING" + "+ New open course" button
- Cards: `card open` class — purple top border (`#534AB7`), purple icon bg (`#EEEDFE`)
- Dashed add card at end

---

## T02 — Class Dashboard (`s-class`)

### Topbar
- "Instructor" role pill (structured context) or "Tutor" pill (open context)

### Stat row
- 4 cards: Students / Class average (green if ≥70%) / Needs attention (amber) / At risk (red) or Sessions this week
- `green` class: `#0F6E56` text. `amber`: `#854F0B`. `red`: `#993C1D`.

### Student roster table
- Header row: grey bg (`#f5f4f0`)
- Each row: avatar circle + name, mini progress bar (64px wide, 4px height), weak topics badge, last active date, "View →" button
- Row hover: `#fafaf8` bg
- Mini bar colours: green ≥75%, amber 50–74%, red <50%
- Weak topic badge: `mb-danger` (red), `mb-warn` (amber), `mb-ok` (green)
- Click row → T03

### Topic performance heatmap (instructor only)
- Each row: topic label (120px) + horizontal bar + avg % value
- Bar colours: green (`#1D9E75`) ≥75%, amber (`#EF9F27`) 50–74%, red (`#D85A30`) <50%
- "Add content" button → T04

### Assignments panel (instructor only)
- List: name, due date, submitted/total, avg score (if completed)
- "+ Assign quiz/exam" button → modal

### Assignment modal
- Template picker (dropdown of available exam_templates for subject/grade, filterable by purpose: Quiz/Exam)
- Due date (date input)
- Optional note to students
- "Assign" confirm button (`#0F6E56`)

---

## T03 — Student Detail (`s-student`)

### Layout (split: main | side 260px)

**Main:**
- Profile card: avatar, name, class/context, overall % + weak topic count
- Topic performance table: same mini-bar pattern as T02 roster

**Sidebar:**
- hAITU analysis card: dark teal header (`#0A3D2B`), "hAITU student analysis" title
- Analysis text (generated on load)
- Three action buttons (`#E1F5EE` bg, `#0F6E56` text): "Plan next session content" / "Generate practice questions" / "Generate progress report"
- Session/doubt history card (tutor only): dated entries
- Notes card: textarea (`notes-input` class, focus border `#0F6E56`), "Save notes" button

---

## T04 — Curriculum Builder (`s-builder`)

### Topbar role tag
- Institutional instructor context: "Instructor"
- Tutor context: "Tutor"

### Layout (split: left tree 220px | right detail)

**Left tree:**
- Header: context name + "+" add button (navy `#080F17` bg)
- Tree nodes: `tnode` class, selected: grey bg
- Levels: chapter (📁) → sub-topic (📄)
- "+ Add topic" dashed button at bottom

**Right panel — instructor restriction banner:**
- Blue info bar: "Core structure owned by institution admin. You can add supplemental content only."

**Right panel — content items:**
- Each item: type icon, title, date, delete button (tutor only)
- Upload zone: dashed border, 📎 icon, "Upload PDF, video link, or text notes"
- "Students on this topic" list (tutor only) — click → T03

---

## T05 — Teacher Profile (`s-profile`)

### Layout
- Two-column split (main | narrow side)
- Bio card: name, subjects (pills), grades, experience, bio textarea
- Availability and rate fields
- Marketplace toggle checkbox with note about pending approval if not yet approved
- Stats card (read-only): active students, topics built, avg progress, rating

---

## T06 — Doubt Inbox (`s-teacher-doubts`)

### Stat row (3 cards)
- Awaiting your reply (amber value)
- Replied (green value)
- Total this week

### Doubt rows
- "Awaiting" section: `drt-new` class — amber left border (`#EF9F27`)
- "Replied" section: `drt-replied` class — green left border (`#0F6E56`), 85% opacity
- Per row: student avatar (22px) + name + topic + course, first student question (truncated), last message preview, time, message count, status badge

### Info note (blue)
- `#E6F1FB` bg, `#0C447C` text — explains escalation model

### Sorted order
- Awaiting section: oldest first (student who has waited longest)
- Replied section: most recent first

---

## T07 — Doubt Reply Thread (`s-teacher-reply`)

### Context bar
- `#E1F5EE` bg, `#9FE1CB` border
- Student name + topic + course + message count
- "View student →" button (`#0F6E56` bg) at far right → T03

### Message bubbles
- Student messages: left, grey bg (`#f5f4f0`)
- hAITU messages: left, blue bg (`#E6F1FB`)
- Teacher (own) messages: right, green bg (`#E1F5EE`), `border-bottom-right-radius: 3px`

### Input area — pending/answered state
- Context note (amber `#FAEEDA`): "📌 hAITU could not fully resolve this. Your explanation will appear directly in the student's doubt thread."
- Textarea (70px height, focus border `#0F6E56`)
- Two buttons stacked right: "Send reply" (`#0F6E56` bg) + "Send & resolve" (outline, `#0F6E56` text)

### Input area — replied state
- "✓ You have replied to this doubt" text
- Textarea still available for additional messages (no resolve button — already resolved)

---

## T08 — Class Exam Results (`s-exam-results`)

### Header (dark teal `#0A3D2B`)
- Assessment name (17px bold white), class name, date (small, 55% opacity)
- Right: 4 stat blocks — class average (colour-coded amber/green), passed (green), below 60% (red), total

### Average colour thresholds
- ≥75%: `#5DCAA5` (teal green)
- 50–74%: `#FAC775` (amber)
- <50%: `#F09595` (red)

### Two-column grid

**Left — Student scores table:**
- Same mini-bar pattern as T02
- Status badges: "Good" (green), "Review" (amber), "Struggling" (red)

**Right column (top to bottom):**

**Question heatmap card:**
- Title + "% of students who got each question right" sub-label
- Grid of cells (36×36px, 6px border-radius, gap 6px):
  - `qhc-good` (≥75%): `#E1F5EE` bg, `#085041` text
  - `qhc-mid` (55–74%): `#FAEEDA` bg, `#633806` text
  - `qhc-bad` (<55%): `#FAECE7` bg, `#712B13` text
- Legend: green ≥75% / amber 55–74% / red <55%

**hAITU recommendations card (`ai-next-steps`):**
- `#E1F5EE` bg, `#9FE1CB` border
- Title: "hAITU recommendations for next class"
- Each recommendation: `ans-item` row with "→" prefix, `#0F6E56` text, green bottom border

**Weak topics card:**
- Each weak topic: `⚠` icon + topic name in red
- "Generate remedial assignment" button → calls hAITU + opens assignment modal pre-filled
