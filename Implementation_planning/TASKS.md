# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:3c53b1a frontend:816194d deploy:b8f650d (2026-07-14)

## G1 [deploy]: Deploy-side reconciliation

### G1.1 [deploy]: Branch file reconciliation
- [ ] T1.1.1 [deploy]: Land net-new common/openbao/ directory files
- [ ] T1.1.2 [deploy]: Land net-new generate-certs-openbao.sh
- [ ] T1.1.3 [deploy]: Reconcile common/docker-compose.yml (depends on T1.1.1)
- [ ] T1.1.4 [deploy]: Reconcile common/scripts/template-configs.sh
- [ ] T1.1.5 [deploy]: Reconcile common/scripts/env-setup.sh
- [ ] T1.1.6 [deploy]: Reconcile other/env_templates/.env.template
- [ ] T1.1.7 [deploy]: Regenerate .secrets.baseline (depends on T1.1.1-T1.1.6)
- [ ] **G1.1: Branch file reconciliation** — integration test

### G1.2 [deploy]: Static seal replaces transit-unseal (design change A)
- [ ] T1.2.1 [deploy]: Remove openbao-unseal service/config/volumes, add seal "static" block (depends on T1.1.1)
- [ ] T1.2.2 [deploy]: Rework bootstrap.sh cmd_unseal_init() + `all` composite (depends on T1.2.1)
- [ ] T1.2.3 [deploy]: Remove --with-unseal flag from backup.sh (depends on T1.2.1)
- [ ] T1.2.4 [deploy]: Remove openbao-unseal cert generation (depends on T1.1.2, T1.2.1)
- [ ] **G1.2: Static seal replaces transit-unseal** — integration test

### G1.3 [deploy]: Version pin to 2.6.0 (design change B)
- [ ] T1.3.1 [deploy]: Bump surviving OpenBao image ref in docker-compose.openbao.yml (depends on T1.2.1)
- [ ] T1.3.2 [deploy]: Bump OPENBAO_IMAGE in .env.config.sh.template (depends on T1.1.1)
- [ ] **G1.3: Version pin to 2.6.0** — integration test

### G1.4 [deploy]: Ollama API key secret-gap closure
- [ ] T1.4.1 [deploy]: Add backend Ollama keys to secret/haisir/backend (depends on T1.1.1)
- [ ] T1.4.2 [deploy]: Add worker Ollama keys to secret/haisir/worker (depends on T1.1.1)
- [ ] T1.4.3 [deploy]: Add backend keys to backend.env(.dynamic).ctmpl (depends on T1.1.1, T1.4.1)
- [ ] T1.4.4 [deploy]: Add worker keys to worker.env(.dynamic).ctmpl (depends on T1.1.1, T1.4.2)
- [ ] T1.4.5 [deploy]: Remove plaintext Ollama key lines from docker-compose.yml (depends on T1.4.1, T1.4.2, T1.4.3, T1.4.4, T1.1.3)
- [ ] **G1.4: Ollama API key secret-gap closure** — integration test

### G1.5 [deploy]: Stack bring-up ordering
- [ ] T1.5.1 [deploy]: Add OpenBao-ready gate before main stack start (depends on T1.1.3, T1.1.4, T1.1.5, T1.2.1, T1.3.1)
- [ ] T1.5.2 [deploy]: Make deploy.sh partial redeploy sidecar-aware (depends on T1.1.3)
- [ ] **G1.5: Stack bring-up ordering** — integration test

### G1.6 [deploy]: Dynamic Postgres engine compatibility
- [ ] T1.6.1 [deploy]: Verify bootstrap.sh db-engine SQL against haisir-postgres image (depends on T1.1.1)
- [ ] **G1.6: Dynamic Postgres engine compatibility** — integration test <!-- UNRESOLVED: subgoal test requires a live OpenBao+Postgres instance, unlike G1.2-G1.5's static checks; accepted as a documented limitation, see PLAN.md G1.6 -->

- [ ] **G1: Deploy-side reconciliation** — end-to-end test

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
- T1.1.1 [deploy]: Land net-new common/openbao/ directory files (no deps)
- T1.1.2 [deploy]: Land net-new generate-certs-openbao.sh (no deps)
- T1.1.4 [deploy]: Reconcile common/scripts/template-configs.sh (no deps)
- T1.1.5 [deploy]: Reconcile common/scripts/env-setup.sh (no deps)
- T1.1.6 [deploy]: Reconcile other/env_templates/.env.template (no deps)

Nothing in G2/G3/G4 is ready until G1 (21 tasks) completes and the G2 hard gate (7 tasks) clears in full — this is deliberate risk-sequencing (see PLAN.md "Embedded design decisions" #4).
