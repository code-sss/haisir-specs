# hAIsir — UI Mapping: Student Flow
> Maps requirement screen IDs to prototype screens and documents UX details.
> → Prototype file: `haisir_student_flow.html`
> → Spec file: `03_student.md`

---

## Screen Map

| Spec ID | Prototype screen ID | Route | Render function |
|---|---|---|---|
| S01 | `s-home` | `/home/dashboard` | `renderHome()` |
| S01 (empty) | `s-home` | `/home/dashboard` | `renderEmptyHome()` |
| S02 | `s-inst` | `/home/join-institution` | `renderInstScreen()` |
| S03 | `s-open` | `/home/browse` | `renderOpenScreen()` |
| S04 | `s-nav` | `/home/topics/:enrollment_id` | `renderNav()` |
| S05 | `s-review` | `/home/review/:attempt_id` | `renderReview()` |
| S06 | `s-tutors` | `/tutors` | `renderTutors()` |
| S07 | `s-tutor-profile` | `/tutors/:keycloak_sub` | `renderTutorProfile()` |
| S08 | `s-doubts` | `/doubts` | `renderDoubtInbox()` |
| S09 | `s-doubt-thread` | `/doubts/:doubt_id` | `renderDoubtThread()` |
| S10 | `s-profile` | `/profile` | `renderProfile()` |

---

## S01 — Home Dashboard (`s-home`)

### Topbar
- Background: `#0A1F5C` (navy)
- Left: "hAIsir" brand
- Right: "Ask hAITU" pill button, "Doubts (N)" button (amber tint when N > 0), "Profile" button, avatar initials circle (`#378ADD`)
- Doubts button badge: count of doubts where `status IN ('pending', 'answered')`. Updates on `updateDoubtsBadge()`.

### Returning student state (has enrollments)
Layout (top to bottom):
1. **Continue card** — dark navy (`#0A1F5C`) card. "Continue where you left off" label, last topic title, enrollment name, "Resume →" button (`#378ADD`).
2. **Due soon strip** — white card with amber left border (`#FAC775`). Title "DUE SOON" in amber caps. Each due item: name (left), source below in grey, badge right (red "Tomorrow" or amber "Upcoming").
3. **Institutions section** — "SCHOOL ENROLLMENTS" section header + grid of enrollment cards (blue top border, `#185FA5`).
4. **Open courses section** — "OPEN COURSES" header + grid of enrollment cards (purple top border, `#534AB7`).
5. **Find-tutor CTA** — purple banner (`#EEEDFE` bg, `#CECBF6` border). "Browse tutors →" button (`#534AB7`).
6. **Review-exam CTA** — blue banner (`#E6F1FB` bg). "Review exam →" button (`#185FA5`).

### Enrollment card layout
- Top border colour: blue (`#185FA5`) for structured, purple (`#534AB7`) for open
- Head: icon (36×36, rounded), enrollment name (bold), source meta, track pill
- Progress bar: 5px height, blue or purple fill
- Alert rows: weak topics (red `#FAECE7`), due items (amber `#FAEEDA`), session info (purple `#EEEDFE`)
- Footer: "Browse topics →" primary button, "Last: {date}" ghost button

### Empty home state (`renderEmptyHome`)
- Owl emoji (48px), "Welcome to hAIsir" title, sub-text
- Two CTA cards side by side:
  - Blue card: "Join your school" — `#E6F1FB` bg, `#185FA5` text
  - Purple card: "Start learning openly" — `#EEEDFE` bg, `#534AB7` text

---

## S02 — Join Institution (`s-inst`)

### Layout
- Breadcrumb: Home → Join an institution
- Hero card: school icon, title, description
- Form card:
  - Invite code input + "Apply" button — live validation on each keystroke (debounced 500ms)
  - Validation message below input: green (✓ found) or grey (not found)
  - OR divider
  - Search by name input → shows institution rows below
  - Each institution row: icon, name + board + grade meta, radio-style check circle (right)
  - Selected row: blue border (`#185FA5`), `#f4f8fd` background
  - "Enroll in selected institution" primary button — disabled until valid code or institution selected

### Valid invite code: `STMARY-2026-G6`
Shows: St. Mary's School · NCERT · Grade 6

---

## S03 — Browse Open Courses (`s-open`)

### Layout
- Left sidebar (200px): subject filter chips. Active chip: `#EEEDFE` bg, `#534AB7` text. Inactive: transparent.
- Search bar + "Add to my courses" button with cart count badge (red circle, top-right of button)
- Results: grouped by tutor as section headers. Each course row: icon (30px, `#EEEDFE` bg), title, subject · course meta, tutor pill, "+ Add" / "✓ Added" button

### Cart behaviour
- "+ Add" → toggles to "✓ Added" (purple solid). Cart badge increments.
- "Add to my courses" button → creates enrollments grouped by tutor → navigates home
- Cart is local state only — lost on navigation

### Filter state
- Active subject chip highlighted purple
- Search filters live (no debounce needed — local data)

---

## S04 — Topic Navigator (`s-nav`)

### Enrollment tab strip
- One tab per active enrollment
- Structured tab active: blue bottom border (`#185FA5`), `#f4f8fd` bg, blue label + blue sub-label
- Open tab active: purple bottom border (`#534AB7`), `#f7f6fe` bg, purple label
- "+ Add" tab at end — opens S03
- Dividers between tabs: 0.5px `#e5e3dc`

### Context bar (below strip)
- Structured: blue bg (`#EBF4FD`), blue text. Shows: [Structured pill] · Institution · Board · Grade · **All subjects**
- Open: purple bg (`#F1F0FE`), purple text. Shows: [Open pill] · Tutor name or "Self-directed" · **All topics**

### Sidebar (collapsible, 210px)
- Toggle button (☰) in nav header — toggles `.collapsed` class which sets `width: 0`
- Filter groups:
  - **Status** chips: Needs attention / In progress / Completed / Not started
  - **Subject** chips (structured only): Maths / Science / English / Hindi / Programming / History
  - Active chip: blue (`#E6F1FB` / `#185FA5`) for structured, purple (`#EEEDFE` / `#534AB7`) for open
- "Clear" button resets all filters

### Filter pills (above topics list)
- Each active filter shown as removable pill
- Blue pills for structured, purple for open
- × button removes individual filter

### Topic rows
- Default: white card, `#e5e3dc` border, 7px border-radius
- Weak topic: amber-red left indicator — `#F5C4B3` border, `#FFFBF9` bg
- Hover: blue border highlight
- Locked: 40% opacity, pointer-events: none, 🔒 icon

### Per topic row layout
- Left: icon (28px, coloured by status), title, breadcrumb (source tag + board·grade·subject·course)
- Source tag: blue pill for structured, purple for open
- Status badges: `tbw` (red) weak, `tbp` (amber) in-progress, `tbd` (green) done, `tbn` (grey) new
- Right: status badge, "Ask hAITU" button (purple pill)
- No "Ask teacher" button on topic rows — escalation is only via the hAITU chat panel

### hAITU chat panel (slide-in overlay)
- Triggered by "Ask hAITU" click on any topic row
- Slides in from the right: fixed position, 300px wide, full viewport height, `z-index: 200`
- Semi-transparent dark overlay (`rgba(0,0,0,0.3)`) behind panel; clicking overlay closes panel
- Panel header: dark navy bg (`#0A1F5C`), topic title in white, "Scoped to this topic" subtitle in `rgba(255,255,255,.5)`, × close button (top-right)
- Chat area: scrollable, AI bubbles blue (`#E6F1FB`), student bubbles right-aligned grey (`#f5f4f0`)
- Input row: text input + send button (`#534AB7` purple — matches open/hAITU colour)
- "Request teacher help →" button: shown below the input row after the first hAITU response is received. Style: amber bg (`#FAEEDA`), amber border (`#FAC775`), dark amber text (`#7A4E00`). Full-width. Clicking creates a doubt and navigates to S09.

### Status grouping order
1. Needs attention (weak)
2. In progress
3. Completed
4. Not started
5. Locked (always last, only shown when no filters active)

---

## S05 — Post-Exam AI Review (`s-review`)

### Layout
- Breadcrumb below topbar
- Summary bar (dark navy `#0A1F5C`): score % in amber (`#FAC775`), correct (green), wrong (red), skipped (grey), total — 5 stat blocks
- Two-column below: questions list (left, scrollable) | hAITU chat panel (right, fixed)

### Question cards
- Correct: green left border (`#1D9E75`), green number badge
- Wrong: red left border (`#D85A30`), red number badge
- Skipped: grey left border, grey number badge
- Header: click to expand/collapse (▼/▲ indicator)
- Pre-expanded on load: all wrong + skipped. Correct: collapsed.
- Expanded answer options:
  - Correct answer: green row (`#E1F5EE`), ✓ icon
  - Student's wrong answer: red row (`#FAECE7`), ✗ icon
  - Other options: neutral grey (`#f5f4f0`)
- hAITU explanation: blue card (`#E6F1FB`) below options with "hAITU explanation" label
- "Ask hAITU to explain this" button: shown for wrong/skipped without pre-loaded explanation

### Paragraph question rendering
- Passage body shown in a card above its embedded questions
- Embedded questions rendered as sub-cards with indentation
- Each sub-card follows same correct/wrong/skipped colour logic

### hAITU chat panel (right, fixed 300px)
- Dark navy header (`#0A1F5C`): "Ask hAITU about this exam" / "Scoped to your answers"
- Scrollable message area — AI bubbles: blue (`#E6F1FB`), student bubbles: right-aligned grey
- Input row: text input + "›" send button (`#185FA5`)
- Pre-loaded message on mount: pattern analysis (generated once, cached for session)

---

## S06 — Tutor Discovery (`s-tutors`)

### Layout
- Left sidebar (210px): Subject / Grade / Availability filter chips (same pattern as S04 sidebar)
- Search bar full-width above results
- Tutor cards (stacked, full-width):
  - Avatar (44px circle, coloured), name (bold), subjects · grade meta
  - Topic tags (small purple pills)
  - Content rating stars + review count + student count (label: "Content rating")
  - Right: rate + availability (stacked), "View profile" button (`#534AB7`)

### Filter state
- Active subject chip: purple (`#EEEDFE` / `#534AB7`)
- Search: live filter, no debounce needed

---

## S07 — Tutor Profile (`s-tutor-profile`)

### Layout
- Hero card: avatar (64px), name (18px bold), subjects · grade · availability, content rating (stars + count) + student count, rate ("₹X/hr" — informational only, no booking button)
- Two-column body (1fr + 280px sidebar):
  - Left: About card, Topics covered (purple pills), Student reviews
  - Right: "Enroll with this tutor" CTA card (`#534AB7` button), "Why hAIsir" trust card

### Enroll CTA
- Button label: "Enroll with this tutor" (`#534AB7` bg, white text, full-width)
- On click: creates open enrollment and navigates to S04 topic navigator scoped to that enrollment
- No slot grid, no payment UI

### Content reviews
- Section label: "Content reviews"
- Each review row: avatar initials (28px), topic name (small purple pill), star rating in amber (`#EF9F27`), comment text (if present), date in grey
- Stars: ★★★★★ / ★★★★☆ etc.
- No reviews state: "No content reviews yet"

### Content rating prompt (S04 topic rows)
- Shown inline below status badge when `enrollment_topics.status = 'completed'` or `'weak'` and no review yet submitted
- Label: "Rate this content:" + 5 star icons (grey default, amber on hover/select)
- Clicking a star immediately submits; an optional comment input appears below (with "Skip" and "Submit" buttons)
- After submission: stars replaced with submitted rating (read-only amber stars)

---

## S08 — Doubt Inbox (`s-doubts`)

### Filter tabs
- Four tabs: All (N) / Pending (N) / Answered (N) / Resolved (N)
- Active tab: `#0A1F5C` bg, white text, rounded pill
- Inactive: transparent, grey text

### Doubt rows
- Left border colour: amber (`#EF9F27`) for pending, blue (`#185FA5`) for answered, green (`#1D9E75`) for resolved
- Class: `dr-pending`, `dr-answered`, `dr-resolved`
- Icon background: amber/blue/green accordingly
- Status badges: `ds-pending` (amber), `ds-answered` (blue), `ds-resolved` (green)
- Resolved rows: 80% opacity

### Empty state
- 💬 icon, "No doubts yet" title, explanatory sub-text

---

## S09 — Doubt Thread (`s-doubt-thread`)

### Context bar
- Blue bg (`#E6F1FB`), blue border (`#B5D4F4`)
- Topic name in blue bold, enrollment crumb in lighter blue
- "Go to topic →" button (`#185FA5`) at far right

### Message bubbles
- Student: right-aligned, grey bg (`#f5f4f0`)
- hAITU: left-aligned, blue bg (`#E6F1FB`), blue text
- Teacher: left-aligned, green bg (`#E1F5EE`), green text
- Each group: sender label above (10px caps), time below

### Status divider
- Horizontal line with centre pill — amber (pending), blue (answered), green (resolved)

### Input area
- Pending/answered: textarea + "Send" (`#185FA5`) + "Mark resolved ✓" (`#1D9E75`, shown only when `answered`)
- Resolved: "✓ This doubt is resolved" text + "Ask a follow-up question" button

---

## S10 — Student Profile (`s-profile`)

### Layout
- Header: navy bg (`#0A1F5C`), avatar initials (56px, `#378ADD`), name (18px white), email (grey), "Edit" ghost button
- Account details card
- Enrollments card: each enrollment with type pill (blue/purple) + progress %
- Parent link code card:
  - Before generation: "Generate parent link code" button (navy)
  - After generation: code in large type (`#0A1F5C`, letter-spacing 0.12em), expiry note, "Copy code" + "Share via WhatsApp" + "Regenerate" buttons
- Settings card: notifications, language, log out (log out in red)

---

