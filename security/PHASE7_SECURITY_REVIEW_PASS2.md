# Phase 7 — Adversarial Security Review, Pass 2 (T8.1.2)

**Date:** 2026-08-06
**Scope:** identical to pass 1 — `deploy 8cb1dbe..5aa8524`, `frontend 3a57718..d6adec7`,
`backend 583511d..9d9ea6b`.

## Independence

Pass 2 was run by a separate agent on a different model (Sonnet 5), explicitly instructed not to
read `PHASE7_SECURITY_REVIEW_PASS1.md` or the T8.1.1 row in `TASKS.md`, and given the phase goals
and an attack-area brief rather than any pass-1 conclusion. Its findings below are its own.

The 5.6 precedent's lesson was carried into the brief: target defects that are **green everywhere
and still wrong**. That framing paid off — pass 2's strongest finding (§2) is exactly that class,
and pass 1 missed it.

Reconciliation of the two passes is in the last section. It is not decoration: the passes
**disagree** on one item, and pass 2 found a second defect inside a file pass 1 had already
flagged.

---

## Pass 2 findings

### P2-1 — CRITICAL · the exam-image proxy cannot work, for two independent reasons

`haisir-frontend/src/app/images/questions/[...path]/route.ts:11-39`

**Defect A — self-referential proxy loop.** `NEXT_PUBLIC_BACKEND_URL` is the public gateway
domain, not an internal address (`Dockerfile:9` → `https://haisir.in`; `Jenkinsfile:5` →
`https://staging.haisir.in`; `src/config/env.ts` describes it as the URL "used by the Next.js
**client**"). No APISIX route exists for `/images/*`, so this server-side fetch lands on
`99-catch-all.json` (priority 0, `/*`, `secured-anonymous`) and is routed straight back to
`frontend:3000` — into the same handler. Every question-image request hairpins: 502/504 once the
catch-all's 6 s upstream timeout trips, or amplified frontend↔gateway load.

**Defect B — authentication is never forwarded.** *(new in pass 2; pass 1 missed this)* Even
pointed at the real backend, `GET /images/questions/{filename}`
(`haisir-backend/src/api/routes/images.py:25-27`) depends on `current_active_user`
(`src/auth/user.py:219-263`), which requires an `Authorization: Bearer` JWT via `HTTPBearer` **and**
an `X-Current-Role` header (400 if absent). The route forwards only the browser's raw `cookie`
header — never `Authorization`, never `X-Current-Role`. The backend's own
`test_get_question_image_requires_authentication` confirms unauthenticated calls get 401/403. **This
call can never succeed against the real backend as written**, independent of Defect A.

Both invisible to the suite because every unit test mocks `fetch()`.

**Fix:** point the server-side fetch at the internal address used everywhere else in the compose
network (`http://backend:8000`, matching APISIX's own upstream), and either forward a real bearer
token + `X-Current-Role`, or add a dedicated APISIX route for `/images/*` that injects the JWT the
way every other authenticated path does, with this handler as a thin pass-through. Add one
integration test through the real topology, not a mocked `fetch`.

### P2-2 — HIGH · false assurance · the WAF regression gate is wired into no CI pipeline

`common/scripts/tests/waf-harness.sh`, `gateway-docker/Jenkinsfile`, `gateway-docker/VERSIONS.md:311-317`

`waf-harness.sh` is a genuinely non-vacuous check: it spins up a throwaway APISIX+etcd+upstream
stack, confirms via the Admin API that `coraza-filter` actually registered, then asserts concrete
403s on XSS/SQLi/LFI probes. `VERSIONS.md:316` says it is "worth gating future gateway image
changes on."

**It is not gated.** No `Jenkinsfile*` in the repo invokes it. `gateway-docker/Jenkinsfile`'s
"Verify Image" stage runs only `docker run --rm … apisix version` — the same shallow check that let
the original defect through. `Jenkinsfile.integration-dast`'s runner globs
`find common/scripts/tests -name "*-test-*.sh"`, which does not match `waf-harness.sh` (no `-test-`
in the filename), so it is not picked up incidentally either.

Net effect: the pipeline can build, static-scan, Trivy-scan, SBOM and **push a gateway image whose
WAF never filters a single request** — the exact incident this phase was convened to fix — with
every stage green.

**Fix:** add a stage in `gateway-docker/Jenkinsfile` after "Build Gateway Image" running
`bash common/scripts/tests/waf-harness.sh ${DOCKER_IMAGE}:${TAG}`, failing the build non-zero.

### P2-3 — MEDIUM · image upload buffers the whole file before the size check

`haisir-backend/src/api/routes/exam.py:255-262` — `await file.read()` materialises the body before
the 5 MB check, instead of the streaming `read_upload_capped` helper used by sibling endpoints.
Bounded by `RequestBodySizeLimitMiddleware` and the `require_instructor()` gate, so worst case is
~50 MB buffered per concurrent authenticated upload. Not unauthenticated-exploitable; inconsistent
with the pattern one file away.

### P2-4 — LOW · the 942200 exclusion is plugin-config-wide, not route-scoped

`common/plugin_configs/{01,02,04}-secured-*.json` — `SecRuleUpdateTargetById 942200
!REQUEST_HEADERS:Referer` disables the rule on `Referer` for **every route sharing that
plugin_config**, not just the diagnosed flow. Well-evidenced in the comments (live 403s traced to
Referer poisoning), and APISIX's plugin_config model offers no finer scoping without per-route
duplication — closer to a structural constraint than an oversight. Flagged only because the
comment's "narrows only the one known-safe query param and the Referer header" understates the real
blast radius.

### P2-5 — LOW · gateway builder base image is an unfamiliar registry

`gateway-docker/Dockerfile:42` — `reg.mini.dev/go:${GO_VERSION}-dev` replaces official
`golang:${GO_VERSION}-bookworm`. Floating tag, no digest pin. Commit history indicates a deliberate,
security-motivated swap to a minimal/hardened image; noted as a new supply-chain dependency whose
provenance is worth confirming independently.

---

## Pass 2 — checked and clean

Recorded verbatim in substance so the two passes' clean lists can be compared:

- **CSP** (`src/proxy.ts`) — header set on every code path (public, onboarding redirect, normal),
  enforced in prod vs Report-Only in dev, `strict-dynamic` + per-request nonce correct,
  `style-src-attr 'unsafe-inline'` narrowly scoped with an explicit residual-risk statement.
- **CSP report collector** — true streaming byte cap (chunked bypass does not work), never 5xxs,
  `JSON.stringify`'d output (no log injection). The matching WAF relaxation is real: body inspection
  only, exact-match URI, strictly tighter than the CRS default for that path.
- **APISIX admin surface** — dashboard and admin CORS disabled; `{{DOCKER_NETWORK_SUBNET}}` removed
  from `allow_admin`; etcd TLS verify true; crowdsec bouncer TLS verify true + https; OIDC
  `ssl_verify: true`. All flipped from insecure defaults.
- **Tailscale ACLs** — dev tags no longer hold blanket `*:*` to staging/ci/compute; prod SSH split
  into its own `tag:prod-ssh`.
- **JWT audience validation** — `verify_aud` flipped `False → True`; previously unchecked.
- **Vendored tree** — the five documented file-level patches are functionally real (verified by
  direct grep of `SetProperty`, the `init()`/`main()` split, `wasip1-bigstack.json` wiring). Manual
  scan of the ~29k lines for AWS keys / PEM blocks / JWTs found nothing.
- **`haitu.py` / `review_chat` ownership** — `_load_owned_completed_session` called on every path in
  all three endpoints **including cache hits**, with a comment showing the authors reasoned through
  IDOR-via-shared-cache. `review_chat_repository.py` is parameterized SQLAlchemy Core throughout —
  no string-built SQL.
- **Route priority ordering** — the priority-30 haitu routes correctly beat the `/api/haitu/*`
  wildcard (20); the new GET thread-read route at 20 correctly beats the generic `/api/*` read route
  (10). No collision across the full route set.

## Pass 2 — not covered

No running stack or network, so P2-1 and P2-2 are traced statically. Did not deep-review the
vendored tree beyond provenance/patches/secret-grep; `admin_extraction.py`, `parent_extraction.py`,
`exam_session.py`; the e2e CSP soak specs; `01-realm.json` beyond the `.secrets.baseline` entry it
triggered; or the `other/services/*` configs beyond compose/tailscale.

---

## Reconciliation of pass 1 and pass 2

### Corroborated by both passes independently

| Item | Pass 1 | Pass 2 |
|---|---|---|
| Image proxy points at the public gateway, not the backend | F2 (HIGH) | P2-1 Defect A (CRITICAL) |
| `exam.py` upload buffers before its size check | F4 (MEDIUM) | P2-3 (MEDIUM) |
| Gateway builder on an unpinned third-party registry | F5 (MEDIUM) | P2-5 (LOW) |

Two independent reviews converging on the image proxy makes it the highest-confidence defect of the
phase. The severity split on the builder registry is a judgement difference, not a factual one.

### Found only by pass 2 — pass 1 missed these

- **P2-1 Defect B** — auth is never forwarded to the backend image endpoint. Pass 1 traced the URL
  defect and stopped there, never checking whether the request would authenticate even if the URL
  were right. Material: it means fixing the URL alone does not fix the feature.
- **P2-2** — `waf-harness.sh` gated by nothing. Pass 1 did not examine CI wiring at all. This is the
  single best finding of either pass, and squarely the 5.6 defect class.
- **P2-4** — the 942200 exclusion's real blast radius.

### Found only by pass 1 — pass 2 did not reach these

F3 (traversal guard `path.includes("..")` catches only an exactly-`..` segment), F6 (WebP accepted
on upload, rejected by the frontend proxy), F7 (extraction routes' 50 MB cap unreachable under the
10 MB config default), F8 (`worker_processes` doc drift), F9 (CSRF on a GET). None were contradicted
by pass 2; they were simply outside where it looked.

Plus the two vendored-tree defects that prompted this fix (§ below), which pass 2 examined the same
tree without noticing — its vendored-tree review confirmed the five patches are real but took
`VENDORED.md`'s own framing at face value.

### The passes disagree — pass 2 is wrong

**The CVE-2026-21876 regression test.** Pass 2 lists
`common/scripts/tests/18-test-cve-2026-21876-multipart.sh` under *checked and clean*: "a genuine
gate … distinguishes a real pass (403/429) from a silent regression (401)". Pass 1 filed it as
false assurance (F1). Re-verified after the disagreement surfaced, and pass 1 is correct — with two
facts neither pass had at first:

1. **The probe does not hit the plugin_config the script claims.** Its comment names
   `04-secured-api-upload.json` as "the exposed surface", but the probe URI
   `/api/admin/topics/…/extraction-jobs` (POST) matches only `05-api-write.json` — priority 10,
   `uri: /api/*`, `plugin_config_id: secured-api`. Enumerated the full POST-capable `/api/*` route
   set to confirm nothing outranks it. So it exercises `03-secured-api.json`'s directives, not the
   upload route's.
2. **`03-secured-api.json`'s `ua-restriction` denylists `curl*` and rejects with `403`** — the exact
   code the test asserts as success — with `bypass_missing: false`. The script sends bare `curl`
   with no `-A`/`User-Agent` override, unlike `config.sh`'s own `get_access_token`, which sets a
   Mozilla UA precisely for this reason.

So the probe returns 403 from `ua-restriction` before rule 922110's verdict is ever relevant, and
would do so against **any** CRS version. Pass 2 checked that the test discriminates a 401
(WAF-priority regression) and stopped; it did not consider that 403 is reachable from a non-WAF
plugin on the same route. Pass 2's related observation — that the script *is* picked up by the
integration-dast glob — makes this worse rather than better: it is actively producing a green CI
signal for a check that cannot fail.

**The remediation itself remains real** — CRS 4.25.1, Coraza v3.7.0, rule 922110 present with the
fixed charset-allowlist regex. Only the test is worthless.

### Pass 2 corrected pass 1

Pass 1 was uneasy about `.secrets.baseline` excluding
`gateway-docker/coraza-proxy-wasm/.*` from scanning. Pass 2 established that this is a **pre-commit
convenience only** — CI's Gitleaks stage scans the tree, `.gitleaks.toml` carries no path exclusion
for it — and independently grepped the ~29k lines for keys, PEM blocks and JWTs, finding nothing.
Dropped; not a finding. (The new `01-realm.json` baseline entry is the `passwordPolicy` string, a
detect-secrets keyword false positive, correctly baselined.)

---

## Fixed under this task

Two pass-1 vendored-tree findings were fixed immediately rather than deferred to T8.1.3, at the
user's direction, because T8.2.1 (the re-vendor runbook) is scheduled to be written *from* the
document they corrupt.

**1. `gateway-docker/coraza-proxy-wasm/VENDORED.md` contradicted itself.** Its "Status" section
claimed the tree was "unmodified upstream source" and that the APISIX patch "has not yet been
applied in-tree — that lands in a follow-up change, after which
`gateway-docker/coraza/apply-apisix-patch.sh` and the Dockerfile's `git clone` step are removed."
All three had already happened (verified: patch markers present in `wasmplugin/plugin.go`, the
`init()`/empty-`main()` shape in `main.go`, `gateway-docker/coraza/` deleted). Two sections later the
same file listed those patches as load-bearing. Rewritten, with the correction dated and explained
in place.

**2. The re-vendor gate had a blind spot exactly where the phase's security floors live.**
`VENDORED.md`'s "must be carried forward on a re-vendor" table listed five *file-level* patches and
omitted five *version* divergences documented only in the Dockerfile's header comment. The
Dockerfile's verification `RUN` asserted none of them, and `waf-harness.sh`'s four generic
XSS/SQLi/LFI probes are all blocked fine by CRS 4.14.0. A re-vendor onto upstream `0.6.0` following
`VENDORED.md` faithfully would therefore have restored **CRS 4.14.0 (CVE-2026-21876 back, CVSS 9.3)**
and **Coraza v3.3.3 (the pre-3.5.0 engine whose broken regex collection keys are the root cause of
the exclusion treadmill)** — while passing the Dockerfile gate and reporting 4/4 on the harness.
Green everywhere, both headline floors silently reverted.

Fixed by adding a second assertion `RUN` to `gateway-docker/Dockerfile` covering all five floors
(Coraza v3.7.0, go-re2 v1.12.0, nottinygc absent, CRS `crs_setup_version=4251`,
`coraza.rule.no_regex_multiline`), each with an error message naming the consequence; and by adding
a "Version floors" table plus a "Verifying a re-vendor" section to `VENDORED.md` that states plainly
what the harness does and does not prove, and that it is not currently CI-wired (P2-2).

The CRS anchor is on `wasmplugin/rules/crs-setup.conf.example`, which `wasmplugin/fs.go:14`
(`//go:embed rules`) compiles into the binary — so it tracks the ruleset that actually ships, not a
stray doc file.

**Verified both directions.** All five assertions pass against the current tree. Against a scratch
copy mutated to simulate the exact regression (`coraza v3.7.0 → v3.3.3`,
`crs_setup_version 4251 → 4140`, `nottinygc` re-added to `go.mod`), 3/3 of the applicable assertions
fired. Left uncommitted in `haisir-deploy` per this repo's norm for WAF/gateway edits.

## Remaining for T8.1.3

Every other finding from both passes: F1 (the CVE test — resolve the disagreement above in favour of
pass 1), F3, F6–F9, and P2-1 through P2-5. P2-1 and P2-2 should be treated as the priority pair —
one is a user-facing feature that cannot work, the other is a pipeline that can ship a
non-functioning WAF.
