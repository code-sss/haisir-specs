# PLAN — Phase 5: Parent Curriculum Builder + Link Codes, RAG-Connected

> Written by `/plan` on 2026-07-02 after two challenger rounds (final verdict: APPROVE, no unresolved items).
> Task checkboxes live in `TASKS.md`; decisions from this cycle are logged in `decisions.md`.

## Planning Inputs

- **Root goal:** A parent can link to their child, build/adopt a private curriculum, upload content that flows through extraction + RAG embedding, and the linked child can study it in Home Study and ask hAITU questions grounded in the parent's notes.
- **Repos:** `[backend]` haisir-backend, `[frontend]` haisir-frontend, `[specs]` haisir-specs. **`[deploy]` confirmed not needed** — APISIX wildcard `/api/*` routes + route 16 already cover parent extraction upload; no new gateway routes or timeouts this phase.
- **Migrations:** one new migration, **V40** (adopt lineage). Everything else rides on existing tables (V22/V23 `parent_link_codes` + `parent_child_links`, V26 extraction/outbox, V32/V33 chunks). `topics.status` needs no migration (exists since V18, default `live`, no CHECK constraint — value set enforced at the Pydantic schema layer, recorded in T3.12).
- **Root acceptance (G7):** Student generates a link code → parent redeems it → parent adopts a platform subtree (409 on repeat) → uploads a PDF to an adopted topic → worker extracts + embeds → parent publishes topic `live` → child sees it in the green Home Study section → child asks hAITU (contract-level in CI; grounded-answer assertion ollama-gated) → student revokes the link → Home Study disappears and hAITU returns 403, immediately.

### Embedded design decisions

1. **hAITU authorization for parent-owned topics — parent-link gate, not enrollments.** `HaituTopicDoubtRequest.enrollment_id` becomes optional. `HaituDoubtService._validate_and_build_context` loads the topic **first** and branches: platform-owned topic → existing enrollment-ownership + subtree gate (unchanged, `enrollment_id` required, 403 if absent); parent-owned topic → require an active `parent_child_links` row (`child_sub = caller`, `parent_sub = topic.owner_id`, `revoked_at IS NULL`) **and** `topic.status = 'live'`. This avoids making `student_enrollments` load-bearing on parent nodes (enrollment API is platform-nodes-only by design, `student_enrollment.py:95–107`). The check is per-request with no cache, so revocation severs access immediately. Grade/subject prompt context keeps the existing ancestor walk — parent trees obey the same 3-tier hierarchy. Vector retrieval stays filtered by `topic_id` only; the service-layer gate remains the sole cross-family defense — covered by an explicit cross-family 403 test (T5.3).
2. **Re-ingestion / delete chunk cleanup.** On content **update**: upsert-with-reset the `rag_indexing_outbox` row (`ON CONFLICT (content_id) DO UPDATE SET status='pending', retry_count=0, last_error=NULL, locked_at=NULL, locked_by=NULL` — `updated_at` handled by the existing `trg_rag_outbox_touch` trigger, V26). The **worker** (`rag_outbox_loop._process_row`) deletes stale chunks by `metadata_->>'content_id'` via raw SQL immediately before `insert_nodes` — idempotent re-embed for both re-enqueue and mid-insert-crash retry. On content **delete**: raw-SQL chunk delete + outbox row delete in the same TX as the content delete. Insert-then-delete-stale ordering NOT required for v1 — the brief retrieval gap is accepted.
3. **Adopted topics start RAG-empty.** Clone copies `course_path_nodes` + `topics` only — zero `topic_contents`, zero chunks. UI shows per-topic "No notes yet" states (T4.7a/T4.7b).
4. **Adopt idempotency via lineage column.** V40 adds `course_path_nodes.source_node_id UUID NULL` + partial unique index `(owner_id, source_node_id) WHERE source_node_id IS NOT NULL` (type-safe: `owner_id` is VARCHAR since V23) — repeat-adopt is a DB constraint violation surfaced as 409.
5. **Endpoint-path reconciliation.** The already-live redemption endpoints (`POST /api/parent-child-links`, `GET /api/parent-link-codes/{code}`) are **kept** as-is; the target spec's `POST /api/parent/children/link` alias is corrected in specs. Live error semantics adopted verbatim: **404** unknown code, **410** expired OR already-used code, **409** duplicate parent-child link, **422** (new, T1.4) max-10 cap. Note: the validate GET carries `Depends(validate_csrf)` in live code, so the frontend must send `X-CSRF-Token` even on that GET (m1).

---

## Goal Tree (summary)

```
ROOT: Phase 5 — Parent curriculum builder + link codes, RAG-connected
├── G1: Parent–child linking lifecycle works end-to-end
│   ├── T1.1 [backend]  Student link-code generation + current-code endpoints
│   ├── T1.2 [backend]  Student parent-link list + revoke endpoints
│   ├── T1.3 [backend]  Parent children list + parent-side revoke endpoints
│   ├── T1.4 [backend]  Max-10-children cap on redemption (BR-PAR-016)
│   ├── T1.5 [frontend] /profile page (new) — link-code + linked-parents sections
│   ├── T1.6 [specs]    Link-code semantics + physical endpoint paths
│   └── T1.7 [backend]  G1 integration test — full link round-trip
├── G2: Parent workspace shell + route guard
│   ├── T2.1 [frontend] ParentRouteGuard component
│   ├── T2.2 [frontend] /parent layout + P-home dashboard (child strip, empty state)
│   ├── T2.3 [frontend] /parent/link-child page (P-link)
│   ├── T2.4 [frontend] Parent header nav (+ G2 verification)
│   ├── T2.5 [specs]    /parent route-guard slice into target 05_parent.md
│   └── T2.6 [frontend] Onboarding parent-ready CTA dead-link fix
├── G3: Parent curriculum builder (structure + content authoring)
│   ├── G3.1: Curriculum structure API
│   │   ├── T3.1  [backend] V40 migration — source_node_id lineage
│   │   ├── T3.2a [backend] Parent node CRUD (owner-scoped)
│   │   ├── T3.2b [backend] Node hierarchy validation for parent trees
│   │   ├── T3.2c [backend] Node cascade delete + exam-session guard
│   │   ├── T3.3  [backend] Parent read access to platform tree (adopt browse)
│   │   ├── T3.4  [backend] Adopt/clone service + endpoint (409 idempotent)
│   │   ├── T3.5  [backend] Parent topic CRUD + draft/live publish
│   │   └── T3.13 [backend] G3.1 integration test — cross-owner 404 sweep
│   ├── G3.2: Content authoring API
│   │   └── T3.6 [backend] Parent instant content create + owner-scoped PATCH/DELETE
│   └── G3.3: Builder UI
│       ├── T3.7  [frontend] features/parent API client + types
│       ├── T3.8  [frontend] /parent/curriculum builder page (tree + topics)
│       ├── T3.9  [frontend] Adopt modal (platform browse, 409 handling)
│       ├── T3.10 [frontend] Parameterize shared content components (admin↔parent)
│       ├── T3.11 [frontend] P-topic Topic Content Manager page
│       └── T3.12 [specs]    05_parent.md + 01_data_model.md builder/V40 updates
├── G4: RAG ingestion + re-ingestion lifecycle
│   ├── T4.1  [backend]  Outbox enqueue on instant text-content create
│   ├── T4.2  [backend]  Outbox upsert-with-reset repository helper
│   ├── T4.3  [backend]  Re-enqueue on content update
│   ├── T4.4  [backend]  Chunk + outbox cleanup on content delete
│   ├── T4.5  [backend]  Worker delete-stale-chunks-before-insert (idempotent re-embed)
│   ├── T4.6  [backend]  Cascade RAG cleanup on topic/node delete
│   ├── T4.7a [frontend] "No notes yet" hint in parent builder
│   ├── T4.7b [frontend] "No notes yet" placeholder in student content viewer
│   ├── T4.8  [specs]    Re-ingestion contract into 12_content_extraction.md §5 + 01_data_model.md
│   └── T4.9  [backend]  G4 integration test — content→chunk lifecycle
├── G5: hAITU answers on parent-owned topics
│   ├── T5.1 [backend]  Optional enrollment_id in topic-doubt schema
│   ├── T5.2 [backend]  Parent-link authorization gate in HaituDoubtService
│   ├── T5.3 [backend]  Severance + cross-family 403 tests (G5 integration test)
│   ├── T5.4 [frontend] HaituDoubtPanel enabled for Home Study topics
│   └── T5.5 [specs]    11_haitu_ai_layer.md §9 — parent-topic access contract
├── G6: Student Home Study surface complete
│   ├── T6.1 [backend]  Live-only + visibility enforcement tests (G6 integration test)
│   ├── T6.2 [frontend] Source-aware empty state in existing Home Study tree
│   └── T6.3 [frontend] Home Study content viewing verification
└── G7: Phase acceptance
    ├── T7.1 [backend]  E2E journey test (contract-level, CI-safe) + ollama-gated grounded variant
    └── T7.2 [frontend] Frontend closure — suites green + manual walkthrough
```

---

## G1 — Parent–child linking lifecycle works end-to-end

**Goal**: A student can generate/rotate a link code and manage links; a parent can redeem the code and manage children; revocation from either side severs access immediately.
**Goal test**: T1.7.
**Repos**: [backend] [frontend] [specs]

##### T1.1 [backend] — Student link-code generation + current-code endpoints
- **Build**: New route module `src/api/routes/student_links.py` registered under `/api/student` (third router on this prefix, coexisting with `student_dashboard` and `student_enrollment` — new sub-paths `parent-link-codes` and `parent-links` collide with none of the existing `/dashboard`, `/nodes`, `/nodes/{id}/topics`, `/topics/{id}/content`, `/catalog`, `/enrollments`). `POST /api/student/parent-link-codes` (student role + CSRF): invalidate any existing unused codes for `child_sub = user.sub` (`is_used = true`), insert a new `parent_link_codes` row — 8-char uppercase A–Z/2–9 code via `secrets`, `expires_at = now() + 72h` (columns verified: V22). `GET /api/student/parent-link-codes`: return the current active (unused, unexpired) code or 404. Service methods on `UserMetadataService`; repository methods on the existing user-metadata repo. No business logic in the route file.
- **Done when**: `POST /api/student/parent-link-codes` returns 201 with a fresh code and the previously active code row has `is_used = true`.
- **Test**: `assert old_code_row.is_used is True and new_code != old_code`
- **Depends on**: None.

##### T1.2 [backend] — Student parent-link list + revoke endpoints
- **Build**: In `student_links.py`: `GET /api/student/parent-links` (student) — active links for `child_sub = user.sub` with parent display name joined from `parent_profiles`; `DELETE /api/student/parent-links/{link_id}` (student + CSRF) — set `revoked_at = now()`; 404 if the link doesn't exist or `child_sub != user.sub` (enumeration protection).
- **Done when**: DELETE returns 204 and the `parent_child_links` row has `revoked_at IS NOT NULL`.
- **Test**: `assert response.status_code == 204 and link_row.revoked_at is not None`
- **Depends on**: None.

##### T1.3 [backend] — Parent children list + parent-side revoke endpoints
- **Build**: New route module `src/api/routes/parent_children.py` under `/api/parent/children`. `GET /api/parent/children` (parent) — active links for `parent_sub = user.sub`, child names joined from `student_profiles`. `DELETE /api/parent/children/{child_sub}/link` (parent + CSRF) — set `revoked_at`; 404 on no active link.
- **Done when**: `GET /api/parent/children` returns `[{child_sub, first_name, last_name, linked_at}]` for active links only (revoked links excluded).
- **Test**: `assert all(c["child_sub"] != revoked_child for c in response.json())`
- **Depends on**: None.

##### T1.4 [backend] — Max-10-children cap on redemption (BR-PAR-016)
- **Build**: In `UserMetadataService.create_parent_child_link` (used by the existing `POST /api/parent-child-links`): count active links for `parent_sub`; if ≥ 10, raise a new `ParentChildLinkLimitError` → 422 in the route.
- **Done when**: The 11th redemption attempt for one parent returns 422 with a "maximum of 10 linked children" detail.
- **Test**: `assert response.status_code == 422` (after seeding 10 active links)
- **Depends on**: None.

##### T1.5 [frontend] — /profile page (new) with link-code + linked-parents sections
- **Build**: **Create-from-scratch** `src/app/profile/page.tsx` (S-profile, student role; no profile page exists today) + `features/student` components: Parent Link Code card — shows current code (`GET /api/student/parent-link-codes`), "Generate new code" (`POST`, via `fetchWithCSRFRetry` + `buildApiHeaders`), copy-to-clipboard, share instructions; Linked Parents card — list from `GET /api/student/parent-links` with "Remove" (confirm dialog → DELETE). Add "Profile" link to the student header.
- **Done when**: Generating a code renders the new code and the "Remove" action removes a parent row without page reload.
- **Test**: `expect(screen.getByText(mockCode)).toBeInTheDocument()` after generate click.
- **Depends on**: T1.1 [backend], T1.2 [backend].

##### T1.6 [specs] — Link-code semantics + physical endpoint paths
- **Build**: Update `target/requirements/03_student.md` (S-profile section) and `target/requirements/05_parent.md` (P-link + endpoint table): code format (8-char), TTL (72h), single-active-code rotation, max-10 rule; correct the endpoint table — redemption stays at `POST /api/parent-child-links` + `GET /api/parent-link-codes/{code}` (live paths; document 404/410/409/422 semantics as shipped and the CSRF-on-validate-GET quirk), new `GET /api/parent/children`, `DELETE /api/parent/children/{child_sub}/link`, and the student-side endpoints.
- **Done when**: Both spec files list the physical paths and code semantics with no reference to the unimplemented `/api/parent/children/link` alias.
- **Test**: Grep both files — `parent/children/link` absent, `parent-child-links` present.
- **Depends on**: T1.1, T1.3 (contract finalized).

##### T1.7 [backend] — G1 integration test: full link round-trip
- **Build**: Integration test: student generates code → parent validates (`GET /api/parent-link-codes/{code}`) → redeems (`POST /api/parent-child-links`) → link present in both `GET /api/student/parent-links` and `GET /api/parent/children` → student revokes → both lists empty, `revoked_at` set.
- **Done when**: The round-trip test passes in the standard integration suite.
- **Test**: This is the G1 goal test.
- **Depends on**: T1.1, T1.2, T1.3, T1.4 [backend].

---

## G2 — Parent workspace shell + route guard

**Goal**: A user with the `parent` active role has a guarded `/parent` app area with a dashboard and a working link-child flow; other roles are redirected away.
**Goal test**: T2.4's verification Done-when covers the redirect matrix in component tests; the in-browser pass is recorded in the T7.2 manual walkthrough.
**Repos**: [frontend] [specs]

##### T2.1 [frontend] — ParentRouteGuard component
- **Build**: `src/features/parent/components/parent-route-guard.tsx` cloned from `src/features/admin/components/admin-route-guard.tsx`: `useAuth` → redirect to `/` if unauthenticated, to `/home` if `currentRole !== "parent"`; spinner while loading. Note: this component guard deliberately coexists with the central `canAccessRoute`/`ROUTE_ROLE_REQUIREMENTS` logic in `use-auth.ts` (which already contains a `/parent` prefix entry) — mirroring the admin pattern; do not deduplicate either away.
- **Done when**: Rendering the guard with `currentRole = "student"` triggers `router.replace("/home")` and renders null.
- **Test**: `expect(mockRouter.replace).toHaveBeenCalledWith("/home")`
- **Depends on**: None.

##### T2.2 [frontend] — /parent layout + P-home dashboard
- **Build**: `src/app/parent/layout.tsx` (wraps children in ParentRouteGuard) + `src/app/parent/page.tsx`: child selector strip from `GET /api/parent/children` (name pills, active-child state in React state/localStorage); when zero children, a prominent "Link your child" card → `/parent/link-child`; nav cards to `/parent/curriculum`. New `features/parent/` feature dir (api/, components/, types/) per the features/* pattern.
- **Done when**: A parent with one linked child sees the child pill; with zero children sees the link card instead.
- **Test**: `expect(screen.getByText("Link your child")).toBeInTheDocument()` when children list is empty.
- **Depends on**: T2.1 [frontend], T1.3 [backend].

##### T2.3 [frontend] — /parent/link-child page (P-link)
- **Build**: `src/app/parent/link-child/page.tsx`: code input → validate via `GET /api/parent-link-codes/{code}` — **must send `X-CSRF-Token` on this GET** (live route has `Depends(validate_csrf)`; use `fetchWithCSRFRetry`) — shows child name for confirmation → `POST /api/parent-child-links` with `{invite_code}` (CSRF). Error states matching live semantics: **404** "Invalid code", **410** "Code expired or already used", **409** "This child is already linked", **422** "Maximum of 10 children".
- **Done when**: Entering a valid code and confirming navigates back to `/parent` with the new child in the strip; each of the four error statuses renders its distinct message.
- **Test**: `expect(screen.getByText(/invalid code/i)).toBeInTheDocument()` on mocked 404.
- **Depends on**: T2.1 [frontend], T1.4 [backend].

##### T2.4 [frontend] — Parent header nav (+ G2 verification)
- **Build**: Extend the shared header for `currentRole === "parent"`: nav links "Dashboard" (`/parent`), "Curriculum" (`/parent/curriculum`). The `/` → `/parent` redirect and `ROUTE_ROLE_REQUIREMENTS` `/parent` entry already exist (`app/page.tsx:58–59`, `use-auth.ts:81,92`) — verify with component tests covering the G2 redirect matrix (parent → `/parent` renders; student at `/parent` → `/home`; unauthenticated → `/`).
- **Done when**: With parent role active, the header shows parent links and no student/admin links; the redirect-matrix tests pass.
- **Test**: `expect(screen.getByRole("link", { name: "Curriculum" })).toHaveAttribute("href", "/parent/curriculum")`
- **Depends on**: T2.2 [frontend].

##### T2.5 [specs] — /parent route-guard slice into target spec
- **Build**: Add a "Routing & guard" note to `target/requirements/05_parent.md`: `/parent/*` requires active role `parent` (client guard mirrors `admin-route-guard`), redirect matrix, and the onboarding CTA path — porting only the `/parent` slice from `vision/requirements/11_role_migration.md` §5.5.
- **Done when**: 05_parent.md documents the guard behavior and redirect targets.
- **Test**: Section present; no other role-migration scope imported.
- **Depends on**: T2.1 (behavior finalized).

##### T2.6 [frontend] — Onboarding parent-ready CTA dead-link fix
- **Build**: Repoint the existing dead link in `src/features/onboarding/components/on05-parent-ready.tsx:82` from `/link-child` (route does not exist) to `/parent/link-child`.
- **Done when**: The parent-ready View B CTA navigates to the working P-link page.
- **Test**: `grep -c '"/parent/link-child"' on05-parent-ready.tsx` returns 1 (and component test asserts the href).
- **Depends on**: T2.3 [frontend].

---

## G3 — Parent curriculum builder (structure + content authoring)

**Goal**: A parent can adopt a platform subtree or build a tree from scratch, manage topics (draft/live), and attach content (instant video/text + PDF/image extraction) — all scoped to `owner_id = parent.idp_sub`.
**Goal test**: T3.13 (API level); the in-browser G3.3 pass (adopt → add node/topic → upload PDF → jobs strip → provenance badges → publish toggle) is recorded in the T7.2 manual walkthrough.
**Repos**: [backend] [frontend] [specs]

#### G3.1 — Curriculum structure API
**Subgoal**: Owner-scoped node/topic CRUD + idempotent adopt exist and enforce hierarchy rules.
**Subgoal test**: T3.13.
**Repos**: [backend]

##### T3.1 [backend] — V40 migration: adopt lineage column
- **Build**: Alembic migration V40: `ALTER TABLE course_path_nodes ADD COLUMN source_node_id UUID NULL;` + partial unique index `ux_course_path_nodes_adopt_lineage ON (owner_id, source_node_id) WHERE source_node_id IS NOT NULL`. Additive; no backfill. Update the imperative-mapped table def in `src/infrastructure/models/course_path_node.py`. Single-purpose migration — no other schema changes.
- **Done when**: `alembic upgrade head` applies cleanly and inserting two rows with the same `(owner_id, source_node_id)` raises IntegrityError.
- **Test**: `with pytest.raises(IntegrityError): insert_duplicate_lineage_row()`
- **Depends on**: None.

##### T3.2a [backend] — Parent node CRUD endpoints (owner-scoped)
- **Build**: New `src/api/routes/parent_curriculum.py` — a **second router on the existing `/api/parent/curriculum` prefix, coexisting with `parent_extraction.py`** (its paths `/topics/{topic_id}/extraction-jobs`, `/extraction-jobs/{job_id}`, `/extraction-jobs/{job_id}/retry` do not collide with the new `/nodes*`, `/adopt`, `/topics/{id}`, `/topic-contents/{id}`) + `src/domain/services/parent_curriculum_service.py`. Endpoints: `GET /nodes` (parent's root nodes), `GET /nodes/{id}` (detail + children), `POST /nodes` (create; root requires `category_id` from platform categories; sets `owner_type='parent'`, `owner_id=user.sub`), `PATCH /nodes/{id}` (rename). All reads/writes filter `owner_id = user.sub`; wrong owner → 404. Extend `AbstractCoursePathNodeRepository` port + SQLAlchemy adapter with owner-scoped methods. Parent role + CSRF on mutations.
- **Done when**: Parent A's `GET /nodes/{id}` on parent B's node returns 404.
- **Test**: `assert cross_owner_response.status_code == 404`
- **Depends on**: T3.1 [backend] (model includes new column).

##### T3.2b [backend] — Node hierarchy validation for parent trees
- **Build**: In `parent_curriculum_service`: enforce the 9-value node-type rules on POST/PATCH with **sibling-type consistency scoped to same-owner siblings** (root=grade, under-grade=subject, deeper=any non-ancestor type); violations → 409.
- **Done when**: Creating a `subject` node at root returns 409.
- **Test**: `assert response.status_code == 409` for subject-at-root.
- **Depends on**: T3.2a [backend].

##### T3.2c [backend] — Node cascade delete + exam-session guard
- **Build**: `DELETE /nodes/{id}` — cascade delete subtree + topics; 409 if any in-progress `exam_sessions` exist under the subtree (BR-PAR-004); owner-scoped 404 otherwise.
- **Done when**: Delete with an in-progress session under the subtree → 409; without → 204 and the subtree rows are gone.
- **Test**: `assert blocked.status_code == 409 and cleared.status_code == 204`
- **Depends on**: T3.2b [backend].

##### T3.3 [backend] — Parent read access to the platform tree (adopt browse)
- **Build**: Allow `parent` role on the read-only platform browse path used by the Adopt modal: extend guards on `GET /api/categories` and the node list/children GETs in `course_path_node.py` to accept `parent`, applying `admin_visibility_clause` (platform-only) for parent viewers — a parent browsing for adoption sees exactly the platform tree, never other parents' trees.
- **Done when**: `GET /api/course-path-nodes?...` with `X-Current-Role: parent` returns platform nodes only (200), where it previously returned 403.
- **Test**: `assert all(n["owner_type"] == "platform" for n in response.json())`
- **Depends on**: None.

##### T3.4 [backend] — Adopt/clone service + endpoint (idempotent 409)
- **Build**: `POST /api/parent/curriculum/adopt` body `{source_node_id}` (parent + CSRF). In `parent_curriculum_service`: validate source node exists and is platform-owned (else 404); deep-copy the `course_path_nodes` subtree (new UUIDs, `owner_type='parent'`, `owner_id=user.sub`, preserve `parent_id` remapping, `order`, `node_type`, `category_id`) + attached `topics` (`owner_type='parent'`, `owner_id=user.sub`, `status='draft'`). Set `source_node_id = {source root id}` on the **cloned root only**. Do NOT copy `topic_contents`, questions, or exam templates (BR-DATA-005). Single transaction; catch the T3.1 unique-index violation → 409 `"You have already adopted this board."`.
- **Done when**: First adopt returns 201 with the cloned root id; identical second adopt returns 409 and node count is unchanged.
- **Test**: `assert second_response.status_code == 409 and node_count_after == node_count_before`
- **Depends on**: T3.1 [backend], T3.2a [backend], T3.3 [backend].

##### T3.5 [backend] — Parent topic CRUD + draft/live publish
- **Build**: In `parent_curriculum.py`: `GET /nodes/{id}/topics`, `POST /nodes/{id}/topics` (creates with `owner_type='parent'`, `owner_id=user.sub`, `status='draft'` default), `PATCH /topics/{id}` (title and/or `status` — **enforced via `Literal["draft","live"]` in the Pydantic PATCH schema**; `topics.status` has no DB CHECK constraint and V40 stays single-purpose), `DELETE /topics/{id}`. Owner checks throughout (404 oracle protection). Extend `AbstractTopicRepository` with owner-scoped methods.
- **Done when**: `PATCH /topics/{id}` with `{"status":"live"}` returns 200 and the row's status is `live`; `{"status":"archived"}` → 422; parent B PATCHing parent A's topic gets 404.
- **Test**: `assert topic_row.status == "live"`
- **Depends on**: T3.2a [backend].

##### T3.13 [backend] — G3.1 integration test: cross-owner 404 sweep
- **Build**: Integration test: parent A performs the full CRUD round-trip (create root node w/ category → child node → topic → publish → adopt a platform subtree); every id is then replayed as parent B (GET/PATCH/DELETE on nodes and topics, adopt of A's node) — all must return 404.
- **Done when**: The sweep passes with zero non-404 responses for parent B.
- **Test**: This is the G3.1 subgoal test.
- **Depends on**: T3.2c, T3.4, T3.5 [backend].

#### G3.2 — Content authoring API
**Subgoal**: Parents create/edit/delete content rows on their own topics with the same shapes as admin.
**Subgoal test**: T3.6's Done-when covers the round-trip (create/edit/delete own → 2xx; platform topic → 404).

##### T3.6 [backend] — Parent instant content create + owner-scoped PATCH/DELETE
- **Build**: `POST /api/parent/curriculum/topics/{topic_id}/content` (parent + CSRF) — instant `topic_contents` row for `video`/`text` types (mirrors admin create incl. title requirement), gated on topic `owner_id = user.sub`. Extend `TopicContentService` with `update_own_content` / `delete_own_content` (topic-owner check; sibling methods to the existing `update_platform_content`/`delete_platform_content`, `topic_content_service.py:141,178`) and expose parent-gated `PATCH`/`DELETE /api/parent/curriculum/topic-contents/{id}`. Admin behavior stays byte-identical. PATCH never clears `source_extraction_job_id` (BR-EXT-023a).
- **Done when**: Parent creates a text row on an own topic (201) and PATCH/DELETE on it succeed, while the same calls against a platform-owned topic return 404.
- **Test**: `assert create_own.status_code == 201 and create_platform_topic.status_code == 404`
- **Depends on**: T3.5 [backend].

#### G3.3 — Builder UI
**Subgoal**: The P-curriculum and P-topic screens work end-to-end against the new API, reusing the admin extraction UI components.
**Subgoal test**: Component tests per task; the in-browser pass (adopt → build → upload → badges → publish) is a T7.2 manual-walkthrough item.
**Repos**: [frontend]

##### T3.7 [frontend] — features/parent curriculum API client + types
- **Build**: `src/features/parent/api/parent-api.ts` + `types/parent.types.ts`: typed raw-fetch functions for all G3.1/G3.2 endpoints (`fetchWithCSRFRetry` on mutations, `buildApiHeaders` incl. `X-Current-Role: parent`), mirroring `features/admin/api` conventions. No Axios/Redux.
- **Done when**: `pnpm typecheck` passes with all endpoint functions exported and typed.
- **Test**: `expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/parent/curriculum/nodes"), expect.objectContaining({method:"POST"}))`
- **Depends on**: T3.2a [backend], T3.5 [backend], T3.6 [backend] (contracts).

##### T3.8 [frontend] — /parent/curriculum builder page
- **Build**: `src/app/parent/curriculum/page.tsx` + `features/parent/components/`: left node-tree panel (expand/collapse, Add Node, Rename inline, Delete with cascade confirm), right panel topic list for the selected leaf (Add Topic, Edit, Delete, Publish toggle with Draft/Live badge), "Adopt from Platform" button, topic rows linking to P-topic. Category picker for scratch root nodes. **Node-type selector**: extract the `isTypeDisabled` hierarchy helper from the admin AddNodeModal into a shared util (e.g. `src/lib/node-type-rules.ts`) consumed by both admin and parent modals; the 9-chip UI itself is copied into `features/parent` (content components are parameterized separately in T3.10 — this selector is out of T3.10's scope by design). Coordination note: T3.8's touch on `features/admin` is limited to the `isTypeDisabled` import swap; coordinate merge order with T3.10, which relocates admin content components concurrently (no dependency needed).
- **Done when**: Creating a node and a topic renders them in the tree/list without reload, and the publish toggle flips the badge.
- **Test**: `expect(screen.getByText("Live")).toBeInTheDocument()` after toggle click (mocked PATCH).
- **Depends on**: T3.7 [frontend], T2.1 [frontend].

##### T3.9 [frontend] — Adopt modal
- **Build**: `AdoptModal` in `features/parent/components/`: browseable platform tree (categories → nodes via the parent-permitted platform GETs), subtree-root selection, "Adopt" → `POST /adopt`; on 201 refresh the tree; on 409 show "You have already adopted this board."
- **Done when**: Selecting a grade node and clicking Adopt inserts the cloned subtree into the left panel; a repeat shows the 409 message inline.
- **Test**: `expect(screen.getByText(/already adopted/i)).toBeInTheDocument()` on mocked 409.
- **Depends on**: T3.7 [frontend], T3.3 [backend], T3.4 [backend].

##### T3.10 [frontend] — Parameterize shared content components for endpoint-base injection
- **Build**: Refactor the admin content components (`add-content-modal.tsx`, the extraction jobs strip/polling hook, `ContentItemRow`, provenance badge) to accept an API adapter/base ({admin: `/api/admin`, `/api/topics-contents`} vs {parent: `/api/parent/curriculum`}) instead of hardcoded admin paths — moving them to a shared location (e.g. `features/content-management/`) or prop-injecting the endpoints. Admin pages must keep byte-identical behavior (existing admin tests stay green). Scope: content components only — the node-type chip selector is handled in T3.8.
- **Done when**: Admin topic page renders unchanged (tests pass) and the components accept a parent adapter without any admin-path constant inside them.
- **Test**: `expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/parent/curriculum/topics/"), …)` when rendered with the parent adapter.
- **Depends on**: None (pure refactor; can start immediately).

##### T3.11 [frontend] — P-topic Topic Content Manager page
- **Build**: `src/app/parent/curriculum/[node_id]/topics/[topic_id]/page.tsx`: editable topic title, Add Content modal (PDF/Image → the already-live parent extraction endpoints with `Idempotency-Key` + pseudo-job upload states; Video/Text → T3.6 instant endpoint), IN PROGRESS jobs strip (2s/10s/stop polling + ETag 304, Cancel/Retry), materialized content rows with provenance badge, inline title rename + edit modal + delete (parent PATCH/DELETE paths).
- **Done when**: Uploading a PDF shows the pseudo-job → real job progression, and on `done` the new text rows appear with "from {filename} · p.N" badges.
- **Test**: `expect(screen.getByText(/from chapter1.pdf/i)).toBeInTheDocument()` with mocked done-job + contents payload.
- **Depends on**: T3.10 [frontend], T3.7 [frontend], T3.5 [backend], T3.6 [backend].

##### T3.12 [specs] — Builder + V40 spec updates
- **Build**: `target/requirements/01_data_model.md`: new "Schema Extensions (Phase 5)" section — V40 `source_node_id` + partial unique index, adopt-idempotency mechanics (BR-DATA-006 now DB-enforced), category rule for scratch roots, sibling-type consistency scoped per-owner, and a note that `topics.status` values are schema-enforced (`Literal["draft","live"]`), no DB CHECK constraint. `target/requirements/05_parent.md`: reconcile the endpoint table with the physical paths shipped (adopt body, topic-content PATCH/DELETE paths, platform-browse access note).
- **Done when**: Both files describe V40 and the shipped endpoint set with no stale paths.
- **Test**: 01_data_model.md contains `source_node_id`; 05_parent.md endpoint table matches the OpenAPI paths.
- **Depends on**: T3.4, T3.6 (contracts final).

---

## G4 — RAG ingestion + re-ingestion lifecycle

**Goal**: Every text-content mutation (create/update/delete, admin or parent, manual or extracted) converges the chunk store: new text gets embedded, edited text replaces its stale chunks, deleted content leaves zero chunks; adopted topics honestly present as RAG-empty.
**Goal test**: T4.9.
**Repos**: [backend] [frontend] [specs]

##### T4.1 [backend] — Outbox enqueue on instant text-content create
- **Build**: In `TopicContentService.create` (admin path) and the T3.6 parent create: when `content_type == 'text'` and text is non-empty, enqueue via the T4.2 helper in the same TX. Video/pdf/url rows are not enqueued.
- **Done when**: `POST` of a text content row leaves a pending outbox row with that `content_id`.
- **Test**: `assert outbox_row.status == "pending"`
- **Depends on**: T4.2 [backend], T3.6 [backend].

##### T4.2 [backend] — Outbox upsert-with-reset repository helper
- **Build**: `enqueue_content(content_id)` on the outbox repository (or a new `rag_outbox_repository`): `INSERT INTO rag_indexing_outbox (content_id, status) VALUES (:id,'pending') ON CONFLICT (content_id) DO UPDATE SET status='pending', retry_count=0, last_error=NULL, locked_at=NULL, locked_by=NULL` — `updated_at` is touched by the existing `trg_rag_outbox_touch` BEFORE UPDATE trigger (V26), so it is deliberately omitted from the SET list. Resolves the PK collision with lingering `done`/`failed` rows (purge only clears `done` after 24h).
- **Done when**: Calling the helper when a `done` row exists for the same `content_id` resets it to `pending` with `retry_count=0`.
- **Test**: `assert refreshed_row.status == "pending" and refreshed_row.retry_count == 0`
- **Depends on**: None.

##### T4.3 [backend] — Re-enqueue on content update
- **Build**: In `update_platform_content` and `update_own_content` (T3.6): if the update changes `text` or `title` on a `text` content row, call `enqueue_content(content_id)` in the same TX. Title changes re-enqueue too (title is embedded in chunk text/metadata).
- **Done when**: PATCHing a text row's body flips its outbox row back to `pending`.
- **Test**: `assert outbox_row_after_patch.status == "pending"`
- **Depends on**: T4.2 [backend], T3.6 [backend].

##### T4.4 [backend] — Chunk + outbox cleanup on content delete
- **Build**: In `delete_platform_content` / `delete_own_content`: within the delete TX run raw SQL `DELETE FROM data_topic_content_chunks WHERE metadata_->>'content_id' = :cid` and `DELETE FROM rag_indexing_outbox WHERE content_id = :cid`. Raw SQL is the sanctioned path — the chunk table is LlamaIndex-owned with no ORM mapping beyond the V32 shim.
- **Done when**: After DELETE of an embedded content row, zero chunk rows and zero outbox rows carry its `content_id`.
- **Test**: `assert chunk_count(content_id) == 0`
- **Depends on**: T3.6 [backend].

##### T4.5 [backend] — Worker delete-stale-chunks-before-insert (idempotent re-embed)
- **Build**: In `src/worker/rag_outbox_loop.py` `_process_row`: before `index.insert_nodes(nodes)`, execute the same raw-SQL chunk delete for `row.content_id`. Makes re-embed idempotent for re-enqueued updates AND retry-after-partial-insert; delete→insert ordering accepted (brief retrieval gap is fine for v1 per locked decision).
- **Done when**: Draining an outbox row for a content_id that already has chunks yields exactly one fresh chunk set (no duplicates).
- **Test**: `assert chunk_count(content_id) == expected_new_chunks` after two consecutive drains.
- **Depends on**: T4.2 [backend].

##### T4.6 [backend] — Cascade RAG cleanup on topic/node delete
- **Build**: In parent topic DELETE (T3.5), parent node cascade DELETE (T3.2c), and the existing admin topic delete path: collect the subtree's `topic_contents` ids and run the T4.4 chunk+outbox cleanup for all of them inside the cascade TX.
- **Done when**: Deleting a parent node whose topics had embedded content leaves zero chunks for any of those content ids.
- **Test**: `assert total_chunk_count_for(subtree_content_ids) == 0`
- **Depends on**: T4.4 [backend], T3.2c [backend], T3.5 [backend].

##### T4.7a [frontend] — "No notes yet" hint in the parent builder
- **Build**: In the T3.8/T3.11 builder surfaces: adopted/created topics with zero contents show a "No notes yet — upload content so hAITU can help your child" hint chip.
- **Done when**: A zero-content parent topic renders the hint chip in the builder topic list.
- **Test**: `expect(screen.getByText(/no notes yet/i)).toBeInTheDocument()` with empty contents mock.
- **Depends on**: T3.11 [frontend].

##### T4.7b [frontend] — "No notes yet" placeholder in the student content viewer
- **Build**: Student side: when a Home Study topic has zero content items, the content viewer shows "Your parent hasn't added notes to this topic yet" instead of an empty pane (data already available from the topic-contents fetch; touches only the existing student content-viewer empty branch).
- **Done when**: A zero-content Home Study topic renders the placeholder in the student viewer.
- **Test**: `expect(screen.getByText(/hasn't added notes/i)).toBeInTheDocument()` with empty contents mock.
- **Depends on**: None (ready now).

##### T4.8 [specs] — Re-ingestion contract into specs
- **Build**: `target/requirements/12_content_extraction.md` §5 (outbox handoff): document upsert-with-reset, worker delete-before-insert, delete-path cleanup, and the accepted brief retrieval gap. `target/requirements/01_data_model.md`: new BR-DATA rules (chunk cleanup on delete, outbox reset on update, cascade cleanup) under the outbox table section.
- **Done when**: Both files describe the full mutation→chunk lifecycle including the v1 gap acceptance.
- **Test**: 12_content_extraction.md mentions `ON CONFLICT (content_id)`.
- **Depends on**: T4.5 (design final).

##### T4.9 [backend] — G4 integration test: content→chunk lifecycle
- **Build**: Integration test in the worker/rag suite (embedding steps **ollama-gated**, following `test_rag_loop_integration.py` conventions): create text content → drain → chunks exist for `content_id`; PATCH text → outbox `pending` again → drain → chunks replaced (old sentence absent, new present); DELETE → zero chunks + zero outbox rows; plus one assertion that an extraction-materialized content row (pre-existing Phase 3/4 enqueue path) also drains to chunks. A non-gated companion asserts the outbox state transitions (create→pending, patch→reset, delete→row gone) without invoking the embed model.
- **Done when**: Gated lifecycle test passes with Ollama up; non-gated transitions test passes in standard CI.
- **Test**: This is the G4 goal test.
- **Depends on**: T4.1, T4.3, T4.4, T4.5 [backend].

---

## G5 — hAITU answers on parent-owned topics

**Goal**: A linked child can ask hAITU about a live parent-owned topic and get an answer grounded in the parent's embedded notes; access is denied to unlinked students and severed instantly on revocation.
**Goal test**: T5.3.
**Repos**: [backend] [frontend] [specs]

##### T5.1 [backend] — Optional enrollment_id in the topic-doubt schema
- **Build**: In `src/schemas/haitu.py` topic-doubt request model: `enrollment_id: UUID4 | None = None`. Route (`haitu.py`) passes it through unchanged. Platform-topic requests without it must fail with 403 in the service (T5.2), preserving current behavior for all existing callers.
- **Done when**: A request body omitting `enrollment_id` passes Pydantic validation (no 422).
- **Test**: `assert TopicDoubtRequest(topic_id=…, message="q", history=[]).enrollment_id is None`
- **Depends on**: None.

##### T5.2 [backend] — Parent-link authorization gate in HaituDoubtService
- **Build**: Rework `HaituDoubtService._validate_and_build_context` (`src/domain/services/haitu_doubt_service.py:92`): load the topic first; if `topic.owner_type == 'parent'` → require an active link via a new port method (`AbstractUserMetadataRepository.has_active_link(parent_sub=topic.owner_id, child_sub=user_sub)` — same predicate as `src/infrastructure/visibility.py:33–43`) AND `topic.status == 'live'`, else `HaituAccessDeniedError`; skip the enrollment/subtree checks entirely on this branch. If platform-owned → existing path, raising `HaituAccessDeniedError` when `enrollment_id is None`. Rate limiter and ancestor-derived grade/subject context unchanged. Vector retrieval untouched — `topic_id` filter + this gate remain the cross-family defense. Doubt persistence works unchanged (keys on student + topic). **Unit-testable with fixtures** — seed a parent topic row + link row directly; no dependency on G1/G3 code artifacts (schema exists since V18/V22/V23).
- **Done when**: A linked child's request on a live parent topic reaches the pipeline (no `HaituAccessDeniedError`); an unlinked student's identical request raises it.
- **Test**: `with pytest.raises(HaituAccessDeniedError): await service.handle(unlinked_sub, parent_topic_id, None, "q", [])`
- **Depends on**: T5.1 [backend].

##### T5.3 [backend] — Severance + cross-family 403 tests (G5 integration test)
- **Build**: Integration tests (fixture-seeded parent topics/links): (a) revoke the link → immediate 403 on the next topic-doubt call, zero new `doubts` rows; (b) child linked to parent A queries parent B's topic → 403; (c) `draft` parent topic → 403 even for the linked child; (d) platform topic without `enrollment_id` → 403 (regression guard).
- **Done when**: All four scenarios pass in the suite.
- **Test**: This is the G5 goal test.
- **Depends on**: T5.2 [backend].

##### T5.4 [frontend] — HaituDoubtPanel enabled for Home Study topics
- **Build**: Thread the source (`platform` | `parent`) from the courses page into `content-viewer.tsx` → `haitu-doubt-panel.tsx`; when `source === 'parent'`, treat the panel as enabled with `enrollmentId` omitted from the `POST /api/haitu/topic-doubt` body (`student-api.ts:469` — omit the key when null for parent source, keep current behavior for platform), and swap the "enroll to ask" gating copy for Home Study copy. Green accent (#1D9E75) on the panel in parent context.
- **Done when**: Opening a Home Study topic shows an active hAITU composer and the request body contains no `enrollment_id` key.
- **Test**: `expect(JSON.parse(fetchMock.mock.calls[0][1].body)).not.toHaveProperty("enrollment_id")`
- **Depends on**: T5.1 [backend], T5.2 [backend].

##### T5.5 [specs] — 11_haitu_ai_layer.md §9: parent-topic access contract
- **Build**: New section in `target/requirements/11_haitu_ai_layer.md`: optional `enrollment_id`, the two-branch gate (enrollment path vs parent-link path), guard ordering (topic load → link check → status check → rate limit), immediate severance guarantee, live-only rule, unchanged vector scoping (topic_id filter + service gate as sole defense), and the "adopted topics start RAG-empty" behavioral note.
- **Done when**: Section documents both branches with the exact 403 conditions.
- **Test**: File contains the parent-link gate contract and references BR-DATA-003 semantics.
- **Depends on**: T5.2 (design final).

---

## G6 — Student Home Study surface complete

**Goal**: The child's Home Study experience (dashboard section, existing courses source switcher, content viewing) reflects the parent's live curriculum exactly, and only while a link is active.
**Goal test**: T6.1 (backend); frontend verification via T6.3's Done-when + T7.2 walkthrough.
**Repos**: [backend] [frontend]

##### T6.1 [backend] — Live-only + visibility enforcement tests on student paths (G6 integration test)
- **Build**: Integration tests (fixture-seeded links + parent trees — no dependency on G1/G3 code artifacts; fixes if any assert fails) covering the parent-owned flavor of every student read path: `GET /api/student/dashboard` (`has_parent_link`, parent root nodes), `GET /api/student/nodes?owner_type=parent`, `GET /api/student/nodes/{id}/topics` (draft excluded — `student_dashboard_service.py:238` filter), topic-contents viewer path (BR-DATA-003), and post-revocation 404/empty responses on all of them.
- **Done when**: The suite proves draft-hidden + revocation-severed on every student read endpoint touching parent content.
- **Test**: This is the G6 goal test. `assert draft_topic_id not in [t["id"] for t in topics_response.json()]`
- **Depends on**: None (fixtures).

##### T6.2 [frontend] — Source-aware empty state in the existing Home Study tree
- **Build**: The Home Study tab + `"platform" | "parent"` source switcher **already exist** (`student-courses-page.tsx`, line numbers shifted since the Pre-Phase-5 G4 deep-link rework landed on 2026-07-05 — re-read the current file rather than trusting the old `:98–164` reference) — this task only fixes its empty state: in `NodeTreeSidebar`, when `source === 'parent'` and the tree is empty, show "No Home Study content yet — ask your parent to add topics" instead of the platform empty state ("No courses enrolled." + Browse Courses → `/enroll`). Note: `NodeTreeSidebar`'s row markup changed under Pre-Phase-5 (chevron is now a sibling `<button>`, not nested; a new `initialExpandedIds` prop exists) — the empty-state branch this task touches is unaffected, but confirm no incidental collision when editing.
- **Done when**: Empty Home Study tab renders the parent-specific message with no `/enroll` link.
- **Test**: `expect(screen.queryByRole("link", { name: /browse courses/i })).toBeNull()` on empty parent source.
- **Depends on**: None.

##### T6.3 [frontend] — Home Study content viewing verification
- **Build**: Verify (and patch where missing) the end-to-end Home Study path on `/courses`: parent-source topic selection loads contents in the viewer (text/video render); the dashboard Home Study grid deep-links into the parent source tab. Theme check limited to three named surfaces — Home Study tab, dashboard Home Study section cards, topic panel header — using the green accent `#1D9E75` (non-gating note; any other surface is out of scope).
- **Done when**: A live parent text topic opens and renders its markdown in the viewer from the Home Study tab.
- **Test**: `expect(screen.getByText(mockParentNoteHeading)).toBeInTheDocument()`
- **Depends on**: T6.2 [frontend], T3.5 [backend] (live parent topics), T4.7b [frontend].

---

## G7 — Phase acceptance

**Goal**: The root goal holds as one uninterrupted journey across both repos.
**Goal test**: T7.1 + T7.2 together are the acceptance gate.
**Repos**: [backend] [frontend]

##### T7.1 [backend] — E2E journey test (contract-level, CI-safe) + ollama-gated grounded variant
- **Build**: Two tests. **(a) Non-gated journey** (standard integration suite, no live LLM): student generates code → parent redeems → adopt subtree → 409 on re-adopt → create text content → outbox pending → publish topic live → child dashboard shows Home Study → child topic-doubt returns SSE 200 with `doubt_id` frame + doubt row persisted (contract-level; no answer-content assertion — with `HAITU__MODEL_SPEC` empty the stream may terminate with the standard SSE error frame after `doubt_id`; assert only `doubt_id` + doubt-row persistence) → revoke link → topic-doubt 403 + Home Study empty. **(b) Ollama-gated grounded variant** (new `phase5_ollama_gated` suite, following `phase3_ollama_gated` conventions): with bge-m3 + a chat model up — outbox drains → chunks exist → child topic-doubt answer text is grounded in the parent's note content → PATCH content → re-drain → answer reflects the new text.
- **Done when**: (a) passes in standard CI; (b) passes locally with Ollama up (skips cleanly otherwise, counted in the "Ollama-gated: N skipped" summary).
- **Test**: This is the backend acceptance test for the root goal.
- **Depends on**: T1.7, T3.13, T4.9, T5.3, T6.1 [backend].

##### T7.2 [frontend] — Frontend closure: suites green + manual walkthrough
- **Build**: Full frontend verification: `pnpm test` + `pnpm typecheck` green across the repo; execute and record a manual browser walkthrough (precedent: `Implementation_planning/phase3_manual_walkthrough_record.md`) covering the G2 redirect matrix, the G3.3 builder journey (adopt → add node/topic → upload PDF → jobs strip → provenance badges → publish), profile link-code flow, Home Study + hAITU panel, and revocation severance in the UI.
- **Done when**: Both suites pass and the walkthrough record is committed to `Implementation_planning/`.
- **Test**: This is the frontend acceptance gate.
- **Depends on**: All frontend leaf tasks of G1–G6 (T1.5, T2.2, T2.3, T2.4, T2.6, T3.8, T3.9, T3.11, T4.7a, T4.7b, T5.4, T6.2, T6.3); T7.1 [backend].

---

## Cross-repo dependency edges

| From (needs) | To (provides) |
|---|---|
| T1.5 [frontend] | T1.1 [backend], T1.2 [backend] |
| T2.2 [frontend] | T1.3 [backend] |
| T2.3 [frontend] | T1.4 [backend] |
| T3.7 [frontend] | T3.2a [backend], T3.5 [backend], T3.6 [backend] |
| T3.9 [frontend] | T3.3 [backend], T3.4 [backend] |
| T3.11 [frontend] | T3.5 [backend], T3.6 [backend] |
| T5.4 [frontend] | T5.1 [backend], T5.2 [backend] |
| T6.3 [frontend] | T3.5 [backend] |
| T1.6 [specs] | T1.1, T1.3 [backend] |
| T2.5 [specs] | T2.1 [frontend] |
| T3.12 [specs] | T3.4, T3.6 [backend] |
| T4.8 [specs] | T4.5 [backend] |
| T5.5 [specs] | T5.2 [backend] |
| T7.2 [frontend] | T7.1 [backend] + all frontend leaf tasks of G1–G6 |

**Ready now (no pending dependencies):** T1.1, T1.2, T1.3, T1.4 [backend]; T3.1, T3.3, T4.2, T5.1, T6.1 [backend]; T2.1, T3.10, T4.7b, T6.2 [frontend].

**Sequencing spine:** G1 (links) → G2 (shell) → G3 (builder; V40 → CRUD → adopt → content) → G4 (ingestion lifecycle) → G5 (hAITU access) → G6 (Home Study completion) → G7 (acceptance). G5/G6 backend tasks are fixture-driven and can start in parallel with G1–G3.

<!-- plan-baseline: backend:da38e8bbab6c089330ec4fafb3b85f4083c39927 frontend:fc78c5fae4f6c55876dd5866d052ce21fc9e6079 deploy:ee39f9cd39659897af35b080d66b4fda8010fbb9 -->
<!-- baseline refreshed 2026-07-06: reconciled against the intervening Pre-Phase-5 hardening pass
     (G1-G8, unrelated scope, closed 2026-07-06). Zero Phase 5 tasks touched; only incidental
     overlap is node-tree-sidebar.tsx/student-courses-page.tsx/topic-list-panel.tsx reshaped
     under Pre-Phase-5 G3/G4 (see T6.2 note above). No re-decomposition needed — see
     decisions.md 2026-07-06. -->
