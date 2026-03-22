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
| `student` | Self-selected during onboarding (see section 6) |
| `parent` | Self-selected during onboarding (see section 6). Institution admin can also invite a parent to link them to a specific student within the institution |
| `tutor` | Explicit "Become a tutor" registration flow, separate from onboarding (like Udemy's instructor signup) |
| `instructor` | Invited by institution_admin via email/userid — never self-assigned |
| `institution_admin` | Assigned by platform admin via Keycloak Admin API — never self-assigned |
| `admin` | Dedicated accounts — never assigned via API |

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
→ Body: {role: "student" | "parent"}
→ Action: calls Keycloak Admin API to assign realm role to current user's Keycloak account
→ Returns: {assigned: true, role: str}
→ Errors:
    400 if role not in self-assignable set
    403 if role is 'instructor', 'tutor', 'institution_admin', or 'admin'
→ Note: Does NOT require X-Current-Role — user may not have an active role yet during onboarding

POST /api/users/me/become-tutor
→ Auth: any authenticated user (valid session cookie)
→ Body: {subjects, grades, bio?, rate_per_session?, availability?, marketplace_listed}
→ Action: assigns 'tutor' role in Keycloak, creates tutor profile
→ Returns: {assigned: true, role: "tutor", profile_id}
→ Errors: 409 if user already holds tutor role
→ Note: Separate explicit flow — not part of onboarding role selection

POST /api/admin/invite-role
→ Auth: institution_admin (for instructor/parent invites) or admin (for institution_admin)
→ Body: {email_or_sub: str, role: "instructor" | "parent", organization_id?: uuid}
→ Action: sends invite; on acceptance, backend assigns role in Keycloak
→ Returns: {invite_id, status: "sent"}
→ Errors: 403 if caller lacks permission for target role
```

**Assignable roles via this endpoint:**
```python
SELF_ASSIGNABLE_ROLES = {'student', 'parent'}
TUTOR_REGISTRATION_ROLES = {'tutor'}  # separate "Become a tutor" flow
INVITE_ONLY_ROLES = {'instructor'}     # institution_admin invites via email/userid
ADMIN_ONLY_ROLES = {'institution_admin', 'admin'}
```

**Keycloak Admin API call (backend-to-Keycloak):**
```python
# Pseudocode — adapt to your Keycloak client library
async def assign_role_to_user(idp_sub: str, role_name: str):
    role = await keycloak_admin.get_realm_role(role_name)
    await keycloak_admin.assign_realm_roles(idp_sub, [role])
```

The backend needs Keycloak Admin credentials (client_id + client_secret with role management permissions). These should already exist for admin operations — check `haisir-deploy` config.

---

## 5. Frontend Changes

### 5.1 `useAuth` hook — no hardcoded role list to update

The existing `useAuth` hook at `/src/hooks/use-auth.ts` does NOT have a hardcoded `VALID_ROLES` list. Roles are dynamically loaded from the backend via `GET /api/users/me` and filtered server-side by the `UserRole` enum.

**No frontend change needed for role validation.** Once the backend `UserRole` enum is updated (section 4.1), new roles will flow through automatically. The `useAuth` hook stores the active role in `localStorage` under the key `currentRole` and includes it in all API calls via `buildApiHeaders()` in `/src/lib/utils.ts`.

### 5.2 `useAuth` hook — role display metadata

The role switcher UI currently has no role metadata mapping — roles are displayed via `capitalizeFirst(role)` in `/src/components/layout/header/user-menu-dropdown.tsx`. **Create** the following metadata map (this is new code, not an extension of existing code):

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

The role switcher renders one pill per role in `realm_access.roles`. The existing role switcher in `/src/components/layout/header/user-menu-dropdown.tsx` renders role options from `userData.roles` with basic capitalized labels. It will need to be updated to use the `ROLE_META` map (5.2) for colour-coded pills, correct display labels, and destination routes per role.

### 5.4 `X-Current-Role` header — no changes needed

The header is already set generically from the stored active role string. No code change needed — just ensuring the new role strings are valid values in the auth hook (5.1).

### 5.5 Route guards

The existing frontend does not have explicit role-based route guards. Route protection is currently handled at the API level (backend returns 403). **New route guards must be created** for the new persona routes:

New role-specific route guards for new pages:

```typescript
// Add these guards for new routes:
'/institution'  → requires 'institution_admin'
'/parent'       → requires 'parent'
// '/teacher' already exists — also allow 'tutor' role
```

---

## 6. Role Assignment Flows

### 6.1 Onboarding (Student / Parent only)

During onboarding, when a user completes a role setup screen, the frontend calls `POST /api/users/me/assign-role` to assign the role in Keycloak. The JWT must then be refreshed so the new role appears in `realm_access.roles`.

**Sequence:**

```
1. User selects "Student" and/or "Parent" on role selection screen (ON02)
2. User completes student setup (ON03) and/or parent setup (ON05)
3. Frontend calls POST /api/users/me/assign-role {role: "student"} (and/or "parent")
4. Backend assigns role in Keycloak via Admin API
5. Frontend triggers token refresh via silent re-authentication (hidden iframe with prompt=none to /auth/login)
6. APISIX OIDC plugin re-authenticates → new JWT containing new role in realm_access.roles
7. Session cookie updated in-place; useAuth picks up new role, adds to switcher
```

### 6.2 "Become a Tutor" (separate flow)

Any authenticated user can register as a tutor via an explicit flow (similar to Udemy's "Become an instructor"). This is NOT part of onboarding — it's accessible from the user's profile page or a "Become a tutor" link.

**Sequence:**
```
1. User clicks "Become a tutor" from profile or marketing page
2. User fills in tutor profile (subjects, grades, bio, marketplace preference)
3. Frontend calls POST /api/users/me/become-tutor with profile data
4. Backend assigns 'tutor' role in Keycloak + creates tutor profile in one transaction
5. Frontend triggers token refresh (same iframe mechanism as 6.1)
6. Tutor role appears in switcher
```

### 6.3 Instructor Invite (institution_admin flow)

Instructors are never self-assigned. Institution admins invite them.

**Sequence:**
```
1. Institution admin calls POST /api/admin/invite-role {email_or_sub, role: "instructor", organization_id}
2. Backend sends invite (email or in-app notification if user exists)
3. Invited user accepts invite
4. Backend assigns 'instructor' role in Keycloak + creates org membership
5. On next login / token refresh, instructor role appears in switcher
6. First visit to /teacher triggers inline profile setup (subjects, grades, experience)
```

### 6.4 Parent–Child Linking

**Institutional context:** Institution admin invites a parent via `POST /api/admin/invite-role {email_or_sub, role: "parent", organization_id}` and links them to a specific student.

**Open course context:** Either party can initiate:
- Student generates a link code from their profile → parent enters it during onboarding (ON05) or from parent dashboard
- Parent generates an invite from their dashboard → student accepts

**JWT refresh after role assignment:**

```typescript
// After each role assignment, force token refresh via silent re-auth:
const iframe = document.createElement('iframe');
iframe.style.display = 'none';
iframe.src = '/auth/login?prompt=none';
document.body.appendChild(iframe);
iframe.onload = () => {
  document.body.removeChild(iframe);
  // Session cookie now contains a new JWT with the updated realm_access.roles
  await refreshUser(); // re-fetch /api/users/me to pick up new role
};
```

**Token refresh uses silent re-authentication — there is no explicit refresh endpoint.** See `02_auth_and_roles.md` section 4.4 for the full mechanism.

**Fallback — if APISIX refresh endpoint is unavailable:** Use Keycloak silent re-authentication (`prompt=none`) via a hidden iframe. Check the existing `useAuth` implementation for any existing token refresh mechanism before implementing from scratch.

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

**BR-ROLE-004:** The `admin` role must not be combined with any other role on the same Keycloak account. Admin accounts are dedicated platform operator accounts. Enforcement:
1. Keycloak Admin API calls that assign `admin` must first verify the user holds no other realm roles, and vice versa.
2. The backend must reject role assignment requests that would create an `admin` + other-role combination.
3. The `POST /api/users/me/assign-role` endpoint already rejects `admin` (403). Additionally, if the caller already holds `admin`, the endpoint must reject any further role assignment with 403.

**BR-ROLE-005:** All combinations of non-admin roles (`student`, `instructor`, `tutor`, `parent`, `institution_admin`) are allowed without restriction. Each role operates in an independent workspace scoped by its own data boundaries (class enrollment, org membership, parent-child link, tutor-student relationship). This includes combinations of three or more roles — e.g., a user holding `student` + `instructor` + `parent` simultaneously is valid.

### 8.1 Full Combination Matrix

| Combination | Allowed? | Notes |
|---|---|---|
| `student` + `parent` | ✅ Allow | College student who is also a young parent |
| `student` + `tutor` | ✅ Allow | Senior student tutoring juniors (common in Indian coaching culture) |
| `student` + `instructor` | ✅ Allow | Grad student / TA who also teaches |
| `student` + `institution_admin` | ✅ Allow | Unlikely but valid — independent workspaces |
| `instructor` + `tutor` | ✅ Allow | School teacher moonlighting as private tutor (very common in India). See BR-ROLE-001 |
| `instructor` + `institution_admin` | ✅ Allow | Admin who also teaches. See BR-ROLE-002 |
| `instructor` + `parent` | ✅ Allow | Teacher tracking their own child's progress |
| `tutor` + `parent` | ✅ Allow | Tutor monitoring their own child |
| `tutor` + `institution_admin` | ✅ Allow | Institution manager who also tutors independently |
| `parent` + `institution_admin` | ✅ Allow | School manager who is also a parent. See BR-ROLE-003 |
| `admin` + any other role | ❌ Forbid | Admin is a dedicated platform operator account. See BR-ROLE-004 |

### 8.2 Enforcement Layers

| Rule | Enforcement layer | Mechanism |
|---|---|---|
| `admin` cannot combine with other roles | Keycloak (primary) + Backend API (secondary) | Keycloak Admin API calls verify no other roles before assigning `admin`, and vice versa. Backend rejects role assignment if user already holds `admin`. |
| `institution_admin` is never self-assigned | Backend API | `POST /api/users/me/assign-role` returns 403. Only backend Keycloak Admin service client assigns it. |
| All non-admin combos allowed | No enforcement needed | Role switcher and workspace scoping handle separation. |

---

## 9. Testing Checklist

After implementing these changes, verify:

- [ ] New roles appear in Keycloak Admin Console → Realm roles
- [ ] `POST /api/users/me/assign-role` with `tutor` → returns 403 (tutor requires separate `POST /api/users/me/become-tutor`)
- [ ] `POST /api/users/me/become-tutor` with valid profile data → assigns tutor role in Keycloak + creates profile → JWT refresh contains new role
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
- [ ] User holding `admin` → cannot be assigned any additional role (403)
- [ ] User holding any non-admin role → cannot be assigned `admin` via Keycloak Admin API (rejected)
- [ ] User with `student` + `tutor` + `parent` → all three pills shown in switcher
- [ ] User with `instructor` + `institution_admin` + `parent` → all three pills shown, scoping correct per role
