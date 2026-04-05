# Recursive Goal Decomposition — Methodology (Multi-Repo)

## The core question

Decompose by answering one question recursively:

> "What does this system need to DO, and can that be broken into smaller things that each have
> their own definition of done?"

## Rule 1 — Start with the single root goal

Not "what repos do I need to change?" but "what does the system achieve for a user?"

The root goal is the reason the feature or phase exists. Everything else is a means to that end. Repos are implementation details — they appear only at the leaf-task level.

## Rule 2 — Decompose by concern, not by repo or file

Split the root goal into independent concerns — things that can fail or succeed independently. Each concern becomes a GOAL node.

A goal like "Authentication works end-to-end" is correct. A goal like "Backend auth changes" is wrong — it's organized by repo, not by behavior.

Sizing heuristic — a goal is wrong-sized if:
- Failing it breaks everything else -> too big, split further.
- It can't be tested on its own -> too small, merge with its parent.

## Rule 3 — Recurse until you hit an atomic task

Keep splitting goals into subgoals until each leaf task has:
1. Exactly one behavior
2. One clear "Done when" criterion
3. One focused test assertion
4. Exactly one target repo

## Rule 4 — Every level has its own test

| Level    | Test type        | What it proves                              |
|----------|------------------|---------------------------------------------|
| TASK     | Unit test        | One assertion, one behavior, one repo       |
| SUBGOAL  | Integration test | All child tasks work together               |
| GOAL     | End-to-end test  | The concern works as a whole (may span repos) |
| ROOT     | Acceptance test  | The system achieves its purpose for a user  |

Subgoal and goal tests often span repos — an integration test might verify that the frontend correctly handles a response shaped by the backend. That is expected. Only leaf tasks are repo-scoped.

## Rule 5 — Dependencies, not phases

Tasks are ordered by what they depend on, not by artificial phase groupings. Declare dependencies explicitly, including the repo tag for cross-repo references:

```
Depends on: T1.2 [backend], T3.1 [deploy]
```

A task in `[frontend]` that needs an API endpoint from `[backend]` declares that dependency. This makes cross-repo sequencing visible without requiring a separate coordination document.

## Rule 6 — One task, one repo

Every leaf task targets exactly one repo: `[backend]`, `[frontend]`, `[deploy]`, or `[specs]`.

- A task that requires changes in two repos **must** be split into two tasks with an explicit cross-repo dependency.
- Goals and subgoals can span repos — they describe concerns, not code changes. But leaf tasks cannot.
- The repo tag goes after the task ID in all references.

Example of a correct split:

```
##### T2.1.1 [backend] — Expose embedding endpoint
- Depends on: T7.4 [deploy] (DB schema with pgvector)

##### T2.1.2 [frontend] — Call embedding endpoint from upload form
- Depends on: T2.1.1 [backend]
```

Example of an incorrect task (spans two repos):

```
##### T2.1.1 — Add embedding endpoint and wire up frontend
```

This must be split. If you find yourself writing "and" in a task name that bridges two repos, it is two tasks.

## Naming conventions

Tasks use a dotted numeric ID followed by the repo tag:

```
##### T2.1.1 [backend] — Vector cosine search
- Depends on: T1.2 [backend] (Embedding), T7.4 [deploy] (DB schema)
```

Goals and subgoals carry a **Repos** field listing which repos their children touch, but the goal itself is named for the concern:

```
### G2 — Hybrid retrieval
**Repos**: [backend] [deploy]
```

## Summary

1. Root goal = user-visible outcome.
2. Decompose by concern, not by repo.
3. Recurse until atomic.
4. Every level has a test.
5. Order by dependency.
6. Every leaf task targets one repo.
