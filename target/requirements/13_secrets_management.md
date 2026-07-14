# Secrets Management (OpenBao, Era-4)

> **Target state scope:** replace plaintext `.env*` secrets with an identity-gated secrets authority (OpenBao). Self-hosted, Docker-Compose-deployable, no cloud KMS. Aligns with the "systems" track of `IdentityManagement.md` (Era 4 — token binding). Cross-cutting infrastructure hardening; not tied to a persona phase.
>
> Implementation lives in `haisir-deploy/common/openbao/` (+ `common/scripts/certs/generate-certs-openbao.sh`). Backend integration is a single `SETTINGS_ENV_FILE` seam in `haisir-backend/src/shared/config.py`.
>
> **Status note (2026-07-14):** originally designed and Phase-0–4 coded on `feature/secrets-management-openbao` in `haisir-deploy` (2026-06-05), never merged to `main`. This spec is landing now, retroactively, ahead of a "Phase 5.5 — Secrets Management Closeout" plan cycle that will reconcile that branch against 5+ weeks of `main` drift rather than rebase it wholesale. Two design deltas from the original branch, found during a design-validation pass on 2026-07-14, will be applied during that closeout rather than reflected here yet: (1) pin/upgrade to OpenBao ≥ v2.5.5 for CVE-2025-54996 (namespace-path privilege escalation, patched 2026-06-17); (2) replace the two-instance transit-auto-unseal design below with OpenBao's built-in **static seal** (`file://`-sourced key, same-host, rotation supported) — functionally equivalent on a single-VM topology with one fewer always-on service.

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

**OpenBao** (MPL-2.0 fork of HashiCorp Vault; API/CLI/agent compatible) on a dedicated VM (same-host for dev), behind the existing Haisir CA and Keycloak. Secrets delivered to the backend/worker by a **Vault Agent sidecar** that renders an env file to tmpfs; deploy-time config (APISIX/Keycloak/compose vars) rendered from OpenBao by the deploy host. Full alternative analysis and phasing in `Implementation_planning/2026-06-05_secrets-management_openbao_plan.md`; a follow-up design-validation pass (2026-07-14) is summarized in the status note above and in `decisions.md`.

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
| deploy | `openbao-client-deploy` | `deploy` | `secret/haisir/{gateway,keycloak,db,infra,shared}` (read-only, for templating + compose vars) |

The OpenBao listener sets `tls_require_and_verify_client_cert = true` — no CA-signed client cert ⇒ TLS handshake fails before any token is presented.

### KV layout (KV v2 at `secret/`, per-env instance — not env-namespaced)

`secret/haisir/{backend,worker,shared,db,keycloak,gateway,infra}` — see `haisir-deploy/common/openbao/README.md` for the key-by-path table. **Not yet audited against `main`'s current secret inventory** — `EMBEDDING__OLLAMA_API_KEY`, `HAITU__OLLAMA_API_KEY`, and `GRADING__OLLAMA_API_KEY` were added to `common/docker-compose.yml` after this branch was built and are not yet in this layout or the Vault Agent templates; closing that gap is in-scope for the Phase 5.5 closeout.

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
- **BR-SEC-019 — Fail-safe app startup.** The backend reads secrets from the Agent-rendered env file via `SETTINGS_ENV_FILE`; the Agent MUST have rendered the file before the app boots. If required secrets are absent, the app fails to start (no silent fallback to dummy defaults). **Not yet implemented** — `haisir-backend/src/shared/config.py` still has `default="dummy"` on secret fields as of 2026-07-14; this is unstarted work, not a partial, per the Phase 5.5 closeout audit.

---

## Phasing (high level)

| Phase | Repo | Outcome |
|---|---|---|
| 0 | deploy | OpenBao stood up; certs, policies, cert+OIDC auth, audit, KV — **no app changes** |
| 1 | deploy + backend | Vault Agent sidecar renders secrets to tmpfs; backend reads via `SETTINGS_ENV_FILE`; backend secret env blocks removed from compose |
| 2 | deploy | `template-configs.sh`/`deploy.sh` source secrets from OpenBao; `.env*` reduced to non-secret config |
| 3 | deploy + DB | Postgres dynamic-secrets engine; rotation of all existing secrets at cutover |
| 4 | deploy + specs | DR/backup runbook, audit shipping/retention, this spec + decisions entry |
| 5.5 (closeout) | deploy + backend + specs | Reconcile Phase 0–4 code against current `main`; static-seal migration + version pin; new-secret inventory audit; BR-SEC-019 fail-fast; first live smoke test; security review gate |
| future | — | SPIFFE/SPIRE workload attestation when scaling past one VM |

Task breakdown for the closeout: `Implementation_planning/PLAN.md` / `TASKS.md` (Phase 5.5, once written). Original decision record: `Implementation_planning/decisions.md` (2026-06-05, landed retroactively 2026-07-14).

---

## Out of scope / follow-up

- **Jenkins CI credentials** stay in the Jenkins credential store (already encrypted); optional later migration to OpenBao AppRole.
- **APISIX-native Vault secret backend** (APISIX 3.x can pull secrets from Vault directly) is a Phase 2+ option vs. deploy-time templating; templating chosen first for minimal moving parts.
- **mTLS-everywhere via Keycloak-JWT auth into OpenBao** (single-authority variant) deferred; mTLS cert-auth chosen first to reuse the Haisir CA and avoid a client_secret secret-zero.
