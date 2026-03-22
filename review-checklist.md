# hAIsir Specs — Human Review Checklist & Order

## Review Order (recommended for product owner / lead dev)

### Phase 1 — Foundation (read first, these inform everything)

- [ ] `requirements/00_overview.md` — Architecture, tech stack, all 6 personas, content ownership, design decisions
  - Verify: Are the 6 personas still the right set? Any persona missing?
  - Verify: Tech stack decisions still hold (Next.js 16, FastAPI, no Redux)?
  - Verify: Content ownership model (platform/institution/tutor) covers all cases?

- [ ] `requirements/01_data_model.md` — All 30+ tables, field-level rules, indexes, migrations
  - Verify: Each new table — is it truly needed? Can any be merged?
  - Verify: `owner_type`/`owner_id` on course_path_nodes, topics, exam_templates — complete?
  - Verify: Mastery formula `(0.6 * latest + 0.4 * previous)` — is this pedagogically sound?
  - Verify: Soft-delete patterns — consistent across entities?
  - Verify: JSON fields (ruleset, tags) — should any be normalized tables instead?

- [ ] `requirements/02_auth_and_roles.md` — JWT flow, CSRF, permission matrix
  - Verify: Permission matrix — every cell (role x resource x action) is correct
  - Verify: 3 exceptions to `X-Current-Role` requirement — are these the right exceptions?
  - Verify: Token refresh via iframe `prompt=none` — tested with all browsers?

- [ ] `requirements/11_role_migration.md` — Adding 3 new Keycloak roles incrementally
  - Verify: Order of steps (Keycloak -> backend -> frontend) is feasible
  - Verify: Multi-role combos (9 listed) — any missing? Any that should be forbidden?
  - Verify: institution_admin/admin are NOT self-assignable — is this enforced at Keycloak level too?

### Phase 2 — Persona-by-persona (one at a time, in dependency order)

- [ ] `requirements/03_student.md` — 11 screens, 18 business rules
  - Walk through S01-S10 with prototype open (`prototypes/haisir_student_flow.html`)
  - Verify: Enrollment flow (structured vs open) makes sense UX-wise
  - Verify: hAITU escalation flow — is "after first AI response" the right trigger?
  - Verify: Topic locking logic (grade comparison) — edge cases?
  - Verify: Weak threshold (<60) and completed threshold (>=75) — correct?

- [ ] `requirements/04_teacher_tutor.md` — 8 screens, instructor vs tutor divergence
  - Walk through T01-T08 with prototype open (`prototypes/haisir_teacher_flow.html`)
  - Verify: Instructor read-only curriculum vs tutor full control — clear enough?
  - Verify: Assignment flow (T02) — is class-level assignment sufficient?
  - Verify: Teacher notes (tutor only) — privacy implications clear?
  - **Decision needed:** Tutor marketplace — immediate visibility or admin approval gate?

- [ ] `requirements/05_06_07_personas.md` — Parent (5 screens), Institution Admin (6), Platform Admin (6)
  - Walk through each set with respective prototypes open
  - **Parent:** Verify plain-language descriptions are feasible at scale (daily cache per child)
  - **Parent:** Verify "no question-level detail" is the right boundary (vs showing question text without answers)
  - **Institution Admin:** Verify aggregate-only access is sufficient (teachers may want admin to see specifics)
  - **Platform Admin:** Verify SA05 feature flags cover the right set (6 flags listed)

### Phase 3 — Cross-cutting concerns

- [ ] `requirements/08_haitu_ai_layer.md` — 8 interaction types, prompt contracts, token limits
  - Verify: Token limits per interaction (200-800) — are these sufficient for quality responses?
  - Verify: `claude-sonnet-4-6` as default — cost implications at scale?
  - Verify: Escalation trigger phrase ("ask your teacher") — robust enough? What if AI says it differently?
  - Verify: Which interactions are cached vs generated on-demand?

- [ ] `requirements/09_onboarding.md` — 8 screens, 29 business rules
  - Walk through ON01-ON08 with prototype (`prototypes/haisir_onboarding_flow.html`)
  - Verify: Multi-role selection UX — user selects up to 4 roles, sees forms for each sequentially
  - Verify: Google SSO + email/password — both paths tested?
  - Verify: Existing user detection — what if someone onboards, deletes cookies, re-visits?

- [ ] `requirements/10_notifications.md` — 22 types, polling model, generation rules
  - Verify: 60s polling is sufficient (vs WebSocket for real-time needs)
  - Verify: Each of 22 notification types — is the trigger correct? Any missing?
  - Verify: Cron schedules (hourly due_soon, weekly digest) — timezone handling?
  - ~~**Missing:** Notification for doubt auto-close (7 days)~~ **Present:** `doubt_auto_closed` (student) and `child_doubt_auto_closed` (parent) are defined in `10_notifications.md` sections 3.1 and 3.4, with generation rules in BR-NOTIF-011.

### Phase 4 — Visual & UX validation

- [ ] `requirements/ui-mapping/ui_student.md`
- [ ] `requirements/ui-mapping/ui_teacher.md`
- [ ] `requirements/ui-mapping/ui_parent_institution_admin.md`
- [ ] `requirements/ui-mapping/ui_onboarding.md`
- [ ] `requirements/ui-mapping/ui_notifications.md`
  - For each: open prototype HTML side-by-side, verify screen-by-screen
  - Check: colour values match persona definitions in `00_overview.md`
  - Check: component states (loading, empty, error) are specified
  - Check: responsive/mobile behaviour is addressed (or explicitly deferred)

### Phase 5 — Final cross-check

- [ ] Re-read permission matrix in `02_auth_and_roles.md` after understanding all personas
- [ ] Verify every API endpoint mentioned in specs has a corresponding permission entry
- [ ] Verify every notification type has a clear generation trigger and recipient
- [ ] Check for orphan business rules (referenced but not defined, or defined but never referenced)
