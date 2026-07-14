> **Landed retroactively 2026-07-14.** This plan was written and approved 2026-06-05 on `feature/secrets-management-openbao` (deploy Phase 0–4 coded against it, never merged). It is copied here verbatim as historical design record ahead of a "Phase 5.5 — Secrets Management Closeout" plan cycle that reconciles the branch against 5+ weeks of `main` drift. Two corrections since this was written: the target spec now lives at `target/requirements/13_secrets_management.md` (slot 08 was claimed by essay AI grading in the interim), and a 2026-07-14 design-validation pass recommends dropping the two-instance transit-auto-unseal design below in favor of OpenBao's built-in static seal, plus pinning to OpenBao ≥ v2.5.5 for CVE-2025-54996 — see `decisions.md`.

# Plan: Era-4 Secrets Management with OpenBao

## Context

**Problem.** Secrets for hAIsir live as plaintext in `.env`, `.env.config.sh`, and `.env_info` files on each host (dev/staging/prod). They are gitignored but sit unencrypted on disk and are injected as **environment variables** — so they're visible in `docker inspect` and `/proc/<pid>/environ`. There is no audit of who reads a secret, no rotation, and no machine-identity gate on access.

**Goal (from the user).** Stop using plaintext `.env*`. Put secrets in a secure store accessible only to (a) the application machine-to-machine and (b) authorised humans through proper authn/authz. Self-hosted (no cloud), on a dedicated VM, deployable to CI/prod. Adopt the **Era-4** model from [IdentityManagement.md](../haisir-specs/IdentityManagement.md): a single trusted authority, machines authenticated by *bound identity* ("a fingerprint, not a key"), addressing the **secret-zero** problem — with **secret rotation** designed in and executed once the solution is proven. Explicit secondary intent: this is a **learning ground for best-practice / financial-grade** patterns that transfer to future work.

**Outcome.** OpenBao (open-source Vault) as the single secrets authority on a dedicated VM, machines authenticated by mTLS-bound identity (reusing the existing Haisir CA), secrets delivered to the backend via a Vault Agent sidecar, deploy-time config rendered from OpenBao instead of `.env*` files, dynamic Postgres credentials + rotation, and a full audit trail. SPIFFE/SPIRE is named as the future north-star for workload attestation at scale.

---

## The requirement, in my own words

Stripped to essentials, you are asking for five things, in priority order:

1. **No plaintext secrets at rest.** Today secrets live unencrypted in `.env` / `.env.config.sh` / `.env_info` and are exposed as container env vars (`docker inspect`, `/proc`). That must end — secrets should live encrypted in one store.
2. **Access only through a verified identity.** Two classes of caller, exactly as your [IdentityManagement.md](../haisir-specs/IdentityManagement.md) frames it: the **application (machine-to-machine)** and **authorised humans**. Each must prove *who it is* before reading a secret; nothing reads secrets just by sitting on the box.
3. **Era-4 specifically.** Not just "a vault" (that's Era 2, which the article shows still leaks in transit and still has secret-zero), and not just short-lived tokens (Era 3). You want **identity-bound** machine auth — the credential a machine holds is something it *is* (a host-bound fingerprint), so a stolen token/secret is useless to anyone else. That answers the **secret-zero** problem head-on.
4. **Self-hosted, no cloud, Docker-Compose-friendly, dedicated-VM-ready.** It has to run on your VPS/CI/dedicated-VM topology — not Kubernetes, not a managed cloud KMS.
5. **A best-practice learning ground.** You're consciously over-investing relative to today's edtech load because you want the *industry-standard, financial-grade* pattern under your hands for future projects. Rotation and audit are part of "done," not nice-to-haves.

**Why OpenBao fits this requirement, point by point:**

- (1) Secrets live encrypted in OpenBao's storage; the app receives them only in memory/tmpfs, never on disk or in `docker inspect`. ✅
- (2) OpenBao has first-class **machine auth** (mTLS cert / AppRole / JWT) *and* **human auth** (OIDC via your existing Keycloak), with per-path **policies** — the exact two-caller split you described, each gated by identity. ✅
- (3) **mTLS cert-auth** is the literal Era-4 "fingerprint": every token OpenBao issues is bound to the machine's CA-signed client cert; a leaked token can't be replayed from another host. Secret-zero collapses to a host-bound cert (issued by the CA you already run). ✅
- (4) OpenBao is a single self-hostable binary/container, runs fine under Docker Compose, and scales from same-host (dev) to a dedicated VM (prod) with no cloud dependency; **transit auto-unseal** removes the only cloud-KMS temptation. ✅
- (5) OpenBao is wire-compatible with HashiCorp Vault — the literal standard in regulated/fintech environments — so policies, dynamic secrets, transit unseal, and audit you learn here transfer 1:1. ✅

In short: the requirement is *"encrypted, identity-gated, Era-4, self-hosted, and a transferable best-practice skill."* OpenBao is the smallest off-the-shelf component that satisfies all five without writing security-critical code yourself.

---

## Current state — discovered facts (implementer: do NOT re-explore; everything you need is here)

> This section is the ground truth gathered from the repos as of June 2026. Treat secret **names** below as canonical; **never** hardcode or print secret *values*. The repos are not Kubernetes — deployment is Docker Compose per environment.

### Repositories (siblings on disk)
- `/home/gulzar/Workspace/haisir-specs` — specs only (this plan lives outside the repo; spec updates go here per convention).
- `/home/gulzar/Workspace/haisir-backend` — FastAPI backend + worker (DDD layout under `src/`).
- `/home/gulzar/Workspace/haisir-frontend` — Next.js (no secrets of concern; skip).
- `/home/gulzar/Workspace/haisir-deploy` — Docker Compose + scripts + APISIX/Keycloak config. **Most work happens here.**

### Environments
Three: `dev`, `staging`, `prod`. Each has its own directory in `haisir-deploy/` (`dev/`, `staging/`, `prod/`) plus shared assets in `common/`. `dev` uses placeholder secrets and is HTTP/localhost-bound; `staging`/`prod` use real secrets, are HTTPS, and bind admin ports to a **Tailscale** IP. Prod fronts traffic with a **Cloudflare Tunnel**; staging uses Nginx Proxy Manager.

### How secrets flow TODAY (the two paths we must replace)
1. **Compose env injection (runtime).** `common/docker-compose.yml` reads `${VAR}` from the per-env `.env` file (Docker Compose variable substitution) and passes them into containers via `environment:` blocks. Backend secret vars are at lines ~85–98; worker at ~147–157; Postgres at 33–37 & 264–268; Keycloak at 311–323.
2. **Deploy-time templating.** `common/scripts/template-configs.sh` `source`s the per-env `.env.config.sh` (shell `export`s) and substitutes `{{PLACEHOLDER}}` tokens into JSON/YAML under `common/routes/`, `common/plugin_configs/`, `common/keycloak/`, and `common/apisix_conf/config.yaml`, writing rendered output to `.templated/<APP_ENV>/`. Placeholder discovery is regex `{{[A-Z_]*}}`; values come from matching shell vars.

Files holding secrets today (gitignored; values are plaintext on disk):
- `dev|staging|prod/.env` — compose vars.
- `dev|staging|prod/.env.config.sh` — shell exports for templating.
- `*/.env_info` — human-readable credential notes (incl. plaintext test-user passwords).
- `other/services/*/.env` — per-service (cftunnel `TUNNEL_TOKEN`, sonarqube, npm, etc.).
- Templates: `other/env_templates/.env.template`, `.env.config.sh.template`.
- `.gitignore` already excludes `.env`, `.env.config.sh`, `.env.config.common.sh`, `.env_info`, `.templated`. `gitleaks` runs as a pre-commit hook (`.gitleaks.toml`, `.secrets.baseline`).

### Secret inventory (NAMES only — these are what must move into OpenBao)
- **Backend / worker (consumed via pydantic-settings, nested delimiter `__`):** `DATABASE_URL`, `OAUTH__KEYCLOAK__ADMIN_CLIENT_ID`, `OAUTH__KEYCLOAK__ADMIN_CLIENT_SECRET`, `CSRF__SECRET`, `EXTRACTION__OLLAMA_API_KEY`, and SDK-read `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`.
- **Databases:** `POSTGRES_USER/PASSWORD/DB`, `KEYCLOAK_POSTGRES_USER/PASSWORD/DB`, `KC_DB_URL/USERNAME/PASSWORD`.
- **Keycloak:** `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD` (bootstrap), `KEYCLOAK_CLIENT_SECRET`, `KEYCLOAK_BACKEND_ADMIN_CLIENT_SECRET`.
- **Gateway / infra:** `APISIX_ADMIN_KEY`, `CROWDSEC_BOUNCER_KEY`, `TUNNEL_TOKEN` (Cloudflare), `SESSION_SECRET`, `GOOGLE_OAUTH_CLIENT_ID/SECRET`.
- **CI (Jenkins, already in Jenkins credential store, out of scope but note for completeness):** `staging/prod-ssh-key`, `*-remote-host`, `*-remote-user`.

### Backend config loading (the integration seam — minimal change)
- `haisir-backend/src/shared/config.py` defines a `pydantic-settings` `Settings` class; singleton instantiated at import (`settings = Settings()`, line 276).
- `model_config` uses `env_file=env_file_name`, `env_nested_delimiter="__"`, `env_ignore_empty=True` (lines 268–273). **`env_file_name` is overridable via the `SETTINGS_ENV_FILE` env var** — this is the hook: point it at the Vault-Agent-rendered tmpfs file and the app needs almost no code change.
- Secrets are read at import/startup (not lazily), so a startup-time render or a sidecar that has the file ready before the app boots is sufficient for v1. JWKS client and Keycloak admin client are built from these settings (`src/auth/user.py`, `src/infrastructure/keycloak_admin.py`, `src/infrastructure/token_introspection.py`).

### Existing mTLS / CA infrastructure to REUSE (do not invent new)
- `common/scripts/certs/generate-certs-ca.sh` creates a **Haisir Root CA** (4096-bit RSA, 10-yr) at `${CERT_ROOT:-$HOME/certs}/${DOMAIN_NAME}/ca.pem` + `ca-key.pem`. Subject `CN=Haisir Root CA`.
- `generate-certs-etcd.sh` / `-apisix.sh` / `-keycloak.sh` show the established pattern for issuing server+client certs from that CA. etcd already runs **mTLS with client-cert auth** (`ETCD_CLIENT_CERT_AUTH=true`) — proof the mTLS machine-auth model already works in this stack.
- Certs are delivered to containers via **external Docker volumes** mounted read-only (e.g. `haisir-etcd-certs`, `haisir-keycloak-certs`, `haisir-apisix-certs`). Network is the external `haisir-net` bridge.
- Container hardening convention (apply to OpenBao too): non-root `user:`, `cap_drop: ALL`, `security_opt: no-new-privileges`, `read_only` root fs + `tmpfs` for writable dirs, `mem_limit`/`cpus`/`pids_limit`, json-file logging with rotation, admin ports bound to Tailscale in staging/prod.

### Existing identity stack (the "single authority" to align with)
- **Keycloak 26** is the OIDC/OAuth2 IdP (realm `haisir-realm-<APP_ENV>`). **APISIX** is the gateway: it terminates TLS, validates JWT via Keycloak JWKS, and injects `Authorization: Bearer <JWT>` upstream (client never sends the token). Backend independently re-validates (local JWKS decode + RFC 7662 introspection).
- Backend already performs **OAuth2 client-credentials M2M** to Keycloak via the `haisir-backend-admin` service account (this is "Era 3 for systems" already done). That means a Keycloak-JWT-auth path into OpenBao is viable later (single-authority variant), but **default to mTLS cert-auth** to reuse the CA and avoid the client_secret being secret-zero.

### Spec-update convention (MANDATORY for this repo family)
Any change to API endpoints, business rules, permissions, DB schema, or infra **must** ship a matching `haisir-specs` update. For this work: add `target/requirements/08_secrets_management.md` and a dated `Implementation_planning/decisions.md` entry; cross-reference from `target/requirements/02_auth_and_roles.md`. New target specs go in `target/requirements/` (never repo root).

---

## Why this approach (and what was rejected)

**Recommended: OpenBao** (the Linux Foundation, MPL-2.0 fork of HashiCorp Vault — API/CLI/agent compatible).

1. **It is the Era-4 architecture, not an approximation.** OpenBao gives a single trusted authority (matches the article's "Authorisation Server"), per-secret access policies, an audit device (who-read-what), dynamic/short-lived secrets, and machine auth by **mTLS client cert** — literally the "fingerprint" Era-4 describes. Nothing custom; this is the industry standard.
2. **It reuses what you already run.** You already operate a private CA and mTLS (etcd ↔ APISIX, cert-gen scripts) and an OAuth2 authority (Keycloak). OpenBao slots into both: mTLS cert-auth reuses [generate-certs-ca.sh](../haisir-deploy/common/scripts/certs/generate-certs-ca.sh); optionally JWT-auth reuses Keycloak as the identity source.
3. **Skills transfer to financial-grade work.** OpenBao is wire-compatible with HashiCorp Vault, the de-facto standard in regulated/fintech shops. What you learn here (policies, dynamic secrets, transit unseal, audit) applies 1:1 to a Vault environment later — exactly the "learning ground" you asked for.

**Alternatives we should NOT proceed with (with reasons, pros & cons):**

**A. Custom in-house secret manager** — *Rejected outright.*
- Pros: full control; nothing new to learn operationally; exactly the API you want.
- Cons: you would be hand-writing the hardest-to-get-right security code there is — encryption-at-rest, an unseal/key-hierarchy, tamper-evident audit, a policy engine, token lifecycle, rotation. A subtle bug = silent total compromise. No external review, no ecosystem, you own every CVE forever.
- Why not: this is the textbook "don't roll your own" domain, and it directly contradicts your "industry-standard, best-practice" goal. OpenBao already *is* the in-house option — open source, self-hosted, auditable — without the risk.

**B. SOPS + age (encrypt secrets files at rest)** — *Good, but doesn't meet this goal.*
- Pros: near-zero ops (no running service to babysit, no unseal); secrets become safe to commit to git; trivial to adopt; perfect if the *only* goal were "no plaintext."
- Cons: it encrypts *files*, full stop. No runtime API, **no machine-identity gate**, no per-secret access policy, no audit of reads, no rotation, no dynamic secrets. The decryption key (age/KMS key) is itself a static secret-zero on disk.
- Why not: it's Era-2-ish (a safer file), not Era-4. It fails requirements #2, #3, and #5. *Keep it in your back pocket* as the right answer if priorities ever collapse back to "just stop plaintext, minimal ops."

**C. Infisical (self-hosted)** — *Capable, but not the best fit for this learning goal.*
- Pros: excellent developer UX and modern web UI; self-hostable; supports machine identities and secret syncing; quick to get value.
- Cons: younger project; depends on Postgres+Redis (more moving parts); weaker/less mature on the exact things this exercise is *about* — mTLS-bound machine auth, dynamic secrets engines, transit auto-unseal, tamper-evident audit. Skills transfer less directly to a Vault-shop/fintech environment.
- Why not: you asked for "best of the best, financial-grade." Infisical optimizes for DX; OpenBao/Vault optimizes for the depth and standardization you're trying to learn. *Keep as fallback* if a friendly UI for non-engineers ever becomes the priority.

**D. HashiCorp Vault Community Edition** — *Same skills, kept as a near-tie swap.*
- Pros: the de-facto standard; biggest ecosystem, most tutorials/docs/integrations; the literal thing many fintechs run; identical concepts to OpenBao.
- Cons: **BSL license** (Business Source License) — free for your use, but not OSI-open and carries a "can't offer it as a competing service" restriction and future-direction risk.
- Why not (as default): OpenBao gives the *same learning and API* under a clean open license (MPL-2.0, Linux Foundation). **This is the one sub-decision genuinely worth confirming with you** — if brand-name/ecosystem on a résumé matters more than license purity, swap to Vault CE with zero plan changes.

**E. Cloud KMS / managed Secret Manager (AWS/GCP/Azure)** — *Excluded by you.*
- Pros: zero ops, auto-unseal, managed HA, strong audit out of the box.
- Cons: cloud lock-in and ongoing cost; you explicitly said no cloud; less "build it yourself" learning.
- Why not: ruled out by your constraint. (Noted only for completeness — it's what most teams *would* reach for, and the transit-auto-unseal design below is the self-hosted substitute for its best feature.)

**Am I overengineering?** For a single-box edtech app, yes — *if* the only goal were "no plaintext," SOPS would do. But the user explicitly chose full Era-4 as a deliberate learning investment and is future-proofing for financial work. Given that, OpenBao is right-sized, **with two honest caveats**: (1) on a single host, OpenBao + app share a blast radius — the real isolation win comes from the dedicated VM, which is why prod uses one; (2) OpenBao adds a stateful service with an **unseal** lifecycle to operate (addressed below). Dev may run a lighter mode.

---

## Target architecture

```
                 ┌─────────────────────────────────────────────┐
                 │  Dedicated VM (or same host for dev)         │
                 │  ┌────────────┐      ┌────────────────────┐  │
   admins ─────► │  │  OpenBao   │◄─────│ OpenBao "unseal"   │  │  transit auto-unseal
  (Keycloak/     │  │  (server)  │      │  (transit engine)  │  │  (no cloud KMS)
   OIDC + mTLS)  │  └─────┬──────┘      └────────────────────┘  │
                 │        │ mTLS cert-auth / policies / audit    │
                 └────────┼─────────────────────────────────────┘
                          │  (Tailscale-only, like Keycloak admin)
        ┌─────────────────┼──────────────────────────────────────┐
        │ App host (per env)                                       │
        │   ┌──────────────────┐   renders    ┌────────────────┐  │
        │   │  Vault Agent      │─────────────►│ secrets → tmpfs│  │
        │   │  (auto-auth mTLS) │   templates  │ env file/files │  │
        │   └──────────────────┘              └───────┬────────┘  │
        │   deploy.sh pulls deploy-time secrets ◄──────┘          │
        │   backend / worker / compose / template-configs.sh      │
        └─────────────────────────────────────────────────────────┘
```

**Single authority.** OpenBao is the source of truth for all secrets. Humans authenticate via Keycloak OIDC (reuse existing IdP) → OpenBao `oidc` auth, gated to admins over Tailscale (same pattern as Keycloak/APISIX admin today). Machines authenticate via **mTLS cert-auth** using certs issued by the Haisir CA — the Era-4 "fingerprint."

**Secret-zero answer.** The only bootstrap credential a machine holds is a **host-bound TLS client cert** issued by the Haisir CA (same model as etcd). No static API token in env. (Documented fallback: AppRole with a **response-wrapped, single-use, short-TTL SecretID** injected by `deploy.sh` — use only where cert-auth is impractical.)

**Unseal (no cloud KMS).** Use **OpenBao transit auto-unseal**: a second, minimal OpenBao instance exposes a transit key that auto-unseals the main server on restart. This is the enterprise pattern without a cloud KMS and is the highest-value "best practice" learning here. Dev may use plain Shamir/manual unseal or `-dev` mode. The transit-unseal instance's own seal is the residual manual step (Shamir keys held by operators, split via `bao operator init`).

**Two consumption paths, one source:**
1. **Runtime (backend/worker).** A **Vault Agent sidecar** auto-authenticates (mTLS), maintains a token, and *templates* secrets to a **tmpfs** env file the container loads — backend code barely changes. This also unlocks **dynamic Postgres credentials** and live rotation.
2. **Deploy-time (APISIX/Keycloak/compose vars).** `deploy.sh` / [template-configs.sh](../haisir-deploy/common/scripts/template-configs.sh) fetch values from OpenBao (`bao kv get`) and render `{{PLACEHOLDER}}` configs + the per-env env files into an **ephemeral/tmpfs** location at deploy time — `.env*` files stop being the stored source of truth.

---

## Phases

> Rotation of existing secrets is deliberately a **later phase** (per the user: design first, rotate once the solution is proven; current secrets are not exposed).

### Phase 0 — Stand up OpenBao (no migration yet) — `haisir-deploy`
- Add OpenBao compose service (start on dev/same-host; provision a dedicated VM for staging/prod). Mirror existing hardening: non-root, `cap_drop: ALL`, `no-new-privileges`, read-only root + tmpfs, Tailscale-bound admin port, json-file logging.
- Add the **transit auto-unseal** OpenBao instance; `bao operator init`, store unseal/recovery keys offline (document the runbook).
- Enable **file audit device** from day one.
- Issue OpenBao server cert + a CA-signed **client cert per machine identity** via a new `generate-certs-openbao.sh` modelled on the existing cert scripts.
- Enable auth methods: `cert` (mTLS, machines) and `oidc` (Keycloak, humans). Write **policies** (least-privilege per service: backend, worker, deploy, apisix).

### Phase 1 — Backend runtime via Vault Agent sidecar — `haisir-deploy` + `haisir-backend`
- Add a `vault-agent` sidecar to the backend & worker services; auto-auth via mTLS; template KV secrets (`DATABASE_URL`, `OAUTH__KEYCLOAK__ADMIN_CLIENT_SECRET`, `CSRF__SECRET`, `EXTRACTION__OLLAMA_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) into a tmpfs env file.
- Point backend at it via the existing `SETTINGS_ENV_FILE` override — **minimal code change** in [config.py](../haisir-backend/src/shared/config.py) (it already supports an external env-file path). Optionally add a small native OpenBao client for hot-reload later; not required for v1.
- Remove backend secret literals from `common/docker-compose.yml` `environment:` blocks (lines ~85–98, 148–157); they come from the rendered file instead.

### Phase 2 — Deploy-time config from OpenBao — `haisir-deploy`
- Update [template-configs.sh](../haisir-deploy/common/scripts/template-configs.sh) and `deploy.sh` to source `{{PLACEHOLDER}}` values from `bao kv get` instead of `.env.config.sh`. Render into tmpfs.
- Convert `.env` / `.env.config.sh` from stored secrets to **non-secret config only** (ports, hostnames, CIDRs, image tags); secrets move to OpenBao KV. Update `.env.template` accordingly.

### Phase 3 — Dynamic secrets + rotation — `haisir-deploy` (+ DB)
- Enable OpenBao **database secrets engine** for Postgres: backend/worker get short-lived, auto-rotated DB credentials instead of a static `DATABASE_URL` password. This is the headline rotation win and the deepest learning.
- Define rotation policy/TTLs for static KV secrets (Keycloak client secret, CSRF secret, API keys); script rotation. **Now** rotate every currently-existing secret as the cutover ("rotate when ready").
- Wire APISIX admin key / CrowdSec / tunnel token into the same model where feasible.

### Phase 4 — Hardening, audit & docs — `haisir-deploy` + `haisir-specs`
- Backup/restore + disaster-recovery runbook (unseal keys, transit instance, snapshots).
- Audit-log shipping/retention; alert on unusual access.
- **Spec update (required by repo convention):** document the secrets architecture in `target/requirements/` (new file, e.g. `08_secrets_management.md`) + a `decisions.md` entry; reference from [02_auth_and_roles.md](../haisir-specs/target/requirements/02_auth_and_roles.md).

### Future (north star, not now) — SPIFFE/SPIRE
- When you outgrow a single VM / move toward K8s, adopt **SPIFFE/SPIRE** for workload attestation: identities issued by node+workload attestation (no pre-shared secret at all), SVIDs that auth to OpenBao. This is the cloud-agnostic, scale-ready endgame of "identity is something a system *is*." Document as a roadmap item.

---

## Critical files

**haisir-deploy**
- `common/docker-compose.yml` — add `openbao`, `openbao-unseal`, `vault-agent` sidecars; strip secret env blocks.
- `common/scripts/template-configs.sh`, `common/scripts/deploy.sh`, `common/scripts/deploy-lib.sh` — source secrets from OpenBao.
- `common/scripts/certs/` — add `generate-certs-openbao.sh` (model on `generate-certs-ca.sh` / `generate-certs-etcd.sh`).
- `*/.env`, `*/.env.config.sh`, `other/env_templates/.env.template` — reduce to non-secret config.
- New: OpenBao policy files + Vault Agent config + auto-unseal config.

**haisir-backend**
- `src/shared/config.py` — consume the agent-rendered env file via `SETTINGS_ENV_FILE`; (optional) native client for dynamic DB creds + hot reload.

**haisir-specs**
- New `target/requirements/08_secrets_management.md` + `Implementation_planning/decisions.md` entry.

---

## Verification

- **OpenBao up & sealed correctly:** `bao status` shows initialized + auto-unseal working after a restart of the main instance (kill/restart the container; it returns unsealed without manual keys).
- **Machine identity (Era-4):** backend's mTLS cert authenticates (`bao login -method=cert`); a request **without** the client cert is denied — proving token/identity binding.
- **Human path:** an admin logs in via Keycloak OIDC over Tailscale and can read only policy-permitted paths; a non-admin is denied.
- **Backend boots from OpenBao:** start backend with **no secrets in `.env`**; confirm it reads `DATABASE_URL`/`CSRF__SECRET`/Keycloak secret from the agent-rendered file and serves a healthy `/health`; confirm `docker inspect` shows **no secret values** in env.
- **Dynamic DB creds:** confirm backend connects with a short-lived OpenBao-issued Postgres credential; revoke the lease and confirm a new one is issued.
- **Audit:** read a secret, then confirm the access appears in the OpenBao audit log (actor, path, time).
- **Rotation:** rotate the Keycloak client secret in OpenBao; confirm backend picks up the new value (restart or hot-reload) and Keycloak M2M still works.
- **Deploy-time render:** run `template-configs.sh` against OpenBao; confirm APISIX/Keycloak JSON render correctly with no `.env.config.sh` secrets present.

---

## Open decision to confirm at build time
- **OpenBao vs Vault Community Edition** — default OpenBao (open license, same skills). Switch to Vault CE only if brand-name/ecosystem matters more than the BSL constraint.
- **mTLS cert-auth vs Keycloak-JWT auth for machines** — default mTLS (reuses your CA, truest Era-4). Keycloak-JWT is the "single-authority everywhere" variant; can be added later.
