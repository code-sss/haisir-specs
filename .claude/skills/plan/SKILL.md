---
name: plan
description: >
  Recursive goal decomposition planner for multi-repo phases. Reads target vs current state,
  presents ranked options with challenger critique, decomposes the chosen option into a tested
  dependency-ordered goal tree with repo tags, and writes PLAN.md + TASKS.md. Use when the
  user wants to plan implementation, asks "what should we build next?", "create a plan",
  "break this down", or says "/plan".
argument-hint: "[phase name or empty to start from gap analysis]"
disable-model-invocation: true
effort: max
---

# /plan — Multi-Repo Recursive Goal Decomposition Planner

This skill plans implementation work across the haisir multi-repo platform. It reads specifications from this repo (`haisir-specs`), compares target state to current state, and produces a dependency-ordered goal tree written to `Implementation_planning/PLAN.md` and `Implementation_planning/TASKS.md`.

The sibling code repos live at relative paths:
- `../haisir-backend` — FastAPI backend
- `../haisir-frontend` — Next.js frontend
- `../haisir-deploy` — Docker/infra

Reference materials for decomposition methodology:
- [methodology.md](methodology.md) — the 5 rules of recursive goal decomposition
- [challenger-checklist.md](challenger-checklist.md) — checklist for stress-testing plans
- [templates/goal-node.md](templates/goal-node.md) — template for goal nodes
- [templates/task-node.md](templates/task-node.md) — template for leaf task nodes
- [examples/multi-repo.md](examples/multi-repo.md) — worked example of a multi-repo plan

---

## Execution: Follow these phases in strict order

---

### Phase 0 — ORIENT

Check whether `Implementation_planning/PLAN.md` exists in this repo.

**If the file exists — reconcile with reality:**

1. Read both `Implementation_planning/PLAN.md` and `Implementation_planning/TASKS.md`.
2. Extract the `<!-- plan-baseline: backend:<sha> frontend:<sha> deploy:<sha> -->` watermark from the bottom of PLAN.md. This records three SHAs, one per sibling repo, from when the plan was last written.
3. If TASKS.md exists, parse current completion status (checked vs unchecked items).
4. For each sibling repo where the current HEAD differs from the baseline SHA:
   - Run `git -C ../haisir-backend rev-parse HEAD` (and likewise for frontend, deploy) to get current HEADs.
   - Run `git -C ../haisir-backend diff <baseline-sha>..HEAD --stat` and `git -C ../haisir-backend diff <baseline-sha>..HEAD` to see what changed.
   - Cross-reference code changes against plan tasks AND TASKS.md checkboxes.
   - For each task, determine: likely done (files mentioned in task were changed), unchanged, or partially done.
5. Present reconciliation summary to the user:

```
Existing plan found (baselined at backend:<sha7>, frontend:<sha7>, deploy:<sha7>).
Since then:
- T1.1 [backend]: Split current_active_user — likely done (auth/user.py changed)
- T1.2 [backend]: Wire exempt endpoints — unchanged
- T2.1 [frontend]: Add doc comment — unchanged

What would you like to do?
1. Refine the remaining plan based on what's changed
2. Add new scope to the existing plan
3. Archive this plan and start fresh
```

6. Wait for the user's choice.
   - **Option 1 (Refine):** Mark completed tasks in TASKS.md, then jump to Phase 2 with the remaining gap.
   - **Option 2 (Add scope):** Keep existing plan, jump to Phase 2 to identify additional work.
   - **Option 3 (Archive):** Move files to `Implementation_planning/archive/PLAN_<phase-name>_<YYYY-MM-DD>.md` and `PROGRESS_<phase-name>_<YYYY-MM-DD>.md`. Create the archive directory if needed. Then proceed to Phase 1.

**If the file does not exist:** Proceed directly to Phase 1.

---

### Phase 1 — GATHER CONTEXT

Launch **three parallel Agent tool calls** to collect all relevant information concurrently. Do NOT proceed until all three complete.

**Agent 1 — Target state (specs):**

Read the following files from this repo to understand what we are building toward:
- `target/requirements/00_overview.md` — if this is a stub or does not exist, fall back to `vision/requirements/00_overview.md`
- `target/requirements/01_data_model.md`
- `target/requirements/02_auth_and_roles.md`
- Any other `target/requirements/*.md` files that are relevant to the domain the user mentioned (or all of them if the user gave no specific domain). If any target file is a stub, fall back to the corresponding `vision/requirements/` file.
- If the user provided a phase name argument, focus on requirements relevant to that phase.

**Agent 2 — Current state and planning history:**

Read the following files from this repo (skip any that do not exist):
- `current/schema.md`
- `current/api_contracts.md`
- `current/ui_flows.md`
- `Implementation_planning/progress.md`
- `Implementation_planning/phases.md`
- `Implementation_planning/decisions.md`

**Agent 3 — Live code ground truth (conditional):**

This agent runs only when `current/` state files are missing, stale, or when the user's message mentions a specific domain that needs code-level verification. If triggered:
- Read relevant source files from sibling repos (`../haisir-backend`, `../haisir-frontend`, `../haisir-deploy`).
- Focus on the area the user mentioned or the area with the largest gap.
- Summarize what exists in code vs what specs say should exist.

Collect and synthesize results from all three agents before proceeding.

---

### Phase 2 — SCOPE

Based on the gap between current state and target state, produce a **ranked list of 2-4 possible next implementation steps**.

Format:

```
Next implementation possibilities:

1. [Recommended] <step name>
   Why now: <reason this should be done first>
   Scope: <which areas of the system change>
   Repos: [backend] [frontend]
   Unblocks: <what downstream steps this enables>

2. <step name>
   Why not yet: <what blocks this or makes it suboptimal to do now>
   Scope: <which areas change>
   Repos: [backend]

3. <step name>
   Why not yet: <blocker or reason to defer>
   ...
```

**Ranking rules (apply in order):**
1. Fewest blockers first — steps that can start immediately rank higher.
2. Break ties by how many downstream steps each option unblocks.
3. Mark the top pick with `[Recommended]`.
4. Be explicit about prerequisites for each option.

**Then run a Challenger Agent** on the ranked options. Give this agent the following instructions:

> You are stress-testing an implementation plan. For each of the ranked options, evaluate:
> 1. Hidden dependencies — what does this option implicitly require that is not listed?
> 2. What could go wrong — failure modes, integration risks, edge cases.
> 3. What it makes harder later — does this option constrain future options or create tech debt?
>
> For the recommended option specifically, identify the single strongest argument against choosing it.

Present the ranked list AND the challenger critique together to the user. Then ask:

**"Which option would you like to proceed with? (Or describe a different scope.)"**

Wait for the user to choose. The chosen option becomes the **ROOT GOAL** for decomposition.

---

### Phase 3 — DECOMPOSE

Launch a **Plan subagent** with the following inputs:
1. The user's chosen option as the root goal.
2. The full decomposition methodology from [methodology.md](methodology.md).
3. The node templates from [templates/goal-node.md](templates/goal-node.md) and [templates/task-node.md](templates/task-node.md).
4. The worked example from [examples/multi-repo.md](examples/multi-repo.md).
5. The relevant spec content gathered in Phase 1.

**Subagent instructions:**

> Apply the 5 rules of recursive goal decomposition from methodology.md. Produce a goal tree where:
>
> - Every node (goal, subgoal, task) is tagged with exactly one target repo: `[backend]`, `[frontend]`, `[deploy]`, or `[specs]`.
> - Cross-repo dependencies are explicit. Use the format: `Depends on: T1.2 [backend]`.
> - Decompose until every leaf task has:
>   - One behavior (single thing that changes)
>   - One "Done when" (observable acceptance criterion)
>   - One test (how to verify it)
> - Use the goal-node and task-node templates for structure.
> - Number tasks as T<goal>.<sequence> (e.g., T1.1, T1.2, T2.1).
> - Number goals/subgoals as G<sequence> (e.g., G1, G1.1, G2).

Collect the complete draft plan from this agent.

---

### Phase 4 — CHALLENGE DECOMPOSITION

Launch a **Challenger subagent** with the draft plan and the checklist from [challenger-checklist.md](challenger-checklist.md).

**Subagent instructions:**

> Evaluate this plan against every item in the challenger checklist. Additionally verify:
>
> 1. Every task is tagged with exactly one repo — no untagged tasks.
> 2. Cross-repo dependencies are explicit — if task A in [frontend] needs an API from task B in [backend], there is a `Depends on: B`.
> 3. No task spans multiple repos — if a task requires changes in both backend and frontend, it must be split.
> 4. Every leaf task has a "Done when" and a test.
> 5. The dependency graph has no cycles.
> 6. Goal-level integration tests are defined for each goal node.
>
> For each issue found, either:
> - Propose a specific fix (preferred), or
> - Flag as `<!-- UNRESOLVED: description -->` if the fix requires user input.

**Revision loop:** Incorporate the challenger's feedback into the plan. Run the challenger a second time on the revised plan. After 2 rounds maximum, include any remaining unresolved issues as `<!-- UNRESOLVED: ... -->` HTML comments in the plan.

---

### Phase 5 — PRESENT & CONFIRM

Present the complete plan to the user with the following sections:

**1. Goal tree (ASCII art):**
```
G1 [backend]: Strict header validation
  T1.1 [backend]: Split current_active_user
  T1.2 [backend]: Wire exempt endpoints (depends on T1.1)
  T1.3 [backend]: Update auth unit tests (depends on T1.1)
  * G1 integration test

G2 [frontend]: Confirm header is sent
  T2.1 [frontend]: Add BR-SEC-006 doc comment
  T2.2 [frontend]: Fix position -> order field name
  * G2 integration test
```

**2. Summary table:**
| Metric | Count |
|---|---|
| Goals | N |
| Subgoals | N |
| Tasks (backend) | N |
| Tasks (frontend) | N |
| Tasks (deploy) | N |
| Tasks (specs) | N |
| Cross-repo dependencies | N |

**3. Cross-repo dependency edges:**
List every dependency that crosses repo boundaries. These are the critical coordination points.

**4. Unresolved challenger warnings:**
List any `<!-- UNRESOLVED: ... -->` items, if present.

**5. Ready-now tasks:**
List tasks with no pending dependencies that can be started immediately.

Then ask:

**"Are you happy to proceed with the write?"**

Do NOT assume confirmation. Do NOT proceed until the user explicitly says yes. The user may request changes — if so, revise and re-present.

---

### Phase 6 — WRITE

On explicit user confirmation, write the following files:

**1. `Implementation_planning/PLAN.md`**

Write the full goal tree with detailed task descriptions. Each task node should include:
- ID and name with repo tag
- Description
- "Done when" acceptance criterion
- Test
- Dependencies (if any)

Append the SHA watermark at the very end of the file:
```
<!-- plan-baseline: backend:<full-sha> frontend:<full-sha> deploy:<full-sha> -->
```

Obtain the SHAs by running `git -C ../haisir-backend rev-parse HEAD` (and likewise for frontend, deploy).

**2. `Implementation_planning/TASKS.md`**

Generate from the plan tree using this exact format:

```markdown
# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:<sha7> frontend:<sha7> deploy:<sha7> (<YYYY-MM-DD>)

## G1 [backend]: <goal name>
- [ ] T1.1 [backend]: <task name>
- [ ] T1.2 [backend]: <task name> (depends on T1.1)
- [ ] **G1: <goal name>** — integration test

## G2 [frontend]: <goal name>
- [ ] T2.1 [frontend]: <task name>
- [ ] T2.2 [frontend]: <task name>
- [ ] **G2: <goal name>** — integration test

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T1.1 [backend]: <task name> (no deps)
- T2.1 [frontend]: <task name> (no deps)
```

**TASKS.md formatting rules:**
- Every leaf task gets `- [ ]` with its repo tag.
- Goal/subgoal integration test entries are listed AFTER their children (they can only pass once children are done). Bold the goal name.
- The "Ready now" section lists every task whose `Depends on` entries are all satisfied (checked) or that has no dependencies.
- If updating an existing TASKS.md: preserve already-checked items, update the watermark, recompute "Ready now".

**3. Clean up `progress.md` (lowercase):**

If `Implementation_planning/progress.md` exists and has a `## Next Phase` section, remove that section — the structured PLAN.md + TASKS.md now replaces it.

---

### Phase 7 — HOUSEKEEPING

Perform these updates automatically after the write. Do not ask the user for confirmation on housekeeping.

**1. `Implementation_planning/decisions.md`**

If any non-obvious decisions were made during the planning session (scope choices, trade-offs, deferral reasons), append them at the TOP of the file:

```markdown
## YYYY-MM-DD — <phase or feature name>
- <decision description>
- <decision description>
```

Skip this step if all decisions were obvious or trivial.

**2. `Implementation_planning/phases.md`**

If the phase scope changed (new phase added, existing phase re-scoped), update this file to reflect the change.

**3. `CLAUDE.md` — Critical Rules section**

Read `CLAUDE.md` in this repo. Update the Critical Rules section ONLY if the plan involves:
- Changes to the backend `UserRole` enum or `permission.py`
- Deprecation of any database table
- Renaming or removing any file path currently referenced in CLAUDE.md

If none of these apply, do not touch CLAUDE.md.

**4. `CLAUDE.md` — Implementation Planning table**

Ensure every file actively used by the planning system (`PLAN.md`, `TASKS.md`, `decisions.md`, `phases.md`) is listed in the Implementation Planning table in CLAUDE.md. Add any missing entries.

---

## Plan Lifecycle (subsequent invocations)

When `/plan` is invoked again in a future session:

1. **Phase 0** detects the existing plan and reconciles against code changes using the SHA watermark.
2. The user chooses to refine, extend, or archive.
3. **When all tasks in TASKS.md are checked:** Automatically archive both `PLAN.md` and `TASKS.md` to `Implementation_planning/archive/`, update `progress.md ## Completed Phases` if it exists, and start a fresh gap analysis from Phase 1.

---

## Rules and constraints

- **Never skip phases.** Execute Phase 0 through Phase 7 in order. Phases 1-5 involve user interaction — wait for responses where indicated.
- **Never assume user confirmation.** Phase 5 requires an explicit "yes" before writing.
- **One repo per task.** If a task requires changes in multiple repos, split it.
- **Cross-repo dependencies must be explicit.** Use `Depends on: T<id> [<repo>]` format.
- **SHA watermarks are mandatory.** Every PLAN.md must end with the baseline watermark.
- **Challenger rounds are mandatory.** Never skip Phase 4, even if the plan looks correct.
- **Cap challenger at 2 rounds.** After 2 rounds, include unresolved issues as HTML comments.
- **Archive, never delete.** Old plans go to `Implementation_planning/archive/`, never removed.
