# Security Response Headers (CSP)

> **Target state scope:** browser-enforced security response headers for the user-facing application — principally Content-Security-Policy, plus ownership of the existing header set. Cross-cutting hardening; not tied to a persona phase.
>
> Implementation is split by necessity: the nonce-bearing CSP lives in `haisir-frontend/src/proxy.ts`; the non-nonce headers stay at the gateway in `haisir-deploy/common/plugin_configs/*.json`. The split is deliberate and specified below.
>
> **Status note (2026-07-27):** six security headers are shipped and enforced at the gateway on all four plugin configs. **CSP is set nowhere** — not at the gateway, not in `next.config.ts`, not in `proxy.ts`. The backend sets CSP only on its own `/api` JSON responses, which are not a rendering context. Partial scaffolding exists: `src/app/csp-report/route.ts` accepts reports and **discards them**, and `/csp-report` is already allowlisted in `proxy.ts`'s `PUBLIC_PATHS`. This spec defines the target state; Phase 7 implements it.

---

## Problem

The SPA is the primary XSS target and ships with no Content-Security-Policy.

Present risk is low — React escapes by default, `react-markdown` runs without `rehype-raw` so raw HTML is not rendered, and the codebase contains no `dangerouslySetInnerHTML` and no `eval`. But CSP is the expected defence-in-depth layer: it is what contains an XSS bug that does land, and it is the control an external reviewer will look for first.

Two secondary problems:

- **`X-XSS-Protection: 1; mode=block`** is set on all four plugin configs. The legacy XSS auditor is deprecated and has itself introduced vulnerabilities in some browsers. Current guidance is `0` — explicitly off — with CSP taking over the job.
- **Dead scaffolding.** `csp-report/route.ts` reads the request body and throws it away. Until it persists something, a Report-Only soak produces no evidence.

### Why this cannot be done at the gateway

The 2026-07-02 review recommended adding CSP at the gateway via `response-rewrite`, "nonce-based rather than blanket `unsafe-inline`". **Those two requirements are incompatible.**

A nonce must be unique per request *and* appear both in the header and on every inline `<script>`/`<style>` tag in the rendered HTML. APISIX can set a header, but it cannot mint a per-request value and inject it into the response body. A gateway-set CSP is therefore necessarily static, which forces `script-src 'unsafe-inline'` — a policy that does not meaningfully constrain XSS.

The nonce has to be generated where the HTML is rendered. For this application that is Next.js.

---

## Goal

- A strict, nonce-based CSP on every HTML response, with no `'unsafe-inline'` in `script-src` in production.
- Evidence-driven rollout: `Content-Security-Policy-Report-Only` with a functioning collector, soaked across all real user journeys, before enforcement.
- Clear, documented ownership of every security response header — one owner per header, no silent overlap between gateway and application.

---

## Solution summary

Extend the existing `haisir-frontend/src/proxy.ts` (Next.js 16 renamed `middleware` → `proxy`; the file already exists and holds the onboarding guards) to mint a per-request nonce, emit the CSP header, and forward the nonce as an `x-nonce` request header. Next.js then attaches it automatically to framework scripts, page bundles and its own inline styles.

The gateway keeps the headers that need no nonce and benefit from applying to *all* responses, including those Next.js never renders.

### Why this is unusually cheap here

| Input | Finding | Consequence |
|---|---|---|
| Rendering mode | **15 of 27 pages carry `export const dynamic = "force-dynamic"`; 12 do not** (verified 2026-07-27) | Nonces require dynamic rendering. For the 15, the usual blocker — losing ISR/PPR/CDN caching — was already paid for other reasons. The other 12 must be opted in before enforcement, or they will break. See the caveat below. |
| Styling | **112 CSS Modules**; no Tailwind, no CSS-in-JS | No runtime style injection, so `style-src` can take a nonce rather than `'unsafe-inline'`. |
| Inline scripts | **None** — no `next/script`, no `<script>` tags, no `dangerouslySetInnerHTML` | Nothing needs a nonce applied by hand. |
| Third-party origins | **None hardcoded** in `src/`; no `next/font` | `default-src 'self'` holds; no external allowlisting for scripts or fonts. |
| Proxy file | `src/proxy.ts` exists with a matcher already covering all non-static paths | Extend, do not create. |
| Report collector | `src/app/csp-report/route.ts` exists, returns 204, **stores nothing** | Must persist before the soak has value. |

> **Caveat — the 12 statically-rendered pages.** Next.js applies nonces during *server-side
> rendering*, reading them from the request's CSP header. A page prerendered at build time has no
> request and therefore no nonce, so its inline framework scripts ship without one and a strict
> `script-src` will block them. The 12 pages without `force-dynamic` (7 server components, 5
> `"use client"`) include **all of `/onboarding/*`** — which every new user hits immediately after
> login — and `/admin/*`. Each must be opted into dynamic rendering (`export const dynamic =
> "force-dynamic"`, or `await connection()` from `next/server`) before enforcement, or verified as
> already dynamic for another reason. This is the single most likely cause of a CSP rollback and is
> tracked as its own task in G5.

### Policy

```
default-src 'self';
script-src  'self' 'nonce-{n}' 'strict-dynamic' [dev: 'unsafe-eval'];
style-src   'self' 'nonce-{n}' [dev: 'unsafe-inline'];
img-src     'self' blob: data:;
font-src    'self';
connect-src 'self';
frame-src   <derived from backend allowed_video_hostnames>;
worker-src  'self' blob:;
object-src  'none';
base-uri    'self';
form-action 'self';
frame-ancestors 'none';
upgrade-insecure-requests;
report-uri  /csp-report;
```

Directive rationale for the non-obvious entries:

- **`img-src ... data:`** — exam authoring inlines images as `data:` URIs (`question-editor.tsx`, `readAsDataURL`), and `form-field.module.css` embeds an inline SVG. Phase 7 G3 removes the former; the latter keeps `data:` needed regardless.
- **`img-src ... blob:` / `worker-src 'self' blob:`** — `use-pdf-blob.ts` creates object URLs, and `react-pdf`/pdf.js runs a worker (self-hosted at `/pdf.worker.min.mjs`, so `'self'` covers the script; `blob:` covers pdf.js wrapping it).
- **`object-src 'none'`** is safe — PDFs render to canvas via pdf.js, not through `<object>`/`<embed>`.
- **`frame-src`** — `content-viewer.tsx` embeds video via `<iframe src={item.url}>`, where the URL comes from the database. It is already constrained server-side by `TopicContentSettings.allowed_video_hostnames`.
- **`'unsafe-eval'` in development only** — React uses `eval` in dev to reconstruct server-side error stacks. Neither React nor Next.js use it in production.

---

## Architecture

### Header ownership

One owner per header. Overlap is prohibited: two layers setting the same header produces browser-dependent behaviour and makes the effective policy unauditable.

| Header | Owner | Rationale |
|---|---|---|
| `Content-Security-Policy` | **frontend** (`proxy.ts`) | Requires a per-request nonce; only the renderer can inject it |
| `X-Frame-Options` | gateway | Static; must cover non-Next responses |
| `X-Content-Type-Options` | gateway | Static |
| `Referrer-Policy` | gateway | Static |
| `Strict-Transport-Security` | gateway | Transport-level; belongs at TLS termination |
| `Permissions-Policy` | gateway | Static |
| `X-Robots-Tag` | gateway | Static |
| `X-XSS-Protection` | gateway | Static — value changes to `0` (see BR-CSP-006) |

The gateway additionally keeps `frame-ancestors`, `base-uri`, `object-src` and `form-action` as a **static backstop CSP on non-HTML routes only** — responses Next.js never renders (direct API responses, error pages served by APISIX). It must not set these on frontend HTML routes, where `proxy.ts` owns the full policy.

### Request flow

```
Browser
  │
  ▼
APISIX  ── sets static headers (X-Frame-Options, HSTS, …)
  │       sets backstop CSP on non-HTML routes only
  ▼
Next.js proxy.ts
  │  1. mint nonce (crypto.randomUUID → base64)
  │  2. set Content-Security-Policy[-Report-Only] on the response
  │  3. set x-nonce on the forwarded *request* headers
  ▼
Next.js renderer
     reads the nonce from the CSP header, attaches it to framework
     scripts, page bundles and its own inline styles automatically
```

### Rollout

1. **Wire the collector** — `csp-report/route.ts` persists reports (structured log is sufficient; it already returns 204 and must keep doing so).
2. **Report-Only soak** — `Content-Security-Policy-Report-Only`, no enforcement, across every real journey: login, onboarding, exam authoring with image upload, exam taking, exam review chat, PDF content viewing, video content viewing, parent curriculum, admin.
3. **Review and adjust** against collected reports.
4. **Enforce** — switch the header name, keep `report-uri` live.

The soak must include the **Keycloak login round-trip**. Those routes (`07-auth-login`, `08-auth-logout`, `09-auth-callback`) are APISIX-owned and redirect cross-origin, so they exercise `form-action` and navigation in a way in-app browsing does not.

---

## Policy (business rules)

- **BR-CSP-001 — Every HTML response carries a CSP.** Emitted by `proxy.ts` on all non-static paths.
- **BR-CSP-002 — No `'unsafe-inline'` in `script-src` in production.** Scripts are permitted by nonce plus `'strict-dynamic'`. `'unsafe-eval'` is permitted in development only.
- **BR-CSP-003 — A fresh nonce per request.** Generated with a CSPRNG. Never cached, never reused across requests, never derived from request content.
- **BR-CSP-010 — Every HTML route is dynamically rendered.** A statically prerendered page cannot receive a nonce, so a strict `script-src` blocks its framework scripts. Any new page must be dynamic, or explicitly exempted from CSP enforcement with a recorded reason. This is a standing constraint, not a one-time migration: adding a static page later silently breaks it in production, not at build.
- **BR-CSP-004 — One owner per header.** No header is set by both gateway and application. The ownership table above is authoritative; changing an owner requires updating it.
- **BR-CSP-005 — `frame-src` is derived from the backend video-hostname allowlist.** The CSP allowlist and `TopicContentSettings.allowed_video_hostnames` must not be maintained independently — they are the same trust decision at two enforcement points, and silent drift means either broken embeds or an unenforced CSP.
- **BR-CSP-006 — `X-XSS-Protection: 0`.** The legacy auditor is deprecated and has caused vulnerabilities; CSP replaces it. (Currently `1; mode=block` across four plugin configs.)
- **BR-CSP-007 — Report-Only precedes enforcement.** A functioning collector plus a soak covering all journeys, including the OIDC round-trip, is required before switching to the enforcing header.
- **BR-CSP-008 — The report collector persists reports.** A collector that discards its input provides no evidence and must not be counted as CSP infrastructure.
- **BR-CSP-009 — `report-uri` stays live after enforcement.** Enforced-mode violations are the signal that something broke in production; losing them at cutover discards the value of having built the collector.

---

## Phasing (high level)

| Phase | Repo | Outcome |
|---|---|---|
| 7 · G5 | frontend | `proxy.ts` mints nonce + emits CSP; collector persists; Report-Only soak across all journeys |
| 7 · G5 | frontend | Enforcement after soak review |
| 7 · G7 | deploy | `X-XSS-Protection: 0`; gateway backstop CSP scoped to non-HTML routes |

---

## Out of scope / follow-up

- **Subresource Integrity (SRI).** Next.js offers experimental hash-based CSP via `experimental.sri`, which would permit static generation. Irrelevant here — every page is already `force-dynamic` — and the feature is experimental. Revisit only if static rendering is reintroduced.
- **`Reporting-API` / `report-to`.** `report-uri` is deprecated in favour of the Reporting API, but browser support and Next.js integration are uneven. Deferred; `report-uri` is adequate for a soak.
- **CSP on backend `/api` responses.** Already set. JSON responses are not a rendering context, so this is cosmetic — harmless, left alone.
- **Trusted Types.** A stronger DOM-XSS control than CSP alone. Not specced; would require an audit of every DOM sink and is disproportionate given no `dangerouslySetInnerHTML` exists today.
