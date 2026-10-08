# hAIsir — Specs

Requirements, plans and HTML prototypes for the hAIsir edtech platform. No code, no build, no tests.
Code lives in the sibling repos `haisir-backend` (FastAPI), `haisir-frontend` (Next.js) and `haisir-deploy` (Docker Compose / infra).

Rules, read order and the spec-update convention for code PRs are in [CLAUDE.md](CLAUDE.md) — the single source for both humans and Claude.

## Directory map

| Path | What |
|---|---|
| `target/requirements/` | Near-term target spec (numbered `00`–`17`) + `ui-mapping/`. What the next phases build. |
| `target/prototypes/` | Target HTML prototypes (admin, parent, student flows) — open in a browser |
| `vision/requirements/` | Long-term 6-persona vision spec, role migration (`11_role_migration.md`), `backlog.md`, `ui-mapping/` |
| `vision/prototypes/` | Vision HTML prototypes (all personas, onboarding, notifications) |
| `vision/phases.md` | Long-term phasing |
| `current/` | What is built today (schema, API contracts, UI flows) + `snapshot_shas.md` baseline |
| `Implementation_planning/` | `progress.md` (start here), `PLAN.md`, `TASKS.md`, `phases.md`, `decisions.md`, `constraints.md`, `archive/` |
| `docs/` | End-user guides (student, parent, platform admin) |
| `security/` | Security review reports and resolutions |
| `experiments/` | RAG experiments and architecture diagrams |
| `specification.md` | Standalone agentic-RAG service spec (2026-04) |
| `parent-screens/` | Empty placeholder |
| `scripts/` | `check_no_coauthored.sh` (commit-msg guard), `test_sync_specs.sh` |
| `sync-specs.sh` | Push/pull specs to/from the devcontainers |
| `.claude/` | Skills, `references/tasks-plan-contract.md`, `settings.json` |

## How specs flow

- **vision** = where the product is going; **target** = what the next phases build (filled incrementally from vision via `/update-target-state`; fall back to vision where a target file is a stub); **current** = what the code does today (`/describe-current-state`).
- `/plan` turns target vs current into `PLAN.md` + `TASKS.md`; the `implement-*` skills in each code repo work from `TASKS.md` and tick tasks off.
- The backend and frontend devcontainers get a copy: commit here, then `./sync-specs.sh push [frontend|backend|all]` (copies committed `target/`, `Implementation_planning/`, `vision/requirements/`, `.claude/references/`, `CLAUDE.md`). Bring their edits back with `/sync-spec <frontend|backend>` (3-way merge). `vision/prototypes/` stays host-only; deploy reads this repo directly.

## Skills

Heavy reading (specs, plans, sibling repos) runs in subagents; the main session only orchestrates. Handoffs go to `.claude/plans/` (gitignored), shared formats to `.claude/references/`.

| Skill | What it does | Auto-picked? |
|---|---|---|
| /plan | Plans the next phase into `PLAN.md` + `TASKS.md` (gather → options → challenger → approval → writer + lint), or archives a finished phase | No — manual only |
| /update-target-state | Changes `target/requirements/` (gather → discussion → challenger → approval → writer); records it in `decisions.md`, `progress.md`, `constraints.md` | Yes — "change the target spec for X" |
| /describe-current-state | Captures what is built into `current/*.md` from sibling-repo diffs since the last snapshot SHA; `--guides` refreshes `docs/` | Yes — "what's built?" |
| /sync-spec | Pulls a devcontainer's spec edits back (3-way merge, conflict agents, Ready-now recompute, lint) | Yes — "sync specs from backend" |

None of them commit.

Scripts (compact, line-oriented output):

- `python3 .claude/skills/plan/scripts/plan_tool.py lint [--plan <file>]|ready [--write]|stats|drift|selftest` — PLAN/TASKS checks
- `python3 .claude/skills/describe-current-state/scripts/snapshot.py [--files <repo>|--write|--selftest]` — sibling-repo changes since `current/snapshot_shas.md`
- `./sync-specs.sh push [frontend|backend|all] [--force]` / `pull <frontend|backend> [--base <sha>]` — container sync (push refuses over unpulled container edits unless `--force`); `bash scripts/test_sync_specs.sh` self-checks it with a fake docker
