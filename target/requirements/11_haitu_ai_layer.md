# hAIsir — hAITU AI Layer Specification (target state)

> Target-state spec for the hAITU AI layer, focused on the Phase 4 doubt-persistence +
> teacher-escalation additions. For the full prompt contracts, interaction-type catalogue,
> token limits, caching rules, and scope rules, fall back to `vision/requirements/08_haitu_ai_layer.md`
> — those are unchanged by this increment and are not duplicated here.
> → Depends on: `00_overview.md` through `07_platform_admin.md`, `03_student.md` (S08/S09),
>   `04_teacher_tutor.md` (T06/T07), `10_notifications.md`.
> → Model is configurable by SuperAdmin. Default: `claude-sonnet-4-6`.

---

## 1. Scope of this increment

Phase 4 makes the hAITU topic-doubt conversation a **durable thread**. Where Phase 3 held chat
history only in client memory (BR-AI-004 — ephemeral), Phase 4 introduces the `doubts` +
`doubt_messages` tables and persists:

- the student's question (written during the validation phase, **after** the rate-limit check), and
- hAITU's full streamed reply + the `haitu_attempted` flag (written by a **post-stream
  background task** using a **fresh DB session**, never the request session that was closed
  before the first token — per the Phase 3 SSE session lifecycle).

A `doubt_id` is emitted as an SSE event so the client can link a just-streamed reply to its
persisted thread. The persistence path is engineered so that **a rate-limited (429) request
leaves zero `doubts` rows** and a **mid-stream disconnect still persists whatever AI text was
produced** (partial or empty). The doubt lifecycle states and their transitions are defined
in §3.

Everything else about hAITU — interaction types, the 4-stage RAG retrieval pipeline, the
streaming wire format, prompt contracts, token limits, caching, and scope rules — is
unchanged from `vision/requirements/08_haitu_ai_layer.md`. The Phase 3 streaming contract
(SSE frames `{"token":…}` → `{"escalation_ready":…}` → `{"done":true}`, 15 s `: ping`
keepalives, `request.is_disconnected()` cancellation, DB session closed before the first
token) is retained and extended with a `doubt_id` event (§2) and the persistence semantics
(§4–§5).

---

## 2. The `doubt_id` SSE event

`POST /api/haitu/topic-doubt` emits one additional SSE event in Phase 4, **immediately after
the validation phase completes and before the first token is yielded**:

```
data: {"doubt_id":"<uuid>"}\n\n      // exactly one, before the first {"token":…} frame
data: {"token":"…"}\n\n
…
data: {"escalation_ready":false}\n\n
data: {"done":true}\n\n
```

Contract:

- The `doubt_id` event is emitted exactly once per successful (non-429) request.
- It carries the UUID of the `doubts` row created/reused for this (student, topic) pair
  (find-or-create — see §4). The client uses it to deep-link the just-completed reply to its
  persisted thread (`/doubts/{doubt_id}`) and to pre-load history on re-open.
- Ordering is strict: `doubt_id` precedes the first `token` frame. A client that consumes the
  stream with `ReadableStream`/`TextDecoder` (per the Phase 3 frontend consumer) captures
  `doubt_id` before appending any tokens.
- The `doubt_id` event is **not** emitted on a 429 — 429 is returned as an ordinary HTTP error
  before the stream begins (Phase 3 contract), and no `doubts` row exists to report
  (§5 "orphan-on-429").
- The existing `escalation_ready` and `done` frames are unchanged.

> The non-streaming `HaituService.answer()` path (used by unit/integration tests and
> non-streaming callers) does not emit SSE events; it returns `HaituResponse{response,
> escalation_ready}`. Persistence in that path is asserted at the service/repository layer in
> tests, not via SSE.

---

## 3. Doubt lifecycle

A doubt is a durable thread owned by a student, anchored to a topic (+ optionally a
course-path node), carrying an ordered list of `doubt_messages` from four sender types.

### 3.1 States

| State | Meaning | Set by |
|---|---|---|
| `new` | Doubt created; no AI reply persisted yet | `find_or_create_doubt` (initial) |
| `ai_answered` | hAITU has replied (an `ai` message exists, `haitu_attempted=true`) | post-stream background task |
| `escalated` | Student has requested teacher help; visible in the shared instructor queue (`escalated_to=NULL` until claimed) | `POST /api/doubts/{id}/escalate` |
| `answered` | A teacher has replied (a `teacher` message exists) | `POST /api/teachers/me/doubts/{id}/messages` |
| `resolved` | Doubt closed — either auto-closed by the worker cron after 7 days of inactivity, or closed manually | auto-close cron / manual |
| `auto_closed` | (Reserved) — the cron may set `resolved` with a closing system message; see note below |

> **Status enum (V35):** `CHECK (status IN ('new','ai_answered','escalated','answered',
> 'resolved','auto_closed'))`. The canonical auto-close path sets `status='resolved'`,
> `resolved_at=now()`, and appends a closing `ai`/`system` message; `auto_closed` is kept in
> the enum as a reserved discriminator for future fine-grained reporting. (See G3.4 /
> `10_notifications.md` BR-NOTIF-011 for the hourly cron and the `doubt_auto_closed`
> notification.)

### 3.2 Transitions

```
new ──hAITU reply persisted──► ai_answered
ai_answered ──student escalates──► escalated
new ──student escalates (before any AI reply)──► escalated
escalated ──teacher replies──► answered
answered | ai_answered | escalated ──7-day inactivity cron──► resolved
answered | ai_answered | escalated ──manual close──► resolved
```

- `find_or_create_doubt` reuses an **open** doubt for the same (student, topic) — i.e. one
  whose `status NOT IN ('resolved','answered')` — instead of creating a duplicate. Two
  identical queries from the same student on the same topic therefore produce **one** thread
  with 2 student + 2 ai messages, not two threads (T1.2.3). Once a doubt reaches `answered`
  (a teacher has replied), it is treated as closed: a new question on the same topic creates
  a fresh doubt thread, restoring the full escalation path.
- Escalation is allowed from `new` or `ai_answered` (the S09 "Request teacher help" CTA is
  visible only when `status IN (new, ai_answered)`); once `escalated` or `answered` the CTA is
  hidden on the current thread. A new thread (created when a student asks a new question after
  `answered`) starts at `new` and exposes the CTA again.
- A teacher reply from the shared queue sets `answered` and appends a `teacher` message.
- The auto-close cron (G3.4) targets doubts with `status != 'resolved'` and
  `auto_close_at <= now()` (indexed via `idx_doubts_auto_close`), sets `resolved`, appends a
  closing message, and emits a `doubt_auto_closed` notification to the student.

### 3.3 `doubt_messages` sender types

`sender_type ∈ ('student','ai','teacher','system')` (V35 CHECK):

- `student` — the student's question or follow-up.
- `ai` — hAITU's reply (full streamed text, written by the post-stream background task).
- `teacher` — an instructor's reply from the shared queue.
- `system` — closing/system notes (e.g. "Escalated to a teacher", auto-close notice).

### 3.4 Escalation routing — shared instructor queue (v1)

v1 uses a **shared instructor queue** with no orgs/classes model:

- When a student escalates (`POST /api/doubts/{id}/escalate`), `escalated_to` is set to
  `NULL`. Any authenticated instructor with `X-Current-Role: instructor` can see the doubt in
  `GET /api/teachers/me/doubts` (the shared queue returns unclaimed doubts where
  `escalated_to IS NULL`, plus this instructor's own claimed doubts where
  `escalated_to = user.sub`).
- An instructor **claims** a doubt via `POST /api/teachers/me/doubts/{id}/claim`, which sets
  `escalated_to = instructor.sub` — an optimistic advisory lock. If another instructor claimed
  first, the endpoint returns 409; the caller should refresh the list.
- After claiming, the doubt disappears from the "unclaimed" view of other instructors' queues
  but remains visible in the claimer's list. Any instructor can still reply
  (`POST /api/teachers/me/doubts/{id}/messages`) regardless of who claimed — claim is
  advisory in v1, not a hard write-lock.
- "Mark read" on a shared `new_doubt_escalated` notification (which has
  `recipient_idp_sub IS NULL`) marks it read globally for the whole instructor role queue —
  a documented v1 limitation (see `10_notifications.md`).

**Rationale:** a full orgs/classes routing model (routing to a specific teacher by class
membership) is deferred to a future phase. `escalated_to` is stored so routing can be refined
without a schema change once orgs/classes exist.

---

## 4. Persistence contract

Persistence is split across **two phases** of the request lifecycle, on purpose, to honour
the Phase 3 SSE invariant that the request DB session is closed before the first token and
to guarantee no orphan rows on 429.

### 4.1 Validation phase — student message (post rate-limit)

Inside `POST /api/haitu/topic-doubt`, **after** the `HaituRateLimiter` check passes (so a 429
never reaches this code) and during the validation phase (enrollment ownership + subtree +
context assembly, all within the scoped request session):

1. `DoubtService.find_or_create_doubt(student_sub, topic_id, node_id, title)` — reuses an
   open doubt for the (student, topic) pair or creates one with
   `auto_close_at = now() + interval '7 days'`, `status='new'`.
2. `DoubtService.add_student_message(doubt_id, query)` — appends a `student` message.
3. The `doubt_id` is captured and passed into the streaming coroutine.
4. The request session is **committed and closed before streaming begins** (Phase 3 SSE
   pattern: `session.close()` before the first token) — an aborted stream cannot leave a
   connection checked out.

`Depends(validate_csrf)` on the POST is preserved (CSRF on every mutation — do not drop it
when adding persistence).

### 4.2 Post-stream background task — AI message + `haitu_attempted` (fresh session)

The AI reply is **not** written on the request session (which is already closed). After the
stream completes (or the client disconnects — see §5), a background task
(`BackgroundTasks` / `asyncio.create_task`) opens a **fresh, independent session** (its own
session maker, not the request session) and:

1. Accumulates the full AI text produced during the stream (whatever was streamed — full or
   partial; possibly empty on an early disconnect).
2. `DoubtService.add_ai_message(doubt_id, full_text)` — appends an `ai` message.
3. `DoubtService.mark_haitu_attempted(doubt_id)` — sets `haitu_attempted=true` and, if the
   doubt is still `new`, transitions it to `ai_answered`.
4. Commits the fresh session.

The fresh-session requirement is the load-bearing detail: writing the AI message on the
request session would violate the Phase 3 "session closed before streaming" invariant and
risk a checked-out connection on a mid-stream abort.

### 4.3 `haitu_attempted`

`doubts.haitu_attempted BOOL DEFAULT false` is set to `true` once hAITU has produced a reply
for the doubt (any reply — full or partial). It is the flag the escalation flow (G2) and the
auto-close cron (G3.4) reason about, and it is what distinguishes "hAITU tried" from "student
escalated immediately".

---

## 5. Failure guarantees

### 5.1 Orphan-on-429

A request that returns **429** (rate limit exceeded) creates **zero** `doubts` rows and
**zero** `doubt_messages` rows. This is guaranteed by ordering: the rate-limit check runs
**before** `find_or_create_doubt` / `add_student_message`, so a rejected request never reaches
the persistence code. No `doubt_id` SSE event is emitted (429 is an HTTP error returned before
the stream begins — Phase 3 contract).

### 5.2 Partial-text-on-disconnect

A client disconnect mid-stream (the route polls `request.is_disconnected()` and signals the
shared cancellation flag, per Phase 3) **still persists**:

- the `doubts` row and the `student` message — both written in the validation phase, before
  streaming, and already committed;
- whatever AI text was accumulated up to the disconnect — written by the post-stream
  background task as an `ai` message (possibly empty if nothing was produced);
- `haitu_attempted=true`.

No unhandled exception escapes the disconnect path. The background task runs to completion
even though the client is gone (it is not tied to the request lifecycle).

### 5.3 No-duplicate-on-retry

A client that retries the same (student, topic) query after a successful stream does **not**
create a second `doubts` row: `find_or_create_doubt` reuses the open doubt for that pair, so
two identical successful queries yield **one** thread with **two** `student` messages and
**two** `ai` messages (T1.2.3).

---

## 6. Endpoints touched by this increment

### G1 — Student doubt persistence (Phase 4 G1)

| Method | Path | Guard | Persistence effect |
|---|---|---|---|
| `POST` | `/api/haitu/topic-doubt` | `student` + CSRF | find-or-create doubt + student message (validation, post rate-limit); emits `doubt_id` SSE event; AI message + `haitu_attempted` via fresh-session background task |
| `GET` | `/api/students/me/doubts` | `student` | list the student's doubts (S08) — see `03_student.md` |
| `GET` | `/api/students/me/doubts/{doubt_id}` | `student` + ownership | thread with messages (S09) — 404 if `doubt.student_sub != user.sub` |
| `POST` | `/api/students/me/doubts/{doubt_id}/messages` | `student` + CSRF + ownership | append a student follow-up; return updated thread |

### G2 — Teacher escalation (Phase 4 G2)

| Method | Path | Guard | Effect |
|---|---|---|---|
| `POST` | `/api/doubts/{doubt_id}/escalate` | `student` + CSRF + ownership | sets `status='escalated'`, `escalated_to=NULL`; emits `new_doubt_escalated` notification (G3.4) |
| `GET` | `/api/teachers/me/doubts` | `instructor` | shared queue — unclaimed escalated doubts + this instructor's claimed doubts |
| `POST` | `/api/teachers/me/doubts/{doubt_id}/claim` | `instructor` + CSRF | sets `escalated_to=user.sub`; 409 if already claimed by another |
| `POST` | `/api/teachers/me/doubts/{doubt_id}/messages` | `instructor` + CSRF | appends a `teacher` message; sets `status='answered'`; emits `doubt_teacher_replied` notification (G3.4) |

> Shared-queue routing semantics (who sees what, the claim advisory lock, v1 limitation on
> read-marking shared notifications) are in §3.4. Full screen specs for the teacher inbox
> (T06) and thread view (T07) are in `04_teacher_tutor.md`.

---

## 7. What is unchanged from the vision spec

The following are unchanged from `vision/requirements/08_haitu_ai_layer.md` and are not
re-stated here — refer to the vision file for the authoritative text:

- §2 Interaction-type catalogue (`topic-doubt`, `exam-review-chat`, `escalation-attempt`,
  `teacher-tools`, parent interactions, `exam-analysis`).
- §3 Prompt contracts and the 4-stage RAG retrieval pipeline (Stage 1 query rewrite + intent
  + safety; Stage 2 hybrid retrieval; Stage 3 rerank — now a no-op passthrough future-hook per
  G0.3; Stage 4 synthesis). The streaming Stage-4 path still uses a single prompt mirroring
  the §3.1 QA template.
- §4 API endpoint shapes (paths, auth, request/response bodies) — extended only by the
  `doubt_id` SSE event (§2) and persistence (§4) for `topic-doubt`.
- §5 Token limits, §6 Caching rules, §7 Failure handling (BR-AI-001…010), §8 Scope rules.

> **BR-AI-004 update (Phase 4):** the Phase 3 "hAITU chat history is fully ephemeral" rule is
> superseded for `topic-doubt`: the student's question and hAITU's reply are now persisted to
> `doubts` + `doubt_messages` as described in §4. The client-side rolling 5-message window
> sent in the request `history` field is retained for the in-flight prompt only; the durable
> thread is the source of truth and is what S09 renders.

---

## 8. Exam review + pattern analysis (G4.3)

Phase 4 G4.3 adds two **no-RAG** hAITU endpoints used by the S05 post-exam review screen
(`03_student.md`). They reuse `HaituService`'s public no-RAG method (added in T4.3.1a —
`answer_no_rag(messages, max_tokens)` / `stream_no_rag(prompt, cancel_event)`, which dispatch to
the underlying private `_dispatch_llm` / `_stream_llm` / `_call_llm_raw` **without** the 4-stage
RAG retrieval pipeline) and the `HaituRateLimiter` (in-memory `(sub, hour_bucket)`, 20/hr,
singleton). The sacred RAG pipeline is untouched.

**Body param canonicalization:** both endpoints take **`attempt_id`** (= `exam_sessions.id`),
resolving the vision student-spec (`session_id`) vs haitu-spec (`attempt_id`) discrepancy. The
S05 review payload is fetched separately via `GET /api/exam-sessions/session/{session_id}/answers`
(the live path — NOT `.../review`); the hAITU endpoints receive only the `attempt_id` + the
student's message, and assemble the question/answer context server-side from that attempt.

### 8.1 `exam-review-chat` (§3.2) — per-question explanation + follow-ups

**When:** Student is in the S05 review screen and either clicks "Ask hAITU to explain this" on a
wrong/skipped question or types a follow-up in the review chat panel.

**Context assembled server-side (no RAG):**
- Assessment title, subject, board.
- All questions for the attempt with: body, correct answer, student's answer, `is_correct`,
  explanation.
- The pre-computed pattern analysis (see §8.2).
- Last 10 messages from this review session (the `history` field mirrors the rolling window;
  the attempt-scoped context is the source of truth).

**System prompt template (port of vision §3.2):**
```
You are hAITU, reviewing a student's performance on "{template_title}" ({subject}, {board}).

Their results: {correct} correct, {wrong} wrong, {skipped} skipped out of {total}.

Question details:
{question_details}

Rules:
- The student wants to understand their mistakes. Be encouraging and precise.
- When explaining a wrong answer, always show the correct reasoning step by step.
- Identify patterns across mistakes (e.g. "You made this mistake on Q3, Q5, and Q8 — they all involve the same concept").
- Never just say "the answer is X" — always explain why.
- Keep responses focused on the exam content.
```

### 8.2 `pattern-analysis` (§3.2a) — pre-computed opening message

**When:** Generated once per attempt on S05 page load, displayed as the opening hAITU message in
the review panel.

**Prompt (port of vision §3.2a):**
```
Analyse the following wrong answers from this exam and identify the single most common mistake
pattern in 2–3 sentences. Be specific about which questions share the pattern.

Wrong answers:
{wrong_questions_with_answers}
```

If the attempt has zero wrong answers, the endpoint returns a neutral opening message
("Great work — no wrong answers to analyse on this attempt.") instead of calling the LLM.

### 8.3 API contracts

```
POST /api/haitu/exam-review-chat
→ Auth: student (CSRF required; X-Current-Role: student)
→ Body: {attempt_id: uuid, message: str, history: [{role, content}]}
→ Returns: {response: str}
→ Token limit: 500 (configurable by SuperAdmin; see §5 of the vision spec)

POST /api/haitu/pattern-analysis
→ Auth: student (CSRF required; X-Current-Role: student)
→ Body: {attempt_id: uuid}
→ Returns: {analysis: str}
→ Cached per attempt_id (see §8.4)
```

### 8.4 Caching

`pattern-analysis` is **cached per `attempt_id`** — the analysis is generated once for an attempt
and reused across page loads / follow-ups within the same review session.

> **v1 limitation:** the cache is **in-memory per worker**, not cross-process. With a single
> worker (current scale) this gives exact per-attempt caching; under multi-worker deployment the
> same `attempt_id` may be re-computed once per worker that handles it. This is acceptable for the
> current scale and is documented here so it is not mistaken for a correctness bug. A shared
> cache (Redis) is a future optimisation, not a Phase 4 requirement.

`exam-review-chat` is **not cached** — each follow-up is a fresh LLM call (rate-limited per
BR-AI-003).

### 8.5 Guards

Both endpoints enforce, in order:

1. **Ownership (403):** the `exam_sessions` row for `attempt_id` must have
   `user_id = calling student's idp_sub`. A session owned by another student → `403`.
2. **Status gate (403 / 400):** the session status must be in `('completed', 'failed')`. An
   ongoing / pending / `grading_pending` session → `403` (review not available yet). A
   non-existent `attempt_id` → `404`.
3. **CSRF (Depends(validate_csrf)):** required on both POSTs (CSRF on every mutation — do not
   drop it when adding these endpoints).
4. **Rate limit (BR-AI-003):** the `HaituRateLimiter` (20 calls/student/hour) gates both
   endpoints; exceeding returns `429` with "You've reached the limit for AI assistance this
   hour. Please try again later." A 429 on `pattern-analysis` leaves no cached entry.

### 8.6 Failure handling (BR-AI-001/002/003)

These apply to both `exam-review-chat` and `pattern-analysis`, ported from the vision spec §7:

- **BR-AI-001:** If the LLM call fails (timeout, rate limit from the provider, 5xx), the backend
  returns a graceful fallback response rather than propagating the error — `exam-review-chat`
  returns `{"response": "I couldn't generate an explanation right now. Please try again in a
  moment."}`; `pattern-analysis` returns `{"analysis": "Pattern analysis is temporarily
  unavailable."}`. The S05 UI degrades gracefully (the chat remains usable; the opening message
  shows the fallback).
- **BR-AI-002:** All hAITU API calls have a 30-second timeout. If exceeded, return `504` with the
  fallback message above (the response body is the fallback string, the HTTP status is `504` so the
  client can distinguish a provider failure from a normal response).
- **BR-AI-003:** Rate limiting — max 20 hAITU calls per student per hour (the `HaituRateLimiter`
  shared with `topic-doubt`). Exceeding returns `429` with: "You've reached the limit for AI
  assistance this hour. Please try again later."