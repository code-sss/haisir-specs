# Gateway WAF (Coraza + OWASP CRS)

> **Target state scope:** the WAF layer at the APISIX gateway — engine version, ruleset version, exclusion discipline, and the build that produces the WASM plugin. Cross-cutting infrastructure hardening; not tied to a persona phase.
>
> Implementation lives in `haisir-deploy/gateway-docker/` (Dockerfile + vendored `coraza-proxy-wasm/`) and `haisir-deploy/common/plugin_configs/*.json` + `common/routes/*.json` (the `coraza-filter` directive maps).
>
> **Status note (2026-07-27):** the shipped build pins `coraza-proxy-wasm 0.6.0` → **Coraza v3.3.3** + **OWASP CRS v4.14.0**. Both are materially out of date: CRS 4.14.0 is affected by **CVE-2026-21876** (CVSS 9.3), and Coraza v3.3.3 predates the v3.5.0 feature that makes precise exclusions possible at all. The resulting tuning treadmill is documented under "Problem" below. This spec defines the target state; Phase 7 implements it.
>
> ## ✅ **STATUS: SHIPPED — Phase 7 closed 2026-08-06 (T8.3.1)**
>
> Everything below this box describes the target state and the reasoning that produced it. It is now
> **implemented**. What actually shipped, verified against the tree rather than the task log:
>
> | | At scoping (2026-07-27) | Shipped |
> |---|---|---|
> | Coraza engine | v3.3.3 | **v3.7.0** (BR-WAF-002 floor is v3.5.0) |
> | OWASP CRS | v4.14.0 — **CVE-2026-21876**, CVSS 9.3 | **v4.25.1 LTS** (`crs_setup_version=4251`) |
> | Blanket `ctl:ruleRemoveById` | **38 rule IDs** | **1** (`931130`) |
> | Field-scoped exclusions | impossible on v3.3.3 | 41 `ctl:ruleRemoveTargetById` + 15 `SecRuleUpdateTargetById` + 5 `…ByTag` |
> | Build source | `git clone` at build time + awk patch script | vendored in-tree, patch script deleted |
>
> **The treadmill is closed.** The one surviving blanket removal, `931130`, is a justified structural
> exception rather than residue: it targets a **`TX` variable**, so the `ARGS_POST` regex form that
> replaced the other 37 cannot apply. Recorded in `03-secured-api.json` at the directive itself.
>
> **Build (`haisir-deploy/gateway-docker/`).** `coraza-proxy-wasm` is vendored in-tree from upstream
> `0.6.0` with **ten** documented divergences — five file-level patches (APISIX body-processing
> opt-ins; registration moved to `init()` with an empty `main()` for the WASI reactor build; a
> `wasip1-bigstack.json` 4 MB linker stack, since CRS regex compilation recurses past 64 KB;
> `magefile.go` wired to it with `-buildmode=c-shared`; wasilibs operators off by default) and five
> version floors (Coraza v3.7.0, CRS v4.25.1, `go-re2 v1.12.0`, `nottinygc` removed,
> `coraza.rule.no_regex_multiline`). Go 1.25 / TinyGo 0.39.0. Base images are digest-pinned.
>
> **This component fails silently, and the verification reflects that.** An image whose WAF never
> executes still builds, links, emits a valid `main.wasm`, and reports its version — that shipped
> once (`VERSIONS.md`, "T2.2.1/T2.3.1"). So: the `Dockerfile` asserts all ten divergences before
> building (the five version floors added under T8.1.3, after the Phase 7 review found a re-vendor
> could silently revert CVE-2026-21876 and the Coraza floor while passing every gate), and
> `common/scripts/tests/waf-harness.sh` — the only check that proves filtering — is now a
> **blocking `WAF Functional Gate` stage in `gateway-docker/Jenkinsfile`, before `Push to
> Registry`**. Note the harness proves the WAF *runs*, not which ruleset it runs; the floors cover
> the rest.
>
> **Operational ceiling:** each nginx worker compiles the full CRS ruleset into its own WASM VM, so
> `worker_processes` is pinned to **1** and `mem_limit` is **3g** on a host with ~4 GB free. That
> lever is spent — a larger ruleset needs RAM or fewer rules. Dropping `nottinygc` moved container
> memory 1.46 → 2.47 GiB.
>
> **Upgrading:** follow `haisir-deploy/gateway-docker/UPGRADE-RUNBOOK.md` (T8.2.1/T8.2.2) — rebase
> procedure, the Go/TinyGo bump trial this project still owes, G2 re-run steps, and the CRS cadence
> / LTS-identification rules. Do not treat a green build as evidence of anything.
>
> ---
>
> **Status update (2026-07-30):** Phase 7 G2.2 closed — the "v3.3.3 silently matches nothing"
> finding that justifies this whole phase is no longer just a 2026-07-01 field observation. T2.2.1
> and T2.2.2 empirically proved both halves on the upgraded image (Coraza v3.7.0 / CRS 4.25.1,
> `haisir-gateway:t134-fixed`, commit `69c077c`): the JSON body processor's real `ARGS_POST`
> variable naming, and that the regex-scoped `ctl:ruleRemoveTargetById` form actually narrows to the
> named field. See "Before/after" under §1 below.

---

## Problem

### 1. The engine is too old to express a precise exclusion

`ctl:ruleRemoveTargetById` accepts a collection key either as an exact string (`ARGS:user`) or as a regex delimited by slashes (`ARGS:/^json\.\d+\.field$/`). **Regex collection keys landed in Coraza v3.5.0.** The shipped build is v3.3.3.

On v3.3.3 a directive such as:

```
ctl:ruleRemoveTargetById=942200;ARGS_POST:/^json\.history\.\d+\.content$/
```

is parsed as a request to exclude a variable *literally named* `/^json\.history\.\d+\.content$/`. No such variable exists, so it matches nothing — **silently, with no error and no log line**. This was observed and re-tested on 2026-07-01 and recorded in `03-secured-api.json` as "request-scoped `ctl:ruleRemoveTargetById` is confirmed unreliable in this Coraza WASM build". The observation was correct; the attributed cause was not. It is a version gap, not an engine defect.

The collection name was never the problem. Coraza's JSON body processor writes to **`ArgsPost`**, keyed with a `json.` prefix, dot-separated nesting and numeric array indices — so `history[2].content` becomes `json.history.2.content`, and `ARGS_POST` is the correct collection.

#### Before/after (2026-07-30, Phase 7 G2.2)

The paragraph above was a 2026-07-01 field observation on the shipped v3.3.3 build. Phase 7 G2.2
(T2.2.1, T2.2.2) turned it into a controlled before/after proof:

| | Engine | Directive | Result |
|---|---|---|---|
| **Before** | Coraza v3.3.3 (shipped, pre-Phase-7) | `ctl:ruleRemoveTargetById=<id>;ARGS_POST:/^json\.history\.\d+\.content$/` | Parsed as a literal variable name — no such variable exists, so it silently matches nothing. No error, no log line. (2026-07-01 observation, `03-secured-api.json`'s pre-existing comment.) |
| **After** | Coraza v3.7.0 (Phase 7, `haisir-gateway:t134-fixed`, commit `69c077c`) | identical directive form, tested via a diagnostic rule (`ctl:ruleRemoveTargetById=900002;ARGS_POST:/^json\.history\.\d+\.content$/`) | Suppresses the rule **only** for `ARGS_POST:json.history.2.content` (200, was 403); an unrelated body field `json.topic` (403), a query arg (403), a header (403) and a cookie (403) all stayed blocked. |

T2.2.1 independently confirmed the collection naming this depends on: Coraza's JSON body processor
populates `ARGS_POST:json.history.2.content` for `history[2].content` — `json.`-prefixed,
dot-nested, 0-based numeric index — identically on both the v3.3.3 and v3.7.0 builds, so the naming
was never in question, only the engine's ability to match a regex collection key. Full evidence and
reproduction steps: `haisir-deploy/gateway-docker/VERSIONS.md` ("T2.2.1/T2.3.1" and "T2.2.2"
sections) and `Implementation_planning/TASKS.md` (T2.2.1, T2.2.2).

### 2. The workaround disabled protection wholesale

Because target-scoped exclusion appeared not to work, the escalation was `ctl:ruleRemoveById` — **whole-rule removal for the entire request**, including headers, cookies and query arguments, not just the offending body field.

Two routes now carry that pattern:

| Route | Exclusion | Effect |
|---|---|---|
| `03-secured-api.json` (`id:199110`) | **38 rule IDs** removed for `POST /api/haitu/(topic-doubt\|exam-review-chat)` | The 942xxx SQLi, 932xxx RCE and 941xxx XSS families are off for those requests **entirely** — headers, cookies and query arguments included |

Only that one block has the problem. **`12-api-exams-static.json` is the counter-example, and it is
already correct** — it uses startup-time, field-scoped directives:

```
SecRuleUpdateTargetByTag OWASP_CRS/ATTACK-SQLI "!ARGS_POST:/question_text/"
SecRuleUpdateTargetById  932271                 !ARGS_POST:/explanation/
```

These remove a *named field* from a rule's inspection scope. Every other field, header and cookie
stays fully inspected. That is precisely the target-state pattern. Its remaining problems are
different and narrower: the anomaly threshold is raised **5 → 12** (`id:199101`), `tx.arg_length` is
raised to 50 MB and `max_num_args` to 2000 (`id:199104`) — all three driven by base64 image payloads
— and the four `image_url` exclusions become unnecessary once images move to URL references. Its
exclusions on `question_text`, `explanation`, `model_answer`, `.text`, `json.description` and
`correct_answers` address genuine, unrelated false positives in science prose, mathematical
notation and quoted text; they are correctly scoped and **must be preserved**.

### Why the good pattern worked there and not on the haitu routes

`SecRuleUpdateTargetByTag` / `SecRuleUpdateTargetById` are **config-parse-time** directives, and
their `!COLLECTION:/regex/` target form has been supported far longer than v3.5.0 — which is why
route 12's exclusions work today on Coraza v3.3.3. The v3.5.0 gap is specific to the **runtime
`ctl:` action** form.

`id:199110` needs the runtime form because `03-secured-api.json` is a *shared* plugin config applied
across all `/api/*` routes: a startup-time directive there would exempt the field on every endpoint,
not just the two that carry chat prose. Hence the chained `SecRule REQUEST_URI ... ctl:` construction
— which then hit the v3.3.3 regex gap and got escalated to whole-rule removal. Route 12, being a
dedicated route config, could use the startup-time form and did.

The exclusion block on `199110` grew across **seven rounds in nine days** (2026-07-01, 07-06, 07-08 ×2, 07-09 ×3), each triggered by ordinary AI-generated markdown: the word `session_id`, a backtick-quoted term, a markdown table row `| Area |`, an apostrophe in a contraction, `---` after a sentence, a literal `<br>`.

### 3. The root cause is in the application, not the WAF

CRS matches regexes against bytes. Natural-language prose, markdown and LLM output are indistinguishable from injection payloads to a regex, and always will be. The endpoints above put multi-kilobyte AI-generated markdown into request bodies on every turn — see `15_security_headers.md`'s sibling analysis and the Phase 7 design goals. **No WAF engine or ruleset fixes this; only not sending the payload does.**

There is also a hard ceiling ahead: `tx.total_arg_length` is 65535, and rule **920390 is not in the exclusion list**. Sufficiently long review chats will begin returning 403 regardless of how many more rule IDs are added.

### 4. The ruleset carries a critical, unpatched CVE

**CVE-2026-21876** (CVSS 9.3, published 2026-01-06) — rule `922110` overwrites its own capture variables while iterating multipart sections, so only the **last** part is validated. An attacker places a UTF-7 encoded payload in the first part and clean UTF-8 in the last. Affects CRS 3.3.x–3.3.7 and 4.0.0–4.21.0; fixed in 4.22.0 / 3.3.8. It is a rule-logic defect, so Coraza is affected identically to ModSecurity. `04-secured-api-upload.json` is the exposed surface.

---

## Goal

- A WAF whose exclusions are **scoped to the field that needs them**, never to the whole request.
- A ruleset new enough to carry current CVE fixes, upgradable on a routine cadence.
- A gateway build that can be upgraded without archaeology — no undocumented version pins, no source-patching by pattern match.
- Application payloads shaped so that exclusions are rare, not structural.

---

## Solution summary

Stay on **OWASP Coraza** as a proxy-wasm filter inside APISIX. It is an OWASP project (vendor-neutral, Apache-2.0), runs **in-process** — so there is no external detector to add latency, no fail-open/fail-closed decision to make, and no additional container to operate.

Four changes:

1. **Vendor** `corazawaf/coraza-proxy-wasm` into `haisir-deploy/gateway-docker/coraza-proxy-wasm/` as a maintained fork, replacing the build-time `git clone --branch <tag>` plus awk patch of `wasmplugin/plugin.go`.
2. **Upgrade** Coraza to ≥ v3.5.0 (the regex-target floor; latest confirmed v3.7.0) and OWASP CRS to 4.25.1 LTS or later.
3. **Rewrite** every exclusion in field-scoped form, retiring both blanket blocks.
4. **Remove the payloads** that make exclusions necessary (Phase 7 design goals, specced against `03_student.md` / `05_parent.md` endpoints).

### Alternatives evaluated and rejected (2026-07-27)

Recorded so they are not re-litigated.

| Option | Verdict |
|---|---|
| **SafeLine** (Chaitin) via APISIX's built-in `chaitin-waf` plugin | **Rejected.** Semantic/grammar analysis genuinely solves the prose false-positive class, and the plugin is stock in APISIX ≥ 3.5. But the community detection engine is a closed-source binary from a non-EU vendor, processing student chat content; it is out-of-process (latency + a fail-open/closed decision) and adds ~5 stateful containers. A prior POC (`safeline-new-poc`) was completed and abandoned for these reasons. |
| **open-appsec** (Check Point) | **Rejected.** Apache-2.0 and genuinely open source, and the earlier POC finding that it "only monitors for 7–14 days" is **wrong** — the model ships pre-trained on millions of requests, the local learning phase is ~2–3 days, and Prevent mode is available from day one (the staged rollout is advice, not a gate). Rejected instead because it is **Israeli (Check Point, Tel Aviv), not European** as previously assumed; it is out-of-process (agent container + attachment); it still requires a custom APISIX image, so it does not remove the build-maintenance burden; and the production-recommended "Advanced Model" must be fetched from `my.openappsec.io` behind a login. |
| **ModSecurity / BunkerWeb** | **Rejected.** Same CRS ruleset, therefore identical false positives; ModSecurity 2.x is end-of-life. A lateral move. |
| **CrowdSec AppSec component** | **Adopted as a complement, not a replacement** — see below. |

### CrowdSec: virtual patching as a complementary layer

The deployed CrowdSec integration is **IP reputation only** — `crowdsec-bouncer.lua` polls LAPI for decisions and blocks by source IP. There is no `appsec_config`, no acquisition datasource, and no request forwarding.

CrowdSec's **virtual patching** ruleset targets specific confirmed CVEs and exploit signatures rather than generic injection shapes, so false positives are near-zero by construction. It is a forwarding model (the bouncer POSTs the request to the agent's AppSec listener and waits), which is the out-of-process hop Coraza avoids — so it is opt-in per route, appropriate for upload/auth/admin routes where CRS already behaves and prose never appears. Sequenced **after** the Coraza work, not instead of it.

---

## Architecture

### Build

```
haisir-deploy/gateway-docker/
├── Dockerfile                     ← multi-stage: TinyGo builder → apache/apisix
├── coraza-proxy-wasm/             ← VENDORED fork (was: git clone at build time)
│   └── wasmplugin/plugin.go       ← APISIX body-processing patch applied in-tree
└── crowdsec/crowdsec-bouncer.lua
```

The current build clones upstream at a pinned tag and rewrites `wasmplugin/plugin.go` with an **awk script that matches source lines by pattern** (`coraza/apply-apisix-patch.sh`). That script breaks silently against any newer upstream source. Vendoring converts it from a fragile rewrite into a one-time, reviewable in-tree diff.

The APISIX-specific patch itself remains necessary: APISIX WASM plugins require explicit `SetProperty("wasm_process_req_body")` / `("wasm_process_resp_body")` opt-in, or `OnHttpRequestBody`/`OnHttpResponseBody` are never invoked.

### Version pinning

`GO_VERSION`, `TINYGO_VERSION`, `TINYGO_SHA256` and the Coraza/CRS versions **move as one set**. TinyGo 0.34.x supports Go ≤ 1.23; a newer Go requires a newer TinyGo, which is only tested against newer proxy-wasm sources.

The current pins are justified in `Dockerfile:9-12` only as *"0.6.0 is the last stable release with tested dependencies"*. An exhaustive search of `git log --all`, all commits touching `gateway-docker/Dockerfile`, `docs/`, `plan_dir/`, `.github/instructions/` and this repo found **no record of an actual build failure**. The claimed "WASM will not compile with a newer Go" blocker is undocumented and may not be real. Phase 7 opens with a timeboxed spike to establish which of Go / TinyGo / Coraza is the genuine constraint, before assuming any of them is.

### Exclusion form

Target state — precise, field-scoped:

```
SecRule REQUEST_URI "@rx ^/api/haitu/(topic-doubt|exam-review-chat)$" \
    "id:199110,phase:1,pass,nolog,chain"
SecRule REQUEST_METHOD "@streq POST" \
    "ctl:ruleRemoveTargetById=942200;ARGS_POST:/^json\.(history\.\d+\.content|message)$/"
```

Everything not named by the regex — headers, cookies, query arguments, and every other body field — keeps full inspection. Contrast with the current form, which removes the rule for the entire request.

---

## Policy (business rules)

- **BR-WAF-001 — In-process only.** The WAF runs as a proxy-wasm filter inside APISIX. No out-of-process detector, so there is no fail-open/fail-closed mode to configure and no WAF-specific availability dependency. Any future out-of-process component (e.g. CrowdSec AppSec) is additive and per-route, and must not become the sole inspection path.
- **BR-WAF-002 — Coraza floor v3.5.0.** The engine must be at or above the version that supports regex collection keys in `ctl:ruleRemoveTargetById` / `ByTag` / `ByMsg`. Below this, target-scoped exclusions fail silently and the only working form is whole-rule removal.
- **BR-WAF-003 — CRS floor 4.22.0, on the LTS track.** The ruleset must be at or above the CVE-2026-21876 fix. Target 4.25.1 LTS or later; prefer the LTS track for predictable upgrades. **LTS is identified by the GitHub release *name* (`v4.25.1 (LTS)`), never by the tag or the version number** — a higher version is routinely not LTS, so "upgrade to latest" silently leaves the supported track. Cadence, the authoritative LTS/advisory queries, and the current position against every open CRS advisory are maintained in `haisir-deploy/gateway-docker/UPGRADE-RUNBOOK.md` § "CRS upgrade cadence and where the LTS track is tracked" (T8.2.2). Summary as of 2026-08-06: rolling releases monthly, LTS patches roughly quarterly, security fixes landing on all supported lines the same day and the advisory publishing about a day later; **check quarterly and on any CRS advisory** — monthly checking buys nothing on an LTS track. We ship 4.25.1, which is the newest LTS and is patched against all four open advisories.
- **BR-WAF-004 — Exclusions are field-scoped.** `ctl:ruleRemoveById` (whole-rule, whole-request) is prohibited for new exclusions. Prefer the **startup-time** form — `SecRuleUpdateTargetById <id> !<COLLECTION>:/regex/` or `SecRuleUpdateTargetByTag <tag> "!<COLLECTION>:/regex/"` — wherever the exclusion applies to a whole route config; it is simpler, has no engine-version floor, and is already proven in this codebase. Use the **runtime** form `ctl:ruleRemoveTargetById=<id>;<COLLECTION>:/regex/` only where the exclusion must be conditional (chained on URI or method inside a shared plugin config); that form requires Coraza ≥ v3.5.0 per BR-WAF-002.
- **BR-WAF-005 — Unscoped tag-family removal is prohibited; field-scoped tag exclusion is the preferred form.** `ctl:ruleRemoveByTag=<tag>` strips high-precision detectors (libinjection-backed `942100`/`942101`, `941100`/`941101`) alongside the low-precision regex rules that actually false-positive, and is never acceptable. `SecRuleUpdateTargetByTag <tag> "!ARGS_POST:/field/"` is the opposite — it narrows one tag's scope by one named field and leaves everything else inspected. It is the recommended form wherever the exclusion applies to a whole route config (`12-api-exams-static.json` is the reference example).
- **BR-WAF-006 — Anomaly thresholds are not route-tunable.** The `inbound_anomaly_score_threshold` stays at the platform default (5). Raising it per-route (as `12-api-exams-static.json` does, 5 → 12) silently weakens every rule at once and hides which specific rule needed attention.
- **BR-WAF-007 — Every exclusion carries a written justification.** Rule ID(s), the exact field, the reason the rule cannot apply, the residual risk, and the compensating control. This convention is already followed and is worth preserving verbatim.
- **BR-WAF-008 — Exclusions are reviewed when their justification changes.** An exclusion whose compensating control has since shipped must be retired or its comment corrected. (Live example: the `931130` justification still says the topic-content URL allowlist is "tracked in backend task"; it has been implemented — https-only scheme plus hostname allowlist, rejecting protocol-relative `//evil.com`.)
- **BR-WAF-009 — Prose does not belong in inspected bodies.** Endpoints must not place AI-generated or free-form markdown in request bodies where the server can reconstruct it from its own state. Where prose is genuinely user-authored and must be sent, it goes in a single named field so one narrow exclusion covers it.
- **BR-WAF-010 — Version pins move as a set, with recorded evidence.** `GO_VERSION`, `TINYGO_VERSION`, `TINYGO_SHA256`, Coraza and CRS versions are upgraded together. Any pin held back below latest must record the **observed** failure — command, error output, date — not an asserted incompatibility.
- **BR-WAF-011 — Exclusion changes soak before enforcement.** Rewriting or retiring an exclusion requires a `SecRuleEngine DetectionOnly` period on the affected URIs, with logs reviewed, before blocking is restored. Retiring a blanket exclusion without first proving the scoped replacement fires will 403 live traffic.
- **BR-WAF-012 — Route matching is unambiguous.** No two routes may match the same URI at equal priority. (Live example: `19-api-haitu.json` (`/api/haitu/*`), `21-api-haitu-exam-review.json` and `22-api-haitu-pattern-analysis.json` all sit at priority 20, so which `body_schema` is enforced depends on radixtree tie-breaking rather than intent.)
- **BR-WAF-013 — The WAF only sees requests that survive the REWRITE phase, so an unauthenticated probe cannot test WAF behaviour on an authenticated route.** `coraza-filter` is registered with `http_request_phase: "access"`; APISIX's `openid-connect` implements `_M.rewrite`. Rewrite runs before access, and plugin *priority* orders plugins only **within** a phase — so `coraza-filter`'s 7999 does **not** put it ahead of `openid-connect`'s 2599. On any route carrying `openid-connect` (`secured-api`, `secured-api-upload`, `secured-authenticated`), an unauthenticated request is terminated with 401 in rewrite and Coraza never evaluates it.

  Verified live on staging 2026-08-07: an identical SQLi payload returns **403 on `/`** (`secured-anonymous`, no OIDC) with 8 Coraza rule matches, and **401 on `/api/*`** with **zero** Coraza log lines ever recorded for an `/api/` URI.

  **This is not a protection gap** — authenticated traffic passes rewrite and does reach the WAF, which is exactly why T2.3.2's real browser journeys produced Coraza *false positives* on `/api/` routes. It is a constraint on how the WAF can be **tested**:

  - A test asserting a WAF verdict on an authenticated route **must** send a valid token, or it can only ever observe the 401 and is structurally incapable of reaching the rule it claims to test.
  - Prefer `common/scripts/tests/waf-harness.sh` for rule-level regression tests. It loads **only** `coraza-filter` (`jq '{plugins: {"coraza-filter": …}}'`), stripping `openid-connect`, `ua-restriction` and `uri-blocker` — so no other plugin can produce a look-alike 403, and no credentials are needed. That is where the CVE-2026-21876 probe lives.
  - Asserting on a status code alone is insufficient where a payload could trip an unrelated rule. Assert the **rule ID** fired (the CVE probe checks for `id "922110"`, because its UTF-7 payload decodes to `<script>alert(1)</script>` and an XSS rule could otherwise mask a broken 922110).

---

## Phasing (high level)

| Phase | Repo | Outcome |
|---|---|---|
| 7 · G1 | deploy | proxy-wasm vendored; Go/TinyGo/Coraza/CRS at latest supported set; spike records the real ceiling |
| 7 · G2 | deploy | **HARD GATE** — CVE-2026-21876 proven blocked; regex-scoped exclusion proven to fire |
| 7 · G3 | backend, frontend | payload design fixed (see `15_security_headers.md` phasing table and Phase 7 goal tree) |
| 7 · G4 | deploy | exclusions rewritten field-scoped or deleted; anomaly threshold restored; route priorities disambiguated |
| 8+ | deploy | CrowdSec AppSec virtual patching on non-prose routes |

---

## Out of scope / follow-up

- **LLM-layer threats are not WAF-addressable.** Prompt injection, system-prompt leakage and exfiltration via model output are invisible to any of the engines evaluated — they are role/semantic concerns, not payload-shape concerns. The `ReviewChatMessage.role` injection hole is fixed in Phase 7 G3 as an application change. A broader LLM guardrail layer is not specced.
- **CrowdSec AppSec** deployment (acquisition datasource, `appsec_config`, bouncer forwarding) — Phase 8 candidate.
- **DAST coverage of WAF behaviour** — `Jenkinsfile.integration-dast` exists; running authenticated ZAP against staging on every release is a standing follow-up from the 2026-07-02 review.
- **Response-body inspection** is enabled by the APISIX patch but no policy depends on it today; whether it earns its cost is unevaluated.
