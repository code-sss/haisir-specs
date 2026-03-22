# hAIsir Specs — Human Review Checklist & Order

> **Phase 0 review complete** — commits `092c6f5` (2026-03-22) and `0cc9207` (2026-03-23). All decisions applied to specs.
> **Phase 1 review complete** — commit `8638a2a`. Persona specs finalised.

## Review Order (recommended for product owner / lead dev)

### Phase 1 — Foundation (read first, these inform everything)

- [x] `requirements/00_overview.md` — Architecture, tech stack, all 6 personas, content ownership, design decisions
  - ✅ 6 personas confirmed correct
  - ✅ Tech stack confirmed (Next.js 16, FastAPI, no Redux)
  - ✅ Content ownership model (platform/institution/tutor) confirmed complete

- [x] `requirements/01_data_model.md` — All 30+ tables, field-level rules, indexes, migrations
  - ✅ All tables reviewed — none merged, all justified
  - ✅ `owner_type`/`owner_id` on course_path_nodes, topics, exam_templates confirmed complete
  - ✅ Mastery formula confirmed — first attempt = latest_score; subsequent = 0.6×latest + 0.4×previous
  - ✅ Soft-delete patterns consistent
  - ✅ JSON fields (ruleset, tags) — kept as JSON; normalisation deferred
  - ✅ Stale `is_correct` on edited questions — UI warning accepted; no backend guard needed

- [x] `requirements/02_auth_and_roles.md` — JWT flow, CSRF, permission matrix
  - ✅ Permission matrix verified
  - ✅ 3 X-Current-Role exceptions confirmed correct (onboarding endpoints only)
  - ✅ iframe `prompt=none` — Safari ITP / Firefox ETP fallback documented in `09_onboarding.md`

- [x] `requirements/11_role_migration.md` — Adding 3 new Keycloak roles incrementally
  - ✅ Step order (Keycloak → backend → frontend) confirmed feasible
  - ✅ Multi-role combos confirmed — admin exclusivity is the only forbidden combo (BR-ROLE-004)
  - ✅ institution_admin/admin not self-assignable — enforced at API layer; Keycloak console access restricted to platform operators

### Phase 2 — Persona-by-persona (one at a time, in dependency order)

- [x] `requirements/03_student.md` — 10 screens (S01–S10), 25 business rules
  - ✅ Enrollment flow confirmed — structured (invite code) vs open (browse) is clear UX-wise
  - ✅ hAITU escalation trigger confirmed — "after first AI response" is correct (student sees response before escalate button appears)
  - ✅ Topic locking confirmed — grade comparison at API layer, edge cases covered in BR-STU-012
  - ✅ Weak threshold (<60) and completed threshold (≥75) confirmed correct

- [ ] `requirements/04_teacher_tutor.md` — 8 screens, instructor vs tutor divergence
  - Walk through T01-T08 with prototype open (`prototypes/haisir_teacher_flow.html`)
  - Verify: Instructor read-only curriculum vs tutor full control — clear enough?
  - Verify: Assignment flow (T02) — is class-level assignment sufficient?
  - Verify: Teacher notes (tutor only) — privacy implications clear?
  - ~~**Decision needed:** Tutor marketplace — immediate visibility or admin approval gate?~~ **Resolved:** Immediate on toggle, admin can suspend post-hoc. See `02_auth_and_roles.md` section 2.3.

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
  - ~~Verify: Escalation trigger phrase ("ask your teacher") — robust enough? What if AI says it differently?~~ **Resolved:** Now uses structured JSON output with `escalation_ready` flag.
  - Verify: Which interactions are cached vs generated on-demand?
  - ~~Verify: escalation trigger relies on LLM phrase match ("ask your teacher") — confirm this is robust enough or replace with structured output / sentinel token approach. Flag for Tech Lead.~~ **Resolved:** Replaced with structured JSON output.
  - Verify: escalation trigger uses structured JSON output (`escalation_ready` flag) — confirm system prompts in sections 3.1 and 3.3 enforce JSON-only responses and no phrase-match logic remains.

- [ ] `requirements/09_onboarding.md` — 6 screens (ON04/ON06 removed), business rules updated
  - Walk through ON01→ON02→ON03/ON05→ON07→ON08 with prototype (`prototypes/haisir_onboarding_flow.html`)
  - Verify: Single-select role selection — Student OR Parent only (instructor invited, tutor separate flow)
  - Verify: Google SSO + email/password — both paths tested?
  - Verify: Existing user detection — what if someone onboards, deletes cookies, re-visits?
  - Verify: "Add role later" flow from profile/settings page works (BR-ON-006a)

- [ ] `requirements/10_notifications.md` — all types, polling model, generation rules
  - Verify: 60s polling is sufficient (vs WebSocket for real-time needs)
  - Verify: Each notification type — is the trigger correct? Any missing?
  - Verify: Cron schedules (hourly due_soon, weekly digest) — timezone handling?
  - ✅ Verified: `doubt_auto_closed` (student) and `child_doubt_auto_closed` (parent) are defined in `10_notifications.md` sections 3.1 and 3.4, with generation rules in BR-NOTIF-011.

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
- [ ] Verify: all unresolved decisions in `gap-analysis.md` are resolved before implementation of their respective phases. ✅ All 9 decisions resolved — ~~pagination strategy~~, ~~file storage~~, ~~dynamic exam ruleset schema~~, ~~archived topic clone flow~~ (BR-CONTENT-005), ~~payment extensibility~~, ~~tutor marketplace gate~~, ~~mastery initial value~~, ~~search backend~~, ~~search embedding model~~ (`all-MiniLM-L6-v2`, self-hosted). No open decisions remain.
