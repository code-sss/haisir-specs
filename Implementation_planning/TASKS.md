# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:aa24252 frontend:816194d deploy:861705b (2026-07-26)

## G1 [backend]: Parent-owned content exposes live indexing status

### G1.1 [backend]: List endpoint carries per-item indexing status
- [x] T1.1.1 [backend]: Transient indexing fields on TopicContent domain model (2026-07-26)
- [x] T1.1.2 [backend]: LEFT JOIN rag_indexing_outbox into get_owner_content_by_topic (2026-07-26)
- [x] T1.1.3 [backend]: Expose indexing fields on TopicContentRead schema (2026-07-26)
- [x] **G1.1: List endpoint carries per-item indexing status** — integration test (2026-07-26, satisfied by T1.1.2/T1.1.3 unit tests)

### G1.2 [backend]: Owner-scoped, cooldown-guarded manual retry
- [x] T1.2.1 [backend]: Single-row outbox read method on ExtractionJobRepository (2026-07-26)
- [x] T1.2.2 [backend]: IndexingRetryCooldownError domain exception (2026-07-26)
- [x] T1.2.3 [backend]: TopicContentService.retry_indexing() (2026-07-26)
- [x] T1.2.4 [backend]: POST /topic-contents/{content_id}/retry-indexing route (depends on T1.2.3, T1.1.3) (2026-07-26)
- [x] **G1.2: Owner-scoped, cooldown-guarded manual retry** — integration test (2026-07-26, satisfied by T1.2.4's TestRetryIndexingRoute class)
- [ ] **G1: Parent-owned content exposes live indexing status** — end-to-end test (blocked: G1 goal test is T3.1's lifecycle test, still pending)

## G2 [frontend]: Parent UI surfaces indexing pills and manual retry

### G2.1 [frontend]: Status pill rendering per content item
- [ ] T2.1.1 [frontend]: Extend TopicContent schemas with indexing fields (depends on T1.1.3 [backend])
- [ ] T2.1.2 [frontend]: IndexingStatusPill component in ContentItemRow (depends on T2.1.1)
- [ ] **G2.1: Status pill rendering per content item** — integration test

### G2.2 [frontend]: Retry action + polling cadence
- [ ] T2.2.1 [frontend]: retryParentIndexing API call + adapter method (depends on T1.2.4 [backend])
- [ ] T2.2.2 [frontend]: Retry mutation wired through useContentManagement + button (depends on T2.2.1, T2.1.2)
- [ ] T2.2.3 [frontend]: 2s/10s/60s content-list polling cadence (depends on T2.1.1)
- [ ] **G2.2: Retry action + polling cadence** — integration test
- [ ] **G2: Parent UI surfaces indexing pills and manual retry** — end-to-end test (manual walkthrough)

## G3: Cross-repo acceptance
- [ ] T3.1 [backend]: End-to-end lifecycle test — pending -> failed -> retry -> pending, 404, 429 (depends on T1.1.2, T1.1.3, T1.2.4)
- [ ] **G3: Cross-repo acceptance** — acceptance test

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T3.1 [backend]: End-to-end lifecycle test — pending -> failed -> retry -> pending, 404, 429 (deps satisfied: T1.1.2, T1.1.3, T1.2.4)
- T2.1.1 [frontend]: Extend TopicContent schemas with indexing fields (deps satisfied: T1.1.3 [backend])
- T2.2.1 [frontend]: retryParentIndexing API call + adapter method (deps satisfied: T1.2.4 [backend])
