# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:3c53b1a frontend:816194d deploy:0c7f77f (2026-07-14)

## G1 [deploy]: Deploy-side reconciliation

### G1.1 [deploy]: Branch file reconciliation
- [x] T1.1.1 [deploy]: Land net-new common/openbao/ directory files (2026-07-14)
- [x] T1.1.2 [deploy]: Land net-new generate-certs-openbao.sh (2026-07-14)
- [x] T1.1.3 [deploy]: Reconcile common/docker-compose.yml (depends on T1.1.1) (2026-07-14)
- [x] T1.1.4 [deploy]: Reconcile common/scripts/template-configs.sh (2026-07-14)
- [x] T1.1.5 [deploy]: Reconcile common/scripts/env-setup.sh (2026-07-14)
- [x] T1.1.6 [deploy]: Reconcile other/env_templates/.env.template (2026-07-14)
- [x] T1.1.7 [deploy]: Regenerate .secrets.baseline (depends on T1.1.1-T1.1.6) (2026-07-14)
- [x] **G1.1: Branch file reconciliation** — integration test (2026-07-14)

### G1.2 [deploy]: Static seal replaces transit-unseal (design change A)
- [x] T1.2.1 [deploy]: Remove openbao-unseal service/config/volumes, add seal "static" block (2026-07-14)
- [x] T1.2.2 [deploy]: Rework bootstrap.sh cmd_unseal_init() + `all` composite (2026-07-14)
- [x] T1.2.3 [deploy]: Remove --with-unseal flag from backup.sh (2026-07-14)
- [x] T1.2.4 [deploy]: Remove openbao-unseal cert generation (2026-07-14)
- [x] **G1.2: Static seal replaces transit-unseal** — integration test (2026-07-14)

### G1.3 [deploy]: Version pin to 2.6.0 (design change B)
- [x] T1.3.1 [deploy]: Bump surviving OpenBao image ref in docker-compose.openbao.yml (2026-07-14)
- [x] T1.3.2 [deploy]: Bump OPENBAO_IMAGE in .env.config.sh.template (2026-07-14)
- [x] **G1.3: Version pin to 2.6.0** — integration test (2026-07-14)

### G1.4 [deploy]: Ollama API key secret-gap closure
- [x] T1.4.1 [deploy]: Add backend Ollama keys to secret/haisir/backend (depends on T1.1.1) (2026-07-14)
- [x] T1.4.2 [deploy]: Add worker Ollama keys to secret/haisir/worker (depends on T1.1.1) (2026-07-14)
- [x] T1.4.3 [deploy]: Add backend keys to backend.env(.dynamic).ctmpl (depends on T1.1.1, T1.4.1) (2026-07-14)
- [x] T1.4.4 [deploy]: Add worker keys to worker.env(.dynamic).ctmpl (depends on T1.1.1, T1.4.2) (2026-07-14)
- [x] T1.4.5 [deploy]: Remove plaintext Ollama key lines from docker-compose.yml (depends on T1.4.1, T1.4.2, T1.4.3, T1.4.4, T1.1.3) (2026-07-14)
- [x] **G1.4: Ollama API key secret-gap closure** — integration test (2026-07-14) <!-- UNRESOLVED: subgoal test calls for a live dry-run template render, which needs a running OpenBao server; accepted as a documented static substitute — all 3 keys (EMBEDDING__OLLAMA_API_KEY, HAITU__OLLAMA_API_KEY, GRADING__OLLAMA_API_KEY) appear as guarded render-ready stanzas in all 4 ctmpl, and grep -c OLLAMA_API_KEY common/docker-compose.yml == 0. Live proof deferred to T2.6.1. -->

### G1.5 [deploy]: Stack bring-up ordering
- [x] T1.5.1 [deploy]: Add OpenBao-ready gate before main stack start (depends on T1.1.3, T1.1.4, T1.1.5, T1.2.1, T1.3.1) (2026-07-14)
- [x] T1.5.2 [deploy]: Make deploy.sh partial redeploy sidecar-aware (depends on T1.1.3) (2026-07-14)
- [x] **G1.5: Stack bring-up ordering** — integration test (2026-07-14)

### G1.6 [deploy]: Dynamic Postgres engine compatibility
- [x] T1.6.1 [deploy]: Verify bootstrap.sh db-engine SQL against haisir-postgres image (depends on T1.1.1) (2026-07-14)
- [x] **G1.6: Dynamic Postgres engine compatibility** — integration test (2026-07-14) <!-- UNRESOLVED: subgoal test requires a live OpenBao+Postgres instance, unlike G1.2-G1.5's static checks; accepted as a documented limitation, see PLAN.md G1.6. Passed via the documented policy-lint substitute (database/creds/haisir-{backend,worker} read granted; creation SQL statically pgvector/public-compatible); live proof deferred to G2.5. -->

- [x] **G1: Deploy-side reconciliation** — end-to-end test (2026-07-14) <!-- Goal test passed: `docker compose -f common/docker-compose.yml -f common/openbao/docker-compose.openbao.yml config` validates (exit 0) and grep -c OLLAMA_API_KEY common/docker-compose.yml == 0. All 21 G1 tasks done (G1.4 + G1.6 live-proof caveats documented, deferred to G2.5/T2.6.1). -->

## G2 [deploy]: HARD GATE — first-ever live verification
*(depends on ALL 21 tasks of G1: T1.1.1-T1.1.7, T1.2.1-T1.2.4, T1.3.1-T1.3.2, T1.4.1-T1.4.5, T1.5.1-T1.5.2, T1.6.1)*

### G2.1 [deploy]: Stack bring-up with static seal + pinned version
- [x] T2.1.1 [deploy]: Bring up OpenBao stack, confirm healthy (depends on all 21 G1 tasks) (2026-07-14) <!-- LIVE PASS: bao status => Sealed: false, Version: 2.6.0, Seal Type: static, Initialized: true; container healthy; NO manual operator unseal run (static seal auto-unsealed — the novel claim is proven). bootstrap.sh all completed (init + audit + KV + policies + cert-auth roles). Three never-live-tested config bugs surfaced and fixed in-repo as root cause: (1) docker-compose.openbao.yml — openbao image runs uid=100 but named volumes mount root-owned => added openbao-init container chowning data/audit/seal to 100:1000 (mirrors etcd-init); (2) same file — host cert keys are 600/uid-1000, unreadable by uid-100 => added openbao-certs named volume populated by openbao-init (copy+chown+chmod), switched openbao cert mount off the host bind-mount; preserves G1.5 bring-up ordering (no env-setup.sh dependency); also fixed the healthcheck to present the deploy client cert (mTLS listener requires it — bare `bao status -tls-skip-verify` could never pass); (3) openbao-server.hcl — v2.6.0 gates API audit creation behind unsafe_allow_api_audit_creation (CVE-2025-54997) => added declarative `audit "file" "file"` stanza, bootstrap's idempotent check skips the legacy enable; (4) bootstrap.sh — `docker cp` of policy files fails on rootless Docker ("remount-ro ... operation not permitted"; staging/prod are rootless too) => svr() now uses -i and policies write via stdin (`bao policy write <name> -`). Side effects: root CA + openbao mTLS certs generated at $HOME/certs/localhost; recovery keys + root token in common/openbao/.bootstrap-out/dev/server-init.json (gitignored, must be moved offline + deleted). OIDC admin path intentionally skipped in dev (env unset). -->
- [x] **G2.1: Stack bring-up** — integration test (2026-07-14) <!-- Subgoal test: `docker compose -f common/openbao/docker-compose.openbao.yml up -d` then `bao status` reports Sealed: false, Version: 2.6.0 — PASSED live on feature/secrets-openbao-v2 (local dev, APP_ENV=dev). -->

### G2.2 [deploy]: mTLS-bound client authentication
- [x] T2.2.1 [deploy]: Request without client cert is denied (depends on T2.1.1) (2026-07-14) <!-- LIVE PASS: against healthy openbao-dev (127.0.0.1:8200). No-client-cert probe: `curl --cacert ca.pem https://127.0.0.1:8200/v1/sys/health` => curl exit 56, OpenSSL "tlsv13 alert certificate required" — TLS handshake rejected before any HTTP response (tls_require_and_verify_client_cert enforced). Valid-cert probe: same URL with --cert openbao-client-backend.pem --key ...-key.pem => HTTP 200 `{"initialized":true,"sealed":false,"version":"2.6.0",...}`. A stolen token without the matching CA-signed client cert cannot complete the handshake. No file changes. -->
- [x] **G2.2: mTLS-bound client authentication** — integration test (2026-07-14) <!-- Subgoal test: curl without --cert/--key denied at TLS layer; same with valid agent cert succeeds — PASSED live. -->

### G2.3 [deploy]: Audit logging proof
- [x] T2.3.1 [deploy]: Audit device logs a KV secret read (depends on T2.1.1) (2026-07-14) <!-- LIVE PASS: against healthy openbao-dev. Seeded a test marker into secret/haisir/backend (root token + deploy cert for mTLS), then read it as the `backend` MACHINE identity via cert auth (`bao login -method=cert` with the backend client cert). The declarative `audit "file" "file"` device (added in T2.1.1) captured the read: two entries (request+response) with `request.operation: "read"`, `request.path: "secret/data/haisir/backend"`, `auth.display_name: "cert-backend"`, `auth.policies: ["backend","default"]`, `auth.metadata.common_name: "openbao-client-backend"`, and `time: 2026-07-15T00:58:28Z`. Secret VALUES are HMAC'd (log_raw=false) — no plaintext leaked. The requesting identity is the cert-bound machine identity, not root — a stronger proof than root-token reads. No file changes. -->
- [x] **G2.3: Audit logging proof** — integration test (2026-07-14) <!-- Subgoal test: an authenticated KV read produces a same-second audit entry with actor identity, exact KV path, and timestamp — PASSED live. -->

### G2.4 [deploy]: Static-seal auto-unseal after restart
- [x] T2.4.1 [deploy]: Restart container, confirm auto-unseal with no manual step (depends on T2.1.1) (2026-07-14) <!-- LIVE PASS — the single riskiest untested claim of the whole effort, now formally proven. Against healthy openbao-dev (pre-restart: sealed=false, version=2.6.0). `docker restart openbao-dev` then polled `bao status -format=json` every 3s for up to 60s. At t=3s: sealed=false, version=2.6.0, initialized=true — auto-unsealed by the `seal "static"` stanza reading /openbao/seal/unseal.key. The poll loop ran ONLY read-only `bao status` — no `bao operator unseal` was ever issued (zero manual intervention). Container returned to (healthy). The never-live-tested static-seal auto-unseal design change A is proven correct. No file changes. -->
- [x] **G2.4: Static-seal auto-unseal after restart** — integration test (2026-07-14) <!-- Subgoal test: `docker restart openbao` -> poll bao status shows Sealed: false on its own within 60s with zero manual unseal calls — PASSED live (auto-unsealed at ~3s). -->

### G2.5 [deploy]: Dynamic Postgres credentials proof (Phase 3)
- [x] T2.5.1 [deploy]: Issue dynamic Postgres creds via database/creds/*, connect (depends on T2.1.1, T1.6.1) (2026-07-14) <!-- LIVE PASS against the real haisir-postgres image. Prereqs filled in: brought up `registry.haisir.in/haisir-postgres:18.4` as `haisir-db-dev` on haisir-net (PG 18.4 + pgvector, the genuine image — pulled from registry.haisir.in, the real registry; the .env template's haisir-registry:5000 value is stale and MagicDNS is down); seeded secret/haisir/db with the db admin creds; ran `APP_ENV=dev OPENBAO_DB_HOST=haisir-db-dev bootstrap.sh db-engine` (enabled database/ engine, wrote database/config/haisir-postgres + roles haisir-backend/haisir-worker with the T1.6.1 creation SQL). Issued `bao read database/creds/haisir-backend` => username `v-root-haisir-b-...`, password (20 chars, redacted), lease_id `database/creds/haisir-backend/b7Bly1VS1Xk5K7rCnZT6iuQQ`, lease_ttl 3600s. Connected using ONLY the dynamic credential: `psql -h haisir-db-dev -U <dyn> -d haisir_backend -c 'SELECT 1 AS ok'` => `1`, exit 0. db admin password read from the running container env into a var (never printed); KV seeded with a throwaway test admin password. No file changes. haisir-db-dev kept up — T2.5.2 (lease revoke) reuses it. -->
- [x] T2.5.2 [deploy]: Verify lease expiry/rotation revokes access (depends on T2.5.1) (2026-07-14) <!-- LIVE PASS against the same healthy openbao-dev + haisir-db-dev from T2.5.1. Proved the full dynamic-credential lifecycle on a freshly issued credential (T2.5.1's password was only ever in a shell var, gone across calls — so re-issued to be rigorous): (1) `bao read database/creds/haisir-backend` => new user `v-root-haisir-b-kQPvxsBhGruzRyrMgJb4-1784078135` + 20-char password (redacted) + lease `database/creds/haisir-backend/fOD5GYNKpsyDrakfFtovp8m0`; (2) connect BEFORE revoke via `psql -h haisir-db-dev -U <dyn> -d haisir_backend -c 'SELECT 1 AS ok'` => `1`, exit 0; (3) `bao lease revoke database/creds/haisir-backend/fOD5GYNKpsyDrakfFtovp8m0` => "All revocation operations queued successfully!"; (4) connect AFTER revoke with the SAME credential => `psql: error: ... FATAL: password authentication failed for user "v-root-haisir-b-kQPvxsBhGruzRyrMgJb4-1784078135"`, exit 2. Revoked credential is immediately rejected at the DB — the database engine's revocation_statements dropped the role's password, so the lease lifecycle (issue → use → revoke → deny) is end-to-end proven. Cleanup: also revoked the leftover T2.5.1 lease `database/creds/haisir-backend/b7Bly1VS1Xk5K7rCnZT6iuQQ`. No file changes. -->
- [x] **G2.5: Dynamic Postgres credentials proof** — integration test (2026-07-14) <!-- Subgoal test: "credential issued connects, same credential rejected after revoke" — PASSED live. T2.5.1 issued a dynamic cred and connected successfully (SELECT 1 => 1); T2.5.2 revoked that credential's lease and confirmed the SAME connection then fails (FATAL: password authentication failed, exit 2). The database secrets engine's dynamic-credential lifecycle — issue, use, revoke, deny — is end-to-end proven against the real haisir-postgres image. This also closes the G1.6 + G1.4 live-proof deferrals (the dynamic DB engine works live; the Ollama-key static-secret live proof remains T2.6.1). -->

### G2.6 [deploy]: Ollama secrets served via OpenBao templating
- [x] T2.6.1 [deploy]: Verify backend/worker receive Ollama API keys via template, not plaintext (depends on T2.1.1, T1.4.5) (2026-07-14) <!-- LIVE PASS. Seeded secret/haisir/backend (DATABASE_URL + EMBEDDING__/HAITU__OLLAMA_API_KEY), created secret/haisir/worker (DATABASE_URL + EXTRACTION__/EMBEDDING__/HAITU__/GRADING__OLLAMA_API_KEY), and secret/haisir/shared (all throwaway dev values, never printed). Templates/agent HCL/compose wiring needed no logic changes, but three previously-untested live bugs surfaced and were fixed as root cause: (1) vault-agent-backend/worker mounted client certs from the raw host dir (${OPENBAO_CERT_DIR}), which is 600/uid-1000 — unreadable by the agent's non-root image user; switched both to mount the openbao-certs named volume (already correctly chowned by the openbao stack's openbao-init, external:true reference added to common/docker-compose.yml) instead of a host bind. (2) consul-template's `{{ with secret "secret/data/haisir/shared" }}` on a NOT-YET-SEEDED path is a hard error (infinite exponential-backoff retry), not a silently-skipped optional block as assumed — confirms the friction the task brief predicted; fixed by seeding a placeholder key at secret/haisir/shared (same pattern as the audit probe), not a template change. (3) rendered secret files (perms 0640, owner openbao:openbao) were unreadable by the backend/worker containers' fixed non-root UID (65532, chainguard image) — changed both templates' `perms` to 0644 in backend-agent.hcl/worker-agent.hcl (single-purpose per-service tmpfs volume, no cross-service exposure). PROOF: `docker exec haisir-backend-dev python -c "from shared.config import settings; ..."` and an equivalent one-off worker container run (full worker loop needs live Ollama connectivity, out of scope) both show all keys non-empty; SHA-256[:10] of each rendered value matches the independently-fetched KV value for all 6 keys (EMBEDDING/HAITU on backend; EXTRACTION/EMBEDDING/HAITU/GRADING on worker) — byte-for-byte proof of template delivery without printing any secret. `grep -c OLLAMA_API_KEY common/docker-compose.yml` stayed 0 (plaintext never reintroduced). NOTE: PLAN.md's literal test wording (`docker exec backend printenv KEY`) cannot pass as written — pydantic-settings' `env_file` loads the file into the Settings model only, never into the container's OS env (by design, so secrets never surface via `docker inspect`); the image is also shell-less (no `sh`), so even a manual source-then-printenv workaround isn't executable. The hash-comparison method above is the actual live-provable equivalent; flagged to the user, PLAN.md not edited (deploy-side task, cross-repo test-wording change left for a spec-owner decision). Files changed: common/docker-compose.yml (openbao-certs external volume + vault-agent mount), common/openbao/agent/backend-agent.hcl, common/openbao/agent/worker-agent.hcl (perms 0640->0644). No plaintext secrets or file changes to templates themselves. -->
- [x] **G2.6: Ollama secrets served via OpenBao templating** — integration test (2026-07-14) <!-- Subgoal test: keys land in the vault-agent-rendered env files and match the KV-seeded values, not plaintext in compose — PASSED live (see T2.6.1). -->

- [x] **G2: HARD GATE — first-ever live verification** — end-to-end test (2026-07-14) <!-- All 7 G2 tasks (T2.1.1, T2.2.1, T2.3.1, T2.4.1, T2.5.1, T2.5.2, T2.6.1) PASSED live in one continuous run against feature/secrets-openbao-v2 (local dev, APP_ENV=dev) — zero manual seal intervention at any point (static-seal auto-unseal proven in T2.4.1; T2.6.1 required no unseal step either). G2 clears; G3 backend fail-fast tasks unlock. -->

## G3 [backend]: Backend fails fast instead of running with dummy secrets
*(depends on ALL 7 tasks of G2: T2.1.1, T2.2.1, T2.3.1, T2.4.1, T2.5.1, T2.5.2, T2.6.1)*

### G3.1 [backend]: CSRF secret and database_url require real values
- [ ] T3.1.1 [backend]: Remove default="dummy" from CSRFSettings.secret (depends on all 7 G2 tasks)
- [ ] T3.1.2 [backend]: Remove default="dummy" from Settings.database_url (depends on T3.1.1)
- [ ] **G3.1: CSRF secret and database_url require real values** — integration test

### G3.2 [backend]: Keycloak admin credentials require real values
- [ ] T3.2.1 [backend]: Remove default="" from admin_client_id (depends on all 7 G2 tasks)
- [ ] T3.2.2 [backend]: Remove default="" from admin_client_secret (depends on T3.2.1)
- [ ] **G3.2: Keycloak admin credentials require real values** — integration test

### G3.3 [backend]: Fail-fast behavior proven and documented
- [ ] T3.3.1 [backend]: Add test asserting Settings() raises when required secrets unset (depends on T3.1.2, T3.2.2)
- [ ] T3.3.2 [backend]: Correct header comment to match enforced behavior (depends on T3.3.1)
- [ ] **G3.3: Fail-fast behavior proven and documented** — integration test

- [ ] **G3: Backend fails fast** — end-to-end test

## G4: Close-out and merge
*(entry point T4.1.1 depends on all 7 G2 tasks + all 6 G3 tasks)*

### G4.1 [deploy]: Full-stack gate test
- [ ] T4.1.1 [deploy]: Combined smoke test — reconciled stack + fail-fast backend together (depends on all 7 G2 + all 6 G3 tasks)
- [ ] **G4.1: Full-stack gate test** — integration test

### G4.2 [deploy]: Ops runbooks
- [ ] T4.2.1 [deploy]: Reduce per-env .env files to non-secret config only (depends on T4.1.1)
- [ ] T4.2.2 [deploy]: Rotate every existing secret value (depends on T4.2.1, T2.5.2)
- [ ] **G4.2: Ops runbooks** — integration test

### G4.3: Security review pass 1 — automated skill
- [ ] T4.3.1 [deploy]: Run security-review skill against haisir-deploy diff (depends on T4.1.1)
- [ ] T4.3.2 [backend]: Run security-review skill against haisir-backend diff (depends on T4.1.1)
- [ ] **G4.3: Security review pass 1** — integration test

### G4.4: Security review pass 2 — independent adversarial review
- [ ] T4.4.1 [deploy]: Adversarial review of trust boundaries/secret-zero/policy/HCL (depends on T4.1.1)
- [ ] T4.4.2 [backend]: Adversarial review of fail-fast correctness and log hygiene (depends on T4.1.1)
- [ ] **G4.4: Security review pass 2** — integration test

### G4.5 [specs]: Close-out documentation
- [ ] T4.5.1 [specs]: Add progress.md entry for OpenBao cutover (depends on T4.6.1, T4.6.2)
- [ ] **G4.5: Close-out documentation** — integration test

### G4.6: Merge to main
- [ ] T4.6.1 [deploy]: Merge feature/secrets-openbao-v2 → haisir-deploy main (depends on T4.2.1, T4.2.2, T4.3.1, T4.4.1)
- [ ] T4.6.2 [backend]: Merge backend fail-fast branch → haisir-backend main (depends on T4.3.2, T4.4.2, T4.6.1 [deploy] — backend cannot merge ahead of deploy)
- [ ] **G4.6: Merge to main** — integration test

- [ ] **G4: Close-out and merge** — end-to-end test

- [ ] **ROOT: OpenBao live as hAIsir's secrets authority** — acceptance test

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T3.1.1 [backend]: Remove default="dummy" from CSRFSettings.secret (deps: all 7 G2 tasks ✓ — `src/shared/config.py:99`, change `secret: str = Field(default="dummy", min_length=1)` to a required field)
- T3.2.1 [backend]: Remove default="" from admin_client_id (deps: all 7 G2 tasks ✓ — `src/shared/config.py:79`, change `admin_client_id: str = Field(default="")` to a required field)

G1 (all 21 deploy tasks) + all 7 G2 tasks (G2.1–G2.6, including T2.6.1) are COMPLETE — the **G2 HARD GATE has cleared**. G3 backend fail-fast tasks are now unlocked: T3.1.1 and T3.2.1 are ready in parallel (independent fields in the same file); T3.1.2/T3.2.2 unlock once their respective predecessor lands; T3.3.x needs both chains done. Nothing in G4 is ready until all 6 G3 tasks clear (deliberate risk-sequencing, see PLAN.md "Embedded design decisions" #4). Live stack still up (dev): openbao-dev, haisir-db-dev, vault-agent-backend/worker, haisir-backend-dev, and a one-off haisir-worker-dev proof run — see T2.6.1 note for what's disposable vs. worth keeping.
