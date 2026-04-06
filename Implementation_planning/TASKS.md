# TASKS — Phase 1c: Admin Topics Management

> Generated from PLAN.md on 2026-04-06.
> Implementers: check off tasks as done. Add blockers to the Blocked section.
> Read `PLAN.md` for full step-by-step detail on each task.

---

## Ready now — Backend (`haisir-backend`)

> All Phase A tasks are unblocked. Work them in order A1 → A8.

- [ ] **A1** — `src/schemas/topic.py`: add `status: str = "live"` to `TopicRead`; add `TopicUpdate` schema with `title?`, `order?`, `status?: Literal["draft", "live"]`
- [ ] **A2** — `src/domain/repositories/topic_repository.py`: add abstract signatures for `update_platform_topic` + `delete_platform_topic`
- [ ] **A3** — `src/infrastructure/repositories/topic_repository.py`: implement `update_platform_topic` (oracle-protected SELECT → partial UPDATE) + `delete_platform_topic` (cascade `topic_contents` → `topics`)
- [ ] **A4** — `src/domain/services/topic_service.py`: add `update_platform_topic` + `delete_platform_topic` service methods with no-op guard and empty-title validation
- [ ] **A5** — `src/api/routes/topic.py`: add `PATCH /{topic_id}` (admin + CSRF, 200/404/422) + `DELETE /{topic_id}` (admin + CSRF, 204/404)
- [ ] **A6** — `src/infrastructure/repositories/topic_repository.py`: fix BR-STU-003 — add `self.table.c.status == "live"` to `get_by_course_path_node_visible` WHERE clause
- [ ] **A7a** — `src/infrastructure/repositories/course_path_node_repository.py`: add `has_live_topics_in_subtree(node_id: UUID) -> bool` (recursive CTE)
- [ ] **A7b** — `src/api/routes/course_path_node.py`: call `has_live_topics_in_subtree` before `has_active_exam_sessions_in_subtree` in DELETE handler; return 409 `"Cannot delete: this node has live topics."` if true
- [ ] **A8** — Tests: PATCH/DELETE topic routes + BR-STU-003 regression + node-delete live-topic 409; maintain 100% coverage

---

## Ready now — Frontend (`haisir-frontend`)

> B1, B2, B3 are independent — start in parallel.
> B4 depends on B1 + B2 + B3.
> B5–B9 depend on B4.
> B10 can run alongside B5–B9.

- [ ] **B1** — `src/features/admin/types/admin.types.ts`: add `Topic`, `CreateTopicInput`, `UpdateTopicInput`, `AddTopicFormSchema`, `AddTopicFormValues`
- [ ] **B2** — `src/features/admin/api/admin-api.ts`: add `getTopicsForNode`, `createTopic`, `updateTopic`, `deleteTopic`
- [ ] **B3** — NEW `src/features/admin/hooks/use-topics.ts`: `useTopics(nodeId: string | null)` hook (pattern: mirror `use-node-tree.ts`)
- [ ] **B4** — `src/features/admin/components/node-detail-panel.tsx`: replace "coming in Phase 1c" stub with `<TopicPanel />`; add `csrfToken` + `refreshCSRF` props to `NodeDetailPanelProps`; thread from `AdminBoardsPage`
- [ ] **B5** — NEW `src/features/admin/components/topic-panel.tsx` + `topic-panel.module.css`: loading / error / empty / list states; "Add Topic" button
- [ ] **B6** — NEW `src/features/admin/components/topic-row.tsx` + `topic-row.module.css`: inline rename + status badge + toggle button + delete icon
- [ ] **B7** — NEW `src/features/admin/components/rename-topic-inline.tsx` + `.module.css`: click-to-edit inline rename (pattern: copy `rename-node-inline.tsx`)
- [ ] **B8** — NEW `src/features/admin/components/add-topic-modal.tsx`: `useFocusTrap`, `title` field, submit → `createTopic` (pattern: mirror `AddNodeModal`)
- [ ] **B9** — NEW `src/features/admin/components/delete-topic-dialog.tsx`: confirm + 409 reason display (pattern: mirror `DeleteNodeDialog`)
- [ ] **B10** — Tests for B2 (API), B3 (hook), B5–B9 (components); maintain 100% coverage

---

## Verification checklist

Run these before marking the phase complete.

### Backend
- [ ] `pytest` exits 0 with 100% coverage
- [ ] `PATCH /api/topics/{id}` returns 404 for non-platform-owned topic (oracle protection)
- [ ] `PATCH /api/topics/{id}` returns 422 for empty `title`
- [ ] `DELETE /api/topics/{id}` cascades `topic_contents` correctly and returns 204
- [ ] Student `GET /api/topics/{node_id}` does NOT return `status = 'draft'` topics (BR-STU-003)
- [ ] `DELETE /api/course-path-nodes/{id}` returns 409 with `"Cannot delete: this node has live topics."` when applicable

### Frontend
- [ ] `pnpm test` exits 0 with 100% coverage
- [ ] Selecting a node in `/admin/boards` renders the topic list (or empty state)
- [ ] "Add Topic" modal creates a topic; it appears in the list immediately
- [ ] Inline rename updates the topic title; empty input does not submit
- [ ] Status toggle changes the badge colour and calls `PATCH /api/topics/{id}`
- [ ] Delete removes the topic; 409 response shows reason message
- [ ] Node-delete shows "Cannot delete: this node has live topics." when backend returns 409 with that detail

---

## Blocked

> Nothing blocked at time of writing.

---

## Notes for implementers

- Full step-by-step detail: `Implementation_planning/PLAN.md`
- Critical rules (CSRF, role header, oracle protection, imperative mapping): `CLAUDE.md`
- Visual spec: open `target/prototypes/haisir_admin_flow.html` in a browser — it is the authoritative layout reference
- UI colour tokens: `--draft-grey: #6B7280`, `--home-study-green: #1D9E75` (from `target/requirements/ui-mapping/ui_parent_institution_admin.md`)
- Backend pattern files: `src/api/routes/course_path_node.py` (PATCH/DELETE handlers)
- Frontend pattern files: `rename-node-inline.tsx`, `delete-node-dialog.tsx`, `add-node-modal.tsx`, `use-node-tree.ts`
