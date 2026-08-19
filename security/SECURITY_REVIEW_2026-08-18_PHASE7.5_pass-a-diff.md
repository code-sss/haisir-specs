# Phase 7.5 — Independent Security Review, Pass A (T7.6)

Reviewer: Claude Opus 5 (Claude Code), acting as the diff reviewer
Basis: diff
Covered: haisir-deploy `844e8f9..dc89963` (42 commits); haisir-backend `00c2c73..46570b7` (5 commits); haisir-frontend `705833d..6512e83` (4 commits)

**Date:** 2026-08-18
**Scope:** the full Phase 7.5 diff across all three code repos, against the plan-baseline SHAs
recorded in `Implementation_planning/phases.md` (§Phase 7.5 header, "baselined against backend
`00c2c73`, frontend `705833d`, deploy `844e8f9`").

| Repo | Range | Reviewed surface |
|---|---|---|
| `haisir-deploy` | `844e8f9..dc89963` | 83 files, 5 422 insertions / 1 573 deletions (excluding the 7 committed `.env*` config paths — see Method) |
| `haisir-backend` | `00c2c73..46570b7` | 12 files, 136 insertions / 31 deletions |
| `haisir-frontend` | `705833d..6512e83` | 8 files, 55 insertions / 58 deletions |

All three working trees are clean at the range endpoints. Every code-side Phase 7.5 task
(G1–G6, including T6.6.1–T6.6.3) is an ancestor of `dc89963`, satisfying T7.6's
"reviews the tree that ships" precondition.

**Method.** Read the diff hunk by hunk, then fact-check each candidate against the current file
contents and its callers rather than against the task log. Two deliberate deviations, both recorded
because they bound this pass's coverage:

1. **The seven committed `.env*` config paths (`{dev,staging,prod}/.env`,
   `{dev,staging,prod}/.env.config.sh`, `common/.env.config.common.sh`) were reviewed by
   *reference*, never by content.** This repo's standing rule forbids reading any `.env*` file, so
   this pass verified how those files are consumed, synced, permissioned and scanned — it did not
   read what is in them. **Anything that turns on a value inside those files is out of Pass A's
   reach**; the one candidate that did (F3) was resolved by owner confirmation rather than by
   reading. The scanners that would cover the general case (`gitleaks`, `detect-secrets`) are not
   installed on this machine and were not run — that gap is still open and belongs to Pass B.
2. Vendored trees (`gateway-docker/coraza-proxy-wasm/`) and generated dashboards
   (`common/grafana/dashboards/json/*.json`) were skimmed for credentials and pinning only.

**Pass B must be run independently of this document** — end-state basis, fresh session, per T7.6's
independence procedure. Phase 5.6's second pass found a live-credential bug pass 1 had rated clean.

---

## Findings

### F1 — HIGH · fail-open · `bootstrap-host.sh` skips its production confirmation prompt whenever stdin is not a TTY

`common/scripts/bootstrap-host.sh:230`:

```bash
if [[ "$ENV" == "prod" && -t 0 ]]; then
    read -p "Are you sure you want to bootstrap PRODUCTION? (yes/no): " -r
    ...
fi
```

The `-t 0` conjunct means the prompt only exists when stdin is a terminal. Run from CI, from
`nohup`, from a pipe, or with `< /dev/null`, the whole guard evaluates false and the script proceeds
**straight into `prepare_remote` → `rm -rf ${REMOTE_DIR}/common ${REMOTE_DIR}/prod` → full
re-provisioning of production**, with nothing between the command and the wipe.

This inverts the intent. Non-interactive invocation is the case where an unattended destructive run
is *most* likely, not least. `CLAUDE.md` states as fact that "`--env prod` prompts for interactive
confirmation"; that is not true of any non-TTY invocation.

The `-t 0` was presumably added because `read` returns non-zero on EOF and `set -e` would abort —
i.e. the failure mode being avoided *was already the safe one*.

**Aggravating:** per the owner, this script has never been run against a real host, so no operator
has had the chance to notice the prompt not appearing.

**Fix (smaller than the current code):**

```bash
if [[ "$ENV" == "prod" ]]; then
    if [[ ! -t 0 ]]; then
        log_error "Refusing to bootstrap PRODUCTION non-interactively — no confirmation possible."
        exit 1
    fi
    read -rp "Are you sure you want to bootstrap PRODUCTION? (yes/no): "
    [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]] || { log_error "Production bootstrap cancelled"; exit 1; }
fi
```

---

### F2 — HIGH · false assurance · `bootstrap-host.sh` reports "completed successfully" after failed tests and an unreachable endpoint

Two branches in the same script downgrade a failure to a warning and return 0:

- `run_tests()` — `log_warn "Some tests failed (see above)"` then falls through.
- `verify_deployment()` — `log_warn "Endpoint not responding yet (may need more time)"` then falls
  through.

`main()` then unconditionally prints `log_success "${ENV} bootstrap completed successfully!"`.
The script has **no path that exits non-zero after `run_full_setup`**, so a cold-start bring-up that
produced a stack failing its own integration suite and serving nothing on its endpoint still exits 0
and prints a success banner.

This is the exact defect class the phase spent itself closing — B11, B20, B22, and the fail-closed
discipline written into `create_route_config.sh`, `render-secrets-hook.sh` and `deploy.sh`'s
`services:` parse. It survived into the one new script in the range that has never been executed.

**Fix:** have `run_tests` return the suite's exit status and `main` propagate it; keep
`verify_deployment` a warning if the settle time is genuinely unpredictable, but then say
"bootstrap finished — endpoint not yet responding" rather than "completed successfully".

---

### F3 — MEDIUM · no provenance · the two monitoring-profile exporter variables reach a host by no mechanism this phase left standing

*(Filed HIGH on first pass as a possible plaintext credential in a committed file. **Resolved down to
MEDIUM 2026-08-18**: the owner confirms `POSTGRES_EXPORTER_DSN` is not assigned in any of the seven
committed paths, and `releases/v2026.7/PROD_WINDOW.md:235` independently records "Prod has no
`postgres_exporter` role and no `POSTGRES_EXPORTER_DSN` in KV". The credential-in-git branch is
closed. The other branch is the finding.)*

`common/docker-compose.yml:874` and `:908`:

```yaml
      - DATA_SOURCE_NAME=${POSTGRES_EXPORTER_DSN}
      - --nginx.scrape-uri=${NGINX_EXPORTER_SCRAPE_URI}
```

Verified provenance of both, repo-wide:

| Source | `POSTGRES_EXPORTER_DSN` | `NGINX_EXPORTER_SCRAPE_URI` |
|---|---|---|
| `common/openbao/` (any policy, template, or `deploy-required-keys.txt` entry) | absent from the entire tree | absent from the entire tree |
| the seven committed `.env*` paths | not assigned (owner-confirmed) | not assigned (owner-confirmed) |
| `other/env_templates/.env.template` | referenced by `common/prometheus/prometheus.yml:37` as the source | present (line 41) |
| a `${VAR:?}` compose guard | none | none |

`other/env_templates/.env.template` is the file an operator copies when standing up a host by hand.
**BR-SEC-022 is precisely what removed that file's authority**: `{env}/.env` is committed,
`prepare_remote` wipes `${REMOTE_DIR}/${env}`, and `sync_files_to_remote` replaces the host copy from
the release on every deploy. "A value that exists only on a host does not exist" is the rule's own
wording — and a value that exists only in a *template* the release never reads has even less standing.
So both variables are, today, sourced from nothing that survives a deploy.

`common/docker-compose.yml` carries exactly **one** `${VAR:?}` guard in the whole file
(`:464`, `KC_DB_USERNAME`), so the Class A fail-closed pattern BR-SEC-019 describes does not cover
these. Starting the `monitoring` profile therefore interpolates both to the empty string:
postgres-exporter comes up with an empty DSN and nginx-exporter with an empty scrape URI, and
Prometheus reports two targets simply down with nothing naming why. That is the phase's own
recurring defect shape (B11/B20/B22) — an absent value and a broken value producing the same silent
answer — reproduced in the one profile the phase added and never started.

**Not currently exploitable**, and correctly out of scope for v2026.7: the `monitoring` profile has
never been activated on staging or prod and `deploy.sh` does not activate it. This is a gate to close
*before* that profile first ships, not a live exposure.

**Fix, and the decision it forces.** `NGINX_EXPORTER_SCRAPE_URI` is not a credential — give it a
`${VAR:?...}` guard so an unset value fails at compose time instead of producing a dead exporter,
or drop the service until a real scrape target exists on `haisir-net` (its own comment already says
there is none). `POSTGRES_EXPORTER_DSN` **is** a credential and needs an explicit owner call, because
the phase's own precedent and the tool disagree: `GRAFANA_ADMIN_PASSWORD` got a KV path, a policy, a
`vault-agent-grafana` sidecar and `$__file{}` delivery so it never becomes an env var (B8), while
postgres_exporter 0.20.1 has no file-based DSN option at all — which is exactly the ceiling the
`ponytail:` comment at `:862` names. The nearest equivalent posture is a dedicated
`secret/haisir/monitoring` path plus a `deploy-required-keys.txt` entry (`envs=staging,prod`) so the
existing per-key gate aborts the render on an unseeded value, accepting the `docker inspect`
exposure as the documented residual. Whichever way it goes, record it — an undecided credential is
how this one ended up with no source at all.

### F4 — MEDIUM · fail-open · `create_route_config.sh`'s whitelist-preservation read treats an HTTP 401/403 as "nothing to preserve"

`common/scripts/create_route_config.sh:222-232`. The preservation read is:

```bash
if live_raw=$(curl -s --connect-timeout 5 --max-time 15 \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    "${APISIX_ADMIN_URL}/apisix/admin/routes/${config_id}" 2>/dev/null); then
    live_wl=$(printf '%s' "$live_raw" | jq -c '.value.plugins[...].whitelist // empty' ...)
else
    live_wl=""
    log_warn "  ⚠ could not read live route ... Any active grant is now revoked"
fi
```

`curl` without `--fail` **exits 0 on an HTTP 401 or 403** — the body is a JSON error object, `jq`
finds no `.value.plugins`, and `live_wl` comes back empty. That lands in the `[[ -z "$live_wl" ]]`
branch, whose entire body is `:` — a silent no-op. The explicit warning the author wrote for exactly
this situation is only reachable on a *transport* failure.

Consequence: with a wrong or rotated `APISIX_ADMIN_KEY` that still permits the subsequent `PUT`
(different key scope) — or in any partial-auth state — a deploy silently discards a live operator
grant and re-publishes the template's deny-all, with no line in the log saying so. This is B10 as
filed, still present in the new code path. It is also the one branch `keycloak-admin-access.sh`'s
header depends on: "create_route_config.sh deliberately preserves a live whitelist so a deploy can
never revoke access mid-session."

The B22 prune added later in the same file *does* fail closed on an unauthenticated list (`jq -er`
+ `exit 1`), which is why the 2026-08-18 staging log's `27 rendered, 1 pruned` is retroactive
evidence that this run's reads were genuine. That is a lucky ordering property, not a guard.

**Fix (one line, plus one branch to keep 404 quiet as the comment intends):**

```bash
http_code=$(curl -s -o "$tmp" -w '%{http_code}' --connect-timeout 5 --max-time 15 \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" "${APISIX_ADMIN_URL}/apisix/admin/routes/${config_id}")
case "$http_code" in
    2*)  live_wl=$(jq -c '.value.plugins["ip-restriction"].whitelist // empty' "$tmp") ;;
    404) live_wl="" ;;                       # genuinely nothing live — stay quiet
    *)   live_wl=""; log_warn "  ⚠ Admin API returned HTTP ${http_code} ..." ;;
esac
```

---

### F5 — MEDIUM · wrong-address grant · `keycloak-admin-access.sh grant` with no argument resolves the *host's* egress IP, not the operator's

`common/scripts/keycloak-admin-access.sh:130-140`. With no CIDR argument the script runs
`curl https://api.ipify.org` and grants `${ip}/32`.

The script's own header says **"Run it on the target host (the Admin API is not published
publicly)."** On the target host, `api.ipify.org` returns *the host's* public egress address, not the
operator's. So the default path grants the wrong address in the ordinary case, and grants it
permanently (the script's own banner: "THIS GRANT DOES NOT EXPIRE").

Worse than useless: if the host sits behind a shared NAT or a cloud NAT gateway, that `/32` is
shared with every other workload behind the same egress address, and the Keycloak admin console
becomes reachable from all of them. The `MIN_GRANT_PREFIX=24` guard does not help — a `/32` of a
shared NAT is still a `/32`.

The correct address is only knowable to the operator (it is whatever `real-ip` derives from
`cf-connecting-ip` for *their* browser), which is why the 2026-08-18 session note already says
"pass the `/32` explicitly, since auto-detect resolves the caller's public IP". That workaround is
documented in a session log; the code still defaults to the unsafe path.

Secondary dependency: the control now depends on a third-party service (`api.ipify.org`) being
reachable and truthful.

**Fix (deletes code):** make the CIDR argument required. `grant` with no argument prints
`usage` and exits 1.

---

### F6 — MEDIUM · unverified delivery · rendered `alertmanager.yml` is mode 600 on the host but bind-mounted into a container that does not run as the host user

`common/scripts/template-configs.sh:279-303` renders `common/prometheus/.templated/$APP_ENV/alertmanager.yml`
and `replace_placeholders` ends with `chmod 600 "$output_file"` (correct — the file holds
`ALERT_SLACK_WEBHOOK` in cleartext). `common/docker-compose.yml` bind-mounts that path into the
`alertmanager` service, which declares no `user:` and therefore runs as its image's default uid.

A 600 file owned by the deploy user is unreadable by any other uid. Under rootless Docker the
container uid maps into the user's subuid range, not to the deploy user, so the mount is expected to
fail to read — Alertmanager would crash-loop on config load. This is the same shape as the
already-recorded OpenBao failure (`reg.mini.dev/openbao` needing `user: "100:1000"` pinned to start
under rootless Docker), and the same shape as the `db-init`/`keycloak-db-init` volume-ownership gap
that Step 5d was added to close.

Not confirmed live, because the `monitoring` profile has never been started on staging or prod.
Filed at MEDIUM rather than HIGH for that reason: it is an availability defect on first deploy, and
the alternative resolutions (loosening to 640 with a matching gid, or `user:` pinning) have a
security dimension worth deciding deliberately rather than discovering at 2am. **Do not "fix" it by
chmod 644** — the file contains the webhook.

---

### F7 — LOW · exposure widening · APISIX's Prometheus export server moved from container-loopback to `0.0.0.0` with no authentication and no network segmentation

`common/apisix_conf/config.yaml:140` (and `dev/apisix_conf/config.yaml:56`):
`plugin_attr.prometheus.export_addr.ip` changed `127.0.0.1` → `0.0.0.0`.

The change itself is correct and fixes a real defect (T3.3: the scrape target could never connect,
so `TargetDown` fired permanently and the dashboard was always empty). The host publish is correctly
narrowed — `"127.0.0.1:9091:9091"` in `common/docker-compose.yml:653`.

What is not addressed is that `haisir-net` is a single flat network shared by every service in the
stack — frontend, backend, worker, keycloak, etcd, db, five exporters, grafana, prometheus,
alertmanager, five vault-agent sidecars. The metrics endpoint carries no authentication, so any one
of those containers, if compromised, can now read APISIX's full route inventory, upstream names,
per-route request counts and status-code distribution. Before the change it could not.

That is reconnaissance value, not credentials, and every alternative (a dedicated monitoring
network, an mTLS scrape) is real work. Filed as LOW and informational: **accept it explicitly** in
the phase record rather than leaving it as an unremarked side effect of a bug fix.

---

### F8 — LOW · over-permissive mode · APISIX's `config.yaml` is written into the shared config volume as mode 666

`common/scripts/deploy.sh:865` (Step 8), unchanged in substance by this range but re-touched by it
when the image moved from `alpine:latest` to `reg.mini.dev/busybox:1.38.0`:

```bash
sh -c "cp /tmp/config.yaml /conf/config.yaml && chmod 666 /conf/config.yaml"
```

That file is the rendered APISIX config — it carries the resolved `APISIX_ADMIN_KEY` and the admin
`allow_admin` CIDR list. Mode 666 makes it world-readable **and world-writable** inside the volume.
Anything that can mount `${APISIX_CONF_VOLUME}` can read the admin key or rewrite `allow_admin`.

The 600 discipline `template-configs.sh` applies to every render (`chmod 600 "$output_file"`,
T7.7.4) is undone at the last hop, for what is almost certainly a uid-mismatch workaround. The
principled fix is `chown` to APISIX's runtime uid plus `chmod 640`; the range already establishes the
pattern for exactly this (`db-init`/`keycloak-db-init` chown the Postgres volume to uid 999).

Mitigating: single-tenant host, rootless Docker, volume not shared with any other compose service in
the current file.

---

### F9 — LOW · pre-existing, confirmed in range · `skip()` increments `PASSED`, and `13-test-prometheus.sh` can never take its assertion path

Already filed as **B20**; recorded here because `common/scripts/tests/config.sh` is inside this
range (`5f817be`) and the change is what completed the mechanism:

- `config.sh:263-268` — `skip()` does `PASSED=$((PASSED + 1))  # Skipped counts as passed`.
- `config.sh:88-96` / `:127-134` (added by `5f817be`) — `DEFAULT_PROMETHEUS_URL` and
  `DEFAULT_APISIX_METRICS_URL` are non-empty **only** when `LOCAL_TESTS=true`, which the runner's
  discovery glob never produces for this file.

Net effect: `13-test-prometheus.sh` prints a green `1/1 ✓` while asserting nothing. T3.3's
metrics-bind fix (F7's counterpart) was consequently unverified on any host until it was checked by
hand on prod on 2026-08-17. A test that cannot fail is worse than an absent one, because the phase
record then cites it as coverage.

No new fix proposed here — B20 owns it. Flagged so Pass B and T7.7 do not count `13-test-prometheus.sh`
as evidence for anything.

---

### F10 — LOW · spec/implementation mismatch · BR-SEC-022 names `--chmod=D700,F600` as the delivery mechanism; the code chmods after the fact

`target/requirements/13_secrets_management.md` (BR-SEC-022) states the three committed files are
"deployed **from the release artifact** at mode `600` (`--chmod=D700,F600`)".

`common/scripts/deploy-lib.sh:139-152` does not use `--chmod` for them. The `${env_name}/` rsync
carries no mode flag, so the files land with git's checkout mode (644), and a **subsequent**
`remote_exec "chmod 600 ..."` tightens them. The in-code comment explains why `--chmod` was rejected
(it would apply to the whole sync and strip the exec bit off `setup.sh` et al.) — that reasoning is
sound; the *spec text* is what is stale.

Two consequences: (1) the spec cites a mechanism the code does not use, so a future reader
verifying BR-SEC-022 by grepping for `--chmod` finds only the `other/cert` sync; (2) there is a real
if brief window during which `{env}/.env` sits at 644 on the host, between the rsync completing and
the chmod landing.

**Fix:** either give the three files their own third rsync invocation with `--chmod=D700,F600` (which
makes the spec true and removes the window), or amend BR-SEC-022 to describe post-sync tightening.
The first is barely more code and is the one the spec already promises.

---

## What this pass checked and found clean

Recorded so Pass B knows where Pass A's attention actually went, and so "not mentioned" is not
mistaken for "not looked at".

- **BR-SEC-023 deny-by-default.** `template-configs.sh`'s `strip_ip_restriction` /
  `jq del(.plugins["ip-restriction"])` fail-open path is fully deleted, not guarded. The replacement
  substitutes `127.0.0.1/32` and the `is_json_cidr` flag makes an *unset* placeholder take the same
  path as an empty one (`[ -v ]` no longer gates it), so B6's "raw `{{marker}}` in a published route"
  is closed too. `ip-restriction-deny-by-default-check.sh` asserts presence **and** value on all
  three routes offline, which is the right assertion — absence would otherwise read as a pass.
- **Fail-closed rendering.** `render-secrets-hook.sh` replaces `source <(render)` everywhere,
  including `template-configs.sh` (T6.1.1). stdout and stderr are captured separately and only
  stderr is echoed on failure, so a partial render cannot spill resolved secrets into a CI log. The
  `RENDER_SECRETS_HOOK_SHOW_VALUES` escape hatch is off by default and documented as CI-forbidden.
- **`REMOTE_*` fail-closed.** `deploy.sh:247-256` and `bootstrap-host.sh:105-113` both abort when
  any of the three is unset. The old `${ENV}-default` / `$(whoami)` / `~/haisir-deploy` defaults are
  gone from both. `Jenkinsfile.deploy` binds all three as Secret Text per environment.
- **Secret-scanner coverage of the newly committed files.** `.gitleaks.toml` correctly **removed**
  its blanket `.*\.env\.config\.sh$` / `.env.config.common.sh` allowlist in the same phase that
  committed those files — the one change that had to happen and is easy to forget. `.gitignore`'s
  negations are exactly the seven paths; `.env_info` stays ignored, and `deploy-lib.sh` excludes it
  from both rsyncs so `--delete` cannot remove the host copy.
- **Prune fail-closed.** `create_route_config.sh`'s B22 prune uses `jq -er` and aborts when the
  live list is unreadable, correctly refusing to equate "cannot read" with "no orphans". Guarded by
  `DRY_RUN == false && -z "$SPECIFIC_FILE"`, and the earlier `${#FILES[@]} -eq 0 → exit 0` means an
  empty render cannot mass-delete every live route. Dev's hand-loaded HMR route is exempted.
- **Bounded preservation.** `MAX_PRESERVE_PREFIX=24` refuses to launder a `0.0.0.0/0` (or any
  wide entry) into permanence, and `keycloak-admin-access.sh`'s `MIN_GRANT_PREFIX` is held at the
  same number with a comment saying why they must not diverge. The `ponytail:` comment names the
  real ceiling (prefix width is a proxy for provenance).
- **Container hardening on all nine new monitoring services.** Every one carries
  `no-new-privileges:true`, `cap_drop: [ALL]`, `mem_limit`, `pids_limit`, `ulimits`, log rotation,
  and a `127.0.0.1:`-scoped host publish. Grafana's anonymous `Viewer` org role was removed
  (`enabled = false`) and its admin password arrives via `$__file{}`, never an env var.
  `node-exporter`'s `pid: host` + `/:/rootfs:ro` is standard for the exporter and is bounded by
  `cap_drop: ALL` under rootless Docker.
- **Image pinning.** `check-image-pins.sh` ships with a ten-case `--self-test`, is wired into the
  Jenkins `Image Pin Check` stage, resolves a single `${VAR:-default}` wrapper before classifying,
  and does not substring-match `latest` (so `v1.31-latest` passes). The `# BR-INFRA-005` per-line
  escape hatch is narrow and documented. Its accepted ceiling — a `:${VAR}` tag whose variable could
  itself be `latest` — is stated in the header.
- **Static checks actually wired.** The `Static Security Checks` Jenkins stage carries the header
  comment explaining *why* it exists (a `*-check.sh` under `tests/` is invisible to the
  `*-test-*.sh` runner glob and would never execute), and lists all seven. This is the direct
  structural fix for F9's class.
- **Backend.** `question_id` on `ExamReviewChatRequest` only *narrows* a set already scoped by
  `attempt_id`, so it cannot widen grounding across attempts — no IDOR. The two poller
  `session.rollback()` additions are correct and each carries a `rollback.assert_awaited_once()`
  regression test. Dockerfile stays non-root (`USER 1000:1000`), root confined to the discarded
  builder stage.
- **Frontend.** Both stages moved to pinned Minimus tags with no `:latest` left; `nanoid` pinned to
  `>=3.3.17 <4` with the ESM/CJS reason recorded; runtime user, tmpfs uids and docs all reconciled
  to 1000. No application code changed.

---

## Coverage statement

This pass read the complete diff for all three ranges named in the `Covered:` line, with the two
Method exclusions above.

**One gap remains open.** Pass A verified that the secret-scanner *configuration* now covers the
seven newly committed paths (`.gitleaks.toml`'s blanket allowlist for them was removed in the same
phase). It did **not** verify the scanners' actual *output* against those files, because neither
`gitleaks` nor `detect-secrets` is installed on this machine and reading the files directly is
forbidden. F3's specific instance is closed by owner confirmation; the general question — does any
secret-shaped value sit in a committed `.env*` file — is not, and no finding here should be read as
answering it. **Pass B, reading the end state, is the correct place to close it**, ideally by running
both scanners rather than by inspection.


---

## Post-review resolutions (2026-08-18, same day)

Findings above are left exactly as written. This section records what happened to them.

| Finding | Resolution |
|---|---|
| Pass A F1 / Pass B F3 (`-t 0` prod confirmation) | **FIXED** in `bootstrap-host.sh` and `deploy.sh`. Both now refuse a non-interactive prod run instead of silently skipping the prompt. `deploy.sh` gained a `--yes` flag for callers that already hold an approval gate, and `Jenkinsfile.deploy`'s prod stage passes it — **without that flag the fix would have broken every CI prod deploy**, since Jenkins runs `deploy.sh --env prod` through a non-interactive `sh` step and relies on its own `input` gate. Verified at runtime both ways: no-TTY-no-`--yes` exits 1 before Step 1 (i.e. before any SSH), `--yes` proceeds past the gate. `shellcheck --severity=warning` clean. `bootstrap-host.sh` deliberately did **not** get `--yes`: it is operator-only cold-start, and a future attempt to wire it into CI should hit a wall. |
| Pass A F2 (`bootstrap-host.sh` reports success after failures) | **FIXED.** `verify_deployment` now polls the endpoint for 60s and returns non-zero if it never answers; `run_tests` returns the suite's exit status; `main` collects both, picks the banner from the result, and propagates it. The script previously had no path that exited non-zero after `run_full_setup`. |
| Pass A F3 (exporter variable provenance) | **DOWNGRADED HIGH→MEDIUM, still open.** Owner confirmed `POSTGRES_EXPORTER_DSN` is in no committed file — closing the credential-in-git branch and leaving the no-provenance branch, which is the finding. Gate to close before the `monitoring` profile first ships. |
| Pass B F5 (OpenBao README contradiction) | **RESOLVED — the README was wrong.** Owner confirms staging and prod both run their own live OpenBao. `common/openbao/README.md` corrected: the "never been started" claim is gone and the bring-up section is relabelled a historical runbook rather than outstanding work. |
| Pass B F8 (27 pre-migration secrets in git history) | **DEFERRED by owner call 2026-08-18.** They were not rotated. Deferred deliberately to avoid breaking staging/prod outside a release window; to be reconsidered at the next release. The exposure is unchanged by the deferral — anyone with repo history access holds those values — so this is an accepted risk, not a closed finding. |
| All other findings | Open, unassigned. See the parent task record in `Implementation_planning/TASKS.md` (T7.6). |
