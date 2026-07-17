# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:ee3a79e frontend:816194d deploy:3abeda3 (2026-07-16)

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
- [ ] T2.4.3 [deploy]: Remove backend-admin plaintext + manifest entry (atomic) (depends on T2.4.2, T1.3.2)
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

- [ ] T3.1 [deploy]: Cold fresh-install bring-up on dev (GATE ROOT) (depends on T2.2.2, T2.3.2, T2.4.3, T2.5.3, T2.6.2, T2.7.2, T1.2.1, T1.2.2)
- [ ] T3.2 [deploy]: Templated-config value hash verification (depends on T3.1)
- [ ] T3.3 [deploy]: APISIX admin API auth probe (depends on T3.1)
- [ ] T3.4 [deploy]: OIDC login end-to-end (depends on T3.1)
- [ ] T3.5 [deploy]: Backend-admin single-source no-drift check (depends on T3.1)
- [ ] T3.6 [deploy]: Incremental render path (build_compose_cmd) exercised (depends on T3.1)
- [ ] T3.7 [deploy]: Class A plaintext-residue scan (depends on T3.1)
- [ ] T3.8 [deploy]: Prod test-user skip verified (depends on T3.1)
- [ ] T3.9 [deploy]: cftunnel token render check (depends on T3.1)
- [ ] **G3: HARD GATE — Class A live verification** — end-to-end test

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
- T2.4.3 [deploy]: Remove backend-admin plaintext + manifest entry (atomic) (depends on T2.4.2 ✓, T1.3.2 ✓) — touches .env.config.sh (the OAUTH__KEYCLOAK__ADMIN_CLIENT_ID/_SECRET pair). After T2.4.3, the G3 gate root T3.1 unblocks (all Class A cutovers T2.2.2/T2.3.2/T2.4.3/T2.5.3/T2.6.2/T2.7.2 + guards T1.2.1/T1.2.2 done).
