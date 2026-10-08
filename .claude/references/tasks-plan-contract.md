# TASKS.md / PLAN.md contract (single source — skills link here, never copy)

Files: `Implementation_planning/PLAN.md` and `Implementation_planning/TASKS.md`. Regexes are Python;
`ID = T\d+p?(?:\.\d+){1,2}[a-z]?` (2- and 3-level, archives use both), `REPO = backend|frontend|deploy|specs`
(`manual` tolerated in archives only; `lint` rejects it in live plans). Canonical going forward: 2-level IDs `T<goal>.<seq>` (sequential within
the goal, subgoal not encoded). Mechanical checks: `python3 .claude/skills/plan/scripts/plan_tool.py lint`
(`lint --plan <file>` = PLAN-only checks on a draft).

## PLAN.md (written only by `/plan`; everyone else reads)

```
# PLAN — <phase name>
> free-text preamble
## ROOT — <user-visible outcome>
**Root goal**: <one sentence>
**Acceptance test** (<where>): <scenario → expected result>
**Repos**: [backend] [frontend] [specs]
---
## G1 — <concern, named for behaviour, not repo>
**Goal**: <one sentence>
**Goal test**: <E2E: inputs → expected outputs>
**Repos**: [backend] [frontend]
### G1.1 — <subgoal>                      (optional level; tasks may sit directly under a goal)
**Subgoal**: <one sentence>
**Subgoal test**: <integration scenario → outcome>
**Repos**: [backend]
##### T1.1 [backend] — <task name>
- **Build**: <concrete files/functions/endpoints>; continuation lines indent 2 spaces
- **Done when**: <one falsifiable criterion>
- **Test**: <one assertion>
- **Depends on**: None | T1.3 [specs], T1.10 [backend]
## Cross-repo dependency edges            (table, informational)
## Ready now                              (frozen at scoping — never maintained; TASKS.md is authoritative)
<!-- plan-baseline: backend:<sha40> frontend:<sha40> deploy:<sha40> -->   (last line)
```

| Element | Regex |
|---|---|
| Root | `^## ROOT — (.+)$` |
| Goal / subgoal | `^## (G\d+) — (.+)$` / `^### (G\d+\.\d+) — (.+)$` |
| Node fields | `^\*\*(Root goal\|Goal\|Subgoal\|Goal test\|Subgoal test\|Repos)\*\*: `, `^\*\*Acceptance test\*\* \([^)]*\): ` |
| Task heading | `^##### (ID) \[(REPO)\] — (.+)$` — any `##### T` line not matching (no tag, two tags) is a lint `HEAD` issue |
| Task field | `^- \*\*(Build\|Done when\|Test\|Depends on)\*\*: (.*)$` — all four, this order, labels exact, none empty |
| Depends on | **Strict:** exactly `None` or a comma list of `ID [REPO]` (optional trailing `.`). IDs only — no `G…` refs, no parenthetical notes (a `G3` shorthand is invisible to Ready now; decisions.md 2026-07-14). May wrap via 2-space continuation lines like any field. `lint` flags anything else as `DEPS`. |
| Watermark | `^<!-- plan-baseline: backend:([0-9a-f]{7,40}) frontend:([0-9a-f]{7,40}) deploy:([0-9a-f]{7,40}) -->` |
| Unresolved | `<!-- UNRESOLVED: … -->` (challenger issue needing the user) |

Hierarchy (for bubble-up) is heading nesting: a task's parent is the nearest preceding `###`/`##` node.
Dependencies are authoritative here; the `(depends on …)` tail in TASKS.md is a human copy.

## TASKS.md (written by `/plan`, implement-* bookkeeping, `/sync-spec`, humans for `[specs]`)

```
# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:d927209 frontend:d178c98 deploy:790e29d (2026-08-21)
> optional free-text phase notes (preserve on refine)

## G1 [backend][frontend][specs]: Per-child Home Study binding
### G1.1 — Binding schema + behaviour-preserving migration
- [ ] T1.2 [backend]: root_node_id column on the three owner-scoped tables
- [x] T1.1 [backend]: parent_content_bindings table model (depends on T1.3) (2026-08-21)
- [ ] **G1.1: Binding schema + behaviour-preserving migration** — integration test
- [ ] **G1: Per-child Home Study binding** — E2E test
---
- [ ] **ROOT: Home Study is per-child** — acceptance test

## Ready now

- T1.2 [backend]: root_node_id column on the three owner-scoped tables (no deps)
- T1.24 [frontend]: createNode sends child_subs (depends on T1.23 [frontend], T1.10 [backend])
```

| Element | Regex |
|---|---|
| Baseline (canonical) | `^> Last baselined: backend:([0-9a-f]{7}) frontend:([0-9a-f]{7}) deploy:([0-9a-f]{7}) \((\d{4}-\d{2}-\d{2})\)$` |
| Baseline (tolerant — readers accept legacy bold/backticked) | ``^> (\*\*)?Last baselined: backend:`?([0-9a-f]{7,40})`? frontend:`?([0-9a-f]{7,40})`? deploy:`?([0-9a-f]{7,40})`? \((\d{4}-\d{2}-\d{2})`` |
| Goal section | `^## (G\d+)((?: ?\[(?:REPO)\])*): (.+)$` (same name as PLAN, colon + tags instead of `—`) |
| Subgoal section | `^### (G\d+\.\d+) — (.+)$` |
| Leaf | `^\s*- \[( \|x\|~)\] (ID) \[(REPO)\]: (.+)$`; optional tail in order: ` (depends on …)`, ` ← note`, ` (YYYY-MM-DD)` when done |
| Node (test row) | `^\s*- \[( \|x\|~)\] \*\*(ROOT\|G\d+(?:\.\d+)?): (.+?)\*\* — (.+)$`, after its children; wrapped evidence indents 6 spaces |
| Release-gate pending leaf | `^\s*- \[ \] T[0-9]` (haisir-deploy `detect-changes.sh`) |
| Ready now | `^## Ready now$`, last section; bullets `^- (ID) \[(REPO)\]: (.+?) \((no deps\|depends on [^)]+)\)$`; when empty exactly one `- None ready — <why>.` bullet. No prose. |

Rules:
- `## Ready now` in TASKS.md is the live queue: every `[ ]` leaf (all tags, `[specs]` included) whose PLAN
  deps are all `[x]`. Recompute with `plan_tool.py ready --write`, never by hand-editing prose.
- Each implement-* skill updates only its own `<repo>:<sha7>` (`git rev-parse --short=7 HEAD`) on the baseline line.
- Done = `[x]` + ` (YYYY-MM-DD)` at end of line. Every PLAN task has exactly one leaf (same ID + tag); every
  goal/subgoal/ROOT has one node row (`lint`: `NODE_MISSING`).
- Status tokens observed on node rows and tolerated (free text after ` — `): `PASSED <date>`, `FAIL` /
  `failed` (bubble-up stopped), `PENDING-LIVE` (needs a live stack; deploy), `NOT RUN`. `[~]` = deferred
  (archives only) — **not** counted as pending by the release gate.
- Archive-eligible = every leaf row **and** the ROOT row `[x]` (`plan_tool.py stats`). Archive as
  `Implementation_planning/archive/PLAN_<phase>_<date>.md` + `Implementation_planning/archive/TASKS_<phase>_<date>.md`
  (`<phase>` kebab-case from the PLAN title, `<date>` YYYY-MM-DD). With no PLAN/TASKS, `lint`/`stats`/`ready` print `NO_PLAN`;
  with only one of them, `PARTIAL missing <file>` (never overwrite that unarchived PLAN.md).

## Consumers (who reads/writes what)

| Consumer | Reads | Writes | Copy used |
|---|---|---|---|
| haisir-backend `/implement-backend` | Ready now, `[backend]` leaves; PLAN task + parent node tests + deps | leaf `[x]`, node rows, Ready now, `backend:` SHA | synced `/workspaces/haisir-specs` (devcontainer) |
| haisir-frontend `/implement-frontend` | same, `[frontend]` | same, `frontend:` SHA | synced copy (devcontainer) or host |
| haisir-deploy `/implement-deploy` | same, `[deploy]` | same + `PENDING-LIVE`, `deploy:` SHA | **host** `~/Workspace/haisir-specs` (live git tree) |
| haisir-deploy `release-manifest/scripts/detect-changes.sh` | TASKS pending-leaf regex → `PENDING <n>` gate | nothing | host; missing file → NOTE, gate skipped |
| haisir-backend `review-backend/rules.md` | TASKS (later task stages migration?) | nothing | synced copy |
| `/plan` (this repo) | everything via `plan_tool.py` | both files; archives | host |
| `/describe-current-state` | PLAN watermark | nothing | host |
| `/sync-spec` + `sync-specs.sh` | pulled TASKS/PLAN vs pushed base | merged TASKS/PLAN | host ↔ containers `frontend`, `backend` |

Synced copy = `sync-specs.sh push` (`git archive HEAD` → `docker cp`) of `target/`, `Implementation_planning/`,
`vision/requirements/`, `.claude/references/` and `CLAUDE.md` (no `.git`, no `.claude/skills/`, so `plan_tool.py` is
not present in containers). Push replaces the container's synced paths with an exact copy of host HEAD (files absent
from HEAD are deleted there), so it refuses when the container has no `.spec-sha` or holds edits not yet pulled
(differs from both its pushed SHA and the last `pull`); `--force` discards them. `pull` never overwrites host edits:
it 3-way merges against the pushed SHA, and `/sync-spec` resolves what conflicts.

## Must not change (breaks a consumer)

- Paths: `haisir-specs/Implementation_planning/{PLAN,TASKS}.md` (all implement-*, release gate, sync-specs.sh).
- Leaf syntax `- [ ] T<digit>… [repo]: …`; pending must stay `[ ]` (release gate fails open otherwise).
- `## Ready now` heading text; `Last baselined` keyword and `backend:`/`frontend:`/`deploy:` keys.
- PLAN watermark syntax and last-line position (`/plan`, `/describe-current-state`).
- Tag placement `ID [repo]` in both files; PLAN field labels `Build` / `Done when` / `Test` / `Depends on`.
- PLAN nesting ROOT ⊃ goal ⊃ subgoal ⊃ task and the `**Goal test**` / `**Subgoal test**` labels (bubble-up).
- Node rows `- [ ] **G…: name** — … test` (bubble-up, archive check).

## Known consumer drift (fix in sibling repos)

None known (last checked 2026-10-08 against implement-frontend/backend/deploy).
