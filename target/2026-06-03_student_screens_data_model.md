# Student Screens → Data Model Mapping
*Discussion notes — 2026-06-03*

---

## The Data Hierarchy

The content tree has four levels, from broad to narrow:

```
categories                     ← the "board" (e.g., NCERT)
  └── course_path_nodes (tree)
        ├── Grade 6               [node_type = 'grade']   ← root of tree
        │     ├── Maths           [node_type = 'subject']
        │     │     ├── Knowing Our Numbers  [node_type = 'chapter']
        │     │     │     └── topics: Large Numbers, Roman Numerals, Estimation
        │     │     ├── Fractions  [node_type = 'chapter']
        │     │     │     └── topics: Types of Fractions, Operations on Fractions
        │     │     └── Algebra    [node_type = 'chapter']
        │     └── Science          [node_type = 'subject']
        │           ├── World of Science  [node_type = 'chapter']
        │           └── Motion & Forces   [node_type = 'chapter']
```

---

## How Each Screen's Tiles Map to the Hierarchy

### S-home — Dashboard tiles

Each tile on the student home dashboard represents a **subject-level `course_path_nodes` row**.

```
"NCERT Maths — Grade 6" tile
    ↑
  course_path_nodes  (node_type='subject', name='Maths', owner_type='platform')
    + parent grade node  → contributes "Grade 6" to the label
    + ancestor category  → contributes "NCERT" to the label
```

- The **progress bar** (e.g. 62%, 11/18 topics done) is computed from all `topics` rows under the chapter descendants of that subject node.
- **Home Study tiles** work the same way but use `owner_type='parent'` nodes, visible only when an active `parent_child_links` record exists for that student.

API: `GET /api/student/dashboard`
→ returns subject-level nodes visible to this student (platform + linked parent)

---

### S-nav — Left sidebar (chapter list)

Each item in the left sidebar is a **chapter-level `course_path_nodes` row**, grouped under its parent subject node as a heading.

```
MATHS  ← subject node (used as a group label, not clickable)
  "Knowing Our Numbers"  ← course_path_nodes (node_type='chapter')
  "Fractions"            ← course_path_nodes (node_type='chapter')
  "Algebra"              ← course_path_nodes (node_type='chapter')

SCIENCE
  "World of Science"     ← course_path_nodes (node_type='chapter')
  "Motion & Forces"      ← course_path_nodes (node_type='chapter')
```

API: `GET /api/student/nodes?owner_type=platform`
→ returns the course_path_nodes tree under the selected subject/grade

---

### S-nav — Right panel (topic rows)

Each row in the right panel is a **`topics` row** attached to the selected chapter node.

```
"Large Numbers"      ← topics.name  (topics.status = 'live' only — draft topics hidden)
  "1 exam available" ← count of exam_templates WHERE course_path_node_id = chapter.id
  [Take exam]        ← shown only when that count > 0

"Estimation"
  "No exams yet"     ← zero exam_templates on that node
```

API: `GET /api/student/nodes/:node_id/topics`
→ returns topics WHERE course_path_node_id = :node_id AND status = 'live'

---

## The 9 Node Types (all live in the database)

The `nodetype` PostgreSQL enum has 9 values, added progressively across phases.

| Type | Lock | Allowed position | Notes |
|---|---|---|---|
| `grade` | 🔒 Reserved | Root only (depth 0) | Groups all content for a grade level |
| `subject` | 🔒 Reserved | Under `grade` only (depth 1) | Becomes the S-home dashboard tile |
| `course` | free | depth 2+ | Any non-ancestor type allowed |
| `chapter` | free | depth 2+ | Most common below subject |
| `module` | free | depth 2+ | |
| `section` | free | depth 2+ | |
| `unit` | free | depth 2+ | |
| `week` | free | depth 2+ | Useful for time-based curricula |
| `skill` | free | depth 2+ | |

**Reserved** means the backend returns a 409 if you try to place a `grade` anywhere other than the root, or a `subject` anywhere other than directly under a `grade`.

---

## The 3-Tier Hierarchy Rule

```
Category (board)
    └── grade node          ← tree root must be 'grade', nothing else allowed
          └── subject node  ← depth 1 must be 'subject', nothing else allowed
                └── any of: course / chapter / module / section / unit / week / skill
                      └── further nesting: same rule — no ancestor type may repeat
```

Two additional invariants enforced by the backend (both return 409 on violation):
1. **Ancestor-type exclusion** — a node's type must not appear anywhere in its ancestor chain.
2. **Sibling-type consistency** — all platform-owned siblings must share the same node type.

---

## Why `grade` and `subject` Drive the Student Experience

- `grade` nodes are the anchor for matching content to a student's grade level.
- `subject` nodes become the **S-home dashboard tiles** — one tile per subject.
- Everything below `subject` (`chapter`, `course`, etc.) becomes the **S-nav left sidebar**.
- `topics` hang off any non-reserved leaf node and appear in the **S-nav right panel**.

This means the student dashboard query is: *"give me all subject-level nodes visible to this student"* — no depth arithmetic needed, just `WHERE node_type = 'subject'` with the BR-DATA-003 visibility filter applied.

---

## What the Admin Already Built (Board Content)

| Done | Phase |
|---|---|
| `categories` (boards) creation and management | Phase 1b |
| `course_path_nodes` tree with grade/subject/chapter hierarchy + type enforcement | Phase 1b + 1c-post |
| `topics` with `status = 'live' / 'draft'`; live-only filter for students (BR-STU-003) | Phase 1c |
| `topic_contents` per topic (PDF, video, text) including extraction pipeline | Phase 1d |
| `owner_type` discrimination + BR-DATA-003 visibility filter in all read queries | Phase 1a |

**What is not yet built:** the student-facing API endpoints (`/api/student/dashboard`, `/api/student/nodes`, `/api/student/nodes/:id/topics`) and the exam session endpoints. The underlying data is fully in place — only the student API layer is missing.
