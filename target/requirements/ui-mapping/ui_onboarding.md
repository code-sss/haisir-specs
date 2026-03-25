# hAIsir — UI Mapping: Onboarding Flow
> Maps requirement screen IDs to prototype screens and documents UX details.
> → Prototype file: `haisir_onboarding_flow.html`
> → Spec file: `09_onboarding.md`

---

## Screen Map

| Spec ID | Prototype screen ID | Render / navigation |
|---|---|---|
| ON01 | `s-keycloak` | Keycloak-native — no custom screen. Prototype shows a placeholder. |
| ON02 | `s-roles` | `buildGrid()` + `pickRole()` (single-select) |
| ON03 | `s-setup-student` | Role queue `advance()` → `buildStuCTAs()` |
| ON04 | ~~`s-setup-teacher`~~ | **Removed from onboarding** — instructors are invited by institution_admin |
| ON05 | `s-setup-parent` | Role queue `advance()` → `buildParCTAs()` |
| ON06 | ~~`s-setup-tutor`~~ | **Removed from onboarding** — separate "Become a tutor" flow |
| ON07 | `s-switcher` | `buildReady()` (single-role users go straight to ready) |
| ON08 | `s-ready` | Static success screen |

---

## General Design

### Topbar (all onboarding screens)
- Background: `#0A1F5C` (navy)
- Left: "hAIsir" brand, "Think and try, learn with hAI" tagline (40% opacity, left border divider)
- Right: "Already have an account? Log in →" link (login screen: "New here? Create account →")

### Progress dots (ON02–ON05)
- 8px circles, gap 8px
- Done steps: `#1D9E75` (green)
- Active step: `#0A1F5C` (navy), 24px width (pill shape), 4px border-radius
- Future steps: `#e5e3dc` (grey)

### Card container
- White bg, `#e5e3dc` border, 18px border-radius
- Padding: 36px 40px
- Max-width: 500px (wide variant: 640px for role grid and multi-role)
- Centre-aligned vertically and horizontally

### Form inputs
- Font-size: 14px
- Border: 0.5px `#d3d1c7`
- Border-radius: 8px
- Focus: `#0A1F5C` border + `rgba(10,31,92,.06)` box-shadow
- Background: `#fafaf8`

### Primary button
- `#0A1F5C` bg, white text, 14px bold, 13px padding, 9px border-radius, full width
- Hover: `#162d7a`
- Disabled: `#b4b2a9` bg, not-allowed cursor

---

## ON01 — Keycloak Login (`s-keycloak`) — not a custom screen

No custom frontend screen. APISIX redirects unauthenticated users to Keycloak's native login page. Keycloak renders its own UI (email/password + Google SSO). The prototype shows a placeholder screen with a "Simulate login →" button for navigation purposes only.

---

## ON02 — Role Selection (`s-roles`)

**Single-select only (BR-ON-005).** Shows exactly two role cards: Student and Parent/Guardian. Instructor and Tutor are not shown here.

### Role grid (1×2)
- Two role cards: Student / Parent/Guardian
- Card: 1.5px `#e5e3dc` border, 12px border-radius, 18px 16px padding, flex-column
- Selected: role-colour border + tinted background (student: `#185FA5` / `#f4f8fd`; parent: `#BA7517` / `#fdf8f2`)
- Check circle (top-right): empty when unselected, role-colour fill + ✓ when selected
- Role icons: 26px emoji
- Continue button disabled until one card is selected
- Info note below grid: "Teacher or tutor? Instructors are invited by their institution admin. Independent tutors register via 'Become a tutor' after signing up."

---

## ON03 — Student Ready (`s-setup-student`)

No form fields. Populated via `buildStuCTAs()`.

### Layout
- Party popper emoji (🎉), 52px, top centre
- `h1`: "You're all set, there!" — bold, `#0A1F5C`
- Subtext: "Your Student account is ready. Here's what to do first." — 13px, `#888780`
- Role badge: `font-size: 12px`, `font-weight: 600`, `padding: 5px 14px`, `border-radius: 20px`, `background: #f0f4ff`, `color: #0A1F5C`

### CTA cards (action rows)
- Full-width, stacked vertically, gap 8px
- Each card: `border: 0.5px solid #e5e3dc`, `border-radius: 10px`, `padding: 13px 16px`, flex row
- Left: 32px icon emoji
- Centre: bold title (role colour) + grey subtitle (11px `#888780`)
- Right: `→` arrow in role colour, `margin-left: auto`
- Hover: `translateY(-2px)` + light box-shadow
- Card 1 bg: `#E6F1FB`, title colour: `#185FA5`
- Card 2 bg: `#EEEDFE`, title colour: `#534AB7`

### Skip link
- Below cards: "Skip — go to dashboard" — 11px, `#b4b2a9`, cursor pointer

---

## ON04 — Teacher Setup — **REMOVED FROM ONBOARDING**

> Instructors are invited by institution_admin. Profile setup happens inline on first login to the teacher dashboard. No prototype screen.

---

## ON05 — Parent Ready (`s-setup-parent`)

No form fields. Populated via `buildParCTAs()`. Same layout pattern as ON03.

### Layout
- Party popper emoji (🎉), 52px, top centre
- `h1`: "You're all set, there!" — bold, `#0A1F5C`
- Subtext: "Your Parent / Guardian account is ready. Here's what to do first." — 13px, `#888780`
- Role badge: `background: #fdf8f2`, `color: #BA7517`, same pill style as ON03

### CTA card
- Single card: bg `#FAEEDA`, title colour `#BA7517`
- Icon: 🔗, Title: "Link your child", Subtitle: "Enter their hAIsir link code"
- Hover: `translateY(-2px)` + light box-shadow

### Skip link
- "Skip — link later from dashboard" — 11px, `#b4b2a9`, cursor pointer

---

## ON07 — Role Switcher (`s-switcher`)

### Topbar colour changes on switch
- Student: `#0A1F5C`
- Teacher/instructor: `#0A3D2B`
- Tutor: `#3C1F6E`
- Parent: `#3D2000`
- Admin: `#080F17`

### Role cards grid
- 4 cards max, flex-wrap, justify-content: center
- Width: 140px each
- Active card: `#0A1F5C` border, `#f4f7fd` bg, box-shadow, "Active" pill (`#E6F1FB` / `#185FA5`)
- Inactive: hover → translate up 2px

### Switcher pills in topbar
- Active pill: `rgba(255,255,255,.25)` bg, white text, bold
- Inactive pills: `rgba(255,255,255,.1)` bg, 60% opacity text

### Explanation card
- White bg, `#e5e3dc` border, 14px border-radius
- "About role switching" title + explanation paragraph

---

## Persistent Role Switcher (post-onboarding)

After onboarding, the role switcher lives in the topbar on every screen for multi-role users.

### Topbar integration
- "Switch role:" label (small, 50% opacity) + pill buttons for each role
- Active pill: `rgba(255,255,255,.25)` bg, white bold text
- Inactive pills: `rgba(255,255,255,.1)` bg, 60% opacity text
- On click: `switchRole(id)` → updates topbar bg colour + re-renders workspace

### Single-role users
- No switcher shown — clean topbar without role pills
