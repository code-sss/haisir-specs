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
| P1 | Full stack up via `haisir-deploy` docker compose (backend, worker, frontend, APISIX, Postgres pgvector) | ☐ |
| P2 | Worker running with RAG outbox + embedding configured (`bge-m3` reachable) — needed for Part D/G | ☐ |
| P3 | Two browser sessions (or one normal + one incognito) so you can be logged in as **Parent A** and **Student A** at once | ☐ |
| P4 | A second parent account (**Parent B**) for the cross-family check in Part H | ☐ |
| P5 | A platform board with at least one live topic exists (Admin-created), for the "Adopt from Platform" step | ☐ |

---

## Part A — Parent–child linking (G1, re-confirm) + workspace shell (G2)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| A1 | Log in as **Student A** → `/profile` → "Parent Access" card → generate/copy link code | 8-char code shown, copy-to-clipboard works | | ☐ |
| A2 | Log in as **Parent A** → onboarding "Parent Ready" screen → "Link your child" CTA | Lands on `/parent/link-child`, **not** a dead link (this was the G2 T2.6 fix) | | ☐ |
| A3 | On `/parent/link-child`, enter the code (auto-uppercased as you type) | Confirm dialog shows the correct child's name; Escape cancels it, focus returns to the trigger button | | ☐ |
| A4 | Confirm the link | Redirects to `/parent`, child appears in the child-selector strip | | ☐ |
| A5 | Reload `/parent` | Selected child persists (localStorage) | | ☐ |
| A6 | Check header nav as Parent A | "Dashboard" and "Curriculum" links present; as Student A, "Profile" link present | | ☐ |
| A7 | Try `/parent` while logged in as Student A (URL bar) | Redirected away (route guard) | | ☐ |

---

## Part B — Curriculum builder: build from scratch (G3.3)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| B1 | Parent A → `/parent/curriculum` (first visit, empty) | Centered "No curriculum yet" with Adopt/Build actions | | ☐ |
| B2 | Click "Build from scratch" → add a root node (e.g. type `grade`, name "Grade 7") | Node appears in the left tree, selected | | ☐ |
| B3 | Add a child node under it (e.g. `subject` "Science") | Hierarchy rules enforced — same chip-lock behavior as Admin's `AddNodeModal` | | ☐ |
| B4 | Add a topic under the leaf node, e.g. "Photosynthesis" | Topic appears in the right panel topic list, status = draft | | ☐ |
| B5 | Open the topic (P-topic page) → rename title inline | Saves without a page reload | | ☐ |
| B6 | Add **text** content to the topic (paste a paragraph containing a unique marker word, e.g. `ZORBLAX-912`) | Content saved; `ParentTopicRow` back on the builder page now shows no "no notes yet" chip for this topic | | ☐ |

---

## Part C — Curriculum builder: adopt from platform (G3.3)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| C1 | Click "Adopt from Platform" | Modal opens, focus-trapped; board `<select>` populated from `GET /api/categories` | | ☐ |
| C2 | Pick a board → expand the lazy-loaded node tree → select a node | Row shows selected (`aria-pressed`); "Adopt" enables | | ☐ |
| C3 | Click "Adopt" | New root node appears in the parent's tree, cloned structure (nodes + topics, no content, topics reset to draft) | | ☐ |
| C4 | Re-open Adopt modal, adopt the **same** node again | 409 surfaced inline as "You have already adopted this board." (not a generic error) | | ☐ |

---

## Part D — Publish + RAG drain (G4, re-confirm end-to-end)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| D1 | On the "Photosynthesis" topic from Part B, toggle draft → live | Topic status flips to live | | ☐ |
| D2 | Wait ~10–15s (worker outbox poll) | *(optional DB check)* `SELECT status FROM rag_indexing_outbox WHERE content_id = '<id>'` → `done`; `SELECT count(*) FROM data_topic_content_chunks WHERE metadata_->>'content_id' = '<id>'` → > 0 | | ☐ |

---

## Part E — Student Home Study surface (G6)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| E1 | Log in as Student A → `/home` | "Home Study" section shows Parent A's adopted/built root nodes as cards (this was the G6 bug fix — previously always 403'd) | | ☐ |
| E2 | `/courses` → switch to "Home Study" tab | Tab enabled (has_parent_link=true); tree renders with green accent | | ☐ |
| E3 | Navigate to "Photosynthesis" | Text content renders (through the markdown renderer — check any formatting, e.g. a bullet list, renders correctly) | | ☐ |
| E4 | Select a topic under Home Study with **no** content yet | Parent-specific "no notes yet" message shown (not the generic "No content available") | | ☐ |
| E5 | Expand/select a Home Study node with **no** topics yet | Sidebar empty state: "No Home Study content yet — ask your parent to add topics" (no "Browse Courses" link, unlike the Platform tab) | | ☐ |
| E6 | From `/home`, click a Home Study root node card directly | Deep-links to `/courses` with Home Study tab active and that node selected (not stranded on Platform tab) | | ☐ |

---

## Part F — hAITU on a Home Study topic (G5)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| F1 | As Student A, on the live "Photosynthesis" topic, open the hAITU panel and ask a question related to the note text | Panel is **enabled** despite no enrollment; answer streams in and is grounded in the parent's note content | | ☐ |
| F2 | Check `/doubts` (Student A) | The Home Study question appears as a persisted doubt thread | | ☐ |

---

## Part G — Live re-ingestion (grounded update, mirrors the ollama-gated G7.1 test)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| G1 | Parent A edits the "Photosynthesis" content, replacing `ZORBLAX-912` with `ZORBLAX-913` | Save succeeds | | ☐ |
| G2 | Wait for the worker to re-drain (~10–15s) | *(optional DB check)* old chunks gone, new chunks present for that content id | | ☐ |
| G3 | Student A asks hAITU "what's the marker word?" again on the same topic | Answer now reflects `ZORBLAX-913`, not the stale `-912` | | ☐ |

---

## Part H — Severance & cross-family security (G7 acceptance)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| H1 | Parent A → `/parent` → revoke the link to Student A | Confirm-then-revoke UI; child removed from Parent A's list | | ☐ |
| H2 | Student A → `/home` | Home Study section reverts to the "no parent linked" placeholder | | ☐ |
| H3 | Student A → `/courses`, Home Study tab | Tab disabled again | | ☐ |
| H4 | Student A tries to re-ask hAITU on the previously-accessible topic (e.g. via a stale bookmark/back button landing on the content) | Panel shows "Your Home Study access has changed…" notice, not a chat UI | | ☐ |
| H5 | Log in as **Parent B** (unrelated) → try to browse/adopt Parent A's private curriculum via URL manipulation (guess a node id) | 404 (cross-owner sweep — content isn't just hidden from nav, it's inaccessible by id) | | ☐ |
| H6 | Re-link Student A to Parent A with a **fresh** code | Re-link succeeds (a revoked pair can re-link) | | ☐ |

---

## Part I — Draft-topic visibility (regression check)

| Step | Action | Expected | Observed | Pass/Fail |
|---|---|---|---|---|
| I1 | Parent A creates a new topic, leaves it in **draft** | Topic exists in the builder | | ☐ |
| I2 | Student A checks Home Study | Draft topic does **not** appear anywhere (list, deep-link, or hAITU) | | ☐ |

---

## Sign-off

- [ ] All steps above pass (or defects filed as a `TASKS.md` G7-patch entry with repro steps).
- [ ] No Redux/Axios/React-Query-outside-existing-precedent introduced.
- [ ] All mutations carried a valid `X-CSRF-Token` (spot-check devtools network tab on at least one POST/PATCH/DELETE).
- [ ] Once green: mark T7.2 `[x]` in `TASKS.md`, close G7, and mark Phase 5 complete in `progress.md` (move it under "Completed Phases" following the Phase 3/Phase 4 precedent).
