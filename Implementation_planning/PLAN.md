# PLAN — Phase 7.5: Minimus Container Images + Phase 7 Deploy Backlog

> Scoped 2026-08-09 via `/plan`. Phase 7 (Gateway WAF Modernisation, CSP & Security Review
> Closeout) closed 2026-08-06 and shipped as v2026.6 (staging 2026-08-07, prod 2026-08-08); its
> plan and tasks are archived at `archive/PLAN_Phase7-GatewayWAF-CSP_2026-08-06.md` /
> `archive/TASKS_Phase7-GatewayWAF-CSP_2026-08-06.md`.
>
> **Specs:** `target/requirements/14_container_images.md` (G1–G4 — written 2026-07-26, unchanged;
> the inventory, version targets and variant-tier policy were already complete, so no
> `/update-target-state` pass was needed) and `target/requirements/13_secrets_management.md`
> (G6 — **BR-SEC-022**, **BR-SEC-023** and the amended **BR-SEC-011**, from the
> `/update-target-state` pass run 2026-08-09).
>
> Phase stub, backlog detail (B1–B6) and the full B6 root-cause trace: `phases.md` § Phase 7.5.
>
> **Two challenger rounds run.** Round 1 raised 20 issues, all applied. Round 2 verified the
> dependency graph is a DAG with no dangling IDs, re-checked the invariants, and corrected three
> file references and four non-runnable or destructive tests. Four owner decisions were taken during
> planning and are encoded below rather than left open — see "Decisions taken during planning".

| Repo | HEAD at scoping |
|---|---|
| haisir-backend | `00c2c73` |
| haisir-frontend | `705833d` |
| haisir-deploy | `844e8f9` |

## ROOT — Pinned images, fail-closed deploy

**Root goal**: Every container image in the stack pulls from Minimus (`reg.mini.dev`) at an explicit pinned version tag, and the deploy-layer failure modes the v2026.6 prod window exposed — all of them fail-open — are closed at the mechanism rather than the value.

**Acceptance test**: From a clean `haisir-deploy` checkout with the three env-config files deleted off the staging host, run `deploy.sh --manifest releases/v<next>/manifest.yaml --env staging`; the deploy completes, then `docker inspect --format '{{.Config.Image}}' $(docker ps -q)` on the staging host emits zero images matching `:latest$` or a registry other than `reg.mini.dev`/`${DOCKER_REGISTRY}`, and `curl -o /dev/null -w '%{http_code}' https://<staging-host>/admin/master/console/` returns `403`.

**Repos**: [backend] [frontend] [deploy] [specs]

### Scope locks (encoded decisions — do not re-open)

- **Node stays on the 26 (current) line.** `haisir-frontend/Dockerfile:2` already builds on `node:26-trixie-slim` and `package.json` declares no `engines`, so G1 is a pure registry swap with no runtime-version delta and a G1 build failure is attributable to the base image alone. Resolves the "24-LTS vs 26-current" open call in `14_container_images.md`.
- **Keycloak admin exposure model. ⟲ REVERSED 2026-08-13 — see T6.2.0.** ~~Gateway routes 13/14/15 stay published and deny everything. Admin reaches Keycloak over the tailnet via `KEYCLOAK_ADMIN_PORT_BINDING`. This is what makes `KC_HOSTNAME_ADMIN` load-bearing.~~ The tailnet-only model **does not work and has been abandoned.** `KC_HOSTNAME_ADMIN` governs only the admin console's own base URLs; the console's `authServerUrl` follows `KC_HOSTNAME`, so the OIDC login redirect still lands on the public hostname and route 14 regardless. It is also server-global, not master-scoped, which is how setting it broke the staging console outright on 2026-08-12. **Current model: routes 13/14/15 stay published on the public hostname and are restricted by `KEYCLOAK_ADMIN_ALLOWED_CIDR` holding the operator's PUBLIC IP CIDR** — the model that worked before v2026.7. `KC_HOSTNAME_ADMIN` is removed from the compose file and from the required-keys gate.
- **G6.2 does not queue behind G1–G4.** The Keycloak admin console answers `200` from the public internet today. It is the most urgent open security item on the system and has no dependency on any image work. Its only ancestors are `T6.1.1`, `T6.1.2` and `T6.1.3` — none of which touch an image.
- **G6 scope guard, non-negotiable, applies to every G6 task**: three files by exact filename — `{env}/.env`, `{env}/.env.config.sh`, `common/.env.config.common.sh` — across `dev`, `staging` and `prod`. Seven paths total. No other file, no prefix/suffix variants, no glob or regex matching. `.gitignore` negations, rsync excludes, gitleaks edits, KV migrations **and every test command** are each enumerated by exact path.
- **The gateway *builder* stage is already done** (`gateway-docker/Dockerfile:69` on `reg.mini.dev/go@${GO_BUILDER_DIGEST}`, Phase 7's carve-out). The gateway *runtime* stage is in G2.
- **B2 stays in the backlog** — fixed in both environments 2026-08-07, not deploy-blocking.

### Decisions taken during planning (2026-08-09)

Four calls were settled at scoping rather than left as `UNRESOLVED` markers. Each is encoded in the
task that implements it; none is re-litigated downstream.

| # | Decision | Where it lands |
|---|---|---|
| 1 | **Node stays on the 26 (current) line**, not 24 LTS — resolves `14_container_images.md`'s open call | Scope lock, T1.4 |
| 2 | **Go builder parity is in scope**, not deferred — Phase 7 moved the registry but never checked the version behind the digest against `go.mod` | **T2.9** (new) |
| 3 | **Monitoring ships alert rules, dashboards and paging**, not just a stand-up — with the paging *destination* an owner input rather than a value this plan invents | **T3.4, T3.5, T3.6** (new) |
| 4 | **`--port-driver=slirp4netns`** on both hosts — the value staging already behaves as, so only prod converges; both `allow_admin` entries stay | T5.8 |
| 5 | **Review independence means different *basis*, not different reviewer** — Pass A reads the diff, Pass B reads the end state against the business rules from a fresh session, and the union of their declared coverage ranges must equal the phase range | T7.6 |

> Decision 5 exists because of a specific recorded failure: both Phase 7 G8 review passes ran
> against the same commit range, so `92a4da2` fell through a gap neither reviewer knew existed.
> Differing `Reviewer:` lines would not have caught it; differing *bases* and asserted coverage do.

---

## G1 — Application images build and boot from pinned Minimus bases

**Goal**: `haisir-backend` and `haisir-frontend` build their builder *and* runtime stages from `reg.mini.dev` at the same explicit version pin, removing the Chainguard-`latest` / Docker-Hub split.
**Goal test**: `docker build` both images from a clean cache, run each container, and `docker inspect --format '{{index .Config.Labels "org.opencontainers.image.base.name"}}' <image>` plus the Dockerfile `FROM` lines show `reg.mini.dev/python:3.14` and `reg.mini.dev/node:26` on the runtime stages, with both containers reaching their healthcheck-passing state.
**Repos**: [specs] [backend] [frontend] [deploy]

> Whether Minimus publishes a `-hardened` variant for python/node/postgres/pgvector on the free tier, and the exact tag line each image offers, are both answered by T1.1's DISCOVER/SELECT TAG steps. Not owner decisions — every G1/G2 task already states its fallback (plain tag per BR-INFRA-003; a BR-INFRA-006 digest pin if no line exists at all).

##### T1.1 [specs] — Pull and record the current Minimus migration workflow
- **Build**: Fetch `https://api.mini.dev/v1/skills/dockerfile` at implementation time (DISCOVER → SELECT TAG → INSPECT → CHECK FOR SHELL → RESOLVE PACKAGES → WRITE → VERIFY → ANALYZE). Record the workflow revision identifier and fetch date in an `Implementation_planning/decisions.md` entry. Do not cache a copy in the repo — Minimus revises it independently of our spec.
- **Done when**: `decisions.md` contains a Phase 7.5 entry naming the workflow revision and fetch date.
- **Test**: `grep -q 'api.mini.dev/v1/skills/dockerfile' Implementation_planning/decisions.md` exits 0.
- **Depends on**: None.

##### T1.2 [backend] — Backend Dockerfile to Minimus, both stages
- **Build**: In `haisir-backend/Dockerfile`, change `:4` `python:3.14-slim` → `reg.mini.dev/python:3.14-dev` and `:52` `cgr.dev/chainguard/python:latest` → `reg.mini.dev/python:3.14`. Both stages pin the same minor version (BR-INFRA-004 — the existing "builder and runner Python minor version must match" comment now has a mechanism behind it). Confirm at SELECT TAG whether a `-hardened` runtime variant is listed; use it if so (BR-INFRA-003), never `-advanced` or `-fips`. Any `USER` or `chown` the new base forces belongs here, not in T1.6.
- **Done when**: `docker build --no-cache -t haisir-backend:t1.2 .` exits 0.
- **Test**: `[ "$(grep -c '^FROM reg.mini.dev/python:3.14' Dockerfile)" = 2 ]` exits 0.
- **Depends on**: T1.1 [specs].

##### T1.3 [backend] — Backend runtime container boots on the Minimus base
- **Build**: Run the CHECK FOR SHELL step against `reg.mini.dev/python:3.14`. Rewrite any shell-form `CMD`/`ENTRYPOINT` for `haisir-backend`/`haisir-worker` that assumes `/bin/sh` into exec form. Run the built image and check startup logs against the Minimus error-signature table (this is the VERIFY step — a green `docker build` is not sufficient evidence).
- **Done when**: `docker run --rm haisir-backend:t1.2` reaches the app's ready log line without an entrypoint or interpreter error.
- **Test**: `docker run -d --name t13 haisir-backend:t1.2 && sleep 20 && [ "$(docker inspect -f '{{.State.Running}}' t13)" = true ]` exits 0.
- **Depends on**: T1.2 [backend].

##### T1.4 [frontend] — Frontend Dockerfile to Minimus, both stages
- **Build**: In `haisir-frontend/Dockerfile`, change `:2` `node:26-trixie-slim` → `reg.mini.dev/node:26-dev` and `:60` `cgr.dev/chainguard/node:latest` → `reg.mini.dev/node:26`. Delete the stale comment at `:58` claiming no versioned tags are available on the free plan — it is the justification for a split that no longer exists. Node stays on 26 per the scope lock. Any `USER` or `chown` the new base forces belongs here, not in T1.6.
- **Done when**: `docker build --no-cache -t haisir-frontend:t1.4 .` exits 0.
- **Test**: `! grep -q 'free plan' Dockerfile` exits 0.
- **Depends on**: T1.1 [specs].

##### T1.5 [frontend] — Frontend runtime container boots on the Minimus base
- **Build**: CHECK FOR SHELL against `reg.mini.dev/node:26`; rewrite any shell-form `CMD` for `haisir-frontend` into exec form. Run and check startup logs against the error-signature table.
- **Done when**: `docker run --rm -p 3000:3000 haisir-frontend:t1.4` serves an HTTP response on its listen port.
- **Test**: `docker run -d --name t15 -p 3000:3000 haisir-frontend:t1.4 && sleep 20 && [ "$(curl -o /dev/null -sw '%{http_code}' localhost:3000)" = 200 ]` exits 0.
- **Depends on**: T1.4 [frontend].

##### T1.6 [deploy] — Reconcile the hardcoded 65532 UID against the Minimus images
- **Build**: Read the actual non-root UID of `reg.mini.dev/python:3.14` and `reg.mini.dev/node:26` via the Minimus INSPECT step. `common/docker-compose.yml`'s tmpfs mounts for the backend, worker and frontend services hardcode `uid=65532,gid=65532` (the Chainguard value). If Minimus differs, update every tmpfs mount option and bind-mount ownership for those three services **in `common/docker-compose.yml` and `dev/docker-compose.yml`**. Any `USER` or `chown` inside the application Dockerfiles is T1.2/T1.4's scope, not this task's. Do not carry `65532` over on the assumption it matches.
- **Done when**: the UID in every tmpfs mount option for backend/worker/frontend equals the UID reported by `docker run --rm --entrypoint "" reg.mini.dev/python:3.14 id -u` (resp. node).
- **Test**: `docker compose -f common/docker-compose.yml up -d backend && ! docker compose -f common/docker-compose.yml logs backend | grep -q 'Permission denied'` exits 0.
- **Depends on**: T1.3 [backend], T1.5 [frontend].

##### T1.7 [deploy] — Boot the full application stack on the migrated bases
- **Build**: Bring backend, worker and frontend up together from `common/docker-compose.yml` on the Minimus images with the reconciled UIDs. T1.3/T1.5 prove each image starts alone; this proves they start against the shared volumes and tmpfs mounts T1.6 changed — the only place a UID mismatch between the python and node images shows up.
- **Done when**: backend, worker and frontend all report `healthy`.
- **Test**: `docker compose -f common/docker-compose.yml up -d backend worker frontend && sleep 90 && [ "$(docker compose -f common/docker-compose.yml ps --format '{{.Name}} {{.Health}}' | grep -vc healthy)" = 0 ]` exits 0.
- **Depends on**: T1.6 [deploy].

---

## G2 — Infrastructure services run on pinned, hardened images

**Goal**: Postgres+pgvector, keycloak-db Postgres, APISIX runtime, Keycloak and etcd all run from `reg.mini.dev` at pinned tags, and the from-source pgvector compile is deleted rather than ported.
**Goal test**: `docker compose -f common/docker-compose.yml up -d` on staging brings all five services to `healthy`, and `docker compose config | grep -E 'image:' | grep -vc 'reg.mini.dev|\$\{DOCKER_REGISTRY\}'` reports `0`.
**Repos**: [deploy]

> **Go builder parity is in scope** (owner call, 2026-08-09). Phase 7 migrated `gateway-docker/Dockerfile:69`'s builder to `reg.mini.dev/go@${GO_BUILDER_DIGEST}` but never checked the version behind that digest against the source. T2.9 closes it.

##### T2.1 [deploy] — App Postgres to the standalone Minimus pgvector image
- **Build**: Replace `common/docker-compose.yml:4` and `:25` (`${DOCKER_REGISTRY}/haisir-postgres:${POSTGRES_IMAGE_TAG}`) and `dev/docker-compose.yml:4` (`pgvector/pgvector:0.8.2-pg18-trixie`) with `reg.mini.dev/pgvector:18` — one tag across all three, replacing two separate pins. Verify at SELECT TAG that the `18` line ships pgvector ≥ 0.8.4 so no extension downgrade occurs.
- **Done when**: all three `image:` lines read `reg.mini.dev/pgvector:18`.
- **Test**: `docker compose -f dev/docker-compose.yml up -d postgres && docker compose -f dev/docker-compose.yml exec postgres psql -U postgres -tAc "SELECT extversion FROM pg_extension WHERE extname='vector'"` prints a version ≥ `0.8.4`.
- **Depends on**: T1.1 [specs].

##### T2.2 [deploy] — Delete the from-source pgvector build
- **Build**: Delete `postgres-docker/` entirely — the Wolfi builder stage, the from-source pgvector compile, the `POSTGRES_BASE_IMAGE` default of `cgr.dev/chainguard/postgres:latest` and its `checkov:skip` comment. Remove the `haisir-postgres` build-and-push stage from `Jenkinsfile` and any `POSTGRES_IMAGE_TAG` **build-arg** threading that exists only to feed it. **Leave `POSTGRES_IMAGE_TAG` itself in `{env}/.env` and in `deploy.sh:535-574`'s drift loop** (`postgres:POSTGRES_IMAGE_TAG:haisir-db-${ENV}`) — the image is now a pinned `reg.mini.dev` tag rather than a built artifact, but the drift comparison still needs a desired value to compare the running container against.
- **Done when**: `postgres-docker/` does not exist and no Jenkins stage builds `haisir-postgres`.
- **Test**: `! grep -rq 'haisir-postgres' Jenkinsfile Jenkinsfile.deploy common/scripts/` exits 0.
- **Depends on**: T2.1 [deploy].

##### T2.3 [deploy] — Re-verify the Postgres data-directory ownership workaround
- **Build**: `common/docker-compose.yml` sets `user: "70"` and `chown -R 70:70` for Postgres — the Chainguard UID. The Chainguard entrypoint does its `mkdir`+`chown` as root *before* dropping privileges, which is why a named volume (docker-created, `0755` root-owned) rather than a root-owned `0700` tmpfs was the T1.4.2 workaround. Read `reg.mini.dev/pgvector:18`'s UID via INSPECT, confirm whether the same entrypoint ordering holds, and update `user:`, the `chown` and the volume type accordingly. Do not assume the workaround still applies.
- **Done when**: the `user:` value for the Postgres services equals the UID reported by `docker run --rm --entrypoint "" reg.mini.dev/pgvector:18 id -u`.
- **Test**: `docker volume rm haisir_pgdata; docker compose -f common/docker-compose.yml up -d postgres && docker compose -f common/docker-compose.yml logs postgres | grep -q 'database system is ready to accept connections'` exits 0.
- **Depends on**: T2.1 [deploy].

##### T2.4 [deploy] — keycloak-db Postgres to Minimus
- **Build**: Replace `common/docker-compose.yml:340` and `:361` (`cgr.dev/chainguard/postgres:latest` — the two rolling-tag services) with `reg.mini.dev/postgres:18`, or its `-hardened` variant if the gallery lists one (BR-INFRA-003). Plain Postgres, no pgvector needed here. Apply the same UID/entrypoint check as T2.3 to these two services.
- **Done when**: neither line contains `cgr.dev` or `:latest`.
- **Test**: `docker compose -f common/docker-compose.yml up -d keycloak-db && docker compose -f common/docker-compose.yml exec keycloak-db pg_isready` exits 0.
- **Depends on**: T2.3 [deploy].

##### T2.5 [deploy] — APISIX runtime stage to Minimus
- **Build**: In `gateway-docker/Dockerfile`, change the runtime `FROM apache/apisix@${APISIX_DIGEST}` at `:157` to `FROM reg.mini.dev/apache-apisix:3.17`, delete the now-dead `ARG APISIX_DIGEST=sha256:27fdde75…` at `:54` and its `checkov:skip=CKV_DOCKER_7` comment at `:156`. In `gateway-docker/Jenkinsfile`, `:104`'s `grep '^ARG APISIX_DIGEST=' gateway-docker/Dockerfile` will return empty into `apisixDigest` and the `'pull apisix'` branch at `:107` would then `docker pull apache/apisix@` — update both to pull `reg.mini.dev/apache-apisix:3.17` by tag. Leave `:54`'s `GO_BUILDER_DIGEST`, `:69`'s builder `FROM reg.mini.dev/go@${GO_BUILDER_DIGEST}` and `:103`'s `goDigest` grep alone — Phase 7 already migrated that stage.
- **Done when**: `docker build -f gateway-docker/Dockerfile .` exits 0 and the WAF Functional Gate stage (`gateway-docker/Jenkinsfile:158` → `common/scripts/tests/waf-harness.sh`, no `when` guard, sits before Export/Push) passes on the rebuilt image.
- **Test**: `bash common/scripts/tests/waf-harness.sh` exits 0 with the CVE-2026-21876 multipart case attributed to rule `922110`.
- **Depends on**: T1.1 [specs].

##### T2.6 [deploy] — Keycloak to one pinned Minimus tag across dev and prod
- **Build**: Replace `common/docker-compose.yml:419` (`quay.io/keycloak/keycloak:${KEYCLOAK_IMAGE_TAG}`) and `dev/docker-compose.yml:46` (`keycloak/keycloak:26.6`) with `reg.mini.dev/keycloak:26.7` — one tag across both, ending the dev/prod version skew. Check whether the Keycloak image has a shell; `common/openbao/`'s vault-agent renders `keycloak.conf` rather than passing password env vars, so confirm that mount path and the healthcheck both survive.
- **Done when**: both lines read `reg.mini.dev/keycloak:26.7` and neither environment references quay.io or Docker Hub for Keycloak.
- **Test**: `docker compose -f dev/docker-compose.yml up -d keycloak && [ "$(curl -o /dev/null -sw '%{http_code}' http://localhost:8080/realms/master/.well-known/openid-configuration)" = 200 ]` exits 0.
- **Depends on**: T1.1 [specs].

##### T2.7 [deploy] — etcd to Minimus
- **Build**: Replace `common/docker-compose.yml:514` (`quay.io/coreos/etcd:${ETCD_IMAGE_TAG}`) and `dev/docker-compose.yml:79` (`quay.io/coreos/etcd:v3.6.11`) with `reg.mini.dev/etcd:<pin>`, verifying Minimus's own etcd line at SELECT TAG (spec suggested `3.6.6` as of 2026-07-26 — re-verify, and do not downgrade below the running `v3.6.11`).
- **Done when**: neither line references `quay.io`.
- **Test**: `docker compose -f dev/docker-compose.yml up -d etcd && docker compose -f dev/docker-compose.yml exec etcd etcdctl endpoint health | grep -q 'is healthy'` exits 0.
- **Depends on**: T1.1 [specs].

##### T2.8 [deploy] — Audit shell-dependent healthchecks across the migrated services
- **Build**: Minimus production images may ship without a shell. Every compose healthcheck and `command:` override for the five G2 services that shells out (`pg_isready`, `curl`, `wget`, `CMD-SHELL`) fails *silently* on a shell-less image — the container reports unhealthy for the wrong reason, or never reports at all. Convert each to exec form using a binary that exists in the image, or move it to a `-dev` stage.
- **Done when**: every healthcheck for the postgres, keycloak-db, keycloak, etcd and apisix services uses `CMD` exec form with a binary verified present in that image.
- **Test**: `sleep 120 && [ "$(docker compose -f common/docker-compose.yml ps --format '{{.Name}} {{.Health}}' | grep -E 'postgres|keycloak|etcd|apisix' | grep -vc healthy)" = 0 ]` exits 0.
- **Depends on**: T2.4 [deploy], T2.5 [deploy], T2.6 [deploy], T2.7 [deploy].

##### T2.9 [deploy] — Bring the Go builder digest to BR-INFRA-004 parity
- **Build**: `gateway-docker/Dockerfile:69` is `FROM reg.mini.dev/go@${GO_BUILDER_DIGEST}` — Phase 7 moved the registry but never asserted the Go version behind that digest matches what the source targets. BR-INFRA-004 requires the builder track `go.mod`'s `go` directive and the `GO_VERSION` ARG exactly; `14_container_images.md` names upstream `1.26`. Resolve the digest to its version, and bump the digest, `GO_VERSION` and `go.mod` together if they disagree — never the digest alone, which is the failure mode BR-INFRA-004 exists to name. `gateway-docker/Jenkinsfile:103` greps `ARG GO_BUILDER_DIGEST=` into `goDigest`, so the digest stays digest-pinned (BR-INFRA-006 allows it; T4.10's allowlist covers `@sha256:` lines).
- **Done when**: the Go version behind `GO_BUILDER_DIGEST` equals the `go` directive in the gateway's `go.mod`.
- **Test**: `[ "$(docker run --rm reg.mini.dev/go@$(grep '^ARG GO_BUILDER_DIGEST=' gateway-docker/Dockerfile | cut -d= -f2) go version | grep -oE '[0-9]+\.[0-9]+')" = "$(grep -oE '^go [0-9]+\.[0-9]+' gateway-docker/coraza-proxy-wasm/go.mod | cut -d' ' -f2)" ]` exits 0.
- **Depends on**: T2.5 [deploy].

---

## G3 — Monitoring is live and alerts fire

**Goal**: The Prometheus and Grafana stack, deferred outright in `decisions.md` 2026-06-18 because Chainguard gated both behind a paid plan, runs from pinned `reg.mini.dev` images — and a real failure produces a real alert at a real destination, rather than a dashboard nobody is watching.
**Goal test**: `docker compose --profile monitoring up -d` starts the stack; `curl -s localhost:9090/api/v1/targets | jq '[.data.activeTargets[] | select(.health=="up")] | length'` returns the full exporter count; stopping the backend container fires a `BackendDown` alert that reaches the configured receiver within its `for:` window.
**Repos**: [deploy]

> **Scope call (owner, 2026-08-09, confirmed 2026-08-10): alert rules, dashboards and alert *routing* land in this phase. The paging *policy* does not.** `common/prometheus/prometheus.yml`, `common/grafana/config/grafana.ini`, `common/grafana/provisioning/{dashboards,datasources}` and one dashboard (`json/apisix-overview.json`) already exist. **No alert rules exist anywhere in the repo** — T3.4 is net-new, not an edit.
>
> **The split, kept deliberately narrow.** Rules and dashboards are config that ships alongside the images, so they belong here. T3.6 wires the alertmanager route and receiver — but the **destination, escalation and quiet hours are an owner input supplied at implementation time**, not a value this plan invents. The plumbing is engineering; who gets woken at 3am is not. This is a phase boundary rather than a deferral: nothing downstream waits on the policy, and T3.6's fail-closed gate means a missing destination stops a deploy instead of silently swallowing every alert.

##### T3.1 [deploy] — Add the Prometheus + exporters compose services
- **Build**: Add `prometheus`, `alertmanager`, `node-exporter`, `postgres-exporter` and `nginx-prometheus-exporter` services to `common/docker-compose.yml` under a `monitoring` profile, at `reg.mini.dev/prometheus`, `-alertmanager`, `-node-exporter`, `-postgres-exporter`, `nginx-prometheus-exporter`, each pinned (spec suggests the `3.11` line — re-verify at SELECT TAG). Mount the existing `common/prometheus/prometheus.yml`. No compose service for any of these exists today.
- **Done when**: `docker compose --profile monitoring config` validates and lists all five services with `reg.mini.dev` images at explicit tags.
- **Test**: `docker compose --profile monitoring up -d && sleep 30 && curl -s localhost:9090/-/ready | grep -q 'Prometheus Server is Ready'` exits 0.
- **Depends on**: T1.1 [specs].

##### T3.2 [deploy] — Add the Grafana compose service
- **Build**: Add a `grafana` service to the same `monitoring` profile at `reg.mini.dev/grafana:13.0` (re-verify the line), mounting `common/grafana/config/grafana.ini` and `common/grafana/provisioning/`. This also avoids the AGPL `grafana/grafana-oss` fallback the original deferral had settled on. Check the image's UID via INSPECT before setting volume ownership.
- **Done when**: the `grafana` service starts and serves its login page.
- **Test**: `[ "$(curl -o /dev/null -sw '%{http_code}' localhost:3001/login)" = 200 ]` exits 0.
- **Depends on**: T3.1 [deploy].

##### T3.3 [deploy] — Turn the skipped Prometheus test into a live gate
- **Build**: `common/scripts/tests/13-test-prometheus.sh` currently short-circuits with "Prometheus/metrics endpoints not configured" because `common/scripts/tests/config.sh` sets `DEFAULT_PROMETHEUS_URL=""` for every environment (`:84`, `:115`, `:139`). Set the dev default to the stood-up endpoint so the test actually runs. Leave staging and prod empty until the stack is deployed there.
- **Done when**: `13-test-prometheus.sh` reports a pass/fail count greater than zero for `ENV=dev` instead of the "not configured" info line.
- **Test**: `! ENV=dev bash common/scripts/tests/13-test-prometheus.sh | grep -q 'not configured'` exits 0.
- **Depends on**: T3.2 [deploy].

##### T3.4 [deploy] — Write the alert rules
- **Build**: Add `common/prometheus/rules/haisir.rules.yml` and reference it from `prometheus.yml`'s `rule_files`. **No alert rule exists anywhere in the repo today** — this is net-new. Cover the failure modes this phase and the last one actually hit, not a generic starter set: service down (backend, worker, frontend, apisix, keycloak, db), certificate expiry inside 21 days (B3's silent failure — certbot renewed while nothing distributed the result, and the only symptom was a cert quietly nearing expiry behind an edge terminator), Postgres `idle in transaction` older than 5 minutes (B1, which held sessions for 2h27m and blocks DDL), disk above 85%, and APISIX 5xx rate. Each rule carries a `severity` label and a `summary` annotation naming the runbook step.
- **Done when**: `promtool check rules` validates the file and every rule carries both a `severity` label and a `summary` annotation.
- **Test**: `docker run --rm -v "$PWD/common/prometheus:/p" reg.mini.dev/prometheus:<pin> promtool check rules /p/rules/haisir.rules.yml` exits 0.
- **Depends on**: T3.1 [deploy].

##### T3.5 [deploy] — Provision the dashboards
- **Build**: `common/grafana/provisioning/dashboards/json/` holds exactly one dashboard (`apisix-overview.json`). Add provisioned dashboards for the tiers that have no view at all: application (backend/worker request rate, latency, error rate, queue depth for the two poller job tables), Postgres (connections, `idle in transaction` count, replication/vacuum lag, cache hit ratio) and host (CPU, memory, disk, from node-exporter). Provisioned as files under the existing `dashboards.yaml` provider — not hand-created in the UI, which does not survive a container replacement.
- **Done when**: Grafana lists four dashboards after a cold start with no manual UI step.
- **Test**: `[ "$(curl -s -u admin:$GRAFANA_PASS localhost:3001/api/search?type=dash-db | jq length)" -ge 4 ]` exits 0.
- **Depends on**: T3.2 [deploy].

##### T3.6 [deploy] — Route alerts to the owner-supplied destination
- **Build**: Add `common/prometheus/alertmanager.yml` with a route tree keyed on the `severity` label from T3.4 and a receiver per tier. **The destination and escalation policy are an owner input, not a value this task invents** — the task wires the route, the webhook/SMTP/integration URL arrives as a secret. Store it in `secret/haisir/infra` following the BR-SEC-022 pattern (it is host-specific and must not be committed), register it in `deploy-required-keys.txt` so an unset destination aborts the render rather than silently dropping every alert on the floor — a monitoring stack that fails open is the same defect class as the rest of this phase.
- **Done when**: a firing alert reaches the configured receiver, and an unset destination fails the render rather than starting alertmanager with no route.
- **Test**: `docker compose stop backend; sleep 120; [ "$(curl -s localhost:9093/api/v2/alerts | jq '[.[] | select(.labels.alertname=="BackendDown")] | length')" -ge 1 ]` exits 0.
- **Depends on**: T3.4 [deploy], T3.5 [deploy].

---

## G4 — No unpinned image can reach a host

**Goal**: Every remaining image in the stack is pinned, the components with no Minimus equivalent are recorded as explicit exceptions rather than silently missed, a CI gate fails the build if a `:latest` reappears, and the migrated set is proven at runtime on staging.
**Goal test**: The pinning gate script run over the whole repo exits 0; `grep -rn ':latest' --include='docker-compose*.yml' --include='Dockerfile*' . | grep -v archived` returns only lines documented as BR-INFRA-005/006/007 exceptions.
**Repos**: [deploy]

##### T4.1 [deploy] — Pin OpenBao to a Minimus image
- **Build**: Replace the six `${OPENBAO_IMAGE:-ghcr.io/openbao/openbao:2.6.0}` defaults — five in `common/docker-compose.yml` (`:657`, `:698`, `:739`, `:779`, `:816`) and one in `common/openbao/docker-compose.openbao.yml:105` — with `reg.mini.dev/openbao:2.6.1`. Keep the ≥ v2.6.0 floor for CVE-2025-54996 (BR-SEC-016 status note); 2.6.1 satisfies it.
- **Done when**: all six defaults read `reg.mini.dev/openbao:2.6.1`.
- **Test**: `docker compose -f common/openbao/docker-compose.openbao.yml up -d && docker compose -f common/openbao/docker-compose.openbao.yml exec openbao bao status | grep -q 'Sealed *false'` exits 0.
- **Depends on**: T1.1 [specs].

##### T4.2 [deploy] — Pin the serving-path `other/services` images
- **Build**: `other/services/cftunnel/docker-compose.yml:3` (`cloudflare/cloudflared:latest`) → `reg.mini.dev/cloudflared:<pin>`; `other/services/embedding/docker-compose.yml:18`, `:56`, `:71`, `:86` (four `ollama/ollama:latest` service definitions) → `reg.mini.dev/ollama:<pin>`, one tag across all four. Both are currently rolling tags in the live request path.
- **Done when**: `! grep -rq ':latest' other/services/cftunnel/ other/services/embedding/` exits 0.
- **Test**: `docker compose -f other/services/embedding/docker-compose.yml up -d && [ "$(curl -s localhost:11434/api/version | jq -r .version)" = "<pin>" ]` exits 0.
- **Depends on**: T1.1 [specs].

##### T4.3 [deploy] — Pin the internal registry to `distribution-registry`
- **Build**: `other/services/registry/docker-compose.yml:13` `registry:3` → `reg.mini.dev/distribution-registry:<pin>` — same upstream project, same API. This registry hosts every `haisir-*` image, so the push/pull auth config (`htpasswd`/`REGISTRY_AUTH_*`) must carry over unchanged; a broken auth carry-over breaks the whole build pipeline, which is why this is its own task.
- **Done when**: the registry service starts on the Minimus image and accepts an authenticated push.
- **Test**: `docker compose -f other/services/registry/docker-compose.yml up -d && docker push ${DOCKER_REGISTRY}/haisir-backend:probe` exits 0.
- **Depends on**: T1.1 [specs].

##### T4.4 [deploy] — Pin SonarQube and its Postgres
- **Build**: `other/services/sonarqube/docker-compose.yml:91` `sonarqube:community` → `reg.mini.dev/sonarqube:<pin>` and `:41` `postgres:18-alpine` → `reg.mini.dev/postgres:18` (same tag T2.4 settles on).
- **Done when**: both `image:` lines resolve to `reg.mini.dev` at an explicit tag.
- **Test**: `docker compose -f other/services/sonarqube/docker-compose.yml up -d && sleep 120 && curl -s localhost:9000/api/system/status | jq -e '.status == "UP"'` exits 0.
- **Depends on**: T1.1 [specs].

##### T4.5 [deploy] — Pin nginx-proxy-manager
- **Build**: `other/services/npm/docker-compose.yml:15` `jc21/nginx-proxy-manager:2.15.1` → `reg.mini.dev/nginx-proxy-manager:<pin>`. Already at an explicit tag today, so this is a registry move only — but it terminates the edge, so verify an existing proxy host still resolves after the swap.
- **Done when**: the `image:` line resolves to `reg.mini.dev` at an explicit tag.
- **Test**: `docker compose -f other/services/npm/docker-compose.yml up -d && sleep 30 && [ "$(curl -o /dev/null -sw '%{http_code}' localhost:81)" = 200 ]` exits 0.
- **Depends on**: T1.1 [specs].

##### T4.6 [deploy] — Rebuild the Jenkins Docker-in-Docker layer on Minimus
- **Build**: `other/services/jenkins/docker-compose.yml:14` runs `jenkins-with-docker:lts`, a locally built layer over `jenkins/jenkins:lts`. Rebase on `reg.mini.dev/jenkins` + `reg.mini.dev/jenkins-agent` at the current LTS line. The Docker-CLI layer needs the Minimus RESOLVE PACKAGES step (workflow step 5) re-run against the new base — the package names and manager differ from the Debian original.
- **Done when**: the rebuilt Jenkins image starts and its agents can invoke `docker` against the mounted socket.
- **Test**: `docker exec jenkins docker version --format '{{.Client.Version}}'` prints a version string.
- **Depends on**: T1.1 [specs].

##### T4.7 [deploy] — Opportunistic busybox swap for the init/util images
- **Build**: Per BR-INFRA-007 (not a hard requirement), swap three named services: the `openbao-init` init container at `common/docker-compose.yml:494` (`alpine:latest`), the `openbao-init` init container at `common/openbao/docker-compose.openbao.yml:36` (`alpine:latest`) and the `sonarqube-init` sysctl container at `other/services/sonarqube/docker-compose.yml:16` (`busybox:stable`) → `reg.mini.dev/busybox`. The busybox case is a pure registry swap with no image-family change. If an alpine init container's inline script depends on something busybox lacks, leave it and record why — this rung is optional.
- **Done when**: each of the three either references `reg.mini.dev/busybox` or carries a one-line comment naming the blocking dependency.
- **Test**: `docker compose -f common/docker-compose.yml up openbao-init && [ "$(docker compose -f common/docker-compose.yml ps -a --format '{{.Name}} {{.ExitCode}}' | grep openbao-init | awk '{print $2}')" = 0 ]` exits 0.
- **Depends on**: T1.1 [specs].

##### T4.8 [deploy] — Record the no-match components as digest-pinned exceptions
- **Build**: CrowdSec (`other/services/crowdsec/docker-compose.yml:18`, `crowdsecurity/crowdsec:v1.7.8`), HuggingFace text-embeddings-inference (`other/services/embedding/docker-compose.yml:99`, `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9`) and dockhand (`other/services/dockhand/docker-compose.yml:3`, `fnsys/dockhand:latest`) have no Minimus equivalent. Per BR-INFRA-006 pin each to version **and** digest (`image@sha256:...`) and add an inline comment with the DISCOVER re-check date. dockhand is the only one currently on a rolling tag.
- **Done when**: all three `image:` lines carry an `@sha256:` digest and a dated BR-INFRA-006 comment.
- **Test**: `for f in other/services/crowdsec/docker-compose.yml other/services/embedding/docker-compose.yml other/services/dockhand/docker-compose.yml; do grep -q '@sha256:' "$f" || exit 1; done` exits 0.
- **Depends on**: T4.2 [deploy].

##### T4.9 [deploy] — Rename image references outside the Dockerfiles
- **Build**: `DOCKER_REGISTRY` and the `*_IMAGE_TAG` build args are threaded through `Jenkinsfile`, `Jenkinsfile.deploy`, `gateway-docker/Jenkinsfile` and the deploy/build scripts, not only the Dockerfiles and compose files. Update every reference the G1–G4 swaps invalidated — otherwise the migration builds the right image and records it under the wrong tag. Includes the `APISIX_DIGEST` grep and pull in `gateway-docker/Jenkinsfile:104`/`:107` that T2.5 makes dead.
- **Done when**: no build arg or pipeline variable names an image or registry that no longer exists after G1–G4.
- **Test**: `! grep -rqE 'cgr\.dev|quay\.io/keycloak|apache/apisix|APISIX_DIGEST|python:3\.14-slim|node:26-trixie' Jenkinsfile Jenkinsfile.deploy gateway-docker/Jenkinsfile common/scripts/` exits 0.
- **Depends on**: T2.2 [deploy], T2.5 [deploy], T4.1 [deploy].

##### T4.10 [deploy] — CI gate that fails on an unpinned image
- **Build**: Add a check to the existing lint/validate pipeline stage: scan tracked `Dockerfile*` and `docker-compose*.y*ml`, excluding `archived/` and `gateway-docker/coraza-proxy-wasm/example/`, and exit non-zero on any `FROM`/`image:` matching `:latest` or carrying no tag. Allowed, by explicit allowlist: the non-versioned Minimus bases (`static`, `glibc-dynamic`, `busybox`); any line pinned by `@sha256:` digest, which is strictly stronger than a tag and covers both the BR-INFRA-006 exceptions and `gateway-docker/Dockerfile:69`'s `FROM reg.mini.dev/go@${GO_BUILDER_DIGEST}`; and one explicit BR-INFRA-005 exclusion for `dev/docker-compose.yml:26`'s `dpage/pgadmin4:latest`, annotated inline in the compose file with `# BR-INFRA-005: dev-only, never ships`. One grep with an allowlist, not a policy framework.
- **Done when**: the check exits 0 on the migrated tree and exits non-zero when `:latest` is reintroduced into any scanned file.
- **Test**: `cp dev/docker-compose.yml /tmp/dc.bak; sed -i 's|reg.mini.dev/etcd:.*|reg.mini.dev/etcd:latest|' dev/docker-compose.yml; bash common/scripts/check-image-pins.sh; rc=$?; mv /tmp/dc.bak dev/docker-compose.yml; [ $rc -ne 0 ]` exits 0 (the injected `:latest` is reverted whether the check passes or fails — the test must not leave a tracked file mutated).
- **Depends on**: T1.7 [deploy], T2.8 [deploy], T2.9 [deploy], T3.2 [deploy], T4.3 [deploy], T4.4 [deploy], T4.5 [deploy], T4.6 [deploy], T4.7 [deploy], T4.8 [deploy], T4.9 [deploy].

##### T4.11 [deploy] — Deploy the migrated image set to staging and verify at runtime
- **Build**: Cut a release manifest at the migrated tags and run `deploy.sh --env staging`. This is the first time the migrated images run as a *stack* on a real host rather than individually on a workstation: every `docker build` and local `compose up` above stops at the image, and the root acceptance test asserts staging container state. Run the full `common/scripts/tests/` suite against staging afterwards.
- **Done when**: every container running on staging reports a `reg.mini.dev`/`${DOCKER_REGISTRY}` image at an explicit tag.
- **Test**: `[ "$(ssh <staging> "docker inspect --format '{{.Config.Image}}' \$(docker ps -q)" | grep -vcE 'reg\.mini\.dev|'"${DOCKER_REGISTRY}")" = 0 ]` exits 0.
- **Depends on**: T4.10 [deploy].

---

## G5 — The v2026.6 backlog failure modes are closed

**Goal**: B1, B3, B4-residual and B5-residual no longer fail open — the worker stops parking transactions, the certbot hook cannot drift unnoticed, secret-render failures name their cause, and the container runtime is pinned across hosts. (B6 is not here: it is G6.2, fixed at the mechanism.)
**Goal test**: On staging after a full deploy, `SELECT count(*) FROM pg_stat_activity WHERE state='idle in transaction'` returns `0` twenty minutes after worker start, the deploy's hook-hash assertion passes, and `docker info --format '{{.ClientInfo.Version}}'` reports the same pinned rootless version on staging and prod.
**Repos**: [backend] [deploy] [specs]

> **`--port-driver=slirp4netns` is the standard** (owner call, 2026-08-09). It is the safer of the two: `allow_admin` has carried `10.0.2.0/24` since before B5, so staging keeps behaving exactly as it does today and only prod converges onto it. Both `allow_admin` entries stay — the `172.19.0.1/32` line added 2026-08-08 becomes redundant rather than wrong, and removing a working allowlist entry to tidy up is how B5 happened in the first place (T7.7.1 removed `172.19.0.0/16`, and nothing noticed until a deploy broke).

##### T5.1 [backend] — Release the extraction poller's transaction on an empty poll
- **Build**: `src/infrastructure/repositories/extraction_job_repository.py:249` executes a `SELECT ... FOR UPDATE SKIP LOCKED`, which opens a transaction; `:251-252` then `return None` when no job matches, without committing or rolling back. `src/worker/__main__.py:149` opens `s_extraction` once for the process lifetime, so that transaction stays open across every subsequent `asyncio.sleep` — the observed 2h27m `idle in transaction`. Add `await self.session.rollback()` immediately before the `return None`. Do not touch the claim path: on the success path `:256` flushes and the caller owns the commit, and that boundary carries the claim semantics.
- **Done when**: `claim_next()` returning `None` leaves the session with no open transaction.
- **Test**: `assert (await repo.claim_next()) is None and not repo.session.in_transaction()`
- **Depends on**: None.

##### T5.2 [backend] — Release the essay-grading poller's transaction on an empty poll
- **Build**: Same defect, same shape: `src/infrastructure/repositories/essay_grading_job_repository.py:62` opens the transaction, `:64-65` returns `None` before reaching the `await self.session.commit()` at `:70`. `s_grading` is likewise a process-lifetime session (`src/worker/__main__.py:150`). Add `await self.session.rollback()` before the `return None`.
- **Done when**: `get_next_queued()` returning `None` leaves the session with no open transaction.
- **Test**: `assert (await repo.get_next_queued()) is None and not repo.session.in_transaction()`
- **Depends on**: None.

##### T5.3 [deploy] — Backstop the dynamic DB roles with an idle-transaction timeout
- **Build**: The app connects with **dynamic OpenBao credentials**, not a static `haisir_worker` role, and there is no app-DB init SQL in `haisir-deploy` — the roles are minted per lease by `common/openbao/bootstrap.sh:265`'s `creation_statements`. Append `ALTER ROLE "{{name}}" SET idle_in_transaction_session_timeout = '60s'; ALTER ROLE "{{name}}" SET statement_timeout = '300s';` to that `creation_statements` string (the loop covers `haisir-backend` and `haisir-worker`), so the setting is applied at role-creation time for every future lease. This is defence in depth against a future poller acquiring the same shape — it is **not** the fix and must not land instead of T5.1/T5.2. A `REINDEX`/`ALTER TABLE` needing `ACCESS EXCLUSIVE` queues behind an idle transaction, and once queued every subsequent reader queues behind it too; that is how the first staging reindex attempt stalled the whole app.
- **Done when**: a freshly issued dynamic credential's session reports a non-zero `idle_in_transaction_session_timeout`.
- **Test**: `user=$(bao read -field=username database/creds/haisir-worker); PGPASSWORD=… psql -U "$user" -tAc "SHOW idle_in_transaction_session_timeout"` prints `1min`.
- **Depends on**: T5.1 [backend], T5.2 [backend].

##### T5.4 [deploy] — Surface the real cause of a deploy-secret render failure
- **Build**: `bao_deploy_token()` in `common/openbao/render-deploy-secrets.sh` redirects stderr to `/dev/null`, collapsing container-down, sealed vault, missing cert, unregistered role, `docker: command not found` and wrong-socket into one generic four-cause message — none of which was the actual cause when B4 was diagnosed. Capture stderr into a variable and print it on the failure path. Keep the fail-closed exit; only the diagnostic changes.
- **Done when**: a render failure prints the underlying `bao`/`docker` stderr above the generic message.
- **Test**: With the OpenBao container stopped, `bash common/openbao/render-deploy-secrets.sh 2>&1 | grep -q 'Cannot connect to the Docker daemon'` exits 0.
- **Depends on**: None.

##### T5.5 [deploy] — Bring `other/cert/` inside the deploy sync
- **Build**: `deploy-lib.sh`'s sync covers only `common/` and `${ENV}/`, so `other/cert/haisir-sync-certs.sh` — installed as the certbot renewal hook — is hand-placed on each host and never updated. The T1.3.3 OpenBao fallback sat three weeks unshipped to prod. Add an `other/cert/` rsync step in `deploy-lib.sh` carrying `--chmod=F755` **on that invocation only** — the file is mode `644` in git and certbot execs it directly, so a content-correct copy that is not executable is still a broken hook. Do **not** add `--chmod` to the `common/` or `${ENV}/` rsyncs: they cover far more than the seven in-scope paths, and `common/scripts/full-setup.sh:268` invokes `"$SCRIPT_DIR/setup.sh"` directly, so stripping the exec bit there breaks the next deploy. Do this in `deploy-lib.sh` only, **not** `deploy-remote-common.sh` — T6.6.1 deletes that file.
- **Done when**: a deploy transfers `other/cert/haisir-sync-certs.sh` to the remote host.
- **Test**: `[ "$(ssh <staging> "sha256sum ~/haisir-deploy/other/cert/haisir-sync-certs.sh" | cut -d' ' -f1)" = "$(sha256sum other/cert/haisir-sync-certs.sh | cut -d' ' -f1)" ]` exits 0.
- **Depends on**: None.

##### T5.6 [deploy] — Assert the installed certbot hook matches the repo
- **Build**: Syncing the file is not sufficient — the copy that runs lives at `/etc/letsencrypt/renewal-hooks/deploy/`, and rsync does not reach it. Add a deploy-time hash comparison between the repo copy and the installed copy, failing loud on mismatch. This is the check that actually closes B3: it catches drift regardless of how the installed file got there. The failure it prevents is silent by construction — a broken hook produces no alert, and the only symptom is a cert quietly nearing expiry behind an edge terminator that hides it.
- **Done when**: a deploy aborts with a named error when the installed hook's hash differs from the repo's.
- **Test**: `ssh <staging> "echo '# drift' >> /etc/letsencrypt/renewal-hooks/deploy/haisir-sync-certs.sh"` then run the deploy; it exits non-zero citing the hook hash mismatch.
- **Depends on**: T5.5 [deploy].

##### T5.7 [deploy] — Assert the installed certbot hook is executable
- **Build**: The hash comparison in T5.6 is content-only and passes on a mode-`644` copy that certbot cannot exec — the exact failure `--chmod=F755` in T5.5 exists to prevent, and the one a content hash cannot see. Add a mode assertion alongside the hash check in the same deploy step.
- **Done when**: the installed hook at `/etc/letsencrypt/renewal-hooks/deploy/haisir-sync-certs.sh` is mode `755` after a deploy.
- **Test**: `[ "$(ssh <staging> "stat -c '%a' /etc/letsencrypt/renewal-hooks/deploy/haisir-sync-certs.sh")" = 755 ]` exits 0.
- **Depends on**: T5.6 [deploy].

##### T5.8 [deploy] — Pin the rootless container runtime across hosts
- **Build**: B5's residual. Neither staging nor prod sets `--port-driver`, so each follows its own rootlesskit version and the two rewrite the source address differently (`slirp4netns` → `10.0.2.2`, `builtin` → the bridge gateway `172.19.0.1`). `allow_admin` now carries both, so either resolves — but staging is correct **by accident**, and a rootlesskit upgrade there reproduces prod's failure exactly. Pin the rootless Docker/rootlesskit version in the host provisioning and set **`--port-driver=slirp4netns`** explicitly and identically on both hosts (owner call — see the note above; it is the value staging already behaves as, so only prod changes). Leave both `allow_admin` entries in place. This is environment drift at the container-runtime layer, invisible to every config diff — and it is why the image-pinning and deploy-backlog concerns share this phase.
- **Done when**: both hosts report the same rootlesskit version and `--port-driver=slirp4netns`.
- **Test**: `[ "$(for h in staging prod; do ssh $h "rootlesskit --version; grep -o 'port-driver=[a-z0-9]*' ~/.config/systemd/user/docker.service"; done | sort -u | wc -l)" = 2 ]` exits 0 — two unique lines total (one version, one driver) proves both hosts agree on both.
- **Depends on**: None.

##### T5.9 [specs] — Close the review-coverage gap on `92a4da2`
- **Build**: `92a4da2` ("test(csp): add production CSP enforcement e2e soak") was not covered by either Phase 7 G8 security review pass — both ran against the host range ending at `d6adec7`. It is now an ancestor of the `705833d` frontend baseline, so this is a review-coverage gap, not a merge question. The review reads `haisir-frontend` code; the deliverable is an entry in this repo, which is why the task is tagged `[specs]` and not `[frontend]` — no frontend file changes.
- **Done when**: a `decisions.md` entry records the review verdict on `92a4da2` with a date.
- **Test**: `grep -q '92a4da2' Implementation_planning/decisions.md` exits 0.
- **Depends on**: None.

##### T5.10 [backend] — Declare `question_id` on `ExamReviewChatRequest`
- **Build**: `haisir-frontend/src/features/student/api/student-api.ts:611` sends `question_id`, but `src/schemas/haitu.py:17-27` declares only `attempt_id`, `message` and `history`, so Pydantic drops it. This is not a stray field: the frontend deliberately reversed `explainQuestion`'s parameter order to `(questionId, questionNumber)` and dropped the question-text preview from the student bubble *because* the backend was to re-ground via `question_id` (`use-exam-review-chat.ts:332-338`). Deleting it from the payload would therefore lose UX, not just a dead field. Add `question_id: UUID | None = None`.
- **Done when**: `ExamReviewChatRequest(**payload).question_id` equals the UUID sent in the request body.
- **Test**: `assert ExamReviewChatRequest(attempt_id=a, message="x", question_id=q).question_id == q`
- **Depends on**: None.

##### T5.11 [backend] — Narrow exam-review grounding to the named question
- **Build**: With `question_id` now arriving, restrict the grounding context for the review-chat stream to that question when it is present, falling back to the whole-attempt grounding when it is absent. Behaviour is currently correct but over-broad — grounding covers every question in the attempt, which is not what the endpoint's contract implies.
- **Done when**: a request carrying `question_id` produces a grounding context containing only that question's content.
- **Test**: `assert [c.question_id for c in build_grounding(attempt, question_id=q)] == [q]`
- **Depends on**: T5.10 [backend].

##### T5.12 [deploy] — Confirm the pollers hold no transaction on staging
- **Build**: Deploy the B1 fix to staging, leave the worker idle through several poll cycles, and sample `pg_stat_activity`. This is G5's goal test and the only evidence that the two `rollback()` calls actually close the observed 2h27m sessions rather than moving where they open — a unit assertion on `in_transaction()` cannot see a process-lifetime session on a real host.
- **Done when**: no worker session is `idle in transaction` twenty minutes after worker start on staging.
- **Test**: `sleep 1200; [ "$(psql -tAc "SELECT count(*) FROM pg_stat_activity WHERE state='idle in transaction'")" = 0 ]` exits 0.
- **Depends on**: T5.3 [deploy].

##### T5.13 [deploy] — Fix the certbot hook assertion to survive root ownership and non-`755` modes
- **Build**: T5.12's live run against prod found T5.6/T5.7's assertion is wrong on two counts, not the host. (1) The installed hook is `-rwx------ root root`; the deploy user has no passwordless sudo, so `assert_certbot_hook_matches()`'s plain `sha256sum` returns *Permission denied*, comes back as an empty hash, and the function's `-z` branch reports "Certbot hook not found at …" — a message that misdirects to a missing file when the file is present and merely unreadable. Read it with `sudo sha256sum` / `sudo stat` instead of a bare user-context read. (2) T5.7 demands mode exactly `755`; the installed copy is `700`, which is functionally correct (root runs certbot, root execs the hook) — loosen the check to "owner-executable" (`stat -c '%a'` first digit is `7`) rather than an exact match.
- **Done when**: `assert_certbot_hook_matches()` correctly reports match/mismatch against a root-owned, mode-`700` hook without a false "not found", and accepts any owner-executable mode.
- **Test**: Against a real root-owned `700` copy identical in content to the repo's: the deploy's Step 2b passes. Against a deliberately drifted copy (content changed, still root-owned `700`): Step 2b fails citing a hash mismatch, not "not found".
- **Depends on**: T5.6 [deploy], T5.7 [deploy].

---

## G6 — Env config is version-controlled and fails closed

**Goal**: The three deploy config files ship with the release instead of being hand-copied to each host, host topology comes from `secret/haisir/infra` fully derived, `ip-restriction` denies by default, and the remote copy is never authoritative.
**Goal test**: Delete all three env-config files off the staging host, run a CI deploy from a clean workspace, and the deploy completes with the three files present at mode `600` matching the committed copies byte for byte, while `curl -o /dev/null -w '%{http_code}' https://<staging-host>/admin/master/console/` returns `403` from a non-whitelisted address and `200` from a whitelisted one.
**Repos**: [deploy] [specs]

> **SCOPE GUARD — applies to every task in G6 without exception.** Three files by exact filename, across `dev`, `staging` and `prod`: `dev/.env`, `staging/.env`, `prod/.env`, `dev/.env.config.sh`, `staging/.env.config.sh`, `prod/.env.config.sh`, `common/.env.config.common.sh`. Seven paths. No prefix or suffix variants, no glob or regex matching, no other file in those directories. Every `.gitignore` negation, rsync exclude, gitleaks entry, KV migration **and every `grep`/`git grep` pathspec in a test command below** is enumerated by exact path.

---

### G6.1 — Host topology resolves from KV, fully derived

**Subgoal**: Nine host-topology values resolve from `secret/haisir/infra` for staging and prod — eight moved out of the env-config files, plus `KC_HOSTNAME_ADMIN`, which is net-new and appears in none of the seven files today — stored as final values, with a fail-closed gate on each.

> **⟲ Amended 2026-08-13 (T6.2.0): eight, not nine.** `KC_HOSTNAME_ADMIN` was seeded (T6.1.3) and gated (T6.1.5) for a consumer — G6.2's tailnet admin model — that has since been abandoned as unworkable. Its gate entry is removed from `deploy-required-keys.txt`; a stale KV value may remain on staging and is inert. The other eight are unaffected. T6.1.3/T6.1.4/T6.1.5 stay checked off as the historical record of what was seeded.
**Subgoal test**: On staging with the eight keys removed from both files and the three decorative `:-` CIDR defaults removed from the common file, `bash common/scripts/template-configs.sh` renders every `*_CIDR` and `*_BASE_URL` placeholder to the same value it produced before the move; with `secret/haisir/infra` unreadable, the render aborts non-zero before writing any file.
**Repos**: [deploy]

##### T6.1.1 [deploy] — `template-configs.sh` sources the render hook
- **Build**: `common/scripts/template-configs.sh` is the only provisioning script that does not source `render-secrets-hook.sh` — `setup.sh:121`, `setup-keycloak.sh:23`, `configure-ssl.sh:39`, `create_plugin_config.sh:23` and `create_route_config.sh:23` all do — and it is the sole consumer of the admin CIDRs. Add the same `source .../openbao/render-secrets-hook.sh` + `render_deploy_secrets_or_die` pair, after the `.env.config.sh` discovery block at `:14-30` and before placeholder expansion. **This is the unblocking task for all of G6**: the hook is a no-op when the OpenBao flag is off, so it is safe to land alone, but the CIDR move must not land without it or every CIDR renders empty — which under today's code is exactly the fail-open path G6.2 exists to close.
- **Done when**: `template-configs.sh` sources `render-secrets-hook.sh` and calls `render_deploy_secrets_or_die` before placeholder expansion.
- **Test**: `grep -q 'render-secrets-hook.sh' common/scripts/template-configs.sh` exits 0.
- **Depends on**: None.

##### T6.1.2 [deploy] — Delete `template-configs.sh`'s cross-environment config fallback
- **Build**: `common/scripts/template-configs.sh:15-30` resolves `ENV_CONFIG` as `$PWD/.env.config.sh` → `../staging/.env.config.sh` → `../dev/.env.config.sh` → `../prod/.env.config.sh`. Those three fallbacks are dead today only because a clean checkout has no committed `.env.config.sh` anywhere; the moment G6.3 commits the seven paths they become live, and any invocation from a directory without its own `.env.config.sh` — **including a prod run** — silently templates with *staging's* config. Delete the `elif` chain at `:19-25`; keep the existing `if [ -z "$ENV_CONFIG" ]` hard failure at `:28-31` as the only remaining branch. Must land before T6.3.2 commits the files.
- **Done when**: `template-configs.sh` exits non-zero when run from a directory containing no `.env.config.sh`.
- **Test**: `(cd "$(mktemp -d)" && bash /path/to/haisir-deploy/common/scripts/template-configs.sh)` exits non-zero.
- **Depends on**: T6.1.1 [deploy].

##### T6.1.3 [deploy] — Seed `KC_HOSTNAME_ADMIN` into KV for staging and prod — ⟲ **SUPERSEDED 2026-08-13 by T6.2.0** (done, kept as record; the key it seeded now has no consumer)
- **Build**: Write the single key `KC_HOSTNAME_ADMIN` into `secret/haisir/infra` for staging and prod, holding its **final** value — the tailnet origin, not the public one. This key is **net-new**: `grep` across all seven in-scope paths at `844e8f9` finds it in none of them, so nothing is being moved and no config file is edited here. It is split out from the other eight because G6.2 — the most urgent open security item on the system — needs only this one, and must not queue behind an eight-key migration across two environments. No new path, policy or machine identity: `secret/haisir/infra` exists and the `deploy` policy already grants read on it.
- **Done when**: `bao kv get -format=json secret/haisir/infra` returns a non-empty `KC_HOSTNAME_ADMIN` on both staging and prod.
- **Test**: `[ -n "$(bao kv get -field=KC_HOSTNAME_ADMIN secret/haisir/infra)" ]` exits 0 on each of staging and prod.
- **Depends on**: T6.1.1 [deploy].

##### T6.1.4 [deploy] — Seed the other eight infra keys, fully derived
- **Build**: Write the remaining eight keys into `secret/haisir/infra` for staging and prod, each holding its **final** value: `KEYCLOAK_ADMIN_PORT_BINDING`, `BACKEND_DB_PORT_BINDING`, `TAILSCALE_ADMIN_CIDR`, `KEYCLOAK_ADMIN_ALLOWED_CIDR`, `APISIX_ADMIN_ALLOWED_CIDR`, `EXTRACTION__OLLAMA_BASE_URL`, `EMBEDDING__OLLAMA_BASE_URL`, `HAITU__RERANK_BASE_URL`. The base addresses `TAILSCALE_IP`, `CLIENT_ADMIN_TAILSCALE_IP` and `COMPUTE_TAILSCALE_IP` **must not** be stored and composed at render time: `env-setup.sh:128-157` sources `.env.config.sh` and `.env` *before* rendering from OpenBao, so a base address arriving later leaves `${TAILSCALE_IP}/32` already evaluated to the literal `/32`.
- **Done when**: no value under `secret/haisir/infra` on staging or prod contains an unexpanded `${`.
- **Test**: `[ -z "$(bao kv get -format=json secret/haisir/infra | jq -r '.data.data | to_entries[] | select(.value | contains("${")) | .key')" ]` exits 0.
- **Depends on**: T6.1.3 [deploy].

##### T6.1.5 [deploy] — Arm the per-key fail-closed gate for all nine
- **Build**: Append nine `infra:<KEY>:envs=staging,prod` lines to `common/openbao/deploy-required-keys.txt`, following the file's documented `path:KEY:envs=` format. This arms the existing per-key check so a partially-seeded KV aborts the render rather than templating an empty value (BR-SEC-019). Land this **before** T6.1.7/T6.1.9 delete any plaintext — the manifest's own convention is gate first, delete second, so a half-cutover state is unrepresentable. No dev key: dev has no host-topology values and no CI deploy path.
- **Done when**: `deploy-required-keys.txt` contains all nine key names with `envs=staging,prod`.
- **Test**: `orig=$(bao kv get -field=KC_HOSTNAME_ADMIN secret/haisir/infra); bao kv patch secret/haisir/infra KC_HOSTNAME_ADMIN=""; APP_ENV=staging bash common/openbao/render-deploy-secrets.sh 2>&1 | grep -q KC_HOSTNAME_ADMIN; rc=$?; bao kv patch secret/haisir/infra KC_HOSTNAME_ADMIN="$orig"; [ $rc -eq 0 ]` exits 0 (the key is restored unconditionally — this test blanks live KV, so it must not leave it blanked on failure).
- **Depends on**: T6.1.4 [deploy].

##### T6.1.6 [deploy] — Delete the three decorative CIDR defaults from the common file
- **Build**: Delete `common/.env.config.common.sh:39` (`export TAILSCALE_ADMIN_CIDR="${TAILSCALE_ADMIN_CIDR:-127.0.0.1/32}"`), `:44` (`KEYCLOAK_ADMIN_ALLOWED_CIDR`, same shape) and `:48` (`APISIX_ADMIN_ALLOWED_CIDR`, same shape) outright. That path is one of the seven, and `deploy.sh:591` runs `cd ${ENV} && source .env.config.sh && … && bash template-configs.sh` where `.env.config.sh` sources the common file — so all three are exported as `127.0.0.1/32` **before** the render hook fires, and any `${VAR:-…}` there pre-empts the KV value. Without this deletion, `APISIX_ADMIN_ALLOWED_CIDR` on prod silently reverts from B5's `172.19.0.1/32` to `127.0.0.1/32`, `setup.sh` cannot reach the Admin API and routes are never pushed — the v2026.6 failure, reproduced by this plan. It is also the same decorative-`:-` pattern that made B6's fail-closed default inert. No other line in the file is touched.
- **Done when**: `common/.env.config.common.sh` contains no `_CIDR` assignment.
- **Test**: `! grep -q '_CIDR=' common/.env.config.common.sh` exits 0.
- **Depends on**: T6.1.5 [deploy].

##### T6.1.7 [deploy] — Remove the eight from staging's config files
- **Build**: Delete the eight assignments from `staging/.env.config.sh` and `staging/.env` (those two paths only; `KC_HOSTNAME_ADMIN` was never in either). Before deleting, capture the pre-move rendered output of `template-configs.sh` into `.templated-before/`; after deleting, diff the rendered output. Staging is the proving ground because `dev/.env.config.sh:54` sets `KEYCLOAK_ADMIN_ALLOWED_CIDR="0.0.0.0/0"` — a deliberate dev convenience that stays, so dev never exercises this path.
- **Done when**: a staging render after the deletion is byte-identical to the render captured before it.
- **Test**: `[ -z "$(diff -r .templated-before .templated)" ]` exits 0.
- **Depends on**: T6.1.6 [deploy].

##### T6.1.8 [deploy] — Positive control: the render aborts when KV is unreadable
- **Build**: T6.1.7's byte-identical diff passes whether the value came from KV or from a surviving `${VAR:-default}` — it cannot, on its own, distinguish "KV supplied it" from "a default supplied it", which is exactly the blind spot that made the three CIDRs decorative. Add the negative half: with `secret/haisir/infra` unreadable (bad token), the staging render must abort non-zero **before writing any file**, rather than producing the same output. Assert `.templated/` is untouched on the failure path.
- **Done when**: a staging render with an invalid `BAO_TOKEN` exits non-zero and writes no file into `.templated/`.
- **Test**: `BAO_TOKEN=invalid bash common/scripts/template-configs.sh` exits non-zero.
- **Depends on**: T6.1.7 [deploy].

##### T6.1.9 [deploy] — Remove the eight from prod's config files
- **Build**: Same deletion in `prod/.env.config.sh` and `prod/.env` (those two paths only), only after T6.1.7's staging render proves identical and T6.1.8 proves the gate is live. Note `prod/.env.config.sh:23` currently sets `KEYCLOAK_ADMIN_ALLOWED_CIDR=""` explicitly — that assignment goes away here, and G6.2 makes its absence harmless rather than fatal.
- **Done when**: a prod render after the deletion is byte-identical to the render captured before it.
- **Test**: `! grep -qE '^ *(export )?(KEYCLOAK_ADMIN_PORT_BINDING|BACKEND_DB_PORT_BINDING|TAILSCALE_ADMIN_CIDR|KEYCLOAK_ADMIN_ALLOWED_CIDR|APISIX_ADMIN_ALLOWED_CIDR|EXTRACTION__OLLAMA_BASE_URL|EMBEDDING__OLLAMA_BASE_URL|HAITU__RERANK_BASE_URL)=' prod/.env prod/.env.config.sh` exits 0.
- **Depends on**: T6.1.8 [deploy].

---

### G6.2 — `ip-restriction` denies by default and is always present

**Subgoal**: An empty, missing or unrendered `*_CIDR` reduces admin reach to zero instead of publishing the route, and the operator retains admin access to Keycloak over the public hostname from a whitelisted IP. (BR-SEC-023; absorbs B6.)
**Subgoal test**: Render routes 13/14/15 with every `*_CIDR` unset; each rendered file contains `.plugins["ip-restriction"].whitelist == ["127.0.0.1/32"]`. After applying on staging, `https://<staging-host>/admin/master/console/` returns 403, returns 200 after `keycloak-admin-access.sh grant`, and returns 403 again after `revoke` — while `https://<staging-host>/realms/haisir-realm-staging/.well-known/openid-configuration` returns 200 throughout.
**Repos**: [deploy]

> **⟲ SCOPE REVERSAL 2026-08-13 — the tailnet admin model is abandoned. Read this before touching any G6.2 task.**
>
> T6.2.1/T6.2.1a/T6.2.1b/T6.2.2 tried to make admin access work over the Tailscale tailnet, via `KC_HOSTNAME_ADMIN` + `KEYCLOAK_ADMIN_PORT_BINDING`. **It cannot work, and it broke things.** Two measured findings, both from the 2026-08-12 gate run:
> 1. `KC_HOSTNAME_ADMIN` does **not** move the admin console's `authServerUrl` — that follows `KC_HOSTNAME`. The console shell loads over the tailnet, then keycloak-js initialises against the **public** origin to authenticate, hitting route 14, which the deny-all is designed to 403. The tailnet path was never end-to-end.
> 2. `KC_HOSTNAME_ADMIN` is **server-global, not master-scoped**. Pointing it at the tailnet broke the *public* admin console too — proven by natural experiment against prod, which has never had the variable.
>
> `phases.md` recorded the right answer during the v2026.6 window and this plan overrode it: a tailnet `/32` can never match what `ip-restriction` evaluates, because `real-ip` extracts the client address from `cf-connecting-ip`. The corollary the plan missed is that the *converse* also holds — the whitelist has to hold the operator's **public** IP, and once it does, the public path is the working admin path and no tailnet plumbing is needed at all.
>
> **The replacement model** (owner call, 2026-08-13): routes 13/14/15 stay published on the public hostname and ship **deny-all**. **No operator CIDR is stored in the deployment at all** — `KEYCLOAK_ADMIN_ALLOWED_CIDR` is *deleted* from KV and from the required-keys gate, not merely set to a safe value (T6.2.0a), so on staging and prod there is nothing that can resolve empty, drift, or fail open. The deny-all comes from T6.2.3's guard in `template-configs.sh`. When an operator needs the console they grant their own public IP directly to the running APISIX with `keycloak-admin-access.sh` (T6.2.0b) and revoke when done; a deploy **preserves** a live grant rather than revoking it mid-session (T6.2.0c). `KC_HOSTNAME_ADMIN` is deleted from compose, from the gate, and from KV. Strictly tighter than the pre-v2026.7 model, which kept a standing allowlist in config.
>
> **The one thing this model gives up**: grants no longer self-expire. Nothing but `revoke` closes one. That is the deliberate trade for "a deploy must never revoke access mid-session" — see T6.2.0c.
>
> **Why this is not an access-loss risk the way the old plan was.** Routes 13/14/15 match `/admin/*`, `/realms/master/*` and `/resources/*` gated by `^/resources/[^/]+/admin/`. App login is route 01, `/realms/haisir-realm-{{APP_ENV}}/*` (realm name at `common/keycloak/01-realm.json:2`). **Zero path overlap — an admin CIDR change is structurally incapable of affecting normal user authentication.** The only lockout risk left is a wrong CIDR value, recoverable by re-seeding KV and re-pushing routes, provided `APISIX_ADMIN_ALLOWED_CIDR` still admits the Admin API (verify before T6.2.6).
>
> **Superseded tasks below are kept, not deleted** — repo convention is to preserve incident history.

> **Ancestry check**: G6.2's only ancestors are T6.1.1 → T6.1.3. Neither touches an image, a Dockerfile or a compose `image:` line, so no G1–G4 task is upstream of this subgoal, directly or transitively.

##### T6.2.0 [deploy] — Revert `KC_HOSTNAME_ADMIN` and the tailnet admin model
- **Build**: Three deletions, no replacement. (1) Delete the `KC_HOSTNAME_ADMIN=${KC_HOSTNAME_ADMIN}` line from the keycloak service in `common/docker-compose.yml` — **delete the line, do not merely clear the KV value**: an unset `${KC_HOSTNAME_ADMIN}` expands to an empty string, which Keycloak reads as set-and-invalid rather than absent. (2) Delete the `infra:KC_HOSTNAME_ADMIN:envs=staging,prod` entry and its comment from `common/openbao/deploy-required-keys.txt`, otherwise every staging/prod deploy fails closed on a key with no consumer. (3) Correct `.github/instructions/keycloak.instructions.md`, which tells the reader to set `KEYCLOAK_ADMIN_ALLOWED_CIDR` to a Tailscale CIDR — wrong for any Cloudflare-fronted env and the origin of this whole detour. `KEYCLOAK_ADMIN_PORT_BINDING` is **kept**: it predates this attempt and `deploy.sh:960` runs `setup-keycloak.sh` against it every deploy.
- **Done when**: no tracked file in `haisir-deploy` references `KC_HOSTNAME_ADMIN` except as historical commentary, and `KEYCLOAK_ADMIN_PORT_BINDING` is untouched.
- **Test**: `! grep -rn 'KC_HOSTNAME_ADMIN=' common/ && grep -q 'KEYCLOAK_ADMIN_PORT_BINDING' common/docker-compose.yml` exits 0.
- **Depends on**: none — this is a pure revert and unblocks the rest of G6.2.

##### T6.2.0a [deploy] — Delete `KEYCLOAK_ADMIN_ALLOWED_CIDR` (and `KC_HOSTNAME_ADMIN`) from KV and the gate
- **Build**: Owner call 2026-08-13 — **remove the variable rather than set it**, so there is no stored allowlist to resolve empty, drift, or fail open. (1) Delete the `infra:KEYCLOAK_ADMIN_ALLOWED_CIDR:envs=staging,prod` line from `common/openbao/deploy-required-keys.txt` (done in-repo). (2) Delete **both** `KEYCLOAK_ADMIN_ALLOWED_CIDR` and the stale `KC_HOSTNAME_ADMIN` from `secret/haisir/infra` on staging and prod — live KV, operator action. With the key unset everywhere, `template-configs.sh` renders routes 13/14/15 to the deny-all default (`127.0.0.1/32`) from T6.2.3's guard alone. `dev/.env.config.sh:54` keeps its explicit `0.0.0.0/0` and is the only env where the variable exists.
- **Why this is also the prod deploy unblocker**: T6.1.5 armed the gate on this key and `check_required_keys()` (`render-deploy-secrets.sh:84-106`) rejects a **seeded-but-empty** value — jq `@sh` renders `""` as exactly `''`. Prod's KV holds `""` (T6.1.9), so **prod's next deploy currently aborts at render time**. Removing the gate entry and the key clears it. Note this changes nothing live on its own: prod's routes are v2026.6-rendered in etcd until T6.2.6 re-pushes them.
- **Ordering**: delete the gate entry *before* deleting the KV keys, or the deploy fails closed on a key that is gone. Both are safe on their own.
- **Done when**: neither key exists under `secret/haisir/infra` on staging or prod, and `render-deploy-secrets.sh` exits 0 on both.
- **Test**: `[ -z "$(bao kv get -format=json secret/haisir/infra | jq -r '.data.data | keys[] | select(. == "KEYCLOAK_ADMIN_ALLOWED_CIDR" or . == "KC_HOSTNAME_ADMIN")')" ] && APP_ENV=prod bash common/openbao/render-deploy-secrets.sh >/dev/null` exits 0.
- **Depends on**: T6.2.0 [deploy].

##### T6.2.0c [deploy] — A deploy must not revoke a live admin grant
- **Build**: In `common/scripts/create_route_config.sh`, before the whole-route `PUT`, read the live route from the Admin API; if it already carries `plugins["ip-restriction"].whitelist`, carry that value into the payload. Scoped to that one field — WAF directives, rate limits and upstream still come from the repo, so this preserves an *access decision*, not arbitrary drift. A route with no live whitelist (new host, or the plugin stripped by the pre-T6.2.3 bug) has nothing to preserve and gets the template's deny-all, which is what closes the exposure on first push.
- **Preservation must be BOUNDED — found by challenger review 2026-08-13, and it was a real hole.** The first cut carried the live value forward unconditionally, which laundered *any* whitelist into permanence: a `0.0.0.0/0` pasted from dev, a fat-fingered `curl`, or a leaked admin key would be re-published by every subsequent deploy and never expire. Demonstrated empirically against a mock Admin API — the deploy re-published `0.0.0.0/0` over the template's deny-all and logged it as a normal "preserving" line. Fix: refuse to preserve any entry broader than `MAX_PRESERVE_PREFIX` (`/24`), fall back to the template's deny-all, and say so loudly. Refusing an illegitimate grant is a deliberate exception to "a deploy never revokes" — the rule protects an operator's own narrow grant, not an unbounded one. `keycloak-admin-access.sh`'s `MIN_GRANT_PREFIX` must stay `>=` this value or the script could issue a grant the next deploy then refuses.
- **Consequence to document loudly**: grants no longer self-expire. The earlier design leaned on "the next deploy reverts it"; owner call is that a deploy must never revoke access mid-session, so `revoke` is now the *only* thing that closes a grant. `keycloak-admin-access.sh` and the instructions file both say so explicitly.
- **Done when**: a route push preserves a narrow grant, refuses a broad one, and applies deny-all to a route that has none.
- **Test**: `common/scripts/tests/route-whitelist-preservation-check.sh` — six cases against a mock Admin API on loopback, offline. Verified it fails when `MAX_PRESERVE_PREFIX` is weakened.
- **Depends on**: T6.2.0 [deploy].

##### T6.2.0b [deploy] — Grant/revoke script for on-demand admin access
- **Build**: `common/scripts/keycloak-admin-access.sh` with `status` / `grant [CIDR]` / `revoke`, writing the whitelist on routes `keycloak-admin`, `keycloak-master-realm` and `keycloak-admin-resources` directly through the APISIX Admin API. Sub-path `PATCH /apisix/admin/routes/{id}/plugins/ip-restriction/whitelist` so the route's WAF directives, rate limits and upstream are left untouched — a whole-route `PUT` would mean reconstructing all of that by hand. `grant` with no argument detects the caller's **public** IP; it refuses `0.0.0.0/0`. `revoke` resets to `[127.0.0.1/32]`, never an empty array (fails the plugin's schema). Grants are intentionally **not** persisted — the next deploy re-templates from the repo and reverts them, so a forgotten grant cannot outlive a deploy. Resolve `APISIX_ADMIN_KEY` through the same fail-closed OpenBao hook `setup.sh:115-121` uses. Document the runbook in `.github/instructions/keycloak.instructions.md`.
- **Done when**: the script grants, reports and revokes against a live APISIX, and the runbook is in the instructions file.
- **Test**: `bash common/scripts/keycloak-admin-access.sh status` lists all three routes as `deny-all` on a freshly deployed host; `grant 203.0.113.4/32` then `status` shows them granted; `revoke` then `status` returns all three to `deny-all`.
- **Depends on**: T6.2.0 [deploy].

##### ~~T6.2.1 [deploy] — Add `KC_HOSTNAME_ADMIN` to the Keycloak service~~ — ⟲ **SUPERSEDED by T6.2.0** (shipped, then reverted; kept as record)
- **Build**: ~~Add `KC_HOSTNAME_ADMIN=${KC_HOSTNAME_ADMIN}` to the keycloak service environment block in `common/docker-compose.yml`.~~ Shipped in v2026.7 and broke the staging admin console. Its test — `KC_HOSTNAME_ADMIN != KC_HOSTNAME` — is satisfied by any wrong value, which is exactly how a dead address passed. **Lesson carried forward to T6.2.5/T6.2.6**: a `*_HOSTNAME_*`/`*_URL` assertion must compare against the live `docker port` mapping, never against another variable.

##### ~~T6.2.1a / T6.2.1b / T6.2.2~~ — ⟲ **SUPERSEDED by T6.2.0** (kept as record; see TASKS.md for the full incident notes)
- T6.2.1a re-seeded `KC_HOSTNAME_ADMIN` to restore the staging console. Its two operational findings survive the reversal and are still true: `rotate-secret.sh`'s `[restart-container]` argument does **not** apply to compose-env values (`Config.Env` is fixed at create time — a **recreate** is required), and `{env}/.env.runtime` does not exist between deploys and must be regenerated the way `build_compose_cmd` does (`deploy-lib.sh:244-252`).
- T6.2.1b asked for a Tailscale ACL opening `tcp:8180`. **No longer required.** Optional break-glass only, for running `setup-keycloak.sh` by hand from an operator box; it is not an admin-console path (`KC_HOSTNAME_STRICT=true` rejects browser use).
- T6.2.2 ran 2026-08-12 and **failed**, producing the two measurements that killed the tailnet model.

##### T6.2.3 [deploy] — Replace plugin-stripping with a deny-all whitelist
- **Build**: Net deletion in `common/scripts/template-configs.sh`. At `:152`, substitute `127.0.0.1/32` into `value` instead of setting `strip_ip_restriction=true`. Delete the `jq del(.plugins["ip-restriction"])` block at `:168-172` in full, including its "no restriction — drop the whole plugin" comment. An empty whitelist array fails `ip-restriction`'s own schema, so `127.0.0.1/32` is the schema-valid expression of deny-all — and because `real-ip` resolves the client address from `cf-connecting-ip` in prod, no external client can ever present it. The plugin is now present regardless of how the variable resolves, which also makes `prod/.env.config.sh:23`'s explicit `""` harmless: the mechanism no longer depends on the value.
- **Done when**: `template-configs.sh` contains no `strip_ip_restriction` variable and no `jq del` call.
- **Test**: `! grep -qE 'strip_ip_restriction|del\(\.plugins' common/scripts/template-configs.sh` exits 0.
- **Depends on**: T6.2.0 [deploy]. *(Was T6.2.2 — the tailnet gate it waited on is withdrawn. The `authServerUrl` question logged against this task on 2026-08-12 is **moot**: route 14 stays reachable from a granted address, so the login redirect resolves normally. Amended: the default must also cover the **unset** case, not just empty, so the guard moves ahead of the `[ -v ]` check.)*

##### T6.2.4 [deploy] — Regression test that fails if fail-open returns
- **Build**: Add a test to `common/scripts/tests/` that renders routes `13-keycloak-admin.json`, `14-keycloak-master-realm.json` and `15-keycloak-admin-resources.json` with `KEYCLOAK_ADMIN_ALLOWED_CIDR` unset and asserts the whitelist equals `["127.0.0.1/32"]` — assert the *presence and value*, not the absence of the key. This is the regression the whole subgoal exists to prevent; the original defect produced three cheerful `INFO: ip-restriction disabled` lines and nothing else.
- **Done when**: the test passes on the fixed script and fails when the `jq del` block is restored.
- **Test**: `KEYCLOAK_ADMIN_ALLOWED_CIDR= bash common/scripts/template-configs.sh && jq -e '.plugins["ip-restriction"].whitelist == ["127.0.0.1/32"]' .templated/13-keycloak-admin.json` exits 0.
- **Depends on**: T6.2.3 [deploy].

##### T6.2.5 [deploy] — Apply the deny-all on staging
- **Build**: Re-template and push routes 13/14/15 on staging: `deploy.sh --steps apisix_routes` (→ `setup.sh --routes-only`). No version bump and no image pull. Then run T6.2.0b's script end-to-end on staging — `status` → `grant` → console loads → `revoke` — because staging is where a mistake is cheap.
- **Done when**: the staging public Keycloak console path returns 403 by default, 200 after `grant`, 403 again after `revoke`, and app login is unaffected throughout.
- **Test**: `[ "$(curl -o /dev/null -sw '%{http_code}' https://<staging-host>/admin/master/console/)" = 403 ]` and `[ "$(curl -o /dev/null -sw '%{http_code}' https://<staging-host>/realms/haisir-realm-staging/.well-known/openid-configuration)" = 200 ]` both exit 0.
- **Depends on**: T6.2.4 [deploy], T6.2.0b [deploy].

##### T6.2.6 [deploy] — Apply the deny-all on prod — 🚫 **[PROD-GATED]**
> **Deferred by owner call 2026-08-13**: no prod deploy until every non-prod-gated task in this phase is done. This task and T6.2.7 are what the prod window is *for*, not blockers on reaching it. Accepted consequence: prod's admin console stays publicly reachable until then.
- **Build**: Re-template and push routes 13/14/15 on prod, same `--steps apisix_routes` path. B6's confirmed public reachability was `GET https://haisir.in/admin/master/console/ → 200` and `GET https://haisir.in/realms/master/.well-known/openid-configuration → 200`. **Before running: confirm `APISIX_ADMIN_ALLOWED_CIDR` on prod still admits the Admin API** (B5's `172.19.0.1/32`, not `127.0.0.1/32`) — if `setup.sh` cannot reach the Admin API, routes are never pushed and there is no way to grant access back. This is the v2026.6 failure mode and PLAN.md's T6.1.6 note flags exactly it.
- **Done when**: the prod public Keycloak console path returns 403 and prod's app login is unaffected.
- **Test**: `[ "$(curl -o /dev/null -sw '%{http_code}' https://haisir.in/admin/master/console/)" = 403 ]` exits 0 (was `200`), and `[ "$(curl -o /dev/null -sw '%{http_code}' https://haisir.in/realms/haisir-realm-prod/.well-known/openid-configuration)" = 200 ]` exits 0.
- **Depends on**: T6.2.5 [deploy].

##### T6.2.7 [deploy] — Prove admin access can still be granted on prod after the deny-all — 🚫 **[PROD-GATED]**
- **Build**: Immediately after T6.2.6, run `keycloak-admin-access.sh grant` on prod, log into the admin console over the public hostname, then `revoke`. Split from T6.2.6 deliberately — "public is denied" and "admin still has a way in" fail independently, and the second one failing is a lockout, so it needs its own explicit pass/fail rather than riding on the 403 check.
- **Done when**: an admin session is established on the prod console after a grant, and the console returns to 403 after the revoke.
- **Test**: `keycloak-admin-access.sh grant && [ "$(curl -o /dev/null -sw '%{http_code}' https://haisir.in/admin/master/console/)" = 200 ] && keycloak-admin-access.sh revoke && [ "$(curl -o /dev/null -sw '%{http_code}' https://haisir.in/admin/master/console/)" = 403 ]` exits 0.
- **Depends on**: T6.2.6 [deploy].

##### T6.2.8 [deploy] — Fix `config.yaml`'s inaccurate `allow_admin` default comment
- **Build**: `common/apisix_conf/config.yaml:94`'s comment claims `{{TAILSCALE_ADMIN_CIDR}}` "defaults to `127.0.0.1/32` when unset" — no such default exists. T6.2.3's deny-all guard lives in `template-configs.sh` and is gated on `.json` output; `config.yaml` is YAML and never enters that branch. Found while implementing T6.2.3, filed here 2026-08-13. Not a live exposure today — `TAILSCALE_ADMIN_CIDR` and `APISIX_ADMIN_ALLOWED_CIDR` are both seeded in `secret/haisir/infra` and gated `envs=staging,prod` in `deploy-required-keys.txt`, so a missing/empty value on those envs already fails the render closed at the gate, before this comment's claim would ever be tested. The gap is narrower than that: an env outside the gate, or a value that resolves to blanks-only rather than empty, has no fallback the comment promises. Fix the comment to state the true behavior, or extend the deny-all guard to also cover `.yaml`/`.yml` output — owner call on which.
- **Done when**: `config.yaml`'s comment accurately describes what happens when `TAILSCALE_ADMIN_CIDR` is unset (either because the guard now covers it, or because the comment says there is no default and points at the gate as the real backstop).
- **Test**: manual read — the comment and the code agree once this lands; no automated assertion, this is a documentation-accuracy fix.
- **Depends on**: T6.2.3 [deploy].

---

### G6.3 — The seven paths are committed, scanned, and sourced from the release

**Subgoal**: The seven paths are tracked in git, gitleaks scans them for real, no `REMOTE_*` variable can be sourced from a committed file into a CI workspace, and the rsync no longer treats the remote copy as authoritative.
**Subgoal test**: `git ls-files` lists all seven paths; `gitleaks detect --no-git` over the repo exits 0; `git grep 'REMOTE_HOST' --` over the seven literal paths returns nothing; and `deploy-lib.sh` carries no `--exclude` for any of the three filenames.
**Repos**: [deploy]

> **This is ONE COMMIT, and the graph now enforces it rather than describing it.** The env rsync at `deploy-lib.sh:136-144` carries `--delete` (`:142`), and the excludes at `:139-141` are currently the only thing protecting the remote copies from it. Committing the files without removing the excludes leaves the remote copy authoritative; removing the excludes without committing the files deletes them off the host; committing them without stripping `REMOTE_*` makes `load_env_config` overwrite the Jenkins-injected SSH target on the very next CI run. In draft v1 these were four tasks with an ordering note — a legal topological order existed that shipped the credential clobber. They are one task here.

##### T6.3.1 [deploy] — Precondition: scan the seven paths for secret and topology residue
- **Build**: Before the files land in git, confirm each of the seven holds only ports, public hostnames, image tags, feature flags and `VERSION=` — no secret-shaped values (Phase 5.6 migrated them all to KV) and no host-topology values (G6.1 moved those). Run the existing `common/scripts/tests/full-plaintext-elimination-scan.sh` (it lives under `common/scripts/tests/`, alongside `plaintext-residue-scan.sh` — not under `common/openbao/`) over all three environments. Anything still present is a G6.1 gap to close there, not a new exception to record here. This is a gate on T6.3.2, not part of its commit.
- **Done when**: `full-plaintext-elimination-scan.sh` reports zero migrated-key-name residue across dev, staging and prod.
- **Test**: `bash common/scripts/tests/full-plaintext-elimination-scan.sh` exits 0.
- **Depends on**: T6.1.9 [deploy].

##### T6.3.2 [deploy] — Land the seven paths, the scanner and the sync in one commit
- **Build**: One commit, five edits, none of which is safe without the others:
  **(a) `.gitignore` negations by exact name.** `.gitignore:1` is `.env*`, which currently excludes all seven. Add `!dev/.env`, `!staging/.env`, `!prod/.env`, `!dev/.env.config.sh`, `!staging/.env.config.sh`, `!prod/.env.config.sh`, `!common/.env.config.common.sh` — seven lines written out individually, no glob, no `!**/.env.config.sh`. `.env.local` and every other `.env*` file stays ignored.
  **(b) Strip `REMOTE_*` from the committed files.** Delete `REMOTE_HOST`, `REMOTE_USER` and `REMOTE_DEPLOY_DIR` outright from `staging/.env.config.sh:36`, `prod/.env.config.sh:34` and `common/.env.config.common.sh`. `${VAR:-default}` is **not** an acceptable substitute — that is the same decorative-`:-` pattern T6.1.6 deletes. Today CI never sees these files, so `deploy.sh:195`'s `elif [[ -z "${REMOTE_HOST:-}" ]]` branch is taken and the Jenkins credentials survive; once committed they exist in the workspace, `load_env_config` sources them, and `export REMOTE_HOST=...` **overwrites the credential**, pointing the deploy at whatever host the file names. Safe to remove: every consumer is deploy-client-side (`deploy.sh`, `deploy-lib.sh`, `deploy-remote-common.sh`, `common/scripts/tests/test-runner.sh`, `verify-setup.sh`), and nothing on a staging or prod host reads them.
  **(c) Make gitleaks actually scan the filenames.** Delete the two allowlist entries at `.gitleaks.toml:156-157` (`'''(^|\/).*\.env\.config\.sh$'''` and `'''(^|\/).*\.env\.config\.common\.sh$'''`) — they existed because those files were the intentional secrets store, which BR-SEC-011 no longer permits. Add `# pragma: allowlist secret` to `dev/.env:13` (`PGADMIN_DEFAULT_PASSWORD`), a local-only tool credential in the only environment where pgadmin exists and the single recorded BR-SEC-011 exception.
  **(d) Delete the five rsync excludes.** In `common/scripts/deploy-lib.sh`, delete `--exclude='.env'` and `--exclude='.env.config.common.sh'` from the common sync (`:130-131`) and `--exclude='.env'`, `--exclude='.env.config.sh'`, `--exclude='.env.config.common.sh'` from the env sync (`:139-141`). Keep `--exclude='.env.local'` at `:129`. The env sync's `--delete` at `:142` stays; with the files committed it is correct rather than dangerous. Do **not** add `--chmod` to either invocation (see T6.4.1).
  **(e) Delete the `prepare_remote()` backup/restore block.** Delete `deploy-lib.sh:207-231` — the three `cp … .bak` calls before the wipe and the three `mv` restores after, plus the comment claiming these files "live only on the remote (never committed, excluded from rsync) and must survive the wipe-and-recreate cycle". That premise is exactly what BR-SEC-022 reverses. Leave the `rm -rf` + `mkdir -p` itself intact; the rsync now repopulates.
- **Done when**: `git show --stat HEAD` lists `.gitignore`, `.gitleaks.toml`, `common/scripts/deploy-lib.sh` and all seven config paths as a single commit.
- **Test**: `[ "$(git ls-files | grep -cE '^(dev|staging|prod)/\.env(\.config\.sh)?$|^common/\.env\.config\.common\.sh$')" = 7 ]` exits 0.
- **Depends on**: T6.1.2 [deploy], T6.1.9 [deploy], T6.2.7 [deploy], T6.3.1 [deploy].

##### T6.3.3 [deploy] — Verify no committed config path carries a `REMOTE_*` assignment
- **Build**: Assert (b) above landed, using the seven literal pathspecs — no `*/.env` or `*/.env.config.sh` glob, which would match outside the scope guard. This is the check that a future edit reintroducing `REMOTE_HOST=` into a committed file trips.
- **Done when**: none of the seven committed paths contains `REMOTE_HOST`, `REMOTE_USER` or `REMOTE_DEPLOY_DIR`.
- **Test**: `! git grep -qE 'REMOTE_HOST|REMOTE_USER|REMOTE_DEPLOY_DIR' -- dev/.env staging/.env prod/.env dev/.env.config.sh staging/.env.config.sh prod/.env.config.sh common/.env.config.common.sh` exits 0.
- **Depends on**: T6.3.2 [deploy].

##### T6.3.4 [deploy] — Supply all three `REMOTE_*` vars as Jenkins credentials
- **Build**: In `Jenkinsfile.deploy`, bind `REMOTE_DEPLOY_DIR` as a third secret-text credential alongside the existing `REMOTE_HOST`/`REMOTE_USER`, rather than relying on `deploy.sh:204`'s `~/haisir-deploy` fallback expanding correctly inside a quoted rsync target. Every CI deploy from T6.4.2 onward needs this binding present.
- **Done when**: the deploy job's environment block binds all three credentials.
- **Test**: A CI deploy run's console log shows the rsync target as an absolute path with no literal `~`.
- **Depends on**: T6.3.2 [deploy].

##### T6.3.5 [deploy] — Make `deploy.sh` fail closed on a missing SSH target
- **Build**: Delete the two decorative defaults in `deploy.sh`: `:202` `REMOTE_HOST="${REMOTE_HOST:-${ENV}-default}"` (silently invents a hostname) and `:204` `REMOTE_DIR="${REMOTE_DEPLOY_DIR:-~/haisir-deploy}"`. Replace with an explicit abort when any of the three is unset. With the config files now committed, `:193-200`'s `elif` branch no longer guards this — the files always exist in the workspace, so the branch never fires and a missing credential would silently resolve to `staging-default`.
- **Done when**: `deploy.sh` exits non-zero with a named error when `REMOTE_HOST` is unset.
- **Test**: `env -u REMOTE_HOST bash common/scripts/deploy.sh --env staging --dry-run 2>&1 | grep -q REMOTE_HOST` exits 0 with the script itself non-zero.
- **Depends on**: T6.3.4 [deploy].

---

### G6.4 — The release artifact is the only source of the three files on any host

**Subgoal**: The three files land from the release at mode 600 with content identical to the committed copies, with nothing preserved across the wipe.
**Subgoal test**: Delete all three files off the staging host, run a CI deploy, and the files reappear from the release at `600` with contents matching the committed copies byte for byte.
**Repos**: [deploy]

##### T6.4.1 [deploy] — Tighten the three synced files to mode 600, by name
- **Build**: After `sync_files_to_remote` in `common/scripts/deploy-lib.sh`, add one `remote_exec "chmod 600 ${REMOTE_DIR}/${env_name}/.env ${REMOTE_DIR}/${env_name}/.env.config.sh ${REMOTE_DIR}/common/.env.config.common.sh"`, naming the three paths explicitly. Do **not** use `--chmod=D700,F600` on the rsync invocations: those syncs cover all of `common/` and `{env}/`, so a blanket file mode is a scope-guard breach, and `F600` strips the exec bit off every synced script — `common/scripts/full-setup.sh:268` invokes `"$SCRIPT_DIR/setup.sh"` directly, so the next deploy after that change fails with permission denied on a file nobody edited.
- **Done when**: `deploy-lib.sh` sets mode 600 on exactly the three named paths and adds no `--chmod` to either rsync.
- **Test**: `! grep -q -- '--chmod' common/scripts/deploy-lib.sh` exits 0.
- **Depends on**: T6.3.2 [deploy].

##### T6.4.2 [deploy] — Verify the files arrive at mode 600 from an empty start
- **Build**: Delete all three files off the staging host, run a CI deploy, and check the resulting file permissions on the remote.
- **Done when**: all three files exist on staging at mode `600` after a deploy that started with them absent.
- **Test**: `[ "$(ssh <staging> "stat -c '%a' ~/haisir-deploy/staging/.env ~/haisir-deploy/staging/.env.config.sh ~/haisir-deploy/common/.env.config.common.sh" | sort -u)" = 600 ]` exits 0.
- **Depends on**: T6.4.1 [deploy], T6.3.4 [deploy].

##### T6.4.3 [deploy] — Verify the remote content matches the committed copy
- **Build**: In the same deploy run, confirm nothing on the host was preserved across the wipe — the remote content must equal the committed content exactly, with no host-only line surviving.
- **Done when**: each of the three remote files hashes identically to its committed counterpart.
- **Test**: `[ "$(ssh <staging> "sha256sum ~/haisir-deploy/staging/.env" | cut -d' ' -f1)" = "$(sha256sum staging/.env | cut -d' ' -f1)" ]` exits 0.
- **Depends on**: T6.4.2 [deploy].

---

### G6.5 — Version reconciliation is deleted, not repaired

**Subgoal**: `deploy.sh` stops inferring image tags from whatever is on the host and instead asserts the manifest version equals the committed `VERSION=`; drift detection stays.
**Subgoal test**: With the manifest version and `staging/.env`'s `VERSION=` deliberately mismatched, the Validate stage fails before any file reaches the host; with them equal, the deploy proceeds and never runs a remote `sed`.
**Repos**: [deploy]

> **`deploy.sh:6` is `set -euo pipefail`.** Every deletion below removes *reads and consumers together*. Deleting the six `*_IMAGE_TAG_OVERRIDE` reads at `:177-182` while `:266-268` and `:499-504` still reference them aborts every deploy on an unbound variable — which is why T6.5.2 is scoped to the full consumer set, not just the "display block" the draft named.

##### T6.5.1 [deploy] — Delete the remote VERSION rewrite and the tag-reconciliation block
- **Build**: Delete from `common/scripts/deploy.sh` the remote `sed -i 's/^VERSION=.*/VERSION=${VERSION}/'` at `:374` **together with its enclosing three-service guard at `:367-380`** (`_has_backend`/`_has_frontend`/`_has_gateway` and the `else` log line), and the **entire** tag-reconciliation block at `:394-485` — the SSH `grep` of the remote `.env`, `_old_env_vals`/`_old_version`/`_old_tags`, the `DEPLOY_TAG_VARS`/`DEPLOY_TAG_OVERRIDES`/`TAG_TO_COMPOSE_SVC` maps and their upsert loop. (Draft v1 said `:396-420`; the block actually runs to `:485`.) **Keep `:535-574`** — that compares `.env` against running containers, which is drift detection, not version arithmetic, and it stays useful once the file is authoritative. Its `postgres:POSTGRES_IMAGE_TAG:haisir-db-${ENV}` entry stays too (see T2.2).
- **Done when**: `deploy.sh` performs no remote write to `${REMOTE_DIR}/${ENV}/.env`.
- **Test**: `bash -n common/scripts/deploy.sh && ! grep -q "sed -i 's/\^VERSION=" common/scripts/deploy.sh` exits 0.
- **Depends on**: T6.4.3 [deploy].

##### T6.5.2 [deploy] — Delete the override reads and every consumer of them
- **Build**: Delete, in one change: the six `*_IMAGE_TAG_OVERRIDE=$(yaml_read '.image_tags.…')` reads at `deploy.sh:177-182`; the `ROLLBACK_VERSION`/`ROLLBACK_NOTES` reads at `:169-170`; the image-tags display block at `:238-261` **and its `_auto_bumped` loop at `:262-274`**, which reads three of the same vars outside the display block proper; the rollback display at `:299-301`; and **the manifest-override auto-extend block at `:488-520` in full** (`_override_to_compose`, `_override_vals` and their loop) — a second, separate block that reads all six vars at `:499-504` and that draft v1 deleted nothing from. With `set -u` in force and the reads gone, leaving either `:266` or `:499` behind aborts every deploy. With the committed `.env` authoritative, per-service manifest overrides have nothing to override.
- **Done when**: `deploy.sh` contains no `_IMAGE_TAG_OVERRIDE` or `ROLLBACK_VERSION` identifier.
- **Test**: `bash -n common/scripts/deploy.sh && ! grep -qE 'IMAGE_TAG_OVERRIDE|ROLLBACK_VERSION' common/scripts/deploy.sh` exits 0.
- **Depends on**: T6.5.1 [deploy].

##### T6.5.3 [deploy] — Remove the dead manifest fields
- **Build**: Remove the `image_tags` block and `rollback.previous_version` from `releases/manifest-template.yaml`, including the "deploy.sh upserts each specified key as `*_IMAGE_TAG=` in the remote `.env`" comment that documents behaviour T6.5.1/T6.5.2 deleted. Leave `version`, `description`, `services` and `steps`.
- **Done when**: `manifest-template.yaml` contains no `image_tags` or `previous_version` key.
- **Test**: `yq -e '.image_tags == null' releases/manifest-template.yaml` exits 0.
- **Depends on**: T6.5.2 [deploy].

##### T6.5.4 [deploy] — Assert manifest version equals the committed `VERSION=`
- **Build**: Add an assertion to `Jenkinsfile.deploy`'s `stage('Validate')` (`:70`) that the manifest's `version` equals the `VERSION=` line in the committed `{env}/.env`, failing the stage on mismatch. This is what replaces the reconciliation: the committed file is the source of record, so the operation is an equality check, not a repair. BR-SEC-022 is not shippable without it.
- **Done when**: the Validate stage fails when the two values differ.
- **Test**: With `staging/.env` set to `VERSION=2026.5` and the manifest to `version: "2026.7"`, the Validate stage exits non-zero before the Deploy stage runs.
- **Depends on**: T6.5.3 [deploy].

---

### G6.6 — One deploy path, not two

**Subgoal**: The parallel manual deploy implementation is deleted, so every future change to the sync is applied once.
**Subgoal test**: A local deploy performed with `deploy.sh` and the three `REMOTE_*` vars exported produces the same remote tree as a CI deploy, and `common/deploy-remote-common.sh` no longer exists.
**Repos**: [deploy]

##### T6.6.1 [deploy] — Delete the manual deploy scripts
- **Build**: Delete `common/deploy-remote-common.sh`, `staging/deploy-remote.sh` and `prod/deploy-remote.sh`. This is a separately written second implementation of the same sync that has already drifted from `deploy-lib.sh` — different excludes, a different backup set, and `${REMOTE_HOST}:` with no `user@` — and it is the reason B3's `other/` gap exists at all. Keeping it means applying every G6.4 change twice forever. **Must not start before G6.4 lands**: it is currently the only working path for a local deploy, so deleting it first retires the working path.
- **Done when**: none of the three files exists.
- **Test**: `! ls common/deploy-remote-common.sh staging/deploy-remote.sh prod/deploy-remote.sh` exits 0.
- **Depends on**: T6.4.3 [deploy].

##### T6.6.2 [deploy] — Take `REMOTE_HOST` from the environment in the test runner
- **Build**: `common/scripts/tests/test-runner.sh:26-33` loads `REMOTE_HOST` from the env config to reach the host over SSH (`:157`, `:166-201`). T6.3.2 removed it from those files, so this is broken from the moment that commit lands. Change it to read `REMOTE_HOST` from the process environment and fail with its existing "Local tests require REMOTE_HOST to be set" message when absent — same fail-closed behaviour, different source.
- **Done when**: `test-runner.sh` does not source the env config for `REMOTE_HOST`.
- **Test**: `env -u REMOTE_HOST LOCAL_TESTS=true bash common/scripts/tests/test-runner.sh` exits non-zero.
- **Depends on**: T6.3.2 [deploy], T6.6.1 [deploy].

##### T6.6.3 [deploy] — Document the single deploy path
- **Build**: Update `README.md` and `docs/` where they reference `deploy-remote.sh`: a local deploy is `deploy.sh` with `REMOTE_HOST`, `REMOTE_USER` and `REMOTE_DEPLOY_DIR` exported. One path, not two.
- **Done when**: no committed documentation references `deploy-remote.sh`.
- **Test**: `! git grep -q 'deploy-remote' -- '*.md'` exits 0.
- **Depends on**: T6.6.2 [deploy].

---

## G7 — Specs and phase record reflect what shipped

**Goal**: The two governing specs, the phase record and the decision log describe the delivered state, and the blast-radius review gate is satisfied.
**Goal test**: `14_container_images.md` lists an actual pinned tag against every inventory row, `13_secrets_management.md`'s BR-SEC-022/023 read as shipped rather than target, and `phases.md`'s Phase 7.5 Outcome column is filled with two recorded independent security review passes.
**Repos**: [specs]

> **What makes the second review pass independent** (decided 2026-08-09). The Phase 7 G8 failure is the specification: both passes ran against the same commit range, so `92a4da2` fell through a gap neither reviewer knew existed, and differing `Reviewer:` lines would not have caught it. Independence here means three things, all asserted rather than asserted-to:
> 1. **Different starting point, not just a different reviewer.** Pass A reviews the **diff** over the phase commit range. Pass B reviews the **end state** against BR-INFRA-001…007 and BR-SEC-011/022/023 **without reading the diff** — that is the pass that catches "internally consistent, wrong overall".
> 2. **Fresh session, no shared context** for pass B. It must not inherit this plan's reasoning about why each change is correct.
> 3. **Each pass declares the exact commit range it covered, per repo**, and T7.6 asserts the union of the two equals the phase range. This is the falsifiable part and the one that directly fixes the recorded failure.

##### T7.1 [specs] — Record the delivered image inventory
- **Build**: Update `target/requirements/14_container_images.md`: replace each "Suggested version" with the tag actually shipped and running on staging, mark the migration complete, record the Minimus workflow revision used (from T1.1), and note the DISCOVER re-check date against the BR-INFRA-006 no-match components. Record the BR-INFRA-005 `dpage/pgadmin4:latest` exclusion. Also record that the Node 24-LTS-vs-26 open call resolved to 26.
- **Done when**: no inventory row still shows only a suggested version with no delivered tag.
- **Test**: `! grep -q 'Suggested version' target/requirements/14_container_images.md` exits 0.
- **Depends on**: T4.11 [deploy].

##### T7.2 [specs] — Report CVE reduction per component from published counts
- **Build**: For each migrated component, record the before/after CVE count from that image's `images.minimus.io` page (Minimus workflow step 8, ANALYZE) with the page URL as the source. Do not assert reductions without a citation — the spec's definition of done requires the counts be sourced.
- **Done when**: every migrated component has a before/after count with a source URL.
- **Test**: `[ "$(grep -c 'images.minimus.io' target/requirements/14_container_images.md)" -ge 19 ]` exits 0 — one citation per migrated inventory row (19 rows, less the three BR-INFRA-006 no-match components, plus the five monitoring images G3 adds).
- **Depends on**: T7.1 [specs].

##### T7.3 [specs] — Mark BR-SEC-022 and BR-SEC-023 shipped
- **Build**: In `target/requirements/13_secrets_management.md`, mark BR-SEC-022 and BR-SEC-023 as shipped with dates. BR-SEC-022 covers the manifest-version assertion, so T6.5.4 must have landed before this claim is true.
- **Done when**: both BR-SEC-022 and BR-SEC-023 carry a shipped status and a date.
- **Test**: `[ "$(grep -cE '^\|? *BR-SEC-02[23].*[Ss]hipped' target/requirements/13_secrets_management.md)" = 2 ]` exits 0.
- **Depends on**: T6.6.3 [deploy], T6.5.4 [deploy].

##### T7.4 [specs] — Record the committed paths and KV keys in the layout section
- **Build**: Add the seven committed deploy-config paths and the **eight** `secret/haisir/infra` topology keys to the KV layout section of `target/requirements/13_secrets_management.md`, enumerated by exact name in both cases. (Nine at plan time; `KC_HOSTNAME_ADMIN` was reverted by T6.2.0 and must not be listed.) Record that `KEYCLOAK_ADMIN_ALLOWED_CIDR` is **absent from KV entirely** on staging and prod (T6.2.0a) — not "set to a safe value". `127.0.0.1/32` is `template-configs.sh`'s fallback when the key is missing, not a value the variable holds. Do not write that the variable "holds" anything on those envs; dev is the only place it exists.
- **Done when**: the KV layout section lists all seven paths and all eight key names.
- **Test**: `[ "$(grep -cE 'KEYCLOAK_ADMIN_PORT_BINDING|BACKEND_DB_PORT_BINDING|TAILSCALE_ADMIN_CIDR|KEYCLOAK_ADMIN_ALLOWED_CIDR|APISIX_ADMIN_ALLOWED_CIDR|EXTRACTION__OLLAMA_BASE_URL|EMBEDDING__OLLAMA_BASE_URL|HAITU__RERANK_BASE_URL' target/requirements/13_secrets_management.md)" -ge 8 ]` exits 0 && `! grep -q KC_HOSTNAME_ADMIN target/requirements/13_secrets_management.md`.
- **Depends on**: T7.3 [specs].

##### T7.5 [specs] — Retire the render-hook follow-up item
- **Build**: Remove the "template-configs.sh does not source render-secrets-hook.sh — it must" item from the Out of scope / follow-up section of `target/requirements/13_secrets_management.md`, now that T6.1.1 landed.
- **Done when**: the follow-up section no longer lists the render-hook prerequisite as outstanding.
- **Test**: `! grep -q 'does not source .render-secrets-hook' target/requirements/13_secrets_management.md` exits 0.
- **Depends on**: T6.1.1 [deploy], T7.3 [specs].

##### T7.6 [specs] — Two independent security review passes
- **Build**: Run the two-independent-pass gate over the full Phase 7.5 commit range across all three code repos, per the independence procedure above: **Pass A reviews the diff; Pass B reviews the end state against BR-INFRA-001…007 and BR-SEC-011/022/023 from a fresh session without reading the diff.** Write each to `security/SECURITY_REVIEW_<date>_PHASE7.5_<reviewer>.md`, each carrying a `Reviewer:` line, a `Basis:` line (`diff` or `end-state`) and a `Covered:` line naming the exact per-repo commit range it read. The blast radius is every service in the stack including the database and the identity provider, plus a change that moves admin exposure and a change that commits config files to git. Every code-side task that could introduce a finding must be an ancestor of this task, or it reviews a tree that does not match what ships.
- **Done when**: the union of the two passes' declared `Covered:` ranges equals the full phase commit range in all three repos, with no gap.
- **Test**: `[ "$(grep -h '^Basis:' security/SECURITY_REVIEW_*PHASE7.5*.md | sort -u | wc -l)" = 2 ]` exits 0 — two passes on different bases, which is what `92a4da2` slipping past two same-range passes proved is the property that matters.
- **Depends on**: T7.2 [specs], T7.4 [specs], T7.5 [specs], T3.6 [deploy], T5.3 [deploy], T5.4 [deploy], T5.6 [deploy], T5.7 [deploy], T5.8 [deploy], T5.9 [specs], T5.11 [backend], T5.12 [deploy], T5.13 [deploy], T6.5.4 [deploy].

##### T7.7 [specs] — Fill the Phase 7.5 Outcome column
- **Build**: Fill the Phase 7.5 Outcome column in `Implementation_planning/phases.md` with the delivered state and the two review verdicts from T7.6.
- **Done when**: the Phase 7.5 row's Outcome cell is non-empty.
- **Test**: `grep -A2 'Phase 7.5' Implementation_planning/phases.md | grep -q 'Outcome.*[A-Za-z]'` exits 0.
- **Depends on**: T7.6 [specs].

##### T7.8 [specs] — Record the phase close-out decisions
- **Build**: Add a `decisions.md` close-out entry covering the four encoded calls: Node 26, the Keycloak admin exposure model (**deny-all + on-demand grant** — including the tailnet model that was tried and reversed, per the 2026-08-13 entry), the deny-by-default `ip-restriction` mechanism, and the rootlesskit/`--port-driver` pin.
- **Done when**: `decisions.md` has a Phase 7.5 close-out entry naming all four decisions.
- **Test**: `grep -A20 'Phase 7.5 close-out' Implementation_planning/decisions.md | grep -qE 'port-driver'` exits 0.
- **Depends on**: T7.6 [specs].

##### T7.9 [specs] — Clear the closed backlog items
- **Build**: Move B1, B3, B4, B5 and B6 out of the Backlog section of `Implementation_planning/phases.md`, leaving B2 (fixed in both environments 2026-08-07, not deploy-blocking) in place.
- **Done when**: `phases.md`'s Backlog section contains only B2.
- **Test**: `[ "$(grep -c '^### B' Implementation_planning/phases.md)" = 1 ]` exits 0.
- **Depends on**: T7.6 [specs].

##### T7.10 [specs] — Add the new load-bearing constraints
- **Build**: Add to `Implementation_planning/constraints.md` whatever this phase made load-bearing: the seven committed config paths, the `reg.mini.dev` pin requirement, **the Keycloak admin deny-all + on-demand-grant model (`keycloak-admin-access.sh`; no standing CIDR in the deployment, and `KC_HOSTNAME_ADMIN` must not be reintroduced)**, and the rootlesskit/`--port-driver` pin.
- **Done when**: `constraints.md` records all four as constraints.
- **Test**: `[ "$(grep -cE 'reg\.mini\.dev|keycloak-admin-access|port-driver|\.env\.config\.common\.sh' Implementation_planning/constraints.md)" -ge 4 ]` exits 0.
- **Depends on**: T7.6 [specs].

##### T7.11 [specs] — Re-snapshot `current/`
- **Build**: Re-run the current-state capture so `current/` reflects the delivered schema, API and infrastructure after this phase.
- **Done when**: every file under `current/` carries a capture date on or after the Phase 7.5 close-out date.
- **Test**: `[ -z "$(find current/ -name '*.md' -not -newermt '<close-out-date>')" ]` exits 0.
- **Depends on**: T7.9 [specs].

---

## Critical path

```
T6.1.1 → T6.1.2 ──────────────────────────────────────────────────────┐
   └→ T6.1.3 → T6.1.4 → T6.1.5 → T6.1.6 → T6.1.7 → T6.1.8 → T6.1.9 ───┤
        │                                                  └→ T6.3.1 ─┤
        └→ T6.2.0 → T6.2.0a ─┬→ T6.2.3 → T6.2.4 →─┬→ T6.2.5 ⋮ T6.2.6 → T6.2.7
           (revert)  (KV del) ├→ T6.2.0b (grant) ──┤  (staging) ⋮  🚫 PROD-GATED
                              └→ T6.2.0c (preserve)┘            ⋮  (deferred — owner
           T6.2.1/.1a/.1b/.2 SUPERSEDED — tailnet withdrawn     ⋮   call 2026-08-13)  │
                                                                      ▼
                                     ONE COMMIT: T6.3.2 (.gitignore + REMOTE_* strip
                                                 + gitleaks + rsync excludes + prepare_remote)
                                                          │
                        ┌─────────────────┬───────────────┼──────────────┐
                        ▼                 ▼               ▼              ▼
                     T6.3.3            T6.3.4 ─┐       T6.4.1         T6.6.2
                                          │    └───────→ T6.4.2 → T6.4.3
                                       T6.3.5                        │
                                                    ┌────────────────┴────────┐
                                                    ▼                         ▼
                                              T6.5.1→2→3→4              T6.6.1→2→3

T1.1 → G1 (T1.2→T1.3, T1.4→T1.5 → T1.6 → T1.7)  ─┐
T1.1 → G2 (T2.1→T2.2/T2.3→T2.4, T2.5→T2.9, T2.6, T2.7 → T2.8) ─┤
T1.1 → G3 (T3.1→T3.2→T3.3, T3.1→T3.4, T3.2→T3.5, T3.4+T3.5→T3.6) ─┼→ T4.10 → T4.11 → T7.1 → T7.2 ─┐
T1.1 → G4 (T4.1…T4.9)                            ─┘                               │
                                                                                  ▼
T5.1, T5.2 → T5.3 → T5.12 ──────────────────────────────────────────────────→  T7.6 → T7.7/T7.8/T7.9/T7.10
T5.5 → T5.6 → T5.7 ─────────────────────────────────────────────────────────→   ▲        T7.9 → T7.11
T5.4, T5.8, T5.9, T5.10→T5.11 ──────────────────────────────────────────────→   │
T6.6.3, T6.5.4 → T7.3 → T7.4 / T7.5 ────────────────────────────────────────→   ┘
```

Fully independent of G6: all of G1–G4. Fully independent of G1–G4: all of G6, and every G5 task except through T7.6.

**Ready now** (no pending dependencies):
- **T1.1** [specs] — pull the current Minimus workflow. Unblocks all of G1–G4.
- **T6.1.1** [deploy] — `template-configs.sh` sources `render-secrets-hook.sh`. Unblocks all of G6; safe alone (the hook is a no-op when the OpenBao flag is off).
- **T5.1** [backend], **T5.2** [backend] — the two one-line poller rollbacks.
- **T5.4** [deploy] — stop swallowing stderr in `bao_deploy_token()`.
- **T5.5** [deploy] — add the `other/cert/` rsync with `--chmod=F755`. No longer gated behind G6; it is a live prod cert-expiry fix.
- **T5.8** [deploy] — pin rootlesskit / `--port-driver`.
- **T5.9** [specs] — record the `92a4da2` review verdict.
- **T5.10** [backend] — declare `question_id` on `ExamReviewChatRequest`.

---

## Ground-truth notes for whoever implements

- `deploy.sh` and `deploy-lib.sh` live at `common/scripts/`, not the repo root. Every `[deploy]` path in G6 is `common/scripts/deploy.sh` / `common/scripts/deploy-lib.sh`.
- ⟲ **2026-08-13**: `KC_HOSTNAME_ADMIN` is gone — reverted by T6.2.0, and the topology key count is **eight**, not nine. The note below is retained as the record of what was true when the plan was written.
- Verified at `844e8f9`: `KC_HOSTNAME_ADMIN` appears in **none** of the seven in-scope paths — it is net-new, not a migration. The other eight keys are all present (`KEYCLOAK_ADMIN_PORT_BINDING` in four files, `BACKEND_DB_PORT_BINDING` and the three `*_BASE_URL` keys in `{staging,prod}/.env`, the three `*_CIDR` keys in `{staging,prod}/.env.config.sh` **and** `common/.env.config.common.sh`).
- Verified at `844e8f9`: `gateway-docker/Dockerfile:157` is `FROM apache/apisix@${APISIX_DIGEST}`, not `apache/apisix:3.17.0-ubuntu`; the digest ARG is at `:54` and `gateway-docker/Jenkinsfile:104`/`:109` read and pull by it.
- Verified at `844e8f9`: app DB credentials are dynamic OpenBao leases from `common/openbao/bootstrap.sh:265`; there is no app-DB init SQL and no static `haisir_worker` role.
- Verified at `844e8f9`: `deploy.sh`'s tag reconciliation runs `:394-485`; a **second** block at `:488-520` reads the same six override vars; `:266-268` reads three more outside the display block; `deploy.sh:6` is `set -euo pipefail`.
- Verified at `844e8f9`: `other/cert/haisir-sync-certs.sh` is mode `100644` in the index.
- Verified at `844e8f9`: `dev/docker-compose.yml:26` is `dpage/pgadmin4:latest` (BR-INFRA-005, dev-only).

- Verified at `844e8f9`: `common/.env.config.common.sh:39`/`:44`/`:48` export all three admin CIDRs with `${VAR:-127.0.0.1/32}` defaults, and `deploy.sh:591` sources that file before `template-configs.sh` runs. This is why T6.1.6 exists and why T6.1.8 is a separate negative control.
- Verified at `844e8f9`: the plaintext scan is `common/scripts/tests/full-plaintext-elimination-scan.sh`, **not** under `common/openbao/`.
- Verified at `844e8f9`: `gateway-docker/Jenkinsfile:103` greps `GO_BUILDER_DIGEST`, `:104` greps `APISIX_DIGEST`, and the `'pull apisix'` branch is `:107`.
- Verified at `844e8f9`: `common/openbao/deploy-required-keys.txt` supports the `path:KEY:envs=` form and `manifest.sh:25-32` parses it — T6.1.5's nine lines follow an existing convention, not a new one.
- Verified at `844e8f9`: `common/prometheus/prometheus.yml`, `common/grafana/config/grafana.ini` and `common/grafana/provisioning/{dashboards,datasources}` exist, with exactly one dashboard (`json/apisix-overview.json`). **No alert rules exist anywhere in the repo** — T3.4 is net-new.

### Critical Files for Implementation
- /home/gulzar/Workspace/haisir-deploy/common/scripts/deploy.sh
- /home/gulzar/Workspace/haisir-deploy/common/scripts/deploy-lib.sh
- /home/gulzar/Workspace/haisir-deploy/common/scripts/template-configs.sh
- /home/gulzar/Workspace/haisir-deploy/common/.env.config.common.sh
- /home/gulzar/Workspace/haisir-deploy/common/docker-compose.yml

---

<!-- plan-baseline: backend:00c2c738ace3ab6e5d40317a4298cea5a94a91ab frontend:705833ddeecae3201ba464d9b3837250e87e2432 deploy:844e8f9df25cca5ffb4b7d3f2ee1ef64a1d02e05 -->
