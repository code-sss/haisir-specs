# PLAN — Phase 1d: Topic Content Upload

> Written: (pending — run `/plan` to generate)
> Phase baseline:
> <!-- plan-baseline: backend:819893c990e3db8922dbd239a6c9f4d6e4b90ad0 frontend:dec3ab89429d948c1d01f76b433b37e0b9aebf55 deploy:b814471ac9a44b3566abe8a47a46957e2f195ec9 -->

## Status

**Not yet planned.** Run `/plan` to generate the full task breakdown.

## Known scope (from `phases.md`)

> Phase 1d — Topic content upload: PDF/video/text content management per topic; `PATCH`/`DELETE` topic_contents. Depends on 1c-post ✓.

## Backlog items to consider for this or a future phase

| Item | Priority | Notes |
|---|---|---|
| Issue 2 — Move "Categories" from avatar/profile menu to sidenav | Medium | New scope. Requires `AdminSidenav` update + removing the entry from the profile/avatar dropdown. No backend changes needed. |
| Issue 3 — Version display on nodes ("NCERT v2.4") | Low | Deferred to Phase 2+. Requires new `version` column on `categories` table + Alembic migration + publish modal. |
| Issue 6 (partial) — Version badge on board cards | Low | Deferred to Phase 2+. Same `version` column dependency as Issue 3. |
