# hAIsir Specs — Open Issues

## Missing Specifications

| # | Gap | Impact |
|---|-----|--------|
| 1 | **Dynamic exam question selection algorithm** | Backend has `mode=dynamic` + `ruleset` JSON but spec never defines the selection logic (random? weighted by difficulty? coverage-based?) |
| 2 | **File storage strategy** | Topic content supports PDF upload, question images exist. No spec for where files are stored (S3? local disk? CDN?). Backend has `data_dir` config but no S3/cloud integration. |
| 3 | **Search implementation** | Student browse (S03), tutor discovery (S06) mention search. No spec for search backend (PostgreSQL full-text? Elasticsearch? Client-side filter?). |
| 4 | **Pagination strategy** | List endpoints (topics, questions, notifications, doubts) have no pagination spec. Current backend returns all results. |
| 5 | **Concurrency handling** | No spec for concurrent exam submissions, double-enrollment prevention (beyond 409), or optimistic locking on shared resources. |
| 6 | **Error response contract** | No standard error response schema defined across endpoints. |
| 7 | **Rate limiting per role** | APISIX has global rate limits (100/min read, 50/min write) but spec doesn't differentiate by role (admin bulk operations vs student browsing). |
| 8 | **Data export/backup** | No spec for institution data export, GDPR compliance, or data deletion workflows. |
| 9 | **Offline/connectivity handling** | No spec for what happens when hAITU is down, Keycloak is unreachable, or network drops mid-exam. |
| 10 | **Multi-role context during exam** | What happens to an in-progress exam session if the user switches roles mid-exam? |

## Consistency Issues

| # | Issue | Files |
|---|-------|-------|
| 1 | **BR numbering not unique** — Some business rules use overlapping prefixes (BR-STU, BR-TCH) but no central index. Hard to cross-reference. | All requirement files |
| 2 | **API endpoint naming** — Specs mention `/api/students`, `/api/teachers`, etc. but existing backend uses `/api/users`, `/api/courses`. Migration path unclear. | `00_overview.md` vs backend `api/router.py` |
| 3 | **`status` field overloading** — Different entities use `status` with different enum values (enrollment, topic, doubt, exam_session, organization). Spec doesn't propose a naming convention to avoid confusion. | `01_data_model.md` |
| 4 | **Colour inconsistency** — Tutor is purple `#3C1F6E` in overview but `#534AB7` appears in student UI for hAITU panel. Are these the same colour intent? | `00_overview.md` vs `ui_student.md` |

## Decisions Pending

| # | Decision | Options |
|---|----------|---------|
| 1 | Pagination strategy | Cursor-based vs offset-based? Max page size? |
| 2 | File storage | S3/cloud vs local disk for PDFs/images? |
| 3 | Search backend | PostgreSQL full-text vs dedicated search service? |
| 4 | Dynamic exam algorithm | Random, weighted, or coverage-based question selection? |
| 5 | Error response contract | Standard error schema across endpoints? |
