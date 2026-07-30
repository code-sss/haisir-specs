# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:`b865ec1` frontend:`bc4d6f7` deploy:`fd997a8` (2026-07-30, reconciled after
> Phase 6.5 shipped in the interim — see `PLAN.md`'s reconciliation note)
> Phase 7 scoped 2026-07-27 — see `PLAN.md` for the goal tree and scope locks.

## G1 [deploy]: Gateway build modernised and self-maintained

### G1.1 [deploy]: Vendor coraza-proxy-wasm into the repo
- [x] T1.1.1 [deploy]: Vendor `corazawaf/coraza-proxy-wasm` at the current pinned tag `0.6.0` into `gateway-docker/coraza-proxy-wasm/`, preserving upstream LICENSE and a `VENDORED.md` recording upstream URL, tag, commit SHA and date (2026-07-29)
- [x] T1.1.2 [deploy]: Apply the APISIX body-processing patch in-tree to `wasmplugin/plugin.go` (the `wasm_process_req_body` / `wasm_process_resp_body` `SetProperty` opt-ins) as a reviewable diff (2026-07-29)
- [x] T1.1.3 [deploy]: Delete `gateway-docker/coraza/apply-apisix-patch.sh` and the `git clone --depth 1 --branch` step from the Dockerfile builder stage (depends on T1.1.2) (2026-07-29)
- [x] T1.1.4 [deploy]: Confirm the image builds reproducibly from the vendored tree and the WASM filter loads in APISIX — no behaviour change at this step (depends on T1.1.3) (2026-07-29)
- [x] **G1.1: proxy-wasm vendored with the patch in-tree** — integration test (2026-07-29)

### G1.2 [deploy]: Spike — establish the real version ceiling
- [x] T1.2.1 [deploy]: Timeboxed spike — attempt Go 1.24/1.25 + TinyGo ≥0.36 + Coraza v3.7.0 against the vendored tree; capture the actual failing command and error output for whichever pin genuinely blocks (2026-07-29; found 3 distinct real blockers, not the assumed one — see `gateway-docker/VERSIONS.md`)
- [x] T1.2.2 [deploy]: Record the finding in `gateway-docker/VERSIONS.md` — the observed ceiling with evidence per BR-WAF-010, replacing the current undocumented `Dockerfile:9-12` assertion (depends on T1.2.1) (2026-07-29)
- [x] **G1.2: real ceiling established with recorded evidence** — acceptance test (2026-07-29; evidence: Coraza v3.7.0 requires Go≥1.25.0; TinyGo needs ≥0.39.0 for Go 1.25 host support, not ≥0.36 as assumed; TinyGo 0.39.0+Go 1.25 then fails at wasm-ld with undefined libc symbols from `wasilibs/nottinygc@v0.7.1` and `wasilibs/go-re2@v1.6.0`'s prebuilt archives — real ceiling is those wasilibs versions, tracked in T1.3.4, not the Go/TinyGo/Coraza pins alone)

### G1.3 [deploy]: Upgrade the pinned version set
- [x] T1.3.1 [deploy]: Bump `github.com/corazawaf/coraza/v3` to ≥ v3.5.0 (target v3.7.0) — BR-WAF-002 floor; upstream `go.mod` still pins v3.3.3 so this must be forced (depends on T1.2.2) (2026-07-29; forced to v3.7.0 via `go mod edit`+`go mod tidy`, verified building — see `gateway-docker/VERSIONS.md` "Resolution")
- [x] T1.3.2 [deploy]: Replace vendored CRS under `wasmplugin/rules/crs/` with 4.25.1 LTS or later — BR-WAF-003 floor; verify the `Include @owasp_crs/*.conf` embed path still resolves (depends on T1.2.2) (2026-07-29; CRS 4.14.0 → 4.25.1 LTS, vendored tree byte-identical to upstream, local rule 900120 re-applied, `tx.crs_setup_version` 4140 → 4251; `Include @owasp_crs/*.conf` is directory-name-based so no code change needed — verified by `docker build --target builder` — see `gateway-docker/VERSIONS.md` T1.3.2)
- [x] T1.3.3 [deploy]: Bump `GO_VERSION`, `TINYGO_VERSION` and `TINYGO_SHA256` together to the set established by the spike (depends on T1.2.2) (2026-07-29; Go 1.25, TinyGo 0.39.0, sha256 `775f15974e...` — `gateway-docker/Dockerfile`)
- [x] T1.3.4 [deploy]: Verify `coraza-wasilibs` compatibility across the version jump; pin or bump as required (depends on T1.3.1) (2026-07-29; `go-re2` forced to v1.12.0 — wasm2go backend links under TinyGo 0.39, v1.6.0's prebuilt archive doesn't; `nottinygc` removed entirely — frozen at v0.7.1, no compatible release exists, upstream itself recommends against using it. Verified end-to-end with a real `docker build` of the committed Dockerfile+vendored tree, not just a scratch copy. Known carried risk: dropping nottinygc reverts to TinyGo's default GC/allocator — a real perf-under-load change, not just a version bump; recommend checking during G2.3's existing WAF-suite run rather than a new gate)
- [x] T1.3.5 [deploy]: Evaluate the `coraza.rule.no_regex_multiline` build tag — aligns `@rx` with CRS expectations and reduces false positives (depends on T1.3.1) (2026-07-29; **adopted** unconditionally in `magefiles/magefile.go` `Build()` + mirrored into `Test()`/`Coverage()` `-tags=`. Traced in Coraza v3.7.0 source: flag drops the implicit `(?m)` so `^`/`$` match whole-string only; grepped both CRS 4.14.0 and 4.25.1 — zero rules rely on implicit multiline, so no detection regression, only tighter `^`/`$` for this project's own field-scoped exclusions — see `gateway-docker/VERSIONS.md` T1.3.5)
- [x] **G1.3: version set upgraded and building** — integration test (2026-07-29; all of T1.3.1–T1.3.5 done, verified by a real `docker build --target builder` of the committed Dockerfile + vendored tree, commit `15c909a`)

### G1.4 [deploy]: Gateway builder stage on Minimus
- [ ] T1.4.1 [deploy]: Swap the gateway builder stage base image to `reg.mini.dev` per BR-INFRA-004, `-dev` tag confined to the builder stage only (depends on T1.3.3)
- [ ] T1.4.2 [deploy]: Update `.github/instructions/docker-compose.instructions.md` — it documents APISIX as 3.14.x while the Dockerfile builds 3.17.0-ubuntu
- [ ] **G1.4: builder stage on Minimus, runtime unchanged** — integration test

- [ ] **G1: Gateway build modernised and self-maintained** — integration test

## G2 [deploy]: WAF verification — HARD GATE

### G2.1 [deploy]: CVE-2026-21876 blocked
- [ ] T2.1.1 [deploy]: Add a regression test posting a multipart request with a UTF-7 payload in the first part and clean UTF-8 in the last; assert it is blocked (depends on T1.3.2)
- [ ] T2.1.2 [deploy]: Confirm the test fails against the pre-upgrade image and passes after — proving the ruleset bump is what fixed it (depends on T2.1.1)
- [ ] **G2.1: multipart charset bypass blocked** — acceptance test

### G2.2 [deploy]: Regex-scoped exclusion proven to work
- [ ] T2.2.1 [deploy]: Prove Coraza's JSON body processor populates `ARGS_POST` with `json.`-prefixed, dot-nested, numerically-indexed keys — assert the observed variable name for `history[2].content` (depends on T1.3.1)
- [ ] T2.2.2 [deploy]: Prove `ctl:ruleRemoveTargetById=<id>;ARGS_POST:/^json\.history\.\d+\.content$/` suppresses the rule for that field **and leaves it active** for headers, cookies, query args and other body fields (depends on T2.2.1)
- [ ] T2.2.3 [deploy]: Record the before/after in `16_gateway_waf.md`'s status note — the v3.3.3 silent-no-match behaviour is the finding that justifies this whole phase (depends on T2.2.2)
- [ ] **G2.2: field-scoped exclusion demonstrably fires** — acceptance test

### G2.3 [deploy]: No regression in detection
- [ ] T2.3.1 [deploy]: Run the existing WAF suites (`common/scripts/tests/02-test-waf.sh`, `15-test-waf-config-validation.sh`, `16-test-waf-advanced.sh`) against the new image (depends on T1.3.3)
- [ ] T2.3.2 [deploy]: Capture a benign-traffic corpus from real journeys and assert zero blocks at the platform anomaly threshold (depends on T2.3.1)
- [ ] **G2.3: attack corpus blocked, benign corpus passes** — acceptance test

- [ ] **G2: WAF verification** — acceptance test — **HARD GATE: G4 must not start until this passes**

## G3 [backend, frontend, deploy]: Payload design fixed at the source

### G3.1 [backend]: Prompt injection closed
- [x] T3.1.1 [backend]: Constrain `ReviewChatMessage.role` to `Literal["student", "ai"]` in `src/schemas/haitu.py:11-12`, mirroring `HaituDoubtMessageSchema` in the sibling schema (2026-07-29)
- [x] T3.1.2 [backend]: Change `_DOMAIN_TO_LLM_ROLE.get(m.role, m.role)` to `_DOMAIN_TO_LLM_ROLE[m.role]` at `src/api/routes/haitu.py:840` so an unmapped role cannot be silently forwarded (depends on T3.1.1) (2026-07-29)
- [x] T3.1.3 [backend]: Regression test — a posted `{"role": "system", ...}` history entry is rejected with 422, not forwarded into `_build_no_rag_messages` (depends on T3.1.2) (2026-07-29)
- [ ] **G3.1: injected system turns rejected** — integration test

### G3.2 [backend, frontend]: exam-review-chat persists server-side
> **T3.2.1 design output (2026-07-29, two-pass challenge):** persistence model is `review_chat_threads`
> + `review_chat_messages` (new tables, not a reuse of `doubts`/`doubt_messages`) — full schema and
> persistence contract in `target/requirements/01_data_model.md` ("New tables — review_chat_threads +
> review_chat_messages") and `target/requirements/11_haitu_ai_layer.md` §8.4a; rationale in
> `decisions.md` (2026-07-29, "T3.2.1: exam-review-chat persistence model designed"). T3.2.3a added
> below — the original 6-task breakdown had no task creating the GET endpoint T3.2.5 depends on.
- [x] T3.2.1 [backend]: Design the persistence model — reuse `doubts`/`doubt_messages` or add a review-chat equivalent; `exam-review-chat` is currently fully stateless so this is new storage, not a refactor (2026-07-29)
- [x] T3.2.2 [backend]: Migration for the chosen model, additive only per the schema-sacred rule (depends on T3.2.1) (2026-07-30)
- [x] T3.2.3 [backend]: Persist both sides of each turn; seed the thread from the cached pattern analysis rather than accepting it from the client (depends on T3.2.2) (2026-07-30)
- [x] T3.2.3a [backend]: Add `GET /api/haitu/exam-review-chat/{attempt_id}` — same router/ownership+status guards as the POST, returns messages where `is_seed = false` ordered `(created_at, id)` (depends on T3.2.3) (2026-07-30; follow-up fix `b865ec1` added the CSRF guard that was missing from the initial GET route)
- [x] T3.2.4 [backend]: Accept `{attempt_id, message}`; keep `history` accepted-but-ignored for one release for compatibility (depends on T3.2.3) (2026-07-30)
- [ ] T3.2.5 [frontend]: Stop sending `history` from `use-exam-review-chat.ts:296,241`; load the thread via GET on mount (depends on T3.2.3a [backend], T3.2.4 [backend])
- [ ] T3.2.6 [deploy]: Relax `21-api-haitu-exam-review.json`'s `body_schema` `required: [attempt_id, message, history]`; add a matching APISIX GET route for T3.2.3a (depends on T3.2.4 [backend])
- [ ] **G3.2: review chat works with a {attempt_id, message} body** — end-to-end test

### G3.3 [backend, frontend]: topic-doubt stops replaying stored history
- [ ] T3.3.1 [backend]: Load the last N messages from `DoubtMessageRepository` in the route instead of reading `body.history` — the server already writes both sides via `add_student_message` / `finalize_ai_response`
- [ ] T3.3.2 [frontend]: Stop re-posting the pre-loaded thread from `use-haitu-doubt.ts:299` (depends on T3.3.1 [backend])
- [ ] T3.3.3 [backend]: Fix E1 — `_generate_events`' `finally` block persists an empty AI message and advances the doubt to `ai_answered` when the stream failed or the client disconnected; guard the `_persist_ai_reply` spawn on non-empty accumulated text (`haitu.py:316-329`)
- [ ] **G3.3: doubt threads round-trip without client-side replay** — end-to-end test

### G3.4 [backend]: exam-review-chat grounded server-side
- [x] T3.4.1 [backend]: Load the review payload via `ExamSessionQuestionService.get_by_session_id(attempt_id)` — already wired into `post_pattern_analysis` at `haitu.py:511` — and build the grounding context in the route (depends on T3.2.3) (2026-07-30)
- [ ] T3.4.2 [frontend]: Stop pasting question text into the message string in `use-exam-review-chat.ts:310-314`; send `question_id` (depends on T3.4.1 [backend])
- [ ] **G3.4: model answers from server-held session data, not client claims** — integration test

### G3.5 [backend, frontend]: Exam images by reference
- [ ] T3.5.1 [backend]: Add an image upload endpoint returning `{url}`, reusing the existing multipart path and `sniff_mime` magic-byte validation
- [ ] T3.5.2 [backend]: Stop calling `encode_image_to_base64` on read in `exam.py:129,148` and `exam_session.py:360,678-679`; return the stored relative path (depends on T3.5.1)
- [ ] T3.5.3 [backend]: Migrate existing base64 `image_url` values in `questions` to stored files + paths (depends on T3.5.2)
- [ ] T3.5.4 [frontend]: `question-editor.tsx:115,153` — upload before submitting the template instead of `readAsDataURL` (depends on T3.5.1 [backend])
- [ ] T3.5.5 [frontend]: Serve images via a static/asset route; verify `img-src` in the CSP still covers them (depends on T3.5.4)
- [ ] **G3.5: exam images round-trip by URL** — end-to-end test

### G3.6 [backend]: Declared field limits
- [ ] T3.6.1 [backend]: Add `Field(max_length=...)` to free-text schema fields — `message`, `question_text`, `explanation`, `model_answer`, `content`, `text`, `working_text`, `user_answer` — sized under the gateway's `tx.arg_length`
- [ ] T3.6.2 [backend]: Verify a too-long field now returns 422 naming the field, not an opaque gateway 403 (depends on T3.6.1)
- [ ] **G3.6: oversized input fails with a 422, not a mystery 403** — integration test

- [ ] **G3: Payload design fixed at the source** — end-to-end test

## G4 [deploy, backend]: Exclusions rewritten field-scoped or deleted

### G4.1 [deploy]: Soak before enforcement
- [ ] T4.1.1 [deploy]: Set `SecRuleEngine DetectionOnly` on the affected URIs per BR-WAF-011 (depends on G2)
- [ ] T4.1.2 [deploy]: Collect and review logs across real journeys before restoring blocking (depends on T4.1.1)
- [ ] **G4.1: soak evidence collected** — acceptance test

### G4.2 [deploy]: Retire the blanket-removal blocks
> **Scope widened 2026-07-29 on reconciliation.** Two more `ctl:ruleRemoveById` blocks landed in
> `03-secured-api.json` during the Phase 6.5 walkthrough — `id:199120` (932130/932240/942410, PATCH
> on OCR'd topic-content edits) and `id:199121` (931130, mirrors `id:199100` onto the parent
> content-URL route). `199121` is the same accepted, already-correctly-justified pattern as
> `199100` (see G4.5) and needs no rewrite here. `199120` is the same disease as `199110` — a
> whole-request blanket removal instead of a field-scoped one — and belongs in this task's scope.
>
> **Grep hazard:** `id:199110` names two unrelated things. This task's target is the 38-ID
> `ctl:ruleRemoveById` block at `03-secured-api.json:251-252`. The *other* `199110` is a
> `setvar:'tx.max_num_args=2000'` SecAction at `12-api-exams-static.json:39`, which belongs to
> T4.3.3, not here. Scope every edit by file, not by rule ID.
- [ ] T4.2.1 [deploy]: Replace `id:199110`'s (hAITU chat-history) and `id:199120`'s (OCR'd
      topic-content edits) `ctl:ruleRemoveById` lists in `03-secured-api.json` with field-scoped
      `ctl:ruleRemoveTargetById` targets — or delete either outright wherever G3's design fixes
      removed the offending prose from the body (depends on T4.1.2, T3.2.5 [frontend])
- [ ] T4.2.2 [deploy]: Confirm 920370 and 920390 no longer fire on the hAITU endpoints now that
      bodies are small (depends on T4.2.1)
- [ ] T4.2.3 [deploy]: Confirm headers, cookies and query args regained inspection on all affected
      endpoints — hAITU chat-history and topic-content edit routes (depends on T4.2.1)
- [ ] **G4.2: hAITU and topic-content-edit endpoints protected and false-positive-free** — integration test

### G4.3 [deploy]: Reclaim the exam authoring route
> **Do not delete this route's field-scoped exclusions.** `12-api-exams-static.json` uses
> `SecRuleUpdateTargetByTag <tag> "!ARGS_POST:/field/"`, which narrows one tag's scope by one named
> field — the target-state pattern, not the blanket removal seen on `199110`. Only the four
> `image_url` exclusions are obsoleted by G3.5. The exclusions on `question_text`, `explanation`,
> `model_answer`, `.text`, `json.description` and `correct_answers` address real, unrelated false
> positives in science prose, mathematical notation and quoted text and **must be preserved**.
- [ ] T4.3.1 [deploy]: Remove only the four `image_url` exclusions (`ATTACK-RCE`, `ATTACK-GENERIC`, `ATTACK-XSS`, `ATTACK-SQLI`) now that images are URL references; leave every other field exclusion in place (depends on T3.5.4 [frontend])
- [ ] T4.3.2 [deploy]: Restore `inbound_anomaly_score_threshold` from 12 to the platform default of 5 (`id:199101`) per BR-WAF-006 (depends on T4.3.1)
- [ ] T4.3.3 [deploy]: Restore `id:199104` in `12-api-exams-static.json` to the platform defaults now that base64 image arguments are gone — the platform baseline is `id:199004`, identical across all seven configs that set it: `max_file_size=1048576`, `combined_file_sizes=1048576`, `max_num_args=512`, `arg_name_length=256`, `arg_length=4096`, `total_arg_length=65535`. Current raised values to be retired: `max_file_size=52428800`, `combined_file_sizes=104857600`, `max_num_args=2000`, `arg_length=52428800`, `total_arg_length=104857600`. Also drop the separate `id:199110` `max_num_args=2000` SecAction at `:39` in this same file — it re-raises what this task lowers (depends on T4.3.1)
- [ ] T4.3.4 [deploy]: Confirm the surviving field exclusions still suppress their original false positives at anomaly threshold 5 — the threshold raise may have been masking cases the field exclusions alone do not cover (depends on T4.3.2)
- [ ] **G4.3: exam authoring route back to platform-default thresholds with field exclusions intact** — integration test

### G4.4 [deploy]: Unambiguous route matching
- [ ] T4.4.1 [deploy]: Raise the exact-URI routes `21-api-haitu-exam-review.json` and `22-api-haitu-pattern-analysis.json` above `19-api-haitu.json`'s `/api/haitu/*` per BR-WAF-012
- [ ] T4.4.2 [deploy]: Verify the intended `body_schema` is the one actually enforced (depends on T4.4.1)
- [ ] **G4.4: route precedence explicit** — integration test

### G4.5 [deploy]: Exclusion hygiene
- [ ] T4.5.1 [deploy]: Correct the `id:199100` `931130` justification in `03-secured-api.json` — it still says the topic-content URL allowlist is "tracked in backend task"; it shipped (https-only + hostname allowlist, rejects protocol-relative `//evil.com`), per BR-WAF-008. `id:199121` (the parent-route mirror added 2026-07-29) already carries a correct, complete justification — no fix needed there, verify only.
- [ ] T4.5.2 [backend]: Close the related gap — `TopicContentUpdate.validate_url` enforces scheme + allowlist but not the "external URLs only for `content_type == video`" rule that create applies, so PATCH can attach an allowlisted external URL to a `pdf`/`text` item
- [ ] T4.5.3 [deploy]: Re-scope or delete the remaining exclusions on `18-api-exam-session-submit.json` and the `01`/`02`/`04` plugin configs to field-scoped form per BR-WAF-004
- [ ] **G4.5: every surviving exclusion is field-scoped and truthfully justified** — acceptance test

- [ ] **G4: Exclusions rewritten field-scoped or deleted** — integration test

## G5 [frontend]: CSP enforced

### G5.1 [frontend]: Working report collector
- [x] T5.1.1 [frontend]: `src/app/csp-report/route.ts` currently reads the body and discards it — persist reports via structlog per BR-CSP-008, keeping the 204 response (2026-07-29)
- [x] T5.1.2 [frontend]: Verify reports surface where they can actually be read during the soak (depends on T5.1.1) (2026-07-29)
- [x] **G5.1: violations are captured** — integration test (2026-07-29; collector persists a posted report as a structured greppable JSON line on every input branch — locked by `tests/unit/app/csp-report-route.test.ts`, 100% coverage; hardened 2026-07-29 in `eb21350`, BR-CSP-008 — unbounded `request.text()` replaced with a 64 KiB-capped streaming read so an oversized/malicious report can't exhaust memory or flood the log)

### G5.2 [frontend]: Nonce CSP in proxy.ts
- [x] T5.2.1 [frontend]: Extend the existing `src/proxy.ts` — mint a per-request nonce, set `Content-Security-Policy-Report-Only`, forward `x-nonce` on request headers (the file exists and holds the onboarding guards; extend, do not replace)
- [x] T5.2.2 [frontend]: Derive `frame-src` from the backend `allowed_video_hostnames` allowlist per BR-CSP-005 rather than hardcoding a second copy (depends on T5.2.1)
- [x] T5.2.3 [frontend]: Confirm `worker-src 'self' blob:` covers pdf.js and whether the build needs `'wasm-unsafe-eval'` (depends on T5.2.1)
- [x] T5.2.4 [frontend]: Confirm `react-pdf.css` and `globals.css` inject nothing at runtime that the nonce will not cover (depends on T5.2.1)
- [x] T5.2.5 [frontend]: Add the prefetch `missing:` filter to the proxy matcher per the Next.js CSP guidance (depends on T5.2.1)
- [x] T5.2.6 [frontend]: Opt the **12 pages lacking `force-dynamic`** into dynamic rendering per BR-CSP-010 — 15 of 27 have it, 12 do not (7 server components, 5 `"use client"`), including all of `/onboarding/*` and `/admin/*`. A statically prerendered page cannot receive a nonce, so a strict `script-src` blocks its framework scripts. Verify by inspecting the build manifest for statically-prerendered routes, not by grep alone (depends on T5.2.1)
- [x] T5.2.7 [frontend]: Add a CI assertion that no new HTML route is statically prerendered, per BR-CSP-010 — this breaks silently in production rather than at build (depends on T5.2.6)
- [ ] **G5.2: Report-Only CSP live with nonces applied on every route** — integration test

### G5.3 [frontend]: Soak
- [x] T5.3.1 [frontend]: Exercise every journey — login, onboarding, exam authoring with image upload, exam taking, review chat, PDF viewing, video viewing, parent curriculum, admin (depends on T5.2.5) (2026-07-30; CI soak shipped — tests/e2e/g5-csp-soak.spec.ts + helpers/csp.ts, 20 journeys green; image-upload interaction, PDF-worker runtime and the full live-stack soak flagged to deploy)
- [ ] T5.3.2 [frontend]: Include the Keycloak OIDC round-trip — `07`/`08`/`09-auth-*` routes are APISIX-owned and redirect cross-origin, exercising `form-action` and navigation (depends on T5.3.1) (NOT frontend-runnable — 07/08/09-auth-* are APISIX-owned cross-origin with no src/ routes; deploy-owned live-stack soak. T5.4.1 enforcement MUST NOT proceed until this passes per BR-CSP-007)
- [x] T5.3.3 [frontend]: Review collected reports and adjust directives (depends on T5.3.2) (2026-07-30; CI soak finding = zero unexplained violations in the scoped directive set, no directive adjustments. Real-production report review incl. the OIDC round-trip is deploy-owned per BR-CSP-007 — T5.4.1 enforcement MUST NOT be unblocked until the deploy soak passes)
- [ ] **G5.3: zero unexplained violations across all journeys** — acceptance test

### G5.4 [frontend]: Enforce
- [ ] T5.4.1 [frontend]: Switch to the enforcing header name, keeping `report-uri` live per BR-CSP-009 (depends on T5.3.3)
- [ ] T5.4.2 [frontend]: Negative test — an injected inline script is blocked (depends on T5.4.1)
- [ ] **G5.4: CSP enforced** — end-to-end test

- [ ] **G5: CSP enforced** — end-to-end test

## G6 [backend, deploy]: Auth and transport verification

### G6.1 [deploy, backend]: TLS verification on Keycloak channels
- [x] T6.1.1 [deploy]: Remove `OAUTH__KEYCLOAK__SSL_VERIFY=false` from `prod/.env:39` and `staging/.env:39`; the code default is already `true` (BR-SEC-021) (2026-07-29)
- [ ] T6.1.2 [deploy]: Trust the internal CA in the backend image so self-signed Keycloak certs validate rather than being bypassed (depends on T6.1.1)
- [ ] T6.1.3 [backend]: Remove or gate the `check_hostname = False` / `CERT_NONE` context in `src/auth/user.py:37-42` so production cannot silently reach it (depends on T6.1.2)
- [ ] T6.1.4 [backend]: Verify introspection and Keycloak-admin calls succeed with verification on (depends on T6.1.3)
- [ ] **G6.1: BR-SEC-021 — no unverified TLS to Keycloak** — integration test

### G6.2 [backend]: JWT audience validation
- [ ] T6.2.1 [backend]: Confirm APISIX-injected tokens actually carry the `haisir-backend-admin` audience before enforcing — enabling this blind will 401 every request
- [ ] T6.2.2 [backend]: Set `verify_aud: True` with the expected audience in `src/auth/user.py:73` (BR-SEC-020) (depends on T6.2.1)
- [ ] T6.2.3 [backend]: Regression test — a token minted for a different realm client is rejected with 401 (depends on T6.2.2)
- [ ] **G6.2: BR-SEC-020 — audience confusion closed** — integration test

### G6.3 [deploy]: Internal TLS verification
- [ ] T6.3.1 [deploy]: Enable `openid-connect.ssl_verify` in `03-secured-api.json:450`, `01-secured-authenticated.json:308`, `04-secured-api-upload.json:311` (M5) — line numbers re-verified 2026-07-29; Phase 6.5's WAF commit shifted all three (`03` by +43, `01`/`04` by +3), so the originally-scoped `407`/`305`/`308` are stale
- [ ] T6.3.2 [deploy]: Enable `etcd.tls.verify` in `common/apisix_conf/config.yaml:48` — client certs already ship (depends on T6.3.1)
- [ ] T6.3.3 [deploy]: Move the CrowdSec LAPI channel to https and enable `ssl_verify` (`config.yaml:67,72`) — the bouncer key currently traverses the Docker network in plaintext
- [ ] T6.3.4 [deploy]: Set `sslmode=require` on OpenBao's database secrets engine connection (`common/openbao/bootstrap.sh:252`)
- [ ] **G6.3: internal channels verify TLS** — integration test

### G6.4 [deploy]: Keycloak realm hardening
- [ ] T6.4.1 [deploy]: Add `passwordPolicy` to `common/keycloak/01-realm.json` — e.g. `length(12) and notUsername and notEmail and passwordHistory(3)` (H3)
- [ ] T6.4.2 [deploy]: Set `sslRequired: "external"` (currently `"none"` at `:10`) (depends on T6.4.1)
- [ ] T6.4.3 [deploy]: Make brute-force parameters explicit — `failureFactor`, `permanentLockout`, `maxDeltaTimeSeconds` — rather than relying on defaults (depends on T6.4.1)
- [ ] T6.4.4 [deploy]: Evaluate requiring OTP/WebAuthn for `admin` and `institution_admin` (depends on T6.4.1)
- [ ] **G6.4: H3 — realm password and TLS policy enforced** — integration test

- [ ] **G6: Auth and transport verification** — integration test

## G7 [deploy, backend, frontend]: Residual review items

### G7.1 [backend]: Request size and upload validation
- [ ] T7.1.1 [backend]: Replace `Content-Length` arithmetic in `src/auth/request_middleware.py:151,169,194` with a streaming byte cap in a pure-ASGI `receive` wrapper; treat a body-bearing request with no `Content-Length` as requiring the streaming path (M2)
- [ ] T7.1.2 [backend]: Delete `_validate_file_uploads` (`request_middleware.py:189`), `_extract_filename` (`:230`) and `_is_allowed_file_type` (`:240`) — spanning roughly `:189-250`, plus the `self._validate_file_uploads(request)` call site at `:184`. They read a request-level `Content-Disposition` that never exists for multipart, so they have never rejected anything (B2). The originally-scoped range `208-228` was wrong at scoping time — it points at the `Content-Disposition` block *inside* the first function, not the three definitions (depends on T7.1.1)
- [ ] T7.1.3 [backend]: Chunk-read extraction uploads and abort past the cap in `admin_extraction.py:175-181` and `parent_extraction.py:182-188`, currently fully spooled before the 50 MB check; shared helper next to `sniff_mime` (B4)
- [ ] T7.1.4 [backend]: Malformed `Content-Length` returns 400, not an unhandled 500 (B3) (depends on T7.1.1)
- [ ] **G7.1: size limits hold under chunked encoding** — integration test

### G7.2 [deploy, backend]: Jenkins parameter injection
- [x] T7.2.1 [backend]: Validate `params.TAG` against `^[A-Za-z0-9._-]+$` and pass via `withEnv` + single-quoted `sh` in `haisir-backend/Jenkinsfile:197,209,305,340` — currently untouched since the review (M3) (2026-07-29)
- [x] T7.2.2 [deploy]: Validate `params.VERSION` against `^\d+\.\d+(\.\d+)?$` in `Jenkinsfile.deploy:58,89-107`; the remote-exec path is already correct, `MANIFEST_PATH` is not (depends on T7.2.1) (2026-07-29)
- [x] T7.2.3 [deploy]: Restrict who can trigger parameterised builds (depends on T7.2.2) (2026-07-29)
- [x] **G7.2: M3 — build params cannot inject shell** — integration test (2026-07-29; verified `VERSION`/`TAG` regex gates in both Jenkinsfiles plus `withEnv`-only shell interpolation, and `matrix-auth` plugin + documented Access Control restriction in `other/services/jenkins/README.md`)

### G7.3 [deploy]: Tailscale least privilege
- [ ] T7.3.1 [deploy]: Replace `dst: ["*:*"]` for `tag:dev1`/`tag:in-dev1`/`tag:in-dev2` in `other/services/tailscale/tailscale.json:28-35` with the specific services and ports actually needed (M4)
- [ ] T7.3.2 [deploy]: Gate prod SSH behind a separate rarely-held tag; consider Tailscale SSH check mode and session recording (`:72-84`) (depends on T7.3.1)
- [ ] **G7.3: M4 — a compromised dev laptop cannot reach prod** — acceptance test

### G7.4 [deploy]: Header cleanup
- [ ] T7.4.1 [deploy]: Set `X-XSS-Protection: 0` across all four plugin configs (L3, BR-CSP-006)
- [ ] T7.4.2 [deploy]: Add the gateway backstop CSP (`frame-ancestors`, `base-uri`, `object-src`, `form-action`) scoped to non-HTML routes only, so it never collides with `proxy.ts`'s policy per BR-CSP-004 (depends on T5.4.1 [frontend])
- [ ] **G7.4: header ownership matches the spec table** — integration test

### G7.5 [deploy, specs]: Documented acceptances
- [ ] T7.5.1 [specs]: Record L5 (`referer-restriction bypass_missing: true`, 7 files) as a deliberate spam filter, not a security boundary — no code change
- [ ] T7.5.2 [specs]: Reframe M6 and L4 as dev-isolation assertions rather than findings — prod is correctly hardened (etcd client-cert auth, no published ports, Keycloak `start` + `KC_HOSTNAME_STRICT=true`, no pgAdmin); the risk is regression, not current state
- [ ] T7.5.3 [deploy]: Add a CI assertion that the dev-only patterns (`ALLOW_NONE_AUTHENTICATION`, `start-dev`, published DB/admin ports, `KEYCLOAK_ADMIN_ALLOWED_CIDR=0.0.0.0/0`) never appear outside `dev/` (depends on T7.5.2)
- [ ] T7.5.4 [deploy]: `chmod 600` staging/dev `.env*` for consistency (L2) — they hold no secrets since Phase 5.6, so this is hygiene
- [ ] **G7.5: accepted risks are documented and regression-guarded** — acceptance test

### G7.6 [deploy]: Phase 5.6 parked gaps
- [x] T7.6.1 [deploy]: Fix `common/scripts/setup.sh`'s `APISIX_ADMIN_KEY` pre-check failing under `set -u` on standalone invocation — landed as a side effect of Phase 6.5's deploy work (the required-var check moved to after the OpenBao render hook runs); confirmed on reconciliation, 2026-07-29
- [ ] T7.6.2 [deploy]: Reconcile `common/docker-compose.yml`'s hardcoded `haisir-net` against the documented dev network `haisir-net-dev`
- [ ] **G7.6: Phase 5.6's parked deploy gaps closed** — integration test

### G7.7 [deploy]: New anomalies from the 2026-07-27 audit
- [ ] T7.7.1 [deploy]: Narrow APISIX `allow_admin` from the whole Docker subnet (`config.yaml:38`) — any container on `haisir-net` that learns the admin key can rewrite every route
- [ ] T7.7.2 [deploy]: Decide whether `enable_admin_ui: true` (`config.yaml:35`) is warranted; it is a routing-config web UI behind a single static key with no MFA
- [ ] T7.7.3 [deploy]: Harden `env-setup.sh:139` so a set `TMPDIR` cannot place the rendered secret env file on disk-backed storage instead of `/dev/shm`
- [ ] T7.7.4 [deploy]: `chmod 600` the files inside `.templated/` — the 0700 directory is currently the only protection on 0664 files containing resolved secrets
- [ ] T7.7.5 [deploy]: Migrate `other/services/sonarqube/.env` (`SONAR_DB_PASSWORD`, mode 0664) out of plaintext, or document the `other/services/*` stacks as explicitly outside the OpenBao boundary
- [ ] **G7.7: audit anomalies closed or documented** — acceptance test

- [ ] **G7: Residual review items** — integration test

## G8 [specs]: Review gate and closeout — HARD GATE

### G8.1 [specs]: Independent review passes
- [ ] T8.1.1 [specs]: Adversarial security-review pass 1 against the full diff, following the Phase 5.5/5.6 precedent
- [ ] T8.1.2 [specs]: Adversarial security-review pass 2, independent of pass 1 — 5.6's pass 2 found a live-credential bug pass 1 rated clean (depends on T8.1.1)
- [ ] T8.1.3 [specs]: Fix or explicitly accept every finding from both passes (depends on T8.1.2)
- [ ] **G8.1: two independent passes clean** — acceptance test

### G8.2 [specs]: Runbook
- [ ] T8.2.1 [specs]: Write the vendored proxy-wasm upgrade runbook — how to rebase on upstream, re-apply the APISIX patch, bump the version set, and re-run the G2 gate
- [ ] T8.2.2 [specs]: Document the CRS upgrade cadence and where the LTS track is tracked (depends on T8.2.1)
- [ ] **G8.2: the next upgrade does not require rediscovery** — acceptance test

### G8.3 [specs]: Reconcile specs with reality
- [ ] T8.3.1 [specs]: Update `16_gateway_waf.md` and `15_security_headers.md` status notes to what actually shipped
- [ ] T8.3.2 [specs]: Update `security/SECURITY_REVIEW_2026-07-02.md` annotations to final status (depends on T8.3.1)
- [ ] T8.3.3 [specs]: Append the Phase 7 close-out entry to `decisions.md` and `progress.md` (depends on T8.3.2)
- [ ] **G8.3: specs match the shipped system** — acceptance test

- [ ] **G8: Review gate and closeout** — acceptance test — **HARD GATE: no merge until this passes**

## Ready now

> Recomputed 2026-07-30 (added T2.1.1, missed on the prior pass despite its sole dependency T1.3.2
> landing 2026-07-29) after T3.2.2–T3.2.4/T3.2.3a and T3.4.1 landed. **Caveat:** entries below with no listed
> `Depends on` in TASKS.md are included on a literal read of the dependency annotations — they have
> not all been individually re-verified against PLAN.md's prose goal tree. Excluded throughout: all
> of **G4** (explicit hard gate at G2, not yet done) and all of **G8** (closeout — "the full diff",
> meaningless before G1–G7 finish, even though some of its tasks list no explicit per-task
> dependency). Also excluded: T5.3.2/T5.4.1 — literally unblocked by T5.3.1/T5.3.3 landing, but each
> carries an explicit BR-CSP-007 "MUST NOT proceed" note pending the deploy-owned live-stack soak.

**Backend**
- T3.3.1 [backend]: Load the last N messages from `DoubtMessageRepository` in the route instead of reading `body.history` (no dependencies)
- T3.3.3 [backend]: Fix E1 — guard the `_persist_ai_reply` spawn on non-empty accumulated text (`haitu.py:316-329`) (no dependencies)
- T3.5.1 [backend]: Add an image upload endpoint returning `{url}` (no dependencies)
- T3.6.1 [backend]: Add `Field(max_length=...)` to free-text schema fields (no dependencies)
- T6.2.1 [backend]: Confirm APISIX-injected tokens carry the `haisir-backend-admin` audience before enforcing (no dependencies)
- T7.1.1 [backend]: Replace `Content-Length` arithmetic with a streaming byte cap (M2) (no dependencies)
- T7.1.3 [backend]: Chunk-read extraction uploads and abort past the cap (B4) (no dependencies)

**Frontend**
- T3.2.5 [frontend]: Stop sending `history` in `use-exam-review-chat.ts`; load the thread via GET on mount (depends on T3.2.3a, T3.2.4, both done 2026-07-30)
- T3.4.2 [frontend]: Stop pasting question text into the message string in `use-exam-review-chat.ts:310-314`; send `question_id` (depends on T3.4.1, done 2026-07-30)

**Deploy**
- T1.4.1 [deploy]: Swap the gateway builder stage base image to `reg.mini.dev` (depends on T1.3.3, done 2026-07-29)
- T2.1.1 [deploy]: Add a regression test posting a multipart request with a UTF-7 payload in the first part and clean UTF-8 in the last; assert it is blocked (depends on T1.3.2, done 2026-07-29)
- T2.2.1 [deploy]: Prove Coraza's JSON body processor's `ARGS_POST` naming for nested JSON (depends on T1.3.1, done 2026-07-29)
- T2.3.1 [deploy]: Run the existing WAF suites against the new image (depends on T1.3.3, done 2026-07-29)
- T3.2.6 [deploy]: Relax `21-api-haitu-exam-review.json`'s `body_schema`; add the matching GET route (depends on T3.2.4, done 2026-07-30)
- T1.4.2 [deploy]: Update `docker-compose.instructions.md` — documents APISIX 3.14.x, Dockerfile builds 3.17.0-ubuntu (no dependencies)
- T6.1.2 [deploy]: Trust the internal CA in the backend image so self-signed Keycloak certs validate rather than being bypassed, now that `OAUTH__KEYCLOAK__SSL_VERIFY=false` is gone (depends on T6.1.1, done)
- T6.3.1 [deploy]: Enable `openid-connect.ssl_verify` in the three named plugin configs (M5) (no dependencies)
- T6.3.3 [deploy]: Move the CrowdSec LAPI channel to https and enable `ssl_verify` (no dependencies)
- T6.3.4 [deploy]: Set `sslmode=require` on OpenBao's database secrets engine connection (no dependencies)
- T6.4.1 [deploy]: Add `passwordPolicy` to `common/keycloak/01-realm.json` (H3) (no dependencies)
- T7.2.2 [deploy]: Validate `params.VERSION` against `^\d+\.\d+(\.\d+)?$` in `Jenkinsfile.deploy:58,89-107` (depends on T7.2.1, done)
- T7.3.1 [deploy]: Replace `dst: ["*:*"]` Tailscale ACLs with specific services/ports (M4) (no dependencies)
- T7.4.1 [deploy]: Set `X-XSS-Protection: 0` across all four plugin configs (L3, BR-CSP-006) (no dependencies)
- T7.5.4 [deploy]: `chmod 600` staging/dev `.env*` (L2 hygiene) (no dependencies)
- T7.6.2 [deploy]: Reconcile `docker-compose.yml`'s hardcoded `haisir-net` against `haisir-net-dev` (no dependencies)
- T7.7.1 [deploy]: Narrow APISIX `allow_admin` from the whole Docker subnet (no dependencies)
- T7.7.2 [deploy]: Decide whether `enable_admin_ui: true` is warranted (no dependencies)
- T7.7.3 [deploy]: Harden `env-setup.sh:139` against a set `TMPDIR` (no dependencies)
- T7.7.4 [deploy]: `chmod 600` the files inside `.templated/` (no dependencies)
- T7.7.5 [deploy]: Migrate `other/services/sonarqube/.env` out of plaintext, or document it outside the OpenBao boundary (no dependencies)

**Specs**
- T7.5.1 [specs]: Record L5 as a deliberate spam filter, not a security boundary — no code change (no dependencies)
- T7.5.2 [specs]: Reframe M6 and L4 as dev-isolation assertions (no dependencies)
