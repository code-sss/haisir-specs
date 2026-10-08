---
name: sync-spec
description: Bring a devcontainer's spec edits back into haisir-specs (`./sync-specs.sh pull` 3-way merge against the pushed SHA → one subagent per conflicted file → Ready-now recompute → lint → diffstat). Does not commit or push.
when_to_use: Use after implement-* work in the backend or frontend devcontainer marked tasks done in its spec copy. Triggers - "sync specs from backend", "sync specs from frontend", "pull specs", "/sync-spec backend".
argument-hint: "<frontend|backend>"
---

# sync-spec

**Context rule:** the main session only orchestrates. It reads the script's compact output and agent return lines, never full diffs or TASKS.md/PLAN.md bodies. Formats (TASKS/PLAN lines, `Last baselined`, `## Ready now`) are defined once in `.claude/references/tasks-plan-contract.md`; link it, don't copy it.

`./sync-specs.sh` syncs `target/`, `Implementation_planning/`, `vision/requirements/`, `.claude/references/` and `CLAUDE.md`, and nothing else. Every `push` makes the container's copy of those paths an exact copy of host HEAD and writes the HEAD SHA to `/workspaces/haisir-specs/.spec-sha`; `pull` uses that SHA as the merge base. `push` refuses (`REFUSED … not pulled …` / `REFUSED no …/.spec-sha …`) when the container may hold edits no `pull` has seen; pull first, and use `push --force` only when the user says to discard them.

## 1. Pull

No argument → ask "`backend` or `frontend`?" and **wait for the answer**. Then run `./sync-specs.sh pull <c>`.
- `REFUSED uncommitted changes …` → tell the user to commit or stash those paths. **Stop.** Don't stash for them.
- `REFUSED cannot reach container …` → the devcontainer is stopped or misnamed. Tell the user to start it. **Stop.**
- `REFUSED no …/.spec-sha …` → this is a legacy push with no recorded SHA. Ask the user for the spec SHA that was last pushed to `<c>`, then rerun with `--base <sha>`.
- `OK merged <n> clean <n> conflicts 0` → check deletions (below), then go to step 3.

The script writes merged files into the working tree only after every merge ran (all or nothing). `CONFLICT` files keep `<<<<<<< host` / `||||||| base` / `>>>>>>> <c>` markers. `CONTAINER-ONLY`, `HOST-DELETED` (host deleted it, container changed it), `CONTAINER-DELETED` (container deleted it, host still has it) and `BINARY` (differs on both sides; host copy kept) are reported only, never applied.

**Deletions.** A clean merge silently applies lines the container removed. For every `MERGED <path> (-<n> lines)` with n > 0, spawn one `general-purpose` Agent (all such paths in one prompt): "Run `git diff -U1 -- <paths>`. Ignore lines rewritten in place (e.g. `[ ]` → `[x]` flips), anything inside TASKS.md `## Ready now`, and the `Last baselined` line. For each remaining pure removal, return `DELETED <path>:<line> — <one-line summary of what was removed>`, or only `NONE`." If it returns any `DELETED` line, show them and ask **"Keep these deletions, or restore them from host?"** and **wait**. Restore = the same agent re-adds the removed lines with targeted edits. Don't read the diffs yourself.

## 2. Resolve conflicts (one message, all agents in parallel)

For each `CONFLICT <path>`, spawn one `general-purpose` Agent with this prompt: "Resolve the git conflict markers in `<path>` (host = haisir-specs HEAD, `<c>` = devcontainer copy). First read the `## Merge rules` section of `.claude/skills/sync-spec/SKILL.md` and `.claude/references/tasks-plan-contract.md`. Edit only the conflict hunks. Remove every marker you resolve, and leave the markers on any hunk you can't decide. Return only `RESOLVED <path>` or `NEEDS-USER <path>: <one line>`."

When the agents return, run `grep -l '^<<<<<<< host' <conflicted paths>`. For each `NEEDS-USER`, put the one-line question to the user, **wait for the answer**, then apply it with a targeted Edit of that hunk.

## Merge rules (for the conflict agents)

- The container's spec copy is stale. Host content wins for planning text: PLAN task blocks, decisions, phases and `target/` wording.
- Keep a container `target/` change only when it is a correction found during implementation, such as a renamed field or a clarified rule. If you can't tell, return NEEDS-USER.
- TASKS.md: keep the container's `[ ]` → `[x]` flips and their `(YYYY-MM-DD)` dates. Never un-check a task that host already marked `[x]`.
- `Last baselined` line: take the container's own `<c>:<sha>` and keep every other repo's SHA from host.
- `## Ready now`: don't merge it by hand. Take the host side; step 3 recomputes it.
- Any other line that both sides changed differently → NEEDS-USER.

## 3. Recompute and lint

```bash
python3 .claude/skills/plan/scripts/plan_tool.py ready --write
python3 .claude/skills/plan/scripts/plan_tool.py lint | tail -20
```

If lint fails, send the failing lines to one `general-purpose` Agent to fix, then lint again.

## 4. Report (compact)

- `git diff --stat -- target Implementation_planning vision/requirements .claude/references CLAUDE.md | tail -15`
- Status line from step 1, plus the `MERGED` / `BINARY` / `CONTAINER-ONLY` / `HOST-DELETED` / `CONTAINER-DELETED` lines verbatim, and the deletion decision (kept / restored / none). Container-only files sit under `.claude/plans/sync-spec/<c>/`; copy one in only if the user asks, because the next push deletes it from the container. For `CONTAINER-DELETED`, ask whether to delete the host copy too; the next push restores it in the container otherwise.
- Next: review and commit, then run `./sync-specs.sh push <c>` so the container gets the merged spec and a fresh `.spec-sha`. Run `/describe-current-state` if the container shipped endpoints or schema.
