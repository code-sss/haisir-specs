# Teacher & Tutor Personas

> Status: stub — to be defined based on current state.
> See `vision/requirements/04_teacher_tutor.md` for the long-term vision spec.

---

## Essay Grading (deferred — role migration prerequisite)

Instructor and tutor roles are configured in the backend (`UserRole` enum + `permission.py`) but
are **not yet active in the Keycloak realm**. Before adding any instructor/tutor grading
permissions, the role migration steps in `vision/requirements/11_role_migration.md` must be
completed.

In the current increment, essay grading override is a parent responsibility (for parent-owned
exams) and a Platform Admin responsibility (for platform exams). Instructor/tutor essay grading
is explicitly deferred.

When instructor scope is added:
- Instructors will be able to override AI essay grades for exams in their assigned classes.
- Tutors will be able to override AI essay grades for exams they administer.
- The `PATCH .../grade` and `POST .../confirm-grade` permission matrix (in
  `02_auth_and_roles.md`) will be extended with `instructor` and `tutor` roles at that time.
