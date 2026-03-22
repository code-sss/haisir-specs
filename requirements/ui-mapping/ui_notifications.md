# hAIsir — UI Mapping: Notifications
> Maps requirement spec to prototype and documents UX details.
> → Prototype file: `haisir_notifications.html`
> → Spec file: `10_notifications.md`

---

## Screen Map

The notifications centre is a single screen with a persona switcher at the top.

| Spec section | Prototype element | Notes |
|---|---|---|
| All personas | `activePersona` state + `render()` | Switching persona re-renders the feed |
| Notification items | `renderItem(n, accent, isUnread)` | Per-item rendering |
| Filter tabs | `FILTERS[activePersona]` | Per-persona filter sets |
| Unread state | `readSet[activePersona]` | Set of read notification IDs |

**Route:** `/notifications`

---

## Overall Layout

### Topbar
- Background changes per active persona:
  - Student: `#0A1F5C`
  - Teacher: `#0A3D2B`
  - Parent: `#3D2000`
  - Institution Admin: `#0D1B2A`
  - Admin: `#080F17`
- Left: "hAIsir" brand, persona name label
- Right: "Mark all read" button (ghost), avatar

### Persona switcher strip
- One tab per persona
- Each tab: persona icon (16px emoji) + label + unread badge (red pill, shown only when > 0)
- Active tab: bottom border colour matches persona topbar colour
- Inactive: grey label

### Notification feed (below tabs)
- Max-width: 680px, centred
- Filter tabs per persona (below main persona switcher):
  - Small pill tabs, active = filled with persona accent colour
- Grouped sections: "Today" / "Yesterday" / "Earlier this week" / "Older"
- Section label: 10px caps, `#b4b2a9`

---

## Notification Item Layout

### Unread item
- Left border: 3px solid accent colour
- Class per persona: `unread` (student blue), `unread-teacher` (green), `unread-parent` (amber), `unread-admin` (navy), `unread-super` (red)
- Slightly elevated appearance vs read items

### Read item
- No left border
- Same white bg, `#e5e3dc` border

### Item structure
- Icon area (38×38px, 9px border-radius): emoji or type icon on coloured bg
- Main area:
  - Title (13px medium): first line of notification — key entity names in `<strong>`
  - Body (12px, `#5f5e5a`): detail text
  - Meta row: time (11px grey) + source pill (10px, coloured)
- Action buttons row (when applicable): right-aligned, small ghost buttons

### Inline action buttons
- 11px, `#d3d1c7` border, ghost style
- Hover: `#f0efe9` bg
- "Reply now →", "View results →", "Review →", "Assign teacher →"

---

## Per-Persona Accent Colours

| Persona | Accent / unread border | Source pill bg | Source pill text |
|---|---|---|---|
| Student | `#185FA5` blue | `#E6F1FB` | `#185FA5` |
| Teacher | `#0F6E56` teal | `#E1F5EE` | `#085041` |
| Parent | `#BA7517` amber | `#FDF4E3` | `#854F0B` |
| Institution Admin | `#0D1B2A` navy | `#e8ebf0` | `#0D1B2A` |
| Admin | `#E24B4A` red | `#FCEBEB` | `#A32D2D` |

---

## Filter Tabs

### Student filters
- All / Doubts / Assessments / Content
- Active filter: `#185FA5` bg, white text
- Counts in parentheses

### Teacher filters
- All / Doubts / Exams / Alerts

### Parent filters
- All / {child_name_1} / {child_name_2} (one per linked child)
- Dynamic based on linked children

### Institution Admin filters
- All / Classes / People / Curriculum

### Admin filters
- All / Institutions / Tutors / System

---

## Notification Type Icons and Backgrounds

| Type | Icon | Icon bg |
|---|---|---|
| `doubt_teacher_replied` | 💬 | `#E6F1FB` (blue) |
| `assessment_due_soon` | 📅 | `#FAEEDA` (amber) |
| `assessment_results_ready` | 📊 | `#E1F5EE` (green) |
| `topic_marked_weak` | ⚠️ | `#FAECE7` (red) |
| `new_content_uploaded` | 📚 | `#E6F1FB` (blue) |
| `new_doubt_escalated` | 📬 | `#FAEEDA` (amber) |
| `class_exam_submitted` | 📋 | `#E1F5EE` (green) |
| `student_at_risk` | 🚨 | `#FAECE7` (red) |
| `child_doubt_replied` | 💬 | `#E1F5EE` (green) |
| `child_assessment_due` | 📅 | `#FAEEDA` (amber) |
| `child_weekly_digest` | 📈 | `#FDF4E3` (amber-warm) |
| `child_streak_milestone` | 🎉 | `#E1F5EE` (green) |
| `class_no_teacher` | ⚠️ | `#FAEEDA` (amber) |
| `student_at_risk_admin` | 📉 | `#FAECE7` (red) |
| `teacher_invite_accepted` | ✅ | `#E1F5EE` (green) |
| `board_content_updated` | 📚 | `#E6F1FB` (blue) |
| `institution_registration` | 🏫 | `#FAEEDA` (amber) |
| `tutor_published` | 👤 | `#E6F1FB` (blue) |
| `haitu_resolution_dropped` | 📉 | `#FAECE7` (red) |
| `board_publish_confirmed` | ✅ | `#E1F5EE` (green) |

---

## Empty State

- Icon: 🔔 (large, 40px)
- Title: "You're all caught up"
- Sub: "No notifications yet" or "No {filter} notifications"
- Shown when filtered list is empty or no notifications exist at all

---

## Mark All Read

- Button in topbar: "Mark all read"
- On click: all items in current persona+filter lose unread styling
- Badge count on persona tab updates to 0
- Does not affect other personas' unread counts
