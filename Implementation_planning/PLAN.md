# PLAN — Phase 8: Parent UX Alignment

> Scoped 2026-08-20 via `/plan`. Phase 7.5 (Minimus Container Images + Phase 7 Deploy Backlog)
> closed 2026-08-18; its plan and tasks are archived at
> `archive/PLAN_Phase7.5-MinimusImages-DeployBacklog_2026-08-18.md` /
> `archive/TASKS_Phase7.5-MinimusImages-DeployBacklog_2026-08-18.md`.
>
> **Specs were written ahead of this plan.** Commit `510bbd8` (2026-08-20) landed the entire
> per-child binding design as spec text: BR-DATA-026 (`01_data_model.md:175-283`), BR-SEC-024
> (`02_auth_and_roles.md:159`), BR-PAR-022 (`05_parent.md:113-129`), the two-term BR-DATA-003 /
> BR-SEC-004 visibility clause, the hAITU doubt-thread gate (`11_haitu_ai_layer.md:589`) and the
> parent ui-mapping. **`[specs]` tasks in this plan are therefore corrections to what that commit
> missed, not new spec text.**
>
> Phase stub, the gap analysis it came from and the eight owner scope decisions: `phases.md` § Phase 8.
>
> **One challenger round run on the scope options, one checklist pass on the decomposition.** The
> scope challenger corrected two premises that had been carried in the stub and the backlog — see
> "Corrections taken during planning" below. The decomposition pass verified the dependency graph is
> a DAG across all 63 tasks with no cycles and no orphans, that every leaf carries exactly one repo
> tag, and that all 11 cross-repo edges are declared.

| Repo | HEAD at scoping |
|---|---|
| haisir-backend | `67b6cc3` |
| haisir-frontend | `784f700` |
| haisir-deploy | `790e29d` |
| haisir-specs | `510bbd8` |

Alembic head is **V43**; this phase adds **V44**.

## ROOT — Home Study is per-child, and the parent surface matches the mock

**Root goal**: A parent's Home Study content is visible only to the children it was explicitly built
for, and the parent surface renders the mock's shell, child switcher, two-tab nav, derivable
curriculum metrics and inline builder content.

**Acceptance test** (staging, manual + `tests/e2e`): Parent P links children Arjun (grade 6) and
Meera (grade 9). P builds root "Grade 6 Maths" bound to Arjun only and a root "Grade 9 Science"
bound to both. Then: (a) Arjun's `/student` Home Study shows Grade 6 Maths + Grade 9 Science;
Meera's shows Grade 9 Science only. (b) Meera `POST /api/haitu/topic-doubt` on a Grade 6 Maths topic
→ 403. (c) P's `/parent` shows a brown/amber topbar, a PARENT pill, `+ Link child`, a child strip
reading `Arjun · Grade 6` / `Meera · Grade 9`, and tabs `Curriculum | Results`. (d) With Meera
active, the Curriculum tab lists only Grade 9 Science with `3 topics · 2 live · 1 draft · 7 content
items`; with Arjun active it lists both. (e) The builder shows `Visible to Arjun and Meera` on
Grade 9 Science, renders content inline on each topic card, exposes no `Create Exam` link, and
`/parent/curriculum/<n>/topics/<t>` 302s to `/parent/curriculum?nodeId=<n>`.

**Repos**: [backend] [frontend] [specs] [deploy]

### Corrections taken during planning (do not re-open)

- **B49 is stale and was wrong.** The backlog entry asserts `ALERT_SLACK_WEBHOOK` is "armed but
  never seeded" and "aborts every staging and prod deploy". The archived Phase 7.5 `TASKS.md`
  contradicts it: the key was seeded on both hosts 2026-08-14 via `rotate-secret.sh` under the
  `admin-ops` cert identity, and **staging is proven end-to-end** — a full CI/CD staging deploy ran
  2026-08-15 (169s, exit 0, 13/13 healthy), which the `deploy.sh:564` gate could not have permitted
  with an unreadable key, and G3's E2E closed the same day with `TargetDown` observed moving pending
  → firing and the message arriving in the Slack channel. **The deploy channel is not blocked.**
  Only prod's render-side confirmation was never captured, because prod has had no `deploy.sh` run
  since the key was armed (T4.12 was a manual container recreation; G6.1's prod half was explicitly
  read-only). That residue is T0.1; correcting the record is T0.2. **Nothing in G1–G4 depends on G0.**
- **The extraction-quota divergence does not exist.** `current/api_contracts.md:418` records the live
  gate as 3 concurrent / 20 daily; the running code at `extraction_service.py:28-29` is
  `_MAX_CONCURRENT_PARENT_JOBS = 5` / `_MAX_DAILY_PARENT_JOBS = 100`, already matching BR-PAR-008a.
  There is nothing to reconcile. **But a worse bug sits underneath it** — see T3.2.
- **`child_sub` is `String`, not `UUID`** (owner call, 2026-08-20). BR-DATA-026's DDL types it `UUID`
  while its own rationale note argues for matching `parent_child_links.child_sub`, which is `String`
  (`src/infrastructure/models/user_metadata.py:89`). String wins: the backfill `INSERT ... SELECT
  l.child_sub` aborts on Postgres without a cast, and with a cast it aborts on any non-UUID sub. The
  spec DDL is corrected by T1.3.
- **The backfill binds revoked pairs too** (T1.4). The spec's SQL filters `revoked_at IS NULL`, which
  would leave pre-migration revoked pairs unable to regain visibility on re-link — the inverse of the
  "bindings outlive revocation" property that holds for every post-Phase-8 pair. A binding to a
  revoked child grants nothing today anyway, because BR-DATA-003's link term is false.

### Scope locks (owner calls carried from the stub — do not re-open)

- **Child scoping is real, not cosmetic.** Rewording the UI to "visible to your linked children" over
  a shared tree was rejected. The schema moves, not the copy.
- **A tree binds to one *or several* children.** Same-grade siblings share one curriculum, built and
  uploaded once. This is what makes the migration behaviour-preserving and is why the **V40 adopt
  index needs no change at all**.
- **`child_subs` is required — hard 400, no fallback.** A breaking change to two shipped endpoints;
  frontend and backend ship together.
- **Overview metrics: only what is derivable.** Day streak, topics-this-week, active modules,
  progress % and "N topics studied" are out. Nothing renders a hardcoded zero.
- **Results is deferred entirely** behind a coming-soon placeholder. **BR-PAR-012 stands unchanged** —
  widening to the child's platform exam results would reverse it and was deferred by owner call.
- **The Overview tab is not built.** With the snapshot stats and weak-topic banner out, it would
  render identically to Curriculum.
- **Binding is anchored at the root only.** Subtree-level binding would force a nearest-bound-ancestor
  walk — the recursive resolution this design exists to avoid.
- **Unbinding hides nothing and deletes nothing**, and is permitted with in-flight `exam_sessions`.
  BR-PAR-004's delete-block is deliberately not extended to it.

### Explicitly out of phase

Parent exam authoring (`/api/parent/exams*`, the mock's `+ Exam` button). The child-results read
path. Study-activity tracking and day streak. Home Study progress and weak topics. Upcoming or
scheduled exams. Essay grade review. The Overview tab.

> `enrollment_topics` is written **only** by the post-exam mastery pipeline
> (`mastery_service.py:246`), requires a `student_enrollments` row, and `EnrollmentService.enroll()`
> hard-rejects non-platform nodes (`enrollment_service.py:57-61`). A parent-owned topic can therefore
> never produce a mastery row — the Overview metrics are structurally impossible, not merely unbuilt.

### Deploy scope: none

New endpoints ride the generic `/api/*` routes (`04-api-read`, `05-api-write`, `06-api-delete`), so
no APISIX route is needed. G0's single deploy task is an observation on an already-scheduled prod
window, not new infrastructure.

### Standing operational preconditions on the G1 release

- **Stop the worker before the V44 deploy** (`constraints.md:117`) — poller sessions sit
  `idle in transaction` and block Alembic.
- **Rollback is the pre-deploy dump + datadir tarball, not `alembic downgrade`** (`constraints.md:125`).
- **Keep `data_topic_content_chunks` out of autogenerate** (`constraints.md:133`) — it is
  LlamaIndex-owned and autogenerate will propose dropping columns it does not know about.
- **CSP is enforced** (`constraints.md:109`, BR-CSP-010, CI-asserted) — no inline `<script>`, no
  `style=` attributes, every route dynamically rendered. Applies to every G1.4/G2/G3/G4 task.

---

## G0 — B49 record corrected, prod render path confirmed

**Goal**: The alerting-secret record in `phases.md` states what is actually true, and prod's
secret-render path is confirmed the next time prod deploys.
**Goal test**: On the prod host, `bash common/scripts/template-configs.sh` from `prod/` exits 0, logs
no unresolved-placeholder warning for any `{{ALERT_*}}`, and `rendered/common/prometheus/alertmanager.yml`
contains a `hooks.slack.com` URL; `phases.md`'s B49 entry no longer claims the key is unseeded.
**Repos**: [deploy] [specs]

> **Opportunistic, not blocking.** T0.1 needs a prod window that is not currently scheduled. Phase 8
> validates on staging, which is proven clean. Nothing in G1–G4 depends on this goal, and G0 staying
> open must not be read as the phase being blocked.

##### T0.1 [deploy] — Capture prod's render-side confirmation
- **Build**: On the next prod `deploy.sh` window, before Step 4, run `bash common/scripts/template-configs.sh`
  from `prod/` and record two things in the deploy log: that it exits 0 with no unresolved-placeholder
  warning from the `:355-373` scan, and that `render-deploy-secrets.sh` reports all ~7 pre-existing
  `secret/haisir/infra` keys as `(set)` — the second guards the failure mode where a `kv put` replaced
  the whole secret rather than patching it.
- **Done when**: A prod deploy log shows `template-configs.sh` exit 0 with zero `{{ALERT_` occurrences
  in `rendered/common/prometheus/alertmanager.yml` and all pre-existing infra keys still `(set)`.
- **Test**: `grep -c '{{ALERT_' prod/rendered/common/prometheus/alertmanager.yml` returns 0.
- **Depends on**: None

##### T0.2 [specs] — Correct the B49 backlog entry
- **Build**: Rewrite the B49 entry in `Implementation_planning/phases.md`. Remove "armed but never
  seeded" and "aborts every staging and prod deploy". Replace with: seeded on both hosts 2026-08-14
  via `rotate-secret.sh` under the admin-ops cert identity; proven end-to-end on staging 2026-08-15
  (full CI/CD deploy exit 0, 13/13 healthy; `TargetDown` pending → firing with the Slack message
  delivered); the only outstanding item is prod's render-side confirmation (T0.1), because prod has
  had no `deploy.sh` run since the key was armed.
- **Done when**: `grep -n "never seeded" Implementation_planning/phases.md` returns nothing in the B49 entry.
- **Test**: The B49 entry contains the string "2026-08-15" and does not contain "aborts every staging and prod deploy".
- **Depends on**: None

---

## G1 — Per-child Home Study binding

**Goal**: A parent's curriculum root is visible to exactly the children it is bound to, on every
student read path and through hAITU, and the parent chooses those children when they create or adopt
the root.
**Goal test**: E2E — parent P (linked to children A and B) creates root R1 with `child_subs=[A]` and
adopts board R2 with `child_subs=[A,B]`. `GET /api/student/nodes?owner_type=parent` as A returns both
roots; as B returns R2 only. `GET /api/student/nodes/{R1_child}/topics` as B → empty. `POST
/api/haitu/topic-doubt` on an R1 topic as B → 403; as A → 200. After `DELETE /nodes/R2/bindings/{B}`,
B sees nothing; after `POST /nodes/R2/bindings {child_subs:[B]}`, B sees R2 again with no content
re-upload.
**Repos**: [backend] [frontend] [specs]

---

### G1.1 — Binding schema + behaviour-preserving migration

**Subgoal**: The binding table and the denormalised `root_node_id` exist, and every parent-owned row
that was visible before V44 is still visible after it.
**Subgoal test**: Integration — seed (pre-migration fixture) a parent with 2 active children and 1
revoked child, a 3-level tree with topics; run `alembic upgrade V44`; assert one
`parent_content_bindings` row per (root, child) for all 3 children, and that every node/topic row's
`root_node_id` equals its tree's root id, self-referential on the root.
**Repos**: [backend] [specs]

> **T1.5, T1.6 and T1.7 build one file — `V44_parent_content_bindings.py` — in three checkpoints and
> land as a single commit.** A migration is atomic; T1.5's "Done when" would pass before the backfills
> exist. They are separate tasks because each has its own falsifiable assertion, not because each is
> independently deployable.

##### T1.1 [backend] — parent_content_bindings table model
- **Build**: Add a `parent_content_bindings` `Table` to `src/infrastructure/models/user_metadata.py`
  (next to `parent_child_links`): `root_node_id UUID FK→course_path_nodes.id ON DELETE CASCADE`,
  `child_sub String NOT NULL` (no FK — `constraints.md:21`), `created_at TIMESTAMP(timezone=True)`,
  composite PK `(root_node_id, child_sub)`, plus `Index("ix_parent_content_bindings_child", "child_sub")`.
- **Done when**: `parent_content_bindings` appears in `registry_mapper.metadata.tables` with `child_sub` typed `String`.
- **Test**: `assert parent_content_bindings.c.child_sub.type.python_type is str`.
- **Depends on**: T1.3 [specs]

##### T1.2 [backend] — root_node_id column on the three owner-scoped tables
- **Build**: Add `Column("root_node_id", UUID(as_uuid=True), nullable=True)` to `course_path_nodes`
  (`src/infrastructure/models/course_path_node.py:9-28`), `topics` and `exam_templates`. No FK — a
  self-referential root and the ON DELETE CASCADE on the binding table already cover integrity, and an
  FK on `topics.root_node_id` would fight `delete_subtree`'s manual DELETE ordering.
- **Done when**: All three tables expose a nullable `root_node_id` column.
- **Test**: `assert all(t.c.root_node_id.nullable for t in (course_path_nodes, topics, exam_templates))`.
- **Depends on**: None

##### T1.3 [specs] — BR-DATA-026 DDL types child_sub as String
- **Build**: In `target/requirements/01_data_model.md:186-192`, change `child_sub UUID NOT NULL` to
  `child_sub VARCHAR NOT NULL` and add a one-line note pointing at `parent_child_links.child_sub`
  (`src/infrastructure/models/user_metadata.py:89`) and `constraints.md:21`. Without this the backfill
  `INSERT ... SELECT l.child_sub` aborts on Postgres with a varchar→uuid mismatch. The rule's own
  rationale paragraph already argues String; only the DDL disagreed.
- **Done when**: The BR-DATA-026 DDL block contains no `UUID` on the `child_sub` line.
- **Test**: `grep -A6 'CREATE TABLE parent_content_bindings' target/requirements/01_data_model.md | grep child_sub` matches `VARCHAR`.
- **Depends on**: None

##### T1.4 [specs] — BR-DATA-026 backfill binds revoked pairs too
- **Build**: In `01_data_model.md:249-264`, drop `AND l.revoked_at IS NULL` from the backfill `SELECT`
  and add the rationale: a revoked pair's binding grants nothing today (BR-DATA-003's link term is
  false), and keeping it makes pre-migration pairs obey the same "bindings outlive revocation"
  property as every post-Phase-8 pair — otherwise re-linking an old child restores the link but
  silently not the visibility. Also update the "Rules" bullet so the property is stated without a
  pre/post-migration exception.
- **Done when**: The migration SQL block contains no `revoked_at` filter and the asymmetry is not documented as accepted behaviour anywhere in BR-DATA-026.
- **Test**: `grep -A8 'INSERT INTO parent_content_bindings' target/requirements/01_data_model.md | grep -c revoked_at` returns 0.
- **Depends on**: None

##### T1.5 [backend] — V44 schema half
- **Build**: New `alembic/versions/V44_parent_content_bindings.py`, `revision="V44"`,
  `down_revision="V43"`, modelled on `V40_adopt_lineage_source_node_id.py`. `upgrade()` creates
  `parent_content_bindings` (composite PK, FK to `course_path_nodes.id` ON DELETE CASCADE) +
  `ix_parent_content_bindings_child`, then three `op.add_column(..., sa.Column("root_node_id",
  sa.UUID(), nullable=True))`. `downgrade()` drops the three columns, the index and the table.
  Docstring carries the worker-stop precondition (`constraints.md:117`).
- **Done when**: `alembic upgrade head` on an empty DB reaches V44 and `alembic downgrade V43` returns cleanly.
- **Test**: New `tests/unit/test_v44_migration.py` (mirroring `test_v40_migration.py`) asserts `parent_content_bindings` exists after upgrade and is gone after downgrade.
- **Depends on**: T1.1 [backend], T1.2 [backend]

##### T1.6 [backend] — V44 root_node_id backfill
- **Build**: In V44's `upgrade()`, after the DDL, one recursive CTE anchored on `owner_type='parent'
  AND parent_id IS NULL` propagating `root_id` down `parent_id`, then three `UPDATE ... FROM tree`
  statements — `course_path_nodes.id = tree.id`, `topics.course_path_node_id = tree.id`,
  `exam_templates.course_path_node_id = tree.id`. Both `course_path_node_id` columns are NOT NULL, so
  no parent-owned row can be missed. Platform rows keep `root_node_id NULL`.
- **Done when**: After upgrade, `SELECT count(*) FROM topics t JOIN course_path_nodes n ON n.id=t.course_path_node_id WHERE n.owner_type='parent' AND t.root_node_id IS NULL` returns 0.
- **Test**: Integration test seeds a 3-level parent tree with topics and asserts every row's `root_node_id` equals the root's id, self-referential on the root.
- **Depends on**: T1.5 [backend]

##### T1.7 [backend] — V44 bindings backfill
- **Build**: In the same `upgrade()`, the amended BR-DATA-026 insert: `INSERT INTO
  parent_content_bindings (root_node_id, child_sub) SELECT n.id, l.child_sub FROM course_path_nodes n
  JOIN parent_child_links l ON l.parent_sub = n.owner_id WHERE n.owner_type='parent' AND n.parent_id
  IS NULL ON CONFLICT DO NOTHING` — no `revoked_at` filter (T1.4), `ON CONFLICT` because a re-linked
  pair has two link rows.
- **Done when**: After upgrade, every (parent root, child) pair that had any link row — active or revoked — has exactly one binding row.
- **Test**: Fixture with one active and one revoked link for the same parent root asserts `SELECT count(*) FROM parent_content_bindings WHERE root_node_id=:root` == 2.
- **Depends on**: T1.5 [backend], T1.4 [specs]

---

### G1.2 — Write path stamps root_node_id and bindings

**Subgoal**: Every parent-owned row created after V44 carries its `root_node_id`, and every root is
bound to at least one actively-linked child at the moment it is created.
**Subgoal test**: Integration — `POST /api/parent/curriculum/nodes` without `child_subs` → 400; with
an unlinked child → 404 and zero rows written; with `[A,B]` → 201 and 2 binding rows, and the created
root's `root_node_id` equals its own id. `POST /adopt {source_node_id, child_subs:[A,B]}` → one cloned
tree, every cloned node and topic carrying the cloned root's id, and exactly 2 binding rows.
**Repos**: [backend]

##### T1.8 [backend] — ParentContentBindingRepository
- **Build**: `src/infrastructure/repositories/parent_content_binding_repository.py` with
  `add_many(root_node_id, child_subs)` (bulk insert, `ON CONFLICT DO NOTHING`), `delete(root_node_id,
  child_sub)` returning a bool, `list_for_root(root_node_id) -> list[str]`, `list_for_child(child_sub)
  -> list[UUID]`, `exists(root_node_id, child_sub) -> bool`. Follow `ParentChildLinkRepository`
  (`user_metadata_repository.py:299`): plain `AsyncSession`, `flush()` not `commit()`.
- **Done when**: All five methods round-trip against a seeded binding row.
- **Test**: `add_many(root, ["a","b"])` then `list_for_root(root) == ["a","b"]`.
- **Depends on**: T1.1 [backend]

##### T1.9 [backend] — Bind-time validation is all-or-nothing
- **Build**: `ParentCurriculumService.bind_children(root_id, child_subs, user)` — resolve the root via
  `repo.get_node_by_id_and_owner` (None → 404 oracle), then for every sub check
  `parent_child_link_repo.exists(parent_sub=user.sub, child_sub=sub)`; a single miss returns `None`
  (→ 404, per BR-SEC-024: not 403, so an unlinked sub is indistinguishable from a nonexistent one)
  with **no** insert. Only on a clean sweep call `add_many`. Inject `AbstractParentChildLinkRepository`
  + the new binding repo into `ParentCurriculumService.__init__` and `get_service`
  (`parent_curriculum.py:70`).
- **Done when**: A two-sub request where one sub is revoked writes zero binding rows.
- **Test**: `bind_children(root, [linked, revoked], user)` returns None and `list_for_root(root) == []`.
- **Depends on**: T1.8 [backend]

##### T1.10 [backend] — child_subs on the two create payloads
- **Build**: Add `child_subs: list[UUID4] | None = None` to `ParentNodeCreate` and `child_subs:
  list[UUID4] = Field(min_length=1)` to `AdoptRequest` (`src/schemas/course_path_node.py:34-58`). In
  `create_node` (`parent_curriculum.py:158`) raise `DomainValidationError` → 400 when `parent_id is
  None` and `child_subs` is empty/absent — same shape as the existing `category_id` 400. Child-node
  creates ignore the field. No single-child fallback (owner call). Update the ~19 signature-only call
  sites in `tests/unit/domain/test_services/test_parent_curriculum_service.py` and the root-creating
  tests in `tests/unit/routes/test_parent_curriculum.py` (lines 281/314/344/362/382/404) plus the 5
  adopt tests (580/600/629/645/662) in the same commit.
- **Done when**: `POST /nodes` with `parent_id=None` and no `child_subs` returns 400 and creates nothing.
- **Test**: `test_parent_curriculum.py::TestCreateNode::test_root_without_child_subs_400` asserts `response.status_code == 400`.
- **Depends on**: None

> **Largest single task in the phase, deliberately not split.** It carries two schema changes, the
> 400, and ~32 test-function updates. The tests must move in the same commit or the suite breaks, so
> splitting would produce a knowingly-red intermediate state.

##### T1.11 [backend] — create_node stamps root_node_id
- **Build**: In `ParentCurriculumService.create_node` (`parent_curriculum_service.py:82`), set
  `root_node_id=node.id` when `parent_id is None`, else `root_node_id=parent.root_node_id` (the parent
  was already owner-resolved at `:127`). Add the field to the `CoursePathNode` domain model and the
  `CoursePathNode` constructor call at `:134`.
- **Done when**: A root's `root_node_id` equals its own id; a child's equals its parent's.
- **Test**: `create_node(parent_id=root.id, ...)` returns a node whose `root_node_id == root.id`.
- **Depends on**: T1.2 [backend]

##### T1.12 [backend] — create_node binds the named children
- **Build**: After the successful `repo.add(node)` in `create_node`, when `parent_id is None`, call
  `bind_children(node.id, child_subs, user)` in the same transaction; on a validation miss, roll back
  and return None so the route 404s without an orphan root.
- **Done when**: A root create naming two linked children leaves exactly two binding rows; a root create naming one unlinked child leaves zero nodes and zero bindings.
- **Test**: `create_node(..., child_subs=[unlinked])` → the node count for that owner is unchanged.
- **Depends on**: T1.9 [backend], T1.11 [backend], T1.10 [backend]

##### T1.13 [backend] — adopt_node stamps root_node_id on every clone
- **Build**: In `adopt_node` (`parent_curriculum_service.py:270`), allocate the cloned root's `new_id`
  first, then set `root_node_id=<cloned root id>` on every cloned `CoursePathNode` and every cloned
  `Topic` inside the existing single transaction. The cloned root is self-referential.
- **Done when**: Every row produced by one adopt shares one `root_node_id` equal to the returned node's id.
- **Test**: After `adopt_node`, `{n.root_node_id for n in cloned} == {root.id}`.
- **Depends on**: T1.2 [backend]

##### T1.14 [backend] — adopt_node binds the named children
- **Build**: After the clone commits, `bind_children(cloned_root.id, payload.child_subs, user)`; a
  validation miss rolls back the whole clone. Leave `AlreadyAdoptedError` → 409
  (`parent_curriculum.py:325`) and the V40 `ux_course_path_nodes_adopt_lineage` index **untouched** —
  under many-to-many binding, one adopt per parent per source board is the correct invariant again.
- **Done when**: An adopt naming two children produces exactly one cloned tree and two binding rows.
- **Test**: `adopt_node(src, child_subs=[A,B])` → `len(list_for_root(cloned.id)) == 2` and one root node created.
- **Depends on**: T1.9 [backend], T1.13 [backend], T1.10 [backend]

##### T1.15 [backend] — Parent topic create stamps root_node_id
- **Build**: In `ParentCurriculumService.create_topic` (the `POST /nodes/{node_id}/topics` path in
  `parent_curriculum.py`), copy `root_node_id` from the owner-resolved node onto the new `Topic`.
  `topics.course_path_node_id` is NOT NULL, so there is no other source and no orphan case.
- **Done when**: A topic created under a parent node has that node's `root_node_id`.
- **Test**: `create_topic(node_id=child_node.id, ...)` → `topic.root_node_id == root.id`.
- **Depends on**: T1.11 [backend]

> **`exam_templates.root_node_id` is deliberately inert.** No live endpoint creates a parent-owned
> template — `src/api/routes/exam.py` is the only writer and it is platform-scoped via
> `require_instructor()`. The column exists so `student_visibility_clause` stays a uniform
> single-table helper across all three tables. There is no missing writer to hunt for.

##### T1.16 [backend] — POST /nodes/{root_id}/bindings
- **Build**: New route in `parent_curriculum.py` taking `{child_subs: list[UUID4]}` (min 1),
  `require_parent()` + `validate_csrf`, delegating to `bind_children`. 404 on unowned root or any
  unlinked sub, 201 on success returning the updated `child_subs` list. Rejects non-root ids (binding
  is anchored at the root only) with 400.
- **Done when**: Binding a second child to an existing root makes that root's subtree visible to them with no content re-upload.
- **Test**: `POST /nodes/{root}/bindings {"child_subs":["<B>"]}` → 201 and `list_for_root(root)` contains B.
- **Depends on**: T1.9 [backend]

##### T1.17 [backend] — DELETE /nodes/{root_id}/bindings/{child_sub}
- **Build**: New route deleting one binding row; 204 on success, 404 when the root is unowned or the
  binding is absent. **No** in-flight-exam-session guard — BR-PAR-004's delete-block is deliberately
  not extended to unbind, which is reversible and destroys nothing.
- **Done when**: Unbinding a child with an in-progress exam session returns 204 and leaves the `exam_sessions` row intact.
- **Test**: Unbind with an active session → 204 and the session row still exists.
- **Depends on**: T1.8 [backend]

##### T1.18 [backend] — child_subs on parent root reads
- **Build**: Add `child_subs: list[str] = []` to `CoursePathNodeRead` (`src/schemas/course_path_node.py:25`)
  and populate it in `list_root_nodes` / `get_node_with_children` via one bulk query over the returned
  root ids (single `WHERE root_node_id = ANY(...)`, not per-root). Platform reads and student reads
  leave it empty — this is the parent's own builder view only, and it is what the privacy pill and
  G3's per-child filter consume.
- **Done when**: `GET /api/parent/curriculum/nodes` returns each root's real binding set.
- **Test**: A root bound to A and B serialises `child_subs` of length 2.
- **Depends on**: T1.8 [backend]

##### T1.19 [backend] — GET /api/parent/children?include_revoked=true
- **Build**: Add an `include_revoked: bool = False` query param to `list_children`
  (`src/api/routes/parent_children.py:31`); when true, `list_children_for_parent` uses a new
  `get_links_for_parent` (no `revoked_at IS NULL` filter) and `ChildLinkView`/`ChildLinkWithProfile`
  gain `revoked_at: datetime | None`. Default false — the shipped wire shape is unchanged for every
  existing caller. This exists so the builder can render a binding to an unlinked child rather than
  silently dropping it (the latent invisible grant).
- **Done when**: A parent with one active and one revoked child gets 1 entry by default and 2 with the flag, the second carrying a non-null `revoked_at`.
- **Test**: `GET /api/parent/children?include_revoked=true` returns 2 items; without the flag, 1.
- **Depends on**: None

---

### G1.3 — Read path enforces both terms, everywhere

**Subgoal**: A child sees and can reach a parent's content only when both an active link and a binding
exist — on every SQL read path, on the Home Study grid, and through hAITU.
**Subgoal test**: Integration — parent P, children A and B both actively linked, root R bound to A
only. As B: `GET /api/student/nodes?owner_type=parent` omits R; `GET /nodes/{R_child}/topics` → `[]`;
`GET /api/student/topic-contents/{id}` → 404; exam template list under R → `[]`; `POST
/api/haitu/topic-doubt` on an R topic → 403. As A, all five succeed. Revoke A's link → all five fail
for A on the next request with no cache flush.
**Repos**: [backend]

##### T1.20 [backend] — The clause gains the binding EXISTS
- **Build**: In `src/infrastructure/visibility.py:17-43`, add a third condition inside the existing
  `and_(...)`: `select(1).select_from(_pcb).where(_pcb.c.root_node_id == table.c.root_node_id,
  _pcb.c.child_sub == viewer_sub).exists()`. **Keep the `owner_id.in_(linked_parents)` term** —
  BR-DATA-003 forbids optimising either away: dropping the link term leaves revoked parents readable;
  dropping the binding term restores pre-Phase-8 behaviour. All 10 call sites
  (`course_path_node_repository.py:67,108,143,166,237`; `topic_repository.py:43`;
  `topic_content_repository.py:111,127`; `exam_repository.py:123,153`) inherit it with no edit,
  because every table it is applied to now has `root_node_id`. Also update
  `_assert_node_in_enrolled_subtree`'s docstring (`student_dashboard_service.py:252-256`) to name both
  terms — its parent-owned early return is justified by this clause and the rationale must not drift.
- **Done when**: A student actively linked to a parent but not bound to a root gets zero rows from every one of the 10 call sites.
- **Test**: `tests/integration/routes/test_g6_visibility_student_read_paths.py` gains a case asserting a linked-but-unbound child receives `[]` from the topic list.
- **Depends on**: T1.2 [backend], T1.6 [backend]

##### T1.21 [backend] — _resolve_parent_nodes filters service-side
- **Build**: In `student_dashboard_service.py:219-231`, after `get_by_owner("parent", parent_sub)` at
  `:230`, filter to `n.root_node_id in bound_root_ids` where `bound_root_ids = set(await
  binding_repo.list_for_child(student_sub))` (one query, hoisted above the parent loop). Inject the
  binding repo through `api/dependencies.get_student_dashboard_service`. **The filter must NOT go
  inside `get_by_owner`** (`course_path_node_repository.py:461-473`): its only other caller is
  `parent_curriculum_service.py:52`, the parent's own builder list, which would then show a parent
  nothing of their own tree.
- **Done when**: A linked-but-unbound child's `GET /api/student/nodes?owner_type=parent` returns `[]` while the parent's `GET /api/parent/curriculum/nodes` still returns the root.
- **Test**: `tests/unit/domain/test_services/test_student_dashboard_service_parent_gate.py` gains a case asserting the unbound root is absent from the tree while `list_root_nodes` for the owner still contains it.
- **Depends on**: T1.8 [backend]

> **This is the whole goal's failure mode.** `_resolve_parent_nodes` resolves parent nodes in Python
> and never touches `student_visibility_clause`. If it is missed, per-child binding is a **no-op on
> the child's primary screen** while every exam/topic/content test still passes.

##### T1.22 [backend] — hAITU gate gains the binding term
- **Build**: In `haitu_doubt_service.py:153-171`, `_assert_parent_owned_access` currently checks only
  `_parent_link_repo.exists(...)` and `topic.status == "live"`. Add `await
  self._binding_repo.exists(topic.root_node_id, user_sub)` as a third mandatory condition, raising the
  same `HaituAccessDeniedError` → 403. Inject the binding repo where `_parent_link_repo` is wired.
  This is the one genuine access hole: without it a child can open a doubt thread on a sibling's topic
  — invisible in the UI, reachable through hAITU.
- **Done when**: A linked-but-unbound child gets 403 on `POST /api/haitu/topic-doubt` for a sibling's live parent-owned topic.
- **Test**: `tests/unit/domain/test_services/test_haitu_doubt_service_parent_gate.py` gains `test_linked_but_unbound_child_403`.
- **Depends on**: T1.8 [backend], T1.2 [backend]

---

### G1.4 — Parent binds content at create time (ships in lockstep)

**Subgoal**: The parent chooses which children a root is for when creating or adopting it, and can see
and change that set afterwards.
**Subgoal test**: Integration (vitest + MSW) — open the Add Root modal with two linked children,
submit without a selection → the submit button is disabled and no request fires; select both → the
POST body carries `child_subs` of length 2; the builder pill then reads "Visible to Arjun and Meera";
removing Meera via the editor fires `DELETE /nodes/{root}/bindings/{meera_sub}` and the pill reads
"Visible to Arjun".
**Repos**: [frontend]

> These ship in the same release as G1.2 — `child_subs` is a hard 400 with no fallback, so an
> un-updated frontend cannot create a root.

##### T1.23 [frontend] — Child multi-select in the Add Root modal
- **Build**: In `src/features/parent/components/parent-add-node-modal.tsx`, when creating a root (no
  `parent_id`), render a "Who is this for?" checkbox group over `useParentChildren()`'s active
  children, styled through `parent-add-node-modal.module.css` (no `style=` attributes — CSP,
  `constraints.md:109`). Submit disabled while the selection is empty. Child-node creation renders no
  such control.
- **Done when**: The root form cannot be submitted with zero children selected.
- **Test**: `tests/unit/features/parent/components/parent-add-node-modal.test.tsx` asserts the submit button has `disabled` until a child checkbox is checked.
- **Depends on**: None

##### T1.24 [frontend] — createNode sends child_subs
- **Build**: Add `child_subs: string[]` to `CreateParentNodeInput`
  (`src/features/parent/types/parent.types.ts`) and pass it through `parentCurriculumApi.createNode`
  (`parent-curriculum-api.ts:137`) and `use-parent-node-mutations.ts`. Existing `fetchWithCSRFRetry` +
  `buildApiHeaders` path unchanged.
- **Done when**: The `POST /nodes` request body for a root contains the selected subs.
- **Test**: A mocked fetch asserts `JSON.parse(body).child_subs` equals the selected array.
- **Depends on**: T1.23 [frontend], T1.10 [backend]

##### T1.25 [frontend] — Child multi-select in the Adopt modal
- **Build**: Same checkbox group in `adopt-modal.tsx`, gating the "Import board curriculum" confirm
  button. Copy makes the shared-tree semantics explicit ("one copy, shared by the children you pick").
- **Done when**: Confirm stays disabled until at least one child is selected.
- **Test**: `adopt-modal.test.tsx` asserts confirm is disabled with no selection and enabled after one check.
- **Depends on**: None

##### T1.26 [frontend] — adoptSubtree sends child_subs
- **Build**: Add `child_subs: string[]` to `AdoptInput` and thread it through
  `parentCurriculumApi.adoptSubtree` (`parent-curriculum-api.ts:208`) and `use-adopt.ts:9`. The
  existing 409 "You have already adopted this board." handling stays — it is still the right invariant.
- **Done when**: The `POST /adopt` body carries `child_subs`.
- **Test**: A mocked fetch asserts the adopt body includes a two-element `child_subs`.
- **Depends on**: T1.25 [frontend], T1.10 [backend]

##### T1.27 [frontend] — Privacy pill renders the real binding set
- **Build**: In `parent-curriculum-page.tsx`, replace the hardcoded pill with one derived from the
  selected root's `child_subs` (T1.18) joined against `useParentChildren()` names: 1 child → "Visible
  to Arjun"; 2 → "Visible to Arjun and Meera"; 3+ → "Arjun +2".
- **Done when**: The pill text changes when a binding changes, with no hardcoded name anywhere in the component.
- **Test**: `parent-curriculum-page.test.tsx` renders a root bound to two children and asserts the text "Visible to Arjun and Meera".
- **Depends on**: T1.18 [backend]

##### T1.28 [frontend] — Binding editor on an existing root
- **Build**: A small popover on the privacy pill listing active children with checkboxes; checking
  calls `POST /nodes/{root}/bindings`, unchecking calls `DELETE /nodes/{root}/bindings/{child_sub}`,
  both via `fetchWithCSRFRetry` and invalidating `parentNodeTreeKey()`. This is the self-service
  remedy for children linked after the migration, who get zero binding rows by design.
- **Done when**: A child linked after the root was created can be granted access without recreating the root.
- **Test**: Unchecking a child fires a DELETE to `/nodes/{root}/bindings/{sub}`.
- **Depends on**: T1.16 [backend], T1.17 [backend], T1.27 [frontend]

##### T1.29 [frontend] — Revoked-but-bound child greyed in the pill
- **Build**: The pill/editor fetch children with `?include_revoked=true` (T1.19) and render any bound
  sub whose link is revoked greyed with a "not linked" suffix. Without this the grant is invisible:
  the parent repurposes the tree for one child, and the moment the other re-links they see everything
  added while unlinked.
- **Done when**: A root bound to a revoked child shows that child greyed rather than omitting them.
- **Test**: With one revoked bound child, the pill contains that child's name and the string "not linked".
- **Depends on**: T1.19 [backend], T1.27 [frontend]

---

### G1.5 — Regression fixtures survive the breaking change

**Subgoal**: The existing backend suite exercises the new required field instead of failing on it.
**Subgoal test**: `pytest tests/` is green with no test skipped or xfailed as a result of `child_subs`.
**Repos**: [backend]

##### T1.30 [backend] — linked_child fixture helper
- **Build**: A `linked_child` fixture in `tests/integration/routes/conftest.py` creating a
  `parent_child_links` row for the test parent and returning the child sub, plus a `bound_root` helper
  that creates a root and its binding in one call. The ~32 affected test functions then differ only by
  payload.
- **Done when**: Both helpers are importable and produce a queryable link/binding pair.
- **Test**: A smoke test asserts `linked_child` yields a sub for which `ParentChildLinkRepository.exists` is True.
- **Depends on**: T1.8 [backend]

##### T1.31 [backend] — Rewrite the cross-owner 404 sweep
- **Build**: `tests/integration/routes/test_g3_1_cross_owner_404_sweep_integration.py:73,84,106` —
  switch the three creation calls to the `linked_child` fixture and add `child_subs`. Add one case to
  the sweep: parent A's root bound to child X is a 404 for parent A's *other* linked child Y on every
  student read path.
- **Done when**: The file passes and covers the linked-but-unbound case.
- **Test**: The new sweep case asserts 404/empty for the unbound sibling on the topic-content route.
- **Depends on**: T1.30 [backend], T1.20 [backend]

##### T1.32 [backend] — Rewrite the E2E journey test
- **Build**: `tests/integration/routes/test_g7_1_e2e_journey_integration.py:192,202` — the journey now
  links a child before the root create/adopt and passes `child_subs`, then asserts the child sees the
  tree end to end.
- **Done when**: The full journey passes with bindings in place.
- **Test**: The journey's student-read assertion returns the parent-built topic for the bound child.
- **Depends on**: T1.30 [backend], T1.21 [backend]

---

### G1.6 — Specs stop contradicting the shipped rule

**Subgoal**: No spec or guide still describes parent content as shared across every linked child, and
the current-state docs match V44.
**Subgoal test**: `grep -rn "no per-child curriculum\|visible to all linked children"` across
`target/`, `current/` and `docs/` returns nothing.
**Repos**: [specs]

##### T1.33 [specs] — 03_student.md BR-STU-001
- **Build**: `target/requirements/03_student.md:40` still reads "parent content only if active
  `parent_child_links` exists", contradicting the updated BR-DATA-003 and the BR-STU-002 note two
  lines below it. Rewrite two-term: active link **and** a `parent_content_bindings` row for the root.
- **Done when**: BR-STU-001 names both terms.
- **Test**: `sed -n '40p' target/requirements/03_student.md | grep -c parent_content_bindings` returns 1.
- **Depends on**: None

##### T1.34 [specs] — parent-guide.md §7
- **Build**: `docs/parent-guide.md:261` says "The curriculum and topics you build are shared across
  all your linked children — there is no per-child curriculum in this version." Replace with the
  shipped behaviour: each curriculum is built for the children you choose; same-grade siblings can
  share one; you can change the audience later from the builder; a child linked after a curriculum was
  built sees nothing until you add them.
- **Done when**: The "no per-child curriculum" sentence is gone.
- **Test**: `grep -c "no per-child curriculum" docs/parent-guide.md` returns 0.
- **Depends on**: None

##### T1.35 [specs] — 05_06_07_personas.md resync
- **Build**: The parent section lags `05_parent.md` (missing BR-PAR-017–021, stale BR-PAR-014/016
  wording) while self-declaring `05_parent.md` canonical. Bring the parent block up to date, including
  BR-PAR-022.
- **Done when**: Every BR-PAR id in `05_parent.md` appears in `05_06_07_personas.md` with matching wording.
- **Test**: A diff of the BR-PAR id sets between the two files is empty.
- **Depends on**: None

##### T1.36 [specs] — 05_parent.md API table completeness
- **Build**: Add the two live-but-undocumented contracts: `PATCH
  /api/parent/curriculum/topic-contents/{id}/publish`, and the `category_id`-required-on-root note for
  `POST /api/parent/curriculum/nodes` (400 today, `parent_curriculum.py:158-211`).
- **Done when**: Both rows exist in the Parent API Endpoints table.
- **Test**: `grep -c 'topic-contents/:content_id/publish' target/requirements/05_parent.md` returns >= 1.
- **Depends on**: None

##### T1.37 [specs] — current/schema.md brought to V44
- **Build**: The Applied Migrations table stops at V41. Add V42_review_chat, V43_migrate_base64_images
  and V44_parent_content_bindings, and add the `parent_content_bindings` table plus the three
  `root_node_id` columns to the per-table sections.
- **Done when**: The table's last row is V44 and `parent_content_bindings` has a section.
- **Test**: `grep -c V44 current/schema.md` returns >= 2.
- **Depends on**: T1.7 [backend]

---

## G2 — Parent shell, child switcher, tab nav

**Goal**: `/parent` renders the mock's parent chrome — brown/amber topbar with a PARENT pill and
`+ Link child`, a child strip showing each child's name and grade, and a two-tab `Curriculum |
Results` bar.
**Goal test**: Playwright — sign in as a parent with two children (grades 6 and 9), load `/parent`:
the topbar background is `#3D2000`, a "Parent" pill is present, the child strip shows "Arjun / Grade
6" and "Meera / Grade 9" with Arjun's tab active, exactly two main tabs render, clicking Meera keeps
the tab selection and reloads persist it. A parent with zero children sees the link card and **no**
tab bar. No CSP violation is reported (`tests/e2e/g5-csp-soak.spec.ts` conventions).
**Repos**: [frontend] [backend]

### G2.1 — Grade reaches the client

**Subgoal**: `GET /api/parent/children` returns each child's grade, and the frontend model carries it.
**Subgoal test**: Integration — a parent with one child whose `student_profiles.grade='6'` and one
with a NULL grade gets `[{grade:"6"},{grade:null}]`.
**Repos**: [backend] [frontend]

##### T2.1 [backend] — grade on the children DTO
- **Build**: Add `grade: str | None = None` to `ChildLinkView` (`src/domain/models/user_metadata.py:139`)
  and `ChildLinkWithProfile` (`src/schemas/user_metadata.py:250`), populated in
  `list_children_for_parent` (`user_metadata_service.py:395-418`) from the `profile` already loaded at
  `:401` and currently discarded except for names. No join, no Keycloak call. (The loop is an existing
  per-child N+1 with an IDP fallback; the switcher makes it hotter but 10 active children is the cap —
  leaving it, batch only if it shows up in timings.)
- **Done when**: The endpoint returns `grade` for a child with a profile grade and `null` for one without.
- **Test**: `tests/unit/routes/` asserts `response.json()[0]["grade"] == "6"`.
- **Depends on**: None

##### T2.2 [frontend] — Child model carries grade
- **Build**: Add `grade?: string | null` to `ChildDto` and `grade: string | null` to `Child`
  (`parent.types.ts`), extend `ChildDtoSchema` (`domain/parent-schemas.ts`) and the mapping in
  `parentApi.listChildren` (`parent-api.ts`). Nullable — no grade means the line is omitted, never
  "Grade null".
- **Done when**: `listChildren` returns `grade: null` for a child without one rather than throwing on the schema.
- **Test**: A DTO with no `grade` key parses and maps to `grade: null`.
- **Depends on**: T2.1 [backend]

### G2.2 — Parent chrome

**Subgoal**: Parent routes render parent-branded chrome instead of the generic shared header.
**Subgoal test**: Rendering `ParentShell` shows the parent topbar and does **not** render the shared
`Header`'s nav; the 18 other call sites of `Header` are untouched.
**Repos**: [frontend]

##### T2.3 [frontend] — ParentShell renders a parent header
- **Build**: **Modify** `src/features/parent/components/parent-shell.tsx` (it exists and is an
  unthemed pass-through) to render a new `ParentHeader` in place of the shared `Header`, following the
  `src/features/admin/components/admin-header.tsx` precedent: `useAuth()` for name/roles/logout/
  role-switch, brand text, a `PARENT` pill, an initials avatar. All styling in a new
  `parent-header.module.css` — brand `#3D2000`, pill `rgba(255,200,80,.2)`/`#FAC775`, avatar `#BA7517`
  — no inline `style=` (CSP). Do not create a second shell; do not touch the shared `Header`, which
  has 18 call sites.
- **Done when**: `/parent` renders the parent topbar and the shared `Header` component is no longer mounted under `/parent`.
- **Test**: `tests/unit/features/parent/components/parent-shell.test.tsx` asserts the "Parent" pill is present.
- **Depends on**: None

##### T2.4 [frontend] — + Link child in the topbar
- **Build**: An amber `+ Link child` link to `/parent/link-child` in `ParentHeader`'s right cluster,
  styled via the CSS module.
- **Done when**: The topbar link navigates to `/parent/link-child`.
- **Test**: `getByRole("link", {name: /link child/i})` has `href="/parent/link-child"`.
- **Depends on**: T2.3 [frontend]

### G2.3 — Child and tab navigation

**Subgoal**: The active child is chosen in a strip, persists across reloads, and drives every
child-labelled surface; the two tabs switch content without navigation.
**Subgoal test**: Integration — with two children, clicking the second updates the strip's active
state, persists `parent.activeChildSub`, and re-renders the tab body against the new child; switching
tabs does not reset the child.
**Repos**: [frontend]

##### T2.5 [frontend] — ParentChildStrip
- **Build**: Extract the child strip out of `parent-dashboard.tsx` into `parent-child-strip.tsx` +
  module CSS: per child an initials avatar (deterministic colour from the sub), the display name, and
  `Grade {grade}` **omitted when grade is null**; active tab gets the amber underline; a trailing
  `+ Link child`. Keep the existing revoke affordance — it is shipped behaviour and out of scope to
  remove.
- **Done when**: A child with a null grade renders their name with no grade line, and the active child carries the active class.
- **Test**: `parent-dashboard.test.tsx` asserts "Grade 6" is present for one child and no "Grade" text renders for the null-grade child.
- **Depends on**: T2.2 [frontend]

##### T2.6 [frontend] — Active child shared across the surface
- **Build**: Lift `activeChildSub` (currently local state + `ACTIVE_CHILD_KEY` in
  `parent-dashboard.tsx:9`) into a small `ParentActiveChildContext` in `src/app/parent/providers.tsx`,
  keeping the same localStorage key so existing sessions do not lose their selection. G3's cards and
  G1.4's pill read from it.
- **Done when**: The selected child survives a reload and is readable from a component outside the dashboard.
- **Test**: Selecting the second child writes `parent.activeChildSub` and a sibling consumer reads that sub.
- **Depends on**: T2.5 [frontend]

##### T2.7 [frontend] — Curriculum | Results tab bar
- **Build**: A two-tab bar in `parent-dashboard.tsx` (`role="tablist"`, amber underline on the active
  tab), default `curriculum`. Two tabs only — Overview is not built; with the snapshot stats and
  weak-topic banner out of scope it would render identically to Curriculum.
- **Done when**: Exactly two tabs render and the Curriculum panel is shown by default.
- **Test**: `getAllByRole("tab")` has length 2 and the first is `aria-selected="true"`.
- **Depends on**: T2.6 [frontend]

##### T2.8 [frontend] — Results coming-soon placeholder
- **Build**: A static panel: "Results — coming soon / Exam results for your child's Home Study will
  appear here." **No fetch, no hardcoded zero.** Copy deliberately does not promise platform exam
  scores — BR-PAR-012 stands unchanged and the platform-results question is deferred.
- **Done when**: Selecting Results issues no network request.
- **Test**: With a fetch spy installed, clicking Results leaves the spy uncalled and shows the placeholder text.
- **Depends on**: T2.7 [frontend]

##### T2.9 [frontend] — Zero-children state hides the tabs
- **Build**: When `children.length === 0`, render only the existing "Link your child" card — no strip,
  no tab bar.
- **Done when**: A parent with no children sees the link card and zero tabs.
- **Test**: With an empty children list, `queryAllByRole("tab")` is empty.
- **Depends on**: T2.7 [frontend]

---

## G3 — Curriculum tab shows only derivable numbers

**Goal**: The Curriculum tab lists the active child's Home Study modules with counts the system can
actually produce, explains what Home Study is, and surfaces the real upload quota.
**Goal test**: Playwright — parent with roots R1 (bound to Arjun, 3 topics: 2 live/1 draft, 7 content
items) and R2 (bound to Meera). With Arjun active the tab shows one card reading `3 topics · 2 live ·
1 draft · 7 content items` and an `Open builder` CTA; switching to Meera shows R2 only. A child bound
to nothing shows "Start building", not an error. Opening the add-content modal shows `0 job(s) in
progress · 12/100 uploads today` from the server, and no element on the page renders a hardcoded zero
or a progress bar.
**Repos**: [frontend] [backend]

> Out of scope by owner call and by structure: progress %, "N topics studied", day streak,
> topics-this-week, weak-topic banner, `View results` CTA.

### G3.1 — Server derives the card metrics

**Subgoal**: One request returns every number a module card shows.
**Subgoal test**: Integration — a root with 3 topics (2 live, 1 draft) and 7 published+draft content
rows returns `{topic_count:3, live_topic_count:2, draft_topic_count:1, content_count:7}` in a single
response.
**Repos**: [backend]

##### T3.1 [backend] — Root stats on GET /nodes
- **Build**: Add a `get_parent_root_stats(root_ids)` repo method to `CoursePathNodeRepository` reusing
  the recursive-CTE shape at `:487-509` (`get_topic_counts_for_nodes`) but grouped by `root_id` with
  `count(*) FILTER (WHERE t.status='live')`, the draft complement, and a `LEFT JOIN topic_contents`
  count. Surface the four numbers on `CoursePathNodeRead` for parent root reads only. One query for
  the whole list — the alternative is a client-side N+1 across every topic of every root.
- **Done when**: `GET /api/parent/curriculum/nodes` returns the four counts per root in one round trip.
- **Test**: A root with 2 live and 1 draft topic serialises `live_topic_count == 2` and `draft_topic_count == 1`.
- **Depends on**: T1.11 [backend]

### G3.2 — The daily quota is actually daily

**Subgoal**: The 100/day parent upload cap rolls every 24 hours instead of acting as a lifetime cap,
and the counters are readable by the client.
**Subgoal test**: Integration — a parent row with `daily_jobs=100` and `daily_window_start` 25 hours
old accepts the next upload (201, `daily_jobs` reset to 1) and `GET /api/parent/curriculum/quota`
reports `1/100`; with a 1-hour-old window the same upload is 429.
**Repos**: [backend]

##### T3.2 [backend] — daily_window_start actually rolls
- **Build**: `parent_quota_counters.daily_window_start` (`src/infrastructure/models/extraction_job.py:152`)
  is written once and **never read** — a grep across `src/`, `tests/` and `alembic/` finds it only in
  the table definition and V26. So `_MAX_DAILY_PARENT_JOBS = 100` is really a lifetime cap: the 100th
  upload ever locks the parent out permanently. Fix in the two places the counter is touched, in one
  change: in `increment_quota` (`extraction_job_repository.py:529-537`) make the upsert `daily_jobs =
  CASE WHEN daily_window_start < now() - interval '1 day' THEN 1 ELSE daily_jobs + 1 END` with a
  matching `daily_window_start = CASE WHEN stale THEN now() ELSE daily_window_start END`; in the check
  at `extraction_service.py:192-196` treat a stale window as 0 used. Both halves or neither — half of
  it leaves the cap broken.
- **Done when**: A parent at `daily_jobs=100` with a >24h-old window can upload again.
- **Test**: A unit test with a 25-hour-old window asserts the create succeeds and the row reads `daily_jobs == 1`.
- **Depends on**: None

> **A live bug, not new scope.** It is in this phase because G3.3's quota line would otherwise put an
> accurate, permanent `100/100` in front of every affected parent.

##### T3.3 [backend] — GET /api/parent/curriculum/quota
- **Build**: New route in `src/api/routes/parent_extraction.py` (`require_parent()`, GET so no CSRF)
  returning `{concurrent_jobs, daily_jobs, max_concurrent: 5, max_daily: 100}` from `get_quota`, with
  the window-roll applied on read so a stale window reports 0. Today no endpoint exposes these
  counters at all — `grep quota src/api/routes/` finds only 429 handling. Constants stay in
  `extraction_service.py:28-29`, which already matches BR-PAR-008a.
- **Done when**: A parent with no quota row gets `{concurrent_jobs:0, daily_jobs:0, ...}` rather than a 404.
- **Test**: `GET /api/parent/curriculum/quota` for a fresh parent returns 200 with `daily_jobs == 0`.
- **Depends on**: T3.2 [backend]

### G3.3 — The tab

**Subgoal**: The Curriculum tab renders per-child module cards, the explainer and the quota line, with
no fabricated metric.
**Subgoal test**: Integration (vitest) — with a mocked roots response, switching the active child
swaps the rendered cards; a child with no bound root renders the "Start building" prompt; no
`progressbar` role and no "0" placeholder is emitted anywhere in the tab.
**Repos**: [frontend]

##### T3.4 [frontend] — Module cards for the active child
- **Build**: A `ParentCurriculumTab` rendering the mock's `.curr-card` grid from `GET
  /api/parent/curriculum/nodes`, filtered to roots whose `child_subs` (T1.18) contains the active
  child (T2.6). Meta line: `{topic_count} topics · {live} live · {draft} draft · {content_count}
  content items`. Footer: a single amber `Open builder` CTA to `/parent/curriculum?nodeId={root.id}` —
  note `nodeId`, not `node`: WAF rule 932236 blocks the bare parameter name `node`. No progress bar,
  no "N done".
- **Done when**: Switching the active child changes the card set without a full page navigation.
- **Test**: With two roots bound to different children, exactly one card renders per selected child.
- **Depends on**: T2.6 [frontend], T1.18 [backend], T3.1 [backend]

##### T3.5 [frontend] — "About Home Study" explainer
- **Build**: The mock's explainer card below the grid, naming the active child: content added here is
  private and visible only to {child}; import a platform board as a starting point, then add your own
  notes.
- **Done when**: The explainer names the currently active child.
- **Test**: With Arjun active, the explainer text contains "Arjun".
- **Depends on**: T3.4 [frontend]

##### T3.6 [frontend] — "Start building" empty state
- **Build**: When the active child has zero bound roots, render a "Start building" prompt linking to
  `/parent/curriculum` — **not** an error. A linked child legitimately sees nothing when the parent
  bound their curriculum to a sibling only (BR-DATA-026), and children linked after the V44 migration
  start with zero bindings by design.
- **Done when**: A child with no bound root shows the prompt and no error banner.
- **Test**: With an empty filtered root list, the "Start building" copy renders and `queryByRole("alert")` is null.
- **Depends on**: T3.4 [frontend]

##### T3.7 [frontend] — Quota line in the add-content modal
- **Build**: Fetch `GET /api/parent/curriculum/quota` in
  `src/features/content-management/components/add-content-modal.tsx` when `contentSource === "parent"`
  and render the mock's line: `{concurrent} job(s) in progress · {daily}/{max_daily} uploads today`.
  Hidden entirely if the request fails — never a hardcoded zero.
- **Done when**: The modal shows real server counters, and shows no quota line when the fetch errors.
- **Test**: With the quota endpoint mocked at `{concurrent_jobs:2, daily_jobs:12}`, the modal contains "2 job(s) in progress · 12/100 uploads today".
- **Depends on**: T3.3 [backend]

---

## G4 — Builder: content inline, topic route retired

**Goal**: A parent manages a topic's content without leaving the builder, extraction uploads render as
the mock's collapsible group card, and the separate topic screen and the dead exam link are gone.
**Goal test**: Playwright — in `/parent/curriculum`, select a node, expand a topic card: an extraction
group shows `notes.pdf` / `4 page(s) extracted · ✨ from notes.pdf`, a `Document | Text` segmented
toggle, `View`, and `▸ Show pages`; expanding lists 4 page rows each with a Published/Draft badge and
`Edit`; publishing the Text side flips the badges without a page reload. No `Create Exam` link exists
on any topic row. Navigating to `/parent/curriculum/<n>/topics/<t>` lands on
`/parent/curriculum?nodeId=<n>` with that node selected.
**Repos**: [frontend]

> Independent of G3; both sit behind G2. `groupContentsByPublish` (`content-grouping.ts:34-63`)
> already returns ordered `{key, kind, rows}` and `PublishControl` already renders the two-sided
> Document/Text choice — this goal is rendering and routing, not new domain logic.

### G4.1 — Content renders in the topic card

**Subgoal**: Every content operation available on the old topic screen is available inline on the
topic card, in the mock's layout.
**Subgoal test**: Integration (vitest + MSW) — rendering `ParentTopicRow` for a topic with one 4-page
extraction and one video mounts `TopicContentSection`, shows one group card and one standalone row,
and an add/rename/delete/publish round-trip fires the same `parentContentAdapter` calls the old page
did.
**Repos**: [frontend]

##### T4.1 [frontend] — Mount TopicContentSection in the topic card
- **Build**: In `parent-topic-row.tsx`, render `<TopicContentSection topicId={topic.id}
  adapter={parentContentAdapter} contentSource="parent" onJobDone={...} />` inside a collapsible card
  body, reusing the exact props from `parent-topic-content-page.tsx:107-114`. Keep the existing
  `hasNoContents` hint chip. Default the body collapsed so a node with many topics does not fire one
  content query per topic on mount.
- **Done when**: Content for a topic can be added and deleted from `/parent/curriculum` with no navigation.
- **Test**: `parent-topic-row.test.tsx` asserts `TopicContentSection` is mounted with `adapter === parentContentAdapter` after expanding the card.
- **Depends on**: None

##### T4.2 [frontend] — Extraction group card shell
- **Build**: In `topic-content-section.tsx`, wrap each `kind === "extraction"` group in the mock's
  `.cg-card`: header line = the group's `provenance.source_filename` (already on
  `ParentTopicContent`), meta = `{rows.length} page(s) extracted · ✨ from {source_filename}`, actions
  = `View` (opens the existing `ContentViewer` modal on the raw pdf/image row) and `Delete`.
  Standalone groups keep today's single-row rendering. CSS module only — no `style=` attributes.
- **Done when**: A 4-row extraction group renders as one card reading "4 page(s) extracted".
- **Test**: A group of 4 rows renders exactly one `.cg-card` header containing "4 page(s) extracted".
- **Depends on**: T4.1 [frontend]

##### T4.3 [frontend] — Show pages expander
- **Build**: A `▸ Show pages` / `▾ Hide pages` toggle on the group card (local `useState`), revealing
  the group's rows as page rows — title, a Published/Draft badge derived from `getGroupPublishState`
  (`publish-state.ts`), and `Edit` wired to the existing `setEditingContent`. Collapsed by default,
  matching the mock.
- **Done when**: Page rows are hidden until the expander is clicked.
- **Test**: Page titles are absent initially and present after clicking "Show pages".
- **Depends on**: T4.2 [frontend]

##### T4.4 [frontend] — Segmented Document | Text toggle
- **Build**: Restyle `content-publish-control.module.css` so `PublishControl`'s extraction branch
  renders as the mock's segmented `.pub-toggle` with `Document` / `Text` labels and an amber active
  segment. `publish-control.tsx`'s branching and `aria-label`s stay as they are — this is CSS plus the
  two visible labels, not new state.
- **Done when**: An extraction group renders one segmented control with the published side visually active.
- **Test**: With the text row published, the "Text" segment carries the active class.
- **Depends on**: T4.2 [frontend]

### G4.2 — The old route and the dead link go

**Subgoal**: No parent-facing link or route leads to a page that 404s or duplicates the builder.
**Subgoal test**: E2E — `/parent/curriculum/<n>/topics/<t>` ends on `/parent/curriculum?nodeId=<n>`
with that node selected, and a crawl of the builder finds no `href` to `/parent/exams`.
**Repos**: [frontend]

##### T4.5 [frontend] — Topic route redirects
- **Build**: Replace `src/app/parent/curriculum/[node_id]/topics/[topic_id]/page.tsx` with a
  `redirect(`/parent/curriculum?nodeId=${node_id}`)` (Next's `next/navigation` redirect; keep
  `export const dynamic = "force-dynamic"` — BR-CSP-010 requires every route dynamically rendered).
  `?nodeId=` not `?node=` (WAF 932236). `useRestoreNodeSelection` already rebuilds the breadcrumb and
  expansion from that param. Delete `parent-topic-content-page.tsx` and its two test files once
  nothing imports them.
- **Done when**: The topic URL returns a redirect to the builder with the node preselected.
- **Test**: The E2E navigation asserts the final URL is `/parent/curriculum?nodeId=<n>` and the node's topics are visible.
- **Depends on**: T4.1 [frontend]

##### T4.6 [frontend] — Remove the dead Create Exam link
- **Build**: Delete the `Create Exam` `<Link href="/parent/exams">` at `parent-topic-row.tsx:173-175`.
  The route does not exist and 404s on every topic row today. Delete the test that pins it broken —
  `tests/unit/features/parent/components/parent-topic-row.test.tsx:97` (`"links 'Create Exam' to
  /parent/exams"`). Parent exam authoring stays out of scope, so no replacement CTA.
- **Done when**: No `/parent/exams` href remains in `src/features/parent/`.
- **Test**: `parent-topic-row.test.tsx` asserts `queryByRole("link", {name:/create exam/i})` is null.
- **Depends on**: None

##### T4.7 [frontend] — Remove the Upload Content link
- **Build**: Delete the `Upload Content` `<Link>` at `parent-topic-row.tsx:169` — content is now
  inline — and its pinned test at `parent-topic-row.test.tsx:88-95`.
- **Done when**: The topic row renders no navigation link, only inline content.
- **Test**: `queryByRole("link", {name:/upload content/i})` is null while the content section is present.
- **Depends on**: T4.1 [frontend]

---

## Cross-repo dependency edges

These are the coordination points. Everything else is same-repo sequencing.

| # | From | To | Why |
|---|---|---|---|
| 1 | T1.1 [backend] | T1.3 [specs] | DDL type must read String before the model is written, or the backfill aborts on varchar→uuid |
| 2 | T1.7 [backend] | T1.4 [specs] | Migration SQL implements the amended (revoked-inclusive) backfill |
| 3 | T1.24 [frontend] | T1.10 [backend] | `child_subs` is a hard 400 — the client cannot create a root until the field exists |
| 4 | T1.26 [frontend] | T1.10 [backend] | Same, for adopt |
| 5 | T1.27 [frontend] | T1.18 [backend] | Privacy pill reads the real binding set off the root read |
| 6 | T1.28 [frontend] | T1.16, T1.17 [backend] | Binding editor calls the two new endpoints |
| 7 | T1.29 [frontend] | T1.19 [backend] | Greyed revoked-but-bound child needs `include_revoked` |
| 8 | T1.37 [specs] | T1.7 [backend] | `current/schema.md` records V44 as applied |
| 9 | T2.2 [frontend] | T2.1 [backend] | `grade` must be on the wire before the strip can render it |
| 10 | T3.4 [frontend] | T1.18, T3.1 [backend] | Cards need both `child_subs` (filter) and the counts |
| 11 | T3.7 [frontend] | T3.3 [backend] | Quota line needs the read endpoint |

**Release-coupling, not a DAG edge**: G1.2 [backend] and G1.4 [frontend] must deploy in the **same
window** — `child_subs` is a breaking change to two shipped endpoints with no fallback. An un-updated
frontend returns 400 on every create-root and every adopt.

## Ready now

No pending dependencies — startable immediately.

**Critical path first** — all of G1 hangs off these three:
- T1.3 [specs] — BR-DATA-026 DDL `child_sub` → String (unblocks T1.1 and the whole G1.1 chain)
- T1.2 [backend] — `root_node_id` columns
- T1.10 [backend] — `child_subs` on the two payloads (carries the ~32-function test update)

**Also startable:**
- T0.1 [deploy] — prod render confirmation (opportunistic, next prod window)
- T0.2 [specs] — correct the B49 entry
- T1.4 [specs] — backfill includes revoked pairs (unblocks T1.7)
- T1.33 [specs] — 03_student.md BR-STU-001
- T1.34 [specs] — parent-guide.md §7
- T1.35 [specs] — 05_06_07_personas.md resync
- T1.36 [specs] — 05_parent.md API table
- T1.19 [backend] — `?include_revoked=true`
- T2.1 [backend] — `grade` on the children DTO
- T3.2 [backend] — daily quota window roll
- T1.23 [frontend] — Add Root modal multi-select
- T1.25 [frontend] — Adopt modal multi-select
- T2.3 [frontend] — ParentShell parent header
- T4.1 [frontend] — mount TopicContentSection inline
- T4.6 [frontend] — remove the dead Create Exam link

**Longest chain**: `T1.3 → T1.1 → T1.5 → T1.6 → T1.20` and, in parallel,
`T1.8 → T1.9 → T1.12/T1.14 → T1.24/T1.26`.

## Two things to carry into implementation

- **T1.21 is the phase's real failure mode.** If `_resolve_parent_nodes` is missed, per-child binding
  is a no-op on the child's primary screen while every exam/topic/content test still passes. And the
  filter must go service-side — putting it in `get_by_owner` would show a parent nothing of their own
  tree, because that method's only other caller is the parent's own builder list.
- **T3.2 is a live bug the new UI would have exposed.** `daily_window_start` is never read, so "100
  daily" is currently a lifetime cap.

---

<!-- plan-baseline: backend:67b6cc3d45ba8b32d4314f6d464f71e1762c93f6 frontend:784f7005c231e5d6bdeb195cb83ed879c168c9a2 deploy:790e29d44989af40228f4094c4a1b7546c5efe52 -->
