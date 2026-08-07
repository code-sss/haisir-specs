# Phase 7 — Review Finding Resolutions (T8.1.3)

**Date:** 2026-08-06
**Inputs:** `PHASE7_SECURITY_REVIEW_PASS1.md` (9 findings) and
`PHASE7_SECURITY_REVIEW_PASS2.md` (5 findings). Deduplicated to **11 distinct items** — three were
found independently by both passes.

Every item below is either **FIXED**, **CLOSED** (removed as a side effect of another fix), or
**ACCEPTED** with the reasoning recorded. Nothing is left undecided, which is G8.1's bar.

All changes are left **uncommitted** in the three code repos, per this repo's established norm for
WAF/gateway edits.

## Resolution table

| # | Finding | Sev | Disposition | Where |
|---|---|---|---|---|
| 1 | P2-1 — image proxy hairpins into itself (A) and never forwards auth (B) | CRITICAL | **FIXED** | new `common/routes/26-images-questions.json`; deleted `src/app/images/questions/[...path]/route.ts` + its test |
| 2 | P2-2 — `waf-harness.sh` wired into no CI pipeline | HIGH | **FIXED** | new `WAF Functional Gate` stage in `gateway-docker/Jenkinsfile` |
| 3 | F1 — CVE-2026-21876 regression test cannot fail for the right reason | HIGH | **FIXED** (revised 2026-08-07 — see note) | `18-test-cve-2026-21876-multipart.sh` + `waf-harness.sh` |
| 4 | F3 — traversal guard caught only an exactly-`..` segment | MEDIUM | **CLOSED** by #1 | file deleted |
| 5 | F4 / P2-3 — image upload buffers whole body before its size check | MEDIUM | **FIXED** | `src/api/routes/exam.py` |
| 6 | F5 / P2-5 — base and utility images pulled by mutable tag | MEDIUM | **FIXED** | `gateway-docker/Dockerfile`, `common/scripts/deploy.sh`, `common/scripts/env-setup.sh` |
| 7 | F6 — WebP accepted on upload, rejected by the frontend proxy | LOW | **CLOSED** by #1 | frontend MIME gate deleted |
| 8 | F7 — extraction routes' 50 MB cap unreachable | LOW | **FIXED** | `admin_extraction.py`, `parent_extraction.py` |
| 9 | F8 — `worker_processes` comment contradicts the config | LOW | **FIXED** | `common/docker-compose.yml` |
| 10 | F9 — CSRF required on a GET | LOW | **ACCEPTED** | documented in `src/api/routes/haitu.py` |
| 11 | P2-4 — 942200 exclusion is config-wide, not route-scoped | LOW | **ACCEPTED** | comment corrected in all four `common/plugin_configs/*.json` |

Two further pass-1 findings (`VENDORED.md` self-contradiction; missing version-floor assertions)
were already fixed under T8.1.2 — see that section of `PHASE7_SECURITY_REVIEW_PASS2.md`.

---

## What was done

### 1. Image serving (CRITICAL)

Both defects had the same root cause: `/images/questions/*` had no APISIX route, so it fell through
`99-catch-all.json` to the frontend, and a Next.js handler tried to do the gateway's job. The fix is
to stop doing that — serve the path the way every other authenticated backend read is served.

- **Added `common/routes/26-images-questions.json`** — GET/OPTIONS, priority 20 (beats the catch-all
  at 0), `plugin_config_id: secured-api`, upstream `backend:8000`. Mirrors `04-api-read.json`.
  `secured-api` carries `openid-connect`, so the **gateway injects the JWT** — satisfying the
  backend's `current_active_user` dependency without any client ever sending a bearer token, per
  CLAUDE.md's hard rule. Defect B disappears rather than being patched.
- **Deleted `src/app/images/questions/[...path]/route.ts` and its test.** No code imported it; the
  other references to `/images/questions/...` are to the URL *string* stored in `image_url` and
  rendered in `<img src>`, which stays valid — the same URL is now served by APISIX instead.

Checked before writing the route: image responses are **not** body-inspected by Coraza
(`coraza.conf-recommended.conf:91` sets `SecResponseBodyMimeType text/plain text/html text/xml`), so
routing binary through `secured-api` raises no outbound-anomaly risk.

This deletion also closed F3 and F6 — the weak traversal guard and the PNG/JPEG-only MIME gate both
lived in the deleted file. The backend's `_SAFE_FILENAME_RE` allowlist is now the single, correct
guard, and it already permits the same three formats the upload endpoint accepts.

### 2. WAF functional gate in CI (HIGH)

New `WAF Functional Gate` stage in `gateway-docker/Jenkinsfile`, placed after `Verify Image` and
**before `Push to Registry`**, so an image whose WAF does not filter cannot reach the registry. The
stage comment records why `Verify Image` was insufficient — it checks an OCI label with an `echo`
fallback (so it cannot fail) and runs `apisix version`, neither of which touches Coraza — and notes
that this gate proves the WAF *runs*, not which version it runs; the version floors are asserted at
build time in the Dockerfile.

### 3. CVE-2026-21876 regression test (HIGH)

Four changes to `18-test-cve-2026-21876-multipart.sh`:

- **A real browser `User-Agent` is now sent.** `03-secured-api.json`'s `ua-restriction` denylists
  `curl*` with `rejected_code: 403` and `bypass_missing: false`, so with curl's default UA the
  script returned 403 from UA blocking and passed against any CRS version.
- **A control probe runs first** — the same multipart shape with both parts clean UTF-8. It must
  return 401 (reached auth). If it returns 403, something on the route blocks every multipart POST
  regardless of content, the attack probe's 403 would prove nothing, and the script now **exits
  non-zero as INCONCLUSIVE** rather than reporting a pass.
- **429 is no longer a pass** on either probe — a rate-limited request never reached rule 922110.
- **The comment naming the wrong plugin_config was corrected.** It claimed
  `04-secured-api-upload.json`; the probe URI is POST `/api/*`, which matches `05-api-write.json`
  (priority 10) → `secured-api`. Verified by enumerating every POST-capable `/api/*` route.

`bash -n` and `shellcheck -S warning` both clean.

> **Revised 2026-08-07, after running it live.** The fix above was necessary but not sufficient, and
> one part of it was wrong.
>
> **The test could never reach rule 922110 at all.** Its premise — restated in my own correction —
> was that `coraza-filter`'s priority 7999 puts it ahead of `openid-connect`'s 2599, so no token is
> needed. That is false: `openid-connect` implements `_M.rewrite` (REWRITE phase) and `coraza-filter`
> is registered `http_request_phase: "access"`. Rewrite runs first, and priority orders plugins only
> *within* a phase. An unauthenticated `/api/*` request is 401'd before the WAF runs. Confirmed live:
> identical SQLi → 403 on `/` with 8 rule matches, 401 on `/api/*` with **zero** Coraza log lines ever
> recorded for an `/api/` URI. Now **BR-WAF-013**.
>
> **And my "correction" about which plugin_config was itself wrong.** I claimed the probe hits
> `05-api-write.json` → `secured-api`. It does not: `16-api-extraction-upload.json` declares `uris`
> (**plural**), which my route enumeration — keyed on `uri` — silently skipped, and it matches at
> priority 20 with `secured-api-upload`. The file's original comment was right; I "fixed" a correct
> statement into an incorrect one on the strength of an enumeration that had a blind spot.
>
> **Resolution.** The rule-level regression moved to `common/scripts/tests/waf-harness.sh`, which
> loads only `coraza-filter` and therefore has no OIDC to intercept and no `ua-restriction` to fake a
> 403 — three probes there (multipart control → 200, CVE payload → 403, and an assertion that
> `id "922110"` fired, since the UTF-7 payload decodes to `<script>alert(1)</script>` and an XSS rule
> could otherwise mask a broken 922110). Verified 7/7 against the deployed image. The standalone test
> now demands a token and exits INCONCLUSIVE without one. **This is the third time in this phase that
> a check looked green while proving nothing — and the second time my own fix for it was incomplete.**

### 5. Upload buffering (MEDIUM)

`exam.py` now uses `read_upload_capped(file, _MAX_IMAGE_UPLOAD_BYTES)` — the streaming helper this
same phase added and wired into both extraction routes. The old `await file.read()` + length check
meant the real ceiling was `SECURITY__MAX_REQUEST_SIZE` (50 MB in staging/prod) against a 1 g
backend `mem_limit`, not the 5 MB the endpoint advertises. 200 backend tests pass.

### 6. Image pinning (MEDIUM)

All digests resolved 2026-08-06 via `docker manifest inspect -v` (multi-arch manifest list digests):

- `gateway-docker/Dockerfile` — both `FROM`s pinned via new `APISIX_DIGEST` / `GO_BUILDER_DIGEST`
  build args, with the `*_VERSION` args retained as the human-readable record of what each digest
  is. `docker build --check` passes and both digests resolve against their registries.
- `common/scripts/deploy.sh` — the four `docker run` invocations that build the platform's CA trust
  bundle (`alpine/openssl`, `alpine`, `busybox` ×2) pinned inline.
- `common/scripts/env-setup.sh` — nine `alpine` invocations replaced with a single pinned
  `ALPINE_IMAGE` variable. Not named in either finding, but the same class, and one of them is this
  phase's own CA-cert upload; fixed at the class rather than the instance.

Pinning freezes patch updates by design — the comments say so and tell the reader to bump the tag
and digest together in one commit.

**Residual, explicitly accepted:** pinning establishes *immutability*, not *trust*. Pass 2's point
that `reg.mini.dev` is a new and less-recognisable supply-chain dependency stands, and confirming its
provenance is an owner decision outside a code review.

### 8–9. Config truthfulness (LOW)

- `_MAX_UPLOAD_BYTES` in both extraction routes is now
  `min(50_000_000, settings.security.max_request_size)` — derived, so it can never again claim a
  limit the stack does not honour.
- The `mem_limit: "3g"` comment in `common/docker-compose.yml` said `worker_processes` was "pinned
  to 2" and offered "drop it to 1 before raising this" as the next lever. `config.yaml:159` already
  sets 1, so that lever was spent; anyone following the old text on a fresh OOM would have raised
  the cap on a host with ~4 g free. Corrected, and the note now says there is no cheaper knob left.

## Accepted, with reasoning

**F9 — CSRF on `GET /api/haitu/exam-review-chat/{attempt_id}`.** Kept. It is strictly *stricter*
than the project rule, not weaker; every caller already goes through `fetchWithCSRFRetry`, so
removing it would buy nothing and re-open a header the endpoint currently demands. Documented in the
route's docstring because it will otherwise surprise anyone adding a plain `fetch` and seeing a 403.

**P2-4 — the 942200 `Referer` exclusion is plugin-config-wide.** Kept. APISIX offers no finer
scoping without duplicating the whole `coraza-filter` block per route — which is the
exclusion-treadmill pattern this phase exists to end. The comment that claimed it left 942200 "fully
active on every other field, header, **and route**" was wrong and has been corrected in all four
configs to state the real blast radius. Residual risk is bounded: 942200 is a naive
comment/space-obfuscation regex, and every sensitive route still carries the full remaining CRS set
plus OIDC and CSRF.

**Verified comment-only:** the four `plugin_configs/*.json` edits were checked by parsing old and new
and comparing the effective directive lists with comment lines stripped, plus every non-Coraza
plugin block. All four report unchanged on both. No WAF behaviour was altered.

## Verification performed

| Check | Result |
|---|---|
| `jq` / `json.load` on all touched JSON | valid |
| Effective WAF directives before vs after | **unchanged** in all four plugin_configs |
| `bash -n` + `shellcheck -S warning` on all touched scripts | clean |
| `docker build --check` on the pinned Dockerfile | "Check complete, no warnings found"; both digests resolve |
| `python yaml.safe_load` on `common/docker-compose.yml` | valid |
| `ruff check` on all touched backend files | all checks passed |
| Backend `pytest` (exam, uploads, haitu, images, both extraction routes) | **364 passed** |
| Frontend `tsc --noEmit` (**devcontainer**) | **clean, exit 0** after `pnpm build` regenerated `.next/types` |
| Frontend `vitest` full suite (**devcontainer**) | **222 files, 3932 tests, all passing, 100% coverage** on statements/branches/functions/lines |
| Statically-prerendered routes after the deletion | **0** — BR-CSP-010 / T5.2.7's guard still holds |

> **Correction (same day).** An earlier draft of this table reported 12 `tsc` errors and 44
> `vitest` failures as "pre-existing, worth their own ticket". That was measured on the **host
> clone**, whose `node_modules` and `.next` are stale. Re-run inside the `frontend` devcontainer —
> the real dev environment — all of it is green. There is no ticket to file. The host numbers were
> an artifact of where they were measured, not a property of the code.
>
> The devcontainer also surfaced one genuine consequence the host could not: `.next/types/validator.ts`
> still referenced the deleted route, failing `pnpm typecheck` until `pnpm build` regenerated it. The
> host missed this because its `.next` predated the route's existence. Resolved by rebuilding.

## Owed before G8.1 can close

These are not findings; they are verification this session could not perform.

1. **A live round-trip for the new image route.** Everything here is static reasoning plus unit
   tests. G3.5 originally closed on exactly that basis and shipped a broken feature, so the
   correction should not close the same way. Load an exam question image end-to-end against the dev
   or staging stack after reloading routes.
2. **One behaviour to watch in that test:** `secured-api`'s `openid-connect` may issue a 302 to
   Keycloak on an expired session. For an `<img>` request that renders as a broken image rather than
   a clean 401. Acceptable if confirmed, but confirm it rather than assume.
3. **The `WAF Functional Gate` stage has never run.** `waf-harness.sh` needs Docker on the Jenkins
   agent and binds ports 19080/19180; verify on a real build, not just by reading the stage.
4. **All code changes are applied in both the host clones and the devcontainers.** The frontend and
   backend devcontainers mount named volumes, not bind-mounts, so they are separate checkouts and
   host edits do not propagate — the same trap noted under T5.3.5. Backend: 4 files copied in, diff
   verified byte-identical to the host, 370 tests pass. Frontend: both deletions applied, rebuilt,
   full suite green.
5. **The `frontend` devcontainer is one commit AHEAD of the host** — `92a4da2`
   ("test(csp): add production CSP enforcement e2e soak") sits on top of `d6adec7`, and is the
   committed form of the `playwright.prod-csp.config.ts` / `tests/e2e/prod-csp/` files that exist
   only as untracked files on the host. **Neither review pass covered `92a4da2`** — both ran against
   the host range ending at `d6adec7`. It is test-only CSP soak work, so the exposure is small, but
   it is un-reviewed Phase 7 code and someone should decide whether that matters before G8 closes.
