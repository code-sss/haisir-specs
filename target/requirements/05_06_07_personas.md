# Parent & Platform Admin Personas

> **Target state scope:** Parent (content creator, private curriculum for linked child) and Platform Admin (platform board content manager). Institution Admin is out of scope for this increment. See `vision/requirements/05_06_07_personas.md` for the full multi-role vision.

---

# Parent Persona

## Overview

Parents are content creators — they build or adopt a private curriculum for their linked child. Their content is never public or marketplace-facing. Parents are fully responsible for the quality of content and exams they create; no instructor oversight in this increment.

## Screens

| Screen ID | Name | Route |
|---|---|---|
| P-home | Parent Dashboard | `/parent` |
| P-curriculum | Curriculum Builder | `/parent/curriculum` |
| P-topic | Topic Content Manager | `/parent/curriculum/:node_id/topics/:topic_id` |
| P-exam | Exam Creator | `/parent/exams` |
| P-results | Child Results | `/parent/children/:child_idp_sub/results` |
| P-link | Link Child | `/parent/link-child` |

---

## P-home — Parent Dashboard

- **Child selector strip** at the top: shows all linked children (name + avatar). Clicking switches the active child context.
- If no child linked: prominent "Link your child" card with navigation to P-link.

### Tabs (per active child)
1. **Overview** — summary cards: topics uploaded, exams created, last exam score, weak topics count.
2. **Curriculum** — shortcut to P-curriculum filtered for this child's view.
3. **Results** — shortcut to P-results for this child.

---

## P-curriculum — Curriculum Builder

Two entry paths:
- **Adopt from Platform** — imports a platform board subtree (deep copy) as a starting point.
- **Build from scratch** — creates a new root node manually.

### Left panel — Node tree
- Hierarchical tree of the parent's own `course_path_nodes` (`owner_type = 'parent'`, `owner_id = parent.idp_sub`).
- Controls: "Add Node" (child of selected node), "Rename", "Delete" (cascade delete; only if no live exam sessions under this subtree).
- "Adopt from Platform" button at the top opens the Adopt modal.

### Right panel — Node detail / Topic list
- When a leaf node is selected: list of topics with `status` badge (Draft / Live), "Add Topic", "Edit", "Delete".
- Topic row actions: "Upload Content", "Create Exam".
- "Publish" toggle per topic: `draft` → `live` (visible to linked child) or `live` → `draft` (hidden).

### Adopt modal (Import from Platform)
- Browseable tree of platform `course_path_nodes`.
- Parent selects a subtree root (e.g., a Grade node).
- "Adopt" button → `POST /api/parent/curriculum/adopt` with `source_node_id`.
- On success: deep copy of the selected subtree + attached topics is created under the parent's curriculum with `owner_type = 'parent'`, topics at `status = 'draft'`.
- Idempotent: if the same subtree root was already adopted, returns 409 Conflict. Parent is shown a message: "You have already adopted this board."
- **What is cloned:** `course_path_nodes` subtree + `topics` rows only.
- **What is NOT cloned:** `topic_contents`, questions, `exam_templates`. Parent uploads their own content after adoption.

**Business rules:**
- BR-PAR-001: Parent can only read/write nodes where `owner_id = parent.idp_sub`.
- BR-PAR-002: Adopted subtree is an independent copy — platform updates to the original do not propagate.
- BR-PAR-003: Adopt is idempotent per subtree root — second adopt returns 409.
- BR-PAR-004: Delete node cascades to child nodes and topics. Not allowed if any topic has active (in-progress) exam sessions.
- BR-PAR-005: Topic `status = 'draft'` is not visible to the linked child. Set to `live` to make it visible.

---

## P-topic — Topic Content Manager

- Topic title (editable).
- Content slots: PDF upload, Video URL, Text (rich text or plain).
  - One item per type allowed (matches `topic_contents` constraint).
  - Upload status: uploading → processing → ready.
- "Save" saves the topic metadata; content items saved individually on upload/submit.

**Business rules:**
- BR-PAR-006: Parent can upload to their own topics only (`owner_id = parent.idp_sub`).
- BR-PAR-007: File uploads go through the same `StorageBackend` interface as platform content (local disk v1).

---

## P-exam — Exam Creator

- Lists all `exam_templates` where `owner_type = 'parent'` and `owner_id = parent.idp_sub`.
- "Create Exam" → modal with: title, linked node (optional), time limit, pass mark.
- Questions tab: add MCQ questions (stem + 4 options + correct answer) or paragraph questions.
- "Publish" toggle: draft → live (available for the linked child to take).

**Business rules:**
- BR-PAR-008: Parent can create, edit, and delete their own exam templates freely.
- BR-PAR-009: Published exams (`status = 'live'`) appear as "Take Exam" on the student's S-nav for this parent's content.
- BR-PAR-010: Deleting a published exam template is blocked if there are completed `exam_sessions` for it. Parent must archive instead.
- BR-PAR-011: No instructor review gate — parent is solely responsible for exam quality.

---

## P-results — Child Results

- Scope: `exam_sessions` where:
  - `user_id = child.idp_sub`
  - `exam_templates.owner_id = parent.idp_sub` (parent's own exams only)
  - Active `parent_child_links` record exists for this parent-child pair.
- Table: exam name, date taken, score, pass/fail.
- Clicking a row: per-question breakdown (student's answer, correct answer, points).

**Business rules:**
- BR-PAR-012: Parents do NOT see results for platform exams the child has taken.
- BR-PAR-013: Results access is revoked immediately if the `parent_child_links` record is revoked.

---

## P-link — Link Child

- Input field for the child's link code (`parent_link_codes.code`).
- "Link" button → `POST /api/parent/children/link` with `{ code }`.
- On success: child appears in the child selector strip on P-home.
- On error: "Invalid or expired code" message.

**Business rules:**
- BR-PAR-014: A link code can only be used once (consumed on first use; or the student can generate a new one).
- BR-PAR-015: A parent can be linked to multiple children.
- BR-PAR-016: Maximum 10 children per parent account — 422 if exceeded.

---

## Parent API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/parent/children` | List linked children |
| `POST` | `/api/parent/children/link` | Link a child using a link code |
| `DELETE` | `/api/parent/children/:child_idp_sub/link` | Revoke link to a child |
| `GET` | `/api/parent/curriculum/nodes` | List parent's curriculum root nodes |
| `GET` | `/api/parent/curriculum/nodes/:node_id` | Get node detail + children |
| `POST` | `/api/parent/curriculum/nodes` | Create a new node |
| `PATCH` | `/api/parent/curriculum/nodes/:node_id` | Rename a node |
| `DELETE` | `/api/parent/curriculum/nodes/:node_id` | Delete a node (cascade) |
| `POST` | `/api/parent/curriculum/adopt` | Adopt a platform subtree (clone) |
| `GET` | `/api/parent/curriculum/nodes/:node_id/topics` | List topics for a node |
| `POST` | `/api/parent/curriculum/nodes/:node_id/topics` | Create a topic |
| `PATCH` | `/api/parent/curriculum/topics/:topic_id` | Update topic (title, status) |
| `DELETE` | `/api/parent/curriculum/topics/:topic_id` | Delete a topic |
| `POST` | `/api/parent/curriculum/topics/:topic_id/content` | Upload content to a topic |
| `GET` | `/api/parent/exams` | List parent's exam templates |
| `POST` | `/api/parent/exams` | Create an exam template |
| `PATCH` | `/api/parent/exams/:exam_id` | Update exam template |
| `DELETE` | `/api/parent/exams/:exam_id` | Delete an exam template |
| `POST` | `/api/parent/exams/:exam_id/questions` | Add a question |
| `PATCH` | `/api/parent/exams/:exam_id/questions/:q_id` | Update a question |
| `DELETE` | `/api/parent/exams/:exam_id/questions/:q_id` | Delete a question |
| `GET` | `/api/parent/children/:child_idp_sub/exam-sessions` | Child's exam results (parent-owned only) |
| `GET` | `/api/parent/children/:child_idp_sub/exam-sessions/:session_id` | Per-question breakdown |

---

---

# Platform Admin Persona

## Overview

Platform Admin (`admin` role) manages the authoritative platform board content. Scoped exclusively to `owner_type = 'platform'` content. Cannot read or modify parent-owned content or any student/parent user data.

## Screens

| Screen ID | Name | Route |
|---|---|---|
| SA-dashboard | Admin Dashboard | `/admin` |
| SA-boards | Board Content Manager | `/admin/boards` |

---

## SA-dashboard — Admin Dashboard

- Summary stats: total platform nodes, total topics, total live topics, total published exam templates.
- Quick-access list of top-level board nodes (grade groups or curriculum roots).
- Navigation to SA-boards.

---

## SA-boards — Board Content Manager

### Board selector strip (top)
- Lists top-level platform `course_path_nodes` (root boards, e.g. NCERT, CBSE).
- "Add Board" button → creates a new root node with `owner_type = 'platform'`.

### Left panel — Node tree (for selected board)
- Full hierarchical tree of platform nodes under the selected board.
- Node type displayed inline (chip/badge). Reserved types (`grade`, `subject`) shown with a 🔒 indicator.
- Controls: "Add Child Node", "Rename", "Delete" (blocked if child has live topics or published exams).

### Right panel — Node detail
- Selected node: name, type, breadcrumb.
- **Topic list:** title, content type, status (`draft` / `live`), "Upload Content", "Edit", "Delete".
- "Add Topic" button.
- **Publish toggle per topic:** `draft` → `live` (visible to all students) or `live` → `draft`.
- **Publish Board modal:** preview of all draft changes, confirmation to publish.

**Business rules:**
- BR-ADM-001: Platform Admin can only write `owner_type = 'platform'` content.
- BR-ADM-002: Platform Admin cannot read or modify `owner_type = 'parent'` content.
- BR-ADM-003: Deleting a node is blocked if it has any `live` topics with active (in-progress) exam sessions.
- BR-ADM-004: Platform content published to `live` is immediately visible to all authenticated students.
- BR-ADM-005: Platform Admin cannot access student profiles, exam sessions, or parent-child links.

---

## Platform Admin API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/admin/nodes` | List all platform root nodes |
| `GET` | `/api/admin/nodes/:node_id` | Get node detail + children |
| `POST` | `/api/admin/nodes` | Create a platform node |
| `PATCH` | `/api/admin/nodes/:node_id` | Update a platform node |
| `DELETE` | `/api/admin/nodes/:node_id` | Delete a platform node |
| `GET` | `/api/admin/nodes/:node_id/topics` | List topics for a node |
| `POST` | `/api/admin/nodes/:node_id/topics` | Create a topic |
| `PATCH` | `/api/admin/topics/:topic_id` | Update topic (title, status) |
| `DELETE` | `/api/admin/topics/:topic_id` | Delete a topic |
| `POST` | `/api/admin/topics/:topic_id/content` | Upload content |
| `GET` | `/api/admin/exams` | List platform exam templates |
| `POST` | `/api/admin/exams` | Create platform exam template |
| `PATCH` | `/api/admin/exams/:exam_id` | Update exam template |
| `DELETE` | `/api/admin/exams/:exam_id` | Delete exam template |
| `POST` | `/api/admin/exams/:exam_id/questions` | Add a question |
| `PATCH` | `/api/admin/exams/:exam_id/questions/:q_id` | Update a question |
| `DELETE` | `/api/admin/exams/:exam_id/questions/:q_id` | Delete a question |
