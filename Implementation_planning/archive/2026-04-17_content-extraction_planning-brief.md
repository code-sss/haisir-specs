# Planning Brief — Content Extraction Service (Phase 1d-pre)

> ## ⚠️ SUPERSEDED — archived 2026-08-09. Historical record only; do not plan from this.
>
> This is a **pre-`/plan` brief**, written 2026-04-17 and blocked at the time on the five scope
> questions in §10. Those questions were answered, and the phase they fed shipped. The successor
> artifacts are the authoritative record:
>
> - `archive/PLAN_phase1d-real_2026-06-05.md` / `archive/TASKS_phase1d-real_2026-06-05.md`
> - `target/requirements/12_content_extraction.md` — the spec as built
> - `decisions.md` — the reasoning actually adopted
>
> **§10's recommended defaults were not all taken.** Most importantly **Q1**: this brief recommended
> *(a) synchronous extraction with a ~10-page cap*. What shipped is a **worker process draining a
> Postgres queue** (`extraction_jobs`, `FOR UPDATE SKIP LOCKED`) — nearer the (c)/(d) options it
> ranked below, but on Postgres rather than ARQ + Redis. Read §10 as options that *were* on the
> table, never as a description of the system. Q2 (local disk under `data_dir`) and Q4 (admin picks
> the type upfront) were adopted broadly as recommended.
>
> **Filing note:** this sat loose in `Implementation_planning/` from creation until 2026-08-09 — the
> pass that archived the Phase 1d plan and tasks (`3f25c5e`) missed it. Its original header claimed
> the file lived at `Implementation_planning/handoffs/…`, a directory that has never existed in this
> repo; that line is removed rather than preserved, since it only ever pointed nowhere.

> **Created**: 2026-04-17
> **Author**: `/plan` skill (Claude Code, Opus 4.7)
> **Status at time of writing**: Decision pending — awaiting architectural answers from the team.
> **Working session**: Phase 0–2 of `/plan` complete; Phase 3 (decomposition) blocked on the 5 scope questions in §10.
> **Output of**: 3 parallel context-gathering agents (target specs, backend ground truth, glm_ocr deep-dive + 2026 PDF-tooling web research) + 1 challenger agent.

---

## 1. Purpose

This document captures every fact gathered, every option ranked, every risk flagged, and every architectural question that must be answered before the next `/plan` invocation can decompose the work into a goal tree and write `Implementation_planning/PLAN.md` + `TASKS.md`.

The brief is intentionally **comprehensive**: it is meant to be read end-to-end by someone making the architectural calls so they don't need to re-derive context from scratch.

---

## 2. Original user prompt (verbatim)

> I want to work on a new requirement
>
> I was doing R&D and now its time to use that code for integrating with real work which happen on backend repo. there is a module glm-ocr in haiguru repo. you should access to all the repos. i.e. haisir-backend, haisir-frontend, haisir-deploy, haiguru. all at parallel path to current repo haisir-specs.
>
> We now need to distill the code from glm-ocr and add it to backend (production ready code with enterprise grade, best practices and industry standard, keeping the high standards of coding).
>
> **What is glm-ocr**
> This module named same as llm glm-ocr which is visual model to read images etc as ocr. This module is trying to read the input as images and then trying to convert into text as outputs, which can be either content or exercise. You can read more (try deep dive to understand what it does to properly distill it).
>
> **Requirement to work on**
> You can look into our current specs and see that we have next state or may be target state to work on 1d. 1d will upload content for platform admin. So to be ready with this requirement (1d), we might need this module which will read those images or pdf files to extract text. there is further work too in haiguru, which will save this extracted content+exercises to postgres pg vector but we will work on that later or soon depending on dependency or sequence for upload content to be successfully work with application. you need to fully analyze the code of backend specially or may be other repos like frontend too to figure out the proper plan and code changes. also look into specs to find more information as necessary.
>
> only one thing not handled currenrtly in the code of glm ocr is the pdf. we need to figure out how to ensure that we use some tool either current glm-ocr or some other pdf tool which must be the best for this to extract the pdf (please do web search for this to find out with facts without hallucination or your own memory). but you may need to add code to decide when to use glm-ocr which is a visual llm to extract from images vs when pdf has easily extratable text out of it instead of overloading or overusing the llm to be cost effective
>
> We want to use ollama for llm models which are open source like glm-ocr or others depending on which fits best for what. for local development, we will use LM Studio or ollama deployed locally but for real production we will use ollama monthly subscription to call the api so ensure our code can handle both.
>
> Please look carefully into above and try to come up with specs to work on. this is the immediate task to do so this should be done before 1d. so better put id back to target state if required and create proper plan and requirement with phases to do this and move to next state.
>
> if any gaps, please fill in. if any questions, then ask.

User clarification mid-session:
> just to make sure, you have latest code for haiguru, please pull again or check latest revision. i committed the code for connecting using lm studio for local dev. please proceed after that.

(`haiguru` confirmed at `main @ 7fc5a42 feat: add LM Studio local server support and update model argument in CLI` — already up to date with origin.)

---

## 3. Goal as I understand it

Insert a **new sub-phase before Phase 1d (Topic Content Upload)** that ships a production-grade content-extraction backend service. This service:

- Distills `haiguru/glm_ocr` (R&D-quality, sync, CLI-driven) into the FastAPI backend (async, DDD, 100% coverage).
- Adds a **smart PDF router** that uses native text extraction when a PDF has an embedded text layer and falls back to the visual LLM only for scanned PDFs. Image inputs always go to the visual LLM.
- Provides a **pluggable LLM provider** so the same code path runs against LM Studio (local dev), local Ollama (local dev/staging), or hosted Ollama Cloud (production).
- Stores `extracted_text` and lifecycle status fields on `topic_contents` so Phase 1d's UI can render upload progress + extracted text without further backend changes.
- **Does NOT** add pgvector/embeddings/RAG chunk store — that is explicitly downstream and will be its own phase.
- Writes the spec file (`target/requirements/12_content_extraction.md` proposed) that this phase implements; updates `target/requirements/01_data_model.md` for the new columns; updates the admin UI mapping for the upload modal.
- Pushes Phase 1d back to "next phase after this one".

---

## 4. Repo layout (multi-repo platform)

| Repo | Path | Role |
|---|---|---|
| `haisir-specs` | `/home/gulzar/Workspace/haisir-specs` (this) | Target/vision requirements, prototypes, planning docs |
| `haisir-backend` | `../haisir-backend` | FastAPI backend (DDD, async, 100% coverage) |
| `haisir-frontend` | `../haisir-frontend` | Next.js frontend |
| `haisir-deploy` | `../haisir-deploy` | Docker Compose / APISIX / Keycloak |
| `haiguru` | `../haiguru` | R&D sandbox — source of glm_ocr, embed_pipeline, etl_pipeline, rag |

Sibling baselines at session start:
- `haisir-backend` HEAD = `819893c` (unchanged from prior plan baseline)
- `haisir-frontend` HEAD = `82a69f1` (2 minor non-functional commits since baseline)
- `haisir-deploy` HEAD = `239f968` (Jenkins/deploy fixes)
- `haiguru` HEAD = `7fc5a42` (LM Studio local-server support added by user before this session)

---

## 5. Phase 0 — Reconciliation outcome

The pre-existing `Implementation_planning/PLAN.md` was a **stub** for Phase 1d (status: "Not yet planned", zero tasks, only a backlog table for deferred Issues 2/3/6). `Implementation_planning/TASKS.md` was the **completed** Phase 1c-post checklist (all items checked, phase ✓ on 2026-04-09).

**Action taken (already executed this session):**
- `Implementation_planning/PLAN.md` → archived as `Implementation_planning/archive/phase1d-plan-stub_2026-04-16.md`
- `Implementation_planning/TASKS.md` → archived as `Implementation_planning/archive/phase1c-post-tasks_2026-04-09.md`

`Implementation_planning/` now contains only `decisions.md`, `phases.md`, `progress.md`, plus the `archive/` and `handoffs/` directories. The next `/plan` cycle starts from a clean slate.

---

## 6. Phase 1a — Target-state spec findings

### 6.1 Current `topic_contents` columns (no extraction fields exist)

From `current/schema.md:L110-118`:

```
id (UUID PK), topic_id (FK), content_type (Enum: video|pdf|text|question|question_answer),
title, url (nullable), text (nullable), order, description (nullable)
```

**No** `text_extracted`, `extraction_status`, `extracted_at`, `extraction_provider`, `extraction_model`, `extraction_checksum` exist today. The vision spec did define them (`vision/requirements/01_data_model.md:L849-866`); the **target spec deliberately dropped them** as part of the target-state increment scope.

### 6.2 Current API surface for content (`current/api_contracts.md:L197-215`)

- `GET /api/topic-contents/{topic_id}` — list (any platform role)
- `GET /api/topic-contents/{content_type}/{topic_id}` — `FileResponse` (PDF download — hardcoded `application/pdf`)
- `POST /api/topic-contents` — admin only, CSRF; **JSON body** (`{topic_id, content_type, title, url?, text?, order, description?}`); **does NOT write bytes anywhere** — the `url` field is just a string the caller supplies.

Phase 1d planned-but-stub: `PATCH /api/topic-contents/{id}` + `DELETE /api/topic-contents/{id}`.

Target persona spec (`target/requirements/05_06_07_personas.md:L225`) references `POST /api/admin/topics/:topic_id/content` — **not implemented anywhere**. This is the route the new phase will design.

### 6.3 Admin prototype for upload (`target/prototypes/haisir_admin_flow.html:L585-598`)

Topic card has an "Upload content" row button — **the button is a pure stub** (`showToast('Upload content for ${name}')`). No modal, no content-type selector, no upload progress states, no success/failure UI exists in the prototype. **Prototype must be filled in or a new UI mapping spec written.**

### 6.4 LLM / OCR / RAG mentions across all specs

- **Primary LLM is Anthropic Claude** for hAITU (`vision/requirements/00_overview.md:L56`, `vision/requirements/01_data_model.md:L621` `platform_settings.haitu_model`). **No Ollama mention anywhere in target or vision.**
- **Embeddings**: `all-MiniLM-L6-v2` planned as a sentence-transformers sidecar (`vision/requirements/00_overview.md:L145`); not deployed today.
- **PDF extraction in vision (deferred from target)**: `pdfplumber` for PDF, passthrough for text, LlamaIndex loaders, 600-char chunks with 100-char overlap, sentence-aware (`Implementation_planning/archive/rag-and-curriculum-decisions.md:L106-144`).
- **hAITU graceful degradation rule (BR-AI-010)** — `vision/requirements/08_haitu_ai_layer.md:L480-482` — already references `extraction_status`. Worth honouring even though full pgvector store is deferred.
- **No spec mentions** anywhere of: Ollama, LM Studio, GLM-OCR, smart PDF router, vision LLM for documents.

### 6.5 Auth + critical rules that affect this phase

- **BR-SEC-006**: `X-Current-Role` required; 400 if missing (`target/requirements/02_auth_and_roles.md:L113`).
- **CSRF on every mutation** (`L24-27`): `X-CSRF-Token` required for `POST/PUT/PATCH/DELETE`. Frontend uses `fetchWithCSRFRetry()` — see §11.5 caveat about `FormData`.
- **Admin-only writes for `owner_type='platform'`** (`L99`). `POST /api/topic-contents` was moved from instructor → admin in Phase 1a.
- **`topic_contents` inherits its parent topic's `owner_type`** (`vision/requirements/01_data_model.md:L253`, BR-CONTENT-004). No ownership columns on `topic_contents` itself.
- **Path traversal hardened** in `imageutil.py` and `topic_content.py` Phase 1a-fix — same pattern must apply to any new bytes-on-disk code.

### 6.6 Spec gaps the new phase must fill

| Spec | Status | Action |
|---|---|---|
| `target/requirements/12_content_extraction.md` | does not exist | **Create new** — pipeline, provider abstraction, PDF router, status lifecycle, BR-EXT-* rules |
| `target/requirements/01_data_model.md` topic_contents extension | columns dropped from target | **Add 6 fields back**: `text_extracted`, `extraction_status`, `extracted_at`, `extraction_provider`, `extraction_model`, `extraction_error` |
| `target/requirements/ui-mapping/ui_content_upload.md` | does not exist | **Create new** — admin upload modal UX (currently a stub button in prototype) |
| `target/prototypes/haisir_admin_flow.html` upload modal | stub | **Implement modal + status indicators** in the prototype HTML |
| `platform_settings` extension | not in target | Defer — for this phase, store LLM config in env (Pydantic Settings); document as "future admin-configurable" |

---

## 7. Phase 1b — Backend ground truth

### 7.1 DDD layout (per `haisir-backend/CLAUDE.md:L41-58`)

```
src/api/routes/         — thin FastAPI routers (HTTP only, deps, call services)
src/schemas/            — Pydantic DTOs
src/domain/models/      — plain dataclasses (no ORM)
src/domain/services/    — business logic
src/domain/repositories/— abstract repo interfaces
src/infrastructure/models/        — SQLAlchemy Table defs (imperative mapping)
src/infrastructure/repositories/  — concrete async repos
src/infrastructure/    — db.py, keycloak_admin.py, visibility.py
src/auth/              — user, permission, csrf
src/shared/            — config, file_validation, imageutil
```

**100% test coverage gate** (`pyproject.toml:L129`).

### 7.2 What exists vs what's missing for extraction

| Concern | Today | Action |
|---|---|---|
| Multipart upload | **Zero usage** of `UploadFile` in `src/` | NEW — but `python-multipart` already installed |
| File-bytes-to-disk | Only `imageutil.save_base64_image` (PNG/JPEG, base64) | NEW PDF/binary saver; reuse path-traversal guard |
| File validation | `validate_file_extension`, `validate_file_size`, magic-byte sniff (img only) | EXTEND for PDF magic bytes |
| Storage root | `settings.data_dir` (default `/app/datadir`), volume mount | REUSE |
| HTTP-to-LLM client | `httpx` installed but only used by `keycloak_admin.py` (with tenacity retry) | NEW LLM client; reuse tenacity pattern |
| Async LLM SDK | None | NEW — `ollama` SDK (AsyncClient) and/or raw httpx |
| Background tasks | **Zero usage** of `BackgroundTasks`, no Celery, no ARQ | DECIDE — see §10 Q1 |
| pgvector | Not installed; Postgres image is Chainguard (no pgvector ext) | OUT OF SCOPE this phase |
| Admin route pattern | `require_admin()` + `validate_csrf` deps | REUSE (`src/api/routes/topic_content.py:L140-174`) |
| Test pattern | pytest, AsyncMock + `dependency_overrides`, httpx AsyncClient | REUSE; need new LLM/extraction stubs |

### 7.3 Existing TopicContent code paths (cite exact files)

- Domain model: `src/domain/models/topic_content.py:L6-24`
- Table: `src/infrastructure/models/topic_content.py:L9-20`
- Repository: `src/infrastructure/repositories/topic_content_repository.py` (CRUD + visibility joins)
- Service: `src/domain/services/topic_content_service.py:L90-117` — `create()` synthesizes URL from `data_dir/topics/{type}/{filename}`, **no actual file I/O**
- Route: `src/api/routes/topic_content.py:L140-174` (POST), `:L76-137` (FileResponse with traversal guard at `:L135`)
- Schemas: `src/schemas/topic_content.py`

### 7.4 Frontend admin state

- `src/app/admin/` has only `boards/page.tsx` + layout + providers.
- `src/features/admin/components/` has ~40 files for boards/nodes/topics tree management.
- **Zero upload UI** — no `FormData`, no dropzone, no file input anywhere in `features/admin/`.
- `react-pdf` is in `package.json:L26` but only for client-side PDF rendering, not upload.
- API helper: `features/admin/api/admin-api.ts` uses `fetchWithCSRFRetry`. **Must verify it forwards `FormData` correctly** (currently designed for JSON).

### 7.5 Deploy / infrastructure today

`deploy/common/docker-compose.yml`: `db-init`, `db` (Chainguard Postgres, read-only fs), `backend`, `frontend`, `keycloak-db*`, `keycloak`, `etcd*`, `apisix`. **No Ollama, no pgvector, no LM Studio, no embedding sidecar.**

Backend container is `read_only: true` with a `haisir-backend-datadir` volume mount (`common/docker-compose.yml:L77-94`). Reusable for uploaded PDFs.

---

## 8. Phase 1c — `haiguru/glm_ocr` deep-dive

### 8.1 Module purpose & flow (`haiguru/glm_ocr/runner.py:L37-83`)

```
CLI → process_image() → get_optimized_image_b64() (PIL → JPEG q=95 → b64)
    → send_streamed_request(model, prompt, [image_b64])
    → stream aggregates ("__first_token__" / "chunk" / "__done__")
    → _strip_outer_code_fence() removes ```markdown fences
    → save_raw_response() writes outputs/{type}_outputs/raw_response_<img>.md
    → check_quality() prints heuristic warnings
```

- **Input formats**: `.jpg .jpeg .png .webp .bmp .tiff` + HTTP(S) URLs
- **Output**: plain Markdown (NOT JSON). Two shapes per the chosen prompt file
- **Model**: default `glm-ocr` (Ollama Modelfile `GLM-Config` configures `num_ctx=16384, num_predict=8192, temperature=0, top_p=0.00001, top_k=1, repeat_penalty=1.1`)
- **No JSON mode, no system prompt, no few-shot. Structure is "pinky promise"** — enforced post-hoc by `check_quality()` heuristics
- **No try/except, no retries, no timeouts** — request errors propagate raw
- A separate downstream pass (`etl_pipeline/llm_transform_exercises.py`) converts exercise Markdown → JSON

### 8.2 Client layer (`haiguru/glm_ocr/client.py`)

- Libs: `ollama` Python SDK (sync) + `openai` SDK (for LM Studio)
- Endpoints: Ollama default `http://localhost:11434` (native API); LM Studio `LMSTUDIO_BASE_URL` default `http://127.0.0.1:1234/v1` (OpenAI-compat Chat Completions)
- Auth: none for Ollama; LM Studio uses placeholder `api_key="lm-studio"`
- **LM Studio vs Ollama switch (commit `7fc5a42`)**: model-spec **prefix convention**. `lmstudio://<model>` → `_lmstudio_vision_stream()` (OpenAI-compat); plain `<model>` → `ollama.generate(images=[b64])`. Logic at `client.py:L40-43`.
- Sync generator (Python `yield`); streaming token-level; no asyncio anywhere

### 8.3 Provider switching (`haiguru/llm_factory.py:L29-65`)

`llm_factory.py` supports prefixes: `openai://`, `anthropic://`, `together://`, plain-name = Ollama. `glm_ocr/client.py` adds `lmstudio://`. Reranker factory adds Cohere/Jina.

**Env vars** (`config.py:L24-46`): `DATABASE_URL`, `EMBED_MODEL` (default `BAAI/bge-m3`), `RAG_MODEL/TRANSFORM_MODEL/EVAL_MODEL` (default `qwen3.5:9b`), `LMSTUDIO_BASE_URL`, plus optional API keys.

**Hosted Ollama Cloud is NOT wired today** — `ollama.Client(host=...)` is never set, so it defaults to `localhost:11434`. To support cloud Ollama: plumb `OLLAMA_HOST` env + `Authorization: Bearer $OLLAMA_API_KEY` header. The hosted API is byte-identical to local (per Ollama docs).

### 8.4 Image preprocessing (`client.py:L13-25`)

URL/path → `PIL.Image.open` → convert RGBA/P → RGB → JPEG q=95 → b64 encode. **No resize, no DPI normalization, no max-dimension clamp** — risk of OOM on very large images.

### 8.5 PDF handling — definitive truth

**Zero first-party PDF code in haiguru.** `pdf` only appears as a `content_type` enum literal. No `PyMuPDF`, `fitz`, `pdfplumber`, `pypdf`, `unstructured`, or `pdf2image` import anywhere. The pipeline assumes pre-extracted images on disk in `inputs/contents/*.jpg`. **Rasterizing a PDF is greenfield work in the backend.**

### 8.6 Content vs exercise branching

Two completely separate prompt files (`prompts/contents_prompt.md`, `prompts/exercises_prompt.md`) selected by CLI flag `--type {contents|exercises}`. **No classifier — the operator chooses upfront.** Output shapes are entirely different (H1/H2 headings vs `### QUESTION` blocks). A third prompt `answer_key_prompt.md` exists for answer-key OCR.

### 8.7 Dependencies to port

From `haiguru/pyproject.toml`, glm_ocr needs: `ollama>=0.6.1`, `openai>=1.0`, `anthropic>=0.25`, `pillow>=12.2.0`, `requests>=2.33.1`, `python-dotenv>=1.0`. **All permissive licenses, production-safe.** Drop everything else (torch, llama-index-*, phoenix, sqlalchemy/psycopg2/alembic — those belong to embed/rag/etl). Swap `requests` → `httpx` (async).

### 8.8 What to distill — recommendation

**Port as-is (after async conversion):**
1. The model-spec **prefix convention** (`lmstudio://`, plain=Ollama, `openai://`, `anthropic://`) — clean, testable, matches existing mental model.
2. **Streaming tuple protocol** (`__first_token__`, `chunk`, `__done__`) — useful for SSE to the frontend later.
3. The **two-prompt split** (content vs exercise) and external Markdown prompt files — keeps prompts reviewable/git-diffable.
4. The **`check_quality()` heuristics** — cheap server-side validation before commit.
5. **Image preprocessing pipeline** (RGB / JPEG q=95 / b64) — but add max-dimension clamp.

**Rebuild to production grade:**
1. Sync `ollama.generate` → **async** via `ollama.AsyncClient` or `httpx.AsyncClient`.
2. Add **tenacity retries** (exponential backoff) + per-request **timeouts** + circuit breaker.
3. Validate model output against a **Pydantic schema** (Ollama supports JSON mode via `format` parameter; use it).
4. **Structured logging** (structlog, already in backend deps) + OpenTelemetry spans per extraction.
5. **Pydantic Settings** config object — no `load_dotenv(override=True)` side effects.

**Do NOT port:**
- `load_dotenv(override=True)` at module import (`client.py:L10`) — test-hostile.
- `phoenix` / `openinference` tracers (R&D-only).
- The `GLM-Config` Modelfile baking — document it, but the backend shouldn't bundle Ollama Modelfiles into deployment.
- The filesystem-as-database pattern (`<topic>/inputs/.../outputs/...`).

---

## 9. Phase 1d — PDF tooling research (web, 2026)

### 9.1 PDF text extractor — comparison (sources: `py-pdf/benchmarks`, official docs)

| Library | Speed | Quality | License | Maintained 2026 | Verdict |
|---|---:|---:|---|---|---|
| **pypdfium2** | 0.1 s | 97 % | **Apache-2.0 OR BSD-3-Clause** | Yes | **RECOMMENDED** |
| PyMuPDF | 0.1 s | 96 % | **AGPL-3.0** or commercial | Yes | **AVOID** (license risk) |
| pypdf | 3.5 s | 96 % | BSD-3-Clause | Yes (v6.0.0 Aug 2025) | OK fallback |
| pdfminer.six | 5.8 s | 89 % | MIT | Yes | Slower, lower quality |
| pdfplumber | 9.5 s | 75 % text; **strong for tables** | MIT | Yes | Use for tables only |
| docling (IBM) | — | layout-aware | MIT | Yes (Aug 2025+) | Future option for structured docs |

**License posture (hard constraint):** AGPL libraries (PyMuPDF, marker) are **banned** from the FastAPI backend image unless a commercial license is procured first. AGPL §13 SaaS clause means serving the app over the network triggers the network-redistribution requirement — high legal risk.

**Recommendation:** **pypdfium2** as the primary PDF library — same library handles text extraction AND page rasterization. Add `pdfplumber` as an optional secondary path for table-heavy pages (gated behind a feature flag).

### 9.2 Native-text vs scanned detection — heuristic

No widely-used library helper exists. **Hand-rolled is the norm** (PyMuPDF Discussion #1653 + Quantrium.ai 2024 article):

```python
text = page.get_text("text").strip()
if len(text) < 50:
    return "scanned"
img_area = sum((r.x1 - r.x0) * (r.y1 - r.y0) for r in page.get_image_rects())
if img_area / (page.rect.width * page.rect.height) >= 0.95 and len(text) < 200:
    return "scanned"
return "native"
```

(For pypdfium2: `page.get_textpage().get_text_range()` + `page.get_objects()` are equivalent.)

### 9.3 Fallback path for scanned PDFs

`pypdfium2.PdfPage.render(scale=2.0).to_pil()` → JPEG q=95 → b64 → glm_ocr (vision LLM). One library covers both extraction and rasterization → fewer deps, no Poppler system package, no `pdf2image`.

### 9.4 Ollama in production (sources: docs.ollama.com, ollama.com/cloud)

- **Ollama Cloud** launched September 2025. Pricing: Pro $20/mo, Max $100/mo. Ollama Turbo ($20/mo) runs `gpt-oss:20b` and `gpt-oss:120b` in datacenter.
- **API surface is byte-identical to local Ollama** — same `/api/generate`, `/api/chat`, `/api/embeddings`, plus OpenAI-compat `/v1/chat/completions` and `/v1/embeddings`.
- **Switch via SDK**: `ollama.AsyncClient(host="https://ollama.com", headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"})`. Local: `host="http://localhost:11434"`. **Same code, different env vars.**
- **Caveat**: confirm vision-capable models exist in the cloud catalog. `gpt-oss` is text-only; vision models still need local Ollama or a different cloud vision model. The choice of cloud vision model is **an open architectural question** — does the team accept "vision = local-only", or pick a hosted vision model (e.g., Anthropic via `anthropic://` prefix as a vision fallback)?

### 9.5 Defensible defaults (recommended for the plan)

| Concern | Default | Escape hatch |
|---|---|---|
| PDF text extraction | `pypdfium2` | `pdfplumber` if `enable_table_mode=true` |
| PDF rasterization (scanned) | `pypdfium2.PdfPage.render(scale=2.0).to_pil()` | — |
| Native vs scanned detection | Inline `classify_page()` with two-check heuristic above | Per-tenant `force_ocr=true` override |
| Vision model | `glm-ocr` via local Ollama | Configurable via `EXTRACTION_VISION_MODEL` env |
| LLM provider | Model-spec prefix (plain=Ollama, `lmstudio://`, `openai://`, `anthropic://`) — same as haiguru | `OLLAMA_HOST` env to point Ollama SDK at local or cloud |
| Cloud Ollama auth | `Authorization: Bearer $OLLAMA_API_KEY` header | — |
| Dep bundle | `ollama`, `pypdfium2`, `pillow`, `tenacity`, `pydantic-settings` (existing) | `pdfplumber`, `openai`, `anthropic` optional extras |
| License posture | Permissive only (Apache/BSD/MIT) | AGPL libs **banned** in backend image |

---

## 10. Architectural decisions awaiting team input

These five questions block the next `/plan` invocation from decomposing the work into a goal tree. Each has a **strawman default** I recommend; the team can override.

### Q1. Execution model for extraction (load-bearing)

A long-running LLM extraction (potentially minutes for large PDFs) doesn't fit a sync HTTP request. Options:

| Option | Pros | Cons |
|---|---|---|
| **(a) Synchronous with hard page-count cap** (e.g., max 20 pages, max 5 MB) | Simple. No new infra. Same code path local & prod. Forces realistic batching. | Caller waits 30–120s on max-size uploads. Doesn't scale to large textbooks. |
| **(b) FastAPI `BackgroundTasks`** | No new infra. Returns 202 fast. | Tasks die on worker restart with no retry; no visibility; in-process only. Challenger flagged this as "wrong primitive — torn out within one phase". |
| **(c) Add ARQ + Redis now** | Real queue, retries, observability, dead-letter. Future-proof. | New infra (Redis container in compose). Scope creep for this phase. |
| **(d) Hybrid: sync API + extraction-worker module that's swappable** | API contract stable; impl can be sync now, queue later. | Demands clean abstraction that survives the swap. |

**My recommended default: (a) Synchronous with page-count cap (≤ 10 pages or ≤ 5 MB), and design the `ExtractionService` interface so a future queue can drop in without API change.** Returns 200 with the completed extraction. For larger uploads, return 413 with a "split your PDF" message. This is the smallest scope that ships honestly.

**Open team question**: Is a 10-page-per-upload cap acceptable for platform admin content? If most NCERT chapters are 30+ pages, the cap is too aggressive and we should pick (c) ARQ + Redis instead.

### Q2. Byte storage target

Where do uploaded PDFs/images live?

| Option | Pros | Cons |
|---|---|---|
| **(a) Local disk under `settings.data_dir`** (current pattern) | Same as existing `topic_contents` URL convention; no new infra; volume already mounted | Not horizontally scalable; no cross-node replication |
| **(b) MinIO container in compose, S3 SDK in code** | Production-ready; same code in dev (MinIO) and prod (S3-compat) | New service in compose; new dep (`boto3` or `aioboto3`) |
| **(c) Postgres `BYTEA`** | Single source of truth; transactional with metadata | Painful for files > 5 MB; bloats DB |

**My recommended default: (a) local disk** with the existing path traversal guard pattern. Migrate to MinIO when we have a multi-node deploy need.

### Q3. LLM output contract — JSON mode vs Markdown

| Option | Pros | Cons |
|---|---|---|
| **(a) JSON mode via Ollama `format` param + Pydantic validation** | Production-grade; deterministic shape; validation errors are clean | Some open models follow JSON mode poorly; needs schema-repair retry path |
| **(b) Markdown output (haiguru-style) + post-hoc parser** | Simpler; matches what glm-ocr was trained for | Brittle; structure drift across model versions |
| **(c) Two-pass: vision LLM → Markdown; small text LLM → JSON normalize (haiguru pattern)** | Decouples concerns; can swap vision model | Doubles LLM cost per upload |

**My recommended default: (a) JSON mode with Pydantic schema and one repair retry.** If the chosen vision model doesn't honor JSON mode well, fall back to (c) but document it. **Open team question**: which Ollama vision model are we standardizing on for the platform? `glm-ocr`? `minicpm-v`? `llama3.2-vision`? This affects JSON-mode reliability significantly.

### Q4. Content vs exercise — classification source

| Option | Pros | Cons |
|---|---|---|
| **(a) Admin picks `content_type` upfront in upload modal**, server picks the prompt | Matches existing `topic_contents.content_type` enum; admin already knows what they're uploading | Still need a sub-classifier inside "content" for question/answer-key sub-types? |
| **(b) Single prompt with classification field in JSON output** | One LLM call; auto-detects | More tokens per call; more failure modes |
| **(c) Two LLM calls (classify, then extract with the right prompt)** | Pure separation | Doubles cost & latency |

**My recommended default: (a) admin picks upfront.** The upload modal already shows `content_type` chips for the existing schema enum (`pdf`, `video`, `text`, `question`, `question_answer`). Map those to prompt files. Keeps the classifier out of the LLM critical path entirely.

### Q5. Multi-page PDF representation

| Option | Pros | Cons |
|---|---|---|
| **(a) One `topic_contents` row per upload**; `text_extracted` = concatenated; per-page structure in `metadata_json` | Simple polling; matches user mental model ("my PDF") | Coarse status (one PDF = pass/fail); no per-page retry |
| **(b) One row per page** with parent FK | Per-page retry; granular status | Schema change; UI lists 30 rows per PDF; aggregation overhead |
| **(c) One row per upload + a child `extraction_pages` table** | Best of both | Most schema work |

**My recommended default: (a) one row per upload + `metadata_json` for per-page structure.** Defer (c) to the pgvector phase where chunking demands per-page boundaries anyway.

---

## 11. Cross-repo footprint preview (assuming Option 1 + recommended defaults)

### 11.1 `haisir-specs` (new spec writes)
- `target/requirements/12_content_extraction.md` — **new**
- `target/requirements/01_data_model.md` — append `topic_contents` extension section
- `target/requirements/ui-mapping/ui_content_upload.md` — **new**
- `target/prototypes/haisir_admin_flow.html` — flesh out upload modal + status pills
- `Implementation_planning/phases.md` — insert "1d-pre" before "1d"
- `Implementation_planning/decisions.md` — record the 5 architectural decisions
- `CLAUDE.md` — add note about `pypdfium2` choice + AGPL ban

### 11.2 `haisir-backend` (new code)
- `src/domain/services/content_extraction/` (new package): `extraction_service.py`, `pdf_router.py`, `pdf_text_extractor.py`, `pdf_rasterizer.py`, `vision_ocr_extractor.py`, `prompts/contents_prompt.md`, `prompts/exercises_prompt.md`
- `src/infrastructure/llm/` (new package): `llm_provider.py` (prefix dispatch), `ollama_provider.py`, `lmstudio_provider.py`, optional `openai_provider.py`/`anthropic_provider.py` stubs
- `src/api/routes/content_extraction.py` (or extend `topic_content.py`): `POST /api/topic-contents/upload` (multipart) + `GET /api/topic-contents/{id}/extraction`
- `src/schemas/content_extraction.py`: Pydantic models for the JSON-mode LLM output + status response
- `src/infrastructure/models/topic_content.py` + domain dataclass: 6 new columns
- New Alembic migration `V26_topic_contents_extraction_columns.py`
- `src/shared/config.py`: new `ExtractionSettings` nested block (`OLLAMA_HOST`, `OLLAMA_API_KEY`, `LMSTUDIO_BASE_URL`, `EXTRACTION_VISION_MODEL`, `EXTRACTION_MAX_PAGES`, `EXTRACTION_MAX_BYTES`)
- `src/shared/file_validation.py`: PDF magic-byte sniffing
- `tests/unit/services/test_content_extraction.py` + LLM stub helpers in `tests/conftest.py`
- `pyproject.toml`: add `ollama`, `pypdfium2`; optional extras `pdfplumber`, `openai`, `anthropic`

### 11.3 `haisir-frontend` (Phase 1d, but doc only this phase)
- Document the new upload endpoints in `features/admin/api/admin-api.ts` (no impl yet — Phase 1d builds the UI)
- **Verify `fetchWithCSRFRetry()` handles `FormData`** (challenger flagged this) — patch if not

### 11.4 `haisir-deploy` (optional)
- Add Ollama service to `deploy/dev/docker-compose.yml` (commented out by default; opt-in via profile or env)
- Document the production env vars (`OLLAMA_HOST`, `OLLAMA_API_KEY`) in `deploy/staging/*.env.example`

### 11.5 Frontend `FormData` + CSRF caveat (open verification item)
Today's `fetchWithCSRFRetry()` was designed for JSON. Verify it does NOT set `Content-Type: application/json` when a `FormData` body is passed (browsers must set the multipart boundary themselves). If it does, that's a one-liner fix that must land before the 1d UI work begins.

---

## 12. Critical rules to honour (from `haisir-specs/CLAUDE.md`)

These are non-negotiable for any code in the new phase:

- **APISIX injects the JWT** — no Bearer token from the client.
- **`X-Current-Role: admin`** required on the upload endpoint; missing header → 400. CSRF (`X-CSRF-Token`) on every mutation.
- **No local users table** — owner/admin attribution by Keycloak `sub` UUID string.
- **Existing schema is sacred** — only ADD columns to `topic_contents`; never drop or rename.
- **`owner_type` ownership rule** — `topic_contents` inherits from parent `topics.owner_type` (BR-CONTENT-004). No new ownership column.
- **DDD layering** — no business logic in route files. ExtractionService is in `domain/services/`; Ollama HTTP client is in `infrastructure/llm/`.
- **SQLAlchemy imperative mapping** — domain models are plain dataclasses; new columns go in BOTH the dataclass AND the `infrastructure/models/topic_content.py` Table.
- **Path traversal hardened** — any new disk write must `Path.resolve().relative_to(settings.data_dir)`.
- **100% test coverage** — LLM client must be stubbable; rasterization must be testable without a GPU.

---

## 13. Risks & open unknowns the team should weigh

| Risk | Severity | Notes |
|---|---|---|
| AGPL exposure if anyone reaches for PyMuPDF | High | Document the ban in `CLAUDE.md`; lint via `pip-licenses` in CI |
| BackgroundTasks footgun | Medium | If team picks Q1(b) over my (a) recommendation, design for queue migration from day one |
| Vision model in cloud Ollama | Medium | If `glm-ocr` isn't on Ollama Cloud's catalog, vision is effectively local-only — affects production deploy story |
| Large PDF OOM | Medium | Page cap (Q1(a)) is the simplest mitigation; Q5(b/c) helps too |
| LLM JSON mode reliability | Medium | Some open models drift from declared schemas; keep schema-repair retry |
| Frontend `FormData` + CSRF interaction | Low | One-line fix likely; verify before 1d UI work |
| 100% coverage on streaming generators | Low | LLM stubs need to yield the same `(__first_token__, chunk, __done__)` tuples |
| Ollama service dependency in dev compose | Low | Make it opt-in (profile) — devs without GPUs shouldn't be blocked |

---

## 14. Sources & references

### Spec files cited (haisir-specs)
- `target/requirements/01_data_model.md`, `02_auth_and_roles.md`, `05_06_07_personas.md`
- `target/requirements/ui-mapping/ui_parent_institution_admin.md` (L208 upload row, L90-97 status states)
- `target/prototypes/haisir_admin_flow.html` (L585-600 upload stub)
- `vision/requirements/01_data_model.md` (L849-866 deferred extraction columns; L870-907 deferred chunks table)
- `vision/requirements/00_overview.md` (L56 Claude default; L134-137 storage; L145 embedding model; L147-149 pgvector usage)
- `vision/requirements/08_haitu_ai_layer.md` (L480-482 BR-AI-010 graceful degradation)
- `current/schema.md` (L110-118 topic_contents)
- `current/api_contracts.md` (L197-215 topic-contents endpoints)
- `Implementation_planning/archive/rag-and-curriculum-decisions.md` (L106-144 PDF pipeline)
- `Implementation_planning/archive/phase1d-plan-stub_2026-04-16.md` (the stub that was archived this session)

### Backend files cited (haisir-backend)
- `CLAUDE.md` (L41-58 DDD layout, L129 coverage gate)
- `src/domain/models/topic_content.py:L6-24`
- `src/infrastructure/models/topic_content.py:L9-20`
- `src/api/routes/topic_content.py:L28-44, L47-73, L76-137, L140-174`
- `src/domain/services/topic_content_service.py:L90-117`
- `src/infrastructure/repositories/topic_content_repository.py`
- `src/shared/imageutil.py:L14-61, L81-84`
- `src/shared/file_validation.py:L16-50, L232-246`
- `src/shared/config.py:L123-131, L195`
- `src/auth/permission.py:L67-69`, `src/auth/csrf.py:L39-50`
- `src/infrastructure/keycloak_admin.py:L86, L134, L180` (tenacity + httpx pattern reference)
- `pyproject.toml:L7-27, L129`

### Frontend files cited (haisir-frontend)
- `src/app/admin/`, `src/features/admin/components/`
- `src/features/admin/api/admin-api.ts`
- `package.json:L13, L26`

### Deploy files cited (haisir-deploy)
- `common/docker-compose.yml:L77-94`
- `dev/docker-compose.yml`

### Haiguru files cited
- `glm_ocr/runner.py:L8, L37-83`
- `glm_ocr/client.py:L10, L13-25, L40-43, L47-67, L80, L174`
- `glm_ocr/utils.py:L16, L24-55`
- `glm_ocr/__main__.py:L11-12`
- `llm_factory.py:L29-65`
- `config.py:L24-46`
- `GLM-Config` (Modelfile)
- `etl_pipeline/__main__.py:L110-113`, `etl_pipeline/llm_transform_exercises.py`, `etl_pipeline/transform.py:L43-54`
- `prompts/contents_prompt.md`, `prompts/exercises_prompt.md`, `prompts/answer_key_prompt.md`
- `pyproject.toml`
- Latest commit: `7fc5a42` (LM Studio support)

### External research sources
- py-pdf benchmarks — https://github.com/py-pdf/benchmarks
- pypdfium2 — https://pypi.org/project/pypdfium2/ , https://github.com/pypdfium2-team/pypdfium2 , https://pypdfium2.readthedocs.io/
- pypdf 6.0.0 — https://github.com/py-pdf/pypdf/releases/tag/6.0.0
- PyMuPDF licensing — https://pymupdf.readthedocs.io/en/latest/about.html , https://artifex.com/licensing
- PyMuPDF Discussion #1653 (scanned-PDF detection) — https://github.com/pymupdf/PyMuPDF/discussions/1653
- Artifex blog on text-extraction strategies — https://artifex.com/blog/text-extraction-strategies-with-pymupdf
- Quantrium.ai article on text-vs-image PDFs — https://medium.com/quantrium-tech/identifying-text-based-and-image-based-pdfs-using-python-10dba29a02b4
- Docling — https://github.com/docling-project/docling , https://research.ibm.com/blog/docling-generative-AI
- Ollama Cloud — https://ollama.com/cloud , https://docs.ollama.com/cloud
- Ollama pricing — https://www.ollama.com/pricing
- Ollama OpenAI compatibility — https://docs.ollama.com/api/openai-compatibility

---

## 15. Recommended next steps

1. **Team reviews this brief** and answers the 5 questions in §10. (15–30 min sync ideal.)
2. **Capture answers** in `Implementation_planning/decisions.md` as a dated entry headed `2026-04-?? — Phase 1d-pre architectural decisions`.
3. **Re-invoke `/plan`** in `haisir-specs` referencing this brief — Phase 0 detects the clean slate; Phase 2 picks Option 1 (or whichever the team chose); Phase 3 decomposes with the resolved scope.
4. **Plan subagent writes** `target/requirements/12_content_extraction.md` as a planned task (not part of this brief) — that becomes the authoritative spec the backend implements against.
5. **PLAN.md + TASKS.md** get written by `/plan` Phase 6 with the SHA watermark for the new baseline.
6. After PLAN.md exists, switch to `haisir-backend` and run `/implement` against the ready-now tasks.

---

## 16. Suggested phase naming

To keep ordering clear in `Implementation_planning/phases.md`:

| Order | Sub-phase | Status | Scope |
|---|---|---|---|
| ... | 1c-post ✓ | done | Admin UX alignment (last completed) |
| **next** | **1d-pre — Content Extraction Service** | **PROPOSED** | This phase |
| then | 1d — Topic Content Upload UI | shifted | Multipart UI + PATCH/DELETE + polling |
| later | 1e (or 2x) — pgvector + RAG chunk store | deferred | Embedding sidecar + chunker + `topic_content_chunks` table |

Alternative names if `1d-pre` reads awkwardly: `1c2-content-extraction`, `1d-foundation`, `1d-backend`.

---

*End of brief. Ping me with answers to §10 and I'll re-enter `/plan` Phase 3 to decompose.*
