# Phase 3 — Manual ROOT Acceptance Test Walkthrough Record

> Task **T10.4.1** [specs]. Execution + recording only — no code changes in this task.
> Defects found are logged against T10.4.2 (backend) / T10.4.3 (frontend) / T10.4.4 (deploy).

## Pre-flight checklist

| # | Requirement | Status |
|---|---|---|
| P1 | Full stack up via `haisir-deploy` docker compose (backend, frontend, APISIX, Postgres pgvector) | ☐ |
| P2 | LLM provider running: **LM Studio** with chat model (e.g. `qwen3:14b`) **and** `bge-m3` embed model loaded | ☐ |
| P3 | `HAITU__MODEL_SPEC` uses `lmstudio://…` prefix and points at the chat model | ☐ |
| P4 | `EMBEDDING__MODEL_SPEC` uses `lmstudio://…` prefix and points at `bge-m3` | ☐ |
| P5 | `GET /api/health` (via APISIX :9080) → healthy | ☐ |
| P6 | Real student account exists whose profile **grade == "Grade 8"** (else set it via the student profile endpoint before step 1) | ☐ |
| P7 | At least one platform board node named "Grade 8" exists in the catalog with ≥1 live topic under it (for step 5) | ☐ |
| P8 | A **second** platform node the student is NOT enrolled in (e.g. "Grade 9") exists, for the step 4b 403 test | ☐ |

> Note: Onboarding does not collect a grade (Phase 0 made the student-ready step CTA-only), so `grade` is `None` for fresh students and `recommended` will be `false` across the catalog until you set the profile grade. Set it before step 1, or step 1 will show `recommended: false` and that's a data/setup issue, not a defect.

---

## 7-step ROOT Acceptance Test

| Step | Action | Expected | Observed | Pass/Fail | Defect ref |
|---|---|---|---|---|---|
| 1 | Student (grade "Grade 8") → `GET /api/student/catalog` (via APISIX) | Grade 8 node has `recommended: true` | recommended badge present after profile grade set | ✅ Pass | — |
| 2 | `POST /api/student/enrollments {course_path_node_id: <grade-8-id>}` | 201 with `enrollment_id` | 201, enrollment created | ✅ Pass | — |
| 3 | `GET /api/student/dashboard` | `platform_nodes` contains Grade 8 node (was empty before enroll) | Grade 8 node appears in platform_nodes | ✅ Pass | — |
| 4a | `GET /api/student/nodes?owner_type=platform` | only Grade 8 subtree nodes | enrolled subtree only | ✅ Pass | — |
| 4b | `GET /api/student/nodes/{grade-9-node-id}/topics` | 403 (unenrolled node) | tested via Swagger: Grade 8 id → 200 [] (no topics directly on grade node; topics live on descendant course nodes — not a defect); Grade 9 id → 403 | ✅ Pass | — |
| 5 | In frontend: select a live topic under Grade 8 → `HaituDoubtPanel` appears with input enabled; type "What is osmosis?" → AI response shown in chat. No DB writes occur. | panel renders; AI response string returned; `student_enrollments` row count unchanged | hAITU works (after SSE-streaming fix — see D1); tokens stream into the AI bubble | ✅ Pass | D1 |
| 6 | 21 calls within same hour → 21st returns 429; UI shows "You've reached the AI limit for this hour." | first 20 × 200; 21st × 429; UI error message shown | Backend 429 logic proven green by automated `test_haitu_topic_doubt_21st_call_429` (T10.3.4b, 20×200 then 21st×429); UI message mapping covered by `useHaituDoubt` 429 → "You've reached the AI limit for this hour." handler (T9.2). Accepted by coverage (user decision 2026-06-24). | ✅ Pass | — |
| 7 | Navigate to `/enroll`, click "Drop" → 204; `GET /api/student/dashboard` → `platform_nodes=[]`; empty state with "Browse Courses" CTA shown | 204; dashboard empty; CTA visible | drop → 204; dashboard empties; CTA shown | ✅ Pass | — |

### Pass criteria (from PLAN.md)
- All 7 steps complete with specified status codes and UI states.
- No Redux, Axios, or React Query in any frontend call.
- No business logic in route handlers.
- All mutations carry a valid `X-CSRF-Token` header.

### Notes / gotchas
- **Step 6 — two rate limiters.** The APISIX `19-api-haitu.json` route has `limit-count` (20 req/min/IP → 429) *separate* from the backend in-process limiter (20/student/hour). 21 rapid requests in one minute → APISIX returns the 429, not the backend limiter. To verify the **backend** in-process limiter specifically: send 20, wait >60 s (APISIX window resets), send the 21st → backend limiter fires 429. If you only care that *a* 429 surfaces, rapid-fire is fine — but record which limiter you hit.
- **Step 1 — `recommended` matching.** `recommended` is a case-insensitive match of the catalog node **name** against the student profile **grade**. Both must read "Grade 8". A fresh student has `grade=None` → `recommended=false` everywhere; that's a setup gap, not a defect.

---

## Defect log

> One row per defect. Route to T10.4.2 (backend) / T10.4.3 (frontend) / T10.4.4 (deploy).
> Environmental defects (LM Studio model not loaded, APISIX misconfig, wrong env var) → deploy (T10.4.4), not backend.

| Defect ID | Step | Symptom | Root-cause repo | Fix task | Status |
|---|---|---|---|---|---|
| D1 | 5 | `POST /api/haitu/topic-doubt` returned a single JSON response after a multi-minute RAG pipeline → frontend/gateway idle timeouts caused 504s; aborted requests could leak a DB connection. | backend + frontend (transport/timeout-driven contract change) | T10.4.2 + T10.4.3 | **Fixed.** Endpoint converted to SSE streaming (`text/event-stream`): incremental `{"token":…}` frames, a `{"escalation_ready":…}` frame, a final `{"done":true}` frame, 15 s `: ping` keepalives, `request.is_disconnected()` cancellation, DB session closed before streaming. Backend commits `2cdedcd`, `6ec91ab` (+ refactors `7da64d6`, `a9f7c30`, `93b9de7`, `aac0c7a`); frontend commits `2cd4305`, `47e4ec2` (+ SonarQube `d4076d3`). Verified working in step 5. **Spec updated** — `vision/requirements/08_haitu_ai_layer.md` §4, §3.1, BR-AI-002, BR-AI-009. |
| D2 | — | **Deferred — design gap, not a defect.** Stage 3 rerank is passthrough when `HAITU__RERANK_MODEL=""` (no cross-encoder configured). | backend | (deferred) | Open. Log to `decisions.md` as a deferred item; not a Phase 3 blocker. Spec §3.1 already documents the empty-rerank skip. |
| D3 | — | **Deferred — pre-existing, out of Phase 3 scope.** Admin feature uses `@tanstack/react-query`, deviating from CLAUDE.md "custom hooks with useState/useEffect only". Student feature (Phase 3 scope) uses none — raw fetch via `fetchWithCSRFRetry`. | frontend (Phase 1 admin) | (deferred) | Open cleanup item. Does NOT affect the Phase 3 student walkthrough pass criterion (student calls use no Redux/Axios/React Query). |

### Pass-criteria verification

- **No Redux, Axios, or React Query in any frontend call** — ✅ for the Phase 3 student flow. Verified by grep: `src/features/student/**` imports none of `redux` / `axios` / `@tanstack/react-query`; all student API calls go through raw `fetch` via `fetchWithCSRFRetry`. (Caveat D3: admin feature uses React Query — pre-existing, out of scope.)
- **No business logic in route handlers** — ✅ by inspection. Phase 3 route files (`student_enrollment.py`, `student_dashboard.py`, `haitu.py`) are thin: parse request → call service → map exceptions to HTTP codes. `haitu.py` SSE plumbing (queue/ping/disconnect) is transport, not business logic; the pipeline lives in `HaituService`/`HaituDoubtService`. (Spot-check confirmed against current code; no business logic crept in during the SSE fix.)
- **All mutations carry a valid `X-CSRF-Token` header** — ✅. Enrollment (POST/DELETE) and hAITU (POST) all go through `validate_csrf` dependency; frontend uses `fetchWithCSRFRetry` which self-heals the CSRF token.

### Spec updates made this session (per CLAUDE.md spec-update convention)

- `vision/requirements/08_haitu_ai_layer.md` — §4 `topic-doubt` contract rewritten to SSE streaming (wire format, headers, 403/429-as-HTTP, disconnect, DB-session lifecycle, Stage 4 trade-off, non-streaming `answer()` retained); history role names corrected `user`/`assistant` → `student`/`ai`; §3.1 Stage 4 streaming note added; BR-AI-002 carve-out for the streaming endpoint (15 s pings, 360 s gateway timeout); BR-AI-009 Phase 3 `HAITU__MODEL_SPEC` env-var + prefix-dispatch note.

---

## Sign-off

- [x] All 7 steps pass (steps 1, 2, 3, 4a, 4b, 5, 7 verified in UI/API; step 6 accepted by automated coverage — T10.3.4b + T9.2)
- [x] Defect log closed — D1 fixed (SSE streaming) + spec updated; D2 (reranker) and D3 (admin React Query) deferred (design/cleanup gaps, not Phase 3 blockers; logged in `decisions.md` 2026-06-24)
- [x] Ready for T10.5.1 (closure checklist) → T10.5.2 (archive + progress.md)

Walkthrough executed by: ______________  Date: 2026-06-24

---

## T10.5.1 — Phase 3 Closure Checklist

> Compiled 2026-06-24. Every row must be green (or skip-with-reported-count for Ollama-gated items when Ollama is absent). This is the gate for T10.5.2 (archive + `progress.md`).

### A. Backend verification — 12 goal-level items

| # | Item | Bucket | Status | Evidence |
|---|---|---|---|---|
| 1 | G1.1 — V34 UNIQUE violation + index | DB-only | ✅ green | T10.2.1, verified 2026-06-20 |
| 2 | G2.1 — EnrollmentRepository CRUD | DB-only | ✅ green | T10.2.2 |
| 3 | G2.2 — EnrollmentService enroll/drop/catalog | DB-only | ✅ green | T10.2.3 |
| 4 | G2.3 — route CRUD cycle 200/201/409/204/404 | DB-only | ✅ green | T10.2.4 |
| 5 | G2 E2E — enroll→enrolled=true→drop→false | DB-only | ✅ green | T10.2.5 |
| 6 | G3.1 — subtree + enrolled-root queries | DB-only | ✅ green | T10.2.6 |
| 7 | G3.2 — unenrolled→[]; wrong node→403 | DB-only | ✅ green | T10.2.7 |
| 8 | G5.2 — valid→200; wrong→403; rate→429 | DB-only | ✅ green | T10.2.8 |
| 9 | G4.1 — _stage1_rewrite (live LLM) | Ollama-gated | ✅ green (or skip-with-count) | T10.3.1 — green with live qwen3:14b 2026-06-20; skips with reported count when LLM down |
| 10 | G4.2 — _stage2_retrieve ≥1 node | Ollama-gated | ✅ green (or skip-with-count) | T10.3.2 |
| 11 | G4 E2E — safe=False short-circuit + safe=True full | DB-only + Ollama-gated | ✅ green | T10.3.3a (DB-only, always) + T10.3.3b (gated, green 2026-06-20) |
| 12 | G5 E2E — AI response no DB writes + 21st→429 | Ollama-gated + DB-only | ✅ green | T10.3.4a (gated, green 2026-06-20) + T10.3.4b (DB-only, always) |

**Aggregate gates:** G10.2 = 8 passed, 0 skipped (verified 2026-06-20 vs temp pgvector Postgres; CI green). G10.3 = `Ollama-gated: 0 skipped, 4 passed` with live models; skip-count line present when down. Full unit suite 3537 passed, 22 skipped, 100% coverage.

### B. Manual walkthrough — 7 ROOT Acceptance Test steps

| Step | Status | Evidence |
|---|---|---|
| 1 | ✅ pass | recommended badge after profile grade set |
| 2 | ✅ pass | 201 enrollment created |
| 3 | ✅ pass | Grade 8 in platform_nodes |
| 4a | ✅ pass | enrolled subtree only |
| 4b | ✅ pass | Grade 8→200 []; Grade 9→403 |
| 5 | ✅ pass | hAITU streams tokens (after SSE fix, D1) |
| 6 | ✅ pass (by coverage) | T10.3.4b backend 429 + T9.2 UI message |
| 7 | ✅ pass | drop→204; dashboard empties; CTA shown |

### C. Frontend Playwright E2E suite

- 16 specs across G3/G7/G8/G9 — ✅ green (shipped commit `54e198c`; user-confirmed green build 2026-06-24).

### D. Pass criteria

- No Redux/Axios/React Query in student frontend calls — ✅ (admin React Query deferred, D3, out of scope).
- No business logic in route handlers — ✅ by inspection.
- All mutations carry `X-CSRF-Token` — ✅.

### E. Spec-update convention satisfied

- `vision/requirements/08_haitu_ai_layer.md` updated for the SSE streaming contract change (D1). See "Spec updates made this session" above.

**Verdict: all rows green — Phase 3 is fully closed. Proceed to T10.5.2 (archive + `progress.md`).**