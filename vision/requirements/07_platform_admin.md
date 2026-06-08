# hAIsir — Platform Admin (SuperAdmin) Specification
> Version 1.1 | Part C extracted from `05_06_07_personas.md`.
> Platform Admin maps to the existing `admin` role in Keycloak — no new role required.
> → Depends on: `00_overview.md`, `01_data_model.md`, `02_auth_and_roles.md`
> → Prototype: `haisir_superadmin_flow.html`
> → See also: `05_parent.md`, `06_institution_admin.md`

---

# PART C — SuperAdmin

## C.1 Persona Summary

**Role:** `admin`
**Topbar colour:** `#080F17` (near-black) with red role pill
**Can:** Everything. Full read/write access to all platform data.
**Unique capabilities:** Publish board content, approve/reject institutions, suspend tutors and users, manage feature flags.

---

## C.2 Screen Inventory

Navigation via persistent left sidebar.

| # | Screen ID | Name |
|---|---|---|
| SA01 | `sa-dashboard` | Platform dashboard |
| SA02 | `sa-boards` | Board content manager |
| SA03 | `sa-institutions` | Institution manager |
| SA04 | `sa-tutors` | Tutor marketplace manager |
| SA05 | `sa-users` | User and role manager |
| SA06 | `sa-settings` | Platform settings |

---

## C.3 Screen Specifications

### SA01 — Platform Dashboard

**Stat row (5):** Active institutions, Total students, Teachers, Inactive institutions, Suspended tutors.

**AI health stat row (4):** hAITU resolution rate %, Total doubts this month, Escalation rate %, Teacher resolution rate %.

**Charts (2×2):**
- Board adoption (horizontal bars per board, value = institution count).
- Weakest topics platform-wide (avg completion, bars).
- Most escalated topics (count, bars) + note "High counts = gaps in hAITU board content."
- hAITU resolution rate by board (bars).

**Institution health table:** Active institutions with health status.

**Activity feed:** Recent platform events (enrollments, tutor submissions, board publishes, registrations).

**Business rules:**
- **BR-SA-001:** hAITU resolution rate = platform-wide across all doubts in current month.
- **BR-SA-002:** Activity feed shows last 20 events from a `platform_events` log table, newest first.
- **BR-SA-003:** HAITU_RESOLUTION_DROPPED notification fires when monthly resolution rate drops below 80% (configurable in settings).

**API calls:**
```
GET /api/admin/dashboard
→ Auth: admin
→ Returns: {
    stats: {institutions, students, teachers, pending_institutions, pending_tutors},
    ai_health: {resolution_rate, doubts_total, escalation_rate, teacher_resolution_rate},
    board_adoption: [{board_label, institution_count}],
    weak_topics: [{label, avg}],
    escalated_topics: [{label, count}],
    resolution_by_board: [{board_label, rate}],
    institution_health: [{name, board, students, health}],
    activity_feed: [{type, text, created_at}]
  }
```

### SA02 — Board Content Manager

**Layout:**
- Board tabs (NCERT / JNV / CBE / + Add board) across tree header. Each tab shows: board icon, label, version badge (e.g. v2.4), live/draft status dot.
- Left tree: arbitrary-depth node tree for the active board. Each node shows: expand/collapse toggle, type badge (with 🔒 for reserved types), live/draft status dot.
- Right detail — two modes:
  - **Non-leaf node selected:** Child node list + "+ Add child node" button.
  - **Leaf node selected:** Topic cards (each showing title, status badge, content count, adoption pill "N institutions") + "+ Add topic" and "Publish" / "Publish update" buttons.

**Node-type picker (Add node modal):**
- Reserved types (`grade`, `subject`) shown as chips with 🔒 icon and help text: *"Reserved types have special system behaviour and cannot be repurposed."*
- Default types (`course`, `chapter`, `module`, `section`, `unit`, `week`) as standard chips.
- "Custom…" option reveals a free-text input.

**Add board modal:**
- Board name input.
- Path type selector: **structured** (board-controlled curriculum — NCERT, Cambridge, IB) vs **flexible** (tutor-built open courses). Maps to `categories.path_type`.

**Leaf-node rule:** Topics can only be added to leaf nodes. "+ Add topic" button is shown only for leaf nodes. `POST /api/admin/boards/{board_id}/topics` returns 400 if the target `course_path_node` has children.

**Adoption count:** How many institutions have adopted this board. Shown as "N institutions" pill on topic cards and in the Publish modal.

**Publish flow:**
- Click "Publish" (new board) or "Publish update" (existing) → modal shows: adoption count warning ("Publishing will push this version to all N institutions…"), optional version notes textarea, "Notify institution admins of this update" checkbox.
- Confirm → publishes and increments version.

**Business rules:**
- **BR-SA-004:** SuperAdmin is the only role that can modify `owner_type = 'platform'` nodes and topics.
- **BR-SA-005:** Publishing a board update propagates to all `board_adoptions` for this board. For each adopted topic: if the institution's version still matches the board original (i.e. `owner_type = 'institution'` but unmodified since adoption), it is updated to the new board version. If the institution has modified the topic since adoption, it is preserved as-is. Institution-created custom topics are never touched. See also BR-INST-006.
- **BR-SA-006:** Version string increments automatically on publish (e.g. v2.4 → v2.5). SuperAdmin can override.
- **BR-SA-007:** Adoption count = `board_adoptions` where `board_id` matches and `status = 'active'`.
- **BR-SA-008:** Reserved node types (`grade`, `subject`) cannot be used as custom types by any non-admin role. Admin can create nodes of any type including reserved.

**API calls:**
```
GET /api/admin/boards/{board_id}/tree
→ Auth: admin
→ Returns: [{id, name, node_type, parent_id, order, status, version, adoption_count, children: [...], topics: [{id, title, status, content_count, adoptions}]}]

POST /api/admin/boards/{board_id}/nodes
→ Auth: admin
→ Body: {parent_id?: uuid, name: str, node_type: str}
→ Returns: {node_id}

POST /api/admin/boards/{board_id}/topics
→ Auth: admin
→ Body: {course_path_node_id: uuid, title: str, status: "draft"}
→ Returns: {topic_id}
→ Errors: 400 if course_path_node has children (leaf-node enforcement)

POST /api/admin/boards/{board_id}/publish
→ Auth: admin
→ Body: {version_notes: str, notify_admins: bool}
→ Returns: {new_version: str, institutions_notified: int}
→ Side effects:
    - Updates board.current_version
    - Creates BOARD_CONTENT_UPDATED notification for all institution admins using this board

PATCH /api/admin/topics/{topic_id}
→ Auth: admin
→ Body: {title?, description?, status?, order?}
→ Returns: updated topic

POST /api/admin/boards
→ Auth: admin
→ Body: {name: str, path_type: "structured" | "flexible"}
→ Returns: {board_id, category_id}
```

### SA03 — Institution Manager

**Two tabs (Phase 1):** Active (N) | Inactive (N)

> **Phase note:** The "Pending approval" tab is **not included in Phase 1**. SuperAdmin creates institutions directly (no pending state). Institution self-registration (which would create pending entries) is behind a feature flag (`institution_self_registration`) that is off by default and not implemented in v1. The Pending tab will be added when self-registration is built.

**Active/Inactive tab:** Data table with columns: Institution, Board, Students, Teachers, Plan, Health, Actions (View / Deactivate).

**Onboard modal:** Institution name, board, city, admin email, grades offered, plan.

**Business rules:**
- **BR-SA-008:** Creating an institution sends a Keycloak invite to the admin email and sets `status = 'active'` immediately.
- **BR-SA-009:** Deactivating an institution sets `status = 'inactive'`. Students and teachers lose access. Data is preserved.
- **BR-SA-010:** Institution plan is informational only in this version — no payment gating.

**API calls:**
```
GET /api/admin/organizations?status={active|inactive}
→ Auth: admin
→ Note: ?status=pending not supported in v1 (no self-registration flow yet)
→ Returns: [{id, name, board, city, plan, students, teachers, status, health, joined_at}]

POST /api/admin/organizations
→ Auth: admin
→ Body: {name, board_id, city, admin_email, grades, plan}
→ Returns: {org_id, invite_sent: bool}

PATCH /api/admin/organizations/{org_id}/status
→ Auth: admin
→ Body: {status: "active"|"inactive"}
→ Returns: {updated_at}
```

### SA04 — Tutor Marketplace Manager

**Two tabs:** Published (N) | Suspended (N)

**Per tutor row:** Name, Subjects, Students, Rating, Status, Actions (View / Suspend or Restore).

**Business rules:**
- **BR-SA-011:** Tutors auto-publish when they set `marketplace_listed = true`. No admin approval required (federated model). Admin can suspend a tutor at any time by setting `marketplace_suspended = true`, which immediately hides them from student discovery regardless of `marketplace_listed`.
- **BR-SA-012:** Flagged tutors are those reported by students or institution admins via a reporting flow (out of scope for this version — flag is set manually by SuperAdmin as a suspend action).

**API calls:**
```
GET /api/admin/tutors?status={published|suspended}
→ Auth: admin
→ Returns: [{idp_sub, name, subjects, student_count, rating, marketplace_listed, marketplace_suspended, joined_at}]

PATCH /api/admin/tutors/{idp_sub}/suspend
→ Auth: admin
→ Returns: {marketplace_suspended: true}

PATCH /api/admin/tutors/{idp_sub}/restore
→ Auth: admin
→ Returns: {marketplace_suspended: false}
```

### SA05 — User and Role Manager

**Stat row:** Students, Instructors, Tutors, Institution Admins, Suspended.

**User table:** Name, Email, Role (colour pill), Institution, Status, Actions (View / Edit role / Suspend or Restore).

**Filters:** Role, Institution, Status.

**Business rules:**
- **BR-SA-013:** Suspending a user revokes their Keycloak session and sets their account to disabled in Keycloak.
- **BR-SA-014:** Restoring a user re-enables their Keycloak account. They must log in again.
- **BR-SA-015:** Role changes are made directly in Keycloak via the Admin REST API.

**API calls:**
```
GET /api/admin/users?role={}&institution_id={}&status={}&q={}&limit=&offset=
→ Auth: admin
→ Returns: [{idp_sub, name, email, roles: [str], institution, status}]

PATCH /api/admin/users/{idp_sub}/suspend
→ Auth: admin
→ Side effect: disables Keycloak account
→ Returns: {status: "suspended"}

PATCH /api/admin/users/{idp_sub}/restore
→ Auth: admin
→ Side effect: enables Keycloak account
→ Returns: {status: "active"}
```

### SA06 — Platform Settings

**AI Configuration card:** Model selector (claude-sonnet / claude-opus / claude-haiku), hAITU toggle per role (student / teacher / parent), max tokens per student query.

**Platform Features card:** Toggle — tutor marketplace, open learning track, parent portal, public tutor profiles, hAITU global on/off, institution self-registration (flag defined; implementation deferred).

**Announcements card:** Banner text, severity selector (info/warning/critical), "Update banner" button.

**Board Content Settings card:** Auto-notify institutions on publish, allow institution customisation, require publish approval.

**Danger Zone:** Maintenance mode toggle, purge AI conversation logs (requires 2FA confirmation).

**Business rules:**
- **BR-SA-016:** Feature flags are stored in a `platform_settings` table as key-value pairs. They are loaded at application startup and cached with a 5-minute TTL.
- **BR-SA-017:** Maintenance mode sets a `maintenance_mode = true` flag. The frontend checks this on each page load and redirects to a maintenance page. Only admin-role sessions bypass maintenance mode.
- **BR-SA-018:** Purge AI logs deletes `doubt_messages` where `sender_type = 'ai'` older than the configured retention period (default 90 days, configurable via `ai_log_retention_days` in platform settings). Scope is `doubt_messages` with `sender_type = 'ai'` only — teacher-tools outputs and parent-report outputs are generated on demand and never stored as persistent rows, so there is nothing to purge for those. Requires explicit 2FA confirmation — do not implement without 2FA check. The Danger Zone description shows the current configured retention period.

**API calls:**
```
GET /api/admin/settings
→ Auth: admin
→ Returns: {
    model: str,
    haitu_enabled: {student, teacher, parent},
    haitu_enabled_global: bool,          // flag 5 — global AI on/off; when false all hAITU calls return graceful "AI is currently unavailable"
    max_tokens: {topic_doubt, exam_review_chat, escalation_attempt, teacher_tools_plan, teacher_tools_questions, teacher_tools_report, parent_topic_description, parent_report, parent_topic_explain, exam_analysis},
    features: {
      marketplace: bool,
      open_learning: bool,
      parent_portal: bool,
      public_tutor_profiles: bool,
      institution_self_registration: bool  // flag 6 — defined now; implementation deferred
    },
    banner: {text, severity} | null,
    maintenance_mode: bool,
    ai_log_retention_days: int           // default 90; used by purge-ai-logs endpoint
  }

PATCH /api/admin/settings
→ Auth: admin
→ Body: partial settings object
→ Returns: updated settings

POST /api/admin/purge-ai-logs
→ Auth: admin
→ Body: {totp_code: str}  // 2FA verification
→ Returns: {deleted_count: int}
```

---

## Edge Cases (SuperAdmin)

| Scenario | Behaviour |
|---|---|
| Board publish while another publish is in progress | Queue the second publish. Show "A publish is already in progress — this will run after it completes." |
| Suspend a currently-logged-in user | Revoke Keycloak session immediately. User sees login screen on next API call. |
| Resolution rate alert threshold | Configurable in settings. Default 80%. Alert fires once per week if threshold is breached. |
