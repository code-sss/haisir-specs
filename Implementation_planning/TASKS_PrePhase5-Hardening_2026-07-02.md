# TASKS — Pre-Phase 5: Phase 4 Release-Hardening Pass

> Auto-generated from `PLAN_PrePhase5-Hardening_2026-07-02.md`. Updated by `/implement` in each
> code repo. Baseline: backend `0cb36bd`, frontend `df7067e`, deploy `98912f8` (Phase 4 sign-off).
> Pre-Phase-5 must close before Phase 5 (`TASKS.md`) starts.
>
> `[specs]` tasks are specs-repo edits — **already written** as part of the plan (✅). `[backend]` /
> `[frontend]` / `[deploy]` tasks are implementation tickets for the sibling repos.

> Last baselined: backend:3ad6789 frontend:df7067e deploy:98912f8 (2026-07-05)

## G1 [frontend]: Exam review navigation wired (issues 1, 8)
- [x] T1.1 [frontend]: Post-submit "Review answers" CTA → /exam/{id}/review (2026-07-04)
- [x] T1.2 [frontend]: AttemptsModal per-attempt "View" → /exam/{id}/review (depends on T1.1) (2026-07-04)
- [x] T1.3 [frontend]: "📊 Results" button → attempts list; each row routes to review (depends on T1.2) (2026-07-04)
- [x] T1.4 [frontend]: Review page must not mislabel pending-grading questions as "Skipped" (gap found in plan review; must land with T1.1–T1.3) (2026-07-04)
- [x] **G1: Exam review navigation wired** — /exam/[session_id]/review reachable from post-submit, attempts modal, and results button, without mislabeling ungraded essays (2026-07-04)

## G2 [frontend/deploy]: Exam builder bulk-topic + sample JSON (issues 2, 4)
- [x] T2.1 [frontend]: "Apply topic to all questions" control in ExamBuilder (2026-07-05)
- [x] T2.2 [deploy]: Add topic_id to qa-sample.json question objects (2026-07-04)
- [x] T2.3 [frontend]: JSON import/export round-trip test for topic_id (depends on T2.2) (2026-07-05)
- [x] **G2: Exam builder bulk-topic + sample JSON** — bulk topic apply ships; qa-sample.json exercises topic_id (2026-07-05)

## G3 [backend/frontend]: Topic-filtered exam taking (issue 5)
- [x] T3.1 [backend]: Optional topic_id filter on GET /api/exams/course/{node_id} (+ /template) (2026-07-05)
- [x] T3.2 [frontend]: TopicListPanel "Take Exam" passes topic_id; /exam consumes it (depends on T3.1) (2026-07-05)
- [x] T3.3 [backend]: Integration test — topic_id filter returns only matching templates (depends on T3.1) (2026-07-05)
- [x] **G3: Topic-filtered exam taking** — Take Exam on a topic lists only that topic's exams (2026-07-05)

## G4 [frontend]: Deep-link + tree interaction fixes (issues 6, 7)
- [x] T4.1 [frontend]: /courses consumes ?topic= searchParam → expand ancestors + select topic (2026-07-05)
- [x] T4.2 [frontend]: NodeTreeSidebar: separate chevron toggle from label select+expand (2026-07-05)
- [x] **G4: Deep-link + tree interaction fixes** — Focus Areas chip deep-links correctly; non-leaf label selects+expands without collapse (2026-07-05)

## G5 [frontend]: Catalog grade label (issue 10)
- [ ] T5.1 [frontend]: CatalogCard renders "Grade {name}" when node_type === "grade"
- [ ] **G5: Catalog grade label** — enrollment root grade nodes display "Grade N"

## G6 [frontend/backend/specs]: Student grade/profile + onboarding completeness (issues 13, 14)
- [ ] T6.1 [frontend]: Grade picker in student onboarding View B → POST /api/students/me/profile
- [x] T6.2 [backend]: Verify profile upsert accepts grade-only patch (verification + test) (2026-07-05)
- [x] T6.3 [specs]: 09_onboarding.md — student View B collects grade (amends BR-ON-008) ✅ written
- [ ] **G6: Student grade/profile + onboarding completeness** — recommended badge activatable from UI; onboarding grade step specced

## G7 [frontend/specs]: Inbox UX targeted polish (issue 12)
- [ ] T7.1 [frontend]: NotificationBell dropdown (recent unread + mark-read + "View all")
- [ ] T7.2 [frontend]: Doubt inboxes: status filter + last-message preview excerpt
- [ ] T7.3 [frontend]: NotificationsPage: unread-only toggle + type/source icon
- [x] T7.4 [specs]: 10_notifications.md + 03_student.md/04_teacher_tutor.md — inbox UX contract ✅ written
- [ ] **G7: Inbox UX targeted polish** — bell dropdown, status filters, previews shipped + specced

## G8 [backend/specs]: At-risk notification interim fix + deferred-items spec documentation (issues 3, 9, 11)
- [ ] T8.1 [backend]: student_at_risk action_url → null (no broken nav) until view exists
- [x] T8.2 [specs]: 04_teacher_tutor.md + backlog: teacher at-risk detail view (Phase 6) ✅ written
- [x] T8.3 [specs]: 03_student.md mastery note — NULL topic_id questions contribute no mastery + 07 cross-ref ✅ written
- [x] T8.4 [specs]: 12_content_extraction.md + backlog: LaTeX/math rendering requirement (content-rendering follow-up) ✅ written
- [ ] **G8: At-risk notification interim fix + deferred-items spec documentation** — no broken nav; 3 deferred items spec'd + backloged

## Ready now (no pending deps)
T5.1, T6.1, T7.1, T7.2, T7.3, T8.1

## Already written (specs repo, part of this plan)
T6.3, T7.4, T8.2, T8.3, T8.4 — spec content committed to target/requirements/* and vision/requirements/backlog.md