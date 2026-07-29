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

## Phase 7 — Gateway WAF Modernisation, CSP & Security Review Closeout (active — restored 2026-07-29)

> Scoped 2026-07-27, archived unstarted the same day when Phase 6.5 took priority, **restored
> 2026-07-29** once 6.5 closed. Now the active plan — see `PLAN.md` / `TASKS.md`, and `decisions.md`
> (2026-07-29, "Phase 7 restored from archive") for what the reconciliation changed. Baseline:
> backend `583511d`, frontend `3a57718`, deploy `8cb1dbe`.

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
| **G1** — Gateway build modernised and self-maintained | Vendor `coraza-proxy-wasm`; spike the real Go/TinyGo ceiling; upgrade Coraza ≥3.5.0 and CRS ≥4.22.0; gateway builder stage to Minimus | deploy | |
| **G2** — WAF verification (**HARD GATE**) | CVE-2026-21876 blocked; runtime regex-scoped `ctl:ruleRemoveTargetById` proven to fire; no detection regression | deploy | |
| **G3** — Payload design fixed at the source | Prompt injection closed; chat transcripts persisted server-side instead of replayed; exam images by URL; `max_length` on free-text fields | backend, frontend, deploy | |
| **G4** — Exclusions rewritten field-scoped or deleted | Retire the 38-ID block; restore anomaly threshold 5 on the authoring route; disambiguate route priorities | deploy, backend | |
| **G5** — CSP enforced | Nonce CSP in the existing `proxy.ts`; working report collector; Report-Only soak including the OIDC round-trip; then enforce | frontend | |
| **G6** — Auth and transport verification | BR-SEC-021 TLS verification to Keycloak; BR-SEC-020 JWT audience; internal TLS (M5); Keycloak realm policy (H3) | backend, deploy | |
| **G7** — Residual review items | M2/B4 streaming size cap; M3 Jenkins params; M4 Tailscale ACLs; L3 header; documented acceptances; Phase 5.6 parked gaps; 2026-07-27 audit anomalies | deploy, backend, frontend | |
| **G8** — Review gate and closeout (**HARD GATE**) | Two independent adversarial security-review passes; proxy-wasm upgrade runbook; specs reconciled with what shipped | specs | |

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
