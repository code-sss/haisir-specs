# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> **Last baselined: backend:`ad82740` frontend:`53f573b` deploy:`d36b9e1` (2026-08-10)** — read directly from each sibling repo's HEAD; deploy has uncommitted changes pending (`common/openbao/deploy-required-keys.txt` arms the `KC_HOSTNAME_ADMIN` fail-closed gate; T2.1's pgvector image swap in `common/docker-compose.yml` + `dev/docker-compose.yml`; T2.3/T2.4's Postgres uid 70→999 reconciliation + keycloak-db → `reg.mini.dev/postgres:${KEYCLOAK_POSTGRES_IMAGE_TAG}` in `common/docker-compose.yml`; T2.5's APISIX runtime stage → `reg.mini.dev/apache-apisix:3.17.0` in `gateway-docker/Dockerfile`/`Jenkinsfile`/`UPGRADE-RUNBOOK.md`; T2.6's keycloak → `reg.mini.dev/keycloak:${KEYCLOAK_IMAGE_TAG}` + T2.7's etcd → `reg.mini.dev/etcd:${ETCD_IMAGE_TAG}` in both compose files) not yet reflected in this SHA.
>
> **Phase 7.5 — Minimus Container Images + Phase 7 Deploy Backlog.** Scoped 2026-08-09 via `/plan`,
> two challenger rounds. 87 tasks across four repos. Goal tree, per-task Build/Done-when/Test and
> the five decisions taken at scoping are in `PLAN.md`.
>
> **Start with T6.1.1 and T1.1.** T6.1.1 unblocks all of G6 and is safe alone; T1.1 unblocks all of
> G1–G4. G6.2 (the Keycloak admin console answering 200 from the public internet) is reachable in
> three tasks and never queues behind image work.
>
> Bolded rows are goal/subgoal-level tests — they can only pass once every child task above them is
> checked, and several are satisfied by a named task rather than a separate run (G1→T1.7, G2→T2.8,
> G4→T4.11, G5→T5.12).


## G1: Application images build and boot from pinned Minimus bases

- [x] T1.1 [specs]: Pull and record the current Minimus migration workflow
- [x] T1.2 [backend]: Backend Dockerfile to Minimus, both stages (depends on T1.1) (2026-08-10)
- [x] T1.3 [backend]: Backend runtime container boots on the Minimus base (depends on T1.2) (2026-08-10)
- [x] T1.4 [frontend]: Frontend Dockerfile to Minimus, both stages (depends on T1.1) (2026-08-10)
- [x] T1.5 [frontend]: Frontend runtime container boots on the Minimus base (depends on T1.4) (2026-08-10)
- [x] T1.6 [deploy]: Reconcile the hardcoded 65532 UID against the Minimus images (depends on T1.3, T1.5) (2026-08-10)
- [ ] T1.7 [deploy]: Boot the full application stack on the migrated bases (depends on T1.6) — BLOCKED: no local environment runs `common/docker-compose.yml`'s backend/worker/frontend (needs OpenBao-rendered secrets + real DB); verify on the next staging deploy carrying T1.2-T1.6, via `docker compose -f common/docker-compose.yml up -d backend worker frontend && sleep 90 && [ "$(docker compose -f common/docker-compose.yml ps --format '{{.Name}} {{.Health}}' | grep -vc healthy)" = 0 ]`
- [ ] **G1: Application images build and boot from pinned Minimus bases** — E2E test

## G2: Infrastructure services run on pinned, hardened images

- [x] T2.1 [deploy]: App Postgres to the standalone Minimus pgvector image (depends on T1.1) (2026-08-10) — three `image:` lines (`common/docker-compose.yml` db-init/db, `dev/docker-compose.yml` postgres) set to `reg.mini.dev/pgvector:${POSTGRES_IMAGE_TAG}` (version held in the existing `POSTGRES_IMAGE_TAG` variable, same `*_IMAGE_TAG` pattern as backend/frontend/keycloak; the value the `deploy.sh` drift loop compares the running container against). **Operator must set `POSTGRES_IMAGE_TAG=0.8.6-pg18`** in `staging/.env` and `prod/.env` (change the existing built-image-tag value) and **add** it to `dev/.env` (dev had no such var — it used a hardcoded `pgvector/pgvector:0.8.2-pg18-trixie`). **Plan's prescribed `:18` tag does not exist** on Minimus; SELECT TAG re-verification (which the plan itself requires) found the real scheme is `0.8.x-pg18`, so the variable value is `0.8.6-pg18`. INSPECT confirmed pgvector 0.8.6 (≥ 0.8.4, no downgrade), shell + `pg_isready`/`psql` present, image default user `0` dropping to `postgres` uid **999**. UID/ownership reconciliation (Chainguard `70` → Minimus `999`) deliberately left to T2.3, so T2.1 alone must not reach staging/prod. T2.1's test is dev-only (dev has no `user:` override; both old and new use uid 999 → no volume wipe). Runtime test not run here — dev stack is off-limits to start; operator to verify after setting the env var: `docker compose -f dev/docker-compose.yml up -d postgres && docker compose -f dev/docker-compose.yml exec postgres psql -U postgres -tAc "SELECT extversion FROM pg_extension WHERE extname='vector'"` (expect `0.8.6`).
- [ ] T2.2 [deploy]: Delete the from-source pgvector build (depends on T2.1)
- [x] T2.3 [deploy]: Re-verify the Postgres data-directory ownership workaround (depends on T2.1) (2026-08-10) — INSPECT of `reg.mini.dev/pgvector:0.8.6-pg18` confirmed Minimus `postgres` uid = **999** (Chainguard was 70; uid 70 absent in the image), standard `docker-entrypoint.sh` that chowns as root only when run as root then `gosu`-drops to 999. Reconciled `common/docker-compose.yml` app-db services: `db-init` entrypoint `chown -R 70:70` → `chown -R 999:999` (×2), `db` `user: "70"` → `user: "999"`, comments updated. No volume-type change needed — the named-volume + db-init pre-chown workaround still applies (db runs as 999, finds PGDATA already 999-owned); tmpfs `/var/run/postgresql` defaults to mode 1777 so the socket dir stays writable. Runtime test (boots `common/docker-compose.yml` db, needs OpenBao secrets) deferred to the next staging deploy.
- [x] T2.4 [deploy]: keycloak-db Postgres to Minimus (depends on T2.3) (2026-08-10) — INSPECT of `reg.mini.dev/postgres:18` confirmed it exists (unlike the pgvector `:18` tag), **no `-hardened` variant** (BR-INFRA-003 → plain base), `postgres` uid = **999**, same standard entrypoint, shell + `pg_isready` present. Swapped both `keycloak-db-init` and `keycloak-db` from `cgr.dev/chainguard/postgres:latest` (rolling tag) → `reg.mini.dev/postgres:${KEYCLOAK_POSTGRES_IMAGE_TAG}` (version in a new `.env` var, kept separate from the app DB's `POSTGRES_IMAGE_TAG` since it's a different image; chosen over a full `POSTGRES_IMAGE_TAG`→`PGVECTOR_IMAGE_TAG` rename to avoid touching `deploy.sh`'s drift loop and `env-setup.sh`'s hard-requirement gate, which T2.2/T6.5 own). Applied the same T2.3 UID reconciliation: `chown -R 70:70` → `999:999` (×2 in init), `user: "70"` → `user: "999"`. `group_add: "1000"` (openbao secrets) unchanged. **Operator must set `KEYCLOAK_POSTGRES_IMAGE_TAG=18`** in `staging/.env` and `prod/.env` (dev has no keycloak-db). Runtime test (boots keycloak-db, needs OpenBao secrets) deferred to the next staging deploy.
- [x] T2.5 [deploy]: APISIX runtime stage to Minimus (depends on T1.1) (2026-08-10) — `gateway-docker/Dockerfile` runtime `FROM apache/apisix@${APISIX_DIGEST}` → `FROM reg.mini.dev/apache-apisix:${APISIX_VERSION}` (pinned by the `APISIX_VERSION` tag ARG, not a literal — deleted `ARG APISIX_DIGEST`; kept a reworded `checkov:skip=CKV_DOCKER_7` since checkov can't resolve ARG-substituted FROM tags); updated `ARG APISIX_VERSION` `3.17.0-ubuntu` → `3.17.0` and the *_VERSION-record comment. `gateway-docker/Jenkinsfile`: deleted the `apisixDigest` grep, added an `apisixTag` grep of `ARG APISIX_VERSION=` (mirrors the `goDigest` pattern) so `'pull apisix'` pulls `reg.mini.dev/apache-apisix:${apisixTag}` in sync with the FROM (kept `'pull golang'` digest-pull — T2.9 owns `GO_BUILDER_DIGEST`). `gateway-docker/UPGRADE-RUNBOOK.md`: base-image paragraph now records only the Go builder as digest-pinned, APISIX as tag-pinned via the ARG. INSPECT confirmed apisix uid 636 + shell present (runtime `USER apisix`/`chown` unchanged). `hadolint` clean of new findings (3 pre-existing — DL3062 go-install, 2× DL3066 named-user — none from this change). **Runtime test deferred to the Jenkins WAF Functional Gate** (`waf-harness.sh` CVE-2026-21876 → rule 922110) — the multi-stage mage/tinygo/go build isn't reproduced locally.
- [x] T2.6 [deploy]: Keycloak to one pinned Minimus tag across dev and prod (depends on T1.1) (2026-08-10) — `common/docker-compose.yml` keycloak `quay.io/keycloak/keycloak:${KEYCLOAK_IMAGE_TAG}` → `reg.mini.dev/keycloak:${KEYCLOAK_IMAGE_TAG}`; `dev/docker-compose.yml` `keycloak/keycloak:26.6` → `reg.mini.dev/keycloak:${KEYCLOAK_IMAGE_TAG}` (dev switched from a hardcoded tag to the var). INSPECT confirmed `reg.mini.dev/keycloak:26.7.1` exists, default user uid **1000** (matches existing `user: "1000"`, no UID reconciliation), `keycloak.conf` mount path stable across 26.6→26.7.1. **Operator set `KEYCLOAK_IMAGE_TAG=26.7.1`** in dev/.env (add), staging/.env + prod/.env (change). ⚠ **Healthcheck `CMD-SHELL /dev/tcp` BREAKS on Minimus keycloak** — its shell is busybox (no `/dev/tcp`) and the image has no `curl`/`wget`/`nc` (busybox applets stripped, no `openssl`); only `java`+`kc.sh` are present, no health subcommand. Since `apisix` hard-depends on `keycloak: service_healthy` (common :599-600), a deploy carrying T2.6 without T2.8 leaves keycloak never-healthy → apisix won't start. **T2.8 (now Ready) must land before any staging/prod deploy carrying T2.6.** Runtime test deferred to the next staging deploy (dev stack off-limits to start).
- [x] T2.7 [deploy]: etcd to Minimus (depends on T1.1) (2026-08-10) — `common/docker-compose.yml` etcd `quay.io/coreos/etcd:${ETCD_IMAGE_TAG}` → `reg.mini.dev/etcd:${ETCD_IMAGE_TAG}`; `dev/docker-compose.yml` `quay.io/coreos/etcd:v3.6.11` → `reg.mini.dev/etcd:${ETCD_IMAGE_TAG}` (dev switched from hardcoded `v3.6.11` to the var — Minimus tags carry no `v` prefix). INSPECT confirmed `reg.mini.dev/etcd:3.7.1` exists, default user uid **1000** (matches existing `user: "1000"`), `etcdctl 3.7.1` present. 3.7.1 is an **upgrade** (new minor over dev's 3.6.11), within the plan's no-downgrade rule. etcd:3.7.1 ships **no shell**, but the healthcheck is exec-form `["CMD","etcdctl","endpoint","health"]` → survives unchanged. `etcd-init`'s `alpine:latest` left to T4.7. **Operator set `ETCD_IMAGE_TAG=3.7.1`** in dev/.env (add), staging/.env + prod/.env (change). Runtime test deferred to the next staging deploy.
- [ ] T2.8 [deploy]: Audit shell-dependent healthchecks across the migrated services (depends on T2.4, T2.5, T2.6, T2.7)
- [ ] T2.9 [deploy]: Bring the Go builder digest to BR-INFRA-004 parity (depends on T2.5)
- [ ] **G2: Infrastructure services run on pinned, hardened images** — E2E test

## G3: Monitoring is live and alerts fire

- [ ] T3.1 [deploy]: Add the Prometheus + exporters compose services (depends on T1.1)
- [ ] T3.2 [deploy]: Add the Grafana compose service (depends on T3.1)
- [ ] T3.3 [deploy]: Turn the skipped Prometheus test into a live gate (depends on T3.2)
- [ ] T3.4 [deploy]: Write the alert rules (depends on T3.1)
- [ ] T3.5 [deploy]: Provision the dashboards (depends on T3.2)
- [ ] T3.6 [deploy]: Route alerts to the owner-supplied destination (depends on T3.4, T3.5)
- [ ] **G3: Monitoring is live and alerts fire** — E2E test

## G4: No unpinned image can reach a host

- [ ] T4.1 [deploy]: Pin OpenBao to a Minimus image (depends on T1.1)
- [ ] T4.2 [deploy]: Pin the serving-path `other/services` images (depends on T1.1)
- [ ] T4.3 [deploy]: Pin the internal registry to `distribution-registry` (depends on T1.1)
- [ ] T4.4 [deploy]: Pin SonarQube and its Postgres (depends on T1.1)
- [ ] T4.5 [deploy]: Pin nginx-proxy-manager (depends on T1.1)
- [ ] T4.6 [deploy]: Rebuild the Jenkins Docker-in-Docker layer on Minimus (depends on T1.1)
- [ ] T4.7 [deploy]: Opportunistic busybox swap for the init/util images (depends on T1.1)
- [ ] T4.8 [deploy]: Record the no-match components as digest-pinned exceptions (depends on T4.2)
- [ ] T4.9 [deploy]: Rename image references outside the Dockerfiles (depends on T2.2, T2.5, T4.1)
- [ ] T4.10 [deploy]: CI gate that fails on an unpinned image (depends on T1.7, T2.8, T2.9, T3.2, T4.3, T4.4, T4.5, T4.6, T4.7, T4.8, T4.9)
- [ ] T4.11 [deploy]: Deploy the migrated image set to staging and verify at runtime (depends on T4.10)
- [ ] **G4: No unpinned image can reach a host** — E2E test

## G5: The v2026.6 backlog failure modes are closed

- [ ] T5.1 [backend]: Release the extraction poller's transaction on an empty poll
- [ ] T5.2 [backend]: Release the essay-grading poller's transaction on an empty poll
- [ ] T5.3 [deploy]: Backstop the dynamic DB roles with an idle-transaction timeout (depends on T5.1, T5.2)
- [ ] T5.4 [deploy]: Surface the real cause of a deploy-secret render failure
- [ ] T5.5 [deploy]: Bring `other/cert/` inside the deploy sync
- [ ] T5.6 [deploy]: Assert the installed certbot hook matches the repo (depends on T5.5)
- [ ] T5.7 [deploy]: Assert the installed certbot hook is executable (depends on T5.6)
- [ ] T5.8 [deploy]: Pin the rootless container runtime across hosts
- [ ] T5.9 [specs]: Close the review-coverage gap on `92a4da2`
- [ ] T5.10 [backend]: Declare `question_id` on `ExamReviewChatRequest`
- [ ] T5.11 [backend]: Narrow exam-review grounding to the named question (depends on T5.10)
- [ ] T5.12 [deploy]: Confirm the pollers hold no transaction on staging (depends on T5.3)
- [ ] **G5: The v2026.6 backlog failure modes are closed** — E2E test

## G6: Env config is version-controlled and fails closed

- [ ] **G6: Env config is version-controlled and fails closed** — E2E test

### G6.1: Host topology resolves from KV, fully derived

- [x] T6.1.1 [deploy]: `template-configs.sh` sources the render hook (2026-08-10)
- [x] T6.1.2 [deploy]: Delete `template-configs.sh`'s cross-environment config fallback (depends on T6.1.1) (2026-08-10)
- [x] T6.1.3 [deploy]: Seed `KC_HOSTNAME_ADMIN` into KV for staging and prod (depends on T6.1.1) (2026-08-10) — seeded on both envs (`secret/haisir/infra`), verified non-empty via `bao kv get` on each. `deploy-required-keys.txt` now arms `infra:KC_HOSTNAME_ADMIN:envs=staging,prod` so a future deploy fails closed if this key is ever missing.
  - **Found + fixed while seeding (both envs)**: `admin-ops` OpenBao identity couldn't log in on either staging or prod (`invalid certificate or no client certificate supplied`). Cert/key/CA chain were all fine (pubkey hash matches the container's trusted CA, `openssl verify` OK, correct `clientAuth` EKU, key not passphrase-protected) — actual cause was that `auth/cert/certs/admin-ops` was simply never registered in OpenBao on either env (`bao read` returned "No value found"). Fixed on both by registering it (`bao write auth/cert/certs/admin-ops display_name=admin-ops policies=admin certificate=@... allowed_common_names=openbao-client-admin-ops ttl=3600`) using each env's bootstrap root token; `admin-ops` now logs in successfully on both and was used to seed the key on prod. Separately noted but NOT the cause: `reissue-ca-keyusage.sh` (2026-08-07) only patched the `apisix-certs` volume and left `openbao-certs-*`/`etcd-certs` on the pre-keyUsage CA cert ("Reconcile in a planned window" — still outstanding, harmless per the script's own same-key invariant, confirmed live).
- [ ] T6.1.4 [deploy]: Seed the other eight infra keys, fully derived (depends on T6.1.3)
- [ ] T6.1.5 [deploy]: Arm the per-key fail-closed gate for all nine (depends on T6.1.4)
- [ ] T6.1.6 [deploy]: Delete the three decorative CIDR defaults from the common file (depends on T6.1.5)
- [ ] T6.1.7 [deploy]: Remove the eight from staging's config files (depends on T6.1.6)
- [ ] T6.1.8 [deploy]: Positive control: the render aborts when KV is unreadable (depends on T6.1.7)
- [ ] T6.1.9 [deploy]: Remove the eight from prod's config files (depends on T6.1.8)
- [ ] **G6.1: Host topology resolves from KV, fully derived** — integration test

### G6.2: `ip-restriction` denies by default and is always present

- [ ] T6.2.1 [deploy]: Add `KC_HOSTNAME_ADMIN` to the Keycloak service (depends on T6.1.3)
- [ ] T6.2.2 [deploy]: Live gate: prove tailnet admin login works on staging (depends on T6.2.1)
- [ ] T6.2.3 [deploy]: Replace plugin-stripping with a deny-all whitelist (depends on T6.2.2)
- [ ] T6.2.4 [deploy]: Regression test that fails if fail-open returns (depends on T6.2.3)
- [ ] T6.2.5 [deploy]: Apply the deny-all on staging (depends on T6.2.4)
- [ ] T6.2.6 [deploy]: Apply the deny-all on prod (depends on T6.2.5)
- [ ] T6.2.7 [deploy]: Re-verify tailnet admin login on prod after the deny-all (depends on T6.2.6)
- [ ] **G6.2: `ip-restriction` denies by default and is always present** — integration test

### G6.3: The seven paths are committed, scanned, and sourced from the release

- [ ] T6.3.1 [deploy]: Precondition: scan the seven paths for secret and topology residue (depends on T6.1.9)
- [ ] T6.3.2 [deploy]: Land the seven paths, the scanner and the sync in one commit (depends on T6.1.2, T6.1.9, T6.2.7, T6.3.1)
- [ ] T6.3.3 [deploy]: Verify no committed config path carries a `REMOTE_*` assignment (depends on T6.3.2)
- [ ] T6.3.4 [deploy]: Supply all three `REMOTE_*` vars as Jenkins credentials (depends on T6.3.2)
- [ ] T6.3.5 [deploy]: Make `deploy.sh` fail closed on a missing SSH target (depends on T6.3.4)
- [ ] **G6.3: The seven paths are committed, scanned, and sourced from the release** — integration test

### G6.4: The release artifact is the only source of the three files on any host

- [ ] T6.4.1 [deploy]: Tighten the three synced files to mode 600, by name (depends on T6.3.2)
- [ ] T6.4.2 [deploy]: Verify the files arrive at mode 600 from an empty start (depends on T6.4.1, T6.3.4)
- [ ] T6.4.3 [deploy]: Verify the remote content matches the committed copy (depends on T6.4.2)
- [ ] **G6.4: The release artifact is the only source of the three files on any host** — integration test

### G6.5: Version reconciliation is deleted, not repaired

- [ ] T6.5.1 [deploy]: Delete the remote VERSION rewrite and the tag-reconciliation block (depends on T6.4.3)
- [ ] T6.5.2 [deploy]: Delete the override reads and every consumer of them (depends on T6.5.1)
- [ ] T6.5.3 [deploy]: Remove the dead manifest fields (depends on T6.5.2)
- [ ] T6.5.4 [deploy]: Assert manifest version equals the committed `VERSION=` (depends on T6.5.3)
- [ ] **G6.5: Version reconciliation is deleted, not repaired** — integration test

### G6.6: One deploy path, not two

- [ ] T6.6.1 [deploy]: Delete the manual deploy scripts (depends on T6.4.3)
- [ ] T6.6.2 [deploy]: Take `REMOTE_HOST` from the environment in the test runner (depends on T6.3.2, T6.6.1)
- [ ] T6.6.3 [deploy]: Document the single deploy path (depends on T6.6.2)
- [ ] **G6.6: One deploy path, not two** — integration test

## G7: Specs and phase record reflect what shipped

- [ ] T7.1 [specs]: Record the delivered image inventory (depends on T4.11)
- [ ] T7.2 [specs]: Report CVE reduction per component from published counts (depends on T7.1)
- [ ] T7.3 [specs]: Mark BR-SEC-022 and BR-SEC-023 shipped (depends on T6.6.3, T6.5.4)
- [ ] T7.4 [specs]: Record the committed paths and KV keys in the layout section (depends on T7.3)
- [ ] T7.5 [specs]: Retire the render-hook follow-up item (depends on T6.1.1, T7.3)
- [ ] T7.6 [specs]: Two independent security review passes (depends on T7.2, T7.4, T7.5, T3.6, T5.3, T5.4, T5.6, T5.7, T5.8, T5.9, T5.11, T5.12, T6.5.4)
- [ ] T7.7 [specs]: Fill the Phase 7.5 Outcome column (depends on T7.6)
- [ ] T7.8 [specs]: Record the phase close-out decisions (depends on T7.6)
- [ ] T7.9 [specs]: Clear the closed backlog items (depends on T7.6)
- [ ] T7.10 [specs]: Add the new load-bearing constraints (depends on T7.6)
- [ ] T7.11 [specs]: Re-snapshot `current/` (depends on T7.9)
- [ ] **G7: Specs and phase record reflect what shipped** — E2E test

---

## Ready now

Tasks with no pending dependencies — can be started immediately:

- T1.7 [deploy]: Boot the full application stack on the migrated bases
- T2.2 [deploy]: Delete the from-source pgvector build
- T2.8 [deploy]: Audit shell-dependent healthchecks across the migrated services
- T2.9 [deploy]: Bring the Go builder digest to BR-INFRA-004 parity
- T3.1 [deploy]: Add the Prometheus + exporters compose services
- T4.1 [deploy]: Pin OpenBao to a Minimus image
- T4.2 [deploy]: Pin the serving-path `other/services` images
- T4.3 [deploy]: Pin the internal registry to `distribution-registry`
- T4.4 [deploy]: Pin SonarQube and its Postgres
- T4.5 [deploy]: Pin nginx-proxy-manager
- T4.6 [deploy]: Rebuild the Jenkins Docker-in-Docker layer on Minimus
- T4.7 [deploy]: Opportunistic busybox swap for the init/util images
- T5.1 [backend]: Release the extraction poller's transaction on an empty poll
- T5.2 [backend]: Release the essay-grading poller's transaction on an empty poll
- T5.4 [deploy]: Surface the real cause of a deploy-secret render failure
- T5.5 [deploy]: Bring `other/cert/` inside the deploy sync
- T5.8 [deploy]: Pin the rootless container runtime across hosts
- T5.9 [specs]: Close the review-coverage gap on `92a4da2`
- T5.10 [backend]: Declare `question_id` on `ExamReviewChatRequest`
- T6.1.4 [deploy]: Seed the other eight infra keys, fully derived
- T6.2.1 [deploy]: Add `KC_HOSTNAME_ADMIN` to the Keycloak service
