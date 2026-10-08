# Recursive goal decomposition (planner + challenger)

Format of every node and file: `.claude/references/tasks-plan-contract.md`. Policy rules: `CLAUDE.md`
Critical Rules. Facts on the ground the plan must stay compatible with: `Implementation_planning/constraints.md`.

Ask one question recursively: **what must the system DO, and can that split into smaller parts that each
have their own definition of done?** Stop splitting when the answer is no.

## Rules (planner)

1. **Root = one user-visible outcome** (what the system achieves for a user, not which repos change), with
   an acceptance test a person could run on staging. Repos are leaf detail.
2. **Goals by concern, not repo or file.** A concern is something that can fail or succeed independently.
   "Strict header validation", not "Backend auth changes"; never split one concern into two goals because it
   spans repos. Wrong-sized if failing it breaks everything (split) or it can't be tested alone (merge into parent).
3. **Recurse until atomic.** A leaf has one behaviour, one falsifiable Done when, one test assertion.
   "and" joining independent conditions in Done when = two tasks; needing two assertions = two tasks.
4. **Every level has a test, and each proves something different.** Task = unit (one behaviour in one repo);
   subgoal = integration (its children work together); goal = E2E (the concern works as a whole);
   ROOT = acceptance (the user's purpose is met). Node tests may span repos; only leaves are repo-scoped.
5. **Order by dependency, not phase.** Declare every dependency explicitly as `ID [repo]`, including on
   artifacts (endpoint, type, config, role, route, env var) another task creates.
6. **One task, one repo.** Every leaf targets exactly one of `[backend] [frontend] [deploy] [specs]`. A change
   in two repos is two tasks linked by a dependency (backend endpoint → frontend caller). If a task name
   needs "and" to bridge two repos, it is two tasks. This is the only place this rule is stated.
7. **Build is concrete**: name the files, functions, endpoints, tables. "Implement search" is not a Build.

Well-formed goal and leaves (shape only — names are illustrative):

```
## G2 — Parent sees only the selected child's content
**Goal**: The Home Study tree lists only roots bound to the child the parent selected.
**Goal test**: Root R bound to child A only → parent's Home Study for child B shows no R card; for A it does.
**Repos**: [backend] [frontend]
##### T2.1 [backend] — Root listing filters on the child binding
- **Build**: `list_roots()` in the parent node repository adds an EXISTS on `parent_content_bindings(root_node_id, child_sub)`.
- **Done when**: `list_roots(parent, child_sub=B)` omits a root bound only to child A.
- **Test**: `assert R.id not in [n.id for n in repo.list_roots(parent, child_sub=B)]`
- **Depends on**: T1.1 [backend]
##### T2.2 [frontend] — Home Study refetches for the selected child
- **Build**: `useParentNodes(childSub)` appends `?child=<sub>` and refetches when `childSub` changes.
- **Done when**: switching from child A to B issues one request carrying `child=B`.
- **Test**: `expect(fetchMock).toHaveBeenLastCalledWith(expect.stringContaining('child=B'), expect.anything())`
- **Depends on**: T2.1 [backend]
```

Not: `Done when: filtering works` (unfalsifiable), `Test: the test itself` (no assertion),
`T2.1 — Filter roots and pass child from the tab` (two repos), `Depends on: G1 (schema)` (G-refs are invisible to Ready now).

## Challenger checklist (judgment only)

Mechanical checks are `plan_tool.py lint --plan` on the draft (before approval) and full `lint` after the
write: task headings with a missing/double/`[manual]` repo tag, missing or empty fields, Depends-on format,
unknown dependency refs, cycles, duplicate IDs, and PLAN↔TASKS leaf/node rows. Don't spend review on them.
Report each failure below as **blocking** (plan is wrong or unbuildable) or **minor**, with a concrete fix,
or `<!-- UNRESOLVED: … -->` if the user must decide.

1. **Implicit dependency** — a Build uses something another task produces but Depends on omits it
   (frontend calls a new endpoint; backend assumes a Keycloak role / APISIX route / env var from deploy).
2. **Multi-behaviour leaf** — Done when, Test or Build holds independently-failing parts; split.
3. **Cross-repo leaf** — Build touches files in two repos (e.g. a `.py` and a `.tsx`); split.
4. **File-named goal** — goal named for files/repos rather than behaviour.
5. **Unfalsifiable** — two reviewers could disagree whether Done when / a node test passes.
6. **Missing test level** — a subgoal without an integration test, goal without E2E, ROOT without acceptance.
7. **Coverage gap** — if every goal test passes, is the ROOT acceptance test actually met? Walk each criterion.
8. **Rule / constraint violation** — breaks a `CLAUDE.md` Critical Rule or a `constraints.md` fact
   (schema drops/renames, migrating deploys, release coupling) without saying so.
9. **Serialised start** — every initially-ready task is in one repo while a blocking task could be split to
   unblock another repo earlier.
10. **Scope creep** — tasks that serve no acceptance criterion of the chosen option.
