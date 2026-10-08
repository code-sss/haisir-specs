---
name: plan
description: Plan the next multi-repo phase into Implementation_planning/PLAN.md + TASKS.md (plan_tool.py orient → gather agents → scope options + challenger → planner draft → challenger → approval → writer agent + lint → housekeeping), or archive a finished phase. Does not commit.
argument-hint: "[phase name or focus area, or empty to start from the next-phase priorities]"
disable-model-invocation: true
effort: max
---

# Plan a phase

**Context rule:** the main session only orchestrates. It never reads PLAN.md/TASKS.md bodies,
decisions.md, phases.md, progress.md, constraints.md, `target/`, `current/` or sibling repos. It runs
`plan_tool.py`, reads its compact output, and reads only the short handoff files named below for the user.
Stages hand off through `D=.claude/plans/plan-<YYYY-MM-DD>/` (create it first); on a same-day rerun use the next free
`plan-<YYYY-MM-DD>-2`, `-3`, … so stale handoffs never leak in (never delete old ones). Agent prompts pass
paths, never pasted content, and end with the return line shown. The user's words (scope choice, approval
feedback) are written verbatim by main to `$D/choice.md` / `$D/feedback-N.md` so later agents see them.

- Format: `.claude/references/tasks-plan-contract.md` · method + challenger checklist: `.claude/skills/plan/methodology.md`
- Tool: `T=python3 .claude/skills/plan/scripts/plan_tool.py` (`lint [--plan <file>] | ready [--write] | stats | drift`)
- Siblings: `../haisir-backend`, `../haisir-frontend`, `../haisir-deploy`

## 1. Orient

Run `$T stats`, `$T lint`, `$T drift`.

- **archive-eligible yes** → go to §7.
- **PLAN.md exists with open rows** → run the **State agent** (§2) now, then show the three outputs plus
  `sed -n '/^## Open-task reconciliation/,/^## /p' $D/context-state.md` and ask: **1** refine the remaining
  plan, **2** add scope to it, **3** archive it as-is and start fresh (§7, then continue). **Wait for the answer.**
- **Both files, no open rows, not eligible** (e.g. ROOT row missing → lint `NODE_MISSING`) → take the open-rows
  branch above; on refine, the §6 writer adds the node rows that lint names as missing.
- **Refine chosen** → list the tasks the reconciliation marks *likely done* and ask which to tick (none is
  fine). Only the IDs the user confirms go to a bookkeeping agent (`general-purpose`, model `sonnet`): "In
  `Implementation_planning/TASKS.md` tick exactly <IDs> per `.claude/references/tasks-plan-contract.md` (`[x]` +
  ` (YYYY-MM-DD)` today at line end), then run `python3 .claude/skills/plan/scripts/plan_tool.py ready --write`. Return only the `READY` line." Otherwise
  ticking belongs to implement-* in the code repos.
- **`PARTIAL`** (only one of PLAN.md/TASKS.md) → show it; ask whether to archive what exists (§7) or stop
  (TASKS.md only: also ask for the phase name — its `# Progress` header has none).
  Never write over an unarchived PLAN.md.
- **`NO_PLAN`** → fresh plan.

If `drift` shows `snapshot` moved, say `current/` is stale and suggest `/describe-current-state` first; continue if the user declines.

## 2. Gather (one message, both agents in parallel, `general-purpose`; skip State if §1 ran it)

**Target agent:** "Read `target/requirements/00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md` (sections
relevant to the focus only) and the target files for the focus `<$ARGUMENTS or 'next-phase priorities in
Implementation_planning/phases.md'>`. Where a target file is a stub, use the matching-topic `vision/requirements/`
file. Write `$D/context-target.md` with sections `## Focus` (≤5 lines), `## Required behaviour` (≤40 bullets, each
citing file:BR-id), `## Open questions` (≤10). Return only `WROTE <path> <lines>`."

**State agent:** "Read only these sections: `Implementation_planning/phases.md` next-phase stub and '## Next-phase
priorities'; `progress.md` '## Current State' (top blockquote and the latest phase paragraphs); `constraints.md` (all);
the newest 3 entries of `decisions.md` plus any older entry whose heading or body matches the focus (grep);
`current/*.md` only by grep for the focus area. Plan state: <paste the `$T stats` and `$T drift` lines>.
<If a plan exists: list open rows with `grep -nE '^\s*- \[ \]' Implementation_planning/TASKS.md`; for each open
leaf read only its PLAN section (`sed -n '/^##### <ID> /,/^#####/p'`) and compare `git -C ../haisir-<tag> diff --name-only
<plan sha>..HEAD` against the paths in its Build line → likely done | partial | untouched (with the evidence path).>
If `current/` is stale for the focus area, check the sibling code directly in `../haisir-backend`,
`../haisir-frontend`, `../haisir-deploy`. Write `$D/context-state.md` with sections
`## Built today` (≤30 bullets), `## Constraints that bind` (≤15, cite constraints.md line), `## Backlog / priorities`
(≤15), `## Open-task reconciliation` (one line per open task, or 'n/a'). Return only `WROTE <path> <lines>`."

## 3. Scope (two sequential agents, `general-purpose`)

**Scoper:** "Mode: <mode>. Read `$D/context-*.md` and `.claude/skills/plan/methodology.md`. Options are: fresh → phase
options; refine → ways to close the remaining gap to the current ROOT; add-scope → additions beyond the current
ROOT. Write `$D/options.md`: 2–4 options ranked by fewest
blockers, ties by most downstream work unblocked; top one marked `[Recommended]`. Each: name, Why now / Why
not yet, Scope, Repos, Unblocks, Prerequisites (≤6 lines each). Return only `WROTE <path>`."

**Challenger:** "Read `$D/options.md`, `$D/context-*.md`, `Implementation_planning/constraints.md`, `CLAUDE.md`
Critical Rules. Append `## Challenger` to options.md: per option hidden dependencies, failure modes, what it
makes harder later; for the recommended one the single strongest argument against. Return only `REVIEWED`."

Read `$D/options.md`, present it, ask **"Which option? (or describe a different scope)"** and **wait**.
The choice is the ROOT goal. Write `$D/choice.md`: the chosen option name (or the user's own scope text),
their stated reasons and constraints, verbatim.

## 4. Decompose → challenge (`general-purpose`, inherited model)

**Planner:** "ROOT goal: read `$D/choice.md`. Mode: fresh | refine | add-scope. Read `.claude/skills/plan/methodology.md`,
`.claude/references/tasks-plan-contract.md`, `$D/options.md`, `$D/context-*.md`, and the specs/code you need. Refine/add-scope: start from the
current `Implementation_planning/PLAN.md` and `Implementation_planning/TASKS.md` (done status), keep done tasks and their IDs. Write the full PLAN.md body (no
watermark) to `$D/draft.md` per the contract, including '## Cross-repo dependency edges' and '## Ready now'
(tasks whose deps are all done or none). Return only `WROTE <path> goals=<n> subgoals=<n>
tasks=<backend n/frontend n/deploy n/specs n> xrepo=<cross-repo edges>`."

**Challenger round N** (N=1): "Read `$D/draft.md`, apply the challenger checklist in `.claude/skills/plan/methodology.md`, check
against `Implementation_planning/constraints.md` and `CLAUDE.md` Critical Rules. Write `$D/review-N.md`: one line per issue
`[blocking|minor] <ID> — problem → fix`. Return only `REVIEW <n blocking> <n minor>`."

**Planner revise:** "Apply `<$D/review-N.md | $D/feedback-N.md | the lint lines below>` to `$D/draft.md` in
place; anything needing the user becomes `<!-- UNRESOLVED: … -->`. Return only `REVISED <n fixed> <n unresolved>`
followed by the planner's `goals=… subgoals=… tasks=… xrepo=…` counts."

Run round 2 only if round 1 returned blocking > 0. No round 3: leftovers stay as UNRESOLVED comments.

Then run `$T lint --plan $D/draft.md`. On `ISSUES`, planner revise once with those lines and re-run.

## 5. Approval

Show compact views only: the latest counts line; `grep -nE '^(## |### |##### )' $D/draft.md` (the goal tree);
`sed -n '/^## Cross-repo/,/^## [^C]/p' $D/draft.md | head -30`; `sed -n '/^## Ready now/,$p' $D/draft.md | head -15`;
`grep -n UNRESOLVED $D/draft.md`; the final `lint --plan` output; and the challenger return lines. Then:

> **⏸ APPROVAL REQUIRED** — reply **go** to write PLAN.md + TASKS.md, or give feedback to revise.
> Only an explicit user message counts. Never auto-approve, even in auto mode.

**Stop.** Feedback → write it verbatim to `$D/feedback-N.md` (N = approval round) → planner revise with it →
`lint --plan` → present again.

## 6. Write + housekeeping

**Writer** (`general-purpose`): "Mode: <mode>. Fresh mode: if `Implementation_planning/PLAN.md` exists, stop and
return `BLOCKED PLAN.md exists unarchived`. Per `.claude/references/tasks-plan-contract.md`: copy `$D/draft.md` to
`Implementation_planning/PLAN.md` and append the watermark from `git -C ../haisir-<repo> rev-parse HEAD` for backend,
frontend, deploy. Generate TASKS.md from it (canonical baseline line with `--short=7` SHAs and today's date). Refine/add-scope:
keep every existing `[x]` row with its date, node evidence and the header's free-text notes. Then run
`python3 .claude/skills/plan/scripts/plan_tool.py lint`. Fix only formatting you introduced (TASKS row/heading
syntax, missing node rows, whitespace); anything that would change a task, dependency or tag means the approved
draft is wrong — don't fix it, return `BLOCKED <lint lines>`. Once `OK`, run
`python3 .claude/skills/plan/scripts/plan_tool.py ready --write`. Return only the final lint line and the `READY` line."

On `BLOCKED`, show the lines to the user and go back to §5 (substantive changes need their approval).

**Housekeeping** (`general-purpose`): "Read `$D/choice.md`, `$D/feedback-*.md`, `$D/options.md` and `$D/review-*.md`.
Prepend a dated `## YYYY-MM-DD — <phase>` entry to `Implementation_planning/decisions.md` with the chosen scope and
the user's reasons, the options deferred, the non-obvious trade-offs and what the user changed at approval.
Update the phase entry in `phases.md`; add to `constraints.md` only a new implementation-reality fact this plan creates. Touch `CLAUDE.md` Critical Rules only if the plan changes the
`UserRole` enum / `permission.py`, deprecates a table, or renames a path CLAUDE.md cites. Return only
`UPDATED <files>`."

Report: lint line, READY line, `$T stats` line, UPDATED files. Do **not** stage or commit.

## 7. Archive (`general-purpose`, model `sonnet`)

"Read line 1 of `Implementation_planning/PLAN.md` (`# PLAN — <phase>`; if PLAN.md is missing, use `<phase name the
user gave in §1>`) for the phase name, kebab-case it (e.g. Phase8-ParentUX); date: today. Move whichever of
`Implementation_planning/PLAN.md` → `Implementation_planning/archive/PLAN_<phase>_<date>.md` and
`Implementation_planning/TASKS.md` → `Implementation_planning/archive/TASKS_<phase>_<date>.md` (date YYYY-MM-DD)
exist with `mv` (no git). Add a 3–5 line `### <phase> ✓` entry at the top of
`progress.md` '## Completed Phases' from the archived TASKS header — or, when `$T stats` said archive-eligible no,
`### <phase> — archived incomplete (<done>/<total> leaves)` (paste the stats line). Return only `ARCHIVED <paths>`."

Then tell the user: run `/release-manifest <version>` in haisir-deploy, dry-run it with
`bash common/scripts/deploy.sh --manifest releases/v<version>/manifest.yaml --env staging --dry-run`, then
`/plan` again for the next phase. Don't start a new plan unless they chose option 3 in §1.
