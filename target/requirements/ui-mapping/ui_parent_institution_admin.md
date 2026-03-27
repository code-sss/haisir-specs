# UI Mapping — Parent & Platform Admin

> Maps prototype screen IDs to routes, components, and colour/state details.
> Target prototypes: `target/prototypes/haisir_parent_flow.html` and `target/prototypes/haisir_admin_flow.html`.
> Institution Admin is out of scope for this increment.

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

## SA-dashboard — Admin Dashboard (`/admin`)

**Prototype function:** `renderAdminDashboard()`

| Element | Detail |
|---|---|
| Topbar | `#080F17`, logo left, admin name right |
| Stats row | 4 metric cards: Total Nodes, Total Topics, Live Topics, Published Exams |
| Board list | Table of top-level platform nodes: name, node count, topic count, "Manage" link |
| "Add Board" button | Blue fill, top-right of board list |

---

## SA-boards — Board Content Manager (`/admin/boards`)

**Prototype functions:** `renderBoardTree()`, `selectBoardNode()`, `renderBoardDetail()`, `confirmBoardPublish()`

| Element | Detail |
|---|---|
| Board selector strip | Horizontal tab strip of top-level platform nodes; active = blue underline |
| Left panel | Scrollable node tree for selected board, ~280px |
| Node row | Indented by depth, type chip; reserved types (grade, subject) show 🔒 badge |
| "Add Child Node" | Appears on hover; adds a child to selected node |
| "Rename" / "Delete" | Contextual; Delete blocked if node has live topics |
| Right panel | Empty state until node selected |
| Topic list | Title, content type icons, status badge (Draft/Live), "Upload Content", "Edit", "Delete" |
| Status toggle | Per topic: Draft ↔ Live |
| "Add Topic" button | Below topic list |
| "Publish Board" button | Top-right of right panel; opens Publish modal |

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
