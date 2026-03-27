# hAIsir — Product Backlog

> Unscoped items that need spec work before implementation. Add new items here with a date, status, and enough context to pick up later. Do not implement without first moving to a requirements spec.

---

## Format

```
### BL-NNN — Short Title
**Raised:** YYYY-MM-DD
**Status:** Unscoped | Speccing | Ready | Deferred
**Related specs:** list of relevant requirement files

Context and open questions.
```

---

## Items

### BL-001 — Post-Onboarding Secondary Role Addition (Student ↔ Parent)
**Raised:** 2026-03-26
**Status:** Unscoped
**Related specs:** `09_onboarding.md` (BR-ON-006a), `11_role_migration.md` §6.1 + §8, `02_auth_and_roles.md` §4

**Context:**
ON02 is single-select — users pick Student OR Parent during onboarding. BR-ON-006a already states that a user can add the other role later from their profile/settings page via `POST /api/users/me/assign-role`, triggering an inline setup flow. However, no screens or UI spec exist for this path.

**What needs to be spec'd:**
- The profile/settings page entry point — where does the user discover "Add role"? (user menu? settings page? dedicated section?)
- Inline setup flow for adding `parent` role to an existing student account:
  - What does the user see? (a condensed ON05-equivalent step, or just a confirmation?)
  - Token refresh handling after assignment (same iframe mechanism as onboarding)
  - Redirect after completion — back to profile or to parent dashboard?
- Inline setup flow for adding `student` role to an existing parent account:
  - Same questions as above
- Edge case: user already holds the target role (e.g. somehow has `student` already) — graceful no-op or informational message
- Screen IDs for any new inline screens (follow `ON__` naming or introduce `PROF__` namespace?)

**Open questions:**
- Should this be a modal/sheet inline on the current page, or a full-page flow?
- Does adding `parent` role prompt the user to immediately link a child, or is that deferred to the parent dashboard?
- Is there a settings page spec planned at all? If not, this item may need a broader "Account settings" screen to be spec'd first.
