# Phase 3 Plan: Student Enrollment + hAITU Topic-Doubt

> Root goal: Students can enroll in platform courses they care about, see only their enrolled content on the dashboard, and ask hAITU AI-tutor questions about topics they are studying.
>
> hAITU chat is session-only (client-side). No chat history is written to the database in Phase 3. Teacher escalation and the doubts/doubt_messages tables are deferred to Phase 4.

---

## G1 — Schema Foundation

**Goal**: The database has the `student_enrollments` table with all indexes and constraints, so every enrollment-dependent feature has a schema to write to.
**Goal test**: Run `alembic upgrade head` from V33 on a clean DB; assert `student_enrollments` exists with correct columns, UNIQUE constraint on `(student_sub, course_path_node_id)`, and `idx_student_enrollments_student_sub` index.
**Repos**: [backend]

---

### G1.1 — Enrollment Table

**Goal**: V34 migration creates `student_enrollments` with its unique constraint and index.

**Integration test**: After `alembic upgrade V34`, INSERT two rows with the same `(student_sub, course_path_node_id)` pair → assert UNIQUE constraint violation. Assert `idx_student_enrollments_student_sub` exists via `pg_indexes`.

##### T1.1 [backend] — V34 Alembic Migration for student_enrollments

- **Build**: Create `alembic/versions/V34_student_enrollments.py`. `revision="V34"`, `down_revision="V33"`. In `upgrade()`: `op.create_table("student_enrollments", ...)` with columns `id UUID PK DEFAULT gen_random_uuid()`, `student_sub TEXT NOT NULL`, `course_path_node_id UUID NOT NULL REFERENCES course_path_nodes(id) ON DELETE CASCADE`, `enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `enrollment_source VARCHAR(20) NOT NULL DEFAULT 'self'`; add `UniqueConstraint("student_sub", "course_path_node_id")`; `op.create_index("idx_student_enrollments_student_sub", "student_enrollments", ["student_sub"])`. In `downgrade()`: drop index, then drop table.
- **Done when**: `alembic upgrade V34` succeeds and `student_enrollments` table exists with correct columns, UniqueConstraint, and index.
- **Test**: Unit test asserts `upgrade()` call includes `create_table` with a `course_path_node_id` column and a `UniqueConstraint`. Integration test: `alembic downgrade V33` removes the table.
- **Depends on**: None

---

## G2 — Enrollment APIs

**Goal**: Students can discover the platform course catalog with recommendation flags, enroll in a node, and drop an enrollment via three REST endpoints.
**Goal test**: E2E — logged-in student POSTs `{course_path_node_id: <grade-node-uuid>}` to `POST /api/student/enrollments` → 201. `GET /api/student/catalog` → enrolled node has `enrolled: true`. `DELETE /api/student/enrollments/<id>` → 204. Re-fetch catalog → `enrolled: false`.
**Repos**: [backend]

---

### G2.1 — Enrollment Domain Layer

**Goal**: Domain model, repository protocol, and infrastructure repository for `student_enrollments` are in place.

**Integration test**: Instantiate `EnrollmentRepository` with a real DB session; `create()` then `get_by_student()` → 1 result. `delete_by_id_and_student()` → `get_by_id()` returns None. `get_enrolled_node_ids()` → returns a set.

##### T2.1 [backend] — StudentEnrollment Domain Model

- **Build**: Create `src/domain/models/enrollment.py` with `@dataclass class StudentEnrollment` having fields `id: UUID`, `student_sub: str`, `course_path_node_id: UUID`, `enrolled_at: datetime`, `enrollment_source: str = "self"`. No `Base` subclassing.
- **Done when**: `from domain.models.enrollment import StudentEnrollment` imports without error; dataclass instantiates successfully with all fields.
- **Test**: Unit test constructs `StudentEnrollment` with all fields and asserts each attribute is retrievable.
- **Depends on**: T1.1 [backend]

##### T2.2 [backend] — Enrollment Infrastructure Table + Mapping

- **Build**: Create `src/infrastructure/models/enrollment.py`. Define `student_enrollments = Table("student_enrollments", registry_mapper.metadata, ...)` mirroring V34 columns using SQLAlchemy `Column` types. Call `registry_mapper.map_imperatively(StudentEnrollment, student_enrollments)`. Add `import infrastructure.models.enrollment` to `src/infrastructure/models/__init__.py`.
- **Done when**: Importing `infrastructure.models.enrollment` does not raise; `"student_enrollments"` is in `registry_mapper.metadata.tables`.
- **Test**: Unit test asserts `"student_enrollments" in registry_mapper.metadata.tables` after import.
- **Depends on**: T2.1 [backend]

##### T2.3 [backend] — Abstract Enrollment Repository Protocol

- **Build**: Create `src/domain/repositories/enrollment_repository.py` with `class AbstractEnrollmentRepository(AbstractRepository[StudentEnrollment])`. Abstract methods: `get_by_student(student_sub: str) -> list[StudentEnrollment]`, `get_by_id(enrollment_id: UUID) -> StudentEnrollment | None`, `get_enrolled_node_ids(student_sub: str) -> set[UUID]`, `find_by_student_and_node(student_sub: str, node_id: UUID) -> StudentEnrollment | None`, `delete_by_id_and_student(enrollment_id: UUID, student_sub: str) -> bool`.
- **Done when**: `AbstractEnrollmentRepository` can be imported; instantiation raises `TypeError` (abstract methods unimplemented).
- **Test**: Unit test asserts `issubclass(AbstractEnrollmentRepository, AbstractRepository)` is True.
- **Depends on**: T2.1 [backend]

##### T2.4 [backend] — Concrete EnrollmentRepository

- **Build**: Create `src/infrastructure/repositories/enrollment_repository.py` with `class EnrollmentRepository(BaseRepository[StudentEnrollment], AbstractEnrollmentRepository)`. Implement all abstract methods via SQLAlchemy `select`/`delete`. `get_enrolled_node_ids` returns `set[UUID]` via a single `select(student_enrollments.c.course_path_node_id)` filtered by `student_sub`. `find_by_student_and_node` uses `WHERE student_sub=? AND course_path_node_id=?`. `delete_by_id_and_student` uses `DELETE WHERE id=? AND student_sub=?` and returns affected row count (True if > 0).
- **Done when**: All five methods execute SQL without error against a real test DB.
- **Test**: Integration test: insert enrollment via `add()`, call `get_enrolled_node_ids(student_sub)`, assert the node UUID is in the result set.
- **Depends on**: T2.2 [backend], T2.3 [backend]

---

### G2.2 — Catalog + Enrollment Service

**Goal**: `EnrollmentService` encapsulates enrollment creation, deletion, and catalog assembly logic.

**Integration test**: Instantiate `EnrollmentService` with a real DB session; call `enroll(student_sub, node_id)` for a valid platform node → returns `StudentEnrollment`. Call `enroll` again with same args → raises `AlreadyEnrolledError`. Call `get_catalog(student_sub, student_grade)` → `enrolled: true` for that node, `enrollment_id` populated. Call `drop(enrollment_id, student_sub)` → passes. Re-call `get_catalog` → `enrolled: false`.

##### T2.5 [backend] — Enrollment Domain Exceptions

- **Build**: In `src/domain/exceptions.py`, add `class AlreadyEnrolledError(Exception)` and `class EnrollmentNotFoundError(Exception)`.
- **Done when**: Both can be imported from `domain.exceptions` and raised/caught in test code.
- **Test**: Unit test: `raise AlreadyEnrolledError()` inside try/except → assert caught.
- **Depends on**: None

##### T2.6 [backend] — CatalogNodeCard Schema

- **Build**: In `src/schemas/student_dashboard.py`, add `class CatalogNodeCard(BaseModel)` with fields: `id: UUID`, `name: str`, `node_type: str`, `owner_type: str`, `enrolled: bool`, `recommended: bool`, `topic_count: int = 0`, `enrollment_id: UUID | None = None`.
- **Done when**: `CatalogNodeCard(id=uuid4(), name="Grade 8", node_type="grade", owner_type="platform", enrolled=False, recommended=True)` instantiates without error.
- **Test**: Unit test: `CatalogNodeCard.model_validate({...}).enrollment_id` is `None` when not provided.
- **Depends on**: None

##### T2.7 [backend] — EnrollmentService

- **Build**: Create `src/domain/services/enrollment_service.py` with `class EnrollmentService(__init__(self, enrollment_repo: AbstractEnrollmentRepository, node_repo: AbstractCoursePathNodeRepository))`. Implement: `async def enroll(student_sub, node_id)` — checks node exists and `owner_type=="platform"` (raises `ValueError` if not); checks `find_by_student_and_node` is None (raises `AlreadyEnrolledError` if found); creates and `add()`s a `StudentEnrollment`. Implement: `async def drop(enrollment_id, student_sub)` — calls `delete_by_id_and_student`; raises `EnrollmentNotFoundError` if 0 rows deleted. Implement: `async def get_catalog(student_sub, student_grade: str | None)` — fetches all platform root nodes via `node_repo.get_platform_root_nodes()`; gets `enrolled_node_ids`; for each node computes `enrolled`, `recommended` (case-insensitive match of node name against `student_grade`), and `enrollment_id` (set if node is in enrolled set); returns `list[CatalogNodeCard]`.
- **Done when**: All three methods callable with mocked repos; unit test confirms `recommended=True` when grade matches.
- **Test**: Unit test with mocked repos: `get_catalog()` returns `recommended=True` when `student_grade` matches a node name.
- **Depends on**: T2.4 [backend], T2.5 [backend], T2.6 [backend]

---

### G2.3 — Enrollment HTTP Endpoints

**Goal**: Three REST endpoints serve catalog, create, and delete enrollment operations.

**Integration test**: Using the integration test client with student identity and CSRF override: `GET /api/student/catalog` → 200, list returned. `POST /api/student/enrollments` with valid node UUID → 201, body has `id`. `POST` again with same node → 409. `DELETE /api/student/enrollments/<id>` → 204. `DELETE` again → 404.

##### T2.8 [backend] — Enrollment Route Module

- **Build**: Create `src/api/routes/student_enrollment.py`. `router = APIRouter()`. Factory `get_enrollment_service(session)` wires `EnrollmentService(EnrollmentRepository(session), CoursePathNodeRepository(session))`. All three routes include `csrf_protected: Annotated[None, Depends(validate_csrf)]` per codebase pattern. Implement:
  - `GET /catalog` — calls `service.get_catalog(user.sub, grade)`; returns `list[CatalogNodeCard]`. Fetches grade via `StudentProfileRepository(session).get_by_sub(user.sub)` → `profile.grade` (pass `None` if no profile or `grade` unset). NOTE: onboarding does not collect a grade (Phase 0 made the student-ready step CTA-only), so `grade` is `None` for most students and `recommended` will be `false` across the catalog until a grade is set via the student profile endpoint — this is acceptable for Phase 3 and `get_catalog` already degrades gracefully on `None`.
  - `POST /enrollments` body `StudentEnrollmentCreate` → calls `service.enroll()`; returns 201 with `StudentEnrollmentRead`. Catches `AlreadyEnrolledError` → 409. Catches `ValueError` → 404.
  - `DELETE /enrollments/{enrollment_id}` → calls `service.drop()`; returns 204. Catches `EnrollmentNotFoundError` → 404.
- **Done when**: `from api.routes.student_enrollment import router` succeeds; three routes registered on router.
- **Test**: Unit test with `TestClient` + mocked service: `POST /enrollments` with `AlreadyEnrolledError` → 409 response.
- **Depends on**: T2.7 [backend], T2.10 [backend]

##### T2.9 [backend] — Register Enrollment Router

- **Build**: In `src/api/router.py`, import `student_enrollment` from `api.routes`. In `register_router()`, add `app.include_router(student_enrollment.router, prefix="/api/student", tags=["Student Enrollment"])`.
- **Done when**: FastAPI OpenAPI spec includes `/api/student/catalog`, `/api/student/enrollments`, and `/api/student/enrollments/{enrollment_id}`.
- **Test**: Integration test: `GET /api/student/catalog` returns 200 (not 404).
- **Depends on**: T2.8 [backend]

##### T2.10 [backend] — StudentEnrollment Read/Create Schemas

- **Build**: In `src/schemas/student_dashboard.py`, add `class StudentEnrollmentRead(BaseModel)` with fields `id: UUID`, `student_sub: str`, `course_path_node_id: UUID`, `enrolled_at: datetime`, `enrollment_source: str`. Add `class StudentEnrollmentCreate(BaseModel)` with field `course_path_node_id: UUID`.
- **Done when**: Both schemas import and validate without error.
- **Test**: Unit test: `StudentEnrollmentRead.model_validate({"id": str(uuid4()), ...})` raises no exception.
- **Depends on**: None

---

## G3 — Enrolled-Only Content Filter

**Goal**: All four student-facing content endpoints return only content within a student's enrolled subtrees; unenrolled content is blocked (403 for node/topic access, empty list for dashboard/nodes list).
**Goal test**: E2E — student enrolled in Grade 8: `GET /api/student/nodes?owner_type=platform` returns only Grade 8 subtree nodes. `GET /api/student/nodes/{grade-9-subject}/topics` → 403. `GET /api/student/dashboard` → only Grade 8 node in `platform_nodes`. Student with zero enrollments → `platform_nodes=[]`.
**Repos**: [backend]

---

### G3.1 — Enrollment-Aware Query Methods

**Goal**: The repository layer has the subtree-scoped query methods needed by the enrollment filter.

**Integration test**: Seed a 3-level tree (grade→subject→course); enroll student in grade node; call `get_subtree_node_ids({grade_id})` → assert all three node UUIDs returned. Call `get_enrolled_root_nodes({grade_id})` → assert grade `CoursePathNode` returned.

##### T3.1a [backend] — get_subtree_node_ids (Recursive CTE)

- **Build**: Add `async def get_subtree_node_ids(self, root_node_ids: list[UUID]) -> set[UUID]` to `AbstractCoursePathNodeRepository` as an abstract method, and implement in `CoursePathNodeRepository` via recursive CTE: `WITH RECURSIVE subtree AS (SELECT id FROM course_path_nodes WHERE id = ANY(:root_ids) UNION ALL SELECT c.id FROM course_path_nodes c JOIN subtree s ON c.parent_id = s.id) SELECT id FROM subtree`. Returns `set[UUID]`.
- **Done when**: Integration test with seeded 3-level tree confirms all 3 node IDs returned when root is passed.
- **Test**: Integration test: seed grade→subject→course; call `get_subtree_node_ids([grade_id])`; assert `{grade_id, subject_id, course_id}` ⊆ result.
- **Depends on**: T2.4 [backend]

##### T3.1b [backend] — get_enrolled_root_nodes (Filter by Enrolled Set)

- **Build**: Add `async def get_enrolled_root_nodes(self, enrolled_node_ids: set[UUID]) -> list[CoursePathNode]` to `AbstractCoursePathNodeRepository` and implement in `CoursePathNodeRepository` via `SELECT * FROM course_path_nodes WHERE id = ANY(:ids) AND owner_type = 'platform'`. Returns `[]` for empty set.
- **Done when**: Unit test: call `get_enrolled_root_nodes({grade_id})` with seeded grade node → returns that `CoursePathNode`. Empty set → returns `[]`.
- **Test**: Unit test with mocked session: `enrolled_node_ids=set()` → empty list returned.
- **Depends on**: T3.1a [backend]

##### T3.2 [backend] — is_topic_in_enrolled_subtree (Topic Visibility Check)

- **Build**: Add `async def is_topic_in_enrolled_subtree(self, topic_id: UUID, enrolled_node_ids: set[UUID]) -> bool` to `AbstractTopicRepository` and implement in `TopicRepository`. Fetches `topic.course_path_node_id`; returns `True` if that node ID is in `enrolled_node_ids`. Returns `False` if topic not found.
- **Done when**: Unit test confirms `True` when topic's `course_path_node_id` is in the provided set; `False` otherwise.
- **Test**: Unit test: mock `select(Topic)` returning a topic with `course_path_node_id=X`; assert `is_topic_in_enrolled_subtree(topic_id, {X})` is `True` and `is_topic_in_enrolled_subtree(topic_id, {Y})` is `False`.
- **Depends on**: None

---

### G3.2 — Enrollment-Aware Dashboard Service

**Goal**: `StudentDashboardService` uses enrollment data to filter `platform_nodes` and enforce subtree access on all four endpoints.

**Integration test**: Student enrolled in `grade_id`; `service.get_dashboard(student_sub)` → `platform_nodes` contains only the Grade node. Unenrolled student → `platform_nodes=[]`. Unenrolled student calling `get_live_topics_for_node(unenrolled_node_id)` → `PermissionError`.

##### T3.3 [backend] — StudentDashboardService Enrollment Injection

- **Build**: Modify `StudentDashboardService.__init__` to accept an additional `enrollment_repo: AbstractEnrollmentRepository | None = None`. Modify `get_dashboard()`: if `enrollment_repo` set, fetch `enrolled_node_ids`; if empty → `platform_nodes=[]`; else call `node_repo.get_enrolled_root_nodes(enrolled_node_ids)` for platform nodes. Modify `get_node_tree()` for `owner_type=="platform"`: compute enrolled subtree via `get_subtree_node_ids(list(enrolled_node_ids))`; filter returned nodes to subtree. Modify `get_live_topics_for_node()`: verify `node_id` in enrolled subtree → raise `PermissionError` if not. Modify `get_topic_content()`: check `is_topic_in_enrolled_subtree(topic_id, enrolled_subtree)` → raise `PermissionError` if `False`.
- **Done when**: Unit test with mocked `enrollment_repo` returning `set()` → `get_dashboard()` returns `{"platform_nodes": [], ...}`.
- **Test**: Unit test: mock `enrollment_repo.get_enrolled_node_ids()` returns `set()` → assert `get_dashboard()` result has `platform_nodes == []`.
- **Depends on**: T2.4 [backend], T3.1b [backend], T3.2 [backend]

##### T3.4 [backend] — Wire EnrollmentRepository into Dashboard Route

- **Build**: In `src/api/routes/student_dashboard.py`, update the `get_student_dashboard_service()` factory to also instantiate `EnrollmentRepository(session)` and pass it to `StudentDashboardService`. Map `PermissionError` raised by `get_live_topics_for_node` and `get_topic_content` to HTTP 403 in the respective route handlers.
- **Done when**: Integration test — student with zero enrollments: `GET /api/student/dashboard` → 200 with `platform_nodes=[]`. Student with no enrollment in a node: `GET /api/student/nodes/{unenrolled-node-id}/topics` → 403.
- **Test**: Integration test: seed platform grade node; `GET /api/student/nodes/{grade_id}/topics` with no-enrollment student → 403.
- **Depends on**: T3.3 [backend]

---

## G4 — hAITU Retrieval Service

**Goal**: `HaituService` implements the 4-stage retrieval pipeline (rewrite → hybrid search → rerank → synthesis) and returns a stateless `HaituResponse` with `response` and `escalation_ready`. No database interaction.
**Goal test**: E2E via mocked LLM + seeded vector store — `HaituService.answer(topic_id, message, history, topic_context)` returns a dict with `response: str` and `escalation_ready: bool`. If stage-1 `safe=False`, assert `_stage2_retrieve` is never called.
**Repos**: [backend]

---

### G4.0 — Shared LlamaIndex Helper Extraction (Refactor)

**Goal**: The embed-model builder, DB-URL parser, and LM Studio embedding adapter live in a neutral shared module that both the worker drain loop and `HaituService` import — avoiding a domain service importing from the `worker/` entrypoint layer (DDD).

**Integration test**: The existing `rag_outbox_loop` integration test still drains the outbox after the helpers are relocated; a unit test imports all three names from the new module.

##### T4.0 [backend] — Extract parse_db_url / build_embed_model / LmStudioEmbedding to a shared module

- **Build**: Create `src/infrastructure/embedding.py`. Move `_parse_db_url`, `_build_embed_model`, and `_LmStudioEmbedding` out of `src/worker/rag_outbox_loop.py` into it as public names: `parse_db_url`, `build_embed_model`, `LmStudioEmbedding`. **Refactor `build_embed_model` to accept `EmbeddingSettings` (not the full `Settings`)** so `HaituService` — which only holds `EmbeddingSettings` — can reuse it. Update `rag_outbox_loop.py` to import from `infrastructure.embedding` and call `build_embed_model(settings.embedding)`. No behaviour change to the worker.
- **Done when**: `from infrastructure.embedding import parse_db_url, build_embed_model, LmStudioEmbedding` succeeds; the worker still drains the outbox (existing integration test passes); `rag_outbox_loop.py` no longer defines the three helpers.
- **Test**: Existing `rag_outbox_loop` unit/integration tests pass against the relocated helpers (update their import paths). New unit test: `build_embed_model(EmbeddingSettings(model_spec="lmstudio://m@h:1/v1"))` returns an `LmStudioEmbedding`.
- **Depends on**: None (pure refactor of existing Phase 2 code).

---

### G4.1 — Stage 1: Query Rewrite + Intent + Safety

**Goal**: LLM is called once to return a structured `{rewritten_query, intent, safe, reject_reason}`.

**Integration test**: With live Ollama (skipped if absent), call `_stage1_rewrite("What is photosynthesis?")` → returned `HaituRewriteResult` has `rewritten_query`, `intent`, `safe`.

##### T4.1 [backend] — HaituService Skeleton + Stage 1

- **Build**: Create `src/domain/services/haitu_service.py`. Define `@dataclass class HaituRewriteResult` with `rewritten_query: str`, `intent: Literal["definition","computation","explanation"]`, `safe: bool`, `reject_reason: str | None`. Define `@dataclass class HaituResponse` with `response: str`, `escalation_ready: bool`. Define `class HaituService(__init__(settings: HaituSettings, embedding_settings: EmbeddingSettings, database_url: str))`. Implement `async def _stage1_rewrite(self, query: str) -> HaituRewriteResult` using `asyncio.to_thread()` to call the LLM (build a LlamaIndex chat LLM from `settings.model_spec` using the same `lmstudio://`-prefix dispatch the shared `infrastructure.embedding` module uses — this is the chat LLM, distinct from the embed model). Parse JSON response; on parse failure default to `safe=True, intent="explanation", rewritten_query=query`.
- **Done when**: `HaituService` imports without error; `_stage1_rewrite` is callable in a unit test with a mocked LLM call.
- **Test**: Unit test: mock LLM returning `'{"rewritten_query":"Q","intent":"definition","safe":true,"reject_reason":null}'` → assert `_stage1_rewrite()` returns `HaituRewriteResult(rewritten_query="Q", intent="definition", safe=True, reject_reason=None)`.
- **Depends on**: T4.0 [backend]

---

### G4.2 — Stage 2: Hybrid Retrieval

**Goal**: The service embeds the rewritten query with bge-m3 and retrieves candidate chunks from `data_topic_content_chunks` filtered by `topic_id` using `QueryFusionRetriever` in `relative_score` mode.

**Integration test**: Skipped if no Ollama. With seeded chunks, `_stage2_retrieve(rewritten_query, topic_id, with_rerank=False)` → at least 1 `NodeWithScore` returned.

##### T4.2 [backend] — Stage 2 Hybrid Retrieval

- **Build**: In `haitu_service.py`, implement `async def _stage2_retrieve(self, query: str, topic_id: UUID, *, with_rerank: bool) -> list` using `asyncio.to_thread()`. Build `PGVectorStore.from_params(hybrid_search=True, text_search_config="english")` using `parse_db_url(self._database_url)` from the shared `infrastructure.embedding` module (T4.0). **Build the bge-m3 query embed model via `build_embed_model(self._embedding_settings)` from the same shared module (includes the `LmStudioEmbedding` adapter required for LM Studio in dev). Pass this embed model explicitly to `VectorStoreIndex.from_vector_store(vector_store, embed_model=...)` and the dense retriever — do not rely on LlamaIndex's global default, which resolves to an OpenAI model and fails.** Compose `QueryFusionRetriever(retrievers=[dense, sparse], mode="relative_score", num_queries=1)` with `topic_id` metadata filter (the drain loop stores `metadata_->>'topic_id'` per chunk — confirmed in `rag_outbox_loop._build_nodes`). Retrieve `top_k * 3` if `with_rerank` else `top_k`.
- **Done when**: Unit test with mocked `QueryFusionRetriever` confirms method returns mock results.
- **Test**: Unit test: mock `QueryFusionRetriever.retrieve()` returning 3 `NodeWithScore` → assert 3 results returned.
- **Depends on**: T4.1 [backend], T4.0 [backend]

---

### G4.3 — Stage 3: Optional Reranking

**Goal**: When `haitu_settings.rerank_model != ""` the service reranks and trims to `top_k`; otherwise passes through unchanged.

**Integration test**: `rerank_model=""` → `_stage3_rerank(nodes, query)` returns same nodes unchanged.

##### T4.3 [backend] — Stage 3 Rerank

- **Build**: In `haitu_service.py`, implement `async def _stage3_rerank(self, nodes: list, original_query: str) -> list`. If `self._settings.rerank_model == ""`: return nodes unchanged. Else `asyncio.to_thread()` with `LLMRerank` or `SentenceTransformerRerank` configured with `self._settings.rerank_model`; trim to `self._settings.top_k`.
- **Done when**: Unit test: `HaituSettings(rerank_model="")` → `_stage3_rerank([n1,n2,n3], "Q")` returns the same 3-item list.
- **Test**: Unit test: instantiate `HaituService` with `rerank_model=""`; call `_stage3_rerank([n1,n2,n3], "Q")` → result is same list.
- **Depends on**: T4.2 [backend]

---

### G4.4 — Stage 4: LLM Synthesis + Public Pipeline Method

**Goal**: `_stage4_synthesize` assembles context and calls `CompactAndRefine` with an intent-specific prompt pair; `answer()` chains all 4 stages with early-exit on safety failure.

**Integration test**: Mock retrieval returning 2 chunks; `_stage4_synthesize(nodes, query, "definition", topic_context)` → `HaituResponse.response` is a non-empty string and `escalation_ready` is a bool.

##### T4.4 [backend] — Stage 4 Synthesis + Full Pipeline

- **Build**: In `haitu_service.py`, implement `async def _stage4_synthesize(self, nodes: list, original_query: str, intent: str, topic_context: dict) -> HaituResponse`. Uses `asyncio.to_thread()`. Builds `CompactAndRefine` response synthesizer with intent-specific QA prompt (definition → define-and-explain, computation → step-by-step, explanation → explain-in-depth) and refine prompt. Constructs context string from `topic_context` (topic title, grade, subject — mastery_score always "N/A") + chunk texts. Checks response text for escalation signals (response references inability to answer or is very short) → sets `escalation_ready`. Returns `HaituResponse`. Also implement public `async def answer(self, topic_id: UUID, message: str, history: list[dict], topic_context: dict) -> HaituResponse` — chains all 4 stages. On `safe=False` early return: `HaituResponse(response=rewrite_result.reject_reason or "I can't answer that.", escalation_ready=False)`.
- **Done when**: Unit test confirms `answer()` short-circuits on `safe=False` without calling `_stage2_retrieve`.
- **Test**: Unit test: mock `_stage1_rewrite()` returning `HaituRewriteResult(safe=False, reject_reason="Off topic", ...)` → call `answer()` → assert `response == "Off topic"` and `_stage2_retrieve` mock was not called.
- **Depends on**: T4.3 [backend]

---

## G5 — hAITU Topic-Doubt Endpoint

**Goal**: `POST /api/haitu/topic-doubt` validates enrollment, rate-limits per student, runs the 4-stage pipeline, and returns `{response, escalation_ready}`. Fully stateless — no database writes.
**Goal test**: E2E — student enrolled in a grade node: POST `{topic_id, enrollment_id, message: "What is osmosis?", history: []}` → 200 with `response` string and `escalation_ready` bool. Wrong `enrollment_id` (other student's) → 403. Topic not in enrolled subtree → 403. 21st call within same hour → 429.
**Repos**: [backend]

---

### G5.1 — In-Memory Rate Limiter

**Goal**: A module-level rate limiter enforces max 20 calls per student per rolling hour.

**Unit test**: Loop 20 calls of `check_and_increment("student1")` → all return `False`. 21st call returns `True`. After bucket rolls over, 1st call returns `False` again.

##### T5.1 [backend] — HaituRateLimiter Utility

- **Build**: Create `src/domain/services/haitu_rate_limiter.py`. Define `class HaituRateLimiter`. Stores `_counts: dict[tuple[str, str], int]` keyed by `(student_sub, hour_bucket_str)` where `hour_bucket_str = datetime.now(UTC).strftime("%Y-%m-%dT%H")`. Method `check_and_increment(student_sub: str) -> bool`: computes current bucket; removes stale entries (keys where bucket != current hour); increments `_counts[(student_sub, bucket)]`; returns `True` if count after increment > 20 (exceeded), `False` otherwise. Uses `threading.Lock` for safety. Module-level instance: `haitu_rate_limiter = HaituRateLimiter()`.
- **Done when**: 20 calls to `check_and_increment("s1")` return `False`; 21st returns `True`.
- **Test**: Unit test: create `HaituRateLimiter`; loop 20 calls of `check_and_increment("s1")` → all `False`; 21st → `True`.
- **Depends on**: None

---

### G5.2 — hAITU Endpoint

**Goal**: The route validates enrollment, applies rate limiting, runs the pipeline, and returns the response — no DB writes.

**Integration test**: With seeded enrollment and mocked `HaituService.answer()` returning canned `HaituResponse`: `POST /api/haitu/topic-doubt` with valid body → 200. Wrong `enrollment_id` → 403. Rate limiter returning exceeded → 429.

##### T5.2 [backend] — HaituDoubt Request/Response Schemas

- **Build**: In `src/schemas/student_dashboard.py`, add `class HaituDoubtMessageSchema(BaseModel)` with `role: str`, `content: str`. Add `class HaituDoubtRequest(BaseModel)` with `topic_id: UUID`, `enrollment_id: UUID`, `message: str`, `history: list[HaituDoubtMessageSchema] = []`. Add `class HaituDoubtResponse(BaseModel)` with `response: str`, `escalation_ready: bool`.
- **Done when**: All three schemas validate without error.
- **Test**: Unit test: `HaituDoubtRequest.model_validate({"topic_id": str(uuid4()), "enrollment_id": str(uuid4()), "message": "test", "history": []})` succeeds.
- **Depends on**: None

##### T5.3 [backend] — HaituDoubtService (Orchestration, No DB Writes)

- **Build**: Create `src/domain/services/haitu_doubt_service.py`. `class HaituDoubtService(__init__(self, enrollment_repo: AbstractEnrollmentRepository, node_repo: AbstractCoursePathNodeRepository, topic_repo: AbstractTopicRepository, haitu_service: HaituService, rate_limiter: HaituRateLimiter))`. (`topic_repo` is required — steps 3 and 5 both need the topic's `course_path_node_id`.) Implement `async def handle(self, user_sub: str, topic_id: UUID, enrollment_id: UUID, message: str, history: list[dict]) -> HaituDoubtResponse`:
  1. Fetch `enrollment = await enrollment_repo.get_by_id(enrollment_id)` → raise `PermissionError` if None or `enrollment.student_sub != user_sub`.
  2. Compute enrolled subtree via `node_repo.get_subtree_node_ids([enrollment.course_path_node_id])`.
  3. Fetch `topic = await topic_repo.get(topic_id)` → raise `PermissionError` if None; verify `topic.course_path_node_id in subtree` → raise `PermissionError` if not.
  4. Call `rate_limiter.check_and_increment(user_sub)` → raise `RateLimitExceededError` if True. (Add `class RateLimitExceededError(Exception)` to `domain/exceptions.py` in this task.)
  5. Build `topic_context = {title, grade, subject}` from node ancestry (`node_repo.get_path_to_root(topic.course_path_node_id)`).
  6. Call `await haitu_service.answer(topic_id, message, history, topic_context)` → return `HaituDoubtResponse(response=result.response, escalation_ready=result.escalation_ready)`.
- **Done when**: Unit test with wrong `enrollment.student_sub` → `PermissionError` raised before any LLM call.
- **Test**: Unit test: mock `enrollment_repo.get_by_id()` returning `StudentEnrollment(student_sub="other")` while `user_sub="a"` → assert `PermissionError` raised; `haitu_service.answer` not called.
- **Depends on**: T4.4 [backend], T5.1 [backend], T2.4 [backend], T3.1a [backend]

##### T5.4 [backend] — haitu Route Module (Thin Handler)

- **Build**: Create `src/api/routes/haitu.py`. `router = APIRouter()`. Factory `get_haitu_doubt_service(session)` wires `HaituDoubtService(EnrollmentRepository(session), CoursePathNodeRepository(session), TopicRepository(session), HaituService(settings.haitu, settings.embedding, settings.database_url), haitu_rate_limiter)`. Implement `POST /topic-doubt` with `user: CurrentUser = Depends(require_student())`, `csrf_protected: Annotated[None, Depends(validate_csrf)]`. Calls `service.handle(user.sub, body.topic_id, body.enrollment_id, body.message, body.history)`. Maps `PermissionError → 403`, `RateLimitExceededError → 429`. Returns `HaituDoubtResponse`.
- **Done when**: Route imports without error; unit test with mocked service: `PermissionError` → 403; `RateLimitExceededError` → 429.
- **Test**: Unit test with `TestClient` + mocked `HaituDoubtService.handle()` raising `PermissionError` → response status 403.
- **Depends on**: T5.3 [backend], T5.2 [backend]

##### T5.5 [backend] — Register hAITU Router

- **Build**: In `src/api/router.py`, import `haitu` from `api.routes`. Add `app.include_router(haitu.router, prefix="/api/haitu", tags=["hAITU"])`.
- **Done when**: FastAPI OpenAPI spec includes `POST /api/haitu/topic-doubt`.
- **Test**: Integration test: `POST /api/haitu/topic-doubt` with missing body → 422 (schema validation), not 404.
- **Depends on**: T5.4 [backend]

---

## G6 — APISIX Route for /api/haitu + Backend Env Vars

**Goal**: The `/api/haitu/*` endpoint is accessible through APISIX with WAF enabled, and the backend container has all HAITU + EMBEDDING env vars so `HaituService` can boot.
**Goal test**: E2E — `POST /api/haitu/topic-doubt` through APISIX (port 9080) with empty body → 422 (route reaches backend). `GET /api/health` → healthy.
**Repos**: [deploy]

---

##### T6.1 [deploy] — 19-api-haitu.json Route Config

- **Build**: Create `common/routes/19-api-haitu.json`. Model after `17-api-actions.json` (a `secured-api` POST route): `id: "api-haitu"`, `uris: ["/api/haitu/*"]`, `methods: ["POST"]`, `priority: 20`, `plugin_config_id: "secured-api"`, upstream `backend:8000` with `timeout: {connect: 10, send: 360, read: 360}` (matches `llm_request_timeout` default — long send/read because hAITU runs a multi-stage LLM pipeline). Do **not** hand-create `.templated/dev/` or `.templated/staging/` copies — `common/routes/.templated/` is gitignored and regenerated at deploy time by `create_route_config.sh`, which falls back to `common/routes/` when no env-specific template exists. Like `17-api-actions.json`, this route has no env-specific WAF tuning, so the single `common/routes/` file is sufficient.
- **Done when**: `python -m json.tool common/routes/19-api-haitu.json` exits 0.
- **Test**: `python -m json.tool common/routes/19-api-haitu.json` exits 0. Integration test: APISIX Admin API accepts the route config.
- **Depends on**: T5.5 [backend]

##### T6.2 [deploy] — HAITU + EMBEDDING Env Vars in Backend Service

- **Build**: In `common/docker-compose.yml`, add to the `backend` service `environment:` block (they already exist in `worker`; copy same variable names): `HAITU__MODEL_SPEC`, `HAITU__OLLAMA_BASE_URL`, `HAITU__MAX_TOKENS`, `HAITU__TOP_K`, `HAITU__RERANK_MODEL`, `HAITU__LLM_CONTEXT_WINDOW`, `HAITU__LLM_REQUEST_TIMEOUT`, `HAITU__LLM_THINKING`, `EMBEDDING__MODEL_SPEC`, `EMBEDDING__OLLAMA_BASE_URL`, `EMBEDDING__EMBED_DIM`. All reference existing `${VAR}` env vars already declared in the worker block.
- **Done when**: `docker-compose config` shows these vars under the `backend` service block without errors.
- **Test**: `docker-compose config 2>&1 | grep "HAITU__MODEL_SPEC"` shows the variable under the backend block.
- **Depends on**: None

---

## G7 — Browse Courses Enrollment Screen (Frontend)

**Goal**: Students can browse a catalog grid of platform nodes, enroll by clicking "Enroll", and drop by clicking "Drop", with toast feedback, empty/loading states, and a persistent nav link to discover the page.
**Goal test**: E2E — student navigates to `/enroll`; sees catalog grid; clicks "Enroll" on a card → button changes to "Drop"; navigates to `/home` → enrolled node appears in Platform Board; returns to `/enroll`, clicks "Drop" → button reverts to "Enroll".
**Repos**: [frontend]

---

### G7.1 — Catalog API Layer

**Goal**: `useStudentCatalog` hook and catalog API functions are available and type-safe.

**Integration test**: Mock `fetch` returning a canned catalog response; render `useStudentCatalog` in a test harness → `catalogNodes` populated; calling `enroll(nodeId)` triggers `POST /api/student/enrollments` fetch call.

##### T7.1 [frontend] — Catalog + Enrollment Types

- **Build**: In `src/features/student/types/student.types.ts`, add `export interface CatalogNode { id: string; name: string; node_type: string; owner_type: string; enrolled: boolean; recommended: boolean; topic_count: number; enrollment_id: string | null; }` and `export interface StudentEnrollment { id: string; student_sub: string; course_path_node_id: string; enrolled_at: string; enrollment_source: string; }`.
- **Done when**: Both interfaces compile without TypeScript errors.
- **Test**: `tsc --noEmit` exits 0 for a file importing `CatalogNode`.
- **Depends on**: None

##### T7.2 [frontend] — Catalog API Functions

- **Build**: In `src/features/student/api/student-api.ts`, add three functions to `studentApi`: `getCatalog(csrfToken): Promise<CatalogNode[]>` — `GET /api/student/catalog` via `fetchWithCSRFRetry`. `enroll(csrfToken, coursePathNodeId): Promise<StudentEnrollment>` — `POST /api/student/enrollments` with `{course_path_node_id}` via `fetchWithCSRFRetry`; throws `ApiError` on non-201. `dropEnrollment(csrfToken, enrollmentId): Promise<void>` — `DELETE /api/student/enrollments/${enrollmentId}` via `fetchWithCSRFRetry`; throws `ApiError` on non-204.
- **Done when**: All three functions exported from `studentApi` and compile without error.
- **Test**: Unit test: mock `fetch` returning `{ok: true, json: () => [...]}` → `studentApi.getCatalog("")` resolves to the array.
- **Depends on**: T7.1 [frontend], T2.9 [backend]

##### T7.3 [frontend] — useStudentCatalog Hook

- **Build**: Create `src/features/student/hooks/use-student-catalog.ts`. Export `function useStudentCatalog()` returning `{ catalogNodes: CatalogNode[], isLoading: boolean, error: Error | null, enroll: (nodeId: string) => Promise<void>, drop: (enrollmentId: string) => Promise<void> }`. `useState` for nodes/loading/error. `useEffect` fetches catalog on mount. `enroll` calls `studentApi.enroll()` then re-fetches catalog. `drop` calls `studentApi.dropEnrollment()` then re-fetches. No Redux, no React Query, no Axios.
- **Done when**: Hook renders without error in a React test harness with mocked `studentApi`; `catalogNodes.length === 2` after mount with 2-node mock.
- **Test**: Unit test with mocked `studentApi.getCatalog()` returning 2 nodes → after render, `catalogNodes.length === 2`.
- **Depends on**: T7.2 [frontend]

---

### G7.2 — Catalog UI

**Goal**: `BrowseCoursesPage` renders the catalog grid with enroll/drop buttons, toast feedback, and a persistent nav link from the student header.

**Integration test**: Render `BrowseCoursesPage` with mocked hook returning 1 enrolled node + 1 unenrolled node → assert 1 "Drop" button and 1 "Enroll" button. Click "Enroll" → assert `studentApi.enroll` was called.

##### T7.4 [frontend] — CatalogCard Component

- **Build**: Create `src/features/student/components/catalog-card.tsx`. Props: `node: CatalogNode`, `onEnroll: (id: string) => void`, `onDrop: (enrollmentId: string) => void`. Renders: node name, a type chip for `node.node_type`, a "Recommended" badge if `node.recommended`. If `node.enrolled`: "Drop" button (calls `onDrop(node.enrollment_id!)`). If not enrolled: "Enroll" button (calls `onEnroll(node.id)`).
- **Done when**: Component renders; "Enroll" button present when `enrolled=false`, "Drop" button when `enrolled=true`.
- **Test**: Unit test: render `CatalogCard` with `enrolled=true` → "Drop" button text present. `enrolled=false` → "Enroll" button text present.
- **Depends on**: T7.3 [frontend]

##### T7.5 [frontend] — BrowseCoursesPage

- **Build**: Create `src/app/enroll/page.tsx`. `"use client"`. Uses `useStudentCatalog()`. Renders: loading skeleton, empty state ("No courses available yet."), or grid of `CatalogCard` components. On `enroll`: call `hook.enroll(nodeId)`; show toast "Enrolled!" via local `useState` banner. On `drop`: call `hook.drop(enrollmentId)`. Export `dynamic = "force-dynamic"`.
- **Done when**: Page renders; navigating to `/enroll` in the running app shows the grid.
- **Test**: Integration render test: mount `BrowseCoursesPage` with mocked hook returning 2 nodes → assert 2 cards rendered.
- **Depends on**: T7.4 [frontend]

##### T7.6 [frontend] — Browse Courses Nav Link in Student Header

- **Build**: In `src/components/layout/header/header.tsx` (or the student-specific nav component), add a "Browse Courses" link pointing to `/enroll` visible when `currentRole === "student"`. Must be persistent — visible whether enrolled or not — so students can add/remove enrollments without relying on empty-state CTAs.
- **Done when**: Unit test: render header with `currentRole="student"` → anchor with `href="/enroll"` and text "Browse Courses" found in DOM.
- **Test**: Unit test as described.
- **Depends on**: T7.5 [frontend]

---

## G8 — Enrolled-Only Dashboard + Empty State (Frontend)

**Goal**: `StudentHomePage` and `StudentCoursesPage` show an empty state with a "Browse Courses" CTA when the backend returns no enrolled content; show enrolled content otherwise.
**Goal test**: E2E — unenrolled student loads `/home` → "You haven't enrolled in any courses yet." with "Browse Courses" link. After enrolling and returning → enrolled node appears in Platform Board.
**Repos**: [frontend]

---

### G8.1 — Dashboard Empty State

**Goal**: When `platform_nodes` is empty, `PlatformBoardSection` shows the enrollment CTA.

**Integration test**: Render `PlatformBoardSection` with `nodes=[]` → "You haven't enrolled in any courses yet." text + `<a href="/enroll">Browse Courses</a>` in DOM.

##### T8.1 [frontend] — PlatformBoardSection Empty State

- **Build**: In `src/features/student/components/platform-board-section.tsx`, add: if `nodes.length === 0`, render "You haven't enrolled in any courses yet." and `<a href="/enroll">Browse Courses</a>`. Else render existing grid.
- **Done when**: Unit test with `nodes=[]` finds the CTA link; unit test with `nodes=[n1]` finds the card grid.
- **Test**: Unit test: render `PlatformBoardSection` with `nodes=[]` → `document.querySelector('a[href="/enroll"]')` not null.
- **Depends on**: T7.5 [frontend], T3.4 [backend]

---

### G8.2 — S-nav Empty Node Tree

**Goal**: When the enrolled node tree is empty in `StudentCoursesPage`, the sidebar shows a "Browse Courses" CTA.

**Integration test**: Render `NodeTreeSidebar` with `nodes=[]` → "Browse Courses" anchor with `href="/enroll"` in DOM.

##### T8.2 [frontend] — NodeTreeSidebar Empty State

- **Build**: In `src/features/student/components/node-tree-sidebar.tsx`, add: if `nodes.length === 0`, render "No courses enrolled." + `<a href="/enroll">Browse Courses</a>`. Else render existing tree.
- **Done when**: Unit test with `nodes=[]` finds the "Browse Courses" link.
- **Test**: Unit test: render `NodeTreeSidebar` with `nodes=[]` → link element with text "Browse Courses" found in DOM.
- **Depends on**: T7.5 [frontend]

---

## G9 — hAITU Doubt Panel (Frontend)

**Goal**: Students see a chat interface below topic content where they can ask hAITU questions; message history is held in client-side state and sent as history on each request; nothing is persisted.
**Goal test**: E2E — student selects a topic; doubt panel appears below content; types "What is osmosis?" and presses Send; loading spinner appears then AI response is shown. `escalation_ready=true` → disabled "Ask your teacher" button appears. 21st call → "reached AI limit" error.
**Repos**: [frontend]

---

### G9.1 — hAITU API + Hook

**Goal**: `useHaituDoubt` hook encapsulates client-side message history, loading state, and the API call.

**Integration test**: Render `useHaituDoubt` in a test harness with mocked fetch returning `{response: "Answer", escalation_ready: false}`; call `send("What is osmosis?")` → assert `messages` has 2 entries (user + AI) and `isLoading === false` after resolution.

##### T9.1 [frontend] — askHaitu API Function + Types

- **Build**: In `src/features/student/types/student.types.ts`, add `export interface HaituMessage { role: "student" | "ai"; content: string; }` and `export interface HaituDoubtResponse { response: string; escalation_ready: boolean; }`. In `src/features/student/api/student-api.ts`, add `askHaitu(csrfToken, topicId, enrollmentId, message, history: HaituMessage[]): Promise<HaituDoubtResponse>` — `POST /api/haitu/topic-doubt` with body `{topic_id, enrollment_id, message, history}` via `fetchWithCSRFRetry`. Throws `ApiError` with status on non-200.
- **Done when**: Function compiles; unit test with mocked fetch asserts returned object has `response` and `escalation_ready`.
- **Test**: Unit test: mock `fetch` returning `{ok: true, json: () => ({response: "A", escalation_ready: false})}` → `studentApi.askHaitu(...)` resolves to `{response: "A", escalation_ready: false}`.
- **Depends on**: T7.1 [frontend], T5.5 [backend]

##### T9.2 [frontend] — useHaituDoubt Hook

- **Build**: Create `src/features/student/hooks/use-haitu-doubt.ts`. Export `function useHaituDoubt(topicId: string, enrollmentId: string | null)`. State: `messages: HaituMessage[]`, `isLoading: boolean`, `error: string | null`, `escalationReady: boolean`. Method `send(userMessage: string)`: appends user message to history, sets `isLoading=true`, calls `studentApi.askHaitu(...)` with last 5 messages as `history`. On success: appends AI message, sets `escalationReady`. On 429: `error = "You've reached the AI limit for this hour. Try again later."` On other error: generic fallback message. `finally`: `isLoading=false`. `useEffect` resets all state when `topicId` changes.
- **Done when**: Unit test with mocked `askHaitu` → `messages.length === 2` and `isLoading === false` after send resolves.
- **Test**: Unit test: call `send("Test")` with mocked `askHaitu` returning `{response: "R", escalation_ready: false}` → assert `messages.length === 2`, `isLoading === false`.
- **Depends on**: T9.1 [frontend]

---

### G9.2 — Doubt Panel Component

**Goal**: `HaituDoubtPanel` renders a scrollable chat UI with input, send button, loading state, escalation flag, and error messages.

**Integration test**: Render `HaituDoubtPanel` with `topicId="t1" enrollmentId="e1"` using mocked hook; simulate typing "What is X?" and clicking Send → loading indicator appears then mock AI message is displayed.

##### T9.3 [frontend] — HaituDoubtPanel Component

- **Build**: Create `src/features/student/components/haitu-doubt-panel.tsx`. `"use client"`. Props: `topicId: string`, `enrollmentId: string | null`. Uses `useHaituDoubt(topicId, enrollmentId)`. Renders: "Ask hAITU" heading. Scrollable message history (chat bubbles by role). Error banner if `error` set. Loading spinner if `isLoading`. If `escalationReady`: disabled button "Ask your teacher" with tooltip "Coming soon". Textarea + Send button (disabled while `isLoading` or `enrollmentId === null`). If `enrollmentId === null`: show "Enroll in this course to ask hAITU questions." placeholder.
- **Done when**: Unit test: `enrollmentId=null` → "Enroll in this course" text visible and input disabled.
- **Test**: Unit test: render `HaituDoubtPanel` with `enrollmentId=null` → "Enroll in this course" text visible, input disabled.
- **Depends on**: T9.2 [frontend]

##### T9.4a [frontend] — ContentViewer Doubt Panel Integration

- **Build**: In `src/features/student/components/content-viewer.tsx`, update `ContentViewerProps` to include `topicId: string | null` and `enrollmentId: string | null`. After the existing content items list, conditionally render `<HaituDoubtPanel topicId={topicId} enrollmentId={enrollmentId} />` when `topicId !== null`.
- **Done when**: Unit test: render `ContentViewer` with `topicId="t1" enrollmentId="e1"` → element with "Ask hAITU" text present.
- **Test**: Unit test as described.
- **Depends on**: T9.3 [frontend]

##### T9.4b [frontend] — StudentCoursesPage Doubt State Wiring

- **Build**: In `src/features/student/components/student-courses-page.tsx` (or the equivalent page component), add `selectedTopicId: string | null` and the id of the enrolled **root** node the selection sits under (`selectedRootNodeId: string | null`) to local state. The node tree from `GET /api/student/nodes` is already the enrolled subtree, so each top-level node in that tree is an enrolled grade whose `id` matches a `CatalogNode.id`. When a topic is selected, set `selectedTopicId` and `selectedRootNodeId` (the top-level ancestor in the sidebar tree). Derive `selectedEnrollmentId = catalogNodes.find(n => n.id === selectedRootNodeId)?.enrollment_id ?? null` from `useStudentCatalog`. Pass `topicId={selectedTopicId}` and `enrollmentId={selectedEnrollmentId}` down to `<ContentViewer>`.
- **Done when**: Integration render test — selecting a topic sets `selectedTopicId` and `ContentViewer` receives a non-null `topicId` prop.
- **Test**: Render test: simulate topic selection → assert `ContentViewer` prop `topicId` is non-null.
- **Depends on**: T9.4a [frontend], T7.3 [frontend]

##### T9.5 [frontend] — Export from Feature Index

- **Build**: In `src/features/student/index.ts`, add exports for `HaituDoubtPanel`, `useHaituDoubt`, `useStudentCatalog`, `HaituMessage`, `HaituDoubtResponse`, `CatalogNode`, `StudentEnrollment`.
- **Done when**: `tsc --noEmit` on a file importing `HaituDoubtPanel` from `@/features/student` exits 0.
- **Test**: TypeScript compiler exits 0.
- **Depends on**: T9.4b [frontend], T7.6 [frontend]

---

## ROOT Acceptance Test

1. Student with grade "Grade 8" in profile calls `GET /api/student/catalog` (via APISIX) → Grade 8 node has `recommended: true`.
2. Student POSTs `{course_path_node_id: <grade-8-id>}` to `POST /api/student/enrollments` → 201 with `enrollment_id`.
3. `GET /api/student/dashboard` → `platform_nodes` contains Grade 8 node (was empty before enrollment).
4. `GET /api/student/nodes?owner_type=platform` → only Grade 8 subtree. `GET /api/student/nodes/{grade-9-node}/topics` → 403.
5. Student selects a live topic under Grade 8 in the frontend → `HaituDoubtPanel` appears with input enabled. Types "What is osmosis?" → AI response shown in chat. No database writes occur.
6. 21 calls within the same hour → 21st returns 429; UI shows "You've reached the AI limit for this hour."
7. Student navigates to `/enroll`, clicks "Drop" → 204. Dashboard → `platform_nodes=[]`; empty state with "Browse Courses" CTA shown.

**Pass criteria**: All 7 steps complete with specified status codes and UI states. No Redux, Axios, or React Query in any frontend call. No business logic in route handlers. All mutations carry a valid `X-CSRF-Token` header.

---

<!-- plan-baseline: backend:0dbec5694697941ee0ede822e3b37b2790d0769e frontend:31062ab9ed6026d682046c177f7ee219327af477 deploy:e57c56bdc5dc04a5eb3d37ac63fedf5c5007eb40 -->
