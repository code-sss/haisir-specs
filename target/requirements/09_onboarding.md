# Onboarding

> Status: stub — to be defined based on current state.
> See `vision/requirements/09_onboarding.md` for the long-term vision spec.

---

## Pre-Phase 5 amendment — student grade step (issues 13/14)

> Added 2026-07-02 (pre-Phase-5 hardening pass). Amends BR-ON-008 for the **student** flow only;
> the parent flow is untouched. Full plan: `Implementation_planning/PLAN_PrePhase5-Hardening_2026-07-02.md` (G6).

**Problem being fixed:** The catalog `recommended` badge (Phase 3 —
`EnrollmentService.get_catalog`, `enrollment_service.py:127`) is `False` for every student until
`student_profiles.grade` is set, and **no UI ever set it** — onboarding was CTA-only (BR-ON-008),
so the only way to activate `recommended` was a manual DB insert. This made the through-Phase-4
build un-testable for the recommended-grade flow.

**Amendment to BR-ON-008 (student View B only):** Student onboarding View B (`on03-student-ready.tsx`,
the `?next=proceed` branch) collects **grade** as the one profile field gathered at onboarding,
posted to `POST /api/students/me/profile` with `{ "grade": <value> }` **before** the existing
`PATCH /api/users/me/onboarding-complete` call. All other BR-ON-008 guarantees hold — no other
profile fields, no inline code entry, no school selection form.

- **Grade picker UI:** a single `<select>` populated from the platform catalog's grade root nodes
  (`GET /api/student/catalog` filtered to `node_type === "grade"`, names rendered per
  `03_student.md` S-enroll as "Grade N" — see pre-Phase-5 G5). Free-text fallback if the catalog
  is empty. "Skip" is allowed (recommended stays off until the student sets a grade later).

  > **Known gap (found in plan review, 2026-07-02, documented not fixed):** "sets a grade later"
  > has **no UI path in pre-Phase-5** — verified there is no `/profile` route or any other screen
  > in the through-Phase-4 frontend that writes `student_profiles.grade`, and onboarding does not
  > re-run once `onboarding-complete` is set. A student who clicks "Skip" is stuck with
  > `recommended = False` until Phase 5 ships `/profile` (T1.5). Fixing this fully (disallow skip,
  > or build an earlier settings surface) is out of pre-Phase-5's small-surgical-fix scope and
  > wasn't one of the 14 reported issues, so it is documented here rather than fixed now. **Tester
  > guidance:** do not skip the grade step if you want to verify the `recommended` badge before
  > Phase 5 lands.
- **Grade value:** the platform grade root node's `name` (e.g. `"8"`), stored verbatim in
  `student_profiles.grade`. `EnrollmentService` matches case-insensitively against catalog node
  `name` (`enrollment_service.py:127`), so a stored `"8"` lights up the Grade 8 catalog card.
- **Auth:** `X-Current-Role: student` on the profile POST; the role is assigned in ON02 and the
  JWT-relogin step (View A) has run before View B, so the header is valid. Use `fetchWithCSRFRetry`
  + `buildApiHeaders` (CSRF on the mutation).
- **Editable later:** Phase 5 T1.5 builds the `/profile` page (S-profile) — pre-Phase-5 only adds
  the onboarding entry point; Phase 5 exposes the **editable** grade field on `/profile` alongside
  the link-code and linked-parents sections.

**Parent onboarding (unchanged):** BR-ON-015 holds — parent onboarding View B stays CTA-only
("Link your child" → `/parent/link-child`, "Skip"). The link-child flow is built in Phase 5 (G2);
the existing dead `/link-child` CTA in `on05-parent-ready.tsx:82` is fixed by Phase 5 T2.6. No
pre-Phase-5 parent-onboarding change. Testers should expect parent link-child to land with Phase 5.