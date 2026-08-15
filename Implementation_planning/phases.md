# hAIsir — Implementation Phase Guide

> Details live in `target/requirements/`. Update this file when phase ordering
> or scope changes significantly.
>
> Long-term vision phasing is in `vision/phases.md`.

---

## Phase 0 — Foundation ✓ (completed 2026-03-26)

Auth, schema, onboarding.

---

## Phase 1 — Board Content Management (Platform Admin)

Split into sub-phases to keep each deployable unit small:

| Sub-phase | Scope | Depends on |
|---|---|---|
| **1a** ✓ — Owner_type visibility enforcement | Backend-only: apply BR-DATA-003 WHERE clause on all student + admin endpoints | — |
| **1b** ✓ — Admin tree UI + node CRUD | `/admin` + `/admin/boards` pages; `PATCH`/`DELETE` course_path_nodes; full-subtree CTE fetch; admin shell layout | 1a |
| **1c-pre** ✓ — X-Current-Role enforcement | Backend: split `current_active_user` into strict (400 if header missing) + lenient (3 exempt onboarding endpoints). Frontend: confirm all calls send header; fix `position`→`order` dev note | 1b |
| **1c** ✓ — Topics panel | Right-panel topic list + CRUD for selected node; `PATCH`/`DELETE` topics; status toggle (draft/live) | 1c-pre |
| **1c-post** ✓ — Admin UX alignment | Fix Add Board modal (missing `path_type`); chip selector for node types (9 enum values); dashboard stats endpoint + rich cards; inline description edit; sibling-type filtering; 3-tier hierarchy enforcement | 1c |
| **1d-stub** ✓ — Topic content URL/video/text CRUD (functionally incomplete) | Manual `topic_contents` rows for video URL and pasted text only. **No PDF/image upload** — the modal’s PDF chip is a stub. | 1c-post |
| **1d-real** — Topic content extraction (PDF/image → text via vision LLM) | Multipart upload → Postgres queue (FOR UPDATE SKIP LOCKED) → worker process → `pypdfium2` (native text) or `glm-ocr` (vision LLM) → N `topic_contents` rows. Inline title rename + Edit modal preserve provenance. See `target/requirements/12_content_extraction.md`. | 1d-stub |

---

## Phase 2 — RAG Infrastructure + Text Restructuring + Student Dashboard ✓ (completed 2026-06-17)

| Sub-phase | Scope | Depends on |
|---|---|---|
| **2a** — pgvector DB image | Wolfi multi-stage Dockerfile; `pgvector/pgvector:pg18` for dev; compose wired | 1d-real |
| **2b** — Vector schema | V31 (`CREATE EXTENSION vector`), V32 (Alembic shim for `data_topic_content_chunks`) | 2a |
| **2c** — RAG drain loop | `EmbeddingSettings`, LlamaIndex deps, `rag_outbox_loop.py` as 4th worker coroutine; outbox drained to pgvector | 2b |
| **2d** — hAITU config stub | `HaituSettings` in `shared/config.py`; HAITU env vars in compose (endpoint deferred to next cycle) | 2c |
| **2e** — Text restructuring | `restructure_page()` in `GlmOcrProvider`; wired in `extract_page()` behind `EXTRACTION__RESTRUCTURE_TEXT` flag | 1d-real |
| **2f** — Student dashboard backend | Four `GET /api/student/` endpoints; `X-Current-Role: student` enforcement; platform + parent-owned node trees | 2a |
| **2g** — Student dashboard frontend | S-home (Platform Board / Home Study sections) + S-nav (tree sidebar + topic list + content viewer) | 2f |

Plan doc: `Implementation_planning/PLAN.md` (written 2026-06-12).
Decisions: `Implementation_planning/decisions.md` (2026-06-12 entries: RAG+hAITU architecture, PDF text restructuring).

---

## Phase 3 — Student Enrollment + hAITU Topic-Doubt ✓ (completed 2026-06-24)

| Sub-phase | Scope | Depends on |
|---|---|---|
| **3a** ✓ — student_enrollments schema | V34 migration; StudentEnrollment domain model + repo | 2e/2f |
| **3b** ✓ — Enrollment APIs | GET /catalog (recommended), POST/DELETE /enrollments; enrolled-only content filter on all 4 student endpoints | 3a |
| **3c** ✓ — hAITU retrieval service | 4-stage pipeline: query rewrite + hybrid pgvector search + optional rerank + CompactAndRefine synthesis | 2c (pgvector + bge-m3 indexing) |
| **3d** ✓ — hAITU endpoint | POST /api/haitu/topic-doubt; HaituDoubtService (stateless); in-memory rate limiter (20/student/hour) | 3b, 3c |
| **3e** ✓ — APISIX route + env vars | 19-api-haitu.json with 360s timeout; HAITU__* + EMBEDDING__* env vars wired in backend service | 3d |
| **3f** ✓ — Enrollment frontend | S-enroll (/enroll) catalog page; enroll/drop CTA; Browse Courses nav link; empty-state handling in S-home + S-nav | 3b |
| **3g** ✓ — hAITU doubt panel | HaituDoubtPanel in ContentViewer; useHaituDoubt hook (client-side history); escalation button (disabled placeholder) | 3d, 3f |
| **3h** ✓ — Verification + manual walkthrough + sign-off (G10) | 12 backend goal-level integration/E2E tests (8 DB-only + 4 Ollama-gated with skip-count reporting); shared integration fixtures (migration-head V34 guard, dep-override wiring, rate-limiter reset, per-test isolation, Ollama probe); manual 7-step ROOT Acceptance Test against the running stack; per-repo defect fixes; archive PLAN.md/TASKS.md + mark Phase 3 ✓. **No deferral.** | 3a–3g |

Implementation for 3a–3g is complete (incl. frontend Playwright E2E suite). 3h sign-off landed 2026-06-24 — Phase 3 ✓. Archived: `archive/PLAN_Phase3-Enrollment-Haitu_2026-06-18.md`. APISIX hAITU timeout corrected 360s → 600s.

**Carried into Phase 4:** doubts + doubt_messages tables (V35), teacher escalation flow, mastery score tracking, parent features.

---

## Phase 4 — Doubt Persistence + Teacher Escalation + Notifications + Mastery / Post-Exam Review ✓ (completed 2026-07-02)

> Root goal: a student's hAITU doubt becomes a persistent thread a teacher can escalate into and reply to, with notifications; the student gains per-topic mastery tracking and a post-exam hAITU review. Two major features, deliberately sequenced (Feature 1 → Feature 2) with a P0 stabilization goal first.

| Sub-goal | Concern | Repos |
|---|---|---|
| **G0** ✓ — Stabilize HEAD (P0 blocker) | Fix 5 Python-2 `except`-clause SyntaxErrors, merge `feature/rag`→`main` across repos, re-verify Phase 3 at HEAD + CI grep guard + correct stale CLAUDE.md Keycloak claim, and remove inline-ML deps (stub the dormant reranker; drop `sentence-transformers`/`torch`/uv torch-CPU pin; future reranker = external HTTP API) | backend, frontend, deploy, specs |
| **G1** ✓ — Doubt persistence + hAITU thread completion | V35 (`doubts` + `doubt_messages`); Doubt/DoubtMessage domain models, repos, schemas, service; student S08 inbox + S09 thread UI; hAITU persists the doubt + student message pre-stream and the AI message post-stream with a `doubt_id` SSE frame; no-orphan-on-429 + no-duplicate-on-retry + disconnect/partial-text persistence tests | specs, backend, frontend |
| **G2** ✓ (+ G2-patch) — Teacher escalation | Escalate endpoint mounting at `/api/doubts`; teacher queue `GET`+claim and reply routes mounting under `/api/teachers` (`require_instructor`); shared-instructor-queue model; T06 teacher inbox + T07 reply UI; student "Request teacher help" CTA wired into S09 + the hAITU panel; G2-patch fixed re-escalation after a teacher answer (`answered` now treated as closed in `find_or_create_doubt`) | specs, backend, frontend |
| **G3** ✓ — Notifications subsystem | V36 `notifications`; NotificationService with a pluggable parent fan-out stub; 4 endpoints (list/unread-count/mark-read/mark-all-read) + APISIX route; bell + feed UI polled every 60s in the shared topbar (all roles); hourly auto-close cron in the worker (7-day) wired to `new_doubt_escalated` / `doubt_teacher_replied` / `doubt_auto_closed` events | specs, backend, frontend, deploy |
| **G4** ✓ (+ G4-patch/-2/-3/-4) — Mastery + post-exam review | V37 **adds** `questions.topic_id` (NULLABLE) + `enrollment_topics` (FK to `student_enrollments(id)`) + `student_risk_state`; EnrollmentTopic model/repo + Question.topic_id mapping wired all the way through the admin exam builder (T4.1.4, the last gap — re-opened 2026-07-01, closed 2026-07-02); MasteryService per-topic recalc (BR-PROGRESS-001/002/003) wired into `submit_exam` completed branch, essay auto-complete, AND manual release/finalize/override path; persistence-based `student_at_risk` recovery gate + `topic_marked_weak`; post-exam hAITU review via a new public no-RAG `HaituService` method (`POST /api/haitu/exam-review-chat`, `POST /api/haitu/pattern-analysis`, both SSE-streamed after G4-patch/-2) + S05 review screen consuming `GET /api/exam-sessions/session/{id}/answers`; weak-topic "Focus areas" strip on the student dashboard | specs, backend, frontend, deploy |

DAG: G0 → G1 → G2 → G3 → G4 (acyclic). Dependencies flow `specs` contracts ahead of `backend` migrations ahead of `frontend` UI; G3 notifications are consumed by G2 (escalate events) and G4 (mastery events).

Sign-off 2026-07-02: all sub-goals ✓, `archive/g4_test_plan.md` T1–T10 fully verified live against the
real admin-built UI (post-T4.1.4). Archived: `archive/PLAN_Phase4-Mastery-PostExam_2026-06-24.md`,
`archive/TASKS_Phase4-Mastery-PostExam_2026-06-24.md`. Walkthrough record:
`Implementation_planning/archive/g4_test_plan.md`. Final baseline SHAs: backend `0cb36bd`, frontend
`df7067e`, deploy `98912f8`.

**Carried into Phase 5:** Parent curriculum builder (adopt board subtree, create own
nodes/topics, upload notes), parent link-code generation/redemption, remaining role-migration
work (`vision/requirements/11_role_migration.md`: `become-tutor`/`invite-role` flows, frontend
role-switcher metadata, `/institution` + `/parent` route guards).

---

## Pre-Phase 5 — Phase 4 Release-Hardening Pass ✓ (completed 2026-07-06)

> Root goal: make the through-Phase-4 build release-ready for user testing by fixing 14 issues
> found in manual testing (plus one latent bug, issue 15, found during plan review — see below).
> Full goal tree: `archive/PLAN_PrePhase5-Hardening_2026-07-02.md` /
> `archive/TASKS_PrePhase5-Hardening_2026-07-02.md`. **Specs-repo plan** — code tasks are tickets for the
> sibling repos; the `[specs]` tasks (T6.3, T7.4, T8.2, T8.3, T8.4) are written as part of the plan.

| Goal | Issues | Repos | Disposition |
|---|---|---|---|
| **G1** — Exam review navigation wired | 1, 8, 15 | frontend | Fix — wire `/exam/[id]/review` from post-submit, AttemptsModal, Results button; fix pending-grading mislabeled as "Skipped" (T1.4, gap found in review) |
| **G2** — Exam builder bulk-topic + sample JSON | 2, 4 | frontend, deploy | Fix — "Apply topic to all" control; `qa-sample.json` carries `topic_id` |
| **G3** — Topic-filtered exam taking | 5 | backend, frontend | Fix — optional `topic_id` filter on `GET /api/exams/course/{node_id}`; "Take Exam" passes it |
| **G4** — Deep-link + tree interaction | 6, 7 | frontend | Fix — `/courses?topic=` consumed (expand ancestors + select); NodeTreeSidebar chevron separated from label select+expand |
| **G5** — Catalog grade label | 10 | frontend | Fix — "Grade N" display on grade root nodes |
| **G6** — Student grade/profile + onboarding | 13, 14 | frontend, backend, specs | Fix — grade picker in student onboarding View B → `POST /api/students/me/profile`; 09_onboarding amended; Phase 5 `/profile` makes it editable |
| **G7** — Inbox UX targeted polish | 12 | frontend, specs | Fix — bell dropdown, status filters, last-message previews; 10_notifications + 03_student + 04_teacher_tutor specced |
| **G8** — At-risk notif interim + deferred docs | 3, 9, 11 | backend, specs | Interim + spec — `action_url=NULL`; teacher at-risk view (BL-002, Phase 6); NULL-topic mastery limit documented; LaTeX rendering requirement (BL-003, follow-up) |

**Gate:** pre-Phase-5 must close before Phase 5 starts. Phase 5's `/profile` page (T1.5) extends
the grade field G6/T6.1 introduces; the parent onboarding dead-link (T2.6) is untouched here.
**No Alembic migrations** — all fixes ride on existing schema (V37 `questions.topic_id`,
`student_profiles.grade`, `notifications.action_url`). **No deploy gateway work** except the
`qa-sample.json` content edit. Baseline: backend `0cb36bd`, frontend `df7067e`, deploy `98912f8`.

**Deferred (not in pre-Phase-5):**
- **Issue 3 (subject-level mastery)** — accepted v1 limitation; `topic_id=NULL` questions are
  silently skipped by `MasteryService`. Documented in `03_student.md`; subject-level rollup
  deferred.
- **Issue 9 (teacher at-risk view)** — `action_url=NULL` interim; the
  `/teacher/students/{sub}` view is Phase 6 (backlog BL-002).
- **Issue 11 (LaTeX rendering)** — requirement + approach specced in
  `12_content_extraction.md` §11; ships as a focused follow-up (backlog BL-003, Status: Ready).

**Gap found during plan review (2026-07-02), documented not fixed:** skipping the G6/T6.1 grade
step at onboarding leaves a student with **no UI path** to set `student_profiles.grade` until
Phase 5 ships `/profile` (T1.5) — onboarding doesn't re-run once complete, and no other screen in
the through-Phase-4 build writes to that field. Documented as an accepted interim limitation in
`09_onboarding.md` (testers should not skip if they want `recommended` to activate pre-Phase-5).

**Manually verified 2026-07-06:** all 15 issues (14 reported + T1.4) retested end-to-end against
the fixes above and confirmed working. Issues 3 and 11 confirmed correctly deferred (spec-only,
not implemented) per the scope decisions. Phase 5 is cleared to start.

---

## Phase 5 — Parent Curriculum Builder + Link Codes, RAG-Connected (planned 2026-07-02)

> Root goal: a parent links to their child, builds/adopts a private curriculum, uploads content
> that flows through extraction + RAG embedding, and the linked child studies it in Home Study
> and asks hAITU questions grounded in the parent's notes. Full goal tree: `PLAN.md` / `TASKS.md`.

| Sub-goal | Concern | Repos |
|---|---|---|
| **G1** — Parent–child linking lifecycle | Student link-code generation/rotation + link management endpoints and new `/profile` page; parent children list + revoke; max-10 cap | backend, frontend, specs |
| **G2** — Parent workspace shell | Guarded `/parent` app area (route guard, layout, P-home dashboard, P-link page, dead-CTA fix) | frontend, specs |
| **G3** — Parent curriculum builder | V40 adopt-lineage migration; owner-scoped node/topic CRUD + hierarchy rules; idempotent adopt/clone (409); parent instant content + owner-scoped PATCH/DELETE; builder UI reusing parameterized admin content components | backend, frontend, specs |
| **G4** — RAG ingestion + re-ingestion lifecycle | Outbox enqueue on create, upsert-with-reset on update, chunk+outbox cleanup on delete (incl. cascade), worker delete-stale-before-insert; "No notes yet" UI states | backend, frontend, specs |
| **G5** — hAITU on parent-owned topics | Optional `enrollment_id`; parent-link authorization gate in `HaituDoubtService`; severance + cross-family 403 tests; Home Study hAITU panel | backend, frontend, specs |
| **G6** — Student Home Study surface | Live-only + revocation enforcement tests on all student read paths; source-aware empty states; content-viewing verification | backend, frontend |
| **G7** — Phase acceptance | CI-safe E2E journey + Ollama-gated grounded variant; frontend suites + manual walkthrough record | backend, frontend |

DAG spine: G1 → G2 → G3 → G4 → G5 → G6 → G7; G5/G6 backend tests are fixture-driven and can run
in parallel with G1–G3. No deploy-repo work (existing APISIX wildcard routes cover all new
endpoints). Baseline: backend `9532392`, frontend `df7067e`, deploy `98912f8`.

**Deferred to Phase 6 (candidates):** remaining role migration (`become-tutor` self-service —
tutor is in scope; `invite-role`/`/institution` route guard blocked — institution_admin is
explicitly out of scope per `06_institution_admin.md`, and no `organizations` table exists to
back BR-ROLE-002's org-scoping); RAG ops backlog (external HTTP reranker shipped 2026-07-08 as
`TeiRerankClient` — no longer backlog, remaining items are ops-only: env-template gap, deployment
verification, stale README; bundled inference service in deploy — intent undefined, needs
clarification; hAITU Prometheus monitoring — still blocked on Chainguard licensing); per-child
audience scoping of parent content — deliberately deferred, no trigger complaint on record;
parent-facing hAITU endpoints (`vision/requirements/08_haitu_ai_layer.md` §3.5–3.7 — corrected
citation, was misfiled as `00_overview.md`; also blocked on a mastery-tracking gap for
non-enrollment content, not just the missing UI).

---

## Phase 5.5 — Secrets Management Closeout (OpenBao) ✓ (completed 2026-07-15)

> Root goal: OpenBao is live as hAIsir's secrets authority — no plaintext secrets in `.env`/
> `docker-compose.yml`, machines authenticate by mTLS-bound identity, humans by Keycloak OIDC,
> every secret read audited, the backend fails fast rather than silently running with dummy
> secret defaults. Reconciles a 5-week-parked branch (`feature/secrets-management-openbao`,
> `haisir-deploy`, Phase 0-4 coded 2026-06-05) onto current `main`, rather than continuing
> straight into Phase 6 — an explicit user reprioritization, not a Phase 6 blocker. Full goal
> tree: `PLAN.md` / `TASKS.md`.

| Sub-goal | Concern | Repos |
|---|---|---|
| **G1** — Deploy-side reconciliation | Land the parked branch's OpenBao stack correctly onto current main; two design changes (static seal replacing two-instance transit-unseal, version pin 2.2.0→2.6.0 for a CVE fix); close the 3-secret gap (`EMBEDDING__`/`HAITU__`/`GRADING__OLLAMA_API_KEY`) on both the KV and compose sides; stack bring-up ordering; dynamic-Postgres-engine compat with the current pgvector image | deploy |
| **G2** — HARD GATE: first-ever live verification | Nothing in G3/G4 starts until this passes in full. Bring-up, mTLS auth, audit logging, static-seal auto-unseal after restart (the one truly novel/untested claim), dynamic Postgres credentials, Ollama secrets served via templating | deploy |
| **G3** — Backend fails fast | Remove `default="dummy"`/`default=""` fallbacks on CSRF secret, `database_url`, Keycloak admin creds (BR-SEC-019); regression test; correct the stale header comment | backend |
| **G4** — Close-out and merge | Combined smoke test; ops runbooks (`.env` cutover, secret rotation at cutover — not before); two independent security-review passes per repo (symmetric depth); merge deploy before backend (backend cannot release ahead of the stack that supplies its secrets) | deploy, backend, specs |

DAG spine: G1 (21 tasks, parallel) → G2 (hard gate, 7 tasks) → G3 (6 tasks) → G4 (10 tasks,
deploy-before-backend merge order enforced as an explicit dependency). Two challenger rounds run
on the goal tree (round 1: 2 Blockers + 4 Majors, all resolved; round 2: verified, one item
downgraded to a documented `<!-- UNRESOLVED -->` limitation). Baseline:
backend `3c53b1a`, frontend `816194d`, deploy `b8f650d`. Work landed on `feature/secrets-openbao-v2`
in `haisir-specs` and `haisir-deploy` (fresh branches, not the stale parked one), fast-forward
merged to `main` in all three repos 2026-07-15: backend `ee3a79e`, deploy `613c092`, specs
`c096504`. Feature branches deleted (local + remote) post-merge. See progress.md's "Phase 5.5"
completed-phase entry for the full close-out narrative.

**Carried forward, unchanged:** everything Phase 5 deferred to Phase 6 (role migration, RAG ops
backlog, per-child audience scoping, parent-facing hAITU endpoints) — this phase doesn't touch
that scope, it's inserted ahead of it by explicit priority choice.

---

## Phase 5.6 — Full .env Secrets Elimination (OpenBao, all remaining services) ✓ (completed 2026-07-21)

> Root goal: every remaining secret-shaped value in `{dev,staging,prod}/{.env,.env.config.sh}`
> is sourced from OpenBao KV, not plaintext — closing the gap Phase 5.5's root-goal wording
> claimed but its task list never covered (5.5 only migrated `haisir-backend`/`haisir-worker`'s
> own secrets). Found during Phase 5.5's G4.1 combined smoke test (2026-07-15). Sat between
> Phase 5.5 and Phase 6 — did not block or reorder Phase 6's backlog.

Planned via `/plan` on 2026-07-16 (two challenger rounds) — full goal tree in `PLAN.md`,
checkboxes in `TASKS.md`, planning decisions in `decisions.md` (2026-07-16 entry, close-out
decisions in the 2026-07-21 entry).

| Goal | Scope | Outcome |
|---|---|---|
| G1 [deploy] | Fail-closed foundations: per-key fail-closed render manifest, `${VAR:?}` compose guards, render hooks for `setup.sh`/`setup-keycloak.sh`, 3 Class-B mechanism spikes | ✓ all 3 spikes returned WORKS |
| G2 [deploy] | Class A cutover (`.env.config.sh` secrets → KV, per-path atomic): gateway (APISIX admin key, session secret, CrowdSec key), OIDC trio, backend-admin dedup via new `secret/haisir/keycloak-clients`, test user (dropped from prod realm), Keycloak admin pw (provisioning side), tunnel token | ✓ all 7 sub-goals cut over |
| G3 [deploy] | **HARD GATE** — Class A live verification on dev (9 tasks incl. both render code paths) | ✓ passed; 3 pre-existing environment bugs found + fixed as root cause (stale image tag, unwired `SECURITY__FORCE_HTTPS`, disjoint Docker networks — network fix a live workaround only, compose file left unchanged) |
| G4 [deploy] | Class B cutover (`.env` cold-start passwords → KV): spike-based per-service mechanism, KC_DB auth-truth verification + role-provisioning fix, db/keycloak-db/keycloak cutovers, rollback runbook | ✓ all 13 sub-tasks; delivery mechanism is vault-agent sidecars rendering `POSTGRES_PASSWORD_FILE`/`keycloak.conf`, not `${VAR:?}` guards (goal-test wording correction recorded in decisions.md) |
| G5 [deploy] | **HARD GATE** — Class B live verification on dev (preserved + fresh volumes, docker-inspect check, sealed-OpenBao fail-loud + break-glass drill) | ✓ passed; found + fixed a missing `group_add` on the `keycloak` service (first-ever real boot of common-project Keycloak in this sandbox) |
| G6 [deploy][specs] | 2 independent security reviews, ops/rotation runbook, rotation executed on dev, specs updates, merge to `haisir-deploy` main | ✓ pass 2 (adversarial) found + fixed a real gap pass 1 missed (unguarded Class B templates could render `<no value>` as a live DB password); 10 secret categories rotated live on dev; no separate branch existed to merge — all work landed as direct commits to `main` |

DAG spine: `G1 → G2 → G3 (gate) → G4 → G5 (gate) → G6`. 64 tasks (60 [deploy], 4 [specs]) — all
[deploy] tasks complete; the 4 [specs] tasks (this file, `progress.md`, `decisions.md`,
`13_secrets_management.md`) closed out the phase.
Scope locks: pgadmin excluded (dev-only); `TEST_USER_PASSWORD` → KV dev/staging + prod realm
drop + Jenkins dual-store; staging/prod KV seeding AND live verification deferred to their
OpenBao bring-up (runbook, fail-closed until then — 5.5 deferral precedent); no OpenBao
redesign; Phase 6 backlog untouched.

**Carried forward as open follow-ups (not fixed this phase, deliberately scoped out of a
secrets-only closeout):** `common/scripts/setup.sh` checks `APISIX_ADMIN_KEY` non-empty before
running its own OpenBao render hook — fails under `set -u` on a standalone invocation now that
the plaintext fallback is gone; `common/docker-compose.yml`'s hardcoded external network name
(`haisir-net`) diverges from the documented dev setup (`haisir-net-dev`), leaving the dev stack
and the `common` project on disjoint Docker networks by default. Both are real, pre-existing gaps
surfaced by this phase's hard gates — worth their own follow-up task whenever deploy work next
touches those files.

Baseline at planning: backend `ee3a79e`, frontend `816194d`, deploy `613c092`.
Baseline at close: backend `ee3a79e` (unchanged — no backend work this phase), frontend
`816194d` (unchanged), deploy `b52ec74`.

---

## Phase 6 — Parent Indexing Status & Retry ✓ (completed 2026-07-26)

> Root goal: parents can see, per content item, whether it has been embedded into RAG (5 states
> sourced from `rag_indexing_outbox.status`), and can manually retry a permanently-`failed` one —
> mirroring the existing extraction-job status-pill UX one level down the pipeline. Already fully
> spec'd (`target/requirements/05_parent.md` BR-PAR-020, `01_data_model.md` BR-DATA-023) before
> this phase — chosen over the Phase 5 backlog candidates because it had no open decisions and no
> missing data model. Full goal tree: `PLAN.md` / `TASKS.md`. One challenger round run — decision
> rationale and the two stale-candidate corrections (reranker, `/parent` guard) in `decisions.md`
> (2026-07-26 entry).

| Goal | Concern | Repos | Outcome |
|---|---|---|---|
| **G1** — Parent-owned content exposes live indexing status | List-endpoint indexing-status field + owner-scoped, cooldown-guarded manual retry endpoint reusing BR-DATA-020's upsert-with-reset | backend | ✓ `2901077` |
| **G2** — Parent UI surfaces indexing pills and manual retry | Status pill per content item (5-state, mirrors admin extraction-job UX) + Retry button + 2s/10s/60s polling | frontend | ✓ `1e5fdd0` |
| **G3** — Cross-repo acceptance | Full lifecycle test: pending → failed → retry → pending, 404, 429 | backend | ✓ `10b2606` |

DAG: G1 → G2 (frontend needs the backend field/endpoint) → G3. No `[deploy]` work (existing
`/api/*` write-route wildcard covers the new endpoint) and no `[specs]` work (spec pre-existed).
Baseline at planning: backend `aa24252`, frontend `816194d`, deploy `861705b`.
Baseline at close: backend `c82d466` (phase work: `2901077`, `10b2606`), frontend `67a883c`
(phase work: `1e5fdd0`), deploy `861705b` (unchanged — no deploy work this phase).

**Not in this phase's scope (Phase 5 backlog candidates, status corrected 2026-07-26):**
tutor self-service role assignment (in-scope, needs a `tutor_profiles` table — not yet planned);
`invite-role` + `/institution` route guard (**blocked** — institution_admin is explicitly out of
scope per `06_institution_admin.md`, and no `organizations` table exists); RAG ops cleanup
(env-template gap, reranker deployment verification, stale README, undecided monitoring stack —
the reranker code itself already shipped 2026-07-08, this is ops-only); per-child audience scoping
of parent content (deliberately deferred, no trigger complaint on record); parent-facing hAITU
endpoints (blocked on a progress-monitoring-UI product decision plus a mastery-tracking gap for
non-enrollment content). See `PLAN.md`'s backlog-candidates section for full detail on each.

**New backlog candidate for the phase after Phase 6 (spec-only, added 2026-07-26):** container
base image migration off Chainguard onto Minimus (`reg.mini.dev`) — free pinned-version images
across `haisir-backend`, `haisir-frontend`, and every Dockerfile/compose service in
`haisir-deploy`. Also resolves the "undecided monitoring stack" Chainguard-licensing blocker
above (Prometheus + Grafana are free on Minimus). Full spec:
`target/requirements/14_container_images.md`. Not planned yet — deliberately sequenced after
Phase 6 closes to avoid disrupting the in-flight Phase 6 plan.

---

## Phase 6.5 — Content Viewing & Publish (planned 2026-07-27)

> Root goal: uploaded content is viewable in its native format by both the uploader and the student,
> and student visibility becomes an explicit per-item publish decision instead of an implicit
> side-effect of extraction finishing.

Baseline at planning: backend `c82d466`, frontend `67a883c`, deploy `861705b`.

Extraction was built to feed RAG embeddings; student display was an accident of that pipeline. The
raw upload was purged on a TTL with no `topic_contents` row pointing at it, so a well-formatted
textbook page was permanently replaced by a lossy transcription and neither admin nor parent could
see what they had uploaded. There was no review gate — a bad OCR pass on a poor scan went straight
to students. This phase materializes a permanent raw row alongside the extracted text rows, adds a
`visibility_status` gate underneath the existing `topics.status='live'` gate, and makes publish a
mutually-exclusive raw-vs-text choice per upload.

**Sequencing:** G1 (schema) unblocks everything. G3 (raw file + serving endpoint) and G4 (publish
API) are independent of each other and both feed the frontend goals. G5 (shared viewer) must land
before G6 (uploader UI), which mounts it.

**Scope locks:** the truncate is a confirm-gated runbook, never an Alembic revision — migrations run
automatically on deploy and an irreversible `TRUNCATE` inside one fires with no operator in the
loop. Publish is never a per-row write; `visibility_status` is absent from `TopicContentUpdate` and
the only mutation path is the group-scoped endpoint, because the mutual-exclusivity invariant cannot
hold if callers can set one row at a time. Video scope stays YouTube + Vimeo, matching the existing
hostname allowlist.

**Correction to the drafted specs:** a challenger pass found eight discrepancies between the target
specs for this increment and the shipped code — most consequentially that the raw file path belongs
in the existing `url` column (not `text`), that `content_type` is a native Postgres enum requiring
`ALTER TYPE`, that the PDF viewer and `ContentViewer` already exist (only the image viewer is
net-new), and that no file-serving endpoint was specced at all. All fixed in the specs before
planning; see the corrections table in `PLAN.md`.

**Deferred out of this phase:** BR-DATA-012's specced-but-unimplemented content-order base shift,
and the pre-existing 0-indexed provenance page display. Both are pre-existing, and the raw row is
deliberately appended after the text rows so neither gets worse.

---

## Phase 7 — Gateway WAF Modernisation, CSP & Security Review Closeout ✓ (completed 2026-08-06)

> Scoped 2026-07-27, archived unstarted the same day when Phase 6.5 took priority, **restored
> 2026-07-29** once 6.5 closed. See `decisions.md` (2026-07-29, "Phase 7 restored from archive") for
> what the reconciliation changed, and (2026-08-06) for the close-out record. Baseline:
> backend `583511d`, frontend `3a57718`, deploy `8cb1dbe`. **Shipped at:** backend `00c2c73`,
> frontend `705833d`, deploy `844e8f9` — released as **v2026.6** (staging 2026-08-07, prod
> 2026-08-08). Plan and tasks archived to `archive/PLAN_Phase7-GatewayWAF-CSP_2026-08-06.md` /
> `archive/TASKS_Phase7-GatewayWAF-CSP_2026-08-06.md`.

> Root goal: the gateway WAF detects attacks precisely instead of being tuned into irrelevance;
> the browser enforces a strict CSP; and every finding from the 2026-07-02 security review is
> either fixed or explicitly and defensibly accepted. Scoped via `/update-target-state` rather than
> `/plan` — the trigger was an operational complaint (WAF false positives requiring near-daily rule
> exclusions), and scoping surfaced a mechanical root cause plus an unpatched CVE. Specs written
> this cycle: `target/requirements/16_gateway_waf.md`, `target/requirements/15_security_headers.md`,
> `02_auth_and_roles.md` (BR-SEC-020/021). One challenger round run — findings and the three
> corrections it forced are in `decisions.md` (2026-07-27 entry).

| Goal | Concern | Repos | Outcome |
|---|---|---|---|
| **G1** — Gateway build modernised and self-maintained | Vendor `coraza-proxy-wasm`; spike the real Go/TinyGo ceiling; upgrade Coraza ≥3.5.0 and CRS ≥4.22.0; gateway builder stage to Minimus | deploy | ✓ Vendored in `gateway-docker/`; the `git clone` + awk `plugin.go` rewrite is deleted. Coraza **v3.3.3 → v3.7.0**, CRS **v4.14.0 → v4.25.1 LTS**. Go 1.25 / TinyGo 0.39.0. Ten upstream-`0.6.0` divergences documented and **asserted at build time** (5 file patches, 5 version floors). Base images digest-pinned; builder on `reg.mini.dev/go` |
| **G2** — WAF verification (**HARD GATE**) | CVE-2026-21876 blocked; runtime regex-scoped `ctl:ruleRemoveTargetById` proven to fire; no detection regression | deploy | ✓ Passed, but only after the test itself was fixed **three times** — the original CVE regression test could not fail. Harness runs against a real APISIX on the docker net (`worker_processes 1`, 3 GB cap for the WASM OOM) |
| **G3** — Payload design fixed at the source | Prompt injection closed; chat transcripts persisted server-side instead of replayed; exam images by URL; `max_length` on free-text fields | backend, frontend, deploy | ✓ `ReviewChatMessage.role` → `Literal["student","ai"]`, closing a live injection hole that let a client add a `system` turn to an authenticated LLM call. V42 persists review chat; V43 migrates base64 `image_url` to files behind `POST /api/exams/images` + `GET /images/questions/{f}`. `max_length` 4000/1000 on free text |
| **G4** — Exclusions rewritten field-scoped or deleted | Retire the 38-ID block; restore anomaly threshold 5 on the authoring route; disambiguate route priorities | deploy, backend | ✓ Blanket `ctl:ruleRemoveById` **38 → 1**. The survivor (`931130`) is structural, not residue: it targets a `TX` variable, so the `ARGS_POST` regex form that replaced the other 37 cannot apply. 41 field-scoped exclusions are now expressible at all — they were silently inert on v3.3.3 |
| **G5** — CSP enforced | Nonce CSP in the existing `proxy.ts`; working report collector; Report-Only soak including the OIDC round-trip; then enforce | frontend | ✓ Enforced in prod, Report-Only kept in dev as the CI regression surface. Collector now **persists** reports (it discarded them, making the soak unable to report). All 27 routes dynamic (BR-CSP-010, CI-asserted). Two documented relaxations: `style-src-attr 'unsafe-inline'`, `'wasm-unsafe-eval'` (pdfjs) |
| **G6** — Auth and transport verification | BR-SEC-021 TLS verification to Keycloak; BR-SEC-020 JWT audience; internal TLS (M5); Keycloak realm policy (H3) | backend, deploy | ✓ `OAUTH__KEYCLOAK__SSL_VERIFY` defaults **true** in compose (was `false` in prod and staging — a finding the July review missed). Realm policy hardened: 12-char, no-username/email, history 3, 30-attempt lockout, `sslRequired external`. **T6.3.4 closed as accepted risk** — no Postgres TLS, reasoning on record |
| **G7** — Residual review items | M2/B4 streaming size cap; M3 Jenkins params; M4 Tailscale ACLs; L3 header; documented acceptances; Phase 5.6 parked gaps; 2026-07-27 audit anomalies | deploy, backend, frontend | ✓ `RequestBodySizeLimitMiddleware` (streamed, chunked-aware). Jenkins params validated + trigger access restricted. APISIX admin UI disabled and the Admin API closed on staging too. Every `SECURITY_REVIEW_2026-07-02.md` row closed or carrying a written acceptance — **four closed by deciding not to fix, each with reasoning on record** |
| **G8** — Review gate and closeout (**HARD GATE**) | Two independent adversarial security-review passes; proxy-wasm upgrade runbook; specs reconciled with what shipped | specs | ✓ Pass 2 run **blind, on a different model**. 14 findings, 11 distinct, all fixed or explicitly accepted. **The dominant defect class was false assurance, not missing controls**: a CVE test that could not fail, a WAF gate wired into no pipeline, and a vendoring record that would have led a faithful re-vendor to silently restore the CVE |

DAG spine: G1 → G2 (gate) → G3 → G4 → G5 → G6 → G7 → G8 (gate). G5/G6/G7 are mutually independent
once G4 lands; G3 may start alongside G1 since it has no dependency on the WAF build; G4 must not
begin until G2 passes.
Baseline at planning: backend `c82d466`, frontend `67a883c`, deploy `861705b`, specs `1928b48`.

**Why G3 precedes G4:** fixing the payloads first means several exclusions get *deleted* rather
than carefully rewritten for a request shape that is about to stop existing. Sequencing them the
other way would spend the phase's most delicate work on configuration that G3 then obsoletes.

**Scope locks:** Coraza stays — SafeLine and open-appsec were evaluated and rejected with reasons
recorded in `16_gateway_waf.md`, so neither should be re-litigated. Only the *gateway builder
stage* of the Minimus migration is in scope; the other ~25 services stay in Phase 8, because
running two hard gates across three repos and two unrelated concerns would make a G2 failure
unattributable between the Coraza upgrade and the base-image swap.

**Carried into Phase 8:** the remaining Minimus container-image migration
(`target/requirements/14_container_images.md`), and CrowdSec AppSec virtual patching as a
complementary per-route layer on non-prose endpoints (the deployed CrowdSec integration is IP
reputation only today — no `appsec_config`, no acquisition datasource, no request forwarding).

**Not in this phase's scope (unchanged from Phase 6):** tutor self-service role assignment (needs
a `tutor_profiles` table); `invite-role` + `/institution` route guard (**blocked** —
institution_admin is on explicit hold per `decisions.md` 2026-07-27); RAG ops cleanup; per-child
audience scoping of parent content; parent-facing hAITU endpoints. Also out: the Platform Admin
twin of Phase 6's parent indexing-status gap; a dedicated IDOR test pass; authenticated ZAP DAST
on staging; gitleaks as a pre-commit hook; staging/prod OpenBao bring-up (runbook exists,
execution deferred until those environments are stood up); and the `other/services/*` stacks,
which were never inside the OpenBao migration boundary.

---

## Phase 7.5 — Minimus Container Images + Phase 7 Deploy Backlog (stub, 2026-08-09)

> **Planned 2026-08-09 via `/plan`** — goal tree in `PLAN.md`, checkboxes in `TASKS.md`, baselined
> against backend `00c2c73`, frontend `705833d`, deploy `844e8f9`. **87 tasks** (deploy 66, specs 13,
> backend 6, frontend 2) across seven goals; two challenger rounds run. The goals below are the
> shape the plan was built from and are unchanged, with three additions the planning cycle decided:
> **G2 gains T2.9** (Go builder version parity — Phase 7 moved the digest but never checked the
> version behind it against `go.mod`), **G3 grows** from a stand-up to alert rules + dashboards +
> alert routing (T3.4–T3.6; no alert rule exists anywhere in the repo today — the paging *policy*
> stays out, with the destination an owner input at implementation time), and **G7** is added for
> the specs/close-out work. Full decision record: `decisions.md`, 2026-08-09 planning entry.
>
> Two findings from planning worth reading before implementing: `common/.env.config.common.sh:39`/
> `:44`/`:48` would have made the G6.1 KV migration a no-op **while its own verification passed**,
> and G6.3/G6.4 as originally split had a legal ordering that shipped the credential clobber the
> stub warns about. Both are fixed in the plan (T6.1.6/T6.1.8, and T6.3.2 as a single task).
>
> Specs: `target/requirements/14_container_images.md` for G1–G4 (written 2026-07-26, unchanged — it
> already carries the full inventory, version targets and variant-tier policy, so no
> `/update-target-state` pass was needed there). **G6 has its own spec:**
> `target/requirements/13_secrets_management.md`, BR-SEC-022/023 plus an amended BR-SEC-011
> (`/update-target-state` pass run 2026-08-09).

> Root goal: every container image in the stack pulls from **Minimus** (`reg.mini.dev`) at an
> explicit pinned version tag, and the deploy-layer failure modes that the v2026.6 prod window
> exposed — all of them fail-open — are closed.

**Why these two concerns share a phase.** They are the same layer. The Minimus migration is about
what the runtime is built from and whether that is pinned; B5's residual is that the *container
runtime itself* (rootless Docker / rootlesskit) is unpinned across hosts, which is what broke the
v2026.6 deploy. Pinning images while leaving the runtime that executes them to drift would fix the
visible half of one problem.

| Goal | Concern | Repos | Outcome |
|---|---|---|---|
| **G1** — Application images | `haisir-backend/Dockerfile` and `haisir-frontend/Dockerfile`: builder **and** runtime stages to `reg.mini.dev` at pinned tags. Removes the current split where the runtime is `cgr.dev/chainguard/{python,node}:latest` and the builder falls back to Docker Hub `python:3.14-slim` / node — a split that exists *only* because Chainguard's free tier has no pinned tag | backend, frontend | |
| **G2** — Infrastructure images | Postgres+pgvector, APISIX runtime, Keycloak, etcd. **Deletes the from-source pgvector compile** in `postgres-docker/` — Minimus ships a maintained standalone Postgres+pgvector image. Extends hardening to APISIX/Keycloak/etcd, which are plain Docker Hub / quay.io today with none of the non-root/minimal-surface properties | deploy | |
| **G3** — Monitoring unblocked | Prometheus + Grafana, deferred outright in `decisions.md` 2026-06-18 because Chainguard gated them behind a paid plan. Now free at pinned tags | deploy | |
| **G4** — Pinning discipline proven | No `:latest` anywhere; `-dev` variants confined to build stages and never shipped; the three components with **no** Minimus equivalent (CrowdSec, HF text-embeddings-inference, dockhand) explicitly recorded as staying put (BR-INFRA-006), not silently missed | deploy | |
| **G5** — Deploy backlog closed | B1, B3, B4, B5-residual — see the backlog section below. **B6 moves to G6**, which fixes it at the mechanism rather than the value | deploy, backend | |
| **G6** — Env files under release control | The three deploy config files (`{env}/.env`, `{env}/.env.config.sh`, `common/.env.config.common.sh`) become version-controlled and ship with the release instead of being hand-copied to each host (**BR-SEC-022**). Host-topology values move to `secret/haisir/infra`; `ip-restriction` becomes deny-by-default (**BR-SEC-023**, **absorbs B6**); the ~130 lines of remote image-tag reconciliation in `deploy.sh` and the entire parallel manual deploy path are deleted | deploy, specs | |

### G6 — Env files under release control

**Why it belongs here.** Every other goal in this phase is about a fail-open deploy-layer default.
G6 is the same shape: three files that CI cannot see, reconciled by inference against whatever is
already on the host. It also *contains* B6 — see below.

> **Spec:** `target/requirements/13_secrets_management.md` — **BR-SEC-022** (env config version-controlled, deployed from the release at mode 600, remote copy never authoritative; the nine fully-derived `secret/haisir/infra` keys; `REMOTE_*` barred from the committed files) and **BR-SEC-023** (`ip-restriction` always present, empty CIDR = deny-all). BR-SEC-011 was amended in the same pass — CIDRs are no longer permitted non-secret config, and committing the three files is now required rather than merely allowed. Numbered 022/023 because `02_auth_and_roles.md` already holds BR-SEC-020/021 (JWT audience, Keycloak TLS) from Phase 7 G6 — unrelated rules, same IDs, do not confuse them.

**Scope guard, non-negotiable:** three files, by exact filename, across all three environments
(`dev`, `staging`, `prod`). `haisir-deploy/{env}/.env`, `haisir-deploy/{env}/.env.config.sh`,
`haisir-deploy/common/.env.config.common.sh`. No prefix or suffix variants, no glob or regex
matching, no other file in those directories.

`dev` is committed for reproducibility only — there is no dev CI deploy path, and dev has no
host-topology values, so nothing moves to KV for it. Committing it closes the recurring
"missing dev config var" failures recorded against T3.1, T3.4 and T3.6.

| Subgoal | Concern |
|---|---|
| **G6.1** — Host topology to KV (staging, prod) — **BR-SEC-022** | `TAILSCALE_IP`, `CLIENT_ADMIN_TAILSCALE_IP`, `COMPUTE_TAILSCALE_IP` and every value derived from them move to `secret/haisir/infra`, stored **fully derived**, not as base IPs — `env-setup.sh:128-157` sources both files *before* rendering OpenBao, so a base IP arriving late would leave `${TAILSCALE_IP}/32` evaluating to the literal `/32`. Nine keys per env: `KEYCLOAK_ADMIN_PORT_BINDING`, `BACKEND_DB_PORT_BINDING`, `TAILSCALE_ADMIN_CIDR`, `KEYCLOAK_ADMIN_ALLOWED_CIDR`, `APISIX_ADMIN_ALLOWED_CIDR`, ~~`KC_HOSTNAME_ADMIN`~~ (**removed 2026-08-13, now eight** — see G6.2's reversal), `EXTRACTION__OLLAMA_BASE_URL`, `EMBEDDING__OLLAMA_BASE_URL`, `HAITU__RERANK_BASE_URL`. All added to `deploy-required-keys.txt` (`envs=staging,prod`) so the existing per-key gate aborts on empty. **`template-configs.sh` must start sourcing `render-secrets-hook.sh`** — it is the only consumer of the CIDRs and the only provisioning script that does not |
| **G6.2** — `ip-restriction` deny-by-default (**BR-SEC-023**; **absorbs B6**) | `template-configs.sh:152,168-172` currently deletes the whole plugin when a `*_CIDR` resolves empty. Replace with a deny-all whitelist; never delete the plugin. ⟲ **Exposure model REVERSED 2026-08-13** (decided 2026-08-09, tried, measured, withdrawn): ~~admin reaches Keycloak over the tailnet via `KC_HOSTNAME_ADMIN`~~ — that variable does not move the console's `authServerUrl` and is server-global, so the tailnet path never authenticated and setting it broke the public staging console. **Current model:** routes 13/14/15 stay on the gateway and ship deny-all with **no operator CIDR stored anywhere**; access is granted ad hoc to the running APISIX via `common/scripts/keycloak-admin-access.sh` and reverts on the next deploy. See `decisions.md` 2026-08-13 |
| **G6.3** — Files into git — **BR-SEC-022** (+ the BR-SEC-011 pgadmin exception) | `.gitignore` negations for the three names across all three envs; remove the two `.gitleaks.toml:156-157` allowlist entries that exempt `*.env.config.sh` from scanning; `# pragma: allowlist secret` on `dev/.env:13` (`PGADMIN_DEFAULT_PASSWORD` — local-only tool credential, deliberate). **Strip `REMOTE_HOST`, `REMOTE_USER` and `REMOTE_DEPLOY_DIR` from the committed files entirely** — see the credential-clobber finding below |
| **G6.4** — CI writes them — **BR-SEC-022** | Delete the five `--exclude` lines (`deploy-lib.sh:130-131`, `:139-141`) and the `prepare_remote()` backup/restore block (`:207-231`); add `--chmod=D700,F600`. **Must land in the same commit as G6.3** — the env rsync carries `--delete` (`:142`), and those excludes are currently the only thing protecting the remote copies from it |
| **G6.5** — Delete the version reconciliation | `deploy.sh:356-485` (VERSION `sed` + tag resolution), `:169` (`ROLLBACK_VERSION`), `:177-182` (six `*_IMAGE_TAG_OVERRIDE` reads), `:238-258` (their display block), and `image_tags` / `rollback.previous_version` in `releases/manifest-template.yaml`. Keep `:535-574` — that compares `.env` against running containers, which is drift detection, not version arithmetic. Add a Validate-stage assertion that the manifest version equals `VERSION=` in the committed `{env}/.env` |
| **G6.6** — Retire the manual deploy path | Delete `common/deploy-remote-common.sh`, `staging/deploy-remote.sh`, `prod/deploy-remote.sh`. It is a separately-written second implementation of the same sync that has already drifted from `deploy-lib.sh` (different excludes, different backup set, `${REMOTE_HOST}:` with no `user@`). Keeping it means applying every G6.4 change twice forever. Local deploys become `deploy.sh` with the three `REMOTE_*` vars exported. Check `common/scripts/tests/test-runner.sh`, which reads `REMOTE_HOST` from the env config and will need it from the environment instead |

**Root cause of B6, traced through all three layers** (2026-08-09):

1. `common/.env.config.common.sh:44` sets `KEYCLOAK_ADMIN_ALLOWED_CIDR="${KEYCLOAK_ADMIN_ALLOWED_CIDR:-127.0.0.1/32}"` — a fail-closed default that never fires, because common is sourced *first* and the env file *second*, so any env-level assignment wins. The `:-` guard is decorative.
2. `prod/.env.config.sh:23` sets it to `""` explicitly.
3. `template-configs.sh:152` flags empty → `:168-172` deletes `ip-restriction` from routes 13/14/15 → the Keycloak admin console is served to the public internet with no network restriction.

Fixing (3) makes (1) and (2) harmless, which is why G6.2 fixes the mechanism and not the value. The
change is a net deletion: at `:152`, substitute `127.0.0.1/32` instead of setting
`strip_ip_restriction=true`; delete the `jq del` block at `:168-172`. An empty whitelist array fails
`ip-restriction`'s schema, so `127.0.0.1/32` is the schema-valid way to express deny-all — and since
`real-ip` resolves the client address from `cf-connecting-ip` in prod, no external client can ever
present it.

> **⟲ SUPERSEDED 2026-08-13 — the paragraph below was acted on, and was wrong.** Setting
> `KC_HOSTNAME_ADMIN` to the tailnet origin shipped in v2026.7 and broke the staging admin console
> outright, because the variable is **server-global, not master-scoped**. Worse, it would not have
> worked even so: it governs the console's own base URLs but **not** its `authServerUrl`, which
> follows `KC_HOSTNAME` — so the browser is always sent back to the public origin to authenticate.
> There was never an end-to-end tailnet path to gate on. Kept below as the record of the reasoning
> that produced the detour.
>
> **The actual resolution**: deny-all with no stored CIDR, plus an on-demand grant against the
> running APISIX (`common/scripts/keycloak-admin-access.sh`). The access-loss concern is real but
> much narrower than it looked — routes 13/14/15 have **zero path overlap** with route 01
> (`/realms/haisir-realm-{{APP_ENV}}/*`), so normal user authentication cannot be affected at all.
>
> ~~**⚠ Access-loss risk — G6.2 must not land alone.** After the fix,
> `https://haisir.in/admin/master/console/` returns 403 and the only remaining admin path is the
> tailnet binding (`KEYCLOAK_ADMIN_PORT_BINDING`, host `:8180` → container `:8443`). But
> `common/docker-compose.yml:442-443` sets `KC_HOSTNAME=${KC_HOSTNAME}` (= `https://haisir.in`) with
> `KC_HOSTNAME_STRICT=true` and **no `KC_HOSTNAME_ADMIN`** — so Keycloak generates console URLs
> against the public hostname and will bounce a tailnet request back to the address that is now
> denied. Set `KC_HOSTNAME_ADMIN` to the tailnet origin and **verify an admin login over the tailnet
> works** before the deny-all takes effect. This is precisely the "risks losing admin access to the
> system that authenticates everything else" concern recorded against B6.~~

Note `dev/.env.config.sh:54` sets `KEYCLOAK_ADMIN_ALLOWED_CIDR="0.0.0.0/0"` — a deliberate dev
convenience that stays, but it means dev never exercises the deny-by-default path. G6.2's test has to
run somewhere other than dev.

**Credential clobber — introduced by the change itself, so it must land inside G6.3.** Today CI never
sees these files, so `deploy.sh:193-200` takes its `elif [[ -z "${REMOTE_HOST:-}" ]]` branch and the
Jenkins-injected `REMOTE_HOST`/`REMOTE_USER` credentials survive. Once the files are committed they
exist in the Jenkins workspace, `load_env_config` sources them, and `staging/.env.config.sh:36` /
`prod/.env.config.sh:34`'s `export REMOTE_HOST=...` **overwrites the credential**. All three
`REMOTE_*` vars must therefore leave the committed files outright — not become `${VAR:-default}`,
which is the same decorative-`:-` pattern that made `common/.env.config.common.sh:44`'s fail-closed
CIDR default useless.

They are safe to remove: every consumer is deploy-client-side (`deploy.sh`, `deploy-lib.sh`,
`deploy-remote-common.sh`, `common/scripts/tests/test-runner.sh`). Nothing running on the staging or
prod host reads them, even though `common/.env.config.common.sh` is rsynced there and sourced on the
remote. CI supplies `REMOTE_HOST` and `REMOTE_USER` as Jenkins secret-text today; add
`REMOTE_DEPLOY_DIR` as a third rather than relying on `deploy.sh:204`'s `~/haisir-deploy` fallback
expanding correctly inside a quoted rsync target.

**Already done, not in scope:** the gateway *builder* stage (`gateway-docker/Dockerfile:69` is on
`reg.mini.dev/go@<digest>`). That was Phase 7's deliberate carve-out — running the base-image swap
and the Coraza upgrade behind the same hard gate would have made a G2 failure unattributable
between the two. The gateway *runtime* stage (`apache/apisix:3.17.0-ubuntu`) is in G2 here.

**Implementation note carried from the spec:** Minimus publishes its own agent migration workflow
(DISCOVER → SELECT TAG → INSPECT → CHECK FOR SHELL → RESOLVE PACKAGES → WRITE → VERIFY → ANALYZE) at
`https://api.mini.dev/v1/skills/dockerfile`. Pull it fresh at implementation time — Minimus revises
it independently of our spec, so a copy cached in this repo would be the stale one.

**Sequencing note.** G5's **B6 is a decision before it is a task**, and it is the most urgent open
security item on the system (Keycloak admin console reachable at `200` from the public internet).
It does not depend on G1–G4 and should not wait behind them.

**Also carried from Phase 7, not claimed as done there:**

- A decision on frontend `92a4da2` — a CSP e2e-soak commit that **neither G8 review pass covered**;
  both ran against the host range ending at `d6adec7`.
- `question_id` is sent by the frontend on `POST /api/haitu/exam-review-chat` but is not declared on
  `ExamReviewChatRequest`, so Pydantic drops it — the field is inert. Behaviour is still correct
  (grounding covers every question in the attempt), but per-question grounding is not what happens.
  Either declare it and narrow the grounding, or delete it from the payload.

> **Resolved and no longer carried — two of the three close-out items:**
>
> 1. **The live end-to-end load of the rebuilt image-serving path.** Image serving and the V43
>    base64→file migration were both exercised on the deployed stack during the v2026.6 prod window
>    (2026-08-08), after the B5 route-push failure was fixed.
> 2. **A real Jenkins run of the WAF gate.** `stage('WAF Functional Gate')`
>    (`gateway-docker/Jenkinsfile:158`) invokes `common/scripts/tests/waf-harness.sh` with **no `when`
>    guard**, deliberately placed *before* `Export Image` and `Push to Registry` so a non-filtering
>    image cannot reach the registry. The v2026.6 gateway image running in prod is therefore itself
>    the evidence: it could not have been built and pushed without the gate passing. The harness also
>    carries the **CVE-2026-21876** multipart charset-bypass test (`waf-harness.sh:291–350`), which
>    asserts the 403 is attributed to rule **922110** rather than accepting a collateral XSS match —
>    so the CVE regression is gated in CI too. Scope note kept from the Jenkinsfile's own comment:
>    the gate proves the WAF *runs and filters*, not **which** Coraza/CRS version it runs; the version
>    floors are asserted at build time in the Dockerfile (`coraza-proxy-wasm/VENDORED.md`).

---

## Backlog — surfaced during Phase 7 close-out, deliberately not folded into it

> Found 2026-08-07/08 while verifying the Phase 7 staging and prod deploys. None is Phase 7 scope.
> Recorded here rather than retrofitted into a closed phase, so the phase record stays honest about
> what it actually covered.
>
> **B1, B3, B4 and B5-residual are claimed by Phase 7.5 G5** (above). **B6 is claimed by G6.2**
> (**BR-SEC-023**), which fixes the fail-open mechanism in `template-configs.sh` rather than setting
> a CIDR value — see the root-cause trace under G6. **B2 stays in the backlog** — it is not deploy-blocking.
>
> Worth naming as a pattern rather than five separate tickets: **B4, B5 and B6 all fail open.**
> B4 collapses every failure cause into one generic message by swallowing stderr; B5 assumed a host
> address and silently allowed the wrong one; B6's `template-configs.sh` responds to an empty
> `*_CIDR` by **dropping the ip-restriction plugin entirely** rather than refusing to template. Each
> was found by accident, and none would appear in a config diff.

### B1 — Worker poller sessions sit `idle in transaction` (backend) — **the one worth fixing properly**

**Observed:** on staging, the `extraction_jobs` and `essay_grading_jobs` poller sessions had held
open transactions for **2h27m**. Confirmed identically on prod (2 sessions). Both loops use
`FOR UPDATE SKIP LOCKED` and appear to leave the session open between polls rather than committing
or rolling back.

**Why this matters beyond tidiness — two distinct consequences:**

1. **It blocks DDL, and does so in the worst way.** A `REINDEX`/`ALTER TABLE` needing
   `ACCESS EXCLUSIVE` queues behind the idle transaction — and once that request is queued, **every
   subsequent reader queues behind it too**. So the failure mode is not "migration fails fast", it is
   "the whole app stalls." This was not theoretical: it is exactly how the first staging reindex
   attempt behaved, and it had to be cancelled. **A future `alembic upgrade head` during a deploy can
   stall the application the same way** — see the prod deploy caution in B2.
2. **It holds back the xmin horizon**, so autovacuum cannot reclaim dead tuples anywhere in the
   database for as long as the oldest transaction stays open.

**Fix direction:** commit or roll back between poll iterations so the session returns to `idle`, not
`idle in transaction`. A `statement_timeout`/`idle_in_transaction_session_timeout` on the worker role
is a defence-in-depth backstop, not the fix. Restarting the worker only resets the clock.

**Do not fix blind** — the loops are `FOR UPDATE SKIP LOCKED` claim-and-process, so transaction
boundaries carry the claim semantics. Changing them needs its own tests.

### B2 — Postgres collation version mismatch (ops) — **RECURRING, not one-time. Reopened 2026-08-15**

Both environments were created under glibc collation **2.42**; the OS now provides **2.43**. That
makes text sort order potentially wrong in indexes built under the old version — 30 `text`/`varchar`
indexes in each environment.

- **staging: FIXED 2026-08-07** — `REINDEX DATABASE` (228 ms, 11 MB) then
  `ALTER DATABASE … REFRESH COLLATION VERSION`, worker stopped for ~40 s. `datcollversion` 2.42 → 2.43,
  0 invalid indexes, all 74 indexes intact.
- **prod: FIXED 2026-08-07** — same procedure, run by the operator (stopping a prod container is outside
  what the assistant is permitted to do). `datcollversion` 2.42 → 2.43, 0 invalid indexes, worker back
  healthy, `/` and `/api/auth/csrf` both 200.

> **RECURRED on staging 2026-08-15, reintroduced by the v2026.7 Minimus migration.** Moving onto
> `reg.mini.dev` base images moved glibc again, 2.43 → **2.44**, and every database went back into
> mismatch. **This is the correction that matters: B2 is not a defect that gets fixed, it is a
> standing consequence of changing a base image.** Any release that moves a Postgres base image
> reintroduces it, silently, with a healthy container and a warning nobody reads. It belongs in
> `post_deploy` on every such manifest, not in a backlog list of closed items.
>
> **The 2026-08-07 fix was also under-scoped, in a way only the second occurrence revealed.** It
> treated one database per host. The 2026-08-15 readings found the miss: on the app cluster
> `template1` and `postgres` were still at **2.42** — untouched by that fix and a full two versions
> behind — and the entire **keycloak-db cluster** (`haisir_keycloak_db`, `template1`, `postgres`) was
> at 2.42 as well, never considered at all. `template1` is the one that compounds: a stale template
> means every database created from it inherits the old collation version, so the defect reproduces
> itself into anything provisioned later.
>
> **staging: FIXED AGAIN 2026-08-15** — all four rows on both clusters now read 2.44.
> `REINDEX DATABASE CONCURRENTLY` then `REFRESH COLLATION VERSION` on the two user databases
> (`haisir_app_db`, `haisir_keycloak_db`); bare `REFRESH` on `template1` and `postgres` in each
> cluster, no reindex — they hold only system catalogs, whose text columns are the `name` type, which
> is always C collation and therefore immune to glibc changes. `CONCURRENTLY` avoids the
> ACCESS EXCLUSIVE locks plain `REINDEX DATABASE` takes per index, so nothing had to be stopped —
> an improvement on the 2026-08-07 procedure, which stopped the worker for ~40 s. `template0` reads
> NULL and is correct untouched: it is frozen and unconnectable by design.
>
> **prod: OUTSTANDING.** Prod runs the same migration and will show the same mismatch on both
> clusters the moment v2026.7 lands. Prod's `keycloak-db` was on unpinned `chainguard/postgres:latest`
> and has never been pinned, so expect a baseline at or below 2.42 — on the cluster holding real user
> records. Read `SELECT datname, datcollversion FROM pg_database` on **both** prod clusters *before*
> the deploy, so the reindex is planned rather than discovered mid-window.
>
> Worth naming, because it is the argument for the pinning work in this phase: the keycloak cluster's
> 2.42 baseline predates v2026.7 entirely. An **unpinned** `:latest` had been rolling new glibc under
> a live data directory for months. The migration did not cause this; pinning is what finally made it
> visible.

  > Observed on the restart: `idle in transaction` was back at **2** within a minute. B1 reproduces
  > immediately — restarting the worker only resets the clock, it does not avoid the problem.

**Order is load-bearing:** `REINDEX` **first**, then `REFRESH COLLATION VERSION`. Refreshing alone
silences the warning while leaving every index built under the old collation — it removes the signal
and keeps the risk, which is strictly worse than doing nothing.

**Caution for the prod v2026.6 deploy:** the deploy runs `alembic upgrade head`. With B1 unfixed and
prod currently showing 2 idle-in-transaction sessions, a migration needing an exclusive lock can
stall behind them and take the app with it. Stop `haisir-worker-prod` before the deploy, or confirm
`SELECT count(*) FROM pg_stat_activity WHERE state='idle in transaction'` is 0 first.

### B3 — `other/` is outside the deploy rsync path, so hook fixes never reach the hosts (ops)

`common/deploy-remote-common.sh` (sync step) rsyncs **only** `common/` and `${ENV}/`. Anything under
`other/` — including `other/cert/haisir-sync-certs.sh`, installed as the certbot renewal hook — is
hand-placed on each host and never updated by a deploy.

**Found 2026-08-07, prod.** The T1.3.3 OpenBao fallback (`3abeda3`, 2026-07-16) had been in the repo
for three weeks and had never reached prod. The installed hook was an older revision still, older
than both HEAD and the March version. Effect: every certbot deploy hook since ~2026-07-16 aborted at
its `APISIX_ADMIN_KEY` guard, before the cert copy — so certbot kept renewing correctly while
**nothing distributed the result**. Discovered incidentally: `/etc/letsencrypt/live/haisir.in` held a
cert valid to **Oct 14 2026** while APISIX was still serving one expiring **Aug 15 2026**, 8 days out.
Invisible from outside because cftunnel terminates public TLS at Cloudflare's edge cert.

Two candidate fixes — the second is the one that actually closes it:

1. Extend the sync to cover `other/cert/`. Cheap, but only fixes files that happen to live under a
   synced path; the installed copy at `/etc/letsencrypt/renewal-hooks/deploy/` is still a *copy*.
2. Have the deploy assert the installed hook matches the repo (hash compare, fail loud). Catches
   drift regardless of how the file got there.

> The failure is silent by construction: a broken renewal hook produces no alert, and the only
> symptom is a cert quietly approaching expiry behind an edge terminator that hides it.

### B4 — T1.3.3's OpenBao render was never exercised as root (ops / deploy)

`other/cert/haisir-sync-certs.sh` requires root (it reads `/etc/letsencrypt`), but T1.3.3 made it call
`render_deploy_secrets_or_die` → `render-deploy-secrets.sh` → `docker exec openbao-prod`. staging and
prod run **rootless** Docker under `sss` (`common/openbao/bootstrap.sh` notes this), so root sees a
different, empty daemon and has no `docker` binary on `PATH`. The render therefore fails in the one
context the hook actually runs in, while working fine under `deploy.sh` — which runs as `sss`.

Fixed 2026-08-07 in `561e631`: when `EUID -eq 0`, point `DOCKER_HOST` at
`/run/user/$(id -u sss)/docker.sock` and prepend `/home/sss/bin` to `PATH`, rather than dropping
privileges (which would lose the `/etc/letsencrypt` access the rest of the script needs).

**The wider item, unfixed:** `bao_deploy_token()` in `common/openbao/render-deploy-secrets.sh`
redirects stderr to `/dev/null`, so *every* failure mode — container down, sealed vault, missing cert,
unregistered role, `docker: command not found`, wrong socket — collapses into one generic message
listing four causes, none of which was the actual one here. Surfacing the underlying stderr on failure
would have made this a one-minute diagnosis instead of a multi-step bisection.

> Related dependency worth noting: the rootless socket only exists while `sss` has a live systemd user
> session. If linger is ever disabled, the hook breaks again at the next unattended renewal.

### B5 — `allow_admin` assumes the wrong host address under rootless Docker (deploy)

**Broke the v2026.6 prod deploy 2026-08-08.** `common/apisix_conf/config.yaml`'s `allow_admin` carries
`10.0.2.0/24` commented *"rootless Docker slirp4netns (host appears as 10.0.2.2)"*. On prod the host
does not appear as `10.0.2.2` — a host-originated call to a published port arrives as the **bridge
gateway, `172.19.0.1`**. That address used to be covered by the `172.19.0.0/16` entry **T7.7.1
removed**, and nothing noticed because `setup.sh` still reached the Admin API over the Tailscale IP,
which its own `/32` allowed. T7.7.2 then moved the binding to loopback — and the two changes, each
correct alone, left no entry matching the caller.

Result: Step 8's `setup.sh` could not reach the Admin API, so **routes, plugin configs and global
rules were never pushed**. Backend, frontend and gateway were all healthy on v2026.6 and login worked,
because APISIX kept serving the previous route table — while `26-images-questions`, new in this
release, was absent and V43 had already rewritten every `questions.image_url` to a path only that
route can serve. A deploy that reports failure at the last step but leaves a *working-looking* site.

Fixed live by setting `APISIX_ADMIN_ALLOWED_CIDR="172.19.0.1/32"` in `prod/.env.config.sh` — the
bridge gateway only, deliberately **not** the `/16`, so T7.7.1's reason for removing it (any container
on haisir-net that learned the admin key could rewrite every route) still holds: containers get
`172.19.0.x`, `.1` is the bridge itself. `.env.config.sh` is gitignored and lives on the host, so the
fix survives future deploys.

**Why staging was unaffected — answered 2026-08-08, and it is not reassuring.** Staging's `allow_admin`
is *identical* (`10.0.2.0/24`, own Tailscale `/32`, workstation `/32`), `APISIX_ADMIN*` is absent from
its `.env` too, and its bridge gateway is also `172.19.0.1`. Same config, same subnet, opposite result:
staging's Admin API answers **401** to a host-originated call (IP accepted) where prod answered 403.
The difference is the **rootlesskit port driver** — neither host sets `--port-driver` explicitly, so
each follows its own rootlesskit version, and the two rewrite the source address differently
(`slirp4netns` → `10.0.2.2`, `builtin` → the bridge gateway). Staging is therefore not correct by
design; it is correct by accident, and a rootlesskit upgrade there reproduces prod's failure exactly.

**Fixed at the template 2026-08-08:** `allow_admin` now carries **both** `10.0.2.0/24` and
`172.19.0.1/32`, so either port driver resolves. Prod's `APISIX_ADMIN_ALLOWED_CIDR="172.19.0.1/32"`
override becomes redundant on its next deploy but is harmless. Residual worth naming: this is
**environment drift at the container-runtime layer**, invisible to every config diff, and an IP
allowlist was simply the first thing to depend on it. Pinning the rootless Docker/rootlesskit version
across hosts is the real remedy and is not done.

### B6 — Keycloak admin routes run with no IP allowlist (security, pre-existing)

Surfaced incidentally while re-templating prod on 2026-08-08:

```
INFO: ip-restriction disabled for 13-keycloak-admin.json (CIDR variable is empty)
INFO: ip-restriction disabled for 14-keycloak-master-realm.json (CIDR variable is empty)
INFO: ip-restriction disabled for 15-keycloak-admin-resources.json (CIDR variable is empty)
```

`KEYCLOAK_ADMIN_ALLOWED_CIDR` is empty in `prod/.env.config.sh`, and `template-configs.sh` responds by
**dropping the plugin entirely** rather than failing closed — so the Keycloak admin console and master
realm are exposed with no network restriction. Predates Phase 7 and is unrelated to the v2026.6
deploy; it is recorded here because nothing else would have surfaced it.

**Confirmed reachable from the public internet, 2026-08-08:**

```
GET https://haisir.in/admin/                     -> 308
GET https://haisir.in/admin/master/console/      -> 200
GET https://haisir.in/realms/master/.well-known/openid-configuration -> 200
```

Not trivially exploitable — this release's realm policy sets `length(12) and notUsername and notEmail
and passwordHistory(3)`, `failureFactor 30`, and `sslRequired external` — but it is an unauthenticated
attack surface on the IdP that gates every other service, plus whatever Keycloak version-specific
surface the console carries.

**Deliberately NOT fixed in the v2026.6 window.** The obvious fix (set the CIDR to the admin
workstation's Tailscale `/32`) does not work as written: admin traffic arrives through cftunnel, so the
address `ip-restriction` evaluates is the real client IP extracted by `real-ip`, not a tailnet address.
Applying that value would lock everyone out of the IdP admin console rather than restrict it. The
decision needed first is **from where should the Keycloak admin console be reachable at all** — public
with an IP allowlist, or removed from the public gateway entirely and reached over the tailnet
directly. That is an owner decision, and making it at the end of a deploy window risks losing admin
access to the system that authenticates everything else.

Three pieces of work once decided: pick the exposure model, set the CIDR (or drop routes 13/14/15 from
the public gateway), and change the empty-variable behaviour from "disable the restriction" to "fail
the templating" — the current default silently weakens security on a missing value, the same fail-open
shape as B4's swallowed stderr and B5's `10.0.2.0/24` assumption.

### B7 — No app-level "service down" or certificate-expiry alerting (deploy)

**Found 2026-08-11 while implementing T3.4 (write the alert rules).** T3.4 named six failure modes to
cover: service down (backend, worker, frontend, apisix, keycloak, db), certificate expiry inside 21
days, Postgres idle-in-transaction, disk space, and APISIX 5xx rate. Only apisix and db (via
`postgres-exporter`) are actually observable today — `up{job=...}` has no target to evaluate against
for backend, worker, frontend or keycloak, because none of the four expose a Prometheus `/metrics`
endpoint, and no exporter in the stack produces certificate-expiry data at all.

**Why not fixed in T3.4:** writing an alert rule against a metric no exporter ever produces would pass
`promtool check rules` (syntax only) but never fire — same fail-open shape B4/B5/B6 already named in
this backlog, just for a monitoring gap instead of a deploy one. T3.4 is `[deploy]` scope; instrumenting
FastAPI/Node apps to expose `/metrics` is `[backend]`/`[frontend]` work in different repos, so folding
it into T3.4 would have meant either silently under-delivering four of six failure modes, or
unilaterally adding a new exporter service beyond what was asked.

**Fix direction:** add a `blackbox_exporter` service (one new `reg.mini.dev` image, same `monitoring`
profile as the rest of T3.1/T3.2) probing each service's existing HTTP health endpoint —
`probe_success` covers "is it up" for backend/worker/frontend/keycloak in one shot, and the same probe's
`probe_ssl_earliest_cert_expiry` metric covers certificate expiry for free, closing both gaps with one
exporter rather than instrumenting four apps across two repos. Needs a probe-target decision per
service (health path, TLS vs plaintext) before it's a task-sized unit of work — that's why this is a
backlog item and not folded into T3.4 directly.

**Rules file:** `common/prometheus/rules/haisir.rules.yml` has a comment at the `TargetDown` rule
pointing back here so the gap stays visible in the file itself, not just in this doc.

### B8 — `GRAFANA_ADMIN_PASSWORD` is a plain `.env` var, not OpenBao-delivered (deploy) — FIXED 2026-08-11

**Found 2026-08-11 while implementing T3.2 (add the Grafana compose service).** T3.2 wires
`GF_SECURITY_ADMIN_PASSWORD` from `${GRAFANA_ADMIN_PASSWORD}` in `common/docker-compose.yml`'s
`environment:` block — a plain compose env var is readable in full by anyone with `docker inspect`/
`docker exec ... env` access to the host, the exact class of exposure BR-SEC-011 exists to close for
every other service in the stack (backend/worker/db/keycloak all deliver their passwords via a
Vault Agent sidecar rendering a file, never through `environment:`).

**Why not fixed in T3.2:** the correct fix is not a Grafana-only change — it means adding `grafana` as
an 8th OpenBao machine identity (README.md's "Machine identities" table), which touches the shared
fail-closed deploy gate directly: `common/openbao/render-deploy-secrets.sh`'s resolved-paths loop
(`for path in db keycloak gateway infra shared keycloak-clients`) and
`common/openbao/deploy-required-keys.txt` both gate every deploy, staging and prod alike, not just
Grafana's. Getting the new path name wrong there doesn't just leave Grafana with a bad password — it
can block every deploy. That is materially bigger and riskier than "add a compose service," and not
something to fold into T3.2 or invent a new task ID for outside `/plan`.

**Fixed 2026-08-11, owner-requested (implemented the same day it was scoped, after "go ahead and
implement the full B8 fix now").** Mirrored `db`'s pattern exactly
(`common/openbao/agent/db-agent.hcl` → `POSTGRES_PASSWORD_FILE`): `grafana` added as an 8th OpenBao
machine identity — `policies/grafana.hcl` (read-only on `secret/data/haisir/grafana`), a new
`vault-agent-grafana` sidecar (`agent/grafana-agent.hcl` + `agent/templates/
grafana-admin-password.ctmpl`), `openbao-certs-grafana`/`openbao-secrets-grafana` volumes, `grafana`'s
compose service now `depends_on: vault-agent-grafana: condition: service_healthy` and reads the
password via `grafana.ini`'s native `$__file{/etc/secrets/grafana_admin_password}` provider —
`GF_SECURITY_ADMIN_PASSWORD` env var removed entirely, `GRAFANA_ADMIN_PASSWORD` removed from
`.env.template`. `bootstrap.sh`, `generate-certs-openbao.sh` and `render-deploy-secrets.sh`'s
resolved-paths loop all updated to include `grafana`; `README.md`'s identity table, secret-layout
table and bring-up example updated to match.

**Deliberately NOT added to `deploy-required-keys.txt`.** That file's `check_required_keys` gate runs
on *every* deploy regardless of which compose profile is starting — unlike `KC_DB_PASSWORD`/
`POSTGRES_PASSWORD` (always-on core services, required from an environment's very first boot),
Grafana is opt-in (`--profile monitoring`). Adding an unconditional requirement there would fail-close
every deploy — including ones that never touch monitoring — the moment this merged, before any
environment has seeded `secret/haisir/grafana`. The `vault-agent-grafana` healthcheck
(`test -s /secrets/grafana_admin_password`) plus `grafana`'s `depends_on: condition: service_healthy`
already gives the same fail-closed guarantee, correctly scoped to only the monitoring profile.

**Operator action required before the monitoring profile can start on any environment:**
1. Re-run cert generation with `grafana` included:
   `OPENBAO_CLIENT_IDENTITIES="... keycloak grafana admin-ops" bash common/scripts/certs/generate-certs-openbao.sh <env-dir>`
2. Re-run `bootstrap.sh configure` to register the new policy + cert-auth role.
3. Seed `secret/haisir/grafana GRAFANA_ADMIN_PASSWORD=...` (stdin-safe, per README's seeding
   convention — never via argv).
Until all three happen, `vault-agent-grafana` never reports healthy and `grafana` never starts —
fails closed, doesn't silently run with an empty/default password.

**This is now enforced at the release-manifest level, not left to memory** (2026-08-11, same-day
follow-up): `/release-manifest`'s `pre_checks` detection (`.claude/skills/release-manifest/SKILL.md`)
now flags any **new** file under `common/openbao/policies/*.hcl` or `common/openbao/agent/*-agent.hcl`
— i.e. any new OpenBao machine identity, not just `grafana` — and emits the three-step bring-up
reminder above into the generated manifest automatically. Verified live against this exact change:
`git diff 7692891..HEAD --name-status -- common/openbao/policies/ common/openbao/agent/` correctly
finds both new files. `.github/instructions/release-manifest.instructions.md` documents `pre_checks`
as a manifest field for the first time (it previously wasn't mentioned there at all).

**Interim, accepted as-is (not a violation):** `GRAFANA_ADMIN_PASSWORD` stays a plain,
operator-supplied `.env` var for now — same treatment T3.1 already gave `POSTGRES_EXPORTER_DSN` and
`NGINX_EXPORTER_SCRAPE_URI`, a documented gap rather than a silent one.

**Related, but NOT deferred:** T3.2 also shipped `common/grafana/config/grafana.ini` with
`[auth.anonymous] enabled = true` / `org_role = Viewer` live for the first time (the setting predates
T3.1/T3.2 but was dormant until the `grafana` service existed to read it) — flagged in review as
MEDIUM, and unlike the password-delivery mechanism above, this one was cheap and safe to fix
immediately rather than defer: `enabled = false`, fixed 2026-08-11, same commit as this entry's
write-up. The distinction that matters: a one-line config toggle with no shared-mechanism blast
radius gets fixed now; a change that touches the deploy-wide fail-closed gate gets scoped and
tracked instead. Owner feedback: security-relevant defaults (auth, exposure) on a new service should
be surfaced before implementation, not shipped first and caught in review.

### B9 — Jenkins `yamllint` does not cover `releases/`, so no release manifest is ever linted (deploy)

**Found 2026-08-14 while reviewing the Slack switch.** `Jenkinsfile`'s `YAML Lint` stage runs
`yamllint` over `common/ dev/ staging/ prod/ other/services/` — **`releases/` is absent**. Every
release manifest in this repo has therefore shipped without CI ever parsing it. Separately, nothing
in the pipeline reads `common/openbao/deploy-required-keys.txt` at all: `gitleaks` scans it as text,
but no stage validates its entry syntax or the `envs=` allowlist, so an arming mistake — the thing
that can make *every* staging and prod deploy abort — is invisible to CI.

Both files were changed in `5a255e9` and `9c4dbac`, and a green build on those commits proved
nothing about either. They were validated by hand instead (`yamllint` clean, `--dry-run` exit 0 on
both envs, arming checked with the real `manifest_entries` parser), so the coverage exists — it just
is not in the pipeline, which means it depends on someone remembering.

**This is the same defect class Phase 7's G8 review named as dominant: false assurance.** A green
CI run that structurally cannot fail on the files under change is worse than no check, because it
reads as a pass.

**Fix, roughly one line plus one stage.** Add `releases/` to the `yamllint` invocation. Optionally
add a manifest-schema check (`yq` for required keys: `version`, `services`, `steps`, `rollback`) and
a `deploy-required-keys.txt` syntax check — the parser (`common/openbao/manifest.sh`) already exists
and could be run against all three `APP_ENV`s in CI to assert it emits without error.

**Deliberately not folded into Phase 7.5** — the phase's remaining work is a staging deploy and a
prod window, and widening CI scope mid-window risks turning a lint failure into a deploy blocker at
exactly the wrong moment. Do it at the start of the next phase, not now.

### B10 — The route-push fallback installs a grant, not a deny-all, and both the manifest and the code say otherwise (deploy / security)

**Found 2026-08-15 during the G6.1 staging verification.** `create_route_config.sh` preserves a live
`ip-restriction` whitelist across a route push. When the Admin API read *fails* (transport error, not
a 404), it falls back to the template — and logs `applying the template's whitelist`. The release
manifest's `post_deploy` item C describes that same fallback as *"applies the template's **deny-all**
rather than failing quietly"*, and the code's own comment at `create_route_config.sh:207` repeats the
phrase for the too-broad-to-preserve branch.

**Both are wrong wherever `KEYCLOAK_ADMIN_ALLOWED_CIDR` resolves to a real address.** The template is
not a deny-all; it renders whatever that key holds in KV. On staging it renders `100.100.87.31/32` —
a live `/32` grant. So the documented safe fallback actually *installs standing access*.

Staging blast radius is nil: that address is Tailscale-only and unreachable from the internet. **Prod
is the concern** — it is public-fronted through cftunnel, so if prod's KV value is a routable
address, a transport blip during Step 8 would silently publish a standing public grant to the
Keycloak admin console while the runbook states the failure mode is closed. Nothing would look wrong:
the deploy reports success and the warning reads as reassurance.

Note this is *only* the failure path. The normal path is correct and was observed working on
2026-08-15 (live `127.0.0.1/32` preserved over the template on all three keycloak-admin routes).

**Fix:** decide which behaviour is intended, then make text and code agree. Failing closed on an
unreadable Admin API is the safer default — an operator who loses a grant can re-issue it with
`keycloak-admin-access.sh grant`, whereas nobody notices an unintended one. **Prod-window action
regardless:** read what prod's `KEYCLOAK_ADMIN_ALLOWED_CIDR` resolves to *before* Step 8, so the
fallback's actual effect is known rather than assumed.

### B11 — `copy-datadir.sh`'s verification step self-skips against a running backend (deploy)

**Found 2026-08-15 in the staging deploy log.** Step 11 printed
`💡 Backend container not running - data is in volume ready to be mounted` while
`haisir-backend-staging` was `Up 2 days (healthy)`. The copy and the `chown 1000:1000` both succeeded;
what did not happen is the **verification** — the 42-entry ownership check the 2026-08-12 run
performed was silently skipped, because the probe looks for a container it cannot find (almost
certainly a name missing the `-<env>` suffix, the same class of bug as the `haisir-backend-datadir-staging`
decoy-volume error already recorded against that manifest's `pre_checks`).

Low severity on staging, and the datadir work itself is fine. It matters on prod because that step's
*only* verification is this probe: pre_check 10 calls prod "its second execution ever" and leans on
the check to confirm the UID 65532 → 1000 move landed. A verification that cannot fail is the same
false-assurance class as B9. One-line fix; do it before the prod window.
