# PLAN — Phase 1d: Topic Content Upload

> Written: 2026-04-17
> Phase baseline:
> <!-- plan-baseline: backend:6dc7595ecb84dd21834ad33aa6c06332cf812504 frontend:82a69f1d5bff9bba94167375ea27aeb0d0f75698 deploy:239f96842d478a2978651a2671d591368218f42d -->

## Problem Statement

Platform admins can create topic-content entries via `POST /api/topic-contents/` but cannot edit or delete them. The frontend has no UI to list, add, edit, or delete content items within a topic. Phase 1d closes this gap: add `PATCH /api/topic-contents/{id}` and `DELETE /api/topic-contents/{id}` to the backend, and build the Topic Content Management section in the admin boards page.

**Binary file upload (multipart/form-data) is OUT OF SCOPE.** Admin supplies URLs (video) or relative filenames (PDF) as plain text strings; actual binary upload deferred to a later phase.

## Scope

### In scope
- Backend: `TopicContentUpdate` schema, `update_platform_content` / `delete_platform_content` abstract + infra repo methods, service methods, `PATCH` + `DELETE` route handlers, platform-oracle protection
- Frontend: `TopicContent` / `CreateTopicContentInput` / `UpdateTopicContentInput` types, API functions, `use-topic-contents` hook, `ContentItemRow` component, `AddContentModal` (shared create/edit), `DeleteContentDialog`, extend `TopicRow` to show content section
- 100% test coverage maintained in both repos

### Out of scope
- Binary file upload (multipart/form-data)
- `content_type` field is **immutable** — not patchable after creation
- `question` and `question_answer` content types hidden from admin UI for now
- Issue 2 (Categories sidenav), Issues 3/6 (version display)

## Architecture decisions

### Oracle protection
Same pattern as `topic.py` / `topic_repository.py`: returns `404` for both "record not found" AND "record not platform-owned" — indistinguishable to caller, preventing enumeration attacks. The infra repo implements this by joining `topic_contents → topics` and filtering `WHERE topic_contents.id = :id AND topics.owner_type = 'platform'`.

### Update field policy
`PATCH /api/topic-contents/{id}` accepts: `title`, `order`, `description`, `url`, `text`. `content_type` is immutable — changing content type after creation is prohibited. All accepted fields are optional (partial update semantics).

### Frontend content type display
Only `video`, `pdf`, `text` content types are shown in the admin UI. Icons: 🎬 video, 📄 pdf, 📝 text.

---

## Backend tasks

> A1 and A2 are independent — work in parallel. A3 requires A1 + A2. A4 requires A3. A5 requires A4. A6 is test coverage — write alongside each task.

### A1 — `TopicContentUpdate` schema (`src/schemas/topic_content.py`)

Add a new Pydantic model:

```python
class TopicContentUpdate(BaseModel):
    title: str | None = None
    order: int | None = None
    description: str | None = None
    url: str | None = None
    text: str | None = None
```

No `content_type` — immutable after creation.

### A2 — Abstract repo new methods (`src/domain/repositories/topic_content_repository.py`)

Add two abstract methods to the existing abstract repo class:

```python
@abstractmethod
def update_platform_content(self, content_id: uuid.UUID, data: dict) -> TopicContent | None: ...

@abstractmethod
def delete_platform_content(self, content_id: uuid.UUID) -> bool: ...
```

`data` is the dict of non-None fields extracted from `TopicContentUpdate`. Returns `None` / `False` for both "not found" and "not platform-owned" cases.

### A3 — Infra repo implementations (`src/infrastructure/repositories/topic_content_repository.py`)

Implement `update_platform_content` and `delete_platform_content`:

- **Ownership check**: query `topic_contents` joined to `topics` where `topic_contents.c.id == content_id AND topics.c.owner_type == 'platform'`. Join condition: `topic_contents.topic_id = topics.id`.
- **update**: if row found, execute `UPDATE topic_contents SET ... WHERE id = :id`; return mapped domain object. If not found, return `None`.
- **delete**: if row found, execute `DELETE FROM topic_contents WHERE id = :id`; return `True`. If not found, return `False`.

Do **not** use `admin_visibility_clause` (which operates on a single table). Write the JOIN condition inline to check the parent `topics.owner_type`.

### A4 — Service methods (`src/domain/services/topic_content_service.py`)

Add:

```python
def update_platform_content(self, content_id: uuid.UUID, data: TopicContentUpdate) -> TopicContent | None:
    update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_dict:
        return self.repository.get_by_id(content_id)  # no-op; return current
    return self.repository.update_platform_content(content_id, update_dict)

def delete_platform_content(self, content_id: uuid.UUID) -> bool:
    return self.repository.delete_platform_content(content_id)
```

### A5 — Route handlers (`src/api/routes/topic_content.py`)

Add two new route handlers after the existing `POST`:

```
PATCH /api/topic-contents/{content_id}
  - Role:    admin only (X-Current-Role: admin, validated via existing admin dependency)
  - CSRF:    required (X-CSRF-Token)
  - Body:    TopicContentUpdate
  - Returns: TopicContentRead (200) on success, 404 if not found / not platform-owned

DELETE /api/topic-contents/{content_id}
  - Role:    admin only
  - CSRF:    required
  - Returns: 204 on success, 404 if not found / not platform-owned
```

Follow the exact decorator/dependency pattern of the existing topic-content `POST` handler.

### A6 — Tests

Cover all new code paths (maintain 100% coverage):
- `PATCH` happy path: full update, partial update (some fields only), no-op update (empty body)
- `PATCH` non-platform topic_content → 404
- `PATCH` non-existent content_id → 404
- `PATCH` without `X-Current-Role: admin` → 403
- `PATCH` without `X-CSRF-Token` → 403
- `DELETE` happy path → 204
- `DELETE` non-platform topic_content → 404
- `DELETE` non-existent content_id → 404
- `DELETE` without admin role → 403
- Unit tests: `update_platform_content` on infra repo
- Unit tests: `delete_platform_content` on infra repo
- Unit tests: service methods delegating to repo

---

## Frontend tasks

> B1 and B2 are independent — start in parallel.
> B3 requires B1 + B2.
> B4, B5, B6 are independent of each other — work in parallel after B3.
> B7 requires B4 + B5 + B6.
> B8 is test coverage — write alongside each task.

### B1 — Types (`src/features/admin/types/admin.types.ts`)

Add:

```typescript
export type ContentType = 'video' | 'pdf' | 'text' | 'question' | 'question_answer';

export interface TopicContent {
  id: string;
  topic_id: string;
  content_type: ContentType;
  title: string;
  url: string | null;
  text: string | null;
  order: number;
  description: string | null;
}

export interface CreateTopicContentInput {
  topic_id: string;
  content_type: ContentType;
  title: string;
  url?: string;
  text?: string;
  order: number;
  description?: string;
}

export interface UpdateTopicContentInput {
  title?: string;
  order?: number;
  description?: string;
  url?: string;
  text?: string;
}
```

### B2 — API functions (`src/features/admin/api/admin-api.ts`)

Add four functions following existing patterns (`buildApiHeaders`, `fetchWithCSRFRetry`, `credentials: 'include'`):

```typescript
getTopicContents(topicId: string, csrfToken: string): Promise<TopicContent[]>
// GET /api/topic-contents/{topicId}

createTopicContent(input: CreateTopicContentInput, csrfToken: string, refreshCSRF): Promise<TopicContent>
// POST /api/topic-contents/ — fetchWithCSRFRetry

updateTopicContent(contentId: string, input: UpdateTopicContentInput, csrfToken: string, refreshCSRF): Promise<TopicContent>
// PATCH /api/topic-contents/{contentId} — fetchWithCSRFRetry

deleteTopicContent(contentId: string, csrfToken: string, refreshCSRF): Promise<void>
// DELETE /api/topic-contents/{contentId} — fetchWithCSRFRetry; expects 204
```

### B3 — Hook (`src/features/admin/hooks/use-topic-contents.ts`)

New hook file — follow the pattern of `use-topics.ts`:

- `useTopicContents(topicId: string | null)` — query; key `["admin", "topic-contents", topicId]`; disabled when `topicId` is null
- `useCreateTopicContent()` — mutation; on success invalidates `["admin", "topic-contents", input.topic_id]`
- `useUpdateTopicContent()` — mutation; on success invalidates `["admin", "topic-contents"]`
- `useDeleteTopicContent()` — mutation; on success invalidates `["admin", "topic-contents"]`

### B4 — `ContentItemRow` component

New files: `src/features/admin/components/content-item-row.tsx` + `content-item-row.module.css`

Props: `item: TopicContent`, `onEdit: (item: TopicContent) => void`, `onDelete: (item: TopicContent) => void`

Renders: type icon (🎬/📄/📝), title, optional description (truncated), order badge, edit button, delete button.

### B5 — `AddContentModal` (shared create/edit)

New files: `src/features/admin/components/add-content-modal.tsx` + `add-content-modal.module.css`

- Native `<dialog>` element (SonarQube requirement — no div modal)
- Props: `mode: 'create' | 'edit'`, `topicId: string`, `initialValues?: TopicContent`, `onSuccess: () => void`, `onClose: () => void`
- Content type selector: dropdown with `video`, `pdf`, `text` only; **disabled** in edit mode (immutable)
- URL field: shown when `content_type` is `video` or `pdf`
- Text area: shown when `content_type` is `text`
- Title, order (number input), description (optional) always visible
- Submit button shows loading spinner during mutation; errors shown inline

### B6 — `DeleteContentDialog`

New file: `src/features/admin/components/delete-content-dialog.tsx`

- Native `<dialog>` confirmation
- Props: `item: TopicContent | null`, `onClose: () => void`
- Text: "Delete '[title]'? This cannot be undone."
- Cancel + "Confirm Delete" (danger/red style) buttons; loading state on confirm

### B7 — Extend `TopicRow` (`src/features/admin/components/topic-row.tsx`)

Extend to show a content management section beneath the existing topic header:

- Call `useTopicContents(topic.id)` inside the component
- Content section shows below the topic header when topic is selected/expanded
- Section: "Content" label + "Add Content" button (admin accent blue), list of `ContentItemRow`s sorted by `order`, empty state "No content yet — add some."
- State: `addContentOpen: boolean`, `editingContent: TopicContent | null`, `deletingContent: TopicContent | null`
- Wire: "Add Content" → `addContentOpen = true`; edit callback → `editingContent`; delete callback → `deletingContent`
- Render `AddContentModal` (create when `addContentOpen`, edit when `editingContent`) and `DeleteContentDialog` (when `deletingContent`)

### B8 — Tests

Maintain 100% coverage:
- `ContentItemRow`: renders type icon, title; edit/delete callbacks fire with correct item
- `AddContentModal` create mode: type selector enabled, URL field shown for video/pdf, textarea for text; submit calls `createTopicContent`
- `AddContentModal` edit mode: pre-fills from `initialValues`; type selector disabled; submit calls `updateTopicContent`
- `DeleteContentDialog`: cancel closes; confirm calls `deleteTopicContent` + shows loading
- `TopicRow` with content: section renders `ContentItemRow`s; "Add Content" opens modal; edit/delete open correct modal/dialog
- `useTopicContents`: fetch disabled when null, mutation invalidates cache

---

## Backlog (deferred from Phase 1d)

| Item | Priority | Notes |
|---|---|---|
| Issue 2 — Move "Categories" from avatar menu to sidenav | Medium | No backend changes; frontend sidenav + dropdown only |
| Issue 3 — Version display on nodes ("NCERT v2.4") | Low | Requires new `version` column on `categories` + migration |
| Issue 6 (partial) — Version badge on board cards | Low | Same `version` column dependency as Issue 3 |
| Binary file upload (multipart) | Medium | Full binary upload to server; deferred until URL-based flow is stable |

---

## Implementation notes

- **Visual authority:** Open `target/prototypes/haisir_admin_flow.html` in a browser. SA-boards section in `target/requirements/ui-mapping/ui_parent_institution_admin.md` is the secondary reference.
- **Backend pattern reference:** `src/api/routes/topic.py` (platform-protected PATCH/DELETE), `src/infrastructure/repositories/topic_repository.py` (oracle protection JOIN)
- **Frontend pattern reference:** `src/features/admin/components/add-board-modal.tsx` (native `<dialog>` modal), `src/features/admin/hooks/use-topics.ts` (hook pattern)
- **CSRF:** All mutations require `X-CSRF-Token`. Use `fetchWithCSRFRetry` for automatic retry.
- **Role header:** `X-Current-Role: admin` on PATCH and DELETE. Missing header → 400.
- **Oracle protection:** Backend 404 = "not found OR not platform-owned". Frontend treats all 404s as "gone" and removes from list.
- **`content_type` immutability:** Enforce in backend (not in update schema) and frontend (disabled selector in edit mode).
- **100% test coverage** is enforced in both repos — new code must not lower coverage.

<!-- plan-baseline: backend:6dc7595ecb84dd21834ad33aa6c06332cf812504 frontend:82a69f1d5bff9bba94167375ea27aeb0d0f75698 deploy:239f96842d478a2978651a2671d591368218f42d -->
