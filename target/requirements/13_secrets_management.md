# Secrets Management (OpenBao, Era-4)

> **Target state scope:** replace plaintext `.env*` secrets with an identity-gated secrets authority (OpenBao). Self-hosted, Docker-Compose-deployable, no cloud KMS. Aligns with the "systems" track of `IdentityManagement.md` (Era 4 — token binding). Cross-cutting infrastructure hardening; not tied to a persona phase.
>
> Implementation lives in `haisir-deploy/common/openbao/` (+ `common/scripts/certs/generate-certs-openbao.sh`). Backend integration is a single `SETTINGS_ENV_FILE` seam in `haisir-backend/src/shared/config.py`.
>
> **Status note (2026-07-21):** OpenBao is now the secrets authority for **every** secret-shaped value across all three environments' `.env`/`.env.config.sh` files — Phase 5.5 (completed 2026-07-15) migrated `haisir-backend`/`haisir-worker`'s own secrets plus the two design deltas below; Phase 5.6 (completed 2026-07-21) closed the remaining gap Phase 5.5's root-goal wording claimed but never covered: gateway (APISIX admin key, session secret, CrowdSec key), the Keycloak OIDC trio + admin password, the backend-admin client credential (deduped into its own `keycloak-clients` path), the test-user credential, the Cloudflare tunnel token, and the three cold-start database passwords (`db`, `keycloak-db`, `keycloak`). See `Implementation_planning/decisions.md` (2026-07-16 planning entry, 2026-07-21 close-out entry) and `phases.md` for the full record. The two design deltas applied during the 5.5 closeout: (1) OpenBao pinned to ≥ v2.6.0 for CVE-2025-54996 (namespace-path privilege escalation, patched 2026-06-17); (2) the two-instance transit-auto-unseal design below was replaced with OpenBao's built-in **static seal** (`file://`-sourced key, same-host, rotation supported) — functionally equivalent on a single-VM topology with one fewer always-on service, live-proven via `docker restart` + poll with zero manual unseal calls.

---

## Problem

Secrets (DB passwords, Keycloak admin + client secrets, CSRF secret, API keys, Cloudflare tunnel token, APISIX admin key, CrowdSec key) live as **plaintext** in per-environment `.env`, `.env.config.sh`, and `.env_info` files and are injected as container **environment variables** — visible via `docker inspect` and `/proc/<pid>/environ`. There is no read-audit, no rotation, and no machine-identity gate: anything running on the host can read every secret. This is the "Era 1 / Era 2" state from `IdentityManagement.md`.

## Goal

A single trusted secrets authority where:
- **Machines** authenticate by a **bound identity** (mTLS client cert — the Era-4 "fingerprint"); a leaked token is useless without the host's cert.
- **Humans** authenticate via the existing Keycloak OIDC (single authority), gated to admins over Tailscale.
- Every secret read is **audited**; secrets are **encrypted at rest** and never appear in `docker inspect`.
- Credentials can be **rotated**, and DB credentials become **short-lived / dynamic**.

## Solution summary

**OpenBao** (MPL-2.0 fork of HashiCorp Vault; API/CLI/agent compatible) on a dedicated VM (same-host for dev), behind the existing Haisir CA and Keycloak. Secrets delivered to the backend/worker by a **Vault Agent sidecar** that renders an env file to tmpfs; deploy-time config (APISIX/Keycloak/compose vars) rendered from OpenBao by the deploy host. Full alternative analysis and phasing in `Implementation_planning/archive/2026-06-05_secrets-management_openbao_plan.md`; a follow-up design-validation pass (2026-07-14) is summarized in the status note above and in `decisions.md`.

---

## Architecture

```
Humans (Keycloak OIDC, Tailscale) ─┐
                                   ▼
                            ┌─────────────┐
Machines (mTLS client cert)─►  OpenBao    │   (self-unseals via static seal —
                            │  (server)   │    see status note above)
                            └──────┬──────┘
                                   │ policies + audit
        ┌──────────────────────────┼───────────────────────────────┐
        │ Vault Agent sidecar (auto-auth mTLS) renders → tmpfs env   │
        │ backend / worker read via SETTINGS_ENV_FILE                │
        │ deploy host renders APISIX/Keycloak/compose config         │
        └────────────────────────────────────────────────────────────┘
```

### Machine identities (cert auth)

| Identity | Client cert CN | Policy | Reads |
|---|---|---|---|
| backend | `openbao-client-backend` | `backend` | `secret/haisir/backend`, `secret/haisir/shared`, `database/creds/haisir-backend` |
| worker | `openbao-client-worker` | `worker` | `secret/haisir/worker`, `secret/haisir/shared`, `database/creds/haisir-worker` |
| deploy | `openbao-client-deploy` | `deploy` | `secret/haisir/{gateway,keycloak,db,infra,shared,keycloak-clients}` (read-only, for templating + compose vars) |
| db | `openbao-client-db` | `db` | `secret/haisir/db` (`POSTGRES_PASSWORD`, via `vault-agent-db` → `POSTGRES_PASSWORD_FILE`) — added Phase 5.6 |
| keycloak-db | `openbao-client-keycloak-db` | `keycloak-db` | `secret/haisir/keycloak` (`KEYCLOAK_POSTGRES_PASSWORD`, via `vault-agent-keycloak-db` → `POSTGRES_PASSWORD_FILE`) — added Phase 5.6 |
| keycloak | `openbao-client-keycloak` | `keycloak` | `secret/haisir/keycloak` (`KC_DB_PASSWORD`, `KC_BOOTSTRAP_ADMIN_PASSWORD`, via `vault-agent-keycloak` → rendered `keycloak.conf`, zero password env vars) — added Phase 5.6 |
| admin-ops (human) | `openbao-client-admin-ops` | `admin` | mTLS identity for OpenBao's OIDC human-admin login path (minted Phase 5.6 T6.4 — the documented flow had no cert-bound identity to use before this) |

The OpenBao listener sets `tls_require_and_verify_client_cert = true` — no CA-signed client cert ⇒ TLS handshake fails before any token is presented. `db`/`keycloak-db`/`keycloak` policies grant path-wide read on their target path rather than per-key scoping (OpenBao KV has no sub-key ACLs) — the same convention every identity above uses; reconfirmed accepted by both Phase 5.6 security review passes.

### KV layout (KV v2 at `secret/`, per-env instance — not env-namespaced)

`secret/haisir/{backend,worker,shared,db,keycloak,gateway,infra,keycloak-clients}` — see `haisir-deploy/common/openbao/README.md` for the key-by-path table. **Fully audited against `main`'s secret inventory as of Phase 5.6 close (2026-07-21)** — every secret-shaped value across `{dev,staging,prod}/{.env,.env.config.sh}` and `other/services/cftunnel/.env` is now sourced from one of these paths; a `full-plaintext-elimination-scan.sh` (added Phase 5.6 T5.7) asserts zero migrated-key-name residue by name across all three environments. `secret/haisir/keycloak-clients` is new this phase — a dedicated path deduping the backend-admin Keycloak client credential's provisioning-side and runtime-side copies into one KV source of record, readable by both `deploy` and `backend`. `secret/haisir/infra` additionally carries the **host-topology** keys defined by BR-SEC-022 for staging and prod (enumerated below) — non-secret by nature, but held in KV because they are host-specific and must not be committed; the `deploy` policy already grants read on that path, so this adds keys, not access.

**pgadmin credentials remain out of scope by deliberate decision** — dev-only convenience, absent from staging/prod entirely. Under BR-SEC-022 `dev/.env` is now committed, so `PGADMIN_DEFAULT_PASSWORD` is committed in plaintext with a `# pragma: allowlist secret` comment. That is the intended end state, not a migration gap: it is a local-only tool credential and deliberately not a KV candidate. It is the sole recorded exception to BR-SEC-011.

#### The seven committed deploy-config paths (BR-SEC-022)

Exactly these seven files are version-controlled in `haisir-deploy` and shipped from the release
artifact at mode `600` (`--chmod=D700,F600`). No other path in those directories is committed, and
no prefix or suffix variant of these names is:

| # | Committed path |
|---|---|
| 1 | `dev/.env` |
| 2 | `dev/.env.config.sh` |
| 3 | `staging/.env` |
| 4 | `staging/.env.config.sh` |
| 5 | `prod/.env` |
| 6 | `prod/.env.config.sh` |
| 7 | `common/.env.config.common.sh` |

#### Host-topology keys in `secret/haisir/infra` (staging and prod only)

Eight key names are in scope. Seven are seeded in KV and armed in
`common/openbao/deploy-required-keys.txt` with `envs=staging,prod`, so the per-key gate aborts the
render rather than emitting a blank. The eighth is deliberately absent:

| Key | Status on staging and prod |
|---|---|
| `KEYCLOAK_ADMIN_PORT_BINDING` | seeded in KV, gated |
| `BACKEND_DB_PORT_BINDING` | seeded in KV, gated |
| `TAILSCALE_ADMIN_CIDR` | seeded in KV, gated |
| `APISIX_ADMIN_ALLOWED_CIDR` | seeded in KV, gated |
| `EXTRACTION__OLLAMA_BASE_URL` | seeded in KV, gated |
| `EMBEDDING__OLLAMA_BASE_URL` | seeded in KV, gated |
| `HAITU__RERANK_BASE_URL` | seeded in KV, gated |
| `KEYCLOAK_ADMIN_ALLOWED_CIDR` | **absent from KV entirely, and removed from the gate** (T6.2.0a, 2026-08-13) |

`KEYCLOAK_ADMIN_ALLOWED_CIDR` does not hold a safe value on staging or prod — it holds nothing. The
variable is unset everywhere on those hosts, and the `127.0.0.1/32` that routes 13/14/15 render is
`template-configs.sh`'s fallback for a **missing** key, not a value the variable carries. There is
therefore no standing admin allowlist stored anywhere in the deployment: nothing to leak, nothing
that can resolve empty. Reach is granted ad hoc with `common/scripts/keycloak-admin-access.sh` and
preserved across a deploy by `create_route_config.sh`. `dev/.env.config.sh` sets it to `0.0.0.0/0`
as a local convenience — dev is the only environment where the variable exists at all.

A ninth key, the withdrawn tailnet model's Keycloak admin-hostname override, was reverted by T6.2.0
(2026-08-13) and MUST NOT be reintroduced — see BR-SEC-023's exposure model.

---

## Business rules

- **BR-SEC-011 — No plaintext secrets at rest (target).** Once cut over (Phase 2), secrets MUST NOT live in committed or on-disk `.env*` files. `.env`/`.env.config.sh` retain **non-secret, non-host-topology config only** — ports, public hostnames, image tags, feature flags. Secret values live in OpenBao; host-topology values (tailnet addresses, admin CIDRs, admin port bindings, compute-host URLs) live in `secret/haisir/infra` per BR-SEC-022. CIDRs were previously listed here as permitted non-secret config; they are not, and that wording is superseded. Because these files hold no secrets, they are not merely *allowed* to be committed — BR-SEC-022 **requires** it.
  - **One recorded exception:** `dev/.env`'s `PGADMIN_DEFAULT_PASSWORD` is committed in plaintext, carrying a `# pragma: allowlist secret` comment. pgadmin is a local-only developer tool that exists in `dev` alone (absent from staging and prod entirely), so this credential grants nothing beyond a developer's own machine and is deliberately not a KV candidate. This is the only plaintext credential permitted in a committed file; anything else matching a secret pattern is a BR-SEC-011 violation, not a second exception.
- **BR-SEC-012 — Identity-bound machine auth.** Machines authenticate to OpenBao via mTLS client cert (cert auth method) mapped to a least-privilege policy. A stolen OpenBao token without the matching client cert MUST be unusable (`tls_require_and_verify_client_cert = true`).
- **BR-SEC-013 — Human access via Keycloak OIDC only.** Human operators authenticate via OIDC against the existing realm; the root token is revoked once OIDC admin login works. Admin reach is gated to Tailscale CIDRs (same pattern as Keycloak/APISIX admin).
- **BR-SEC-014 — Least privilege.** Each policy grants the minimum paths needed. `backend` cannot read `keycloak`/`gateway`/`infra` secrets; `deploy` is read-only and cannot read app-runtime-only secrets it doesn't template; no policy below `admin` can disable the audit device.
- **BR-SEC-015 — Audit on.** A file audit device is enabled from first boot; every secret read is logged (actor, path, time). Audit device hashes request/response so raw secrets are not stored in the log.
- **BR-SEC-016 — Self-unseal, bounded secret-zero.** The main server self-unseals without a cloud KMS or human keys on restart, via OpenBao's static seal (a `file://`-sourced key on the same host, rotation supported) rather than a second transit-unseal instance (superseding the original two-instance design — see status note). The residual secret-zero is that static key file (root-only permissions, never in compose env) plus the Shamir/recovery keys generated at init (held offline).
- **BR-SEC-017 — Dynamic DB credentials (Phase 3).** Backend/worker SHOULD obtain Postgres credentials from the database secrets engine (`database/creds/*`) as short-lived leases rather than a static `DATABASE_URL` password. Static KV secrets have a documented rotation procedure.
- **BR-SEC-018 — Recovery material handling.** Init output (recovery keys, root token) is written to gitignored `.bootstrap-out/<env>/` with `600`, MUST be moved offline, and MUST never be committed.
- **BR-SEC-019 — Fail-safe app startup.** The backend reads secrets from the Agent-rendered env file via `SETTINGS_ENV_FILE`; the Agent MUST have rendered the file before the app boots. If required secrets are absent, the app fails to start (no silent fallback to dummy defaults). **Implemented (Phase 5.5, 2026-07-15)** — `CSRFSettings.secret`, `Settings.database_url`, and `OAuthSettings.keycloak.admin_client_id`/`admin_client_secret` lost their `dummy`/empty-string defaults; `Settings()` raises `pydantic.ValidationError` immediately at import time if any are unset, with the module-level singleton wrapped to re-raise only field-path names (not sibling plaintext values — a partial-misconfiguration leak an adversarial review caught and fixed). Phase 5.6 extended the same fail-closed posture to deploy-side rendering: a per-key required-keys manifest + `${VAR:?}` compose guards (Class A), and vault-agent healthcheck + `service_healthy` gating (Class B, `db`/`keycloak-db`/`keycloak`).
- **BR-SEC-022 — Deploy env config is version-controlled and ships with the release.** Exactly three files, by exact filename, across all three environments — `haisir-deploy/{dev,staging,prod}/.env`, `haisir-deploy/{dev,staging,prod}/.env.config.sh`, and `haisir-deploy/common/.env.config.common.sh` — are committed to `haisir-deploy` and deployed **from the release artifact** at mode `600` (`--chmod=D700,F600`). No prefix or suffix variants, no glob or regex matching, no other file in those directories. **The copy on the remote host is never authoritative**: it is overwritten by the release, never read back, never reconciled against, and never inferred from. A value that exists only on a host does not exist.
  - **Host topology comes from `secret/haisir/infra`, stored fully derived.** Base addresses (`TAILSCALE_IP`, `CLIENT_ADMIN_TAILSCALE_IP`, `COMPUTE_TAILSCALE_IP`) MUST NOT be stored and composed at render time. `env-setup.sh:128-157` sources `.env.config.sh` and `.env` **before** rendering from OpenBao, so a base address arriving later would leave `${TAILSCALE_IP}/32` already evaluated to the literal `/32`. Eight key names per environment, **staging and prod only**, each holding its final value — enumerated with their status in the KV layout section above. Seven are registered in `deploy-required-keys.txt` with `envs=staging,prod` so the per-key gate aborts on empty rather than rendering blank (BR-SEC-019's fail-closed posture); the eighth, `KEYCLOAK_ADMIN_ALLOWED_CIDR`, is absent from KV and from the gate by owner call (T6.2.0a). A ninth key from the withdrawn tailnet admin model was reverted by T6.2.0 and must not be reintroduced. `secret/haisir/infra` already exists and is already readable by the `deploy` identity — no new path, policy, or machine identity.
  - **`dev` is committed for reproducibility only.** There is no dev CI deploy path and dev has no host-topology values, so no dev key moves to KV and none of the nine keys is defined for it. Committing dev closes the recurring "missing dev config var" class of failure.
  - **`REMOTE_HOST`, `REMOTE_USER` and `REMOTE_DEPLOY_DIR` MUST NOT appear in the committed files.** They are deploy-*client* configuration, not host configuration: every consumer runs client-side (`deploy.sh`, `deploy-lib.sh`, `common/scripts/tests/test-runner.sh`), and nothing running on a staging or prod host reads them even though `common/.env.config.common.sh` is rsynced there and sourced. Once the files are committed they exist in the Jenkins workspace, `load_env_config` sources them, and an `export REMOTE_HOST=...` in a committed file **overwrites the Jenkins-injected credential** — the deploy then targets whatever host the file names. Removing them outright is required; `${VAR:-default}` is not an acceptable substitute, being the same decorative-`:-` pattern that made `common/.env.config.common.sh:44`'s fail-closed CIDR default inert (see BR-SEC-023). CI supplies all three as Jenkins secret text, `REMOTE_DEPLOY_DIR` included rather than relying on a `~/haisir-deploy` fallback expanding correctly inside a quoted rsync target.
- **BR-SEC-023 — `ip-restriction` is deny-by-default and always present.** The `ip-restriction` plugin MUST be present on every admin route regardless of how its CIDR variable resolves. **An empty `*_CIDR` value means deny all — never "no restriction."** A configuration mistake, a missing KV key, or an unrendered variable MUST reduce admin reach to zero, never expand it to the public internet.
  - **Mechanism — shipped 2026-08-13 (T6.2.3).** `template-configs.sh` previously set `strip_ip_restriction=true` when a CIDR resolved empty and then ran `jq del(.plugins["ip-restriction"])` on the rendered route — publishing the Keycloak admin console to the internet with no network restriction. That path is gone: an empty CIDR now substitutes `127.0.0.1/32`, and the `jq del` block was deleted outright rather than guarded. An empty whitelist array fails `ip-restriction`'s own schema, so `127.0.0.1/32` is the schema-valid expression of deny-all; because `real-ip` resolves the client address from `cf-connecting-ip`, no external client can present it. `common/scripts/tests/ip-restriction-deny-by-default-check.sh` (T6.2.4) asserts **presence and value** on all three routes offline — an absent key would otherwise read as a pass — so a re-introduced fail-open fails CI.
  - **Exposure model — deny-all + on-demand grant (decided 2026-08-09, revised 2026-08-13).** Gateway routes 13/14/15 stay published and deny everything by default. **The tailnet-only variant was tried and withdrawn.** It required a Keycloak admin-hostname override, because `common/docker-compose.yml` sets `KC_HOSTNAME` to the public origin with `KC_HOSTNAME_STRICT=true`; that override is *server-global*, not master-realm-scoped, so it changed console URL generation for every realm. T6.2.0 reverted it and the variable must not come back. The shipped model stores **no standing admin allowlist in the deployment at all**. An operator grants their own address with `common/scripts/keycloak-admin-access.sh grant <ip>/32` — a `PATCH` against only the `ip-restriction.whitelist` sub-path of the three routes, leaving WAF directives and rate limits untouched — and revokes it when done. `create_route_config.sh` carries a live grant across a deploy so a release cannot lock the operator out mid-session. Pass the `/32` explicitly: auto-detect resolves the caller's *public* IP, which is the wrong address on a Tailscale-only host.
  - **Ordering requirement.** Tailnet admin login MUST be verified working before the deny-all takes effect. Landing the deny-all first risks losing administrative access to the system that authenticates everything else. Note that `dev/.env.config.sh:54` sets `KEYCLOAK_ADMIN_ALLOWED_CIDR="0.0.0.0/0"` — a deliberate dev convenience that stays, which means dev never exercises this path and the verification must run on staging. **Satisfied**: staging 2026-08-13 (T6.2.5, full browser cycle verified by the operator), prod 2026-08-16 (T6.2.6/T6.2.7 — deny-all applied, then grant → console login → revoke → 403 proven as a round trip).

**Shipped status (Phase 7.5 close-out).**

| Rule | Status | Date | Evidence |
|---|---|---|---|
| BR-SEC-022 | Shipped | 2026-08-18 | Seven paths committed in `39eff4a` (T6.3.2, 2026-08-17); `{env}/.env` made the sole source of `VERSION` and image tags in `e6f4a27` (T6.5.1) with the manifest-version assertion in T6.5.4, and the second deploy path deleted in `dc89963` (T6.6.1–T6.6.3). Verified live on staging 2026-08-18: bootstrap from an empty remote tree, then all three synced files byte-identical host-vs-committed (T6.4.2/T6.4.3), deploy exit 0, 13/13 healthy. |
| BR-SEC-023 | Shipped | 2026-08-13 (staging), 2026-08-16 (prod) | Plugin-stripping replaced by a `127.0.0.1/32` deny-all whitelist (T6.2.3) with an offline regression that fails if fail-open returns (T6.2.4). Applied and browser-verified on staging 2026-08-13 (T6.2.5) and on prod in the v2026.7 window 2026-08-16 (T6.2.6), with the grant → login → revoke → 403 round trip proven on prod the same day (T6.2.7). |

> **BR-SEC numbering note:** `02_auth_and_roles.md` allocated `BR-SEC-001 … BR-SEC-012` and `BR-SEC-020 … BR-SEC-021`; this file holds `BR-SEC-011 … BR-SEC-019` plus `BR-SEC-022 … BR-SEC-023`. The **011/012 overlap between the two files is pre-existing and is recorded rather than renumbered** — those IDs are cited from shipped code and past decision entries (see `decisions.md`, 2026-07-27). New rules in either file continue from the highest ID allocated across both, so no *further* collision is created; cross-cutting infrastructure specs use their own prefix (`BR-INFRA-*`, `BR-WAF-*`, `BR-CSP-*`).

---

## Phasing (high level)

| Phase | Repo | Outcome |
|---|---|---|
| 0 | deploy | OpenBao stood up; certs, policies, cert+OIDC auth, audit, KV — **no app changes** |
| 1 | deploy + backend | Vault Agent sidecar renders secrets to tmpfs; backend reads via `SETTINGS_ENV_FILE`; backend secret env blocks removed from compose |
| 2 | deploy | `template-configs.sh`/`deploy.sh` source secrets from OpenBao; `.env*` reduced to non-secret config |
| 3 | deploy + DB | Postgres dynamic-secrets engine; rotation of all existing secrets at cutover |
| 4 | deploy + specs | DR/backup runbook, audit shipping/retention, this spec + decisions entry |
| 5.5 (closeout) ✓ | deploy + backend + specs | Reconcile Phase 0–4 code against current `main`; static-seal migration + version pin; new-secret inventory audit; BR-SEC-019 fail-fast; first live smoke test; security review gate — completed 2026-07-15, scoped to `secret/haisir/{backend,worker,db}` |
| 5.6 (full elimination) ✓ | deploy + specs | Every remaining plaintext secret (apisix/keycloak/db/keycloak-db/gateway/infra/keycloak-clients) migrated to KV; two hard-gate live-verification rounds (Class A, Class B); two independent security review passes; rotation executed live on dev — completed 2026-07-21 |
| future | — | Staging/prod OpenBao bring-up + seeding (runbook exists, execution deferred until those environments are stood up); SPIFFE/SPIRE workload attestation when scaling past one VM |

Task breakdown: `Implementation_planning/TASKS.md` (Phase 5.5 G1–G4, Phase 5.6 G1–G6 — both archived in-place, not moved to `archive/`). Decision records: `Implementation_planning/decisions.md` (2026-06-05 original design, landed retroactively 2026-07-14; 2026-07-16 Phase 5.6 planning; 2026-07-21 Phase 5.6 close-out).

---

## Out of scope / follow-up

- **Jenkins CI credentials** stay in the Jenkins credential store (already encrypted); optional later migration to OpenBao AppRole.
- **APISIX-native Vault secret backend** (APISIX 3.x can pull secrets from Vault directly) is a Phase 2+ option vs. deploy-time templating; templating chosen first for minimal moving parts.
- **mTLS-everywhere via Keycloak-JWT auth into OpenBao** (single-authority variant) deferred; mTLS cert-auth chosen first to reuse the Haisir CA and avoid a client_secret secret-zero.
- **Render hook in `template-configs.sh` — RESOLVED 2026-08-10 (T6.1.1), no longer outstanding.** It was the last provisioning script omitting `render-secrets-hook.sh` while being the sole consumer of the admin CIDRs, so the BR-SEC-022 CIDR move could not land ahead of it. The hook is now sourced at `common/scripts/template-configs.sh:46`, alongside `setup.sh`, `setup-keycloak.sh`, `configure-ssl.sh`, `create_plugin_config.sh` and `create_route_config.sh`.
- **pgadmin stays out of KV.** `dev/.env`'s `PGADMIN_DEFAULT_PASSWORD` is now committed in plaintext with a `# pragma: allowlist secret` comment — a local-only tool credential in the only environment where pgadmin exists. This is a decision, not deferred work: no future phase should migrate it. See the exception recorded under BR-SEC-011.
