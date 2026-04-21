# TASKS — Phase 1d: Topic Content Upload

> Generated from PLAN.md on 2026-04-17.
> Commits: haisir-backend `dd7da7f`, haisir-frontend `82a69f1`

---

## Ready now — Backend (`haisir-backend`)

> A1 and A2 are independent — work in parallel. A3 depends on A1 + A2. A4 depends on A3. A5 depends on A4.

- [x] **A1** — `src/schemas/topic_content.py`: add `TopicContentUpdate(BaseModel)` with all-optional fields: `title`, `order`, `description`, `url`, `text`. No `content_type` — immutable after creation. (2026-04-21)
- [x] **A2** — `src/domain/repositories/topic_content_repository.py`: add two abstract methods: `update_platform_content(content_id, data: dict) -> TopicContent | None` and `delete_platform_content(content_id) -> bool`. (2026-04-21)
- [x] **A3** — `src/infrastructure/repositories/topic_content_repository.py`: implement the two abstract methods. Use a JOIN to the `topics` table (`topic_contents.topic_id = topics.id AND topics.owner_type = 'platform'`) for platform-oracle protection. Return `None`/`False` for both "not found" and "non-platform" cases (indistinguishable to caller). (2026-04-21)
- [x] **A4** — `src/domain/services/topic_content_service.py`: add `update_platform_content(content_id, data: TopicContentUpdate) -> TopicContent | None` and `delete_platform_content(content_id) -> bool`. Service strips None fields before delegating to repo. (2026-04-21)
- [x] **A5** — `src/api/routes/topic_content.py`: add `PATCH /api/topic-contents/{content_id}` (body: `TopicContentUpdate`, response: `TopicContentRead` 200 / 404) and `DELETE /api/topic-contents/{content_id}` (204 / 404). Both admin-only (`X-Current-Role: admin`), CSRF required. Follow existing POST handler pattern. (2026-04-21)
- [x] **A6** — Tests: PATCH/DELETE happy paths; 404 for non-platform + non-existent; 403 for non-admin + missing CSRF. Unit tests for infra repo + service. Maintain 100% coverage. (2026-04-21)

---

## Ready now — Frontend (`haisir-frontend`)

> B1 and B2 are independent — start in parallel.
> B3 depends on B1 + B2.
> B4, B5, B6 are independent of each other — work in parallel after B3.
> B7 depends on B4 + B5 + B6.
> B8 is test coverage — write alongside each task.

- [ ] **B1** — `src/features/admin/types/admin.types.ts`: add `ContentType` union (`'video' | 'pdf' | 'text' | 'question' | 'question_answer'`), `TopicContent` interface, `CreateTopicContentInput`, `UpdateTopicContentInput`.
- [ ] **B2** — `src/features/admin/api/admin-api.ts`: add `getTopicContents(topicId, csrfToken)`, `createTopicContent(input, csrfToken, refreshCSRF)`, `updateTopicContent(contentId, input, csrfToken, refreshCSRF)`, `deleteTopicContent(contentId, csrfToken, refreshCSRF)`. Mutations use `fetchWithCSRFRetry`.
- [ ] **B3** — New `src/features/admin/hooks/use-topic-contents.ts`: `useTopicContents(topicId)` (query, disabled when null; key `["admin", "topic-contents", topicId]`), `useCreateTopicContent()`, `useUpdateTopicContent()`, `useDeleteTopicContent()` (mutations; all invalidate `["admin", "topic-contents", ...]`).
- [ ] **B4** — New `src/features/admin/components/content-item-row.tsx` + `content-item-row.module.css`: renders one content item — type icon (🎬/📄/📝), title, optional description (truncated), order badge, edit button, delete button.
- [ ] **B5** — New `src/features/admin/components/add-content-modal.tsx` + `add-content-modal.module.css`: native `<dialog>` modal; `mode: 'create' | 'edit'` + `initialValues?: TopicContent`; content type selector shows `video`/`pdf`/`text` only, disabled in edit mode; URL field for video/pdf, textarea for text; loading spinner on submit.
- [ ] **B6** — New `src/features/admin/components/delete-content-dialog.tsx`: native `<dialog>` confirmation — "Delete '[title]'? This cannot be undone." Cancel + Confirm Delete (danger style); loading state on confirm.
- [ ] **B7** — `src/features/admin/components/topic-row.tsx`: extend to show content section below topic header. Section: "Content" label + "Add Content" button, `ContentItemRow` list sorted by `order`, empty state. Wire `AddContentModal` (create/edit modes) and `DeleteContentDialog` via local state.
- [ ] **B8** — Tests: `ContentItemRow` renders + callbacks; `AddContentModal` create/edit modes + submit; `DeleteContentDialog` cancel/confirm; `TopicRow` content section; `useTopicContents` hook. Maintain 100% coverage.

---

## Verification checklist

Run these before marking the phase complete.

### Backend
- [ ] `pytest` exits 0 with 100% coverage
- [ ] `POST /api/topic-contents/` still works (no regressions)
- [ ] `PATCH /api/topic-contents/{id}` with valid admin + CSRF → 200 with updated fields
- [ ] `PATCH /api/topic-contents/{id}` for non-platform topic → 404
- [ ] `PATCH /api/topic-contents/{id}` as non-admin → 403
- [ ] `DELETE /api/topic-contents/{id}` with valid admin + CSRF → 204
- [ ] `DELETE /api/topic-contents/{id}` for non-platform topic → 404
- [ ] `DELETE /api/topic-contents/{id}` as non-admin → 403

### Frontend
- [ ] `pnpm test` exits 0 with 100% coverage
- [ ] Admin boards page: topic row shows content section when expanded
- [ ] "No content yet — add some." empty state shown for topics with no content
- [ ] "Add Content" button opens `AddContentModal` in create mode
- [ ] Submit creates content item; item appears in list with correct icon
- [ ] Edit button opens `AddContentModal` in edit mode, pre-filled; content type disabled
- [ ] Delete button opens `DeleteContentDialog`; confirm removes item from list
- [ ] Content type icons correct: 🎬 video, 📄 pdf, 📝 text

---

## Blocked

> Nothing blocked at time of writing.

---

## Notes for implementers

- Full step-by-step detail: `Implementation_planning/PLAN.md`
- Critical rules (CSRF, role header, oracle protection, imperative mapping): `CLAUDE.md`
- Visual spec: open `target/prototypes/haisir_admin_flow.html` in a browser — SA-boards section is the authoritative layout reference
- Backend pattern files: `src/api/routes/topic.py` (platform-protected PATCH/DELETE), `src/infrastructure/repositories/topic_repository.py` (oracle JOIN pattern)
- Frontend pattern files: `src/features/admin/components/add-board-modal.tsx` (native `<dialog>` pattern), `src/features/admin/hooks/use-topics.ts` (hook pattern)
- **Binary file upload is OUT OF SCOPE** — admin provides URL/filename as plain text; actual binary upload deferred
- **`content_type` is immutable** — omit from `TopicContentUpdate`; disable selector in edit modal
