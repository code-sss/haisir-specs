# PLAN — RAG Infrastructure + Text Restructuring + Student Dashboard

> Written: 2026-06-12
> Decisions: `Implementation_planning/decisions.md` (2026-06-12 RAG+hAITU entry; 2026-06-12 text restructuring entry)
> Scope note: G4 wires hAITU config only. The `POST /api/haitu/topic-doubt` retrieval endpoint is out-of-scope — it requires vectors to be populated first and will be planned in the next cycle.

---

## Problem Statement

Three independent gaps need closing in parallel:

1. **RAG pipeline dead end** — `rag_indexing_outbox` rows have been accumulating since Phase 1d-real but nothing drains them. No pgvector extension is installed, no drain loop exists, no embeddings have been generated.
2. **Garbled native text** — When pypdfium2 extracts text from educational PDFs, it often produces fragmented output (fractions split across lines, broken words). The extraction worker returns this raw text unchanged, degrading content quality and embedding quality.
3. **Student UI missing** — The student dashboard (S-home) and content navigator (S-nav) are unbuilt. Backend APIs for these screens don't exist yet.

---

## Architecture Decisions

See `Implementation_planning/decisions.md` (2026-06-12 entries) for full rationale. Key:
1. pgvector in the same DB as the backend — hAITU retrieval JOINs vectors with topic_contents; cross-DB JOINs impossible without FDW.
2. Custom Wolfi multi-stage Dockerfile for prod (pgvector not in Wolfi package repo — compile from source); `pgvector/pgvector:pg18` for dev.
3. LlamaIndex `PGVectorStore` manages `data_topic_content_chunks` — V32 migration is an Alembic shim only.
4. BAAI/bge-m3, dimension 1024, SentenceSplitter(512/100) — multilingual, MIT, Ollama-native; dim is fixed at migration time.
5. Text restructuring: optional text-only LLM pass after native extraction, using `EXTRACTION__RESTRUCTURE_MODEL_SPEC` (default: same as vision model). Adapted from `anhad-final-exam` project.
6. Student dashboard: two-section S-home (Platform Board / Home Study), tabbed S-nav. All read-only; no new tables.

---

## Goal Tree

### G1 — pgvector Database Image
**Goal**: The Docker infrastructure provides a PostgreSQL 18.4 + pgvector 0.8.2 image for production (Wolfi/Chainguard multi-stage) and a pgvector-enabled image for dev, so `CREATE EXTENSION vector` succeeds and Alembic V31 can run.
**Goal test**: `docker compose up db` starts successfully; `psql -c "SELECT extversion FROM pg_extension WHERE extname='vector'"` returns `0.8.2`. Dev `docker compose up postgres` similarly starts without error.
**Repos**: [deploy]

---

##### T1.1 [deploy] — Wolfi pgvector Dockerfile
- **Build**: Create `common/images/postgres-pgvector/Dockerfile`. Multi-stage build:
  - Stage 1 (`builder`): `FROM cgr.dev/chainguard/wolfi-base`. Install build deps: `apk add --no-cache postgresql-18-dev git gcc make clang`. Clone pgvector 0.8.2: `git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git /pgvector`. Run `cd /pgvector && make OPTFLAGS="" && make install` (uses `$(pg_config --pkglibdir)` and `$(pg_config --sharedir)/extension`).
  - Stage 2 (`final`): `FROM cgr.dev/chainguard/postgres:latest`. Copy compiled `.so` from `$(pg_config --pkglibdir)/vector.so` and `$(pg_config --sharedir)/extension/vector*.sql` + `vector.control` from builder into the same paths in the final image.
- **Done when**: `docker build -t haisir-postgres-pgvector ./common/images/postgres-pgvector` exits 0; `docker run --rm haisir-postgres-pgvector ls $(pg_config --pkglibdir) | grep vector` exits 0.
- **Test**: Build the image; run `docker run --rm haisir-postgres-pgvector ls $(pg_config --pkglibdir) | grep -c vector` returns 1.
- **Depends on**: None

##### T1.2 [deploy] — Update common/docker-compose.yml db services to custom image
- **Build**: In `common/docker-compose.yml`, for the `db` and `db-init` services: replace `image: cgr.dev/chainguard/postgres:latest` with a `build:` block: `build: { context: ../../, dockerfile: common/images/postgres-pgvector/Dockerfile }`. Remove the bare `image:` line from both services. Keep all other service config (volumes, env, healthchecks) unchanged. Keycloak DB service is NOT modified.
- **Done when**: `docker compose -f common/docker-compose.yml config` exits 0; output shows `build.context` for both `db` and `db-init`; Keycloak DB still shows the original `image:`.
- **Test**: `grep -c "build:" common/docker-compose.yml` returns 2.
- **Depends on**: T1.1

##### T1.3 [deploy] — Update dev/docker-compose.yml postgres to pgvector image
- **Build**: In `dev/docker-compose.yml`, replace `image: postgres:18` with `image: pgvector/pgvector:pg18` for the `postgres` service. No other changes.
- **Done when**: `grep "pgvector/pgvector:pg18" dev/docker-compose.yml` exits 0; `docker compose -f dev/docker-compose.yml config` exits 0.
- **Test**: `grep -c "pgvector/pgvector:pg18" dev/docker-compose.yml` returns 1.
- **Depends on**: T1.2

##### T1.4 [deploy] — pgvector smoke test
- **Build**: After compose is up, verify the extension can be created. Add a note in `common/images/postgres-pgvector/README.md` (or inline in the Dockerfile as a `LABEL test=`) with the verification command: `psql -h localhost -U $POSTGRES_USER -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extversion FROM pg_extension WHERE extname='vector';"`.
- **Done when**: Running the verification command against a started `db` or `postgres` container returns a row with `extversion = '0.8.2'`.
- **Test**: `docker run --rm --entrypoint psql haisir-postgres-pgvector -c "SELECT 1;"` exits 0 (basic connectivity).
- **Depends on**: T1.2, T1.3

**G1 integration test**: Run `docker compose up db -d` using the custom image; connect via `psql`; execute `CREATE EXTENSION IF NOT EXISTS vector;`; assert no error and `pg_extension` row exists.

---

### G2 — Vector Extension + Schema
**Goal**: Alembic migrations V31 and V32 run on the pgvector-enabled DB: the `vector` extension is installed, and LlamaIndex's `data_topic_content_chunks` table is registered in Alembic's migration history so autogenerate never diffs it.
**Goal test**: `alembic upgrade head` completes without error; `SELECT extversion FROM pg_extension WHERE extname='vector'` returns a non-empty row; `\d data_topic_content_chunks` shows `embedding vector(1024)`; `alembic current` shows V32.
**Repos**: [backend]

---

##### T2.1 [backend] — Alembic V31: CREATE EXTENSION vector
- **Build**: Create `alembic/versions/V31_pgvector_extension.py`. Set `revision = "V31"`, `down_revision = "V30"`. In `upgrade()`: `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`. In `downgrade()`: add a comment `# Intentional no-op: dropping vector extension may corrupt data_topic_content_chunks` and no action. Add module-level docstring explaining this migration enables the pgvector extension for embedding storage.
- **Done when**: `alembic upgrade V31` against a pgvector-enabled DB exits 0; `SELECT COUNT(*) FROM pg_extension WHERE extname='vector'` returns 1.
- **Test**: `tests/unit/migrations/test_v31.py` — import V31 module; assert `upgrade.__doc__` or the SQL string contains `CREATE EXTENSION`; assert `down_revision == "V30"`.
- **Depends on**: T1.1 [deploy]

##### T2.2 [backend] — Alembic V32: shim for data_topic_content_chunks
- **Build**: Create `alembic/versions/V32_rag_vector_table_shim.py`. Set `revision = "V32"`, `down_revision = "V31"`. Module-level comment: "LlamaIndex PGVectorStore manages this table. This migration is a registration shim only — do not autogenerate diffs against data_topic_content_chunks." In `upgrade()`: create the table exactly as LlamaIndex `PGVectorStore` creates it, so Alembic records the schema: `op.create_table("data_topic_content_chunks", sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True), sa.Column("text", sa.Text, nullable=True), sa.Column("metadata_", sa.JSON, nullable=True), sa.Column("node_id", sa.VARCHAR, nullable=True), sa.Column("embedding", Vector(1024), nullable=True))`. Import `Vector` from `pgvector.sqlalchemy`. Add table comment via `op.execute("COMMENT ON TABLE data_topic_content_chunks IS 'Managed by LlamaIndex PGVectorStore; this migration is a registration shim only.'")`. In `downgrade()`: `op.drop_table("data_topic_content_chunks")`.
- **Done when**: `alembic upgrade V32` exits 0; `alembic current` shows V32; `\d data_topic_content_chunks` shows `embedding vector(1024)`.
- **Test**: `tests/unit/migrations/test_v32.py` — import V32 module; assert `down_revision == "V31"`; assert upgrade creates `data_topic_content_chunks`; assert downgrade drops it.
- **Depends on**: T2.1

**G2 integration test**: Run `alembic upgrade head` on pgvector-enabled test DB; query `pg_extension` for vector; describe `data_topic_content_chunks`; confirm `alembic current` = V32; run `alembic downgrade V31` then re-upgrade; assert idempotency.

---

### G3 — RAG Drain Loop
**Goal**: The worker drains `rag_indexing_outbox` rows, loads the matching `topic_contents` text, chunks with SentenceSplitter(512/100), embeds with bge-m3 via Ollama, and upserts into `data_topic_content_chunks`. Processed rows are marked `done`; failures are retried up to 3 times then marked `failed`.
**Goal test**: Seed one `rag_indexing_outbox` row + matching `topic_contents` row with text "Hello world". Start worker. After one poll cycle, `rag_indexing_outbox.status = 'done'`; `SELECT COUNT(*) FROM data_topic_content_chunks WHERE metadata_->>'content_id' = '<uuid>'` returns >= 1.
**Repos**: [backend] [deploy]

---

#### G3.1 — Config + Dependencies [backend]

##### T3.1 [backend] — LlamaIndex dependencies in pyproject.toml
- **Build**: In `pyproject.toml` under `[project].dependencies`, add: `"llama-index-core>=0.12.0"`, `"llama-index-vector-stores-postgres>=0.4.0"`, `"llama-index-embeddings-ollama>=0.6.0"`. Run `uv sync` to verify resolution.
- **Done when**: `uv sync` exits 0; `python -c "from llama_index.vector_stores.postgres import PGVectorStore; from llama_index.embeddings.ollama import OllamaEmbedding"` exits 0.
- **Test**: `tests/unit/worker/test_rag_outbox_loop.py` imports `from llama_index.embeddings.ollama import OllamaEmbedding` at module level without raising `ImportError`.
- **Depends on**: None

##### T3.2 [backend] — EmbeddingSettings in shared/config.py
- **Build**: In `src/shared/config.py`, add a new `EmbeddingSettings(BaseModel)` class immediately after `GradingSettings`: fields are `model_spec: str = Field(default="bge-m3")`, `ollama_base_url: str = Field(default="http://localhost:11434")`, `batch_size: int = Field(default=10)`. In `Settings`, add `embedding: EmbeddingSettings = EmbeddingSettings()` after the `grading` field.
- **Done when**: `from shared.config import settings; settings.embedding.model_spec` returns `"bge-m3"`; `settings.embedding.batch_size` returns `10`.
- **Test**: `tests/unit/shared/test_config.py` — assert `Settings().embedding.model_spec == "bge-m3"`, `Settings().embedding.batch_size == 10`; with env `EMBEDDING__BATCH_SIZE=5`, assert `Settings().embedding.batch_size == 5`.
- **Depends on**: None

---

#### G3.2 — Loop Implementation [backend]

##### T3.3 [backend] — Create worker/rag_outbox_loop.py
- **Build**: Create `src/worker/rag_outbox_loop.py`. The async function `async def run_rag_outbox_loop(session_maker, settings: Settings) -> None` loops forever with `await asyncio.sleep(settings.embedding.poll_interval_seconds if hasattr(settings.embedding, 'poll_interval_seconds') else 5)`. Each iteration:
  1. Claims up to `settings.embedding.batch_size` outbox rows: `SELECT ... FROM rag_indexing_outbox WHERE status IN ('pending','retry') AND retry_count < 3 ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT :batch`. Sets `status='processing'`, `locked_at=now()`, `locked_by=socket.gethostname()`.
  2. For each row, loads the `topic_contents` row by `content_id`. If `text` is null or empty: sets `status='failed'`, `last_error='empty text'`. Skips.
  3. Chunks text: `from llama_index.core.node_parser import SentenceSplitter; splitter = SentenceSplitter(chunk_size=512, chunk_overlap=100); nodes = splitter.get_nodes_from_documents(...)`. Each node metadata dict includes `content_id`, `topic_id`, `title`, `content_type`.
  4. Creates `OllamaEmbedding(model_name=settings.embedding.model_spec, base_url=settings.embedding.ollama_base_url)` and `PGVectorStore(table_name="topic_content_chunks", ...)` using the DB connection string.
  5. Calls `await asyncio.to_thread(vector_store.add, nodes)` (LlamaIndex sync → thread).
  6. On success: sets `status='done'`, clears `locked_at`, `locked_by`, `last_error=None`.
  7. On exception: increments `retry_count`; if `retry_count >= 3` sets `status='failed'`; else sets `status='retry'`; sets `last_error=str(exc)[:500]`.
  Wrap the whole loop body in `try/except Exception` so a crash doesn't kill the coroutine.
- **Done when**: `tests/unit/worker/test_rag_outbox_loop.py` passes — all unit tests with mocked DB session and mocked LlamaIndex PGVectorStore.
- **Test**: Mock `PGVectorStore.add` and `OllamaEmbedding`; mock DB returning one outbox row + one `topic_contents` row with `text="Test content"`; assert `status='done'` is written; assert `PGVectorStore.add` was called with at least 1 node.
- **Depends on**: T2.2 [backend], T3.1, T3.2

##### T3.4 [backend] — Register rag_outbox_loop in worker/__main__.py
- **Build**: In `src/worker/__main__.py`:
  - Add `from worker.rag_outbox_loop import run_rag_outbox_loop` import.
  - Construct the coroutine and add it to the `asyncio.gather(...)` call alongside `extraction_loop`, `essay_grading_loop`, `purge_loop`, `heartbeat_loop`.
  - In the startup validation block, if `settings.embedding.model_spec` is empty: log a `WARNING` message "EMBEDDING__MODEL_SPEC not set — rag_outbox_loop will process rows but embedding calls will fail" (non-fatal; extraction still starts).
- **Done when**: Worker starts without error; `asyncio.gather` includes the RAG loop task; `tests/unit/worker/test_main.py` shows `run_rag_outbox_loop` is registered.
- **Test**: Unit test mocks `run_rag_outbox_loop`; assert it is called as a coroutine argument to `asyncio.gather` at startup.
- **Depends on**: T3.3

##### T3.6 [backend] — Unit tests for rag_outbox_loop
- **Build**: Create (or expand) `tests/unit/worker/test_rag_outbox_loop.py`. Test cases:
  - Happy path: one outbox row + topic_contents text → `status='done'`, `PGVectorStore.add` called.
  - Empty text: outbox row but topic_contents text is None → `status='failed'`, `last_error='empty text'`.
  - Embed failure (first attempt): PGVectorStore.add raises → `retry_count=1`, `status='retry'`.
  - Embed failure (third attempt, retry_count already 2): raises → `status='failed'`.
  - Wrap-around: loop exception (outer try/except) does not kill the coroutine — continues on next iteration.
- **Done when**: `uv run pytest tests/unit/worker/test_rag_outbox_loop.py -v` passes with 100% branch coverage for the file.
- **Test**: Test suite self-verifying — `pytest --cov=src/worker/rag_outbox_loop` shows 100%.
- **Depends on**: T3.3

##### T3.7 [backend] — RAG loop integration test
- **Build**: Add `tests/integration/worker/test_rag_loop_integration.py`. Against the test DB (pgvector-enabled): seed a `topic_contents` row with `text="Hello world. Testing RAG pipeline."`. Seed an `rag_indexing_outbox` row pointing to it with `status='pending'`. Run one iteration of `run_rag_outbox_loop` with a real (or mocked-but-real) `OllamaEmbedding` call (skip in CI if Ollama unavailable via `pytest.mark.skipif`). Assert outbox row `status='done'`; assert `SELECT COUNT(*) FROM data_topic_content_chunks WHERE metadata_->>'content_id' = '<uuid>'` >= 1.
- **Done when**: Test passes against local stack with Ollama running `bge-m3`; CI skips gracefully when Ollama unavailable.
- **Test**: The test itself is the integration assertion.
- **Depends on**: T3.4, T3.6

---

#### G3.3 — Deploy Config [deploy]

##### T3.5 [deploy] — EMBEDDING env vars in common/docker-compose.yml worker block
- **Build**: In `common/docker-compose.yml`, under the `worker` service `environment:` block, append three lines:
  ```yaml
  EMBEDDING__MODEL_SPEC: ${EMBEDDING__MODEL_SPEC}
  EMBEDDING__OLLAMA_BASE_URL: ${EMBEDDING__OLLAMA_BASE_URL:-http://ollama:11434}
  EMBEDDING__BATCH_SIZE: ${EMBEDDING__BATCH_SIZE:-10}
  ```
- **Done when**: `docker compose -f common/docker-compose.yml config` exits 0; the `worker` environment section contains all three vars.
- **Test**: `grep -c "EMBEDDING__" common/docker-compose.yml` returns >= 3.
- **Depends on**: T3.2 [backend]

**G3 integration test**: With pgvector DB + Ollama `bge-m3` running: insert `topic_contents` row; insert `rag_indexing_outbox` row; start worker; wait 10s; assert outbox row `status='done'`; assert `data_topic_content_chunks` has rows with matching `content_id` in metadata.

---

### G4 — hAITU Settings Wired
**Goal**: `HaituSettings` exists in `shared/config.py` and its env vars are wired in the worker service, so the hAITU endpoint (next plan cycle) can read config without a separate settings migration.
**Goal test**: `Settings().haitu.model_spec` returns `""` (empty default); `HAITU__MODEL_SPEC=qwen3:14b` env override is respected; docker-compose config shows HAITU vars in worker environment.
**Repos**: [backend] [deploy]

---

##### T4.1 [backend] — HaituSettings in shared/config.py
- **Build**: In `src/shared/config.py`, add `HaituSettings(BaseModel)` class after `EmbeddingSettings`: fields `model_spec: str = Field(default="")`, `ollama_base_url: str = Field(default="http://localhost:11434")`, `max_tokens: int = Field(default=2048)`. Add `haitu: HaituSettings = HaituSettings()` to `Settings` after `embedding`.
- **Done when**: `Settings().haitu.max_tokens == 2048`; `Settings().haitu.model_spec == ""`; env `HAITU__MODEL_SPEC=test` sets `model_spec="test"`.
- **Test**: `tests/unit/shared/test_config.py` — add assertions for `haitu` defaults and env override `HAITU__MODEL_SPEC=my_model`.
- **Depends on**: None

##### T4.2 [deploy] — HAITU env vars in common/docker-compose.yml worker block
- **Build**: In `common/docker-compose.yml` worker `environment:`, append:
  ```yaml
  HAITU__MODEL_SPEC: ${HAITU__MODEL_SPEC:-}
  HAITU__OLLAMA_BASE_URL: ${HAITU__OLLAMA_BASE_URL:-http://ollama:11434}
  ```
- **Done when**: `grep -c "HAITU__" common/docker-compose.yml` returns >= 2; `docker compose -f common/docker-compose.yml config` exits 0.
- **Test**: `grep "HAITU__MODEL_SPEC" common/docker-compose.yml` exits 0.
- **Depends on**: T4.1 [backend]

**G4 integration test**: `docker compose -f common/docker-compose.yml config` resolves HAITU vars in worker environment without warnings; `Settings(HAITU__MODEL_SPEC="qwen3:14b")` returns `haitu.model_spec == "qwen3:14b"`.

---

### G5 — Text Restructuring Pass
**Goal**: When native PDF extraction yields text (`len >= 50`, image coverage < 0.95) and `EXTRACTION__RESTRUCTURE_TEXT=true`, the worker passes raw text through a text-only LLM call (`restructure_page()`) that fixes fragmented fractions, broken line-breaks, and layout artefacts, returning clean Markdown; if the LLM returns empty, falls back to raw text.
**Goal test**: Configure `EXTRACTION__RESTRUCTURE_TEXT=true`, `EXTRACTION__RESTRUCTURE_MODEL_SPEC=<model>`. Upload a PDF with fragmented native text (e.g., a maths worksheet). The `extraction_job_pages.markdown_text` stored after extraction contains reassembled content (e.g., `3/4` where raw had `3\n4`); no content is added or removed.
**Repos**: [backend] [deploy]

---

#### G5.1 — Config [backend]

##### T5.1 [backend] — Add restructure fields to ExtractionSettings
- **Build**: In `src/shared/config.py` inside `ExtractionSettings`, add two new fields after `purge_interval_seconds`: `restructure_text: bool = Field(default=True)` and `restructure_model_spec: str = Field(default="")`. No other changes.
- **Done when**: `Settings().extraction.restructure_text is True`; `Settings().extraction.restructure_model_spec == ""`; env `EXTRACTION__RESTRUCTURE_TEXT=false` makes it `False`.
- **Test**: `tests/unit/shared/test_config.py` — assert defaults and env overrides for both new fields.
- **Depends on**: None

---

#### G5.2 — Restructure Prompt [backend]

##### T5.2 [backend] — Create prompts/restructure_prompt.md
- **Build**: Determine where `worker/prompts.py` reads prompt files. Create `src/worker/prompts/restructure_prompt.md` (or wherever contents prompt lives). File content:
  ```
  The text below was extracted from a PDF page (educational content).
  The extraction may be fragmented: fractions may be split across lines, words may be
  broken, and spacing or layout context may be lost.

  Rewrite the text as clean, readable Markdown following these rules:
  - Reassemble fractions: if a number sits alone on a line and the next line is also a
    lone number, they form a fraction — write them as numerator/denominator (e.g. 3
    then 4 → 3/4).
  - Use ## for the page/section title, ### for sub-sections.
  - Use numbered lists (1. 2. 3.) for questions, lettered sub-lists (a. b. c.) for parts.
  - Preserve every number, symbol (≡ = < > ± × ÷ →), and word exactly — do NOT
    paraphrase, summarise, or add anything.
  - Output ONLY the Markdown — no explanation, no code fences.

  Extracted text:
  ---
  {raw_text}
  ---
  ```
- **Done when**: File exists; `open("restructure_prompt.md").read().format(raw_text="abc")` executes without `KeyError`.
- **Test**: `tests/unit/worker/test_prompts.py` — read the file, call `.format(raw_text="hello")`, assert result contains `"hello"` and does not contain `"{raw_text}"`.
- **Depends on**: None

---

#### G5.3 — restructure_page() Method [backend]

##### T5.3 [backend] — Add text-only helpers + restructure_page() to GlmOcrProvider
- **Build**: In `src/infrastructure/extraction/glm_ocr_provider.py`:
  1. Add `_text_stream_ollama(self, prompt: str) -> Generator[StreamEvent]`: same as `_stream_ollama` but the payload dict has no `"images"` key — text-only `/api/generate` call.
  2. Add `_text_stream_openai_compat(self, prompt: str, *, model: str, api_key: str | None = None, base_url: str | None = None) -> Generator[StreamEvent]`: same as `_stream_openai_compat` but `content` is a single string message `{"role": "user", "content": prompt}` (no image).
  3. Add `_text_stream_anthropic(self, prompt: str) -> Generator[StreamEvent]`: same as `_stream_anthropic` but `content_blocks` is `[{"type": "text", "text": prompt}]` only.
  4. Add `restructure_page(self, raw_text: str) -> str` public method: (a) locate the prompt file relative to this module's `__file__`; (b) load and format with `{raw_text=raw_text}`; (c) dispatch to the correct text-only stream helper based on `self._scheme`; (d) collect chunks; (e) if result is empty after strip, return `raw_text`; else return result. Note: `ExtractionProvider` protocol is NOT changed — `restructure_page` is a concrete extension on `GlmOcrProvider` only; `extract_page` uses `hasattr(provider, "restructure_page")` guard.
- **Done when**: `tests/unit/infrastructure/test_glm_ocr_provider.py` — new test class `TestRestructurePage` passes: (a) Ollama scheme: mock httpx, assert payload has no `"images"` key; (b) empty LLM response → returns raw_text fallback; (c) non-empty response → returns restructured text.
- **Test**: Mock Ollama httpx call; assert `restructure_page("hello")` calls `/api/generate` without `"images"` in request body.
- **Depends on**: T5.2

---

#### G5.4 — Extraction Loop Integration [backend]

##### T5.4 [backend] — Call restructure_page in extract_page()
- **Build**: In `src/worker/extraction_loop.py`, modify the `extract_page()` function. In the PDF branch, update the `if len(text) >= 50 and coverage < 0.95:` block:
  ```python
  if len(text) >= 50 and coverage < 0.95:
      if (
          settings.extraction.restructure_text
          and settings.extraction.restructure_model_spec
          and hasattr(provider, "restructure_page")
      ):
          restructured = await asyncio.to_thread(provider.restructure_page, text)
          return restructured if restructured.strip() else text
      return text
  ```
  The triple-condition guard (flag + non-empty model spec + method exists) ensures the raw path is unchanged when restructuring is disabled or model spec is unset.
- **Done when**: `tests/unit/worker/test_extraction_loop.py` — parametrised tests: (1) `restructure_text=True, restructure_model_spec="m"` and text >= 50 chars → `restructure_page` called and result returned; (2) `restructure_text=False` → `restructure_page` NOT called; (3) `restructure_model_spec=""` → NOT called; (4) `restructure_page` returns empty string → original text returned.
- **Test**: Mock `provider.restructure_page` returning `"cleaned"`. Assert page markdown is `"cleaned"` when all three conditions are true.
- **Depends on**: T5.1, T5.3

---

#### G5.5 — Deploy Config [deploy]

##### T5.5 [deploy] — Add EXTRACTION__RESTRUCTURE_* to common/docker-compose.yml worker
- **Build**: In `common/docker-compose.yml` worker `environment:`, append:
  ```yaml
  EXTRACTION__RESTRUCTURE_TEXT: ${EXTRACTION__RESTRUCTURE_TEXT:-true}
  EXTRACTION__RESTRUCTURE_MODEL_SPEC: ${EXTRACTION__RESTRUCTURE_MODEL_SPEC:-}
  ```
- **Done when**: `grep -c "EXTRACTION__RESTRUCTURE" common/docker-compose.yml` returns 2.
- **Test**: `docker compose -f common/docker-compose.yml config` exits 0.
- **Depends on**: T5.1 [backend]

---

#### G5.6 — Tests [backend]

##### T5.6 [backend] — Unit tests for restructure_page()
- **Build**: In `tests/unit/infrastructure/test_glm_ocr_provider.py`, add `TestRestructurePage` class with: (a) Ollama scheme mock — assert `/api/generate` called without `images` key, returns restructured text; (b) empty response → returns original `raw_text`; (c) lmstudio scheme mock; (d) openai scheme mock; (e) anthropic scheme mock.
- **Done when**: All test cases in `TestRestructurePage` pass.
- **Test**: Test suite self-verifying.
- **Depends on**: T5.3

##### T5.7 [backend] — Integration test for text restructuring pipeline
- **Build**: In `tests/unit/worker/test_extraction_loop.py`, add an integration-style unit test `test_restructure_called_when_enabled`: configure mock `provider` with `restructure_page` method; call `extract_page()` with a PDF page mock returning text of 60 chars and image coverage 0.1; with `EXTRACTION__RESTRUCTURE_TEXT=true` and `EXTRACTION__RESTRUCTURE_MODEL_SPEC=m`; assert `restructure_page` was called exactly once; assert returned text equals the mock restructured output.
- **Done when**: Test passes under `uv run pytest tests/unit/worker/test_extraction_loop.py::test_restructure_called_when_enabled`.
- **Test**: Assert `provider.restructure_page.call_count == 1`.
- **Depends on**: T5.4, T5.6

**G5 integration test**: Upload a synthetic PDF with fragmented native text (fractions split) to the API; worker processes; query `extraction_job_pages`; assert `markdown_text` contains the reassembled fraction format.

---

### G6 — Student Dashboard Backend APIs
**Goal**: Four GET endpoints under `/api/student/` return node trees, topic lists, and content for authenticated students. `X-Current-Role: student` required; wrong role → 403; missing role → 400. Parent-owned content gated behind active `parent_child_links`.
**Goal test**: Student with `X-Current-Role: student` calls `GET /api/student/dashboard` → 200 with platform nodes. Student without student role → 403. Parent-linked student calls `GET /api/student/nodes?owner_type=parent&owner_id=<sub>` → includes parent nodes. Non-linked student calls same → 403.
**Repos**: [backend]

---

##### T6.1 [backend] — Add get_active_links_for_child to ParentChildLinkRepository
- **Build**: In `src/domain/repositories/user_metadata_repository.py`, add abstract method `async def get_active_links_for_child(self, child_sub: str) -> list[ParentChildLink]` to `AbstractParentChildLinkRepository`. In `src/infrastructure/repositories/user_metadata_repository.py`, implement in `ParentChildLinkRepository`: `SELECT * FROM parent_child_links WHERE child_sub = :child_sub AND revoked_at IS NULL ORDER BY created_at`.
- **Done when**: Calling `repo.get_active_links_for_child("sub-123")` returns a list (empty when no links, populated when links exist).
- **Test**: `tests/unit/infrastructure/test_user_metadata_repository.py` — mock DB session; assert query filters `revoked_at IS NULL` and `child_sub = :child_sub`.
- **Depends on**: None

##### T6.2 [backend] — Create StudentDashboardService
- **Build**: Create `src/domain/services/student_dashboard_service.py`. Class `StudentDashboardService` injected with `node_repo`, `topic_repo`, `topic_content_repo`, `link_repo`. Methods:
  - `get_dashboard(student_sub: str) -> dict`: returns `{"platform_nodes": list[CoursePathNode], "has_parent_link": bool}`. Platform nodes via `node_repo.get_platform_root_nodes()`. has_parent_link = `len(await link_repo.get_active_links_for_child(student_sub)) > 0`.
  - `get_node_tree(owner_type: str, owner_id: str | None, student_sub: str) -> list[CoursePathNode]`: if `owner_type == "parent"`, verify active link where `owner_id` matches a `parent_sub` for `child_sub == student_sub` — raise `PermissionError("No active parent link")` if none. Then return nodes for that owner.
  - `get_live_topics_for_node(node_id: UUID, student_sub: str) -> list[Topic]`: returns topics via `topic_repo` filtered `status='live'`.
  - `get_topic_content(topic_id: UUID, student_sub: str) -> list[TopicContent]`: verify topic is live and accessible; return content via `topic_content_repo`.
- **Done when**: All four method unit tests pass.
- **Test**: `tests/unit/domain/test_services/test_student_dashboard_service.py` — mock all repos; assert `get_node_tree(owner_type="parent", ...)` raises `PermissionError` when no active link; assert `get_dashboard` sets `has_parent_link=False` with empty link list.
- **Depends on**: T6.1, T6.3

##### T6.3 [backend] — Add get_platform_root_nodes to CoursePathNodeRepository
- **Build**: In `src/domain/repositories/course_path_node_repository.py` (abstract), add `async def get_platform_root_nodes(self) -> list[CoursePathNode]`. In `src/infrastructure/repositories/course_path_node_repository.py`, implement: `SELECT * FROM course_path_nodes WHERE owner_type='platform' AND parent_id IS NULL ORDER BY "order"`.
- **Done when**: `repo.get_platform_root_nodes()` returns root platform nodes only.
- **Test**: `tests/unit/infrastructure/test_course_path_node_repository.py` — mock session; assert query contains `owner_type='platform'` and `parent_id IS NULL`.
- **Depends on**: None

##### T6.4 [backend] — Create schemas/student_dashboard.py
- **Build**: Create `src/schemas/student_dashboard.py`. Pydantic models:
  - `PlatformNodeCard`: `id: UUID`, `name: str`, `node_type: str`, `topic_count: int = 0`, `owner_type: str`.
  - `StudentDashboardRead`: `platform_nodes: list[PlatformNodeCard]`, `has_parent_link: bool`.
  - `StudentTopicRead`: `id: UUID`, `title: str`, `status: str`, `order: int | None = None`, `has_exam: bool = False`.
  - `StudentTopicContentRead`: `id: UUID`, `content_type: str`, `title: str`, `text: str | None = None`, `url: str | None = None`.
- **Done when**: `from schemas.student_dashboard import StudentDashboardRead; StudentDashboardRead(platform_nodes=[], has_parent_link=False)` instantiates without error.
- **Test**: `tests/unit/schemas/test_student_dashboard.py` — assert `StudentDashboardRead(platform_nodes=[], has_parent_link=False).model_dump()` has keys `platform_nodes` and `has_parent_link`.
- **Depends on**: None

##### T6.5 [backend] — Create api/routes/student_dashboard.py
- **Build**: Create `src/api/routes/student_dashboard.py`. `router = APIRouter()`. Four GET endpoints, all use `Depends(current_active_user)` with `X-Current-Role: student` enforcement (`current_role != "student"` → `HTTPException(403)`). No CSRF required (GET-only).
  - `GET /dashboard` → `StudentDashboardService.get_dashboard(user.sub)` → `StudentDashboardRead`.
  - `GET /nodes` query params `owner_type: str`, `owner_id: str | None = None` → `get_node_tree(...)`. Map `PermissionError` → `HTTPException(403)`.
  - `GET /nodes/{node_id}/topics` → `get_live_topics_for_node(node_id, user.sub)` → `list[StudentTopicRead]`.
  - `GET /topics/{topic_id}/content` → `get_topic_content(topic_id, user.sub)` → `list[StudentTopicContentRead]`. Map `PermissionError` → `HTTPException(403)`.
  Inline `get_student_dashboard_service` dependency function wires `StudentDashboardService` from DB session.
- **Done when**: All four routes return 200 for authorized student, 403 for wrong role, 400 for missing role header.
- **Test**: `tests/unit/routes/test_student_dashboard.py` — student role → 200; `X-Current-Role: instructor` → 403; no `X-Current-Role` header → 400.
- **Depends on**: T6.2, T6.4

##### T6.6 [backend] — Register student_dashboard router in api/router.py
- **Build**: In `src/api/router.py`, add `from api.routes import student_dashboard` and `app.include_router(student_dashboard.router, prefix="/api/student", tags=["Student Dashboard"])`.
- **Done when**: `GET /api/student/dashboard` appears in `/openapi.json`; existing routes are unaffected.
- **Test**: `tests/unit/routes/test_student_dashboard.py` integration call — `GET /api/student/dashboard` returns 200 (mocked service) not 404.
- **Depends on**: T6.5

##### T6.7 [backend] — Student dashboard API integration test
- **Build**: Create `tests/integration/routes/test_student_dashboard_integration.py`. Against test DB: seed platform `course_path_nodes` (owner_type='platform', parent_id=NULL); seed a `parent_child_links` row for a test student. Call `GET /api/student/dashboard` with `X-Current-Role: student` → assert 200 with `platform_nodes` non-empty and `has_parent_link=true`. Call `GET /api/student/nodes?owner_type=parent&owner_id=<parent_sub>` → 200. Call same with a different student (no link) → 403.
- **Done when**: Integration test passes against test DB.
- **Test**: The test file is the assertion.
- **Depends on**: T6.6

**G6 integration test**: End-to-end via FastAPI test client: seed student + platform nodes + parent link; call all four endpoints; assert shape, status codes, and permission boundary.

---

### G7 — Student Dashboard Frontend
**Goal**: Students see a working `/home` dashboard (S-home) with Platform Board (blue) + Home Study (green) sections, and a `/courses` content navigator (S-nav) with tree sidebar, topic list, and inline content viewer — all populated from the student API endpoints.
**Goal test**: Log in as student role. `/home` shows "Platform Board" heading with blue subject cards. No parent link → Home Study shows placeholder. `/courses` shows Platform | Home Study tabs; selecting a node in the tree shows topic list; clicking a topic opens the content viewer.
**Repos**: [frontend]

---

#### G7.1 — Types + API Layer [frontend]

##### T7.1 [frontend] — Student domain types
- **Build**: Create `src/features/student/types/student.types.ts`. Define interfaces: `StudentDashboardResponse { platform_nodes: PlatformNodeCard[]; has_parent_link: boolean }`, `PlatformNodeCard { id: string; name: string; node_type: string; topic_count: number; owner_type: string }`, `StudentNode { id: string; name: string; parent_id: string | null; children?: StudentNode[]; topic_count: number }`, `StudentTopic { id: string; title: string; status: string; has_exam: boolean }`, `StudentTopicContent { id: string; content_type: "video" | "pdf" | "text" | "question" | "question_answer"; title: string; text: string | null; url: string | null }`.
- **Done when**: `tsc --noEmit` passes with no errors on the new file.
- **Test**: `src/features/student/types/__tests__/student-types.test.ts` — construct a `StudentDashboardResponse` object and assert it `satisfies StudentDashboardResponse`.
- **Depends on**: None

##### T7.2 [frontend] — student-api.ts
- **Build**: Create `src/features/student/api/student-api.ts`. Export object `studentApi` with methods using raw `fetch` + `credentials: 'include'` + `buildApiHeaders(csrfToken, "student")` (X-Current-Role: student):
  - `getDashboard(csrfToken: string): Promise<StudentDashboardResponse>` → `GET /api/student/dashboard`
  - `getNodes(csrfToken: string, ownerType: string, ownerId?: string): Promise<StudentNode[]>` → `GET /api/student/nodes?owner_type=...`
  - `getTopicsForNode(csrfToken: string, nodeId: string): Promise<StudentTopic[]>` → `GET /api/student/nodes/:nodeId/topics`
  - `getTopicContent(csrfToken: string, topicId: string): Promise<StudentTopicContent[]>` → `GET /api/student/topics/:topicId/content`
  All throw a typed `ApiError` on non-ok responses.
- **Done when**: TypeScript compiles; unit tests pass.
- **Test**: `src/features/student/api/__tests__/student-api.test.ts` — mock `fetch`; assert `getDashboard` sends `GET /api/student/dashboard` with `X-Current-Role: student`; assert error thrown on 403.
- **Depends on**: T7.1

---

#### G7.2 — Hooks [frontend]

##### T7.3 [frontend] — useStudentDashboard hook
- **Build**: Create `src/features/student/hooks/use-student-dashboard.ts`. Custom hook using `useState`/`useEffect` (no React Query). Fetches `studentApi.getDashboard()` on mount when `csrfToken` is available. Returns `{ platformNodes: PlatformNodeCard[], hasParentLink: boolean, isLoading: boolean, error: Error | null }`.
- **Done when**: Hook returns `isLoading=false` and populated `platformNodes` after mocked fetch resolves.
- **Test**: `src/features/student/hooks/__tests__/use-student-dashboard.test.ts` — mock `studentApi.getDashboard`; render hook; assert `platformNodes` populated after promise resolves.
- **Depends on**: T7.2

##### T7.4 [frontend] — useStudentNav hook
- **Build**: Create `src/features/student/hooks/use-student-nav.ts`. State: `selectedSource: "platform" | "parent"`, `nodeTree: StudentNode[]`, `selectedNodeId: string | null`, `topics: StudentTopic[]`, `selectedTopicContent: StudentTopicContent[] | null`, `isLoading: boolean`. Actions: `selectSource`, `selectNode`, `selectTopic`, `clearContent`. Uses `useEffect` to fetch node tree when source changes; fetch topics when `selectedNodeId` changes; fetch content when topic selected.
- **Done when**: Calling `selectSource("platform")` triggers fetch and populates `nodeTree`.
- **Test**: `src/features/student/hooks/__tests__/use-student-nav.test.ts` — mock `studentApi.getNodes`; call `selectSource("platform")`; assert `nodeTree` populated.
- **Depends on**: T7.2

---

#### G7.3 — S-home Page [frontend]

##### T7.5 [frontend] — PlatformBoardSection component
- **Build**: Create `src/features/student/components/platform-board-section.tsx`. Accepts `nodes: PlatformNodeCard[]`. Renders section with heading "Platform Board" (blue `#185FA5`). Grid of cards: each card shows node name, topic count, "Start" CTA linking to `/courses?source=platform&nodeId=<id>`. CSS module `platform-board-section.module.css`.
- **Done when**: Renders 2 cards when given 2 nodes; "Start" links to correct URL.
- **Test**: `src/features/student/components/__tests__/platform-board-section.test.tsx` — render with 2 nodes; assert 2 cards with correct names appear.
- **Depends on**: T7.1

##### T7.6 [frontend] — HomeStudySection component
- **Build**: Create `src/features/student/components/home-study-section.tsx`. Accepts `hasParentLink: boolean`, `nodes: PlatformNodeCard[]`. When `!hasParentLink`: render single placeholder card with text "No Home Study content yet — ask your parent to link their account." When `hasParentLink`: render card grid (green `#1D9E75`), linking to `/courses?source=parent&nodeId=<id>`. CSS module.
- **Done when**: `hasParentLink=false` → placeholder text; `hasParentLink=true` → card grid.
- **Test**: `src/features/student/components/__tests__/home-study-section.test.tsx` — render with `hasParentLink=false`, assert placeholder text; render with `hasParentLink=true` + 1 node, assert card.
- **Depends on**: T7.1

##### T7.7 [frontend] — Update app/home/page.tsx with student role branch
- **Build**: In `src/app/home/page.tsx`, add conditional: if `currentRole === "student"`, render `<StudentHomePage />` (new component). Create `src/features/student/components/student-home-page.tsx`: uses `useStudentDashboard` hook, renders `<PlatformBoardSection nodes={platformNodes} />` and `<HomeStudySection hasParentLink={hasParentLink} nodes={[]} />`. Non-student roles render existing content unchanged.
- **Done when**: `currentRole=student` → renders "Platform Board" and "Home Study" sections. `currentRole=instructor` → existing UI unchanged.
- **Test**: `src/features/student/components/__tests__/student-home-page.test.tsx` — mock `useStudentDashboard` returning 2 platform nodes + `hasParentLink=false`; assert "Platform Board" heading; assert placeholder in Home Study section.
- **Depends on**: T7.3, T7.5, T7.6, T6.6 [backend]

---

#### G7.4 — S-nav Page [frontend]

##### T7.8 [frontend] — app/courses page shell
- **Build**: Create `src/app/courses/page.tsx`. `export const dynamic = "force-dynamic"`. Uses `useStudentNav` hook. Renders two tabs: "Platform" (always enabled) and "Home Study" (disabled when `!hasParentLink`). Tab click calls `selectSource(...)`. Left sidebar placeholder (wired in T7.12); right panel placeholder. Uses existing `MainLayout`/`Header`.
- **Done when**: `/courses` route renders; tabs visible; Home Study tab has disabled attribute when `hasParentLink=false`.
- **Test**: `src/app/courses/__tests__/courses-page.test.tsx` — render, assert "Platform" and "Home Study" tabs; assert Home Study is disabled when `hasParentLink=false`.
- **Depends on**: T7.4

##### T7.9 [frontend] — NodeTreeSidebar component
- **Build**: Create `src/features/student/components/node-tree-sidebar.tsx`. Props: `nodes: StudentNode[]`, `selectedNodeId: string | null`, `onSelectNode: (id: string) => void`. Each row: expand/collapse chevron (toggles children), node name, topic-count badge. Leaf nodes (no children) clickable — calls `onSelectNode`. CSS module for indentation levels.
- **Done when**: Chevron toggles children visibility; clicking leaf calls `onSelectNode` with correct id.
- **Test**: `src/features/student/components/__tests__/node-tree-sidebar.test.tsx` — render 2-level tree; click chevron → children appear; click leaf → `onSelectNode` called with leaf id.
- **Depends on**: T7.1

##### T7.10 [frontend] — TopicListPanel component
- **Build**: Create `src/features/student/components/topic-list-panel.tsx`. Props: `topics: StudentTopic[]`, `onSelectTopic: (id: string) => void`. Each row: topic title, content-type icon badges (PDF/video/text), "Take Exam" button when `has_exam=true` (disabled for this increment — tooltip "Exam available"). Clicking row calls `onSelectTopic`.
- **Done when**: Renders topic rows; "Take Exam" appears only for `has_exam=true`; row click fires `onSelectTopic`.
- **Test**: `src/features/student/components/__tests__/topic-list-panel.test.tsx` — render 2 topics (one with `has_exam=true`); assert 1 "Take Exam" button; click row → `onSelectTopic` called.
- **Depends on**: T7.1

##### T7.11 [frontend] — ContentViewer component
- **Build**: Create `src/features/student/components/content-viewer.tsx`. Props: `contents: StudentTopicContent[]`. For each item: `content_type='pdf'` → `<SecurePdfViewer url={url} />` (lazy import, existing component); `content_type='video'` → `<iframe src={url} allowFullScreen>`; `content_type='text'` → `<div dangerouslySetInnerHTML={{ __html: sanitizedHtml(text) }}>` (sanitise via `DOMPurify` or equivalent). Shows loading spinner while PDF lazy-chunk loads.
- **Done when**: Text content renders as HTML; video renders as iframe with correct src; PDF renders via SecurePdfViewer.
- **Test**: `src/features/student/components/__tests__/content-viewer.test.tsx` — render text content, assert text displayed; render video, assert `<iframe>` with correct src.
- **Depends on**: T7.1

##### T7.12 [frontend] — Wire S-nav in courses/page.tsx
- **Build**: In `src/app/courses/page.tsx`, replace sidebar and panel placeholders with: `<NodeTreeSidebar nodes={nodeTree} selectedNodeId={selectedNodeId} onSelectNode={selectNode} />` and `<TopicListPanel topics={topics} onSelectTopic={selectTopic} />` and `<ContentViewer contents={selectedTopicContent ?? []} />`. Tab switch calls `selectSource`. Handle `isLoading` with skeleton states.
- **Done when**: Full S-nav cycle works in unit test: switching tab → nodeTree loads; clicking node → topics load; clicking topic → content appears.
- **Test**: `src/app/courses/__tests__/courses-page.test.tsx` — mock `useStudentNav`; assert that when `selectedNodeId` changes, `TopicListPanel` receives `topics`; when `selectedTopicContent` changes, `ContentViewer` receives content.
- **Depends on**: T7.8, T7.9, T7.10, T7.11, T6.6 [backend]

##### T7.13 [frontend] — Playwright E2E test: student dashboard
- **Build**: Create `tests/e2e/student-dashboard.spec.ts`. Test steps:
  1. Log in as student role.
  2. Navigate to `/home`.
  3. Assert "Platform Board" heading and at least 1 subject card.
  4. When no parent link: assert Home Study placeholder text.
  5. Click a subject card → navigate to `/courses`.
  6. Assert "Platform" tab active; left sidebar shows nodes; click a node → right panel shows topics.
  7. Click a topic → content viewer opens.
- **Done when**: Playwright test passes against local stack with seeded data.
- **Test**: The test file is the E2E assertion.
- **Depends on**: T7.7, T7.12

**G7 integration test**: Vitest with React Testing Library — render `StudentHomePage` with mocked `useStudentDashboard` (2 nodes, no parent link); assert Platform Board section + Home Study placeholder. Render `courses/page.tsx` with mocked `useStudentNav`; assert full tree→topic→content interaction cycle.

---

## ROOT Acceptance Test

**Manual + Playwright E2E:**
1. Start local stack (pgvector-enabled db, Ollama with `bge-m3`, worker).
2. Platform admin uploads a multi-page PDF with math content (fractions, lists).
3. Worker extracts: native-text pages are restructured via `restructure_page()` — verify `extraction_job_pages.markdown_text` has reassembled fractions.
4. `rag_indexing_outbox` row is created after finalize.
5. Worker drain loop fires: row transitions to `done`; `data_topic_content_chunks` gains rows with correct `content_id` metadata.
6. Student logs in: `/home` shows Platform Board with subject cards.
7. Student navigates to `/courses`: tree sidebar loads; selecting a leaf node shows topics; clicking a topic opens content viewer.

---

## Implementation Notes

**Backend pattern references:**
- Config: `src/shared/config.py` `ExtractionSettings` / `GradingSettings` — copy pattern for `EmbeddingSettings`, `HaituSettings`
- Provider: `src/infrastructure/extraction/glm_ocr_provider.py` — existing streaming helpers are patterns for text-only variants
- Worker loop: `src/worker/extraction_loop.py`, `src/worker/essay_grading_loop.py` — SKIP LOCKED pattern
- Worker entry: `src/worker/__main__.py` — asyncio.gather registration pattern

**Frontend pattern references:**
- Auth hook: `src/hooks/use-auth.ts` — `useState`/`useEffect` pattern (no React Query)
- API calls: `src/lib/utils.ts` `buildApiHeaders()` — include `X-Current-Role`
- Existing student screens: `src/app/exam/` — page shell pattern; `src/features/exam/` — feature module pattern
- Content viewer: `SecurePdfViewer` is already implemented — lazy import for PDF pages

**Open Points (deferred, requires separate spec):**
1. hAITU retrieval endpoint (`POST /api/haitu/topic-doubt`) — next plan cycle, depends on vectors being populated
2. "Take Exam" CTA in S-nav — `POST /api/student/exam-sessions` is already implemented (from Phase 1c-pre); wire up in a subsequent frontend task
3. Parent Home Study nodes in S-nav — node API exists; parent nodes need to be fetched alongside platform nodes once `hasParentLink=true`
4. S-results grading status display — API contract is specced in `03_student.md`; frontend rendering deferred to next phase

<!-- plan-baseline: backend:7c1b72d3eb4dbc579981184abc86679e72dbed1d frontend:d0e9242c9c03580305725285f995180de3624952 deploy:c407e7a052adf331776b261596d53dbd6f0595e8 -->
