# Task Node Template

## Template

```markdown
##### T<N.M.K> [repo] — <Task Name>
- **Build**: <What to implement — specific enough to act on without ambiguity.>
- **Done when**: <One falsifiable criterion.>
- **Test**: <One assertion.>
- **Depends on**: <Explicit task/goal IDs with repo tags, or "None".>
```

## Rules

### Each task targets exactly ONE repo

The repo tag appears immediately after the task ID: `T1.1.1 [backend]`.

Valid repo tags: `[backend]`, `[frontend]`, `[deploy]`, `[specs]`.

If a change spans two repos, split it into two tasks linked by a dependency. There are no exceptions.

### Cross-repo dependencies include repo tags

When a task depends on work in another repo, the dependency reference includes the repo tag:

```
Depends on: T1.2 [backend], T3.1 [deploy]
```

Same-repo dependencies may omit the tag if unambiguous, but including it is always acceptable.

### "Done when" must be falsifiable

The criterion must be something a reviewer can check with a yes/no answer. Avoid vague language.

- Correct: `Done when: POST /api/rag/ingest returns 201 and the chunk row exists in rag_chunks.`
- Wrong: `Done when: Ingestion works properly.`

### "Test" is one assertion

Each task has exactly one test assertion. If you need two assertions, you likely have two tasks.

- Correct: `Test: assert response.status_code == 201`
- Wrong: `Test: assert status is 201 and body contains chunk_id and database row exists`

### "Build" is specific and actionable

State what to implement, not how to think about it. Reference concrete functions, endpoints, tables, or components.

- Correct: `Build: Add hybrid_search() in retrieval.py — run vector cosine and BM25 queries concurrently, fuse with RRF.`
- Wrong: `Build: Implement the search functionality.`

### Dependencies point to task or goal IDs

Use `Depends on: None` for tasks with no prerequisites. Otherwise list specific IDs:

```
Depends on: T2.1.1 [backend], G1 (schema exists)
```

## Example

```markdown
##### T2.1.1 [backend] — Vector cosine search function
- **Build**: Add `vector_search()` in `retrieval.py` — query `rag_chunks` by cosine similarity against a query embedding, return top-k rows with scores.
- **Done when**: `vector_search(embedding, k=5)` returns 5 rows ordered by descending cosine similarity.
- **Test**: `assert len(results) == 5 and results[0].score >= results[1].score`
- **Depends on**: T1.2 [backend] (BGE-M3 embedding util), T7.4 [deploy] (pgvector extension enabled)

##### T2.1.2 [backend] — BM25 keyword search function
- **Build**: Add `keyword_search()` in `retrieval.py` — query `rag_chunks` using `ts_rank` against the `tsv` column, return top-k rows with scores.
- **Done when**: `keyword_search("mitochondria ATP", k=5)` returns rows containing those terms.
- **Test**: `assert all("mitochondria" in r.content or "ATP" in r.content for r in results)`
- **Depends on**: T7.4 [deploy] (tsvector column exists)

##### T4.3.1 [frontend] — Render source cards below answer
- **Build**: Add `SourceCard` component in `components/SourceCard.tsx` — display title, snippet, and link for each source returned in the SSE done event.
- **Done when**: After a query completes, source cards appear below the streamed answer with correct titles.
- **Test**: `expect(screen.getByText(mockSource.title)).toBeInTheDocument()`
- **Depends on**: T4.2.1 [frontend] (SSE stream parsing), T2.3.1 [backend] (sources in done event)
```
