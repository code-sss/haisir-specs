# Current UI Flows Snapshot

## Snapshot Baseline
| Repo | Commit |
|---|---|
| haisir-backend | 3c53b1a (Phase 5 close — G7-patch-6/12/15/17/19/20 fixes + cognitive-complexity refactor, 2026-07-14) |
| haisir-frontend | 816194d (Phase 5 close — G7-patch-3/5/7/8/9/13/14/15/17/18 fixes, 2026-07-14) |
| haisir-deploy | b8f650d (rootless-dockerd network reconcile script, unrelated to Phase 5, 2026-07-14) |

> Next session: run `git diff 3c53b1a..HEAD` in haisir-backend, `git diff 816194d..HEAD` in haisir-frontend, and `git diff b8f650d..HEAD` in haisir-deploy to see only what changed since this snapshot.

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
  - Key behaviour: BR-ON-008 amended (Pre-Phase-5 G6, 2026-07-06) — an optional Grade `<select>` field is now shown (label "Grade (optional)"), populated from `GET /api/student/catalog`'s `grade`-type nodes via `useGradeOptions`; falls back to a free-text input if the catalog fetch errors or returns no grade nodes. If a grade is chosen, `POST /api/students/me/profile` (`{ grade }`) fires before `onboarding-complete`; a failed profile POST still proceeds to onboarding-complete (never strands the user). No other form fields on this screen.

---

## Onboarding — Parent

- Screen: `/onboarding/parent-ready` View A — Same pattern as student View A. "Relogin" → `/auth/logout`.

- Screen: `/onboarding/parent-ready` View B (`?next=proceed`) — One CTA:
  - "Link your child" → `/parent/link-child` (fixed Phase 5 G2 T2.6 — was a dead `/link-child` link)
  - "Skip — link later from dashboard" → `/home`
  - All exits call `PATCH /api/users/me/onboarding-complete` before navigating.
  - Key behaviour: No inline code entry on this screen (BR-ON-015); deferred to `/parent/link-child`.

---

## Parent Workspace (Phase 5 complete — G1–G7 all closed, T7.2 manual walkthrough signed off 2026-07-13)

- Screen: `/profile` (student, S-profile) — "My Profile" page: header card (name/email); "Parent Access" card with the student's link code (generate/regenerate button, copy-to-clipboard with an `execCommand` fallback for browsers without the Clipboard API, expiry date); "Linked Parents" list with inline confirm-then-revoke per row.
  - Key behaviour: only rendered for the `student` role; parent/instructor/admin see a placeholder message.
  - API: `GET`/`POST /api/student/parent-link-codes`, `GET /api/student/parent-links`, `DELETE /api/student/parent-links/{id}`.

- Screen: `/parent` (P-home) — Parent dashboard: a child-selector pill strip (`aria-pressed`, persisted in `localStorage`, defaults to the first child) when ≥1 child is linked, each pill paired with an inline confirm-then-revoke control (Phase 5 G7-patch-18 — `DELETE /api/parent/children/{child_sub}/link`, per-child in-flight tracking via `revokingSubs`, dismissable error banner; mirrors the `/profile` Linked Parents row pattern — the endpoint existed since G1 but had no UI consumer until this fix). A persistent "+ Add another child" affordance (Phase 5 G7-patch-3, gated on the 10-child cap) is shown once ≥1 child is linked — previously the "Link your child" card only rendered when `children.length === 0`, with no way to add a second child. Empty-state CTA card ("Link your child") → `/parent/link-child` when none are linked; a nav card to `/parent/curriculum` (curriculum builder route).
  - API: `GET /api/parent/children`, `DELETE /api/parent/children/{child_sub}/link`.

- Screen: `/parent/link-child` (P-link) — 8-character link-code entry form (React Hook Form + Zod, uppercase-normalized on type, `A-Z2-9` charset). Validate → `GET /api/parent-link-codes/{code}` shows the resolved child's name (`child_display_name`, Phase 5 G7-patch-19 — the response carried no name field at all before this fix, so the confirm dialog's Zod parse always threw and no parent could ever complete a link through the UI) in a `role="alertdialog"` confirm panel (autoFocus on Confirm, Escape-to-cancel via a document-level listener, focus restored to the triggering button on close). Confirm → `POST /api/parent-child-links`, then redirects to `/parent`.
  - Key behaviour: inline field errors map backend statuses to user-facing text (404 invalid code, 410 expired/used, 409 already linked, 422 10-child cap reached).

- Header nav: student role gains a "Profile" link (→ `/profile`); parent role gains "Dashboard" (→ `/parent`) and "Curriculum" (→ `/parent/curriculum`) links.

---

## Parent Curriculum Builder (Phase 5 G3.3 — complete, browser walkthrough signed off T7.2 2026-07-13)

- Screen: `/parent/curriculum` (P-curriculum) — Two-pane builder. Top bar: "Adopt from Platform" / "Build from scratch" actions. Left pane: resizable (`useResize`, 260px default, 180–500px range) `ParentNodeTree` of the caller's owned root nodes with breadcrumb-tracked selection. Right pane: `ParentTopicPanel` — breadcrumb + node name header, topic list (`ParentTopicRow` per topic), "+ Add topic" button opening `ParentAddTopicModal`. Empty state (no root nodes yet): centered "No curriculum yet" message with the same Adopt/Build actions.
  - Key behaviour (Phase 5 G7-patch-5): `ParentNodeRow`'s expand toggle now derives a `mayHaveChildren` flag (`isExpanded ? children.length > 0 : !hasTopics`) instead of trusting the stale `children.length` from the root-list response (which never includes children pre-expansion) — previously a newly-added child node under a root with no prior children was permanently invisible, since the toggle that would have fetched and revealed it was disabled from the start.
  - Key behaviour (Phase 5 G7-patch-7): returning from a topic content page via `?nodeId=<id>` restores the tree selection and breadcrumb — `useRestoreNodeSelection` walks `parent_id` up through `GET /nodes/{id}` to rebuild the ancestor chain and pre-expands it (deferred until the CSRF token is available). Previously the builder always landed on the empty "Select a node" state on return.
  - Key behaviour (Phase 5 G4, `cfc6f64`): `ParentTopicRow` shows a "no notes yet" chip (via `useParentTopicContents`) when a topic has zero content items, so a parent can spot empty topics without opening each one.
  - Key behaviour: "Build from scratch" opens `ParentAddNodeModal` (same 9-type chip + hierarchy-enforcement rules as the admin `AddNodeModal`, `owner_type` hardcoded to `"parent"`). Selecting a node updates the breadcrumb and topic panel; no node selected shows an "Select a node" placeholder.
  - API: `GET/POST/PATCH/DELETE /api/parent/curriculum/nodes`, `GET/POST/PATCH/DELETE /api/parent/curriculum/nodes/{id}/topics` and `/topics/{id}`.

- Modal: **AdoptModal** (triggered from `/parent/curriculum`) — focus-trapped (`useFocusTrap`) dialog. A platform-board `<select>` (from `GET /api/categories`) drives a lazy-loaded, expandable platform node tree (`GET /api/course-path-nodes/tree/{category_id}`, only fetched once a board is picked). Clicking a tree row selects it as the adopt source (`aria-pressed`); "Adopt" is disabled until a node is selected. On submit, `POST /api/parent/curriculum/adopt`; a 409 (`AlreadyAdoptedError`) surfaces "You have already adopted this board." inline instead of a generic error.
  - Key behaviour: platform-tree browse reuses the same `GET /api/categories` / `GET /api/course-path-nodes/*` endpoints as admin, now parent-accessible browse-only via `require_any_platform_role_or_parent()`.
  - Fixed (Phase 5 G7-patch-9): the modal rendered functional but pinned to the top-left of the viewport instead of centered — it renders `<dialog open>` directly rather than calling `.showModal()` (a deliberate choice for a custom backdrop/focus-trap), so it never picked up the `:modal` UA-stylesheet default and fell out of `.overlay`'s centering flex layout. Fixed with `position: static` on the shared `.modal` class. Same fix applies to the "Build from scratch" add-node modal (shares the CSS).

- Screen: `/parent/curriculum/[node_id]/topics/[topic_id]` (P-topic) — Topic Content Manager. Header: inline-editable topic title (`RenameTopicInline`, shared with admin) + "Back to curriculum" link (Phase 5 G7-patch-7/8 — now carries `?nodeId=<id>` to restore tree selection on return; the query param is named `nodeId`, not `node`, since the WAF's Coraza RCE ruleset (932236) flags bare shell/interpreter binary names like `node` as a query **parameter name** and blocks the request). Body: `TopicContentSection` — the same content-management feature module used by the admin `TopicRow`, parameterized via a `parentContentAdapter` (owner-scoped API calls instead of platform-scoped). Supports the full instant (video/text) + extraction (PDF/image) content flows, extraction job strip, and toast notifications on job completion, identical UX to the admin content manager.
  - Key behaviour: `content-management` is a new shared feature module (`add-content-modal`, `content-item-row`, `delete-content-dialog`, `jobs-strip`, `topic-content-section`) extracted so admin and parent consume one implementation via an adapter interface rather than two drifting copies.
  - API: `GET/POST /topics/{topic_id}/content` (Phase 5 G7-patch-6 — `GET` was entirely missing before this fix, 405ing the content list and making saved content look lost), `PATCH/DELETE /topic-contents/{content_id}`, `POST/GET/DELETE /api/parent/curriculum/topics/{topic_id}/extraction-jobs` (+ retry).

- Architecture note: `ParentRouteGuard` and `AdminRouteGuard` were both refactored onto one shared generic `RouteGuard({ requiredRole })` component (`@/shared/components/route-guard`) — no behavior change, just de-duplication.

---

## Home Dashboard

> Superseded by **Student Dashboard** below (Platform Board / Home Study split has been built since Phase 2 and is complete as of Phase 5 G6). This section is retained only as a pointer — see "Student Dashboard" for the current `/home` and `/courses` behaviour for the `student` role. Non-student roles are redirected away from `/home` (see "Auth & Root" above).

---

## Exam Flow (Student)

- Screen: `/exam?node_id=...` (list) — Lists active exam templates for the node. Shows title, description, duration, passing score. "Try Exam" opens summary modal; "View Results" opens attempts list.

- Screen: `/exam` (active session) — Timed exam form. Questions rendered by type: `single_choice` / `true_false` / `multiple_choice` (radio/checkbox), `fill_in_the_blank` (text input), `essay` (textarea with subtype-specific guidance from `ESSAY_GUIDANCE` lookup when `essay_subtype` is set — e.g. "Aim for 2–3 paragraphs" for `short`, "Analyse the topic and support your view with evidence" for `critical`), **`one_word_response`** (`OneWordResponseInput` — 12rem single-line text input, placeholder "One word…"), **`matching`** (`MatchingInput` — two-column grid; right column pre-shuffled via `seededShuffle(shuffle_seed)` LCG for deterministic per-session ordering; user selects right-side pair for each left item), **`problem_solving`** (`ProblemSolvingInput` — answer text input + working textarea shown when `working_required=true`). Timer counts down from `duration_minutes`. Image zoom modal for questions with images. Answers recorded individually via `POST .../answer` (includes `working_text` for problem_solving). **Auto-scroll after answering choice questions was removed** (was causing UX issues). "Submit" calls `POST .../submit`.
  - Key behaviour: `useCourseNavigation` waits for both `csrfToken` AND `currentRole` before fetching categories — prevents a role-header race on cold load where the JWT has refreshed but `buildApiHeaders` hasn't yet received the role.
  - API: `POST /api/exam-sessions/session/create`, `GET /api/exam-sessions/session/{id}/questions`, `POST /api/exam-sessions/session/{id}/answer`, `POST /api/exam-sessions/session/{id}/submit`

- Screen: `/exam` (grading pending) — When session submit returns `sessionStatus='grading_pending'`, the exam page renders a "Grading Pending" interstitial banner instead of the results display. Banner title + explanatory text indicates AI grading is in progress. Two CTAs: "View Attempts" (opens attempts modal, clears banner) and "Back to Exams" (returns to list). `gradingPending` local state is set by `handleSubmitExam` when the API response indicates `grading_pending` status.

- Screen: `/exam` (submitted — immediate result, Pre-Phase-5 G1, 2026-07-06) — When submit returns an immediately-scored result (not `grading_pending`), a "Submitted!" banner is shown instead of navigating straight into results. Two CTAs: "Review answers" → `router.push('/exam/{session_id}/review')` (the S05 review route, see below); "View Attempts" → opens the attempts modal (list view). `submittedSessionId` local state (`useExamPage`) drives the banner; replaces the previous behaviour of auto-opening `AttemptsModal` with an inline results view.

- Screen: `/exam` (attempts list / AttemptsModal) — All past sessions with scores. `grading_pending` sessions show status label "Grading…" (`.tagPending` CSS class); the "View" detail button is disabled for these attempts. **Per-row "View" now navigates to `/exam/{session_id}/review`** (Pre-Phase-5 G1) instead of expanding an inline results table — the modal itself is list-only; its former inline results detail (score summary, sortable results table, essay expanded rows via `renderEssayRows`/`renderResultRow`) was removed from `attempts-modal.tsx`/`.module.css` since that view now lives solely on the review route. The modal footer gains a **"Refresh"** button (re-fetches attempts for the current template; requests are request-id-guarded so a stale in-flight fetch can't clobber a newer one).
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
- Screen: `/add-exam` — Multi-field exam authoring form with question builder for MCQ and paragraph questions. Create or edit mode based on `template_id` query param. Exam settings include an **"Essay grading mode"** dropdown (`auto_release` = grades published to students immediately after AI grades; `manual_release` = instructor approves before publishing); defaults to `auto_release`. Essay questions show: **"Auto-grade with AI" checkbox** (defaults to `true`; when unchecked, AI grading pipeline skips the question on submit); **"Model answer" textarea** (prose answer shown to students after grade release, stored as `model_answer`); **"Mark scheme / Rubric" textarea** (grading criteria for reference, stored as `explanation`). Both model answer and mark scheme are optional. JSON import/export also serialises `model_answer` per essay question. **"Apply topic to all questions"** control (Pre-Phase-5 G2, 2026-07-05) — a topic `<select>` + "Apply to all questions" button above the questions section; stamps the chosen `topic_id` (or clears it) onto every standalone and paragraph-embedded question in one click, so exam authors don't have to tag each question individually for mastery tracking to fire.
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

- **CatalogCard** — node name (grade-type nodes with a numeric `name` display as "Grade {N}" — Pre-Phase-5 G5, 2026-07-05; Phase 5 G7-patch-14 extracted this into a shared `formatNodeDisplayName` domain helper and applied it to 3 more spots that had been missed: `home-study-section.tsx`, `platform-board-section.tsx`, and `node-tree-sidebar.tsx` — grades previously showed as bare "7"/"8" on `/home` and `/courses`), node_type chip, topic count, "Recommended" green badge (when `recommended=true`). **Enroll** button (blue) calls `POST /api/student/enrollments`; **Drop** button (red) calls `DELETE /api/student/enrollments/{id}`. Both re-fetch the catalog on success and show a transient toast ("Enrolled!" / "Dropped."). The grid sorts recommended nodes first (Pre-Phase-5, 2026-07-06).
- Loading, error, and empty states shown; toast auto-dismisses after 3 s.
- `useStudentCatalog` hook — fetch on mount, enroll/drop with catalog re-fetch; exposes `{ catalogNodes, isLoading, error, enroll, drop }`.

> **Backend note:** `GET /api/student/catalog`, `POST /api/student/enrollments`, `DELETE /api/student/enrollments/{id}` are now wired in the backend (T2.8/T2.9 done at backend `9379bb7`, 2026-06-18). Enroll → 201 + re-fetch; already enrolled → 409; drop → 204.

---

## Student Dashboard (Phase 2 complete — enrollment filtering live, G3 done, G4.4 weak-topics done; Phase 5 G6 — Home Study surface complete)

### Screen: `/home` (StudentHomePage — student role only)
`app/home/page.tsx` branches on `currentRole === "student"` → renders `StudentHomePage`.

Data from `useStudentDashboard` (`GET /api/student/dashboard`). Three sections in order:
- **FocusAreasStrip** (G4.4) — rendered above all boards when `weak_topics` is non-empty. Orange-themed chip row; each chip shows topic title + mastery score badge (red pill) and links to `/home/topics/{enrollment_id}`. Hidden when no weak topics.
- **Platform Board** — grid of root platform node cards (name, topic_count badge, "Start" → `/courses?source=platform&nodeId=…`). When no nodes returned (unenrolled): **empty state** with dashed border — "You haven't enrolled in any courses yet." + "Browse Courses" CTA → `/enroll`.
- **Home Study** — if `has_parent_link=true`, grid of parent-owned root node cards with "Start" CTAs; else dashed-border placeholder "No Home Study content yet — ask your parent to link their account." Card deep-links (Phase 5 G6, `afacb33`) validate the target node id against the loaded tree before selecting it, since it now arrives via a URL query param rather than internal state — lands on the Home Study tab with the right node pre-selected instead of the Platform tab with nothing selected.

### Screen: `/courses` (StudentCoursesPage — student role)
Full-page three-panel layout. Data managed by `useStudentNav` + `useStudentCatalog`.

- **Tab bar** — "Platform" (always enabled) / "Home Study" (disabled when `has_parent_link=false`). ArrowLeft/ArrowRight keyboard navigation; switching source resets node/topic/content + `selectedTopicId`/`selectedRootNodeId`. Active tab + selected topic title get a green accent when `source==='parent'` (Phase 5 G6, `afacb33`).
- **NodeTreeSidebar** (left `<aside>`) — renders `StudentNode[]` from `GET /api/student/nodes?owner_type={source}` — no `owner_id` is ever sent (the frontend has no source for a parent's raw `idp_sub`); for the Home Study source the backend resolves and aggregates across every actively-linked parent (Phase 5 G7-patch-12/20 — see API contract). **Row interaction fixed (Pre-Phase-5 G4, 2026-07-05):** the chevron is now a separate sibling `<button>` (`aria-expanded`, toggle-only — collapses or expands) rather than nested inside the row button (a11y fix); clicking the node **label** always `selectNode(id)` **and** expands (never collapses) when the node has children. Leaf nodes have a chevron placeholder (no button) and just select on label click. **Empty state** (when tree is empty): Platform source shows "No courses enrolled." + "Browse Courses" link → `/enroll`; Home Study source shows "No Home Study content yet — ask your parent to add topics" with no CTA link (Phase 5 G6, `afacb33`). Accepts an `initialExpandedIds` prop (set of ancestor ids) to pre-expand on the deep-link path below; applied at most once via a one-shot ref guard.
- **Deep-link resolution** (`/courses?topic={topic_id}`, Pre-Phase-5 G4, 2026-07-05) — `StudentCoursesPage` reads `initialTopicId` from the `topic` search param (server component wrapper in `app/courses/page.tsx` awaits `searchParams`). On tree load, `useStudentNav.findNodeIdForTopic(topicId)` does a DFS over the loaded tree, using a per-node topics cache (populated by prior `selectNode` calls) and fetching+caching `GET /api/student/nodes/{id}/topics` per-node on cache miss (per-node error isolation — a failed node fetch doesn't abort the probe). Once the owning node is found: `selectNode` + `selectTopic` fire, and `findAncestorIds` (new pure `tree-traversal.ts` module: `findNodePath`/`findAncestorIds`) computes the ancestor chain to pass as `initialExpandedIds`. A stale/unresolvable topic id fails silently (collapsed tree, no error UI) — this is what makes the dashboard's `FocusAreasStrip` weak-topic chip links (previously dead) actually land on the right topic.
- **TopicListPanel** (centre `<section>`) — `StudentTopic[]` from `GET /api/student/nodes/{id}/topics`. Fires `selectTopic(id)` on click; sets `selectedTopicId` state. Each topic row with `has_exam=true` renders a **"Take Exam"** button routing to `/exam?node_id={selectedNodeId}&topic_id={topicId}` (Pre-Phase-5 G3, 2026-07-05 — topic_id now included so the exam list is pre-filtered to that topic's exams only; previously routed with `node_id` alone). **Empty-state fixed (Phase 5 G7-patch-13):** a `selectedNodeId === null` check now runs before the `topics.length === 0` fallback, and the "selected but empty" case is source-aware ("No Home Study content yet — ask your parent to add topics" vs. "No topics in this course yet", via a new `source` prop) — previously selecting an empty Home Study node showed the same generic "Select a node to view topics" message as true no-selection.
- **ContentViewer** (right) — `StudentTopicContent[]` from `GET /api/student/topics/{id}/content`. Text content renders through the shared `MarkdownText` renderer (Phase 5 G6, `afacb33`) instead of raw text, so parent notes display formatted. Empty state (Phase 5 G6, `cfc6f64`): Platform source shows "No content available"; Home Study source (`source==='parent'`) shows a parent-specific "no notes yet" message instead. When a topic is selected (`topicId != null`), renders **HaituDoubtPanel** below the content, passed the current `source`.
- `selectedRootNodeId` is resolved via `findNodePath(nodeTree, nodeId)?.[0]` (root of the returned root→target path) on node selection; `selectedEnrollmentId` is looked up in the catalog (`catalogNodes.find(n => n.id === selectedRootNodeId)?.enrollment_id`).

### Component: HaituDoubtPanel
Rendered at the bottom of `ContentViewer` whenever a topic is selected.

- **Enrollment/access guard** — if not `isEnabled` (no real enrollment and `source !== 'parent'`) or `accessDenied` is set, shows grey italic notice instead of chat UI: platform source → "Enroll in this course to ask hAITU questions."; parent source → "Your Home Study access has changed. Ask your parent to check the link, or refresh this page." (Phase 5 G5, `dd8a6a4`). Heading gets a distinct style when `source==='parent'`.
- **Chat UI** — scrollable bubble list (`role="log" aria-live="polite"`): student messages right-aligned (blue), AI messages left-aligned (grey). Spinner bubble while `isLoading`. Input textarea (Enter = send, Shift+Enter = newline), disabled while loading. Send button disabled when input empty or loading.
- **Error banner** — 429 rate-limit → "You've reached the AI limit for this hour. Try again later."; other errors → "Something went wrong. Please try again."
- **Escalation** — "Ask your teacher" button shown when `escalation_ready=true` AND `!isEscalated` **AND `source !== "parent"`** (Phase 5 G7-patch-15, security-relevant — the button previously rendered and worked identically on Home Study topics, escalating to a generic "instructor" role that has no oversight of parent content in this increment and never notified the parent; blocked server-side too, see `POST /api/doubts/{id}/escalate`'s new 409). Clicking calls `POST /api/doubts/{doubtId}/escalate`; button is disabled if `doubtId` is null (not yet set by the `doubt_id` SSE event) or while the mutation is pending. On success `isEscalated` is set (client mutation state) and the button hides. Escalation error shown inline.
- `useHaituDoubt(topicId, enrollmentId, source?)` hook — client-side message history (last 5 sent as `history` to API), loading/error state, 429 detection. Resets on `topicId` change. Calls `POST /api/haitu/topic-doubt`, omitting `enrollment_id` from the body when null (Home Study topics have no enrollment), and consumes the **SSE stream** via `ReadableStream`/`TextDecoder`, appending `{"token"}` frames to the live assistant bubble; on stream/network failure, resends the last message (resend-on-failure). Exposes `isEnabled` (real enrollment, or `source==='parent'`) and `accessDenied` (set on a 403 from a parent-context request — e.g. a revoked Home Study link mid-session).

> **Backend note (G1 update):** `POST /api/haitu/topic-doubt` now persists doubts. Before the stream starts, a `doubts` row and student `doubt_messages` row are created. The SSE stream emits `event: doubt_id` (payload `{"doubt_id":"<uuid>"}`) as the very first frame; after the stream ends a background task persists the AI reply. On 429 no row is created (no orphan). `HaituDoubtPanel` consumes `doubt_id` from the SSE and shows a "View thread" link to `/doubts/{doubtId}`. On panel re-open for the same topic (not yet resolved/closed), the hook pre-loads the existing thread from `GET /api/students/me/doubts` and restores chat history.

Unit test suite: 11 test files covering all components, hooks, and api layer (100% coverage). **Playwright E2E suite shipped (commit `54e198c`, 2026-06-18):** 16 specs across G3 content-filter, G7 browse-courses, G8 empty-state, and G9 hAITU panel, all green; gated in `/commit-frontend` as a peer to the 100% coverage check.

---

## Post-Exam Review + hAITU Chat (G4.3 — complete; G4-patch streaming rework 2026-07-01)

### Screen: `/exam/[session_id]/review` (ExamReviewPage — S05, student role)
`app/exam/[session_id]/review/page.tsx` → `ExamReviewPage` (client component).

- **Top bar**: back link "← Back to Home" + exam title (`template_title` from review payload).
- **Score bar**: percentage score (`score / total_marks`), correct / wrong / skipped / total question counts.
- **Left panel** (`ExamReviewQuestionList`): collapsible `QuestionCard` items. Wrong / skipped cards default-expanded; correct cards collapsed. Colour-coded badges: green ✓ Correct, red ✗ Wrong, amber "Pending grading" (an essay with `grading_status==='pending'` — Pre-Phase-5 G1/T1.4, 2026-07-04, fixed a regression where this would have rendered as "Skipped"), grey — Skipped. Choice questions render option list with ✓/✗ decorations; `optionCorrect` (green bg) + `optionWrong` (red bg). **Matching questions** render as left→right pairs (`MatchingPairs`) marked ✓/✗ per pair instead of an options list — `user_answer_options`/`correct_answer_options` are parsed as `"L:R"` id-pair strings. Text questions show "Your answer" / "Correct answer" rows (both hidden for matching; "Correct answer" also hidden for essay). **`model_answer`** (teal box) and **`ai_feedback`** (blue box) render when present, ahead of the explanation box. Explanation rendered in a blue-left-bordered box when present. "Ask hAITU to explain this" button per incorrect question triggers `explainQuestion(number, text)`. Reading-passage paragraph groups rendered as titled card with prose + nested question cards.
- **Right panel** (`ExamReviewChatPanel`): hAITU chat sidebar. On mount, `useExamReviewChat` immediately seeds a friendly "preparing your review" bubble, then streams `POST /api/haitu/pattern-analysis` over SSE (`Accept: text/event-stream`) and replaces the seed bubble with the first token (falls back to a single synthetic token on the JSON/202 path). Follow-up questions and `explainQuestion` stream `POST /api/haitu/exam-review-chat` over SSE, appending tokens into a lazily-created AI bubble (spinner shows until the first token arrives). AI bubbles (and the doubt panel) render through a shared **`MarkdownText`** component (react-markdown + remark-gfm, no rehype-raw — AI markdown can't inject raw HTML). Last 10 messages sent as history. Enter sends; Shift+Enter newlines. A clean failure (no AI token ever arrived) badges the user bubble with a **↻ Resend** button (`retry()` re-sends the exact message + history); a non-blocking error banner (e.g. the "Preparing your review…" 202 notice) is dismissible via `clearError()` without clearing the chat. In-flight streams are aborted on `attemptId` switch and on unmount. 429 / 502 / 403 mapped to user-facing error banners. `explainQuestion` prepends "Explain question N: {text}" as the user message.
- **Forbidden state**: shown when `getSessionAnswers` returns 403/null — "This exam isn't available for review yet" + "Back to Home".
- **Error state**: shown on fetch failure — generic error message + "Back to Home".
- `useExamReview(attemptId)`: fetches `GET /api/exam-sessions/session/{id}/answers`; 403/null → `isForbidden=true`; loading/error states exposed. `session-answers-mapper.ts` maps the live DTO to the `ExamReviewPayload` domain model (anti-corruption layer — tolerates both current and legacy backend shapes).
- `useExamReviewChat(attemptId)`: loads pattern analysis on mount via SSE with JSON fallback; resets all state (including the abort controller) on `attemptId` change; manages `messages: ExamReviewChatMessage[]`, `isLoading`, `error`, `patternAnalysisLoaded`, `failedMessageId`; exposes `send(message)`, `retry()`, `explainQuestion(n, text)`, `clearError()`.
- Responsive: below 900 px panels stack vertically; right panel gets fixed 24 rem height.

## Student Doubt Inbox + Thread (G1 — complete)

### Screen: `/doubts` (DoubtInboxPage — S08, student role)
`app/doubts/page.tsx` → `DoubtInboxPage` (client component).

- Fetches `GET /api/students/me/doubts` via `useDoubtInbox` hook.
- Renders a list of doubt rows: question title (or truncated first message), topic name subtitle, status chip (New / AI Answered / Escalated / Answered / Resolved / Closed), relative timestamp.
- Status chip colours: `new`/`ai_answered` → grey surface; `escalated` → amber; `answered` → green; `resolved`/`auto_closed` → grey muted.
- **Status filter** (Pre-Phase-5 G7, 2026-07-05) — dropdown above the list: All / New / Escalated / Answered / Resolved (`filterDoubtsByStatus`, client-side); shown only when doubts exist. "No doubts match this filter." empty state when the filter yields zero rows.
- **Last-message preview** — each row shows a truncated `last_message_excerpt` line when present. The backend list endpoint doesn't send this field yet; the UI tolerates its absence rather than doing a per-row thread fetch to fake it.
- Each row is a link → `/doubts/{id}`.
- Empty state (no doubts at all): "No doubts yet." + "Browse Courses" CTA → `/courses`.
- Error state shown inline.
- Student header: "My Doubts" nav link added beside "Browse Courses".

### Screen: `/doubts/[id]` (DoubtThreadPage — S09, student role)
`app/doubts/[id]/page.tsx` → `DoubtThreadPage` (client component).

- Fetches `GET /api/students/me/doubts/{id}` via `useDoubtThread` hook.
- Renders ordered `doubt_messages` as chat bubbles: `student` sender right-aligned, `ai` left-aligned, `teacher`/`system` distinguished.
- Shows doubt title and topic name at top.
- Follow-up input: textarea + send button; calls `POST /api/students/me/doubts/{id}/messages`; refreshes thread on success.
- **Request teacher help** CTA — amber button visible when `status` is `new` or `ai_answered`, `!isEscalated`, **and `thread.doubt.topic_owner_type !== "parent"`** (Phase 5 G7-patch-17 — this persisted-thread page had its own independent instance of the button with no topic-ownership awareness at all, a second gap on top of G7-patch-15's fix to the live in-topic panel; the backend-side block already covered it, so this was a broken-looking-but-not-exploitable affordance, not a security hole). Clicking calls `POST /api/doubts/{id}/escalate`; on success the button hides and the thread re-fetches (status chip updates to `escalated`, system message appears).
- 404 → "Doubt not found" message.

---

## Teacher Doubt Queue (G2 — complete)

### Screen: `/teacher/doubts` (TeacherDoubtInboxPage — T06, instructor role)
`app/teacher/doubts/page.tsx` → `TeacherDoubtInboxPage` (client component, `TeacherDoubtsProviders` QueryClient wrapper).

- Fetches `GET /api/teachers/me/doubts` via `useTeacherDoubtInbox` hook (enabled when `currentRole === "instructor"`).
- Renders a list of `TeacherDoubtRow` items: student name, topic title, status chip (amber for `escalated`, green for `answered`), relative timestamp.
- **Status filter** (Pre-Phase-5 G7, 2026-07-05) — dropdown above the list, default **"Unclaimed"**: All / Unclaimed / Claimed by me / Answered (`filterTeacherDoubts`, client-side). "No doubts match this filter." empty state when the filter yields zero rows.
- **Last-message preview** — each row shows a truncated `last_message_excerpt` line when present (same optional-field tolerance as the student inbox).
- Per-row actions: **Claim** button (amber, shown when `escalated_to === null`) → calls `POST /api/teachers/me/doubts/{id}/claim`, navigates to `/teacher/doubts/{id}` on success; shows 409 "already claimed" error inline; **Open** link (shown when `escalated_to === userId`); **Taken** chip (shown when claimed by another instructor).
- Empty state (no escalated doubts at all): "No escalated doubts — all caught up."
- Error state: "Failed to load doubt queue."
- Instructor header: "Doubt Queue" nav link → `/teacher/doubts`.

### Screen: `/teacher/doubts/[id]` (TeacherDoubtThreadPage — T07, instructor role)
`app/teacher/doubts/[id]/page.tsx` → `TeacherDoubtThreadPage` (client component).

- Fetches `GET /api/teachers/me/doubts/{id}` via `useTeacherDoubtThread` hook (enabled when `currentRole === "instructor"`).
- Header shows student name + topic title + status chip.
- Renders ordered `doubt_messages` as `MessageBubble` components (shared component with S09: student right-aligned, ai/teacher left-aligned, system centred).
- Reply composer: textarea + Send button (Enter submits, Shift+Enter newline); calls `POST /api/teachers/me/doubts/{id}/messages`; updates thread via `queryClient.setQueryData` on success.
- 404 → "Doubt thread not found or you do not have access."
- Back link → `/teacher/doubts`.

---

## Notifications (G3 — complete)

All notification UI lives in the `src/features/notifications/` module (api client, types, hooks, domain grouping, components). The route `/notifications` has its own `NotificationsProviders` layout wrapper (`QueryClientProvider`).

### Component: NotificationBell (shared topbar — all roles)
Wired into the shared site header for every role. Bell icon with an unread-count badge (hidden when count is 0). Polls `GET /api/notifications/me/unread-count` every 60 s via `useNotifications`; polling **pauses when the tab is hidden** (`visibilitychange` → document hidden) and resumes on focus, avoiding wasted requests in background tabs.

**Dropdown rework (Pre-Phase-5 G7, 2026-07-05):** clicking the bell now opens a real `<dialog>` dropdown (was: click navigated straight to `/notifications`) — refreshes the feed on open, closes on outside-click or Escape (focus returns to the bell button). Shows up to 8 most-recent **unread** items (`getRecentUnread`), each with a red dot, title, relative time; clicking an item marks it read (`PATCH /api/notifications/{id}/read`) and navigates to its `action_url` if present. Footer has **"Mark all read"** (disabled when no unread items shown; calls `PATCH /api/notifications/me/read-all`) and **"View all"** (closes dropdown, navigates to `/notifications`). Empty state: "You're all caught up." Error state (feed fetch failed and no cached items): "Failed to load notifications."

### Screen: `/notifications` (NotificationsPage — all roles)
Full notification feed page. Fetches `GET /api/notifications/me` (default `limit=50`) via the `useNotifications` hook; renders items **grouped by recency** (Today / Yesterday / Earlier / Older) using the `notification-grouping.ts` domain helper. Each item shows a **category dot** (Pre-Phase-5 G7, 2026-07-05 — amber for doubt-related types, green for `topic_marked_weak`, red for `student_at_risk`, grey for anything else, via `getNotificationCategory(type)`), title, body, a deep link to `action_url`, and read/unread styling. An **"Unread only"** checkbox toggle (Pre-Phase-5 G7) filters the list client-side; shows "No unread notifications" when the toggle yields zero rows but unfiltered items exist. A "Mark all read" button in the header calls `PATCH /api/notifications/me/read-all`. Per-item mark-read via `PATCH /api/notifications/{id}/read`. Unread count is reflected in the topbar bell badge.

- Domain: `notification-grouping.ts` — pure functions: recency bucketing (`today | yesterday | earlier | older`), `getRecentUnread(notifications, limit=8)` for the bell dropdown, `getNotificationCategory(type)` mapping known notification types (`new_doubt_escalated`, `doubt_teacher_replied`, `doubt_auto_closed`, `child_doubt_replied`, `child_doubt_auto_closed` → `"doubt"`; `topic_marked_weak` → `"mastery"`; `student_at_risk` → `"at-risk"`; unknown → `"other"`).
- Types: `Notification { id, type, title, body, action_url, read, created_at }`; `NotificationFeedResponse { unread_count, items }`; `UnreadCountResponse { count }`; `ReadAllResponse { marked_count }`.
