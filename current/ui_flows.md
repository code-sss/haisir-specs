# Current UI Flows Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | fc2eeb2 (feature/rag — live Ollama verification fixes: MockLLM + asyncio marks, 2026-06-20) |
| haisir-frontend | 7fc8811 (feature/rag — chore-only, no UI changes, 2026-06-19) |
| haisir-deploy | 59e42f3 (feature/rag — hAITU APISIX route + backend HAITU/EMBEDDING env vars, 2026-06-19) |

> Next session: run `git diff fc2eeb2..HEAD` in haisir-backend, `git diff 7fc8811..HEAD` in haisir-frontend, and `git diff 59e42f3..HEAD` in haisir-deploy to see only what changed since this snapshot.

---

## Auth & Root

- Screen: `/` — Landing page for unauthenticated users. Authenticated users are redirected: `admin` role → `/admin`; onboarding incomplete → `/onboarding`; `parent` role → `/parent`; else → `/home`. Waits for `isLoading === false` before redirecting (no premature navigation on cold load).

---

## Onboarding — Student

- Screen: `/onboarding` — Entry guard (ON01). No visible UI. Routes based on auth state:
  - No roles assigned → `/onboarding/role`
  - Roles exist + onboarding complete → `/home`
  - Roles exist + onboarding incomplete → role-aware redirect to ready screen with `?next=proceed`

- Screen: `/onboarding/role` (ON02) — Role selection. User picks "Student" or "Parent" from two cards. On "Continue": calls `POST /api/users/me/assign-role`, writes optimistic role to localStorage, navigates to the matching ready screen (View A).

- Screen: `/onboarding/student-ready` View A — Shown immediately after role assignment while JWT still lacks the student role. Single "Relogin" button that redirects to `/auth/logout` → Keycloak login → fresh JWT with new role.
  - Key behaviour: Relogin uses explicit logout, not `prompt=none` (Safari ITP / Firefox ETP block silent re-auth in iframes).

- Screen: `/onboarding/student-ready` View B (`?next=proceed`) — Shown after relogin once JWT carries the student role. Two CTAs:
  - "Join your school" → `/join-school` (not yet built)
  - "Browse open courses" → `/courses` (not yet built)
  - "Skip — go to dashboard" → `/home`
  - All three exits call `PATCH /api/users/me/onboarding-complete` before navigating and set `haisir_onboarding_done` cookie.
  - Key behaviour: No form fields on this screen (BR-ON-008).

---

## Onboarding — Parent

- Screen: `/onboarding/parent-ready` View A — Same pattern as student View A. "Relogin" → `/auth/logout`.

- Screen: `/onboarding/parent-ready` View B (`?next=proceed`) — One CTA:
  - "Link your child" → `/link-child` (not yet built)
  - "Skip — link later from dashboard" → `/home`
  - All exits call `PATCH /api/users/me/onboarding-complete` before navigating.
  - Key behaviour: No inline code entry on this screen (BR-ON-015); deferred to `/link-child`.

---

## Home Dashboard

- Screen: `/home` — Category grid; hierarchical node navigation (grade → subject → course); topics list for the selected terminal node; inline PDF viewer when a content item is opened. Links to `/exam` and `/assess` per node/topic.
  - Key behaviour: Onboarding guard redirects unauthenticated or non-onboarded users. Breadcrumb tracks navigation path.
  - NOT yet built: two-section layout (Platform Board / Home Study split). Currently shows a single unified content tree with no owner_type filtering.
  - API: `GET /api/categories`, `GET /api/course-path-nodes/*`, `GET /api/topics/{node_id}`, PDF file fetch

---

## Exam Flow (Student)

- Screen: `/exam?node_id=...` (list) — Lists active exam templates for the node. Shows title, description, duration, passing score. "Try Exam" opens summary modal; "View Results" opens attempts list.

- Screen: `/exam` (active session) — Timed exam form. Questions rendered by type: `single_choice` / `true_false` / `multiple_choice` (radio/checkbox), `fill_in_the_blank` (text input), `essay` (textarea with subtype-specific guidance from `ESSAY_GUIDANCE` lookup when `essay_subtype` is set — e.g. "Aim for 2–3 paragraphs" for `short`, "Analyse the topic and support your view with evidence" for `critical`), **`one_word_response`** (`OneWordResponseInput` — 12rem single-line text input, placeholder "One word…"), **`matching`** (`MatchingInput` — two-column grid; right column pre-shuffled via `seededShuffle(shuffle_seed)` LCG for deterministic per-session ordering; user selects right-side pair for each left item), **`problem_solving`** (`ProblemSolvingInput` — answer text input + working textarea shown when `working_required=true`). Timer counts down from `duration_minutes`. Image zoom modal for questions with images. Answers recorded individually via `POST .../answer` (includes `working_text` for problem_solving). **Auto-scroll after answering choice questions was removed** (was causing UX issues). "Submit" calls `POST .../submit`.
  - Key behaviour: `useCourseNavigation` waits for both `csrfToken` AND `currentRole` before fetching categories — prevents a role-header race on cold load where the JWT has refreshed but `buildApiHeaders` hasn't yet received the role.
  - API: `POST /api/exam-sessions/session/create`, `GET /api/exam-sessions/session/{id}/questions`, `POST /api/exam-sessions/session/{id}/answer`, `POST /api/exam-sessions/session/{id}/submit`

- Screen: `/exam` (grading pending) — When session submit returns `sessionStatus='grading_pending'`, the exam page renders a "Grading Pending" interstitial banner instead of the results display. Banner title + explanatory text indicates AI grading is in progress. Two CTAs: "View Attempts" (opens attempts modal, clears banner) and "Back to Exams" (returns to list). `gradingPending` local state is set by `handleSubmitExam` when the API response indicates `grading_pending` status.

- Screen: `/exam` (results) — Score, pass/fail badge, answer review with correct answers highlighted. For essay questions, released-grade content is surfaced via the attempts modal (see below).
  - API: `GET /api/exams/session/{id}/answers`

- Screen: `/exam` (attempts list / AttemptsModal) — All past sessions with scores. Drill in to review any attempt. `grading_pending` sessions show status label "Grading…" (`.tagPending` CSS class); the "View" detail button is disabled for these attempts. When viewing a completed attempt, results are sorted by question type (`single_choice → multiple_choice → true_false → fill_in_the_blank → one_word_response → matching → problem_solving → essay`) and include a `#` row counter. Essay questions use a dedicated expanded layout (`renderEssayRows`): main row shows the full submitted essay text spanning the "Your Answer"/"Correct Answer" columns and earned/total points. A second expanded row is shown below (only when `grading_status` is `released`, `finalized`, or `overridden`) containing: AI Feedback (blue-tinted box), Model Answer (teal-tinted box, prose answer set by exam author), and Mark Scheme (standard explanation box for grading criteria). Non-essay questions use the compact `renderResultRow` layout. Points formatted to 2 decimal places where fractional.
  - API: `GET /api/exams/session/all/{template_id}`

- Key behaviour: Unfinished session resume supported via `GET /api/exams/session/unfinished/{template_id}` check on load.

---

## Legacy Assessment Flow (deprecated — still accessible)

- Screen: `/assess?topic_id=...` — Lists assessments for a topic. Student can start, answer, submit, and review attempts.
  - API: deprecated `/api/assessments/*` endpoints
  - Note: deprecated flow; no new development. Retained as-is.

---

## Exam Template Management (outside current target increment — retained)

- Screen: `/exam` (instructor view) — Template list with Edit/Delete buttons. "+ Add Exam" button navigates to `/add-exam`.
- Screen: `/add-exam` — Multi-field exam authoring form with question builder for MCQ and paragraph questions. Create or edit mode based on `template_id` query param. Exam settings include an **"Essay grading mode"** dropdown (`auto_release` = grades published to students immediately after AI grades; `manual_release` = instructor approves before publishing); defaults to `auto_release`. Essay questions show: **"Auto-grade with AI" checkbox** (defaults to `true`; when unchecked, AI grading pipeline skips the question on submit); **"Model answer" textarea** (prose answer shown to students after grade release, stored as `model_answer`); **"Mark scheme / Rubric" textarea** (grading criteria for reference, stored as `explanation`). Both model answer and mark scheme are optional. JSON import/export also serialises `model_answer` per essay question.
  - Note: instructor persona deferred. Screens remain functional in codebase.

---

## Assessment Upload (outside current target increment — retained)

- Screen: `/add-assessment` — Multi-step: upload PDF/file → extracted text review → AI MCQ generation → review and edit MCQs → save.
  - Note: instructor persona deferred. Screen remains functional in codebase.

---

## Admin: Category Management (outside current target increment — retained)

- Screen: `/manage-categories` — Create categories (name, path_type, description) and edit descriptions inline. Admin-role guard redirects non-admins to `/home`.
  - API: `GET/POST /api/categories`, `PATCH /api/categories/{id}`
  - Note: Pre-Phase-1b category management screen. Superseded by the new Admin Board Content Manager below for board/node management; this screen is still functional in the codebase.

---

## Admin: Board Content Manager (Phase 1b)

Route guard: `AdminRouteGuard` in `src/app/admin/layout.tsx` shows a spinner while auth resolves then redirects non-admin to `/home`. Backend also rejects non-admin API calls (defence-in-depth).

**Shell layout** — All `/admin` routes render inside `AdminShell`: topbar + flex-row(`AdminSidenav` | `main`). `AdminSidenav` is a resizable dark sidebar (190px default, 140–300px range) with 3 nav items (🏠 Dashboard → `/admin`, 📚 Board content → `/admin/boards`, ⚙️ Workers → `/admin/system/workers`) and a drag handle on its right edge. Active item highlighted via `usePathname()`.

- Screen: `/admin` — AdminDashboard. **Platform Overview** — 4 stat cards (Platform boards / Live topics / Draft topics / Total topics) fetched from `GET /api/admin/board-stats`. Stat cards use colour-coded left borders (blue / green / amber / gray). If the stats endpoint is unavailable, an alert is shown and cards display “—“. **Boards section** — header with “+ Add board” button (opens AddBoardModal directly from dashboard). Each board renders as a rich card: emoji icon (cycling 📗📘📙…), board name, “{live} live topics · {draft} drafts” subtitle, unconditional “Live” green badge, “Manage” link to `/admin/boards?board={id}`. **The entire card is clickable** via an invisible stretch `<button>` (`position: absolute; inset: 0`) — clicking anywhere on the card navigates to `/admin/boards?board={id}` via `router.push`. The description input and “Manage” link each call `stopPropagation` to prevent double-navigation. Click-to-edit board description: click shows inline textarea, Enter/blur calls `PATCH /api/categories/{id}` with `{ description }`, Escape cancels. Empty state: “No boards yet.” with the “+ Add board” button still visible.
  - API: `GET /api/categories`, `GET /api/admin/board-stats`, `POST /api/categories`, `PATCH /api/categories/{id}`

- Screen: `/admin/boards` — AdminBoardsPage. Three-panel layout:
  1. **BoardSelectorStrip** — 60px vertical dark strip (`#080F17`), rendered as semantic `<ul>/<li>`. Each board = 40×40px emoji icon `<button>` cycling 📗📘📙, active board highlighted; "+ Add board" `<li>` pinned at bottom. Board change resets the selected node. `?board=` query param validated against `/^[\w-]+$/`; invalid values silently ignored.
  2. **NodeTree** — hierarchical tree of nodes for the active board, fetched via `GET /api/course-path-nodes/tree/{categoryId}`. Tree rebuilt client-side via `buildNestedTree()` (handles both flat and nested API shapes). Each row (`NodeTreeRow`) shows: expand/collapse toggle (disabled for leaf nodes), node name + `NodeTypeChip`, inline actions (+ add child, ✎ rename, × delete) hidden when node has topics. **An invisible stretch button covers the full row area** and fires `onToggle(node.id)` on click (only when node has children and not renaming; `aria-hidden`, `tabIndex=-1`). Clicking the node label button also triggers expand/collapse in addition to node selection. Topics displayed inline as `TopicTreeRows` below their node (live/draft coloured dot + title) — always visible for leaf nodes, visible when expanded for branch nodes. Panel resizable (240px default, 160–500px). `ancestorTypes` passed down the tree for hierarchy enforcement.
  3. **NodeDetailPanel** — shown when a node is selected. **Conditionally renders** based on node type: reserved types (`grade`, `subject`) → `ChildNodesPanel`; non-reserved types → `TopicPanel`. Header shows breadcrumb path, node name chip, and "Type: X · Owner: platform" meta line.
  - API: `GET /api/course-path-nodes/tree/{categoryId}`, `POST /api/course-path-nodes`, `PATCH /api/course-path-nodes/{id}`, `DELETE /api/course-path-nodes/{id}`, `POST /api/categories`, `GET /api/topics/{nodeId}`, `POST /api/topics/`, `PATCH /api/topics/{id}`, `DELETE /api/topics/{id}`
  - Layout wrapper: `AdminProviders` (in `src/app/admin/layout.tsx`) wraps all `/admin` routes; `src/app/admin/error.tsx` is the error boundary.

- Panel: **TopicPanel** — fetches topics for the selected node via `GET /api/topics/{nodeId}`; shows loading spinner, error state, topic list (one TopicRow per topic), and an "+ Add topic" button.

- Row: **TopicRow** — individual topic card with: inline rename (click title → RenameTopicInline), draft/live status toggle ("Set live" / "Set draft" button calling `PATCH /api/topics/{id}`), and a delete (×) button opening DeleteTopicDialog. Renders a **content management section** (ContentItemRows with inline rename + provenance badges, "Add Content" button) and an **extraction jobs strip** below the content section. The jobs strip shows the last 3 extraction jobs (sorted newest-first) via `useExtractionJobs`; each job row shows filename, status label, pages_completed/pages_total progress, and Cancel/Retry actions. When a job transitions to `done`, the strip fires `onJobDone` which invalidates the topic contents query and shows a toast. When all jobs are terminal and 60 s have elapsed with no active jobs, polling stops. **Inline content rename**: `handleRenameContent` uses `useUpdateTopicContent` mutation; `renamingContentId` state tracks the in-flight item; `isTitleSaving` prop passed to `ContentItemRow` for disabled state.
  - API: `GET /api/topics-contents/{topicId}`, `POST /api/topics-contents/`, `PATCH /api/topics-contents/{id}`, `DELETE /api/topics-contents/{id}`, `GET /api/admin/topics/{topicId}/extraction-jobs`, `DELETE /api/admin/extraction-jobs/{jobId}`, `POST /api/admin/extraction-jobs/{jobId}/retry`

- Row: **ContentItemRow** — one row per content item: type icon (🎬 video / 📄 pdf / 📝 text / ❓ question / 💬 question_answer), **inline title rename** (title rendered as a `<button>`; click → switches to `<input>` with `autoFocus`, max 200 chars; Enter saves, Escape/blur cancels; disabled while save is in-flight), **provenance badge** (if `item.provenance != null`, renders `✨ from {source_filename} · p.{page_no}` pill below title with tooltip “Edits don’t affect the audit record”), optional description (truncated, full text in `title` tooltip), order badge, “Edit” button, × delete button. Rename callback `onRename(item, title)` and `isTitleSaving` prop passed from `TopicRow`.

- Modal: **AddContentModal** — native `<dialog>`; `mode: 'create' | 'edit'`. **4-chip type selector**: PDF, Image(s), Video URL, Text (chips disabled in edit mode). For PDF/Image chips: drag-and-drop file zone (or click to browse, accepts `application/pdf`/`image/*`); shows file list with remove buttons; cost estimate preview (pages × per-page rate) with a confirmation checkbox before upload is enabled; up to 5 files per submission; validates size ≤ 50 MB and MIME type. **Upload-closes-immediately**: on submit with files, modal closes at once and background upload fires via `extractionHook.uploadFiles()`; pseudo-jobs appear in the topic strip immediately. For Video URL chip: URL field + title/description/order fields, same Zod validation as before. For Text chip: textarea + title/description/order. In edit mode, only Video/Text are editable; content_type is immutable. `useFocusTrap` traps keyboard focus.

- Dialog: **DeleteContentDialog** — native `<dialog>` confirmation: “Delete this content? The extraction audit record will be preserved.” Cancel + “Confirm Delete” (danger style); loading state on confirm. Calls `DELETE /api/topics-contents/{id}`; 404 treated as already-gone.

- Hook: **useExtractionJobs(topicId, { onJobDone })** — manages extraction job lifecycle for a single topic. Merges pseudo-jobs (local optimistic state for in-flight uploads) with server-polled jobs. Polling interval: 3 s while any job is `uploading|pending|extracting`; 5 s for 60 s after last active job ends; then stops. Exposes `{ jobs: DisplayJob[], isLoading, isError, uploadFiles, cancelJob, retryJob }`. `uploadFiles(files)` creates one pseudo-job per file, calls `createExtractionJob` with a UUID idempotency key, replaces the pseudo-job with the server job on success or marks it `upload_failed` on error.

- API module: **extraction-api.ts** — `createExtractionJob` (multipart POST, bodyFactory re-clone on CSRF retry per BR-EXT-018, throws `ExtractionJobDuplicateError` on 409), `listExtractionJobs` (ETag/304 support), `getExtractionJob`, `cancelExtractionJob`, `retryExtractionJob`, `listAdminWorkers`.

- Component: **Toast** (`src/shared/components/ui/toast/`) — lightweight imperative toast system. `useToast()` hook exposes `showToast(message, variant)`. Variants: `success`, `error`, `info`. Auto-dismisses after 4 s. Rendered by `ToastProvider` mounted in `AdminProviders`. Used by TopicRow to surface extraction-complete and extraction-failed notifications.

- Inline: **RenameTopicInline** — controlled text input; Enter or blur saves (calls `PATCH /api/topics/{id}` with `{title}`), Escape cancels.

- Modal: **AddTopicModal** — triggered by "+ Add topic". Fields: `title` (required, React Hook Form + Zod). Submits `POST /api/topics/` with `{title, course_path_node_id}`.

- Dialog: **DeleteTopicDialog** — confirmation modal for topic deletion. Calls `DELETE /api/topics/{id}`; handles 409 (`AdminDeleteBlockedError`) by showing a dismissal state with the backend `detail` message directly.

- Modal: **AddNodeModal** — triggered from NodeDetailPanel or NodeTreeRow. Fields: `name` (required, label "Node label", placeholder "e.g. Grade 8, Algebra, Chapter 3…"), `node_type` (chip selector grid, required). **9 chips**: course, chapter, module, section, unit, week, skill (regular — neutral chips), grade, subject (reserved — 🔒 amber chips). Hierarchy enforcement via `isTypeDisabled(type, ancestorTypes)`: root-level → only `grade` enabled; under a single `grade` → only `subject` enabled; deeper → any type not in ancestor chain. Default selection = first enabled type. Modal title: "Add top-level node" or "Add child node" ("Under: {parentNodeName}" subtitle). `owner_type` hardcoded to `"platform"` (not user-editable). Submits `POST /api/course-path-nodes`.

- Modal: **AddBoardModal** — triggered from BoardSelectorStrip and Admin Dashboard header. Fields: `name` (required), `description` (optional textarea, placeholder "e.g. Calgary Board of Education"). `path_type` hardcoded to `"structured"` (not shown to user). Submits `POST /api/categories`.

- Panel: **ChildNodesPanel** — shown in NodeDetailPanel when a reserved-type node (`grade` or `subject`) is selected. Lists direct child nodes as cards showing: 🔒 lock icon (if child is also reserved), child name, topic count (via `useTopics`), and `NodeTypeChip`. Empty state: "No child nodes yet."

- Rows: **TopicTreeRows** — inline topic display within NodeTree rows. Renders for non-reserved node types only (`isReservedType` guard). Each topic shown as a tree row with a coloured dot (green = live, gray = draft) and title. Leaf nodes always show topics; branch nodes show topics only when expanded.

- Domain: **admin-node-domain.ts** — pure functions (no React/Next imports): `isReservedType`, `isTypeDisabled` (hierarchy enforcement), `findNodeById`, `buildBreadcrumb`, `sortNodesByPosition`, `buildNestedTree` (handles both flat and pre-nested API shapes).

- Inline: **RenameNodeInline** — double-click on a node name activates an inline text input. On blur or Enter: submits `PATCH /api/course-path-nodes/{id}` with `{name}` only. Escape cancels without saving.

- Dialog: **DeleteNodeDialog** — triggered from NodeTreeRow action menu. Shows node name and a confirm button. On 409 response from backend: displays a human-readable blocked reason (node has children or topics). On success: removes node from tree and clears node selection if the deleted node was selected.

- Accessibility: `useFocusTrap` hook traps keyboard focus inside any open modal (AddNodeModal, AddBoardModal, DeleteNodeDialog).

---

## Admin: Worker Health (Phase 1e)

- Screen: `/admin/system/workers` — Worker health page. Shows a table of registered worker heartbeats polled from `GET /api/admin/system/workers` every 30 s (via `useAdminWorkers` hook, `refetchInterval: 30_000`). Table columns: hostname (`worker_id`), Started (ISO), Last Seen (relative, via `formatRelativeTime()`), Job (first 8 chars of `job_id` or —), Status pill (Active = green / Stale = red, derived from `is_stale` flag via `getWorkerStatus()` — never re-derived on client per BR-EXT-031). Zero-active-workers banner shown when `active_count === 0`. Shows loading spinner on initial fetch; error state on failure. No user actions.
  - Hook: `useAdminWorkers()` in `src/features/admin/hooks/use-admin-workers.ts` — `useQuery` wrapping `listAdminWorkers` from extraction-api.ts; `refetchInterval: 30_000`.
  - Domain: `formatRelativeTime(iso: string): string` and `getWorkerStatus(is_stale: boolean): 'Active' | 'Stale'` pure functions in `src/features/admin/domain/worker-domain.ts`.
  - Types: `AdminWorkerSchema = { worker_id, started_at, last_seen, job_id, is_stale }`; `WorkerListResponseSchema = { workers: AdminWorker[], active_count, stale_count }` in `src/features/admin/types/admin.types.ts`.

---

## Utility

- Screen: `/health` — `GET` returns 204. No UI.
- Screen: `/csp-report` — `POST` accepts CSP violation reports; returns 204. No UI.
- Screen: `/*` (not-found) — 404 fallback page.

---

## Student: Browse Courses + Enrollment (G7/G8/G9 + E2E complete)

### Screen: `/enroll` (BrowseCoursesPage — student role)
"Browse Courses" nav link appears in the site header for students (`currentRole === "student"`). Renders a responsive grid of `CatalogCard`s populated by `useStudentCatalog` (calls `GET /api/student/catalog`).

- **CatalogCard** — node name, node_type chip, topic count, "Recommended" green badge (when `recommended=true`). **Enroll** button (blue) calls `POST /api/student/enrollments`; **Drop** button (red) calls `DELETE /api/student/enrollments/{id}`. Both re-fetch the catalog on success and show a transient toast ("Enrolled!" / "Dropped.").
- Loading, error, and empty states shown; toast auto-dismisses after 3 s.
- `useStudentCatalog` hook — fetch on mount, enroll/drop with catalog re-fetch; exposes `{ catalogNodes, isLoading, error, enroll, drop }`.

> **Backend note:** `GET /api/student/catalog`, `POST /api/student/enrollments`, `DELETE /api/student/enrollments/{id}` are now wired in the backend (T2.8/T2.9 done at backend `9379bb7`, 2026-06-18). Enroll → 201 + re-fetch; already enrolled → 409; drop → 204.

---

## Student Dashboard (Phase 2 complete — enrollment filtering live, G3 done)

### Screen: `/home` (StudentHomePage — student role only)
`app/home/page.tsx` branches on `currentRole === "student"` → renders `StudentHomePage`.

Two sections, data from `useStudentDashboard` (`GET /api/student/dashboard`):
- **Platform Board** — grid of root platform node cards (name, topic_count badge, "Start" → `/courses?source=platform&nodeId=…`). When no nodes returned (unenrolled — pending T3 enrollment filter): **empty state** with dashed border — "You haven't enrolled in any courses yet." + "Browse Courses" CTA → `/enroll`.
- **Home Study** — if `has_parent_link=true`, grid of parent-owned root node cards with "Start" CTAs; else dashed-border placeholder "No Home Study content yet — ask your parent to link their account."

### Screen: `/courses` (StudentCoursesPage — student role)
Full-page three-panel layout. Data managed by `useStudentNav` + `useStudentCatalog`.

- **Tab bar** — "Platform" (always enabled) / "Home Study" (disabled when `has_parent_link=false`). ArrowLeft/ArrowRight keyboard navigation; switching source resets node/topic/content + `selectedTopicId`/`selectedRootNodeId`.
- **NodeTreeSidebar** (left `<aside>`) — renders `StudentNode[]` from `GET /api/student/nodes?owner_type={source}`. Each `NodeRow` shows a chevron + expand/collapse for nodes with `children`; leaf nodes fire `selectNode(id)`. **Empty state** (when tree is empty — unenrolled): "No courses enrolled." + "Browse Courses" link → `/enroll`.
- **TopicListPanel** (centre `<section>`) — `StudentTopic[]` from `GET /api/student/nodes/{id}/topics`. Fires `selectTopic(id)` on click; sets `selectedTopicId` state.
- **ContentViewer** (right) — `StudentTopicContent[]` from `GET /api/student/topics/{id}/content`. Shows "No content available" when `contents` is empty. When a topic is selected (`topicId != null`), renders **HaituDoubtPanel** below the content.
- `selectedRootNodeId` is resolved via `findRootNodeId(nodeTree, nodeId)` on node selection; `selectedEnrollmentId` is looked up in the catalog (`catalogNodes.find(n => n.id === selectedRootNodeId)?.enrollment_id`).

### Component: HaituDoubtPanel
Rendered at the bottom of `ContentViewer` whenever a topic is selected.

- **Enrollment guard** — if `enrollmentId === null`, shows grey italic "Enroll in this course to ask hAITU questions." (no chat UI).
- **Chat UI** — scrollable bubble list (`role="log" aria-live="polite"`): student messages right-aligned (blue), AI messages left-aligned (grey). Spinner bubble while `isLoading`. Input textarea (Enter = send, Shift+Enter = newline), disabled while loading. Send button disabled when input empty or loading.
- **Error banner** — 429 rate-limit → "You've reached the AI limit for this hour. Try again later."; other errors → "Something went wrong. Please try again."
- **Escalation** — "Ask your teacher" button shown when `escalation_ready=true` from API; disabled with `title="Coming soon"` (instructor persona deferred).
- `useHaituDoubt(topicId, enrollmentId)` hook — client-side message history (last 5 sent as `history` to API), loading/error state, 429 detection. Resets on `topicId` change. Calls `POST /api/haitu/topic-doubt`.

> **Backend note:** `POST /api/haitu/topic-doubt` is now wired (T5.4/T5.5 done at backend `9379bb7`, 2026-06-18). Valid request → 200 + `HaituDoubtResponse`; wrong enrollment / out-of-subtree topic → 403; 21st call in the hour → 429. No DB rows written.

Unit test suite: 11 test files covering all components, hooks, and api layer (100% coverage). **Playwright E2E suite shipped (commit `54e198c`, 2026-06-18):** 16 specs across G3 content-filter, G7 browse-courses, G8 empty-state, and G9 hAITU panel, all green; gated in `/commit-frontend` as a peer to the 100% coverage check.
