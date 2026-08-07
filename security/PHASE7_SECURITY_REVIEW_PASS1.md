# Phase 7 — Adversarial Security Review, Pass 1 (T8.1.1)

**Date:** 2026-08-06
**Scope:** the full Phase 7 diff across all three code repos, against the plan-baseline SHAs
recorded in `Implementation_planning/PLAN.md`:

| Repo | Range | Human-written surface |
|---|---|---|
| `haisir-deploy` | `8cb1dbe..5aa8524` | 58 files, ~2 700 lines (excluding the vendored `gateway-docker/coraza-proxy-wasm/` tree) |
| `haisir-frontend` | `3a57718..d6adec7` | 73 files, 3 199 insertions |
| `haisir-backend` | `583511d..9d9ea6b` | 58 files, 4 075 insertions |

All three working trees are clean; the 8 files T7.4.2 left uncommitted in `haisir-deploy` have
since landed as `5aa8524`. Method follows the Phase 5.5/5.6 precedent
(`common/openbao/security-review-pass1.md`): identify candidates against the real repo files and
this project's threat model, then fact-check each one against the code rather than the task log.

**Pass 2 (T8.1.2) must be run independently of this document.** In Phase 5.6 the second pass found
a live-credential bug that pass 1 had rated clean.

---

## Findings

### F1 — HIGH · false assurance · the CVE-2026-21876 regression test cannot fail for the right reason

`common/scripts/tests/18-test-cve-2026-21876-multipart.sh`

The probe is sent with bare `curl` and no `-A` override. The route it targets is covered by
`common/plugin_configs/04-secured-api-upload.json`, whose `ua-restriction` denylist contains
`curl*`. The script asserts on the status code alone:

```bash
if [ "$code" = "403" ]; then
    pass "MULTIPART-CHARSET-1 ... blocked (HTTP 403)"
```

A 403 from `ua-restriction` is indistinguishable from a 403 from rule 922110, so **this script
would pass identically against a vulnerable CRS 4.14.0 build**. The ordering of the two plugins
does not matter — whichever fires first returns 403. `config.sh`'s own `get_access_token` /
`get_refresh_token` set an explicit `User-Agent: Mozilla/5.0 …` for exactly this reason; the new
script does not.

Compounding it, one branch below:

```bash
elif [ "$code" = "429" ]; then
    pass "MULTIPART-CHARSET-1 rate-limited (HTTP 429)"
```

A rate-limit means the rule was never evaluated. Treating it as a pass is plausible in a suite of
18 sequential scripts against `limit-req rate 10 burst 20`. (The same `429 → pass` pattern exists
in `config.sh`'s shared `test_attack` / `test_allow`, and `skip()` also increments `PASSED` — all
pre-existing, but this script is new in Phase 7 and guards the phase's headline CVSS 9.3 item.)

**Fix:** send a browser `User-Agent`; assert on the Coraza log entry for `id:922110` rather than
the status code alone; make 429 a retry, not a pass.

**Not a finding — the CVE fix itself is real.** Verified at source, not from the task log:
`gateway-docker/coraza-proxy-wasm/wasmplugin/rules/crs-setup.conf.example` carries
`setvar:tx.crs_setup_version=4251` (CRS 4.25.1 LTS), `go.mod` pins
`github.com/corazawaf/coraza/v3 v3.7.0`, and `REQUEST-922-MULTIPART-ATTACK.conf` contains rule
922110 with the fixed charset-allowlist regex. Only the *test* is worthless, not the remediation.

---

### F2 — HIGH · availability · the exam-question image proxy targets the public gateway, not the backend

`haisir-frontend/src/app/images/questions/[...path]/route.ts:12`

```ts
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:9080";
...
const upstreamUrl = `${BACKEND_URL}/images/questions/${path.join("/")}`;
```

`NEXT_PUBLIC_BACKEND_URL` is the **public APISIX ingress**, not an internal service address —
`haisir-frontend/Dockerfile:9` bakes `https://haisir.in`, `Jenkinsfile:5` defaults staging to
`https://staging.haisir.in`, and every other consumer in the codebase treats it that way
(`${BACKEND_URL}/auth/login`, `${BACKEND_URL}/api/auth/csrf`). Port `9080` in the fallback is
APISIX's, not `backend:8000`.

So this **server-side** handler makes an outbound request back to the public front door.
`common/routes/` has no `/images/*` route, so it falls through `99-catch-all.json` (`uri: /*`,
`methods: [GET, OPTIONS]`) to `frontend:3000` — into the same handler again. Two outcomes:

1. Node's `fetch` (undici) sends no `User-Agent`. `secured-anonymous`'s `ua-restriction` has
   `bypass_missing: false`, so the missing header is evaluated and the request is rejected 403 on
   the first hop. `!upstreamRes.ok` → the browser gets a 403 and **no exam question image ever
   renders**.
2. If a `User-Agent` is ever added, the handler recurses through the public ingress into itself,
   bounded only by `limit-count` (100/min/IP) and the 6 s read timeout.

Why this survived the phase: G3.5 was closed on "code-level proof… no separate live HTTP round-trip
was made this session"; the unit tests (`tests/unit/app/images-questions-route.test.ts`) mock
`globalThis.fetch` entirely; and T2.3.2's dev-stack sweep on 2026-08-01 *did* observe the symptom —
"a frontend image-serving proxy 502 (`BACKEND_URL` misconfig in the frontend devcontainer)" — and
recorded it as an out-of-scope environment quirk rather than root-causing it.

**Fix:** introduce a server-only internal base URL (no `NEXT_PUBLIC_` prefix, so it is read at
runtime rather than inlined at build) pointing at `http://backend:8000`, and use it here.

---

### F3 — MEDIUM · path traversal · incomplete guard in the same route

`haisir-frontend/src/app/images/questions/[...path]/route.ts:26`

```ts
if (path.includes("..")) {
  return new Response(null, { status: 400 });
}
```

`Array.prototype.includes` matches only a segment **exactly equal** to `..`. A single decoded
segment containing `../../etc` passes the guard; `path.join("/")` then produces a relative path
that WHATWG URL parsing inside `fetch()` normalizes away, redirecting the upstream request — which
carries the caller's `cookie` header — to an arbitrary path on the target host.

Bounded by the `image/png | image/jpeg` content-type gate on the response, by the backend's own
`_SAFE_FILENAME_RE` allowlist, and currently unreachable because of F2. It becomes live the moment
F2 is fixed and the request actually reaches `backend:8000`. The unit test at
`tests/unit/app/images-questions-route.test.ts:113` covers only the exact-`..`-segment case.

**Fix:** `path.some((p) => p.includes(".."))`, or better, validate each segment against the same
allowlist the backend enforces (`/^[a-zA-Z0-9_-]{1,70}\.(png|jpg|webp)$/`).

---

### F4 — MEDIUM · resource exhaustion · the new upload endpoint ignores this phase's own capped-read helper

`haisir-backend/src/api/routes/exam.py:264`

```python
file_bytes = await file.read()
if len(file_bytes) > _MAX_IMAGE_UPLOAD_BYTES:   # 5 MB
    raise HTTPException(413, ...)
```

The entire body is materialised in memory *before* the 5 MB check. The effective ceiling is
`RequestBodySizeLimitMiddleware`'s `settings.security.max_request_size`, which this phase raised to
**50 MB** in `common/docker-compose.yml` (`SECURITY__MAX_REQUEST_SIZE: ${...:-52428800}`), against a
backend `mem_limit: "1g"`.

The sharp edge is that Phase 7 added `read_upload_capped()` (`src/shared/uploads.py`) for precisely
this shape and wired it into `admin_extraction.py:176` and `parent_extraction.py:183` — the new
endpoint is the single place it was not applied, while the middleware that used to do a
`Content-Length` pre-check for it was simultaneously reworked. Requires an authenticated instructor
and `limit-conn` caps per-IP concurrency at 10, so this is authenticated abuse rather than anonymous
DoS.

**Fix:** `file_bytes = await read_upload_capped(file, _MAX_IMAGE_UPLOAD_BYTES)`.

Related, same endpoint: writes land in `{data_dir}/images/questions/` with no quota. At the route's
`limit-count` of 100/min an instructor can add ~500 MB/min to the `haisir-backend-datadir` volume.
Worth a bound or a monitoring alert, not necessarily code.

---

### F5 — MEDIUM · supply chain · the WAF binary is compiled in an unpinned third-party image

`gateway-docker/Dockerfile:42`

```dockerfile
FROM reg.mini.dev/go:${GO_VERSION}-dev AS builder
```

The builder moved off Docker Official `golang:1.23-bookworm` onto a third-party registry, pulled by
**mutable tag**, with no digest pin and no signature verification. TinyGo inside it *is*
SHA256-pinned (`TINYGO_SHA256`); the image that runs it is not. The artifact produced is
`main.wasm` — the WAF that inspects every request to the platform. The runtime stage
(`apache/apisix:${APISIX_VERSION}`, line 104) is likewise tag-pinned only.

Same class in `common/scripts/deploy.sh:646-695`, which pulls `alpine/openssl`, `alpine` and
`busybox` by bare tag and runs them `--user root` with the certs volume mounted, to *build the
platform's CA trust bundle* (`cat /etc/ssl/certs/ca-certificates.crt /certs/ca.pem >
/certs/ca-bundle.pem`). A compromised `alpine` tag yields an attacker-chosen trust anchor for both
APISIX and the backend.

**Fix:** pin all four by `@sha256:` digest, with the tag retained in a comment for readability.

---

### F6 — LOW · correctness · WebP uploads are accepted, stored, and then unservable

Backend accepts and stores WebP (`exam.py` `_IMAGE_MIME_TO_EXT` includes `image/webp`;
`images.py` `_SAFE_FILENAME_RE` allows `webp`), but the frontend proxy rejects it:

```ts
const ALLOWED_IMAGE_TYPES = new Set(["image/png", "image/jpeg"]);
```

A WebP upload returns 201 with a URL, the URL is persisted in `question.image_url`, and every
subsequent render 400s. Pick one list and share it, or drop WebP from the upload map.

---

### F7 — LOW · dead config · the extraction routes' 50 MB cap is unreachable in any env that doesn't override the default

`admin_extraction.py:49` and `parent_extraction.py:46` both set `_MAX_UPLOAD_BYTES = 50_000_000`,
but `RequestBodySizeLimitMiddleware` rejects on `Content-Length` first, at
`settings.security.max_request_size` — `10485760` (10 MB) by default in
`src/shared/config.py:183`. Only `common/docker-compose.yml` raises it to 50 MB, so in dev and in
any environment not setting `SECURITY__MAX_REQUEST_SIZE` the per-route limit can never be reached
and `read_upload_capped` never fires its own 413. Derive one value from the other rather than
maintaining two.

---

### F8 — LOW · doc drift · `worker_processes` disagrees with the comment operators will read

`common/apisix_conf/config.yaml` sets `worker_processes: 1`. The `mem_limit: "3g"` comment in
`common/docker-compose.yml:612-620` says "with `nginx_config.worker_processes` pinned to **2**" and
advises "If this ever OOMs again, drop worker_processes to 1 before raising this — the host only
has ~4g free." The escape hatch has already been taken; the comment still offers it. On a ~4 GB
host, the next operator following that comment raises the cap instead. Reconcile.

---

### F9 — LOW · convention · CSRF is required on a GET

`haisir-backend/src/api/routes/haitu.py` — `get_exam_review_chat` takes
`csrf_protected: Annotated[None, Depends(validate_csrf)]`. This is stricter, not weaker, and the
frontend goes through `fetchWithCSRFRetry` so it works today. But `CLAUDE.md` states CSRF applies to
`POST`/`PUT`/`PATCH`/`DELETE`, and the matching APISIX route
(`common/routes/23-api-haitu-exam-review-get.json`) carries no hint of it. Either document the
exception in `02_auth_and_roles.md` or drop the dependency.

---

## Checked and clean

Recorded so pass 2 spends its effort elsewhere — each of these was verified against the files, not
inferred from `TASKS.md`.

- **CVE-2026-21876 remediation** — CRS 4.25.1 LTS (`crs_setup_version=4251`), Coraza v3.7.0, rule
  922110 present with the fixed charset-allowlist regex. Real. (Only its regression test is
  worthless — F1.)
- **Exam-review chat authorization** — client-supplied `history` is now accepted-but-ignored;
  conversation and grounding prompt are rebuilt from server-held session questions.
  `_load_owned_completed_session` gates both `POST /exam-review-chat` and the new
  `GET /exam-review-chat/{attempt_id}` before any data is read.
- **Auth/TLS hardening, all confirmed in the diff** — `verify_aud: False → True` with an explicit
  `audience`; etcd `tls.verify: false → true`; crowdsec LAPI `http → https` with `ssl_verify: true`;
  Keycloak `sslRequired: none → external` plus a real `passwordPolicy`; `enable_admin_ui` and
  `enable_admin_cors` off for staging/prod; `allow_admin` narrowed off the whole Docker subnet;
  `TMPDIR` redirection of the rendered secret file closed; `.templated/` files chmod 600.
- **The `/csp-report` WAF relaxation is correctly scoped.** `id:199150` is chained to
  `REQUEST_METHOD @streq POST` **and** `REQUEST_URI @rx ^/csp-report$`; it *overwrites*
  `tx.allowed_request_content_type` to two report types, which is strictly tighter than the platform
  default, rather than removing rule 920420; a query string fails the anchor and gets no relaxation.
  It sits before the CRS include, which is required for a phase:1 rule. `ctl:requestBodyAccess=Off`
  is bounded — `25-csp-report.json` inherits `secured-anonymous`'s `limit-count` (100/min/IP),
  `limit-conn` and `limit-req`, and the collector caps at 64 KiB **on bytes actually read** (not on
  a spoofable `Content-Length`), `JSON.parse`s inside try/catch, and `JSON.stringify`s before
  logging, so a crafted body cannot forge a second log line.
- **T7.4.2's route-level `response-rewrite` overrides** — the six route files each carry all 7
  pre-existing headers plus the new CSP, matching `02-secured-anonymous.json`'s block exactly.
  Nothing already shipped regressed, and the frontend-upstream routes were correctly left alone.
- **`_PATTERN_ANALYSIS_CACHE`** is bounded (10 000 entries with insertion-order eviction); the two
  write sites that skip `_evict_oldest_if_over_capacity` only overwrite an existing key.
- **`frameHostnames()`** strips `;`, and CR/LF in a header value is rejected by the `Headers` API,
  so the `ALLOWED_VIDEO_HOSTNAMES` env var cannot inject a directive.
- **The middleware matcher's prefetch `missing` conditions** skip only RSC prefetch responses, which
  are not documents; a header cannot be forced onto a victim's cross-origin navigation.
- **`get_safe_filename`** derives the extension from the sniffed MIME, not from the client filename;
  `Path(...).stem` neutralises directory components; the result matches `images.py`'s serving
  allowlist. 32 bits of prefix entropy means a birthday collision (silent overwrite) at roughly 65 k
  images — noted, not filed.

## Not covered by this pass

Stated plainly so G8.1 is not read as broader than it is. Pass 2 should weigh whether any of these
need coverage:

- The vendored `gateway-docker/coraza-proxy-wasm/` source diff beyond version pins and the
  build-time patch assertions (~29 000 of the 31 689 deploy insertions).
- The CRS rule files themselves.
- `other/services/tailscale/tailscale.json` ACL changes, and the Jenkins/CI diffs.
- Frontend component-level changes (question editor, exam form, providers).
- The `review_chat` repository SQL and its migration.
- The test diffs themselves (3 199 frontend / 4 075 backend insertions), except where a test was the
  finding (F1) or explained why one was missed (F2, F3).
