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

`secret/haisir/{backend,worker,shared,db,keycloak,gateway,infra,keycloak-clients}` — see `haisir-deploy/common/openbao/README.md` for the key-by-path table. **Fully audited against `main`'s secret inventory as of Phase 5.6 close (2026-07-21)** — every secret-shaped value across `{dev,staging,prod}/{.env,.env.config.sh}` and `other/services/cftunnel/.env` is now sourced from one of these paths; a `full-plaintext-elimination-scan.sh` (added Phase 5.6 T5.7) asserts zero migrated-key-name residue by name across all three environments. `secret/haisir/keycloak-clients` is new this phase — a dedicated path deduping the backend-admin Keycloak client credential's provisioning-side and runtime-side copies into one KV source of record, readable by both `deploy` and `backend`. pgadmin credentials remain out of scope by deliberate decision (dev-only convenience, absent from staging/prod entirely).

---

## Business rules

- **BR-SEC-011 — No plaintext secrets at rest (target).** Once cut over (Phase 2), secrets MUST NOT live in committed or on-disk `.env*` files. `.env`/`.env.config.sh` retain **non-secret config only** (ports, hostnames, CIDRs, image tags). Secret values live in OpenBao.
- **BR-SEC-012 — Identity-bound machine auth.** Machines authenticate to OpenBao via mTLS client cert (cert auth method) mapped to a least-privilege policy. A stolen OpenBao token without the matching client cert MUST be unusable (`tls_require_and_verify_client_cert = true`).
- **BR-SEC-013 — Human access via Keycloak OIDC only.** Human operators authenticate via OIDC against the existing realm; the root token is revoked once OIDC admin login works. Admin reach is gated to Tailscale CIDRs (same pattern as Keycloak/APISIX admin).
- **BR-SEC-014 — Least privilege.** Each policy grants the minimum paths needed. `backend` cannot read `keycloak`/`gateway`/`infra` secrets; `deploy` is read-only and cannot read app-runtime-only secrets it doesn't template; no policy below `admin` can disable the audit device.
- **BR-SEC-015 — Audit on.** A file audit device is enabled from first boot; every secret read is logged (actor, path, time). Audit device hashes request/response so raw secrets are not stored in the log.
- **BR-SEC-016 — Self-unseal, bounded secret-zero.** The main server self-unseals without a cloud KMS or human keys on restart, via OpenBao's static seal (a `file://`-sourced key on the same host, rotation supported) rather than a second transit-unseal instance (superseding the original two-instance design — see status note). The residual secret-zero is that static key file (root-only permissions, never in compose env) plus the Shamir/recovery keys generated at init (held offline).
- **BR-SEC-017 — Dynamic DB credentials (Phase 3).** Backend/worker SHOULD obtain Postgres credentials from the database secrets engine (`database/creds/*`) as short-lived leases rather than a static `DATABASE_URL` password. Static KV secrets have a documented rotation procedure.
- **BR-SEC-018 — Recovery material handling.** Init output (recovery keys, root token) is written to gitignored `.bootstrap-out/<env>/` with `600`, MUST be moved offline, and MUST never be committed.
- **BR-SEC-019 — Fail-safe app startup.** The backend reads secrets from the Agent-rendered env file via `SETTINGS_ENV_FILE`; the Agent MUST have rendered the file before the app boots. If required secrets are absent, the app fails to start (no silent fallback to dummy defaults). **Implemented (Phase 5.5, 2026-07-15)** — `CSRFSettings.secret`, `Settings.database_url`, and `OAuthSettings.keycloak.admin_client_id`/`admin_client_secret` lost their `dummy`/empty-string defaults; `Settings()` raises `pydantic.ValidationError` immediately at import time if any are unset, with the module-level singleton wrapped to re-raise only field-path names (not sibling plaintext values — a partial-misconfiguration leak an adversarial review caught and fixed). Phase 5.6 extended the same fail-closed posture to deploy-side rendering: a per-key required-keys manifest + `${VAR:?}` compose guards (Class A), and vault-agent healthcheck + `service_healthy` gating (Class B, `db`/`keycloak-db`/`keycloak`).

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
