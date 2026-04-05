# Goal / Subgoal Node Template

## Template

```markdown
### G<N> — <Concern Name>
**Goal**: <What this concern achieves — one sentence, behavior-focused.>
**Goal test**: <E2E test that proves this concern works. Specific inputs -> expected outputs.>
**Repos**: <Which repos are involved — e.g., [backend] [frontend]>

---

#### G<N.M> — <Subgoal Name>
**Subgoal**: <What this subset of the concern achieves.>
**Subgoal test**: <Integration test. Specific scenario -> expected outcome.>
**Repos**: <Which repos are involved.>
```

## Rules

### Goals describe behaviors, not repos

Name goals for the concern they address:

- Correct: `G3 — Strict header validation`
- Wrong: `G3 — Backend auth changes`

The goal is the behavior. The repo is where the code happens to live.

### The Repos field is informational

The **Repos** field shows which repos are touched by the goal's child tasks. It is derived, not prescriptive — the concern dictates the grouping, not the repo layout.

- A goal that touches only `[backend]` is fine.
- A goal that touches `[backend]`, `[frontend]`, and `[deploy]` is also fine.
- Never split a single concern into two goals just because it spans repos.

### Goal tests can span repos

A goal-level E2E test might start at the frontend, hit the backend, and depend on deploy config. This is expected — goals represent cross-cutting concerns. Only leaf tasks are repo-scoped.

### Subgoals group related tasks within a concern

A subgoal collects tasks that must work together to satisfy part of the parent goal. Subgoals can also span repos.

## Example

```markdown
### G2 — Hybrid retrieval returns relevant chunks
**Goal**: Given a user query, the system retrieves the most relevant content chunks using combined vector and keyword search.
**Goal test**: POST /api/rag/query with "What is photosynthesis?" returns chunks from the biology source material, not unrelated content.
**Repos**: [backend] [deploy]

---

#### G2.1 — Vector similarity search
**Subgoal**: Embedding-based search returns chunks ordered by cosine similarity to the query.
**Subgoal test**: A query embedding matched against known stored embeddings returns the expected top-3 chunks.
**Repos**: [backend]

#### G2.2 — BM25 keyword search
**Subgoal**: Full-text search returns chunks matching query keywords, ranked by relevance.
**Subgoal test**: Query "mitochondria ATP" returns chunks containing those terms, ranked above chunks that mention neither.
**Repos**: [backend] [deploy]
```
