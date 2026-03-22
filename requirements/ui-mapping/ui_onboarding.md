# hAIsir — UI Mapping: Onboarding Flow
> Maps requirement screen IDs to prototype screens and documents UX details.
> → Prototype file: `haisir_onboarding_flow.html`
> → Spec file: `09_onboarding.md`

---

## Screen Map

| Spec ID | Prototype screen ID | Render / navigation |
|---|---|---|
| ON01 | `s-signup` / `s-login` | Static HTML + `checkSignup()` |
| ON02 | `s-roles` | `buildGrid()` |
| ON03 | `s-setup-student` | Role queue `advance()` |
| ON04 | `s-setup-teacher` | Role queue `advance()` |
| ON05 | `s-setup-parent` | Role queue `advance()` |
| ON06 | `s-setup-tutor` | Role queue `advance()` |
| ON07 | `s-switcher` | `renderSwitcher()` |
| ON08 | `s-ready` | Static success screen |

---

## General Design

### Topbar (all onboarding screens)
- Background: `#0A1F5C` (navy)
- Left: "hAIsir" brand, "Think and try, learn with hAI" tagline (40% opacity, left border divider)
- Right: "Already have an account? Log in →" link (login screen: "New here? Create account →")

### Progress dots (ON02–ON06)
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

## ON01 — Welcome / Sign-up (`s-signup`)

### Google SSO button
- White bg, `#d3d1c7` border, "G" icon (18px), "Continue with Google" label
- Full width

### OR divider
- Horizontal lines + "or with email" centre text (11px grey)

### Validation
- "Create account" button enabled only when: name non-empty + email non-empty + password ≥ 8 chars
- `checkSignup()` fires on `oninput` of each field

---

## ON02 — Role Selection (`s-roles`)

### Role grid (2×2)
- Four role cards: Student / Teacher+Tutor / Parent / Multi-role
- Card: 1.5px `#e5e3dc` border, 12px border-radius, 20px 18px padding, flex-column
- Selected: `#0A1F5C` border, `#f4f7fd` bg, `rgba(10,31,92,.07)` box-shadow
- Check circle (top-right): empty when unselected, `#0A1F5C` fill + ✓ when selected
- Role icons: 28px emoji
- Continue button disabled until at least one role selected

---

## ON03 — Student Setup (`s-setup-student`)

### Subject tag picker
- Pill buttons: 12px, 5px 12px padding, 20px border-radius
- Inactive: `#d3d1c7` border, `#5f5e5a` text
- Active: `#0A1F5C` bg, white text, `#0A1F5C` border
- Hover (inactive): `#0A1F5C` border + text

### Start mode selection (step 2)
- Two option cards (full-width, stacked):
  - "Join institution": blue selection (`#0A1F5C` border, `#f4f7fd` bg)
  - "Explore open courses": purple selection (`#534AB7` border, `#f7f6fe` bg)
- Check circle colours match: blue for institution, purple for open
- Invite code section (inside institution card, hidden until selected):
  - Text input + "Apply" button — live validation on input
  - Valid: `#0F6E56` green message below
  - Invalid: `#993C1D` red message
- "Get started →" button enabled only when at least one mode selected

---

## ON04 — Teacher Setup (`s-setup-teacher`)

### Teaching type selection (3 options, stacked)
- Row-direction role cards: icon + title + desc + check circle (right)
- Selected: `#0A1F5C` border + bg
- Options: Institutional teacher / Independent tutor / Both

### Continue button
- Enabled only when teaching type selected

---

## ON05 — Parent Setup (`s-setup-parent`)

### Code input
- 20px bold, `#0A1F5C` text, centre-aligned, letter-spacing 0.12em, UPPERCASE
- Focus: `#0A1F5C` border (1.5px)
- Validation message:
  - Match (`ARJUN-2026`): `#E1F5EE` bg, `#085041` text
  - No match: `#FAECE7` bg, `#712B13` text
- "Link account →" enabled only on valid code

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
