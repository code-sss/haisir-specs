# hAIsir — UI Mapping: Parent, Institution Admin, and Admin Flows
> Maps requirement screen IDs to prototype screens and documents UX details.
> → Prototype files: `haisir_parent_flow.html`, `haisir_institution_flow.html`, `haisir_superadmin_flow.html`
> → Spec file: `05_06_07_personas.md`

---

# PART A — Parent Flow

## Screen Map

| Spec ID | Prototype screen ID | Route | Render function |
|---|---|---|---|
| P01 | `s-home` (overview tab) | `/parent` | `renderOverview()` |
| P02 | `s-home` (progress tab) | `/parent` | `renderProgress()` |
| P03 | `s-home` (results tab) | `/parent` | `renderResults()` |
| P04 | `s-home` (teachers tab) | `/parent` | `renderTeachers()` |
| P05 | `s-link` | `/parent/link` | `renderLink()` |

**Note:** P01–P04 are tabs within a single screen (`s-home`). The screen does not reload on tab switch — `renderCurrentTab()` re-renders the `home-body` div in place.

---

## Topbar
- Background: `#3D2000` (warm amber-brown)
- Left: "hAIsir" brand, "Parent" role pill (`rgba(255,200,80,.2)` bg, `#FAC775` text)
- Right: "+ Link child" button, avatar (`#BA7517`)

## Child Switcher Strip
- White bg, `#e5e3dc` bottom border
- One tab per linked child: child avatar (24px circle), name, grade sub-label
- Active tab: `#BA7517` bottom border, `#fdf8f2` bg, `#854F0B` name, `#BA7517` grade
- Dividers: 0.5px `#e5e3dc`
- "+ Link child" at end — navigates to P05

## Main Tabs
- White bg, `#e5e3dc` bottom border
- Four tabs: Overview / Progress / Assessments / Teachers & tutors
- Active: `#3D2000` bottom border (2.5px), `#3D2000` text, `font-weight: 600`

---

## P01 — Overview Tab

### Snapshot banner
- Dark brown bg (`#3D2000`), white/amber text
- "Good morning, {parent_name}" heading
- "{child_name}'s week at a glance" sub
- 4 stat blocks: day streak / topics this week / active courses / needs attention
- Stat values in `#FAC775` (amber gold)

### Status banner
- **Green** (`sb-ok`): `#E1F5EE` bg, `#9FE1CB` border, `#085041` text — "✓ {child_name} is on track this week"
- **Amber** (`sb-warn`): `#FAEEDA` bg, `#FAC775` border, `#633806` text — "⚠ {child_name} needs some attention"
- **Red** (`sb-danger`): `#FAECE7` bg, `#F5C4B3` border, `#712B13` text — "⚠ {child_name} needs urgent attention"
- Action button on right: coloured to match banner (`#1D9E75` / `#EF9F27` / `#D85A30`)

### Due soon strip
- White bg, `#FAC775` border, amber left border (3px)
- "Upcoming for {child_name}" title in amber caps
- Each item: name (bold) + source below, badge right (red "Tomorrow" or amber)

### Course cards
- Blue top border (`#185FA5`) for structured, purple (`#534AB7`) for open
- Alert rows: red for weak topics (`ca-warn`), amber for due items (`ca-amber`), green for sessions (`ca-ok`)
- Footer: "View progress" button (`#BA7517` amber) + "Last: {date}" ghost

### Weekly report card
- White card, grey border
- "View last report" ghost button + "Get report now" amber button

---

## P02 — Progress Tab

### Layout: two-column (main | 240px sidebar)

### Subject cards (main)
- One card per enrollment
- Header: icon, enrollment name, source meta, overall % (colour: green ≥75%, amber 50–74%, red <50%)
- Topic rows:
  - Topic name (13px medium) + plain-language description (12px grey)
  - Status badge right: `mb-good` (green "Doing well"), `mb-ok` (amber "On track"), `mb-low` (red "Needs attention"), `mb-new` (grey "Not started")
  - "Explain this" button (shown only for `mb-low`): `#FAEEDA` bg, `#633806` text, amber border

### hAITU summary card (sidebar)
- Header: dark brown (`#3D2000`) bg, "hA" avatar (`#BA7517`), "hAITU summary" title, "Plain language for parents" sub
- Body: plain-language paragraph — **never contains raw scores or percentages**
- Teacher response mention: if a teacher has replied to a doubt, bold sentence added: "{teacher_name} responded to a doubt about {topic_name} — the teacher's reply is in the doubt thread."
- Three action buttons (`ais-btn`): `#FAEEDA` bg, `#633806` text, amber border. Hover: `#BA7517` bg, white

### Activity timeline (sidebar, below AI card)
- Each item: coloured dot (8px) + vertical line + text + time
- Dot colours: `tl-dot-ok` green (`#1D9E75`), `tl-dot-warn` amber (`#EF9F27`), `tl-dot-info` blue (`#378ADD`), `tl-dot-study` amber-brown (`#BA7517`), `tl-dot-teacher` green (`#0F6E56`)
- Teacher response entries: `#f2fbf7` bg row, `#085041` text, bold, "· New response" tag in `#0F6E56`

---

## P03 — Assessments Tab

### Stat row (3 cards)
- Average score (colour-coded: ≥70% green, ≥55% amber, <55% red)
- Improving topics (green)
- Upcoming (amber)

### Assessment items
- **Upcoming**: `at-upcoming` class — amber left border (`#EF9F27`), amber icon bg (`#FAEEDA`)
- **Good score** (≥70%): `at-done` — green left border (`#1D9E75`), green icon bg
- **Poor score** (<70%): `at-poor` — red left border (`#D85A30`), red icon bg
- Score: large (20px bold), colour-coded: `score-good` green, `score-ok` amber, `score-poor` red
- Trend: `trend-up` green "↑ Improving", `trend-dn` red "↓ Dropped", `trend-flat` grey "→ Steady"

### Info note
- `#E6F1FB` bg, `#B5D4F4` border, `#0C447C` text
- "For detailed question-level feedback, ask their teacher directly."

---

## P04 — Teachers & Tutors Tab

### Institutional teacher card
- Grey info box (`#f5f4f0`): "To contact {teacher_name}, please reach out through {institution}." — no direct message input shown

### Tutor card
- Shows: name, role, next session, rate, topics covering
- Message thread section: "Message thread" label (10px caps grey)
- Bubbles: parent messages right (`#FAEEDA` bg), tutor messages left (`#f5f4f0` bg)
- Message input row: flex, full-width input (focus: `#BA7517` border) + "Send" button (`#BA7517` bg)

### Browse tutors card (bottom)
- `#EEEDFE` bg, `#CECBF6` border
- Title: `#3C3489`, sub: `#534AB7`
- "Browse tutors" button (`#534AB7`)

---

## P05 — Link Child (`s-link`)

### Layout
- Centred card (max 420px)
- 🔗 emoji (42px), "Link your child's account" title, sub-text
- Large code input (20px bold, `#0A1F5C` text, centre-aligned, letter-spacing 0.12em, uppercase)
- Validation message:
  - Match: `#E1F5EE` bg, `#085041` text, ✓ prefix
  - No match: `#FAECE7` bg, `#712B13` text
- "Link account" primary button (navy, disabled until valid code)
- "Skip" link (grey)
- "How does this work" info box (`#f5f4f0` bg): step-by-step instructions

---

# PART B — Institution Admin Flow

## Screen Map

| Spec ID | Prototype screen ID | Route | Render function |
|---|---|---|---|
| I01 | `s-home` | `/institution` | `renderHome()` |
| I02 | `s-curr` | `/institution/curriculum` | `renderCurr()` |
| I03 | `s-people` | `/institution/people` | `renderPeople()` |
| I04 | `s-classes` | `/institution/classes` | `renderClasses()` |
| I05 | `s-analytics` | `/institution/analytics` | `renderAnalytics()` |
| I06 | `s-class-detail` | `/institution/classes/:class_id` | `renderClassDetail()` |

---

## Topbar
- Background: `#0D1B2A` (near-black navy)
- Left: "hAIsir" brand, institution name (small grey), "Institution Admin" role pill (amber tint `rgba(255,165,0,.2)`, `#FAC775` text)
- Right: "+ New class" button (`#185FA5` bg), avatar (`#378ADD`)

## Main Nav Tabs
- White bg, `#e5e3dc` bottom border
- Five tabs: Dashboard / Classes / Curriculum / People / Analytics
- Badge on Classes tab: count of classes with no teacher
- Badge on People tab: count of pending teacher invites
- Active: `#0D1B2A` bottom border (2.5px), `#1a1a18` text

---

## I01 — Home Dashboard (`s-home`)

### Stat row (5 cards)
- Teachers (green left), Students (green), Active classes (green or amber if no-teacher > 0), School avg % (green ≥70% / amber), At-risk (red left if > 0)
- `ok-card`: green left border, `warn-card`: amber, `alert-card`: red

### Action required strip
- `#FAEEDA` bg, `#FAC775` border, amber left border (3px)
- "⚠ Issues to resolve" title in amber caps
- Each alert item: text + sub + "Fix now →" link (blue)
- Items: class without teacher → fix in /classes; students without parent → fix in /people; at-risk → fix in /analytics

### Quick action cards (2×2 grid)
- White cards, hover: `#0D1B2A` border

### Classes overview
- First 4 class cards + "View all →" link

---

## I04 — Classes Manager (`s-classes`)

### Class card colour coding (top border)
- `ok-border`: `#1D9E75` green — on track (avg ≥65%)
- `warn-border`: `#EF9F27` amber — needs attention (avg 50–64%)
- `danger-border`: `#D85A30` red — at risk (avg <50%)
- No colour / grey: no teacher assigned (`new`)

### Card status badge
- "On track" (`b-ok`): `#E1F5EE` / `#085041`
- "Attention" (`b-warn`): `#FAEEDA` / `#633806`
- "At risk" (`b-danger`): `#FAECE7` / `#712B13`
- "No teacher" (`b-new`): `#F1EFE8` / `#5F5E5A`

### No teacher state in card
- Teacher row shows: `⚠ No teacher assigned` in `#993C1D` italic

---

## I05 — Analytics Dashboard (`s-analytics`)

### First stat row (5 cards) — existing
- School avg, Students, At-risk, Assignment completion, Assessments run

### Second stat row (4 cards) — doubt metrics ← **not in spec, only in UI**
- "Doubts raised this month" / "Resolved by hAITU %" (green) / "Escalated to teacher %" (amber) / "Escalations resolved %" (green)
- `grn-left`: green left border. `amb-left`: amber.

### Charts grid (2×3)
1. Subject performance (horizontal bars)
2. Weakest topics (horizontal bars)
3. Teacher class averages + disclaimer note
4. **Doubt resolution by teacher** — % replied within 24hrs per teacher. Low performers noted.
5. Cohort comparison (grade-level cards)
6. **Most escalated topics** — count bars with note "High counts = gaps in hAITU board content"

### Chart bar colours
- ≥75%: `#1D9E75` green
- 50–74%: `#EF9F27` amber
- <50%: `#D85A30` red

### At-risk students table
- Below charts — students below 50% progress across multiple topics

---

# PART C — Admin (SuperAdmin) Flow

## Screen Map

| Spec ID | Prototype screen ID | Route | Render function |
|---|---|---|---|
| SA01 | `s-dashboard` | `/admin` | `renderDashboard()` |
| SA02 | `s-boards` | `/admin/boards` | `renderBoards()` |
| SA03 | `s-institutions` | `/admin/institutions` | `renderInstitutions()` / `switchTab()` |
| SA04 | `s-tutors` | `/admin/tutors` | `renderTutors()` / `switchTab()` |
| SA05 | `s-users` | `/admin/users` | `renderUsers()` |
| SA06 | `s-settings` | `/admin/settings` | `renderSettings()` |

---

## Topbar
- Background: `#080F17` (near-black), `rgba(255,255,255,.06)` bottom border
- Left: "hAIsir" brand, "Platform console" label (35% opacity), "Super Admin" role pill (`rgba(210,40,40,.25)` bg, `#F09595` text, red border)
- Right: "System status" button, avatar (`#E24B4A` red)

## Left Sidebar Nav
- `#080F17` bg, `rgba(255,255,255,.06)` right border
- Items: Dashboard / Board content / Institutions (badge: pending count) / Tutor marketplace (badge: pending+flagged) / Users & roles / Platform settings
- Active item: `rgba(255,255,255,.1)` bg, white label
- Inactive: 60% opacity label
- Badge: `rgba(210,40,40,.4)` bg, `#F09595` text

---

## SA01 — Platform Dashboard (`s-dashboard`)

### First stat row (5 cards) — existing
- Active institutions (green) / Total students (green) / Teachers (green) / Pending institution approvals (amber) / Suspended tutors (red)

### Second stat row (4 cards) — AI health metrics ← **not in spec, only in UI**
- "hAITU resolution rate" (green, `#1D9E75`) / "Total doubts this month" / "Escalation rate %" (amber) / "Teacher resolution rate %" (green)
- `grn-left`: green left border. `amb-left`: amber.

### Charts (2×2 first grid)
- Board adoption (count bars)
- Weakest topics platform-wide (% bars)

### Charts (2×2 second grid) — ← **not in spec, only in UI**
1. **Most escalated topics** — count bars with note "High counts = gaps in hAITU board content for these topics."
2. **hAITU resolution rate by board** (NCERT/JNV/CBE %) — amber warning card if any board < 80%: "⚠ {board} at {N}% — lowest resolution rate. Consider reviewing and enriching {board} content."

### Institution health table + Activity feed
- Two-column layout below charts
- Activity feed: dot (green/amber/red/blue) + text + time

---

## SA02 — Board Content Manager (`s-boards`)

### Board tabs (above tree)
- Board name + version pill (green `#E1F5EE`/`#085041` if live, amber if draft) + "+ Board" tab

### Tree nodes
- Live dot: `pub-dot-live` — `#1D9E75` (6px circle)
- Draft dot: `pub-dot-draft` — `#EF9F27`

### Adoption count pill
- `#E6F1FB` bg, `#185FA5` text — "N institutions"

### Publish impact modal (`m-publish-board`)
- Amber warning box: "⚠ {N} institutions are using {board}. Publishing will update their adopted curriculum. Custom changes will be preserved."
- Version notes textarea
- Notify preference dropdown

### Adoption summary (below tree)
- 4 stat cards: total adoptions + one per board

---

## SA03 — Institution Manager (`s-institutions`)

### Pending tab — review cards
- Each pending institution: avatar, name, board/city/plan, "Pending review" badge
- Two action buttons: "Reject" (outline) + "Approve & invite admin" (navy)

### Active/Inactive tab — data table
- Plan badge colours: `b-navy` Enterprise, `b-blue` School, `b-new` Starter
- Health badges: `b-ok` Healthy, `b-warn` Review, `b-danger` At risk, `b-new` New
- Row actions: "View" + "Deactivate" (red outline button)

---

## SA06 — Platform Settings (`s-settings`)

### Toggle buttons
- Off: `#e5e3dc` bg, pill slides left
- On: `#080F17` bg (near-black), pill slides right
- Transition: 0.2s

### Danger zone
- `#FCEBEB` bg, `#F7C1C1` border
- "⚠ Danger zone" title in `#A32D2D`
- Row items with "Enable" / "Purge logs" red buttons
- Purge requires 2FA confirmation — do not implement without 2FA check
