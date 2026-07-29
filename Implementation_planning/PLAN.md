# PLAN — Phase 7 (Gateway WAF Modernisation, CSP & Security Review Closeout)

> Scoped 2026-07-27 via `/update-target-state`. Phase 6 closed out 2026-07-26 and archived to
> `archive/PLAN_Phase6-ParentIndexingRetry_2026-07-26.md` /
> `archive/TASKS_Phase6-ParentIndexingRetry_2026-07-26.md`. Phase 5.6 was already archived
> (`archive/PLAN_Phase5.6-SecretsElimination_2026-07-16.md`).
>
> Specs: `target/requirements/16_gateway_waf.md` (new), `target/requirements/15_security_headers.md`
> (new), `target/requirements/02_auth_and_roles.md` (BR-SEC-020/021),
> `security/SECURITY_REVIEW_2026-07-02.md` (annotated with current status).
>
> **Archived unstarted 2026-07-27, restored and reconciled 2026-07-29** after Phase 6.5 (Content
> Viewing & Publish) shipped in the interim. Reconciliation found: T7.6.1 already done (Phase 6.5's
> deploy fixes reordered `setup.sh`'s required-var check past the OpenBao render hook, which is
> exactly what T7.6.1 called for); G4.2's scope grew — the Phase 6.5 walkthrough added two more
> blanket `ctl:ruleRemoveById` blocks to `03-secured-api.json` (`id:199120` on OCR'd topic-content
> edits, `id:199121` mirroring the existing `id:199100` video-URL exclusion onto the parent route),
> the same treadmill pattern G4 exists to fix. `id:199121` itself is already correctly justified
> (unlike `id:199100`, which T4.5.1 still needs to fix) so it needs no rewrite, only `id:199120`
> joins T4.2.1's scope.
>
> **Second reconciliation pass, 2026-07-29** (the first pass swept the G4 files for content drift but
> not the *other* goals' line references into those same files, and asserted an all-clear it had not
> checked). Corrected since: **T6.3.1's three line numbers were all stale** — the same Phase 6.5 WAF
> commit that added `199120`/`199121` grew `03-secured-api.json` by 43 lines and `01`/`02`/`04` by 3
> each, moving `ssl_verify` to `03:450`, `01:308`, `04:311`. **T4.3.3 named no target values** —
> "platform defaults" is `id:199004` (`max_num_args=512`, `arg_length=4096`, `total_arg_length=65535`,
> `max_file_size`/`combined_file_sizes=1048576`), identical across all seven configs that set it.
> **T7.1.2's line range was wrong at scoping** (`208-228` points inside the first function; the three
> definitions are at `:189`, `:230`, `:240`). All three are fixed in `TASKS.md`.
>
> ~25 further file:line references across G3, G5, G6, G7 and G8 were then verified individually
> against the sibling repos and are correct as written — including T5.2.6's page counts (27 pages,
> 15 with `force-dynamic`, 12 without), T3.5.2's four encode call sites, T4.4.1's three-way priority-20
> collision, and T4.5.2's `TopicContentUpdate.validate_url` gap. `src/auth/` and the haitu/exam routes
> did not change during the Phase 6.5 window at all.

## Root goal

The gateway WAF detects attacks precisely instead of being tuned into irrelevance; the browser
enforces a strict CSP; and every finding from the 2026-07-02 security review is either fixed or
explicitly and defensibly accepted.

## Context — why now

Three independent findings converged during scoping:

1. **The WAF exclusion treadmill has a mechanical root cause.** Regex collection keys in
   `ctl:ruleRemoveTargetById` landed in **Coraza v3.5.0**; the shipped build is **v3.3.3** (via
   `coraza-proxy-wasm 0.6.0`). Every attempt at a field-scoped exclusion was silently parsed as a
   literal variable name and matched nothing — which is why the workaround became whole-rule
   removal, and why the exclusion block grew across seven rounds in nine days to **38 rule IDs**.
2. **CRS 4.14.0 carries CVE-2026-21876** (CVSS 9.3, multipart charset bypass in rule 922110, fixed
   in 4.22.0 / 3.3.8 on 2026-01-06). The upload route is the exposed surface.
3. **A new finding not in the July review:** `OAUTH__KEYCLOAK__SSL_VERIFY=false` in `prod/.env:39`
   and `staging/.env:39` disables TLS verification on the backend's token-introspection and
   Keycloak-Admin channels, contradicting BR-SEC-010's fail-closed guarantee.

There is also a deadline the treadmill cannot outrun: `tx.total_arg_length` is 65535 and rule
**920390 is not excluded**, so sufficiently long review chats will 403 regardless of further tuning.

## Scope locks

- **Minimus migration is Phase 8, except the gateway builder stage.** G1 rewrites
  `gateway-docker/Dockerfile` for the Go/TinyGo bump, so swapping that one builder image to
  `reg.mini.dev` in the same edit avoids rebuilding the WASM plugin twice. The other ~25 services
  in `14_container_images.md` stay out — running two hard gates across three repos and two
  unrelated concerns would make a G2 failure unattributable (Coraza upgrade vs. base-image swap).
- **G3 (design fixes) precedes G4 (exclusion rewrite), deliberately.** Fixing the payloads first
  means several exclusions get *deleted* rather than carefully rewritten for a request shape that
  is about to stop existing.
- **Vendoring precedes upgrading.** Today's build clones upstream at a tag and awk-patches
  `wasmplugin/plugin.go` by pattern match. Vendor first and that script becomes a one-time
  reviewable diff instead of a rewrite chasing moving source.
- **No WAF engine change.** Coraza stays. SafeLine and open-appsec were evaluated and rejected with
  reasons recorded in `16_gateway_waf.md`; CrowdSec AppSec is a Phase 8 complement, not a
  replacement.
- **`_PATTERN_ANALYSIS_CACHE` is not a persistence layer.** `exam-review-chat` is fully stateless
  today (`haitu.py:838-845` reads `body.history[-10:]` and persists nothing), so G3.2 requires new
  storage, not a client-side trim. `topic-doubt` is the easy case — the server already writes to
  `doubt_messages`.

## Goal tree

```
G1 [deploy] Gateway build modernised and self-maintained
  G1.1 Vendor coraza-proxy-wasm into gateway-docker/, patch applied in-tree
  G1.2 Spike: establish the real Go/TinyGo/Coraza ceiling and record the evidence
  G1.3 Upgrade the pinned version set (Go, TinyGo+SHA, Coraza >=3.5.0, CRS >=4.22.0)
  G1.4 Gateway builder stage moved to reg.mini.dev (Minimus overlap only)
  * G1 integration test: image builds reproducibly; APISIX starts; WASM filter loads

G2 [deploy] WAF verification — HARD GATE
  G2.1 CVE-2026-21876 multipart charset bypass is blocked
  G2.2 Regex-scoped ctl:ruleRemoveTargetById demonstrably suppresses a rule
  G2.3 Baseline attack corpus still blocked; benign corpus still passes
  * G2 acceptance test: documented evidence for each of G2.1-G2.3 before G4 may start

G3 [backend, frontend, deploy] Payload design fixed at the source
  G3.1 Prompt injection closed — ReviewChatMessage.role constrained
  G3.2 exam-review-chat persists server-side; client sends {attempt_id, message}
  G3.3 topic-doubt stops replaying history the server already stores
  G3.4 exam-review-chat grounded in server-side session data
  G3.5 Exam images uploaded and referenced by URL, not base64-inlined
  G3.6 max_length on free-text schema fields
  * G3 end-to-end test: chat and exam authoring work with bodies under tx.arg_length

G4 [deploy, backend] Exclusions rewritten field-scoped or deleted
  G4.1 DetectionOnly soak on affected URIs
  G4.2 199110's 38-ID block and 199120's OCR-content block replaced with field-scoped
       targets (or deleted post-G3); 199121 already correctly scoped/justified, no rewrite
  G4.3 12-api-exams-static image_url exclusions + anomaly/size raises retired
  G4.4 Route priority collision on /api/haitu/* resolved
  G4.5 Stale exclusion justifications corrected (931130 URL allowlist has shipped)
  * G4 integration test: prose passes, real payloads blocked, anomaly threshold back to 5

G5 [frontend] CSP enforced
  G5.1 Report collector persists reports
  G5.2 proxy.ts mints nonce, emits Report-Only CSP, all routes rendered dynamically
  G5.3 Soak across all journeys including the Keycloak OIDC round-trip
  G5.4 Switch to enforcing; report-uri stays live
  * G5 end-to-end test: no violations on any journey; inline script injection blocked

G6 [backend, deploy] Auth and transport verification
  G6.1 BR-SEC-021 — OAUTH__KEYCLOAK__SSL_VERIFY true in staging/prod, CA trusted
  G6.2 BR-SEC-020 — JWT audience validated
  G6.3 M5 — OIDC/etcd/CrowdSec TLS verification enabled
  G6.4 H3 — Keycloak passwordPolicy, sslRequired=external, explicit brute-force params
  * G6 integration test: revoked token rejected; wrong-audience token rejected; TLS verified

G7 [deploy, backend, frontend] Residual review items
  G7.1 M2/B4 — streaming size cap replaces Content-Length trust; dead upload validator deleted
  G7.2 M3 — Jenkins build params validated and passed via withEnv
  G7.3 M4 — Tailscale dev tags off *:*
  G7.4 L3 — X-XSS-Protection: 0; gateway backstop CSP scoped to non-HTML routes
  G7.5 L5 + dev-isolation assertions documented rather than "fixed"
  G7.6 Phase 5.6 parked deploy gaps (setup.sh under set -u; haisir-net vs haisir-net-dev)
  G7.7 New anomalies from the 2026-07-27 audit
  * G7 integration test: chunked-encoding upload rejected; parameterised build rejects bad input

G8 [specs] Review gate and closeout — HARD GATE
  G8.1 Two independent adversarial security-review passes
  G8.2 Runbook for the vendored proxy-wasm upgrade path
  G8.3 Spec + review-doc updates reconciled against what shipped
  * G8 acceptance test: both passes clean or findings fixed; specs match reality
```

**DAG spine:** `G1 → G2 (gate) → G3 → G4 → G5 → G6 → G7 → G8 (gate)`

G6 and G7 are mutually independent of each other and of G5. G3 may start as soon as G1 is underway
— it has no dependency on the WAF build — and G4 must not begin until G2 passes.

Two documented exceptions to the spine, both real and both in `TASKS.md`:

- **G5 starts early.** T5.1.1 (make the CSP report collector persist) has no dependency on anything
  in G1–G4 and is listed in "Ready now". Only the *soak and enforcement* (G5.3, G5.4) need to wait,
  and they wait on nothing in G1–G4 either — they wait on G5.2.
- **G7 reaches back into G5.** T7.4.2 (gateway backstop CSP scoped to non-HTML routes) depends on
  T5.4.1, because the backstop must not be applied until `proxy.ts` owns the full policy, or the two
  layers collide (BR-CSP-004).

The spine orders *goal completion*, not every task within a goal.

**Baseline at planning (2026-07-27):** backend `c82d466`, frontend `67a883c`, deploy `861705b`,
specs `1928b48`. **Reconciled baseline (2026-07-29):** backend `583511d`, frontend `3a57718`,
deploy `8cb1dbe` — see the reconciliation note above for what changed in between.

## Carried forward, not in this phase

- Minimus migration for the remaining ~25 services (`14_container_images.md`) — **Phase 8**
- CrowdSec AppSec virtual patching — Phase 8 candidate, after the Coraza work stabilises
- Remaining role migration (`become-tutor`; `invite-role` + `/institution` still **blocked** —
  institution_admin is on explicit hold per `decisions.md` 2026-07-27)
- Per-child audience scoping of parent-created content — still no trigger complaint on record
- Parent-facing hAITU endpoints — still blocked on a progress-monitoring-UI product decision
- Platform Admin indexing-status gap (the `07_platform_admin.md` twin of Phase 6's parent fix)
- Dedicated IDOR test pass; authenticated ZAP DAST on staging; gitleaks as a pre-commit hook
- Staging/prod OpenBao bring-up (runbook exists; deferred until those environments are stood up)
- `other/services/*` stacks (sonarqube, npm, dockhand, jenkins, registry, embedding) were never in
  the OpenBao migration scope and remain outside it

<!-- plan-baseline: backend:583511dec7fa94c800a6865c7e500338518d8dbb frontend:3a57718774770fe6180f50ca4f46a25eef207890 deploy:8cb1dbe1945284e632f6d387aba786639f9ae437 -->
