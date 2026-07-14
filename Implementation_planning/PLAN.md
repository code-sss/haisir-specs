# PLAN — Phase 5.5: Secrets Management Closeout (OpenBao)

> Written by `/plan` on 2026-07-14 after two challenger rounds (round 1: 2 Blockers + 4 Majors,
> all resolved; round 2 verdict: READY TO WRITE, one item downgraded to a documented limitation
> — see Unresolved section). Task checkboxes live in `TASKS.md`; decisions from this cycle are
> logged in `decisions.md`.

## Planning Inputs

- **Root goal:** OpenBao is live as hAIsir's secrets authority — no plaintext secrets in `.env`/`docker-compose.yml`, machines authenticate by mTLS-bound identity, humans by Keycloak OIDC, every secret read is audited, the backend fails fast rather than silently running with dummy secret defaults — reconciled from the 5-week-parked `feature/secrets-management-openbao` branch onto current `main` and safely merged, with the static-seal unseal mechanism (never run live in any form) proven working before any backend-facing change lands.
- **Repos:** `[deploy]` haisir-deploy (majority — the OpenBao stack itself), `[backend]` haisir-backend (fail-fast secret loading), `[specs]` haisir-specs (already landed spec + decisions entries; only a close-out doc task remains). No `[frontend]` work.
- **Branch:** land on `feature/secrets-openbao-v2` (already created off current `haisir-deploy` main) — NOT the stale `feature/secrets-management-openbao` branch, which stays parked as historical reference.
- **Sequencing constraint (deliberate, confirmed by user — Option 4 from the pre-plan challenger round):** G3 and G4 depend transitively on G2 (the live-verification hard gate) passing in full. Nothing backend-facing or merge-facing starts until the riskiest, most novel piece — a static-seal unseal mechanism that has never run live in any form — is proven working in isolation.
- **Root acceptance (G4):** the reconciled deploy stack and the fail-fast backend work together in a combined smoke test, pass two independent security reviews each, and merge to their respective `main` branches in the correct order (deploy before backend), with `haisir-specs` recording completion.

### Embedded design decisions

1. **Static seal replaces the original two-instance transit-auto-unseal design.** The parked branch's design (a second `openbao-unseal` OpenBao instance whose transit key auto-unseals the main server) is replaced with OpenBao's built-in static seal (a `file://`-sourced key on the same host, with rotation support). Found via an independent design-validation pass (2026-07-14, real web research) — see `decisions.md` 2026-06-05 entry's addendum. On a single-VM topology the two-instance design added a failure mode without adding a real trust boundary (the unseal instance's own keys sit on the same host anyway); the static seal gives equivalent coverage with one fewer always-on service.
2. **Version pin bumped 2.2.0 → 2.6.0.** CVE-2025-54996 (High-severity namespace-path privilege escalation) was patched in OpenBao v2.5.5 (2026-06-17), 12 days after the branch was built at `2.2.0`. v2.6.0 shipped 2026-07-14 (today).
3. **The 3-secret gap must be closed on both sides, not just one.** `EMBEDDING__OLLAMA_API_KEY`, `HAITU__OLLAMA_API_KEY`, `GRADING__OLLAMA_API_KEY` were added to `common/docker-compose.yml` after the branch was built and aren't covered by its Vault Agent templates. Closing this correctly requires adding them to the OpenBao KV layout AND both static+dynamic template variants AND removing the plaintext lines from `docker-compose.yml` — a partial fix (templates without removing the compose lines) would leave the secrets in both places, which is worse than the current state because it would read as closed in tracking while still leaking via `docker inspect`.
4. **The hard gate is a real dependency-graph property, not a documented convention.** Every G3 task and G4's entry point (`T4.1.1`) has the full, explicitly-enumerated G2 task set in its `Depends on:` line — not a shorthand reference to "G2." This was a round-1 challenger finding (M3): shorthand notation isn't machine-resolvable for `TASKS.md`'s "Ready now" computation.
5. **Backend cannot merge/release ahead of deploy.** `T4.6.2 [backend]` (merge to `haisir-backend` main) explicitly depends on `T4.6.1 [deploy]` (merge to `haisir-deploy` main) — not just on its own security review. This closes a round-1 Blocker (B2): without this edge, the fail-fast backend could theoretically ship before the OpenBao stack that's supposed to supply its secrets, recreating exactly the failure mode this migration exists to prevent, just triggered by merge-order instead of by the removed dummy defaults.
6. **Security review depth is now symmetric.** Both `[deploy]` and `[backend]` get two independent passes (an automated `security-review` skill run plus a separate adversarial review, run without reference to each other's findings) — round 1 (M4) found the original draft gave backend only one pass despite its secret-handling logic having just changed.
7. **Ops-runbook tasks use "runbook executed and verified" as Done-when, not a code test.** `T4.2.1` (cutover `.env` files to non-secret config) and `T4.2.2` (rotate every existing secret) are operational actions with no code artifact — this matches the original branch's own T16.9/T16.11, which were correctly left `[~]` partial rather than forced into a unit-testable shape.
8. **T16.9→T16.11's original dependency logic is preserved.** Rotation (`T4.2.2`) isn't considered meaningful until both the KV-only cutover (`T4.2.1`) AND the dynamic-secrets-engine path are proven (`T2.5.2`) — matching the parked branch's original task graph.

---

## Goal Tree (summary)

```
ROOT: OpenBao live as hAIsir's secrets authority
├── G1 [deploy]: Deploy-side reconciliation
│   ├── G1.1: Branch file reconciliation
│   │   ├── T1.1.1 [deploy]  Land net-new common/openbao/ directory files
│   │   ├── T1.1.2 [deploy]  Land net-new generate-certs-openbao.sh
│   │   ├── T1.1.3 [deploy]  Reconcile common/docker-compose.yml
│   │   ├── T1.1.4 [deploy]  Reconcile common/scripts/template-configs.sh
│   │   ├── T1.1.5 [deploy]  Reconcile common/scripts/env-setup.sh
│   │   ├── T1.1.6 [deploy]  Reconcile other/env_templates/.env.template
│   │   └── T1.1.7 [deploy]  Regenerate .secrets.baseline
│   ├── G1.2: Static seal replaces transit-unseal (design change A)
│   │   ├── T1.2.1 [deploy]  Remove openbao-unseal service/config/volumes, add seal "static" block
│   │   ├── T1.2.2 [deploy]  Rework bootstrap.sh cmd_unseal_init() + `all` composite
│   │   ├── T1.2.3 [deploy]  Remove --with-unseal flag from backup.sh
│   │   └── T1.2.4 [deploy]  Remove openbao-unseal cert generation
│   ├── G1.3: Version pin to 2.6.0 (design change B)
│   │   ├── T1.3.1 [deploy]  Bump surviving OpenBao image ref in docker-compose.openbao.yml
│   │   └── T1.3.2 [deploy]  Bump OPENBAO_IMAGE in .env.config.sh.template
│   ├── G1.4: Ollama API key secret-gap closure
│   │   ├── T1.4.1 [deploy]  Add backend Ollama keys to secret/haisir/backend
│   │   ├── T1.4.2 [deploy]  Add worker Ollama keys to secret/haisir/worker
│   │   ├── T1.4.3 [deploy]  Add backend keys to backend.env(.dynamic).ctmpl
│   │   ├── T1.4.4 [deploy]  Add worker keys to worker.env(.dynamic).ctmpl
│   │   └── T1.4.5 [deploy]  Remove plaintext Ollama key lines from docker-compose.yml
│   ├── G1.5: Stack bring-up ordering
│   │   ├── T1.5.1 [deploy]  Add OpenBao-ready gate before main stack start
│   │   └── T1.5.2 [deploy]  Make deploy.sh partial redeploy sidecar-aware
│   └── G1.6: Dynamic Postgres engine compatibility
│       └── T1.6.1 [deploy]  Verify bootstrap.sh db-engine SQL against haisir-postgres image
├── G2 [deploy]: HARD GATE — first-ever live verification (depends on all 21 of G1)
│   ├── G2.1: Stack bring-up with static seal + pinned version
│   │   └── T2.1.1 [deploy]  Bring up OpenBao stack, confirm healthy
│   ├── G2.2: mTLS-bound client authentication
│   │   └── T2.2.1 [deploy]  Request without client cert is denied
│   ├── G2.3: Audit logging proof
│   │   └── T2.3.1 [deploy]  Audit device logs a KV secret read
│   ├── G2.4: Static-seal auto-unseal after restart (the novel/untested claim)
│   │   └── T2.4.1 [deploy]  Restart container, confirm auto-unseal with no manual step
│   ├── G2.5: Dynamic Postgres credentials proof
│   │   ├── T2.5.1 [deploy]  Issue dynamic Postgres creds via database/creds/*, connect
│   │   └── T2.5.2 [deploy]  Verify lease expiry/rotation revokes access
│   └── G2.6: Ollama secrets served via OpenBao templating
│       └── T2.6.1 [deploy]  Verify backend/worker receive Ollama keys via template, not plaintext
├── G3 [backend]: Backend fails fast instead of running with dummy secrets (depends on all 7 of G2)
│   ├── G3.1: CSRF secret and database_url require real values
│   │   ├── T3.1.1 [backend]  Remove default="dummy" from CSRFSettings.secret
│   │   └── T3.1.2 [backend]  Remove default="dummy" from Settings.database_url
│   ├── G3.2: Keycloak admin credentials require real values
│   │   ├── T3.2.1 [backend]  Remove default="" from admin_client_id
│   │   └── T3.2.2 [backend]  Remove default="" from admin_client_secret
│   └── G3.3: Fail-fast behavior proven and documented
│       ├── T3.3.1 [backend]  Add test asserting Settings() raises when required secrets unset
│       └── T3.3.2 [backend]  Correct header comment to match enforced behavior
└── G4: Close-out and merge (entry point depends on all of G2 + G3)
    ├── G4.1 [deploy]: Full-stack gate test
    │   └── T4.1.1 [deploy]  Combined smoke test — reconciled stack + fail-fast backend together
    ├── G4.2 [deploy]: Ops runbooks
    │   ├── T4.2.1 [deploy]  Reduce per-env .env files to non-secret config only
    │   └── T4.2.2 [deploy]  Rotate every existing secret value
    ├── G4.3: Security review pass 1 — automated skill
    │   ├── T4.3.1 [deploy]   Run security-review skill against haisir-deploy diff
    │   └── T4.3.2 [backend]  Run security-review skill against haisir-backend diff
    ├── G4.4: Security review pass 2 — independent adversarial review
    │   ├── T4.4.1 [deploy]   Adversarial review — trust boundaries/secret-zero/policy/HCL
    │   └── T4.4.2 [backend]  Adversarial review — fail-fast correctness, no secret leakage in logs
    ├── G4.5 [specs]: Close-out documentation
    │   └── T4.5.1 [specs]  Add progress.md entry for OpenBao cutover
    └── G4.6: Merge to main
        ├── T4.6.1 [deploy]   Merge feature/secrets-openbao-v2 → haisir-deploy main
        └── T4.6.2 [backend]  Merge backend fail-fast branch → haisir-backend main (gated behind T4.6.1)
```

---

## G1 — Deploy-side reconciliation

**Goal**: The parked `feature/secrets-management-openbao` branch's OpenBao stack lands correctly on current `haisir-deploy` main (via `feature/secrets-openbao-v2`), with the static-seal and version-pin design changes baked in and no plaintext-secret regressions.
**Goal test**: `docker compose -f common/docker-compose.yml -f common/openbao/docker-compose.openbao.yml config` validates with no errors on `feature/secrets-openbao-v2`, and `grep -c OLLAMA_API_KEY common/docker-compose.yml` returns 0 in the `environment:` blocks.
**Repos**: [deploy]

---

### G1.1 — Branch file reconciliation
**Subgoal**: All 22 net-new files and the 5 pre-existing-but-modified files from the parked branch are correctly present on `feature/secrets-openbao-v2`, with genuine main-drift conflicts (in `template-configs.sh`, `env-setup.sh`, `.env.template`) resolved by read-through merge rather than blind overwrite.
**Subgoal test**: `git diff main...feature/secrets-openbao-v2 -- common/scripts/template-configs.sh common/scripts/env-setup.sh` shows both the branch's OpenBao-related additions and main's independent additions present together, with neither side's changes silently dropped.
**Repos**: [deploy]

##### T1.1.1 [deploy] — Land net-new common/openbao/ directory files
- **Build**: Bring all 22 net-new files under `common/openbao/` (docker-compose.openbao.yml, config/*.hcl, bootstrap.sh, agent/*.hcl, agent/templates/*.ctmpl, policies/*.hcl, render-deploy-secrets.sh, rotate-secret.sh, backup.sh, openbao-audit.logrotate, README.md, .gitignore) from `feature/secrets-management-openbao` onto `feature/secrets-openbao-v2` unmodified (base `32e028c`).
- **Done when**: `git diff feature/secrets-management-openbao:common/openbao feature/secrets-openbao-v2:common/openbao` is empty for every file in this set.
- **Test**: `assert git diff --stat <old-branch> <new-branch> -- common/openbao/ | wc -l == 0`
- **Depends on**: None.

##### T1.1.2 [deploy] — Land net-new generate-certs-openbao.sh
- **Build**: Bring `common/scripts/certs/generate-certs-openbao.sh` onto `feature/secrets-openbao-v2` unmodified as a starting point (cleanup happens in T1.2.4).
- **Done when**: File exists at that path and is executable.
- **Test**: `assert os.access("common/scripts/certs/generate-certs-openbao.sh", os.X_OK)`
- **Depends on**: None.

##### T1.1.3 [deploy] — Reconcile common/docker-compose.yml
- **Build**: Merge the branch's new `vault-agent-backend`/`vault-agent-worker` service definitions (referencing `common/openbao/agent/*.hcl`) into current main's `common/docker-compose.yml`, land them pinned to `ghcr.io/openbao/openbao:2.6.0` directly (not 2.2.0), and preserve every other service main has added since the branch was cut.
- **Done when**: `vault-agent-backend` and `vault-agent-worker` services exist in the merged file, `backend`/`worker` have `depends_on: {vault-agent-*: {condition: service_healthy}}`, and no other service main added is missing.
- **Test**: `assert "vault-agent-backend" in yaml.safe_load(open("common/docker-compose.yml"))["services"] and yaml.safe_load(...)["services"]["vault-agent-backend"]["image"] == "ghcr.io/openbao/openbao:2.6.0"`
- **Depends on**: T1.1.1 [deploy].

##### T1.1.4 [deploy] — Reconcile common/scripts/template-configs.sh
- **Build**: Read-through merge: apply the branch's OpenBao-related edits (inserted after `source "$ENV_CONFIG"`, ~line 30) into current main's version of this file, preserving main's independent CIDR-quoting-fix edits (~line 93, inside `replace_placeholders()`) — the two regions don't overlap, so this is additive, not a conflict resolution.
- **Done when**: File contains both the branch's OpenBao template-sourcing logic and main's independently-added CIDR-quoting fix.
- **Test**: `assert "openbao" in open("common/scripts/template-configs.sh").read().lower() and "replace_placeholders" in open("common/scripts/template-configs.sh").read()`
- **Depends on**: None.

##### T1.1.5 [deploy] — Reconcile common/scripts/env-setup.sh
- **Build**: Read-through merge of the branch's OpenBao setup steps (`--env-file` plumbing rewrite, ~lines 129-163+) into current main's version, preserving main's independently-added `POSTGRES_IMAGE_TAG` guard (~line 167) — adjacent but non-overlapping regions, verify by reading both diffs, not by mechanical merge.
- **Done when**: File contains both the OpenBao `--env-file` plumbing and the `POSTGRES_IMAGE_TAG` guard.
- **Test**: `assert "openbao" in open("common/scripts/env-setup.sh").read().lower() and "POSTGRES_IMAGE_TAG" in open("common/scripts/env-setup.sh").read()`
- **Depends on**: None.

##### T1.1.6 [deploy] — Reconcile other/env_templates/.env.template
- **Build**: Merge main's independently-added 62 lines (`HAITU__RERANK_*`, `GRADING__*` placeholders) with the branch's 7 lines of OpenBao annotations into one file — both sides grew this file since the branch was cut, so this is an additive merge, not a conflict resolution.
- **Done when**: File contains all `HAITU__RERANK_*`/`GRADING__*` placeholders from main AND all OpenBao annotation lines from the branch.
- **Test**: `assert "HAITU__RERANK" in content and "openbao" in content.lower()`
- **Depends on**: None.

##### T1.1.7 [deploy] — Regenerate .secrets.baseline
- **Build**: Re-run the repo's `detect-secrets scan` against the fully-reconciled tree and merge into `.secrets.baseline`, rather than taking either branch's stale baseline.
- **Done when**: `detect-secrets audit .secrets.baseline` shows no unaudited findings introduced by the merge.
- **Test**: `assert subprocess.run(["detect-secrets", "scan", "--baseline", ".secrets.baseline"]).returncode == 0`
- **Depends on**: T1.1.1, T1.1.2, T1.1.3, T1.1.4, T1.1.5, T1.1.6 [deploy].

---

### G1.2 — Static seal replaces transit-unseal (design change A)
**Subgoal**: OpenBao is sealed/unsealed via a `seal "static"` stanza sourcing a `file://` key, with the transit-unseal service, config, volumes, and all dead code paths it leaves behind removed.
**Subgoal test**: `bash -n common/openbao/bootstrap.sh` (syntax check) passes AND `grep -c 'seal "transit"' common/openbao/config/openbao-server.hcl` returns 0 AND `grep -c 'seal "static"' common/openbao/config/openbao-server.hcl` returns 1. (Static/dry-run check — no live instance required; validated live at G2.1/G2.4.)
**Repos**: [deploy]

##### T1.2.1 [deploy] — Remove openbao-unseal service/config/volumes, add seal "static" block
- **Build**: Delete `common/openbao/config/openbao-unseal.hcl`. Remove the `openbao-unseal` service block and the `openbao-unseal-data`/`openbao-unseal-token` volumes from `common/openbao/docker-compose.openbao.yml`. In `common/openbao/config/openbao-server.hcl`, remove the `seal "transit" { address = "https://openbao-unseal:8200"; ... }` block and add `seal "static" { key = "file:///path/to/key" }` (or equivalent), generating/mounting the key file as part of this change.
- **Done when**: `grep -c 'seal "transit"' common/openbao/config/openbao-server.hcl` returns 0 and `grep -c 'seal "static"' common/openbao/config/openbao-server.hcl` returns 1.
- **Test**: `assert "seal \"static\"" in open("common/openbao/config/openbao-server.hcl").read()`
- **Depends on**: T1.1.1 [deploy].

##### T1.2.2 [deploy] — Rework bootstrap.sh cmd_unseal_init() and `all` composite
- **Build**: In `common/openbao/bootstrap.sh`, delete `cmd_unseal_init()` (dead code under static seal) and rework the `all` composite command to drop its restart-after-unseal-init step, replacing it with single-instance init appropriate for static seal (server starts already unsealed, no separate init-then-restart cycle).
- **Done when**: `bootstrap.sh all` runs end-to-end against a fresh static-seal OpenBao instance without invoking any transit-unseal-instance logic.
- **Test**: `assert "cmd_unseal_init" not in open("common/openbao/bootstrap.sh").read()`
- **Depends on**: T1.2.1 [deploy].

##### T1.2.3 [deploy] — Remove --with-unseal flag from backup.sh
- **Build**: In `common/openbao/backup.sh`, remove the `--with-unseal` flag and any logic branching on it — there is no second instance to snapshot under static seal.
- **Done when**: `bash common/openbao/backup.sh --help` (or usage output) no longer lists `--with-unseal`.
- **Test**: `assert "--with-unseal" not in subprocess.run(["bash","common/openbao/backup.sh","--help"], capture_output=True, text=True).stdout`
- **Depends on**: T1.2.1 [deploy].

##### T1.2.4 [deploy] — Remove openbao-unseal cert generation
- **Build**: In `common/scripts/certs/generate-certs-openbao.sh`, remove the code path that generates an `openbao-unseal` server cert.
- **Done when**: `grep -c openbao-unseal common/scripts/certs/generate-certs-openbao.sh` returns 0.
- **Test**: `assert "openbao-unseal" not in open("common/scripts/certs/generate-certs-openbao.sh").read()`
- **Depends on**: T1.1.2, T1.2.1 [deploy].

---

### G1.3 — Version pin to 2.6.0 (design change B)
**Subgoal**: Every surviving OpenBao image reference across the stack is pinned to `ghcr.io/openbao/openbao:2.6.0`, with no reference left at `2.2.0`.
**Subgoal test**: `docker compose -f common/openbao/docker-compose.openbao.yml config` resolves the `openbao` service's image to exactly `ghcr.io/openbao/openbao:2.6.0` (config parse only, no live bring-up). `grep -r "openbao:2.2.0" common/ other/` returns no matches after G1.2 and G1.3 land.
**Repos**: [deploy]

##### T1.3.1 [deploy] — Bump surviving OpenBao image ref in docker-compose.openbao.yml
- **Build**: In `common/openbao/docker-compose.openbao.yml`, bump the image tag on the one `openbao` service definition that survives after T1.2.1 removed the `openbao-unseal` service to `ghcr.io/openbao/openbao:2.6.0`.
- **Done when**: The surviving `openbao` service's `image:` field reads `ghcr.io/openbao/openbao:2.6.0`.
- **Test**: `assert yaml.safe_load(open("common/openbao/docker-compose.openbao.yml"))["services"]["openbao"]["image"] == "ghcr.io/openbao/openbao:2.6.0"`
- **Depends on**: T1.2.1 [deploy].

##### T1.3.2 [deploy] — Bump OPENBAO_IMAGE in .env.config.sh.template
- **Build**: In `other/env_templates/.env.config.sh.template`, change `export OPENBAO_IMAGE=ghcr.io/openbao/openbao:2.2.0` to `:2.6.0`.
- **Done when**: `grep "OPENBAO_IMAGE" other/env_templates/.env.config.sh.template` shows `2.6.0`.
- **Test**: `assert "openbao:2.6.0" in open("other/env_templates/.env.config.sh.template").read()`
- **Depends on**: T1.1.1 [deploy].

---

### G1.4 — Ollama API key secret-gap closure
**Subgoal**: `EMBEDDING__OLLAMA_API_KEY`, `HAITU__OLLAMA_API_KEY`, and `GRADING__OLLAMA_API_KEY` are sourced exclusively from OpenBao KV via vault-agent-rendered templates, with zero remaining plaintext occurrences in `docker-compose.yml`'s `environment:` blocks.
**Subgoal test**: A dry-run template render (`bao agent -config=... -exit-after-auth` or equivalent, no live server required) confirms all 3 new keys appear as non-empty placeholders in the rendered template output.
**Repos**: [deploy]

##### T1.4.1 [deploy] — Add backend Ollama keys to secret/haisir/backend KV layout
- **Build**: Extend `common/openbao/bootstrap.sh`'s KV seeding step (and `common/openbao/policies/backend.hcl` path allow-list if scoped per-key) to include `EMBEDDING__OLLAMA_API_KEY` and `HAITU__OLLAMA_API_KEY` under `secret/haisir/backend`.
- **Done when**: `bao kv get secret/haisir/backend` (post-seed) lists both keys.
- **Test**: `assert set(["EMBEDDING__OLLAMA_API_KEY","HAITU__OLLAMA_API_KEY"]).issubset(kv_get("secret/haisir/backend").keys())`
- **Depends on**: T1.1.1 [deploy].

##### T1.4.2 [deploy] — Add worker Ollama keys to secret/haisir/worker KV layout
- **Build**: Extend the same seeding/policy mechanism to include `EMBEDDING__OLLAMA_API_KEY`, `HAITU__OLLAMA_API_KEY`, and `GRADING__OLLAMA_API_KEY` under `secret/haisir/worker`.
- **Done when**: `bao kv get secret/haisir/worker` (post-seed) lists all three keys.
- **Test**: `assert set(["EMBEDDING__OLLAMA_API_KEY","HAITU__OLLAMA_API_KEY","GRADING__OLLAMA_API_KEY"]).issubset(kv_get("secret/haisir/worker").keys())`
- **Depends on**: T1.1.1 [deploy].

##### T1.4.3 [deploy] — Add backend keys to backend.env(.dynamic).ctmpl
- **Build**: In both `common/openbao/agent/templates/backend.env.ctmpl` and `backend.env.dynamic.ctmpl`, add template stanzas rendering `EMBEDDING__OLLAMA_API_KEY` and `HAITU__OLLAMA_API_KEY` from `secret/haisir/backend`.
- **Done when**: Both files contain `{{ with secret "secret/haisir/backend" }}` blocks referencing both keys.
- **Test**: `assert "EMBEDDING__OLLAMA_API_KEY" in open("common/openbao/agent/templates/backend.env.ctmpl").read() and "EMBEDDING__OLLAMA_API_KEY" in open("common/openbao/agent/templates/backend.env.dynamic.ctmpl").read()`
- **Depends on**: T1.1.1, T1.4.1 [deploy].

##### T1.4.4 [deploy] — Add worker keys to worker.env(.dynamic).ctmpl
- **Build**: In both `common/openbao/agent/templates/worker.env.ctmpl` and `worker.env.dynamic.ctmpl`, add template stanzas rendering all three keys from `secret/haisir/worker`.
- **Done when**: Both files contain rendering stanzas for `EMBEDDING__OLLAMA_API_KEY`, `HAITU__OLLAMA_API_KEY`, `GRADING__OLLAMA_API_KEY`.
- **Test**: `assert all(k in open("common/openbao/agent/templates/worker.env.ctmpl").read() for k in ["EMBEDDING__OLLAMA_API_KEY","HAITU__OLLAMA_API_KEY","GRADING__OLLAMA_API_KEY"])`
- **Depends on**: T1.1.1, T1.4.2 [deploy].

##### T1.4.5 [deploy] — Remove plaintext Ollama key lines from docker-compose.yml
- **Build**: Remove all 5 line-occurrences of `EMBEDDING__OLLAMA_API_KEY`, `HAITU__OLLAMA_API_KEY` (backend + worker blocks) and `GRADING__OLLAMA_API_KEY` (worker only) from `common/docker-compose.yml`'s `environment:` blocks, now that vault-agent renders them.
- **Done when**: `grep -c OLLAMA_API_KEY common/docker-compose.yml` returns 0.
- **Test**: `assert "OLLAMA_API_KEY" not in open("common/docker-compose.yml").read()`
- **Depends on**: T1.4.1, T1.4.2, T1.4.3, T1.4.4, T1.1.3 [deploy].

---

### G1.5 — Stack bring-up ordering
**Subgoal**: The OpenBao compose project (a separate stack from the main app compose project) is guaranteed up, bootstrapped, and KV-seeded before the main app stack starts, and partial redeploys keep vault-agent sidecars in sync.
**Subgoal test**: Static analysis — `grep -c 'vault-agent' common/scripts/deploy.sh` returns >0 (confirms T1.5.2 touched the file) AND the readiness-gate script (T1.5.1) exits non-zero when pointed at a deliberately-unreachable OpenBao URL (unit-level check, no live stack needed).
**Repos**: [deploy]

##### T1.5.1 [deploy] — Add OpenBao-ready gate before main stack start
- **Build**: In `common/scripts/env-setup.sh` (or `template-configs.sh`), add an explicit check — poll `bao status`/health endpoint and confirm KV paths are seeded — before the main `docker-compose.yml` stack (whose service definitions were reconciled in T1.1.3) is brought up, failing with a clear message if OpenBao isn't ready.
- **Done when**: Running the main stack bring-up script with OpenBao stopped exits non-zero with a message naming OpenBao as the blocker, instead of hanging on `vault-agent-*` health checks.
- **Test**: `assert subprocess.run(["bash","common/scripts/env-setup.sh"], env={"OPENBAO_STOPPED":"1"}).returncode != 0`
- **Depends on**: T1.1.3, T1.1.4, T1.1.5, T1.2.1, T1.3.1 [deploy].

##### T1.5.2 [deploy] — Make deploy.sh partial redeploy sidecar-aware
- **Build**: In `common/scripts/deploy.sh` Step 6 (`up -d --no-deps ${SERVICES}`), add a check that starts/ensures the relevant `vault-agent-*` sidecar is running before a `--no-deps` redeploy of `backend`/`worker`.
- **Done when**: Redeploying only `backend` via `deploy.sh` with `vault-agent-backend` stopped brings `vault-agent-backend` up first (or fails with a clear message), rather than launching `backend` without its sidecar.
- **Test**: `assert "vault-agent" in open("common/scripts/deploy.sh").read()` and manual verification of the redeploy path with the sidecar stopped.
- **Depends on**: T1.1.3 [deploy].

---

### G1.6 — Dynamic Postgres engine compatibility
**Subgoal**: The branch's Phase 3 dynamic-credential SQL in `bootstrap.sh db-engine` works against current main's custom `haisir-postgres` pgvector image, not just the branch's original `cgr.dev/chainguard/postgres` baseline.
**Subgoal test**: `bao read database/creds/backend-role` against a `db`/`db-init` pair running the current `${DOCKER_REGISTRY}/haisir-postgres:${POSTGRES_IMAGE_TAG}` image returns valid, connectable credentials.

<!-- UNRESOLVED: this subgoal test requires a live OpenBao+Postgres instance, unlike G1.2-G1.5's
static/dry-run checks. Accepted as a documented limitation (round 2 challenger ruling) —
dynamic-secret issuance has no static equivalent, and this check only needs a narrow 2-service
subset live, materially cheaper than G2's full 21-task gate, so it still serves early-isolation.
If it proves to need the full integrated stack in practice, replace with a policy-lint substitute
(static check that the OpenBao policy grants `database/creds/backend-role` read to the backend
role) and treat G2.5 as the sole live proof point. -->

**Repos**: [deploy]

##### T1.6.1 [deploy] — Verify bootstrap.sh db-engine SQL against haisir-postgres image
- **Build**: Run `common/openbao/bootstrap.sh db-engine` configuration/connection SQL against a `db` container built from the current `haisir-postgres` image; fix any incompatibility found (extension load order, role-creation SQL, connection URL template).
- **Done when**: `bootstrap.sh db-engine` completes without error against the `haisir-postgres` image and a subsequent `bao read database/creds/backend-role` returns a usable role.
- **Test**: `assert psycopg2.connect(**dynamic_creds).closed == 0` (connection succeeds with issued creds).
- **Depends on**: T1.1.1 [deploy].

---

## G2 — HARD GATE: first-ever live verification

**Goal**: The reconciled stack, running the never-live-tested static-seal mechanism at the pinned OpenBao version, is proven to actually work end-to-end before any backend-facing change is made. This goal is the hard gate: no G3 or G4 task may begin until every one of its 7 child tasks passes.
**Goal test**: A single continuous live run against `feature/secrets-openbao-v2` passes T2.1.1 through T2.6.1 without manual seal intervention at any point.
**Repos**: [deploy]

---

### G2.1 — Stack bring-up with static seal + pinned version
**Subgoal**: The OpenBao compose project starts, initializes, and reports healthy using the static-seal config and `2.6.0` image.
**Subgoal test**: `docker compose -f common/openbao/docker-compose.openbao.yml up -d` followed by `bao status` reports `Sealed: false`, `Version: 2.6.0`.
**Repos**: [deploy]

##### T2.1.1 [deploy] — Bring up OpenBao stack, confirm healthy
- **Build**: Run `docker compose -f common/openbao/docker-compose.openbao.yml up -d` on `feature/secrets-openbao-v2`, then `bootstrap.sh all`, against a clean environment.
- **Done when**: `bao status` reports `Sealed: false` and `Version: 2.6.0` with no manual unseal step performed.
- **Test**: `assert bao_status()["sealed"] == False and bao_status()["version"] == "2.6.0"`
- **Depends on**: T1.1.1, T1.1.2, T1.1.3, T1.1.4, T1.1.5, T1.1.6, T1.1.7, T1.2.1, T1.2.2, T1.2.3, T1.2.4, T1.3.1, T1.3.2, T1.4.1, T1.4.2, T1.4.3, T1.4.4, T1.4.5, T1.5.1, T1.5.2, T1.6.1 [deploy].

---

### G2.2 — mTLS-bound client authentication
**Subgoal**: Requests to OpenBao without a valid client certificate are rejected; the machine-identity trust boundary is real, not just configured.
**Subgoal test**: `curl` without `--cert`/`--key` against the OpenBao API is denied at the TLS layer or with an auth error; the same request with a valid agent cert succeeds.
**Repos**: [deploy]

##### T2.2.1 [deploy] — Request without client cert is denied
- **Build**: From a live host, send a request to the OpenBao HTTPS listener with no client certificate presented.
- **Done when**: The connection is rejected (TLS handshake failure or 4xx auth error), and the identical request with a valid `vault-agent-backend` client cert succeeds.
- **Test**: `assert requests.get(openbao_url, verify=ca_cert).status_code in (400,401,403) or raises SSLError` (no client cert)
- **Depends on**: T2.1.1 [deploy].

---

### G2.3 — Audit logging proof
**Subgoal**: Every secret read is captured by the audit device with actor, path, and time.
**Subgoal test**: A KV read from an authenticated client produces a corresponding audit log entry within the same second, containing actor identity, the exact KV path read, and a timestamp.
**Repos**: [deploy]

##### T2.3.1 [deploy] — Audit device logs a KV secret read
- **Build**: Perform one authenticated `bao kv get secret/haisir/backend` against the live instance, then inspect the audit log file/stream configured by `openbao-server.hcl`.
- **Done when**: The audit log contains an entry for this read with the requesting identity, the path `secret/haisir/backend`, and a timestamp.
- **Test**: `assert any(e["request"]["path"] == "secret/haisir/backend" for e in read_audit_log())`
- **Depends on**: T2.1.1 [deploy].

---

### G2.4 — Static-seal auto-unseal after restart (the novel/untested claim)
**Subgoal**: The single riskiest untested claim in this whole effort — that a container restart under the static-seal design results in an automatically-unsealed server, with no known-good fallback to compare against (the old transit-unseal design was also never live-tested).
**Subgoal test**: `docker restart openbao` followed by polling `bao status` shows the server return to `Sealed: false` on its own, with zero manual `bao operator unseal` calls.
**Repos**: [deploy]

##### T2.4.1 [deploy] — Restart container, confirm auto-unseal with no manual step
- **Build**: Run `docker restart openbao` against the live instance from T2.1.1, then poll `bao status` every few seconds for up to 60s.
- **Done when**: `bao status` reports `Sealed: false` within the poll window without any manual unseal command being run in between.
- **Test**: `assert poll_until(lambda: bao_status()["sealed"] == False, timeout=60) == True`
- **Depends on**: T2.1.1 [deploy].

---

### G2.5 — Dynamic Postgres credentials proof (Phase 3)
**Subgoal**: The dynamic-credential secrets engine issues working, revocable Postgres credentials against the current `haisir-postgres` image — right-sized as its own subgoal, distinct from the four core go/no-go smoke-test criteria above.
**Subgoal test**: A credential issued via `database/creds/backend-role` connects successfully to `db`, and the same credential is rejected after its lease expires/is revoked.
**Repos**: [deploy]

##### T2.5.1 [deploy] — Issue dynamic Postgres creds via database/creds/*, connect
- **Build**: Run `bao read database/creds/backend-role` against the live instance, then attempt a Postgres connection using the returned username/password against the running `db` container.
- **Done when**: The connection succeeds using only the dynamically-issued credential.
- **Test**: `assert psycopg2.connect(user=creds["username"], password=creds["password"], ...).closed == 0`
- **Depends on**: T2.1.1, T1.6.1 [deploy].

##### T2.5.2 [deploy] — Verify lease expiry/rotation revokes access
- **Build**: Force-revoke (or wait out) the lease from T2.5.1 via `bao lease revoke`, then retry the same Postgres connection.
- **Done when**: The connection attempt with the revoked credential fails with an authentication error.
- **Test**: `assert pytest.raises(psycopg2.OperationalError): psycopg2.connect(user=creds["username"], password=creds["password"], ...)`
- **Depends on**: T2.5.1 [deploy].

---

### G2.6 — Ollama secrets served via OpenBao templating
**Subgoal**: The 3-key Ollama secret-gap closure from G1.4 actually works live — backend and worker containers receive `EMBEDDING__`/`HAITU__`/`GRADING__OLLAMA_API_KEY` via the vault-agent-rendered file, not the (now-removed) plaintext compose lines. Added during the round-1 challenger pass (M1) — G1.6 got an explicit live proof (G2.5) but this analogous secret category originally did not.
**Subgoal test**: `docker exec backend printenv EMBEDDING__OLLAMA_API_KEY` (and the equivalent for `HAITU__OLLAMA_API_KEY` on `backend`, and all three keys on `worker`) returns the OpenBao-KV-seeded value, non-empty, sourced from the rendered file.
**Repos**: [deploy]

##### T2.6.1 [deploy] — Verify backend/worker receive Ollama API keys via template, not plaintext
- **Build**: Exec into the running `backend`/`worker` containers post-T1.4.5 and confirm `EMBEDDING__OLLAMA_API_KEY`/`HAITU__OLLAMA_API_KEY`/`GRADING__OLLAMA_API_KEY` are present and non-empty, sourced from the vault-agent-rendered file.
- **Done when**: `docker exec backend printenv EMBEDDING__OLLAMA_API_KEY` and the same for `HAITU__OLLAMA_API_KEY` on `backend`, and all three on `worker`, are non-empty and match the values seeded into OpenBao KV (not any stale plaintext value).
- **Test**: `assert all(docker_exec(c, "printenv", k).strip() == kv_seeded_value(k) for c, k in [("backend","EMBEDDING__OLLAMA_API_KEY"), ("backend","HAITU__OLLAMA_API_KEY"), ("worker","EMBEDDING__OLLAMA_API_KEY"), ("worker","HAITU__OLLAMA_API_KEY"), ("worker","GRADING__OLLAMA_API_KEY")])`
- **Depends on**: T2.1.1, T1.4.5 [deploy].

---

## G3 — Backend fails fast instead of running with dummy secrets

**Goal**: `haisir-backend` refuses to start when required secrets are missing rather than silently running with `"dummy"`/`""` defaults, closing BR-SEC-019. This goal cannot start until G2 (the live-verification hard gate) has passed in full.
**Goal test**: Starting the backend with `CSRF_SECRET`/`DATABASE_URL`/Keycloak admin env vars unset causes `Settings()` instantiation to raise immediately at import time; starting it with vault-agent-rendered values present succeeds.
**Repos**: [backend]

---

### G3.1 — CSRF secret and database_url require real values
**Subgoal**: `CSRFSettings.secret` and `Settings.database_url` have no silent fallback; missing values fail construction.
**Subgoal test**: Instantiating `Settings()` with `CSRF_SECRET` and `DATABASE_URL` unset in the environment raises `pydantic.ValidationError`.
**Repos**: [backend]

##### T3.1.1 [backend] — Remove default="dummy" from CSRFSettings.secret
- **Build**: In `src/shared/config.py:99`, change `secret: str = Field(default="dummy", min_length=1)` to a required field with no default (`Field(min_length=1)` / `Field(...)`).
- **Done when**: `CSRFSettings()` with no `CSRF_SECRET` env var raises `ValidationError`.
- **Test**: `assert pytest.raises(ValidationError): CSRFSettings()` with env var unset.
- **Depends on**: T2.1.1, T2.2.1, T2.3.1, T2.4.1, T2.5.1, T2.5.2, T2.6.1 [deploy].

##### T3.1.2 [backend] — Remove default="dummy" from Settings.database_url
- **Build**: In `src/shared/config.py:303`, change `database_url: str = Field(default="dummy", min_length=1)` to a required field with no default.
- **Done when**: `Settings()` with no `DATABASE_URL` env var raises `ValidationError`.
- **Test**: `assert pytest.raises(ValidationError): Settings()` with env var unset.
- **Depends on**: T3.1.1 [backend].

---

### G3.2 — Keycloak admin credentials require real values
**Subgoal**: `KeycloakSettings.admin_client_id`/`admin_client_secret` have no silent empty-string fallback.
**Subgoal test**: Instantiating `Settings()` with `KEYCLOAK_ADMIN_CLIENT_ID`/`KEYCLOAK_ADMIN_CLIENT_SECRET` unset raises `pydantic.ValidationError`.
**Repos**: [backend]

##### T3.2.1 [backend] — Remove default="" from admin_client_id
- **Build**: In `src/shared/config.py:79`, change `admin_client_id: str = Field(default="")` to a required field with no default.
- **Done when**: `KeycloakSettings()` with no `KEYCLOAK_ADMIN_CLIENT_ID` env var raises `ValidationError`.
- **Test**: `assert pytest.raises(ValidationError): KeycloakSettings()` with env var unset.
- **Depends on**: T2.1.1, T2.2.1, T2.3.1, T2.4.1, T2.5.1, T2.5.2, T2.6.1 [deploy].

##### T3.2.2 [backend] — Remove default="" from admin_client_secret
- **Build**: In `src/shared/config.py:80`, change `admin_client_secret: str = Field(default="")` to a required field with no default.
- **Done when**: `KeycloakSettings()` with no `KEYCLOAK_ADMIN_CLIENT_SECRET` env var raises `ValidationError`.
- **Test**: `assert pytest.raises(ValidationError): KeycloakSettings()` with env var unset.
- **Depends on**: T3.2.1 [backend].

---

### G3.3 — Fail-fast behavior proven and documented
**Subgoal**: The fail-fast behavior across all four fields is covered by a regression test, and the file's header comment (which already claims "REQUIRED... no defaults") stops contradicting the code.
**Subgoal test**: `uv run pytest tests/unit/shared/test_config.py -k fail_fast` passes, and the header comment at lines 8-10 accurately describes the enforced behavior.
**Repos**: [backend]

##### T3.3.1 [backend] — Add test asserting Settings() raises when required secrets unset
- **Build**: Add a test to `tests/unit/shared/test_config.py` that clears `CSRF_SECRET`, `DATABASE_URL`, `KEYCLOAK_ADMIN_CLIENT_ID`, `KEYCLOAK_ADMIN_CLIENT_SECRET` from the environment and asserts `Settings()` raises `ValidationError`.
- **Done when**: `uv run pytest tests/unit/shared/test_config.py::test_settings_fail_fast_on_missing_secrets -v` passes.
- **Test**: The test itself is the verification.
- **Depends on**: T3.1.2, T3.2.2 [backend].

##### T3.3.2 [backend] — Correct header comment to match enforced behavior
- **Build**: Update the header comment at `src/shared/config.py:8-10` so it accurately reflects that these fields are now enforced as required with no defaults.
- **Done when**: Comment text matches the actual field definitions (no defaults present on the four fields).
- **Test**: Read the file, confirm comment no longer contradicts the `Field(...)` definitions.
- **Depends on**: T3.3.1 [backend].

---

## G4 — Close-out and merge

**Goal**: The reconciled deploy stack and the fail-fast backend are jointly proven, reviewed twice independently (symmetric depth on both repos), and merged to both repos' `main` in the correct order, with `haisir-specs` reflecting completion.
**Goal test**: `haisir-deploy` main and `haisir-backend` main both contain the merged changes, in that order; `haisir-specs` progress.md has a completion entry.
**Repos**: [deploy] [backend] [specs]

---

### G4.1 — Full-stack gate test
**Subgoal**: The reconciled deploy stack (G1, proven live in G2) and the fail-fast backend (G3) work together as one system, not just independently. This is G4's entry point — everything else in G4 depends on it.
**Subgoal test**: Full stack (`common/docker-compose.yml` + `common/openbao/docker-compose.openbao.yml`) starts cold on `feature/secrets-openbao-v2` with the fail-fast backend branch checked out, and `backend`/`worker` reach healthy state consuming only vault-agent-rendered secrets.
**Repos**: [deploy]

##### T4.1.1 [deploy] — Combined smoke test: reconciled stack + fail-fast backend together
- **Build**: Bring up the full stack cold with the fail-fast `haisir-backend` branch built into the `backend`/`worker` images, and confirm no `ValidationError` is thrown (proving vault-agent rendering + fail-fast fields are compatible) and both services report healthy.
- **Done when**: `docker compose ps` shows `backend`/`worker` healthy with no restart loop attributable to config validation failure.
- **Test**: `assert docker_compose_ps()["backend"]["health"] == "healthy"`
- **Depends on**: T2.1.1, T2.2.1, T2.3.1, T2.4.1, T2.5.1, T2.5.2, T2.6.1 [deploy], T3.1.1, T3.1.2, T3.2.1, T3.2.2, T3.3.1, T3.3.2 [backend].

---

### G4.2 — Ops runbooks
**Subgoal**: Real per-env `.env` files are reduced to non-secret config, and every existing secret value is rotated now that the OpenBao path is proven — matching the original decision to rotate at cutover, not before. Both are runbook executions, verified operationally rather than by code test.
**Subgoal test**: Post-cutover, `grep`-ing real per-env `.env` files for secret-shaped values (API keys, passwords, tokens) returns none; post-rotation, the previous secret values no longer authenticate against their respective services.
**Repos**: [deploy]

##### T4.2.1 [deploy] — Reduce per-env .env files to non-secret config only
- **Build**: Execute the runbook: for each real per-env `.env`/`.env.config.sh` file, remove every key now sourced from OpenBao KV (all keys covered by G1.4 and the branch's original template coverage), leaving only non-secret configuration.
- **Done when**: Runbook executed and verified — no secret-shaped values remain in any real per-env `.env` file.
- **Test**: `assert not any(re.search(r"(API_KEY|SECRET|PASSWORD|TOKEN)=\S+", line) for line in open(env_file))`
- **Depends on**: T4.1.1 [deploy].

##### T4.2.2 [deploy] — Rotate every existing secret value
- **Build**: Execute the runbook: rotate every secret currently in OpenBao KV (and any DB-native credentials) now that both the KV-only cutover (T4.2.1) and the dynamic-secrets-engine path (G2.5) are proven — preserving the original design's dependency that rotation isn't meaningful until both hold.
- **Done when**: Runbook executed and verified — old secret values are confirmed rejected by their respective services after rotation.
- **Test**: `assert authenticate_with(old_secret_value) == False` for a sampled rotated key.
- **Depends on**: T4.2.1 [deploy], T2.5.2 [deploy].

---

### G4.3 — Security review pass 1: automated skill
**Subgoal**: The repo's `security-review` skill runs against both repos' diffs for this effort, independently of the adversarial pass in G4.4 so the two don't anchor each other.
**Subgoal test**: `security-review` skill reports no unresolved high/critical findings against either diff.
**Repos**: [deploy] [backend]

##### T4.3.1 [deploy] — Run security-review skill against haisir-deploy diff
- **Build**: Run the `security-review` skill against `feature/secrets-openbao-v2`'s full diff from `haisir-deploy` main; resolve any findings raised.
- **Done when**: Skill run completes with zero unresolved high/critical findings.
- **Test**: `assert security_review_report(deploy_diff).unresolved_high_critical == 0`
- **Depends on**: T4.1.1 [deploy].

##### T4.3.2 [backend] — Run security-review skill against haisir-backend diff
- **Build**: Run the `security-review` skill against the fail-fast branch's diff from `haisir-backend` main; resolve any findings raised.
- **Done when**: Skill run completes with zero unresolved high/critical findings.
- **Test**: `assert security_review_report(backend_diff).unresolved_high_critical == 0`
- **Depends on**: T4.1.1 [deploy].

---

### G4.4 — Security review pass 2: independent adversarial review
**Subgoal**: A separate, independently-conducted review focused specifically on trust boundaries, secret-zero handling, OpenBao policy least-privilege, and HCL misconfiguration risk on the deploy side, and fail-fast correctness + no-secret-leakage-in-logs on the backend side — run without reference to G4.3's findings. Symmetric depth across both repos (round-1 challenger finding M4 — the original draft gave backend only one review pass).
**Subgoal test**: Adversarial review report shows no unresolved finding in any focus area, on either repo.
**Repos**: [deploy] [backend]

##### T4.4.1 [deploy] — Adversarial review of trust boundaries/secret-zero/policy/HCL
- **Build**: Conduct a manual adversarial review of `feature/secrets-openbao-v2`'s diff, focused on: how secret-zero (the initial root/admin credential) is bootstrapped and stored; whether `policies/{admin,backend,deploy,worker}.hcl` grant least-privilege KV/database paths only; and HCL syntax/logic misconfigurations across `openbao-server.hcl` and the agent configs (especially the new static-seal stanza from T1.2.1).
- **Done when**: Review completes with no unresolved finding in any of the four focus areas.
- **Test**: `assert adversarial_review_report(deploy_diff).unresolved_findings == 0`
- **Depends on**: T4.1.1 [deploy].

##### T4.4.2 [backend] — Adversarial review of fail-fast correctness and log hygiene
- **Build**: Conduct a manual adversarial review of the fail-fast branch's diff, focused on: (a) the fail-fast validation actually triggers before any secret-dependent code path executes (no code path reads `settings.database_url`/`settings.csrf.secret`/Keycloak admin creds before `Settings()` construction completes), and (b) no secret values are interpolated into log or exception messages on validation failure (grep the error-handling path for secret-field values appearing in `str()`/`repr()`/log calls).
- **Done when**: Reviewer confirms in writing both (a) and (b) hold, with no unresolved finding.
- **Test**: `assert adversarial_review_report(backend_diff).unresolved_findings == 0`
- **Depends on**: T4.1.1 [deploy].

---

### G4.5 — Close-out documentation
**Subgoal**: `haisir-specs` reflects that the OpenBao cutover is complete (the decisions.md addendum already exists; only the progress entry is needed).
**Subgoal test**: `progress.md` contains a dated entry referencing the OpenBao cutover completion, merge commits, and rotation.
**Repos**: [specs]

##### T4.5.1 [specs] — Add progress.md entry for OpenBao cutover
- **Build**: Add a dated entry to `haisir-specs`' `progress.md` documenting the OpenBao cutover completion — reconciled branch merged, static seal proven live, backend fail-fast landed, secrets rotated.
- **Done when**: `progress.md` contains an entry referencing this work, dated on or after the merge date.
- **Test**: `assert "OpenBao" in open("progress.md").read().split("\n\n")[-1]` (entry present in most recent section).
- **Depends on**: T4.6.1 [deploy], T4.6.2 [backend].

---

### G4.6 — Merge to main
**Subgoal**: Both repos' feature work is merged to their respective `main`, gated on runbooks and both independent security reviews passing — backend explicitly cannot merge/release ahead of deploy.
**Subgoal test**: `haisir-deploy` main contains the reconciled OpenBao stack, merged before `haisir-backend` main contains the fail-fast config changes.
**Repos**: [deploy] [backend]

##### T4.6.1 [deploy] — Merge feature/secrets-openbao-v2 → haisir-deploy main
- **Build**: Merge `feature/secrets-openbao-v2` into `haisir-deploy` main once runbooks and both deploy-side reviews have passed.
- **Done when**: `git log main` on `haisir-deploy` contains the merge commit for `feature/secrets-openbao-v2`.
- **Test**: `assert subprocess.run(["git","merge-base","--is-ancestor","feature/secrets-openbao-v2","main"]).returncode == 0`
- **Depends on**: T4.2.1, T4.2.2, T4.3.1, T4.4.1 [deploy].

##### T4.6.2 [backend] — Merge backend fail-fast branch → haisir-backend main
- **Build**: Merge the fail-fast branch into `haisir-backend` main once the backend security reviews have passed AND the deploy-side merge (T4.6.1) has landed — backend must not ship expecting an OpenBao-sourced secrets path from a deploy stack that hasn't actually shipped yet.
- **Done when**: `git log main` on `haisir-backend` contains the merge commit for the fail-fast branch, and that commit postdates `T4.6.1`'s merge on `haisir-deploy`.
- **Test**: `assert subprocess.run(["git","merge-base","--is-ancestor","<fail-fast-branch>","main"]).returncode == 0`
- **Depends on**: T4.3.2, T4.4.2 [backend], T4.6.1 [deploy].

---

**Ready now (no pending dependencies):** T1.1.1, T1.1.2, T1.1.4, T1.1.5, T1.1.6 [deploy]. Everything else in G1 has at least one dependency; nothing in G2/G3/G4 is ready until the hard gate (G2) clears in full.

**Sequencing spine:** G1 (21 tasks, deploy-only, mostly parallel) → G2 (HARD GATE, 7 tasks, all deploy) → G3 (backend fail-fast, 6 tasks) → G4 (close-out, 10 tasks, deploy+backend+specs, backend merge explicitly gated behind deploy merge).

<!-- plan-baseline: backend:3c53b1a3017b1bf2c48905b0aecf2a69b5cc55f1 frontend:816194d35c8bdddb804f67b9fded7d5f9d6aa897 deploy:b8f650dbd0df98757dd09ad09ff2e36b6bb7c4fc -->
