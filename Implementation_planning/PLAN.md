# PLAN — Phase 6: Parent Indexing Status & Retry

> Phase 5.6 closed out 2026-07-21 and archived to
> `archive/PLAN_Phase5.6-SecretsElimination_2026-07-16.md` /
> `archive/TASKS_Phase5.6-SecretsElimination_2026-07-16.md`. Phase 5.5 was already archived
> (`archive/PLAN_Phase5.5-SecretsOpenBao_2026-07-15.md`).

## Backlog candidates (carried forward from Phase 5, reconciled 2026-07-26)

Reconciled against live code/specs before scoping this cycle — two items below were stale
(already shipped) and one citation was wrong; corrected here and in `phases.md` /
`target/requirements/11_haitu_ai_layer.md` §7.

- ~~`/parent` route guard~~ — **done**, shipped Phase 5 G2 (`ParentRouteGuard`, live).
- Remaining role migration — `become-tutor` self-service (tutor is in scope; no `tutor_profiles`
  table exists yet, uncounted migration); `invite-role` + `/institution` route guard **blocked** —
  `target/requirements/06_institution_admin.md` states institution_admin is out of scope for this
  increment, and no `organizations` table exists to back BR-ROLE-002's org-scoping. Needs
  `/update-target-state` before this slice is plannable. (Also found, unrelated: `assign-role`'s
  `if user.roles: raise 409` blocks a user from ever holding both `student` + `parent`,
  contradicting BR-ROLE-005's own example — flagged for whoever next touches role assignment.)
- ~~External HTTP reranker for the stubbed Stage 3~~ — **done**, shipped 2026-07-08 as
  `TeiRerankClient` (fails open to passthrough). Remaining RAG ops backlog is ops-only: missing
  `HAITU__RERANK_BASE_URL` in `.env.template`, unverified whether the reranker VM is actually
  reachable in any environment, a stale README claiming it's still unwired; "bundled inference
  service in deploy" intent is undefined (today it's a standalone GPU VM, the opposite of
  "bundled") and needs clarification; hAITU Prometheus monitoring still blocked on Chainguard
  licensing (pay for tier / re-pin upstream images / switch to VictoriaMetrics — undecided).
- Per-child audience scoping of parent-created content — deliberately deferred 2026-07-02
  ("revisit if parents with multiple children at different grades complain"); no such complaint
  is on record and zero design exists. Not ready to plan.
- Parent-facing hAITU endpoints — corrected citation:
  `vision/requirements/08_haitu_ai_layer.md` §3.5–3.7 (was misfiled as `00_overview.md`). Blocked
  on two things: a product decision to reintroduce progress-monitoring UI into the target Parent
  persona (dropped when scoped from vision), and a mastery-tracking gap — `enrollment_topics` is
  FK'd to `student_enrollments` only, so exam attempts on parent-owned topics likely don't
  populate it.

**Chosen as this cycle's root goal:** Parent Indexing Status & Retry
(`target/requirements/05_parent.md` BR-PAR-020, `01_data_model.md` BR-DATA-023) — already fully
spec'd and implementation-ready, no open decisions, no missing data model.

---

## Root goal

Parents can see, per content item, whether it has been embedded into RAG (5 states sourced from
`rag_indexing_outbox.status`), and can manually retry a permanently-`failed` one — mirroring the
existing extraction-job status-pill UX one level down the pipeline.

## Goal tree

```
G1 [backend]: Parent-owned content exposes live indexing status
  G1.1 [backend]: List endpoint carries per-item indexing status
    T1.1.1 [backend]: Transient indexing fields on TopicContent domain model
    T1.1.2 [backend]: LEFT JOIN rag_indexing_outbox into get_owner_content_by_topic
    T1.1.3 [backend]: Expose indexing fields on TopicContentRead schema
    * G1.1 integration test
  G1.2 [backend]: Owner-scoped, cooldown-guarded manual retry
    T1.2.1 [backend]: Single-row outbox read method on ExtractionJobRepository
    T1.2.2 [backend]: IndexingRetryCooldownError domain exception
    T1.2.3 [backend]: TopicContentService.retry_indexing()
    T1.2.4 [backend]: POST /topic-contents/{content_id}/retry-indexing route
    * G1.2 integration test
  * G1 end-to-end test

G2 [frontend]: Parent UI surfaces indexing pills and manual retry
  G2.1 [frontend]: Status pill rendering per content item
    T2.1.1 [frontend]: Extend TopicContent schemas with indexing fields
    T2.1.2 [frontend]: IndexingStatusPill component in ContentItemRow
    * G2.1 integration test
  G2.2 [frontend]: Retry action + polling cadence
    T2.2.1 [frontend]: retryParentIndexing API call + adapter method
    T2.2.2 [frontend]: Retry mutation wired through useContentManagement + button
    T2.2.3 [frontend]: 2s/10s/60s content-list polling cadence
    * G2.2 integration test
  * G2 end-to-end test (manual walkthrough)

G3: Cross-repo acceptance
  T3.1 [backend]: End-to-end lifecycle test — pending -> failed -> retry -> pending, 404, 429
```

No `[deploy]` work — verified `common/routes/17-api-actions.json` (explicit-URI allowlist, no
parent-curriculum path) vs. `05-api-write.json` (`/api/*` wildcard, POST/PUT/PATCH) — the new
route falls through the wildcard exactly like the existing
`POST /api/parent/curriculum/extraction-jobs/{job_id}/retry` sibling does. No `[specs]` work — the
spec (BR-PAR-020, BR-DATA-023) already exists and needs no changes.

---

## G1 [backend] — Parent-owned content exposes live indexing status

**Goal test:** For a topic owned by parent A with one `text` content item whose
`rag_indexing_outbox` row has `status='failed', retry_count=3`,
`GET /api/parent/curriculum/topics/{topic_id}/content` returns that item with
`indexing_status="failed"` and `indexing_retry_count=3`;
`POST /api/parent/curriculum/topic-contents/{content_id}/retry-indexing` as parent A resets the
outbox row to `status='pending', retry_count=0`, and a subsequent `GET` reflects
`indexing_status="pending"`; the same `POST` as parent B (non-owner) returns 404. (Satisfied by
T3.1's full lifecycle test.)

### G1.1 [backend] — List endpoint carries per-item indexing status

**Subgoal test:** Given two content items under one topic — one `text` item with an outbox row
`status='processing', retry_count=1`, one `pdf` item with no outbox row — the repo method returns
both `TopicContent` objects with the `text` item carrying `indexing_status="processing"` /
`indexing_retry_count=1` and the `pdf` item carrying `indexing_status=None` /
`indexing_retry_count=0`. (Satisfied by T1.1.2's and T1.1.3's own tests.)

#### T1.1.1 [backend] — Transient indexing fields on TopicContent domain model
- **Build:** In `src/domain/models/topic_content.py`, add two transient fields to the
  `TopicContent` dataclass (after `provenance`, following its exact precedent — "not mapped to a
  DB column; populated by repo JOIN queries"): `indexing_status: str | None = None` and
  `indexing_retry_count: int = 0`.
- **Done when:** `TopicContent(id=..., topic_id=..., content_type=..., title=...)` constructs
  successfully with `indexing_status is None` and `indexing_retry_count == 0` by default.
- **Test:** `tests/unit/domain/test_models/test_topic_content.py::test_indexing_fields_default_to_none_and_zero`
  — asserts both defaults on a minimally-constructed instance.
- **Depends on:** none.

#### T1.1.2 [backend] — LEFT JOIN rag_indexing_outbox into get_owner_content_by_topic
- **Build:** In `src/infrastructure/repositories/topic_content_repository.py`, extend
  `get_owner_content_by_topic` (line ~245): add an outer join against `rag_indexing_outbox` on
  `content_id`, select `status`/`retry_count` alongside the existing `extraction_job_audit` join
  used for provenance, and extend (or add a sibling to) the existing `_attach_provenance` static
  helper (line ~30) to set `indexing_status`/`indexing_retry_count` from the joined columns.
  Import `rag_indexing_outbox` from `infrastructure.models.extraction_job` (already imported
  there for `extraction_job_audit`).
- **Done when:** `get_owner_content_by_topic(topic_id, owner_id)` returns a `text` content item
  with `indexing_status == "processing"` when its outbox row has `status='processing'`, and
  `indexing_status is None` for a `pdf` item with no outbox row.
- **Test:** `tests/unit/infrastructure/test_topic_content_repository.py` — new test seeding one
  content item with an outbox row and one without, asserting both outcomes.
- **Depends on:** T1.1.1 [backend].

#### T1.1.3 [backend] — Expose indexing fields on TopicContentRead schema
- **Build:** In `src/schemas/topic_content.py`, add `indexing_status: str | None = None` and
  `indexing_retry_count: int = 0` to `TopicContentRead` (line ~140) —
  `ConfigDict(from_attributes=True)` already on the class means these populate automatically from
  the domain object's new transient fields.
- **Done when:** `TopicContentRead.model_validate(obj_with_indexing_status_processing).indexing_status == "processing"`.
- **Test:** `tests/unit/schemas/test_topic_content.py` — new test round-tripping a domain object
  with `indexing_status="failed", indexing_retry_count=3` through `TopicContentRead.model_validate(...)`.
- **Depends on:** T1.1.1 [backend].

### G1.2 [backend] — Owner-scoped, cooldown-guarded manual retry

**Subgoal test:** For a parent-owned `text` content item with an outbox row
`status='failed', updated_at=now()-60s`, `POST .../retry-indexing` returns 200 and the row becomes
`status='pending', retry_count=0`; calling it again immediately returns 429; calling it for a
`content_id` owned by a different parent returns 404. (Satisfied by T1.2.4's `TestRetryIndexingRoute` class.)

#### T1.2.1 [backend] — Single-row outbox read method on ExtractionJobRepository
- **Build:** In `src/domain/repositories/extraction_job_repository.py`, add an abstract method
  `async def get_outbox(self, content_id: UUID) -> RagIndexingOutbox | None`. In
  `src/infrastructure/repositories/extraction_job_repository.py`, implement it next to
  `get_outbox_batch` (line ~563): `select(RagIndexingOutbox).where(rag_indexing_outbox.c.content_id == content_id)`,
  return `result.scalars().first()`.
- **Done when:** `get_outbox(content_id)` returns the matching row for an existing `content_id`,
  and `None` when no row exists.
- **Test:** `tests/unit/infrastructure/test_extraction_job_repository.py` — new tests for the
  present and absent cases.
- **Depends on:** none.

#### T1.2.2 [backend] — IndexingRetryCooldownError domain exception
- **Build:** In `src/domain/exceptions.py`, add `class IndexingRetryCooldownError(Exception)`
  following the `ExtractionQuotaExceededError` pattern (docstring: "HTTP mapping: 429."),
  constructor taking `content_id: UUID` and storing it as `self.content_id`.
- **Done when:** `IndexingRetryCooldownError(uuid4()).content_id` returns the UUID passed in.
- **Test:** `tests/unit/domain/test_exceptions.py` — new test asserting the stored `content_id`.
- **Depends on:** none.

#### T1.2.3 [backend] — TopicContentService.retry_indexing()
- **Build:** In `src/domain/services/topic_content_service.py`, add
  `async def retry_indexing(self, content_id: UUID, owner_id: str) -> RagIndexingOutbox | None`.
  Steps: (1) `content = await self.repo.get_own_content_by_id(content_id, owner_id)`; return
  `None` if not found (404 oracle, matching every other `*_own_content` method's convention).
  (2) `outbox = await self._outbox.get_outbox(content_id)` (guard `self._outbox is not None`,
  matching the existing idiom used at lines 134/209/291/324). (3) If `outbox is not None` and
  `datetime.now(UTC) - outbox.updated_at < timedelta(seconds=30)`, raise
  `IndexingRetryCooldownError(content_id)`. (4) Call `await self._outbox.enqueue_content(content_id)`
  (BR-DATA-023: reuse the existing upsert-with-reset, no new SQL). (5) Return
  `await self._outbox.get_outbox(content_id)`.
- **Done when:** resets a failed/stale row to `pending`/0 for owned content; returns `None` for
  non-owned content; raises `IndexingRetryCooldownError` inside the 30s cooldown window.
- **Test:** `tests/unit/domain/test_services/test_topic_content_service.py` — three cases:
  `test_retry_indexing_resets_stale_row` (asserts `enqueue_content` called),
  `test_retry_indexing_returns_none_for_non_owned`,
  `test_retry_indexing_raises_cooldown_error_within_window`.
- **Depends on:** T1.2.1 [backend], T1.2.2 [backend].

#### T1.2.4 [backend] — POST /topic-contents/{content_id}/retry-indexing route
- **Build:** In `src/api/routes/parent_curriculum.py`, add
  `@router.post("/topic-contents/{content_id}/retry-indexing", status_code=status.HTTP_200_OK)`
  mirroring `update_own_topic_content`'s dependency shape (line ~549):
  `Depends(get_content_service)`, `Depends(require_parent())`, `Depends(validate_csrf)`. Call
  `service.retry_indexing(content_id, user.sub)`; catch `IndexingRetryCooldownError` ->
  `HTTPException(429, ...)` (per-route try/except, matching this codebase's existing exception
  mapping convention, e.g. `parent_extraction.py`'s `ExtractionQuotaExceededError` handling); if
  the result is `None` -> `HTTPException(404, ...)`; else return a new `IndexingRetryRead`
  response schema (`content_id`, `status`, `retry_count`) added to `src/schemas/topic_content.py`.
- **Done when:** 200 with the reset status for an owned, non-cooldown `content_id`; 404 for
  wrong-owner/nonexistent; 429 inside the cooldown window.
- **Test:** `tests/unit/routes/test_parent_curriculum.py` — new `TestRetryIndexingRoute` class
  covering all three outcomes.
- **Depends on:** T1.2.3 [backend], T1.1.3 [backend] (shares `schemas/topic_content.py`).

---

## G2 [frontend] — Parent UI surfaces indexing pills and manual retry

**Goal test:** Rendering `ParentTopicContentPage` for a topic with one content item at
`indexing_status="failed", indexing_retry_count=3` shows "✕ Indexing failed" and a Retry button;
clicking Retry calls `POST .../retry-indexing`, and after the mocked response flips the item to
`indexing_status="pending"` on refetch, the pill updates to "⏱ Queued for indexing" and the Retry
button disappears. (Satisfied by manual walkthrough at sign-off, plus the component/hook tests below.)

### G2.1 [frontend] — Status pill rendering per content item

**Subgoal test:** `ContentItemRow` with `indexing_status="retry", indexing_retry_count=1` shows
"Retrying (1/3)"; `indexing_status="done"` or `null` renders no pill. (Satisfied by T2.1.2's test.)

#### T2.1.1 [frontend] — Extend TopicContent schemas with indexing fields
- **Build:** Add `indexing_status: z.enum(["pending","processing","retry","failed","done"]).nullish()`
  and `indexing_retry_count: z.number().int().nullish()` to **both**
  `TopicContentSchema` (`src/features/content-management/types/content.types.ts`, line ~8) **and**
  `ParentTopicContentSchema` (`src/features/parent/domain/parent-schemas.ts`, line ~21). Both are
  required: `parent-content-adapter.ts` parses the API response with `ParentTopicContentSchema`
  and then casts it `as Promise<TopicContent[]>` (a `ponytail:`-annotated structural cast) — zod
  strips unknown keys by default, so if only `TopicContentSchema` gained the fields they'd be
  silently dropped at the parse step despite type-checking clean.
- **Done when:** `TopicContentSchema.parse(fixtureWithIndexingFields)` succeeds and carries both
  fields; the same fixture parses successfully through `ParentTopicContentSchema`.
- **Test:** schema-level parse test for both schemas asserting the fields survive.
- **Depends on:** T1.1.3 [backend] (field names/values must match).

#### T2.1.2 [frontend] — IndexingStatusPill component in ContentItemRow
- **Build:** Add `src/features/content-management/components/indexing-status-pill.tsx` exporting
  `IndexingStatusPill({ status, retryCount })` — returns `null` for `status == null || status === "done"`,
  otherwise renders the spec-table copy per status (`"⏱ Queued for indexing"`, `"🌀 Indexing"`,
  `` `🔁 Retrying (${retryCount}/3)` ``, `"✕ Indexing failed"`) with a status-keyed CSS class.
  Render it inside `ContentItemRow` (`src/features/content-management/components/content-item-row.tsx`,
  next to the existing provenance badge, line ~98).
- **Done when:** an item with `indexing_status="processing"` renders "🌀 Indexing"; an item with
  `indexing_status=null` renders no pill.
- **Test:** `content-item-row.test.tsx` — new case asserting the pill text for a `processing`
  fixture and absence for a `null`-status fixture.
- **Depends on:** T2.1.1 [frontend].

### G2.2 [frontend] — Retry action + polling cadence

**Subgoal test:** Clicking Retry on a `failed` item invalidates the content query so the list
refetches (satisfied by T2.2.2's test); `computeIndexingPollInterval` returns `2000` for an active
item and `false` after 60s of full idle (satisfied by T2.2.3's test).

#### T2.2.1 [frontend] — retryParentIndexing API call + adapter method
- **Build:** In `src/features/parent/api/parent-curriculum-api.ts`, add
  `retryParentIndexing(contentId, csrfToken, refreshCSRF)` — a no-body POST to
  `.../topic-contents/{contentId}/retry-indexing` with **no** `Idempotency-Key` header (unlike
  `retryParentExtractionJob` at line ~538, which takes `(jobId, idempotencyKey, csrfToken, refreshCSRF)`
  and sends one — this call is a state transition against an existing cooldown-guarded row, not a
  job-creation call needing client-side dedup, so the key is deliberately omitted). Throw a new
  `ParentIndexingCooldownError` on `res.status === 429`, mirroring `ParentDeleteBlockedError`'s
  class shape (line ~37: extends `Error`, sets `.name`). Add `retryIndexing(contentId, csrfToken, refreshCSRF): Promise<void>`
  to the `ContentApiAdapter` interface (`src/features/content-management/api/content-adapter.ts`)
  and implement it in `parent-content-adapter.ts` delegating to the new function.
- **Done when:** calling `parentContentAdapter.retryIndexing(id, token, refresh)` issues the POST
  and resolves on 200; rejects with `ParentIndexingCooldownError` on 429.
- **Test:** `parent-curriculum-api.test.ts` — new test mocking `fetch` to return 429 and asserting
  the thrown error type.
- **Depends on:** T1.2.4 [backend].

#### T2.2.2 [frontend] — Retry mutation wired through useContentManagement + button
- **Build:** In `src/features/content-management/hooks/use-content-management.ts`, add a
  `retryIndexingMutation` mirroring `updateMutation`'s shape (line ~180): `mutationFn` calls
  `adapter.retryIndexing`, `onSuccess` invalidates the content query key (`cKey`). Expose
  `retryIndexing: (contentId: string) => void` on the hook's result. In `content-item-row.tsx`,
  render a Retry button next to `IndexingStatusPill` when `item.indexing_status === "failed"`,
  wired via a new `onRetryIndexing` prop plumbed the same way `onRename` is.
- **Done when:** clicking Retry calls `adapter.retryIndexing` with that item's id; success
  invalidates the content query so the list refetches.
- **Test:** `content-item-row.test.tsx` — new test clicking Retry on a `failed` fixture and
  asserting `onRetryIndexing` was called with that item.
- **Depends on:** T2.2.1 [frontend], T2.1.2 [frontend].

#### T2.2.3 [frontend] — 2s/10s/60s content-list polling cadence
- **Build:** In `use-content-management.ts`, add a pure helper
  `computeIndexingPollInterval(contents, lastActiveSeenMs): number | false` co-located with
  `computeRefetchInterval` (line ~37): `2000` if any item is `pending`/`processing`/`retry`;
  `10000` if idle but `Date.now() - lastActiveSeenMs < 60_000`; else `false`. Track
  `lastActiveSeenMs` in a ref updated whenever the active check is true, mirroring
  `lastActiveSeenRef` for jobs (line ~208). Wire it as the `refetchInterval` option on the
  existing content `useQuery` (line ~161), replacing its current no-poll,
  `staleTime: 30_000`-only configuration.
- **Done when:** returns `2000` with an active item present, `10000` while idle-but-recent, and
  `false` after 60s of continuous idle.
- **Test:** `use-content-management.test.tsx` — new `describe("computeIndexingPollInterval")`
  block mirroring the existing `computeRefetchInterval` tests (line ~165), covering all three cases.
- **Depends on:** T2.1.1 [frontend].

---

## G3 — Cross-repo acceptance

**Goal test:** Seed a `text` content item owned by parent A with
`rag_indexing_outbox.status='failed', retry_count=3, updated_at=now()-60s`. `GET .../content` as
parent A shows `indexing_status="failed", indexing_retry_count=3`. `POST .../retry-indexing` as
parent A returns 200 and resets the row; a subsequent `GET` shows `indexing_status="pending", indexing_retry_count=0`.
The same `POST` as parent B returns 404. A second immediate `POST` as parent A returns 429.

#### T3.1 [backend] — End-to-end lifecycle test: pending -> failed -> retry -> pending, 404, 429
- **Build:** In `tests/unit/routes/test_parent_curriculum.py`, add
  `test_retry_indexing_full_lifecycle` using the fixtures from `TestListTopicContentRoute` /
  `TestRetryIndexingRoute`: seed the topic/content/outbox row, `GET` (assert `failed`), `POST`
  retry (assert 200, re-`GET` and assert `pending`), `POST` as a different owner (assert 404),
  `POST` again immediately as the true owner (assert 429).
- **Done when:** the single test method passes, exercising all four HTTP outcomes in one lifecycle.
- **Test:** `uv run pytest tests/unit/routes/test_parent_curriculum.py::test_retry_indexing_full_lifecycle -v`
- **Depends on:** T1.1.2 [backend], T1.1.3 [backend], T1.2.4 [backend].

---

## Summary

| Metric | Count |
|---|---|
| Goals | 2 (+ 1 cross-repo acceptance) |
| Subgoals | 4 |
| Tasks (backend) | 8 |
| Tasks (frontend) | 5 |
| Tasks (deploy) | 0 |
| Tasks (specs) | 0 |
| Cross-repo dependencies | 2 (T2.1.1 -> T1.1.3, T2.2.1 -> T1.2.4) |

Challenger review: 1 round run against the draft goal tree (methodology + full checklist).
Findings were mechanical/textual only (a wrong method-name reference, an inaccurate "mirrors X"
description, thin test-case wording) — all fixed inline above. No structural issues (no cycles, no
orphan tasks, no missing repo tags, no undeclared cross-repo dependencies), so a second round was
not run. Zero `<!-- UNRESOLVED -->` items.

<!-- plan-baseline: backend:aa24252ff5291b97acb59d851f59fd27015d2178 frontend:816194d35c8bdddb804f67b9fded7d5f9d6aa897 deploy:861705bc29164ba73746297ad563ab1d6259e4de -->
