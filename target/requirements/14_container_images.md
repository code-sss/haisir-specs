# Container Base Images (Minimus Migration)

> **Target state scope:** replace Chainguard (`cgr.dev/chainguard/*`) and assorted unhardened Docker Hub / quay.io / ghcr.io images with Minimus hardened images (`reg.mini.dev/*`) across every Dockerfile and compose service in `haisir-backend`, `haisir-frontend`, and `haisir-deploy`. Cross-cutting infrastructure hardening; not tied to a persona phase.
>
> **Status note (2026-08-14):** migration **complete and shipped to staging** (T4.11, 2026-08-13; 17/17 containers on `reg.mini.dev/*` or `registry.haisir.in/*`). The inventory table below records the tag actually delivered and running on staging for each component, not a suggestion. The Minimus migration workflow used (T1.1, pulled 2026-08-10 from `https://api.mini.dev/v1/skills/dockerfile`) carries no vendor-issued revision field — content fingerprint `sha256:728c7f196ec70fadc67fa8c083cef929d011fef1c07b51dfd4cd40404a5b6e3f` (see `decisions.md`, 2026-08-10). The Node 24-LTS-vs-26 open call resolved to **26**. The three BR-INFRA-006 no-match components were re-checked at DISCOVER time on **2026-08-10** (still no Minimus image) and pinned to a specific version + digest. CVE reduction per component (Minimus workflow step 8, ANALYZE) is recorded separately under T7.2.

---

## Problem

The stack currently mixes two base-image strategies, each with real gaps:

1. **Chainguard's free tier is `latest`-only for most images**, and a handful of images the stack needs aren't in the free tier at all. Concretely:
   - `haisir-backend/Dockerfile` runtime stage is pinned to `cgr.dev/chainguard/python:latest` — the builder stage uses `python:3.14-slim` (Docker Hub) specifically because Chainguard offers no pinned Python tag for free.
   - `haisir-frontend/Dockerfile` has the identical pattern and says so in a comment: *"Chainguard node:latest is intentional; no versioned tags available on free plan."*
   - `haisir-deploy/postgres-docker/Dockerfile` compiles pgvector 0.8.4 (against Postgres 18.4) from source in a Wolfi builder stage because **pgvector isn't in Chainguard's Postgres image at all**.
   - `haisir-deploy/gateway-docker/Dockerfile`'s runtime stage is `apache/apisix:3.17.0-ubuntu` (Docker Hub) — APISIX has never been on Chainguard's free tier.
   - Prometheus + Grafana monitoring was deferred outright (`decisions.md`, 2026-06-18) because `cgr.dev/chainguard/prometheus`/`grafana` require a paid plan.
2. **`:latest`-pinned runtime images break reproducibility** — `postgres-docker/Dockerfile`'s `POSTGRES_BASE_IMAGE` defaults to `cgr.dev/chainguard/postgres:latest`, a rolling tag with a `checkov:skip` comment acknowledging the risk.
3. Where Chainguard wasn't viable at all, the fallback was a **plain, unhardened Docker Hub image** for both builder and runtime (`apache/apisix`, `quay.io/keycloak/keycloak`, `keycloak/keycloak`, `quay.io/coreos/etcd`, `golang:1.23-bookworm`) — none of Chainguard's non-root/minimal-attack-surface properties apply there.

## Goal

Every container image in the stack — application runtime, build stages, and infrastructure services — pulls from **Minimus** (`reg.mini.dev`), free, with an explicit pinned version tag (never `:latest`), using Minimus's own dev/prod tag discipline (build tooling confined to the `-dev` variant, never shipped in the runtime image). This:

- Fixes the pinned-version gap for Python/Node/Go runtime images (BR-INFRA-002).
- Unblocks Prometheus + Grafana monitoring, previously stalled on Chainguard licensing.
- Eliminates the from-source pgvector compile — Minimus ships `pgvector` as a standalone, maintained Postgres+pgvector image.
- Extends hardening to APISIX, Keycloak, and etcd, which were plain Docker Hub/quay.io images before.

## Solution summary

Migrate every `FROM` line — in `haisir-backend/Dockerfile`, `haisir-frontend/Dockerfile`, and every Dockerfile/compose service in `haisir-deploy` — to its `reg.mini.dev/*` Minimus equivalent, following Minimus's own AI-agent migration workflow (DISCOVER → SELECT TAG → INSPECT → CHECK FOR SHELL → RESOLVE PACKAGES → WRITE → VERIFY → ANALYZE) at implementation time. That workflow is published and versioned at `https://api.mini.dev/v1/skills/dockerfile` (mirrored as the `minimus-dockerfile` skill) — whoever implements this phase should pull the current version fresh rather than relying on a stale copy, since Minimus revises it independently of this spec.

Three components have no Minimus equivalent as of this writing (2026-07-26) and stay on their current registries (BR-INFRA-006).

---

## Policy (business rules)

- **BR-INFRA-001 — Minimus default, both stages.** All new and migrated container infrastructure defaults to `reg.mini.dev` images, for build stages *and* runtime stages — not just the shipped image. Docker Hub / quay.io / ghcr.io is the fallback only when BR-INFRA-006 applies.
- **BR-INFRA-002 — Always pin to the current stable release; no `:latest`.** Every `FROM` line names an explicit version line (e.g. `18`, `3.17`, `26.7`) — never `:latest`, including in builder stages. hAIsir tracks upstream's current stable release and upgrades on a regular cadence; a pin is a starting point to keep current, not a set-and-forget value. (This reverses the Chainguard-era `postgres-docker/Dockerfile` default of `:latest` with a `checkov:skip` justifying it — that justification no longer applies once a pinned Minimus tag is available.)
- **BR-INFRA-003 — Variant tier selection.** Default to the plain Minimus base image; use the `-hardened` variant when the gallery lists one for that image (extra CIS/NIST-standard hardening on top of the base, no functional cost, still free). Do **not** use `-advanced` (Bitnami-compatibility layer — hAIsir doesn't consume Bitnami-style env conventions today) or `-fips` (FIPS 140-3 cryptographic-module validation — no regulatory driver for hAIsir today) unless a documented compliance requirement emerges later. Confirm which tier a given image actually offers at DISCOVER time (step 1 of the Minimus workflow) — don't assume `-hardened` exists just because the base image does.
- **BR-INFRA-004 — Builder/runtime language-version parity.** A language builder image's version (Go, Python, Node) MUST match the version the source targets (`go.mod`'s `go` directive, the Python ABI the compiled extensions were built against, Node's `engines` field). Bumping the Minimus builder tag without bumping the matching in-source version pin breaks the build — this is the same failure mode `haisir-backend/Dockerfile` already guards against with its "builder and runner Python minor version must match" comment; it now also applies to `gateway-docker/Dockerfile`'s `GO_VERSION` ARG, which the builder tag must track exactly.
- **BR-INFRA-005 — Dev-only tooling stays out of scope.** Images that exist purely for local developer convenience and never ship to staging/prod (`pgadmin4` today) are excluded from this migration — hardening them has no security payoff.
- **BR-INFRA-006 — No-match fallback.** A component with no Minimus image (verified via the DISCOVER step, not assumed) stays on its current registry, pinned to a specific version **and** digest rather than `:latest`. Re-check at each future touch of that component in case Minimus adds coverage.
- **BR-INFRA-007 — Opportunistic hardening for intermediate/deploy-only utility images.** `alpine:latest`-class images used only as init/wait-for/deployment scaffolding (not part of the served application) may move to a Minimus equivalent (e.g. `busybox`) where it's a clean fit, but this is not a hard requirement the way BR-INFRA-001 is for application and service images.

---

## Image inventory

Delivered version = the tag pinned in the shipped Dockerfile/compose and, for `*_IMAGE_TAG`-driven services, the value set in `other/env_templates/.env.template` and running on staging as of the 2026-08-12 v2026.7 deploy + the 2026-08-13 T4.11 runtime recreation (17/17 containers pinned). `*_IMAGE_TAG`-driven rows show the env-var value; the compose line is `reg.mini.dev/<image>:${<VAR>}`.

| Component | Current image(s) | Target Minimus image | Delivered version | Notes |
|---|---|---|---|---|
| Postgres + pgvector (app DB) | Custom Wolfi build: `cgr.dev/chainguard/wolfi-base:latest` (builder) → `cgr.dev/chainguard/postgres:latest` (rolling tag; built as Postgres 18.4 + pgvector 0.8.4 per the Dockerfile's `POSTGRES_VERSION`/`PGVECTOR_VERSION` ARGs, compiled from source) | `reg.mini.dev/pgvector` | `0.8.6-pg18` (`POSTGRES_IMAGE_TAG`) | Standalone image — **removes the custom multi-stage build entirely** (T2.2), including the `:latest` rolling-tag risk. pgvector 0.8.6 (≥ 0.8.4, no downgrade). The plan's prescribed `:18` tag does not exist on Minimus; SELECT TAG re-verification found the real scheme is `0.8.x-pg18`. Also replaces dev's `pgvector/pgvector:0.8.2-pg18-trixie` (Docker Hub, a separate older pin). UID reconciliation (Chainguard `70` → Minimus `999`) in T2.3. |
| Postgres (keycloak-db) | `cgr.dev/chainguard/postgres:latest` | `reg.mini.dev/postgres` | `18` (`KEYCLOAK_POSTGRES_IMAGE_TAG`) | No pgvector needed here — plain Postgres. No `-hardened` variant exists → plain base per BR-INFRA-003. UID 999 (T2.4). |
| Postgres (SonarQube DB, `other/services/sonarqube`) | `postgres:18-alpine` (Docker Hub) | `reg.mini.dev/postgres` | `18` | Same tag as keycloak-db (T4.4). |
| APISIX | `apache/apisix:3.17.0-ubuntu` (Docker Hub) | `reg.mini.dev/apache-apisix` | `3.17.0` (`APISIX_VERSION` ARG) | Was never on Chainguard's free tier. Tag-pinned via the ARG (moved off the old `@digest` pin in T2.5). Runtime healthcheck rewritten to exec form in T2.8. |
| Go (gateway builder stage) | `golang:1.23-bookworm` (Docker Hub) | `reg.mini.dev/go` (builder, `-dev` variant via digest) | `go1.25.12` — pinned by digest `sha256:8ebfe4ddacc2401022c8813d6fc6e66cc784c8deec28011d261f6d9e03ed2826` (`GO_BUILDER_DIGEST`); `GO_VERSION=1.25`, `go.mod` declares `go 1.25.0` | See BR-INFRA-004 — T2.9 verified parity holds: digest resolves to go1.25.12, `GO_VERSION` and `go.mod` all on the 1.25 line. No bump taken (the task forbids bumping the digest alone). |
| Keycloak | `quay.io/keycloak/keycloak:${KEYCLOAK_IMAGE_TAG}` (prod), `keycloak/keycloak:26.6` (dev, Docker Hub) | `reg.mini.dev/keycloak` | `26.7.1` (`KEYCLOAK_IMAGE_TAG`) | Runtime image is JRE-only (busybox shell, no `nc`/`curl`/`wget`/`/dev/tcp`); healthcheck rewritten to exec-form `/proc/net/tcp` grep in T2.8. Default uid 1000 (matches existing `user: "1000"`). |
| Python (backend) | Builder `python:3.14-slim` (Docker Hub) → runtime `cgr.dev/chainguard/python:latest` | `reg.mini.dev/python:3.14-dev` (builder) → `reg.mini.dev/python:3.14` (runtime) | `3.14` (both stages, T1.2) | Both stages now pin the same version — closes the Chainguard `latest`-only gap directly. |
| Node (frontend) | Builder `node:26-trixie-slim` (Docker Hub) → runtime `cgr.dev/chainguard/node:latest` | `reg.mini.dev/node:26-dev` (builder) → `reg.mini.dev/node:26` (runtime) | `26` (both stages, T1.4) | Same fix as Python. **The Node 24-LTS-vs-26 open call resolved to 26** (current line, matching the builder's pre-migration `node:26-trixie-slim`). |
| Prometheus + exporters | Deferred (blocked on Chainguard licensing) | `reg.mini.dev/prometheus`, `reg.mini.dev/prometheus-alertmanager`, `reg.mini.dev/prometheus-node-exporter`, `reg.mini.dev/prometheus-postgres-exporter`, `reg.mini.dev/nginx-prometheus-exporter` | `prometheus:3.13.2`, `prometheus-alertmanager:0.33.1`, `prometheus-node-exporter:1.12.1`, `prometheus-postgres-exporter:0.20.1`, `nginx-prometheus-exporter:1.5.1` (T3.1) | Unblocks the deferred monitoring stack decision (`decisions.md`, 2026-06-18). All five behind the `monitoring` profile (opt-in, not started by `deploy.sh`). Note the `prometheus-*` repo-name prefix the bare names lack. |
| Grafana | Deferred (`grafana/grafana-oss`, AGPL, was the fallback option) | `reg.mini.dev/grafana` | `13.1.3` (`GRAFANA_IMAGE_TAG`, T3.2) | Same — unblocks it, and avoids the AGPL fallback. Owner-chosen 13.1 over the initially-verified 13.0. |
| etcd | `quay.io/coreos/etcd:${ETCD_IMAGE_TAG}` / `v3.6.11` (dev) | `reg.mini.dev/etcd` | `3.7.1` (`ETCD_IMAGE_TAG`, T2.7) | Upgrade over dev's 3.6.11 (within the no-downgrade rule). Minimus tags carry no `v` prefix. Healthcheck already exec-form `etcdctl`. |
| OpenBao | `${OPENBAO_IMAGE:-ghcr.io/openbao/openbao:2.6.0}` | `reg.mini.dev/openbao` | `2.6.1` (`OPENBAO_IMAGE_TAG`, T4.1) | 2.6.1 satisfies the ≥2.6.0 floor for CVE-2025-54996 (BR-SEC-016). Deliberately NOT wired into `deploy.sh`'s drift loop (separate operator-run lifecycle). **T4.11 correction**: runs as uid 0 by default, which crash-loops under rootless Docker writing the seal key — pinned to `user: "100:1000"` in production. |
| nginx-proxy-manager | `jc21/nginx-proxy-manager:2.15.1` (Docker Hub) | `reg.mini.dev/nginx-proxy-manager` | `2.15.1` (T4.5) | Registry move only, version unchanged (already at an explicit tag). |
| Jenkins | `jenkins/jenkins:lts` + custom Docker-in-Docker layer | `reg.mini.dev/jenkins` (the `-dev` tag is the final image — a CI toolbox, not a served app) | `2.568.2-dev` (T4.6) | The Docker-CLI-in-Jenkins layer ran the `-dev` package-resolution workflow (Minimus step 5) at migration time. No separate `jenkins-agent` image exists — the compose builds one monolithic controller. |
| SonarQube | `sonarqube:community` (Docker Hub) | `reg.mini.dev/sonarqube` | `26.8.0.126808` (T4.4) | |
| Ollama | `ollama/ollama:latest` (×4 service defs) | `reg.mini.dev/ollama` | `0.32.7` (T4.2) | Single tag across all four service defs. |
| cloudflared | `cloudflare/cloudflared:latest` | `reg.mini.dev/cloudflared` | `2026.7.3` (T4.2) | |
| Generic init/util (`alpine:latest` / `busybox:stable`) | `alpine:latest` (multiple compose services: `common/docker-compose.yml`, `common/openbao/docker-compose.openbao.yml`); `busybox:stable` (`other/services/sonarqube/docker-compose.yml`) | `reg.mini.dev/busybox` | `1.38.0` (T4.7) | Opportunistic per BR-INFRA-007. The `busybox:stable` case is already the same tool, just an unhardened registry — this one's a pure registry swap with no image-family change. Replaced `etcd-init`, `openbao-init`, `sonarqube-init`. |
| Docker registry | `registry:3` (`other/services/registry/docker-compose.yml`) | `reg.mini.dev/distribution-registry` | `3.1.1` (T4.3) | Hosts hAIsir's own pushed images (`haisir-backend`, `haisir-frontend`, `haisir-gateway`) — same upstream `distribution/registry` project/API; `REGISTRY_AUTH*`/htpasswd config carried over. (`haisir-postgres` build was deleted in T2.2.) |

### No Minimus match — stay on current registry, digest-pinned (BR-INFRA-006)

Re-checked at DISCOVER time on **2026-08-10** (T4.8): still no Minimus image for any of the three. Each is now pinned to a specific version **and** digest (was `:latest` for dockhand). Re-check again at each future touch in case Minimus adds coverage.

| Component | Delivered image | Notes |
|---|---|---|
| CrowdSec | `crowdsecurity/crowdsec:v1.7.8@sha256:2f527c9bb8b367120eb08b82890aa912ce96bfa1ada93dda0721700e4b4e0dde` (`other/services/crowdsec/docker-compose.yml`) | No Minimus image at discovery time (2026-07-26) or re-check (2026-08-10). |
| HuggingFace text-embeddings-inference (reranker) | `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9@sha256:ad950d30878eceb72aaf32024d26fa2b1d04a75304fa0b4776b49aa1941fea07` (`other/services/embedding/docker-compose.yml`) | No Minimus image at discovery time or re-check. |
| dockhand | `fnsys/dockhand:v1.0.41@sha256:de6c7d4bb30d7563a94991f15915c58067ebad29acfbc365fe6ce0c5785b4386` (`other/services/dockhand/docker-compose.yml`) | No Minimus image at discovery time or re-check. Moved off the rolling `:latest` onto `v1.0.41` (verified live to currently resolve to the same digest as `latest`, so this is an accurate pin of what was running, not a downgrade). |

### Explicitly excluded (BR-INFRA-005)

`pgadmin4` (`dpage/pgadmin4:latest`, `dev/docker-compose.yml`, dev-only convenience tool) — out of scope. The compose line carries the trailing annotation `# BR-INFRA-005: dev-only, never ships`, which the T4.10 image-pin CI gate treats as a per-line escape hatch (the one documented exception).

### Explicitly excluded — archived/superseded configs

`haisir-deploy/archived/{dev,staging,prod}/docker-compose.yml` reference `cgr.dev/chainguard/postgres:latest`, `cgr.dev/chainguard/nginx:latest` (dev), and `owasp/modsecurity-crs` (staging/prod — the WAF predecessor to the current Coraza-in-APISIX gateway). These are kept for historical reference only, are not live configs, and are **not** in scope for this migration — do not spend implementation effort on them.

---

## CVE reduction per component (T7.2)

Before/after CVE counts per migrated Minimus image, sourced from each image's `images.minimus.io` risk-reduction page (Minimus workflow step 8, ANALYZE). Counts are unique CVEs; "Minimus" is the `reg.mini.dev/*` image, "Public" is the upstream image the page compares against. Pages prepared **2026-08-14** — re-pull before relying on these at a future touch, since Minimus rebuilds daily and counts drift. The three BR-INFRA-006 no-match components have no Minimus page and no row here (they are digest-pinned on their own registries, not migrated).

> **Caveat on the "before" column.** The "Public" image is whatever upstream the Minimus page chooses to compare against — in most cases the Docker Hub `:latest` of the same project. It is **not always the exact image hAIsir ran before the migration**: e.g. the keycloak-db and SonarQube DB rows previously ran Chainguard (`cgr.dev/chainguard/postgres:latest`), not Docker Hub `library/postgres:latest`; APISIX previously ran `apache/apisix:3.17.0-ubuntu`, not `:latest`. The count is the published reduction the Minimus page advertises for that image family, cited as published — not a measured delta of hAIsir's specific prior pin. Where the page's comparison image *does* match the prior pin (pgvector → `pgvector/pgvector:0.8.6-pg18`, distribution-registry → `registry:3.1.1`), the "before" is exact.

| Minimus image (delivered tag) | Minimus CVEs | Public CVEs | Reduction | Public image compared | Source |
|---|---|---|---|---|---|
| `reg.mini.dev/pgvector:0.8.6-pg18` | 0 | 154 | 100% | `pgvector/pgvector:0.8.6-pg18` | https://images.minimus.io/images/pgvector/risk-reduction |
| `reg.mini.dev/postgres:18` (keycloak-db + SonarQube DB) | 0 | 144 | 100% | `library/postgres:latest` | https://images.minimus.io/images/postgres/risk-reduction |
| `reg.mini.dev/apache-apisix:3.17.0` | 0 | 49 | 100% | `apache/apisix:latest` | https://images.minimus.io/images/apache-apisix/risk-reduction |
| `reg.mini.dev/go@sha256:8ebfe4dd…` (gateway builder, go1.25.12) | 1 | 218 | 99% | `library/golang:latest` | https://images.minimus.io/images/go/risk-reduction |
| `reg.mini.dev/keycloak:26.7.1` | 2 | 47 | 95% | `keycloak/keycloak:latest` | https://images.minimus.io/images/keycloak/risk-reduction |
| `reg.mini.dev/python:3.14` (backend, both stages) | 1 | 426 | 99% | `library/python:latest` | https://images.minimus.io/images/python/risk-reduction |
| `reg.mini.dev/node:26` (frontend, both stages) | 0 | 415 | 100% | `library/node:latest` | https://images.minimus.io/images/node/risk-reduction |
| `reg.mini.dev/prometheus:3.13.2` | 0 | 6 | 100% | `prom/prometheus:latest` | https://images.minimus.io/images/prometheus/risk-reduction |
| `reg.mini.dev/prometheus-alertmanager:0.33.1` | 0 | 25 | 100% | `prom/alertmanager:latest` | https://images.minimus.io/images/prometheus-alertmanager/risk-reduction |
| `reg.mini.dev/prometheus-node-exporter:1.12.1` | 0 | 4 | 100% | `prom/node-exporter:latest` | https://images.minimus.io/images/prometheus-node-exporter/risk-reduction |
| `reg.mini.dev/prometheus-postgres-exporter:0.20.1` | 0 | 8 | 100% | `prometheuscommunity/postgres-exporter:latest` | https://images.minimus.io/images/prometheus-postgres-exporter/risk-reduction |
| `reg.mini.dev/nginx-prometheus-exporter:1.5.1` | 0 | 65 | 100% | `nginx/nginx-prometheus-exporter:1.5.1` | https://images.minimus.io/images/nginx-prometheus-exporter/risk-reduction |
| `reg.mini.dev/grafana:13.1.3` | 0 | 26 | 100% | `grafana/grafana:latest` | https://images.minimus.io/images/grafana/risk-reduction |
| `reg.mini.dev/etcd:3.7.1` | 0 | 4 | 100% | `rapidfort/etcd-ib:latest` | https://images.minimus.io/images/etcd/risk-reduction |
| `reg.mini.dev/openbao:2.6.1` | 0 | 7 | 100% | `openbao/openbao:latest` | https://images.minimus.io/images/openbao/risk-reduction |
| `reg.mini.dev/nginx-proxy-manager:2.15.1` | 2 | 405 | 99% | `jc21/nginx-proxy-manager:latest` | https://images.minimus.io/images/nginx-proxy-manager/risk-reduction |
| `reg.mini.dev/jenkins:2.568.2-dev` | 4 | 209 | 98% | `jenkins/jenkins:latest` | https://images.minimus.io/images/jenkins/risk-reduction |
| `reg.mini.dev/sonarqube:26.8.0.126808` | 2 | 131 | 98% | `library/sonarqube:latest` | https://images.minimus.io/images/sonarqube/risk-reduction |
| `reg.mini.dev/ollama:0.32.7` | 0 | 133 | 100% | `ollama/ollama:latest` | https://images.minimus.io/images/ollama/risk-reduction |
| `reg.mini.dev/cloudflared:2026.7.3` | 0 | 18 | 100% | `cloudflare/cloudflared:latest` | https://images.minimus.io/images/cloudflared/risk-reduction |
| `reg.mini.dev/busybox:1.38.0` (init/util) | 0 | 3 | 100% | `library/busybox:latest` | https://images.minimus.io/images/busybox/risk-reduction |
| `reg.mini.dev/distribution-registry:3.1.1` | 0 | 43 | 100% | `library/registry:3.1.1` | https://images.minimus.io/images/distribution-registry/risk-reduction |

**Aggregate:** across the 22 migrated images, the published public-image CVE load was **2,540** (sum of the "Public" column); the Minimus images carry **12** total (1 go + 2 keycloak + 1 python + 2 nginx-proxy-manager + 4 jenkins + 2 sonarqube). 16 of 22 images report a 100% reduction (0 residual); the other 6 carry residual CVEs in the application package itself (`keycloak`, `jenkins-plugin-manager`, `sonarqube`, `nginx-proxy-manager-2`) or a shared toolchain package (`binutils` in go, `python-3.14-base` in python/nginx-proxy-manager) — i.e. residuals are upstream-application or shared-package CVEs that no base-image swap can remove, not Minimus-build regressions.

**Residual CVEs worth tracking** (the 12, named so a future bump can verify they close): go `CVE-2026-4647` (binutils, medium); keycloak `CVE-2026-54513` + `CVE-2026-54512` (high, keycloak package); python `CVE-2025-15367` (medium, python-3.14-base); nginx-proxy-manager `CVE-2025-15367` (medium, python-3.14-base) + `CVE-2024-51999` (unknown, nginx-proxy-manager-2); jenkins `CVE-2026-54513` + `CVE-2026-54512` (high) + `GHSA-72hv-8253-57qq` + `CVE-2025-48924` (medium); sonarqube `CVE-2026-5598` (high) + `CVE-2024-41909` (medium).

---

## Migration risks / operational considerations

These aren't blockers, but an implementer should budget for them rather than discover them mid-build:

- **Non-root UID may differ per image family.** UID isn't uniform across the current stack — `haisir-backend`/`haisir-frontend` run as `65532` (`security/SECURITY_REVIEW_2026-07-02.md`, with tmpfs mounts in `common/docker-compose.yml` hardcoding `uid=65532,gid=65532`), while Chainguard Postgres runs as `70` (`user: "70"` / `chown -R 70:70` in the same compose file). Minimus images are non-root by default but the *specific* UID is per-image (read via the Minimus INSPECT step, not assumed) and won't necessarily match either current value — every hardcoded UID in a volume mount, bind mount, or `chown`/`chmod` step needs re-verification against the new image, not carried over blind. Postgres specifically has a related, adjacent gotcha already on record: the deploy repo's Chainguard Postgres entrypoint does its `mkdir`+`chown` as root *before* dropping privileges, so a root-owned `0700` tmpfs blocks that step — a named volume (docker-created, `0755` root-owned) is what worked around it (`common/openbao/class-b-mechanism-spikes.md`, T1.4.2). Confirm the same entrypoint-ordering behavior holds (or doesn't) on `reg.mini.dev/pgvector` before assuming the current volume-type workaround still applies.
- **Entrypoint/CMD shape may differ from the Chainguard/Docker Hub equivalent.** Per the Minimus workflow's own CHECK FOR SHELL step, several of these (Postgres, Keycloak, APISIX) may have no shell in the production image, meaning any `RUN`/shell-form `CMD` in the current Dockerfiles or any `command:`/healthcheck override in compose that assumes `/bin/sh` needs rewriting to exec form or moved into a `-dev` build stage.
- **CI/build scripts reference image names outside the Dockerfiles themselves.** `DOCKER_REGISTRY`/`*_IMAGE_TAG` build args are threaded through Jenkins pipeline config and `haisir-deploy`'s deploy/build scripts, not just the Dockerfiles and compose files inventoried above — those references need the same rename, or the migration will build the right image under the wrong recorded tag.
- **Health checks and readiness probes** in compose files that shell out (`pg_isready`, `curl`, `wget`) will fail silently on a shell-less production image — needs the same shell-availability check as application `RUN` steps.

---

## Definition of done — closure status (T7.1, 2026-08-14)

- ✅ Every `FROM` line and every compose `image:` in the inventory table above resolves to `reg.mini.dev/*`, pinned to a specific version (no `:latest`), except the documented no-match/excluded/archived exceptions. Statically gated by T4.10 (`check-image-pins.sh` in CI) and runtime-verified on staging by T4.11 (17/17 containers pinned).
- ✅ Each migrated service builds clean and passes the Minimus VERIFY step (build + run, logs checked per the error-signature table in the Minimus skill) — not just a successful `docker build`. Per-component VERIFY landed with each T1.x/T2.x/T3.x/T4.x task.
- ✅ CVE reduction is reported per component using the published counts on each image's `images.minimus.io` page (Minimus workflow step 8, ANALYZE) — not asserted without a source. Delivered in T7.2: a 22-row before/after table, each row cited to its risk-reduction page (see "CVE reduction per component" above).
- ✅ No plaintext `:latest` tag remains anywhere in the migrated Dockerfiles/compose files without an explicit, documented reason (the non-versioned Minimus bases — `static`, `glibc-dynamic`, `busybox` — are the only expected exceptions, per the Minimus tag convention itself). The one tracked exception, `dev/docker-compose.yml`'s `dpage/pgadmin4:latest`, is annotated `# BR-INFRA-005: dev-only, never ships`.
- ⏳ Given the blast radius (touches every service in the stack, including the database and identity provider), this phase should get the same two-independent-security-review-pass gate that `13_secrets_management.md`'s Phase 5.6 used before merge — not a new rule, just flagging the precedent applies here too. **Deferred to T7.6.**

---

## Registry access

Minimus images pull **anonymously**, without `docker login`, at the same `FROM` line whether authenticated or not (confirmed: "Standard Minimus images can be pulled without authentication with any tag or digest"). An optional `docker login reg.mini.dev` in CI (Jenkins) raises pull-rate limits but changes nothing else — if adopted, the token follows the existing OpenBao-managed-secret pattern (`13_secrets_management.md`), not a plaintext `.env` entry.

---

## Out of scope / follow-up

- Per-image build verification (Minimus workflow steps 4–7: shell-presence check, package resolution, actual Dockerfile rewrite, build+run smoke test) was the implementation work of Phase 7.5's T1.x/T2.x/T3.x/T4.x tasks — now delivered.
- The Node 24-LTS-vs-26-current version call (inventory table) resolved to **26** at implementation time (T1.4) — the current line, matching the builder's pre-migration `node:26-trixie-slim`.
- FIPS/advanced variant adoption is deferred pending a documented compliance driver (BR-INFRA-003) — revisit if one appears.
- **Docker Hardened Images (DHI)**, Docker's own competing hardened-image line, surfaced during research as an adjacent option but wasn't evaluated in depth — Minimus was the explicit, named choice for this migration, not a default arrived at by elimination.
- **Air-gapped/self-hosted registry mirroring.** Minimus supports syncing its images into a private registry (relevant if `haisir-deploy`'s own `distribution-registry`/Docker registry service — see inventory table — is ever used to mirror rather than just host `haisir-*` images). Not evaluated; no current requirement for it.
- **SBOM/signature verification in CI.** Every Minimus image ships a signed SBOM and build attestations; wiring `cosign verify` (or equivalent) into the Jenkins pipeline to check them at pull time would extend this migration's supply-chain hardening further, but is a separate scope decision — not assumed as part of this phase.
