# Prod window 2026-08-16 — outcome and findings

> Capture written at the end of the v2026.7 prod window (deploy completed
> 2026-08-16 01:05 UTC, exit 0, 373s, 13 containers healthy). **This file is a
> holding pen, not the record.** Tomorrow: fold the new items into `phases.md`
> as B12–B18, update the affected TASKS.md entries, and delete this file.

---

## 1. What the window closed

| Item | Status |
|---|---|
| **G5 clause 2** — certbot hook hash assertion | ✅ **PASSED LIVE ON PROD**, its first execution against a real host. Installed hook hashed identical to repo, mode `700` accepted. G5 can now close. |
| **B5** — `allow_admin` wrong host address | ✅ **CONFIRMED FIXED LIVE.** `setup.sh` reached the Admin API; 4 plugin configs, global rules and **27 routes pushed, 0 failed**. The v2026.6 silent-no-push did not recur. |
| **B6 / T6.2.6** — Keycloak admin console public | ✅ **CLOSED.** Routes 13/14/15 pushed with deny-all `127.0.0.1/32`; console returns 403 from outside, realm endpoints stay reachable. |
| **T6.2.7** — access still grantable after deny-all | ✅ **PROVEN** — grant → browser login to the prod console → revoke → 403 returns. Required a workaround, see B12. |
| **Step 5d** — Postgres UID 70→999 | ✅ Both `db-init` and `keycloak-db-init` completed successfully. |
| **Step 11** — datadir UID 65532→1000 | ✅ Verified **by hand** (the step's own check self-skipped, see B11 below). All entries `1000:1000`. |
| **pre_check 16 / B10 risk on prod** | ✅ **Answered.** The rendered whitelist was `127.0.0.1/32`, not a routable address, so the fallback could not have installed a standing public grant. |

---

## 2. New findings to file as B12–B18

### B12 — `keycloak-admin-access.sh` cannot grant an IPv6 address at all (security / deploy) — **the real bug of the night**

`keycloak-admin-access.sh:149` validates the CIDR against an IPv4-only regex and
hard-rejects anything else. There is **no argument** that grants an IPv6 client.

Prod is public-fronted through cftunnel, `real-ip` extracts the true client
address from `cf-connecting-ip`, and a client on an IPv6-capable connection
arrives as IPv6. `ip-restriction` then compares an IPv6 address against an
IPv4-only whitelist and denies — the console 403s no matter what the operator
grants. That is exactly what happened tonight.

**Consequence:** post_deploy B ("prove admin access can still be GRANTED") is
**unprovable through the supported path** on any IPv6-reachable public host.
The deny-all half works fine — an IPv6 client not being in the whitelist is
correctly denied — so this fails in the safe direction, but it means the only
tool for recovering admin access does not work when it is most needed.

**Workaround used tonight** (worked, console reachable, then revoked): sub-path
PATCH straight at the Admin API, mirroring the script's own `set_whitelist`:

```bash
cd ~/haisir-deploy/prod
V6='<operator-ipv6>/128'
( source .env.config.sh
  source ../common/openbao/render-secrets-hook.sh
  render_deploy_secrets_or_die ../common/openbao deploy-secrets
  for r in keycloak-admin keycloak-master-realm keycloak-admin-resources; do
    curl -fsS -X PATCH "http://127.0.0.1:9180/apisix/admin/routes/$r/plugins/ip-restriction/whitelist" \
      -H "X-API-KEY: $APISIX_ADMIN_KEY" -H 'Content-Type: application/json' \
      -d "[\"127.0.0.1/32\",\"$V6\"]" >/dev/null && echo "$r ok"
  done )
```

`revoke` needs no change — it has no validation and reset all three routes correctly.

**Fix:** accept IPv6 in the validator, with its own minimum-prefix floor
(`MIN_GRANT_PREFIX` is an IPv4 concept; `/64` is the sane IPv6 equivalent of a
single customer allocation, `/128` for a stable address). Verify
`lua-resty-ipmatcher` handles the mixed-family whitelist — it should, but that
needs a live check, not an assumption.

### B13 — bare `grant` detects the wrong machine's address (deploy)

The script must run **on the target host** (the Admin API is loopback-only), so
the no-arg path's `curl https://api.ipify.org` (`:137`) returns the **prod VM's**
egress address, never the operator's. The no-arg form is wrong by construction on
any host, not just prod.

`releases/v2026.7/manifest.yaml` post_deploy B asserts the opposite — "On prod,
grant's auto-detect of the caller's public IP via api.ipify.org is CORRECT". It
is not. Fix the script (drop the auto-detect, or make it fail loudly when
`$PWD` is a deploy environment directory) and fix the manifest text.

### B14 — `deploy.sh` Step 3 reports success while writing nothing (deploy) — **cost two failed attempts**

Both the manifest-override and auto-bump paths write image tags with
`sed -i 's|^VAR=.*|VAR=…|'` (`deploy.sh:457`). `sed` **silently no-ops when the
line does not exist** and exits 0, so the step logs
`[SUCCESS] GATEWAY_IMAGE_TAG set to v2026.7` having changed nothing. The failure
surfaces two steps later as an opaque
`invalid reference format` on `registry.haisir.in/haisir-gateway:`.

Same class as pre_check 4's "deploy.sh will NEVER write them", but worse,
because this one *claims* it did.

**Fix:** append the line when absent, or assert the line exists and abort with a
message naming the variable. The auto-bump path's `does not match … — skipping`
message should also distinguish "tag is pinned" from "variable is absent" — they
print identically today, and the second is a hard error dressed as a routine skip.

### B15 — the certbot sudoers grant is undocumented host provisioning (deploy)

Step 2b reads the installed hook under `sudo`, so the deploy user needs
passwordless sudo for `sha256sum` and `stat` on
`/etc/letsencrypt/renewal-hooks/deploy/haisir-sync-certs.sh`. That grant exists
only as prose in one release manifest's pre_check 1. It is not in
`docs/DOCKER_INSTALL_GUIDE.md`, not in `verify-setup.sh`, not anywhere a host
rebuild would pick it up — so a rebuilt prod host reproduces tonight's Step 2b
abort exactly.

Compounding it: the error text is misleading. A missing sudo grant and a missing
file both produce an empty read, and the branch at `deploy-lib.sh:194` reports
both as **"Certbot hook not found"**. Tonight the hook was present and correct;
the message sent us looking for a missing file. The `2>/dev/null` on that remote
command is what discards the real reason.

**Fix:** document the grant as required provisioning next to the rootlesskit pin,
and split the two failure modes in `assert_certbot_hook_matches` — probe
existence and readability separately so the message names the actual cause.

### B16 — release manifest carries three wrong facts (specs)

All three in `releases/v2026.7/manifest.yaml`:

1. **post_deploy A's realm URL is wrong.** It says
   `https://haisir.in/realms/haisir-realm/.well-known/openid-configuration`.
   Route `01-keycloak-realms.json` is `uri: /realms/haisir-realm-{{APP_ENV}}/*`,
   so prod's realm is `haisir-realm-prod`. The documented URL matches no route,
   falls through to catch-all and returns 403 — which reads as "the deploy broke
   app login" when nothing is wrong.
2. **The rollback note's frontend tag is wrong for prod.** It says restoring
   `VERSION=2026.6` returns frontend to `v2026.6-${APP_ENV}`. Prod's frontend
   actually runs the bare `v2026.7` tag (see B17). Following the rollback note as
   written would pull an image that does not exist.
3. **post_deploy B's ipify claim** — see B13.

### B17 — the frontend image tag convention differs between environments and is documented nowhere (deploy)

`haisir-frontend/Jenkinsfile:5` defaults to `v<VERSION>-staging`, and the
manifest describes the pattern as `v${VERSION}-${APP_ENV}` — but **prod runs the
bare `v2026.7`** (log line 1008: `registry.haisir.in/haisir-frontend:v2026.7 Pulled`).
Backend and gateway are bare on both. So the env-suffix applies to staging's
frontend only, and nothing in the repo says so.

**Open question worth answering before the next window:** how did prod's `.env`
lose `BACKEND_IMAGE_TAG`, `FRONTEND_IMAGE_TAG` and `GATEWAY_IMAGE_TAG` in the
first place? All three lines were simply absent (Step 3 read them as empty), yet
prod had been running v2026.6 from those same variables. If something removes
them, it will happen again — and B14 guarantees the next occurrence is equally
opaque.

### B18 — every curl-based post_deploy check returns a false 403 (specs / verification)

`curl` against the public hostname is rejected on user-agent before it ever
reaches `ip-restriction` — confirmed tonight on
`/realms/haisir-realm-prod/.well-known/openid-configuration`, which returned
**403 to curl and valid JSON in a browser**.

This is not a bug in the WAF; it is a bug in **every manifest check written as a
curl one-liner**, including post_deploy A's "must stay 200". Those checks cannot
pass as written, so an operator following the runbook literally sees failures
that are not there — or, worse, learns to ignore them.

**Fix:** rewrite the public-endpoint checks to send a browser user-agent, or
state explicitly that they must be run in a browser. Host-local checks against
`127.0.0.1:9180` are unaffected.

---

## 3. Existing backlog items needing an update, not a new number

- **B2 (collation) — prod readings captured, fix outstanding.** OS is at **2.44**.
  Six databases across two clusters need work:

  | cluster | database | at | action |
  |---|---|---|---|
  | `haisir-db-prod` | `haisir_app_db` | 2.43 | REINDEX CONCURRENTLY → REFRESH |
  | `haisir-db-prod` | `postgres`, `template1` | 2.42 | bare REFRESH |
  | `keycloak-db-prod` | `haisir_keycloak_db` | 2.42 | REINDEX CONCURRENTLY → REFRESH |
  | `keycloak-db-prod` | `postgres`, `template1` | 2.42 | bare REFRESH |
  | both | `template0` | NULL | correct untouched |

  `haisir_keycloak_db` two glibc generations behind on the cluster holding real
  user records is the worst reading either environment has produced, exactly as
  B2 predicted from its months on unpinned `chainguard/postgres:latest`.
  Reindex **before** refresh — refreshing first silences the warning and leaves
  every index built under the old collation.

- **B11 (datadir verification self-skip) — reproduced on prod.** Log line 1292
  printed "Backend container not running" while `haisir-backend-prod` was
  `Up 2 minutes (healthy)`, identical to the 2026-08-15 staging occurrence. The
  copy and chown both succeeded; only the verification was absent. Prod's
  ownership was confirmed by hand instead. Second occurrence — the container-name
  probe is definitively broken, not flaky.

- **B10** — prod's leg is answered (see §1), no code change yet. The text/code
  mismatch it tracks is still open.

---

## 4. Still outstanding on prod after this window

- **OpenBao stack is still on `ghcr.io/openbao/openbao:2.6.0`** — all five
  vault-agent sidecars, `Up 4 days`, unchanged by this deploy. This is by design
  (pre_check 8: separate operator-run lifecycle, deliberately outside deploy.sh's
  drift detection), and `OPENBAO_IMAGE_TAG=2.6.1` is set in prod's `.env` but
  **inert until something recreates them**. The T4.11 cutover ran on staging
  2026-08-13; **prod has not had it.** When it does, the `user: "100:1000"` pin
  from 16983f2 is mandatory — `reg.mini.dev/openbao` ships no default non-root
  USER, and without the pin the server and all five sidecars crash-loop on
  Permission denied. Everything with a `depends_on: vault-agent-* service_healthy`
  (backend, worker, keycloak, db, keycloak-db) blocks behind that, so this is a
  window of its own, not a tail-end task.
- **post_deploy G** — pgvector extension version (`\dx vector` on `haisir-db-prod`).
  Staging found a real 0.8.4-against-0.8.6 residual; prod is more likely stale.
- **post_deploy D** — G6.1's positive half, rendered vs live comparison.
- **post_deploy E** — integration suite. `13-test-prometheus.sh` gets its first
  real execution anywhere (it self-skips on staging), which is the only gate on
  T3.3's metrics-bind fix.
- **post_deploy F** — the 2026-08-08 rollback artifacts are now safe to delete.
  **Keep** `~/certs/haisir.in/ca.pem.bak.*` and `~/certs/ca-backup-*` — a few KB,
  and the only copy of the pre-re-issue certificate.
- **B10's own fix**, **B1** (worker idle-in-transaction), **B3**, **B4** — unchanged.

---

## 5. TASKS.md edits due tomorrow

- **T6.2.6** and **T6.2.7** — close, with tonight's evidence (403 from outside,
  grant→login→revoke round trip). Note that T6.2.7 required B12's workaround, so
  the task passed but the tool it depends on did not.
- **G5** — clause 2 now passes live; the goal can close.
- **G6.1** — prod half still open (post_deploy D).
- **B5**, **B6** — mark closed with the prod evidence.
