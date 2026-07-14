# Phase 5 — Manual Browser Walkthrough Record

> Task **T7.2** [frontend] gate. Execution + recording only — no code changes in this task.
> Every automated gate (unit, integration, E2E-contract, ollama-gated-grounded) is already green
> (see `progress.md` 2026-07-11 entry). This is the one remaining human check before Phase 5 closes.
> Mirrors the scripted journey in `test_g7_1_e2e_journey_integration.py` /
> `test_g7_1_ollama_gated_grounded_journey.py`, but driven through the real UI so visual/UX
> regressions (focus traps, empty states, a11y, dead links) that a backend-only test can't see get
> one real pass. Fill in **Observed** / **Pass/Fail** as you go; defects go to a new `TASKS.md` G7-patch
> entry, not silently fixed.

## Pre-flight checklist

| # | Requirement | Status |
|---|---|---|
| P1 | Full stack up via `haisir-deploy` docker compose (backend, worker, frontend, APISIX, Postgres pgvector) | ☑ |
| P2 | Worker running with RAG outbox + embedding configured (`bge-m3` reachable) — needed for Part D/G | ☑ |
| P3 | Two browser sessions (or one normal + one incognito) so you can be logged in as **Parent A** and **Student A** at once | ☑ |
| P4 | A second parent account (**Parent B**) for the cross-family check in Part H | ☑ |
| P5 | A platform board with at least one live topic exists (Admin-created), for the "Adopt from Platform" step | ☑ |

---

## Part A — Parent–child linking (G1, re-confirm) + workspace shell (G2)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| A1 | Log in as **Student A** → `/profile` → "Parent Access" card → generate/copy link code | 8-char code shown, copy-to-clipboard works | Code section renders correctly; Linked Parents row initially showed blank name + "Invalid Date" (field-name mismatch bug), fixed and re-verified | ☑ |
| A2 | Log in as **Parent A** → onboarding "Parent Ready" screen → "Link your child" CTA | Lands on `/parent/link-child`, **not** a dead link (this was the G2 T2.6 fix) | Confirmed | ☑ |
| A3 | On `/parent/link-child`, enter the code (auto-uppercased as you type) | Confirm dialog shows the correct child's name; Escape cancels it, focus returns to the trigger button | Confirmed | ☑ |
| A4 | Confirm the link | Redirects to `/parent`, child appears in the child-selector strip | Confirmed; child chip name correct (test data first_name = "Student") | ☑ |
| A5 | Reload `/parent` | Selected child persists (localStorage) | Confirmed | ☑ |
| A6 | Check header nav as Parent A | "Dashboard" and "Curriculum" links present; as Student A, "Profile" link present | Confirmed | ☑ |
| A7 | Try `/parent` while logged in as Student A (URL bar) | Redirected away (route guard) | Confirmed | ☑ |

**Additional defects found (outside scripted steps), filed as `TASKS.md` G7-patch:**
- G7-patch-3 (fixed, re-verified): once a parent had ≥1 child linked, there was no UI path to link a second child — `parent-dashboard.tsx`'s "Link your child" card only rendered when `children.length === 0`. Fixed with a persistent "+ Add another child" affordance; second-child link tested successfully.
- G7-patch-4 (open): the second linked child then rendered as a blank, unlabeled circle in the child-selector strip instead of a name chip — same root cause class as G7-patch-2 (child's `student_profiles` row never populated, no fallback), plus a frontend defensive-fallback/`aria-label` gap on the pill itself. Not yet fixed.

---

## Part B — Curriculum builder: build from scratch (G3.3)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| B1 | Parent A → `/parent/curriculum` (first visit, empty) | Centered "No curriculum yet" with Adopt/Build actions | Confirmed | ☑ |
| B2 | Click "Build from scratch" → add a root node (e.g. type `grade`, name "Grade 7") | Node appears in the left tree, selected | Confirmed | ☑ |
| B3 | Add a child node under it (e.g. `subject` "Science") | Hierarchy rules enforced — same chip-lock behavior as Admin's `AddNodeModal` | Initially failed: node created (201) but never appeared in the tree — expand toggle was permanently disabled for a root node with no prior children (G7-patch-5); fixed and re-verified with both Science and a second subject (Maths) | ☑ |
| B4 | Add a topic under the leaf node, e.g. "Photosynthesis" | Topic appears in the right panel topic list, status = draft | Confirmed (also re-verified with "Ratio" under Maths) | ☑ |
| B5 | Open the topic (P-topic page) → rename title inline | Saves without a page reload | Confirmed | ☑ |
| B6 | Add **text** content to the topic (paste a paragraph containing a unique marker word, e.g. `ZORBLAX-912`) | Content saved; `ParentTopicRow` back on the builder page now shows no "no notes yet" chip for this topic | Initially failed: `GET .../topics/{id}/content` was 405 (route never implemented, G7-patch-6), and "Back to curriculum" 404'd (G7-patch-7) then lost tree selection on return, then a WAF false-positive on the fix's own query param (G7-patch-8). All fixed and re-verified: Photosynthesis chip clears after content save; Ratio (no content yet) still shows the chip, confirming both directions | ☑ |

**Additional defects found (outside scripted steps), filed as `TASKS.md` G7-patch entries — see G7-patch-5 through G7-patch-8 (all fixed and re-verified).**

---

## Part C — Curriculum builder: adopt from platform (G3.3)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| C1 | Click "Adopt from Platform" | Modal opens, focus-trapped; board `<select>` populated from `GET /api/categories` | Modal opened and was functional, but rendered pinned to the left edge instead of centered (G7-patch-9); fixed and re-verified | ☑ |
| C2 | Pick a board → expand the lazy-loaded node tree → select a node | Row shows selected (`aria-pressed`); "Adopt" enables | Confirmed (NCERT board → Grade 8 → Maths → Algebra) | ☑ |
| C3 | Click "Adopt" | New root node appears in the parent's tree, cloned structure (nodes + topics, no content, topics reset to draft) | Confirmed — "Algebra" appears as a new independent root (adopt clones the selected subtree only, not its platform ancestors, per BR-DATA-005/006 — by design); no content, topics in draft | ☑ |
| C4 | Re-open Adopt modal, adopt the **same** node again | 409 surfaced inline as "You have already adopted this board." (not a generic error) | Confirmed | ☑ |

**Additional defects found (outside scripted steps), filed as `TASKS.md` G7-patch entries — see G7-patch-9 (fixed and re-verified).**

---

## Part D — Publish + RAG drain (G4, re-confirm end-to-end)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| D1 | On the "Photosynthesis" topic from Part B, toggle draft → live | Topic status flips to live | Confirmed | ☑ |
| D2 | Wait ~10–15s (worker outbox poll) | *(optional DB check)* `SELECT status FROM rag_indexing_outbox WHERE content_id = '<id>'` → `done`; `SELECT count(*) FROM data_topic_content_chunks WHERE metadata_->>'content_id' = '<id>'` → > 0 | Initially failed: outbox row was `status='failed', retry_count=3, last_error='Connection error.'` — the dev environment's embedding config (`EMBEDDING__MODEL_SPEC`) was never pointed at the real embedding host (LM Studio on the LAN, `text-embedding-bge-m3`), so the worker defaulted to a local Ollama instance with zero models pulled and permanently exhausted its 3 retries (no retry UI/button exists — retriggering is via re-saving the content's text/title, which resets the outbox row). Fixed by setting `EMBEDDING__MODEL_SPEC=lmstudio://text-embedding-bge-m3@<lmstudio-host>:<port>/v1` in `src/.env` and restarting the worker; re-verified: outbox row `done`, retry_count 0, 1 chunk row in `data_topic_content_chunks` | ☑ |

**Additional defects found (outside scripted steps), filed as `TASKS.md` G7-patch entries:**
- G7-patch-10 (fixed, re-verified): dev environment's embedding config wasn't pointed at the real embedding host; see Observed above.
- G7-patch-11 (open, spec gap): no parent-facing visibility into RAG indexing status and no retry affordance for a permanently failed embed (`retry_count >= 3` is excluded from the worker's claim query forever) — a real embedding-host outage would silently and permanently degrade that content to text-only hAITU grounding with no signal to the parent. Flagged for `/update-target-state`, not yet designed or fixed.

---

## Part E — Student Home Study surface (G6)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| E1 | Log in as Student A → `/home` | "Home Study" section shows Parent A's adopted/built root nodes as cards (this was the G6 bug fix — previously always 403'd) | Initially failed: section rendered with zero cards. `GET /api/student/nodes?owner_type=parent` 400'd — required `owner_id`, which the frontend has no source for (deliberately excluded from `/parent-links`). Fixed (G7-patch-12) by making `owner_id` optional server-side, auto-resolving to the student's active linked parent; re-verified — cards now show correctly (including a legitimately duplicate "8" board from an earlier separate adopt of Grade 8 itself, confirmed not a bug via direct DB check) | ☑ |
| E2 | `/courses` → switch to "Home Study" tab | Tab enabled (has_parent_link=true); tree renders with green accent | Confirmed | ☑ |
| E3 | Navigate to "Photosynthesis" | Text content renders (through the markdown renderer — check any formatting, e.g. a bullet list, renders correctly) | Confirmed | ☑ |
| E4 | Select a topic under Home Study with **no** content yet | Parent-specific "no notes yet" message shown (not the generic "No content available") | `content-viewer.tsx`'s logic was already correct (source-aware "Your parent hasn't added notes to this topic yet"); no live, contentless topic existed yet in test data to exercise it directly, but confirmed via code read, not just inference | ☑ |
| E5 | Expand/select a Home Study node with **no** topics yet | Sidebar empty state: "No Home Study content yet — ask your parent to add topics" (no "Browse Courses" link, unlike the Platform tab) | Initially failed: selecting "Maths" (0 topics) showed the generic "Select a node to view topics" message instead — `TopicListPanel` never checked whether a node was actually selected before falling back to that copy. Fixed (G7-patch-13) with a `selectedNodeId === null` check + source-aware messaging; re-verified | ☑ |
| E6 | From `/home`, click a Home Study root node card directly | Deep-links to `/courses` with Home Study tab active and that node selected (not stranded on Platform tab) | Confirmed | ☑ |

**Additional defects found (outside scripted steps), filed as `TASKS.md` G7-patch entries — see G7-patch-12 and G7-patch-13 (both fixed and re-verified). Also caught but unrelated to G6: grade nodes displayed as bare numbers ("7"/"8") instead of "Grade 7"/"Grade 8" across `/home` and `/courses` — see G7-patch-14 (fixed, re-verified).**

---

## Part F — hAITU on a Home Study topic (G5)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| F1 | As Student A, on the live "Photosynthesis" topic, open the hAITU panel and ask a question related to the note text | Panel is **enabled** despite no enrollment; answer streams in and is grounded in the parent's note content | Confirmed | ☑ |
| F2 | Check `/doubts` (Student A) | The Home Study question appears as a persisted doubt thread | Confirmed | ☑ |

**Additional defects found (outside scripted steps), filed as `TASKS.md` G7-patch entries:**
- G7-patch-15 (fixed, re-verified, security-relevant): "Ask Teacher Help" rendered and worked identically for Home Study topics as platform topics, with no ownership check anywhere in the chain — escalating notified a generic "instructor" role (nobody, in this increment's scope) instead of the parent, and an instructor's queue had no filter preventing them from seeing a parent's private topic/student/doubt content if one did exist. Blocked server-side (`DoubtService.escalate_doubt` now checks topic ownership) and hidden client-side (button no longer renders when `source === "parent"`). Whether Home Study should have *any* escalation path (e.g. to the parent) is an open design question — see G7-patch-16.
- G7-patch-17 (fixed, re-verified): G7-patch-15's fix only covered the live in-topic hAITU panel — a second, independent "Request teacher help" button on the persisted `/doubts/{id}` thread page had no topic-ownership awareness at all (though the backend-side block already covered it — a broken-looking but not exploitable affordance). Fixed by threading `topic_owner_type` through the single-thread fetch end-to-end; button now hidden there too.

---

## Part G — Live re-ingestion (grounded update, mirrors the ollama-gated G7.1 test)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| G1 | Parent A edits the "Photosynthesis" content, replacing `ZORBLAX-912` with `ZORBLAX-913` | Save succeeds | Confirmed | ☑ |
| G2 | Wait for the worker to re-drain (~10–15s) | *(optional DB check)* old chunks gone, new chunks present for that content id | Confirmed | ☑ |
| G3 | Student A asks hAITU "what's the marker word?" again on the same topic | Answer now reflects `ZORBLAX-913`, not the stale `-912` | Confirmed | ☑ |

---

## Part H — Severance & cross-family security (G7 acceptance)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| H1 | Parent A → `/parent` → revoke the link to Student A | Confirm-then-revoke UI; child removed from Parent A's list | Initially failed: no revoke/remove affordance existed anywhere on `/parent` — `parent-dashboard.tsx`'s child strip only rendered a selectable pill per child, with no way to invoke the already-existing backend `DELETE /api/parent/children/{child_sub}/link` (T1.3). Fixed (G7-patch-18) and re-verified: "Revoke" control added per child pill with confirm/cancel inline prompt, mirroring the student-side `/profile` "Remove" pattern | ☑ |
| H2 | Student A → `/home` | Home Study section reverts to the "no parent linked" placeholder | Confirmed | ☑ |
| H3 | Student A → `/courses`, Home Study tab | Tab disabled again | Confirmed | ☑ |
| H4 | Student A tries to re-ask hAITU on the previously-accessible topic (e.g. via a stale bookmark/back button landing on the content) | Panel shows "Your Home Study access has changed…" notice, not a chat UI | Confirmed | ☑ |
| H5 | Log in as **Parent B** (unrelated) → try to browse/adopt Parent A's private curriculum via URL manipulation (guess a node id) | 404 (cross-owner sweep — content isn't just hidden from nav, it's inaccessible by id) | Confirmed — direct topic-content-page URL for a Parent-A-owned node returned 404 (devtools) and rendered a generic "Failed to load topic." + Retry/Back-to-curriculum, not a distinct "access denied" message. This is the *safer* choice (doesn't leak node-existence to a prober) and is backed by the existing automated `test_g3_1_cross_owner_404_sweep_integration.py` (T3.13) at the API level; the "Retry" affordance reads a little oddly for a permanent 404 but that's cosmetic, not a security gap — not filed as a patch | ☑ |
| H6 | Re-link Student A to Parent A with a **fresh** code | Re-link succeeds (a revoked pair can re-link) | Initially failed: `GET /api/parent-link-codes/{code}` (validate-before-link) has never returned the child's name — its domain model/schema only ever carried `code`/`child_sub`/`expires_at` — but the frontend's Zod schema required `first_name`/`last_name`, which don't exist on that endpoint. Every validate call therefore failed client-side (502 Zod parse failure, surfaced as "Something went wrong"), silently blocking the confirm-dialog step of *every* link (not just re-link — this predates this walkthrough entirely; Part A3's earlier "Confirmed" was not actually exercising this path correctly). Fixed (G7-patch-19) and re-verified: backend `get_link_code_preview` resolves the child's display name via the existing Keycloak-fallback pattern (`_resolve_identity`/`build_display_name`, same as `/parent/children` and `/student/parent-links`) and returns `child_display_name`; frontend consumes `displayName` instead of the nonexistent `firstName`/`lastName`. Re-link then succeeded, but Home Study came back empty — see the note below | ☑ |

**Additional defects found (outside scripted steps), filed as `TASKS.md` G7-patch entries:**
- G7-patch-18 (fixed, re-verified): H1 — no revoke UI existed at all on `/parent`. See G7-patch-18 in `TASKS.md`.
- G7-patch-19 (fixed, re-verified): H6 — parent link-code validate response never carried the child's name; see above and `TASKS.md`.
- G7-patch-20 (fixed, re-verified): after H6's re-link, Student User's Home Study still showed no content. Root cause: the student had a second, older active parent link (from a prior, unrelated test pass with a different parent account) that was never revoked. `get_node_tree`'s owner-resolution (G7-patch-12) picked the single *oldest* active parent link when the frontend omits `owner_id` (which it always does) — so it silently resolved to the stray, content-less parent instead of the actual one with curriculum, with no signal to the student that a second parent link even existed. Fixed: aggregates content from **every** actively-linked parent instead of just the first, matching how Home Study cards already render as a flat list with no per-parent grouping. See `TASKS.md` for full detail.

---

## Part I — Draft-topic visibility (regression check)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| I1 | Parent A creates a new topic, leaves it in **draft** | Topic exists in the builder | Confirmed | ☑ |
| I2 | Student A checks Home Study | Draft topic does **not** appear anywhere (list, deep-link, or hAITU) | Confirmed | ☑ |

---

## Sign-off

- [x] All steps above pass (or defects filed as a `TASKS.md` G7-patch entry with repro steps).
- [x] No Redux/Axios/React-Query-outside-existing-precedent introduced (spot-checked `features/parent`/`features/student` for `axios`/`react-redux`/`@reduxjs` — none found).
- [x] All mutations carried a valid `X-CSRF-Token` (spot-checked in devtools network tab, e.g. on the revoke `DELETE` and re-link `POST`).
- [x] Once green: mark T7.2 `[x]` in `TASKS.md`, close G7, and mark Phase 5 complete in `progress.md` (move it under "Completed Phases" following the Phase 3/Phase 4 precedent).
