# Progress

> Auto-generated from PLAN.md. Updated by `/implement` in each code repo.
> Last baselined: backend:da38e8b frontend:fc78c5f deploy:ee39f9c (2026-07-09 — refreshed pre-Phase-5-start, non-Phase-5 hardening/infra only, no task status change)

## G1 [backend/frontend/specs]: Parent–child linking lifecycle
- [ ] T1.1 [backend]: Student link-code generation + current-code endpoints
- [ ] T1.2 [backend]: Student parent-link list + revoke endpoints
- [ ] T1.3 [backend]: Parent children list + parent-side revoke endpoints
- [ ] T1.4 [backend]: Max-10-children cap on redemption (BR-PAR-016)
- [ ] T1.5 [frontend]: /profile page (new) — link-code + linked-parents sections (depends on T1.1, T1.2)
- [ ] T1.6 [specs]: Link-code semantics + physical endpoint paths (depends on T1.1, T1.3)
- [ ] **G1: Parent–child linking lifecycle** — T1.7 [backend] integration test: full link round-trip (depends on T1.1, T1.2, T1.3, T1.4)

## G2 [frontend/specs]: Parent workspace shell + route guard
- [ ] T2.1 [frontend]: ParentRouteGuard component
- [ ] T2.2 [frontend]: /parent layout + P-home dashboard (depends on T2.1, T1.3)
- [ ] T2.3 [frontend]: /parent/link-child page (P-link) (depends on T2.1, T1.4)
- [ ] T2.4 [frontend]: Parent header nav + redirect-matrix verification (depends on T2.2)
- [ ] T2.5 [specs]: /parent route-guard slice into target 05_parent.md (depends on T2.1)
- [ ] T2.6 [frontend]: Onboarding parent-ready CTA dead-link fix (depends on T2.3)
- [ ] **G2: Parent workspace shell** — redirect-matrix component tests (in T2.4) + browser pass recorded in T7.2 walkthrough

## G3 [backend/frontend/specs]: Parent curriculum builder

### G3.1 Curriculum structure API
- [ ] T3.1 [backend]: V38 migration — source_node_id lineage column + partial unique index
- [ ] T3.2a [backend]: Parent node CRUD endpoints (owner-scoped) (depends on T3.1)
- [ ] T3.2b [backend]: Node hierarchy validation for parent trees (depends on T3.2a)
- [ ] T3.2c [backend]: Node cascade delete + exam-session guard (depends on T3.2b)
- [ ] T3.3 [backend]: Parent read access to platform tree (adopt browse)
- [ ] T3.4 [backend]: Adopt/clone service + endpoint (409 idempotent) (depends on T3.1, T3.2a, T3.3)
- [ ] T3.5 [backend]: Parent topic CRUD + draft/live publish (depends on T3.2a)
- [ ] **G3.1: Curriculum structure API** — T3.13 [backend] integration test: cross-owner 404 sweep (depends on T3.2c, T3.4, T3.5)

### G3.2 Content authoring API
- [ ] T3.6 [backend]: Parent instant content create + owner-scoped PATCH/DELETE (depends on T3.5)
- [ ] **G3.2: Content authoring API** — round-trip covered by T3.6 Done-when

### G3.3 Builder UI
- [ ] T3.7 [frontend]: features/parent curriculum API client + types (depends on T3.2a, T3.5, T3.6)
- [ ] T3.8 [frontend]: /parent/curriculum builder page (depends on T3.7, T2.1)
- [ ] T3.9 [frontend]: Adopt modal (depends on T3.7, T3.3, T3.4)
- [ ] T3.10 [frontend]: Parameterize shared content components (admin↔parent)
- [ ] T3.11 [frontend]: P-topic Topic Content Manager page (depends on T3.10, T3.7, T3.5, T3.6)
- [ ] T3.12 [specs]: 05_parent.md + 01_data_model.md builder/V38 updates (depends on T3.4, T3.6)
- [ ] **G3.3: Builder UI** — component tests per task + browser journey recorded in T7.2 walkthrough

## G4 [backend/frontend/specs]: RAG ingestion + re-ingestion lifecycle
- [ ] T4.1 [backend]: Outbox enqueue on instant text-content create (depends on T4.2, T3.6)
- [ ] T4.2 [backend]: Outbox upsert-with-reset repository helper
- [ ] T4.3 [backend]: Re-enqueue on content update (depends on T4.2, T3.6)
- [ ] T4.4 [backend]: Chunk + outbox cleanup on content delete (depends on T3.6)
- [ ] T4.5 [backend]: Worker delete-stale-chunks-before-insert (depends on T4.2)
- [ ] T4.6 [backend]: Cascade RAG cleanup on topic/node delete (depends on T4.4, T3.2c, T3.5)
- [ ] T4.7a [frontend]: "No notes yet" hint in parent builder (depends on T3.11)
- [ ] T4.7b [frontend]: "No notes yet" placeholder in student content viewer
- [ ] T4.8 [specs]: Re-ingestion contract into 12_content_extraction.md §5 + 01_data_model.md (depends on T4.5)
- [ ] **G4: RAG ingestion lifecycle** — T4.9 [backend] integration test: content→chunk lifecycle (ollama-gated + non-gated companion) (depends on T4.1, T4.3, T4.4, T4.5)

## G5 [backend/frontend/specs]: hAITU answers on parent-owned topics
- [ ] T5.1 [backend]: Optional enrollment_id in topic-doubt schema
- [ ] T5.2 [backend]: Parent-link authorization gate in HaituDoubtService (depends on T5.1)
- [ ] T5.4 [frontend]: HaituDoubtPanel enabled for Home Study topics (depends on T5.1, T5.2)
- [ ] T5.5 [specs]: 11_haitu_ai_layer.md §9 — parent-topic access contract (depends on T5.2)
- [ ] **G5: hAITU on parent topics** — T5.3 [backend] severance + cross-family 403 tests (depends on T5.2)

## G6 [backend/frontend]: Student Home Study surface complete
- [ ] T6.2 [frontend]: Source-aware empty state in existing Home Study tree
- [ ] T6.3 [frontend]: Home Study content viewing verification (depends on T6.2, T3.5, T4.7b)
- [ ] **G6: Student Home Study surface** — T6.1 [backend] live-only + visibility enforcement tests (fixture-driven, no deps)

## G7 [backend/frontend]: Phase acceptance
- [ ] T7.1 [backend]: E2E journey test — contract-level (CI-safe) + ollama-gated grounded variant (depends on T1.7, T3.13, T4.9, T5.3, T6.1)
- [ ] **G7: Phase acceptance** — T7.2 [frontend] suites green + manual walkthrough record (depends on T7.1 + all frontend leaf tasks of G1–G6)

## Ready now
Tasks with no pending dependencies — can be started immediately:
- T1.1 [backend]: Student link-code generation + current-code endpoints (no deps)
- T1.2 [backend]: Student parent-link list + revoke endpoints (no deps)
- T1.3 [backend]: Parent children list + parent-side revoke endpoints (no deps)
- T1.4 [backend]: Max-10-children cap on redemption (no deps)
- T3.1 [backend]: V38 migration — source_node_id lineage (no deps)
- T3.3 [backend]: Parent read access to platform tree (no deps)
- T4.2 [backend]: Outbox upsert-with-reset repository helper (no deps)
- T5.1 [backend]: Optional enrollment_id in topic-doubt schema (no deps)
- T6.1 [backend]: Live-only + visibility enforcement tests (fixture-driven, no deps)
- T2.1 [frontend]: ParentRouteGuard component (no deps)
- T3.10 [frontend]: Parameterize shared content components (no deps)
- T4.7b [frontend]: "No notes yet" placeholder in student content viewer (no deps)
- T6.2 [frontend]: Source-aware empty state in Home Study tree (no deps)
