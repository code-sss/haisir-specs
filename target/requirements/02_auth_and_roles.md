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
- Keycloak signs RS256; APISIX validates via JWKS (24-hour cache) **at the gateway**
- The **backend independently re-validates** every JWT (local JWKS decode + optional token introspection — see *Token Introspection* below)
- `sub` claim is `idp_sub` — UUID string used as identity across all tables
- Rotate signing keys with 24-hour overlap

### Token Introspection (backend, RFC 7662)

Layered on top of APISIX gateway validation, the FastAPI backend verifies every JWT in two steps:

1. **Local JWKS decode (always):** verify RS256 signature, `exp`, `iat`, and issuer against Keycloak's JWKS. Fast, no network call — rejects malformed / expired / wrong-issuer tokens immediately.
2. **Introspection (when `introspection_enabled`):** `POST {keycloak}/realms/{realm}/protocol/openid-connect/token/introspect` to confirm the token is *active*. Catches revocation (logout, admin-disabled account, password reset) that stateless JWT validation cannot detect within the 300s access-token lifespan.

- **Introspecting identity:** the existing `haisir-backend-admin` service-account client (credentials already in backend config). The web/gateway client secret is never shared with the backend.
- **Cache:** introspection results are cached per token, keyed by a hash of the token, for a short TTL (`min(configured_ttl, token_remaining_exp)`, default ~30s) to bound Keycloak load. Raw tokens are never stored or logged (BR-SEC-007).
- **Failure mode (fail closed):** Keycloak introspection unreachable → `503`; `active: false` → `401`.
- **Keycloak 26 requirements (provisioned declaratively by deploy):** the introspecting client must have the `token-introspection` client scope as a *default* scope, and must appear in the introspected token's `aud` claim (an audience mapper on the web client adds `haisir-backend-admin` to `aud`). `haisir-deploy/common/scripts/setup-keycloak.sh` provisions both — superseding the temporary `add-token-introspection-scope.sh` workaround.
- **Rollout:** feature-flagged via `introspection_enabled` (default off); enabled in staging before prod.

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

**Endpoints exempt from `X-Current-Role`** (use `current_active_user_lenient`):

*Onboarding — the client has not selected a role yet:*
- `GET /api/users/me`
- `PATCH /api/users/me/onboarding-complete`
- `POST /api/users/me/assign-role`

*Browser subresource — the request cannot carry a custom header (added 2026-08-07, T8.1.3):*
- `GET /images/questions/{filename}`

> The fourth exemption is a different *kind* of exemption from the first three and the distinction
> matters. The onboarding endpoints are exempt because the role is not yet **known**. The image
> endpoint is exempt because the header is not **sendable**: it is fetched by an `<img src>` tag, and
> a browser attaches no custom headers to an image subresource — there is no client-side fix. Under
> the strict dependency it returned `400 X-Current-Role header required` on every render, which is
> how it was found on staging. Authentication is unchanged: the gateway still injects the JWT and
> `verify_token` still runs. Only the role header is waived, and the endpoint never branched on role
> — any authenticated user may read any question image, because students need them mid-exam.
> Locked by a regression test in `tests/unit/routes/test_images.py` that overrides only
> `verify_token`, so the header path actually executes; it fails against the strict dependency.

---

## Permission Matrix

### Student (`X-Current-Role: student`)

| Resource | Allowed |
|---|---|
| Platform `course_path_nodes` / `topics` / `topic_contents` | Read (visibility filter applied) |
| Parent Home Study nodes/topics (linked parent **and** bound to this student) | Read (visibility filter applied — BR-DATA-026) |
| Platform `exam_templates` | Read |
| Parent `exam_templates` (linked parent **and** bound to this student) | Read (BR-DATA-026) |
| Own `exam_sessions` | Read + submit |
| Own `student_profiles` | Read + write |
| Own `parent_link_codes` | Read + generate |
| Dispute own essay grade (`POST .../dispute`) | Yes — own session only, `grading_status = 'released'` |
| Other students' data | 404 (not 403) |

### Parent (`X-Current-Role: parent`)

| Resource | Allowed |
|---|---|
| Platform `course_path_nodes` / `topics` | Read (browse for adoption — no write) |
| Own curriculum nodes (`owner_id = self`) | Full CRUD |
| Own curriculum topics (`owner_id = self`) | Full CRUD |
| Bind/unbind own curriculum root to a linked child | ✓ — actively-linked children only (BR-SEC-024) |
| Own `topic_contents` (upload to own topics) | Read + upload |
| Own `exam_templates` (`owner_id = self`) | Full CRUD |
| Child's `exam_sessions` (parent-owned exams only, linked child only) | Read scores |
| Own `parent_profiles` | Read + write |
| `parent_child_links` | Create + revoke |
| Adopt platform board (`POST /api/parent/curriculum/adopt`) | ✓ |
| Override AI essay grade on own exam (`PATCH .../grade`) | Yes — `exam_templates.owner_id = self` only |
| Confirm AI grade on own exam (`POST .../confirm-grade`) | Yes — `exam_templates.owner_id = self` only |
| Dispute child's essay grade (`POST .../dispute`) | Yes — linked child's session on parent-owned exam only |

### Platform Admin (`X-Current-Role: admin`)

| Resource | Allowed |
|---|---|
| Platform `course_path_nodes` / `topics` / `topic_contents` (`owner_type = 'platform'`) | Full CRUD |
| Platform `exam_templates` (`owner_type = 'platform'`) | Full CRUD |
| Override AI essay grade on platform exam (`PATCH .../grade`) | Yes — `exam_templates.owner_type = 'platform'` only |
| Confirm AI grade on platform exam (`POST .../confirm-grade`) | Yes — `exam_templates.owner_type = 'platform'` only |
| Parent-owned content (incl. parent essay overrides) | No access — BR-SEC-005 |
| Student / parent data | No access |

---

## Security Rules

- **BR-SEC-001:** All endpoints require JWT; only `/api/health` and OIDC endpoints are unauthenticated.
- **BR-SEC-002:** Students receive 404 (not 403) for other students' data.
- **BR-SEC-003:** Parent access to child data requires an active (`revoked_at IS NULL`) `parent_child_links` record; revocation removes access immediately.
- **BR-SEC-004:** Parent content (`owner_type='parent'`) is never visible to a student without **both** a valid `parent_child_links` record linking `owner_id` to the requesting student **and** a `parent_content_bindings` row binding the content's `root_node_id` to that student (BR-DATA-026). An active link alone is no longer sufficient — a child sees only the trees their parent bound to them.
- **BR-SEC-005:** Platform Admin cannot read or modify parent-owned content.
- **BR-SEC-006:** `X-Current-Role` is required on all role-gated endpoints. Missing header returns `400 "X-Current-Role header required"`. Explicit exceptions (use lenient path — no header required): `GET /api/users/me`, `POST /api/users/me/assign-role`, `PATCH /api/users/me/onboarding-complete`, and `GET /images/questions/{filename}` (browser subresource — an `<img src>` cannot send a custom header; authentication still enforced, role never used). See the exemption list above for why the fourth differs in kind from the first three.
- **BR-SEC-007:** Never log JWT, CSRF tokens, or session cookies; use structlog with redaction.
- **BR-SEC-008:** `POST /api/users/me/assign-role` accepts only `student` or `parent` → 422 otherwise.
- **BR-SEC-009:** When `introspection_enabled`, the backend confirms the token is active via Keycloak introspection (RFC 7662) *after* local JWKS validation; an inactive (revoked) token returns `401` even when its signature and expiry are still valid.
- **BR-SEC-010:** Introspection fails closed — if the Keycloak introspection endpoint is unreachable the request is rejected (`503`); a token is never accepted on local JWKS validation alone while introspection is enabled.
- **BR-SEC-011:** Essay grade dispute (`POST .../dispute`) is allowed only for the student who owns the session (own `exam_sessions.user_id = current_user.idp_sub`), or for a parent acting on their linked child's session on a parent-owned exam (`exam_templates.owner_id = parent.idp_sub` AND active `parent_child_links`). All other callers → 403.
- **BR-SEC-012:** Essay grade override and confirm-grade (`PATCH .../grade`, `POST .../confirm-grade`) are allowed only for the exam owner: Parent for `owner_type='parent'` exams (`owner_id = parent.idp_sub`); Admin for `owner_type='platform'` exams. A Platform Admin cannot override or confirm grades on parent-owned exams (BR-SEC-005 extends here). Missing or wrong role → 403.
- **BR-SEC-020:** The backend validates the JWT **audience**. Local JWKS decode asserts the backend's own client is present in `aud` (`verify_aud: True`, or an explicit post-decode assertion). A token minted for a different client in the same realm — including the frontend's own access token — is rejected with `401`. Introspection confirms a token is *active*, not that it was issued *for this API*; without audience validation the two checks together still permit audience confusion. The Keycloak audience mapper adding `haisir-backend-admin` to `aud` is already provisioned (see "JWT" above), so the claim exists to enforce against — confirm APISIX-injected tokens carry it before enabling.
- **BR-SEC-021:** Every backend→Keycloak channel verifies TLS. `OAUTH__KEYCLOAK__SSL_VERIFY` must be `true` in staging and production; the code default is already `true` and must not be overridden. This covers the token-introspection channel (RFC 7662) and the Keycloak Admin API client. An introspection call made over an unverified TLS channel is **not** fail-closed in the sense BR-SEC-010 requires — an on-path attacker can answer `active: true` for a revoked token, silently defeating revocation. Self-signed development certificates are handled by trusting the internal CA, never by disabling verification.
- **BR-SEC-024:** A parent may bind a curriculum root to a child only when an active, non-revoked `parent_child_links` record exists for that pair at bind time. Applied **per binding row** — an `adopt` or `create-node` request naming several children validates every one, and rejects the whole request if any is unlinked or revoked (no partial binding). Enforced on `POST /api/parent/curriculum/nodes`, `POST /api/parent/curriculum/adopt`, and `POST /api/parent/curriculum/nodes/:root_id/bindings`. Binding to a child the caller is not linked to returns `404` (oracle protection — same pattern as BR-PAR-006), never `403`.

> **BR-SEC numbering note:** `13_secrets_management.md` independently allocated **BR-SEC-011 … BR-SEC-019** for secrets-management rules, colliding with BR-SEC-011/012 above. The collision is recorded rather than renumbered — the IDs are referenced from shipped code and past decision entries. It has since taken **BR-SEC-022 … BR-SEC-023** (deploy env files under release control; `ip-restriction` deny-by-default), continuing past this file's 020/021 rather than repeating them, so the 011/012 overlap remains the only one. New rules in **either** file continue from the highest ID allocated across both — next free is **BR-SEC-025** (BR-SEC-024 allocated above for per-child content binding). New cross-cutting infrastructure specs use their own prefix (`BR-INFRA-*`, `BR-WAF-*`, `BR-CSP-*`) rather than extending `BR-SEC-*`.

---

## Token Refresh After Role Assignment

1. `POST /api/users/me/assign-role` → Keycloak Admin API assigns role via client-credentials.
2. Frontend writes optimistic role to `localStorage` via `setCurrentRole()` in `useAuth`.
3. Frontend navigates to `/auth/logout` (explicit logout — not `prompt=none`).
4. Keycloak login → APISIX OIDC → session cookie updated with new JWT containing the new role.
5. ON01 role-aware redirect → `/onboarding/student-ready?next=go` or `/onboarding/parent-ready?next=go`.

See `Implementation_planning/decisions.md` (2026-03-27) for why `prompt=none` was rejected.
