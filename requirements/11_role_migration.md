# hAIsir — Role Migration Specification
> Version 1.0 | Exact changes required to extend the existing role system for new personas.
> This file documents what to change in the existing codebase — not what to build from scratch.
> → Depends on: `00_overview.md`, `02_auth_and_roles.md`

---

## 1. Current State

The existing codebase has three Keycloak realm roles and all auth logic is written for these three only:

| Role | Exists | Where used |
|---|---|---|
| `student` | ✅ | Keycloak, `auth/roles.py`, `useAuth` hook, localStorage |
| `instructor` | ✅ | Keycloak, `auth/roles.py`, `useAuth` hook, localStorage |
| `admin` | ✅ | Keycloak, `auth/roles.py`, `useAuth` hook, localStorage |

The `X-Current-Role` header is validated against these three values only. Any other value currently returns 400 or is rejected silently.

---

## 2. New Roles Required

| Role | Status | Maps to persona |
|---|---|---|
| `institution_admin` | ❌ Add | Institution Admin |
| `tutor` | ❌ Add | Independent Tutor |
| `parent` | ❌ Add | Parent |

---

## 3. Keycloak Changes

### 3.1 Add realm roles

In the `haisir` Keycloak realm, add three new realm-level roles:

```
institution_admin
tutor
parent
```

Do this via Keycloak Admin Console → Realm roles → Create role. Or via Keycloak Admin REST API:

```bash
# For each new role:
POST /admin/realms/haisir/roles
{
  "name": "institution_admin",
  "description": "Institution curriculum builder and people manager"
}

POST /admin/realms/haisir/roles
{
  "name": "tutor",
  "description": "Independent tutor — owns curriculum, manages own students"
}

POST /admin/realms/haisir/roles
{
  "name": "parent",
  "description": "Read-only access to linked child's progress"
}
```

### 3.2 Role assignment flows

| Role | Assignment method |
|---|---|
| `institution_admin` | Admin assigns via Keycloak Admin API — never self-assigned |
| `tutor` | Auto-assigned by backend on onboarding completion (see section 6) |
| `parent` | Auto-assigned by backend on onboarding completion (see section 6) |

### 3.3 No changes to existing role definitions

`student`, `instructor`, `admin` — leave completely unchanged. Do not modify their descriptions, composite role settings, or any existing client scope mappings.

---

## 4. Backend Changes

### 4.1 `auth/roles.py` — extend role validation

The existing `require_role()` factory and `X-Current-Role` validation must accept the new role values.

**Current valid roles list (find in `auth/roles.py` or equivalent):**
```python
VALID_ROLES = {'student', 'instructor', 'admin'}
```

**Update to:**
```python
VALID_ROLES = {
    'student',
    'instructor',
    'admin',
    'institution_admin',  # new
    'tutor',              # new
    'parent',             # new
}
```

### 4.2 Add new `Depends` factories

Add to `auth/roles.py` following the exact same pattern as existing role decorators:

```python
def require_institution_admin():
    return require_role('institution_admin')

def require_tutor():
    return require_role('tutor')

def require_parent():
    return require_role('parent')
```

These are thin wrappers — the existing `require_role()` logic handles everything. Do not duplicate the JWT validation or CSRF logic.

### 4.3 `CurrentUser` dataclass — no changes needed

The existing `CurrentUser` dataclass stores `current_role: str` and `roles: list[str]`. Because these are already generic strings, no structural change is needed — only the validation set in `auth/roles.py` needs updating (done in 4.1).

### 4.4 `X-Current-Role` header validation

Find the middleware or dependency that validates the `X-Current-Role` header value. Update the allowed set to include the three new roles (same as 4.1 — these may be in the same place or separate).

If the validation is a hardcoded conditional, replace with a set lookup:

```python
# Before (example — match your existing pattern):
if active_role not in ('student', 'instructor', 'admin'):
    raise HTTPException(400, "Invalid X-Current-Role value")

# After:
VALID_ROLES = {'student', 'instructor', 'admin', 'institution_admin', 'tutor', 'parent'}
if active_role not in VALID_ROLES:
    raise HTTPException(400, "Invalid X-Current-Role value")
```

### 4.5 Role assignment endpoint

A new backend endpoint is needed to assign Keycloak roles programmatically during onboarding. This calls the Keycloak Admin REST API from the backend — the client never assigns roles directly.

```
POST /api/users/me/assign-role
→ Auth: any authenticated user (valid session cookie)
→ Body: {role: "tutor" | "parent" | "student" | "instructor"}
→ Action: calls Keycloak Admin API to assign realm role to current user's Keycloak account
→ Returns: {assigned: true, role: str}
→ Errors:
    400 if role not in assignable set
    403 if role is 'institution_admin' or 'admin' (these are never self-assigned)
→ Note: Does NOT require X-Current-Role — user may not have an active role yet during onboarding
```

**Assignable roles via this endpoint:**
```python
SELF_ASSIGNABLE_ROLES = {'student', 'instructor', 'tutor', 'parent'}
ADMIN_ONLY_ROLES = {'institution_admin', 'admin'}
```

**Keycloak Admin API call (backend-to-Keycloak):**
```python
# Pseudocode — adapt to your Keycloak client library
async def assign_role_to_user(keycloak_sub: str, role_name: str):
    role = await keycloak_admin.get_realm_role(role_name)
    await keycloak_admin.assign_realm_roles(keycloak_sub, [role])
```

The backend needs Keycloak Admin credentials (client_id + client_secret with role management permissions). These should already exist for admin operations — check `haisir-deploy` config.

---

## 5. Frontend Changes

### 5.1 `useAuth` hook — extend valid roles

Find where `useAuth` validates the stored role from `localStorage` against a known set. Extend it:

```typescript
// Before:
const VALID_ROLES = ['student', 'instructor', 'admin'];

// After:
const VALID_ROLES = [
  'student',
  'instructor',
  'admin',
  'institution_admin',  // new
  'tutor',              // new
  'parent',             // new
];
```

### 5.2 `useAuth` hook — role display metadata

The role switcher UI needs display metadata per role. Add entries for new roles wherever existing roles are mapped to labels and colours:

```typescript
// Extend existing role metadata map:
const ROLE_META: Record<string, { label: string; colour: string; route: string }> = {
  student:           { label: 'Student',            colour: '#0A1F5C', route: '/home/dashboard' },
  instructor:        { label: 'Teacher',             colour: '#0A3D2B', route: '/teacher' },
  admin:             { label: 'Admin',               colour: '#080F17', route: '/admin' },
  // New:
  institution_admin: { label: 'Institution Admin',   colour: '#0D1B2A', route: '/institution' },
  tutor:             { label: 'Tutor',               colour: '#3C1F6E', route: '/teacher' },
  parent:            { label: 'Parent',              colour: '#3D2000', route: '/parent' },
};
```

Note: `tutor` and `instructor` share the `/teacher` route — the teacher dashboard renders differently based on which contexts (classes vs tutor students) the user has.

### 5.3 Role switcher component

The role switcher renders one pill per role in `realm_access.roles`. Since the switcher is already generic (renders based on the roles list), no structural change is needed — only the metadata map (5.2) needs updating so the new roles have correct labels, colours, and destination routes.

### 5.4 `X-Current-Role` header — no changes needed

The header is already set generically from the stored active role string. No code change needed — just ensuring the new role strings are valid values in the auth hook (5.1).

### 5.5 Route guards

Any existing route guards that check the active role must be extended. Find all places where role checks are hardcoded:

```typescript
// Pattern to find and fix:
if (activeRole === 'student' || activeRole === 'instructor' || activeRole === 'admin') {
  // allow
}

// Replace with:
if (VALID_ROLES.includes(activeRole)) {
  // allow
}
```

New role-specific route guards for new pages:

```typescript
// Add these guards for new routes:
'/institution'  → requires 'institution_admin'
'/parent'       → requires 'parent'
// '/teacher' already exists — also allow 'tutor' role
```

---

## 6. Onboarding Role Assignment Flow

During onboarding, when a user completes a role setup screen, the frontend calls `POST /api/users/me/assign-role` to assign the role in Keycloak. The JWT is then refreshed so the new role appears in `realm_access.roles`.

**Sequence:**

```
1. User selects "Student" on role selection screen (ON02)
2. User completes student setup (ON03)
3. Frontend calls POST /api/users/me/assign-role {role: "student"}
4. Backend assigns role in Keycloak
5. Frontend calls Keycloak token refresh endpoint to get updated JWT
6. Updated JWT now contains "student" in realm_access.roles
7. useAuth hook picks up new role, adds to switcher
8. Repeat for each selected role
```

**JWT refresh after role assignment:**

```typescript
// After each role assignment, refresh the token:
// APISIX handles the OIDC token exchange — call the refresh endpoint
await fetch('/api/auth/refresh', {
  method: 'POST',
  credentials: 'include',
  headers: { 'X-CSRF-Token': csrfToken }
});
// New JWT with updated roles is now in the session cookie
```

If APISIX does not expose a refresh endpoint, use the Keycloak token endpoint directly (check existing `useAuth` implementation for how token refresh is currently handled).

---

## 7. `institution_admin` Assignment (Admin-only Flow)

Institution admins are never self-assigned. The flow is:

```
1. Platform admin creates institution via POST /api/admin/organizations
2. Backend calls Keycloak Admin API to invite admin email
3. Invited user registers via Keycloak email link
4. Backend assigns 'institution_admin' role via Keycloak Admin API after registration
5. User lands on onboarding — but role selection is skipped (role already assigned)
6. User goes directly to institution admin dashboard
```

The `POST /api/users/me/assign-role` endpoint must reject `institution_admin` with 403. Only the backend's Keycloak Admin service client can assign this role.

---

## 8. Multi-Role Combinations

These combinations are valid and must work correctly through the role switcher:

| Combination | Example user | Switcher shows |
|---|---|---|
| `student` + `parent` | A student who is also a parent | Student + Parent pills |
| `instructor` + `tutor` | A school teacher who also tutors privately | Teacher + Tutor pills |
| `institution_admin` + `instructor` | Admin who also teaches | Institution Admin + Teacher pills |
| `student` + `instructor` | A grad student who also teaches | Student + Teacher pills |

**BR-ROLE-001:** When a user holds both `instructor` and `tutor`, both appear as separate pills in the role switcher. Switching to `instructor` context shows institutional classes. Switching to `tutor` context shows personal tutor students. They share the `/teacher` route but render different content based on active role.

**BR-ROLE-002:** When a user holds `institution_admin` and switches to `instructor`, the teacher workspace is scoped to their own organisation only — they cannot see classes from other institutions.

**BR-ROLE-003:** There is no combination of `parent` + `institution_admin` that requires special handling — these are fully independent workspaces.

---

## 9. Testing Checklist

After implementing these changes, verify:

- [ ] New roles appear in Keycloak Admin Console → Realm roles
- [ ] `POST /api/users/me/assign-role` with `tutor` → assigns role in Keycloak → JWT refresh contains new role
- [ ] `POST /api/users/me/assign-role` with `institution_admin` → returns 403
- [ ] `POST /api/users/me/assign-role` with `admin` → returns 403
- [ ] `X-Current-Role: institution_admin` on any request → accepted (not 400)
- [ ] `X-Current-Role: tutor` on any request → accepted
- [ ] `X-Current-Role: parent` on any request → accepted
- [ ] `X-Current-Role: unknown_role` → returns 400
- [ ] User with `instructor` + `tutor` roles → both pills shown in switcher
- [ ] Switching to `tutor` → topbar colour changes to `#3C1F6E`
- [ ] Switching to `parent` → topbar colour changes to `#3D2000`
- [ ] Route `/institution` → accessible only with `institution_admin` active role
- [ ] Route `/parent` → accessible only with `parent` active role
- [ ] Existing `student`, `instructor`, `admin` role behaviour → unchanged
