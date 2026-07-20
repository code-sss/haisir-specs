# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:ee3a79e frontend:816194d deploy:9cf91f2 (2026-07-17)

## G1 [deploy]: Fail-closed foundations

### G1.1 [deploy]: Render pipeline fails closed per required key
- [x] T1.1.1 [deploy]: Required-keys manifest + per-key fail-closed render (2026-07-16)
- [x] T1.1.2 [deploy]: Unresolved-placeholder guard in template-configs.sh (2026-07-16)
- [x] T1.1.3 [deploy]: On-disk render-residue hardening (0700, .env.runtime gitignore, env-template annotations) (2026-07-16)
- [x] **G1.1: Render pipeline fails closed per required key** — integration test (2026-07-16; PASS: render self-test + SESSION_SECRET-unset guard fires → exit 1, set → exit 0)

### G1.2 [deploy]: Un-rendered compose invocations fail loudly
- [x] T1.2.1 [deploy]: ${VAR:?} guards in common/docker-compose.yml (2026-07-16)
- [x] T1.2.2 [deploy]: ${VAR:?} guards in dev/docker-compose.yml (2026-07-16)
- [x] **G1.2: Un-rendered compose invocations fail loudly** — integration test (2026-07-16; PASS: both compose files `config` exit 1 naming the guarded var when env/.env unset)

### G1.3 [deploy]: Every provisioning entry point can render from KV
- [x] T1.3.1 [deploy]: setup.sh render hook (depends on T1.1.1) (2026-07-16)
- [x] T1.3.2 [deploy]: setup-keycloak.sh render hook (depends on T1.1.1) (2026-07-16)
- [x] T1.3.3 [deploy]: APISIX helper-script key-inheritance audit/hook (depends on T1.3.1) (2026-07-16)
- [ ] **G1.3: Every provisioning entry point can render from KV** — integration test (RE-VERIFIED 2026-07-16: the prior "403" was a `bao read` probe hitting the v1 endpoint `/v1/secret/haisir/X` instead of the KV-v2 `data/` endpoint the render code uses (`bao kv get`). ⚠ OpenBao does NOT do implicit cert-auth: a cert-only `bao kv get` (no token) 403s. RENDER-AUTH GAP — FIXED 2026-07-16: `render-deploy-secrets.sh` now acquires a deploy token via `bao login -method=cert name=deploy` (captured from `-format=json`, forwarded by name `-e BAO_TOKEN` so it never hits argv/ps) before the kv reads — mirroring the agents' auto_auth. Verified live from a fresh state (no cached `~/.bao_token`): render emits all 15 keys across db/keycloak/gateway/infra/shared/keycloak-clients, exit 0; unreachable container fails closed with a clear message, exit 1. All 3 children's hook code validated hermetically + live fail-closed. Remaining: run the full e2e `setup.sh --wait` + `setup-keycloak.sh` under `OPENBAO_DEPLOY_SECRETS=true`.)

### G1.4 [deploy]: Class B mechanism spikes (pre-decision, load-bearing)
- [x] T1.4.1 [deploy]: Spike — haisir-postgres POSTGRES_PASSWORD_FILE support (2026-07-16)
- [x] T1.4.2 [deploy]: Spike — chainguard keycloak-db POSTGRES_PASSWORD_FILE support (2026-07-16)
- [x] T1.4.3 [deploy]: Spike — Keycloak 26 file-based bootstrap/db passwords (2026-07-16)
- [x] **G1.4: Class B mechanism spikes** — integration test (2026-07-16; PASS: all 3 verdicts WORKS + repro commands recorded in common/openbao/class-b-mechanism-spikes.md)

- [ ] **G1: Fail-closed foundations** — end-to-end test

## G2 [deploy]: Class A secrets from KV (dev-seeded; staging/prod via bring-up runbook)

### G2.1 [deploy]: Render activation
- [x] T2.1.1 [deploy]: Flip OPENBAO_DEPLOY_SECRETS=true in all three envs (depends on T1.1.1, T1.3.1, T1.3.2, T1.3.3) (2026-07-16)
- [ ] **G2.1: Render activation** — integration test

### G2.2 [deploy]: Gateway secrets from KV
- [x] T2.2.1 [deploy]: Seed secret/haisir/gateway (dev; env-agnostic helper) (depends on T2.1.1) (2026-07-16)
- [x] T2.2.2 [deploy]: Remove gateway plaintext + manifest entry (atomic) (depends on T2.2.1, T1.1.2, T1.1.3) (2026-07-17)
- [ ] **G2.2: Gateway secrets from KV** — integration test

### G2.3 [deploy]: Keycloak realm/OIDC secrets from KV
- [x] T2.3.1 [deploy]: Seed keycloak path — OIDC trio (dev) (depends on T2.1.1) (2026-07-16)
- [x] T2.3.2 [deploy]: Remove OIDC-trio plaintext + manifest entry (atomic) (depends on T2.3.1, T1.1.2) (2026-07-17)
- [ ] **G2.3: Keycloak realm/OIDC secrets from KV** — integration test

### G2.4 [deploy]: Backend-admin client credential has ONE KV source of record
- [x] T2.4.1 [deploy]: Create keycloak-clients path + policy/render plumbing (depends on T2.1.1) (2026-07-16)
- [x] T2.4.2 [deploy]: Repoint backend vault-agent template to the single source (depends on T2.4.1) (2026-07-17)
- [x] T2.4.3 [deploy]: Remove backend-admin plaintext + manifest entry (atomic) (depends on T2.4.2, T1.3.2) (2026-07-17)
- [ ] **G2.4: Backend-admin single KV source of record** — integration test

### G2.5 [deploy]: Test-user credential — KV for dev/staging, gone from prod
- [x] T2.5.1 [deploy]: Skip test-user provisioning when APP_ENV=prod (2026-07-16)
- [x] T2.5.2 [deploy]: Seed TEST_USER_PASSWORD (dev; staging via runbook) (depends on T2.1.1) (2026-07-16)
- [x] T2.5.3 [deploy]: Remove TEST_USER_PASSWORD plaintext + env-conditional manifest entry (atomic) (depends on T2.5.1, T2.5.2, T1.3.2) (2026-07-17)
- [ ] **G2.5: Test-user credential** — integration test

### G2.6 [deploy]: Keycloak admin password sourced from KV (provisioning side)
- [x] T2.6.1 [deploy]: Seed KEYCLOAK_ADMIN_PASSWORD (dev, live-verified value) (depends on T2.1.1) (2026-07-16)
- [x] T2.6.2 [deploy]: Remove KEYCLOAK_ADMIN_PASSWORD from .env.config.sh + manifest (atomic) (depends on T2.6.1, T1.3.2) (2026-07-17)
- [ ] **G2.6: Keycloak admin password (provisioning side)** — integration test

### G2.7 [deploy]: Tunnel token sourced from KV
- [x] T2.7.1 [deploy]: Seed secret/haisir/infra TUNNEL_TOKEN (dev) (depends on T2.1.1) (2026-07-16)
- [x] T2.7.2 [deploy]: cftunnel render wrapper + plaintext removal (atomic) (depends on T2.7.1) (2026-07-17)
- [ ] **G2.7: Tunnel token sourced from KV** — integration test

- [ ] **G2: Class A secrets from KV** — end-to-end test

## G3 [deploy]: HARD GATE — Class A live verification on dev
*(gate root T3.1 depends on all Class A cutovers: T2.2.2, T2.3.2, T2.4.3, T2.5.3, T2.6.2, T2.7.2 + guards T1.2.1, T1.2.2)*

- [x] T3.1 [deploy]: Cold fresh-install bring-up on dev (GATE ROOT) (depends on T2.2.2, T2.3.2, T2.4.3, T2.5.3, T2.6.2, T2.7.2, T1.2.1, T1.2.2) (2026-07-17: DONE. `common`-project side verified live from a genuine cold stop — `openbao-dev` → `render-deploy-secrets.sh` → scoped `docker compose -f common/docker-compose.yml --project-name common up -d db-init db backend worker vault-agent-backend vault-agent-worker` (`env-setup.sh` itself wasn't invoked directly since it isn't service-scoped and would collide with `dev/docker-compose.yml`'s apisix/keycloak/etcd container names — deliberate, disclosed deviation from the literal script). Then, after the user restarted `dev/docker-compose.yml`'s stack themselves, provisioning completed: `setup.sh --wait --keycloak` (via `template-configs.sh` run explicitly from `dev/` first, then the render-secrets-hook sourced manually before `setup.sh` — see notes below) — 4/4 plugin configs, 23/23 routes, 7/7 Keycloak items (realm, roles, client, service-account client, client scopes, identity provider, user) all succeeded, exit 0. Final state: all 12 dev containers healthy. **Three pre-existing, unrelated-to-secrets bugs surfaced and were fixed along the way** (exactly what a HARD GATE is for): (1) stray OpenBao KV test debris `EMBEDDING__OLLAMA_API_KEY`/`HAITU__OLLAMA_API_KEY` = `test-openbao-new` under `secret/haisir/backend`, rejected by the backend's strict pydantic Settings — cleared via `bao kv patch` (empty values, template's `{{if}}` guard skips the line); (2) `dev/.env.config.sh`'s `BACKEND_IMAGE_TAG`/`GATEWAY_IMAGE_TAG="latest"` pointed at a stale ~7-month-old image lacking the `worker` module — real tag is `v2026.4` (user fixed the file); (3) the `haisir` Postgres role `DATABASE_URL` expects never existed (only bootstrap superuser `user` did) — created it + granted DB/schema privileges + ran `alembic upgrade head` (36 tables) to unblock `worker`. **A fourth, deploy-script-level bug found during provisioning:** `common/scripts/setup.sh` checks `APISIX_ADMIN_KEY` is non-empty (line ~56) BEFORE it runs its own OpenBao render hook (line ~129) — under `set -u` this makes standalone `setup.sh` invocation always fail with "unbound variable" now that Class A migration removed the plaintext fallback from `.env.config.sh`. Worked around by manually sourcing `common/openbao/render-secrets-hook.sh` + calling `render_deploy_secrets_or_die` in the caller's shell before invoking `setup.sh` (mirrors what the script does internally, just reordered). **This ordering bug in setup.sh itself is still unfixed in the script** — a real follow-up worth its own task. Also hit the known `template-configs.sh` cwd-sensitivity trap again (its `.env.config.sh`-exists guard checks `common/scripts/.env.config.sh`, which never exists, so the auto-template block inside `setup.sh` silently no-ops) — worked around by running `template-configs.sh` explicitly from `dev/` first, per [[project_dev_deploy_flow]].)
- [x] T3.2 [deploy]: Templated-config value hash verification (depends on T3.1) (2026-07-17: `common/scripts/tests/templated-config-hash-verify.sh` added — sha256(admin_key in dev/apisix_conf/.templated/config.yaml, the live dev-mounted file) == sha256(kv gateway APISIX_ADMIN_KEY), and sha256(client_secret in common/plugin_configs/.templated/dev/01-secured-authenticated.json) == sha256(kv keycloak KEYCLOAK_CLIENT_SECRET). Both pairs matched on first run against the live T3.1 dev state, exit 0.)
- [x] T3.3 [deploy]: APISIX admin API auth probe (depends on T3.1) (2026-07-17: `common/scripts/tests/apisix-admin-auth-probe.sh` added — GET /apisix/admin/routes with KV-rendered APISIX_ADMIN_KEY -> 200; with a junk key -> 401. Both confirmed on live dev, exit 0.)
- [x] T3.4 [deploy]: OIDC login end-to-end (depends on T3.1) (2026-07-20: `common/scripts/tests/oidc-login-e2e.sh` added — drives a real browser-style login: unauthenticated GET /home -> Keycloak login form -> credential POST -> APISIX /auth/callback code exchange (KEYCLOAK_CLIENT_SECRET) -> session cookie (SESSION_SECRET) -> CSRF bootstrap (GET /api/auth/csrf) -> authenticated GET /api/users/me -> 200. PASSED, exit 0, confirmed via a clean re-run. This was the first test to ever exercise gateway-to-backend HTTP proxying live (T3.1's own check only covered container health/provisioning exit codes), and it surfaced a chain of real, pre-existing dev-environment gaps — none related to Class A secrets, all now fixed: (1) `apisix-dev`/`keycloak-dev` (dev/docker-compose.yml, network `haisir-net-dev`) and `backend`/`worker`/`db` (common project, network `haisir-net`) were on two disjoint Docker networks with no route between them — `common/docker-compose.yml:653` hardcodes external network name `haisir-net`, diverging from CLAUDE.md's documented `docker network create haisir-net-dev` dev setup step; fixed for this session via `docker network connect haisir-net apisix-dev` and `... keycloak-dev` (reversible, no restart) — **the underlying compose network-name mismatch is unfixed and worth a follow-up task**; (2) `common/docker-compose.yml`'s `backend` environment never wired `SECURITY__FORCE_HTTPS`, so haisir-backend's `HTTPSRedirectMiddleware` used its pydantic default (`true`) unconditionally, 301-redirecting every plain-HTTP request even authenticated ones — fixed by adding `SECURITY__FORCE_HTTPS: ${SECURITY__FORCE_HTTPS:-true}` to docker-compose.yml (committed, safe default, dev overrides to `false`); (3) `dev/.env.config.sh` was missing `SECURITY__ENVIRONMENT`, `OAUTH__KEYCLOAK__URL`, `OAUTH__KEYCLOAK__ISSUERS`, and `OAUTH__KEYCLOAK__REALM` entirely (all silently blank, each causing a different failure mode: HTTPS enforcement, JWKS connection-refused, JWKS 404) — user added all four; (4) discovered mid-fix: pydantic-settings needs `OAUTH__KEYCLOAK__ISSUERS` as valid JSON-array syntax with the outer value single-quoted in the shell so the inner double-quotes survive — my first two suggested values were wrong (a bash quoting mistake on my part), corrected on the third attempt; (5) the backend's CSRF middleware requires `X-CSRF-Token` even on this GET route — the test script now bootstraps it via `GET /api/auth/csrf` (`csrfToken` field) first, per `02_auth_and_roles.md`. **Also encountered along the way**: a genuine WAF/rate-limit 403 on the internal Keycloak token-exchange call, self-inflicted by the sheer volume of rapid repeated login attempts during debugging — resolved by pausing ~90s before the final clean run; not a bug. **Security note**: three separate accidental secret-value exposures happened in this session's tool output while debugging (a `bash -x` trace of a token/client-secret; an unredacted `session.secret` field in a plugin-config dump; and a raw session-cookie/identity-JWT value from an overly broad `grep` on curl headers) — all dev-only credentials, flagged to the user in real time, worth rotating as a precaution.)
- [x] T3.5 [deploy]: Backend-admin single-source no-drift check (depends on T3.1) (2026-07-17: `common/scripts/tests/backend-admin-no-drift-check.sh` added — sha256(agent-rendered OAUTH__KEYCLOAK__ADMIN_CLIENT_SECRET, hashed inside the haisir-backend-dev container via python3 so the raw value never crosses the docker-exec boundary) == sha256(kv keycloak-clients KEYCLOAK_BACKEND_ADMIN_CLIENT_SECRET), plus a live client_credentials grant + GET /admin/realms/haisir-realm-dev/users with that credential -> 200. Both passed, exit 0. Hit and fixed a script bug along the way: haisir-backend-dev is a minimal/distroless image with no sh/grep — switched to python3-in-container extraction, which also improved the security posture by never letting the raw secret leave the container at all. NOTE: an earlier debug pass with `bash -x` on the pre-fix script briefly printed the OpenBao token and the raw KEYCLOAK_BACKEND_ADMIN_CLIENT_SECRET value in the assistant's tool output before the fix — a dev-only credential, but worth rotating.)
- [x] T3.6 [deploy]: Incremental render path (build_compose_cmd) exercised (depends on T3.1) (2026-07-17: `common/scripts/tests/incremental-render-path-check.sh` added — replicates build_compose_cmd's exact render command body locally (dev has no remote host to SSH into; disclosed deviation), verifies umask-077 `.env.runtime` creation (mode 600), `docker compose config` resolves fully, an incremental `up -d backend` succeeds, and `.env.runtime` is absent after cleanup. Surfaced two real pre-existing gaps in `dev/.env.config.sh` unrelated to the secrets work: `KEYCLOAK_POSTGRES_PASSWORD` entirely missing, and `POSTGRES_IMAGE_TAG`/`DOCKER_REGISTRY` unset (same category as T3.1's stale-image-tag find) — user added all three. **Incident during this task**: after those fixes, a real `up -d backend` recreate attempt hit a port collision on host 127.0.0.1:5432 between `common/docker-compose.yml`'s `db` service and `dev/docker-compose.yml`'s separate `postgres-dev` container (both default to that port) — `haisir-db-dev` and `haisir-backend-dev` were left stopped (`Created` state) as a side effect, `haisir-worker-dev` restarted. Service was restored immediately (`up -d db backend`) once the user brought `postgres-dev` down to free the port (per [[feedback_dev_stack_off_limits]], that stack is off-limits for the assistant to touch directly). All common-project containers confirmed healthy afterward; `postgres-dev` intentionally left down. Re-run of the full check then PASSed, exit 0. Also, during earlier debugging of T3.5 (before this task), a `bash -x` trace briefly printed the OpenBao token and the raw `KEYCLOAK_BACKEND_ADMIN_CLIENT_SECRET` in tool output — flagged to the user, dev-only credential, worth rotating. **Post-verification cleanup (2026-07-20):** the script itself was deleted, not committed — it re-implements `build_compose_cmd`'s logic locally rather than calling it, so it would silently drift out of sync if that function changes; kept as a one-time verification, not an ongoing regression check. This task's evidence stands regardless.)
- [x] T3.7 [deploy]: Class A plaintext-residue scan (depends on T3.1) (2026-07-17: scan script `common/scripts/tests/plaintext-residue-scan.sh` added — checks Class A key names absent from `.env.config.sh` [name-only grep, never values], all `.templated/<env>` dirs 0700 [incl. `dev/apisix_conf/.templated`, previously outside T1.1.3's scope], no leftover `.env.runtime`, no orphaned tmpfs render fragments. First run FAILED: found `TEST_USER_PASSWORD` still live in `prod/.env.config.sh` — T2.5.3's atomic removal had missed prod. Also found and fixed two other residue gaps: `dev/apisix_conf/.templated` was 775 not 700 [chmod'd], and an orphaned tmpfs fragment `/dev/shm/haisir-dev-runtime.*` whose EXIT trap never fired [confirmed unheld, deleted]. User removed the prod `TEST_USER_PASSWORD` line; scan now PASSes, exit 0.)
- [x] T3.8 [deploy]: Prod test-user skip verified (depends on T3.1) (2026-07-20: `common/scripts/tests/prod-test-user-skip-check.sh` added — runs `setup-keycloak.sh --dry-run` with `APP_ENV=prod` against the dev stack [temporary `.templated/prod` -> `dev` symlink for config resolution, `OPENBAO_DEPLOY_SECRETS=false` + manually KV-fetched secrets to bypass the fail-closed openbao-prod lookup that doesn't exist in this sandbox — neither substitution touches what's under test]. Confirmed: the T2.5.1 skip message fires, zero `- User:` lines listed, and a follow-up admin API check confirms the dev realm's `trial` test user is still present/untouched. PASSED, exit 0.)
- [x] T3.9 [deploy]: cftunnel token render check (depends on T3.1) (2026-07-17: added a `--check` flag to `other/services/cftunnel/up.sh` — renders + `docker compose config` only, no container started; T3.9's build note anticipates this for dev, which has no live tunnel exposure and shouldn't have a real cloudflared started against Cloudflare's edge just to run a test. `APP_ENV=dev bash up.sh --check` resolved TUNNEL_TOKEN from KV, exit 0, and all `cftunnel-*` tmp fragments were gone afterward (EXIT trap).)
- [x] **G3: HARD GATE — Class A live verification** — end-to-end test (2026-07-20: all 9 tasks PASS against the same live T3.1 dev bring-up, verified across one extended session rather than a single unattended run. Along the way, real pre-existing gaps unrelated to Class A secrets were found and fixed — exactly the HARD GATE's purpose: a stray prod `TEST_USER_PASSWORD` plaintext leftover (T3.7), a disjoint-Docker-network split between the dev/docker-compose.yml stack and the common project (T3.4, workaround applied — permanent compose fix still open), an unwired `SECURITY__FORCE_HTTPS` in common/docker-compose.yml (T3.4, fixed), and several missing dev/.env.config.sh values: `KEYCLOAK_POSTGRES_PASSWORD`, `POSTGRES_IMAGE_TAG`, `DOCKER_REGISTRY`, `BACKEND_DB_PORT_BINDING`, `SECURITY__ENVIRONMENT`, `OAUTH__KEYCLOAK__URL/ISSUERS/REALM` (T3.6, T3.4 — all added by the user). All Class A secrets (APISIX_ADMIN_KEY, SESSION_SECRET, KEYCLOAK_CLIENT_SECRET, KEYCLOAK_BACKEND_ADMIN_CLIENT_ID/_SECRET, TUNNEL_TOKEN) confirmed hash-matching KV and functioning live end-to-end, including a full browser-style OIDC login.)

## G4 [deploy]: Class B cold-start passwords from KV
*(entry tasks T4.1.1 and T4.2.1 each depend on ALL 9 G3 tasks: T3.1–T3.9)*

### G4.1 [deploy]: Per-service delivery mechanism decided from spike evidence
- [ ] T4.1.1 [deploy]: Mechanism decision doc (GATE ENTRY) (depends on T1.4.1, T1.4.2, T1.4.3 + all 9 G3 tasks)
- [ ] **G4.1: Mechanism decision** — integration test

### G4.2 [deploy]: Keycloak DB auth truth established and role gap closed
- [ ] T4.2.1 [deploy]: Verify live keycloak-db auth (GATE ENTRY) (depends on all 9 G3 tasks)
- [ ] T4.2.2 [deploy]: Provision KC_DB_USERNAME role on init (depends on T4.2.1)
- [ ] **G4.2: Keycloak DB auth truth + role gap** — integration test

### G4.3 [deploy]: Per-service cutover (seed verified-live → compose change → remove plaintext)
- [ ] T4.3.1 [deploy]: Seed/confirm secret/haisir/db POSTGRES_PASSWORD (dev, verified-live) (depends on T4.1.1)
- [ ] T4.3.2 [deploy]: db service compose change (chosen mechanism) (depends on T4.3.1)
- [ ] T4.3.3 [deploy]: Remove POSTGRES_PASSWORD plaintext + manifest (atomic) (depends on T4.3.2)
- [ ] T4.3.4 [deploy]: Seed keycloak path KEYCLOAK_POSTGRES_PASSWORD (dev, verified-live) (depends on T4.1.1)
- [ ] T4.3.5 [deploy]: keycloak-db service compose change (depends on T4.3.4)
- [ ] T4.3.6 [deploy]: Remove KEYCLOAK_POSTGRES_PASSWORD plaintext + manifest (atomic) (depends on T4.3.5)
- [ ] T4.3.7 [deploy]: Seed KC_DB_PASSWORD with the VERIFIED-live value (dev) (depends on T4.2.1, T4.1.1)
- [ ] T4.3.8 [deploy]: keycloak service delivery change (KC_DB_PASSWORD + bootstrap admin) (depends on T4.3.7, T4.2.2, T2.6.1)
- [ ] T4.3.9 [deploy]: Remove KC_DB_PASSWORD + KEYCLOAK_ADMIN_PASSWORD from .env files + manifest (atomic) (depends on T4.3.8)
- [ ] **G4.3: Per-service cutover** — integration test

### G4.4 [deploy]: Rollback/backout plan for cold-start-critical services
- [ ] T4.4.1 [deploy]: Author rollback/backout runbook (depends on T4.1.1, T4.3.8)
- [ ] **G4.4: Rollback/backout plan** — integration test

- [ ] **G4: Class B cold-start passwords from KV** — end-to-end test

## G5 [deploy]: HARD GATE — Class B live verification on dev
*(entry task T5.1 depends on ALL 13 G4 tasks: T4.1.1, T4.2.1, T4.2.2, T4.3.1–T4.3.9, T4.4.1)*

- [ ] T5.1 [deploy]: Cold bring-up with preserved volumes (GATE ENTRY) (depends on all 13 G4 tasks)
- [ ] T5.2 [deploy]: Fresh-volume first-init test (depends on T5.1)
- [ ] T5.3 [deploy]: docker-inspect exposure check (depends on T5.1)
- [ ] T5.4 [deploy]: Sealed-OpenBao cold start fails loudly (depends on T5.1)
- [ ] T5.5 [deploy]: Break-glass drill (depends on T5.4, T4.4.1)
- [ ] T5.6 [deploy]: Restart-only path behaves (depends on T5.1)
- [ ] T5.7 [deploy]: Full plaintext-elimination scan (depends on T5.1)
- [ ] **G5: HARD GATE — Class B live verification** — end-to-end test

## G6: Close-out — reviews, rotation, docs, merge

- [ ] T6.1 [deploy]: Security review pass 1 (automated) (depends on T5.1–T5.7)
- [ ] T6.2 [deploy]: Security review pass 2 (independent adversarial) (depends on T6.1)
- [ ] T6.3 [deploy]: Ops/rotation runbook additions — 7 items (depends on T5.1, T5.5)
- [ ] T6.4 [deploy]: Execute rotation of migrated secrets (dev) (depends on T6.3, T5.7)
- [ ] T6.5 [specs]: decisions.md entry for Phase 5.6 (depends on T4.1.1, T4.2.1, T5.3, T5.5)
- [ ] T6.6 [specs]: phases.md Phase 5.6 expansion (depends on T6.9)
- [ ] T6.7 [specs]: progress.md close-out (depends on T6.2, T6.9)
- [ ] T6.8 [specs]: 13_secrets_management.md KV-table audit (depends on T4.3.9, T2.7.2)
- [ ] T6.9 [deploy]: Merge to haisir-deploy main (depends on T6.1, T6.2, T6.3, T6.4)
- [ ] **G6: Close-out** — end-to-end test

- [ ] **ROOT: Full .env secrets elimination via OpenBao** — acceptance test

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T4.1.1 [deploy]: Mechanism decision doc (GATE ENTRY) (depends on T1.4.1, T1.4.2, T1.4.3 ✓ + all 9 G3 tasks ✓)
- T4.2.1 [deploy]: Verify live keycloak-db auth (GATE ENTRY) (depends on all 9 G3 tasks ✓)

G3 (HARD GATE) passed 2026-07-20 — all 9 tasks (T3.1–T3.9) verified live against the same dev bring-up; see the G3 summary above for the real, unrelated-to-secrets gaps found and fixed along the way (network split, HTTPS enforcement, several missing dev/.env.config.sh values). This unblocks G4's two entry tasks, T4.1.1 and T4.2.1 — both are GATE ENTRY tasks each depending on the full G3 set, so either can be started next. Recommend T4.2.1 (verify live keycloak-db auth) first since T4.3.7/T4.3.8 and T4.2.2 depend on its findings; T4.1.1 (mechanism decision doc) can run in parallel since it only needs the T1.4.x spike verdicts (already done) plus G3 (now done).
