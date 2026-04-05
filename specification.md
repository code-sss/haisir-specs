# Agentic RAG Service — Full Build Specification

> **Purpose**: This document is a self-contained specification for building an agentic RAG (Retrieval-Augmented Generation) service from scratch. It is designed to be handed to a Claude Code session with zero prior context. Every architectural decision, data format, schema, API contract, and tool definition is specified here.
>
> **Deployment model**: **Standalone-first.** Built as an independent service with its own database and full `STUB_MODE` bypass for auth, CSRF, and ownership. Integration into hAIsir requires configuration changes only (`DATABASE_URL` + `STUB_MODE=False`) — no code or schema changes. All tables are `rag_`-prefixed and designed to coexist in hAIsir's Postgres cleanly. `rag_chunks` supersedes the planned `topic_content_chunks` table in hAIsir's schema (see section 16).

---

## 1. System Overview

An **educational content assistant** that answers questions about study materials. It uses an **agentic RAG** pattern: the LLM (Claude) autonomously decides whether and what to retrieve, rather than following a fixed retrieve-then-generate pipeline.

### Core Flow

```
User asks question
  → Frontend streams request via SSE
    → FastAPI backend receives query
      → Anthropic Claude (with tool definitions) decides:
          a) Answer directly (no retrieval needed), OR
          b) Call search_content tool (one or more times)
      → If tools called: execute tools → return results to Claude → Claude synthesizes
    → Stream response tokens back to frontend in real-time
  → User sees answer token-by-token with source citations
```

### What Makes This "Agentic"

- Claude decides **if** retrieval is needed (general knowledge questions get direct answers)
- Claude decides **what** to search for (constructs query and filters autonomously)
- Claude can call **multiple tools** in sequence (up to a configurable round budget)
- Claude **synthesizes** results — it doesn't just pass through retrieved text

---

## 2. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | Next.js 14+ App Router (TypeScript) | SSE streaming, dev stub UI |
| **Backend** | FastAPI (Python 3.11+) | Async, SSE support, auto-generated OpenAPI docs |
| **LLM (Primary)** | Anthropic Claude (`claude-sonnet-4-6`) via `anthropic` Python SDK | Native tool_use, streaming, highest quality |
| **LLM (Local/Fallback)** | `qwen3-8b` via Ollama (`ollama/qwen3-8b`) | Offline capable, zero API cost, privacy-first option |
| **LLM Router** | Configurable in `config.py` — `LLM_PROVIDER: "anthropic" | "ollama"` | Switch between cloud and local without code changes |
| **Database** | PostgreSQL 16+ with `pgvector` and `pg_trgm` extensions | Single DB for vectors, full-text search, conversations |
| **Embeddings** | `BAAI/bge-m3` (1024-dim, local via `sentence-transformers` or FlagEmbedding) | State-of-the-art multilingual, dense+sparse in one model |
| **Retrieval** | Raw SQL via asyncpg (vector cosine + tsvector BM25 + RRF fusion) | Full control, no ORM/framework overhead |
| **Local Model Server** | Ollama | Manages local model lifecycle, OpenAI-compatible API |
| **Package Manager** | `uv` for Python, `npm` for Node.js | Fast, deterministic |

### Key Dependencies

**Python (backend)**:
```
anthropic
fastapi
uvicorn[standard]
sse-starlette
asyncpg
pgvector
FlagEmbedding
sentence-transformers
ollama
httpx
python-dotenv
pydantic
pydantic-settings
```

**Node.js (frontend — dev stub only)**:
```
next
react
react-dom
react-markdown
typescript
@types/react
@types/node
tailwindcss
```

---

## 3. Project Structure

```
project-root/
├── backend/
│   ├── app.py                  # FastAPI app, SSE endpoint, startup/shutdown
│   ├── config.py               # All configuration (env vars + defaults)
│   ├── models.py               # Pydantic models (Chunk, Conversation, Message, etc.)
│   ├── database.py             # asyncpg connection pool, schema creation
│   ├── auth.py                 # JWT extraction / STUB_MODE bypass
│   ├── llm_client.py           # LLM abstraction: Anthropic vs Ollama routing
│   ├── ingestion.py            # Chunking, embedding, DB upsert (called by ingest endpoint)
│   ├── retrieval.py            # Hybrid search (vector + BM25 + RRF) with ownership scoping
│   ├── tools.py                # Tool definitions + execution (search_content)
│   ├── agent.py                # Streaming tool loop (Anthropic) / generate loop (Ollama)
│   ├── conversations.py        # Conversation + message persistence (Postgres)
│   ├── pyproject.toml          # Python dependencies (uv)
│   └── tests/
│       ├── conftest.py
│       ├── test_api.py
│       ├── test_tools.py
│       └── test_ingestion.py
├── frontend/                   # Dev stub — not for production
│   ├── src/
│   │   └── app/
│   │       ├── layout.tsx
│   │       ├── page.tsx        # Chat UI + debug panels
│   │       └── components/
│   │           ├── ChatWindow.tsx
│   │           ├── MessageBubble.tsx
│   │           ├── SourceCard.tsx
│   │           ├── InputBar.tsx
│   │           ├── IngestForm.tsx       # Manual ingest form
│   │           ├── ChunkInspector.tsx   # Browse/search chunks
│   │           └── DebugPanel.tsx       # Raw SSE event viewer
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.ts
├── scripts/
│   └── seed_from_files.py      # Dev script: parse txt files → POST /api/rag/ingest
├── docs/                       # Sample content files (for standalone testing)
│   └── sample_content.txt
├── .env.example
├── docker-compose.yml          # Postgres with pgvector
├── run.sh                      # Dev startup script
└── CLAUDE.md
```

---

## 4. Database Schema

Use PostgreSQL with `pgvector` extension. All tables are `rag_`-prefixed to coexist with other services in the same database. All tables created on app startup via `database.py`.

### Connection Pool (`database.py`)

`database.py` manages a global `asyncpg.Pool` with the following lifecycle:

```python
import asyncpg

_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    """Return the global connection pool (create on first call)."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=2,
            max_size=10,
        )
        async with _pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        await _create_schema(_pool)
    return _pool

async def close_pool():
    """Called on FastAPI shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
```

**How modules get DB access**: All modules (`tools.py`, `conversations.py`, `retrieval.py`, `agent.py`) call `await get_pool()` to obtain the pool, then `pool.acquire()` for individual connections. No DI framework needed.

FastAPI wires it in `app.py`:
```python
@app.on_event("startup")
async def startup():
    await get_pool()  # Creates pool + schema

@app.on_event("shutdown")
async def shutdown():
    await close_pool()
```

### Schema

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Chunks table (main retrieval target)
-- Content arrives via the ingest endpoint. Soft-references the source system.
CREATE TABLE IF NOT EXISTS rag_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL,
    source_table    TEXT NOT NULL,
    owner_type      TEXT NOT NULL DEFAULT 'platform',
    owner_id        TEXT,
    source_title    TEXT,
    metadata        JSONB DEFAULT '{}',
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    embedding       VECTOR(1024),
    tsv             TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Conversations table (groups messages into threads)
CREATE TABLE IF NOT EXISTS rag_conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT NOT NULL,
    title       TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS rag_chat_messages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id   UUID NOT NULL REFERENCES rag_conversations(id) ON DELETE CASCADE,
    role              TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content           TEXT NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding ON rag_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_tsv ON rag_chunks USING gin (tsv);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_source ON rag_chunks (source_id);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_owner ON rag_chunks (owner_type, owner_id);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata ON rag_chunks USING gin (metadata);

CREATE INDEX IF NOT EXISTS idx_rag_conversations_user ON rag_conversations (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_chat_messages_conversation ON rag_chat_messages (conversation_id, created_at);
```

### Column Reference

**`rag_chunks`**:

| Column | Type | Notes |
|---|---|---|
| `source_id` | UUID | ID of the content in the source system (e.g., a topic ID, exam template ID). No FK constraint — soft reference. |
| `source_table` | TEXT | Source table name. Expected values: `'topics'`, `'topic_contents'`, `'exam_templates'`. Extensible. |
| `owner_type` | TEXT | `'platform'` (platform-managed content) or `'parent'` (parent-created private content). |
| `owner_id` | TEXT | `NULL` for platform content. Parent's `idp_sub` (UUID as string) for parent-created content. Matches hAIsir's `owner_id TEXT` convention — do not use UUID type. |
| `source_title` | TEXT | Cached display title from the source system. Refreshed on content update via ingest webhook. |
| `metadata` | JSONB | Caller-provided structured data. Stored as-is. Used for filtering and enriching citations. Expected keys vary by source — see section 6.1. |
| `chunk_index` | INTEGER | Ordering within a source document. |
| `content` | TEXT | The chunk text. |
| `embedding` | VECTOR(1024) | BGE-M3 dense embedding. |
| `tsv` | TSVECTOR | Auto-generated from `content` for BM25 full-text search. |

**`rag_conversations`**:

| Column | Type | Notes |
|---|---|---|
| `user_id` | TEXT | User identifier. In STUB_MODE: `STUB_USER_ID`. In production: `idp_sub` from JWT. |
| `title` | TEXT | Optional conversation title. Can be auto-generated from the first message. |

**`rag_chat_messages`**:

| Column | Type | Notes |
|---|---|---|
| `conversation_id` | UUID | FK to `rag_conversations`. |
| `role` | TEXT | `'user'` or `'assistant'`. |
| `content` | TEXT | Message text. |

---

## 5. Configuration (`backend/config.py`)

Use `pydantic-settings` `BaseSettings` to load from environment with defaults:

```python
class Settings(BaseSettings):
    # --- Mode ---
    STUB_MODE: bool = True  # True = standalone dev, False = behind APISIX with JWT

    # Stub-mode identity (used when STUB_MODE=True)
    STUB_USER_ID: str = "dev-user-001"
    STUB_USER_ROLE: str = "student"

    # --- LLM Provider ("anthropic" or "ollama") ---
    LLM_PROVIDER: str = "anthropic"

    # Anthropic (used when LLM_PROVIDER == "anthropic")
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # Ollama (used when LLM_PROVIDER == "ollama")
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3-8b"

    # Shared LLM settings
    MAX_TOKENS: int = 1024
    TEMPERATURE: float = 0

    # --- Database ---
    DATABASE_URL: str = "postgresql://raguser:ragpass@localhost:5432/ragdb"

    # --- Embeddings ---
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 1024

    # --- Chunking ---
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # --- Retrieval ---
    MAX_SEARCH_RESULTS: int = 5
    SIMILARITY_CUTOFF: float = 0.3

    # --- Agent ---
    MAX_TOOL_ROUNDS: int = 3
    MAX_CONVERSATION_HISTORY: int = 10  # Messages to load from DB

    # --- Ingest auth ---
    WEBHOOK_SECRET: str = "dev-secret"  # HMAC secret for ingest endpoint

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

### `.env.example`
```
# Mode: True for standalone dev, False for hAIsir integration
STUB_MODE=true
STUB_USER_ID=dev-user-001
STUB_USER_ROLE=student

# LLM_PROVIDER=anthropic (default) or LLM_PROVIDER=ollama
ANTHROPIC_API_KEY=sk-ant-...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-8b

DATABASE_URL=postgresql://raguser:ragpass@localhost:5432/ragdb

# HMAC secret for ingest endpoint
WEBHOOK_SECRET=dev-secret
```

### 5.1 STUB_MODE Behavior

When `STUB_MODE=True` (default — standalone development):

| Concern | Behavior |
|---|---|
| **Auth** | Skip JWT extraction. Use `STUB_USER_ID` and `STUB_USER_ROLE` as the current user identity. |
| **CSRF** | Disabled. No `X-CSRF-Token` required on mutations. |
| **Ownership scoping** | Bypassed. All chunks are visible regardless of `owner_type`/`owner_id`. |
| **HMAC validation** | Skipped on ingest endpoint. Any caller can ingest. |

When `STUB_MODE=False` (hAIsir integration):

| Concern | Behavior |
|---|---|
| **Auth** | Extract `idp_sub` from APISIX-injected `Authorization: Bearer <JWT>`. Require `X-Current-Role` header (`student` or `parent`). |
| **CSRF** | Required. `X-CSRF-Token` on all mutations. |
| **Ownership scoping** | Applied. Query filters by `owner_type`/`owner_id` based on user role (see section 7.2). |
| **HMAC validation** | Required. Ingest requests must include valid `X-Webhook-Signature` header. |

### 5.2 LLM Client Abstraction (`backend/llm_client.py`)

The system supports two LLM backends, selected by `LLM_PROVIDER` in config. Both expose the same interface so the rest of the codebase doesn't care which is active.

```python
# llm_client.py — unified interface for Anthropic and Ollama

async def create_streaming_response(messages, tools, system_prompt):
    """
    Routes to the active provider. Returns an async iterator of events
    with the same shape regardless of backend:
      - {"type": "text_delta", "text": "..."}
      - {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
      - {"type": "message_complete", "stop_reason": "end_turn"|"tool_use", "content": [...]}
    """
    if settings.LLM_PROVIDER == "anthropic":
        return _stream_anthropic(messages, tools, system_prompt)
    elif settings.LLM_PROVIDER == "ollama":
        return _stream_ollama(messages, tools, system_prompt)

async def generate_simple(prompt: str, system: str = "") -> str:
    """Non-streaming single-shot generation (used for ingestion enrichment)."""
    ...
```

**Anthropic backend**: Uses the `anthropic` Python SDK with native `tool_use` and streaming as specified in section 9.

**Ollama backend**: Uses the Ollama Python client or raw HTTP to `http://localhost:11434/api/chat`. Ollama supports tool calling for Qwen3 models — tool definitions are passed in the OpenAI-compatible format. The `_stream_ollama` function normalizes Ollama's streaming chunks into the same event shape as Anthropic.

**Important**: When using Ollama, tool calling quality depends on the model. Qwen3-8B supports function calling but may need more explicit tool descriptions than Claude. The system prompt should be slightly more directive for Ollama (e.g., "You MUST call a tool if the question is about course content. Never guess.").

**Ollama setup prerequisite**:
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model (one-time, ~5GB download)
ollama pull qwen3-8b
```

---

## 6. Ingestion

Content enters the system via the `POST /api/rag/ingest` endpoint. There is no file-based ingestion built into the service itself — a dev script (`scripts/seed_from_files.py`) handles parsing text files and calling the ingest endpoint for standalone testing.

### 6.1 Ingest Endpoint

`POST /api/rag/ingest` — accepts content from the source system (or dev script) and chunks → embeds → upserts into `rag_chunks`.

**Request body**:
```json
{
  "event": "created | updated | deleted",
  "source_id": "uuid",
  "source_table": "topics | topic_contents | exam_templates",
  "owner_type": "platform | parent",
  "owner_id": "uuid-or-null",
  "source_title": "Display title for citations",
  "content": "The full text content to chunk and embed",
  "metadata": {
    "board": "CBSE",
    "grade": "10",
    "subject": "Mathematics",
    "node_path": ["CBSE", "Class 10", "Mathematics", "Algebra"],
    "difficulty": "intermediate",
    "tags": ["quadratic-equations", "polynomials"]
  }
}
```

The `metadata` field is optional (defaults to `{}`). It is stored as-is on every chunk created from this content. The caller decides what keys to include — the RAG service treats it as opaque JSONB except for filtering in `search_content`.

**Expected metadata keys by source** (convention, not enforced):

| Key | Type | Description |
|---|---|---|
| `board` | string | Education board (e.g., `"CBSE"`, `"ICSE"`, `"State"`) |
| `grade` | string | Grade/class level (e.g., `"10"`, `"12"`) |
| `subject` | string | Subject name (e.g., `"Mathematics"`, `"Physics"`) |
| `node_path` | string[] | Full hierarchy path from the content tree |
| `difficulty` | string | `"beginner"` / `"intermediate"` / `"advanced"` |
| `tags` | string[] | Freeform topic tags |

**Headers**:
- `X-Webhook-Signature: sha256=<hmac_hex>` — HMAC-SHA256 of the raw request body using `WEBHOOK_SECRET`. Skipped in STUB_MODE.

**Behavior by event type**:

| Event | Action |
|---|---|
| `created` | Chunk `content` → embed each chunk → INSERT into `rag_chunks` |
| `updated` | DELETE existing chunks for `source_id` → re-chunk → re-embed → INSERT |
| `deleted` | DELETE all chunks WHERE `source_id = $1` |

**Response**: `200 {"status": "ok", "chunks_created": N}` or `200 {"status": "ok", "chunks_deleted": N}`

### 6.2 Chunking Algorithm

Split on sentence boundaries, accumulate up to `CHUNK_SIZE` (1000 chars), overlap last sentences up to `CHUNK_OVERLAP` (150 chars).

**Sentence boundary regex**: `(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+(?=[A-Z])`

**Code block preservation**: If a chunk boundary falls inside a fenced code block (`` ``` `` or `~~~`), extend the chunk to include the full code block rather than splitting mid-code.

Each chunk is stored with:
- `source_id`, `source_table`, `owner_type`, `owner_id`, `source_title`, `metadata` — copied from the ingest request
- `chunk_index` — sequential within the source document (0-based)
- `content` — the chunk text
- `embedding` — BGE-M3 1024-dim dense vector

### 6.3 Dev Seed Script (`scripts/seed_from_files.py`)

A standalone Python script for seeding content during development. Parses text files from `docs/` and calls `POST /api/rag/ingest` for each document.

**Input document format** (plain text files in `docs/`):
```
Title: Introduction to Algebra
Source-Table: topics
Board: CBSE
Grade: 10
Subject: Mathematics
Tags: quadratic-equations, polynomials

Content begins here after the blank line.

This is the actual text that will be chunked and embedded...
```

**Parsing rules**:
- Line 1: `Title: <title>` (required)
- Line 2: `Source-Table: <table>` (optional, defaults to `topics`)
- Lines 3+: `Key: value` headers (optional) — parsed into the `metadata` JSONB field. `Tags` is split on commas into an array.
- Blank line separator
- Everything after the blank line is the content

**The script**:
1. Reads each `.txt` file in `docs/`
2. Parses title, source_table, and content
3. Generates a deterministic UUID from the filename (so re-running is idempotent)
4. POSTs to `http://localhost:8000/api/rag/ingest` with `event: "created"`, `owner_type: "platform"`, `owner_id: null`

```bash
# Usage
cd scripts && uv run seed_from_files.py
# Or with a custom endpoint:
cd scripts && uv run seed_from_files.py --url http://localhost:8000/api/rag/ingest
```

---

## 7. Retrieval System (`backend/retrieval.py`)

**Important design decision**: Do NOT use LlamaIndex for retrieval. Use direct SQL queries via asyncpg for both vector and full-text search. This avoids LlamaIndex's opinionated table layout and gives full control over the hybrid fusion logic.

### 7.1 Hybrid Search Implementation (Raw SQL)

The `search_content` function performs two parallel queries and fuses results using Reciprocal Rank Fusion (RRF):

```python
async def hybrid_search(
    pool: asyncpg.Pool,
    query: str,
    query_embedding: list[float],
    source_table: str | None = None,
    source_id: str | None = None,
    metadata_filters: dict[str, str] | None = None,  # e.g. {"board": "CBSE", "grade": "10"}
    user_id: str | None = None,
    user_role: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Hybrid retrieval: vector cosine + BM25 full-text, fused via RRF.
    
    1. Run vector search (cosine similarity on rag_chunks.embedding)
    2. Run text search (ts_rank on rag_chunks.tsv)
    3. Fuse results using RRF: score = sum(1 / (k + rank)) across both lists
    4. Return top-k fused results with metadata
    """

    # Build WHERE clauses
    filters = []
    params = [query_embedding]  # $1 = embedding
    param_idx = 2

    # Ownership scoping (see section 7.2)
    ownership_clause = build_ownership_clause(user_id, user_role, params, param_idx)
    if ownership_clause:
        filters.append(ownership_clause.sql)
        param_idx = ownership_clause.next_param_idx

    if source_table:
        filters.append(f"ch.source_table = ${param_idx}")
        params.append(source_table)
        param_idx += 1

    if source_id:
        filters.append(f"ch.source_id = ${param_idx}::uuid")
        params.append(source_id)
        param_idx += 1

    # Metadata JSONB filters (e.g. board, grade, subject)
    if metadata_filters:
        for key, value in metadata_filters.items():
            filters.append(f"ch.metadata->>'{key}' = ${param_idx}")
            params.append(value)
            param_idx += 1

    where_clause = (" AND " + " AND ".join(filters)) if filters else ""

    # Vector search query
    vector_sql = f"""
        SELECT ch.id, ch.content, ch.source_id, ch.source_table,
               ch.source_title, ch.owner_type, ch.owner_id,
               1 - (ch.embedding <=> $1::vector) AS vector_score
        FROM rag_chunks ch
        WHERE ch.embedding IS NOT NULL {where_clause}
        ORDER BY ch.embedding <=> $1::vector
        LIMIT {top_k * 2}
    """

    # BM25 full-text search query
    tsquery_param = f"${param_idx}"
    params.append(query)
    text_sql = f"""
        SELECT ch.id, ch.content, ch.source_id, ch.source_table,
               ch.source_title, ch.owner_type, ch.owner_id,
               ts_rank(ch.tsv, plainto_tsquery('english', {tsquery_param})) AS text_score
        FROM rag_chunks ch
        WHERE ch.tsv @@ plainto_tsquery('english', {tsquery_param}) {where_clause}
        ORDER BY text_score DESC
        LIMIT {top_k * 2}
    """

    # Run both queries concurrently
    async with pool.acquire() as conn:
        vector_rows, text_rows = await asyncio.gather(
            conn.fetch(vector_sql, *params[:param_idx-1]),
            conn.fetch(text_sql, *params),
        )

    # RRF fusion (k=60 is standard)
    RRF_K = 60
    scores: dict[str, float] = {}
    metadata: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows):
        chunk_id = str(row["id"])
        scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (RRF_K + rank + 1)
        metadata[chunk_id] = dict(row)

    for rank, row in enumerate(text_rows):
        chunk_id = str(row["id"])
        scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (RRF_K + rank + 1)
        if chunk_id not in metadata:
            metadata[chunk_id] = dict(row)

    # Sort by fused score, return top-k
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [metadata[chunk_id] for chunk_id, _ in ranked]
```

### 7.2 Ownership Scoping

Ownership scoping controls which chunks a user can see during retrieval. The logic depends on `STUB_MODE` and the user's role.

**STUB_MODE=True**: No filtering. All chunks visible.

**STUB_MODE=False** (role-aware):

| Role | Filter |
|---|---|
| `student` | Platform content + content owned by linked parent(s) |
| `parent` | Platform content + own content |

**Student filter** (requires `parent_child_links` table — present in hAIsir's database):
```sql
WHERE (ch.owner_type = 'platform')
   OR (ch.owner_type = 'parent' AND ch.owner_id IN (
       SELECT parent_sub FROM parent_child_links
       WHERE child_sub = $user_id
         AND revoked_at IS NULL
   ))
```

**Parent filter**:
```sql
WHERE (ch.owner_type = 'platform')
   OR (ch.owner_type = 'parent' AND ch.owner_id = $user_id)
```

> **Note**: The `parent_child_links` query is a read-only dependency on a hAIsir table. This table only exists when `STUB_MODE=False` and the service is pointed at hAIsir's database. In STUB_MODE, this query is never executed.

### 7.3 Source Title Resolution

When a user says "the algebra topic" or "trigonometry", resolve to matching content via fuzzy match on `source_title`:

```sql
SELECT DISTINCT source_id, source_title, similarity(source_title, $1) AS sim
FROM rag_chunks
WHERE similarity(source_title, $1) > 0.1
ORDER BY sim DESC
LIMIT 1;
```

This uses `pg_trgm` for fuzzy matching. If no match found, fall back to embedding similarity:

```sql
SELECT DISTINCT source_id, source_title
FROM rag_chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> $1::vector
LIMIT 1;
```

---

## 8. Tool Definitions (`backend/tools.py`)

One tool is available to the LLM. The tool registration is a list, making it easy to add more tools later without restructuring the agent loop.

### 8.1 `search_content`

Searches ingested content using hybrid retrieval (vector + BM25).

```json
{
  "name": "search_content",
  "description": "Search study materials for specific information. Use this for questions about content, concepts, code examples, or topic details. Supports optional filtering by source type, specific source, and content metadata (board, grade, subject, difficulty).",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "What to search for in the content"
      },
      "source_table": {
        "type": "string",
        "description": "Filter by content type (e.g. 'topics', 'exam_templates')"
      },
      "source_id": {
        "type": "string",
        "description": "Filter to a specific source document by UUID"
      },
      "board": {
        "type": "string",
        "description": "Filter by education board (e.g. 'CBSE', 'ICSE')"
      },
      "grade": {
        "type": "string",
        "description": "Filter by grade/class level (e.g. '10', '12')"
      },
      "subject": {
        "type": "string",
        "description": "Filter by subject (e.g. 'Mathematics', 'Physics')"
      }
    },
    "required": ["query"]
  }
}
```

**Execution** (`execute_tool` in `tools.py`):
1. Generate embedding for `query` using BGE-M3
2. Build metadata filters from optional `board`, `grade`, `subject` params (see below)
3. Call `hybrid_search()` with the query, embedding, filters, and the current user's identity (for ownership scoping)
4. Format results as a string, each chunk prefixed with `[source_title]` and metadata context (e.g., `[Intro to Algebra — CBSE Class 10]`)
5. Return `(result_text, sources_list)`

**Metadata filtering in SQL**: Metadata filters are applied as additional WHERE clauses using JSONB operators:
```sql
-- Example: board='CBSE' AND grade='10'
AND ch.metadata->>'board' = $N
AND ch.metadata->>'grade' = $M
```

**Returns**: Formatted string with matched chunks. Sources list: one per chunk `{"label": source_title, "source_id": source_id, "metadata": metadata}`.

### 8.2 Adding New Tools

Tools are registered as a list in `tools.py`:

```python
TOOL_DEFINITIONS = [SEARCH_CONTENT_DEF]  # Add new tool defs here

TOOL_EXECUTORS = {
    "search_content": execute_search_content,
    # Add new executors here
}
```

The agent loop (section 9) iterates over whatever tools are in `TOOL_DEFINITIONS`. No code changes needed in `agent.py` to add tools.

---

## 9. Agent / Streaming Tool Loop (`backend/agent.py`)

This is the core orchestration layer. It manages the conversation with the LLM (Claude or Qwen via Ollama), including streaming and tool execution. The agent uses `llm_client.py` (section 5.2) to route to the active provider.

### 9.1 System Prompt

The base system prompt is the same for both providers, but Ollama gets an additional directive to compensate for weaker tool-calling reliability:

**Base prompt (both providers)**:
```
You are an AI assistant specialized in educational content and study materials.

Tool Usage:
- Use search_content for questions about specific content, concepts, or details
- For general knowledge questions, answer directly without tools
- Use up to 2 tool calls per query only when genuinely needed. The system enforces a hard cap of MAX_TOOL_ROUNDS=3 as a safety limit

Response Protocol:
- Provide direct answers — no meta-commentary about your search process
- Do not say "based on the search results" or describe your reasoning
- Be concise, educational, and clear
- Include relevant examples when they aid understanding
- When citing content, mention the source title naturally
- If retrieval returns no relevant results, say "I don't have information about that in the available materials" rather than guessing
```

**Additional Ollama directive** (appended when `LLM_PROVIDER == "ollama"`):
```
IMPORTANT: You MUST call a tool if the user's question is about specific study content, topics, or materials. Never answer from memory when a tool is available. When in doubt, call search_content.
```

### 9.2 Streaming Tool Loop

```python
async def stream_response(
    query: str,
    conversation_id: str,
    user_id: str,
    user_role: str,
) -> AsyncGenerator[str, None]:
    """Core agent loop. Yields SSE-formatted JSON lines.
    Works with both Anthropic and Ollama via llm_client abstraction."""

    from llm_client import create_streaming_response

    # 1. Load history and build messages
    history = await load_history(conversation_id)
    messages = history + [{"role": "user", "content": query}]

    tools = TOOL_DEFINITIONS
    sources: list[dict] = []
    full_response_text = ""
    rounds = 0

    while rounds <= settings.MAX_TOOL_ROUNDS:
        # 2. Stream an LLM call
        async with client.messages.stream(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=settings.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools if rounds < settings.MAX_TOOL_ROUNDS else [],
            temperature=settings.TEMPERATURE,
        ) as stream:

            # 3. Collect the full response (text blocks + tool_use blocks)
            assistant_content = []
            current_text = ""
            tool_calls = []

            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        yield sse_json({"type": "tool_call", "name": event.content_block.name})

                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield sse_json({"type": "chunk", "content": event.delta.text})
                        current_text += event.delta.text

            response = await stream.get_final_message()

        # 4. Process the response content blocks
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
                tool_calls.append(block)

        full_response_text += current_text

        # 5. If no tool calls, we're done
        if response.stop_reason != "tool_use" or not tool_calls:
            break

        # 6. Execute tools and build tool_result messages
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tc in tool_calls:
            result_str, tool_sources = await execute_tool(
                tc.name, tc.input, user_id=user_id, user_role=user_role
            )
            sources.extend(tool_sources)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})
        rounds += 1

    # 7. Save conversation to DB
    await save_messages(conversation_id, query, full_response_text)

    # 8. Final SSE event
    yield sse_json({
        "type": "done",
        "sources": deduplicate_sources(sources),
        "conversation_id": conversation_id,
    })


def sse_json(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"
```

**Key SDK details**:
- Use `client.messages.stream()` (async context manager) — NOT `client.messages.create(stream=True)`
- The `stream` context manager yields events; call `await stream.get_final_message()` after iteration to get the complete `Message` object with `stop_reason` and full content blocks
- `stop_reason == "tool_use"` means Claude wants to call a tool; `stop_reason == "end_turn"` means it's done
- Tool results must be appended as a `"user"` message with `"type": "tool_result"` blocks
- On the final round (when `rounds == MAX_TOOL_ROUNDS`), pass `tools=[]` to force Claude to synthesize without requesting more tools

### 9.3 Source Collection

Sources are collected during tool execution, not from the LLM response. `execute_tool()` returns a tuple: `(result_text, sources_list)`.

- `search_content`: Returns sources extracted from chunk metadata — one per chunk: `{"label": source_title, "source_id": source_id}`

Sources accumulate across multiple tool rounds. Duplicates (same `source_id`) are deduplicated before sending in the `done` event. If no tools were called, `sources` is an empty array `[]`.

### 9.4 SSE Event Format

```
# Text chunks (streamed as they arrive):
data: {"type": "chunk", "content": "The"}

data: {"type": "chunk", "content": " topic"}

data: {"type": "chunk", "content": " covers"}

# Tool call notification (so frontend can show a loading indicator):
data: {"type": "tool_call", "name": "search_content"}

# Final event:
data: {"type": "done", "sources": [{"label": "Intro to Algebra", "source_id": "uuid"}], "conversation_id": "uuid"}
```

### 9.5 Conversation History

Load from Postgres, pass as the `messages` array to the Anthropic SDK (not as a system prompt string):

```python
# Load last N messages for this conversation
rows = await conn.fetch(
    "SELECT role, content FROM rag_chat_messages WHERE conversation_id = $1 ORDER BY created_at DESC LIMIT $2",
    conversation_id, settings.MAX_CONVERSATION_HISTORY
)
# Reverse to chronological order, then prepend to messages array
history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
messages = history + [{"role": "user", "content": query}]
```

---

## 10. Auth Layer (`backend/auth.py`)

### 10.1 User Identity Resolution

```python
async def get_current_user(request: Request) -> CurrentUser:
    """Extract user identity from JWT or stub config."""
    if settings.STUB_MODE:
        return CurrentUser(
            user_id=settings.STUB_USER_ID,
            role=settings.STUB_USER_ROLE,
        )

    # Production: extract from APISIX-injected JWT
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing Authorization header")

    token = auth_header.split(" ", 1)[1]
    payload = decode_jwt(token)  # RS256, validate against Keycloak JWKS

    role = request.headers.get("X-Current-Role")
    if not role:
        raise HTTPException(400, "X-Current-Role header required")
    if role not in ("student", "parent"):
        raise HTTPException(403, "RAG chat requires student or parent role")

    return CurrentUser(
        user_id=payload["sub"],  # idp_sub — UUID string
        role=role,
    )
```

### 10.2 CSRF Validation

```python
async def validate_csrf(request: Request):
    """Validate CSRF token on mutations. Skipped in STUB_MODE."""
    if settings.STUB_MODE:
        return
    # Validate X-CSRF-Token header against double-submit cookie
    ...
```

### 10.3 HMAC Validation (Ingest Endpoint)

```python
def validate_webhook_signature(request: Request, body: bytes):
    """Validate HMAC-SHA256 signature. Skipped in STUB_MODE."""
    if settings.STUB_MODE:
        return

    signature = request.headers.get("X-Webhook-Signature", "")
    expected = "sha256=" + hmac.new(
        settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(401, "Invalid webhook signature")
```

---

## 11. API Endpoints (`backend/app.py`)

All endpoints are prefixed with `/api/rag/` to avoid path collisions when coexisting with other services behind the same gateway.

### 11.1 `POST /api/rag/query`

Main chat endpoint. Returns an SSE stream.

**Headers** (when `STUB_MODE=False`):
- `Authorization: Bearer <JWT>` (injected by APISIX)
- `X-Current-Role: student | parent`
- `X-CSRF-Token: <token>`

**Request body**:
```json
{
  "query": "What is a quadratic equation?",
  "conversation_id": "optional-uuid"
}
```

**Response**: `Content-Type: text/event-stream` — see SSE format in section 9.4.

**Behavior**:
1. Resolve user identity via `get_current_user()`
2. If `conversation_id` is null/missing, create a new `rag_conversations` row for this user
3. Call `stream_response(query, conversation_id, user_id, user_role)` and pipe SSE events
4. On error, yield `data: {"type": "error", "message": "..."}` and close stream

### 11.2 `GET /api/rag/conversations`

Returns the current user's conversation list.

**Response**:
```json
{
  "conversations": [
    {
      "id": "uuid",
      "title": "Quadratic equations",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

### 11.3 `GET /api/rag/conversations/{conversation_id}/messages`

Returns messages for a conversation. Only accessible by the conversation owner.

**Response**:
```json
{
  "messages": [
    {"role": "user", "content": "What is...", "created_at": "..."},
    {"role": "assistant", "content": "A quadratic...", "created_at": "..."}
  ]
}
```

### 11.4 `POST /api/rag/ingest`

Ingestion endpoint. See section 6.1 for full specification.

### 11.5 `GET /api/rag/chunks` (debug — STUB_MODE only)

Returns chunks with optional filters. For the dev stub's chunk inspector.

**Query params**: `source_id`, `source_table`, `q` (text search), `limit` (default 50)

**Response**:
```json
{
  "chunks": [
    {
      "id": "uuid",
      "source_id": "uuid",
      "source_table": "topics",
      "source_title": "Intro to Algebra",
      "owner_type": "platform",
      "chunk_index": 0,
      "content": "A quadratic equation is...",
      "created_at": "..."
    }
  ]
}
```

### 11.6 `GET /api/rag/health`

Health check. Returns `{"status": "ok", "chunks_count": N, "stub_mode": true}`.

### 11.7 CORS

Allow origins from `CORS_ORIGINS` setting (default: `http://localhost:3000`).

---

## 12. Frontend (Dev Stub — `frontend/`)

A development-only frontend for testing the RAG service in isolation. **Not for production** — production integration embeds chat into hAIsir's frontend.

### 12.1 Chat UI (`page.tsx`)

Single-page chat interface with:
- **Conversation sidebar**: List of past conversations, "New chat" button
- **Message list**: Scrollable area showing user and assistant messages
- **Input bar**: Text input + send button at the bottom
- **Streaming display**: Assistant messages render token-by-token as SSE chunks arrive
- **Source cards**: After a complete response, show cited sources below the message

### 12.2 Ingest Form (`IngestForm.tsx`)

Manual content ingestion for testing without hAIsir:
- Text fields: `source_title`, `source_table` (dropdown), `content` (textarea)
- Generates a random UUID for `source_id`
- POSTs to `/api/rag/ingest` with `event: "created"`, `owner_type: "platform"`
- Shows result: number of chunks created

### 12.3 Chunk Inspector (`ChunkInspector.tsx`)

Browse and search ingested chunks:
- Text search box (calls `GET /api/rag/chunks?q=...`)
- Filter by `source_table`
- Shows chunk content, source title, chunk index
- Useful for verifying ingestion and debugging retrieval quality

### 12.4 Debug Panel (`DebugPanel.tsx`)

Raw SSE event viewer:
- Shows every SSE event as it arrives (type, payload)
- Shows which chunks were retrieved and their scores for each tool call
- Toggle on/off — hidden by default

### 12.5 SSE Client Logic

**Important**: `ReadableStream` chunks do NOT align with SSE event boundaries. A single `read()` may return half a JSON payload or multiple events concatenated. Use a line buffer to accumulate text and only parse complete `data:` lines.

```typescript
async function sendQuery(query: string, conversationId?: string) {
  const response = await fetch("http://localhost:8000/api/rag/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, conversation_id: conversationId }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const eventBlock = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      for (const line of eventBlock.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === "chunk") appendToCurrentMessage(event.content);
          if (event.type === "tool_call") showSearchingIndicator(event.name);
          if (event.type === "done") {
            setSources(event.sources);
            setConversationId(event.conversation_id);
          }
          if (event.type === "error") showError(event.message);
        } catch {
          // Malformed JSON — skip this line
        }
      }
    }
  }
}
```

### 12.6 Styling

- Clean, minimal design with Tailwind
- Dark/light mode via `prefers-color-scheme`
- Responsive: mobile and desktop
- Font: system font stack

---

## 13. Docker Compose (`docker-compose.yml`)

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: raguser
      POSTGRES_PASSWORD: ragpass
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    profiles: ["local"]  # Only starts with: docker compose --profile local up

volumes:
  pgdata:
  ollama_data:
```

The backend and frontend run locally during development (not in Docker). The `ollama` service is behind a profile — it only starts when you explicitly request it with `docker compose --profile local up`. If you already have Ollama installed natively, skip the Docker service and just run `ollama serve` directly.

---

## 14. Startup Script (`run.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Start Postgres if not running
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d db
echo "Waiting for Postgres..."
until docker compose -f "$SCRIPT_DIR/docker-compose.yml" exec db pg_isready -U raguser -d ragdb > /dev/null 2>&1; do
  sleep 1
done
echo "Postgres ready."

# Start backend
echo "Starting backend..."
cd "$SCRIPT_DIR/backend" && uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd "$SCRIPT_DIR/frontend" && npm run dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose -f '$SCRIPT_DIR/docker-compose.yml' stop db" EXIT

wait
```

---

## 15. Testing Strategy

### 15.1 Backend Tests (`backend/tests/`)

Use `pytest` with `pytest-asyncio`. Tests require a running Postgres instance (use the Docker Compose DB).

**`test_ingestion.py`**:
- Test chunking respects size and overlap settings
- Test code block preservation (chunks don't split mid-code-block)
- Test ingest `created` event inserts chunks
- Test ingest `updated` event replaces chunks
- Test ingest `deleted` event removes chunks

**`test_tools.py`**:
- Test `search_content` returns relevant results for a known query
- Test `source_table` filter narrows results correctly
- Test fuzzy source title resolution
- Test ownership scoping: student sees platform + linked parent content only
- Test ownership scoping: parent sees platform + own content only
- Test STUB_MODE bypasses ownership scoping

**`test_api.py`**:
- Test `POST /api/rag/query` returns SSE stream with expected event types
- Test conversation creation (no `conversation_id` → new conversation returned)
- Test conversation continuity (same `conversation_id` → history-aware response)
- Test `GET /api/rag/conversations` returns user's conversations
- Test `GET /api/rag/health` returns ok
- Test `POST /api/rag/ingest` with valid HMAC succeeds
- Test `POST /api/rag/ingest` with invalid HMAC fails (when `STUB_MODE=False`)

### 15.2 Frontend Tests

Not required for the dev stub. Manual testing against the running backend is sufficient.

---

## 16. hAIsir Integration Reference

> **This section is future reference only.** The service is built and operated standalone. Integration requires configuration changes only — no schema migration, no code changes in this service.

### Schema Decision: `rag_chunks` supersedes `topic_content_chunks`

hAIsir's data model (`target/requirements/01_data_model.md`) had a planned `topic_content_chunks` table for pgvector RAG scoped to `topic_contents` only. **That table will not be created.** `rag_chunks` is a strict superset: it covers multiple source types (`topics`, `topic_contents`, `exam_templates`), includes ownership columns that match hAIsir's convention, BM25 via `tsvector`, and metadata JSONB. At integration time, update `01_data_model.md` to reflect this decision.

### 16.1 What Changes

| Setting | Standalone | Integrated |
|---|---|---|
| `DATABASE_URL` | Own Postgres instance (`ragdb`) | hAIsir's Postgres instance |
| `STUB_MODE` | `true` | `false` |
| `WEBHOOK_SECRET` | `dev-secret` | Shared secret with haisir-backend |
| `CORS_ORIGINS` | `http://localhost:3000` | hAIsir frontend origin |

### 16.2 hAIsir-Backend Changes

haisir-backend calls `POST /api/rag/ingest` on content lifecycle events:

| hAIsir Event | Ingest Payload |
|---|---|
| Topic content created/updated | `{event: "created"/"updated", source_id: topic.id, source_table: "topics", owner_type, owner_id, source_title: topic.title, content: topic_content.text}` |
| Topic deleted | `{event: "deleted", source_id: topic.id, source_table: "topics"}` |
| Exam template created/updated | `{event: "created"/"updated", source_id: exam.id, source_table: "exam_templates", owner_type, owner_id, source_title: exam.title, content: exam.description + questions}` |
| Exam template deleted | `{event: "deleted", source_id: exam.id, source_table: "exam_templates"}` |

**Bulk initial sync**: On first deployment, haisir-backend replays all existing content as `created` events to the ingest endpoint. This is a one-time script, not a permanent feature.

### 16.3 APISIX Routing

Add a route in APISIX to forward `/api/rag/*` to the rag-service:

```
/api/rag/*  →  rag-service:8000
```

APISIX injects `Authorization: Bearer <JWT>` on these routes, same as for haisir-backend.

### 16.4 hAIsir-Frontend Changes

Embed the chat UI into haisir-frontend under a student/parent route. Use `fetchWithCSRFRetry()` with `credentials: 'include'`. The SSE client logic (section 12.5) is the same — just change the endpoint URL and add the required headers (`X-Current-Role`, `X-CSRF-Token`).

### 16.5 Ownership Scoping Dependencies

When `STUB_MODE=False`, the student ownership filter reads the `parent_child_links` table (section 7.2). This table is owned by haisir-backend and exists in haisir's database. The rag-service performs read-only queries against it — never writes.

### 16.6 Content Types

The ingest endpoint accepts plaintext `content`. For non-text content types in hAIsir:

| hAIsir Content Type | Handling |
|---|---|
| Text (`topic_contents.type = 'text'`) | Send as-is |
| PDF (`topic_contents.type = 'pdf'`) | haisir-backend extracts text before sending to ingest |
| Video (`topic_contents.type = 'video'`) | Future — requires transcript extraction. Not in scope for initial integration. |

Text extraction is the **caller's responsibility**, not the rag-service's. The ingest endpoint always receives plaintext.

---

## 17. Error Handling

- **Missing API key**: If `LLM_PROVIDER == "anthropic"` and `ANTHROPIC_API_KEY` is empty, fail fast on startup with clear error message. If `LLM_PROVIDER == "ollama"`, no API key is needed.
- **Ollama not running**: If `LLM_PROVIDER == "ollama"`, check connectivity to `OLLAMA_BASE_URL` on startup. If unreachable, log error with instructions: "Run `ollama serve` or start the Docker ollama service."
- **Ollama model not pulled**: On first request, if the model returns a 404, log: "Model not found. Run `ollama pull qwen3-8b`" and return an error to the user.
- **Database connection failure**: Retry 3 times with exponential backoff on startup, then fail.
- **Tool execution failure**: Return error message as `tool_result` to the LLM; it will explain the failure to the user.
- **Embedding model download**: `FlagEmbedding` / `sentence-transformers` auto-downloads BGE-M3 on first use (~2.4GB); log progress.
- **Ingest with empty content**: Return 422 with clear message. Don't create zero chunks.
- **Conversation not found**: If a provided `conversation_id` doesn't exist or belongs to a different user, create a new conversation and proceed.
- **HMAC validation failure** (when `STUB_MODE=False`): Return 401 immediately. Do not process the payload.

---

## 18. CLAUDE.md for the New Project

Include this as the `CLAUDE.md` in the generated project root:

```markdown
# CLAUDE.md

## Commands

**Prerequisites**: Docker (for Postgres), Python 3.11+, Node.js 18+, uv. Optionally: Ollama (for local LLM mode).

**Setup**
\```bash
docker compose up -d db          # Start Postgres with pgvector
cd backend && uv sync             # Install Python dependencies
cp .env.example .env              # Configure LLM_PROVIDER + keys
cd ../frontend && npm install     # Install Node dependencies
\```

**Local LLM setup (optional)**
\```bash
ollama pull qwen3-8b              # Download Qwen3 (~5GB, one-time)
# Then set LLM_PROVIDER=ollama in .env
\```

**Run everything**
\```bash
./run.sh
\```
Backend: http://localhost:8000 (API docs: http://localhost:8000/docs)
Frontend: http://localhost:3000

**Seed sample content**
\```bash
cd scripts && uv run seed_from_files.py
\```

**Run backend only**
\```bash
cd backend && uv run uvicorn app:app --reload --port 8000
\```

**Run tests**
\```bash
cd backend && uv run pytest -v
\```

## Architecture

Agentic RAG: LLM (Claude or Qwen3 via Ollama) decides whether/what to retrieve via tool_use.

LLM Provider: Configurable via LLM_PROVIDER env var. "anthropic" for Claude (cloud, best quality), "ollama" for Qwen3-8B (local, offline, free).

Request flow: Frontend → FastAPI SSE → LLM streaming + tool loop → Postgres (pgvector hybrid search) → streamed response

Tool: search_content (hybrid vector+BM25 retrieval). Tool list is extensible.

Database: PostgreSQL with pgvector. Tables: rag_chunks, rag_conversations, rag_chat_messages. All rag_-prefixed.

Embeddings: BAAI/bge-m3 (1024-dim, local).

Retrieval: Raw SQL hybrid search — RRF fusion of pgvector cosine similarity + tsvector BM25.

STUB_MODE (default: true): Bypasses JWT auth, CSRF, ownership scoping, and HMAC validation for standalone development. Set to false when integrating with hAIsir.
```

---

## 19. Implementation Order

Build in this sequence. Each step should be independently testable.

1. **`docker-compose.yml`** + **`backend/config.py`** + **`backend/database.py`** — Postgres up, schema created
2. **`backend/models.py`** — Pydantic models
3. **`backend/auth.py`** — STUB_MODE identity resolution
4. **`backend/llm_client.py`** — LLM abstraction (Anthropic + Ollama routing)
5. **`backend/ingestion.py`** — Chunking + embedding logic (called by ingest endpoint)
6. **`backend/retrieval.py`** — Hybrid search (vector + BM25 + RRF fusion + ownership scoping) via raw SQL
7. **`backend/tools.py`** — `search_content` tool definition + execution
8. **`backend/conversations.py`** — Conversation and message CRUD
9. **`backend/agent.py`** — Streaming tool loop using llm_client abstraction
10. **`backend/app.py`** — FastAPI endpoints wiring everything together
11. **`scripts/seed_from_files.py`** — Dev seed script
12. **Backend tests** — Verify ingestion, tools, API, ownership scoping
13. **`frontend/`** — Dev stub: chat UI, ingest form, chunk inspector, debug panel
14. **`run.sh`** + **`.env.example`** + **`CLAUDE.md`** — Developer experience
