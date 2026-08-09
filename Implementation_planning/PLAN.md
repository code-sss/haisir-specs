# PLAN — no active phase

> Phase 7 (Gateway WAF Modernisation, CSP & Security Review Closeout) closed **2026-08-06** and
> shipped as **v2026.6** (staging 2026-08-07, prod 2026-08-08). Its plan and tasks are archived:
>
> - `archive/PLAN_Phase7-GatewayWAF-CSP_2026-08-06.md`
> - `archive/TASKS_Phase7-GatewayWAF-CSP_2026-08-06.md`
>
> Close-out record: `decisions.md` (2026-08-06) and `phases.md` (Phase 7, Outcome column).

## Next up — Phase 7.5

**Minimus Container Images + Phase 7 Deploy Backlog.** The stub — root goal, the five intended
goals, scope carve-outs and carried-forward items — is in `phases.md` (§ Phase 7.5). Primary spec is
`target/requirements/14_container_images.md`, written 2026-07-26 and still current; it already
carries the full image inventory, version targets and variant-tier policy, so no
`/update-target-state` pass is needed before planning.

Run `/plan` to populate this file and `TASKS.md`.

**Baseline for that plan** (verified from each sibling repo's HEAD, working trees clean, 2026-08-09):

<!-- plan-baseline: backend:00c2c738ace3ab6e5d40317a4298cea5a94a91ab frontend:705833ddeecae3201ba464d9b3837250e87e2432 deploy:844e8f9df25cca5ffb4b7d3f2ee1ef64a1d02e05 -->

| Repo | HEAD |
|---|---|
| haisir-backend | `00c2c73` |
| haisir-frontend | `705833d` |
| haisir-deploy | `844e8f9` |

> One thing to settle before or during planning, not after: **B6 — the Keycloak admin console is
> reachable at `200` from the public internet.** It is a decision, not a task. The obvious fix does
> not work as written: admin traffic arrives through cftunnel, so `ip-restriction` evaluates the real
> client IP that `real-ip` extracts, not a tailnet address — setting the CIDR to the workstation's
> Tailscale `/32` would lock everyone out of the IdP that authenticates every other service. What
> must be decided first is **from where the console should be reachable at all**: public with an
> allowlist, or off the public gateway entirely and reached over the tailnet. The realm policy
> (12-char, no-username/email, 30-attempt lockout, TLS-only) makes the current state survivable for a
> short while; it does not make it acceptable indefinitely.
