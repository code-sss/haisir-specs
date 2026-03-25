# hAIsir Specs — Human Review Checklist & Order

> **Phase 0 review complete** — commits `092c6f5` (2026-03-22) and `0cc9207` (2026-03-23). All decisions applied to specs.
> **Phase 1 review complete** — commit `8638a2a`. Persona specs finalised.

## Review Order (recommended for product owner / lead dev)

### Phase 1 — Foundation (read first, these inform everything)

- [x] `target/requirements/00_overview.md` — Architecture, tech stack, all 6 personas, content ownership, design decisions
  - ✅ 6 personas confirmed correct
  - ✅ Tech stack confirmed (Next.js 16, FastAPI, no Redux)
  - ✅ Content ownership model (platform/institution/tutor) confirmed complete

- [x] `target/requirements/01_data_model.md` — All 30+ tables, field-level rules, indexes, migrations
  - ✅ All tables reviewed — none merged, all justified
  - ✅ `owner_type`/`owner_id` on course_path_nodes, topics, exam_templates confirmed complete
  - ✅ Mastery formula confirmed — first attempt = latest_score; subsequent = 0.6×latest + 0.4×previous
  - ✅ Soft-delete patterns consistent
  - ✅ JSON fields (ruleset, tags) — kept as JSON; normalisation deferred
  - ✅ Stale `is_correct` on edited questions — UI warning accepted; no backend guard needed

- [x] `target/requirements/02_auth_and_roles.md` — JWT flow, CSRF, permission matrix
  - ✅ Permission matrix verified
  - ✅ 3 X-Current-Role exceptions confirmed correct (onboarding endpoints only)
  - ✅ iframe `prompt=none` — Safari ITP / Firefox ETP fallback documented in `09_onboarding.md`

- [x] `target/requirements/11_role_migration.md` — Adding 3 new Keycloak roles incrementally
  - ✅ Step order (Keycloak → backend → frontend) confirmed feasible
  - ✅ Multi-role combos confirmed — admin exclusivity is the only forbidden combo (BR-ROLE-004)
  - ✅ institution_admin/admin not self-assignable — enforced at API layer; Keycloak console access restricted to platform operators

### Phase 2 — Persona-by-persona (one at a time, in dependency order)

- [x] `target/requirements/03_student.md` — 10 screens (S01–S10), 25 business rules
  - ✅ Enrollment flow confirmed — structured (invite code) vs open (browse) is clear UX-wise
  - ✅ hAITU escalation trigger confirmed — "after first AI response" is correct (student sees response before escalate button appears)
  - ✅ Topic locking confirmed — grade comparison at API layer, edge cases covered in BR-STU-012
  - ✅ Weak threshold (<60) and completed threshold (≥75) confirmed correct

- [x] `target/requirements/04_teacher_tutor.md` — 8 screens, instructor vs tutor divergence
  - ✅ Instructor read-only curriculum vs tutor full control — clear. BR-TCH-025, BR-TCH-026 added.
  - ✅ Assignment flow (T02) — class-level assignment confirmed sufficient.
  - ✅ Teacher notes (tutor only) — absolute privacy confirmed, no admin override in v1 (BR-TCH-009).
  - ✅ Teacher reply edit window — 5-minute window added (BR-DOUBT-011).
  - ✅ Exam results while open — two-state model added (BR-TCH-020).
  - ✅ "Generate remedial assignment" — deferred to Phase 2 (T08 phase note added).
  - ~~**Decision needed:** Tutor marketplace — immediate visibility or admin approval gate?~~ **Resolved:** Immediate on toggle, admin can suspend post-hoc. See `02_auth_and_roles.md` section 2.3.

- [x] `target/requirements/05_06_07_personas.md` — Parent (5 screens), Institution Admin (6), Platform Admin (6)
  - ✅ **Parent:** Plain-language descriptions — Phase 1 static fallback added (BR-PAR-006); hAITU in Phase 2.
  - ✅ **Parent:** "No question-level detail" confirmed correct (BR-PAR-009). Status banner thresholds refined (BR-PAR-004). Max 10 children added (BR-PAR-016).
  - ✅ **Institution Admin:** Aggregate-only access confirmed (BR-INST-007, BR-INST-015). CSV invite-link enrollment added (BR-INST-017). Analytics periods added.
  - ✅ **Platform Admin:** 6 feature flags confirmed: marketplace, open_learning, parent_portal, public_tutor_profiles, haitu_enabled_global, institution_self_registration. SA03 pending tab removed for Phase 1. Retention period configurable (BR-SA-018).

### Phase 3 — Cross-cutting concerns

- [ ] `target/requirements/08_haitu_ai_layer.md` — 8 interaction types, prompt contracts, token limits
  - Verify: Token limits per interaction (200-800) — are these sufficient for quality responses?
  - Verify: `claude-sonnet-4-6` as default — cost implications at scale?
  - ~~Verify: Escalation trigger phrase ("ask your teacher") — robust enough? What if AI says it differently?~~ **Resolved:** Now uses structured JSON output with `escalation_ready` flag.
  - Verify: Which interactions are cached vs generated on-demand?
  - ~~Verify: escalation trigger relies on LLM phrase match ("ask your teacher") — confirm this is robust enough or replace with structured output / sentinel token approach. Flag for Tech Lead.~~ **Resolved:** Replaced with structured JSON output.
  - Verify: escalation trigger uses structured JSON output (`escalation_ready` flag) — confirm system prompts in sections 3.1 and 3.3 enforce JSON-only responses and no phrase-match logic remains.

- [ ] `target/requirements/09_onboarding.md` — 6 screens (ON04/ON06 removed), business rules updated
  - Walk through ON01→ON02→ON03/ON05→ON07→ON08 with prototype (`target/prototypes/haisir_onboarding_flow.html`)
  - Verify: Single-select role selection — Student OR Parent only (instructor invited, tutor separate flow)
  - Verify: Google SSO + email/password — both paths tested?
  - Verify: Existing user detection — what if someone onboards, deletes cookies, re-visits?
  - Verify: "Add role later" flow from profile/settings page works (BR-ON-006a)

- [ ] `target/requirements/10_notifications.md` — all types, polling model, generation rules
  - Verify: 60s polling is sufficient (vs WebSocket for real-time needs)
  - Verify: Each notification type — is the trigger correct? Any missing?
  - Verify: Cron schedules (hourly due_soon, weekly digest) — timezone handling?
  - ✅ Verified: `doubt_auto_closed` (student) and `child_doubt_auto_closed` (parent) are defined in `10_notifications.md` sections 3.1 and 3.4, with generation rules in BR-NOTIF-011.

### Phase 4 — Visual & UX validation

- [ ] `target/requirements/ui-mapping/ui_student.md`
- [ ] `target/requirements/ui-mapping/ui_teacher.md`
- [ ] `target/requirements/ui-mapping/ui_parent_institution_admin.md`
- [ ] `target/requirements/ui-mapping/ui_onboarding.md`
- [ ] `target/requirements/ui-mapping/ui_notifications.md`
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
