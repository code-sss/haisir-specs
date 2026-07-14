# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:3c53b1a frontend:816194d deploy:b8f650d (2026-07-14)

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
- [ ] T2.1.1 [deploy]: Bring up OpenBao stack, confirm healthy (depends on all 21 G1 tasks)
- [ ] **G2.1: Stack bring-up** — integration test

### G2.2 [deploy]: mTLS-bound client authentication
- [ ] T2.2.1 [deploy]: Request without client cert is denied (depends on T2.1.1)
- [ ] **G2.2: mTLS-bound client authentication** — integration test

### G2.3 [deploy]: Audit logging proof
- [ ] T2.3.1 [deploy]: Audit device logs a KV secret read (depends on T2.1.1)
- [ ] **G2.3: Audit logging proof** — integration test

### G2.4 [deploy]: Static-seal auto-unseal after restart
- [ ] T2.4.1 [deploy]: Restart container, confirm auto-unseal with no manual step (depends on T2.1.1)
- [ ] **G2.4: Static-seal auto-unseal after restart** — integration test

### G2.5 [deploy]: Dynamic Postgres credentials proof (Phase 3)
- [ ] T2.5.1 [deploy]: Issue dynamic Postgres creds via database/creds/*, connect (depends on T2.1.1, T1.6.1)
- [ ] T2.5.2 [deploy]: Verify lease expiry/rotation revokes access (depends on T2.5.1)
- [ ] **G2.5: Dynamic Postgres credentials proof** — integration test

### G2.6 [deploy]: Ollama secrets served via OpenBao templating
- [ ] T2.6.1 [deploy]: Verify backend/worker receive Ollama API keys via template, not plaintext (depends on T2.1.1, T1.4.5)
- [ ] **G2.6: Ollama secrets served via OpenBao templating** — integration test

- [ ] **G2: HARD GATE — first-ever live verification** — end-to-end test

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
- T2.1.1 [deploy]: Bring up OpenBao stack, confirm healthy (deps: all 21 G1 tasks ✓ — **G2 LIVE HARD-GATE TASK**: needs a running OpenBao+stack environment to verify static-seal auto-unseal and health; not a static-edit task, do not auto-start, requires operator to bring up the live stack)

G1 (all 21 deploy tasks) is COMPLETE. Nothing else in G2/G3/G4 is ready until the G2 hard gate (7 tasks) clears in full — this is deliberate risk-sequencing (see PLAN.md "Embedded design decisions" #4). G3 backend tasks (T3.1.x/T3.2.x) unlock only after all 7 G2 tasks pass.
