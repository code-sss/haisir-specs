# hAIsir — Implementation Constraints

> Things the current implementation imposes on the target state. Surface these when evolving requirements so the target stays compatible with what is already built — or so the cost of diverging is made explicit.
>
> This is distinct from `CLAUDE.md` Critical Rules, which are policy/architecture decisions. Entries here are implementation-reality constraints: things already coded, migrated, or deployed that would require non-trivial rework to change.
>
> **Maintainer:** Update this file when `/update-target-state` surfaces a new constraint, or when a phase decision creates one.
>
> **Last verified against code: 2026-08-09** — backend `00c2c73`, frontend `705833d`, deploy `844e8f9`. Every entry below was re-checked against the sibling repos on that date, not carried forward on trust. The file had gone unmaintained from its creation (2026-04-17) through Phases 2–7; one entry was found to be **flatly wrong** and one to describe intent rather than shipped reality. Both are corrected below. **Put the date and SHAs above at the top of any future pass** — an unverifiable "last reviewed" claim is worse than none.

---

## schema — deprecated assessment tables

**What:** `assessments`, `assessment_attempts`, and `assessment_answers` tables are deprecated. The unified model is `exam_templates` with `purpose = 'quiz' | 'exam'`. Existing data migrated as `mode = 'static'`, `purpose = 'quiz'`.
**Why it exists:** Phase 0 consolidation decision (2026-03-22) — two overlapping models were merged.
**Impact on target state:** Any spec referencing `assessments` or `assessment_attempts` must be rewritten to use `exam_templates`. Do not add new columns or endpoints for the deprecated tables.

---

## schema — user identity is `idp_sub`, not a local users table

**What:** There is no local `users` table. Identity is Keycloak `sub` stored as a raw UUID string (`idp_sub`). No FK constraints on user columns.
**Why it exists:** Keycloak is the identity provider; the backend never owns user records.
**Impact on target state:** Any spec that needs to reference a user must use `idp_sub` as a plain UUID column (no FK). No target design can assume a joinable `users` table.

---

## schema — `user_metadata` is minimal by design

**What:** `user_metadata` table contains only `idp_sub` (PK) and `onboarding_completed_at`. No profile data.
**Why it exists:** Phase 0 decision — profile data lives in persona-specific tables (`student_profiles`, `teacher_profiles`, etc.), not a central user record.
**Impact on target state:** Do not add profile fields to `user_metadata`. Route new user attributes to the appropriate persona profile table.

---

## schema — `rate_per_session` removed from teacher profiles

**What:** `rate_per_session` was removed from teacher/tutor profiles. No payment model in v1.
**Why it exists:** Tutors are publishers, not session-based service providers. Payment extensibility is via `subscription_status` / `payment_id` on `enrollments` and `tutor_student_relationships`.
**Impact on target state:** Any monetisation spec must use the `enrollments.subscription_status` / `payment_id` fields, not session-rate columns.

---

## auth — all six realm roles are provisioned; the *assignment flows* are what's missing

> **Corrected 2026-08-09. The previous version of this entry was wrong** and had been wrong for months. It read: *"`institution_admin`, `tutor`, and `parent` roles exist in the backend but are **not yet added to the Keycloak realm**"*. All six are in `haisir-deploy/common/keycloak/02-roles.json` and are created idempotently by `common/scripts/setup-keycloak.sh`. Anyone who scoped work off that sentence would have planned Keycloak provisioning that was already done, and — worse — treated a role as unusable end-to-end when it was not the blocker.

**What:** All six realm roles — `student`, `instructor`, `admin`, `institution_admin`, `tutor`, `parent` — are provisioned in the Keycloak realm and validated against `X-Current-Role` by the backend `UserRole` enum and the `permission.py` factories (`require_instructor` / `require_tutor` / `require_parent` / `require_institution_admin`). `04-user-instructor.json` provisions an instructor test user.

**The real residual constraint is one level up: only `POST /api/users/me/assign-role` exists.** There is no `become-tutor` flow and no `invite-role` flow — grep confirms `src/api/routes/user.py` is the only route file with an assignment endpoint. Frontend role-switcher metadata and the `/institution` + `/parent` route guards are likewise unbuilt.

**Why it exists:** Role migration is a controlled process (`vision/requirements/11_role_migration.md`). The IdP caught up; the application-side acquisition flows did not.
**Impact on target state:** A spec may assume any of the six roles *authenticates and authorises* correctly. It may **not** assume a user can acquire `tutor`, `instructor`, or `institution_admin` — there is no path to that role today except direct assignment in Keycloak. Note also that **`institution_admin` is on explicit hold** (`decisions.md`, 2026-07-27), so `invite-role` and the `/institution` guard are blocked rather than merely unbuilt.

---

## auth — APISIX injects the JWT; client never sends Bearer

**What:** The API gateway (APISIX) validates and forwards the JWT as headers to the FastAPI backend. The client sends session cookies; it never constructs or sends a `Authorization: Bearer` header. The backend independently re-verifies: local JWKS RS256 decode, then — with `introspection_enabled`, which **defaults to `True`** (`src/shared/config.py:88`) — an RFC 7662 introspection call that fails closed (Keycloak unreachable → 503, inactive → 401).
**Why it exists:** Security boundary — token validation is centralised at the gateway; introspection catches revocation that stateless validation cannot.
**Impact on target state:** No spec may introduce a client-side Bearer token flow. Any new protected endpoint is automatically covered by the APISIX plugin — no extra auth wiring needed in the spec.

**Corollary constraint — `X-Current-Role` has exactly four exemptions, and the fourth is structural.** Every role-gated endpoint requires the header (missing → 400). The lenient paths are `GET /api/users/me`, `POST /api/users/me/assign-role`, `PATCH /api/users/me/onboarding-complete`, and — added Phase 7 — **`GET /images/questions/{filename}`**. The last one is not a policy relaxation: it is fetched by an `<img src>` tag, and a browser cannot attach a custom header to an image subresource, so the strict dependency returned 400 on every render and made the endpoint structurally unreachable. Auth is still enforced; the role is simply never read. **Any new spec for a browser-subresource endpoint — images, fonts, downloads reached by `<img>`/`<link>`/direct navigation — hits this same wall and must plan for the lenient path, not discover it in testing.**

---

## auth — `admin` role cannot be combined

**What:** The `admin` role (Platform Admin) cannot be combined with any other role on the same account (BR-ROLE-004).
**Why it exists:** Privilege isolation.
**Impact on target state:** Any multi-role or role-switching spec must exclude `admin` from the combination matrix.

---

## api — role assignment flows (intended model; mostly unbuilt)

> **Sharpened 2026-08-09.** This entry described the *intended* assignment model as though it were implemented. Only the `student`/`parent` leg exists in code. Kept because the model still governs new specs, but relabelled so it is not mistaken for shipped behaviour — see the auth entry above for what actually exists.

**What (intended):** Role assignment is not self-service for all roles. `student` and `parent` self-select at onboarding; `tutor` via an explicit "Become a tutor" flow; `instructor` is invited by `institution_admin`; `institution_admin` is assigned by platform admin; `admin` is dedicated accounts only.
**What (built):** the `student`/`parent` onboarding leg, via `POST /api/users/me/assign-role`. Nothing else. `tutor` self-service additionally needs a `tutor_profiles` table that does not exist.
**Why it exists:** Phase 0 decision to match trust levels with assignment mechanisms.
**Impact on target state:** Any spec that adds a new role or changes how a role is acquired must be consistent with this assignment model — and must budget for building the flow, not just wiring to it.

---

## ui — ON04 and ON06 removed from onboarding

**What:** Instructor setup (ON04) and Tutor setup (ON06) screens were removed from the onboarding flow.
**Why it exists:** Phase 0 decision — these roles are not self-initiated at onboarding.
**Impact on target state:** Do not re-add these screens to onboarding. Post-onboarding profile completion is the right home for instructor/tutor setup.

---

## ui — institution admin SA03 has no pending tab in v1

**What:** SA03 (student management) has Active + Inactive tabs only. Pending tab is deferred until institution self-registration is built.
**Why it exists:** Phase 1 scope decision — pending state requires a self-registration flow that isn't built yet.
**Impact on target state:** Do not spec pending-state UI for SA03 until institution self-registration is in scope. Note the whole persona is now on **explicit hold** (`decisions.md`, 2026-07-27), so this is blocked, not merely queued.

---

# Constraints added 2026-08-09 (Phases 2–7 backfill)

> The entries below existed as implementation reality for months but were never recorded here, because this file went unmaintained after 2026-04-17. They are the ones that actually change how a new spec must be written.

---

## ui — CSP is enforced, so inline styles and scripts are unavailable

**What:** A nonce-based Content-Security-Policy is **enforced in production** (Report-Only retained in development as the CI regression surface), minted per-request in `haisir-frontend/src/proxy.ts` with `'strict-dynamic'`. Two documented relaxations only: `style-src-attr 'unsafe-inline'` and `'wasm-unsafe-eval'` (pdfjs-dist).
**Why it exists:** Phase 7 G5. CSP was the one missing header of seven, and a gateway-side policy was rejected as unimplementable — APISIX cannot mint a per-request value and inject it into rendered HTML, so a gateway CSP is necessarily static and forces `script-src 'unsafe-inline'`.
**Impact on target state:** Three hard consequences for any new UI spec. (1) **No inline `<script>` and no `style=` attributes** carrying anything nonce-able — styling is CSS Modules / `globals.css`; this is why question-image previews use a plain `<img class="img-fill-contain">` rather than `next/image` with an inline `style`. (2) **No third-party script origins** without an explicit policy amendment. (3) **Every route must be dynamically rendered** (BR-CSP-010, asserted in CI) — a build-time-prerendered page cannot receive a per-request nonce, so a spec that calls for a statically generated page is specifying something that cannot carry the nonce and will break under enforcement.

---

## deploy — the worker must be stopped before any migrating deploy

**What:** Worker poller sessions sit `idle in transaction`, holding locks that block Alembic migrations. Stopping the worker is therefore a **manual precondition on every migrating deploy**, not an optimisation.
**Why it exists:** Backlog **B1** (`phases.md`) — the poll loops do not release their transactions between iterations.
**Impact on target state:** Any spec that adds a migration, or adds a new worker loop, inherits this. A spec proposing zero-downtime migration must fix B1 first — it is not achievable around the current poller. Claimed by Phase 7.5 G5.

---

## deploy — some migrations have no downgrade path

**What:** `V43_migrate_base64_images.py`'s `downgrade()` is a **deliberate no-op** — it does not reconstruct base64 `data:` URIs from the files it wrote. `V41`'s downgrade drops `visibility_status` but cannot remove the `'image'` value from the `contenttype` enum (PostgreSQL does not support removing enum values).
**Why it exists:** Both are one-way data migrations where the inverse is either lossy or impossible in PostgreSQL.
**Impact on target state:** **The rollback path for these releases is the pre-deploy dump plus datadir tarball, not `alembic downgrade`.** Any deploy spec or runbook that assumes migrations are reversible is wrong for this codebase. Retain the dump for the agreed window before deleting it.

---

## schema — `data_topic_content_chunks` is owned by LlamaIndex, not by us

**What:** The table is created and managed by LlamaIndex's `PGVectorStore`. V32 is a registration shim; V33 adds the `text_search_tsv` column, trigger and GIN index that the store requires but does not create.
**Why it exists:** Phase 2 RAG. Hybrid retrieval needs the sparse leg, and the store assumes the column exists.
**Impact on target state:** **Do not add this table to Alembic autogenerate targets** — autogenerate will propose dropping columns it does not know about. Do not spec direct writes to it; it is written through `index.insert_nodes(nodes)`, not `vector_store.add`.

---

## content — publish is an explicit decision, and raw/extracted are mutually exclusive

**What:** A PDF/image upload materialises **both** a raw `topic_contents` row and N extracted `text` rows. `visibility_status` (`'draft'` / `'published'`) gates student visibility **underneath** the topic-level `status='live'` gate, and exactly one of raw/extracted may be published at a time (enforced at the service layer, BR-DATA-024/025). The column default is `'draft'`.
**Why it exists:** Phase 6.5. It reverses BR-DATA-008/009 and BR-EXT-012, which had asserted the source file was transient and that content was visible to students immediately on creation.
**Impact on target state:** New content specs must state a publish step explicitly — nothing is student-visible on creation any more. Note the `'draft'` default encodes a **clean-reset** deployment decision: existing content was truncated and re-uploaded rather than migrated. A deployment intending to preserve existing content would need `DEFAULT 'published'`. Related: question images are **paths, never data URIs** (V43), served only by `GET /images/questions/{filename}`.

---

## ai — the LLM never does arithmetic, and never supplies its own grounding

**What:** Two separate rules that share a shape. **Essay grading:** the LLM emits per-criterion *levels* only; the backend computes `ai_score = Σ(level/scale_max × weight) × points`. **Exam-review chat:** the grounding prompt is built server-side from the attempt's own session questions, and the client-supplied `history` is accepted-but-ignored in favour of the persisted `review_chat_messages` thread.
**Why it exists:** Essay grading — LLM arithmetic is unreliable and unauditable. Review chat — Phase 7 G3.4; `ReviewChatMessage.role` was a bare `str`, so a client could inject a `system` turn into an authenticated LLM call. It is now `Literal["student","ai"]`, with a matching DB CHECK constraint.
**Impact on target state:** Any new AI-scored or AI-grounded feature must keep computation and grounding server-side. **A WAF cannot catch this class of attack** — the payload is well-formed JSON on an authenticated endpoint and the injected text is ordinary prose — so "the gateway will catch it" is not an acceptable answer in a spec review.

---

## gateway — WAF exclusions must be field-scoped, and prose payloads are the enemy

**What:** Coraza is **v3.7.0**, CRS **v4.25.1 LTS**. Blanket `ctl:ruleRemoveById` is down from 38 rule IDs to 1, and that survivor (`931130`) is structural — it targets a `TX` variable, so the `ARGS_POST` regex form cannot apply to it.
**Why it exists:** Phase 7 G1/G4. The root cause of the old exclusion treadmill was a version gap, not an engine defect: regex collection keys in `ctl:ruleRemoveTargetById` landed in Coraza **v3.5.0**, and the shipped build was **v3.3.3** — so every field-scoped exclusion parsed as a literal variable name and silently matched nothing.
**Impact on target state:** New exclusions must be **field-scoped** (`ctl:ruleRemoveTargetById` with a regex key, or `SecRuleUpdateTargetByTag <tag> "!ARGS_POST:/field/"`); a blanket whole-request removal now needs a written structural justification. More importantly, the durable lesson is upstream of the WAF: **`tx.total_arg_length` is 65535 and rule 920390 is unexcluded**, so a spec that puts unbounded free text or a replayed transcript in a request body has a hard ceiling no tuning can clear. Cap free-text fields at the schema (`max_length`) and keep transcripts server-side.
