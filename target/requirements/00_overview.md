# Architecture & Tech Stack

> **Target state scope:** Student, Parent, Platform Admin only. Institutions, instructors, tutors, classes, doubts, hAITU, and notifications are explicitly out of scope for this increment.

## What is hAIsir (this increment)?

An AI-enabled edtech platform where:
- **Parents** build or adopt a curriculum, upload study material, and create quizzes/exams for their child — privately.
- **Students** browse platform content and their parent's "Home Study" curriculum as a separate section, and take exams on both.
- **Platform Admins** manage the authoritative platform board content that parents can adopt from.

---

## System Architecture

```
Browser
  ↓ HTTPS (cookie + X-CSRF-Token + X-Current-Role)
Cloudflare (DDoS + CDN)
  ↓
Apache APISIX (TLS termination · WAF/Coraza · OIDC · CSRF · JWT injection)
  ├─→ Next.js Frontend  (haisir-frontend)
  └─→ FastAPI Backend   (haisir-backend)
       └─→ PostgreSQL 18 + pgvector
       └─→ Keycloak 26 (identity)
       └─→ Local disk storage (file uploads, v1)
```

**Key invariants:**
- APISIX injects `Authorization: Bearer <JWT>` — the client never sends a Bearer token.
- Every request carries `X-Current-Role: <role>` and `X-CSRF-Token: <token>` on mutations.
- Identity is the Keycloak `sub` claim (`idp_sub`) — a raw UUID string. No local users table.
- The backend independently verifies each JWT (local JWKS decode + optional Keycloak token introspection for revocation, RFC 7662). Introspection requires the `token-introspection` client scope and the backend client present in the token `aud` (Keycloak 26). See `target/requirements/02_auth_and_roles.md`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React, raw `fetch` with `credentials: 'include'` |
| Backend | FastAPI 0.135, SQLAlchemy (imperative mapping, no Base subclassing) |
| Identity | Keycloak 26.6, Google SSO, JWT RS256 |
| Database | PostgreSQL 18, pgvector |
| Gateway | Apache APISIX (OIDC, CSRF, Coraza WAF, CrowdSec, rate limiting) |
| File storage | Local disk (v1) via `StorageBackend` abstract interface |
| Infra | Docker Compose (haisir-deploy) |

---

## Personas (this increment)

| Persona | Keycloak role | How assigned |
|---|---|---|
| Student | `student` | Self-registers → auto-assigned at onboarding |
| Parent | `parent` | Self-registers → auto-assigned at onboarding |
| Platform Admin | `admin` | Manual Keycloak console only |

Roles `instructor`, `tutor`, `institution_admin` are configured in Keycloak but **not used in this increment**.

---

## Content Ownership Model

All content (nodes, topics, exams) is tagged with `owner_type` and `owner_id`:

| owner_type | owner_id | Who creates | Visible to |
|---|---|---|---|
| `platform` | `NULL` | Platform Admin | All authenticated students |
| `parent` | parent `idp_sub` (UUID) | Parent | Linked children only (via `parent_child_links`) |

Parent content is **private** — never shared to a marketplace, never visible to unlinked students.

---

## Key Design Decisions

1. **No Redux, no Axios** — raw `fetch` with `credentials: 'include'`; custom hooks using `useState`/`useEffect`.
2. **SQLAlchemy imperative mapping** — domain models are plain dataclasses; no `Base` subclassing in `domain/models/`.
3. **DDD folder structure** — no business logic in route files: `api/routes/`, `domain/models/`, `domain/services/`, `domain/repositories/`, `infrastructure/`, `schemas/`, `auth/`.
4. **Existing schema sacred** — `ALTER TABLE` only; no column drops or renames.
5. **`admin` = Platform Admin** — scoped exclusively to platform board content management. No user management in this increment.
6. **Parent as content creator** — parents are modelled similarly to tutors (content publishers) but their content is private to one linked child, not marketplace-facing. Parents are fully responsible for the quality of content and exams they create; no instructor oversight in this increment.

7. **Domain `ValueError` maps to HTTP 400, with the message shown to the client** (added 2026-08-07). Domain
   services raise `ValueError` for invalid user input — malformed questions, empty titles, disallowed video
   hostnames. A dedicated `@app.exception_handler(ValueError)` in `src/main.py` returns
   `400 {"detail": "<message>"}`. Previously these fell through to the `Exception` catch-all and surfaced as
   an opaque `500`, which logged a stack trace and told the user nothing about what they had typed wrong.

   **Only a *bare* `ValueError` is echoed.** `ValueError` has library subclasses whose `str()` is not safe
   to return: `pydantic.ValidationError` renders field names, type codes and `input_value=` — the caller's
   actual submitted data — and `json.JSONDecodeError` renders parser offsets. Both are `ValueError`
   subclasses, so an unguarded handler leaks them. The handler therefore checks `type(exc) is ValueError`
   and hands anything else to the generic 500 handler. This is safe to rely on because no domain exception
   in `domain/exceptions.py` inherits from `ValueError` and all ~53 domain raise sites use it bare — if that
   ever changes, the guard must change with it. Locked by tests in `tests/unit/test_main.py` that assert the
   subclass premise and that neither field names, `input_value`, nor parser offsets reach the client.

   **The consequence to keep in mind when writing one:** every bare `ValueError` message in `src/` is
   user-facing. Write them as plain sentences aimed at the person who submitted the request, and do not
   interpolate internal state (file paths, SQL, secrets, another user's identifiers). Echoing back a value
   the caller themselves supplied — a hostname, a scheme, an ID from their own payload — is fine and is what
   the current messages do. Stack traces and unhandled exceptions still go to the generic 500 handler and are
   never returned.

   > Note the dev/prod split: with `SECURITY__DEBUG=true` (dev only) Starlette's `ServerErrorMiddleware`
   > renders an HTML traceback *instead of* deferring to the `Exception` catch-all, so 500s look very
   > different there. `debug` defaults to `False` and is not set in staging/prod, so the catch-all governs.
