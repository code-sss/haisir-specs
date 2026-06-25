# Phase 4 Implementation Plan — Doubt Persistence + Teacher Escalation + Notifications + Mastery/Post-Exam Review

> Two locked features, properly phased. Challenger-verified (2 rounds). Written 2026-06-24.
> Goal 0 is a P0 stabilization that must land first.
> Feature 1 = G1 + G2 + G3 (doubt persistence → teacher escalation → notifications).
> Feature 2 = G4 (mastery tracking + post-exam review).
> Order: G0 → G1 → G2 → G3 → G4 (acyclic; rationale at the end).
>
> Confirmed decisions (2026-06-24):
> - Doubts link to the student by a plain-text `student_sub` column (no DB foreign key), per the project rule that user identity is never a hard FK. The `student_enrollments` table is NOT extended. Only `enrollment_topics` (G4) foreign-keys to `student_enrollments`.
> - Shared-instructor-queue "read" marks a shared notification read globally for the role queue (v1 limitation, documented).
> - CLAUDE.md's stale Keycloak-roles claim is corrected by T0.8.

## ROOT GOAL
A student's hAITU doubt conversation becomes a durable thread they can leave and return to, can be escalated to a teacher who replies in-thread, and every doubt lifecycle event raises a notification (bell + feed). Then, after exams, per-topic mastery is tracked, weak topics are flagged + notified, and the student can review their exam with hAITU explaining wrong answers.

---

## G0 — Stabilize HEAD (P0 blocker)

**Goal**: The backend app and worker import cleanly at HEAD on `main` (feature/rag merged), so all Phase 4 backend work starts from a green, importable base. Today the app + worker are un-importable on `feature/rag` due to Python-2 `except A, B:` syntax in 4 files (5 sites).
**Goal test**: `python -c "from main import app"` and `python -c "import worker"` succeed on `main`; the Phase 3 integration suite passes at HEAD with the sign-off test count; a CI grep guard blocks the regression.
**Repos**: [backend] [frontend] [deploy] [specs]

### G0.1 — Fix Python-2 SyntaxErrors + merge feature/rag → main
**Subgoal**: All 5 `except A, B:` sites are converted to `except (A, B):`, and feature/rag is merged into main in all three repos so HEAD is green and contains Phase 3.
**Subgoal test**: `ast.parse` succeeds on parent.py, exam_session.py, haitu_service.py, worker/__main__.py; `from main import app` succeeds; main contains the Phase 3 commits (V34, hAITU pipeline, SSE).
**Repos**: [backend] [frontend] [deploy]

##### T0.1 [backend] — Fix 5 Python-2 except-clause SyntaxErrors
- **Build**: Convert `except A, B:` → `except (A, B):` at src/api/routes/parent.py:56 and :88 (`LinkCodeAlreadyUsedError, LinkCodeExpiredError`), src/api/routes/exam_session.py:219 (`json.JSONDecodeError, TypeError`), src/domain/services/haitu_service.py:262 (`json.JSONDecodeError, KeyError`), src/worker/__main__.py:192 (`KeyboardInterrupt, asyncio.CancelledError`). All 4 files must be fixed — fixing only parent.py does NOT make the app importable (exam_session.py is imported first via the router tuple).
- **Done when**: `python -c "from main import app"` and `python -c "import worker"` succeed on feature/rag at HEAD (no SyntaxError).
- **Test**: `assert __import__("main").app is not None`
- **Depends on**: None

##### T0.2 [backend] — Merge feature/rag → main
- **Build**: `git -C ../haisir-backend checkout main && git merge feature/rag` (ff or merge commit); resolve conflicts preserving Phase 3; push main; verify `from main import app` imports on main.
- **Done when**: main includes the Phase 3 commits and main == feature/rag (or main is a descendant).
- **Test**: `assert $(git -C ../haisir-backend rev-parse main) == $(git -C ../haisir-backend rev-parse feature/rag)`
- **Depends on**: T0.1 [backend]

##### T0.3 [frontend] — Merge feature/rag → main
- **Build**: `git -C ../haisir-frontend checkout main && git merge feature/rag`; resolve conflicts preserving Phase 3 enrollment/hAITU UI; push main.
- **Done when**: frontend main includes Phase 3 frontend commits and matches feature/rag (or ahead).
- **Test**: `assert $(git -C ../haisir-frontend rev-parse main) == $(git -C ../haisir-frontend rev-parse feature/rag)`
- **Depends on**: None

##### T0.4 [deploy] — Merge feature/rag → main
- **Build**: `git -C ../haisir-deploy checkout main && git merge feature/rag` (Keycloak realm with all 6 roles, 19-api-haitu.json, env vars); resolve conflicts; push main.
- **Done when**: deploy main includes Phase 3 commits and matches feature/rag (or ahead).
- **Test**: `assert $(git -C ../haisir-deploy rev-parse main) == $(git -C ../haisir-deploy rev-parse feature/rag)`
- **Depends on**: None

### G0.2 — Re-verify Phase 3 at HEAD + CI guard + correct stale docs
**Subgoal**: Phase 3 suites pass at the new main HEAD (they couldn't at the broken feature/rag HEAD), a CI guard prevents Python-2 except syntax from regressing, and the stale CLAUDE.md Keycloak-roles claim is corrected (so G2 can rely on instructor being available).
**Subgoal test**: `pytest tests/integration/phase3_db_only tests/integration/phase3_ollama_gated` passes (matching the Phase 3 sign-off baseline, ~3537 tests); Playwright passes; a CI step fails on any `except <Name>, <Name>:` in src/; CLAUDE.md no longer says tutor/parent/institution_admin are "not yet added to the Keycloak realm".
**Repos**: [backend] [frontend] [specs]

##### T0.5 [backend] — Re-run Phase 3 integration suites at HEAD
- **Build**: After merge, run `pytest tests/integration/phase3_db_only tests/integration/phase3_ollama_gated -q` from haisir-backend; the two E2E tests that do `from main import app` (test_g2_e2e_enrollment_lifecycle.py, test_g5_e2e_haitu_topic_doubt.py) now import; fix regressions; record the pass count (must match Phase 3 sign-off).
- **Done when**: the Phase 3 DB-only + Ollama-gated suites pass at main HEAD with the sign-off test count.
- **Test**: `assert exit_code == 0` for the Phase 3 integration suite.
- **Depends on**: T0.2 [backend]

##### T0.6 [frontend] — Re-run Playwright E2E at HEAD
- **Build**: After the frontend merge, run the project's Playwright E2E (enrollment/hAITU flows); fix regressions.
- **Done when**: the frontend Playwright suite passes at main HEAD.
- **Test**: `assert exit_code == 0` for the Playwright run.
- **Depends on**: T0.3 [frontend]

##### T0.7 [backend] — CI grep guard against Python-2 except syntax
- **Build**: Add `scripts/check_except_syntax.py` in haisir-backend that regex-searches `^\s*except\s+[A-Za-z_]\w*\s*,` (bare-name only — no dot, so dotted exception refs like `except json.JSONDecodeError, TypeError:` are deliberately NOT matched; that form is valid Python 3.14+ and is ruff's preferred form, which T0.1 left as-is) in `src/**/*.py` and exits 1 on match; wire into the existing CI workflow as a required step.
- **Done when**: a CI run on a branch re-introducing `except A, B:` fails; a clean branch passes.
- **Test**: `assert check_exit_code == 1` when the checker runs against a file containing `except ValueError, TypeError:`.
- **Depends on**: T0.5 [backend]

##### T0.8 [specs] — Correct stale CLAUDE.md Keycloak-roles claim
- **Build**: In CLAUDE.md (Critical Rules), update the "Keycloak roles" bullet: `institution_admin`, `tutor`, `parent` ARE provisioned in the Keycloak realm — `deploy/common/keycloak/02-roles.json` provisions all 6 roles (student, instructor, admin, institution_admin, tutor, parent) and `04-user-instructor.json` provisions an instructor test user. State that `require_instructor` / `require_tutor` / `require_parent` work against the provisioned realm (remove the "not yet added / follow 11_role_migration.md steps before enabling them" caveat). Leave the role-migration reference in place only if still relevant to other un-provisioned behaviour.
- **Done when**: CLAUDE.md no longer claims institution_admin/tutor/parent are "not yet added to the Keycloak realm".
- **Test**: `! grep -q "not yet added to the Keycloak realm" CLAUDE.md` (the stale claim is gone).
- **Depends on**: None

### G0.3 — Remove inline-ML deps + stub the reranker (external-API future-hook)
**Subgoal**: The only inline-ML code path (the hAITU reranker's `SentenceTransformerRerank` at `src/domain/services/haitu_service.py:312`, already disabled via `rerank_model=""`) is replaced by a documented no-op stub that preserves the `rerank_model` config as a hook for a future external rerank API, and the heavy `sentence-transformers` + `torch` deps (plus the uv torch-CPU pin + pytorch-cpu index) are removed so the backend no longer ships ~1-2 GB of unused ML wheels. Embedding/OCR/RAG stay external (Ollama/LM Studio HTTP) — unchanged. Rationale: the platform runs all LLM/embedding/rerank workloads against external services (lmstudio local-dev, ollama cloud); there is no plan to run inline models in the backend.
**Subgoal test**: `from main import app` + `import worker` succeed; the Phase 3 hAITU suite passes with the reranker as a passthrough; `uv.lock` contains no `torch` / `transformers` / `sentence-transformers`; the Docker build no longer pulls the pytorch-cpu index.
**Repos**: [backend]

##### T0.9 [backend] — Stub _stage3_rerank to a no-op (keep rerank_model as external-API hook)
- **Build**: In `src/domain/services/haitu_service.py` `_stage3_rerank` (~lines 293-321), remove the lazy `from llama_index.core.postprocessor import SentenceTransformerRerank` import and the `SentenceTransformerRerank(...)` instantiation; replace the method body with a passthrough that returns `nodes` unchanged. Keep the `rerank_model == ""` fast path and the `rerank_model` config field (`src/shared/config.py:269`) as a documented future-hook: if `rerank_model` is non-empty, log a warning ("rerank requested (model=<x>) but no external rerank client is configured yet; returning unordered nodes") and return `nodes`. Keep the method signature + the 4-stage pipeline call sites (`haitu_service.py:458`, `:688`) intact. Do NOT change the `with_rerank` over-fetch flag behavior.
- **Done when**: `_stage3_rerank` returns `nodes` unchanged without importing `SentenceTransformerRerank`; a non-empty `rerank_model` logs a warning instead of raising; the 4-stage pipeline still calls `_stage3_rerank`.
- **Test**: `assert result == nodes` when `_stage3_rerank(nodes, q)` is called with `rerank_model="cross-encoder/ms-marco"` (and no `SentenceTransformerRerank` import remains in the file).
- **Depends on**: T0.2 [backend] (work on a green main)

##### T0.10 [backend] — Update the reranker unit tests
- **Build**: In `tests/unit/domain/test_services/test_haitu_service.py`, the two tests that `patch("llama_index.core.postprocessor.SentenceTransformerRerank")` (~lines 258, 301) — `test_rerank_branch_uses_sentence_transformer_rerank` and `test_rerank_branch_propagates_results` — are replaced by a test asserting `_stage3_rerank` is a passthrough no-op even when `rerank_model` is set (no model loaded, nodes returned unchanged). Keep the passthrough tests (`test_passthrough_on_empty_*`, ~:240, :251). Remove all `SentenceTransformerRerank` patch references.
- **Done when**: the reranker tests pass with the no-op stub and no longer reference `SentenceTransformerRerank`; `pytest tests/unit/domain/test_services/test_haitu_service.py` is green.
- **Test**: `assert pytest_exit_code == 0` for the haitu_service unit tests.
- **Depends on**: T0.9 [backend]

##### T0.11 [backend] — Remove sentence-transformers + torch + uv torch-CPU pin from pyproject
- **Build**: In `pyproject.toml`: delete `sentence-transformers>=5.0.0` (line 40) and `torch>=2.7.0` (line 41) from `[project.dependencies]`; delete the `[tool.uv.sources]` torch entry (~lines 68-69), the `[[tool.uv.index]] pytorch-cpu` block (~lines 71-74), and the explanatory comment (~lines 62-67). Keep `llama-index-core`, `llama-index-vector-stores-postgres`, `llama-index-embeddings-ollama` (external RAG — unchanged). Regenerate `uv.lock` (`uv lock`); verify `numpy` stays only if another live dep still needs it. Confirm `from main import app` still imports (no live module relied on the removed deps).
- **Done when**: `pyproject.toml` has no `sentence-transformers` / `torch` / pytorch-cpu entries; `uv.lock` no longer lists `torch`, `transformers`, `tokenizers`, `huggingface-hub`, `safetensors`, `sentence-transformers`, `scikit-learn`, `scipy`; `from main import app` succeeds.
- **Test**: `assert "torch" not in open("uv.lock").read()` (and `sentence-transformers` absent).
- **Depends on**: T0.9 [backend], T0.10 [backend] (code no longer imports the removed classes)

##### T0.12 [backend] — Verify post-cleanup: imports + Phase 3 hAITU suite + lock clean
- **Build**: After the dep removal, re-run `python -c "from main import app"` + `python -c "import worker"`; run the Phase 3 hAITU integration suite (reranker passthrough path) to confirm retrieval + synthesis still work without the reranker; assert `uv.lock` is free of torch/transformers/sentence-transformers; confirm the backend Docker image build no longer references the pytorch-cpu index and the image is smaller.
- **Done when**: app + worker import; the Phase 3 hAITU suite passes; `uv.lock` is clean of the removed ML deps; the Docker build succeeds without the pytorch-cpu index.
- **Test**: `assert exit_code == 0` for the Phase 3 hAITU suite after the dep removal.
- **Depends on**: T0.11 [backend], T0.5 [backend]

**G0 integration test**: After G0, `from main import app` + `import worker` succeed on main; the Phase 3 backend integration + frontend Playwright suites pass at HEAD with the sign-off test count; the CI grep guard blocks Python-2 except syntax; CLAUDE.md's Keycloak section matches the deployed realm; the inline-ML deps (sentence-transformers/torch) are removed and the hAITU reranker is a no-op future-hook. Phase 4 backend work can begin on a green, lean base.

---

## G1 — Doubt persistence + hAITU thread completion

**Goal**: A student's hAITU topic-doubt conversation (and any escalation) is persisted as a durable thread (doubts + doubt_messages), so a student can leave and return to their doubts, see AI + teacher replies in one thread — with no orphaned rows on rate-limit (429) or mid-stream disconnect.
**Goal test**: A student asks hAITU a doubt → doubts row + student message + AI reply persist; the student reopens the thread (S09) seeing both messages; a 429 leaves no doubts row; a mid-stream disconnect still persists whatever AI text was produced.
**Repos**: [specs] [backend] [frontend]

### G1.1 — Doubt schema + spec contracts (V35)
**Subgoal**: The doubts + doubt_messages schema (V35) is migrated and mapped, and the spec contracts (doubt lifecycle, doubt_id SSE event, student endpoints) are written so backend + frontend build against a fixed contract.
**Subgoal test**: `alembic upgrade V35` creates doubts + doubt_messages with required columns/constraints; 11_haitu_ai_layer.md + 03_student.md document the lifecycle, the doubt_id SSE event, and S08/S09 + endpoints.
**Repos**: [specs] [backend]

##### T1.1.1 [specs] — Doubt lifecycle + persistence contracts in 11/03
- **Build**: Create `target/requirements/11_haitu_ai_layer.md` (fall back to `vision/requirements/08_haitu_ai_layer.md` for source content) and document: the doubt lifecycle states (new → ai_answered → escalated → answered → resolved → auto_closed), the SSE event `doubt_id` (emitted after validation, before first token), the persistence contract (student message written in validation phase AFTER rate-limit; AI message + haitu_attempted via post-stream background task with a FRESH session), and the orphan-on-429 / partial-text-on-disconnect guarantees. In `target/requirements/03_student.md` add the S08 (doubt inbox) + S09 (doubt thread) screen descriptions and the student doubt endpoints (GET /api/students/me/doubts, GET /api/students/me/doubts/{id}, POST /api/students/me/doubts/{id}/messages).
- **Done when**: 11_haitu_ai_layer.md describes the doubt lifecycle + doubt_id SSE event + persistence guarantees, and 03_student.md describes S08/S09 + the student endpoints.
- **Test**: `grep -q "doubt_id" target/requirements/11_haitu_ai_layer.md` exits 0.
- **Depends on**: None

##### T1.1.2 [backend] — V35 migration: doubts + doubt_messages
- **Build**: Create alembic/versions/V35_doubts.py (down_revision="V34"): `doubts(id UUID PK, student_sub TEXT NOT NULL, topic_id UUID FK→topics NULL, course_path_node_id UUID FK NULL, title TEXT, status VARCHAR(20) NOT NULL DEFAULT 'new' CHECK in (new,ai_answered,escalated,answered,resolved,auto_closed), escalated_to TEXT NULL, haitu_attempted BOOL DEFAULT false, auto_close_at TIMESTAMPTZ NOT NULL DEFAULT now()+interval '7 days', resolved_at TIMESTAMPTZ NULL, created_at, updated_at)`; `doubt_messages(id UUID PK, doubt_id UUID FK→doubts ON DELETE CASCADE, sender_type VARCHAR(10) CHECK in (student,ai,teacher,system) NOT NULL, content TEXT NOT NULL, created_at)`; indexes idx_doubts_student_sub, idx_doubts_status, idx_doubts_auto_close (partial WHERE status!='resolved' AND auto_close_at<=now()), idx_doubt_messages_doubt_id. `student_sub` is a raw `TEXT` with NO FK (no local users — Keycloak sub as raw string, per CLAUDE.md).
- **Done when**: `alembic upgrade V35` creates both tables with CHECK constraints + indexes; `alembic downgrade V34` reverses.
- **Test**: `assert "doubts" in inspector.get_table_names()` after upgrade.
- **Depends on**: T1.1.1 [specs], T0.2 [backend] (head is on main)

##### T1.1.3 [backend] — Doubt + DoubtMessage domain models (imperative)
- **Build**: Create src/domain/models/doubt.py — `@dataclass Doubt(...)` + `@dataclass DoubtMessage(...)` (plain dataclasses, no Base). Create src/infrastructure/models/doubt.py — `doubts` + `doubt_messages` Tables mirroring V35; `registry_mapper.map_imperatively(Doubt, doubts)` + `map_imperatively(DoubtMessage, doubt_messages)`; import in src/infrastructure/models/__init__.py.
- **Done when**: Doubt + DoubtMessage round-trip through a session (insert + select returns populated dataclasses, no Base subclassing).
- **Test**: `assert isinstance(loaded, Doubt) and loaded.status == "new"` after insert/select.
- **Depends on**: T1.1.2 [backend]

##### T1.1.4 [backend] — Doubt Pydantic schemas
- **Build**: Create src/schemas/doubt.py — `DoubtRead`, `DoubtMessageRead`, `DoubtThreadResponse(doubt, messages)`, `DoubtListResponse(items)`, `CreateDoubtMessageRequest(content)`. `from_attributes` config.
- **Done when**: `DoubtThreadResponse` serializes a Doubt + messages to valid JSON with sender_type + content per message.
- **Test**: `assert serialized["doubt"]["status"] == "new" and len(serialized["messages"]) >= 1`.
- **Depends on**: T1.1.3 [backend]

##### T1.1.5 [backend] — DoubtRepository + DoubtMessageRepository
- **Build**: src/domain/repositories/doubt_repository.py — `AbstractDoubtRepository`: `find_open_by_student_and_topic(student_sub, topic_id) -> Doubt | None` (status NOT IN (resolved, auto_closed)), `create(...)`, `add_message(doubt_id, sender_type, content)`, `get_with_messages(doubt_id) -> DoubtThread`, `list_by_student(student_sub)`, `update_status(doubt_id, status)`, `mark_haitu_attempted(doubt_id)`. Concrete repos in src/infrastructure/repositories/.
- **Done when**: `find_open_by_student_and_topic` returns an existing open doubt (no new row); `create` + `add_message` persist a thread retrievable via `get_with_messages`.
- **Test**: `assert thread.doubt.id == thread.messages[0].doubt_id` after create + add_message + get_with_messages.
- **Depends on**: T1.1.3 [backend]

##### T1.1.6 [backend] — DoubtService (find-or-create + message writers)
- **Build**: src/domain/services/doubt_service.py — `DoubtService(doubt_repo, message_repo)`: `find_or_create_doubt(student_sub, topic_id, node_id, title) -> Doubt` (reuses an open doubt for the same student+topic else creates one with auto_close_at=now+7d), `add_student_message`, `add_ai_message`, `get_thread`, `list_student_doubts`. Pure domain logic, session-injected.
- **Done when**: two `find_or_create_doubt` calls for the same (student, topic) return the same doubt id (no duplicate); student + ai messages append in order.
- **Test**: `assert d1.id == d2.id` for two find_or_create calls with identical (student_sub, topic_id).
- **Depends on**: T1.1.5 [backend]

##### T1.1.7 [backend] — Student doubt routes (S08/S09 read endpoints)
- **Build**: Create src/api/routes/doubts.py with a student sub-router: `GET /api/students/me/doubts` (list), `GET /api/students/me/doubts/{doubt_id}` (thread with messages), both guarded by `Depends(require_student())` + strict current-role + ownership (doubt.student_sub == user.sub else 404). Register the student sub-router in src/api/router.py under `/api/students`.
- **Done when**: GET list returns 200 with the student's doubts; GET thread returns the thread; another student's doubt → 404.
- **Test**: `assert response.status_code == 200 and "items" in response.json()` for GET /api/students/me/doubts with X-Current-Role: student.
- **Depends on**: T1.1.4 [backend], T1.1.6 [backend]

### G1.2 — hAITU persistence + doubt_id SSE
**Subgoal**: The hAITU topic-doubt endpoint persists the doubt + student message (validation phase, after rate-limit) and the AI message + haitu_attempted (post-stream background task, fresh session), emits a doubt_id SSE event, and handles 429 + disconnect without orphan rows.
**Subgoal test**: A successful hAITU stream leaves exactly one doubts row + student msg + AI msg + haitu_attempted=true; the client receives a doubt_id SSE event; a 429 leaves ZERO doubts rows; a mid-stream disconnect persists whatever AI text was produced and marks haitu_attempted.
**Repos**: [backend]

##### T1.2.1 [backend] — Persist doubt + student message in validation phase (post rate-limit)
- **Build**: In src/api/routes/haitu.py POST /api/haitu/topic-doubt, AFTER the HaituRateLimiter check (so a 429 never writes), in the validation phase: `DoubtService.find_or_create_doubt(...)` then `add_student_message(doubt_id, query)`; pass doubt_id into the streaming coroutine. Commit the request session before streaming begins (per Phase 3 SSE pattern: session.close() BEFORE streaming). Preserve the existing `Depends(validate_csrf)` on the POST (CSRF on every mutation — do not drop it when adding persistence).
- **Done when**: a request that passes the rate limiter creates/updates exactly one doubts row + one student doubt_message; a request that returns 429 creates ZERO doubts rows.
- **Test**: `assert doubt_count == 0` after a request that returns 429.
- **Depends on**: T1.1.6 [backend], T1.1.7 [backend]

##### T1.2.2 [backend] — Emit doubt_id SSE event + persist AI message post-stream (fresh session)
- **Build**: In the hAITU streaming response, emit `event: doubt_id\ndata: {"doubt_id": "..."}\n\n` immediately after validation (before the first token). Accumulate the full AI text; AFTER `await session.close()`, spawn a background task (BackgroundTasks / asyncio.create_task) that opens a FRESH session (own session maker, not the request session) and writes `add_ai_message(doubt_id, full_text)` + `mark_haitu_attempted(doubt_id)`, then commits.
- **Done when**: a completed stream produces a doubts row with haitu_attempted=true + an ai doubt_message with the streamed text, and the client receives the doubt_id event.
- **Test**: `assert ai_msg.sender_type == "ai" and doubt.haitu_attempted is True` after a successful stream.
- **Depends on**: T1.2.1 [backend]

##### T1.2.3 [backend] — No-orphan-on-429 + no-duplicate-on-retry test
- **Build**: Integration test (tests/integration/phase4): (a) a hAITU request returning 429 → assert zero doubts rows; (b) the same (student, topic) query twice successfully → assert exactly ONE doubts row with TWO student messages + TWO ai messages (find-or-create dedup).
- **Done when**: test passes — 429 leaves no rows; two identical queries produce one thread with 2+2 messages.
- **Test**: `assert doubts_count == 1 and student_msgs == 2 and ai_msgs == 2` after two identical successful queries.
- **Depends on**: T1.2.2 [backend]

##### T1.2.4 [backend] — Disconnect/partial-text persistence test
- **Build**: Integration test simulating a client disconnect mid-stream (cancel the request): assert the doubts row exists, haitu_attempted is set, and the ai doubt_message contains whatever partial text was accumulated (possibly empty), and no unhandled exception escapes.
- **Done when**: test passes — a mid-stream disconnect persists the doubt + partial/empty AI text + haitu_attempted, no unhandled exception.
- **Test**: `assert doubt.haitu_attempted is True` after a simulated mid-stream cancel.
- **Depends on**: T1.2.2 [backend]

### G1.3 — Student doubt inbox (S08) + thread (S09) UI
**Subgoal**: The student can browse doubts (S08), reopen a thread (S09) seeing AI + (later) teacher messages, post follow-ups, and the hAITU panel links a doubt to its persisted thread.
**Subgoal test**: A student with one persisted doubt opens /doubts (S08) → sees it listed → opens /doubts/[id] (S09) → sees student + AI messages in order → posts a follow-up → it appears → reopens the hAITU panel for the same topic and sees the persisted history.
**Repos**: [backend] [frontend]

##### T1.3.1 [backend] — Student follow-up message endpoint
- **Build**: In src/api/routes/doubts.py add `POST /api/students/me/doubts/{doubt_id}/messages` (body CreateDoubtMessageRequest) guarded by require_student + `validate_csrf` + ownership; appends a student follow-up via `DoubtService.add_student_message` and returns the updated thread (DoubtThreadResponse).
- **Done when**: POST returns 200 with the thread containing the new student message last; posting to another student's doubt → 404.
- **Test**: `assert response.json()["messages"][-1]["sender_type"] == "student"`.
- **Depends on**: T1.1.7 [backend]

##### T1.3.2 [frontend] — Doubt API client + types
- **Build**: src/features/doubts/types/doubt.types.ts (Doubt, DoubtMessage, DoubtThread, DoubtListResponse) + src/features/doubts/api/doubt-api.ts (`listDoubts`, `getDoubtThread`, `postFollowUp`) using fetchWithCSRFRetry + buildApiHeaders with X-Current-Role: student. Barrel src/features/doubts/index.ts.
- **Done when**: `doubtApi.listDoubts` parses a Doubt[] for a mocked 200 response.
- **Test**: `expect(Array.isArray(result)).toBe(true)` for a mocked list response.
- **Depends on**: T1.3.1 [backend]

##### T1.3.3 [frontend] — S08 doubt inbox page
- **Build**: src/app/doubts/page.tsx — /doubts inside MainLayout + Header, guarded by useAuth (student only); renders Doubt rows (title, topic, status chip, last activity) linking to /doubts/[id]; empty state.
- **Done when**: /doubts renders the student's doubts as clickable rows; empty state shows when none.
- **Test**: `expect(screen.getByText(doubt.title)).toBeInTheDocument()` with mocked list data.
- **Depends on**: T1.3.2 [frontend]

##### T1.3.4 [frontend] — S09 doubt thread page
- **Build**: src/app/doubts/[id]/page.tsx — fetches the thread; renders messages as chat bubbles (student right, ai/teacher left) reusing the HaituDoubtPanel bubble pattern; follow-up composer (textarea + send) calls postFollowUp; status chip; back link to /doubts.
- **Done when**: /doubts/[id] renders messages in order with correct bubble alignment; posting a follow-up appends a student bubble.
- **Test**: `expect(screen.getByRole("textbox")).toBeInTheDocument()` on the thread page.
- **Depends on**: T1.3.3 [frontend]

##### T1.3.5 [frontend] — Link hAITU panel to persisted thread (doubt_id)
- **Build**: In src/features/student/components/haitu-doubt-panel.tsx + useHaituDoubt hook, consume the doubt_id SSE event: (a) show a "View thread" link to /doubts/[doubt_id] after the first AI reply; (b) on re-open for the same topic, pre-load the existing thread from getDoubtThread so history is continuous (not client-side-only).
- **Done when**: after a hAITU reply the panel shows a "View thread" link to /doubts/[doubt_id]; reopening the panel for a topic with an existing doubt shows persisted history.
- **Test**: `expect(screen.getByRole("link", { name: /view thread/i })).toBeInTheDocument()` after a mocked hAITU reply with a doubt_id.
- **Depends on**: T1.3.4 [frontend], T1.2.2 [backend] (doubt_id SSE event)

##### T1.3.6 [frontend] — Student "My Doubts" nav link
- **Build**: Add a "My Doubts" nav link to the student navigation (S-nav/topbar), visible only for X-Current-Role: student, linking to /doubts; reuse the existing role-gated nav-item pattern.
- **Done when**: a logged-in student sees the "My Doubts" nav item; parent/instructor do not.
- **Test**: `expect(screen.getByRole("link", { name: /my doubts/i })).toBeInTheDocument()` for a mocked student.
- **Depends on**: T1.3.3 [frontend]

**G1 integration test**: E2E — a student asks a hAITU doubt → AI streams a reply → client receives doubt_id → student opens /doubts (S08) → opens /doubts/[id] (S09) → sees student + AI messages → posts a follow-up → it appears → reopens the hAITU panel for the same topic and sees persisted history. A second identical query does NOT create a second doubt (find-or-create). A 429 leaves no doubt row. A mid-stream disconnect still persists the doubt + partial text.

---

## G2 — Teacher escalation

**Goal**: A student can escalate a doubt to a teacher, any instructor can see and claim escalated doubts from a shared queue, and the teacher's reply is persisted into the thread and visible to the student — without an orgs/classes model (shared instructor queue, escalated_to=NULL until claimed).
**Goal test**: A student escalates a doubt → an instructor's shared queue (T06) shows it → the instructor replies → the student's thread (S09) shows the teacher reply + status='answered' — all with escalated_to=NULL until claimed (no orgs/classes routing).
**Repos**: [specs] [backend] [frontend]

### G2.1 — Teacher doubt routes (shared instructor queue)
**Subgoal**: Backend exposes the student escalate endpoint and the teacher-facing doubt routes (shared queue list, claim, reply) guarded by require_instructor, with shared-queue routing (escalated_to=NULL until claimed), each mounted at the right path.
**Subgoal test**: A student POST escalate → status='escalated' (reachable at /api/doubts/{id}/escalate); an instructor GET /api/teachers/me/doubts sees it; the instructor POST reply → status='answered' + a teacher doubt_message; another instructor does not see it as unclaimed after claim.
**Repos**: [specs] [backend]

##### T2.1.1 [specs] — Teacher doubt contracts in 04/11
- **Build**: In `target/requirements/04_teacher_tutor.md` add T06 (teacher doubt inbox — shared queue) + T07 (teacher doubt thread/reply) screen descriptions and teacher endpoints (GET /api/teachers/me/doubts — shared queue; POST /api/teachers/me/doubts/{id}/claim; POST /api/teachers/me/doubts/{id}/messages — teacher reply) and the student escalate endpoint POST /api/doubts/{id}/escalate. In `target/requirements/11_haitu_ai_layer.md` document the escalate lifecycle (new/ai_answered → escalated → answered) + the shared-queue routing decision (escalated_to NULL until claimed; any instructor can reply; no orgs/classes in v1).
- **Done when**: both files document T06/T07, the teacher + escalate endpoints, and the shared-queue + escalate lifecycle.
- **Test**: `grep -q "shared" target/requirements/04_teacher_tutor.md` exits 0.
- **Depends on**: T1.1.1 [specs]

##### T2.1.2a [backend] — Student escalate endpoint + mount doubts router at /api/doubts
- **Build**: In src/api/routes/doubts.py add `POST /api/doubts/{doubt_id}/escalate` (require_student + `validate_csrf` + ownership) → status='escalated', escalated_to=NULL. Register a `doubts` router at `/api/doubts` in src/api/router.py so the top-level escalate route is reachable (the student read routes live under /api/students from T1.1.7; escalate lives at /api/doubts/{id}/escalate).
- **Done when**: POST /api/doubts/{id}/escalate returns 200 and doubt.status='escalated'; the route is reachable at /api/doubts/{id}/escalate.
- **Test**: `assert response.status_code == 200 and doubt.status == "escalated"` after POST escalate.
- **Depends on**: T1.1.6 [backend], T1.1.7 [backend]

##### T2.1.2b [backend] — Teacher queue GET + claim (mount teacher sub-router under /api/teachers)
- **Build**: In src/api/routes/doubts.py add `GET /api/teachers/me/doubts` (require_instructor — strict current_role, 400 if header missing/other) → escalated doubts where escalated_to IS NULL (unclaimed) OR escalated_to=user.sub (mine), newest first, with student name + topic title; `POST /api/teachers/me/doubts/{doubt_id}/claim` (require_instructor + `validate_csrf`) → escalated_to=user.sub if NULL (409 if already claimed by another). Register the teacher sub-router in src/api/router.py under `/api/teachers`.
- **Done when**: GET /api/teachers/me/doubts returns the shared queue for an instructor; claim sets escalated_to and blocks double-claim (409).
- **Test**: `assert response.status_code == 200 and "items" in response.json()` for GET /api/teachers/me/doubts with X-Current-Role: instructor.
- **Depends on**: T2.1.2a [backend] (doubts router + DoubtService exist)

##### T2.1.2c [backend] — Teacher reply endpoint
- **Build**: In src/api/routes/doubts.py add `POST /api/teachers/me/doubts/{doubt_id}/messages` (require_instructor + `validate_csrf`) → appends a teacher doubt_message, sets status='answered'. (The doubt_teacher_replied notification is wired in T3.4.3, not here.)
- **Done when**: teacher reply appends a teacher message + sets status='answered'.
- **Test**: `assert response.json()["messages"][-1]["sender_type"] == "teacher"`.
- **Depends on**: T2.1.2b [backend]

##### T2.1.3 [backend] — Teacher doubt schemas
- **Build**: Add to src/schemas/doubt.py: `TeacherDoubtRead(doubt, student_name, topic_title, escalated_to, last_message_at)`, `TeacherDoubtListResponse(items)`, `ClaimResponse(doubt_id, escalated_to)`. from_attributes.
- **Done when**: GET /api/teachers/me/doubts serializes to TeacherDoubtListResponse with student_name + topic_title populated.
- **Test**: `assert item["student_name"] and item["doubt"]["status"] == "escalated"`.
- **Depends on**: T2.1.2b [backend], T2.1.2c [backend]

### G2.2 — Teacher doubt inbox (T06) + reply (T07) UI
**Subgoal**: An instructor can browse the shared escalated-doubt queue (T06), claim a doubt, open the thread (T07), and reply — and the reply persists and is visible to the student.
**Subgoal test**: An instructor opens /teacher/doubts (T06) → sees escalated doubts → claims one → opens /teacher/doubts/[id] (T07) → replies → the student's S09 thread shows the teacher reply.
**Repos**: [frontend]

##### T2.2.1 [frontend] — Teacher doubt API client + types
- **Build**: Extend src/features/doubts/api/doubt-api.ts with `listTeacherDoubts`, `claimDoubt`, `postTeacherReply` using fetchWithCSRFRetry + X-Current-Role: instructor; add TeacherDoubt types to doubt.types.ts.
- **Done when**: `doubtApi.listTeacherDoubts` parses TeacherDoubt[] for a mocked 200.
- **Test**: `expect(Array.isArray(result)).toBe(true)` for a mocked teacher list response.
- **Depends on**: T2.1.3 [backend]

##### T2.2.2 [frontend] — T06 teacher doubt inbox page
- **Build**: src/app/teacher/doubts/page.tsx — /teacher/doubts inside MainLayout + Header, guarded by useAuth (instructor only); renders the shared queue as rows (student name, topic, question preview, time, "Claim" button); Claim calls claimDoubt then navigates to /teacher/doubts/[id]; already-claimed-by-me doubts show "Open"; empty state.
- **Done when**: /teacher/doubts renders escalated doubts with Claim buttons; clicking Claim claims (or shows "Open" if mine) and navigates to the thread.
- **Test**: `expect(screen.getByRole("button", { name: /claim/i })).toBeInTheDocument()` with mocked queue.
- **Depends on**: T2.2.1 [frontend]

##### T2.2.3 [frontend] — T07 teacher doubt thread + reply page
- **Build**: src/app/teacher/doubts/[id]/page.tsx — fetches the thread; renders student + AI + teacher messages (teacher distinct styling); reply composer (textarea + send) calls postTeacherReply and appends a teacher bubble; shows student name + topic; back link to /teacher/doubts. Reuse bubble pattern from S09.
- **Done when**: /teacher/doubts/[id] renders the thread + a working reply composer that appends the teacher message.
- **Test**: `expect(screen.getByRole("textbox")).toBeInTheDocument()` on the teacher thread page.
- **Depends on**: T2.2.2 [frontend]

##### T2.2.4 [frontend] — Teacher "Doubt Queue" nav link
- **Build**: Add a "Doubt Queue" nav link to the instructor navigation, visible only for X-Current-Role: instructor, linking to /teacher/doubts; reuse the role-gated nav-item pattern.
- **Done when**: a logged-in instructor sees the "Doubt Queue" nav item; a student does not.
- **Test**: `expect(screen.getByRole("link", { name: /doubt queue/i })).toBeInTheDocument()` for a mocked instructor.
- **Depends on**: T2.2.2 [frontend]

### G2.3 — Student "Request teacher help" activation
**Subgoal**: The student can escalate a doubt to a teacher from the S09 thread (and the hAITU panel), completing the student→teacher loop.
**Subgoal test**: A student on /doubts/[id] (S09) clicks "Request teacher help" → status='escalated' + a system note "Escalated to a teacher"; the button is hidden once escalated/answered; the hAITU panel's escalate button now works (not the Phase 3 disabled placeholder).
**Repos**: [frontend]

##### T2.3.1 [frontend] — Escalate CTA in S09 (+ hAITU panel)
- **Build**: In src/app/doubts/[id]/page.tsx add a "Request teacher help" button (visible when status in (new, ai_answered)) calling `doubtApi.escalateDoubt` (new method → POST /api/doubts/{id}/escalate); on success update the status chip + append a system note "Escalated to a teacher — you'll be notified when they reply" and hide the button. Also enable the escalation button in the hAITU panel (replacing the Phase 3 disabled placeholder) to escalate the current doubt_id.
- **Done when**: clicking "Request teacher help" escalates (status='escalated'), shows the system note, hides the button; the hAITU panel's escalate button works (not disabled).
- **Test**: `expect(screen.queryByRole("button", { name: /request teacher help/i })).toBeNull()` after a successful escalation.
- **Depends on**: T2.2.3 [frontend], T2.1.2a [backend], T1.3.5 [frontend]

**G2 integration test**: E2E — a student escalates a doubt from S09 → an instructor opens T06 and sees it in the shared queue → claims it → opens T07 → replies → the student's S09 thread shows the teacher reply and status='answered' (with a doubt_teacher_replied notification once G3.4 is wired). Shared-queue routing works with no orgs/classes (escalated_to=NULL until claim).

---

## G3 — Notifications subsystem

**Goal**: A generic notification subsystem (not doubt-only) lets any backend part raise notifications for a user or a role-shared queue, a bell + feed UI shows them across all roles with 60s polling, and the doubt lifecycle events (escalation, teacher reply, auto-close) are wired to emit notifications.
**Goal test**: A doubt escalation creates a notification visible to all instructors; a teacher reply creates a notification for the student; the student's bell badge reflects unread count and updates every 60s (pausing when the tab is hidden); a 7-day-stale doubt is auto-closed by the worker cron with a notification to the student.
**Repos**: [specs] [backend] [frontend] [deploy]

### G3.1 — Notification schema + service
**Subgoal**: The notifications table (V36) is migrated and mapped, a generic NotificationService can create a personal or shared-queue notification, and a pluggable parent fan-out stub is in place (no-op when no parent-child links exist).
**Subgoal test**: `alembic upgrade V36` creates notifications; `NotificationService.create(recipient_sub=None, recipient_role='instructor', ...)` inserts a shared-queue row; `fan_out_to_parents(child_sub, ...)` returns [] with no error when no parent_child_links exist.
**Repos**: [specs] [backend]

##### T3.1.1 [specs] — Fill 10_notifications.md with the notification contract
- **Build**: Fill `target/requirements/10_notifications.md` (fall back to `vision/requirements/10_notifications.md`) with: the notifications table contract (id, recipient_idp_sub NULLABLE, recipient_role, type, title, body, action_url, read, created_at), shared-queue semantics (NULL recipient_idp_sub + recipient_role = role-wide), the 4 endpoints + per-role feed filtering + 90-day window (BR-NOTIF-003), 60s visibility-aware polling, the auto-close cron (BR-NOTIF-011, hourly, 7-day auto_close_at), and the event types (new_doubt_escalated, doubt_teacher_replied, doubt_auto_closed, child_doubt_replied, child_doubt_auto_closed, topic_marked_weak, student_at_risk).
- **Done when**: 10_notifications.md documents the table, shared-queue semantics, 4 endpoints, polling, cron, and event types.
- **Test**: `grep -q "recipient_idp_sub" target/requirements/10_notifications.md` exits 0.
- **Depends on**: None

##### T3.1.2 [backend] — V36 migration: notifications
- **Build**: Create alembic/versions/V36_notifications.py (down_revision="V35"): `notifications(id UUID PK, recipient_idp_sub TEXT NULL, recipient_role VARCHAR(20) NOT NULL, type VARCHAR(40) NOT NULL, title TEXT NOT NULL, body TEXT, action_url TEXT NULL, read BOOL NOT NULL DEFAULT false, created_at TIMESTAMPTZ NOT NULL DEFAULT now())`; indexes idx_notifications_recipient (recipient_idp_sub), idx_notifications_role_unread (recipient_role, read), partial idx_notifications_unread_personal WHERE read=false AND recipient_idp_sub IS NOT NULL, idx_notifications_shared_unread WHERE read=false AND recipient_idp_sub IS NULL. No FK on recipient_idp_sub (no local users — Keycloak sub as raw string).
- **Done when**: `alembic upgrade V36` creates notifications with nullable recipient_idp_sub + indexes; `alembic downgrade V35` reverses.
- **Test**: `assert "notifications" in inspector.get_table_names()` after upgrade.
- **Depends on**: T3.1.1 [specs], T1.1.2 [backend] (V35 is the prior migration)

##### T3.1.3 [backend] — Notification model + repository
- **Build**: src/domain/models/notification.py (`@dataclass Notification`) + src/infrastructure/models/notification.py (`notifications` Table + map_imperatively). src/domain/repositories/notification_repository.py — `AbstractNotificationRepository`: `create(...)`, `list_for_user(sub, role, limit, offset)` (personal OR shared-queue for role, 90-day window), `mark_read(id, sub, role)`, `mark_all_read(sub, role)`, `count_unread(sub, role)`. The list query: `WHERE (recipient_idp_sub = :sub OR (recipient_idp_sub IS NULL AND recipient_role = :role)) AND created_at >= now() - interval '90 days'`. Concrete repo in src/infrastructure/repositories/.
- **Done when**: `list_for_user` returns both personal + shared-queue rows for the role; `mark_read` on a shared-queue row marks it read; `count_unread` sums personal + shared.
- **Test**: `assert len(feed) == 2` (1 personal + 1 shared) for an instructor with one of each.
- **Depends on**: T3.1.2 [backend]

##### T3.1.4 [backend] — NotificationService (generic + pluggable parent fan-out stub)
- **Build**: src/domain/services/notification_service.py — `NotificationService(notification_repo, parent_link_repo)`: `create(recipient_sub: str | None, recipient_role, type, title, body, action_url=None) -> Notification` (None recipient → shared queue for the role) and `fan_out_to_parents(child_sub, type, title, body, action_url) -> list[Notification]` — queries parent_child_links for active links where child_sub = :child_sub; if zero rows (v1) returns [] with no error (no-op stub); documents the v1 limitation in the docstring.
- **Done when**: `create(None, 'instructor', ...)` inserts a shared-queue row (recipient_idp_sub NULL); `fan_out_to_parents(unlinked_child, ...)` returns [] and inserts zero rows, no exception.
- **Test**: `assert result == []` for fan_out_to_parents with no parent links.
- **Depends on**: T3.1.3 [backend]

### G3.2 — Notification endpoints + APISIX routes
**Subgoal**: The four vision notification API endpoints (feed, mark-read, mark-all-read, unread-count) are implemented behind the standard current-role + CSRF guards with per-role feed filtering and shared-instructor-queue inclusion, and APISIX routes notification paths through the secured-api OIDC + CSRF pattern (doubt paths are already covered by the catch-all routes).
**Subgoal test**: An instructor with `X-Current-Role: instructor` has one shared-queue `new_doubt_escalated` row (recipient_idp_sub NULL, recipient_role='instructor') and one personal unread notification. `GET /api/notifications/me` → 200, `items` contains both rows and `unread_count=2`. `PATCH /api/notifications/{shared_id}/read` → 200 `{"read": true}`. `GET /api/notifications/me/unread-count` → 200 `count=1`. `PATCH /api/notifications/me/read-all` body `{role:"instructor"}` → 200 `marked_count=1`. Re-fetch unread-count → `count=0`. A student calling `GET /api/notifications/me` does NOT see the instructor shared-queue row.
**Repos**: [backend] [deploy]

##### T3.2.1 [backend] — 4 notification routes + schemas
- **Build**: Create src/api/routes/notifications.py (`router = APIRouter()`) and src/schemas/notifications.py. Schemas: `NotificationRead` (id, type, title, body, action_url, read, created_at, group: Literal["today","yesterday","earlier","older"]), `NotificationFeedResponse` (unread_count, items), `UnreadCountResponse` (count), `ReadAllRequest` (role), `ReadAllResponse` (marked_count). Factory `get_notification_service(session)`. Four endpoints, all guarded by `Depends(current_active_user)` (strict — valid X-Current-Role, any role); mutations additionally `Depends(validate_csrf)`:
  - `GET /me` (limit=50, offset=0) → `NotificationFeedResponse`. Filter: `WHERE (recipient_idp_sub = :sub OR (recipient_idp_sub IS NULL AND recipient_role = :role)) AND created_at >= now() - interval '90 days' ORDER BY created_at DESC LIMIT :limit OFFSET :offset` with `:sub = user.sub`, `:role = user.current_role.value`. Compute `group` from created_at vs today.
  - `PATCH /{notification_id}/read` → `{"read": true}`. `UPDATE notifications SET read=true WHERE id = :id AND (recipient_idp_sub = :sub OR (recipient_idp_sub IS NULL AND recipient_role = :role))`. 404 if 0 rows. Docstring caveat: marking a NULL-recipient shared notification read marks it read globally for the entire instructor queue (known v1 limitation).
  - `PATCH /me/read-all` (body ReadAllRequest) → `ReadAllResponse`. Validate `body.role == user.current_role.value` (403 if mismatch). `UPDATE notifications SET read=true WHERE read=false AND ((recipient_idp_sub = :sub AND recipient_role = :role) OR (recipient_idp_sub IS NULL AND recipient_role = :role))`. Return marked_count = rowcount.
  - `GET /me/unread-count` → `UnreadCountResponse`. `SELECT COUNT(*) WHERE read=false AND (recipient_idp_sub = :sub OR (recipient_idp_sub IS NULL AND recipient_role = :role))`.
  Register in src/api/router.py: `app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])`.
- **Done when**: `GET /api/notifications/me` returns 200 with `unread_count` + `items` for an authenticated user with valid X-Current-Role; `PATCH /api/notifications/{id}/read` returns `{"read": true}`; the OpenAPI spec lists all four paths under `/api/notifications`.
- **Test**: `assert response.status_code == 200 and "unread_count" in response.json()` for `GET /api/notifications/me` with header `X-Current-Role: student`.
- **Depends on**: T3.1.4 [backend]

##### T3.2.2 [deploy] — APISIX route for /api/notifications/* (doubt paths already covered)
- **Build**: Create common/routes/20-api-notifications.json — dedicated route for `/api/notifications/*` (GET, PATCH) at priority 15 (beats the catch-all `/api/*` at priority 10), `plugin_config_id: "secured-api"`, `limit-count: {count: 60, time_window: 60, key_type: var, key: remote_addr, rejected_code: 429}` (allows the 60s polling cadence) and `request-validation` requiring `Content-Type: application/json` for PATCH. Upstream `backend:8000`, standard 6s timeout. Verify (no new file) that the doubt paths — `/api/students/me/doubts`, `/api/teachers/me/doubts`, `/api/doubts/{id}/escalate` — are already covered by the existing catch-all routes 04-api-read.json (GET, priority 10) + 05-api-write.json (POST/PATCH, priority 10), both `plugin_config_id: "secured-api"` (OIDC at gateway, CSRF enforced at FastAPI). Document this coverage in the `desc` field of 20-api-notifications.json.
- **Done when**: `20-api-notifications.json` exists with `secured-api` plugin config; an unauthenticated `curl http://localhost:9080/api/notifications/me` returns 401; an unauthenticated `curl http://localhost:9080/api/students/me/doubts` returns 401 (doubt paths covered by catch-all secured-api).
- **Test**: `assert curl_response_code == 401` for unauthenticated `GET http://localhost:9080/api/notifications/me`.
- **Depends on**: T3.2.1 [backend]

### G3.3 — Notification bell + feed UI
**Subgoal**: A notification bell with unread-count badge is rendered in the shared topbar for all roles, a `/notifications` feed page lists notifications grouped by recency with mark-read and mark-all-read actions, and a `useNotifications` hook polls unread-count every 60s with visibility-aware pausing (BR-NOTIF-003).
**Subgoal test**: A student with 2 unread notifications loads `/home` — the bell badge shows "2"; clicking the bell navigates to `/notifications` which lists 2 items under group section headers; clicking one item marks it read (badge decrements to 1); clicking "Mark all read" sets the badge to 0; with the tab hidden, polling pauses; on tab focus, it resumes and refreshes.
**Repos**: [frontend]

##### T3.3.1 [frontend] — Notification types + API + useNotifications (60s poll)
- **Build**: src/features/notifications/types/notification.types.ts with `Notification`, `NotificationFeedResponse`, `UnreadCountResponse`, `ReadAllResponse`. src/features/notifications/api/notification-api.ts — `notificationApi`: `getFeed`, `getUnreadCount`, `markRead`, `markAllRead`, all via fetchWithCSRFRetry + buildApiHeaders with X-Current-Role. src/features/notifications/hooks/use-notifications.ts — `useNotifications(csrfToken, currentRole)` using useState/useEffect only (NO Redux, NO Axios): polls getUnreadCount every 60_000 ms; registers a visibilitychange listener that pauses the interval when `document.visibilityState === 'hidden'` and resumes + immediately refreshes on `visible` (BR-NOTIF-003); exposes `{ unreadCount, notifications, loading, markRead, markAllRead, refreshFeed }`. Barrel src/features/notifications/index.ts.
- **Done when**: `useNotifications` returns an `unreadCount` number that updates after a `markRead` call; a visibilitychange listener is registered after mount.
- **Test**: `expect(typeof result.unreadCount).toBe("number")` after rendering the hook with a mocked fetch returning `{"count": 3}`.
- **Depends on**: T3.2.1 [backend]

##### T3.3.2 [frontend] — NotificationBell + feed page
- **Build**: src/features/notifications/components/notification-bell.tsx — bell icon `<button>` with unread-count badge (red pill, `aria-label="Notifications"`, hidden when count=0); onClick navigates to /notifications via next/navigation useRouter().push. src/features/notifications/components/notification-feed.tsx — lists Notification items grouped by `group` (section headers: Today / Yesterday / Earlier this week / Older); each item renders title + body + relative time + an `<a>` to action_url; clicking an item calls markRead(id) then navigates; a "Mark all read" button calls markAllRead. src/app/notifications/page.tsx — /notifications route rendering NotificationFeed inside MainLayout + Header (same pattern as src/app/home/page.tsx), guarded by useAuth (redirects to / if unauthenticated). Empty state: bell + "You're all caught up" (vision §8).
- **Done when**: /notifications renders notification items with group section headers; the bell badge shows the correct unread count; clicking "Mark all read" clears the badge to 0.
- **Test**: `expect(screen.getByText("Mark all read")).toBeInTheDocument()` on the notifications page with mocked feed data containing 1+ items.
- **Depends on**: T3.3.1 [frontend]

##### T3.3.3 [frontend] — Wire bell into shared topbar (all roles)
- **Build**: Modify src/components/layout/header/header.tsx — import NotificationBell; render `<NotificationBell csrfToken={csrfToken} currentRole={user.currentRole} />` inside rightSection immediately before UserMenuDropdown, visible for all authenticated roles. The bell is hidden when no user is logged in (gated by the existing `user.name ?` conditional on rightSection). Export NotificationBell from src/features/notifications/index.ts.
- **Done when**: the bell with unread badge is visible in the header for a logged-in student; the badge count matches the API; clicking the bell navigates to /notifications.
- **Test**: `expect(screen.getByRole("button", { name: /notifications/i })).toBeInTheDocument()` in the header for a mocked authenticated user.
- **Depends on**: T3.3.2 [frontend]

### G3.4 — Auto-close cron + wire doubt events
**Subgoal**: A hourly worker cron auto-closes doubts past their 7-day auto_close_at (BR-NOTIF-011), and the three doubt lifecycle events — escalation, teacher reply, auto-close — emit their respective notifications via NotificationService from G3.1.
**Subgoal test**: Seed a doubt with auto_close_at = now()-1h and status='pending'; run the auto-close cron once; assert status='resolved', a doubt_messages row with sender_type='ai' and body "This doubt was automatically closed after 7 days of inactivity." exists, and a doubt_auto_closed notification exists for the student. Separately: POST /api/doubts/{id}/escalate creates a new_doubt_escalated notification (recipient_idp_sub NULL, recipient_role='instructor'); the teacher reply endpoint creates a doubt_teacher_replied notification for the student.
**Repos**: [backend]

##### T3.4.1 [backend] — Auto-close cron loop in worker
- **Build**: Create src/worker/auto_close_loop.py with `async def auto_close_doubts_loop(session_maker, poll_interval_seconds=3600)` — each tick: `SELECT id, student_sub, topic_id FROM doubts WHERE status != 'resolved' AND auto_close_at <= now()` (uses idx_doubts_auto_close); for each: (1) `UPDATE doubts SET status='resolved', resolved_at=now() WHERE id=:id`; (2) `INSERT INTO doubt_messages (doubt_id, sender_type, content) VALUES (:id, 'ai', 'This doubt was automatically closed after 7 days of inactivity.')`; (3) `NotificationService.create(recipient_sub=student_sub, recipient_role='student', type='doubt_auto_closed', title='Your doubt was closed', body='...', action_url=f'/doubts/{doubt_id}')`; (4) `NotificationService.fan_out_to_parents(child_sub=student_sub, type='child_doubt_auto_closed', ...)` (stub no-op). Commit per doubt. Register in src/worker/__main__.py as a 6th coroutine: `t6 = asyncio.create_task(auto_close_doubts_loop(async_session_maker, settings), name="auto_close")`; append t6 to all_tasks.
- **Done when**: after one cron tick on a DB with a doubt where auto_close_at <= now() and status != 'resolved', the doubt's status='resolved' and a notifications row type='doubt_auto_closed' / recipient_role='student' exists for that student's recipient_idp_sub.
- **Test**: `assert doubt.status == "resolved"` after running auto_close_doubts_loop once (poll_interval_seconds=0) against a seeded doubt with auto_close_at = now() - timedelta(hours=1).
- **Depends on**: T3.1.4 [backend], T1.1.2 [backend] (V35 auto_close_at + idx), T1.1.5 [backend] (DoubtRepository)

##### T3.4.2 [backend] — Wire new_doubt_escalated into escalate endpoint
- **Build**: In the escalate endpoint (POST /api/doubts/{id}/escalate from T2.1.2a, in src/api/routes/doubts.py), after status='escalated' is persisted, inject NotificationService and call `NotificationService.create(recipient_sub=None, recipient_role='instructor', type='new_doubt_escalated', title='Student needs your help', body=f'{student_name} has a question about {topic_title}', action_url=f'/teacher/doubts/{doubt_id}')`. Resolve student_name from the student profile, topic_title from the topic record (same session). Targets the instructor shared queue (NULL recipient_idp_sub + recipient_role='instructor').
- **Done when**: after POST /api/doubts/{id}/escalate returns 200, a notifications row exists with recipient_idp_sub IS NULL, recipient_role='instructor', type='new_doubt_escalated', action_url containing the doubt ID.
- **Test**: `assert notif.recipient_idp_sub is None and notif.type == "new_doubt_escalated"` after calling escalate and querying notifications.
- **Depends on**: T2.1.2a [backend], T3.1.4 [backend]

##### T3.4.3 [backend] — Wire doubt_teacher_replied into teacher reply
- **Build**: In the teacher reply endpoint (POST /api/teachers/me/doubts/{id}/messages with sender_type='teacher' from T2.1.2c), after the teacher message is persisted and status='answered', inject NotificationService and call `NotificationService.create(recipient_sub=doubt.student_sub, recipient_role='student', type='doubt_teacher_replied', title='Teacher replied to your doubt', body=f'{teacher_name} answered your question about {topic_title}', action_url=f'/doubts/{doubt_id}')`; then `NotificationService.fan_out_to_parents(child_sub=doubt.student_sub, type='child_doubt_replied', ...)` (stub no-op). Resolve teacher_name (instructor profile), topic_title (topic record), child_name (student profile).
- **Done when**: after POST /api/teachers/me/doubts/{id}/messages with sender_type='teacher' returns 200, a notifications row exists with recipient_idp_sub = doubt.student_sub, recipient_role='student', type='doubt_teacher_replied'.
- **Test**: `assert notif.type == "doubt_teacher_replied" and notif.recipient_idp_sub == doubt.student_sub` after calling the teacher reply endpoint.
- **Depends on**: T2.1.2c [backend], T3.1.4 [backend]

##### T3.4.4 [backend] — Wire doubt_auto_closed parent fan-out (stub)
- **Build**: In auto_close_doubts_loop (T3.4.1) the fan_out_to_parents call is already in the loop body. This task verifies + documents the stub: `NotificationService.fan_out_to_parents(child_sub, type, title, body, action_url)` queries parent_child_links for active links where child_sub = :child_sub; if zero rows (v1) returns [] with no error (no-op). Add a unit test tests/unit/domain/services/test_notification_service.py that calls fan_out_to_parents with a child_sub having no parent_child_links rows and asserts: zero notifications rows created, no exception. Update the fan_out_to_parents docstring (from T3.1.4) to document the v1 stub behavior.
- **Done when**: fan_out_to_parents(child_sub, ...) returns [] and creates zero notification rows when no parent_child_links exist for the child_sub; no exception; docstring documents the v1 stub.
- **Test**: `assert result == []` when calling fan_out_to_parents with an unlinked child_sub against an empty parent_child_links table.
- **Depends on**: T3.4.1 [backend], T3.1.4 [backend]

**G3 integration test**: E2E — a student escalates a doubt via POST /api/doubts/{id}/escalate → the instructor shared queue (GET /api/notifications/me with X-Current-Role: instructor) shows a new_doubt_escalated notification. The teacher replies via POST /api/teachers/me/doubts/{id}/messages sender_type='teacher' → the student's GET /api/notifications/me shows a doubt_teacher_replied notification and the bell badge increments. The student clicks the notification → PATCH /api/notifications/{id}/read → badge decrements. "Mark all read" → PATCH /api/notifications/me/read-all → unread-count returns 0. A doubt with auto_close_at in the past is picked up by the hourly worker cron → status='resolved', a system doubt_message (sender_type='ai') is appended, a doubt_auto_closed notification appears in the student's feed. Throughout, polling pauses when the tab is hidden and resumes on focus (BR-NOTIF-003).

---

## G4 — Mastery + post-exam review

**Goal**: After a student completes an exam, their per-topic mastery scores are recomputed per BR-PROGRESS-001/002/003, weak topics trigger notifications, the student can review their exam with hAITU explaining wrong answers (S05), and weak-topic flags appear on the student dashboard.
**Repos**: [specs] [backend] [frontend]

### G4.1 — Exam→topic linkage + enrollment_topics schema
**Subgoal**: The enrollment_topics table is migrated (V37), the existing questions.topic_id is confirmed in the live schema + mapped in the Question model, and the EnrollmentTopic domain model + repository are in place — enabling per-topic mastery aggregation from completed exam sessions.
**Subgoal test**: After `alembic upgrade V37`, enrollment_topics exists with (id, enrollment_id, topic_id, status, mastery_score, last_studied_at) + CHECK on status (4 values) and mastery_score (0–100); questions.topic_id is present in the live schema (per 01_data_model.md it is NOT NULL soft FK — verify, add only if absent); EnrollmentTopicRepository.upsert inserts-or-updates and returns the EnrollmentTopic entity; the Question model maps topic_id.
**Repos**: [specs] [backend]

##### T4.1.1 [specs] — 01/03/11: enrollment_topics + exam→topic decision + S05 + exam-review
- **Build**: Update three spec files:
  - `target/requirements/01_data_model.md`: add the enrollment_topics table DDL — id UUID PK, enrollment_id UUID NOT NULL REFERENCES student_enrollments(id) ON DELETE CASCADE, topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE, status VARCHAR(20) NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started','in_progress','completed','weak')), mastery_score INTEGER NOT NULL DEFAULT 0 CHECK (mastery_score >= 0 AND mastery_score <= 100), last_studied_at TIMESTAMPTZ NULL, created_at, updated_at, UNIQUE (enrollment_id, topic_id), index on enrollment_id — per vision §4.3. Document the **exam→topic linkage decision** as an explicit paragraph: "Each question already carries a topic_id (NOT NULL, soft link to topics — existing; unchanged). Per-topic mastery_score is aggregated from exam_session_questions joined to questions.topic_id within a completed session. (Defensive: a question with no usable topic_id contributes to no topic — currently all questions have one.) v1 — a future exam_templates.topic_id for whole-exam tagging is deferred." Do NOT change questions.topic_id.
  - `target/requirements/03_student.md`: add the S05 screen description — a /exam/[session_id]/review route listing questions with wrong/right indicators, a pattern-analysis opening hAITU message, and a per-question hAITU review chat panel on wrong-question click.
  - Create `target/requirements/11_haitu_ai_layer.md` (fall back to `vision/requirements/08_haitu_ai_layer.md`) and confirm the POST /api/haitu/exam-review-chat (§3.2) and POST /api/haitu/pattern-analysis (§3.2a) contracts — attempt_id maps to exam_sessions.id; the route reuses the hAITU LLM provider with a fixed server-side review prompt (NOT the topic-doubt RAG pipeline); 403 if the session doesn't belong to the student or isn't reviewable.
- **Done when**: all three spec files contain the enrollment_topics DDL, the exam→topic linkage decision paragraph, and the S05 / exam-review endpoint description respectively.
- **Test**: `grep -q "enrollment_topics" target/requirements/01_data_model.md` exits 0.
- **Depends on**: None

##### T4.1.2 [backend] — V37 migration: enrollment_topics (+ questions.topic_id only if absent)
- **Build**: Create alembic/versions/V37_enrollment_topics.py (revision="V37", down_revision="V36"). upgrade(): op.create_table("enrollment_topics", id UUID PK server_default gen_random_uuid(), enrollment_id UUID FK→student_enrollments NOT NULL, topic_id UUID FK→topics NOT NULL, status String(20) NOT NULL server_default 'not_started', mastery_score Integer NOT NULL server_default 0, last_studied_at DateTime(timezone=True) NULL, created_at, updated_at, UniqueConstraint(enrollment_id, topic_id), CheckConstraint(status IN (...)), CheckConstraint(mastery_score 0–100)); op.create_index("idx_enrollment_topics_enrollment", "enrollment_topics", ["enrollment_id"]). THEN verify questions.topic_id exists in the live schema (01_data_model.md declares it NOT NULL soft FK): if present, do nothing; if absent, op.add_column("questions", topic_id UUID FK→topics NULL) + op.create_index("idx_questions_topic_id"). downgrade() reverses whatever was added.
- **Done when**: `alembic upgrade V37` succeeds on a DB at V36; enrollment_topics exists with CHECK constraints + UNIQUE (enrollment_id, topic_id); questions.topic_id is present (pre-existing or added); downgrade V36 reverses.
- **Test**: `assert "enrollment_topics" in inspector.get_table_names()` after upgrade V37 on a clean V36 DB.
- **Depends on**: T4.1.1 [specs], T3.1.2 [backend] (V36 is the prior migration)

##### T4.1.3a [backend] — EnrollmentTopic model + repository
- **Build**: src/domain/models/enrollment_topic.py — `@dataclass EnrollmentTopic(id, enrollment_id, topic_id, status="not_started", mastery_score=0, last_studied_at, created_at, updated_at)`. src/infrastructure/models/enrollment_topic.py — `enrollment_topics` Table mirroring V37; `registry_mapper.map_imperatively(EnrollmentTopic, enrollment_topics)`; import in src/infrastructure/models/__init__.py. src/domain/repositories/enrollment_topic_repository.py — `AbstractEnrollmentTopicRepository`: `get_by_enrollment_and_topic(enrollment_id, topic_id) -> EnrollmentTopic | None`, `upsert(enrollment_id, topic_id, status, mastery_score, last_studied_at) -> EnrollmentTopic` (INSERT ... ON CONFLICT (enrollment_id, topic_id) DO UPDATE SET ... RETURNING *), `get_weak_topics(student_sub) -> list[EnrollmentTopic]` (JOIN student_enrollments WHERE student_sub=:sub AND status='weak'), `count_weak_topics(student_sub) -> int`. Concrete EnrollmentTopicRepository in src/infrastructure/repositories/.
- **Done when**: EnrollmentTopicRepository.upsert inserts a new row on first call and updates mastery_score + status on the second call with the same pair, returning the entity both times.
- **Test**: `assert created.status == "weak" and created.mastery_score == 50` after upsert(status="weak", mastery_score=50) on a fresh pair.
- **Depends on**: T4.1.2 [backend]

##### T4.1.3b [backend] — Map questions.topic_id in the Question model
- **Build**: Verify the Question domain + infra models map the existing questions.topic_id column (01_data_model.md declares it NOT NULL soft FK to topics). If src/domain/models/question.py or src/infrastructure/models/question.py omits it, add `topic_id: UUID | None` to the Question dataclass + the questions Table column mapping; ensure QuestionRepository.get_by_ids maps topic_id into the entity. No DB migration (column already exists or added by T4.1.2). This unblocks pattern-analysis (T4.3.1a) using topic context.
- **Done when**: Question entities loaded via QuestionRepository.get_by_ids carry a populated topic_id; the Question dataclass has a topic_id attribute.
- **Test**: `assert question.topic_id is not None` after loading a known topic-tagged question.
- **Depends on**: T4.1.2 [backend] (column present)

### G4.2 — Mastery recalc service
**Subgoal**: MasteryService.recompute_on_session_complete runs on exam submission (and on essay-grading auto-complete), recomputes per-topic mastery_score + status per BR-PROGRESS-001/002/003, and emits topic_marked_weak + student_at_risk notifications when thresholds are crossed.
**Subgoal test**: A student completes a session with 2 questions tagged to topic A (1/2 correct = 50%) and 2 to topic B (2/2 = 100%) — first attempt. After submit, enrollment_topics shows A mastery_score=50 status='weak' and B mastery_score=100 status='completed'; a topic_marked_weak notification exists for the student. A student with 3 weak topics has a student_at_risk notification in the instructor shared queue. A second attempt on A scoring 80% yields mastery_score = round(0.6*80 + 0.4*50) = 68 and status='in_progress'.
**Repos**: [backend]

##### T4.2.1a [backend] — MasteryService + per-topic recalc algorithm
- **Build**: src/domain/services/mastery_service.py — `class MasteryService(enrollment_topic_repo, enrollment_repo, course_path_node_repo, question_repo, topic_repo, session_question_repo, exam_session_repo, notification_service)`. (NOTE: step 4 uses `course_path_node_repo.get_subtree_node_ids(...)` — that method lives on the course-path-node repository, not the enrollment repo.) `async def recompute_on_session_complete(session_id, student_sub) -> None`:
  1. Load exam_session_questions for session_id; load their questions (with topic_id).
  2. Group by question.topic_id (skip a topic_id that is None/unusable — defensive).
  3. Per topic: topic_score_pct = round(sum(earned_points or 0) / sum(points) * 100).
  4. Find the student's enrollment covering the topic: topic's course_path_node_id from topic_repo; enrollment_repo.get_enrolled_node_ids(student_sub); check the topic's node is in course_path_node_repo.get_subtree_node_ids(enrolled_node_ids) (reuse the existing recursive CTE); find the matching enrollment_id via enrollment_repo.find_by_student_and_node. If no enrollment covers the topic, skip it.
  5. existing = enrollment_topic_repo.get_by_enrollment_and_topic(enrollment_id, topic_id). None → first attempt: mastery_score = topic_score_pct. Else → mastery_score = round(0.6*topic_score_pct + 0.4*existing.mastery_score) (BR-PROGRESS-003).
  6. status: <60 → 'weak' (BR-PROGRESS-001); >=75 → 'completed' (BR-PROGRESS-002); else 'in_progress'.
  7. last_studied_at = now(); enrollment_topic_repo.upsert(...).
  Pure service + algorithm; no HTTP/worker hooks in this task.
- **Done when**: calling recompute_on_session_complete on a session with topic-tagged questions writes enrollment_topics rows with mastery_score + status matching BR-PROGRESS-001/002/003; a second attempt applies 0.6*latest + 0.4*previous.
- **Test**: `assert et.status == "weak" and et.mastery_score == 50` for a topic where the student scored 50% on the first attempt after recompute_on_session_complete (called directly).
- **Depends on**: T4.1.3a [backend], T4.1.3b [backend]

##### T4.2.1b [backend] — Wire MasteryService into submit_exam
- **Build**: In src/api/routes/exam_session.py submit_exam, after exam_session_service.recompute_score(session_id), when session.status == ExamStatus.completed (not grading_pending), call `MasteryService.recompute_on_session_complete(session_id, user.sub)`; add a `get_mastery_service(session)` factory wiring all repos + NotificationService, and add it as a submit_exam dependency.
- **Done when**: after POST /api/exam-sessions/{session_id}/submit on a session that transitions to completed, enrollment_topics rows are recomputed for each touched topic.
- **Test**: `assert "enrollment_topics" written` after POST submit on a completed session (assert a weak-topic row exists for a <60% topic).
- **Depends on**: T4.2.1a [backend]

##### T4.2.1c [backend] — Wire MasteryService into essay-grading auto-complete
- **Build**: In src/worker/essay_grading_loop.py `_maybe_autocomplete_session` (the path that transitions a session grading_pending → completed in auto_release mode), call `MasteryService.recompute_on_session_complete(session_id, student_sub)` with the session's student_sub (resolve from exam_session.user_id → str(user_id)). Reuse the same get_mastery_service-style factory built for the worker context.
- **Done when**: when the essay-grading loop auto-completes a session, enrollment_topics rows are recomputed for the touched topics.
- **Test**: `assert enrollment_topics recomputed` after essay_grading_loop auto-completes a session (a weak-topic row exists for a <60% topic).
- **Depends on**: T4.2.1a [backend]

##### T4.2.2 [backend] — topic_marked_weak + student_at_risk notifications
- **Build**: In MasteryService.recompute_on_session_complete (T4.2.1a), after each upsert, check if status transitioned to 'weak' (existing is None or existing.status != 'weak') and new status == 'weak' → `notification_service.create(recipient_sub=student_sub, recipient_role='student', type='topic_marked_weak', title='Topic needs attention', body=f'{topic_title} has been flagged as a weak area', action_url=f'/home/topics/{enrollment_id}')` (topic_title from topic_repo.get_by_id). After all topics processed, if `enrollment_topic_repo.count_weak_topics(student_sub) >= 3` → `notification_service.create(recipient_sub=None, recipient_role='instructor', type='student_at_risk', title='Student needs attention', body=f'{student_name} is struggling across multiple topics', action_url=f'/teacher/student/{student_sub}')` (BR-TCH-004, shared queue). (notification_service is already in the constructor from T4.2.1a.)
- **Done when**: after a session where a topic's status transitions to 'weak', a topic_marked_weak notification row exists recipient_role='student' recipient_idp_sub=student_sub; when a student reaches 3 weak topics, a student_at_risk notification row exists recipient_idp_sub IS NULL recipient_role='instructor'.
- **Test**: `assert notif.type == "topic_marked_weak" and notif.recipient_role == "student"` after a session that drops a topic's mastery below 60 for the first time.
- **Depends on**: T4.2.1a [backend], T3.1.4 [backend]

### G4.3 — Post-exam hAITU review (S05)
**Subgoal**: The backend exposes POST /api/haitu/exam-review-chat and POST /api/haitu/pattern-analysis reusing the hAITU LLM provider with a fixed server-side review prompt (not the topic-doubt RAG pipeline), and the frontend renders the S05 review screen with question-level wrong/right indicators and a per-question hAITU review chat panel.
**Subgoal test**: A student who completed a session with 3 wrong answers calls POST /api/haitu/pattern-analysis with {session_id} → 200 with a non-empty analysis string. The student opens /exam/{session_id}/review — sees all questions with wrong/right indicators, the pattern-analysis text as the opening hAITU message, clicks a wrong question, types "Why is the answer X?", and receives a hAITU explanation. A session_id belonging to another student → 403. A non-completed session → 403.
**Repos**: [backend] [frontend]

##### T4.3.1a [backend] — POST /api/haitu/exam-review-chat
- **Build**: Add `POST /exam-review-chat` to src/api/routes/haitu.py (existing module, registered at /api/haitu). Body ExamReviewChatRequest(session_id, message, history: list[dict]). Guards: `require_student()` + `validate_csrf`. Load exam_session by session_id via ExamSessionRepository; 404 if not found; 403 if session.user_id != user.id; 403 if session.status not in (completed, grading_pending) ("not reviewable"). Load exam_session_questions + questions (with correct answers, explanations, is_correct) via the existing ExamSessionQuestionService + QuestionService. Build the §3.2 system prompt from the template title, results summary, per-question details. Call `HaituService._dispatch_llm(messages)` (reuse the existing provider — NOT _stage2_retrieve / the RAG pipeline). Return {"response": str}. Apply the existing HaituRateLimiter with a distinct bucket key `f"review:{user.sub}"` at 10/student/hour. Add ExamReviewChatRequest + ExamReviewChatResponse(response) to src/schemas/haitu.py and the fixed review prompt template to src/shared/prompts.py.
- **Done when**: POST /api/haitu/exam-review-chat with a valid owned session_id returns 200 with a non-empty response; another student's session_id returns 403; a non-completed session returns 403; the OpenAPI spec lists the path under /api/haitu.
- **Test**: `assert response.status_code == 200 and len(response.json()["response"]) > 0` for POST /api/haitu/exam-review-chat on the student's own completed session (mocked LLM).
- **Depends on**: T4.1.3b [backend] (questions carry topic_id for richer review context)

##### T4.3.1b [backend] — POST /api/haitu/pattern-analysis (in-memory cache)
- **Build**: Add `POST /pattern-analysis` to src/api/routes/haitu.py. Body PatternAnalysisRequest(session_id). Guards: `require_student()` + `validate_csrf`. Verify ownership + completed status (same as T4.3.1a). Cache: an in-memory `dict[UUID, tuple[str, float]]` keyed by session_id with a 1-hour TTL (timestamp from settings/passed-in clock). v1 limitation (document in the docstring): the cache is per-worker — with multiple uvicorn workers the cache is not shared, so a request landing on a different worker recomputes; acceptable for v1. If cached + not expired, return it. Else build the §3.2a prompt from wrong answers only (question body + student answer + correct answer), call `HaituService._dispatch_llm`, cache, return {"analysis": str}. Add PatternAnalysisRequest + PatternAnalysisResponse(analysis) to src/schemas/haitu.py and the pattern-analysis prompt template to src/shared/prompts.py.
- **Done when**: POST /api/haitu/pattern-analysis with a valid owned session_id returns 200 with a non-empty analysis; a repeat call within the TTL returns the same string without recomputing (on the same worker); another student's session_id returns 403.
- **Test**: `assert response.status_code == 200 and len(response.json()["analysis"]) > 0` for POST /api/haitu/pattern-analysis on the student's own completed session (mocked LLM).
- **Depends on**: T4.1.3b [backend]

##### T4.3.2 [frontend] — S05 exam review screen + hAITU review chat
- **Build**: src/app/exam/[session_id]/review/page.tsx — S05 route. Fetch review data via the existing examApi.getAttemptResults(csrfToken, session_id) (GET /api/exam-sessions/session/{session_id}/answers) for per-question results[] (is_correct, correct_answer_options, user_answer, explanation). Fetch pattern analysis via a new examApi.getPatternAnalysis(csrfToken, session_id) → POST /api/haitu/pattern-analysis. Render: (1) results summary header (score, correct/wrong/skipped counts); (2) a list of questions with wrong/right indicators (reuse the ✘/✓ rendering from attempts-modal.tsx renderResultIcon); (3) the pattern-analysis text as the opening hAITU message in a chat panel at the bottom; (4) clicking a wrong question expands a hAITU review chat panel below it — a new useExamReviewChat(csrfToken, session_id, question_id) hook (src/features/exam/hooks/) calling POST /api/haitu/exam-review-chat with {session_id, message, history}, rendering chat bubbles (reuse the HaituDoubtPanel bubble pattern). Add types ExamReviewChatMessage, PatternAnalysisResponse to src/features/exam/types/exam.types.ts. Add getPatternAnalysis + postExamReviewChat to src/features/exam/api/exam-api.ts using fetchWithCSRFRetry + buildApiHeaders with X-Current-Role: student.
- **Done when**: /exam/{session_id}/review renders question-level wrong/right indicators for a completed session; the pattern-analysis text appears as the opening chat message; clicking a wrong question opens a hAITU review chat panel that sends a message and displays the response.
- **Test**: `expect(screen.getByText(/pattern analysis|analysis/i)).toBeInTheDocument()` on the review page with mocked pattern-analysis data.
- **Depends on**: T4.3.1a [backend], T4.3.1b [backend]

### G4.4 — Weak-topic flags + dashboard
**Subgoal**: The student dashboard API exposes weak_topics derived from enrollment_topics.status='weak', and the frontend renders a "Focus areas" weak-topic strip on the student home page (S-home).
**Subgoal test**: A student with 2 weak topics loads /home — a "Focus areas" strip appears listing the 2 weak topic titles as clickable links; a student with 0 weak topics sees no strip. The GET /api/student/dashboard response includes a weak_topics array with {topic_id, topic_title, enrollment_id, mastery_score} per weak topic.
**Repos**: [backend] [frontend]

##### T4.4.1 [backend] — Student home API exposes weak-topic flags
- **Build**: In src/api/routes/student_dashboard.py, modify GET /dashboard + StudentDashboardService.get_dashboard to include weak_topics. Add a WeakTopic schema to src/schemas/student_dashboard.py (topic_id, topic_title, enrollment_id, mastery_score). In StudentDashboardService.get_dashboard, after fetching platform_nodes, call `EnrollmentTopicRepository(session).get_weak_topics(user.sub)` (from T4.1.3a); for each weak EnrollmentTopic, resolve topic_title via `TopicRepository.get_by_id(topic_id).title`; assemble list[WeakTopic]. Add weak_topics: list[WeakTopic] to the dashboard response schema. Add EnrollmentTopicRepository(session) + TopicRepository(session) to the service constructor (the existing get_student_dashboard_service factory has the session).
- **Done when**: GET /api/student/dashboard returns 200 with a weak_topics array; a student with weak topics sees them in the array; a student with no weak topics sees weak_topics: [].
- **Test**: `assert "weak_topics" in response.json()` for GET /api/student/dashboard with X-Current-Role: student.
- **Depends on**: T4.1.3a [backend] (repo exists; weak topics are populated at runtime by T4.2.1b)

##### T4.4.2 [frontend] — Weak-topic flags on student dashboard
- **Build**: Add WeakTopic to src/features/student/types/student.types.ts (topic_id, topic_title, enrollment_id, mastery_score). Update the dashboard response type to include weak_topics: WeakTopic[]. In src/features/student/api/student-api.ts ensure getDashboard parses weak_topics. Create src/features/student/components/focus-areas-strip.tsx — a horizontal strip of clickable topic chips (amber/warning styling) titled "Focus areas"; each chip links to /home/topics/{enrollment_id}; hidden when weak_topics.length === 0. Render <FocusAreasStrip weakTopics={data.weak_topics} /> in src/features/student/components/student-home-page.tsx above PlatformBoardSection.
- **Done when**: a student with weak topics sees a "Focus areas" strip with clickable chips on /home; a student with 0 weak topics sees no strip; clicking a chip navigates to the topic study view.
- **Test**: `expect(screen.getByText("Focus areas")).toBeInTheDocument()` on StudentHomePage with mocked dashboard data containing 1+ weak topics.
- **Depends on**: T4.4.1 [backend]

**G4 integration test**: E2E — a student completes a quiz with 4 questions: 2 tagged to topic A (1/2 correct = 50%) and 2 to topic B (2/2 = 100%). After POST /api/exam-sessions/{session_id}/submit, enrollment_topics shows A mastery_score=50 status='weak' (BR-PROGRESS-001) and B mastery_score=100 status='completed' (BR-PROGRESS-002); a topic_marked_weak notification appears in the student's feed. The student opens /exam/{session_id}/review — sees the pattern-analysis opening message, question-level wrong/right indicators, clicks the wrong question tagged to A, and hAITU explains the mistake. A second attempt on the same quiz scoring 80% on A yields mastery_score = round(0.6*80 + 0.4*50) = 68 (BR-PROGRESS-003) status='in_progress'. When the student accumulates 3 weak topics, a student_at_risk notification appears in the instructor shared queue. The student's /home dashboard shows a "Focus areas" strip listing the weak topics.

---

## DAG + ordering rationale

Chosen order: **G0 → G1 → G2 → G3 → G4** (acyclic).

- G0 must land first — every backend task needs an importable app + green base.
- G1 establishes the doubts schema + persistence that G2 (escalation needs doubts rows) and G3.4 (auto-close + event wiring need doubts + the escalate/reply endpoints) build on.
- G2 defines the escalate (T2.1.2a) + teacher reply (T2.1.2c) endpoints that G3.4 retroactively wires notifications into.
- G3 (notifications) is sequenced after G2 only to keep each goal independently deliverable; G3's NotificationService (T3.1.4) is the dependency for G3.4 wiring AND for G4.2.2.
- G4 depends on G3 (NotificationService for topic_marked_weak/student_at_risk) and on the V35→V36 migration chain (V37 follows V36).

Forward edges only, no cycles. No leaf task spans two repos. Every cross-repo dependency carries a repo tag.

### Decisions locked this session (2026-06-24)
1. **Doubt → student linkage** = plain-text `student_sub` (no FK), per the project rule that user identity is never a hard FK. `student_enrollments` is NOT extended. Only `enrollment_topics` (G4) FKs to `student_enrollments`. (Confirmed with user.)
2. **Shared-instructor-queue read caveat** = marking a NULL-recipient shared notification read marks it read globally for the entire instructor queue (known v1 limitation, documented in T3.2.1 + T3.1.4).
3. **CLAUDE.md Keycloak staleness** = corrected by T0.8 [specs] (all 6 roles + an instructor test user are provisioned in the realm; G2 relies on instructor availability).
4. **questions.topic_id** = unchanged (already NOT NULL soft FK per 01_data_model.md); V37 only creates enrollment_topics and verifies the column is present. The earlier "nullable hard-FK" language was dropped.
5. **hAITU spec file** = `target/requirements/11_haitu_ai_layer.md` (slot 11 is free; slots 08/09/10/12 are taken), falling back to `vision/requirements/08_haitu_ai_layer.md`.
6. **Teacher escalation routing** = shared instructor queue (any instructor replies), escalated_to=NULL until claimed — NOT platform-admin; no orgs/classes in v1.
7. **Inline-ML cleanup (G0.3)** = the only inline-ML code is the hAITU reranker (`SentenceTransformerRerank`), already disabled. Remove `sentence-transformers` + `torch` + the uv torch-CPU pin + pytorch-cpu index; stub `_stage3_rerank` to a no-op that keeps `rerank_model` as a future-hook for an external rerank API. Embedding/OCR/RAG stay external (Ollama/LM Studio HTTP) — unchanged. (Confirmed with user 2026-06-24.)

---

<!-- plan-baseline: backend:6ec91ab616b839f551eed830eb8bded56931eb44 frontend:47e4ec26d5e69781e3545909554104bdd605ef0b deploy:31784517a24c3047767abfd6b41c7f2098266717 -->