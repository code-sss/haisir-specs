# Auth & Roles

> **Target state scope:** `student`, `parent`, `admin` only. See `vision/requirements/02_auth_and_roles.md` for the full multi-role vision.

---

## Auth Architecture

### Request flow (all authenticated routes)

```
Browser sends:
  Cookie: <session_cookie>          (set by APISIX OIDC plugin)
  X-CSRF-Token: <token>             (double-submit, required on all mutations)
  X-Current-Role: <role>            (active persona context)

APISIX injects upstream:
  Authorization: Bearer <JWT>       (RS256, signed by Keycloak)

FastAPI receives all four. Never reads cookies directly.
```

### CSRF
- Pattern: double-submit cookie (`fastapi-csrf-protect`)
- Bootstrap: `GET /api/auth/csrf` → token in response body + `Set-Cookie`
- Mutations: include token in `X-CSRF-Token` header
- Frontend: use `fetchWithCSRFRetry()` — auto-retries on 403

### JWT
- Keycloak signs RS256; APISIX validates via JWKS (24-hour cache)
- `sub` claim is `idp_sub` — UUID string used as identity across all tables
- Rotate signing keys with 24-hour overlap

---

## Roles (this increment)

| Role | Keycloak realm role | Assignment method |
|---|---|---|
| `student` | `student` | Self-registers → auto-assigned via `POST /api/users/me/assign-role` at ON02 |
| `parent` | `parent` | Self-registers → auto-assigned via `POST /api/users/me/assign-role` at ON02 |
| `admin` | `admin` | Manual Keycloak console only — never self-assigned |

`POST /api/users/me/assign-role` accepts only `student` or `parent`. Any other value → 422.
`admin` cannot combine with any other role (BR-ROLE-004).

---

## FastAPI Auth Layer

```python
# Resolved from JWT by auth middleware
CurrentUser: idp_sub, email, name, email_verified, roles: list[str], current_role: str

# Role guard (Depends factory in auth/roles.py)
@router.get("/resource", dependencies=[Depends(require_role("student"))])
```

**Endpoints exempt from `X-Current-Role`** (onboarding endpoints):
- `GET /api/users/me`
- `PATCH /api/users/me/onboarding-complete`
- `POST /api/users/me/assign-role`

---

## Permission Matrix

### Student (`X-Current-Role: student`)

| Resource | Allowed |
|---|---|
| Platform `course_path_nodes` / `topics` / `topic_contents` | Read (visibility filter applied) |
| Parent Home Study nodes/topics (linked parent only) | Read (visibility filter applied) |
| Platform `exam_templates` | Read |
| Parent `exam_templates` (linked parent only) | Read |
| Own `exam_sessions` | Read + submit |
| Own `student_profiles` | Read + write |
| Own `parent_link_codes` | Read + generate |
| Other students' data | 404 (not 403) |

### Parent (`X-Current-Role: parent`)

| Resource | Allowed |
|---|---|
| Platform `course_path_nodes` / `topics` | Read (browse for adoption — no write) |
| Own curriculum nodes (`owner_id = self`) | Full CRUD |
| Own curriculum topics (`owner_id = self`) | Full CRUD |
| Own `topic_contents` (upload to own topics) | Read + upload |
| Own `exam_templates` (`owner_id = self`) | Full CRUD |
| Child's `exam_sessions` (parent-owned exams only, linked child only) | Read scores |
| Own `parent_profiles` | Read + write |
| `parent_child_links` | Create + revoke |
| Adopt platform board (`POST /api/parent/curriculum/adopt`) | ✓ |

### Platform Admin (`X-Current-Role: admin`)

| Resource | Allowed |
|---|---|
| Platform `course_path_nodes` / `topics` / `topic_contents` (`owner_type = 'platform'`) | Full CRUD |
| Platform `exam_templates` (`owner_type = 'platform'`) | Full CRUD |
| Parent-owned content | No access |
| Student / parent data | No access |

---

## Security Rules

- **BR-SEC-001:** All endpoints require JWT; only `/api/health` and OIDC endpoints are unauthenticated.
- **BR-SEC-002:** Students receive 404 (not 403) for other students' data.
- **BR-SEC-003:** Parent access to child data requires an active (`revoked_at IS NULL`) `parent_child_links` record; revocation removes access immediately.
- **BR-SEC-004:** Parent content (`owner_type='parent'`) is never visible to students without a valid `parent_child_links` linking `owner_id` to the requesting student.
- **BR-SEC-005:** Platform Admin cannot read or modify parent-owned content.
- **BR-SEC-006:** `X-Current-Role` defaults to first role in JWT if missing (onboarding endpoints excepted).
- **BR-SEC-007:** Never log JWT, CSRF tokens, or session cookies; use structlog with redaction.
- **BR-SEC-008:** `POST /api/users/me/assign-role` accepts only `student` or `parent` → 422 otherwise.

---

## Token Refresh After Role Assignment

1. `POST /api/users/me/assign-role` → Keycloak Admin API assigns role via client-credentials.
2. Frontend writes optimistic role to `localStorage` via `setCurrentRole()` in `useAuth`.
3. Frontend navigates to `/auth/logout` (explicit logout — not `prompt=none`).
4. Keycloak login → APISIX OIDC → session cookie updated with new JWT containing the new role.
5. ON01 role-aware redirect → `/onboarding/student-ready?next=go` or `/onboarding/parent-ready?next=go`.

See `Implementation_planning/decisions.md` (2026-03-27) for why `prompt=none` was rejected.
