# hAIsir — Decisions Log

> Running log of decisions made during `plan-next-state` cycles. Newest entry first. Append only — do not edit past entries.

---

## 2026-06-24 — hAITU topic-doubt converted to SSE streaming; two deferred items logged

> Phase 3 manual walkthrough (T10.4.1) surfaced that the single-shot JSON `POST /api/haitu/topic-doubt` caused gateway 504s on long RAG pipelines. Resolved by streaming; two design gaps deferred.

- **`POST /api/haitu/topic-doubt` now streams SSE (contract change).** The prior single JSON response after a multi-minute 4-stage pipeline tripped frontend/gateway idle timeouts (504) and could leak a DB connection on abort. Endpoint now returns `text/event-stream` with incremental `{"token":…}` frames, a `{"escalation_ready":…}` frame, a final `{"done":true}` frame, 15 s `: ping` keepalives, `request.is_disconnected()` cancellation, and a DB session closed before the streaming phase. 403/429 remain ordinary HTTP errors returned before the stream starts. Backend commits `2cdedcd` / `6ec91ab` (+ refactors `7da64d6`, `a9f7c30`, `93b9de7`, `aac0c7a`); frontend commits `2cd4305` / `47e4ec2` (+ SonarQube `d4076d3`). Non-streaming `HaituService.answer()` retained for callers/tests. Spec updated in `vision/requirements/08_haitu_ai_layer.md` (§4, §3.1, BR-AI-002, BR-AI-009). **Trade-off:** streaming bypasses `CompactAndRefine` (it calls `complete()`, not `stream_complete()`) — a single prompt mirroring the QA template is used; `escalation_ready` is still computed from the accumulated response.
- **Deferred — Stage 3 reranker is passthrough.** With `HAITU__RERANK_MODEL=""` (no cross-encoder configured), Stage 3 is a no-op. Acceptable for Phase 3; revisit when a rerank model is selected. Spec §3.1 already documents the empty-rerank skip.
- **Deferred — admin feature uses `@tanstack/react-query`.** Deviates from CLAUDE.md "custom hooks with useState/useEffect only." Pre-existing Phase 1 admin work, outside the Phase 3 student scope (the student feature uses raw `fetch` via `fetchWithCSRFRetry`, satisfying the Phase 3 pass criterion). Cleanup item for a later cycle.

---

## 2026-06-18 — Deferred: monitoring stack (Prometheus + Grafana) and WAF body exclusions

> Work done during `feature/rag` for hAITU RAG pipeline deploy tasks. Two areas explicitly deferred — needs follow-up before Phase 4.

**Monitoring stack (Prometheus + Grafana):**
- Full service definitions were designed and validated (Prometheus with `--storage.tsdb.retention.time=30d --storage.tsdb.retention.size=8GB`, Grafana OSS hardened with `read_only`, `cap_drop: ALL`, no anonymous access). Alert rules written for `HAITUPipelineLatencyHigh` (P95 > 60s) and `HAITUHighErrorRate` (5xx > 10%) using APISIX `apisix_http_latency_bucket` / `apisix_http_requests_total` metrics with `prefer_name: true`.
- **Blocker**: `cgr.dev/chainguard/prometheus` and `cgr.dev/chainguard/grafana` are not in the free Chainguard public tier (unlike `cgr.dev/chainguard/postgres:latest` already in use). `grafana/grafana-oss` is AGPL v3 — free for self-hosting. Options when revisiting: (1) subscribe to Chainguard paid tier, (2) digest-pin official images and re-pin on each update cycle, (3) collapse to VictoriaMetrics (Apache 2.0) with built-in vmui and check Chainguard free tier availability.
- **Not committed** — `env-setup.sh` guards requiring `PROMETHEUS_IMAGE_TAG`/`GRAFANA_IMAGE_TAG`/`GRAFANA_ADMIN_*` in `.env` would break existing staging/prod deploys if those vars are absent. Add to `.env` files first, then re-apply the stack.

**WAF body exclusions for `/api/haitu/*`:**
- Run the endpoint under load first to collect which CRS rule IDs actually fire on academic/LLM input.
- Pattern is established in `common/plugin_configs/03-secured-api.json` at rule `199100` (see `/api/topics-contents/` exclusion). Add a new chain at `id:199200,phase:1` using `ctl:ruleRemoveTargetById=<rule_id>;REQUEST_BODY` for each firing rule (likely candidates: 942100, 942200, 942260, 942440 for SQLi; 941100, 941110 for XSS; 932100, 932150, 932160, 932220 for RCE).
- Include JUSTIFICATION comment per existing convention before committing any exclusion.

---

## 2026-06-18 — Phase 3 closeout plan: verify, manually test, then sign off (G10)

> `/plan` cycle reconciling the existing Phase 3 PLAN.md (G1–G9) against current HEADs (backend `9379bb7`, frontend `54e198c`, deploy `e57c56b`). All G1–G9 implementation + the frontend Playwright E2E suite are done; the only unchecked items are 12 backend goal-level integration/E2E tests. User intent: **finish everything in Phase 3, test it all manually, then sign off — no deferral, no premature archiving.** New goal **G10** appended to PLAN.md (G1–G9 preserved as the implementation record).

- **Scope = all 12 verification items + a manual walkthrough as the sign-off gate (no deferral).** Ranked options included deferring the 4 Ollama-gated items to a later cycle. Rejected: the user explicitly wants Phase 3 fully closed before any Phase 4 / Phase 2-revisit work. Ollama-gated items run when Ollama is up and **skip-with-reported-count** when it is down — they are never silently dropped.
- **Two-tier test strategy to defeat the false-completeness gate.** The 8 DB-only tests (G10.2) are the deterministic CI gate — they always run against Postgres@V34, no skips. The 4 Ollama-gated tests (G10.3) are a separately-gated sub-signal: a `pytest_terminal_summary` hook prints `Ollama-gated: N skipped, M passed`, and an aggregate-gate task (T10.3.5) asserts that line is present, so a green all-skipped run is visibly distinct from a genuinely-green run. Without this, Ollama's `skipif` could make a green build mean "everything was skipped."
- **Manual walkthrough (G10.4) gated on automated green-with-enforced-counts, not just "green-or-skip."** T10.4.1's entry condition references the G10.2/G10.3 *subgoal* tests (8 passed 0 skipped; Ollama bucket ≥1 passed-or-4-skipped+2-passed with the skip-count line), so the stack is known-good at the automated layer before a human walks the 7-step ROOT Acceptance Test against the running stack. Defects found route to per-repo fix tasks (T10.4.2/3/4); sign-off (G10.5) cannot happen until those resolve.
- **Test isolation wired into a shared fixtures module (T10.1.2), not per-file.** `tests/integration/shared_fixtures.py` centralises the dependency-override wiring (`make_student_client` overrides `get_async_session`/`current_active_user`/`validate_csrf` + sends `X-Current-Role`) currently duplicated in `test_student_dashboard_integration.py`; the existing test is refactored to import it (T10.1.2b). `reset_haitu_rate_limiter` is **autouse** within `tests/integration/` (the limiter is a process-global singleton — without reset, the 21st-call 429 test and other suites share state). `unique_student_sub()` per test + `rolled_back_session()` prevent the V34 UNIQUE constraint from producing false 409s across tests. `integration_db_head` autouse asserts the integration DB is at `V34` before any DB-only test runs.
- **Plan-baseline updated** backend `0dbec56` → `9379bb7`, frontend `31062ab` → `54e198c` (deploy unchanged `e57c56b`).

---

## 2026-06-17 — Phase 3 plan review: fixes applied

> Post-`/plan` review of PLAN.md against the actual `feature/rag` state of all three repos. Findings and fixes:

- **`HaituDoubtService` missing a topic repository (bug).** T5.3/T5.4 fetch the topic's `course_path_node_id` (subtree check + ancestry for `topic_context`) but never injected a topic repo. Added `topic_repo: AbstractTopicRepository` to the constructor and the route factory; `topic_repo.get(topic_id)` already exists (the dashboard service uses it).
- **Shared LlamaIndex helpers extracted (code reuse + DDD).** `_parse_db_url`, `_build_embed_model`, `_LmStudioEmbedding` move from `worker/rag_outbox_loop.py` into `src/infrastructure/embedding.py` as public `parse_db_url` / `build_embed_model` / `LmStudioEmbedding`; `build_embed_model` refactored to take `EmbeddingSettings` (not full `Settings`). New task **T4.0** gates G4. Rationale: `HaituService` (domain layer) must not import from the `worker/` entrypoint, and Stage-2 dense retrieval needs the bge-m3 / LM-Studio embed model wired explicitly into `VectorStoreIndex` — LlamaIndex's global default resolves to an OpenAI model and fails in dev.
- **Deploy route templating (no change to T6.1's intent).** `common/routes/.templated/{dev,staging}/` is gitignored and generated at deploy time by `create_route_config.sh` (falls back to `common/routes/` when no env template exists). T6.1 reworded to author only `common/routes/19-api-haitu.json` (modeled on `17-api-actions.json`); do not hand-create `.templated/` copies.
- **T6.2 confirmed necessary.** The `backend` service in `common/docker-compose.yml` uses an explicit `environment:` mapping (no `env_file`) and lists no `HAITU__`/`EMBEDDING__` vars. Dev verification (vars in the backend repo `.env`, loaded by Pydantic) proves the code reads them, but staging/prod still need the explicit compose entries — T6.2 stays.
- **`recommended` depends on `student_profiles.grade`, which onboarding never collects.** Documented in T2.8: grade is `None` for most students, so recommendations are absent until set via the profile endpoint; `get_catalog` degrades gracefully.
- **Plan-baseline updated** backend `2686279` → `0dbec56` (current HEAD; one continuation fix).

---

## 2026-06-17 — Phase 3: Student Enrollment + hAITU topic-doubt

- **Enrollment is a prerequisite for hAITU.** Students must enroll before seeing any platform content. The dashboard and S-nav now filter to enrolled subtrees; unenrolled students see an empty state with a Browse Courses CTA. No enrollments = no platform content visible.
- **Student self-enrollment only (Phase 3).** Students browse the catalog and self-enroll. Grade-based recommendations (string match on `student_profiles.grade`) are shown as badges — no ML. Platform-admin and parent-initiated enrollment deferred.
- **Enrollment scoped at any node level.** Enrolling at grade level grants access to all descendant subjects, courses, and topics. The server enforces via recursive CTE subtree query.
- **hAITU chat is fully stateless in Phase 3.** No chat history is written to the database. The client holds the rolling 5-turn window in memory and sends it with each request. Teacher escalation and the `doubts` + `doubt_messages` tables are deferred to Phase 4 (requires teacher role in Keycloak).
- **V35 (doubts + doubt_messages) deferred to Phase 4.** Schema design is documented but not migrated. `POST /api/haitu/topic-doubt` returns `{response, escalation_ready}` only — no `doubt_id`.
- **Rate limiting is in-memory per worker (no Redis).** 20 calls/student/hour using a module-level `HaituRateLimiter` with `threading.Lock`. Acceptable for Phase 3; revisit if multi-worker scaling requires cross-process coordination.
- **Business logic in HaituDoubtService, not in the route.** The route handler maps exceptions to HTTP codes only. All validation (enrollment ownership, subtree check, rate limit) lives in the domain service, per project DDD rules.
- **Mastery score always "N/A" in Phase 3.** The system prompt template includes the mastery_score slot (for future use) but the value is always "N/A" until mastery tracking is implemented.
- **bge-m3 (BAAI/bge-m3, 1024-dim) is the fixed embedding model.** Changing the model requires full re-indexing of `data_topic_content_chunks`. Do not change without planning a reindex cycle.

---

## 2026-06-12 — PDF text restructuring pass (adapted from anhad-final-exam)

> Affects: `haisir-backend` — `GlmOcrProvider`, `ExtractionSettings`, `extraction_loop.py`, new `prompts/restructure_prompt.md`.

### Problem
Native PDF text extraction (pypdfium2) often produces garbled output for real educational content: fractions split across lines (numerator on one line, denominator on the next), words broken at layout boundaries, structural ordering lost. The current extraction pipeline returns this raw text as-is when `len(text) >= 50 and image_coverage < 0.95`, making the content hard to read and poor for embedding quality.

### Decision
Add an optional **text restructuring pass** (`restructure_page()`) triggered after native text extraction. Uses a text-only LLM call — no image — to fix fragmentation and output clean Markdown. Falls back to raw text if LLM returns empty. Adapted from `~/Workspace/anhad-final-exam/src/pdf_to_markdown/ocr.py`.

- `EXTRACTION__RESTRUCTURE_TEXT=true` (default) — enables the pass
- `EXTRACTION__RESTRUCTURE_MODEL_SPEC` — separate, lighter text model (e.g. `qwen3.5:9b`); defaults to same as vision model spec when unset
- `GlmOcrProvider.restructure_page(raw_text: str) -> str` — new text-only method using all existing backend dispatch (Ollama / lmstudio / openai / anthropic)
- Prompt stored in `haisir-backend/prompts/restructure_prompt.md`
- No schema change; no new table; pure behaviour enhancement in the worker

---

## 2026-06-12 — RAG + hAITU infrastructure: architecture decisions

> Status: all decisions locked; implementation plan pending (`/plan` not yet run).
> Affects: `haisir-deploy` (new postgres image), `haisir-backend` (V31+V32 migrations, drain loop, hAITU endpoint, LlamaIndex dep), `haiguru` (2-line table rename).

### Problem
The `rag_indexing_outbox` table has been populated since Phase 1d-real but nothing drains it — no embeddings are generated, no vector table exists, and students cannot ask hAITU questions about topic content. pgvector is also absent from the Chainguard Postgres image.

### Decisions

- **pgvector in the same DB as the backend.** hAITU retrieval requires JOINing `data_topic_content_chunks` with `topic_contents` — impossible across two separate Postgres instances without FDW. The worker already writes everything to the main DB; splitting only vector tables would create split-brain with no atomicity.

- **Custom Postgres image: Wolfi multi-stage build.** `cgr.dev/chainguard/wolfi-base` as compiler stage, `cgr.dev/chainguard/postgres:latest` as final stage. pgvector 0.8.2 compiled from source. Replaces the backend `db` and `db-init` services only. Keycloak DB stays on unmodified Chainguard image. Dev compose uses `pgvector/pgvector:pg18` (simpler, no hardening needed locally). Location: `haisir-deploy/common/images/postgres-pgvector/Dockerfile`. Versions: PostgreSQL 18.4, pgvector 0.8.2.

- **LlamaIndex-managed table, renamed `topic_content_chunks`.** Keep LlamaIndex's `PGVectorStore` managing the table (as haiguru's `embed_pipeline` does today). Rename the `TABLE_NAME` constant in haiguru from `topic_content_vectors` → `topic_content_chunks` (2-line change: `embed_pipeline/__main__.py:22`, `rag/retriever.py:31`). Physical Postgres table = `data_topic_content_chunks` (LlamaIndex prepends `data_`). Schema: `id` BIGINT PK, `node_id` VARCHAR, `text` VARCHAR, `metadata_` JSONB (stores topic_id, content_id, topic_title, course hierarchy), `embedding vector(1024)`, `text_search_tsv` TSVECTOR. HNSW + GIN indexes. Hybrid dense+sparse search enabled. Backend hAITU queries use raw SQL with JSONB operator: `WHERE metadata_ ->> 'topic_id' = $1`.

- **AI assistant feature is named hAITU (not hAIsir).** hAIsir is the product name; using it for the AI sub-feature creates confusion. hAITU is distinct, scoped ("AI Tutor"), and memorable. All code, routes, env vars, and UX copy use `haitu`.

- **hAITU LLM uses same prefix-dispatch pattern as extraction/grading.** `lmstudio://host/model` for local dev, plain `model-name` via Ollama for production. New `HaituSettings` block in `shared/config.py` with `HAITU__MODEL_SPEC` + `HAITU__OLLAMA_BASE_URL`. `anthropic://` path available but not tested in current increment.

- **T7.4 drain loop: 4th coroutine in the existing worker.** `run_rag_outbox_loop` added to `worker/__main__.py`'s `asyncio.gather`. Implemented as standalone `worker/rag_outbox_loop.py` (extractable to a separate service later via compose-only change — zero code rewrite). Same `FOR UPDATE SKIP LOCKED` polling pattern. Rate-limited via `EMBEDDING__BATCH_SIZE` config. Long-term risks (non-blocking): resource contention with extraction at bulk scale; mitigated by batch size config. Crash isolation: each loop requires its own try/except (existing worker pattern).

- **Embedding model: BAAI/bge-m3, `vector(1024)`.** Multilingual support required. bge-m3 scores ~66–67 on MTEB multilingual, 335M params, MIT license, Ollama-native, 8192-token context window. Qwen3-Embedding-8B scores higher (#1, 70.58) but requires ~16GB VRAM — deferred until hardware budget is confirmed. Dimension 1024 is fixed in the V32 migration and cannot change without dropping + rebuilding the HNSW index. New `EmbeddingSettings` block: `EMBEDDING__MODEL_SPEC`, `EMBEDDING__OLLAMA_BASE_URL`.

- **Drain loop writes via LlamaIndex in haisir-backend.** Add `llama-index-core`, `llama-index-vector-stores-postgres`, `llama-index-embeddings-ollama` to `haisir-backend/pyproject.toml`. Writing raw SQL into a LlamaIndex-managed table (with its `node_id`/`metadata_` conventions) would be fragile and couple to LlamaIndex internals.

- **Chunking: LlamaIndex SentenceSplitter, `chunk_size=512, chunk_overlap=100`.** Consistent with haiguru's existing pipeline; no new dependency. Parameters map to vision spec's ~600-char intent in token terms, well within bge-m3's 8192-token window. Can be tuned later — chunk params are internal to the drain loop and don't affect any DB schema or external API.

---

## 2026-06-08 — AI Essay Grading Engine: architecture decisions

> Spec: `target/requirements/08_essay_ai_grading.md`. Schema deltas: `target/requirements/01_data_model.md` § "Schema Extensions (Essay AI Grading)". Auth: `02_auth_and_roles.md`. Persona updates: `03_student.md`, `04_teacher_tutor.md`, `05_parent.md`. Implementation tasks: PLAN.md G7–G12.

### Problem
`essay` questions return `(None, 0.0)` from `grade_question()` — no evaluation path exists (neither automatic nor manual). The platform already runs an LLM for content extraction (`glm-ocr` / Ollama cloud); that pattern maps cleanly onto essay grading with no new infra.

### Decisions

- **Per-exam grading mode, not global flag.** `exam_templates.essay_grading_mode` defaults to `auto_release` (AI score released to student immediately; student can dispute, owner can override). `review_first` is opt-in for high-stakes exams (score held until owner confirms). A global flag would block results for all exams even when only one is sensitive.
- **Rubric optional + smart default.** Creator may attach an analytic JSONB rubric (3–6 criteria, weighted, with per-level descriptors) and optional `model_answer`. If absent, the worker selects a built-in default rubric by `essay_subtype`. Requiring a rubric would block quick exam creation; a pure default would be too generic.
- **Backend computes score, LLM outputs levels only.** The LLM returns per-criterion `level` integers; the backend computes `ai_score = Σ(level/scale_max × weight) × points`. This eliminates hallucinated arithmetic, length/fluency bias, and number-range drift.
- **Temperature 0, structured JSON output.** Temperature 0 for grading consistency. Output is validated JSON matching a fixed schema; on parse failure or out-of-range levels → retry up to 3 times; on exhaustion → `error` status, not silent zero.
- **Local-first model path.** Default `GRADING__MODEL_SPEC=qwen3:14b` (on-prem, PII stays local). Ollama-cloud (`gpt-oss:120b-cloud`) and `anthropic://claude-sonnet-4-6` are opt-in config swaps. Mirrors OCR's `glm-ocr` local / `gemma` cloud pattern.
- **Async worker, not inline grading.** Submit returns immediately; a new `essay_grading_jobs` table is polled by a new `essay_grading_loop` alongside the existing extraction loop. Same `FOR UPDATE SKIP LOCKED` pattern, same worker process.
- **Rubric lives on `questions`, not per-session-question.** One essay question can be reused in multiple exams; the rubric should not be duplicated per attempt. No per-instance rubric override in v1.
- **Grading owner = exam owner.** Parent for parent-owned exams (`owner_id = self`); Admin for platform exams (`owner_type='platform'`). Instructor/tutor grading is deferred until the role migration (`vision/requirements/11_role_migration.md`) is complete.
- **`auto_grade_essay = false` escape hatch.** Lets a creator opt out of AI grading per question (e.g. subjective creative writing where AI scoring is inappropriate).

### Challenger resolutions
- Admin cannot override parent-owned essay grades — BR-SEC-005 + BR-SEC-012 enforce this explicitly.
- `error` state never writes `earned_points = 0` — silently zeroing a failed-grading essay would be misleading. Owner must manually override.
- `ai_rationale` (per-criterion breakdown) is owner-only — not returned to student to prevent coaching before disputes.

### Out of scope / follow-up
- **Phase 2:** Teacher/parent review dashboard, per-criterion feedback display in S-results, regrade UI controls.
- **Phase 3:** Self-consistency (median of N), confidence-based auto-flagging, prompt-injection test suite, AI-written essay detection.

---

## 2026-06-05 — Question type extension: architecture decisions

> Spec: `target/2026-06-05_question_types_extension.md`. Plan archived from previous phase (1d-real) before starting fresh. Tasks: PLAN.md G1–G6.

- **No backend shuffle for matching.** Backend generates a random uint31 `shuffle_seed` via `random.randint(0, 2**31-1)` at session-creation time and stores it on `exam_session_questions`. The frontend applies a seeded LCG Fisher-Yates shuffle to right-column items. This keeps shuffle deterministic (page-refresh safe) without requiring server-side ordering logic.
- **LCG cross-stack contract.** Algorithm: `next_state = (state * 1664525 + 1013904223) & 0xFFFFFFFF` (Python) / `(Math.imul(state, 1664525) + 1013904223) >>> 0` (TypeScript). Fisher-Yates: `i` from `len-1` down to `1`, `j = next() % (i+1)`. Both sides must use this exact formula — no Python `random.shuffle` or JS `Math.random`.
- **working_text at submit time.** No per-question answer endpoint exists; `working_text` is captured as part of the bulk `POST /session/{id}/submit` payload via an optional `working_text` field on `AnswerCreate`. Only stored for `problem_solving` questions; ignored for all other types.
- **Canonical matching correct_answers format.** `correct_answers` for matching = list of `"Lx:Ry"` strings (left option ID : right option ID). This format is the contract between authoring validation, grading, and frontend answer serialization.
- **essay_subtype is a rendering hint only.** No enum, no validation rule. `essay_subtype VARCHAR(10) NULL` on `questions`. Values `'short'`/`'long'`/`null`. Grading and storage unchanged.
- **Alembic V27 non-transactional migration.** `ALTER TYPE ... ADD VALUE` must use `op.get_bind().execution_options(isolation_level="AUTOCOMMIT")` — cannot run inside a transaction. The four `ADD COLUMN` statements run inside normal transaction. V27 migration must be applied before deploying application code referencing new `QuestionType` values.
- **problem_solving working_text unscored this phase.** Captured and stored, visible to parent who owns the exam, but carries no `earned_points`. Instructor scoring deferred to when instructor scope is added.
- **Open points deferred.** P-exam question creator UI for new types, S-results rendering for matching/problem_solving, and instructor working_text scoring are all explicitly deferred (see PLAN.md "Open Points").

---

## 2026-06-02 — Backend OAuth2 token introspection (RFC 7662)

> Spec: `target/requirements/02_auth_and_roles.md` § "Token Introspection (backend, RFC 7662)" + BR-SEC-009/010; invariant added to `target/requirements/00_overview.md`. Task breakdown: TASKS.md G14. Cross-cutting security hardening (not tied to a persona phase). Specs updated this cycle; backend + deploy implementation queued.

**Problem.** The backend validates JWTs locally only (`PyJWKClient` JWKS + `jwt.decode` for signature/exp/iat/issuer in `auth/user.py`). Stateless validation cannot detect a revoked token (logout, admin-disabled account, password reset) within the 300s access-token lifespan, and if the backend is ever reached bypassing APISIX it trusts a token the gateway would reject. The Keycloak side was unblocked manually in staging via `haisir-deploy/common/scripts/add-token-introspection-scope.sh` — a temp workaround that is now being made declarative.

### Decisions

- **Hybrid model, not replace (challenged).** Keep local JWKS decode as the fast first gate, then call RFC 7662 introspection when enabled. Replacing local validation entirely was rejected — it removes the fast-fail path and couples *all* auth liveness to a Keycloak round-trip. The "is this over-engineering given APISIX already validates + 300s tokens?" challenge was considered: the value is revocation enforcement + defense-in-depth at the resource server, made cheap by caching + fail-closed.
- **Short-lived per-token cache.** Keyed by `sha256(token)` (raw tokens never stored/logged — BR-SEC-007), TTL `min(configured_ttl, token_remaining_exp)`, default ~30s. Bounds Keycloak load; revocation detected within the TTL window.
- **Fail closed.** Keycloak introspection unreachable → `503`; `active:false` → `401`. A token is never accepted on local validation alone while introspection is enabled (BR-SEC-010).
- **Introspecting identity = existing `haisir-backend-admin` service-account client.** Its credentials are already in backend config (`OAUTH__KEYCLOAK__ADMIN_CLIENT_ID/SECRET`) and wired through deploy — zero new secret distribution, and the web/gateway client secret is never shared with the backend. Architecturally correct: the resource server introspects with its own machine identity.
- **Declarative deploy replaces the temp script.** Keycloak 26 requires the `token-introspection` client scope (as a *default* scope on the introspecting client) AND the introspecting client present in the introspected token's `aud`. Provisioned in `setup-keycloak.sh` (new client-scope config + audience mapper on the web client). `add-token-introspection-scope.sh` is retained only as a manual recovery tool.
- **Feature-flagged, staging-first.** `introspection_enabled` defaults `false`; enable in staging before prod.

### Out of scope / follow-up

- **Tighten `verify_aud`** (currently `False`): once the audience mapper reliably puts `haisir-backend-admin` in token `aud`, a follow-up can flip local validation to enforce audience. Kept separate to avoid coupling an auth-breaking change to this feature.
- Frontend: no changes (APISIX/session-cookie flow unchanged).

---

## 2026-04-23 — Phase 1d-real: Content Extraction architecture + post-challenger hardening

> Spec: `target/requirements/12_content_extraction.md`. Schema deltas: `target/requirements/01_data_model.md` § "Schema Extensions (Phase 1d-real)". Prototype: `target/prototypes/haisir_admin_flow.html` (Playwright-validated).

**Phase 1d (the URL-only stub) was retroactively renamed `1d-stub`.** It shipped a non-functional Add Content modal — PDF chip existed but no upload pipeline. Phase 1d-real is the actual functional extraction work.

### Five base architecture decisions

- **PDF library: `pypdfium2`** (Apache/BSD). PyMuPDF is BANNED (AGPL §13 SaaS clause). Same library used for both native-text extraction (fast path, no LLM) and rasterization (slow path, feeds the vision LLM).
- **Vision LLM: `glm-ocr`** copied from `../haiguru/glm_ocr/`. Prefix-dispatch on model spec (`lmstudio://`, plain Ollama, `openai://`, `anthropic://`). Streaming tuple protocol (`__first_token__`/`chunk`/`__done__`). Default model spec via env `EXTRACTION_MODEL_SPEC`; per-upload model selection deferred.
- **Persistence model: ONE upload → N `topic_contents` rows with `content_type='text'`.** Source PDF/image is transient (purged per status TTL). No new `content_type` enum value. Confirmed against haiguru `etl_pipeline/load.py:_load_contents` proof-of-concept.
- **Queue: Postgres `FOR UPDATE SKIP LOCKED`.** No Redis, no ARQ, no Celery — 5–10 admins / ~50–200 PDFs/week shows no scale signal yet. Migration trigger to SSE/Redis documented as ">100 concurrent active jobs platform-wide".
- **Worker = same backend repo, second process mode.** Compose `replicas: 2` from day one (SKIP LOCKED needs N≥2 to be meaningful). Docker image is shared with the API.

### Nine critical challenger fixes (integrated into spec before any code)

- **CSRF on multipart MUST be verified first.** `fetchWithCSRFRetry` with FormData is a known footgun (Body is consumed on first send). Integration test required as a blocking gate before worker code (BR-EXT-018).
- **Resume-after-crash via `extraction_job_pages` staging table.** Worker death no longer wastes LLM tokens — reclaimer resumes from `MAX(page_no)+1` (BR-EXT-008).
- **RAG embedding via outbox (`rag_indexing_outbox`).** Embedding failure can never roll back content. Content is visible immediately; searchable when outbox drains (BR-EXT-012).
- **Provenance is permanent.** `topic_contents.source_extraction_job_id` (additive nullable column) + indefinite `extraction_job_audit` table. Survives source purge, survives content delete, survives content edit (BR-DATA-010, BR-EXT-022).
- **`MAX(content_order) FOR UPDATE` inside finalize TX.** Prevents collisions with manual content rows added during extraction (BR-DATA-012).
- **Owner_type re-validated by worker in finalize TX.** Defence in depth — API gate is not the only check. Mismatch → `extraction_failed` with `error='ownership_violation'` (BR-DATA-011, BR-EXT-010).
- **`Idempotency-Key` UUID header REQUIRED on POST.** Replay returns the original 201. Unique index on `(created_by, idempotency_key)` (BR-EXT-005).
- **No `'uploading'` enum value.** HTTP transfer is client-side; the row is INSERTed only after the multipart handler succeeds. Frontend renders an in-memory pseudo-job for upload progress; replaced by the real `pending` row on 201, marked `upload_failed` on error (BR-EXT-019).
- **Varied final-state TTLs.** `done`=7d, `extraction_failed`=30d (admin retry window), `cancelled`=24h, `upload_failed`=7d. Single uniform 7d would have killed the retry path.

### Two post-design refinements (today)

- **No upload-time title for PDF/image.** One upload becomes N rows, so a single user-typed title cannot map. Per-page titles auto-derived from first H1 (fallback `"Page N — {filename}"`); editable post-hoc via inline rename or Edit modal. Video and Text uploads (1 upload → 1 row) DO accept a title at creation (BR-EXT-023b).
- **Two edit affordances on every content row.** Click-on-title for inline rename (cheap path, frequent); Edit button for full title+body modal (heavy path, OCR-error fixes). `PATCH` MUST NOT clear `source_extraction_job_id` — provenance badge persists even after admin rewrites the body (BR-EXT-023a).

### Out of scope (v1)

`exercises` job type (column wired, UI not exposed — ships in 1d-real-2), per-upload model selection UI, HEIC/HEIF, ClamAV, SSE/WebSocket progress, bulk re-extract by model upgrade.

---

## 2026-04-09 — Phase 1c-post: Admin UX Alignment (completion + deviations)

- **Phase 1c-post is complete.** All six UX gaps listed in the plan are closed. Commits: haisir-backend `819893c`, haisir-frontend `dec3ab8`. Archived plan at `archive/phase1c-post-plan.md`. Next phase is 1d (topic content upload).
- **"Custom node type" option rejected permanently.** The original audit listed a "custom / free-flow fallback" chip as a potential scope item. Decision: the 9-value fixed enum (`grade`, `subject`, `course`, `chapter`, `module`, `section`, `unit`, `week`, `skill`) is the complete and final set. No free-text escape hatch will be added. This removes ambiguity for admins and avoids DB enum proliferation.
- **3-tier hierarchy instead of simple sibling filtering.** Plan specified disabling reserved types already used by siblings. Implementation went further: root-level nodes must be `grade`; immediate children of `grade` must be `subject`; deeper nodes may be any type not already in the ancestor chain. This maps to the standard curriculum hierarchy and is enforced both in `isTypeDisabled` (frontend) and in `create()` service validation (backend 409).
- **`POST /api/course-path-nodes` returns 409 on hierarchy violations.** Two server-side checks added: (A) ancestor-type exclusion — the new node's type must not appear anywhere in the ancestor path; (B) sibling-type consistency — all platform-owned children of the same parent must share a single type. Both checks run before INSERT. TOCTOU window acknowledged but acceptable (admin-only, concurrent admin sessions not a realistic concern).
- **`POST /api/topics` now requires `status`.** `TopicCreate` schema changed from having no `status` field to requiring `"draft" | "live"`. Frontend sends `"draft"` on all `AddTopicModal` submissions. This makes intent explicit and prevents ambiguous defaults at the API boundary.
- **NodeDetailPanel is type-conditional.** Reserved-type nodes (`grade`, `subject`) cannot hold topics directly — they are structural containers. NodeDetailPanel now renders `ChildNodesPanel` for reserved types and `TopicPanel` for all others. This makes the UI structurally correct without needing backend enforcement.
- **`admin-node-domain.ts` extracted as pure domain module.** Tree manipulation logic (`buildNestedTree`, `isTypeDisabled`, `buildBreadcrumb`, etc.) extracted from components into a pure functions file with no React/Next imports. Enables unit testing without React harness.
- **Native `<dialog>` throughout.** All four admin modals (AddBoardModal, AddNodeModal, AddTopicModal, DeleteNodeDialog, DeleteTopicDialog) converted from `<div role="dialog" aria-modal="true">` to native `<dialog open>`. Fixes SonarQube accessibility issues and improves focus management semantics.
- **Issue 2 (sidenav Categories) tracked as future scope.** Moving "Categories" from the avatar/profile menu to the `AdminSidenav` is new scope not covered by any existing phase. Recorded in PLAN.md backlog. Medium priority; frontend-only change, no backend work needed.
- **Issue 3 + 6b (version display) remain deferred to Phase 2+.** No `version` column exists on `categories`. Requires Alembic migration + publish workflow + UI modal. Low priority. Recorded in PLAN.md backlog.

---

## 2026-04-06 — Phase 1c-post: Admin UX Alignment

- **Six UX gaps identified between prototype and built screens.** After hands-on testing of Phase 1c, six issues found: (1) Add Board modal sends incomplete payload (`name` only; backend requires `path_type` → 422), (2) category description editing buried on legacy `/manage-categories` page, (3) board version display deferred (no schema), (4) Add Node modal uses free-text for node type instead of chip selector, (5) no sibling-type filtering on reserved types, (6) dashboard shows bare board list instead of prototype's rich cards with stats.
- **No custom node types — fixed enum of 9 values.** Node types are: `grade`, `subject`, `course`, `chapter`, `module`, `section`, `unit`, `week`, `skill`. Kept as PG enum with Alembic migration adding 6 new values to the existing 3. No VARCHAR change. No frontend "Custom" escape hatch.
- **Reserved types remain `grade` and `subject` only.** These show 🔒 in the chip selector and are disabled if already used at the same tree level. All other types can repeat.
- **Board stats: new admin-only endpoint.** `GET /api/admin/board-stats` returns per-board `live_topics`, `draft_topics`, `total_topics` + platform-wide overview. Single JOIN query; comment added noting materialized view as future optimisation path if needed.
- **Board version/publish DEFERRED.** No `version` column in schema. Prototype shows version numbers and a publish modal, but this requires a schema migration + full publish workflow. Tracked for Phase 2+.
- **`path_type` hardcoded to "structured".** Add Board modal does not expose `path_type` to the user; it is always `"structured"`. The field exists for future "flexible" paths but is not yet needed.
- **`/manage-categories` effectively deprecated.** Not removed, but not linked from admin sidenav. Its "edit description" capability moves to inline editing on the dashboard board cards.

---

## 2026-04-06 — Phase 1c: Admin Topics Management

- **`status` missing from `TopicRead` identified as a blocking gap.** The `topics.status` column and `Topic.status` domain field existed since Phase 1a but were never added to `TopicRead` (Pydantic schema). The admin PATCH endpoint cannot function without exposing this field. Added `status: str = "live"` to `TopicRead` as step A1.
- **BR-STU-003 gap: students can currently see draft topics.** `get_by_course_path_node_visible` in `TopicRepository` applies the owner-type visibility clause but not the `status = 'live'` filter required by BR-STU-003. Gap became observable in Phase 1c because status toggling makes draft topics possible. Fixed in step A6.
- **Node-delete live-topic guard was missing.** The spec (`target/requirements/ui-mapping/ui_parent_institution_admin.md`) says node delete is blocked when the subtree contains live topics, but `DELETE /api/course-path-nodes/{id}` only checked for active exam sessions. Fixed in A7 — live-topic check runs before the existing session check.
- **Topic delete cascades `topic_contents` only.** Topics do not FK-reference `exam_templates` or `exam_sessions` directly (those link to `course_path_node_id`). The cascade for topic delete is: `topic_contents` rows → `topics` row. Simpler than the node subtree cascade.
- **Phase B (frontend) runs in parallel with Phase A.** B1–B3 (types, API functions, hook) have no backend runtime dependency — they can be written and unit-tested with mocks before backend endpoints are deployed. B4–B9 build on B1–B3.
- **`status` field stays as `str` in domain model; validation lives at schema boundary.** Existing `Topic` dataclass uses `status: str = "live"`. `TopicUpdate` uses `Literal["draft", "live"]` for Pydantic validation. Avoids a breaking domain-layer change while still enforcing valid values at the API boundary.
- **"Upload Content" stub deferred to Phase 1d.** `TopicRow` will render a disabled "Upload Content" button pointing to Phase 1d. Topic content upload is out of scope for Phase 1c.

---

## 2026-04-02 — Phase 1c-pre: X-Current-Role Enforcement (backend + frontend)

- **Scope expanded from backend-only to both repos.** Originally planned as a backend-only audit. After scanning the frontend, `buildApiHeaders()` already sends `X-Current-Role` on all calls via `localStorage`. Both repos change together in the same dev cycle to avoid the deployment sequencing risk (backend strict before frontend sends header = instant breakage).
- **`current_active_user` split into strict + lenient.** The single `current_active_user` function in `src/auth/user.py` is split: `current_active_user` (strict — `400` when header absent) and `current_active_user_lenient` (old behaviour — defaults to `roles[0]`). Lenient is used only for the three exempt onboarding endpoints. All `require_*()` helpers automatically inherit strict enforcement via the dependency chain — no per-route changes needed.
- **Three endpoints remain exempt.** `GET /api/users/me`, `POST /api/users/me/assign-role`, and `PATCH /api/users/me/onboarding-complete` use `current_active_user_lenient`. Rationale: users may not have a role yet (or their JWT may not reflect the newly assigned role) at the point these endpoints are called during onboarding.
- **`PATCH /me/onboarding-complete` gets inline role check instead of `require_student_or_parent()`.** It needs the lenient dep for the header but still enforces the student/parent role restriction. Inline check preserves the security guarantee without the strict dep.
- **No route tests change except `test_user.py`.** All other route tests override `current_active_user` via `dependency_overrides` and inherit the strict dep change automatically. Only `tests/unit/auth/test_user.py` and `tests/unit/routes/test_user.py` need updating.
- **Frontend functional changes are none.** `buildApiHeaders()` already sends the header correctly. `fetchWithCSRFRetry` correctly does not retry `400 "X-Current-Role header required"` (detail doesn't contain "csrf"). Only a code comment + `position`→`order` field-name fix in admin-api.ts.
- **`CreateNodeInput.position` → `order` fixed.** Phase 1b shipped `CreateNodeInput.position?: number` on the frontend but the backend field is `order`. Backend was silently ignoring `position`. Fixed as part of 1c-pre cleanup.
- **BR-SEC-006 updated from "defaults" to "400".** The rule now reads: `X-Current-Role` is required on all role-gated endpoints; missing header returns `400 "X-Current-Role header required"`. Three onboarding endpoints are the explicit exception.

---

## 2026-04-01 — Phase 1b-fix: Admin Layout Alignment + Routing

- **Admin shell layout deviates from the HTML prototype — fix before Phase 1c.** Phase 1b shipped the tree UI + node CRUD but with a horizontal board selector (prototype shows vertical icon strip, 60px) and no left sidenav (prototype shows 190px dark sidebar with Dashboard + Board content nav items). Fixing the layout after Phase 1c would require refactoring the shell around already-built topic components. Fix first, build topics on correct layout.
- **Role-aware redirect from `/` added.** Root page currently sends all authenticated users to `/home`. Admin users must type `/admin` manually. Added a role→route map: `admin` → `/admin`, `parent` → `/parent`, `student`/default → `/home`. Uses `useAuth.currentRole` which falls back to `localStorage` optimistic role during JWT refresh window.
- **Admin route guard added to `admin/layout.tsx`.** Backend already rejects non-admin API calls (403). Client-side guard is defence in depth — prevents users from landing on admin UI at all. Uses existing `ROUTE_ROLE_REQUIREMENTS` config in `use-auth.ts`.
- **Resizable panels (sidenav + tree) added as UX fix.** Prototype uses fixed widths (190px sidenav, 240px tree), but tree node names truncate at fixed width ("Ma...", "Arit..."). Added drag-to-resize on both panels. No external library — `mousedown`/`mousemove`/`mouseup` pattern. Not in prototype but improves usability.
- **`parent` → `/parent` redirect is forward-compatible stub.** Will 404 until parent UI is built. Acceptable — no real users have `parent` Keycloak role yet (role migration not executed).
- **Visual authority rule formalised.** Added note to `ui_parent_institution_admin.md`: HTML prototypes are the authoritative visual reference. If prototype and text spec conflict, the prototype wins. This was the root cause of the horizontal-vs-vertical board strip mismatch.
- **`current_role` column in `user_metadata` rejected.** Proposed storing last-used role in DB to avoid sending `X-Current-Role` header on every request. Rejected because: (1) adds a DB lookup on every request, (2) multi-tab race condition (changing role in one tab affects all tabs), (3) breaks stateless request model. The header approach is correct; the problem was endpoints silently defaulting when header is missing.
- **`X-Current-Role` enforcement audit scheduled after Phase 1b-fix.** Backend audit to make `X-Current-Role` required on all role-gated endpoints (return `400` if missing). Onboarding endpoints remain exempt. Replaces the silent default from `BR-SEC-006` with an explicit failure, forcing the frontend to always send the header.

---

## 2026-03-31 — Phase 1 Board Content Management: split into micro-phases

- **BR-DATA-003 enforcement is a separate micro-phase (1a) before the admin UI (1b).** The `owner_type`/`owner_id` columns are live but no endpoint applies the visibility filter. Building the admin UI on an unfiltered backend would ship a known data isolation gap. Phase 1a closes it first (backend-only, ~1 day).
- **Phase 1b scope locked to tree UI + node CRUD only.** Topics panel (right side of prototype) and topic content upload are separate follow-on phases (1c, 1d) to keep each deployable unit small.
- **Hard delete for course_path_nodes in Phase 1b (soft-delete deferred).** Nodes with active exam sessions cannot be deleted (rejected at API layer). Soft-delete via `archived_at` column deferred — parent adoption introduces orphan risk that requires a migration strategy before soft-delete is safe.
- **Full-subtree CTE fetch endpoint added in Phase 1b.** `GET /api/course-path-nodes/tree/{category_id}` returns the entire tree for a category in one query to avoid N+1 on the admin tree render.
- **Admin read filter: `owner_type = 'platform'` only.** BR-SEC-005 states admin cannot read parent-owned content. This filter is applied on all admin GET endpoints for nodes/topics/exams as part of Phase 1a enforcement.

---

## 2026-03-27 — Target state reset: Student + Parent + Platform Admin increment

- **Target state scoped to three personas only:** Student, Parent, Platform Admin. Institutions, instructors, tutors, classes, doubts, hAITU, and notifications explicitly deferred to a future increment.
- **Parent as content creator:** Parents are modelled similarly to tutors (content publishers) but their content is private to one linked child only — no marketplace, no instructor oversight. Parents are solely responsible for quality of content and exams they create.
- **`owner_type` discriminator introduced:** New columns `owner_type` (VARCHAR, NOT NULL, DEFAULT `'platform'`) and `owner_id` (UUID, NULL) added to `course_path_nodes`, `topics`, and `exam_templates` via additive `ALTER TABLE`. `owner_type = 'platform'` for all existing rows (backfill migration provided). `owner_type = 'parent'` for parent-created content with `owner_id = parent.idp_sub`.
- **Content visibility rule:** Platform content visible to all authenticated students. Parent content (`owner_type = 'parent'`) visible only to students with an active (non-revoked) `parent_child_links` record where `parent_idp_sub = owner_id`. Applied as a WHERE clause on all student queries.
- **Adopt/clone flow:** When a parent adopts a platform board subtree, a deep copy of `course_path_nodes` rows + `topics` rows is created with `owner_type = 'parent'`. `topic_contents`, `topic_content_chunks`, `questions`, `exam_templates`, and `exam_template_questions` are NOT cloned — parent populates their own content after adoption. Platform updates to the original do not propagate to parent copies; each copy is independent.
- **Adopt is idempotent:** Second adopt of the same subtree root returns 409 Conflict — no duplicates created.
- **No instructor review gate for parent exams:** Parents create and publish exams directly. No approval flow.
- **Home Study section on student dashboard:** Two distinct sections — "Platform Board" (blue, `#185FA5`) and "Home Study" (green, `#1D9E75`). Home Study section is hidden entirely if no active parent link exists.
- **Token refresh after role assignment:** Explicit logout (`/auth/logout`) not `prompt=none`. Safari ITP and Firefox ETP block third-party cookies in iframes, making silent re-auth unreliable. (Confirmed from 2026-03-26 decision; applies equally to parent role.)
- **Target state prototypes created:** `target/prototypes/haisir_student_flow.html`, `target/prototypes/haisir_parent_flow.html`, `target/prototypes/haisir_admin_flow.html` — interactive HTML prototypes for the three personas.
- **`admin` = Platform Admin only in this increment:** Scoped to platform board content management. No user management, no institution management.
- **Parent exam results scoping:** Parents see child results for parent-owned exams only (`exam_templates.owner_id = parent.idp_sub`). Platform exam results not visible to parents.

---

## 2026-03-27 — Phase 0 onboarding flow — Relogin approach revised + ON01 skip

- Switched Relogin from `prompt=none` silent re-auth to **explicit logout + fresh Keycloak login** (`/auth/logout`). The `prompt=none` approach was already partially implemented but relied on APISIX honouring `redirect_uri` on `/auth/login`, which it does not (static redirect to `/home`). Explicit logout is simpler and gives a guaranteed clean JWT with the new role.
- APISIX `07-auth-login.json` (static redirect to `/home`) left as-is — OIDC plugin on `secured-authenticated` handles auth automatically on any protected route; nobody navigates to `/auth/login` directly.
- ON01 Welcome screen eliminated for first-time users: `/onboarding` auto-redirects to `/onboarding/role` when no roles are present (no "Get started" button click required).
- ON01 gains role-aware redirect for returning users with incomplete onboarding: `student` role → `/onboarding/student-ready?next=go`; `parent` role → `/onboarding/parent-ready?next=go`. This handles the post-Relogin re-entry point cleanly without any APISIX config changes.

---

## 2026-03-31 — Phase 1a: owner_type visibility enforcement

### Physical column names in parent_child_links
The `parent_child_links` table was created with physical column names `parent_sub` / `child_sub`, diverging from the spec's logical aliases `parent_idp_sub` / `child_idp_sub`. The schema is sacred — the physical names will not be renamed. All code uses the physical names. The spec retains the logical aliases with a note documenting the divergence.

### OwnerType StrEnum in domain layer
`owner_type` raw strings (`"platform"`, `"parent"`) were replaced with `OwnerType(StrEnum)` defined in `src/domain/models/owner_type.py`. Python dataclasses do not enforce type annotations at runtime, but mypy strict mode catches invalid assignments at compile time. `StrEnum` values compare equal to their string equivalents so SQLAlchemy compiled SQL is unaffected.

### Instructor gets platform_only for exam templates (not unfiltered)
The `exam_service.get_by_course_path_node_for_viewer` and `get_by_id_for_viewer` methods use `case _:` defaulting to `platform_only` rather than an explicit `case UserRole.instructor:` branch. Rationale: instructors should not see parent-private exam templates (data isolation); any future role also safely defaults to platform-only (defence in depth). The instructor persona is deferred — if it ever needs unfiltered access, the intent must be explicit.

### topic_content GET endpoints opened to any platform role
Previously student-only. Changed to `require_any_platform_role()` (student | instructor | admin). The `POST /api/topic-contents` creator role changed from instructor to admin — instructors have no content-management mandate in the current increment.

### TopicContent file URL path includes content_type subdirectory
Stored files are placed under `topics/{content_type}/{filename}` (e.g. `topics/pdf/file.pdf`). Previously files were flat under `topics/`. This is a breaking change for files on disk, but no production data exists yet.

### role dispatch in services uses match/case _ default
All four `*_for_viewer` service methods dispatch: `student` → `*_visible(viewer_sub)`, then `case _:` → `*_platform_only()`. No explicit admin branch needed — admin is absorbed by the default. Any future role added to the platform also defaults to platform-only unless explicitly handled.

---

## 2026-03-26 — Phase 0 onboarding flow — JWT refresh approach

- Replaced iframe `prompt=none` silent refresh with an explicit **Relogin button** on ON03/ON05 View A. Safari ITP and Firefox ETP block third-party cookies in iframes, making the silent refresh fail silently. Full-page `prompt=none` redirect is first-party and works in all browsers; APISIX updates the session cookie during the OIDC flow so no client-side refresh logic is needed.
- ON03 and ON05 split into two views: View A ("You're all set!" + Relogin button) and View B (CTAs). Onboarding is not marked complete until the user exits View B.
- ON07 (role-switcher demo) and ON08 (ready screen) removed from the onboarding flow. Users complete onboarding with a single role; the role switcher is post-onboarding persistent topbar only.
- `PATCH /api/users/me/onboarding-complete` moved from ON08 to ON03/ON05 View B exit (any CTA or skip link).

---

## 2026-03-23 — Phase 1 persona review (Teacher/Tutor, Parent, Institution Admin, Platform Admin)

- Teacher reply edit window: 5-minute window after sending; messages locked after that. `edited_at` (nullable) added to `doubt_messages`.
- Exam results while assignment is open: two-state model — open → submission count + total only (all result fields null); after due date or full submission → full results.
- "Generate remedial assignment" (T08): deferred to Phase 2 entirely — no stub or disabled state in Phase 1.
- Parent status banner thresholds: ok = no weak topics; warn = 1–3 topics mastery 40–59%; danger = any topic < 40% OR more than 3 weak topics.
- Parent max children: capped at 10 per account (BR-PAR-016), enforced at POST /api/parent-child-links with 422.
- CSV enroll for unknown student emails: generate invite links instead of skipping. Backend returns `{email, invite_url}` list; student auto-enrolled on first login via invite URL.
- Board publish propagation: modified topics preserved; unchanged topics updated to new board version.
- Institution admin SA03: no pending state in v1 — Active + Inactive tabs only. Pending tab deferred to when institution self-registration is built.
- Platform admin feature flags: 6 total — added `haitu_enabled_global` (global AI on/off) and `institution_self_registration` (flag defined now, form deferred).
- AI log retention: configurable via `ai_log_retention_days` (default 90 days); scope is `doubt_messages` with `sender_type = 'ai'` only.
- P02 plain-language descriptions: Phase 1 uses static score-based strings; Phase 2 replaces with hAITU prose (no UI change needed).
- Weekly digest: Phase 1 stats-only (streak, topics, courses, weak count); Phase 2 adds hAITU prose.

---

## 2026-03-22 — Phase 0 review (Role Migration, Schema Extensions, User Metadata, Onboarding)

- Tutor model: publishers not session managers — students subscribe independently, tutor cannot remove students.
- Role assignment: `student` and `parent` self-select at onboarding; `tutor` via explicit "Become a tutor" flow; `instructor` invited by institution_admin; `institution_admin` assigned by platform admin; `admin` dedicated accounts only.
- Assessment module deprecated: `assessments`, `assessment_attempts`, `assessment_answers` tables deprecated. `exam_templates` is the unified model with `purpose = 'quiz' | 'exam'`. Existing data migrated as `mode = 'static'`, `purpose = 'quiz'`.
- `keycloak_sub` renamed to `idp_sub` across all specs (IdP-agnostic naming).
- `rate_per_session` removed from teacher profiles (no payment in v1; tutors are publishers not session-based).
- ON02 single-select: Student OR Parent only at onboarding (not both). Other role added later from profile.
- ON04 (Instructor setup) and ON06 (Tutor setup) removed from onboarding flow.
- `user_metadata` table: minimal — `idp_sub` (PK) + `onboarding_completed_at` only.

---

## 2026-03-22 — Phase 1 foundation review (Data model, Auth, Roles)

- Mastery formula: first attempt = raw score; subsequent = (0.6 × latest) + (0.4 × previous). Thresholds: <60 weak, 60–75 progressing, ≥75 completed.
- Pagination: cursor-based for feeds (notifications, doubt threads, chat history); offset-based for management tables (default page=1, page_size=20, max 100).
- File storage: local disk in v1 via `StorageBackend` abstract interface; `STORAGE_BACKEND` env var selects backend. S3/GCS/Azure swappable later.
- Dynamic exam ruleset: `total_questions` required; `difficulty_mix`, `topics`, `tags_include`, `tags_exclude`, `question_types` optional. Random selection with difficulty fallback (hard → medium → easy). Validated at creation time.
- hAITU escalation: structured JSON output (`escalation_ready: true/false`) — not phrase-match on "ask your teacher".
- Payment extensibility: `subscription_status` (`free`/`paid`, default `free`) and `payment_id` (nullable) added to `enrollments` and `tutor_student_relationships` now; all records default to free in v1.
- Search backend: PostgreSQL hybrid — full-text (`tsvector` + GIN) + `pgvector` semantic search. Embedding model: `all-MiniLM-L6-v2` (384-dim, self-hosted sidecar).
- Exam correct-answer mutation risk: UI warning only (no backend lock). Warning shown when editing a question used in completed exam sessions.
- `admin` role isolation: cannot combine with any other role (BR-ROLE-004). Tutor marketplace: immediate visibility on toggle, admin can suspend post-hoc.
