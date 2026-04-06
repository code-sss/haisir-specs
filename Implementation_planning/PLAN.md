# PLAN — Phase 1c: Admin Topics Management

> Written: 2026-04-06
> Phase baseline:
> <!-- plan-baseline: backend:d8713adb5055991a383eb13fe2113411eacddd8f frontend:c7084e581e6609239b951c876a0c051f6a200043 deploy:b814471ac9a44b3566abe8a47a46957e2f195ec9 -->

## Goal

Build the topics panel on the right side of the Admin Board Content Manager (`/admin/boards`). When a node is selected, the admin sees the list of platform topics for that node and can create, rename, delete, and toggle topics between `draft` and `live`. Two spec-compliance gaps found during planning are fixed in this phase because they become observable (and testable) once status toggling exists.

---

## Context

### What already exists (Phase 1b / 1c-pre)
- `GET /api/topics/{node_id}` — lists topics for a node (visibility-filtered)
- `POST /api/topics` — creates a topic (admin only)
- `Topic` domain model with `status: str = "live"` field and `TopicService.create()`
- `TopicRepository` with three `get_by_course_path_node_*` methods
- `admin_visibility_clause` / `student_visibility_clause` in `infrastructure/visibility.py`
- Frontend: `NodeDetailPanel` stub with placeholder "Topics panel coming in Phase 1c."
- Frontend: `adminApi` in `admin-api.ts` + `admin.types.ts` + `useNodeTree` hook as patterns to follow

### What is missing (Phase 1c scope)
- `TopicRead` does not expose `status` (field exists in domain model but missing from Pydantic schema)
- No `PATCH /api/topics/{id}` or `DELETE /api/topics/{id}` endpoints
- Student visibility query does not filter by `status = 'live'` (BR-STU-003 gap)
- Node delete does not block when subtree has live topics (spec: "Cannot delete: this node has live topics.")
- Frontend: no topic list, no CRUD UI in the admin panel

---

## Phase A — Backend (`haisir-backend`)

All steps are sequential within Phase A. Phase A can proceed independently of Phase B.

### A1 — Expose `status` in `TopicRead`; add `TopicUpdate` schema
**File:** `src/schemas/topic.py`
- Add `status: str = "live"` to `TopicRead`
- Add `TopicUpdate(BaseModel)` with optional fields:
  - `title: str | None = None`
  - `order: int | None = None`
  - `status: Literal["draft", "live"] | None = None`

### A2 — Abstract repository: add update + delete signatures
**File:** `src/domain/repositories/topic_repository.py`
- Add `@abstractmethod async def update_platform_topic(self, topic_id: UUID, title: str | None, order: int | None, status: str | None) -> Topic | None`
- Add `@abstractmethod async def delete_platform_topic(self, topic_id: UUID) -> bool`

### A3 — Infrastructure repository: implement update + delete
**File:** `src/infrastructure/repositories/topic_repository.py`

`update_platform_topic`:
- SELECT topic with `admin_visibility_clause` first (oracle protection — returns `None` if not found OR non-platform-owned; do not distinguish the two cases)
- Apply only the non-None fields to the fetched topic object
- `session.add(topic)` + `await session.commit()` + `await session.refresh(topic)`
- Return updated topic

`delete_platform_topic`:
- SELECT with `admin_visibility_clause` first; return `False` if not found
- DELETE all `topic_contents` rows for this topic (FK constraint)
- DELETE the `topics` row
- Commit; return `True`
- Pattern: see `delete_subtree` in `course_path_node_repository.py` for the cascade approach

### A4 — Service: add update + delete methods
**File:** `src/domain/services/topic_service.py`

`update_platform_topic(topic_id, title, order, status) -> Topic | None`:
- Guard: if `title is None and order is None and status is None`, return `None` (route will treat as 404, consistent with node PATCH no-op pattern)
- Validate: if `title is not None and title.strip() == ""`, raise `ValueError("title cannot be empty")`
- Delegate to `self.repo.update_platform_topic(...)`

`delete_platform_topic(topic_id) -> bool`:
- Delegate to `self.repo.delete_platform_topic(topic_id)`

### A5 — Routes: `PATCH /api/topics/{topic_id}` + `DELETE /api/topics/{topic_id}`
**File:** `src/api/routes/topic.py`

`PATCH /{topic_id}` (admin only + CSRF):
- Request body: `TopicUpdate`
- `422` if `title == ""` (caught from `ValueError` in service)
- `404` if service returns `None` (not found, non-platform-owned, or all-None no-op)
- `200` + `TopicRead` on success
- Pattern: identical to `PATCH /api/course-path-nodes/{id}` in `course_path_node.py`

`DELETE /{topic_id}` (admin only + CSRF):
- `404` if service returns `False`
- `204 No Content` on success
- Pattern: identical to `DELETE /api/course-path-nodes/{id}`

### A6 — Fix BR-STU-003: student topic query must filter `status = 'live'`
**File:** `src/infrastructure/repositories/topic_repository.py`

In `get_by_course_path_node_visible`: add `self.table.c.status == "live"` to the WHERE clause.

Do NOT add the status filter to:
- `get_by_course_path_node_platform_only` — admin must see both draft and live
- `get_by_course_path_node` — fallback/instructor must see both

### A7 — Fix node-delete: block if subtree has live topics
**File:** `src/infrastructure/repositories/course_path_node_repository.py`

Add `has_live_topics_in_subtree(node_id: UUID) -> bool`:
```python
stmt = text("""
    WITH RECURSIVE subtree AS (
        SELECT id FROM course_path_nodes WHERE id = :node_id
        UNION ALL
        SELECT c.id FROM course_path_nodes c
        INNER JOIN subtree s ON c.parent_id = s.id
    )
    SELECT EXISTS (
        SELECT 1 FROM topics t
        JOIN subtree s ON t.course_path_node_id = s.id
        WHERE t.status = 'live'
    )
""")
result = await self.session.execute(stmt, {"node_id": node_id})
return bool(result.scalar())
```

**File:** `src/api/routes/course_path_node.py`

In the DELETE handler, before the existing `has_active_exam_sessions_in_subtree` check, add:
```python
if await service.repo.has_live_topics_in_subtree(node_id):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Cannot delete: this node has live topics.",
    )
```

> Note: `has_live_topics_in_subtree` is a repository method, not a service method — call it via `service.repo` (same pattern used in the existing DELETE handler for `has_active_exam_sessions_in_subtree`).

### A8 — Tests
Pattern file: `tests/unit/routes/test_course_path_node.py`

Required new/updated test cases:
- `PATCH /api/topics/{id}` → 200 updated topic
- `PATCH /api/topics/{id}` with non-platform-owned topic → 404
- `PATCH /api/topics/{id}` with `title = ""` → 422
- `PATCH /api/topics/{id}` with all-None body → 404 (no-op treated as not found)
- `DELETE /api/topics/{id}` → 204
- `DELETE /api/topics/{id}` with non-platform-owned topic → 404
- BR-STU-003 regression: student `GET /api/topics/{node_id}` does NOT return topics with `status = 'draft'`
- Node-delete with subtree containing live topic → 409 `"Cannot delete: this node has live topics."`
- Maintain 100% coverage

---

## Phase B — Frontend (`haisir-frontend`)

B1–B3 are independent (run in parallel). B4 depends on B1 + B2 + B3. B5–B9 depend on B4. B10 runs alongside B5–B9.

### B1 — Types
**File:** `src/features/admin/types/admin.types.ts`

Add:
```typescript
export interface Topic {
  id: string;
  title: string;
  course_path_node_id: string;
  order: number | null;
  status: "draft" | "live";
  owner_type: "platform" | "parent";
}

export interface CreateTopicInput {
  title: string;
  course_path_node_id: string;
  order?: number;
}

export interface UpdateTopicInput {
  title?: string;
  order?: number;
  status?: "draft" | "live";
}

export const AddTopicFormSchema = z.object({
  title: z.string().min(1, "Title is required").max(200),
});
export type AddTopicFormValues = z.infer<typeof AddTopicFormSchema>;
```

### B2 — API functions
**File:** `src/features/admin/api/admin-api.ts`

Add to the `adminApi` object:

```typescript
/** GET /api/topics/{nodeId} */
getTopicsForNode: async (csrfToken: string | null, nodeId: string): Promise<Topic[]> => {
  const res = await fetch(`${BACKEND_URL}/api/topics/${nodeId}`, {
    method: "GET",
    headers: buildApiHeaders(csrfToken),
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to fetch topics: ${res.status}`);
  return (await res.json()) as Topic[];
},

/** POST /api/topics */
createTopic: async (csrfToken, refreshCSRF, input: CreateTopicInput): Promise<Topic> => {
  const res = await fetchWithCSRFRetry(
    `${BACKEND_URL}/api/topics/`,
    { method: "POST", headers: buildApiHeaders(csrfToken), credentials: "include", body: JSON.stringify(input) },
    refreshCSRF,
  );
  if (!res.ok) throw new Error(`Failed to create topic: ${res.status}`);
  return (await res.json()) as Topic;
},

/** PATCH /api/topics/{id} */
updateTopic: async (csrfToken, refreshCSRF, id: string, input: UpdateTopicInput): Promise<Topic> => {
  const res = await fetchWithCSRFRetry(
    `${BACKEND_URL}/api/topics/${id}`,
    { method: "PATCH", headers: buildApiHeaders(csrfToken), credentials: "include", body: JSON.stringify(input) },
    refreshCSRF,
  );
  if (!res.ok) throw new Error(`Failed to update topic: ${res.status}`);
  return (await res.json()) as Topic;
},

/** DELETE /api/topics/{id} */
deleteTopic: async (csrfToken, refreshCSRF, id: string): Promise<void> => {
  const res = await fetchWithCSRFRetry(
    `${BACKEND_URL}/api/topics/${id}`,
    { method: "DELETE", headers: buildApiHeaders(csrfToken), credentials: "include" },
    refreshCSRF,
  );
  if (res.status === 409) {
    const body = (await res.json()) as { detail?: string };
    throw new AdminDeleteBlockedError(body.detail ?? "Delete blocked");
  }
  if (!res.ok) throw new Error(`Failed to delete topic: ${res.status}`);
},
```

### B3 — `useTopics` hook
**New file:** `src/features/admin/hooks/use-topics.ts`

Pattern: mirror `use-node-tree.ts` exactly.

```typescript
// Signature:
export function useTopics(nodeId: string | null): {
  topics: Topic[];
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}
```

- Fetches via `adminApi.getTopicsForNode(csrfToken, nodeId)` when `nodeId` is not null
- Clears topics (empty array) when `nodeId` changes to null
- Refetches when `nodeId` changes or `refetch()` is called
- Uses `useCSRF()` for the token

### B4 — Replace stub in `NodeDetailPanel`
**File:** `src/features/admin/components/node-detail-panel.tsx`

Current placeholder to replace:
```tsx
<p className={styles.topicsEmpty}>Topics panel coming in Phase 1c.</p>
```

Replace with:
```tsx
<TopicPanel
  selectedNode={selectedNode}
  csrfToken={csrfToken}
  refreshCSRF={refreshCSRF}
/>
```

Thread `csrfToken` and `refreshCSRF` props into `NodeDetailPanel` (they are already available in `AdminBoardsPage` from the existing `useCSRF()` call — pass them down).

Update `NodeDetailPanelProps` interface accordingly.

### B5 — `TopicPanel` component
**New files:** `src/features/admin/components/topic-panel.tsx` + `topic-panel.module.css`

Props:
```typescript
interface TopicPanelProps {
  readonly selectedNode: BoardNode;
  readonly csrfToken: string | null;
  readonly refreshCSRF: () => Promise<string | null>;
}
```

States:
- `isLoading` → spinner (same pattern as NodeTree loading state)
- `isError` → error message
- empty `topics` → "No topics yet — add one."
- populated → list of `<TopicRow />` components + "Add Topic" button at bottom

On `createTopic` / `updateTopic` / `deleteTopic` success: call `refetch()` to reload the list.

### B6 — `TopicRow` component
**New files:** `src/features/admin/components/topic-row.tsx` + `topic-row.module.css`

Props:
```typescript
interface TopicRowProps {
  readonly topic: Topic;
  readonly csrfToken: string | null;
  readonly refreshCSRF: () => Promise<string | null>;
  readonly onChanged: () => void;
}
```

Layout (left → right):
1. `<RenameTopicInline>` — shows topic title; click to edit
2. Status badge pill:
   - `draft`: background `#6B7280` (token `--draft-grey`)
   - `live`: background `#1D9E75` (token `--home-study-green`)
3. Toggle button:
   - When `draft`: "Publish" → calls `adminApi.updateTopic(..., { status: "live" })` then `onChanged()`
   - When `live`: "Unpublish" → calls `adminApi.updateTopic(..., { status: "draft" })` then `onChanged()`
4. Delete icon button → opens `<DeleteTopicDialog>`

### B7 — `RenameTopicInline` component
**New files:** `src/features/admin/components/rename-topic-inline.tsx` + `rename-topic-inline.module.css`

Pattern: **identical** to `rename-node-inline.tsx`. Copy and adapt:
- On click: activates `<input>` pre-filled with current `topic.title`
- On blur or Enter: submit if value changed and non-empty → `adminApi.updateTopic(csrfToken, refreshCSRF, topic.id, { title: value })`; then call `onRenamed()`
- On Escape: cancel without saving
- Do not submit if value is empty string

### B8 — `AddTopicModal` component
**New file:** `src/features/admin/components/add-topic-modal.tsx`

Pattern: **mirror `AddNodeModal`** exactly.
- Uses `useFocusTrap`
- Single field: `title` (required, validated via `AddTopicFormSchema`)
- On submit: `adminApi.createTopic(csrfToken, refreshCSRF, { title, course_path_node_id: selectedNode.id })`
- On success: close modal + call `onTopicAdded()`
- On error: show inline error message

### B9 — `DeleteTopicDialog` component
**New file:** `src/features/admin/components/delete-topic-dialog.tsx`

Pattern: **mirror `DeleteNodeDialog`** exactly.
- Shows topic title in confirmation text
- On confirm: `adminApi.deleteTopic(csrfToken, refreshCSRF, topic.id)`
- On `AdminDeleteBlockedError` (409): display the error message (e.g. future: "has active exam sessions")
- On success: close dialog + call `onDeleted()`
- Uses `useFocusTrap`

### B10 — Tests
Pattern: `tests/unit/features/admin/`

Required coverage:
- `admin-api.ts` new functions: `getTopicsForNode`, `createTopic`, `updateTopic`, `deleteTopic`
- `use-topics.ts`: loading, error, populated, refetch, nodeId-change-clears
- `topic-panel.tsx`: loading state, error state, empty state, list render
- `topic-row.tsx`: status badge colour, toggle calls updateTopic, delete opens dialog
- `rename-topic-inline.tsx`: edit/save/cancel/empty-string-guard
- `add-topic-modal.tsx`: validation, submit, error
- `delete-topic-dialog.tsx`: confirm, 409 message, success
- Maintain 100% coverage

---

## Critical implementation rules (from `CLAUDE.md`)

- **APISIX injects the JWT** — no Bearer token on the client.
- **`X-Current-Role: admin`** is sent automatically via `buildApiHeaders(csrfToken)` which reads from localStorage.
- **CSRF on every mutation** — use `fetchWithCSRFRetry` for all PATCH / DELETE / POST. Never use raw `fetch` for mutations.
- **Oracle protection** — `PATCH /api/topics/{id}` and `DELETE /api/topics/{id}` return `404` for both "not found" and "non-platform-owned". Do not distinguish these cases in the UI.
- **Schema is sacred** — `topics.status` already exists as a VARCHAR column. No migration needed.
- **SQLAlchemy imperative mapping** — domain models are plain dataclasses. No `Base` subclassing in `domain/models/`.
- **No Redux, no Axios** — raw `fetch` with `credentials: "include"`, custom hooks with `useState`/`useEffect` only.
- **DDD folder structure** — no business logic in route files. Logic belongs in the service layer.

---

## Out of scope (Phase 1d)

- Topic content upload (PDF / video / text slots per topic)
- "Upload Content" button on `TopicRow` — may stub as a disabled button
- "Publish Board" modal on `/admin/boards`
- Dashboard stats row on `/admin` (Live topics / Draft topics count cards)
