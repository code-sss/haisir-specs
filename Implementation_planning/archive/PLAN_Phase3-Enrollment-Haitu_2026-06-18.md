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

## G10 — Phase 3 Verification, Manual Walkthrough & Sign-off

> **Scope note (2026-06-18):** Implementation across backend/frontend/deploy (G1–G9) is DONE and the frontend Playwright E2E suite (G3/G7/G8/G9) is shipped. The backend has extensive UNIT tests, but the goal-level backend INTEGRATION and E2E entries under G1–G9 are NOT yet written. G10 closes Phase 3: it writes and runs all 12 remaining backend verification items (8 DB-only + 4 Ollama-gated), performs a full MANUAL end-to-end walkthrough of the ROOT Acceptance Test above against the running stack, fixes any defects found, then signs off and archives Phase 3. **Nothing is deferred or dropped.**

**Goal**: Finish Phase 3 completely — all 12 backend verification items green (Ollama-gated items green-or-skip-with-reported-count), the 7-step ROOT Acceptance Test executed manually and recorded as passing, defects fixed, Phase 3 archived.
**Goal test (ROOT acceptance for G10)**: (1) the 12 verification items (G1.1, G2.1, G2.2, G2.3, G2 E2E, G3.1, G3.2, G5.2, G4.1, G4.2, G4 E2E, G5 E2E) all report green; Ollama-gated items report a skip count when Ollama is absent and a green run is distinguishable from an all-skipped run; (2) the 7-step ROOT Acceptance Test is executed manually and recorded as passing (with defects fixed); (3) `PLAN.md` and `TASKS.md` are archived to `Implementation_planning/archive/` and `progress.md` "Completed Phases" gains a Phase 3 entry.
**Repos**: [backend] [frontend] [deploy] [specs]

---

### G10.1 — Shared Integration Fixtures & Scaffolding

**Goal**: A reusable fixtures layer ensures the integration DB is at `alembic head` (V34), every new integration test file gets the dependency-override wiring without copy-paste, the process-global `haitu_rate_limiter` is resettable per test, enrollment rows cannot leak across tests, and the Ollama skip guard probes the actual model endpoint and reports its skip count.
**Subgoal test**: `tests/integration/shared_fixtures.py` imports clean (no ImportError); `reset_haitu_rate_limiter`, `rolled_back_session`, and `seed_3level_tree` are usable; a canary asserts the integration DB revision is `V34`; the refactored dashboard integration test still passes.
**Repos**: [backend]

##### T10.1.1 [backend] — Integration conftest: assert/ensure migration head is V34

- **Build**: Extend `tests/integration/conftest.py`. Add a session-scoped autouse fixture `integration_db_head` that, after the integration engine is created, runs `SELECT version_num FROM alembic_version` via `text()` and asserts the result equals `"V34"` (the head creating `student_enrollments`). On mismatch, `pytest.fail("integration DB head is <found>, expected V34 — run alembic upgrade head against INTEGRATION_DB_URL")`. Document the prerequisite (V31/V32/V33/V34 all present) in the module docstring.
- **Done when**: `uv run pytest tests/integration -q` against a DB migrated only to V33 fails with the clear V34 message; against a V34 DB the suite proceeds.
- **Test**: Canary `test_integration_db_at_v34` asserts `version_num == "V34"`.
- **Depends on**: None (verifies existing V34 migration from T1.1 [backend]).

##### T10.1.2 [backend] — Shared integration fixtures module

- **Build**: Create `tests/integration/shared_fixtures.py` centralising the wiring currently duplicated in `tests/integration/routes/test_student_dashboard_integration.py`. Provide:
  - `make_student_client(app, session_maker, student_sub, roles=("student",))` — contextmanager building an `httpx.AsyncClient` via `ASGITransport(app=app)` with `app.dependency_overrides` set for `get_async_session`, `current_active_user` (returns `CurrentUser(sub=student_sub, roles=list(roles), current_role=UserRole.student)`), and `validate_csrf` (returns `None`); client sends `X-Current-Role: student`; tears down overrides on exit.
  - `reset_haitu_rate_limiter` — **autouse, function-scope** for any test module under `tests/integration/` that imports `shared_fixtures`: before each test, swap `src.domain.services.haitu_rate_limiter.haitu_rate_limiter` with a fresh `HaituRateLimiter()` and restore afterward. Include `hour_bucket_override(bucket_str)` to pin `_current_bucket()` to a fixed string so the 21st-call test is hour-bucket- and order-independent.
  - `unique_student_sub()` — returns a fresh `str(uuid.uuid4())` per call.
  - `rolled_back_session(session_maker)` — fixture yielding a session inside a transaction that rolls back at teardown, for repository-level integration tests.
  - `seed_3level_tree(session)` — seeds grade→subject→course platform nodes; returns `(grade_id, subject_id, course_id)`.
- **Done when**: `grep -r "dependency_overrides\[get_async_session\]" tests/integration` hits only `shared_fixtures.py`; canary using `make_student_client` twice with `reset_haitu_rate_limiter` between shows an empty rate-limiter dict at the start of the second call.
- **Test**: Canary `test_shared_fixtures_rate_limiter_reset` asserts the limiter dict is empty at the start of the second client's first call.
- **Depends on**: T10.1.1 [backend].

##### T10.1.2b [backend] — Refactor existing dashboard integration test to import shared_fixtures

- **Build**: Refactor `tests/integration/routes/test_student_dashboard_integration.py` to import `make_student_client`/fixtures from `shared_fixtures.py` instead of inlining the override wiring. No behaviour change — the existing parent-403 assertion must still hold.
- **Done when**: `grep -r "dependency_overrides\[get_async_session\]" tests/integration` returns only `shared_fixtures.py`; the refactored dashboard integration test still passes.
- **Test**: `uv run pytest tests/integration/routes/test_student_dashboard_integration.py -q` exits 0.
- **Depends on**: T10.1.2 [backend].

##### T10.1.3 [backend] — Ollama probe-based skip guard + skip-count reporter

- **Build**: Create `tests/integration/ollama_probe.py`:
  - `ollama_model_available(model_spec: str, base_url: str | None) -> bool` — GETs `{base_url}/api/tags` (Ollama) or `/v1/models` (LM Studio, dispatched by the same `lmstudio://` vs `ollama://` prefix the embedding module uses); returns True only if BOTH the configured chat model AND the bge-m3 embed model are present and loaded. Update `tests/integration/worker/test_rag_loop_integration.py` to use this probe instead of the `OLLAMA_AVAILABLE` env-only check.
  - A session-scoped `report_ollama_skip_count` fixture wired via a `pytest_terminal_summary` hook in `tests/integration/conftest.py`, printing a single line `Ollama-gated: N skipped, M passed` so a green all-skipped run is visibly distinct from a green all-run run.
  - Expose a `pytestmark = pytest.mark.skipif(not ollama_model_available(...), reason="...")` import for the four Ollama-gated test files (G10.3) to apply.
- **Done when**: With Ollama down, `uv run pytest tests/integration -q` prints `Ollama-gated: 4 skipped, 0 passed`; with Ollama up and models loaded, it prints `Ollama-gated: 0 skipped, 4 passed`.
- **Test**: Unit-scale `test_ollama_probe_closed_port` asserts `ollama_model_available(...)` returns False against a closed port.
- **Depends on**: None.

---

### G10.2 — DB-Only Verification Tests

**Goal**: The 8 DB-only goal-level integration/E2E entries (G1.1, G2.1, G2.2, G2.3, G2 E2E, G3.1, G3.2, G5.2) are written and green against a Postgres DB at V34. No Ollama required.
**Subgoal test**: `uv run pytest tests/integration/phase3_db_only -q` exits 0 with 8 collected items passing and 0 skipped.
**Repos**: [backend]

##### T10.2.1 [backend] — G1.1: V34 UNIQUE violation + index exists

- **Build**: Create `tests/integration/phase3_db_only/test_g1_1_enrollment_schema.py`. INSERT one `student_enrollments` row with `(student_sub=S, course_path_node_id=N)`; INSERT a second row with the same pair and assert `IntegrityError` (UNIQUE). Query `pg_indexes` and assert `idx_student_enrollments_student_sub` present. Use `unique_student_sub()` and a freshly seeded platform node from `seed_3level_tree`; wrap writes in a rolled-back transaction.
- **Done when**: Test passes against a V34 DB; it fails (no IntegrityError) against a DB missing the UNIQUE constraint.
- **Test**: `assert pytest.raises(IntegrityError)` on duplicate INSERT; `assert "idx_student_enrollments_student_sub" in indexnames`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G1.1)

##### T10.2.2 [backend] — G2.1: EnrollmentRepository CRUD via real DB

- **Build**: Create `tests/integration/phase3_db_only/test_g2_1_enrollment_repository.py`. With `EnrollmentRepository(session)` from `rolled_back_session` and a seeded platform node: `create()` → `get_by_student(sub)` returns 1; `get_by_id(id)` returns same; `get_enrolled_node_ids(sub)` returns `{node_id}`; `delete_by_id_and_student(id, sub)` returns True; re-`get_by_id` returns None; `delete_by_id_and_student` again returns False. Use `unique_student_sub()`.
- **Done when**: All five repository methods execute SQL without error and return the asserted values.
- **Test**: `assert enrolled_node_ids == {grade_id}` after create; `assert result is None` after delete.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G2.1)

##### T10.2.3 [backend] — G2.2: EnrollmentService enroll/drop/catalog

- **Build**: Create `tests/integration/phase3_db_only/test_g2_2_enrollment_service.py`. With `EnrollmentService(EnrollmentRepository(session), CoursePathNodeRepository(session))` against a real session and a seeded grade node: `enroll(sub, grade_id)` → `StudentEnrollment`; `get_catalog(sub, "Grade 8")` → card `enrolled=True`, `enrollment_id` set, `recommended=False`; `enroll` again → `AlreadyEnrolledError`; `drop(id, sub)` → passes; `get_catalog` again → `enrolled=False`, `enrollment_id=None`. Use `unique_student_sub()`.
- **Done when**: The four-step sequence completes with the asserted states and the second `enroll` raises `AlreadyEnrolledError`.
- **Test**: `assert pytest.raises(AlreadyEnrolledError)` on second enroll; `assert card.enrolled is False` after drop.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G2.2)

##### T10.2.4 [backend] — G2.3: route CRUD cycle 200/201/409/204/404

- **Build**: Create `tests/integration/phase3_db_only/test_g2_3_enrollment_routes.py`. With `make_student_client` and a seeded platform grade node: `GET /api/student/catalog` → 200; `POST /api/student/enrollments` `{course_path_node_id}` → 201 with `id`; `POST` again → 409; `DELETE /api/student/enrollments/{id}` → 204; `DELETE` again → 404. Use a fresh `unique_student_sub()` per test.
- **Done when**: The five-request sequence yields 200, 201, 409, 204, 404 in order.
- **Test**: `assert [r.status_code for r in responses] == [200, 201, 409, 204, 404]`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G2.3)

##### T10.2.5 [backend] — G2 E2E: enroll → catalog enrolled=true → drop → enrolled=false

- **Build**: Create `tests/integration/phase3_db_only/test_g2_e2e_enrollment_lifecycle.py`. With `make_student_client`: `POST /api/student/enrollments` → 201; `GET /api/student/catalog` → enrolled node card `enrolled=True`; `DELETE /api/student/enrollments/{id}` → 204; `GET /api/student/catalog` → same card `enrolled=False`. No service mocking — exercises the route layer end-to-end.
- **Done when**: Both catalog fetches reflect the post-mutation enrolled state.
- **Test**: `assert first_catalog_card.enrolled is True` and `assert second_catalog_card.enrolled is False`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G2 E2E)

##### T10.2.6 [backend] — G3.1: seeded 3-level tree; subtree + enrolled-root queries

- **Build**: Create `tests/integration/phase3_db_only/test_g3_1_subtree_queries.py`. With `seed_3level_tree(session)`: `CoursePathNodeRepository(session).get_subtree_node_ids([grade_id])` → `{grade_id, subject_id, course_id} ⊆ result`; `get_enrolled_root_nodes({grade_id})` → list containing the grade `CoursePathNode`; `get_enrolled_root_nodes(set())` → `[]`.
- **Done when**: Both queries return the asserted sets/lists against the seeded tree.
- **Test**: `assert {grade_id, subject_id, course_id}.issubset(subtree_ids)`; `assert len(enrolled_roots) == 1 and enrolled_roots[0].id == grade_id`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G3.1)

##### T10.2.7 [backend] — G3.2: unenrolled → platform_nodes=[]; wrong node → 403

- **Build**: Create `tests/integration/phase3_db_only/test_g3_2_enrollment_filter.py`. With `make_student_client` and a `unique_student_sub()` (no enrollments seeded): `GET /api/student/dashboard` → 200, `platform_nodes == []`. Seed a platform grade node the student is NOT enrolled in; `GET /api/student/nodes/{unenrolled_node_id}/topics` → 403.
- **Done when**: Both assertions hold against the real DB + route layer.
- **Test**: `assert response.json()["platform_nodes"] == []`; `assert topics_response.status_code == 403`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G3.2)

##### T10.2.8 [backend] — G5.2: valid → 200; wrong enrollment → 403; rate exceeded → 429

- **Build**: Create `tests/integration/phase3_db_only/test_g5_2_haitu_endpoint_paths.py`. With `make_student_client` and `reset_haitu_rate_limiter` (autouse) + `hour_bucket_override` pinned: seed an enrollment + live topic for the student; mock `HaituService.answer` at the integration layer (override the `HaituDoubtService` factory dependency, or monkeypatch `HaituService.answer` to return `HaituResponse(response="ok", escalation_ready=False)`). Valid `{topic_id, enrollment_id, message:"x", history:[]}` → 200. Wrong `enrollment_id` (seed a second enrollment for `other_student_sub`, POST that id) → 403. Rate exceeded: pre-fill the pinned bucket with 20 calls for this `student_sub`, then POST → 429. No Ollama required.
- **Done when**: All three paths return the asserted status codes with `HaituService.answer` mocked.
- **Test**: `assert [r.status_code for r in [valid, wrong, exceeded]] == [200, 403, 429]`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G5.2)

---

### G10.3 — Ollama-Gated Verification Tests

**Goal**: The 4 Ollama-gated goal-level integration/E2E entries (G4.1, G4.2, G4 E2E, G5 E2E) are written and green when Ollama + the configured chat model and bge-m3 embed model are available; they skip with a reported count otherwise. The two DB-only sub-cases (G4 E2E short-circuit, G5 E2E 429) run even when Ollama is absent.
**Subgoal test**: With Ollama up — `uv run pytest tests/integration/phase3_ollama_gated -q` exits 0, terminal summary `Ollama-gated: 0 skipped, 6 passed` (4 Ollama-gated + 2 DB-only sub-cases). With Ollama down — exits 0, summary `Ollama-gated: 4 skipped, 2 passed`, and T10.3.5 asserts the skip-count line is present.
**Repos**: [backend]

##### T10.3.1 [backend] — G4.1: _stage1_rewrite with live Ollama  [Ollama-gated]

- **Build**: Create `tests/integration/phase3_ollama_gated/test_g4_1_stage1_rewrite.py`. Apply the `ollama_model_available` skip mark from T10.1.3. Instantiate `HaituService(settings.haitu, settings.embedding, settings.database_url)`; `await service._stage1_rewrite("What is photosynthesis?")` → assert returned `HaituRewriteResult` has non-empty `rewritten_query`, `intent in {"definition","computation","explanation"}`, and `safe` is a bool.
- **Done when**: With Ollama up + chat model loaded, the test passes; with Ollama down, it skips and is counted in the summary line.
- **Test**: `assert result.rewritten_query and result.intent in {...} and isinstance(result.safe, bool)`.
- **Depends on**: T10.1.3 [backend]. (covers G4.1)

##### T10.3.2 [backend] — G4.2: seeded chunks; _stage2_retrieve ≥1 NodeWithScore  [Ollama-gated]

- **Build**: Create `tests/integration/phase3_ollama_gated/test_g4_2_stage2_retrieve.py`. Apply the skip mark. Seed the full hierarchy (category→grade→subject→course→topic→topic_content) and insert a `data_topic_content_chunks` row with a bge-m3 embedding produced via `build_embed_model(settings.embedding)` (or run `_process_row` once via a `rag_indexing_outbox` row). Call `await service._stage2_retrieve("photosynthesis", topic_id, with_rerank=False)` → assert `len(result) >= 1` and each item is a `NodeWithScore`.
- **Done when**: With Ollama up, ≥1 `NodeWithScore` returned; with Ollama down, skips and is counted.
- **Test**: `assert len(nodes) >= 1`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend], T10.1.3 [backend]. (covers G4.2)

##### T10.3.3a [backend] — G4 E2E: safe=False short-circuit (no _stage2 call)  [DB-only]

- **Build**: Create `tests/integration/phase3_ollama_gated/test_g4_e2e_answer_pipeline.py::test_answer_short_circuits_on_safe_false`. No skip mark. Monkeypatch `HaituService._stage1_rewrite` to return `HaituRewriteResult(rewritten_query="x", intent="explanation", safe=False, reject_reason="Off topic")`; spy on `_stage2_retrieve`; call `await service.answer(topic_id, "x", [], {})`; assert `result.response == "Off topic"`, `result.escalation_ready is False`, and `_stage2_retrieve` was not called.
- **Done when**: The short-circuit test passes always (no Ollama).
- **Test**: `assert result.response == "Off topic" and not stage2_called`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G4 E2E — short-circuit half)

##### T10.3.3b [backend] — G4 E2E: safe=True full pipeline  [Ollama-gated]

- **Build**: `test_g4_e2e_answer_pipeline.py::test_answer_full_pipeline_safe_true`. Apply the skip mark. Seed chunks as in T10.3.2; call `await service.answer(topic_id, "What is photosynthesis?", [], topic_context)` with a real `topic_context`; assert `result.response` is a non-empty string and `result.escalation_ready` is a bool.
- **Done when**: Passes with Ollama up; skips (counted) with Ollama down.
- **Test**: `assert isinstance(result.response, str) and result.response`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend], T10.1.3 [backend]. (covers G4 E2E — full-pipeline half)

##### T10.3.4a [backend] — G5 E2E: AI response + no DB writes  [Ollama-gated]

- **Build**: Create `tests/integration/phase3_ollama_gated/test_g5_e2e_haitu_topic_doubt.py::test_haitu_topic_doubt_ai_response_no_db_writes`. Apply the skip mark. With `make_student_client`, seed an enrollment + live topic; `POST /api/haitu/topic-doubt` valid body → 200, `response` non-empty, `escalation_ready` bool. Before/after, `SELECT count(*) FROM student_enrollments WHERE student_sub=?` → unchanged (hAITU path is stateless). Assert no `doubt_messages`-style rows were created (table deferred to Phase 4 — the hAITU path must touch no such table).
- **Done when**: Passes with Ollama up; skips (counted) with Ollama down.
- **Test**: `assert response.status_code == 200 and response.json()["response"]` and `count_before == count_after`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend], T10.1.3 [backend]. (covers G5 E2E — AI-response half)

##### T10.3.4b [backend] — G5 E2E: 21st call → 429  [DB-only]

- **Build**: `test_g5_e2e_haitu_topic_doubt.py::test_haitu_topic_doubt_21st_call_429`. No skip mark. With `reset_haitu_rate_limiter` (autouse) + `hour_bucket_override` pinned, seed enrollment + topic; mock `HaituService.answer` at the integration layer to return canned responses fast. Loop 20 POSTs → all 200; 21st POST → 429 with rate-limit body.
- **Done when**: The 429 test passes always (no Ollama).
- **Test**: `assert [r.status_code for r in first_20] == [200]*20 and twenty_first.status_code == 429`.
- **Depends on**: T10.1.1 [backend], T10.1.2 [backend]. (covers G5 E2E — 429 half)

##### T10.3.5 [backend] — Aggregate-gate: ollama-gated suite exits 0 with skip-count line

- **Build**: Add a guard (a small test or a CI step recorded in TASKS.md) that runs `uv run pytest tests/integration/phase3_ollama_gated -q` and asserts (a) exit code 0, and (b) the `Ollama-gated: N skipped, M passed` terminal-summary line is present in output. This is the gate that distinguishes a genuinely-green Ollama run from a silently-all-skipped run, and is the entry condition the manual walkthrough (T10.4.1) depends on.
- **Done when**: With Ollama up: exit 0, line `Ollama-gated: 0 skipped, 6 passed`. With Ollama down: exit 0, line `Ollama-gated: 4 skipped, 2 passed`. Either way the skip-count line is present and parseable.
- **Test**: `assert exit_code == 0 and "Ollama-gated:" in output`.
- **Depends on**: T10.3.1 [backend], T10.3.2 [backend], T10.3.3a [backend], T10.3.3b [backend], T10.3.4a [backend], T10.3.4b [backend].

---

### G10.4 — Manual End-to-End Walkthrough

**Goal**: The 7-step ROOT Acceptance Test is executed manually against the running stack (backend + frontend + APISIX + Postgres + Ollama), each step's result is recorded, and any defects found are fixed before sign-off.
**Subgoal test**: A walkthrough record exists showing all 7 steps passing (with specified status codes and UI states); any defects found were fixed and the affected step re-run green.
**Repos**: [specs] [backend] [frontend] [deploy]

##### T10.4.1 [specs] — Run ROOT Acceptance Test manually, record results

- **Build**: Bring up the full stack via `haisir-deploy` docker compose (backend, frontend, APISIX, Postgres, Ollama with chat + bge-m3 models loaded). With a real student whose profile grade is "Grade 8", execute the 7 steps from the "## ROOT Acceptance Test" section verbatim. Record the observed status code / UI state for each step. **No code changes in this task** — execution + recording only. If a step fails, log it as a defect for T10.4.2/T10.4.3/T10.4.4. If stack-up itself fails, log as a deploy defect → T10.4.4.
- **Done when**: A 7-row record exists, each row pass/fail with (if fail) a defect reference.
- **Test**: The recorded table has 7 rows; each row has a pass/fail and (if fail) a defect reference.
- **Depends on**: G10.2 subgoal test green (8 passed, 0 skipped) AND G10.3 subgoal test green via T10.3.5 (Ollama up: 4 Ollama-gated + 2 DB-only passed; Ollama down: 4 skipped + 2 passed, skip-count line present). Also requires G1–G9 complete (per `progress.md`) and stack brought up via `haisir-deploy` docker compose.

##### T10.4.2 [backend] — Fix backend defects surfaced by the manual walkthrough

- **Build**: For each defect logged in T10.4.1 whose root cause is in the backend (route handler, service, repository, schema, migration), implement the minimal fix. Re-run the affected integration test(s) and the failing manual step. Environmental defects (Ollama model not loaded, APISIX misconfig) are NOT backend — route to T10.4.3 or T10.4.4. If none found, record "no backend defects."
- **Done when**: All backend-rooted defects fixed and the affected manual step re-runs green.
- **Test**: The affected step from T10.4.1 flips fail→pass; the relevant G10.2/G10.3 test still passes.
- **Depends on**: T10.4.1 [specs].

##### T10.4.3 [frontend] — Fix frontend defects surfaced by the manual walkthrough

- **Build**: For each defect logged in T10.4.1 whose root cause is in the frontend (component, hook, API call, header wiring), implement the minimal fix. Re-run the affected Playwright E2E spec and the failing manual step. If none found, record "no frontend defects."
- **Done when**: All frontend-rooted defects fixed and the affected manual step re-runs green.
- **Test**: The affected Playwright spec in the existing G3/G7/G8/G9 suite passes; the affected manual step flips to pass.
- **Depends on**: T10.4.1 [specs].

##### T10.4.4 [deploy] — Fix deploy defects surfaced by the manual walkthrough

- **Build**: For each defect logged in T10.4.1 whose root cause is in the deploy repo (APISIX route config, WAF rule, env var, docker-compose service, Ollama model availability), implement the minimal fix (e.g., adjust `19-api-haitu.json`, add a WAF exclusion, fix an env var). Re-apply config and re-run the failing manual step. If none found, record "no deploy defects."
- **Done when**: All deploy-rooted defects fixed and the affected manual step re-runs green.
- **Test**: `GET /api/health` via APISIX → healthy; the affected manual step flips to pass.
- **Depends on**: T10.4.1 [specs].

---

### G10.5 — Phase 3 Sign-off & Archive

**Goal**: After all 12 verification items are green-or-skip-with-count and the manual walkthrough is recorded as fully passing, archive `PLAN.md` and `TASKS.md` and record Phase 3 as completed in `progress.md`.
**Subgoal test**: `Implementation_planning/archive/` contains the Phase 3 PLAN.md and TASKS.md snapshots; `progress.md` "Completed Phases" section contains a Phase 3 entry.
**Repos**: [specs]

##### T10.5.1 [specs] — Verify full closure: 12 items + manual walkthrough + Playwright

- **Build**: Compile a closure checklist: (a) the 12 verification items are each green or, for Ollama-gated items, green-or-skip-with-reported-count (and the reported count distinguishes green from all-skipped); (b) the 7-step manual walkthrough record shows all steps passing (defects from T10.4.2/T10.4.3/T10.4.4 resolved); (c) the existing frontend Playwright suite (G3/G7/G8/G9) is still green. If any item is not green, do NOT proceed — surface the gap.
- **Done when**: The checklist has 12 + 7 + 1 rows, every row green (or skip-with-count for Ollama items when Ollama is absent).
- **Test**: `assert all(row.green for row in checklist)`.
- **Depends on**: T10.4.2 [backend], T10.4.3 [frontend], T10.4.4 [deploy].

##### T10.5.2 [specs] — Archive PLAN.md + TASKS.md; update progress.md Completed Phases

- **Build**: `git mv` `Implementation_planning/PLAN.md` and `Implementation_planning/TASKS.md` to `Implementation_planning/archive/` with Phase-3-suffixed filenames (`PLAN_Phase3-Enrollment-Haitu_2026-06-18.md`, `TASKS_Phase3-Enrollment-Haitu_2026-06-18.md`), preserving history. Append a "Phase 3 — Student Enrollment + hAITU Topic-Doubt ✓" entry to `progress.md` "Completed Phases" with: completion date, backend/frontend/deploy commit SHAs, archived-plan path, what-was-done summary (schema V34; enrollment domain/repo/service/routes; enrolled-only content filter; hAITU 4-stage pipeline + topic-doubt endpoint + rate limiter; APISIX route + env vars; frontend browse-courses + dashboard empty state + hAITU doubt panel; Playwright E2E suite; the 12 backend verification tests; manual walkthrough), and deviations (Ollama-gated tests skip-with-count when Ollama absent; any walkthrough defects + fixes). Do not delete the working files until archive copies are committed.
- **Done when**: `ls Implementation_planning/archive/PLAN_Phase3*.md` and `ls Implementation_planning/archive/TASKS_Phase3*.md` both succeed; `grep "Phase 3 — Student Enrollment" Implementation_planning/progress.md` returns the new entry.
- **Test**: `test -f Implementation_planning/archive/PLAN_Phase3-Enrollment-Haitu_2026-06-18.md` and `grep -q "Phase 3 — Student Enrollment" progress.md`.
- **Depends on**: T10.5.1 [specs].

---

<!-- plan-baseline: backend:9379bb72c3e2ccb94d7256bf0eb533e37d78a76e frontend:54e198cc88399f1bd57d679bd010d134b5546c86 deploy:e57c56bdc5dc04a5eb3d37ac63fedf5c5007eb40 -->
