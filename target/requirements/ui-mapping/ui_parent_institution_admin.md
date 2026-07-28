# UI Mapping — Parent & Platform Admin

> Maps prototype screen IDs to routes, components, and colour/state details.
> Target prototypes: `target/prototypes/haisir_parent_flow.html` and `target/prototypes/haisir_admin_flow.html`.
> Institution Admin is out of scope for this increment.
>
> **Visual authority rule:** The HTML prototypes (`target/prototypes/*.html`) are the authoritative visual reference for layout, colours, and component placement. The text descriptions below are secondary — if the prototype and the text description conflict, the prototype wins. Always open the HTML file in a browser before implementing a screen.

---

## Parent — Colour tokens

| Token | Value | Usage |
|---|---|---|
| `--parent-topbar` | `#3D2000` | Top navigation bar background |
| `--parent-amber` | `#B45309` | Accent colour, CTAs |
| `--home-study-green` | `#1D9E75` | "Home Study" labels, publish badges |
| `--draft-grey` | `#6B7280` | Draft topic/exam status badges |
| `--danger-red` | `#DC2626` | Delete, revoke actions |

---

## P-home — Parent Dashboard (`/parent`)

**Prototype function:** `renderParentHome()`

| Element | Detail |
|---|---|
| Topbar | `#3D2000`, logo left, parent name + avatar right |
| Child selector strip | Horizontal scroll strip below topbar; each child = avatar + name chip; active child = amber underline |
| "Link your child" card | Shown if zero children linked; dashed border, "+" icon, navigates to P-link |
| Tab bar | "Overview" | "Curriculum" | "Results" — active tab = amber underline |
| Overview tab | Summary cards: Topics Uploaded (count), Exams Created (count), Last Exam Score, Weak Topics |
| Curriculum tab | Shortcut link banner → `/parent/curriculum` |
| Results tab | Shortcut link banner → `/parent/children/:child_idp_sub/results` |

**States:**
- No children linked → only "Link your child" card, no tabs.
- Active child with no curriculum → Overview tab shows zeroes; Curriculum tab shows "Start building" prompt.

---

## P-curriculum — Curriculum Builder (`/parent/curriculum`)

**Prototype functions:** `renderBuilderTree()`, `renderBuilderDetail()`, `openAdoptModal()`, `confirmAdopt()`

| Element | Detail |
|---|---|
| "Adopt from Platform" button | Top-left, amber fill; opens Adopt modal |
| "Build from scratch" button | Top-left, amber outline; opens Add Root Node modal |
| Left panel | Scrollable node tree, ~280px wide |
| Node row | Indented by depth, expand/collapse arrow, node type chip |
| Selected node | Amber left-border highlight |
| "Add Node" | Appears on hover of any node row; adds a child |
| "Rename" / "Delete" | Contextual actions; Delete shows confirmation if has children |
| Right panel | Empty state "Select a node to see topics" until node selected |
| Topic row | Title, status badge (Draft/Live), "Upload Content", "Create Exam", "Delete" |
| "Publish" toggle | Draft → Live toggle per topic; green when Live |
| "Add Topic" button | Below topic list |

### Adopt modal

| Element | Detail |
|---|---|
| Platform board tree | Browseable; greyed if already adopted |
| Already adopted label | "Already adopted" chip on the node row |
| "Adopt" button | Amber fill; triggers `POST /api/parent/curriculum/adopt` |
| Loading state | Spinner on "Adopt" button while cloning |
| Success | Modal closes; new nodes appear in left panel |
| 409 response | Toast: "You have already adopted this board." |

### Add Node modal

| Element | Detail |
|---|---|
| Name field | Required text input |
| Type field | Text input; freeform |
| "Save" button | Amber fill |

**States:**
- Empty curriculum → left panel shows "No curriculum yet" with "Adopt from Platform" and "Build from scratch" buttons prominent.
- Node with no topics → right panel shows "No topics yet — add one."
- Unsaved topic changes → "Unsaved changes" warning banner.

---

## P-topic — Topic Content Manager (`/parent/curriculum/:node_id/topics/:topic_id`)

| Element | Detail |
|---|---|
| Topic title | Editable inline (click to edit) |
| Content slots | Three cards: PDF Upload, Video URL, Text (rich text); each independent |
| Upload card | Drag-and-drop or file picker; progress bar while uploading; "Ready" badge when done |
| Video URL card | Text input for URL; preview thumbnail if valid |
| Text card | Simple textarea or rich text editor |
| "Save" button | Amber fill; fixed bottom bar |
| Status toggle | "Draft" / "Live" toggle at top-right of page |

---

## P-exam — Exam Creator (`/parent/exams`)

| Element | Detail |
|---|---|
| Exam list | Table: title, linked node, questions count, status (Draft/Live), created date |
| "Create Exam" button | Amber fill, top-right |
| Create exam modal | Title, linked node (select), time limit (optional), pass mark (optional) |
| Exam detail | Two tabs: "Settings" (metadata) and "Questions" |
| Question row | Stem preview, type chip, edit/delete icons |
| "Add Question" button | Amber outline; opens question editor |
| Question editor | MCQ: stem + 4 option fields + correct answer radio; Paragraph: stem only |
| "Publish" toggle | Draft → Live per exam; amber when Live |

**States:**
- Exam with 0 questions → "Publish" button disabled, tooltip "Add at least one question to publish."
- Published exam with completed sessions → "Delete" blocked; "Archive" shown instead.

---

## P-results — Child Results (`/parent/children/:child_idp_sub/results`)

| Element | Detail |
|---|---|
| Child name header | Shows active child's name + avatar |
| Results table | Exam name, date taken, score (X/Y), pass/fail badge |
| Row click | Expands per-question breakdown inline |
| Correct answer | Green text |
| Wrong answer | Red text |
| Empty state | "No exam results yet — publish an exam for your child to take." |

---

## P-link — Link Child (`/parent/link-child`)

| Element | Detail |
|---|---|
| Code input | Large text input, placeholder "Enter your child's link code" |
| "Link" button | Amber fill; disabled while empty |
| Success | Toast "Child linked!" + redirect to P-home |
| Error | Inline error below input: "Invalid or expired code" |

---

---

## Platform Admin — Colour tokens

| Token | Value | Usage |
|---|---|---|
| `--admin-topbar` | `#080F17` | Top navigation bar background |
| `--admin-accent` | `#3B82F6` | CTAs, active states |
| `--platform-blue` | `#185FA5` | Section headers |
| `--draft-grey` | `#6B7280` | Draft status badges |
| `--live-green` | `#16A34A` | Live status badges |

---

## Admin Shell Layout (all `/admin*` routes)

> Prototype: `.shell` → `.topbar` + `.app-layout` (flex row) → `.sidenav` | `.main-area`

| Element | Detail |
|---|---|
| Topbar | `#080F17`, 48px, logo left ("hAIsir"), "Platform console" label, role badge (red), admin avatar right |
| Sidenav | 190px, dark `#080F17`, left side. 2 nav items: 🏠 Dashboard (`/admin`), 📚 Board content (`/admin/boards`). Active item = white text + `rgba(255,255,255,.1)` background. Item style: 12px label, icon + text, 8px vertical padding, 7px border-radius. |
| Main area | `flex: 1`, scrollable, contains page-specific content |

**Resizable panels:**
- Sidenav: drag handle on right edge. Default 190px, min 140px, max 300px.

**Routing:**
- `/admin` is the default landing page for `admin` role (role-aware redirect from `/`).
- Admin layout requires `admin` role — non-admin users redirected to `/home`.
- Role redirect map: `admin` → `/admin`, `parent` → `/parent`, `student` / default → `/home`.
- Redirect uses `useAuth.currentRole` (falls back to `localStorage` optimistic role during JWT refresh).
- Must check `isLoading` before redirecting — prevent premature redirect while auth resolves.

---

## SA-dashboard — Admin Dashboard (`/admin`)

**Prototype function:** `renderAdminDashboard()`

| Element | Detail |
|---|---|
| Shell | Admin shell layout (topbar + sidenav + main area) |
| Breadcrumb | "Dashboard" |
| Stats row | 4 metric cards: Platform boards, Live topics, Draft topics, Total topics |
| Board list | Each board = card with icon, name, node/topic counts, "Manage" button → `/admin/boards?board={id}` |
| "Add Board" button | Blue fill, top-right of board list |

---

## SA-boards — Board Content Manager (`/admin/boards`)

**Prototype functions:** `renderBoardTree()`, `selectBoardNode()`, `renderBoardDetail()`, `confirmBoardPublish()`, `openAddContent()`, `confirmAddContent()`, `simulateUpload()`, `simulateExtraction()`, `renderJobRow()`, `renderContentRow()`, `rerenderCurrentNode()`

> Inside `main-area`, the boards page uses a three-column `.board-layout` (flex row): `.board-strip` | `.board-tree` | `.board-detail`.

| Element | Detail |
|---|---|
| Board selector strip | **Vertical** icon strip, 60px wide, dark `#080F17`. Each board = 40×40px icon button (emoji or first letter). Active board = highlighted. "+" add-board button at bottom. |
| Tree panel | Scrollable node tree for selected board, default 240px. Resizable via drag handle on right edge (min 160px, max 500px). Node labels ≥ 13px; tooltip on text overflow. |
| Node row | Indented by depth, type chip; reserved types (grade, subject) show 🔒 badge |
| "Add Child Node" | Appears on hover; adds a child to selected node |
| "Rename" / "Delete" | Contextual; Delete blocked if node has live topics |
| Right panel | Empty state until node selected |
| Topic card | Header (title + status pill + Live/Draft toggle), CONTENT section (rows of `renderContentRow`), IN PROGRESS section (rows of `renderJobRow`, hidden if zero jobs), `+ Add content` button at bottom |
| Status toggle | Per topic: Draft ↔ Live |
| "Add Topic" button | Below topic list |
| "Publish Board" button | Top-right of right panel; opens Publish modal |

### Add Content modal (Phase 1d-real)

Native `<dialog id="modal-add-content">`, `.modal-inner.modal-wide` (560px). Type chip selector + dynamic body.

| Element | Detail |
|---|---|
| Topic context line | "Topic: {topic.name}" — subtle grey, top of modal |
| Type chips (`#uc-types`) | 4 chips horizontally: 📄 PDF / 🖼️ Image(s) / 🎬 Video URL / 📝 Text. Selected chip = `.uc-type.sel` (blue border + tint). Switching chip resets state. |
| Drop zone (`.uc-drop`) | For PDF / Image: 120px tall dashed border zone with 📥 icon + "Drop files here or click to browse" + hint text. `.dragover` class on dragenter/dragover. Click triggers hidden `<input type="file" multiple>`. |
| File list (`.uc-files`) | One `.uc-file` row per added file: icon, name, size (human), status text, mini progress bar (`.uc-file-bar` + `.uc-file-fill`), ✕ remove button (only when `status='pending'`). |
| URL input (Video) | Single `<input type="url">` with placeholder "https://youtube.com/watch?v=…". Optional title input below. |
| Text body | Title input + 6-row textarea. Live char count. |
| Cost preview band | Right of Upload button: "Est. $0.50–$2.00". For >$2: confirmation checkbox required. |
| Confirm button (`#uc-confirm-btn`) | Label changes by type: "Upload N PDFs" / "Upload N images" / "Add video" / "Save text". Disabled when no content provided. |
| Cancel button | "Cancel" (close + drop pseudo-jobs not yet POSTed). Closing during in-flight POSTs does NOT cancel — work continues on topic card. |

### Topic card — IN PROGRESS strip (`.tc-jobs`)

Visible only when `topic.jobs.length > 0`. One `.job-row` per job from `renderJobRow(job, topicId)`.

| Element | Detail |
|---|---|
| Section header | "IN PROGRESS ({n})" small caps, grey |
| Job row layout | Icon (📄/🖼️) · main (filename, meta, progress bar) · status pill · actions |
| Status pills | `.js-pending` "⏱ Queued" (grey) / `.js-uploading` "🌀 Uploading X%" (blue) / `.js-extracting` "🌀 Extracting" (purple, pulsing bar) / `.js-failed` "✕ Failed" (red) |
| Progress bar | `.job-bar` 4px tall · `.job-fill` width=progress%, `.extracting` class adds pulse `@keyframes` |
| Cancel | Visible for pending/uploading/failed; sets `cancel_requested=true` for extracting (soft) |
| Retry | Visible only for `extraction_failed` |

### Topic card — CONTENT section (`.tc-content`)

Visible whenever topic has any `contents`. One `.content-row` per item from `renderContentRow(c)`.

| Element | Detail |
|---|---|
| Row layout | Icon (📄 pdf / 🖼️ image / 🎬 video / 📝 text) · main (title, meta) · View / Edit / Delete buttons · publish state pill |
| Title (`.cr-name`) | **Click to inline-rename**. `contenteditable=true`, blue outline, Enter saves, Esc reverts, empty reverts. Sends `PATCH /api/topic-contents/{id}` with `{title}`. |
| Provenance badge (`.cr-prov`) | When `source_extraction_job_id` is set: "✨ from {source_filename} · p.{n}" pill on the meta line. Tooltip: "This row was created by an extraction job." (Revised — the original PDF/image is now permanently retained, not purged; see `12_content_extraction.md`.) Persists after edits. |
| Publish state pill | `.cr-published` "● Published" (green) or `.cr-draft` "○ Draft" (grey) per row. For a `pdf`/`image` row and its sibling extracted `text` rows, exactly one side shows Published at a time (BR-DATA-024). |
| View button | For `pdf`/`image` rows: opens the inline PDF/image viewer (read-only, no body to edit). For `video` rows: opens the SDK-based player preview. |
| Edit button | For `text` rows: opens `#modal-edit-content` (560 px), title input + **markdown editor with live preview**. For `video` rows: title + URL input. Not shown on `pdf`/`image` rows (use View instead — there is no editable body). Save sends `PATCH /api/topic-contents/{id}` with `{title, body}`. |
| Publish toggle | On the upload group (raw + its sibling text rows, keyed by `source_extraction_job_id`) or the standalone video/text row (`source_extraction_job_id IS NULL` → group of one): switches which side is `visibility_status='published'`. One `PATCH /api/topic-contents/{content_id}/publish` call per BR-EXT-037 — the server drafts the previous side in the same transaction; the UI never writes rows individually. |
| Delete button | Confirm dialog mentioning audit is preserved. Sends `DELETE /api/topic-contents/{id}`. Provenance audit row is NOT cascade-deleted. |
| Empty state | When no content AND no jobs: "No content yet — add a PDF, image, video URL, or text below." |

### Edit content modal (`#modal-edit-content`)

Native `<dialog>`, 560 px wide. Triggered by Edit button on any content row.

| Element | Detail |
|---|---|
| Provenance line | Top of modal. For extracted `text` rows: "✨ Extracted from **{source_filename}** · page {n}. Edits don’t affect the audit record." For non-extracted: "Video URL content." / "Text content (manually authored)." |
| Title input | Required. Cannot be empty. |
| Body field | Markdown editor with live preview (side-by-side or toggleable rendered pane, `text` rows) OR URL input (`video`). `pdf`/`image` rows never open this modal — see the View button / inline viewer instead. |
| Save | `PATCH /api/topic-contents/{id}`. `source_extraction_job_id` is NEVER touched. |
| Cancel | Closes modal without sending. |

### Content viewers (`pdf` / `image` / `video`)

| Element | Detail |
|---|---|
| PDF viewer | Inline, opened via the content row's View button. Reuses the existing `SecurePdfViewer` (`src/components/pdf-viewer/secure-pdf-viewer.tsx`) — not a new component; only its `pdfUrl` changes, to `GET /api/topic-contents/{content_id}/file`. |
| Image viewer | Inline (lightbox/zoom optional), same trigger. **Net-new** — fetches the same per-content file endpoint. |
| Shared component | All three come from the `ContentViewer` promoted out of `src/features/student/components/` into a shared location, so student, admin and parent mount one component. |
| Video player | YouTube IFrame Player API / Vimeo Player SDK, not a raw `<iframe>`. On an embed error (video owner disabled embedding), shows a "Watch on YouTube"/"Watch on Vimeo" external-link button instead of a broken frame. Same component used in the uploader's View action and the student's S-nav content viewer. |

### Polling cadence (frontend, JS)

| Condition | Cadence | Notes |
|---|---|---|
| ≥1 job in `pending`/`extracting` for the topic | every 2s | Sends `If-None-Match: <last-etag>` |
| No active jobs visible | every 10s | Backoff |
| All-done for >60s | stop | Resumes on next user action that opens this topic |

### Publish Board modal

| Element | Detail |
|---|---|
| Draft changes summary | List of topics changed since last publish |
| Confirmation text | "Publishing will make all Live topics visible to all students immediately." |
| "Confirm Publish" button | Blue fill |
| "Cancel" button | Grey outline |

**States:**
- No board selected → left and right panels show "Select a board to manage."
- No node selected → right panel shows "Select a node to see topics."
- Node with no topics → right panel shows "No topics yet — add one."
- Node delete blocked → tooltip "Cannot delete: this node has live topics."
- Cost estimate >$2 → Upload button disabled until checkbox confirmed.
- Per-job cost cap exceeded → status pill "✕ Failed · cost cap reached" + admin contact link.

### P-topic — Parent Topic Content Manager (`/parent/curriculum/:node_id/topics/:topic_id`)

Mirrors SA-boards Add Content modal + topic card behaviour exactly. Differences:

| Element | Difference |
|---|---|
| Endpoint base | `/api/parent/curriculum/...` instead of `/api/admin/...` |
| Quota gate | Modal disables Upload when concurrent_jobs ≥ 5 (warning: "You have 5 jobs in progress. Cancel or wait."). Daily count shown in footer ("78 / 100 today"). |
| Cost cap | Per-job cap same as platform; daily cap is parent-account scoped, not platform-wide. |
