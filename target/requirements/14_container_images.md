# Container Base Images (Minimus Migration)

> **Target state scope:** replace Chainguard (`cgr.dev/chainguard/*`) and assorted unhardened Docker Hub / quay.io / ghcr.io images with Minimus hardened images (`reg.mini.dev/*`) across every Dockerfile and compose service in `haisir-backend`, `haisir-frontend`, and `haisir-deploy`. Cross-cutting infrastructure hardening; not tied to a persona phase.
>
> **Status note (2026-07-26):** spec only — no implementation. Explicitly sequenced as the next candidate phase **after** Phase 6 closes (`Implementation_planning/phases.md`); do not start `/plan` on this while Phase 6 is in flight.

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

Suggested version = current stable release as of 2026-07-26 — re-verify against Minimus's SELECT TAG step (supported, non-EOL lines) when this phase is actually planned, since upstream will have moved on by then.

| Component | Current image(s) | Target Minimus image | Suggested version | Notes |
|---|---|---|---|---|
| Postgres + pgvector (app DB) | Custom Wolfi build: `cgr.dev/chainguard/wolfi-base:latest` (builder) → `cgr.dev/chainguard/postgres:latest` (rolling tag; built as Postgres 18.4 + pgvector 0.8.4 per the Dockerfile's `POSTGRES_VERSION`/`PGVECTOR_VERSION` ARGs, compiled from source) | `reg.mini.dev/pgvector` | `18` (Postgres 18.4, pgvector 0.8.5) | Standalone image — **removes the custom multi-stage build entirely**, including the `:latest` rolling-tag risk. Also replaces dev's `pgvector/pgvector:0.8.2-pg18-trixie` (Docker Hub, a separate older pin). |
| Postgres (keycloak-db) | `cgr.dev/chainguard/postgres:latest` | `reg.mini.dev/postgres` (or `-hardened` if listed) | `18` | No pgvector needed here — plain Postgres. |
| Postgres (SonarQube DB, `other/services/sonarqube`) | `postgres:18-alpine` (Docker Hub) | `reg.mini.dev/postgres` | `18` | |
| APISIX | `apache/apisix:3.17.0-ubuntu` (Docker Hub) | `reg.mini.dev/apache-apisix` | `3.17` | Was never on Chainguard's free tier; already at current upstream release. |
| Go (gateway builder stage) | `golang:1.23-bookworm` (Docker Hub) | `reg.mini.dev/go:<ver>-dev` | Match `go.mod` / `GO_VERSION` ARG (upstream latest: `1.26`) | See BR-INFRA-004 — bump `go.mod`/`GO_VERSION` and the image tag together. |
| Keycloak | `quay.io/keycloak/keycloak:${KEYCLOAK_IMAGE_TAG}` (prod), `keycloak/keycloak:26.6` (dev, Docker Hub) | `reg.mini.dev/keycloak` | `26.7` | |
| Python (backend) | Builder `python:3.14-slim` (Docker Hub) → runtime `cgr.dev/chainguard/python:latest` | `reg.mini.dev/python:3.14-dev` (builder) → `reg.mini.dev/python:3.14` (runtime) | `3.14` (3.14.6) | Both stages now pin the same version — closes the Chainguard `latest`-only gap directly. |
| Node (frontend) | Builder `node:26-trixie-slim` (Docker Hub) → runtime `cgr.dev/chainguard/node:latest` | `reg.mini.dev/node:<ver>-dev` (builder) → `reg.mini.dev/node:<ver>` (runtime) | `26` (current), or `24` (Active LTS) — **open call for whoever plans this phase**, not a Minimus question | Same fix as Python. |
| Prometheus + exporters | Deferred (blocked on Chainguard licensing) | `reg.mini.dev/prometheus`, `-alertmanager`, `-node-exporter`, `-postgres-exporter`, `nginx-prometheus-exporter` | `3.11` | Unblocks the deferred monitoring stack decision (`decisions.md`, 2026-06-18). |
| Grafana | Deferred (`grafana/grafana-oss`, AGPL, was the fallback option) | `reg.mini.dev/grafana` | `13.0` | Same — unblocks it, and avoids the AGPL fallback. |
| etcd | `quay.io/coreos/etcd:${ETCD_IMAGE_TAG}` / `v3.6.11` (dev) | `reg.mini.dev/etcd` | `3.6.6` (verify against Minimus's own etcd line at plan time) | |
| OpenBao | `${OPENBAO_IMAGE:-ghcr.io/openbao/openbao:2.6.0}` | `reg.mini.dev/openbao` | `2.6.1` | |
| nginx-proxy-manager | `jc21/nginx-proxy-manager:2.15.1` (Docker Hub) | `reg.mini.dev/nginx-proxy-manager` | Latest supported line at plan time | |
| Jenkins | `jenkins/jenkins:lts` + custom Docker-in-Docker layer | `reg.mini.dev/jenkins` + `reg.mini.dev/jenkins-agent` | Latest LTS line | The Docker-CLI-in-Jenkins layer needs the `-dev` package-resolution workflow (Minimus step 5) re-run at migration time — flagged as a real implementation detail, not a blocker. |
| SonarQube | `sonarqube:community` (Docker Hub) | `reg.mini.dev/sonarqube` | Latest | |
| Ollama | `ollama/ollama:latest` (×4 service defs) | `reg.mini.dev/ollama` | Pin instead of `latest` | |
| cloudflared | `cloudflare/cloudflared:latest` | `reg.mini.dev/cloudflared` | Pin instead of `latest` | |
| Generic init/util (`alpine:latest` / `busybox:stable`) | `alpine:latest` (multiple compose services: `common/docker-compose.yml`, `common/openbao/docker-compose.openbao.yml`); `busybox:stable` (`other/services/sonarqube/docker-compose.yml`) | `reg.mini.dev/busybox` | — | Opportunistic per BR-INFRA-007, not required. The `busybox:stable` case is already the same tool, just an unhardened registry — this one's a pure registry swap with no image-family change. |
| Docker registry | `registry:3` (`other/services/registry/docker-compose.yml`) | `reg.mini.dev/distribution-registry` | Latest supported line at plan time | Hosts hAIsir's own pushed images (`haisir-backend`, `haisir-frontend`, `haisir-postgres`, `haisir-gateway`) — verify push/pull auth config carries over (Minimus's registry image is the upstream `distribution/registry` project, same API). |

### No Minimus match — stay on current registry (BR-INFRA-006)

| Component | Current image | Notes |
|---|---|---|
| CrowdSec | `crowdsecurity/crowdsec:v1.7.8` (`other/services/crowdsec/docker-compose.yml`) | No Minimus image found at discovery time (2026-07-26). |
| HuggingFace text-embeddings-inference | `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9` (`other/services/embedding/docker-compose.yml`) | No Minimus image found at discovery time. |
| dockhand | `fnsys/dockhand:latest` (`other/services/dockhand/docker-compose.yml`) | No Minimus image found at discovery time (2026-07-26) — confirmed via DISCOVER, not left unverified. |

### Explicitly excluded (BR-INFRA-005)

`pgadmin4` (`dpage/pgadmin4:latest`, `dev/docker-compose.yml`, dev-only convenience tool) — out of scope.

### Explicitly excluded — archived/superseded configs

`haisir-deploy/archived/{dev,staging,prod}/docker-compose.yml` reference `cgr.dev/chainguard/postgres:latest`, `cgr.dev/chainguard/nginx:latest` (dev), and `owasp/modsecurity-crs` (staging/prod — the WAF predecessor to the current Coraza-in-APISIX gateway). These are kept for historical reference only, are not live configs, and are **not** in scope for this migration — do not spend implementation effort on them.

---

## Migration risks / operational considerations

These aren't blockers, but an implementer should budget for them rather than discover them mid-build:

- **Non-root UID may differ per image family.** UID isn't uniform across the current stack — `haisir-backend`/`haisir-frontend` run as `65532` (`security/SECURITY_REVIEW_2026-07-02.md`, with tmpfs mounts in `common/docker-compose.yml` hardcoding `uid=65532,gid=65532`), while Chainguard Postgres runs as `70` (`user: "70"` / `chown -R 70:70` in the same compose file). Minimus images are non-root by default but the *specific* UID is per-image (read via the Minimus INSPECT step, not assumed) and won't necessarily match either current value — every hardcoded UID in a volume mount, bind mount, or `chown`/`chmod` step needs re-verification against the new image, not carried over blind. Postgres specifically has a related, adjacent gotcha already on record: the deploy repo's Chainguard Postgres entrypoint does its `mkdir`+`chown` as root *before* dropping privileges, so a root-owned `0700` tmpfs blocks that step — a named volume (docker-created, `0755` root-owned) is what worked around it (`common/openbao/class-b-mechanism-spikes.md`, T1.4.2). Confirm the same entrypoint-ordering behavior holds (or doesn't) on `reg.mini.dev/pgvector` before assuming the current volume-type workaround still applies.
- **Entrypoint/CMD shape may differ from the Chainguard/Docker Hub equivalent.** Per the Minimus workflow's own CHECK FOR SHELL step, several of these (Postgres, Keycloak, APISIX) may have no shell in the production image, meaning any `RUN`/shell-form `CMD` in the current Dockerfiles or any `command:`/healthcheck override in compose that assumes `/bin/sh` needs rewriting to exec form or moved into a `-dev` build stage.
- **CI/build scripts reference image names outside the Dockerfiles themselves.** `DOCKER_REGISTRY`/`*_IMAGE_TAG` build args are threaded through Jenkins pipeline config and `haisir-deploy`'s deploy/build scripts, not just the Dockerfiles and compose files inventoried above — those references need the same rename, or the migration will build the right image under the wrong recorded tag.
- **Health checks and readiness probes** in compose files that shell out (`pg_isready`, `curl`, `wget`) will fail silently on a shell-less production image — needs the same shell-availability check as application `RUN` steps.

---

## Definition of done (for whoever plans/implements this phase)

- Every `FROM` line and every compose `image:` in the inventory table above resolves to `reg.mini.dev/*`, pinned to a specific version (no `:latest`), except the documented no-match/excluded/archived exceptions.
- Each migrated service builds clean and passes the Minimus VERIFY step (build + run, logs checked per the error-signature table in the Minimus skill) — not just a successful `docker build`.
- CVE reduction is reported per component using the published counts on each image's `images.minimus.io` page (Minimus workflow step 8, ANALYZE) — not asserted without a source.
- No plaintext `:latest` tag remains anywhere in the migrated Dockerfiles/compose files without an explicit, documented reason (the non-versioned Minimus bases — `static`, `glibc-dynamic`, `busybox` — are the only expected exceptions, per the Minimus tag convention itself).
- Given the blast radius (touches every service in the stack, including the database and identity provider), this phase should get the same two-independent-security-review-pass gate that `13_secrets_management.md`'s Phase 5.6 used before merge — not a new rule, just flagging the precedent applies here too.

---

## Registry access

Minimus images pull **anonymously**, without `docker login`, at the same `FROM` line whether authenticated or not (confirmed: "Standard Minimus images can be pulled without authentication with any tag or digest"). An optional `docker login reg.mini.dev` in CI (Jenkins) raises pull-rate limits but changes nothing else — if adopted, the token follows the existing OpenBao-managed-secret pattern (`13_secrets_management.md`), not a plaintext `.env` entry.

---

## Out of scope / follow-up

- Per-image build verification (Minimus workflow steps 4–7: shell-presence check, package resolution, actual Dockerfile rewrite, build+run smoke test) is implementation work, not spec work — deferred to whichever phase picks this up.
- The Node 24-LTS-vs-26-current version call (inventory table) is a product/eng decision independent of the Minimus migration itself — flagged for the planning cycle, not resolved here.
- FIPS/advanced variant adoption is deferred pending a documented compliance driver (BR-INFRA-003) — revisit if one appears.
- **Docker Hardened Images (DHI)**, Docker's own competing hardened-image line, surfaced during research as an adjacent option but wasn't evaluated in depth — Minimus was the explicit, named choice for this migration, not a default arrived at by elimination.
- **Air-gapped/self-hosted registry mirroring.** Minimus supports syncing its images into a private registry (relevant if `haisir-deploy`'s own `distribution-registry`/Docker registry service — see inventory table — is ever used to mirror rather than just host `haisir-*` images). Not evaluated; no current requirement for it.
- **SBOM/signature verification in CI.** Every Minimus image ships a signed SBOM and build attestations; wiring `cosign verify` (or equivalent) into the Jenkins pipeline to check them at pull time would extend this migration's supply-chain hardening further, but is a separate scope decision — not assumed as part of this phase.
