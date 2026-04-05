# Challenger Checklist

Use this checklist to evaluate plan quality. Each criterion has a concrete pass/fail check. Walk through every criterion; report all FAILs before suggesting fixes.

---

## Structural integrity

### 1. Circular dependencies
**Check:** No task A depends on B which depends on A (directly or transitively).
**How to verify:** Build a dependency graph from all `Depends on:` lines. Walk every edge; confirm the graph is a DAG (no cycles).
**FAIL example:** T2.1 depends on T3.1, T3.1 depends on T2.1.

### 2. Orphan tasks
**Check:** Every task belongs to exactly one subgoal or goal.
**How to verify:** List all task IDs under goal headings. List all task IDs mentioned anywhere in the plan. The two sets must be identical.
**FAIL example:** T4.2 appears in the dependency list of T5.1 but is not listed under any goal.

### 3. Implicit dependencies
**Check:** Every dependency is explicitly declared. If task B uses something task A produces, B must have `Depends on: A`.
**How to verify:** For each task, read its "Build" description. If it references an artifact (function, endpoint, config, type) created by another task, confirm that task appears in `Depends on:`.
**FAIL example:** T2.3 calls `POST /api/foo` which is created by T1.2, but T2.3 says `Depends on: None`.

---

## Decomposition quality

### 4. Multi-behavior tasks
**Check:** Every leaf task has exactly one behavior and one "Done when" criterion. If "Done when" contains "and" joining independent conditions, split.
**How to verify:** Read each "Done when" line. If it contains "and" or ";" joining conditions that could pass/fail independently, flag it.
**FAIL example:** `Done when: Endpoint returns 400 on missing header AND migration adds new column.` These are independent behaviors — split into two tasks.

### 5. Wrong sizing
**Check:** No leaf task still contains sub-concerns that could fail independently.
**How to verify:** Read each "Build" description. If it describes more than one file change where each change has its own success criterion, flag it.
**FAIL example:** `Build: Add validation middleware, update 12 route files to use it, and write migration for audit log table.` Three independent concerns.

### 6. File-based decomposition
**Check:** Goals are named after behaviors, not files.
**How to verify:** Read each goal name. It should describe what the system does differently, not which file changes.
**FAIL example:** `G2: Update user.py and routes.py` — should be `G2: Strict header validation`.

---

## Test coverage

### 7. Missing test levels
**Check:** Every TASK has a unit test, every SUBGOAL has an integration test, every GOAL has an E2E test.
**How to verify:** Confirm each task has a `Test:` line. Confirm each goal's last item is an integration or E2E test task. Confirm the root goal has an acceptance test.
**FAIL example:** G2 has three tasks but no integration test verifying they work together.

### 8. Unfalsifiable "Done when"
**Check:** Every criterion can be objectively verified as pass/fail.
**How to verify:** For each "Done when", ask: could two people disagree on whether this passes? If yes, it needs tightening.
**FAIL example:** `Done when: Code is clean and well-structured.` — not falsifiable. Should be: `Done when: uv run pytest tests/unit/auth/ -v passes.`

---

## Completeness

### 9. Coverage gaps
**Check:** If every child goal passes its E2E test, is the root goal achieved?
**How to verify:** Re-read the root goal definition. Walk each acceptance criterion. Confirm at least one goal's E2E test covers it.
**FAIL example:** Root goal says "admin can bulk-import users" but no goal covers the import endpoint — only export is tested.

---

## Multi-repo integrity

### 10. Repo tag missing
**Check:** Every leaf task has exactly one repo tag: `[backend]`, `[frontend]`, `[deploy]`, or `[specs]`. A task without a tag is ambiguous. A task with two tags must be split.
**How to verify:** Scan every task ID line. Confirm exactly one repo tag in brackets appears. Flag any task with zero or two+ tags.
**FAIL example:** `T2.3: Add validation and update form component` — no repo tag. Is this backend or frontend?

### 11. Cross-repo task
**Check:** A leaf task that requires code changes in more than one repo must be split into separate tasks linked by dependency.
**How to verify:** For each leaf task, read the "Build" description. If it mentions files or changes in two different repos (e.g., a Python file and a TypeScript file), flag it.
**FAIL example:** `T3.1 [backend]: Add /api/export endpoint and update ExportButton.tsx to call it.` — this touches backend and frontend. Split into `T3.1 [backend]: Add /api/export endpoint` and `T3.2 [frontend]: Wire ExportButton to /api/export` with T3.2 depending on T3.1.

### 12. Cross-repo dependency not declared
**Check:** If a task in one repo consumes an artifact produced by a task in another repo, the dependency must be explicit.
**How to verify:** For each `[frontend]` task, check if its "Build" references a new API endpoint, type, or contract — if so, confirm it depends on the `[backend]` task that creates it. For each `[backend]` task, check if it assumes a Keycloak role, APISIX route, or infra config — if so, confirm it depends on the `[deploy]` task that provisions it. For each `[deploy]` task, check if it references env vars or secrets that another task creates.
**FAIL example:** `T2.1 [frontend]: Call GET /api/roles/summary` has `Depends on: None`, but that endpoint is created by `T1.3 [backend]`. Should be `Depends on: T1.3 [backend]`.

### 13. Repo-blocked parallelism
**Check:** If all "Ready now" tasks target the same repo, verify that no task could reasonably be split to unblock work in another repo.
**How to verify:** Look at the "Ready now" list. If every entry is `[backend]` (or all `[frontend]`, etc.), scan the plan for tasks in other repos that are blocked only by same-repo dependencies. Ask: could any blocking task be split so part of it finishes earlier, unblocking cross-repo work?
**FAIL example:** Ready now: T1.1 [backend], T1.2 [backend], T1.3 [backend]. Meanwhile T2.1 [frontend] depends on T1.3. But T1.3 is "create endpoint + add auth + write tests" — the endpoint alone could be a separate task, unblocking T2.1 while auth and tests continue in parallel.
