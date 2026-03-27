# UI Mapping — Student

> Maps prototype screen IDs to routes, components, and colour/state details.
> Prototype reference: `vision/prototypes/haisir_student_flow.html` (open in browser for visual reference).
> Target prototype: `target/prototypes/haisir_student_flow.html`.

---

## Colour tokens

| Token | Value | Usage |
|---|---|---|
| `--platform-blue` | `#185FA5` | Platform content section, platform exam accent |
| `--home-study-green` | `#1D9E75` | Home Study section, parent exam accent |
| `--topbar-navy` | `#0A1F5C` | Top navigation bar background |
| `--text-primary` | `#1A1A2E` | Body text |
| `--card-bg` | `#FFFFFF` | Card background |
| `--card-border` | `#E0E7FF` | Card border (platform) |
| `--card-border-green` | `#C3F0E0` | Card border (Home Study) |

---

## S-home — Dashboard (`/home`)

**Prototype function:** `renderHome()`

| Element | Detail |
|---|---|
| Topbar | Navy (`#0A1F5C`), logo left, student name + avatar right |
| Section heading "Platform Board" | Blue (`#185FA5`), bold |
| Platform subject cards | White cards, blue left-border accent, subject name, topic count, "Continue" or "Start" CTA |
| Section heading "Home Study" | Green (`#1D9E75`), bold |
| Home Study subject cards | White cards, green left-border accent; same layout as platform cards |
| No-parent placeholder | Dashed green border card, lock icon, "No Home Study content yet" text |
| Home Study section | Hidden entirely if `parent_child_links` count = 0 |

**States:**
- `has_parent_link = false` → Home Study section replaced by placeholder card.
- `has_parent_link = true, content_empty = true` → Home Study section shows empty state: "Your parent hasn't published any content yet."

---

## S-nav — Content Navigator (`/courses`)

**Prototype function:** `openNav(source)`

| Element | Detail |
|---|---|
| Source tabs | "Platform" (blue) | "Home Study" (green); active tab has coloured underline |
| Home Study tab | Greyed + disabled if no active parent link |
| Left sidebar | Fixed width (~260px), scrollable node tree |
| Node rows | Indented by depth, expand/collapse arrow, leaf node shows topic count badge |
| Selected node | Highlighted row |
| Right panel | Topic list or empty state "Select a topic to begin" |
| Topic row | Title, content type icons (PDF/video/text), `live` badge, "Take Exam" button |
| Draft topics | Not shown to students |
| "Take Exam" button | Blue (platform) or green (Home Study) |

**States:**
- No leaf node selected → empty right panel with prompt.
- Leaf node with no topics → "No topics available yet."
- Leaf node with topics → topic list rendered.

---

## S-exam — Exam Taking (`/exam/:session_id`)

**Prototype function:** `startExam(source)` → renders exam questions

| Element | Detail |
|---|---|
| Topbar | Context colour: blue (platform) or green (Home Study) |
| Timer | Top-right, countdown MM:SS; hidden if no time limit |
| Question number | "Question X of Y" |
| MCQ options | Radio buttons; selected option highlighted in context colour |
| Paragraph question | Textarea, min-height 120px |
| "Submit" button | Disabled until ≥1 answer given; triggers confirmation modal |
| Confirmation modal | "Are you sure? You cannot change answers after submission." |

**States:**
- In progress: all answers editable.
- Timer expired: auto-submit triggered, brief "Time's up" toast.

---

## S-results — Exam Results (`/exam/:session_id/results`)

**Prototype function:** `submitExam()` → transitions to results view

| Element | Detail |
|---|---|
| Score card | Large "X / Y" score, percentage, Pass (green) / Fail (red) badge |
| Per-question table | Question text, student answer, correct answer, points awarded |
| Correct answer row | Green highlight |
| Wrong answer row | Red highlight |
| "Back" CTA | "Back to Platform" (blue) or "Back to Home Study" (green) based on exam source |

---

## S-profile — Student Profile (`/profile`)

**Prototype function:** `renderProfile()`

| Element | Detail |
|---|---|
| Name + email | Read-only, from IdP |
| "Parent Link Code" card | Code displayed in monospace font, copy-to-clipboard icon, "Generate new code" button |
| "Linked Parents" section | List rows: parent name, linked date, "Remove" button |
| Remove confirmation | Inline confirmation: "This will remove access for this parent." |

**States:**
- No linked parents → "No parents linked yet" empty state under Linked Parents.
- Code generation → brief spinner on the code field while `POST /api/student/parent-link-codes` resolves.
