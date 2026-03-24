# RAG, Curriculum Structure & hAITU — Design Decisions
> Session date: 2026-03-24
> Covers: content hierarchy, node types, RAG data model, multi-board support, open track mapping, curriculum builder gaps

---

## 1. Content Hierarchy — Clarified Terminology

### The tree

```
categories                          ← "board" in UI (NCERT, CBSE, ICSE, IB MYP…)
  └── course_path_nodes (tree)      ← self-referential, arbitrary depth
        └── topics                  ← hang off the LEAF course_path_node only
              └── topic_contents    ← 1 per type per topic (video | pdf | text)
                    └── topic_content_chunks   ← NEW: chunks for RAG retrieval
```

### Key rules
- `topics` attach only to **leaf** `course_path_nodes` (nodes with no children). Enforced at API layer: `POST /api/topics` rejects if `course_path_node` has children.
- `topic_contents` is **1 item per type per topic**: one video, one PDF, one text note. Multiple videos = multiple topics.
- `topic_content_chunks` exist only for `pdf` and `text` content types. Videos are skipped (`extraction_status = 'skipped'`).

### What "course", "topic", "chapter" mean

| Term in spec | What it maps to | Example |
|---|---|---|
| Board | `categories` row | NCERT, CBSE, IB MYP |
| Grade / Subject | `course_path_nodes` (reserved types) | Grade 6, Science |
| Chapter / Module / Section | `course_path_node` (leaf) | "Food: Where Does It Come From?" |
| Topic | `topics` row | "Food Variety", "Plant Parts We Eat" |
| Content item | `topic_contents` row | NCERT Ch1 Sec1 PDF, YouTube video |
| Chunk | `topic_content_chunks` row | 600-char segment of the PDF |

---

## 2. NodeType — Flexible with Reserved Defaults

### Decision
`node_type` on `course_path_nodes` is a **free string**, not a strict enum. Two tiers:

**Reserved** — system behaviour depends on these. Cannot be repurposed.

| Type | Why reserved |
|---|---|
| `grade` | Grade-locking: `topic.locked` derived from student grade vs nearest `grade` ancestor |
| `subject` | Subject-level analytics grouping |

**Defaults** — shown as suggestions in the curriculum builder UI. No special system behaviour.

```
course, chapter, module, section, unit, week
```

**Custom** — tutor or admin types any string (e.g. `sprint`, `strand`, `track`). Stored as-is.

### Data model change
```python
# Before: strict StrEnum
class NodeType(StrEnum):
    grade = "grade"
    subject = "subject"
    course = "course"

# After: free string, validated at service layer only for reserved types
class CoursePathNode:
    node_type: str    # non-empty, max 50 chars. Service checks reserved set when needed.

RESERVED_NODE_TYPES = frozenset({"grade", "subject"})
DEFAULT_NODE_TYPES  = frozenset({"course", "chapter", "module", "section", "unit", "week"})
```

### Curriculum builder UI
When adding a node, show a dropdown of defaults + "Custom…" text input. Tutors pick in one click. Reserved types shown with 🔒 in platform admin view.

---

## 3. RAG / hAITU Data Model

### Problem with current spec (context-stuffing)
Current approach truncates each `topic_contents.text_extracted` to 2000 chars, caps total at 4000 chars, injects all of it into the system prompt. Breaks down for large PDFs (30+ pages).

### Decision: RAG within a topic using pgvector

**New table: `topic_content_chunks`**

```sql
topic_content_chunks (
    id                UUID         PRIMARY KEY,
    topic_id          UUID         NOT NULL,    -- filter scope at query time
    topic_content_id  UUID         NOT NULL,    -- which content item this came from
    chunk_index       INT          NOT NULL,
    content           TEXT         NOT NULL,    -- 600-char piece of extracted text
    embedding         vector(384)  NOT NULL,    -- all-MiniLM-L6-v2
    created_at        TIMESTAMPTZ  NOT NULL
)

CREATE INDEX ON topic_content_chunks USING hnsw(embedding vector_cosine_ops);
CREATE INDEX ON topic_content_chunks(topic_id);
```

**Why not self-referential on `topic_contents`?**
One content item produces many chunks — it's a 1:N relationship. Adding chunks as rows on `topic_contents` (e.g. with `parent_content_id`) would break all existing queries on that table (they'd need `WHERE parent_content_id IS NULL` everywhere). Separate table is one migration, zero footgun risk.

**Extraction pipeline**
```
topic_contents row created/updated
    → async background job
        ├── extract full text (pdfplumber for PDF, passthrough for text)
        ├── store in text_extracted (kept for fallback per BR-AI-010)
        ├── chunk: 600-char pieces, 100-char overlap, sentence-aware split
        └── for each chunk:
                embed (all-MiniLM-L6-v2) → upsert into topic_content_chunks
```

### LlamaIndex Integration — Document-Driven Chunking

Decision: Source-Document-Driven Chunking

- The `topic_contents` table is the source of truth for all content items (PDFs, text, etc.), storing metadata and file references for each topic.
- The RAG pipeline (for example, using LlamaIndex) reads from `topic_contents`, loads each document, and handles chunking, embedding, and storage of nodes ("chunks") in the vector database (`topic_content_chunks`).
- `topic_content_chunks` are not managed directly by application code; they are generated and updated by the ingestion pipeline based on the current state of `topic_contents` (create/update/delete).
- Only minimal linking metadata (e.g., `topic_content_id`, `topic_id`, `chunk_index`) is stored in `topic_content_chunks`. All rich metadata (source filename, content type, uploader, timestamps, any provenance) remains in normalized tables (`topic_contents`, `topics`, etc.) and is accessed via joins or materialized views as needed at query time.
- This approach keeps the schema clean, leverages LlamaIndex's document loading and node management strengths, and ensures maintainability and scalability for both ingestion and retrieval.

Notes / Implementation details:
- Ingestion: the pipeline should detect document changes (checksum or content version) and re-run chunking + embedding for affected `topic_contents` rows; obsolete chunks are removed or soft-deleted to keep the vector store consistent.
- Vector DB records must include `topic_id` and `topic_content_id` for efficient scoping during retrieval (e.g., `WHERE topic_id = ?`).
- Metadata-driven joins: when presenting retrieved chunks to hAITU or UI flows, enrich returned chunks with metadata from `topic_contents` via a join on `topic_content_id` rather than duplicating metadata in the vector rows.
- LlamaIndex can be used to centralize loaders, chunking logic (chunk size, overlap, sentence-aware splitting), and node-level metadata; keep the pipeline idempotent so re-ingestion is safe.

- Embedding model: use `all-MiniLM-L6-v2` (or an agreed canonical embedding model) for both ingestion and retrieval to ensure vector compatibility.
- Vector cleanup policy: ingestion must either hard-delete obsolete vectors for a `topic_content` or mark them with a tombstone/soft-delete flag and rely on a periodic reconciliation job to purge stale vectors. The ingestion job should be idempotent and detect content checksum/version changes to trigger re-chunking and cleanup.

Example flow:
```
topic_contents row created/updated
    → ingestion job (LlamaIndex loader)
        ├── load document (PDF/text)
        ├── chunk into nodes (600-char, 100-char overlap)
        ├── for each node: create embedding, write vector with topic_id + topic_content_id + chunk_index
        └── mark old vectors for this topic_content as removed if they no longer exist after re-chunking
```

This section supersedes the earlier ad-hoc chunk-management guidance: prefer document-driven ingestion (LlamaIndex) and keep `topic_content_chunks` as a generated table/representation, not a manually maintained content store.

**hAITU query time**
```
Student asks doubt on a topic
    → embed the student's message
        → pgvector search: WHERE topic_id = <this topic> ORDER BY embedding <=> ? LIMIT 5
            → top-5 relevant chunks (~3000 chars) assembled
                → injected into hAITU system prompt → Claude answers
```

**Video-only gap**
Courses with video-only content have no extractable text → no chunks → hAITU has no retrieval context.

Mitigation (v1): Curriculum builder (T04) shows a warning on topics with no text/pdf content:
> *"No text content for this topic — hAITU will answer from general knowledge only."*

Future: auto-transcription pipeline (Whisper) — out of scope for v1.

---

## 4. Multi-Board Support

### Indian boards — all work with existing model

| Board | Hierarchy | Status |
|---|---|---|
| NCERT / CBSE | grade → subject → chapter → topic | ✅ works |
| ICSE | grade → subject → chapter → topic | ✅ works (Science splits into Physics/Chemistry/Biology as separate subjects) |
| State boards | grade → subject → chapter → topic | ✅ works |

### International boards

| Board | Hierarchy | Status |
|---|---|---|
| Cambridge IGCSE / A Level | grade → subject → unit → topic | ✅ add `unit` to defaults |
| Cambridge Primary | stage → strand → sub-strand → topic | ✅ add `stage`, `strand`, `sub_strand` to defaults |
| IB MYP | grade → subject_group → subject → unit → topic | ✅ add `subject_group` to defaults |
| IB DP | programme → subject → unit → topic | ✅ no grade node needed (DP is 2-year flat) |
| IB PYP | theme → unit of inquiry (transdisciplinary) | ❌ doesn't fit the tree model — themes span all subjects simultaneously. Needs a separate content model. Defer. |

### `categories` table — `path_type` clarification
- `structured` — board-controlled curriculum (NCERT, CBSE, Cambridge, IB)
- `flexible` — tutor-built open courses

IB PYP would use `flexible` with a custom structure if ever supported.

---

## 5. Open Track — Online Course Mapping

Validated against: DeepLearning.AI (RAG course, MCP course), Coursera (Enterprise Architecture), Udemy (Kubernetes).

### Mapping rule

| Platform pattern | `course_path_node` | `topic` | `topic_content` |
|---|---|---|---|
| Modular (Module → Lesson) | course → module (leaf) | Each lesson | Video + transcript |
| Flat (Lesson only) | course (leaf) | Each lesson | Video + notes |
| Week-based (Week → Lecture) | course → week (leaf) | Each lecture | Video + reading PDF |
| Section-based (Section → Lecture) | course → section (leaf) | Each lecture | Video + optional PDF |

### Key findings
1. Topics are individual **lessons**, not modules. Module/Week/Section = `course_path_node`.
2. The flat MCP-style course (no modules) has topics hanging directly off the `course` node — the same FK works for both cases.
3. Quizzes within modules → `exam_templates` with `purpose='quiz'`, `topic_id` = the module's topic.
4. hAITU query scope: flat course uses `WHERE topic_id = ?`; modular course needs topics scoped to the module's node: `WHERE topic_id IN (topics hanging off this module node)`.

---

## 6. Curriculum Builder — Spec Gaps Found

Two builders exist: **T04** (Teacher/Tutor) in `04_teacher_tutor.md` and **SA02** (Platform Admin) in `05_06_07_personas.md`.

Both have the same structural gaps:

| Gap | Current spec | What it should be |
|---|---|---|
| Tree depth | Hardcoded "chapter → sub-topic" (2 levels) | Arbitrary depth — owner decides |
| Node-type | "+ Add chapter" hardcoded | "+ Add node" with type picker (defaults + custom) |
| Type picker UI | Not described | Dropdown: defaults + custom text input |
| Leaf enforcement | Not mentioned | Topics addable only to leaf nodes (API enforces) |
| API `level` field | `POST /api/topics body: {level: str}` | Rename to `node_type` |

SA02 additional gap: no "add node" action described at all (only edit/publish existing).

---

## 7. Implementation Tasks

### Schema changes

- [ ] **`course_path_nodes.node_type`** — change from enum to `VARCHAR(50)`. Existing values (`grade`, `subject`, `course`) remain valid.
- [ ] **`course_path_nodes`** — add `owner_type` and `owner_id` columns via `ALTER TABLE` (per spec §3.1 — already planned, confirm not done yet).
- [ ] **`topics`** — add `status`, `owner_type`, `owner_id` columns via `ALTER TABLE` (per spec §3.2 — already planned).
- [ ] **`topic_content_chunks`** — new table with pgvector index (see §3 above).
- [ ] **pgvector extension** — must be enabled on the PostgreSQL instance before the above migration.

### Backend changes

- [ ] **`domain/models/course_path_node.py`** — replace `NodeType` enum with free string + `RESERVED_NODE_TYPES` / `DEFAULT_NODE_TYPES` constants.
- [ ] **Topic service** — add leaf-node enforcement: reject `POST /api/topics` if target `course_path_node` has children.
- [ ] **`POST /api/topics` body** — rename `level` → `node_type`.
- [ ] **Extraction pipeline** — new async job: extract text → chunk → embed → insert into `topic_content_chunks`. Runs on `topic_contents` create/update.
- [ ] **hAITU service** — replace context-stuffing with pgvector retrieval: embed student message → `WHERE topic_id = ?` vector search → inject top-5 chunks.
- [ ] **hAITU fallback** — if `topic_content_chunks` is empty for topic (e.g. video-only), fall back to `text_extracted` truncated (existing BR-AI-010 behaviour).

### Spec files to update (after prototype validation)

- [ ] **`01_data_model.md`** — add `topic_content_chunks` table definition; update `CoursePathNode.node_type` to free string.
- [ ] **`04_teacher_tutor.md` T04** — replace fixed 2-level tree description with arbitrary depth; add node-type picker; add leaf-node rule; rename `level` → `node_type` in API block.
- [ ] **`05_06_07_personas.md` SA02** — same tree fixes as T04; add "Add node" action and API; show reserved type indicators for `grade` and `subject`.
- [ ] **`08_haitu_ai_layer.md`** — replace context-stuffing with vector retrieval description; add `topic_content_chunks` to hAITU data dependencies; add video-only warning behaviour.
- [ ] **`00_overview.md`** — update search convention to mention `topic_content_chunks` for hAITU (distinct from general hybrid search).

### Prototype validation pending

- [ ] Build curriculum builder prototype demonstrating: arbitrary depth tree, node-type picker, leaf-node topic management, 1-content-per-type rule.
- [ ] Validate with tutor view (open track, modular course) and platform admin view (NCERT structured).
- [ ] Once validated, update T04 and SA02 spec sections and merge into existing HTML prototypes.
