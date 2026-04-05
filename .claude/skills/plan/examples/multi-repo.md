# Worked Example: Multi-Repo Plan

## Phase 1c-pre — X-Current-Role Enforcement

This example shows a complete plan for a feature spanning backend and frontend repos, with cross-repo dependencies and parallel work.

---

## Planning Inputs

- **Root goal:** All role-gated API endpoints require the `X-Current-Role` header; missing header returns 400.
- **Scope:** Backend auth enforcement + frontend confirmation + field name fix.
- **Constraints:** Three exempt endpoints (GET /api/users/me, POST /api/users/me/assign-role, PATCH /api/users/me/onboarding-complete). APISIX injects JWT, client sends X-Current-Role. Existing 1810+ tests must stay green at 100% coverage.
- **Done when:** Missing header on any non-exempt endpoint returns 400; exempt endpoints work without header; frontend sends header on every call.

---

## Goal Tree

```
ROOT: X-Current-Role Enforcement
├── G1 [backend]: Strict header validation
│   ├── T1.1 [backend]: Split current_active_user into strict + lenient
│   ├── T1.2 [backend]: Wire exempt endpoints to lenient dependency
│   ├── T1.3 [backend]: Add strict auth unit tests
│   └── T1.4 [backend]: Add lenient auth unit tests
├── G2 [frontend]: Header compliance
│   ├── T2.1 [frontend]: Add BR-SEC-006 contract comment to buildApiHeaders
│   └── T2.2 [frontend]: Fix CreateNodeInput.position → order field name
└── G3: Cross-repo verification
    └── T3.1 [backend]: E2E test — header missing → 400, header present → 200, exempt → 200
```

---

## G1 [backend]: Strict header validation

### T1.1 [backend]: Split current_active_user into strict + lenient

**Build:** In `src/auth/user.py`, split `current_active_user` into two functions. `current_active_user` (strict): when `x_current_role is None`, raise `HTTPException(400, "X-Current-Role header required")`. `current_active_user_lenient`: preserve old behavior (defaults to `roles[0]`).

**Done when:** Calling `current_active_user` with `x_current_role=None` raises `HTTPException(400)`.

**Test:** `test_strict_auth_rejects_missing_role_header` — call with `x_current_role=None`, assert `HTTPException` with status 400.

**Depends on:** None.

---

### T1.2 [backend]: Wire exempt endpoints to lenient dependency

**Build:** In `src/api/routes/user.py`, change the three exempt endpoints from `Depends(current_active_user)` to `Depends(current_active_user_lenient)`. For `PATCH /me/onboarding-complete`, also add inline role check for student/parent.

**Done when:** Exempt endpoints accept requests without `X-Current-Role` header; non-exempt endpoints reject them.

**Test:** `test_exempt_endpoints_accept_missing_header` — call GET /me, POST /me/assign-role, PATCH /me/onboarding-complete without header, assert 200/success.

**Depends on:** T1.1 [backend].

---

### T1.3 [backend]: Add strict auth unit tests

**Build:** Update `tests/unit/auth/test_user.py`. Change `test_valid_payload_default_role` to expect `HTTPException(400)` when strict auth receives `x_current_role=None`.

**Done when:** `uv run pytest tests/unit/auth/test_user.py -v` passes.

**Test:** The test itself is the verification.

**Depends on:** T1.1 [backend].

---

### T1.4 [backend]: Add lenient auth unit tests

**Build:** Add `TestCurrentActiveUserLenient` test class to `tests/unit/auth/test_user.py`. Test that lenient auth with `x_current_role=None` returns user with `current_role = roles[0]`.

**Done when:** `uv run pytest tests/unit/auth/test_user.py::TestCurrentActiveUserLenient -v` passes.

**Test:** The test itself is the verification.

**Depends on:** T1.1 [backend].

---

## G2 [frontend]: Header compliance

### T2.1 [frontend]: Add BR-SEC-006 contract comment to buildApiHeaders

**Build:** Add a code comment to `src/lib/utils.ts` `buildApiHeaders()` documenting the BR-SEC-006 contract and the three exempt endpoints.

**Done when:** Comment exists and accurately describes the contract.

**Test:** Read the file, verify comment is present and matches spec.

**Depends on:** None.

---

### T2.2 [frontend]: Fix CreateNodeInput.position to order field name

**Build:** In `src/features/admin/types/admin.types.ts`, rename `CreateNodeInput.position` to `order`. Update `src/features/admin/api/admin-api.ts` to send `order` instead of `position`.

**Done when:** `pnpm typecheck` passes and network request sends `order` field.

**Test:** Existing admin tests pass; manual verify network tab shows `order` not `position`.

**Depends on:** None.

---

## G3: Cross-repo verification

### T3.1 [backend]: E2E acceptance test

**Build:** After all other tasks, run full test suite: `uv run pytest --cov --cov-fail-under=100` and `pnpm test:coverage`. Manual: send request without header to non-exempt endpoint -> 400; send to exempt endpoint -> 200.

**Done when:** All tests pass, manual verification confirms behavior.

**Test:** This IS the acceptance test for the root goal.

**Depends on:** T1.2 [backend], T1.3 [backend], T1.4 [backend], T2.1 [frontend], T2.2 [frontend].

---

## TASKS.md Output

```markdown
# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:a293bf8 frontend:cc9d69a deploy:8bf1b5d (2026-04-05)

## G1 [backend]: Strict header validation
- [ ] T1.1 [backend]: Split current_active_user into strict + lenient
- [ ] T1.2 [backend]: Wire exempt endpoints to lenient dependency
- [ ] T1.3 [backend]: Add strict auth unit tests
- [ ] T1.4 [backend]: Add lenient auth unit tests
- [ ] **G1: Strict header validation** — integration test

## G2 [frontend]: Header compliance
- [ ] T2.1 [frontend]: Add BR-SEC-006 contract comment
- [ ] T2.2 [frontend]: Fix position → order field name
- [ ] **G2: Header compliance** — integration test

## G3: Cross-repo verification
- [ ] T3.1 [backend]: E2E acceptance test
- [ ] **G3: Cross-repo verification** — acceptance test

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T1.1 [backend]: Split current_active_user (no deps)
- T2.1 [frontend]: Add BR-SEC-006 doc comment (no deps)
- T2.2 [frontend]: Fix position → order (no deps)
```

---

## What to notice

1. **Tasks are tagged by repo** — `/implement-backend` picks T1.1, `/implement-frontend` picks T2.1. Each skill filters by its own repo tag.
2. **Cross-repo deps are explicit** — T1.2 depends on T1.1 (same repo), T3.1 depends on tasks in both repos. No implicit assumptions.
3. **Parallel work is visible** — backend and frontend have independent "Ready now" tasks. Two developers can start immediately in different repos.
4. **G3 (cross-repo verification) depends on everything else** — it is the root acceptance test. It cannot run until both repos are done.
5. **Goals span repos (G3 touches both) but leaf tasks never do** — every leaf task has exactly one repo tag and touches files in only that repo.
