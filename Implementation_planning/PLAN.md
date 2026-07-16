# PLAN — Phase 5.6: Full .env Secrets Elimination (OpenBao, all remaining services)

> Written by `/plan` on 2026-07-16 after two challenger rounds (round 1: 1 Blocker + 3 Majors +
> 4 Minors, all resolved; round 2 verdict: READY TO WRITE, two Minors applied during write-up).
> Task checkboxes live in `TASKS.md`; decisions from this cycle are logged in `decisions.md`.

## Planning Inputs

- **Root goal:** Every remaining secret-shaped value in `{dev,staging,prod}/{.env,.env.config.sh}` is sourced from OpenBao KV, not plaintext — migrated in two internally-gated stages: Class A (deploy-time templated secrets) lands and passes a live verification hard gate BEFORE Class B (postgres/keycloak cold-start passwords) begins; both-sides discipline per path (seed KV AND remove plaintext, atomically); live-verified on the dev stack; migrated secrets rotated at cutover; two independent security reviews; explicit rollback/backout plan for cold-start-critical services; merged to `haisir-deploy` main; specs updated.
- **Root acceptance test:** (1) automated scan of all six env files finds zero secret-shaped values (pgadmin pair whitelisted, documented); (2) dev stack cold-starts healthy end-to-end with every secret KV-sourced; (3) migrated secrets rotated on dev (old values rejected); (4) two independent security-review sign-offs; (5) haisir-deploy main contains the work; (6) specs (decisions/phases/progress/13_secrets_management) updated.
- **Repos:** `[deploy]` (60 tasks), `[specs]` (4 tasks). No `[backend]`/`[frontend]` work — the one task adjacent to backend (T2.4.2) changes only deploy-side artifacts (agent template, KV, policies); backend code and env var names are untouched.
- **Scope locks (user-confirmed 2026-07-15):** pgadmin OUT (dev-only convenience, documented exclusion). TEST_USER_PASSWORD → KV for dev/staging, dropped from the prod realm, Jenkins keeps its own copy (documented dual-store). Extends the 5.5 OpenBao stack — no redesign. Staging/prod live verification AND staging/prod KV seeding deferred pending their OpenBao bring-up (5.5 precedent, documented limitation, protected by fail-closed guards). Backend/worker's migrated secrets untouched except the T2.4.2 delivery-path repoint (flagged, no code change). Phase 6 backlog untouched.

### Embedded design decisions

1. **The deploy-time mechanism is Phase 5.5's dormant `render-deploy-secrets.sh` path, activated — not new infrastructure.** `env-setup.sh`/`deploy-lib.sh`/`template-configs.sh` already hook it behind `OPENBAO_DEPLOY_SECRETS=true`; `deploy.hcl` already grants the 5 KV paths. This phase seeds the paths, wires the two missing provisioning-script hooks, flips the flag, and deletes plaintext.
2. **Class A before Class B, as hard gates.** The dormant render path is proven at templating-level stakes (G3) before any cold-start database credential moves (G4/G5). Gate entries enumerate their full upstream task sets — graph properties, not conventions (5.5 precedent).
3. **Per-key fail-closed rendering via a required-keys manifest.** `render-deploy-secrets.sh` today fails closed only when ZERO paths resolve; partial seeding could template an empty `APISIX_ADMIN_KEY` into a live gateway (a regression). A manifest (`common/openbao/deploy-required-keys.txt`, env-conditional entries) is appended in the same commit as each plaintext removal, making partial states unrepresentable.
4. **Compose `${VAR:?}` guards make un-wrapped invocations fail loudly.** A bare `docker compose up -d` must never interpolate a missing password to `""`.
5. **Seeding is dev-now; staging/prod seeding is a bring-up runbook.** Staging/prod OpenBao instances have never been brought up (5.5 verified dev only) and `render-deploy-secrets.sh` execs into the local `openbao-<env>` container — "seed staging/prod" is not executable today. The seed helper is env-agnostic; the runbook (T6.3) reuses it verbatim at future bring-up. Consequence, accepted and recorded: once plaintext leaves staging/prod env files, those hosts cannot deploy until their OpenBao exists — fail-loud by design, with the T4.4.1 break-glass `.env`-restore as the emergency path.
6. **Backend-admin client credential gets a dedicated `secret/haisir/keycloak-clients` path** readable by both `backend` (its own client cred — no BR-SEC-014 violation) and `deploy` (provisioning templating). Rejected: extending `backend.hcl` to all of `secret/haisir/keycloak` (after G4 that path holds KC_DB/admin passwords — least-privilege violation); rejected: permanent dual-write (ongoing drift failure mode vs one-time plumbing).
7. **Class B delivery mechanism is decided from spike evidence, not assumption.** Whether `haisir-postgres`/`cgr.dev/chainguard/postgres` honor `POSTGRES_PASSWORD_FILE` and whether Keycloak 26 accepts file-based db/bootstrap passwords are unverified; T1.4.x spikes answer them before T4.1.1 decides per service. Fallback where a spike fails: tmpfs runtime env-file delivery with the docker-inspect exposure accepted as documented risk.
8. **`.templated/<env>/` render residue stays on disk, hardened (0700) and accepted.** Moving it to tmpfs would break dev's bind-mount (`dev/docker-compose.yml:102`) and post-reboot restarts. Host-disk compromise is already accepted risk (5.5 seal-key colocation decision) — same trust domain.
9. **First-init vs every-boot semantics are explicit.** `POSTGRES_PASSWORD`/`KEYCLOAK_POSTGRES_PASSWORD` are consulted only at first init (volumes persist); `KC_DB_PASSWORD` every boot; `KC_BOOTSTRAP_ADMIN_*` first boot (+ `KEYCLOAK_ADMIN_PASSWORD` every provisioning run). KV is seeded with verified-live values, and the runbook states that rotating first-init keys in KV does NOT rotate live DB auth (requires ALTER ROLE, 5.5 T4.2.2 precedent).
10. **`KC_DB_*` ≠ `KEYCLOAK_POSTGRES_*` (hash-verified different).** The `KC_DB_USERNAME` role is provisioned by no script today — live auth is whatever the persisted volume holds. T4.2.1 establishes the truth before seeding; T4.2.2 closes the provisioning gap for fresh inits.
11. **Rotation is executed, not just documented** (dev live; staging/prod deferred with seeding) — the migrated values sat in on-disk plaintext for months (5.5 T4.2.2 precedent).

---

## Goal Tree (summary)

```
ROOT: Full .env secrets elimination via OpenBao
├── G1 [deploy]: Fail-closed foundations
│   ├── G1.1: Render pipeline fails closed per required key
│   │   ├── T1.1.1 [deploy]  Required-keys manifest + per-key fail-closed render
│   │   ├── T1.1.2 [deploy]  Unresolved-placeholder guard in template-configs.sh
│   │   └── T1.1.3 [deploy]  On-disk render-residue hardening (0700, .env.runtime gitignore)
│   ├── G1.2: Un-rendered compose invocations fail loudly
│   │   ├── T1.2.1 [deploy]  ${VAR:?} guards in common/docker-compose.yml
│   │   └── T1.2.2 [deploy]  ${VAR:?} guards in dev/docker-compose.yml
│   ├── G1.3: Every provisioning entry point can render from KV
│   │   ├── T1.3.1 [deploy]  setup.sh render hook
│   │   ├── T1.3.2 [deploy]  setup-keycloak.sh render hook
│   │   └── T1.3.3 [deploy]  APISIX helper-script key-inheritance audit/hook
│   └── G1.4: Class B mechanism spikes (pre-decision, load-bearing)
│       ├── T1.4.1 [deploy]  Spike: haisir-postgres POSTGRES_PASSWORD_FILE
│       ├── T1.4.2 [deploy]  Spike: chainguard keycloak-db POSTGRES_PASSWORD_FILE
│       └── T1.4.3 [deploy]  Spike: Keycloak 26 file-based bootstrap/db passwords
├── G2 [deploy]: Class A secrets from KV (dev-seeded; staging/prod via bring-up runbook)
│   ├── G2.1: T2.1.1  Flip OPENBAO_DEPLOY_SECRETS=true (all 3 envs, fail-loud accepted)
│   ├── G2.2: T2.2.1 seed gateway (dev) → T2.2.2 remove plaintext + manifest
│   ├── G2.3: T2.3.1 seed OIDC trio (dev) → T2.3.2 remove + manifest
│   ├── G2.4: T2.4.1 keycloak-clients path + policies → T2.4.2 repoint agent template → T2.4.3 remove + manifest
│   ├── G2.5: T2.5.1 prod test-user skip · T2.5.2 seed (dev) → T2.5.3 remove + env-conditional manifest
│   ├── G2.6: T2.6.1 seed KEYCLOAK_ADMIN_PASSWORD (dev, live-verified) → T2.6.2 remove from .env.config.sh + manifest
│   └── G2.7: T2.7.1 seed TUNNEL_TOKEN (dev) → T2.7.2 cftunnel render wrapper + removal
├── G3 [deploy]: HARD GATE — Class A live verification on dev (9 tasks)
│   └── T3.1 cold fresh-install bring-up (GATE ROOT) → T3.2 templated hash-compare ·
│       T3.3 APISIX auth probe · T3.4 OIDC login E2E · T3.5 backend-admin no-drift ·
│       T3.6 incremental render path · T3.7 plaintext-residue scan · T3.8 prod test-user skip ·
│       T3.9 cftunnel render check
├── G4 [deploy]: Class B cold-start passwords from KV (entries: T4.1.1, T4.2.1 ← all 9 G3)
│   ├── G4.1: T4.1.1  Mechanism decision doc (from spike verdicts)
│   ├── G4.2: T4.2.1 verify live keycloak-db auth → T4.2.2 provision KC_DB_USERNAME role on init
│   ├── G4.3: T4.3.1–3 db · T4.3.4–6 keycloak-db · T4.3.7–9 keycloak (seed → compose change → remove)
│   └── G4.4: T4.4.1  Rollback/backout runbook (sealed-OpenBao break-glass, per-service backout)
├── G5 [deploy]: HARD GATE — Class B live verification on dev (entry: T5.1 ← all 13 G4)
│   └── T5.1 cold bring-up preserved vols → T5.2 fresh-volume first-init · T5.3 docker-inspect check ·
│       T5.4 sealed-OpenBao fails loudly · T5.5 break-glass drill · T5.6 restart-only path ·
│       T5.7 full plaintext-elimination scan
└── G6: Close-out — reviews, rotation, docs, merge
    ├── T6.1 [deploy] security review pass 1 (automated) → T6.2 [deploy] pass 2 (adversarial)
    ├── T6.3 [deploy] ops/rotation runbook additions (6 items incl. staging/prod bring-up seeding)
    ├── T6.4 [deploy] execute rotation of migrated secrets (dev)
    ├── T6.5 [specs] decisions.md entry · T6.6 [specs] phases.md expansion
    ├── T6.7 [specs] progress.md close-out · T6.8 [specs] 13_secrets_management.md KV audit
    └── T6.9 [deploy] merge to haisir-deploy main
```

---

## G1 — Fail-closed foundations

**Goal**: Every mechanism that will carry secrets fails loudly (never silently-empty) before any cutover begins, and the two load-bearing image questions are answered with runnable evidence.
**Goal test**: With the manifest listing the gateway keys and `secret/haisir/gateway` deliberately unseeded on dev, `env-setup.sh` (fresh path, `OPENBAO_DEPLOY_SECRETS=true`) aborts non-zero before any `docker compose` runs; after seeding, `render-deploy-secrets.sh` emits every manifest key non-empty; all three spikes have recorded verdicts.
**Repos**: [deploy]

### G1.1 — Render pipeline fails closed per required key
**Subgoal**: Partial KV seeding or empty values can never produce a partially-secret runtime env or templated config.
**Subgoal test**: Seed 4 of 5 paths with the 5th path's keys in the manifest → render exits 1 naming the missing keys; template-configs.sh with one unresolved `{{PLACEHOLDER}}` exits 1.
**Repos**: [deploy]

##### T1.1.1 [deploy] — Required-keys manifest + per-key fail-closed render
- **Build**: Add `common/openbao/deploy-required-keys.txt` (format `path:KEY[:envs=dev,staging]` — env-conditional entries for dev/staging-only keys like TEST_USER_PASSWORD). In `common/openbao/render-deploy-secrets.sh` (after the path loop at L47-52), collect emitted key names; exit 1 listing any manifest key for the current `APP_ENV` that is missing or empty. Keep the existing zero-paths check. Manifest starts empty; each remove-plaintext task appends its keys in the same commit (both-sides discipline enforced by the graph).
- **Done when**: With `gateway:APISIX_ADMIN_KEY` in the manifest and the gateway path absent from dev KV, the script exits 1 and stderr names `APISIX_ADMIN_KEY`; with an empty manifest, behavior is unchanged.
- **Test**: `APP_ENV=dev render-deploy-secrets.sh; assert exit==1 && stderr contains "APISIX_ADMIN_KEY"` (unseeded gateway path).
- **Depends on**: None.

##### T1.1.2 [deploy] — Unresolved-placeholder guard in template-configs.sh
- **Build**: In `common/scripts/template-configs.sh`, after substitution into `.templated/<env>/`, grep outputs for any remaining `{{[A-Z_]+}}` and for empty-value substitutions of secret placeholders; exit 1 listing offending files (names only, never values).
- **Done when**: Running template-configs.sh with one secret env var unset exits 1 naming the file with the unresolved placeholder.
- **Test**: `unset SESSION_SECRET; template-configs.sh; assert exit != 0`.
- **Depends on**: None.

##### T1.1.3 [deploy] — On-disk render-residue hardening
- **Build**: `template-configs.sh` creates `.templated/<env>/` dirs mode 0700 (and chmods existing ones); add `.env.runtime` to `haisir-deploy/.gitignore` (`.templated` already ignored). The residue itself (rendered configs on the deploy host's disk) is accepted risk — same trust domain as the 5.5 seal-key colocation decision; do NOT move to tmpfs (breaks `dev/docker-compose.yml:102`'s bind-mount and post-reboot restarts). Annotate `other/env_templates/` tracked templates for migrated keys with "now sourced from OpenBao" comments (5.5 precedent).
- **Done when**: Post-templating, `.templated/<env>` dirs are 0700; `.env.runtime` is gitignored; env templates carry the annotation.
- **Test**: `assert stat -c %a .templated/dev == 700 && git check-ignore dev/.env.runtime`.
- **Depends on**: None.

### G1.2 — Un-rendered compose invocations fail loudly
**Subgoal**: A bare `docker compose up -d` without the render wrapper can never interpolate a missing secret to `""`.
**Subgoal test**: With a Class B var removed from the environment, `docker compose config` exits non-zero naming the var (both compose files).
**Repos**: [deploy]

##### T1.2.1 [deploy] — ${VAR:?} guards in common/docker-compose.yml
- **Build**: Change `${POSTGRES_PASSWORD}`, `${KEYCLOAK_POSTGRES_PASSWORD}`, `${KC_DB_PASSWORD}`, `${KC_DB_USERNAME}`, `${KEYCLOAK_ADMIN_PASSWORD}` interpolations (db L35, keycloak-db L325-327, keycloak L372-377) to `${VAR:?VAR required — run via the OpenBao render wrapper}`. Harmless while plaintext still exists.
- **Done when**: `docker compose -f common/docker-compose.yml config` with `KC_DB_PASSWORD` unset exits non-zero naming it.
- **Test**: `env -u KC_DB_PASSWORD docker compose ... config; assert exit != 0`.
- **Depends on**: None.

##### T1.2.2 [deploy] — ${VAR:?} guards in dev/docker-compose.yml
- **Build**: Same `:?` treatment for `KC_DB_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`, `POSTGRES_PASSWORD` in `dev/docker-compose.yml`.
- **Done when**: `docker compose -f dev/docker-compose.yml config` with `POSTGRES_PASSWORD` unset exits non-zero.
- **Test**: `env -u POSTGRES_PASSWORD docker compose ... config; assert exit != 0`.
- **Depends on**: None.

### G1.3 — Every provisioning entry point can render from KV
**Subgoal**: setup.sh and setup-keycloak.sh (and all APISIX_ADMIN_KEY consumers) resolve secrets from OpenBao when the flag is on, matching the hooks already in env-setup.sh, deploy-lib.sh, template-configs.sh.
**Subgoal test**: With Class A keys exported ONLY via seeded dev KV (not the shell), `setup.sh --wait` and `setup-keycloak.sh` both complete under `OPENBAO_DEPLOY_SECRETS=true`.
**Repos**: [deploy]

##### T1.3.1 [deploy] — setup.sh render hook
- **Build**: In `common/scripts/setup.sh` after the `source .env.config.sh` at L117: if `OPENBAO_DEPLOY_SECRETS=true`, `set -a; source <(render-deploy-secrets.sh); set +a`, mirroring env-setup.sh (fail-closed propagation — abort if render fails). deploy.sh L754/766 need no change.
- **Done when**: With `APISIX_ADMIN_KEY` absent from the shell env and present in dev KV, `setup.sh` resolves it and its admin-API calls send the KV value.
- **Test**: `env -u APISIX_ADMIN_KEY OPENBAO_DEPLOY_SECRETS=true setup.sh --wait; assert exit 0`.
- **Depends on**: T1.1.1 [deploy].

##### T1.3.2 [deploy] — setup-keycloak.sh render hook
- **Build**: Same hook in `common/scripts/setup-keycloak.sh` after the L13 `source .env.config.sh`, before the L31-36 admin-token login. deploy.sh L775 needs no change.
- **Done when**: With `KEYCLOAK_ADMIN_PASSWORD`/`KEYCLOAK_CLIENT_SECRET`/`TEST_USER_PASSWORD` absent from the shell and present in KV, `setup-keycloak.sh` completes realm provisioning.
- **Test**: `env -u KEYCLOAK_ADMIN_PASSWORD OPENBAO_DEPLOY_SECRETS=true setup-keycloak.sh; assert exit 0`.
- **Depends on**: T1.1.1 [deploy].

##### T1.3.3 [deploy] — APISIX helper-script key-inheritance audit/hook
- **Build**: Verify `create_route_config.sh`, `create_plugin_config.sh`, `create_global_rule.sh`, `configure-ssl.sh` (X-API-KEY consumers) are only invoked from a parent that has already rendered (setup.sh/env-setup.sh) and inherit `APISIX_ADMIN_KEY` via exported env; add the render hook to any supporting standalone invocation.
- **Done when**: Every APISIX_ADMIN_KEY consumer either inherits from a hooked parent or has its own hook; documented at each entry point.
- **Test**: Audit script: every file using `X-API-KEY.*APISIX_ADMIN_KEY` either contains the hook or is proven child-only; assert list empty.
- **Depends on**: T1.3.1 [deploy].

### G1.4 — Class B mechanism spikes
**Subgoal**: The two unverified image questions are answered with runnable evidence BEFORE any Class B mechanism decision.
**Subgoal test**: Each spike has a recorded works/doesn't verdict with the exact command used.
**Repos**: [deploy]

##### T1.4.1 [deploy] — Spike: haisir-postgres POSTGRES_PASSWORD_FILE support
- **Build**: Run the custom haisir-postgres (chainguard-based) image locally with `POSTGRES_PASSWORD_FILE=/run/secrets/pw` and a mounted file on a throwaway volume; attempt `psql` auth. Record verdict + command in a spike note.
- **Done when**: A written verdict exists: `_FILE` supported yes/no for this image.
- **Test**: `psql -U $POSTGRES_USER -c 'select 1'` against the spike container succeeds (or documented failure).
- **Depends on**: None.

##### T1.4.2 [deploy] — Spike: chainguard keycloak-db POSTGRES_PASSWORD_FILE support
- **Build**: Same spike against `cgr.dev/chainguard/postgres` (the keycloak-db image) — a different image whose entrypoint may diverge from library/postgres.
- **Done when**: Written verdict exists for this image.
- **Test**: `psql` auth with the file-delivered password succeeds (or documented failure).
- **Depends on**: None.

##### T1.4.3 [deploy] — Spike: Keycloak 26 file-based bootstrap/db passwords
- **Build**: Run quay.io Keycloak 26 locally with (a) `db-password` in a mounted `/opt/keycloak/conf/keycloak.conf` (no `KC_DB_PASSWORD` env) and (b) `KC_BOOTSTRAP_ADMIN_PASSWORD` via conf-file/keystore/`*_FILE`; assert boot + admin login. Record which mechanism works per key.
- **Done when**: Written verdict exists per key (db password, bootstrap admin password).
- **Test**: Keycloak health returns ready with zero password env vars in `docker inspect` of the spike container.
- **Depends on**: None.

---

## G2 — Class A secrets from KV (dev-seeded; staging/prod via bring-up runbook)

**Goal**: All Class A secrets (+ TUNNEL_TOKEN) live only in OpenBao KV; `.env.config.sh` in all three envs carries zero secret-shaped values; each path cut over atomically (seed → remove+manifest in lockstep). Seeding executes on dev (the only live OpenBao); the env-agnostic seed helper + T6.3 runbook cover staging/prod at their future bring-up, with the manifest guaranteeing fail-closed until then.
**Goal test**: `grep -E 'APISIX_ADMIN_KEY|SESSION_SECRET|CROWDSEC_BOUNCER_KEY|KEYCLOAK_CLIENT_SECRET|GOOGLE_OAUTH_CLIENT_(ID|SECRET)|KEYCLOAK_BACKEND_ADMIN_CLIENT_(ID|SECRET)|TEST_USER_PASSWORD|KEYCLOAK_ADMIN_PASSWORD' {dev,staging,prod}/.env.config.sh` returns nothing, AND on dev the sha256 of the admin-key field in the templated apisix config equals the sha256 of the KV value.
**Repos**: [deploy]

### G2.1 — Render activation
**Subgoal**: The dormant 5.5 mechanism is switched on so subsequent cutovers take effect.
**Subgoal test**: A dev deploy run logs the render step executing (and succeeding) in env-setup.sh, template-configs.sh, setup.sh, setup-keycloak.sh.
**Repos**: [deploy]

##### T2.1.1 [deploy] — Flip OPENBAO_DEPLOY_SECRETS=true in all three envs
- **Build**: Add `export OPENBAO_DEPLOY_SECRETS=true` to `{dev,staging,prod}/.env.config.sh` (non-secret flag). Render output is sourced after `.env.config.sh`, so KV values override remaining plaintext during transition — safe with partially-seeded KV because the manifest is empty for un-cutover paths. Staging/prod consequence (deploys fail loudly until their OpenBao exists) is deliberate — recorded in T6.5 and covered by T4.4.1's break-glass.
- **Done when**: A dev `env-setup.sh` run shows `check_openbao_ready()` and the render step executing.
- **Test**: Deploy log contains the render invocation with exit 0.
- **Depends on**: T1.1.1 [deploy], T1.3.1 [deploy], T1.3.2 [deploy], T1.3.3 [deploy].

### G2.2 — Gateway secrets from KV
**Subgoal**: APISIX_ADMIN_KEY, SESSION_SECRET, CROWDSEC_BOUNCER_KEY are sourced from `secret/haisir/gateway`.
**Subgoal test**: Dev templating run with the three keys absent from `.env.config.sh` produces a config.yaml whose admin-key hash matches KV, and setup.sh admin calls succeed.
**Repos**: [deploy]

##### T2.2.1 [deploy] — Seed secret/haisir/gateway (dev; env-agnostic helper)
- **Build**: Extend `common/openbao/bootstrap.sh` with an idempotent, env-agnostic `seed_deploy_path gateway` command (admin auth, reads current values from the env's `.env.config.sh`, `bao kv patch secret/haisir/gateway APISIX_ADMIN_KEY=... SESSION_SECRET=... CROWDSEC_BOUNCER_KEY=...`); execute against dev. Staging/prod execution deferred to the T6.3 bring-up runbook (same command).
- **Done when**: `bao kv get secret/haisir/gateway` on dev lists exactly the three key names, each value hash-matching the current `.env.config.sh` value.
- **Test**: `assert sha256(kv APISIX_ADMIN_KEY) == sha256(file value)` on dev (hash compare, never printed).
- **Depends on**: T2.1.1 [deploy].

##### T2.2.2 [deploy] — Remove gateway plaintext + manifest entry (atomic)
- **Build**: In ONE change: delete `APISIX_ADMIN_KEY`, `SESSION_SECRET`, `CROWDSEC_BOUNCER_KEY` from `{dev,staging,prod}/.env.config.sh` (local untracked files — runbook-style edit, 5.5 T4.2.1 precedent) AND append `gateway:APISIX_ADMIN_KEY`, `gateway:SESSION_SECRET`, `gateway:CROWDSEC_BOUNCER_KEY` to `deploy-required-keys.txt` (tracked, committed).
- **Done when**: `grep` finds none of the three keys in any `.env.config.sh`; render on dev fails closed if the gateway path is unseeded.
- **Test**: `assert grep -c 'APISIX_ADMIN_KEY|SESSION_SECRET|CROWDSEC_BOUNCER_KEY' */.env.config.sh == 0`.
- **Depends on**: T2.2.1 [deploy], T1.1.2 [deploy], T1.1.3 [deploy].

### G2.3 — Keycloak realm/OIDC secrets from KV
**Subgoal**: KEYCLOAK_CLIENT_SECRET and GOOGLE_OAUTH_CLIENT_ID/_SECRET are sourced from `secret/haisir/keycloak` for both realm import and APISIX oidc plugin templating.
**Subgoal test**: Realm import + plugin templating succeed on dev with the keys absent from `.env.config.sh`; the client secret in the templated plugin JSON hash-matches KV.
**Repos**: [deploy]

##### T2.3.1 [deploy] — Seed keycloak path: OIDC trio (dev)
- **Build**: `seed_deploy_path keycloak` puts `KEYCLOAK_CLIENT_SECRET`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (current values) into `secret/haisir/keycloak` on dev, using `bao kv patch` (must not clobber keys added by later tasks).
- **Done when**: Key names present in dev KV; values hash-match current files.
- **Test**: `assert sha256(kv KEYCLOAK_CLIENT_SECRET) == sha256(file value)` on dev.
- **Depends on**: T2.1.1 [deploy].

##### T2.3.2 [deploy] — Remove OIDC-trio plaintext + manifest entry (atomic)
- **Build**: One change: delete the three keys from `{dev,staging,prod}/.env.config.sh`; append `keycloak:KEYCLOAK_CLIENT_SECRET`, `keycloak:GOOGLE_OAUTH_CLIENT_ID`, `keycloak:GOOGLE_OAUTH_CLIENT_SECRET` to the manifest.
- **Done when**: Zero grep hits for the three keys in any `.env.config.sh`.
- **Test**: `assert grep count == 0`.
- **Depends on**: T2.3.1 [deploy], T1.1.2 [deploy].

### G2.4 — Backend-admin client credential has ONE KV source of record
**Subgoal**: `KEYCLOAK_BACKEND_ADMIN_CLIENT_ID/_SECRET` (provisioning side) and `OAUTH__KEYCLOAK__ADMIN_CLIENT_ID/_SECRET` (backend runtime side) read the same KV keys from a dedicated `secret/haisir/keycloak-clients` path — drift structurally impossible, least privilege preserved (backend reads only its own client cred, never the Class B passwords that will land in `secret/haisir/keycloak`).
**Subgoal test**: sha256 of the backend vault-agent-rendered admin client secret equals sha256 of the value templated into 06-backend-admin-client.json, both traced to `secret/haisir/keycloak-clients`.
**Repos**: [deploy]

##### T2.4.1 [deploy] — Create keycloak-clients path + policy/render plumbing
- **Build**: Seed `secret/haisir/keycloak-clients` on dev with `KEYCLOAK_BACKEND_ADMIN_CLIENT_ID/_SECRET`, values copied from the existing `secret/haisir/backend` `OAUTH__KEYCLOAK__ADMIN_CLIENT_*` keys (hash-verified equal at seed time). Add the path to: `render-deploy-secrets.sh`'s path loop, `deploy.hcl` (read), `backend.hcl` (read — backend's own client cred, no BR-SEC-014 violation).
- **Done when**: Hash of keycloak-clients secret equals hash of the backend-path copy on dev; deploy + backend identities can both read the new path.
- **Test**: `assert sha256(kv keycloak-clients secret) == sha256(kv backend path secret)` on dev.
- **Depends on**: T2.1.1 [deploy].

##### T2.4.2 [deploy] — Repoint backend vault-agent template to the single source
- **Build**: Update `common/openbao/agent/templates/backend.env(.dynamic).ctmpl` so `OAUTH__KEYCLOAK__ADMIN_CLIENT_ID/_SECRET` render from `secret/haisir/keycloak-clients`; then delete the duplicate keys from `secret/haisir/backend`. Backend code and env var names untouched — this changes only the deploy-side delivery path of an already-migrated secret (flagged exception, user-visible in review).
- **Done when**: Backend container restarts healthy with the agent-rendered env file sourcing the pair from keycloak-clients, and `secret/haisir/backend` no longer contains the pair.
- **Test**: `assert backend /health ok after agent re-render && kv get secret/haisir/backend lacks OAUTH__KEYCLOAK__ADMIN_CLIENT_SECRET`.
- **Depends on**: T2.4.1 [deploy].

##### T2.4.3 [deploy] — Remove backend-admin plaintext + manifest entry (atomic)
- **Build**: One change: delete `KEYCLOAK_BACKEND_ADMIN_CLIENT_ID/_SECRET` from `{dev,staging,prod}/.env.config.sh`; append both to the manifest under `keycloak-clients:`.
- **Done when**: Zero grep hits in any `.env.config.sh`.
- **Test**: `assert grep count == 0`.
- **Depends on**: T2.4.2 [deploy], T1.3.2 [deploy].

### G2.5 — Test-user credential: KV for dev/staging, gone from prod
**Subgoal**: TEST_USER_PASSWORD comes from KV in dev/staging; the prod realm never gets the test user; Jenkins keeps its own credential copy (documented dual-store).
**Subgoal test**: `setup-keycloak.sh` under `APP_ENV=prod` skips 04-user*.json; under `APP_ENV=dev` provisions the user with the KV password and test login succeeds.
**Repos**: [deploy]

##### T2.5.1 [deploy] — Skip test-user provisioning when APP_ENV=prod
- **Build**: Guard both `04-user*.json` loops in `common/scripts/setup-keycloak.sh` (dry-run listing ~L113 and the real provisioning loop ~L561) with a shared prod-skip condition + log line. Add a T6.3 runbook item for one-time manual deletion of the already-provisioned prod test user (prod live ops deferred).
- **Done when**: Running with `APP_ENV=prod` logs the skip and performs zero user-create/update calls for 04-user files.
- **Test**: `APP_ENV=prod setup-keycloak.sh 2>&1 | assert contains skip && no user API call logged`.
- **Depends on**: None.

##### T2.5.2 [deploy] — Seed TEST_USER_PASSWORD (dev; staging via runbook)
- **Build**: `bao kv patch secret/haisir/keycloak TEST_USER_PASSWORD=...` (current value) on dev. Staging seeding deferred to the T6.3 bring-up runbook. Jenkins credential untouched.
- **Done when**: Key present in dev KV (hash-matches file); prod KV will never require it (env-conditional manifest entry in T2.5.3).
- **Test**: `assert kv get on dev has key (hash match)`.
- **Depends on**: T2.1.1 [deploy].

##### T2.5.3 [deploy] — Remove TEST_USER_PASSWORD plaintext + env-conditional manifest entry (atomic)
- **Build**: One change: delete `TEST_USER_PASSWORD` from all three `.env.config.sh`; append `keycloak:TEST_USER_PASSWORD:envs=dev,staging` to the manifest. `tests/config.sh`/`full-setup.sh` consumers get it via the render hook environment.
- **Done when**: Zero grep hits in any `.env.config.sh`; render on prod does NOT require the key.
- **Test**: `assert grep count == 0`.
- **Depends on**: T2.5.1 [deploy], T2.5.2 [deploy], T1.3.2 [deploy].

### G2.6 — Keycloak admin password sourced from KV (provisioning side)
**Subgoal**: `setup-keycloak.sh`'s every-run admin login uses the KV value; the `.env` compose-side copy stays until Class B (T4.3.9).
**Subgoal test**: `setup-keycloak.sh` succeeds on dev with `KEYCLOAK_ADMIN_PASSWORD` absent from `.env.config.sh`.
**Repos**: [deploy]

##### T2.6.1 [deploy] — Seed KEYCLOAK_ADMIN_PASSWORD (dev, live-verified value)
- **Build**: `bao kv patch secret/haisir/keycloak KEYCLOAK_ADMIN_PASSWORD=...` with the CURRENT live value — verify by an admin-token login probe before seeding (first-boot-only caveat: the persisted keycloak-db holds the real auth).
- **Done when**: Key present in dev KV; a dev admin-token request using the KV value returns a token.
- **Test**: `assert token endpoint returns 200 with KV-sourced password` (dev).
- **Depends on**: T2.1.1 [deploy].

##### T2.6.2 [deploy] — Remove KEYCLOAK_ADMIN_PASSWORD from .env.config.sh + manifest (atomic)
- **Build**: One change: delete from `{dev,staging,prod}/.env.config.sh` (NOT from `.env` — that copy is Class B, removed in T4.3.9); append `keycloak:KEYCLOAK_ADMIN_PASSWORD` to the manifest.
- **Done when**: Zero grep hits in any `.env.config.sh`; key still present in `.env` files.
- **Test**: `assert grep .env.config.sh count == 0 && grep .env count == 3`.
- **Depends on**: T2.6.1 [deploy], T1.3.2 [deploy].

### G2.7 — Tunnel token sourced from KV
**Subgoal**: TUNNEL_TOKEN moves to `secret/haisir/infra` via the same render path (deploy.hcl already grants infra; render already reads it — cheaper than documenting an exclusion).
**Subgoal test**: `docker compose config` for `other/services/cftunnel` via the new wrapper resolves TUNNEL_TOKEN with no plaintext copy on disk.
**Repos**: [deploy]

##### T2.7.1 [deploy] — Seed secret/haisir/infra TUNNEL_TOKEN (dev / envs where cloudflared runs locally)
- **Build**: `bao kv put secret/haisir/infra TUNNEL_TOKEN=...` with the current token on dev (other envs via the T6.3 runbook).
- **Done when**: Key present in dev KV, hash-matching the current value.
- **Test**: `assert sha256(kv) == sha256(current value)`.
- **Depends on**: T2.1.1 [deploy].

##### T2.7.2 [deploy] — cftunnel render wrapper + plaintext removal (atomic)
- **Build**: Add `other/services/cftunnel/up.sh`: render `secret/haisir/infra` via `render-deploy-secrets.sh` to a mktemp file on `/dev/shm` (0600, EXIT-trap delete), `docker compose --env-file <tmp> up -d`; same change removes the plaintext token from the cftunnel env file and appends `infra:TUNNEL_TOKEN` to the manifest.
- **Done when**: `up.sh` brings cloudflared up on dev (or `compose config` resolves where dev has no tunnel) and no tracked file contains the token.
- **Test**: `assert up.sh compose config resolves TUNNEL_TOKEN && no value-bearing TUNNEL_TOKEN line in other/services/cftunnel`.
- **Depends on**: T2.7.1 [deploy].

---

## G3 — HARD GATE: Class A live verification on the dev stack

**Goal**: The full Class A cutover is proven live on dev across BOTH code paths (fresh-install env-setup.sh AND deploy-lib.sh incremental render) before any Class B work begins. Staging/prod live verification deferred — documented limitation (T6.5).
**Goal test**: One cold dev bring-up run in which all nine tasks pass in sequence; the run log archived as the gate record.
**Repos**: [deploy]

##### T3.1 [deploy] — Cold fresh-install bring-up on dev (GATE ROOT)
- **Build**: From stopped containers (volumes preserved), run the full dev fresh-install path (`env-setup.sh` flow) with `OPENBAO_DEPLOY_SECRETS=true` end-to-end: OpenBao up → `check_openbao_ready()` → render → RUNTIME_ENV_FILE on /dev/shm → compose up → provisioning (setup.sh, setup-keycloak.sh).
- **Done when**: All services report healthy and both provisioning scripts exit 0 with the render hook active.
- **Test**: `assert docker ps healthy-count == baseline && env-setup.sh exit 0`.
- **Depends on**: T2.2.2, T2.3.2, T2.4.3, T2.5.3, T2.6.2, T2.7.2, T1.2.1, T1.2.2 [deploy].

##### T3.2 [deploy] — Templated-config value hash verification
- **Build**: Script extracting the admin-key field from the templated `apisix_conf` config and the `client_secret` from one templated plugin JSON, sha256 each, compare against sha256 of the corresponding `bao kv get` field — hashes only, values never printed.
- **Done when**: Both hash pairs match on the T3.1 run.
- **Test**: `assert h(config.admin_key)==h(kv APISIX_ADMIN_KEY) && h(plugin.client_secret)==h(kv KEYCLOAK_CLIENT_SECRET)`.
- **Depends on**: T3.1 [deploy].

##### T3.3 [deploy] — APISIX admin API auth probe
- **Build**: Probe the admin API with the rendered key (as env-setup.sh:548 does) and once with a junk key.
- **Done when**: Rendered key → 200; junk key → 401.
- **Test**: `assert status(rendered)==200 && status(junk)==401`.
- **Depends on**: T3.1 [deploy].

##### T3.4 [deploy] — OIDC login end-to-end
- **Build**: Drive a scripted OIDC login for the test user through APISIX openid-connect → Keycloak → authenticated session (exercises SESSION_SECRET, the KEYCLOAK_CLIENT_SECRET realm+etcd coupled pair, and the imported Google IdP config parsing).
- **Done when**: Login completes; an authenticated request through the gateway returns 200.
- **Test**: `assert authenticated GET through gateway == 200`.
- **Depends on**: T3.1 [deploy].

##### T3.5 [deploy] — Backend-admin single-source no-drift check
- **Build**: Compare sha256 of the backend vault-agent-rendered `OAUTH__KEYCLOAK__ADMIN_CLIENT_SECRET` against sha256 of the keycloak-clients KV value; exercise one backend→Keycloak admin operation.
- **Done when**: Hashes equal and the admin operation succeeds.
- **Test**: `assert h(agent-rendered)==h(kv) && admin op success`.
- **Depends on**: T3.1 [deploy].

##### T3.6 [deploy] — Incremental render path (build_compose_cmd) exercised
- **Build**: Run the deploy-lib.sh incremental path against dev locally (simulate the remote host): `<env>/.env.runtime` created umask-077, compose config fully resolves from it, trap-removal leaves no `.env.runtime` behind post-run.
- **Done when**: Incremental deploy of one service succeeds and `.env.runtime` is absent afterward.
- **Test**: `assert incremental deploy exit 0 && [ ! -f dev/.env.runtime ]`.
- **Depends on**: T3.1 [deploy].

##### T3.7 [deploy] — Class A plaintext-residue scan
- **Build**: Automated scan script (under `common/scripts/tests/`): zero Class A key assignments with values in `{dev,staging,prod}/.env.config.sh`, `.templated/<env>` dirs 0700, no rendered fragments outside `.templated`/tmpfs, no leftover `.env.runtime`.
- **Done when**: Scan exits 0 on the T3.1 run's aftermath.
- **Test**: `assert scan exit 0`.
- **Depends on**: T3.1 [deploy].

##### T3.8 [deploy] — Prod test-user skip verified
- **Build**: Run `setup-keycloak.sh` with `APP_ENV=prod` overridden against the dev stack (safe: skip = no writes); confirm the 04-user skip fires; confirm dev realm still has the test user from T3.1.
- **Done when**: Prod-mode run logs the skip with zero user API calls.
- **Test**: `assert log contains skip && user-create call count == 0`.
- **Depends on**: T3.1 [deploy].

##### T3.9 [deploy] — cftunnel token render check
- **Build**: Run `other/services/cftunnel/up.sh` in config-check mode on dev; verify TUNNEL_TOKEN resolves from KV and the tmpfs env fragment is deleted after.
- **Done when**: `compose config` resolves the token; tmp file gone.
- **Test**: `assert config resolves && tmpfile absent`.
- **Depends on**: T3.1 [deploy].

---

## G4 — Class B cold-start passwords from KV

**Goal**: The 4 Class B password groups (POSTGRES_PASSWORD, KEYCLOAK_POSTGRES_PASSWORD, KC_DB_PASSWORD, KEYCLOAK_ADMIN_PASSWORD compose-side) are delivered from KV via the spike-justified mechanism, plaintext removed from all `.env` files, with a written rollback plan — OpenBao is now cold-start-critical for Keycloak.
**Goal test**: On dev, bare `docker compose --env-file dev/.env config` (no render wrapper) exits non-zero naming a missing var; the wrapped invocation resolves fully; no Class B password remains in any env file.
**Repos**: [deploy]

**HARD GATE ENFORCEMENT**: G4's two entry tasks (T4.1.1, T4.2.1) each enumerate the complete G3 task set. Every other G4 task routes through them.

### G4.1 — Per-service delivery mechanism decided from spike evidence
**Subgoal test**: The decision doc names a mechanism per service, each traceable to a spike verdict, with the fallback (tmpfs runtime env-file; docker-inspect exposure accepted as documented risk) invoked only where a spike failed.

##### T4.1.1 [deploy] — Mechanism decision doc (GATE ENTRY)
- **Build**: Write a decision note: for `db`, `keycloak-db`, `keycloak` (KC_DB + bootstrap admin), choose file-based delivery (compose `secrets:`/tmpfs-rendered file + `*_FILE`/conf-file per T1.4.x verdicts) or the fallback env-file path; state rollback implications per choice.
- **Done when**: Doc names one mechanism per service, each citing its spike verdict.
- **Test**: Review checklist: every Class B consumer has exactly one chosen mechanism with a cited spike.
- **Depends on**: T1.4.1, T1.4.2, T1.4.3, T3.1, T3.2, T3.3, T3.4, T3.5, T3.6, T3.7, T3.8, T3.9 [deploy].

### G4.2 — Keycloak DB auth truth established and role gap closed
**Subgoal test**: Documented confirmation of exactly which role/password Keycloak live-authenticates with on dev, and a fresh init provisions the KC_DB_USERNAME role deterministically.

##### T4.2.1 [deploy] — Verify live keycloak-db auth (GATE ENTRY)
- **Build**: On dev, attempt `psql` login to keycloak-db as `KC_DB_USERNAME` with the file value of `KC_DB_PASSWORD`; cross-check `pg_authid`. Record which role+password the persisted volume actually accepts (file values may not match live auth — the role was never provisioned by script).
- **Done when**: A written record states the verified live KC_DB credential identity (match/mismatch vs file values; corrective value if mismatched).
- **Test**: `assert login result recorded (success or documented mismatch + working credential identified)`.
- **Depends on**: T3.1, T3.2, T3.3, T3.4, T3.5, T3.6, T3.7, T3.8, T3.9 [deploy].

##### T4.2.2 [deploy] — Provision KC_DB_USERNAME role on init
- **Build**: In `env-setup.sh` (near L471-472): add an idempotent `CREATE ROLE`/`ALTER ROLE $KC_DB_USERNAME PASSWORD ...` step so fresh inits deterministically provision the role Keycloak connects with (values from the rendered env).
- **Done when**: A fresh keycloak-db init produces a KC_DB_USERNAME role whose password matches the rendered KC_DB_PASSWORD.
- **Test**: `assert psql login as KC_DB_USERNAME with rendered password succeeds on a fresh init`.
- **Depends on**: T4.2.1 [deploy].

### G4.3 — Per-service cutover (seed verified-live → compose change → remove plaintext)
**Subgoal test**: Each service starts healthy on dev with its password delivered by the chosen mechanism and no plaintext copy in env files.

##### T4.3.1 [deploy] — Seed/confirm secret/haisir/db POSTGRES_PASSWORD (dev, verified-live)
- **Build**: `bao kv patch secret/haisir/db POSTGRES_PASSWORD=...` on dev with the CURRENT live value (first-init illusion — verify by `psql` auth before seeding); path already holds dynamic-engine admin creds, patch not put. Staging/prod via T6.3 runbook.
- **Done when**: Key present in dev KV; value verified against live auth; dynamic-engine keys untouched.
- **Test**: `assert psql auth with KV value succeeds (dev) && dynamic-engine keys still present`.
- **Depends on**: T4.1.1 [deploy].

##### T4.3.2 [deploy] — db service compose change (chosen mechanism)
- **Build**: Apply the T4.1.1 mechanism for the `db` service in `common/docker-compose.yml` L35 AND `dev/docker-compose.yml` (e.g. `POSTGRES_PASSWORD_FILE` + tmpfs-rendered secret file created by the render wrapper pre-up; or fallback env-file). One behavior: db receives its password without `.env` plaintext.
- **Done when**: Dev db container starts healthy with the password delivered by the new mechanism.
- **Test**: `assert db healthcheck passing with mechanism active`.
- **Depends on**: T4.3.1 [deploy].

##### T4.3.3 [deploy] — Remove POSTGRES_PASSWORD plaintext + manifest (atomic)
- **Build**: One change: delete `POSTGRES_PASSWORD` from `dev/.env`, `dev/.env.config.sh`, `staging/.env`, `prod/.env`; append `db:POSTGRES_PASSWORD` to the manifest.
- **Done when**: Zero grep hits across the four files.
- **Test**: `assert grep count == 0`.
- **Depends on**: T4.3.2 [deploy].

##### T4.3.4 [deploy] — Seed keycloak path KEYCLOAK_POSTGRES_PASSWORD (dev, verified-live)
- **Build**: `bao kv patch secret/haisir/keycloak KEYCLOAK_POSTGRES_PASSWORD=...` on dev (current live value, `psql`-verified; _USER/_DB stay in `.env` as non-secrets). Staging/prod via runbook.
- **Done when**: Key present in dev KV; value verified via `psql` against keycloak-db.
- **Test**: `assert psql auth as KEYCLOAK_POSTGRES_USER with KV value succeeds (dev)`.
- **Depends on**: T4.1.1 [deploy].

##### T4.3.5 [deploy] — keycloak-db service compose change
- **Build**: Apply the chosen mechanism for `keycloak-db` in `common/docker-compose.yml` L325-327 (per T1.4.2 verdict).
- **Done when**: Dev keycloak-db starts healthy with the new delivery.
- **Test**: `assert keycloak-db healthcheck passing`.
- **Depends on**: T4.3.4 [deploy].

##### T4.3.6 [deploy] — Remove KEYCLOAK_POSTGRES_PASSWORD plaintext + manifest (atomic)
- **Build**: One change: delete from `staging/.env`, `prod/.env` (dev has no copy — verify at implementation); append `keycloak:KEYCLOAK_POSTGRES_PASSWORD` to the manifest.
- **Done when**: Zero grep hits in any env file.
- **Test**: `assert grep count == 0`.
- **Depends on**: T4.3.5 [deploy].

##### T4.3.7 [deploy] — Seed KC_DB_PASSWORD with the VERIFIED-live value (dev)
- **Build**: `bao kv patch secret/haisir/keycloak KC_DB_PASSWORD=...` using the credential identity established by T4.2.1 (NOT blindly the file value). Staging/prod via runbook, with the T4.2.1 caveat recorded.
- **Done when**: Dev KV value passes a live `psql` login as KC_DB_USERNAME.
- **Test**: `assert psql login with KV value succeeds (dev)`.
- **Depends on**: T4.2.1 [deploy], T4.1.1 [deploy].

##### T4.3.8 [deploy] — keycloak service delivery change (KC_DB_PASSWORD + bootstrap admin)
- **Build**: Apply the T4.1.1 mechanism for the `keycloak` service (common compose L372-377 and dev compose): db password per T1.4.3 verdict (consulted EVERY boot — the cold-start-critical edge), `KC_BOOTSTRAP_ADMIN_PASSWORD` from the KV value seeded in T2.6.1.
- **Done when**: Dev keycloak restarts healthy with zero password env vars supplied from `.env`.
- **Test**: `assert keycloak health/ready == true after restart with mechanism active`.
- **Depends on**: T4.3.7 [deploy], T4.2.2 [deploy], T2.6.1 [deploy].

##### T4.3.9 [deploy] — Remove KC_DB_PASSWORD + KEYCLOAK_ADMIN_PASSWORD from .env files + manifest (atomic)
- **Build**: One change: delete `KC_DB_PASSWORD` and `KEYCLOAK_ADMIN_PASSWORD` from `dev/.env`, `dev/.env.config.sh` (KC_DB_* copies), `staging/.env`, `prod/.env` (`KEYCLOAK_ADMIN` username stays — non-secret); append `keycloak:KC_DB_PASSWORD` to the manifest (`KEYCLOAK_ADMIN_PASSWORD` already listed from T2.6.2).
- **Done when**: Zero grep hits for either key in any env file.
- **Test**: `assert grep count == 0`.
- **Depends on**: T4.3.8 [deploy].

### G4.4 — Rollback/backout plan for cold-start-critical services
**Subgoal test**: A reviewer can execute the documented recovery from each failure scenario using only the doc.

##### T4.4.1 [deploy] — Author rollback/backout runbook
- **Build**: New doc: (1) sealed/down OpenBao at cold start — expected fail-loud behavior, break-glass read from offline recovery material (root token/recovery keys per 5.5 bootstrap), temporary `.env` restore with exact commands and re-elimination steps; (2) per-service backout to plaintext (compose revert + env restore); (3) restart semantics (compose does not recreate on rendered-file change — explicit restart required); (4) staging/prod: undeployable-until-OpenBao-bring-up consequence and its recovery path.
- **Done when**: Doc covers all four scenarios with copy-pasteable commands.
- **Test**: Dry-read review: each scenario executable without tribal knowledge (drilled live in T5.5).
- **Depends on**: T4.1.1 [deploy], T4.3.8 [deploy].

---

## G5 — HARD GATE: Class B live verification on the dev stack

**Goal**: The Class B cutover is proven live on dev for both persisted-volume and fresh-volume lifecycles, the exposure constraint checked, and the OpenBao-down emergency path exercised.
**Goal test**: One gate run in which T5.1–T5.7 all pass; run log archived as the gate record.
**Repos**: [deploy]

**HARD GATE ENFORCEMENT**: entry task T5.1 enumerates the complete G4 task set; every other G5 task depends on T5.1.

##### T5.1 [deploy] — Cold bring-up with preserved volumes (GATE ENTRY)
- **Build**: Stop all dev containers (volumes intact), cold-start the full stack through the standard path with Class B delivery active — proves the every-boot KC_DB credential from KV matches the persisted volume's auth.
- **Done when**: All services healthy, keycloak connected to keycloak-db, backend serving.
- **Test**: `assert healthy-count == baseline`.
- **Depends on**: T4.1.1, T4.2.1, T4.2.2, T4.3.1, T4.3.2, T4.3.3, T4.3.4, T4.3.5, T4.3.6, T4.3.7, T4.3.8, T4.3.9, T4.4.1 [deploy].

##### T5.2 [deploy] — Fresh-volume first-init test
- **Build**: In an isolated compose project (or after snapshotting dev volumes), run first init: db and keycloak-db initialize with KV-delivered passwords, KC_DB_USERNAME role provisioned (T4.2.2), keycloak bootstrap admin created from KV, then `setup-keycloak.sh` provisions the realm.
- **Done when**: Fresh stack reaches the same healthy state as T5.1; admin login works.
- **Test**: `assert admin-token request == 200 on the fresh stack`.
- **Depends on**: T5.1 [deploy].

##### T5.3 [deploy] — docker-inspect exposure check
- **Build**: `docker inspect` on db, keycloak-db, keycloak: assert no Class B password value appears in `Config.Env` (file mechanism) — or, where T4.1.1 chose the fallback for a service, assert the documented-risk record exists and matches (compare by hash, never print).
- **Done when**: Per-service assertion passes per its chosen mechanism.
- **Test**: `assert inspect Config.Env contains no value whose sha256 matches any Class B KV value` (fallback services excepted per doc).
- **Depends on**: T5.1 [deploy].

##### T5.4 [deploy] — Sealed-OpenBao cold start fails loudly
- **Build**: Seal (or stop) openbao-dev, attempt a stack cold start: `check_openbao_ready()`/render must abort before compose; the `:?` guards catch any bypass — no partial stack, no container started with an empty credential.
- **Done when**: Cold start aborts with a clear error and zero application containers running.
- **Test**: `assert bring-up exit != 0 && app container count == 0`.
- **Depends on**: T5.1 [deploy].

##### T5.5 [deploy] — Break-glass drill
- **Build**: With OpenBao still sealed, execute the T4.4.1 break-glass procedure verbatim → stack up; then unseal, revert to normal path, re-verify T5.3's clean state.
- **Done when**: Stack recovers using only the runbook; temporary material removed afterward.
- **Test**: `assert stack healthy via break-glass && post-drill residue scan exit 0`.
- **Depends on**: T5.4 [deploy], T4.4.1 [deploy].

##### T5.6 [deploy] — Restart-only path behaves
- **Build**: With the stack running, `docker compose restart keycloak` and an incremental `up -d` (no recreate): verify the delivery mechanism survives restart (files still mounted/rendered; the 5.5 gotcha that rendered-file changes do NOT trigger recreate is captured in T6.3).
- **Done when**: Keycloak healthy after both restart forms.
- **Test**: `assert keycloak ready == true after restart and after up -d`.
- **Depends on**: T5.1 [deploy].

##### T5.7 [deploy] — Full plaintext-elimination scan (root-level residue check)
- **Build**: Extend the T3.7 scan to all six env files + cftunnel env: zero secret-shaped values anywhere (pgadmin pair whitelisted with a pointer to the decisions.md exclusion).
- **Done when**: Scan exits 0 against the final branch state.
- **Test**: `assert scan exit 0`.
- **Depends on**: T5.1 [deploy].

---

## G6 — Close-out: reviews, rotation, docs, merge

**Goal**: Two independent security reviews pass, migrated secrets are rotated on dev, rotation/ops semantics documented, specs reflect reality, work lands on haisir-deploy main.
**Goal test**: Main contains the full diff with both review sign-offs recorded; rotation executed on dev (old values rejected); all four specs files updated and consistent with the merged state.
**Repos**: [deploy] [specs]

##### T6.1 [deploy] — Security review pass 1 (automated)
- **Build**: Run the `security-review` skill methodology against the full phase branch diff; fix or explicitly accept every finding (acceptance requires written rationale).
- **Done when**: Zero unaddressed findings.
- **Test**: Review report attached with all findings resolved/accepted.
- **Depends on**: T5.1, T5.2, T5.3, T5.4, T5.5, T5.6, T5.7 [deploy].

##### T6.2 [deploy] — Security review pass 2 (independent adversarial)
- **Build**: Independent reviewer (no shared context with pass 1) attacks: partial seeding, empty interpolation, inspect exposure, tmpfs/disk residue, break-glass abuse, manifest bypass, staging/prod drift, keycloak-clients policy scoping.
- **Done when**: Second sign-off recorded with zero unaddressed findings.
- **Test**: Adversarial report attached, all items closed.
- **Depends on**: T6.1 [deploy].

##### T6.3 [deploy] — Ops/rotation runbook additions
- **Build**: Extend `common/openbao/README.md`/docs with six items: (1) KEYCLOAK_CLIENT_SECRET coupled-pair rotation (realm + etcd plugin JSON + explicit container restart); (2) first-init caveat — rotating POSTGRES_PASSWORD/KEYCLOAK_POSTGRES_PASSWORD/KC_DB_PASSWORD in KV does NOT rotate live DB auth (ALTER ROLE required, 5.5 T4.2.2 precedent); (3) TEST_USER Jenkins dual-store; (4) backend-admin (keycloak-clients) rotation; (5) one-time manual prod test-user deletion; (6) staging/prod OpenBao bring-up + KV seeding runbook (reuses seed_deploy_path verbatim; until executed, staging/prod deploys fail closed by design); (7) KEYCLOAK_ADMIN_PASSWORD rotation order — change inside Keycloak (admin API) FIRST, then `bao kv patch` (compose-side KC_BOOTSTRAP_ADMIN_* is first-boot-only; setup-keycloak.sh logs in with the KV value every run, fresh inits pick up KV automatically).
- **Done when**: Runbook covers all seven items with commands.
- **Test**: Dry-read: each procedure executable from the doc alone.
- **Depends on**: T5.1, T5.5 [deploy].

##### T6.4 [deploy] — Execute rotation of migrated secrets (dev)
- **Build**: Execute the rotation runbook on dev for the migrated Class A secrets (values sat in on-disk plaintext for months): APISIX_ADMIN_KEY, SESSION_SECRET, CROWDSEC_BOUNCER_KEY, KEYCLOAK_CLIENT_SECRET (coupled-pair procedure), backend-admin client secret (Keycloak regenerate + keycloak-clients KV), TEST_USER_PASSWORD, KEYCLOAK_ADMIN_PASSWORD (T6.3 item-7 order: Keycloak-internal change first, then KV patch), TUNNEL_TOKEN (Cloudflare-side regenerate + KV patch always; live old-token-rejection check only where a tunnel runs on dev, else verified via Cloudflare-side token invalidation) — Class B DB passwords per the first-init caveat (ALTER ROLE + KV patch, 5.5 method). Staging/prod rotation deferred with their seeding (runbook item 6). Explicit container restarts per the T5.6/T6.3 gotcha.
- **Done when**: Runbook executed on dev — a sampled old value is rejected by its service; stack healthy on the new values.
- **Test**: `assert authenticate_with(old_value) fails && stack healthy post-rotation` (sampled per category).
- **Depends on**: T6.3 [deploy], T5.7 [deploy].

##### T6.5 [specs] — decisions.md entry for Phase 5.6
- **Build**: Add to `Implementation_planning/decisions.md`: (1) dormant-mechanism activation over new infrastructure; (2) chicken-and-egg resolution — deploy-host pre-up render + fail-loud + break-glass, OpenBao cold-start-critical for Keycloak accepted; (3) KC_DB findings (KC_DB_* ≠ KEYCLOAK_POSTGRES_*, hash-verified; unprovisioned-role gap + fix); (4) backend-admin dedup via keycloak-clients sub-path (BR-SEC-014 preserved; rejected alternatives recorded); (5) Class B mechanism per service + any accepted docker-inspect risk; (6) pgadmin exclusion + TUNNEL_TOKEN inclusion; (7) staging/prod seeding deferred to bring-up runbook — deploys there fail closed until then (accepted consequence); (8) .templated on-disk residue accepted (0700), tmpfs rejected for dev bind-mount/reboot reasons.
- **Done when**: Entry covers all eight decisions with rationale, dated, at the top of the file.
- **Test**: Checklist review: 8/8 present.
- **Depends on**: T4.1.1 [deploy], T4.2.1 [deploy], T5.3 [deploy], T5.5 [deploy].

##### T6.6 [specs] — phases.md Phase 5.6 expansion
- **Build**: Replace the stub at `Implementation_planning/phases.md` (final section) with the executed scope, the two-gate structure, and outcomes; mark completed.
- **Done when**: Section describes what shipped, matching the merged state.
- **Test**: Cross-check against merged diff: no claim without a corresponding change.
- **Depends on**: T6.9 [deploy].

##### T6.7 [specs] — progress.md close-out
- **Build**: Add Phase 5.6 close-out entry to `Implementation_planning/progress.md` (gate records, review sign-offs, rotation, deferred items: staging/prod OpenBao bring-up + seeding + rotation, prod test-user manual deletion if not yet executed).
- **Done when**: Entry present with dates and the deferred-items list.
- **Test**: Entry lists both gate records, both reviews, and the rotation.
- **Depends on**: T6.2 [deploy], T6.9 [deploy].

##### T6.8 [specs] — 13_secrets_management.md KV-table audit
- **Build**: Update `target/requirements/13_secrets_management.md`: KV path/key table now including gateway, keycloak (full key list), keycloak-clients (new sub-path + policy note), db, infra; Jenkins dual-store note; pgadmin exclusion pointer; remove the "not yet audited against main's current secret inventory" flag.
- **Done when**: Table matches `bao kv` reality (key names) on dev.
- **Test**: Key-name diff between table and dev KV listing is empty.
- **Depends on**: T4.3.9 [deploy], T2.7.2 [deploy].

##### T6.9 [deploy] — Merge to haisir-deploy main
- **Build**: Merge the phase branch to main after both reviews and the dev rotation; regenerate `.secrets.baseline` if tracked-file changes trip detect-secrets (5.5 T1.1.7 precedent).
- **Done when**: `git log main` contains the phase work; T5.7 scan exits 0 on main.
- **Test**: `assert main contains phase HEAD && scan exit 0 on main`.
- **Depends on**: T6.1, T6.2, T6.3, T6.4 [deploy].

---

**Ready now (no pending dependencies):** T1.1.1, T1.1.2, T1.1.3, T1.2.1, T1.2.2, T1.4.1, T1.4.2, T1.4.3, T2.5.1 — all [deploy].

**Sequencing spine:** G1 (11 tasks, foundations + spikes, mostly parallel) → G2 (15 tasks, Class A per-path atomic cutovers) → G3 (HARD GATE, 9 tasks, dev-live) → G4 (13 tasks, Class B design + cutover) → G5 (HARD GATE, 7 tasks, dev-live incl. break-glass drill) → G6 (9 tasks, reviews + rotation + docs + merge; specs tasks ride the close-out).

<!-- plan-baseline: backend:ee3a79e3faf251a75da614d7866169cbac23a1c7 frontend:816194d35c8bdddb804f67b9fded7d5f9d6aa897 deploy:613c0929535b7d7722605169f27081cd33fc5373 -->
