# WAF Content Tuning by Corpus

> **Target state scope:** how the gateway WAF (Coraza + OWASP CRS, see `16_gateway_waf.md`) is tuned
> for fields that carry **user-authored content** — markdown, LaTeX, code, chemistry, Indic-script
> prose, AI chat text. Replaces ad-hoc, ticket-driven exclusions with a measured, CI-gated process.
> Implementation lives in `haisir-deploy` (`common/waf/`, `common/scripts/tests/`) and, for the
> production feedback loop, `haisir-frontend` + `haisir-backend`.
>
> **Status (2026-10-06):** P1 started. The synthetic regression corpus
> (`common/scripts/tests/waf-corpus/benign/`, 10 pattern-class files plus a README with the
> add-a-sample process) runs in `waf-harness.sh`: every file must pass as `text` on all three routes
> and still be blocked as a `description` (140/140 green). Each corpus file was confirmed blocked by
> the pre-2026-10-05 config, so none is a no-op. A real, unpublished 26-file technical book was
> probed metadata-only: 26/26 blocked on today's prod config, **26/26 pass** with BR-WAF-017.
> hAITU chat fields are covered too (BR-WAF-023, harness 181/181). A challenger review on
> 2026-10-06 refuted path-confusion (`%2F..%2F`) and Content-Type-confusion bypasses on the
> gateway image, fixed a guard-test blind spot (spread / bracket / function forms) and a Safari
> < 16.4 regex-lookbehind crash risk, and confirmed libinjection SQLi stays a known false-positive
> source for security tutorials that quote classic SQLi payloads.
> Pre-upload check for new books: `common/scripts/tests/waf-probe-docs.sh <folder>` (local,
> metadata-only, exit 1 if any file would be blocked).
> Still to do: the registry, the generator and public corpora, the CRS attack corpus and
> detection matrix, the CI gates, and the production loop. Backlog **B67** (HIGH). Requested by the product
> team after the 2026-10-05 `.md` import failure: *"User will be frustrated with too many WAF blocks …
> we need to find a better way to tune our WAF instead of with user back and forth."*

## Problem

Every content-bearing feature has gone through the same loop: a real user hits a 403, reports it,
we reproduce from their one sample, add a per-rule exclusion, ship — and the next document trips a
sibling rule. The record:

| When | Where | What the WAF read as an attack |
|---|---|---|
| 2026-06-23 → 07-09 (~8 rounds) | hAITU chat `message` / `history` | AI markdown: lists, tables, backticks, blockquotes |
| 2026-07-28 | site-wide `csrf-token` cookie | `942440` SQL comment sequence |
| 2026-07-29 | topic-content PATCH | OCR'd LaTeX next to MCQ options (`932240`, `942410`) |
| 2026-08-01 | topic-content POST `text` | ordinary prose: `said "it's fine"`, `H2O <-> H+` |
| 2026-08 | 4+ unrelated routes | `942200` on comma + quote in plain prose |
| 2026-09-23 | topic-content create/edit | LaTeX + markdown (BR-WAF-016, 9 rules) |
| 2026-10-05 | `.md` import | a technical doc: shell, SQL, backticks, `localhost` URLs (16 rules) |
| (frontend) | parent curriculum page | query param renamed `node` → `nodeId` to dodge `932236` |

**Root causes:**
1. **The content class is the trigger.** CRS signatures are built for generic web parameters.
   Math, code, chemistry and AI-written markdown are made of exactly the tokens those signatures
   look for. Per-rule fixes can't converge: each content class touches dozens of rules.
2. **Nothing measures the false-positive rate.** `waf-harness.sh` asserts about 20 hand-picked
   strings. Whether a change helps or hurts real content is unknown until a user finds out.
3. **No production signal.** A blocked user sees *"Failed to save content. Please try again."*
   Retrying can never help, and nobody is told unless the user complains.

## Goals (all measurable)

- **G1 — No false positives:** 0 blocks on the benign corpus for every registered content field. Release gate.
- **G2 — No lost detection:** for each content field, attack families whose **sink exists** keep at
  least their baseline block rate. Release gate.
- **G3 — Evidence-based exclusions:** every exclusion traces to corpus evidence plus a sink
  analysis, not to one user's file.
- **G4 — Production blocks surface by themselves:** a block on a content route reaches ops within a
  day, without the user reporting it and without the content leaving their browser unless they agree.
- **G5 — A block never loses work:** the user's text survives, and the message never says "try again".

## Design

### 1. Content-field registry — `common/waf/content-fields.yaml`

One entry per (route regex, method, JSON field). Each entry records the **content classes** it
carries and the **sinks** the value reaches, with a code pointer proving each sink claim:

```yaml
- id: topic-text
  routes:
    - {method: POST,  uri: '^/api/topics-contents/?$'}
    - {method: POST,  uri: '^/api/parent/curriculum/topics/[^/]+/content$'}
    - {method: PATCH, uri: '^/api/(topics-contents|parent/curriculum/topic-contents)/[^/]+$'}
  field: json.text
  classes: [prose-en, prose-hi, markdown, latex, mhchem, code, ocr]
  sinks:
    render: MarkdownText          # client-only, no rehype-raw, KaTeX trust:false (BR-EXT-048)
    store: orm                    # bound params only
    llm: haitu-rag                # chunked, top-k
    sql-concat: none              # verified 2026-10-05
    shell: none
    template: none
    url-fetch: none
```

Initial entries:
- topic-content `text`;
- hAITU `message` / `history[*].content`;
- exam essay answers (`18-api-exam-session-submit`);
- topic-content `title` / `description`.

A field-scoped exclusion on a field that is **not** registered is rejected in review.

### 2. Benign corpus — `common/scripts/tests/waf-corpus/benign/`

Stratified by content class, at least 5,000 documents, deterministic:

| Source | What it covers | Notes |
|---|---|---|
| **Regression set** | every past false positive (the table above, BR-WAF-016 items, the 2026-10-05 fixture) | never removable |
| **Synthetic generator** (fixed seed) | building blocks combined into documents: EN/Hindi/Hinglish prose with quotes and apostrophes; markdown (headings, tables, lists, links, blockquotes); code fences in ~20 languages incl. shell, SQL, Python, JS, HTML, YAML, Dockerfile; LaTeX (`\frac`, `aligned`, matrices, `\\[4pt]`, `\text`); mhchem; OCR'd MCQ artifacts; URLs (`localhost`, IPs, YouTube); file paths (`/etc`, `/tmp`, `C:\`); emoji, smart quotes, NBSP, zero-width, RTL | gives breadth no sample set can |
| **Real documents** from the product team | the shapes users actually write | private; see Privacy |
| **Public, licensed** snapshots | OpenStax chapters (CC BY), Wikipedia math/chemistry/programming articles (CC BY-SA) | snapshot with LICENSE, not fetched at test time |
| **AI output** | hAITU answers captured on staging | AI markdown has its own style |

### 3. Attack corpus — `common/scripts/tests/waf-corpus/attack/`

- **CRS regression tests** (`coreruleset/tests/regression`, ~4,000 cases, each labelled with the rule
  it must trigger; already used by `gateway-docker/coraza-proxy-wasm/ftw/`). Payloads are re-homed
  into each registered field's JSON.
- PayloadsAllTheThings / SecLists lists for XSS, SQLi, SSTI and LFI, plus libinjection's test vectors.
- Every payload is labelled by **family**: `xss`, `sqli`, `rce`, `lfi`, `ssrf`, `ssti`, `php`, `java`,
  `nodejs`, `protocol`.

### 4. Runner — `waf-corpus.sh`

- Reuses the `waf-harness.sh` stack: the real gateway image, the real `plugin_configs`, no OIDC.
- Sends every document × registered field, in parallel.
- Attributes rule IDs per request by Coraza `unique_id`, not by `--since` time windows.
- Writes `waf-corpus-report.{json,md}`:
  - **False-positive matrix:** rule ID × content class → count, with sample document IDs (the
    worst offenders first);
  - **Detection matrix:** attack family × field → block rate, with sink-relevant families marked;
  - **Diff against** the committed `waf-corpus-baseline.json`.
- Two modes:
  - **PR smoke:** the regression set plus a fixed 10% sample, a few minutes.
  - **Nightly full:** everything.

### 5. Decision procedure (replaces per-ticket judgement)

For each rule that blocks benign corpus documents on a field:

1. **Does the rule's attack family have no sink for this field** (per the registry)? Then add a
   field-scoped ID or ID-range exclusion in the BR-WAF-017 form. The runner prints the directive and
   a justification stub, and the result still gets a challenger review.
2. **Does the sink exist** (for example XSS on a rendered field)? Keep the rule. In order, try:
   - an application-side fix (a parameter rename like `nodeId`, or BR-WAF-009 server-side
     reconstruction);
   - otherwise, a per-ID exclusion **only if** a high-precision sibling (libinjection `941100`/`942100`)
     still covers the field, and the attack corpus proves detection did not drop.
3. **Never:** raise the threshold (BR-WAF-006), remove a whole tag unscoped (BR-WAF-005), or run
   DetectionOnly in production.

Being honest about the trade-off: a field that carries code **will** lose WAF coverage for the
families that match code. The registry makes that explicit per field, and backs it with sink proof
instead of hope. The WAF is defence in depth; the sink-level controls (ORM bind parameters, a renderer
with no raw HTML, CSP) are the primary defence and are tested directly (BR-EXT-048).

### 6. CI gates

The corpus runs on:
- any change to `plugin_configs` / `routes`;
- any gateway image bump;
- any CRS upgrade (historically where new false positives come from).

The run **fails** on:
- any benign block on a registered field (G1);
- any detection regression in a sink-relevant family (G2).

### 7. Production loop

- **Frontend (G5):** when a content save gets a gateway 403:
  - keep the draft locally;
  - show a non-blaming message: *"Our security filter couldn't verify part of this text. Your text
    is saved as a draft, and our team has been notified."* No "try again";
  - send an automatic report (`request_id`, route, field, length, SHA-256, **never the content**);
  - offer an optional **"Share this text with support"** button, which attaches the content with
    consent. Shared samples join the regression set after review.

  The gateway marks its own blocks with a response header (e.g. `X-WAF-Block: 1`) so the frontend can
  tell a WAF 403 from an authorisation 403.
- **Gateway:** alert on Coraza blocks on registered content routes, with `request_id` and rule IDs.
  Uses the B64 alerting infrastructure.
- **Runbook:** `request_id` → rule IDs from the APISIX log → reproduce with the corpus runner → fix
  via §5 → add the sample to the regression set (BR-WAF-021).

### 8. Privacy

- Real documents and consented samples are user data. Keep them out of logs.
- Store them in a private corpus location, or scrub them before they enter the repo.
- Public snapshots carry their licence files.

## Policy (business rules)

- **BR-WAF-018 — Content fields are registered.** Every request field carrying user-authored
  content has a `content-fields.yaml` entry with classes and code-proven sinks. Exclusions on
  unregistered fields are rejected.
- **BR-WAF-019 — Zero benign blocks is a release gate** for registered fields (corpus runner).
- **BR-WAF-020 — Detection must not regress** for any sink-relevant attack family on any
  registered field.
- **BR-WAF-021 — Every production false positive becomes a permanent regression-corpus item**
  before its fix ships.
- **BR-WAF-022 — A WAF block on a content save never loses the user's text.** The message is
  non-blaming and never says "try again". The block is reported automatically, without content
  unless the user consents.

Related, already shipped 2026-10-05:
- harmful characters (controls, NUL, bidi overrides, unpaired surrogates) are replaced with a
  visible `�` (U+FFFD) on both client and server instead of failing the save;
- oversize text is caught before submit by the counter (BR-EXT-048).

## Phasing

1. **P1, foundations:** registry, regression set, runner, and a first report on the current config.
   Collect the product team's documents.
2. **P2, breadth:** synthetic generator, public snapshots, CRS attack corpus. Set the baseline and
   clear the false positives it finds via §5.
3. **P3, gates:** PR smoke, nightly full run, and the CRS-upgrade gate in CI.
4. **P4, production loop:** frontend draft-preserving UX, report endpoint, gateway block header, alert.

## Out of scope

- Replacing the WAF, or moving content routes off it. Re-evaluate only if P2 shows a content class
  where §5 can't reach zero false positives without losing a sink-relevant family.
- Large documents (> 50 KB) — see B66.
