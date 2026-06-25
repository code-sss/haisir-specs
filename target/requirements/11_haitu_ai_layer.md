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
  whose `status NOT IN ('resolved','auto_closed')` — instead of creating a duplicate. Two
  identical queries from the same student on the same topic therefore produce **one** thread
  with 2 student + 2 ai messages, not two threads (T1.2.3).
- Escalation is allowed from `new` or `ai_answered` (the S09 "Request teacher help" CTA is
  visible only when `status IN (new, ai_answered)`); once `escalated` or `answered` the CTA is
  hidden.
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

| Method | Path | Guard | Persistence effect |
|---|---|---|---|
| `POST` | `/api/haitu/topic-doubt` | `student` + CSRF | find-or-create doubt + student message (validation, post rate-limit); emits `doubt_id` SSE event; AI message + `haitu_attempted` via fresh-session background task |
| `GET` | `/api/students/me/doubts` | `student` | list the student's doubts (S08) — see `03_student.md` |
| `GET` | `/api/students/me/doubts/{doubt_id}` | `student` + ownership | thread with messages (S09) — 404 if `doubt.student_sub != user.sub` |
| `POST` | `/api/students/me/doubts/{doubt_id}/messages` | `student` + CSRF + ownership | append a student follow-up; return updated thread |

> The escalate + teacher-queue + teacher-reply endpoints (`POST /api/doubts/{id}/escalate`,
> `GET /api/teachers/me/doubts`, `POST /api/teachers/me/doubts/{id}/claim`,
> `POST /api/teachers/me/doubts/{id}/messages`) are documented in `04_teacher_tutor.md`
> (T06/T07) and the escalate lifecycle is added to this file by T2.1.1.

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