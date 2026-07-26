# PLAN — Phase 7 (scoping in progress)

> Phase 6 closed out 2026-07-26 and archived to
> `archive/PLAN_Phase6-ParentIndexingRetry_2026-07-26.md` /
> `archive/TASKS_Phase6-ParentIndexingRetry_2026-07-26.md`. Phase 5.6 was already archived
> (`archive/PLAN_Phase5.6-SecretsElimination_2026-07-16.md`). This file will be replaced with the
> full Phase 7 goal tree once scope is confirmed via `/plan`.

## Backlog candidates (carried forward from Phase 5, untouched by Phase 6)

Per `phases.md`'s Phase 6 section ("Not in this phase's scope"):

- Remaining role migration — `become-tutor` self-service (tutor is in scope, needs a
  `tutor_profiles` table — not yet planned); `invite-role` + `/institution` route guard
  (**blocked** — institution_admin is explicitly out of scope per `06_institution_admin.md`, and
  no `organizations` table exists to back BR-ROLE-002's org-scoping)
- RAG ops backlog — ops-only cleanup (missing `HAITU__RERANK_BASE_URL` in `.env.template`,
  reranker deployment verification, stale README, undecided monitoring stack — Prometheus/Grafana
  blocked on Chainguard licensing, resolved by the Minimus candidate below); the reranker code
  itself already shipped 2026-07-08 as `TeiRerankClient`
- Per-child audience scoping of parent-created content — deliberately deferred, no trigger
  complaint on record
- Parent-facing hAITU endpoints — blocked on a progress-monitoring-UI product decision plus a
  mastery-tracking gap for non-enrollment content (`vision/requirements/08_haitu_ai_layer.md`
  §3.5–3.7)

## New backlog candidate (spec-only, added during Phase 6)

- **Container base images: Minimus migration** — every Dockerfile/compose service across
  `haisir-backend`, `haisir-frontend`, `haisir-deploy` moves from Chainguard to Minimus
  (`reg.mini.dev`) for free pinned-version images; unblocks the Prometheus/Grafana monitoring
  stack. Full spec: `target/requirements/14_container_images.md`. Deliberately sequenced after
  Phase 6 to avoid disrupting the in-flight plan — now unblocked.

Root goal for Phase 7 not yet chosen — run `/plan` to reconcile this list against live code and
scope the next cycle.
